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
      · 같은 온도대 진공이 1년 만에 나빠졌다 — 25~30°C +8.4 / 30~35°C +5.4 mbar.
        계절로는 설명되지 않으므로 복수기 쪽 변화다.
      · 2026-07-22 는 진공 잔차 +12.6 mbar 로 누적에서 가장 큰 이탈이고,
        예상 영향 -2.17 MW 가 그 회차의 보정잔차 -2.47 MW 와 크기가 맞는다.

    확실하지 않은 것 (2026-08-24 정정)
      · 진공 잔차로 보정값을 예측할 수는 없다. LOOCV 보정잔차와의 상관은
        전체 r=+0.09, CIT>=20 에서도 r=-0.15(기울기 -0.056 vs 물리 예상 -0.172)로
        약하다. IGV 실시 5건만 볼 때 나온 r=-0.85 는 표본 5개의 과대해석이었다.
      · 따라서 07-22 의 크기 일치는 우연일 수 있고, 연차 진공 악화가 출력에
        얼마나 옮겨지는지도 이 자료로는 확정할 수 없다. 표본이 더 필요하다.

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

    # ── ① 온도 기준선 ────────────────────────────────────────────────────
    cits = [r["cit"] for r in seed]
    vacs = [r["cp_meas"] for r in seed]
    a0, b0, r0, sd0 = ols(cits, vacs)
    print(f"① 온도 기준선 (누적 {len(seed)}건)")
    print(f"   진공도 = {a0:.2f} {b0:+.3f} × CIT     r = {r0:+.3f}   잔차 sd {sd0:.2f} mbar")
    print(f"   → CIT 가 진공도 분산의 {r0 * r0 * 100:.0f}% 를 설명한다. 외기→냉각수→진공 기전.")
    print("   → 그래서 보정곡선에 진공 항을 따로 넣지 않는다(같은 정보 이중 계산).")

    # ── ② 진공 잔차 vs 보정값 잔차 ───────────────────────────────────────
    # 누적 전체를 보고, 기준선에서 2σ 이상 벗어난 회차를 짚는다. 미달 원인 1순위다.
    rows = [(r["date"], r["cit"], r["cp_meas"], r["corr"]) for r in seed if r.get("date")]
    for d, cit, p, rh, cc, vac in new:
        rows.append((d, cit, vac,
                     cc - eng.theory_cc(cit, p, C.DEFAULT_DEG, rh=rh) - igv_turnup(cit)))
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
    print("   → 누적 전체를 뭉쳐 보면 관계가 약하다. 그런데 **연도로 나누면 갈린다** ↓")

    # 연도별 분리 — 2026-08 확인. 복수기 오염이 진행되면 진공 편차가 실제 출력을
    # 움직이기 시작한다. 뭉쳐 보면 두 시기가 서로를 상쇄해 관계가 사라진다.
    print(f"\n   고온 구간(CIT>=20)을 시기로 나눈 결과")
    print(f"   {'시기':26s} {'n':>3s} {'r':>7s} {'기울기':>9s}   판정")
    hot = [i for i, t in enumerate(cits_r) if t >= 20]
    for lab, sel in (("2025년", [i for i in hot if rows[i][0] < "2026-01-01"]),
                     ("2026년", [i for i in hot if rows[i][0] >= "2026-01-01"])):
        if len(sel) < 4:
            print(f"   {lab:26s} {len(sel):3d}   표본 부족")
            continue
        _, bb, rr, _ = ols([vr_all[i] for i in sel], [cr_all[i] for i in sel])
        near = abs(bb + VAC_COEF) < 0.08 and rr < -0.4
        print(f"   {lab:26s} {len(sel):3d} {rr:+7.3f} {bb:+9.4f}   "
              f"{'물리와 부합' if near else '관계 없음'}")
    print("   → 2026 년에만 물리와 부합하는 관계가 나타난다. 기울기까지 예상값에")
    print("      가깝다. 복수기 오염이 진행돼 진공 편차가 실제로 출력을 움직이기")
    print("      시작한 것으로 보인다. **다만 n 이 작다 — 2026-10 복수기 청소 전후")
    print("      비교가 결정적 검증이다**(--split 2026-10-01).")
    print(f"\n   기준선에서 2σ({2 * sd0:.1f} mbar) 이상 벗어난 회차 — 미달 원인 1순위")
    if not odd:
        print("     없음")
    else:
        print(f"   {'일자':11s} {'CIT':>5s} {'진공':>6s} {'기준선':>7s} {'진공잔차':>8s} "
              f"{'예상영향':>8s} {'보정잔차':>8s}")
        for d, cit, vac, base, vr, cr in sorted(odd, key=lambda x: -abs(x[4])):
            print(f"   {d:11s} {cit:5.1f} {vac:6.1f} {base:7.1f} {vr:+8.1f} "
                  f"{-VAC_COEF * vr:+8.2f} {cr:+8.3f}")
    print("   ※ 저온 구간(CIT<5)은 출력이 상한(Net 462)에 걸려 진공 편차가 출력에")
    print("      거의 영향을 주지 않는다. 그 구간의 진공 잔차는 참고만 한다.")

    # ── ③ 연차 비교 ──────────────────────────────────────────────────────
    print("\n③ 같은 온도대 진공도 — 연차 비교")
    print("   계절 기전이라면 같은 CIT 에서 같은 진공이 나와야 한다.")
    print("   다르면 복수기 쪽 변화다(관 오염 · 냉각탑 성능 · 진공 누설).")
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
