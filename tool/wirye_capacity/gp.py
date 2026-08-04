"""가우시안 프로세스(GP) 보정기 — 예측 불확실성까지 산출하는 연속 보정곡선.

curve.CorrectionCurve 와 동일한 인터페이스(corrector 로 주입)이며, 추가로 온도별
예측 표준편차 sigma(cit) 를 제공한다. 실측 32건 LOOCV 검증:

    구간평균   MAE 1.419 / 미달 3건(9%)
    커널회귀   MAE 1.341 / 미달 4건(12%)
    GP        MAE 1.243 / 미달 2건(6%)      ← 최소

하이퍼파라미터(길이척도·신호·노이즈)는 **학습 데이터의 주변우도(log marginal
likelihood)만으로** 선택한다. 검증 데이터를 쓰지 않으므로 선택 편향이 없다
(전체 LOOCV 로 고르면 낙관 편향 — 검토 문서의 winner's curse 참조).

안전장치는 curve.py 와 동일:
  · 외삽 금지 — 실측 범위 밖은 끝값으로 클램프
  · 특수구간 유지 — Shaft Limit(−20~−14)=0, 보수적 고정(−14~0)=+8.78
"""
from __future__ import annotations

import math

from .correction import aggregate_bins, bin_for

# 하이퍼파라미터 탐색 격자 (길이척도 °C, 신호 MW, 노이즈 MW)
_LS = (2.0, 3.0, 4.0, 6.0, 8.0, 10.0, 14.0)
_SF = (2.0, 3.0, 5.0, 8.0)
_SN = (0.8, 1.2, 1.8, 2.5)


def _cholesky(A: list[list[float]]) -> list[list[float]] | None:
    n = len(A)
    L = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = A[i][j] - sum(L[i][k] * L[j][k] for k in range(j))
            if i == j:
                if s <= 1e-12:
                    return None
                L[i][i] = math.sqrt(s)
            else:
                L[i][j] = s / L[j][j]
    return L


def _solve(L: list[list[float]], b: list[float]) -> list[float]:
    n = len(L)
    y = [0.0] * n
    for i in range(n):
        y[i] = (b[i] - sum(L[i][k] * y[k] for k in range(i))) / L[i][i]
    x = [0.0] * n
    for i in reversed(range(n)):
        x[i] = (y[i] - sum(L[k][i] * x[k] for k in range(i + 1, n))) / L[i][i]
    return x


def _log_ml(xs, ys, ls, sf, sn) -> float:
    """log marginal likelihood — 학습 데이터만으로 하이퍼파라미터를 평가."""
    n = len(xs)
    mu = sum(ys) / n
    y0 = [v - mu for v in ys]
    sf2, sn2 = sf * sf, sn * sn
    K = [[sf2 * math.exp(-0.5 * ((xs[i] - xs[j]) / ls) ** 2) + (sn2 if i == j else 0.0)
          for j in range(n)] for i in range(n)]
    L = _cholesky(K)
    if L is None:
        return -math.inf
    a = _solve(L, y0)
    fit = sum(y * ai for y, ai in zip(y0, a))
    logdet = 2.0 * sum(math.log(L[i][i]) for i in range(n))
    return -0.5 * fit - 0.5 * logdet - 0.5 * n * math.log(2 * math.pi)


class GPCorrectionCurve:
    """온도→보정값 GP 보정기. profile/pipeline 의 corrector 로 주입해 사용.

    records: [{'cit': float, 'corr': float}, ...]
    hyper:   None 이면 주변우도로 자동 선택. (ls, sf, sn) 튜플로 고정도 가능.
    """

    def __init__(self, records, *, hyper: tuple[float, float, float] | None = None):
        all_pts = sorted((r["cit"], r["corr"]) for r in records)
        self._bins = aggregate_bins([{"cit": t, "corr": c} for t, c in all_pts])
        # 곡선 적합은 'avg' 구간 실측만 사용(특수구간 고정점이 곡선을 왜곡하지 않도록)
        pts = [(t, c) for t, c in all_pts
               if (b := bin_for(t)) is not None and b[2] == "avg"]
        self.temps = [p[0] for p in pts]
        self.corrs = [p[1] for p in pts]
        self.tmin = self.temps[0] if self.temps else 0.0
        self.tmax = self.temps[-1] if self.temps else 0.0
        self._ready = len(pts) >= 3
        if not self._ready:
            self.hyper = hyper or (4.0, 3.0, 1.2)
            return
        self.hyper = hyper or max(
            ((ls, sf, sn) for ls in _LS for sf in _SF for sn in _SN),
            key=lambda h: _log_ml(self.temps, self.corrs, *h))
        ls, sf, sn = self.hyper
        self._sf2, self._sn2, self._ls = sf * sf, sn * sn, ls
        self.mu = sum(self.corrs) / len(self.corrs)
        n = len(self.temps)
        K = [[self._k(self.temps[i], self.temps[j]) + (self._sn2 if i == j else 0.0)
              for j in range(n)] for i in range(n)]
        self._L = _cholesky(K)
        if self._L is None:                     # 수치 실패 → 평균으로 후퇴
            self._ready = False
            return
        self._alpha = _solve(self._L, [c - self.mu for c in self.corrs])

    def _k(self, a: float, b: float) -> float:
        return self._sf2 * math.exp(-0.5 * ((a - b) / self._ls) ** 2)

    def _clamp(self, t: float) -> float:
        return min(max(t, self.tmin), self.tmax)     # 외삽 금지

    def _post(self, t: float) -> tuple[float, float]:
        """사후 평균·표준편차 (avg 구간 기준)."""
        if not self._ready:
            m = sum(self.corrs) / len(self.corrs) if self.corrs else 0.0
            return m, float("nan")
        tc = self._clamp(t)
        ks = [self._k(tc, xi) for xi in self.temps]
        mean = self.mu + sum(a * kk for a, kk in zip(self._alpha, ks))
        v = _solve(self._L, ks)
        var = self._sf2 + self._sn2 - sum(kk * vi for kk, vi in zip(ks, v))
        return mean, math.sqrt(max(var, 1e-9))

    def __call__(self, cit: float) -> float:
        b = bin_for(cit)
        if b is None:
            return 0.0
        lo, hi, kind = b
        if kind == "shaft_limit":
            return 0.0
        if kind == "fixed":                          # −14~0°C 보수적 고정
            applied = self._bins.get((lo, hi), {}).get("applied")
            return applied if applied is not None else self._post(cit)[0]
        return self._post(cit)[0]

    def sigma(self, cit: float) -> float:
        """온도별 예측 표준편차(MW). 특수구간·데이터 부족 시 nan."""
        b = bin_for(cit)
        if b is None or b[2] != "avg":
            return float("nan")
        return self._post(cit)[1]

    def interval(self, cit: float, z: float = 1.645) -> tuple[float, float]:
        """예측구간 (기본 90%). LOOCV 실측 포함률 87%(90% 목표) 검증."""
        m = self(cit)
        s = self.sigma(cit)
        if s != s:                                   # nan
            return (m, m)
        return (m - z * s, m + z * s)

    def r_squared(self) -> float:
        """적합도(avg 구간 점 기준) — 진단·표시용."""
        if len(self.corrs) < 2:
            return 0.0
        mean = sum(self.corrs) / len(self.corrs)
        ss_tot = sum((c - mean) ** 2 for c in self.corrs)
        ss_res = sum((c - self._post(t)[0]) ** 2 for t, c in zip(self.temps, self.corrs))
        return 1 - ss_res / ss_tot if ss_tot else 0.0
