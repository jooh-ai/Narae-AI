"""이론엔진 검증 — 엑셀4 'Profile' 셀값을 정확히 재현하는지 확인."""
import json
from pathlib import Path

import pytest

from wirye_capacity import constants as C
from wirye_capacity.theory import TheoryEngine, igv_turnup

SEED = json.loads(
    (Path(__file__).parent.parent / "wirye_capacity" / "data" / "measurements_seed.json")
    .read_text(encoding="utf-8")
)


@pytest.fixture
def eng():
    return TheoryEngine()


def test_p_corr_unity_at_reference(eng):
    assert eng.p_corr(1013.0) == pytest.approx(1.0)


def test_base_cc_anchor_values(eng):
    # 엑셀4 Profile D열 base 계수
    assert eng.base_cc(-20) == pytest.approx(444.567007, abs=1e-5)
    assert eng.base_cc(25) == pytest.approx(412.292902, abs=1e-5)


def test_theory_cc_reproduces_profile_iso(eng):
    # B2=1013, Deg=1.028 → 이론기준값 = base 그대로
    assert eng.theory_cc(-20, 1013, 1.028) == pytest.approx(444.567007, abs=1e-4)
    assert eng.theory_cc(25, 1013, 1.028) == pytest.approx(412.292902, abs=1e-4)


def test_theory_with_igv_matches_profile_cells(eng):
    # 엑셀4 Profile 이론(D)열: D50(24°C)=419.257, D51(25°C)=418.293 (= base + W)
    assert eng.theory_cc_with_igv(24, 1013, 1.028) == pytest.approx(419.25732, abs=1e-4)
    assert eng.theory_cc_with_igv(25, 1013, 1.028) == pytest.approx(418.292902, abs=1e-4)


def test_igv_bands():
    assert igv_turnup(-20) == 0.0
    assert igv_turnup(-1.9) == 0.0      # 실측 row5와 동일
    assert igv_turnup(-1) == 2.0
    assert igv_turnup(10) == 4.0
    assert igv_turnup(25) == 6.0
    assert igv_turnup(35) == 6.0


def test_pressure_direction(eng):
    # 대기압↑ → 출력↑ (P_corr 분모↓)
    hi = eng.theory_cc(15, 1020, 1.028)
    lo = eng.theory_cc(15, 1000, 1.028)
    assert hi > lo


def test_degradation_direction(eng):
    # Deg↑ → 출력↓
    fresh = eng.theory_cc(15, 1013, 1.000)
    worn = eng.theory_cc(15, 1013, 1.070)
    assert fresh > worn


def test_theory_vs_legacy_handcalc_within_tolerance(eng):
    """엑셀2 수기 이론기준값(I열, 테스트별 설계복수기압 사용)과의 차이.
    base-table 방식은 표준 설계곡선을 쓰므로 약간의 차이가 있다(Phase 2 정합 대상).
    여기서는 회귀 방지를 위한 상한만 확인한다."""
    errs = [
        eng.theory_cc(r["cit"], r["press"], 1.028) - r["theory"]
        for r in SEED
    ]
    mean = sum(errs) / len(errs)
    worst = max(abs(e) for e in errs)
    assert abs(mean) < 0.5, f"mean err {mean:.3f} MW"
    assert worst < 3.0, f"worst err {worst:.3f} MW"
