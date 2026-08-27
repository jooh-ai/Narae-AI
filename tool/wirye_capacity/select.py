"""모델 선정 — 테스트셋 분리 → 학습셋 LOOCV → 최종 모델 → 테스트셋 검증.

절차 (순서를 지키는 것이 이 모듈의 존재 이유다)
    1. 누적 전체에서 테스트셋을 먼저 떼어낸다. 시드를 고정하므로 같은 설정이면
       같은 분할이 나온다 — 결정을 나중에 재현할 수 있어야 한다.
    2. 학습셋만으로 LOOCV 를 돌려 후보를 채점하고 기준(RMSE/MAE/R²)으로 고른다.
       테스트셋은 이 단계에서 전혀 쓰이지 않는다. 그래서 3의 성적이 정직하다.
    3. 고른 모델을 학습셋 전체로 다시 적합해 테스트셋을 예측한다. 이것이
       '한 번도 안 본 데이터' 성적이다.

층화 추출 — 왜 온도구간으로 나눠 뽑는가
    보정값은 온도의 함수다. 완전 랜덤으로 뽑으면 특정 온도대가 통째로 테스트셋에
    가서 학습셋에 그 구간 데이터가 0건이 될 수 있다. 누적 36건에서 20~25°C 는
    실측이 1건뿐이라, 완전 랜덤이면 20% 확률로 그 구간이 비어 비교 자체가
    성립하지 않는다.

    그래서 층화 계층은 C.BINS 를 그대로 쓰지 않고 **15~25°C 를 한 계층으로 합친다**
    (2026-08-25 부장님 지시). 15~20°C 3건 + 20~25°C 1건 = 4건이 되어 최소 1건은
    학습셋에 남는다.

    ⚠ 이 병합은 **추출 계층에만** 적용된다. 실제 보정 테이블(C.BINS)은 건드리지
      않는다. 병합해서 구간평균을 내면 15~20°C(+5.552)와 20~25°C(+2.619)의 실제
      기울기가 평균으로 뭉개져 LOOCV 가 나빠지고(MAE 1.335 → 1.452), 20~25°C
      입찰값이 2.2 MW 높아진다 — 미달 방향이다. 표본 확보와 보정값 산출은
      목적이 다르므로 계층만 합친다.

R² 를 기준으로 쓸 때
    R² = 1 − SSE/SST 이고 SST(=실측 분산)는 **같은 평가집합 안에서** 모든 후보에
    동일하므로, R² 순위는 RMSE 순위와 항상 같다. MAE 만 다른 순서가 나올 수 있다.
    (부장님 확인: 알고 있음. 세 기준 모두 제공한다.)

    단서가 붙는다 — '같은 평가집합' 이어야 한다. 후보마다 예측 가능한 회차가
    다르면 n 과 SST 가 달라져 순위가 갈린다. 그래서 loocv() 는 모든 후보가
    예측할 수 있는 회차만 골라 전원 같은 집합에서 채점한다.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from . import constants as C
from .correction import aggregate_bins
from .curve import CorrectionCurve
from .gp import KERNEL_LABEL, KERNELS, GPCorrectionCurve

# 층화 계층 — C.BINS 에서 15~20 과 20~25 를 15~25 로 합친 것. 추출에만 쓴다.
STRATA = [(-20, -14), (-14, 0), (0, 10), (10, 15), (15, 25), (25, 30), (30, 41)]

CRITERIA = ("rmse", "mae", "r2")
CRITERION_LABEL = {"rmse": "RMSE", "mae": "MAE", "r2": "R²"}

# 후보 방법 — 'bin'/'curve' + GP 커널별. 화면 콤보와 같은 키를 쓴다.
METHOD_LABEL: dict[str, str] = {"bin": "구간평균", "curve": "커널회귀"}
METHOD_LABEL.update({f"gp:{k}": f"GP · {KERNEL_LABEL[k]}" for k in KERNELS})
METHODS = tuple(METHOD_LABEL)


def stratum_of(cit: float) -> tuple[int, int] | None:
    for lo, hi in STRATA:
        if lo <= cit < hi:
            return (lo, hi)
    return None


def make_corrector(method: str, records: list[dict]):
    """방법 키 → corrector. 'bin' 은 구간 테이블을 쓰므로 None 을 돌려준다."""
    if method == "bin":
        return None
    if method == "curve":
        return CorrectionCurve(records)
    if method.startswith("gp:"):
        return GPCorrectionCurve(records, kernel=method.split(":", 1)[1])
    raise ValueError(f"알 수 없는 방법 '{method}' — 가능: {', '.join(METHODS)}")


def predict(method: str, train: list[dict], cit: float) -> float | None:
    """train 만으로 적합해 cit 의 보정값을 예측. 예측 불가면 None."""
    if not train:
        return None
    if method == "bin":
        b = next((b for b in C.BINS if b[0] <= cit < b[1]), None)
        if b is None:
            return None
        agg = aggregate_bins(train).get((b[0], b[1]))
        return None if agg is None else agg.get("applied")
    try:
        return make_corrector(method, train)(cit)
    except Exception:                      # noqa: BLE001 — 적합 실패는 '예측 불가'
        return None


@dataclass
class Score:
    method: str
    n: int
    mae: float
    rmse: float
    r2: float
    me: float                     # 편차(bias) — + 면 실측이 예측보다 높다(안전)
    over: int                     # 예측이 실측보다 높은 건수 = 미달 위험
    skipped: int = 0              # 평가에서 제외된 건수(후보 공통 — loocv 주석 참조)

    def value(self, criterion: str) -> float:
        """작을수록 좋은 값으로 정규화 — 선정에 쓴다(R² 는 부호를 뒤집는다)."""
        return {"rmse": self.rmse, "mae": self.mae, "r2": -self.r2}[criterion]


def score(actual: list[float], pred: list[float], method: str,
          skipped: int = 0) -> Score:
    n = len(actual)
    err = [a - p for a, p in zip(actual, pred)]
    mu = sum(actual) / n
    sst = sum((a - mu) ** 2 for a in actual)
    sse = sum(e * e for e in err)
    return Score(method=method, n=n,
                 mae=sum(abs(e) for e in err) / n,
                 rmse=(sse / n) ** 0.5,
                 r2=(float("nan") if sst == 0 else 1 - sse / sst),
                 me=sum(err) / n,
                 over=sum(1 for e in err if e < 0),
                 skipped=skipped)


def split(records: list[dict], test_frac: float, seed: int,
          stratified: bool = True) -> tuple[list[dict], list[dict], list[str]]:
    """테스트셋 분리. (학습, 테스트, 경고) 반환.

    층화 시 각 계층에서 round(n × test_frac) 건을 뽑되, **학습셋에 최소 1건은
    남긴다** — 계층이 비면 그 온도대는 아예 예측할 수 없다.
    """
    rng = random.Random(seed)
    warn: list[str] = []
    if not stratified:
        idx = list(range(len(records)))
        rng.shuffle(idx)
        k = round(len(records) * test_frac)
        test_i = set(idx[:k])
        thin = [f"{lo}~{hi}°C" for lo, hi in STRATA
                if not any(lo <= r["cit"] < hi for i, r in enumerate(records)
                           if i not in test_i)]
        if thin:
            warn.append("완전 랜덤 추출로 학습셋에서 비어버린 계층: "
                        + ", ".join(thin) + " — 그 온도대는 예측할 수 없습니다")
        return ([r for i, r in enumerate(records) if i not in test_i],
                [r for i, r in enumerate(records) if i in test_i], warn)

    train: list[dict] = []
    test: list[dict] = []
    for lo, hi in STRATA:
        grp = [r for r in records if lo <= r["cit"] < hi]
        if not grp:
            continue
        rng.shuffle(grp)
        k = min(round(len(grp) * test_frac), len(grp) - 1)   # 최소 1건은 학습에 남긴다
        if k < round(len(grp) * test_frac):
            warn.append(f"{lo}~{hi}°C 는 {len(grp)}건뿐이라 테스트셋에 "
                        f"{k}건만 뺐습니다(학습셋 보호)")
        test += grp[:k]
        train += grp[k:]
    train.sort(key=lambda r: r["cit"])
    test.sort(key=lambda r: r["cit"])
    return train, test, warn


def loocv(train: list[dict], methods: list[str]) -> list[Score]:
    """학습셋 LOOCV — 1건을 빼고 나머지로 그 1건을 예측. 테스트셋은 안 쓴다.

    **모든 후보를 같은 평가집합에서 채점한다.** 어느 후보든 예측할 수 없는 회차는
    전원 제외한다. 구간평균은 1건을 빼면 그 구간이 비어 예측 불가가 되는 회차가
    있어서(20~25°C 는 실측 1건), 후보마다 평가집합이 달라지면 지표를 나란히 놓을
    수 없다 — RMSE 는 n 이 다르고 R² 는 SST 가 달라진다. 실제로 이 때문에
    R² 순위와 RMSE 순위가 갈리는 것을 테스트가 잡았다(2026-08-25).
    """
    grid = {m: [predict(m, train[:i] + train[i + 1:], r["cit"])
                for i, r in enumerate(train)] for m in methods}
    common = [i for i in range(len(train))
              if all(grid[m][i] is not None for m in methods)]
    dropped = len(train) - len(common)
    out: list[Score] = []
    for m in methods:
        act = [train[i]["corr"] for i in common]
        prd = [grid[m][i] for i in common]
        if act:
            out.append(score(act, prd, m, dropped))
    return out


def holdout(train: list[dict], test: list[dict], method: str) -> tuple[Score | None, list[dict]]:
    """학습셋 전체로 적합해 테스트셋을 예측. (성적, 회차별 상세) 반환."""
    rows: list[dict] = []
    act: list[float] = []
    prd: list[float] = []
    skipped = 0
    for r in test:
        p = predict(method, train, r["cit"])
        if p is None:
            skipped += 1
            rows.append({**r, "pred": None, "err": None})
            continue
        act.append(r["corr"])
        prd.append(p)
        rows.append({**r, "pred": p, "err": r["corr"] - p})
    return (score(act, prd, method, skipped) if act else None), rows


@dataclass
class SelectionResult:
    test_frac: float
    seed: int
    stratified: bool
    criterion: str
    n_train: int
    n_test: int
    loocv: list[Score] = field(default_factory=list)
    best: str | None = None
    holdout: Score | None = None
    holdout_rows: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def run(records: list[dict], *, test_frac: float = 0.2, seed: int = 42,
        stratified: bool = True, criterion: str = "rmse",
        methods: list[str] | None = None) -> SelectionResult:
    """전 절차 실행. records: [{'cit','corr'}, ...] (누적 전체)."""
    if criterion not in CRITERIA:
        raise ValueError(f"기준은 {CRITERIA} 중 하나여야 합니다 (입력: {criterion})")
    if not 0.0 <= test_frac < 1.0:
        raise ValueError(f"테스트셋 비율은 0 이상 1 미만이어야 합니다 (입력: {test_frac})")
    cand = list(methods or METHODS)
    train, test, warn = split(records, test_frac, seed, stratified)
    scores = loocv(train, cand)
    best = min(scores, key=lambda s: s.value(criterion)).method if scores else None
    hs, rows = (holdout(train, test, best) if (best and test) else (None, []))

    if len(test) < 10 and test:
        warn.append(f"테스트셋 {len(test)}건은 표본이 작습니다 — MAE 표준오차가 "
                    f"약 ±{1.7 / len(test) ** 0.5:.2f} MW 이므로, 방법 간 차이가 "
                    f"그보다 작으면 이 결과로 우열을 가릴 수 없습니다")
    if criterion == "r2":
        warn.append("R² 순위는 RMSE 순위와 수학적으로 항상 같습니다"
                    "(SST 가 후보 전체에 동일) — 다른 관점을 보려면 MAE 를 쓰십시오")
    return SelectionResult(test_frac=test_frac, seed=seed, stratified=stratified,
                           criterion=criterion, n_train=len(train), n_test=len(test),
                           loocv=scores, best=best, holdout=hs, holdout_rows=rows,
                           warnings=warn)
