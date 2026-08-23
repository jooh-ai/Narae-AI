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
                       connector=conn, forecast=forecast, deg=1.028, accumulate=True)

    # 누적 1건 증가 (32 → 33), 반영됨
    assert res.measurement_count == 32
    assert res.reflected is True
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
    res = run_pipeline(date="2025-09-20", store=store, connector=conn, forecast=forecast,
                       accumulate=True)
    after = res.correction_table[(25, 30)]
    assert after["count"] == 4            # 3 → 4
    assert after["avg"] > before          # 평균 이동


def test_preview_does_not_store(forecast):
    """기본(미반영): 취득·보정값 계산만, 누적은 그대로."""
    store = MeasurementStore(":memory:"); store.seed()
    conn = MockRimsConnector({
        "2025-09-12": AcquiredTest(date="2025-09-12", cit=25.5, pressure=1008.0,
                                   cc_meas=414.5)})
    res = run_pipeline(date="2025-09-12", store=store, connector=conn, forecast=forecast)
    assert res.new_record is not None          # 보정값은 계산됨(표시용)
    assert res.reflected is False
    assert res.measurement_count == 31         # 저장 안 됨
    store.close()


def test_duplicate_date_skipped(forecast):
    """같은 날짜 반영 두 번 → 두 번째는 건너뜀(중복 방지)."""
    store = MeasurementStore(":memory:"); store.seed()
    conn = MockRimsConnector({
        "2025-09-12": AcquiredTest(date="2025-09-12", cit=25.5, pressure=1008.0,
                                   cc_meas=414.5)})
    r1 = run_pipeline(date="2025-09-12", store=store, connector=conn,
                      forecast=forecast, accumulate=True)
    assert r1.reflected and store.count() == 32
    r2 = run_pipeline(date="2025-09-12", store=store, connector=conn,
                      forecast=forecast, accumulate=True)
    assert r2.duplicate_skipped and not r2.reflected
    assert store.count() == 32                 # 그대로
    store.close()


def test_no_connector_just_builds_profile(forecast):
    """connector 없이도 현재 누적으로 Profile 생성 (재발행)."""
    store = MeasurementStore(":memory:")
    store.seed()
    res = run_pipeline(date="2025-09-12", store=store, forecast=forecast, accumulate=False)
    assert res.new_record is None
    assert res.measurement_count == 31
    assert len(res.profile_rows) == 61


def test_start_time_passed_to_connector(forecast):
    """start(테스트 시작 시각)가 커넥터 acquire 까지 전달된다 (17시 외 테스트 지원)."""
    captured = {}

    class SpyConnector:
        def acquire(self, date, start="17:00"):
            captured["start"] = start
            return AcquiredTest(date=date, cit=4.0, pressure=1011.0, cc_meas=460.0)

    store = MeasurementStore(":memory:"); store.seed()
    run_pipeline(date="2025-01-06", store=store, connector=SpyConnector(),
                 forecast=forecast, start="14:00")
    assert captured["start"] == "14:00"
    store.close()


def test_default_pressure_without_forecast():
    store = MeasurementStore(":memory:")
    store.seed()
    res = run_pipeline(date="x", store=store)
    assert res.applied_pressure == C.REF_PRESSURE


# ── 보정 방법의 적용 범위 (사용자 확인 사항) ────────────────────────────────
# "40건을 구간평균으로 쌓고 41번째만 GP 로 돌리면?" → 41건 전체를 GP 로 적합한다.
# 방법은 기록에 붙는 값이 아니라 산출 시점에 누적 전체에 적용되는 값이다.

def test_method_is_not_stored_per_record(forecast):
    """어떤 방법으로 돌려도 저장되는 보정값은 같다 (실측에서 나오는 값이므로)."""
    acq = {"2025-09-12": AcquiredTest(date="2025-09-12", cit=25.5, pressure=1008.0,
                                      cc_meas=414.5, season="여름")}
    saved = {}
    for method in ("bin", "curve", "gp"):
        store = MeasurementStore(":memory:")
        store.seed()
        run_pipeline(date="2025-09-12", store=store, connector=MockRimsConnector(dict(acq)),
                     forecast=forecast, accumulate=True, correction_method=method)
        rec = next(r for r in store.all() if r.date == "2025-09-12")
        saved[method] = (rec.theory, rec.corr)
        # DB 스키마에 방법을 적는 칸이 없다
        cols = [c[1] for c in store.conn.execute("PRAGMA table_info(measurements)")]
        assert "method" not in cols and "correction_method" not in cols
    assert saved["bin"] == saved["curve"] == saved["gp"]


def test_method_applies_to_whole_accumulation(forecast):
    """마지막 1건만 GP 로 돌려도 Profile 은 누적 전체를 GP 로 적합한 결과다."""
    from wirye_capacity.gp import GPCorrectionCurve
    from wirye_capacity.profile import build_profile
    from wirye_capacity.theory import TheoryEngine

    conn = MockRimsConnector({
        "2025-09-12": AcquiredTest(date="2025-09-12", cit=25.5, pressure=1008.0,
                                   cc_meas=414.5, season="여름")})
    store = MeasurementStore(":memory:")
    store.seed()
    res = run_pipeline(date="2025-09-12", store=store, connector=conn,
                       forecast=forecast, accumulate=True, correction_method="gp")
    assert res.correction_method == "gp"

    # 같은 누적 전건을 GP 로 적합한 Profile 과 일치해야 한다
    recs = [{"cit": r.cit, "corr": r.corr} for r in store.all()]
    expect = build_profile(TheoryEngine(), store.correction_table(),
                           pressure=res.applied_pressure,
                           corrector=GPCorrectionCurve(recs))
    assert [r.correction for r in res.profile_rows] == [r.correction for r in expect]


def test_method_changes_bid_across_temperatures(forecast):
    """방법을 바꾸면 오늘 온도만이 아니라 여러 구간의 신고값이 함께 움직인다."""
    def run(method):
        store = MeasurementStore(":memory:")
        store.seed()
        return run_pipeline(date="2025-09-12", store=store, forecast=forecast,
                            correction_method=method).profile_rows

    a, b = run("bin"), run("gp")
    moved = [x.temp for x, y in zip(a, b) if abs(x.cc_real_net - y.cc_real_net) > 0.005]
    assert len(moved) > 20, f"{len(moved)}개 구간만 변함 — 전역 재적합이 아닌 듯"


def test_stamp_records_method(tmp_path, forecast):
    """입찰파일 도장에 방법이 남는다 — 지문은 방법을 담지 않으므로 이것이 유일한 단서."""
    import openpyxl

    from wirye_capacity.correction import table_fingerprint
    fps = set()
    for method, label in (("bin", "구간평균"), ("gp", "GP")):
        store = MeasurementStore(":memory:")
        store.seed()
        out = str(tmp_path / f"bid_{method}.xlsx")
        res = run_pipeline(date="2025-09-12", store=store, output_path=out,
                           forecast=forecast, correction_method=method, margin_k=0.8)
        fps.add(table_fingerprint(res.correction_table))
        props = openpyxl.load_workbook(out).properties
        stamp = " ".join(str(v) for v in (props.title, props.subject, props.description,
                                          props.keywords, props.category) if v)
        assert f"보정방법 {label}" in stamp, stamp
        assert "마진0.8" in stamp, stamp
    assert len(fps) == 1, "지문은 방법과 무관해야 한다(기존 입찰파일이 구버전으로 오판되면 안 됨)"
