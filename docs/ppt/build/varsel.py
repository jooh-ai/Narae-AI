#!/usr/bin/env python3
"""입력 변수 선정 — **같은 모델**에서 **변수 조합만** 바꿔 겨룬다.

장표 6장이 쓰는 계산이다. 묻는 것은 하나다:

    외기온도 외에 환경변수를 더 넣으면 보정값 예측이 실제로 좋아지는가?

도구의 gp.GPCorrectionCurve 는 입력이 온도 하나(1차원)뿐이라 이 질문에 답할 수
없다. 그래서 여기에 **입력이 여러 개인 같은 커널의 GP** 를 둔다. 도구 코드를
고치지 않는다 — 도구는 온도 하나로 운영하는 것이 결론이기 때문이다.

## 비교가 공정하려면 (이 모듈의 존재 이유)

1. **모델을 같게 한다** — GP · RBF(제곱지수) 커널. 커널·격자·적합 절차가 모두
   같고 바뀌는 것은 입력 변수 조합 하나다.
2. **단위를 같게 한다** — 온도(°C)·진공도(mmHg)·대기압(hPa)·습도(%)는 눈금이
   다르다. 각 변수를 **온도의 산포와 같은 크기**로 환산해 넣는다
   (c_k = s_cit / s_k). 그래서 길이척도 격자를 커널 간·차원 간 그대로 쓴다.
   d=1 이면 c=1 이므로 **도구의 GP 와 완전히 같은 모델**이 된다.
3. **변수마다 길이척도를 따로 준다**(ARD). 이것이 중요하다 — 쓸모없는 변수는
   길이척도를 크게 잡아 모델이 **스스로 무시할 수 있다.** 그런데도 성적이
   나아지지 않는다면 '그 변수에 정보가 없다' 는 결론이 강해진다.
   ("변수를 억지로 섞어서 나빠진 것 아니냐" 는 반론을 미리 막는다.)
   실측 결과 추가 변수의 길이척도는 **모두 격자 상한 14.0** 에 붙었다 — 모델이
   실제로 무시하는 쪽을 골랐다는 뜻이다. 6장 결론 카드 3번이 이 관찰이다.
4. **채점집합을 같게 한다** — 장표의 다른 채점과 같은 회차 집합(공통 39회)에서
   select.score 로 잰다. 그래서 '외기온도 단독' 행은 8장 표의 GP·RBF 값과
   **같은 숫자**여야 한다 (RMSE 1.678 / MAE 1.301 / R² 0.854). 어긋나면 버그다.
5. **한 건씩 가리고 맞힌다**(LOOCV) — 하이퍼파라미터도 **매 회차마다 학습분으로
   다시** 고른다(주변우도). 빼 둔 회차를 보고 고르는 일이 없다.

## AIC

    AIC = 2k − 2·lnL      k = 하이퍼파라미터 수 = (변수 수 d) + 2
                          lnL = 전체 적합의 log marginal likelihood

값이 낮을수록 좋다. 변수를 늘리면 lnL(적합도)은 오르기 쉬우므로 2k 로 벌점을
준다 — 적합도와 복잡도를 함께 보는 지표다. lnL 은 곡선을 실제로 학습하는
구간(평균 구간 38회차)에서 재며, 모든 행이 같은 집합이라 나란히 놓을 수 있다.

RMSE/MAE/R² 는 **밖에서 잰 성적**(LOOCV)이고 AIC 는 **안에서 잰 성적**이다.
서로 독립인 두 관점이 같은 결론을 가리키면 그 결론은 단단하다.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[3] / "tool"
if str(TOOL) not in sys.path:
    sys.path.insert(0, str(TOOL))

from wirye_capacity import select                                   # noqa: E402
from wirye_capacity.correction import aggregate_bins, bin_for       # noqa: E402
from wirye_capacity.gp import _LS, _SF, _SN, _cholesky, _solve      # noqa: E402

# 후보 변수 — 보정값에 영향을 줄 수 있는 환경변수. IGV(w) 는 넣지 않는다
# (보정값 = 실측 − 이론 − W 로 이미 빼고 있는 값이라 환경변수와 나란히 둘 수 없다).
LABEL = {"cit": "외기 온도", "cp_meas": "복수기 진공도",
         "press": "대기압", "rh": "상대습도"}
EXTRA = ("cp_meas", "press", "rh")
COMBOS: list[tuple[str, tuple[str, ...]]] = (
    [("외기 온도", ("cit",))]
    + [(f"외기 온도 + {LABEL[k]}", ("cit", k)) for k in EXTRA]
    + [("전체 변수", ("cit",) + EXTRA)]
)
# ARD 좌표상승 반복 횟수. 2 회로 정한 근거 — 40건에서 실측:
#   1 회: 전체 변수 lnL −80.744    2 회: −80.518    4 회: −80.518 (더 안 오른다)
# 나머지 조합은 1 회에서 이미 수렴한다. 2 회면 충분하고 4 회는 시간만 두 배다.
_SWEEPS = 2


def _std(v: list[float]) -> float:
    n = len(v)
    m = sum(v) / n
    return max(math.sqrt(sum((x - m) ** 2 for x in v) / n), 1e-12)


class MultiGP:
    """입력이 여러 개인 GP·RBF 보정기. 도구의 GPCorrectionCurve 와 같은 규칙.

    · 곡선은 'avg' 구간 실측만으로 적합한다(특수구간 고정점이 곡선을 왜곡하지
      않도록) — gp.py 와 동일.
    · Shaft Limit(−20~−14) = 0, 보수적 고정(−14~0) = 구간 적용값 — gp.py 와 동일.
    · 온도 범위 밖은 끝값으로 클램프(외삽 금지) — gp.py 와 동일.
    · 호출은 record 하나를 받는다: f(rec) → 보정값(MW).
    """

    def __init__(self, records: list[dict], keys: tuple[str, ...]):
        if keys[0] != "cit":
            raise ValueError("첫 변수는 온도('cit')여야 합니다 — 구간 규칙이 온도 기준입니다")
        self.keys = keys
        self.d = len(keys)
        pts = [r for r in records
               if (b := bin_for(r["cit"])) is not None and b[2] == "avg"]
        self._bins = aggregate_bins(records)
        self.temps = [r["cit"] for r in pts]
        self.tmin = min(self.temps) if self.temps else 0.0
        self.tmax = max(self.temps) if self.temps else 0.0
        self._ready = len(pts) >= 3
        if not self._ready:
            return
        # ② 단위 통일 — 각 변수를 온도의 산포와 같은 크기로 환산한다
        s_cit = _std([r["cit"] for r in pts])
        self._c = [s_cit / _std([r[k] for r in pts]) for k in keys]
        self._X = [[r[k] * c for k, c in zip(keys, self._c)] for r in pts]
        ys = [r["corr"] for r in pts]
        self.mu = sum(ys) / len(ys)
        self._y0 = [y - self.mu for y in ys]
        n = len(pts)
        # 하이퍼파라미터와 무관한 차원별 제곱차를 미리 접어 둔다
        self._D = [[[(self._X[i][k] - self._X[j][k]) ** 2 for k in range(self.d)]
                    for j in range(n)] for i in range(n)]
        self.hyper, self.log_ml = self._fit()
        self._ls, self._sf2, self._sn2 = self.hyper[0], self.hyper[1] ** 2, self.hyper[2] ** 2
        K = self._gram(self._ls, self._sf2, self._sn2)
        self._L = _cholesky(K)
        if self._L is None:
            self._ready = False
            return
        self._alpha = _solve(self._L, self._y0)

    # ── 적합 ────────────────────────────────────────────────────────────
    def _gram(self, ls, sf2, sn2):
        n = len(self._X)
        inv = [1.0 / (l * l) for l in ls]
        out = []
        for i in range(n):
            row = []
            Di = self._D[i]
            for j in range(n):
                dij = Di[j]
                u = 0.0
                for k in range(self.d):
                    u += dij[k] * inv[k]
                row.append(sf2 * math.exp(-0.5 * u) + (sn2 if i == j else 0.0))
            out.append(row)
        return out

    def _lml(self, ls, sf, sn) -> float:
        K = self._gram(ls, sf * sf, sn * sn)
        L = _cholesky(K)
        if L is None:
            return -math.inf
        a = _solve(L, self._y0)
        fit = sum(y * ai for y, ai in zip(self._y0, a))
        logdet = 2.0 * sum(math.log(L[i][i]) for i in range(len(L)))
        return -0.5 * fit - 0.5 * logdet - 0.5 * len(L) * math.log(2 * math.pi)

    def _fit(self):
        """주변우도 최대화. 1차원이면 도구와 같은 전수 격자, 다차원이면
        등방(모든 길이척도 동일) 최적점에서 출발해 변수별로 좌표상승한다."""
        cand = [(([l] * self.d), sf, sn) for l in _LS for sf in _SF for sn in _SN]
        ls, sf, sn = max(cand, key=lambda h: self._lml(h[0], h[1], h[2]))
        ls = list(ls)
        best = self._lml(ls, sf, sn)
        if self.d > 1:
            for _ in range(_SWEEPS):
                for k in range(self.d):
                    keep = ls[k]
                    for cand_l in _LS:
                        ls[k] = cand_l
                        v = self._lml(ls, sf, sn)
                        if v > best:
                            best, keep = v, cand_l
                    ls[k] = keep
                for s2 in _SF:
                    for n2 in _SN:
                        v = self._lml(ls, s2, n2)
                        if v > best:
                            best, sf, sn = v, s2, n2
        return (tuple(ls), sf, sn), best

    @property
    def k_params(self) -> int:
        """하이퍼파라미터 수 = 변수별 길이척도 d개 + 신호 + 노이즈."""
        return self.d + 2

    @property
    def aic(self) -> float:
        return 2.0 * self.k_params - 2.0 * self.log_ml

    # ── 예측 ────────────────────────────────────────────────────────────
    def _post(self, rec: dict) -> float:
        t = min(max(rec["cit"], self.tmin), self.tmax)          # 외삽 금지
        x = [(t if k == "cit" else rec[k]) * c for k, c in zip(self.keys, self._c)]
        inv = [1.0 / (l * l) for l in self._ls]
        ks = []
        for xi in self._X:
            u = 0.0
            for k in range(self.d):
                dv = x[k] - xi[k]
                u += dv * dv * inv[k]
            ks.append(self._sf2 * math.exp(-0.5 * u))
        return self.mu + sum(a * kk for a, kk in zip(self._alpha, ks))

    def __call__(self, rec: dict) -> float | None:
        b = bin_for(rec["cit"])
        if b is None:
            return None
        lo, hi, kind = b
        if kind == "shaft_limit":
            return 0.0
        if kind == "fixed":
            ap = self._bins.get((lo, hi), {}).get("applied")
            if ap is not None:
                return ap
        if not self._ready:
            return None
        return self._post(rec)


def compare(recs: list[dict], sel: list[int]) -> dict:
    """변수 조합별 성적. sel = 채점에 쓸 회차 번호(장표 공통 39회).

    반환 rows 는 RMSE 오름차순(좋은 것부터)이며 `pick` 이 선정 결과다.
    """
    rows = []
    idx: list[int] = []
    for label, keys in COMBOS:
        pred = []
        for i in range(len(recs)):
            train = recs[:i] + recs[i + 1:]
            try:
                pred.append(MultiGP(train, keys)(recs[i]))
            except Exception:                                   # noqa: BLE001
                pred.append(None)
        if not idx:
            idx = [i for i in sel if pred[i] is not None]
        sc = select.score([recs[i]["corr"] for i in idx],
                          [pred[i] for i in idx], ":".join(keys))
        full = MultiGP(recs, keys)
        rows.append({"label": label, "keys": list(keys), "d": len(keys),
                     "n": sc.n, "rmse": round(sc.rmse, 3), "mae": round(sc.mae, 3),
                     "r2": round(sc.r2, 4), "aic": round(full.aic, 2),
                     "k": full.k_params, "log_ml": round(full.log_ml, 2),
                     "ls": [round(x, 1) for x in full.hyper[0]],
                     "_ae": [abs(recs[i]["corr"] - pred[i]) for i in idx]})

    # ── 짝지어 비교 — 표의 소수점 차이가 '실제 차이' 인지 '잡음' 인지 가른다.
    #    같은 회차를 두 모델이 각각 맞히므로 회차별 차이를 짝지어 재는 것이 맞다.
    #    |오차|의 회차별 차이 평균 = MAE 차이, 그 표준오차로 구분 가능성을 본다.
    base = next(r for r in rows if r["d"] == 1)
    for r in rows:
        if r is base:
            r["vs_base"] = None
            continue
        dif = [a - b for a, b in zip(r["_ae"], base["_ae"])]    # + 면 추가변수가 더 나쁘다
        n = len(dif)
        m = sum(dif) / n
        sd = (sum((x - m) ** 2 for x in dif) / (n - 1)) ** 0.5
        se = sd / n ** 0.5
        r["vs_base"] = {"d_mae": round(m, 3), "se": round(se, 3),
                        "t": round(m / se, 2) if se else None,
                        "sig": bool(se and abs(m / se) >= 2.024)}   # α=0.05, df≈38

    rows.sort(key=lambda r: r["rmse"])
    for r in rows:
        r.pop("_ae")
    near = min((r for r in rows if r["d"] > 1), key=lambda r: r["mae"])
    return {"rows": rows, "pick": base["label"], "pick_keys": base["keys"],
            "n_fit": len([r for r in recs
                          if (b := bin_for(r["cit"])) is not None and b[2] == "avg"]),
            "base": {k: base[k] for k in ("label", "rmse", "mae", "r2", "aic", "n")},
            "near": {k: near[k] for k in ("label", "rmse", "mae", "r2", "aic")}
                    | {"vs_base": near["vs_base"]},
            "any_sig": any(r["d"] > 1 and r["vs_base"]["sig"] and r["vs_base"]["d_mae"] < 0
                           for r in rows),
            "best_rmse_is_base": rows[0]["d"] == 1,
            "best_mae_is_base": min(rows, key=lambda r: r["mae"])["d"] == 1,
            "best_aic_is_base": min(rows, key=lambda r: r["aic"])["d"] == 1}
