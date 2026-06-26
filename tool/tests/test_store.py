"""저장소(Phase 2) 검증 — 시드 적재·List-up·누적 보정 집계·신규 등록."""
import pytest

from wirye_capacity import constants as C
from wirye_capacity.store import MeasurementStore, TestRecord
from wirye_capacity.theory import TheoryEngine


@pytest.fixture
def store():
    s = MeasurementStore(":memory:")
    s.seed()
    yield s
    s.close()


def test_seed_loads_32(store):
    assert store.count() == 32


def test_list_up_sorted_by_cit(store):
    rows = store.list_up()
    cits = [r["cit"] for r in rows]
    assert cits == sorted(cits)
    assert cits[0] == pytest.approx(-1.9)
    assert cits[-1] == pytest.approx(36.1)


def test_correction_table_matches_excel4(store):
    table = store.correction_table()
    expect = {
        (0, 10): (5.78, 8), (10, 15): (6.28, 6), (15, 20): (6.12, 3),
        (20, 25): (2.62, 1), (25, 30): (-2.39, 4), (30, 41): (-0.32, 9),
    }
    for key, (avg, cnt) in expect.items():
        assert table[key]["count"] == cnt
        assert table[key]["avg"] == pytest.approx(avg, abs=0.01)
    assert table[(-14, 0)]["applied"] == pytest.approx(8.78)


def test_record_test_computes_and_accumulates(store):
    eng = TheoryEngine()
    rec = store.record_test(cit=25.5, press=1008.0, cc_meas=414.5, w=6.0,
                            season="여름", engine=eng)
    # 보정값 = 실측 − 이론(엔진) − W
    expect_theory = eng.theory_cc(25.5, 1008.0, C.DEFAULT_DEG)
    assert rec.theory == pytest.approx(expect_theory, abs=1e-9)
    assert rec.corr == pytest.approx(414.5 - expect_theory - 6.0, abs=1e-9)
    assert store.count() == 33
    # 새 레코드가 25~30 구간 건수에 반영됨 (시드 4건 + 1)
    assert store.correction_table()[(25, 30)]["count"] == 5


def test_delete_and_clear(store):
    rows = store.list_up()
    store.delete(rows[0]["id"])
    assert store.count() == 31
    store.clear()
    assert store.count() == 0


def test_roundtrip_record_fields(store):
    rec = store.all()[0]
    assert isinstance(rec, TestRecord)
    assert rec.cit == pytest.approx(-1.9)
    assert rec.cc_meas == pytest.approx(468.76)
    assert rec.season == "극저온△"
