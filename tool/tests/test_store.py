"""저장소(Phase 2) 검증 — 시드 적재·List-up·누적 보정 집계·신규 등록."""
import sys
from pathlib import Path

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


def test_seed_loads_31(store):
    assert store.count() == 31


def test_list_up_sorted_by_cit(store):
    rows = store.list_up()
    cits = [r["cit"] for r in rows]
    assert cits == sorted(cits)
    assert cits[0] == pytest.approx(-1.9)
    assert cits[-1] == pytest.approx(36.1)


def test_correction_table_matches_excel4(store):
    table = store.correction_table()
    expect = {
        (0, 10): (5.62, 7), (10, 15): (6.12, 6), (15, 20): (5.55, 3),
        (20, 25): (2.62, 1), (25, 30): (-2.69, 3), (30, 41): (-0.32, 9),
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
    assert store.count() == 32
    # 새 레코드가 25~30 구간 건수에 반영됨 (시드 4건 + 1)
    assert store.correction_table()[(25, 30)]["count"] == 4


def test_delete_and_clear(store):
    rows = store.list_up()
    store.delete(rows[0]["id"])
    assert store.count() == 30
    store.clear()
    assert store.count() == 0


def test_roundtrip_record_fields(store):
    rec = store.all()[0]
    assert isinstance(rec, TestRecord)
    assert rec.cit == pytest.approx(-1.9)
    assert rec.cc_meas == pytest.approx(468.76)
    assert rec.season == "극저온△"


# ─────────────────────────────────────────────────────────────────────────────
# update — List-up 셀 편집용. 파생값(이론·보정)은 저장할 때 다시 계산한다.
# 새 시험 결과의 계절 라벨 입력, RH 이상값 수동 정정에 쓴다.
# ─────────────────────────────────────────────────────────────────────────────
def test_update_recalculates_theory_and_corr():
    st = MeasurementStore()
    st.seed()
    r0 = st.all()[0]
    r1 = st.update(r0.id, rh=41.4)
    assert r1.rh == 41.4
    assert r1.theory != r0.theory                 # RH 가 이론에 반영됨
    # 보정값 = CC실측 − 이론 − W 관계가 유지돼야 한다
    assert r1.corr == pytest.approx(r1.cc_meas - r1.theory - r1.w, abs=1e-9)
    st.close()


def test_update_cc_only_keeps_stored_theory():
    """CC실측만 고치면 이론값은 그대로, 보정값만 움직여야 한다.

    씨앗 31건의 theory 는 엑셀4 I열 값이라 엔진 재계산값과 최대 0.19MW 다르다.
    CC 편집으로 그게 덮어써지면 기준이 흔들린다.
    """
    st = MeasurementStore()
    st.seed()
    r0 = st.all()[0]
    r1 = st.update(r0.id, cc_meas=r0.cc_meas + 5.0)
    assert r1.theory == r0.theory                 # 건드리지 않는다
    # 재계산된 보정값은 저장된 이론값과 정확히 정합해야 한다.
    # (씨앗의 corr·theory 는 엑셀4에서 각각 반올림된 값이라 서로 0.005 안쪽으로
    #  어긋나 있다. 재계산은 그 어긋남을 없애는 쪽이므로 r0.corr+5 와는 다르다.)
    assert r1.corr == pytest.approx(r1.cc_meas - r1.theory - r1.w, abs=1e-9)
    assert r1.corr == pytest.approx(r0.corr + 5.0, abs=0.01)
    st.close()


def test_update_season_only_keeps_numbers():
    """계절 라벨만 바꾸면 숫자는 그대로여야 한다(재계산해도 같은 값)."""
    st = MeasurementStore()
    st.seed()
    r0 = st.all()[0]
    r1 = st.update(r0.id, season="봄·가을")
    assert r1.season == "봄·가을"
    assert r1.cit == r0.cit and r1.cc_meas == r0.cc_meas
    assert r1.theory == r0.theory                 # 라벨 편집은 숫자를 건드리지 않는다
    assert r1.corr == r0.corr
    st.close()


def test_update_rh_to_none_falls_back_to_fixed():
    """RH 를 비우면 이론계산이 60% 고정으로 돌아간다."""
    st = MeasurementStore()
    st.seed()
    r0 = st.all()[0]
    r1 = st.update(r0.id, rh=None)
    assert r1.rh is None
    eng = TheoryEngine()
    assert r1.theory == pytest.approx(
        eng.theory_cc(r1.cit, r1.press, C.DEFAULT_DEG, rh=None))
    st.close()


def test_update_recalc_w_from_new_cit():
    """CIT 를 크게 고치면 W 도 온도밴드값으로 다시 산정해야 한다."""
    from wirye_capacity.theory import igv_turnup
    st = MeasurementStore()
    st.seed()
    r0 = next(r for r in st.all() if r.cit < 0)     # W=0 구간
    r1 = st.update(r0.id, cit=13.7, recalc_w=True)
    assert r1.w == igv_turnup(13.7)
    assert r1.w != r0.w
    st.close()


def test_update_keeps_w_when_given_explicitly():
    st = MeasurementStore()
    st.seed()
    r0 = st.all()[0]
    r1 = st.update(r0.id, cit=13.7, w=6.0, recalc_w=True)   # 명시 W 가 우선
    assert r1.w == 6.0
    st.close()


def test_update_rejects_derived_fields():
    st = MeasurementStore()
    st.seed()
    rid = st.all()[0].id
    for bad in ({"corr": 9.9}, {"theory": 400.0}, {"id": 5}, {"cp_meas": 1.0}):
        with pytest.raises(ValueError, match="수정할 수 없는 필드"):
            st.update(rid, **bad)
    st.close()


def test_update_unknown_id():
    st = MeasurementStore()
    st.seed()
    with pytest.raises(KeyError):
        st.update(999999, rh=50.0)
    st.close()


def test_update_persists_and_reaggregates():
    """수정이 저장되고 보정 테이블 재집계에 반영돼야 한다."""
    st = MeasurementStore()
    st.seed()
    r0 = st.all()[0]
    before = st.correction_table()
    st.update(r0.id, cc_meas=r0.cc_meas + 5.0)
    again = next(r for r in st.all() if r.id == r0.id)
    assert again.cc_meas == pytest.approx(r0.cc_meas + 5.0)
    assert again.corr == pytest.approx(again.cc_meas - again.theory - again.w, abs=1e-9)
    assert st.correction_table() != before
    st.close()


def test_update_date_field():
    """날짜 오배정 정정용 — 2025-04-15·2026-01-08 사례.

    씨앗에 이미 실제 날짜가 들어 있으므로(2026-08 정정) 씨앗에 없는 날짜로 시험한다.
    """
    st = MeasurementStore()
    st.seed()
    assert not st.has_date("2026-06-30")
    rid = st.all()[0].id
    st.update(rid, date="2026-06-30")
    assert st.has_date("2026-06-30")
    st.update(rid, date=None)
    assert not st.has_date("2026-06-30")
    st.close()


# ─────────────────────────────────────────────────────────────────────────────
# 누적 DB 위치 — Tool 폴더 기준(사용자별 독립). 담당자 교체 시 폴더째 인수인계.
# ─────────────────────────────────────────────────────────────────────────────
def test_db_path_priority(tmp_path, monkeypatch):
    """명시 인자 > 설정(환경변수) > Tool 폴더 > 홈 폴백."""
    assert C.db_path(tmp_path / "x.db") == tmp_path / "x.db"
    monkeypatch.setenv("WIRYE_DB_PATH", str(tmp_path / "cfg.db"))
    assert C.db_path() == tmp_path / "cfg.db"
    monkeypatch.delenv("WIRYE_DB_PATH")
    assert C.db_path() == C.app_dir() / C.DB_NAME


def test_db_path_falls_back_to_home_when_unwritable(monkeypatch):
    """Program Files 처럼 쓰기 불가한 곳에 설치되면 홈으로 물러난다."""
    monkeypatch.setattr(C, "_writable", lambda d: False)
    assert C.db_path() == Path.home() / C.DB_NAME


def test_app_dir_uses_exe_folder_when_frozen(monkeypatch, tmp_path):
    """exe 는 sys.executable 의 부모. _MEIPASS(_internal)를 쓰면 재빌드 때 지워진다."""
    exe = tmp_path / "dist" / "WiryeBidTool" / "WiryeBidTool.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))
    monkeypatch.setattr(sys, "_MEIPASS", str(exe.parent / "_internal"), raising=False)
    assert C.app_dir() == exe.parent


def test_migrate_legacy_db_copies_once(tmp_path, monkeypatch):
    """예전 홈 DB 를 새 위치로 1회 복사. 원본은 지우지 않는다."""
    from wirye_capacity.store import migrate_legacy_db
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    src = home / C.DB_NAME
    s = MeasurementStore(src)
    s.seed()
    s.conn.execute("UPDATE measurements SET season='표식' WHERE id=1")
    s.conn.commit()
    n = s.count()
    s.close()

    dst = tmp_path / "app" / C.DB_NAME
    note = migrate_legacy_db(dst)
    assert note and "옮겼습니다" in note
    d = MeasurementStore(dst)
    assert d.count() == n
    assert any(r["season"] == "표식" for r in d.list_up())    # 내용 보존
    d.close()
    assert src.exists()                                       # 원본 유지
    assert migrate_legacy_db(dst) is None                     # 두 번째는 아무것도 안 함


def test_migrate_legacy_db_noop_when_no_source(tmp_path, monkeypatch):
    from wirye_capacity.store import migrate_legacy_db
    empty = tmp_path / "nohome"
    empty.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: empty))
    assert migrate_legacy_db(tmp_path / "app" / C.DB_NAME) is None
