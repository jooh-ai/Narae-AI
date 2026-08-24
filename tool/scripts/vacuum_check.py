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
    ① 온도 기준선 — 진공도가 CIT 로 얼마나 설명되는가
    ② 진공 잔차 — 같은 온도인데 진공이 기준선보다 나쁜 회차. 이건 계절이 아니라
       그날의 설비 상태다. 출력 저하로 직결되므로 미달 원인 1순위다.
           Δ출력 ≈ -0.1721 × 진공잔차   (기존 회귀, r = 0.983)
    ③ 연차 비교 — 같은 온도대에서 진공이 해마다 나빠지는가. 계절 기전이라면
       같은 CIT 에서 같은 진공이 나와야 한다. 다르면 복수기 쪽 변화다
       (관 오염 · 냉각탑 성능 · 진공 누설).

2026-08 확인 사항
    · 2026-07-22 의 미달(-2.14 MW)은 진공 잔차 +14.2 mbar 로 설명된다.
      예상 영향 -2.44 MW 와 거의 일치한다.
    · 같은 온도대 진공이 1년 만에 나빠졌다 — 25~30°C +8.4 / 30~35°C +5.4 mbar.
      여름 구간(30~41°C)은 누적 10건이 전부 2025년이므로, 2025 여름 데이터로
      2026 여름을 예측하면 과대 예측이 될 수 있다. 계속 감시할 항목이다.

대응은 진공 항 추가가 아니라 안전마진이다. 진공 잔차는 입찰 전날 알 수 없다.

실행:
    python scripts/vacuum_check.py
    python scripts/vacuum_check.py --add 2026-07-22,28.7,997.5,58.1,395.3,81.9
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

# 시운전에서 확인한 IGV 실시 회차 (2026). --add 로 더 넣을 수 있다.
NEW_2026 = [
    ("2026-04-15", 25.7, 1000.7, 32.4, 411.5, 61.6),
    ("2026-05-27", 25.4, 993.4, 74.1, 407.5, 69.3),
    ("2026-07-07", 32.4, 994.9, 68.5, 384.2, 79.1),
    ("2026-07-22", 28.7, 997.5, 58.1, 395.3, 81.9),
    ("2026-07-29", 31.7, 999.8, 62.8, 389.1, 80.4),
]


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
    a = ap.parse_args()

    new = list(NEW_2026)
    for spec in a.add:
        f = spec.split(",")
        if len(f) != 6:
            raise SystemExit(f"--add 형식은 날짜,CIT,대기압,RH,CC,진공 입니다: {spec}")
        new.append((f[0].strip(), *(float(v) for v in f[1:])))

    seed = json.loads(_SEED.read_text(encoding="utf-8"))
    eng = TheoryEngine()
    gp = GPCorrectionCurve([{"cit": r["cit"], "corr": r["corr"]} for r in seed])

    # ── ① 온도 기준선 ────────────────────────────────────────────────────
    cits = [r["cit"] for r in seed]
    vacs = [r["cp_meas"] for r in seed]
    a0, b0, r0, sd0 = ols(cits, vacs)
    print(f"① 온도 기준선 (누적 {len(seed)}건)")
    print(f"   진공도 = {a0:.2f} {b0:+.3f} × CIT     r = {r0:+.3f}   잔차 sd {sd0:.2f} mbar")
    print(f"   → CIT 가 진공도 분산의 {r0 * r0 * 100:.0f}% 를 설명한다. 외기→냉각수→진공 기전.")
    print("   → 그래서 보정곡선에 진공 항을 따로 넣지 않는다(같은 정보 이중 계산).")

    # ── ② 진공 잔차 vs 보정값 잔차 ───────────────────────────────────────
    print(f"\n② 회차별 진공 잔차와 보정값 잔차")
    print(f"   {'일자':11s} {'CIT':>5s} {'진공':>6s} {'기준선':>7s} {'진공잔차':>8s} "
          f"{'예상영향':>8s} {'보정잔차':>8s}")
    vr_all, cr_all = [], []
    for d, cit, p, rh, cc, vac in new:
        base = a0 + b0 * cit
        vr = vac - base
        corr = cc - eng.theory_cc(cit, p, C.DEFAULT_DEG, rh=rh) - igv_turnup(cit)
        cr = corr - gp._post(cit)[0]
        vr_all.append(vr)
        cr_all.append(cr)
        flag = "  ⚠" if abs(vr) > 2 * sd0 else ""
        print(f"   {d:11s} {cit:5.1f} {vac:6.1f} {base:7.1f} {vr:+8.1f} "
              f"{-VAC_COEF * vr:+8.2f} {cr:+8.3f}{flag}")
    if len(vr_all) > 2:
        _, _, rr, _ = ols(vr_all, cr_all)
        print(f"\n   r(진공잔차, 보정잔차) = {rr:+.3f}  (n={len(vr_all)})")
        print(f"   음의 상관이면 물리와 맞다 — 진공이 나쁠수록 출력이 낮다.")
    print(f"   ⚠ 표시 = 기준선에서 2σ({2 * sd0:.1f} mbar) 이상 벗어난 회차. 미달 원인 1순위다.")

    # ── ③ 연차 비교 ──────────────────────────────────────────────────────
    print("\n③ 같은 온도대 진공도 — 연차 비교")
    print("   계절 기전이라면 같은 CIT 에서 같은 진공이 나와야 한다.")
    print("   다르면 복수기 쪽 변화다(관 오염 · 냉각탑 성능 · 진공 누설).")
    for lo, hi in ((20, 25), (25, 30), (30, 35), (35, 41)):
        old = [(r["date"], r["cit"], r["cp_meas"]) for r in seed if lo <= r["cit"] < hi]
        add = [(d, cit, vac) for d, cit, _p, _rh, _cc, vac in new if lo <= cit < hi]
        if not old or not add:
            continue
        mo = sum(v for _, _, v in old) / len(old)
        mn = sum(v for _, _, v in add) / len(add)
        print(f"\n   CIT {lo}~{hi}°C   누적 평균 {mo:5.1f} (n={len(old)})   "
              f"신규 평균 {mn:5.1f} (n={len(add)})   차 {mn - mo:+5.1f} mbar"
              f"   → 출력 {-VAC_COEF * (mn - mo):+.2f} MW")
        for d, c, v in sorted(old + add, key=lambda x: x[1]):
            tag = "  ← 신규" if any(d == x[0] for x in add) else ""
            print(f"       {d}  CIT {c:5.1f}  진공 {v:5.1f}{tag}")


if __name__ == "__main__":
    main()
