"""시뮬레이션 — 실측 32건과 일치하는지 · 밴드/미달 판정이 맞는지 검증."""
import json
import math

import pytest

from wirye_capacity import constants as C
from wirye_capacity.correction import aggregate_bins
from wirye_capacity.gp import GPCorrectionCurve
from wirye_capacity.margin import MarginCorrector
from wirye_capacity.simulate import BAND, SimInput, format_result, simulate
from wirye_capacity.store import _SEED
from wirye_capacity.theory import TheoryEngine

SEED = json.loads(_SEED.read_text(encoding="utf-8"))
RECS = [{"cit": r["cit"], "corr": r["corr"], "cp_meas": r.get("cp_meas"),
         "cp_design": r.get("cp_design")} for r in SEED]
TABLE = aggregate_bins(RECS)
ENG = TheoryEngine()


def test_theory_matches_seed_recorded_values():
    """시드에 기록된 이론기준값을 시뮬레이션이 재현한다(수기 계산 정합)."""
    worst = 0.0
    for r in SEED:
        res = simulate(SimInput(cit=r["cit"], pressure=r["press"], rh=r["rh"], w=r["w"]),
                       engine=ENG, records=RECS, correction_table=TABLE)
        worst = max(worst, abs(res.theory_base - r["theory"]))
    assert worst < 0.2, worst          # 검증 기준: 최대오차 0.18 MW


def test_measured_correction_matches_seed():
    """실측 CC를 넣으면 시드의 보정값과 같은 값이 나온다."""
    for r in SEED[:8]:
        res = simulate(SimInput(cit=r["cit"], pressure=r["press"], rh=r["rh"],
                                w=r["w"], cc_meas=r["cc_meas"]),
                       engine=ENG, records=RECS, correction_table=TABLE)
        assert res.meas_corr == pytest.approx(r["corr"], abs=0.2)


def test_bid_value_matches_profile():
    """시뮬레이션 입찰값이 build_profile 의 같은 온도 값과 일치한다."""
    from wirye_capacity.profile import build_profile
    rows = {row.temp: row for row in build_profile(ENG, TABLE)}
    for t in (-20, -10, 0, 12, 25, 33, 40):
        res = simulate(SimInput(cit=t), engine=ENG, records=RECS, correction_table=TABLE)
        assert res.real_net == pytest.approx(rows[t].cc_real_net, abs=1e-6)


def test_pressure_and_deg_affect_output():
    base = simulate(SimInput(cit=20), engine=ENG, records=RECS, correction_table=TABLE)
    low_p = simulate(SimInput(cit=20, pressure=990), engine=ENG, records=RECS,
                     correction_table=TABLE)
    worse_deg = simulate(SimInput(cit=20, deg=1.05), engine=ENG, records=RECS,
                         correction_table=TABLE)
    assert low_p.real_net < base.real_net        # 대기압 낮으면 출력 감소
    assert worse_deg.real_net < base.real_net    # 열화 크면 출력 감소


def test_band_and_shortfall_judgement():
    """±0.5% 밴드·미달 판정."""
    inp = SimInput(cit=20)
    ref = simulate(inp, engine=ENG, records=RECS, correction_table=TABLE)
    gross_for_net = ref.real_net + C.CC_AUX          # 정확히 예상값과 같은 실측
    # ① 예상과 동일 → 밴드 안, 미달 아님
    r1 = simulate(SimInput(cit=20, cc_meas=gross_for_net), engine=ENG, records=RECS,
                  correction_table=TABLE)
    assert r1.in_band and not r1.shortfall
    assert r1.net_diff == pytest.approx(0.0, abs=1e-6)
    # ② 밴드보다 크게 낮음 → 미달
    r2 = simulate(SimInput(cit=20, cc_meas=gross_for_net - 5.0), engine=ENG, records=RECS,
                  correction_table=TABLE)
    assert r2.shortfall and not r2.in_band
    assert any("미달" in n for n in r2.notes)
    # ③ 밴드보다 높음 → 미달 아님(출력 줄여 대응)
    r3 = simulate(SimInput(cit=20, cc_meas=gross_for_net + 5.0), engine=ENG, records=RECS,
                  correction_table=TABLE)
    assert not r3.shortfall and not r3.in_band
    assert r3.net_diff > 0


def test_gp_corrector_gives_sigma_and_margin():
    gp = GPCorrectionCurve(RECS)
    res = simulate(SimInput(cit=22), engine=ENG, records=RECS, corrector=gp)
    assert res.corr_sigma > 0
    mc = MarginCorrector(gp, RECS, k=0.8)
    res2 = simulate(SimInput(cit=22), engine=ENG, records=RECS, corrector=mc)
    assert res2.margin > 0
    assert res2.real_net < res.real_net          # 마진만큼 낮아짐


def test_margin_k_without_corrector():
    """구간평균 + margin_k 조합(corrector 미지정)도 마진이 반영된다."""
    plain = simulate(SimInput(cit=35), engine=ENG, records=RECS, correction_table=TABLE)
    marg = simulate(SimInput(cit=35), engine=ENG, records=RECS, correction_table=TABLE,
                    margin_k=0.8)
    assert marg.margin > 0
    assert marg.real_net < plain.real_net


def test_notes_flag_sparse_and_policy_bins():
    sparse = simulate(SimInput(cit=22), engine=ENG, records=RECS, correction_table=TABLE)
    assert any("1건" in n or "신뢰도" in n for n in sparse.notes)   # 20~25°C 는 1건
    shaft = simulate(SimInput(cit=-18), engine=ENG, records=RECS, correction_table=TABLE)
    assert shaft.correction == 0.0
    assert any("Shaft Limit" in n for n in shaft.notes)
    fixed = simulate(SimInput(cit=-5), engine=ENG, records=RECS, correction_table=TABLE)
    assert any("보수적 고정" in n for n in fixed.notes)


def test_condenser_pressure_is_reference_only():
    """복수기압을 넣어도 출력은 바뀌지 않고, 참고 메모만 붙는다."""
    a = simulate(SimInput(cit=33), engine=ENG, records=RECS, correction_table=TABLE)
    b = simulate(SimInput(cit=33, cp_meas=95.0), engine=ENG, records=RECS,
                 correction_table=TABLE)
    assert a.real_net == pytest.approx(b.real_net)
    assert any("동결" in n for n in b.notes)
    assert any("유사온도" in n for n in b.notes)


def test_igv_auto_vs_manual():
    auto = simulate(SimInput(cit=30), engine=ENG, records=RECS, correction_table=TABLE)
    assert auto.w == 6.0                            # 25°C↑ 밴드
    manual = simulate(SimInput(cit=30, w=0.0), engine=ENG, records=RECS,
                      correction_table=TABLE)
    assert manual.w == 0.0
    assert manual.real_net < auto.real_net


def test_format_result_is_readable():
    inp = SimInput(cit=25.1, pressure=1007.7, rh=44.0, cc_meas=414.54)
    txt = format_result(simulate(inp, engine=ENG, records=RECS, correction_table=TABLE), inp)
    for key in ("이론기준값", "예상 입찰값", "실측 대조", "Net 차이"):
        assert key in txt
    assert "nan" not in txt.lower()
