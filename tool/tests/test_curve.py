"""연속 보정곡선(Phase 6) 검증 — 매끄러움·특수구간·외삽금지·토글."""
import json
from pathlib import Path

import pytest

from wirye_capacity import constants as C
from wirye_capacity.curve import CorrectionCurve
from wirye_capacity.pipeline import run_pipeline
from wirye_capacity.profile import build_profile
from wirye_capacity.store import MeasurementStore
from wirye_capacity.theory import TheoryEngine

SEED = json.loads(
    (Path(__file__).parent.parent / "wirye_capacity" / "data" / "measurements_seed.json")
    .read_text(encoding="utf-8")
)


@pytest.fixture
def curve():
    return CorrectionCurve([{"cit": r["cit"], "corr": r["corr"]} for r in SEED], bandwidth=3.5)


def test_special_zones_preserved(curve):
    assert curve(-18) == 0.0                         # Shaft Limit
    assert curve(-5) == pytest.approx(8.78, abs=1e-9)  # 보수적 고정(−14~0)


def test_continuous_no_boundary_jump(curve):
    # 구간 방식은 19→20°C 에서 +6.12→+2.62 (3.5MW 점프), 곡선은 완만
    jump = abs(curve(20) - curve(19))
    assert jump < 1.5
    # 곡선 값은 구간 두 값 사이쯤
    assert 3.0 < curve(19) < 6.5
    assert 3.0 < curve(20) < 5.0


def test_no_extrapolation(curve):
    # 데이터 최대(36.1°C) 밖은 끝값으로 클램프
    assert curve(40) == pytest.approx(curve(36.1), abs=1e-9)


def test_fixed_zone_point_excluded_from_fit(curve):
    """M2 회귀: −1.9°C(고정구간) 점은 곡선 적합에서 제외 → 저온 왜곡 방지."""
    assert min(curve.temps) >= 0          # −1.9°C 제외됨
    # 0°C 보정값이 −1.9°C(+12.9)에 끌려 과대(>8)되지 않고 0~10 군집(~5~6)에 가까움
    assert curve(0) < 8.0


def test_reasonable_fit(curve):
    assert curve.r_squared() > 0.8        # 국소가중은 데이터에 잘 붙음


def test_poly_method_runs():
    c = CorrectionCurve([{"cit": r["cit"], "corr": r["corr"]} for r in SEED],
                        method="poly", degree=2)
    v = c(15)
    assert isinstance(v, float)
    assert -10 < v < 15


def test_build_profile_with_curve_differs_at_boundary():
    eng = TheoryEngine()
    s = MeasurementStore(":memory:"); s.seed()
    table = s.correction_table()
    cur = CorrectionCurve([{"cit": r.cit, "corr": r.corr} for r in s.all()])
    bin_rows = {r.temp: r for r in build_profile(eng, table, pressure=1013, deg=1.028)}
    cur_rows = {r.temp: r for r in build_profile(eng, table, pressure=1013, deg=1.028,
                                                  corrector=cur)}
    # 20°C: 구간(−2.39 적용?) vs 곡선 — 보정값이 다름
    assert bin_rows[20].correction != pytest.approx(cur_rows[20].correction, abs=0.1)
    # Shaft 구간은 동일(0)
    assert bin_rows[-18].correction == cur_rows[-18].correction == 0.0
    s.close()


def test_pipeline_curve_toggle(tmp_path):
    s = MeasurementStore(":memory:"); s.seed()
    res = run_pipeline(date="x", store=s, accumulate=False, correction_method="curve")
    rows = {r.temp: r for r in res.profile_rows}
    # 곡선 적용 시 20°C 보정값이 구간(+2.62)과 다름
    assert rows[20].correction != pytest.approx(2.62, abs=0.1)
    s.close()
