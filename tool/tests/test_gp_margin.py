"""GP 보정기 · 안전마진 — 실측 32건 기준 동작·안전장치 검증."""
import json
import math

import pytest

from wirye_capacity import constants as C
from wirye_capacity.correction import aggregate_bins
from wirye_capacity.curve import CorrectionCurve
from wirye_capacity.gp import GPCorrectionCurve
from wirye_capacity.margin import (DEFAULT_K, FALLBACK_SD, MarginCorrector,
                                   bin_std, margin_for, margin_rows)
from wirye_capacity.profile import build_profile
from wirye_capacity.store import _SEED
from wirye_capacity.theory import TheoryEngine

SEED = json.loads(_SEED.read_text(encoding="utf-8"))
RECS = [{"cit": r["cit"], "corr": r["corr"]} for r in SEED]


# ───────────────────────── GP ─────────────────────────
def test_gp_hyperparams_selected_and_finite():
    gp = GPCorrectionCurve(RECS)
    ls, sf, sn = gp.hyper
    assert ls > 0 and sf > 0 and sn > 0
    for t in range(-20, 41):
        assert math.isfinite(gp(t)), t


def test_gp_respects_special_bins():
    """Shaft Limit = 0, 보수적 고정 = 정책값 — 곡선이 덮어쓰지 않는다."""
    gp = GPCorrectionCurve(RECS)
    table = aggregate_bins(RECS)
    for t in (-20, -18, -15):
        assert gp(t) == 0.0
    fixed = table[(-14, 0)]["applied"]
    for t in (-14, -7, -1):
        assert gp(t) == pytest.approx(fixed)


def test_gp_no_extrapolation_beyond_measured_range():
    """실측 범위 밖은 끝값으로 클램프 — 40°C 가 36.1°C 값을 넘지 않는다."""
    gp = GPCorrectionCurve(RECS)
    tmax = max(r["cit"] for r in RECS)
    assert gp(40) == pytest.approx(gp(math.floor(tmax)), abs=0.5)
    assert abs(gp(40)) < 20            # 외부 회귀처럼 폭주하지 않음


def test_gp_sigma_and_interval():
    gp = GPCorrectionCurve(RECS)
    s = gp.sigma(20)
    assert 0 < s < 10
    lo, hi = gp.interval(20)
    assert lo < gp(20) < hi
    assert math.isnan(gp.sigma(-18))          # 특수구간은 nan
    assert gp.interval(-18) == (gp(-18), gp(-18))


def test_gp_beats_kernel_on_seed_loocv():
    """LOOCV 예측오차: GP < 커널회귀 < 구간평균 (검토 문서 수치 재현)."""
    eng = TheoryEngine()

    def loocv(make):
        ae = []
        for i, r in enumerate(SEED):
            tr = [RECS[k] for k in range(len(RECS)) if k != i]
            corr = make(tr)(r["cit"])
            pred = eng.theory_cc(r["cit"], r["press"], rh=r["rh"]) + r["w"] + corr
            ae.append(abs(r["cc_meas"] - pred))
        return sum(ae) / len(ae)

    mae_gp = loocv(lambda tr: GPCorrectionCurve(tr))
    mae_k = loocv(lambda tr: CorrectionCurve(tr, method="kernel"))
    assert mae_gp < mae_k, (mae_gp, mae_k)
    assert mae_gp < 1.35


def test_gp_handles_tiny_dataset():
    """3건 미만이면 평균으로 후퇴 — 예외 없이 동작."""
    gp = GPCorrectionCurve([{"cit": 12.0, "corr": 5.0}, {"cit": 13.0, "corr": 6.0}])
    assert math.isfinite(gp(12.5))


# ───────────────────────── 마진 ─────────────────────────
def test_bin_std_and_fallback():
    sd = bin_std(RECS)
    assert sd[(30, 41)] is not None and sd[(30, 41)] > 1.5     # 고온 변동 큼
    assert sd[(15, 20)] is not None and sd[(15, 20)] < 1.0     # 안정
    assert sd[(20, 25)] is None                                 # 1건 → 추정 불가
    # 표본 부족 구간은 FALLBACK 적용
    assert margin_for(22, sd, k=1.0) == pytest.approx(FALLBACK_SD)


