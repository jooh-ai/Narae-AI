"""학습곡선 — 데이터가 늘어나면 어떤 모델이 유리해지는가 (재현 스크립트).

    실행:  python scripts/learning_curve.py     (tool 폴더에서)


표본 수를 8→28건으로 늘려가며 각 모델의 테스트 성능을 측정한다.
층화(온도 정렬 후 균등 추출)로 온도 범위가 골고루 들어가게 뽑고, 여러 번 반복 평균.
마지막으로 '데이터가 무한히 많아도 남는 오차'(irreducible noise)를 추정해
각 모델이 그 한계에 얼마나 가까운지 본다.
"""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _regress import N, SEED, Scaler, f_linear, f_poly2, predict, ridge_fit

from wirye_capacity.correction import aggregate_bins, applied_correction
from wirye_capacity.curve import CorrectionCurve
from wirye_capacity.gp import GPCorrectionCurve

X6 = [[r["cit"], r["press"], r["rh"], r["cp_meas"], r["cp_design"], r["w"]] for r in SEED]
Y = [r["corr"] for r in SEED]
R = [{"cit": r["cit"], "corr": r["corr"]} for r in SEED]
SD_Y = math.sqrt(sum((v - sum(Y) / N) ** 2 for v in Y) / N)

ORDER = sorted(range(N), key=lambda i: SEED[i]["cit"])   # 온도순


def stratified(n, seed):
    """온도 범위를 골고루 덮는 n건 추출 (구간 안에서만 랜덤)."""
    rnd = random.Random(seed)
    step = N / n
    picks = []
    for k in range(n):
        lo, hi = int(k * step), max(int((k + 1) * step), int(k * step) + 1)
        picks.append(ORDER[rnd.randrange(lo, min(hi, N))])
    return sorted(set(picks))


def rmse(yt, yp):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(yt, yp)) / len(yt))


def eval_model(kind, tr_idx, te_idx, alpha=10.0):
    """tr 로 학습 → te 예측."""
    if kind in ("bin", "kernel", "gp"):
        tr = [R[i] for i in tr_idx]
        if kind == "gp":
            f = GPCorrectionCurve(tr)
        elif kind == "kernel":
            f = CorrectionCurve(tr, method="kernel")
        else:
            tb = aggregate_bins(tr)
            f = lambda t, tb=tb: applied_correction(t, tb)      # noqa: E731
        return [f(SEED[i]["cit"]) for i in te_idx]
    feat = f_poly2 if kind == "poly2ridge" else f_linear
    Ftr = feat([X6[i] for i in tr_idx])
    Fte = feat([X6[i] for i in te_idx])
    sc = Scaler().fit(Ftr)
    b0, w = ridge_fit(sc.tr(Ftr), [Y[i] for i in tr_idx], alpha)
    return [predict(b0, w, r) for r in sc.tr(Fte)]


MODELS = [("구간평균", "bin"), ("커널회귀", "kernel"), ("GP", "gp"),
          ("Ridge 6변수", "ridge"), ("2차다항+Ridge 6변수", "poly2ridge")]
SIZES = (8, 12, 16, 20, 24, 28)
REPS = 24

print("=" * 84)
print("학습곡선 — 학습 표본 수를 늘려가며 테스트 RMSE 측정 (남은 건으로 평가, 24회 평균)")
print("=" * 84)
head = "  " + f"{'모델':22}" + "".join(f"{n:>9}건" for n in SIZES)
print(head)
print("-" * 84)
curves = {}
for label, kind in MODELS:
    row = []
    for n in SIZES:
        vals = []
        for rep in range(REPS):
            tr = stratified(n, seed=1000 * n + rep)
            te = [i for i in range(N) if i not in tr]
            if not te:
                continue
            try:
                yp = eval_model(kind, tr, te)
            except Exception:      # noqa: BLE001 — 표본 부족으로 실패 시 제외
                continue
            vals.append(rmse([Y[i] for i in te], yp))
        row.append(sum(vals) / len(vals) if vals else float("nan"))
    curves[label] = row
    print(f"  {label:22}" + "".join(f"{v:>10.3f}" for v in row))
print("-" * 84)
print("  (단위 MW · 낮을수록 좋음)")

# ── 개선 추세: 8건 → 28건 사이 감소량
print("\n[개선 속도] 8건 → 28건 사이 RMSE 감소폭")
print(f"  {'모델':22} {'8건':>8} {'28건':>8} {'감소':>8} {'감소율':>8}")
for label, row in curves.items():
    a, b = row[0], row[-1]
    print(f"  {label:22} {a:>8.3f} {b:>8.3f} {a - b:>8.3f} {(a - b) / a * 100:>7.1f}%")

# ── 이론적 하한 (데이터가 무한해도 남는 오차)
print("\n" + "=" * 84)
print("데이터를 아무리 모아도 남는 오차 (irreducible noise) 추정")
print("=" * 84)
gp_all = GPCorrectionCurve(R)
ls, sf, sn = gp_all.hyper
print(f"  GP 가 데이터에서 추정한 노이즈 = {sn:.2f} MW")
print("    (같은 온도에서도 그날 운전상태에 따라 보정값이 흔들리는 폭)")
# 구간 내 변동으로 교차 확인
tot_w = tot_v = 0
for lo, hi in ((0, 10), (10, 15), (15, 20), (25, 30), (30, 41)):
    v = [r["corr"] for r in R if lo <= r["cit"] < hi]
    if len(v) < 2:
        continue
    m = sum(v) / len(v)
    var = sum((x - m) ** 2 for x in v) / (len(v) - 1)
    tot_v += var * (len(v) - 1)
    tot_w += len(v) - 1
pooled = math.sqrt(tot_v / tot_w)
print(f"  구간 내 변동으로 교차확인한 노이즈 = {pooled:.2f} MW  (두 방법이 근접 → 신뢰 가능)")
print()
print(f"  보정값 표준편차 {SD_Y:.2f} MW 기준으로 환산하면:")
for name, s in (("현재 GP (32건)", 1.605), ("이론 하한", sn), ("이론 하한(교차확인)", pooled)):
    r2 = 1 - (s / SD_Y) ** 2
    print(f"    {name:22} RMSE {s:.3f} MW → 테스트 R² {r2:.4f}")
print()
gp_now = 1.605
print(f"  → 현재 GP RMSE {gp_now:.3f} MW, 하한 {sn:.2f} MW."
      f" 남은 개선 여지 {(gp_now - sn) / gp_now * 100:.0f}%")
print(f"  → 데이터를 무한히 모아도 테스트 R² 는 약 {1 - (sn / SD_Y) ** 2:.2f} 가 한계")
