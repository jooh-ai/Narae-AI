#!/usr/bin/env python3
"""진공도가 보정값을 설명하는가 — 검정.

    python3 docs/ppt/build/vacuum_effect_check.py

배경
    2026-08 회차 4건에서 예측 오차가 커졌고, 원인 후보로 진공도(복수기압)가
    지목됐다. 10월 컨덴서 세척을 앞두고 있어 물리적으로도 그럴듯하다.

    그런데 이 프로젝트는 이미 같은 대상을 한 번 기각했다 (계획서 §6 가설 2)
    — '진공 잔차로 보정값을 예측할 수 있다', n=5 r=−0.85 → n=36 r=+0.09.
    그래서 이번에도 같은 함정인지 아닌지를 먼저 가린다.

무엇을 재는가 — 순서가 중요하다
    ① 원시 상관        보정값 vs 진공도. 여기서 강하게 보이는 것이 함정이다.
    ② 교란 확인        진공도 vs 온도. 계획서 §6 가설 4 는 r=+0.947 로 채택됐다.
                       즉 진공도는 사실상 온도의 함수다.
    ③ 온도 통제 후     '온도로 설명되지 않는 진공' vs '온도로 설명되지 않는 보정값'.
                       이게 진짜 질문이다 — 진공도가 우리 모델의 오차를 설명하는가.
    ④ 실익             진공 잔차로 모델 오차를 보정하면 MAE 가 실제로 줄어드는가.
    ⑤ 시기 분리        2025/2026 으로 나누면 관계가 강해지는가 (분리 검정 주장 확인).
    ⑥ 파울링 누적      진공 잔차가 시간에 따라 나빠지는가.

모델 오차는 LOOCV 로 낸다 — 한 건을 빼고 나머지로 학습해 그 건을 예측한다.
그래야 '이미 본 답'을 쓰지 않는다.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tool"))
from wirye_capacity import select                      # noqa: E402

SEED = ROOT / "tool" / "wirye_capacity" / "data" / "measurements_seed.json"
# 2026-08 4회차 — 화면 캡쳐값 (docs/ppt/build/trial_raw_2026-08.md) + 진공도 별도 수령
NEW = [
    {"date": "2026-08-04", "cit": 37.92, "cp_meas": 84.3, "corr": 1.48},
    {"date": "2026-08-12", "cit": 30.16, "cp_meas": 68.9, "corr": -0.65},
    {"date": "2026-08-18", "cit": 32.82, "cp_meas": 74.2, "corr": -1.47},
    {"date": "2026-08-26", "cit": 30.94, "cp_meas": 78.6, "corr": -3.21},
]
VAC_A, VAC_B = 33.64, 1.242          # 진공도 = A + B×CIT (계획서 §6 가설 4)


def r(x, y):
    n = len(x)
    if n < 3: return float("nan")
    mx, my = sum(x) / n, sum(y) / n
    sx = sum((a - mx) ** 2 for a in x) ** .5
    sy = sum((b - my) ** 2 for b in y) ** .5
    return float("nan") if sx * sy == 0 else sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)


def fit(x, y):
    """최소제곱 직선 y = a + b·x 와 R²."""
    n = len(x); mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    b = sum((a - mx) * (c - my) for a, c in zip(x, y)) / sxx if sxx else 0.0
    a = my - b * mx
    sst = sum((c - my) ** 2 for c in y)
    sse = sum((c - (a + b * v)) ** 2 for v, c in zip(x, y))
    return a, b, (1 - sse / sst if sst else float("nan"))


def main():
    recs = json.loads(SEED.read_text(encoding="utf-8"))
    full = [r_ for r_ in recs if r_.get("cp_meas") is not None]
    rows = sorted([{"date": r_["date"], "cit": r_["cit"], "vac": r_["cp_meas"], "corr": r_["corr"]}
                   for r_ in full] + [{"date": d["date"], "cit": d["cit"], "vac": d["cp_meas"],
                                       "corr": d["corr"]} for d in NEW],
                  key=lambda d: d["date"])
    for d in rows:
        d["vres"] = d["vac"] - (VAC_A + VAC_B * d["cit"])       # 온도로 설명 안 되는 진공

    print("검정 대상  %d건 (시드 %d + 2026-08 %d)   진공도 결측 %d건"
          % (len(rows), len(full), len(NEW), len(recs) - len(full)))

    # ── ① 원시 상관 / ② 교란 ──────────────────────────────────
    V = [d["vac"] for d in rows]; K = [d["corr"] for d in rows]; T = [d["cit"] for d in rows]
    print("\n① 원시 상관   보정값 vs 진공도        r = %+.3f   ← 강해 보인다" % r(V, K))
    print("② 교란 확인   진공도 vs 외기온도        r = %+.3f   ← 진공도는 사실상 온도의 함수다" % r(T, V))
    print("              보정값 vs 외기온도        r = %+.3f" % r(T, K))
    print("              두 변수가 같은 것(온도)을 따라가므로 ①은 그 그림자일 수 있다.")

    # ── ③ 온도를 통제한다 — 모델이 못 맞힌 부분을 진공이 설명하는가 ──
    err = []
    for i, d in enumerate(rows):
        tr = [{"cit": x["cit"], "corr": x["corr"]} for j, x in enumerate(rows) if j != i]
        p = select.predict("gp:rbf", tr, d["cit"])
        d["pred"] = p
        d["err"] = None if p is None else d["corr"] - p          # + 면 모델이 낮게 봤다
        if d["err"] is not None: err.append(d)
    E = [d["err"] for d in err]; R = [d["vres"] for d in err]
    print("\n③ 온도 통제   진공 잔차 vs 모델 오차   r = %+.3f   (n=%d, LOOCV)" % (r(R, E), len(err)))
    print("              ①의 %+.3f 이 여기서 %+.3f 로 무너지면, 관계는 온도가 만든 것이다."
          % (r(V, K), r(R, E)))

    # ── ④ 실익 — 진공으로 보정하면 오차가 줄어드는가 ──────────
    a, b, r2 = fit(R, E)
    mae0 = sum(abs(e) for e in E) / len(E)
    mae1 = sum(abs(e - (a + b * v)) for v, e in zip(R, E)) / len(E)
    print("\n④ 실익       모델 오차 ≈ %+.3f %+.4f × 진공잔차   설명력 R² = %+.3f" % (a, b, r2))
    print("              평균 오차  %.3f → %.3f MW   (%+.3f MW, %+.1f%%)"
          % (mae0, mae1, mae1 - mae0, (mae1 / mae0 - 1) * 100))

    # ── ⑤ 시기를 나누면 강해지는가 ────────────────────────────
    print("\n⑤ 시기 분리")
    print("   %-14s %4s  %-22s %-22s" % ("", "n", "보정값 vs 진공도", "진공잔차 vs 모델오차"))
    groups = [("전체", rows), ("2025년", [d for d in rows if d["date"] < "2026"]),
              ("2026년", [d for d in rows if d["date"] >= "2026"]),
              ("2026-08 4회차", [d for d in rows if d["date"] >= "2026-08"]),
              ("30~33℃ 만", [d for d in rows if 30 <= d["cit"] < 33])]
    for tag, sel in groups:
        se = [d for d in sel if d.get("err") is not None]
        print("   %-14s %4d  %+22.3f %+22.3f"
              % (tag, len(sel), r([d["vac"] for d in sel], [d["corr"] for d in sel]),
                 r([d["vres"] for d in se], [d["err"] for d in se]) if len(se) >= 3 else float("nan")))

    # ── ⑥ 파울링 누적 ─────────────────────────────────────────
    print("\n⑥ 파울링 누적   진공 잔차가 시간에 따라 나빠지는가")
    for tag, sel in (("2025년", [d for d in rows if d["date"] < "2026"]),
                     ("2026년", [d for d in rows if d["date"] >= "2026"])):
        res = [d["vres"] for d in sel]
        print("   %-8s n=%-3d 시간 vs 진공잔차 r = %+.3f   처음3건 %+.2f → 마지막3건 %+.2f"
              % (tag, len(sel), r(list(range(len(sel))), res), sum(res[:3]) / 3, sum(res[-3:]) / 3))
    print("   작년 같은 온도대와 대조 (파울링이면 올해가 높아야 한다)")
    for c25, c26 in ((32.80, 32.82), (30.20, 30.16), (30.70, 30.94)):
        a25 = next((d for d in rows if d["date"] < "2026" and abs(d["cit"] - c25) < .06), None)
        a26 = next((d for d in rows if d["date"] >= "2026-08" and abs(d["cit"] - c26) < .06), None)
        if a25 and a26:
            print("     %5.2f℃ %s %5.1f  →  %5.2f℃ %s %5.1f   (%+.1f)"
                  % (a25["cit"], a25["date"], a25["vac"], a26["cit"], a26["date"], a26["vac"],
                     a26["vac"] - a25["vac"]))

    # ── 마지막 회차의 교란 ────────────────────────────────────
    last = rows[-1]
    print("\n⑦ 08-26 한 건에 세 가지가 겹쳐 있다 — n=1 이라 가릴 수 없다")
    print("   진공 잔차 %+.2f (최대급) · 습도 67.5%% (최고) · 보정값 %+.2f (최저)"
          % (last["vres"], last["corr"]))

    print("\n" + "─" * 74)
    print("판정   ①의 %+.3f 은 온도가 만든 그림자다. 온도를 통제하면 %+.3f 로 남고,"
          % (r(V, K), r(R, E)))
    print("       진공으로 보정해도 평균 오차는 %.3f → %.3f MW 로 %s."
          % (mae0, mae1, "거의 그대로다" if abs(mae1 - mae0) < 0.05 else "달라진다"))
    print("       계획서 §6 가설 2(n=5 r=−0.85 → n=36 r=+0.09)와 같은 형태다.")
    print("\n반박하려면 — 아래 중 하나를 보이면 이 판정은 뒤집힌다")
    print("  · ③ 진공잔차 vs 모델오차 r 이 |0.5| 이상으로 나오는 다른 정의")
    print("  · ④ 진공 보정으로 LOOCV MAE 가 0.1 MW 이상 줄어드는 구성")
    print("  · ⑥ 같은 온도대에서 올해 진공도가 작년보다 계통적으로 높다는 증거")
    print("  · 10월 세척 전/후 같은 온도대 비교 — 이게 가장 결정적이다")


if __name__ == "__main__":
    main()