def test_margin_is_larger_where_variance_is_larger():
    sd = bin_std(RECS)
    assert margin_for(35, sd) > margin_for(17, sd)      # 고온 > 안정구간


def test_margin_excluded_on_policy_bins():
    """Shaft Limit·보수적 고정 구간은 이미 보수화된 정책값 → 마진 0."""
    sd = bin_std(RECS)
    for t in (-20, -16, -14, -8, -1):
        assert margin_for(t, sd) == 0.0
    assert margin_for(5, sd) > 0                        # 실측 기반 구간은 적용


def test_margin_zero_when_k_zero():
    sd = bin_std(RECS)
    assert margin_for(35, sd, k=0.0) == 0.0


def test_margin_corrector_lowers_output_only():
    """마진 적용 시 보정값이 낮아지고(안전), 원래 기능은 유지."""
    base = GPCorrectionCurve(RECS)
    mc = MarginCorrector(base, RECS, k=DEFAULT_K)
    for t in range(0, 41, 5):
        assert mc(t) <= base(t) + 1e-12
        assert mc(t) == pytest.approx(base(t) - mc.margin(t))
    assert mc.sigma(20) == base.sigma(20)      # __getattr__ 위임


def test_margin_removes_shortfall_on_seed():
    """K=0.8 이면 시드 32건 LOOCV 에서 미달 0건 (검토 문서 결론)."""
    eng = TheoryEngine()
    band = 0.005
    short_plain = short_margin = 0
    for i, r in enumerate(SEED):
        tr = [RECS[k] for k in range(len(RECS)) if k != i]
        gp = GPCorrectionCurve(tr)
        actual = min(r["cc_meas"] - C.CC_AUX, C.BID_CAP_NET)
        theory = eng.theory_cc(r["cit"], r["press"], rh=r["rh"]) + r["w"]
        for corrector, counter in ((gp, "plain"), (MarginCorrector(gp, tr, k=0.8), "margin")):
            bid = min(theory + corrector(r["cit"]) - C.CC_AUX, C.BID_CAP_NET)
            if actual < bid * (1 - band):
                if counter == "plain":
                    short_plain += 1
                else:
                    short_margin += 1
    assert short_plain > 0                      # 마진 없으면 미달 발생
    assert short_margin == 0, short_margin      # 마진 0.8× 로 제거


def test_margin_rows_covers_all_bins():
    rows = margin_rows(RECS)
    assert len(rows) == len(C.BINS)
    assert all(r["margin"] >= 0 for r in rows)
    hot = next(r for r in rows if r["bin"] == (30, 41))
    assert hot["count"] == 9 and hot["sd"] > 1.5


# ───────────────────────── Profile 통합 ─────────────────────────
def test_profile_with_gp_and_margin():
    """corrector 자리에 GP·마진을 넣어도 Profile 이 정상 생성된다."""
    eng = TheoryEngine()
    table = aggregate_bins(RECS)
    gp = GPCorrectionCurve(RECS)
    plain = build_profile(eng, table, corrector=gp)
    marg = build_profile(eng, table, corrector=MarginCorrector(gp, RECS, k=0.8))
    assert len(plain) == len(marg) == 61
    assert [r.temp for r in plain] == list(range(-20, 41))
    # 마진 적용분은 항상 같거나 더 낮다(상한 462 에 걸린 구간은 동일)
    for a, b in zip(plain, marg):
        assert b.cc_real_net <= a.cc_real_net + 1e-9
    # 특수구간(Shaft Limit·보수적 고정)은 마진 제외 → 두 Profile 이 동일
    for a, b in zip(plain, marg):
        if a.temp < 0:
            assert b.cc_real_net == pytest.approx(a.cc_real_net)
    # 462 상한은 현재 데이터에서 발동하지 않는다(최대 Net 458)
    assert max(r.cc_real_net for r in plain) < C.BID_CAP_NET
