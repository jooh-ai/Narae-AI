"""엔드투엔드 오케스트레이터 검증 — 날짜 → 취득·누적 → Profile → 엑셀3 파일."""
from pathlib import Path

import pytest

from wirye_capacity import constants as C
from wirye_capacity.pipeline import run_pipeline
from wirye_capacity.rims import AcquiredTest, MockRimsConnector
from wirye_capacity.store import MeasurementStore
from wirye_capacity.weather import WeatherForecast


@pytest.fixture
def forecast():
    return WeatherForecast(
        capture="2026-04-15 18:09:12",
        days=["수요일, 4월 15일", "목요일, 4월 16일", "금요일, 4월 17일",
              "토요일, 4월 18일", "일요일, 4월 19일"],
        times=[0, 3, 6, 9, 12, 15, 18, 21],
        pressure_median={"수요일, 4월 15일": 1010.0, "목요일, 4월 16일": 1015.0,
                         "금요일, 4월 17일": 1013.0, "토요일, 4월 18일": 1015.0,
                         "일요일, 4월 19일": 1015.0})


def test_end_to_end_creates_bid_file(tmp_path, forecast):
    import openpyxl
    store = MeasurementStore(":memory:")
    store.seed()                       # 기존 누적 32건
    conn = MockRimsConnector({
        "2025-09-12": AcquiredTest(date="2025-09-12", cit=25.5, pressure=1008.0,
                                   cc_meas=414.5, season="여름")})
    out = str(tmp_path / "bid.xlsx")

    res = run_pipeline(date="2025-09-12", store=store, output_path=out,
                       connector=conn, forecast=forecast, deg=1.028)

    # 누적 1건 증가 (32 → 33)
    assert res.measurement_count == 33
    assert res.new_record is not None and res.new_record.cit == 25.5
    # 적용 대기압 = 전체 중위 평균 − 8
    mean_med = sum(forecast.pressure_median.values()) / len(forecast.pressure_median)
    assert res.applied_pressure == pytest.approx(mean_med - 8)
    # Profile 61행
    assert len(res.profile_rows) == 61
    # 엑셀3 파일 생성 + Mode3 입력 기입됨
    assert Path(out).exists()
    wb = openpyxl.load_workbook(out)
    assert wb["Mode3"]["A5"].value == -20
    assert isinstance(wb["Mode3"]["B5"].value, (int, float))


def test_new_test_shifts_correction(tmp_path, forecast):
    """신규 테스트가 해당 구간 보정 평균을 바꾼다 (누적 효과)."""
    store = MeasurementStore(":memory:")
    store.seed()
    before = store.correction_table()[(25, 30)]["avg"]
    # 25~30 구간에 보정값이 큰 테스트 추가
    conn = MockRimsConnector({
        "2025-09-20": AcquiredTest(date="2025-09-20", cit=26.0, pressure=1013.0,
                                   cc_meas=999.0)})   # 비현실적으로 큰 실측 → 평균 상승
    res = run_pipeline(date="2025-09-20", store=store, connector=conn, forecast=forecast)
    after = res.correction_table[(25, 30)]
    assert after["count"] == 5            # 4 → 5
    assert after["avg"] > before          # 평균 이동


def test_no_connector_just_builds_profile(forecast):
    """connector 없이도 현재 누적으로 Profile 생성 (재발행)."""
    store = MeasurementStore(":memory:")
    store.seed()
    res = run_pipeline(date="2025-09-12", store=store, forecast=forecast, accumulate=False)
    assert res.new_record is None
    assert res.measurement_count == 32
    assert len(res.profile_rows) == 61


def test_default_pressure_without_forecast():
    store = MeasurementStore(":memory:")
    store.seed()
    res = run_pipeline(date="x", store=store)
    assert res.applied_pressure == C.REF_PRESSURE
