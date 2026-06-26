"""Phase 4 검증 — RiMS 자동취득→누적 경로 (mock 커넥터)."""
import pytest

from wirye_capacity import constants as C
from wirye_capacity.rims import AcquiredTest, MockRimsConnector, RimsConnector
from wirye_capacity.store import MeasurementStore
from wirye_capacity.theory import TheoryEngine, igv_turnup


def test_mock_implements_protocol():
    conn = MockRimsConnector.from_seed()
    assert isinstance(conn, RimsConnector)        # Protocol 충족
    assert len(conn.dates) == 32


def test_mock_acquire_returns_test():
    conn = MockRimsConnector.from_seed()
    acq = conn.acquire(conn.dates[0])
    assert isinstance(acq, AcquiredTest)
    assert acq.cit == pytest.approx(-1.9)
    assert acq.cc_meas == pytest.approx(468.76)


def test_acquire_unknown_date_raises():
    conn = MockRimsConnector.from_seed()
    with pytest.raises(KeyError):
        conn.acquire("1999-01-01")


def test_record_from_rims_auto_accumulates():
    """날짜 입력 → 자동취득 → 보정값 계산 → 누적 저장."""
    eng = TheoryEngine()
    conn = MockRimsConnector({
        "2025-09-12": AcquiredTest(date="2025-09-12", cit=25.5, pressure=1008.0,
                                   cc_meas=414.5, season="여름"),
    })
    store = MeasurementStore(":memory:")
    rec = store.record_from_rims(conn, "2025-09-12", engine=eng)
    # W = 밴드값 (25.5°C → +6)
    assert igv_turnup(25.5) == 6.0
    expect_theory = eng.theory_cc(25.5, 1008.0, C.DEFAULT_DEG)
    assert rec.theory == pytest.approx(expect_theory, abs=1e-9)
    assert rec.corr == pytest.approx(414.5 - expect_theory - 6.0, abs=1e-9)
    assert rec.date == "2025-09-12"
    assert store.count() == 1
    store.close()


def test_bulk_ingest_reproduces_seed_bins():
    """32건을 RiMS 자동취득으로 적재 → 보정값 집계가 엑셀4와 동일 구간건수.

    (이론기준값은 엔진 계산이라 시드 수기값과 ±차이가 있을 수 있으나, 건수·구간배정은 동일.)
    """
    conn = MockRimsConnector.from_seed()
    store = MeasurementStore(":memory:")
    for d in conn.dates:
        store.record_from_rims(conn, d)
    assert store.count() == 32
    table = store.correction_table()
    assert table[(0, 10)]["count"] == 8
    assert table[(25, 30)]["count"] == 4
    assert table[(30, 41)]["count"] == 9
    store.close()
