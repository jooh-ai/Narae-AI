"""엑셀4 이론기준값 vs Base load 실적표 공급가능용량 — 왜 다른가.

담당자 엑셀에는 이론값 성격의 컬럼이 두 개 있고, 같은 날짜에서 값이 다르다.

  ① 엑셀4 '실측데이터' → **이론기준값(MW)**
     `보정값 = CC실측 − 이론기준값 − W(IGV)` 의 기준선. 우리 Tool 이 재현하는 값.
  ② Base load 실적표 → **공급가능용량(온도+Actual RH+mbar+진공)**
     사후 실적 분석용. Dev.(MW) = CC실측(Net) − 이 컬럼(Net).

결론 (2026-08-24, 실적표 58건 전수 대조)
    차이는 **진공 항이 아니다. 온도에 따라 벌어지는 곡선 차이다.**

        Δ(담당자 − 우리) = -2.196 + 0.1183 × CIT     r = +0.751, 잔차 sd 1.16

    CIT 0°C 에서 -2.2 MW, 36°C 에서 +2.1 MW — 온도 전 구간에 걸쳐 4.3 MW 벌어진다.
    즉 담당자 Base load 시트가 쓰는 곡선은 우리가 동결한 엑셉4 온도 Profile
    테이블과 **모양이 다르다**(저온에서 낮고 고온에서 높다).

    진공은 있어도 부차적이다. CIT 추세를 뺀 잔차와 진공잔차의 상관은
    r = -0.344, 기울기 -0.060 MW/mbar (부호는 물리와 맞지만 크기가 작다).
    남은 흩어짐 sd 1.09 MW 를 설명하지 못한다.

기각된 가설과 그 이유 — 같은 함정을 다시 밟지 않기 위해 남긴다
    가설 A "컬럼 이름에 +진공 이 있으니 진공 항 하나 차이다"
        표본 2건(2026-03-04, 04-15)에서 부호가 맞아 그럴듯해 보였다. 58건으로
        늘리자 무너졌다. 2건으로 세운 가설은 2건짜리 가설이다.
    가설 B "GT 도 같은 비율로 움직이니 진공(ST 전용)이 아니다"
        **이 검증 자체가 무효다.** 담당자 이론 GT/CC 비는 우리 base 테이블의
        GT비와 sd 0.00008(기계정밀도)로 일치한다 — 즉 담당자 이론 GT 는 CC 를
        곡선 GT비로 나눈 값이고 독립 정보가 아니다. ΔGT 의 비례는 원인과 무관하다.
        (실측 GT/CC 비는 sd 0.0032 로 흩어진다. 실측은 독립이고 이론은 아니다.)

우리 Tool 은 ①을 쓰는 게 맞다 — 그리고 곡선 차이는 최종 입찰값에서 상쇄된다
    `보정값 = CC실측 − 이론기준값` 이므로 기준선을 바꾸면 보정값이 같은 크기만큼
    반대로 움직인다. 프로파일 생성 때 다시 더하므로 서로 지워진다. 실제로
    기준선을 담당자 곡선으로 바꿔 36건을 다시 쌓고 GP 로 프로파일을 만들면

        CIT  3 ~ 36°C (시험 33건)     |최대| 0.12 MW   ← 사실상 완전 상쇄
        CIT -5 ~  2°C (시험  3건)     |최대| 2.79 MW
        CIT ≤ -6, ≥ 37°C (시험 없음)  |최대| 4.56 MW

    저온에서 상쇄가 깨지는 것은 GP 가 데이터 희박한 곳에서 사전평균으로
    수축하기 때문이다 — 기준선에 더한 직선이 그대로 빠져나오지 않는다.
    극저온 입찰이 실제로 나가는 구간이면 (a) 담당자에게 어느 곡선이 최신인지
    확인하고 (b) 저온 시험 이력을 쌓아야 한다. 지금 저온 시험은 3건뿐이다.

입력값 정합 (2026-08 대조)
    누적 DB(엑셀4 출처)와 실적표의 CIT·대기압·RH·진공도·CC실측을 36건 대조한
    결과 불일치는 소수점 반올림 4건(0.1)뿐이다. **진공도는 전 건 일치한다** —
    2026-01-08 도 양쪽 모두 32.6 mbar 로 기록돼 있다.

실행:
    python scripts/theory_gap.py
    python scripts/theory_gap.py --csv other.csv
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wirye_capacity import constants as C  # noqa: E402
from wirye_capacity.gp import GPCorrectionCurve  # noqa: E402
from wirye_capacity.store import _SEED  # noqa: E402
from wirye_capacity.theory import (TheoryEngine, igv_turnup,  # noqa: E402
                                   rh_corr)

DATA = Path(__file__).resolve().parent / "data" / "baseload.csv"
# 진공 기준선 (vacuum_check.py 와 동일): 진공도 = 33.64 + 1.242 × CIT, r=+0.947
VAC_A, VAC_B = 33.64, 1.242


def stat(v: list[float]) -> tuple[float, float, float]:
    n = len(v)
    mu = sum(v) / n
    sd = (sum((x - mu) ** 2 for x in v) / (n - 1)) ** 0.5 if n > 1 else float("nan")
    return mu, sd, max(abs(x) for x in v)


def ols(xs: list[float], ys: list[float]) -> tuple[float, float, float, float]:
    """단순회귀 → (절편, 기울기, r, 잔차 sd)."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    b = sxy / sxx
    a = my - b * mx
    res = [y - (a + b * x) for x, y in zip(xs, ys)]
    sd = (sum(v * v for v in res) / (n - 2)) ** 0.5 if n > 2 else float("nan")
    return a, b, sxy / (sxx * syy) ** 0.5, sd


