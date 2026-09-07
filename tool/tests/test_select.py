"""모델 선정 — 테스트셋 분리 · 학습셋 LOOCV · 테스트셋 검증."""
from __future__ import annotations

import json

import pytest

from wirye_capacity import constants as C
from wirye_capacity import select as S
from wirye_capacity.gp import KERNELS, GPCorrectionCurve
from wirye_capacity.store import _SEED


@pytest.fixture(scope="module")
def recs():
    seed = json.loads(_SEED.read_text(encoding="utf-8"))
    return [{"cit": r["cit"], "corr": r["corr"]} for r in seed]


def test_seed_makes_split_reproducible(recs):
    """같은 시드 = 같은 분할. 이게 깨지면 '왜 이 모델을 골랐나' 를 재현할 수 없다."""
    a = S.split(recs, 0.2, seed=42)
    b = S.split(recs, 0.2, seed=42)
    c = S.split(recs, 0.2, seed=7)
    assert [r["cit"] for r in a[1]] == [r["cit"] for r in b[1]]
    assert [r["cit"] for r in a[1]] != [r["cit"] for r in c[1]]


def test_split_sizes_and_disjoint(recs):
    train, test, _ = S.split(recs, 0.2, seed=42)
    assert len(train) + len(test) == len(recs)
    assert not ({id(r) for r in train} & {id(r) for r in test})
    assert 0 < len(test) < len(recs)


def test_strata_merge_15_25(recs):
    """15~20 과 20~25 는 하나의 계층이다 — 20~25°C 실측이 1건뿐이라서다.

    C.BINS 는 그대로 두고 계층만 합친다. 보정 테이블까지 합치면 실제 기울기가
    평균으로 뭉개져 LOOCV 가 나빠지고(1.335 → 1.452) 20~25°C 입찰값이 2.2 MW
    높아진다(미달 방향).
    """
    assert (15, 25) in S.STRATA
    assert (15, 20) not in S.STRATA and (20, 25) not in S.STRATA
    # 실제 보정 구간은 건드리지 않았다
    assert (15, 20, "avg") in C.BINS and (20, 25, "avg") in C.BINS
    assert S.stratum_of(21.3) == (15, 25) and S.stratum_of(16.6) == (15, 25)


def test_stratified_never_empties_a_stratum(recs):
    """층화 추출은 어떤 시드로도 학습셋 계층을 비우지 않는다."""
    for seed in range(30):
        train, _test, _w = S.split(recs, 0.4, seed=seed)
        for lo, hi in S.STRATA:
            if any(lo <= r["cit"] < hi for r in recs):
                assert any(lo <= r["cit"] < hi for r in train), \
                    f"시드 {seed}: {lo}~{hi}°C 계층이 학습셋에서 비었다"


def test_random_split_can_empty_a_stratum(recs):
    """완전 랜덤은 계층을 비울 수 있다 — 층화가 필요한 이유의 반례."""
    hit = False
    for seed in range(60):
        _train, _test, warn = S.split(recs, 0.2, seed=seed, stratified=False)
        if any("비어버린 계층" in x for x in warn):
            hit = True
            break
    assert hit, "완전 랜덤에서 빈 계층이 한 번도 안 나왔다 — 경고 경로가 죽었다"


def test_loocv_does_not_see_test_set(recs):
    """LOOCV 성적이 테스트셋 비율에 따라 변한다 = 학습셋만 쓴다는 증거."""
    r20 = S.run(recs, test_frac=0.2, seed=42, methods=["gp:rbf"])
    r00 = S.run(recs, test_frac=0.0, seed=42, methods=["gp:rbf"])
    assert r20.n_train < r00.n_train
    assert r00.n_test == 0 and r00.holdout is None
    assert r20.loocv[0].n != r00.loocv[0].n


def test_criterion_changes_winner_only_via_mae(recs):
    """R² 순위는 RMSE 순위와 항상 같다(SST 가 후보 전체에 동일). MAE 만 다를 수 있다."""
    by = {c: S.run(recs, test_frac=0.2, seed=42, criterion=c) for c in S.CRITERIA}
    rank = {c: [s.method for s in sorted(by[c].loocv, key=lambda s: s.value(c))]
            for c in S.CRITERIA}
    assert rank["rmse"] == rank["r2"], "R² 와 RMSE 순위가 갈렸다 — 수학적으로 불가능"
    assert by["rmse"].best == by["r2"].best


def test_all_kernels_are_candidates(recs):
    res = S.run(recs, test_frac=0.2, seed=42)
    got = {s.method for s in res.loocv}
    for k in KERNELS:
        assert f"gp:{k}" in got
    assert "bin" in got and "curve" in got


def test_holdout_uses_full_train_set(recs):
    """테스트셋 예측은 학습셋 전체로 적합한 모델이 낸다(LOOCV 잔여가 아니다)."""
    res = S.run(recs, test_frac=0.2, seed=42, methods=["gp:rbf"])
    train, test, _ = S.split(recs, 0.2, seed=42)
    gp = GPCorrectionCurve(train, kernel="rbf")
    for row in res.holdout_rows:
        if row["pred"] is not None:
            assert abs(row["pred"] - gp(row["cit"])) < 1e-9


def test_small_test_set_warns(recs):
    res = S.run(recs, test_frac=0.1, seed=42)
    assert res.n_test < 10
    assert any("표본이 작습니다" in w for w in res.warnings)


def test_r2_criterion_warns_about_tie_with_rmse(recs):
    res = S.run(recs, test_frac=0.2, seed=42, criterion="r2")
    assert any("RMSE 순위와" in w for w in res.warnings)


def test_bad_inputs_raise(recs):
    with pytest.raises(ValueError):
        S.run(recs, criterion="mape")
    with pytest.raises(ValueError):
        S.run(recs, test_frac=1.5)
    with pytest.raises(ValueError):
        S.make_corrector("gp:nope", recs)


def test_method_labels_cover_all_methods():
    assert set(S.METHODS) == set(S.METHOD_LABEL)
    assert S.METHOD_LABEL["gp:rbf"].startswith("GP")


def test_gp_default_kernel_unchanged(recs):
    """기본 커널은 rbf — 종전 동작이 바뀌면 누적 보정값 해석이 달라진다."""
    assert abs(GPCorrectionCurve(recs)(20.0)
               - GPCorrectionCurve(recs, kernel="rbf")(20.0)) < 1e-12


def test_kernels_differ_but_stay_sane(recs):
    """커널마다 값은 달라도 실측 범위 안에서는 상식적인 폭을 벗어나지 않는다."""
    vals = {k: GPCorrectionCurve(recs, kernel=k)(20.0) for k in KERNELS}
    assert len(set(round(v, 3) for v in vals.values())) > 1      # 실제로 다르다
    assert max(vals.values()) - min(vals.values()) < 3.0         # 그러나 폭주하지 않는다
