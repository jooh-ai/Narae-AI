#!/usr/bin/env python3
"""회귀 모델 개념 설명용 예시 데이터 — 교과서 그림을 우리 손으로 그린다.

    python3 docs/ppt/build/gp_concept.py      →  gp_concept.json

왜 우리 실적을 쓰지 않는가
  부록 첫 판은 위례 시험 40회로 그렸다. 그런데 우리 데이터에서는 커널을
  바꿔도 곡선이 거의 같아서(최대 1.9 MW) **개념 차이가 그림에 드러나지
  않았다**. 회귀 모델을 처음 보는 사람에게 "RBF 는 매끄럽고 지수는 각지다"
  를 보여 주려면, 그 차이가 크게 벌어지는 예시가 있어야 한다.

  그래서 이 파일은 프로젝트와 무관한 **교과서 예시**를 만든다.
    참값  f(x) = sin(x) + 0.25 sin(3.1x)      0 ≤ x ≤ 10
    관측  13점 · 잡음 표준편차 0.14
    빈칸  x = 4.3 과 7.6 사이에 관측이 없다 — 데이터가 없는 구간에서
          예측 구간이 넓어지는 것을 보이려고 일부러 비웠다.

무엇을 뽑는가
  prior   관측 전 커널만으로 뽑은 곡선 5개 (가능한 곡선들의 분포)
  post    관측 뒤 곡선 5개 + 평균 + 95% 구간
  kern    같은 관측에 커널만 바꾼 평균·구간 — RBF / Matérn 5/2 / 지수
  nw      커널회귀(Nadaraya-Watson) 곡선 — GP 가 아니다. 구간이 없다.
  bin     구간평균 — 가장 단순한 방법. 빈 구간에는 답이 없다.
  ls      길이척도 효과 — 짧으면 출렁이고 길면 뭉갠다

numpy 가 없는 환경이라 순수 파이썬으로 짠다. 관측이 13점뿐이라
13×13 촐레스키면 충분하다.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

OUT = Path(__file__).resolve().parent / "gp_concept.json"

X0, X1 = 0.0, 10.0
GRID = [X0 + (X1 - X0) * i / 100.0 for i in range(101)]
#   점을 촘촘히 둔다 — 듬성하면 어떤 커널을 써도 곡선이 다 매끄러워서
#   "지수는 각진다" 가 그림에 나타나지 않는다. 0.5 간격이면 지수 커널이
#   점마다 꺾이는 것이 눈에 보인다.
OBS_X = [0.3, 0.8, 1.3, 1.8, 2.3, 2.8, 3.3, 3.8, 4.3, 7.6, 8.2, 8.8, 9.5]
NOISE = 0.14
SIGMA = 1.0
ELL = 1.2


def truth(x: float) -> float:
    return math.sin(x) + 0.25 * math.sin(3.1 * x)


# ── 난수 — 결과가 매번 같아야 한다(장표는 다시 그려도 같은 그림이어야 한다) ──
class Rng:
    def __init__(self, seed: int = 20260922):
        self.s = seed

    def unit(self) -> float:
        self.s = (1103515245 * self.s + 12345) % (1 << 31)
        return self.s / (1 << 31)

    def normal(self) -> float:
        u1 = max(self.unit(), 1e-12)
        u2 = self.unit()
        return math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)


# ── 커널 세 가지 ────────────────────────────────────────────────────────
def k_rbf(r: float, ell: float) -> float:
    """제곱지수(RBF) — 무한히 미분가능. 가장 매끄럽다."""
    return SIGMA ** 2 * math.exp(-(r * r) / (2 * ell * ell))


def k_mat52(r: float, ell: float) -> float:
    """Matérn 5/2 — 두 번 미분가능. 실무 기본값으로 자주 쓴다."""
    a = math.sqrt(5.0) * r / ell
    return SIGMA ** 2 * (1 + a + a * a / 3.0) * math.exp(-a)


def k_exp(r: float, ell: float) -> float:
    """지수(Matérn 1/2, Ornstein-Uhlenbeck) — 연속이지만 미분 불가. 각진다."""
    return SIGMA ** 2 * math.exp(-r / ell)


KERNELS = {"rbf": k_rbf, "mat52": k_mat52, "exp": k_exp}


def gram(xs, ys, kf, ell):
    return [[kf(abs(a - b), ell) for b in ys] for a in xs]


# ── 선형대수 (작은 행렬이라 순수 파이썬으로 충분하다) ────────────────────
def cholesky(A):
    n = len(A)
    L = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = sum(L[i][k] * L[j][k] for k in range(j))
            if i == j:
                L[i][j] = math.sqrt(max(A[i][i] - s, 1e-12))
            else:
                L[i][j] = (A[i][j] - s) / L[j][j]
    return L


def fwd(L, b):
    n = len(b)
    y = [0.0] * n
    for i in range(n):
        y[i] = (b[i] - sum(L[i][k] * y[k] for k in range(i))) / L[i][i]
    return y


def bwd(L, y):
    n = len(y)
    x = [0.0] * n
    for i in reversed(range(n)):
        x[i] = (y[i] - sum(L[k][i] * x[k] for k in range(i + 1, n))) / L[i][i]
    return x


def gp_posterior(ox, oy, kf, ell, grid, noise=NOISE):
    """평균과 표준편차. 교과서 식 그대로다.

        K  = k(X,X) + σ_n² I        L = chol(K)
        평균  = k(x*,X) K⁻¹ y
        분산  = k(x*,x*) − k(x*,X) K⁻¹ k(X,x*)
    """
    K = gram(ox, ox, kf, ell)
    for i in range(len(ox)):
        K[i][i] += noise ** 2
    L = cholesky(K)
    alpha = bwd(L, fwd(L, oy))
    mean, sd = [], []
    for x in grid:
        ks = [kf(abs(x - a), ell) for a in ox]
        mean.append(sum(ks[i] * alpha[i] for i in range(len(ox))))
        v = fwd(L, ks)
        var = kf(0.0, ell) - sum(t * t for t in v)
        sd.append(math.sqrt(max(var, 0.0)))
    return mean, sd


def gp_samples(mean, sd_grid, ox, oy, kf, ell, grid, n_draw, rng, noise=NOISE):
    """사후 표본 곡선 — 격자 위 공분산을 촐레스키로 쪼개 뽑는다."""
    m = len(grid)
    K = gram(ox, ox, kf, ell)
    for i in range(len(ox)):
        K[i][i] += noise ** 2
    L = cholesky(K)
    Ks = [[kf(abs(g - a), ell) for a in ox] for g in grid]
    V = [fwd(L, row) for row in Ks]
    cov = [[kf(abs(grid[i] - grid[j]), ell) - sum(V[i][t] * V[j][t]
            for t in range(len(ox))) for j in range(m)] for i in range(m)]
    for i in range(m):
        cov[i][i] += 1e-8
    Lg = cholesky(cov)
    out = []
    for _ in range(n_draw):
        z = [rng.normal() for _ in range(m)]
        out.append([mean[i] + sum(Lg[i][j] * z[j] for j in range(i + 1))
                    for i in range(m)])
    return out


def prior_samples(kf, ell, grid, n_draw, rng):
    cov = gram(grid, grid, kf, ell)
    for i in range(len(grid)):
        cov[i][i] += 1e-8
    L = cholesky(cov)
    out = []
    for _ in range(n_draw):
        z = [rng.normal() for _ in range(len(grid))]
        out.append([sum(L[i][j] * z[j] for j in range(i + 1))
                    for i in range(len(grid))])
    return out


def nadaraya_watson(ox, oy, grid, h):
    """커널회귀 — 가까운 점에 무게를 더 준 가중평균. 확률 모형이 아니다."""
    out = []
    for x in grid:
        w = [math.exp(-((x - a) ** 2) / (2 * h * h)) for a in ox]
        s = sum(w)
        out.append(sum(w[i] * oy[i] for i in range(len(ox))) / s if s > 1e-12
                   else float("nan"))
    return out


def bin_mean(ox, oy, grid, edges):
    """구간평균 — 가장 단순한 방법. 구간마다 그 안의 평균을 쓴다.

    점이 없는 구간은 답이 없다(None). 계단이 끊기는 것이 이 방법의 성질이라
    그대로 둔다 — 장표에서 그 자리가 비어 보여야 설명이 된다.
    """
    val = []
    for i in range(len(edges) - 1):
        ys = [oy[j] for j, x in enumerate(ox) if edges[i] <= x < edges[i + 1]]
        val.append(sum(ys) / len(ys) if ys else None)
    out = []
    for x in grid:
        k = None
        for i in range(len(edges) - 1):
            if edges[i] <= x < edges[i + 1]:
                k = i
                break
        out.append(None if k is None else val[k])
    return out


def r3(v):
    return [None if x is None else round(x, 4) for x in v]


def main() -> int:
    rng = Rng()
    obs_y = [truth(x) + NOISE * rng.normal() for x in OBS_X]

    data = {
        "note": "회귀 개념 설명용 예시. 프로젝트 데이터가 아니다.",
        "x": [round(v, 4) for v in GRID],
        "truth": r3([truth(v) for v in GRID]),
        "obs": [[round(OBS_X[i], 3), round(obs_y[i], 4)] for i in range(len(OBS_X))],
        "ell": ELL, "noise": NOISE,
    }

    data["prior"] = [r3(s) for s in prior_samples(k_rbf, ELL, GRID, 5, rng)]

    m, sd = gp_posterior(OBS_X, obs_y, k_rbf, ELL, GRID)
    data["post_mean"], data["post_sd"] = r3(m), r3(sd)
    data["post_draws"] = [r3(s) for s in
                          gp_samples(m, sd, OBS_X, obs_y, k_rbf, ELL, GRID, 5, rng)]

    data["kern"] = {}
    for name, kf in KERNELS.items():
        mm, ss = gp_posterior(OBS_X, obs_y, kf, ELL, GRID)
        data["kern"][name] = {"mean": r3(mm), "sd": r3(ss)}

    data["nw"] = r3(nadaraya_watson(OBS_X, obs_y, GRID, 0.8))
    data["bin_edges"] = [0.0, 2.5, 5.0, 7.5, 10.001]
    data["bin"] = r3(bin_mean(OBS_X, obs_y, GRID, data["bin_edges"]))

    data["ls"] = {}
    for tag, ell in (("short", 0.35), ("long", 3.0)):
        mm, ss = gp_posterior(OBS_X, obs_y, k_rbf, ell, GRID)
        data["ls"][tag] = {"ell": ell, "mean": r3(mm), "sd": r3(ss)}

    OUT.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print("출력 %s  (%.0f KB)" % (OUT.name, OUT.stat().st_size / 1024))
    print("관측 %d점 · 빈 구간 %.1f~%.1f" % (len(OBS_X), OBS_X[8], OBS_X[9]))
    for name in KERNELS:
        sd = data["kern"][name]["sd"]
        gap = max(sd[44:76])
        print("  %-6s 빈 구간 최대 표준편차 %.2f · 곡선 범위 %.2f ~ %.2f"
              % (name, gap, min(data["kern"][name]["mean"]),
                 max(data["kern"][name]["mean"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