def load(path: Path) -> list[dict]:
    """담당자 Base Load 실적표 CSV 로드."""
    cols = ("date", "cit", "cip", "press", "rh", "vac",
            "a_gt", "a_st", "a_cc_g", "a_cc_n", "s_gt", "s_st", "s_cc_g", "s_cc_n")
    out = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.split("#", 1)[0].strip()
        if not ln:
            continue
        p = [c.strip() for c in ln.split(",")]
        if len(p) != len(cols):
            raise SystemExit(f"{path.name}: 열 개수가 {len(cols)} 이어야 합니다 — {ln[:40]}")
        try:
            out.append({"date": p[0],
                        **{k: float(v) for k, v in zip(cols[1:], p[1:])}})
        except ValueError:              # 헤더 행
            continue
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(DATA), help="Base load 실적표 CSV")
    args = ap.parse_args()

    rows = load(Path(args.csv))
    eng = TheoryEngine()
    seed = {r["date"]: r for r in json.loads(_SEED.read_text(encoding="utf-8"))}
    kf = (C.REF_DEG / C.DEFAULT_DEG)

    def ours(r: dict) -> float:
        """우리 이론기준값 = 엑셀4 이론기준값 (검증 오차 0.19 MW)."""
        return (eng.base_cc(r["cit"]) * kf / eng.p_corr(r["press"])
                / rh_corr(r["rh"], r["cit"]))

    print("=" * 74)
    print(f"① 재현 검증 — 우리 Tool 이 엑셀4 '이론기준값' 을 재현하는가 ({len(seed)}건)")
    print("=" * 74)
    e = [(abs(eng.theory_cc(r["cit"], r["press"], rh=r.get("rh")) - r["theory"]), d)
         for d, r in seed.items()]
    mx = max(e)
    print(f"   최대오차 {mx[0]:.3f} MW ({mx[1]})  → 기준선은 정합하다.")

    print()
    print("=" * 74)
    print(f"② Base load '공급가능용량' 과의 차이는 무엇의 함수인가 (n={len(rows)})")
    print("=" * 74)
    d = [r["s_cc_g"] - ours(r) for r in rows]
    mu, sd, m = stat(d)
    print(f"   Δ = 담당자 − 우리 : 평균 {mu:+.3f}  sd {sd:.3f}  |최대| {m:.2f} MW")
    print(f"\n   {'변수':10}{'r':>8}{'기울기':>11}")
    cand = {"CIT": [r["cit"] for r in rows],
            "대기압": [r["press"] for r in rows],
            "RH": [r["rh"] for r in rows],
            "진공도": [r["vac"] for r in rows],
            "진공잔차": [r["vac"] - (VAC_A + VAC_B * r["cit"]) for r in rows]}
    for name, xs in cand.items():
        _, b, r_, _ = ols(xs, d)
        print(f"   {name:10}{r_:+8.3f}{b:+11.4f}")

    a, b, r_, sdr = ols(cand["CIT"], d)
    lo, hi = min(cand["CIT"]), max(cand["CIT"])
    print(f"\n   Δ = {a:+.3f} {b:+.4f} × CIT     r={r_:+.3f}  잔차sd {sdr:.3f}")
    print(f"   → CIT {lo:.1f}°C {a + b * lo:+.1f} MW,  {hi:.1f}°C {a + b * hi:+.1f} MW"
          f" — 관측 구간에서 {b * (hi - lo):.1f} MW 벌어지는 곡선 모양 차이다.")

    res = [y - (a + b * x) for x, y in zip(cand["CIT"], d)]
    _, b2, r2, sd2 = ols(cand["진공잔차"], res)
    print(f"\n   CIT 추세 제거 후 잔차 vs 진공잔차 : r={r2:+.3f}"
          f"  {b2:+.4f} MW/mbar  잔차sd {sd2:.3f}")
    print("   → 진공은 있어도 부차적이다. 남은 흩어짐을 설명하지 못한다.")

    print()
    print("=" * 74)
    print("③ 왜 GT 검증으로는 판정할 수 없는가 (가설 B 기각)")
    print("=" * 74)
    g1 = [r["s_gt"] / r["s_cc_g"] - eng.base_gt(r["cit"]) / eng.base_cc(r["cit"])
          for r in rows]
    g2 = [r["a_gt"] / r["a_cc_g"] - eng.base_gt(r["cit"]) / eng.base_cc(r["cit"])
          for r in rows]
    print(f"   GT/CC 비 − base 테이블 GT비")
    print(f"      담당자 이론값 : sd {stat(g1)[1]:.5f}   |최대| {stat(g1)[2]:.5f}")
    print(f"      실측(Actual) : sd {stat(g2)[1]:.5f}   |최대| {stat(g2)[2]:.5f}")
    print("   → 담당자 이론 GT 는 CC 를 곡선 GT비로 나눈 값(기계정밀도로 일치).")
    print("      독립 정보가 아니므로 ΔGT 의 비례는 원인을 가리지 못한다.")

    print()
    print("=" * 74)
    print("④ 최종 입찰값에 영향이 있는가 — 기준선을 담당자 곡선으로 바꿔 재계산")
    print("=" * 74)
    use = [r for r in seed.values() if r["date"] in {x["date"] for x in rows}]

    def bid(shift) -> dict[int, float]:
        gp = GPCorrectionCurve([{"cit": r["cit"],
                                 "corr": r["cc_meas"] - (r["theory"] + shift(r["cit"]))
                                 - r["w"]} for r in use])
        return {t: eng.base_cc(t) * kf + shift(t) + igv_turnup(t) + gp(t)
                for t in range(-20, 41)}

    p0, p1 = bid(lambda t: 0.0), bid(lambda t: a + b * t)
    cits = sorted(r["cit"] for r in use)
    n_dense = sum(1 for c in cits if c >= 3)
    print(f"   누적 {len(use)}건 재적층. 시험 CIT {cits[0]:.1f} ~ {cits[-1]:.1f}°C "
          f"— 3°C 이상에 {n_dense}건, 그 아래는 {len(cits) - n_dense}건뿐이다.")
    print(f"\n   {'CIT':>5}{'우리 기준선':>13}{'담당자 기준선':>15}{'차이':>9}")
    for t in range(-20, 41, 5):
        print(f"   {t:5}{p0[t]:13.2f}{p1[t]:15.2f}{p1[t] - p0[t]:+9.3f}")

    bands = [("시험 촘촘 (CIT 3~36)", range(3, 37)),
             ("저온 경계 (CIT -5~2, 시험 2건)", range(-5, 3)),
             ("완전 외삽 (CIT ≤ -6, ≥ 37)",
              [t for t in range(-20, 41) if t <= -6 or t >= 37])]
    print()
    for lab, rng in bands:
        v = [abs(p1[t] - p0[t]) for t in rng]
        print(f"   {lab:32} |최대| {max(v):6.3f} MW")
    print("\n   → 시험이 촘촘한 구간에서는 곡선 차이가 보정값에 흡수되어 사실상")
    print("      완전히 상쇄된다. 우리 입찰값은 그 구간에서 안전하다.")
    print("   → 저온으로 갈수록 상쇄가 깨진다. GP 가 데이터 희박한 곳에서 평균으로")
    print("      수축하기 때문에, 기준선에 더한 직선이 그대로 빠져나오지 않는다.")
    print("      극저온 입찰이 실제로 나가는 구간이면 담당자에게 어느 곡선이")
    print("      최신인지 확인하고, 저온 시험 이력을 쌓아야 한다.")


if __name__ == "__main__":
    main()
