"""복수기 진공도 점검 — 계절 효과인가, 설비 변화인가.

왜 필요한가
    진공도는 외기 온도의 함수다. 외기가 오르면 냉각수 온도가 오르고 진공이
    나빠진다(담당자 설명). 누적 31건에서 실제로 확인된다:

        진공도 = 34.15 + 1.169 × CIT      r = +0.958   (분산의 92% 설명)

    그래서 **보정곡선에 진공 항을 따로 넣지 않는다**. CIT 기반 곡선이 이미 이
    효과를 담고 있어서, 진공 항을 더하면 같은 정보를 두 번 세게 된다. 실제로
    넣어 보면 LOOCV 가 나빠졌다(MAE 1.239 → 1.291). 그리고 입찰 시점에 알 수
    있는 것은 예보 온도뿐이다 — 내일의 진공은 알 수 없다.

무엇을 보는가
    ① 온도 기준선 — 진공도가 CIT 로 얼마나 설명되는가 (r = +0.947, 확실하다)
    ② 진공 잔차 — 같은 온도인데 진공이 기준선보다 나쁜 회차를 짚는다.
       이건 계절이 아니라 그날의 설비 상태다. 미달이 나오면 여기를 먼저 본다.
       다만 **누적 전체에서 진공 잔차가 보정값을 설명하지는 못한다**(아래).
    ③ 연차 비교 — 같은 온도대에서 진공이 해마다 나빠지는가. 계절 기전이라면
       같은 CIT 에서 같은 진공이 나와야 한다. 다르면 복수기 쪽 변화다
       (관 오염 · 냉각탑 성능 · 진공 누설).
    ④ --split 로 정비 전/후 비교 (복수기 청소 효과 확인)

2026-08 확인 사항 — 어디까지 말할 수 있나
    확실한 것
      · 진공도 = 33.64 + 1.242 × CIT,  r = +0.947 (분산의 90%). 외기→냉각수→진공.
        **이것만 확실하다.** 진공도는 사실상 온도의 함수다.
      · 2026-07-22 는 진공 잔차 +12.6 mbar 로 누적에서 가장 큰 이탈이다.
        (그 회차의 보정잔차와 크기가 맞지만, n=1 이므로 인과가 아니다 — 아래 기각 참조)

    기각 (2026-09-01 재확인)
      · **진공 잔차는 보정값을 설명하지 못한다.** 원시 상관은 강해 보이지만
        (보정값 vs 진공도 r=-0.82) 진공도가 온도의 함수라서 생긴 그림자다.
        온도를 통제하면 40건 r=+0.003 으로 사라진다.
      · 부분집합을 잘라 CIT>=20·2026(n=9)만 보면 r=-0.675 로 임계값(0.666)을
        간신히 넘지만, **한 건씩 빼면 9건 중 6건에서 유의성을 잃는다.** 한두
        회차가 만든 관계다. 결론으로 쓸 수 없다.
      · 연차 비교 +8.4 mbar(25~30°C)도 **66% 가 2026-07-22 한 건에서 나왔다.**
        같은 온도 짝으로 직접 보면 -0.6 / +9.9 로 엇갈린다. 계통적 열화가 아니다.
      · 진공 항을 넣으면 LOOCV 예측오차가 오히려 나빠진다(1.27 → 1.28 MW).

    같은 함정에 세 번 빠졌다 — 이 기록을 남기는 이유
      회차 1 (2026-08-24)  IGV 실시 5건만 보고 r=-0.85 → n=36 에서 +0.09 → 기각
      회차 2 (2026-08-26)  CIT>=20·2026 9건에서 r=-0.675, 기울기가 물리와 맞아
                           '2026년에만 관계가 나타난다' 고 판단 → 기각
      회차 3 (같은 날)      8월 4건만 보면 r=-0.775 → n=4 임계값 0.95 에 못 미침

      전부 **부분집합을 잘라 큰 r 을 본 것**이다. 표본을 줄이면 가짜 관계가 더
      쉽게 보인다. 그래서 ② 에 유의성(임계 r)과 안정성(한 건씩 빼기)을 상설
      출력으로 넣었다. **부분집합에서 관계가 보이면 먼저 이 두 칸을 보라.**

대응은 진공 항 추가가 아니라 안전마진이다. 진공 잔차는 입찰 전날 알 수 없다.

실행:
    python scripts/vacuum_check.py
    python scripts/vacuum_check.py --split 2026-10-01        # 복수기 청소 전/후
    python scripts/vacuum_check.py --add 2026-08-12,33.5,998.0,55.0,383.0,81.0
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
from wirye_capacity.theory import TheoryEngine, igv_turnup  # noqa: E402

# 진공 편차 1 mbar 가 출력에 주는 영향 (기존 회귀 Δ이론 = +0.1721×편차, r=0.983)
VAC_COEF = 0.1721



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


_T05 = {1: 12.71, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
        8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145,
        15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086}


def _crit_r(n: int) -> float:
    """상관계수 유의 임계값 (α=0.05 양측). 표본이 작으면 |r| 이 커야 한다.

    n=4 면 0.950, n=9 면 0.666, n=40 면 0.312. 작은 부분집합에서 나온 큰 r 을
    '관계 발견' 으로 오독하지 않도록 항상 함께 출력한다.
    """
    import math
    if n < 3:
        return float("nan")
    df = n - 2
    t = _T05.get(df, 2.02)
    return t / math.sqrt(df + t * t)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--add", action="append", default=[], metavar="CSV",
                    help="회차 추가: 날짜,CIT,대기압,RH,CC_Gross,진공도")
    ap.add_argument("--split", metavar="YYYY-MM-DD",
                    help="이 날짜 전/후로 갈라 진공 잔차를 비교한다. 복수기 청소·정비 "
                         "효과 확인용 (예: --split 2026-10-01)")
    a = ap.parse_args()

    seed = json.loads(_SEED.read_text(encoding="utf-8"))
    eng = TheoryEngine()
    gp = GPCorrectionCurve([{"cit": r["cit"], "corr": r["corr"]} for r in seed])
    have = {r.get("date") for r in seed}

    # 누적(씨앗)에 아직 없는 회차만 --add 로 받는다. 이미 있는 날짜를 또 넣으면
    # 같은 회차가 두 번 세어져 연차 비교·잔차 통계가 어긋난다.
    new = []
    for spec in a.add:
        f = spec.split(",")
        if len(f) != 6:
            raise SystemExit(f"--add 형식은 날짜,CIT,대기압,RH,CC,진공 입니다: {spec}")
        d = f[0].strip()
        if d in have:
            print(f"  [건너뜀] {d} 는 이미 누적에 있습니다 (중복 계산 방지)\n")
            continue
        new.append((d, *(float(v) for v in f[1:])))

    # 회차 목록을 먼저 만든다. --add 로 받은 회차도 ①의 기준선 적합에 포함해야
    # ②의 잔차가 "자기 자신이 빠진 기준선" 대비로 재이지 않는다. 예전에는 ①을
    # 씨앗만으로 적합하고 ②를 씨앗+추가로 재서, 추가 회차의 진공 잔차가 실제보다
    # 부풀려 보였다.
    rows = [(r["date"], r["cit"], r["cp_meas"], r["corr"]) for r in seed if r.get("date")]
    for d, cit, p, rh, cc, vac in new:
        rows.append((d, cit, vac,
                     cc - eng.theory_cc(cit, p, C.DEFAULT_DEG, rh=rh) - igv_turnup(cit)))

    # ── ① 온도 기준선 ────────────────────────────────────────────────────
    a0, b0, r0, sd0 = ols([r[1] for r in rows], [r[2] for r in rows])
    print(f"① 온도 기준선 ({len(rows)}건)")
    print(f"   진공도 = {a0:.2f} {b0:+.3f} × CIT     r = {r0:+.3f}   잔차 sd {sd0:.2f} mbar")
    print(f"   → CIT 가 진공도 분산의 {r0 * r0 * 100:.0f}% 를 설명한다. 외기→냉각수→진공 기전.")
    print("   → 그래서 보정곡선에 진공 항을 따로 넣지 않는다(같은 정보 이중 계산).")

    # ── ② 진공 잔차 vs 보정값 잔차 ───────────────────────────────────────
    # 기준선에서 2σ 이상 벗어난 회차를 짚는다. 다만 그것이 미달의 **원인**이라고
    # 말할 근거는 아직 없다 — 아래 상관·안정성 검정을 먼저 보라.
    # 보정잔차는 LOOCV 로 낸다. 그 회차를 포함한 곡선으로 재면 잔차가 곡선에
    # 흡수돼(in-sample) 관계가 사라진다 — 실제로 그렇게 재면 r 이 +0.13 으로
    # 나와 물리와 어긋난 것처럼 보인다.
    pts = [{"cit": c, "corr": q} for _, c, _, q in rows]
    vr_all, cr_all, odd = [], [], []
    for i, (d, cit, vac, corr) in enumerate(rows):
        vr = vac - (a0 + b0 * cit)
        loo = GPCorrectionCurve([p for j, p in enumerate(pts) if j != i])
        cr = corr - loo._post(cit)[0]
        vr_all.append(vr)
        cr_all.append(cr)
        if abs(vr) > 2 * sd0:
            odd.append((d, cit, vac, a0 + b0 * cit, vr, cr))
    print(f"\n② 진공 잔차가 출력을 설명하는가 (누적 {len(rows)}건, 보정잔차는 LOOCV)")
    print(f"   물리 예상 기울기 {-VAC_COEF:+.3f} MW/mbar")
    print(f"   {'구간':30s} {'n':>3s} {'r':>7s} {'기울기':>9s}")
    cits_r = [r[1] for r in rows]
    for lo, hi, lab in ((-99, 99, "전체"),
                        (20, 99, "CIT>=20 (출력이 진공에 민감)"),
                        (-99, 20, "CIT<20 (상한·저온 — 영향 작음)")):
        idx = [i for i, t in enumerate(cits_r) if lo <= t < hi]
        if len(idx) < 4:
            continue
        _, bb, rr, _ = ols([vr_all[i] for i in idx], [cr_all[i] for i in idx])
        print(f"   {lab:30s} {len(idx):3d} {rr:+7.3f} {bb:+9.3f}")
    print("   → 관계가 약하다. 누적 전체에서 진공 잔차로 보정값을 예측할 수 없다.")

    # 부분집합을 잘라 보는 것은 표본을 줄이는 일이다. 표본이 작으면 가짜 관계가
    # 더 쉽게 보인다. 이 프로젝트는 같은 변수(진공)에서 이미 두 번 속았다:
    #   n=5  r=-0.85  → n=36 r=+0.09   (기각)
    #   n=4  r=-0.775 → 임계 0.950 미달, 애초에 유의하지 않았다  (기각)
    #   n=9  r=-0.679 → 임계 0.666 을 0.009 차로 넘겼으나 한 건씩 빼면
    #                   6/9 에서 유의성 상실  (기각, 2026-09-01)
    # 세 번 모두 "부분집합을 골라서 만든 상관" 이었다.
    # 그래서 부분집합 결과는 **반드시 유의성·안정성과 함께** 출력한다.
    print(f"\n   부분집합 검정 — 유의성과 안정성을 함께 본다")
    print(f"   {'구간':22s} {'n':>3s} {'r':>7s} {'임계r':>7s} {'기울기':>9s} {'안정':>6s}  판정")
    hot = [i for i, t in enumerate(cits_r) if t >= 20]
    for lab, sel in (("CIT>=20 전체", hot),
                     ("CIT>=20 · 2025", [i for i in hot if rows[i][0] < "2026-01-01"]),
                     ("CIT>=20 · 2026", [i for i in hot if rows[i][0] >= "2026-01-01"])):
        if len(sel) < 4:
            print(f"   {lab:22s} {len(sel):3d}   표본 부족")
            continue
        _, bb, rr, _ = ols([vr_all[i] for i in sel], [cr_all[i] for i in sel])
        c = _crit_r(len(sel))
        # 안정성: 한 건씩 빼도 유의성이 유지되는 비율
        keep = 0
        for k in range(len(sel)):
            rest = [i for j, i in enumerate(sel) if j != k]
            _, _, r2, _ = ols([vr_all[i] for i in rest], [cr_all[i] for i in rest])
            if abs(r2) > _crit_r(len(rest)):
                keep += 1
        ok = abs(rr) > c and keep >= len(sel) * 0.8
        print(f"   {lab:22s} {len(sel):3d} {rr:+7.3f} {c:7.3f} {bb:+9.4f} "
              f"{keep:3d}/{len(sel):<2d}  {'유의·안정' if ok else '기각'}")
    print("   → '안정' 은 한 건씩 빼도 유의성이 남는 비율이다. 이것이 80% 미만이면")
    print("      한두 건이 만든 관계이므로 결론으로 쓰지 않는다.")
    print("   → 2026-10 복수기 청소 전후 비교가 결정적 시험이다(--split 2026-10-01).")
    print(f"\n   기준선에서 2σ({2 * sd0:.1f} mbar) 이상 벗어난 회차 — 참고용")
    if not odd:
        print("     없음")
    else:
        print(f"   {'일자':11s} {'CIT':>5s} {'진공':>6s} {'기준선':>7s} {'진공잔차':>8s} "
              f"{'환산(미실증)':>8s} {'보정잔차':>8s}")
        for d, cit, vac, base, vr, cr in sorted(odd, key=lambda x: -abs(x[4])):
            print(f"   {d:11s} {cit:5.1f} {vac:6.1f} {base:7.1f} {vr:+8.1f} "
                  f"{-VAC_COEF * vr:+8.2f} {cr:+8.3f}")
    print("   ※ '환산' 은 물리 계수 -0.172 MW/mbar 를 곱한 값일 뿐이고, 위 검정에서")
    print("      보듯 우리 데이터로는 실증되지 않았다. 미달 원인으로 단정하지 말 것.")
    print("   ※ 저온이 출력 상한(Net 462)에 걸려 감도가 안 보인다는 설명도 확인되지")
    print("      않았다 — 저온 18건 중 상한에 걸리는 회차는 1건뿐이다.")

    # ── ③ 연차 비교 ──────────────────────────────────────────────────────
    print("\n③ 같은 온도대 진공도 — 연차 비교")
    print("   계절 기전이라면 같은 CIT 에서 같은 진공이 나와야 한다.")
    print("   다르면 복수기 쪽 변화일 수 있다(관 오염 · 냉각탑 성능 · 진공 누설).")
    print("   ※ 구간 평균의 차이는 회차가 몇 건뿐이어서 한 건에 크게 흔들린다.")
    print("      아래 목록에서 CIT 가 가장 가까운 짝끼리 직접 비교해 보라 — 평균")
    print("      차이와 부호가 다르게 나오는 구간이 있다. 연차 열화는 미확정이다.")
    for lo, hi in ((20, 25), (25, 30), (30, 35), (35, 41)):
        sub = [(d, c, v) for d, c, v, _ in rows if lo <= c < hi]
        y25 = [x for x in sub if x[0][:4] == "2025"]
        y26 = [x for x in sub if x[0][:4] == "2026"]
        if not y25 or not y26:
            continue
        m5 = sum(v for _, _, v in y25) / len(y25)
        m6 = sum(v for _, _, v in y26) / len(y26)
        print(f"\n   CIT {lo}~{hi}°C   2025 평균 {m5:5.1f} (n={len(y25)})   "
              f"2026 평균 {m6:5.1f} (n={len(y26)})   차 {m6 - m5:+5.1f} mbar"
              f"   → 출력 {-VAC_COEF * (m6 - m5):+.2f} MW")
        for d, c, v in sorted(sub, key=lambda x: x[1]):
            print(f"       {d}  CIT {c:5.1f}  진공 {v:5.1f}")

    # ── ④ 정비 전/후 비교 (복수기 청소 효과) ─────────────────────────────
    if a.split:
        pre = [(d, c, v - (a0 + b0 * c)) for d, c, v, _ in rows if d < a.split]
        post = [(d, c, v - (a0 + b0 * c)) for d, c, v, _ in rows if d >= a.split]
        print(f"\n④ {a.split} 전/후 진공 잔차 (온도 기준선 대비)")
        if not post:
            print(f"   {a.split} 이후 회차가 없습니다 — 청소 후 시험이 쌓이면 다시 돌리세요.")
        else:
            for label, sub in (("이전", pre), ("이후", post)):
                if not sub:
                    continue
                n = len(sub)
                mu = sum(v for _, _, v in sub) / n
                sd = ((sum((v - mu) ** 2 for _, _, v in sub) / (n - 1)) ** 0.5
                      if n > 1 else float("nan"))
                print(f"   {label}  n={n:2d}  평균 잔차 {mu:+6.2f} mbar  sd {sd:5.2f}")
            mp = sum(v for _, _, v in pre) / len(pre) if pre else 0.0
            mq = sum(v for _, _, v in post) / len(post)
            print(f"   변화 {mq - mp:+.2f} mbar  →  출력 {-VAC_COEF * (mq - mp):+.2f} MW")
            print("   음(-)으로 내려가면 진공이 회복된 것이다. 그러면 청소 이전 데이터로")
            print("   이후를 예측하면 과소 예측(기회손실)이 되므로, 이후 회차를 쌓아")
            print("   곡선을 되올려야 한다. 반대라면 오염이 더 진행된 것이다.")


if __name__ == "__main__":
    main()
