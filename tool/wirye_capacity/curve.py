"""연속 보정곡선 — 구간(bin) 평균을 매끄러운 곡선으로 대체.

32개 실측점에 곡선을 입혀 어떤 온도든 고유한 보정값을 산출한다. 구간 경계의 계단 점프와
단건 구간 불안정을 해소하며, 데이터가 쌓일수록 자동으로 1도 해상도에 수렴한다.

방법:
  kernel (기본) — 국소가중 평활(가우시안). 폭(bandwidth) 안의 점을 거리가중 평균. 모양 가정 없음.
  poly          — 전역 다항 회귀(2~3차). 식 하나로 표현, 평탄+하강 모양엔 덜 맞을 수 있음.

안전장치:
  · 외삽 금지 — 실측 범위 [tmin, tmax] 밖은 끝값으로 클램프.
  · 특수구간 유지 — Shaft Limit(−20~−14)=0, 보수적 고정(−14~0)=+8.78 은 구간정책 그대로.
    (곡선은 실측이 있는 'avg' 구간에만 적용)
"""
from __future__ import annotations

import math

from .correction import aggregate_bins, bin_for


def _kernel(temps, corrs, t, bandwidth):
    num = den = 0.0
    for ti, ci in zip(temps, corrs):
        w = math.exp(-0.5 * ((ti - t) / bandwidth) ** 2)
        num += w * ci
        den += w
    return num / den if den else 0.0


def _polyfit(xs, ys, degree):
    """최소제곱 다항 적합 (정규방정식 + 가우스 소거, 표준 라이브러리)."""
    n = degree + 1
    moments = [0.0] * (2 * degree + 1)
    rhs = [0.0] * n
    for x, y in zip(xs, ys):
        p = 1.0
        for k in range(2 * degree + 1):
            moments[k] += p
            if k < n:
                rhs[k] += y * p
            p *= x
    mat = [[moments[i + j] for j in range(n)] + [rhs[i]] for i in range(n)]
    for i in range(n):
        piv = max(range(i, n), key=lambda r: abs(mat[r][i]))
        mat[i], mat[piv] = mat[piv], mat[i]
        d = mat[i][i]
        if abs(d) < 1e-12:
            continue
        for j in range(i, n + 1):
            mat[i][j] /= d
        for r in range(n):
            if r != i:
                f = mat[r][i]
                for j in range(i, n + 1):
                    mat[r][j] -= f * mat[i][j]
    return [mat[i][n] for i in range(n)]


def _polyeval(coef, x):
    return sum(c * x ** k for k, c in enumerate(coef))


class CorrectionCurve:
    """온도→보정값 연속 보정기. pipeline/profile 의 corrector 로 주입해 사용.

    records: [{'cit': float, 'corr': float}, ...]
    """

    def __init__(self, records, *, method: str = "kernel", bandwidth: float = 3.5,
                 degree: int = 2):
        self.method = method
        self.bandwidth = bandwidth
        self.degree = degree
        pts = sorted((r["cit"], r["corr"]) for r in records)
        self.temps = [p[0] for p in pts]
        self.corrs = [p[1] for p in pts]
        self.tmin = self.temps[0] if self.temps else 0.0
        self.tmax = self.temps[-1] if self.temps else 0.0
        # 특수구간(shaft/fixed) 정책값 보존
        self._bins = aggregate_bins([{"cit": t, "corr": c} for t, c in pts])
        self._coef = (_polyfit(self.temps, self.corrs, degree)
                      if method == "poly" and len(pts) > degree else None)

    def _smooth(self, t: float) -> float:
        if not self.temps:
            return 0.0
        tc = min(max(t, self.tmin), self.tmax)   # 외삽 금지
        if self.method == "poly" and self._coef is not None:
            return _polyeval(self._coef, tc)
        return _kernel(self.temps, self.corrs, tc, self.bandwidth)

    def __call__(self, cit: float) -> float:
        b = bin_for(cit)
        if b is None:
            return 0.0
        lo, hi, kind = b
        if kind == "shaft_limit":
            return 0.0
        if kind == "fixed":                      # −14~0°C 보수적 고정(+8.78)
            applied = self._bins.get((lo, hi), {}).get("applied")
            return applied if applied is not None else self._smooth(cit)
        return self._smooth(cit)                 # avg 구간 → 연속 곡선

    def r_squared(self) -> float:
        """적합도(avg 구간 점 기준). 진단·신뢰도 표시용."""
        if len(self.corrs) < 2:
            return 0.0
        mean = sum(self.corrs) / len(self.corrs)
        ss_tot = sum((c - mean) ** 2 for c in self.corrs)
        ss_res = sum((c - self._smooth(t)) ** 2 for t, c in zip(self.temps, self.corrs))
        return 1 - ss_res / ss_tot if ss_tot else 0.0
