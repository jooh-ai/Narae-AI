"""엑셀4 이론기준값 vs Base load 실적표 공급가능용량 — 왜 다른가, 계수는 얼마인가.

문제
    담당자 엑셀에는 이론값 성격의 컬럼이 두 개 있고, 같은 날짜에서 값이 다르다.

      ① 엑셀4 '실측데이터' 시트 → **이론기준값(MW)**
         온도 · 대기압 · Actual RH · 열화(Deg)  — 복수기는 **설계값 고정**
         `보정값 = CC실측 − 이론기준값 − W(IGV)` 의 기준선. 우리 Tool 이 재현하는 값.

      ② Base load 실적표 → **공급가능용량(온도+Actual RH+mbar+진공)**
         ① + 그날 **실측 복수기압**까지 반영. 사후 실적 분석용.

    두 시트의 CIT · 대기압 · RH · 복수기압 실측이 모두 동일함이 확인됐으므로
    (2026-08 부장님 대조), 남은 차이는 **진공 항을 쓰는지 여부** 하나뿐이다.

이 스크립트가 하는 일
    ① 재현 검증 — 우리 Tool 이 엑셀4 이론기준값을 재현하는지 (기준선 정합 확인)
    ② 결정적 검증 — 실측 복수기압이 설계와 거의 같은 날짜를 골라낸다.
       진공 항 하나가 원인이라면 **그 날짜에서는 두 컬럼이 일치해야 한다.**
       담당자 값 없이도 부장님이 엑셀 두 개만 열어 1분에 확인할 수 있다.
    ③ 계수 역산 — 담당자 컬럼 값을 주면
          Δ(= ②컬럼 − ①컬럼)  vs  Δv(= 복수기압 설계 − 실측)
       를 회귀해 담당자 진공 보정계수(MW/mbar)를 되찾는다.
    ④ 복수기 청소 효과 환산 — 계수가 나오면 진공 개선 mbar → MW 로 옮긴다.
       2026-10 청소 전후 비교의 근거가 된다.

왜 우리 Tool 은 ①을 쓰는가 (설계 의도, 버그 아님)
    · base_table 이 이미 엑셀2 5중보정(온도·대기압·습도·복수기·열화)의 설계 진공
      기준 산출물이다. 실측 진공을 또 곱하면 이중 보정이다.
    · 입찰은 D+1~D+7 예측이다. 내일의 복수기 진공은 알 수 없다.
    · 진공도 ≈ 33.64 + 1.242 × CIT (r=+0.947). 평균적인 진공 효과는 이미 온도
      곡선에 실려 있고, 설계 대비 편차는 보정값이 흡수한다.

주의 — vacuum_check.py 의 VAC_COEF = 0.1721 은 출처가 문서로 남아 있지 않은
    유산 값이다. 이 스크립트로 역산한 계수가 나오면 그쪽을 갱신할 근거가 된다.
    (2026-08 표본 2건은 0.242 / 0.438 MW/mbar 로 둘 다 0.1721 보다 크다.)

실행:
    python scripts/theory_gap.py                       # ①②만 (담당자 값 불필요)
    python scripts/theory_gap.py --row 2026-04-15=408.3 --row 2026-03-04=441.6
    python scripts/theory_gap.py --mgr baseload.csv     # 날짜,담당자이론값
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wirye_capacity.store import _SEED  # noqa: E402
from wirye_capacity.theory import TheoryEngine  # noqa: E402

FLAT = 1.0          # |Δv| <= 이 값이면 '설계와 사실상 같다' → 결정적 검증 대상
HEAT_CIT = 16.0     # 이 아래는 지역난방 추기가 있는 시기로 본다(복수기 유량 적음)


def ols(xs: list[float], ys: list[float]) -> dict:
    """단순회귀 + 원점통과 회귀. 표본이 모자라면 None 항목으로 돌려준다."""
    n = len(xs)
    out: dict = {"n": n}
    sxx0 = sum(x * x for x in xs)
    out["slope0"] = sum(x * y for x, y in zip(xs, ys)) / sxx0 if sxx0 else None
    if n < 3:
        out.update(a=None, b=None, r=None, sd=None)
        return out
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        out.update(a=None, b=None, r=None, sd=None)
        return out
    b = sxy / sxx
    a = my - b * mx
    res = [y - (a + b * x) for x, y in zip(xs, ys)]
    out.update(a=a, b=b, r=sxy / (sxx * syy) ** 0.5,
               sd=(sum(v * v for v in res) / (n - 2)) ** 0.5 if n > 2 else None)
    return out


def poly_fit(xs: list[float], ys: list[float], deg: int) -> list[float]:
    """최소제곱 다항식 계수 [c0, c1, ...]. 설계 복수기압 곡선 복원용."""
    m = deg + 1
    A = [[x ** k for k in range(m)] for x in xs]
    N = [[sum(A[i][a] * A[i][b] for i in range(len(xs))) for b in range(m)]
         for a in range(m)]
    v = [sum(A[i][a] * ys[i] for i in range(len(xs))) for a in range(m)]
    for c in range(m):
        p = max(range(c, m), key=lambda r: abs(N[r][c]))
        N[c], N[p] = N[p], N[c]
        v[c], v[p] = v[p], v[c]
        for r in range(m):
            if r != c and N[r][c]:
                f = N[r][c] / N[c][c]
                for k in range(c, m):
                    N[r][k] -= f * N[c][k]
                v[r] -= f * v[c]
    return [v[i] / N[i][i] for i in range(m)]


def load_mgr(paths: list[str], rows: list[str]) -> dict[str, float]:
    """담당자 Base load 이론값 → {날짜: MW}. CSV 는 '날짜,값' (# 주석 허용)."""
    out: dict[str, float] = {}
    for spec in rows:
        if "=" not in spec:
            raise SystemExit(f"--row 형식은 날짜=값 입니다: {spec}")
        d, v = spec.split("=", 1)
        out[d.strip()] = float(v)
    for p in paths:
        for ln in Path(p).read_text(encoding="utf-8").splitlines():
            ln = ln.split("#", 1)[0].strip()
            if not ln:
                continue
            parts = [c.strip() for c in ln.replace("\t", ",").split(",")]
            if len(parts) < 2 or not parts[1]:
                continue
            try:
                out[parts[0]] = float(parts[1])
            except ValueError:      # 헤더 행
                continue
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mgr", action="append", default=[], metavar="CSV",
                    help="담당자 Base load 이론값 CSV (날짜,공급가능용량)")
    ap.add_argument("--row", action="append", default=[], metavar="날짜=MW",
                    help="담당자 값 직접 입력 (예: 2026-04-15=408.3)")
    args = ap.parse_args()

    seed = {r["date"]: r
            for r in json.loads(_SEED.read_text(encoding="utf-8"))}
    eng = TheoryEngine()

    print("=" * 78)
    print("① 재현 검증 — 우리 Tool 이 엑셀4 '이론기준값' 을 재현하는가")
    print("=" * 78)
    worst = (0.0, "")
    for d, r in sorted(seed.items()):
        mine = eng.theory_cc(r["cit"], r["press"], rh=r.get("rh"))
        e = abs(mine - r["theory"])
        if e > worst[0]:
            worst = (e, d)
    print(f"   누적 {len(seed)}건 최대오차 {worst[0]:.3f} MW ({worst[1]})")
    print("   → 기준선은 정합. 담당자 Base load 컬럼과의 차이는 정의 차이다.")

    have = [r for r in seed.values() if r.get("cp_design") is not None]
    have.sort(key=lambda r: r["cit"])
    co = poly_fit([r["cit"] for r in have], [r["cp_design"] for r in have], 3)
    print(f"\n   설계 복수기압 곡선(3차, n={len(have)}): "
          + " + ".join(f"{c:+.6g}·CIT^{k}" for k, c in enumerate(co)))
    print("   → 설계 진공은 CIT 만의 함수다(날짜별 판단이 아니다).")

    print()
    print("=" * 78)
    print(f"② 결정적 검증 — 실측 복수기압이 설계와 거의 같은 날짜 (|Δv| ≤ {FLAT} mbar)")
    print("=" * 78)
    print("   진공 항 하나가 원인이라면 이 날짜들에서는 두 컬럼이 일치해야 한다.")
    print(f"\n   {'날짜':12}{'CIT':>6}{'실측':>7}{'설계':>7}{'Δv':>7}   엑셀4 이론기준값")
    flat = [r for r in have if abs(r["cp_design"] - r["cp_meas"]) <= FLAT]
    for r in sorted(flat, key=lambda r: abs(r["cp_design"] - r["cp_meas"])):
        dv = r["cp_design"] - r["cp_meas"]
        print(f"   {r['date']:12}{r['cit']:6.1f}{r['cp_meas']:7.1f}"
              f"{r['cp_design']:7.1f}{dv:+7.1f}{r['theory']:19.2f}")
    print(f"\n   → 위 {len(flat)}건의 Base load '공급가능용량' 을 확인해 주십시오.")
    print("      거의 같다  → 진공 항 차이로 확정. 계수만 역산하면 끝난다.")
    print("      크게 다르다 → 진공 외에 다른 항(Deg 등)이 하나 더 다르다.")

    mgr = load_mgr(args.mgr, args.row)
    if not mgr:
        print("\n   담당자 값을 주시면 ③ 계수 역산까지 진행합니다:")
        print("      python scripts/theory_gap.py --row 2026-04-15=408.3 ...")
        return

    print()
    print("=" * 78)
    print("③ 계수 역산 — Δ(담당자 − 엑셀4) vs Δv(설계 − 실측 복수기압)")
    print("=" * 78)
    print(f"   {'날짜':12}{'CIT':>6}{'Δv':>7}{'엑셀4':>9}{'담당자':>9}"
          f"{'Δ':>8}{'MW/mbar':>9}  구분")
    pts: list[tuple[float, float, float]] = []      # (Δv, Δ, CIT)
    for d, mv in sorted(mgr.items()):
        r = seed.get(d)
        if r is None:
            print(f"   {d:12}  누적 DB 에 없는 날짜 — 건너뜀")
            continue
        if r.get("cp_design") is None or r.get("cp_meas") is None:
            print(f"   {d:12}  복수기압 결측 — 건너뜀")
            continue
        dv = r["cp_design"] - r["cp_meas"]
        dd = mv - r["theory"]
        band = "난방기" if r["cit"] < HEAT_CIT else "비난방기"
        per = f"{dd / dv:9.3f}" if abs(dv) > 0.05 else "        —"
        print(f"   {d:12}{r['cit']:6.1f}{dv:+7.1f}{r['theory']:9.2f}"
              f"{mv:9.2f}{dd:+8.2f}{per}  {band}")
        pts.append((dv, dd, r["cit"]))

    if len(pts) < 2:
        print("\n   표본이 2건 미만입니다 — 회귀 생략.")
        return

    def show(label: str, sub: list[tuple[float, float, float]]) -> None:
        if len(sub) < 2:
            print(f"   {label:10} n={len(sub)} — 표본 부족")
            return
        f = ols([p[0] for p in sub], [p[1] for p in sub])
        line = f"   {label:10} n={f['n']:2}  원점통과 {f['slope0']:+.3f} MW/mbar"
        if f["b"] is not None:
            line += (f"   |  절편 {f['a']:+.2f}  기울기 {f['b']:+.3f}"
                     f"  r={f['r']:+.3f}  잔차sd {f['sd']:.2f}")
        print(line)

    print()
    show("전체", pts)
    show("난방기", [p for p in pts if p[2] < HEAT_CIT])
    show("비난방기", [p for p in pts if p[2] >= HEAT_CIT])
    print("\n   난방기·비난방기 기울기가 다르면 정상이다 — 열병합이라 지역난방")
    print("   추기량에 따라 복수기로 내려가는 증기량이 달라, mbar 당 민감도가 바뀐다.")

    f = ols([p[0] for p in pts], [p[1] for p in pts])
    k = f["slope0"]
    if k:
        print()
        print("=" * 78)
        print("④ 복수기 청소 효과 환산 (2026-10 예정)")
        print("=" * 78)
        print(f"   역산 계수 {k:+.3f} MW/mbar 기준")
        for imp in (3, 5, 8, 10):
            print(f"      진공 {imp:2}mbar 개선 → 출력 {k * imp:+.2f} MW")
        print("\n   ※ 이 계수는 담당자 '이론값' 컬럼의 보정계수다. 실제 출력이")
        print("      그만큼 올라간다는 보증은 아니다 — 청소 후 실측으로 확인해야 한다.")
        print("      (vacuum_check.py --split 2026-10-01)")


if __name__ == "__main__":
    main()
