"""회귀 비교용 공용 구현(Scaler/Ridge/Lasso/Poly2) — 검증 스크립트가 import 해서 사용 — 실측 32건 LOOCV 동일조건 비교.

sklearn 없는 환경이므로 StandardScaler / Ridge / Lasso(좌표하강) / Poly2 / Extended
특성을 표준 라이브러리로 직접 구현(수식은 sklearn 정의와 동일).
  Ridge : ||y-Xw||^2 + a||w||^2      → (X'X + aI)w = X'y
  Lasso : (1/2n)||y-Xw||^2 + a||w||1 → 좌표하강 + soft-threshold
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wirye_capacity.correction import aggregate_bins, applied_correction
from wirye_capacity.curve import CorrectionCurve
from wirye_capacity.theory import TheoryEngine, igv_turnup

SEED = json.loads((Path(__file__).resolve().parent / "wirye_capacity" / "data"
                   / "measurements_seed.json").read_text(encoding="utf-8"))
ENG = TheoryEngine()

# ── 상대 코드의 X: 온도, 대기압, RH, 복수기압실측, 복수기압설계 (5개)
XNAMES = ["온도", "대기압", "RH", "복수기압실측", "복수기압설계"]
X_ALL = [[r["cit"], r["press"], r["rh"], r["cp_meas"], r["cp_design"]] for r in SEED]
Y_ALL = [r["cc_meas"] for r in SEED]                      # 상대 타깃: CC실측 직접
N = len(SEED)


# ───────────────────────── 선형대수 (표준 라이브러리) ─────────────────────────
def solve(A, b):
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(M[r][i]))
        M[i], M[p] = M[p], M[i]
        if abs(M[i][i]) < 1e-12:
            M[i][i] = 1e-12
        d = M[i][i]
        for j in range(i, n + 1):
            M[i][j] /= d
        for r in range(n):
            if r != i and M[r][i]:
                f = M[r][i]
                for j in range(i, n + 1):
                    M[r][j] -= f * M[i][j]
    return [M[i][n] for i in range(n)]


class Scaler:
    def fit(self, X):
        n, p = len(X), len(X[0])
        self.mu = [sum(r[j] for r in X) / n for j in range(p)]
        self.sd = []
        for j in range(p):
            v = sum((r[j] - self.mu[j]) ** 2 for r in X) / n
            self.sd.append(math.sqrt(v) if v > 1e-18 else 1.0)
        return self

    def tr(self, X):
        return [[(r[j] - self.mu[j]) / self.sd[j] for j in range(len(self.mu))] for r in X]


def ridge_fit(X, y, alpha):
    n, p = len(X), len(X[0])
    ym = sum(y) / n
    yc = [v - ym for v in y]
    A = [[sum(X[i][a] * X[i][b] for i in range(n)) + (alpha if a == b else 0.0)
          for b in range(p)] for a in range(p)]
    rhs = [sum(X[i][a] * yc[i] for i in range(n)) for a in range(p)]
    w = solve(A, rhs) if p else []
    return ym, w


def lasso_fit(X, y, alpha, iters=300):
    n, p = len(X), len(X[0])
    b0 = sum(y) / n
    w = [0.0] * p
    xx = [sum(X[i][j] ** 2 for i in range(n)) for j in range(p)]
    pred = [b0] * n
    for _ in range(iters):
        big = 0.0
        for j in range(p):
            if xx[j] < 1e-12:
                continue
            rho = sum(X[i][j] * (y[i] - pred[i] + w[j] * X[i][j]) for i in range(n))
            t = alpha * n
            nw = (rho - t) / xx[j] if rho > t else ((rho + t) / xx[j] if rho < -t else 0.0)
            if nw != w[j]:
                d = nw - w[j]
                for i in range(n):
                    pred[i] += d * X[i][j]
                big = max(big, abs(d))
                w[j] = nw
        b0m = sum(y[i] - (pred[i] - b0) for i in range(n)) / n
        if abs(b0m - b0) > 1e-12:
            for i in range(n):
                pred[i] += b0m - b0
            b0 = b0m
        if big < 1e-9:
            break
    return b0, w


def predict(b0, w, x):
    return b0 + sum(wi * xi for wi, xi in zip(w, x))


# ───────────────────────── 특성 생성 ─────────────────────────
def f_linear(X):
    return [r[:] for r in X]


def f_poly2(X):
    out = []
    for r in X:
        p = len(r)
        row = list(r) + [r[j] ** 2 for j in range(p)]
        row += [r[a] * r[b] for a in range(p) for b in range(a + 1, p)]
        out.append(row)
    return out


class Extended:
    """상대 코드 ExtendedNonlinearFeatures 재현(원+제곱+교차+로그+지수+역수)."""

    def fit(self, X):
        n, p = len(X), len(X[0])
        self.mn = [min(r[j] for r in X) for j in range(p)]
        self.mu = [sum(r[j] for r in X) / n for j in range(p)]
        self.sd = []
        for j in range(p):
            v = sum((r[j] - self.mu[j]) ** 2 for r in X) / n
            self.sd.append(math.sqrt(v) if v > 1e-18 else 1.0)
        return self

    def tr(self, X):
        out = []
        for r in X:
            p = len(r)
            row = list(r) + [r[j] ** 2 for j in range(p)]
            row += [r[a] * r[b] for a in range(p) for b in range(a + 1, p)]
            sh = [max(r[j] - self.mn[j] + 1.0, 1e-8) for j in range(p)]
            row += [math.log(s) for s in sh]
            row += [math.exp(max(-5.0, min(5.0, (r[j] - self.mu[j]) / self.sd[j])))
                    for j in range(p)]
            row += [1.0 / s for s in sh]
            out.append(row)
        return out


# ───────────────────────── 우리 방식 (이론값 + 보정) ─────────────────────────
def ours_predict(train_idx, i, *, mode="bin", bw=3.5):
    """31건으로 보정테이블/곡선 학습 → i건의 CC실측 예측.
    예측 = 이론기준값(실측 대기압·RH) + W(운전실적) + 보정값(CIT)"""
    recs = [{"cit": SEED[k]["cit"], "corr": SEED[k]["corr"]} for k in train_idx]
    r = SEED[i]
    th = ENG.theory_cc(r["cit"], r["press"], rh=r["rh"])
    if mode == "bin":
        corr = applied_correction(r["cit"], aggregate_bins(recs))
    else:
        corr = CorrectionCurve(recs, method="kernel", bandwidth=bw)(r["cit"])
    return th + r["w"] + corr


# ───────────────────────── 평가 ─────────────────────────
def metrics(yt, yp):
    n = len(yt)
    mae = sum(abs(a - b) for a, b in zip(yt, yp)) / n
    rmse = math.sqrt(sum((a - b) ** 2 for a, b in zip(yt, yp)) / n)
    ym = sum(yt) / n
    sst = sum((v - ym) ** 2 for v in yt)
    sse = sum((a - b) ** 2 for a, b in zip(yt, yp))
    return mae, rmse, (1 - sse / sst if sst else 0.0), max(abs(a - b) for a, b in zip(yt, yp))


def loocv_reg(feat, fitter, alpha, cols=None):
    """상대 방식 LOOCV — fold마다 특성·스케일러·모델을 train 에서만 학습."""
    yt, yp = [], []
    for i in range(N):
        tr = [k for k in range(N) if k != i]
        Xtr = [[X_ALL[k][j] for j in (cols or range(len(XNAMES)))] for k in tr]
        Xte = [[X_ALL[i][j] for j in (cols or range(len(XNAMES)))]]
        if isinstance(feat, Extended):
            f = Extended().fit(Xtr)
            Ftr, Fte = f.tr(Xtr), f.tr(Xte)
        else:
            Ftr, Fte = feat(Xtr), feat(Xte)
        sc = Scaler().fit(Ftr)
        Str, Ste = sc.tr(Ftr), sc.tr(Fte)
        b0, w = fitter(Str, [Y_ALL[k] for k in tr], alpha)
        yt.append(Y_ALL[i])
        yp.append(predict(b0, w, Ste[0]))
    return metrics(yt, yp), yp


def loocv_ours(mode, bw=3.5):
    yt, yp = [], []
    for i in range(N):
        tr = [k for k in range(N) if k != i]
        yt.append(Y_ALL[i])
        yp.append(ours_predict(tr, i, mode=mode, bw=bw))
    return metrics(yt, yp), yp


RIDGE_A = [0.0001, 0.001, 0.01, 0.1, 1, 10, 100, 1000]
LASSO_A = [0.00001, 0.0001, 0.001, 0.01, 0.1, 1, 10, 100]

print("=" * 78)
print("실측 32건 · LOOCV(31건 학습 → 1건 예측) · 타깃 = CC실측(MW)")
print("=" * 78)
print(f"{'모델':38} {'MAE':>7} {'RMSE':>7} {'R²':>8} {'최대오차':>8}")
print("-" * 78)

results = {}


def run(name, m):
    (mae, rmse, r2, mx), _ = m
    results[name] = (mae, rmse, r2, mx)
    print(f"{name:38} {mae:7.3f} {rmse:7.3f} {r2:8.4f} {mx:8.3f}")


# ── 상대 코드 방식
run("[상대] Linear (X5)", loocv_reg(f_linear, lambda X, y, a: ridge_fit(X, y, 0.0), 0))
best = min(RIDGE_A, key=lambda a: loocv_reg(f_linear, ridge_fit, a)[0][1])
run(f"[상대] Ridge best(a={best})", loocv_reg(f_linear, ridge_fit, best))
bestl = min(LASSO_A, key=lambda a: loocv_reg(f_linear, lasso_fit, a)[0][1])
run(f"[상대] Lasso best(a={bestl})", loocv_reg(f_linear, lasso_fit, bestl))
run("[상대] Poly2+Linear", loocv_reg(f_poly2, lambda X, y, a: ridge_fit(X, y, 0.0), 0))
bp = min(RIDGE_A, key=lambda a: loocv_reg(f_poly2, ridge_fit, a)[0][1])
run(f"[상대] Poly2+Ridge best(a={bp})", loocv_reg(f_poly2, ridge_fit, bp))
be = min(RIDGE_A, key=lambda a: loocv_reg(Extended(), ridge_fit, a)[0][1])
run(f"[상대] Extended+Ridge best(a={be})", loocv_reg(Extended(), ridge_fit, be))
bel = min(LASSO_A, key=lambda a: loocv_reg(Extended(), lasso_fit, a)[0][1])
run(f"[상대] Extended+Lasso best(a={bel})", loocv_reg(Extended(), lasso_fit, bel))
# 온도만 단순회귀(참고)
run("[상대] Linear (온도만)", loocv_reg(f_linear, lambda X, y, a: ridge_fit(X, y, 0.0), 0,
                                    cols=[0]))
print("-" * 78)
# ── 우리 방식
run("[우리] 이론값 + 구간평균 보정", loocv_ours("bin"))
run("[우리] 이론값 + 커널회귀 보정", loocv_ours("kernel"))
print("=" * 78)

# ── 보정값(잔차)만 따로 — 우리 모델의 실제 학습 대상
print("\n[참고] 우리 이론값의 설명력 — 보정값(잔차) 크기")
corr = [r["corr"] for r in SEED]
cm = sum(corr) / N
print(f"  이론값만(보정 0) MAE = {sum(abs(c) for c in corr) / N:.3f} MW"
      f" / 잔차 표준편차 = {math.sqrt(sum((c - cm) ** 2 for c in corr) / N):.3f} MW")
print(f"  CC실측 범위 {min(Y_ALL):.1f}~{max(Y_ALL):.1f} MW (변동폭 {max(Y_ALL) - min(Y_ALL):.1f})")

# ── 모델선택 편향 시연 (nested LOOCV)
print("\n[검증의 함정] 여러 모델 중 LOOCV 최고를 고르면 그 점수는 낙관적으로 편향")
cands = ([("Linear", f_linear, ridge_fit, 0.0)]
         + [(f"Ridge{a}", f_linear, ridge_fit, a) for a in RIDGE_A]
         + [(f"Poly2Ridge{a}", f_poly2, ridge_fit, a) for a in RIDGE_A]
         + [(f"ExtRidge{a}", Extended(), ridge_fit, a) for a in RIDGE_A])
inner_cache = {nm: loocv_reg(ft, fr, a)[0][1] for nm, ft, fr, a in cands}
win = min(inner_cache, key=inner_cache.get)
print(f"  후보 {len(cands)}개 중 LOOCV RMSE 최고: {win} → {inner_cache[win]:.3f} MW (보고되는 값)")

outer_yt, outer_yp = [], []
for i in range(N):
    tr = [k for k in range(N) if k != i]
    scores = {}
    for nm, ft, fr, a in cands:                      # 내부 LOOCV (train 31건 안에서만)
        ys, ps = [], []
        for j in tr:
            tr2 = [k for k in tr if k != j]
            Xtr = [X_ALL[k] for k in tr2]
            Xte = [X_ALL[j]]
            if isinstance(ft, Extended):
                f = Extended().fit(Xtr)
                Ftr, Fte = f.tr(Xtr), f.tr(Xte)
            else:
                Ftr, Fte = ft(Xtr), ft(Xte)
            sc = Scaler().fit(Ftr)
            b0, w = fr(sc.tr(Ftr), [Y_ALL[k] for k in tr2], a)
            ys.append(Y_ALL[j])
            ps.append(predict(b0, w, sc.tr(Fte)[0]))
        scores[nm] = metrics(ys, ps)[1]
    pick = min(scores, key=scores.get)
    nm, ft, fr, a = next(c for c in cands if c[0] == pick)
    Xtr = [X_ALL[k] for k in tr]
    Xte = [X_ALL[i]]
    if isinstance(ft, Extended):
        f = Extended().fit(Xtr)
        Ftr, Fte = f.tr(Xtr), f.tr(Xte)
    else:
        Ftr, Fte = ft(Xtr), ft(Xte)
    sc = Scaler().fit(Ftr)
    b0, w = fr(sc.tr(Ftr), [Y_ALL[k] for k in tr], a)
    outer_yt.append(Y_ALL[i])
    outer_yp.append(predict(b0, w, sc.tr(Fte)[0]))
nm_, nr_, n2_, nx_ = metrics(outer_yt, outer_yp)
print(f"  같은 '모델선택 절차'를 nested LOOCV 로 정직하게 평가 → RMSE {nr_:.3f} MW"
      f" (편향 +{nr_ - inner_cache[win]:.3f})")

# ── 외삽: 입찰은 −20~40°C 전 구간 필요, 실측은 −1.9~36.1°C
print("\n[외삽] 입찰 Profile 은 −20~40°C 전 구간 필요 / 실측 범위는 "
      f"{min(r['cit'] for r in SEED):.1f}~{max(r['cit'] for r in SEED):.1f}°C")
Xf = f_linear(X_ALL)
sc = Scaler().fit(Xf)
b0, w = ridge_fit(sc.tr(Xf), Y_ALL, 0.0)
for t in (-20, -10, 40):
    x = [[t, 1013.0, 60.0, 48.0, 45.0]]
    reg = predict(b0, w, sc.tr(x)[0])
    ours = ENG.theory_cc_with_igv(t, 1013.0) + applied_correction(
        t, aggregate_bins([{"cit": r["cit"], "corr": r["corr"]} for r in SEED]))
    print(f"  {t:>4}°C : 상대회귀 {reg:7.1f} MW | 우리(이론+보정) {ours:7.1f} MW"
          f" | 차이 {reg - ours:+7.1f}")
