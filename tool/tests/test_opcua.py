"""OPC UA 커넥터(B) 검증 — 네트워크 없는 순수 로직·조립·캐시.

실제 서버 접속은 사내 PC 전용(scripts/opcua_probe.py 로 검증). 여기서는 시간가중평균·
AcquiredTest 조립·엔드포인트 생성·NodeId 캐시를 네트워크 없이 검증한다.
"""
from datetime import datetime, timedelta, timezone

import pytest

from wirye_capacity.rims.opcua import (
    CORE_TAGS, OpcUaRimsConnector, time_weighted_average,
)


def _t(h, m, s=0):
    return datetime(2026, 5, 5, h, m, s, tzinfo=timezone.utc)


def test_time_weighted_average_basic():
    # 17:00 값10 (30분 유지) → 17:30 값20 (30분 유지) → 18:00 종료 = (10*1800+20*1800)/3600 = 15
    pts = [(_t(17, 0), 10.0), (_t(17, 30), 20.0)]
    assert time_weighted_average(pts, _t(17, 0), _t(18, 0)) == pytest.approx(15.0)


def test_time_weighted_average_unequal_weights():
    # 17:00 값10 (45분) → 17:45 값30 (15분) = (10*2700+30*900)/3600 = 15
    pts = [(_t(17, 0), 10.0), (_t(17, 45), 30.0)]
    assert time_weighted_average(pts, _t(17, 0), _t(18, 0)) == pytest.approx(15.0)


def test_time_weighted_average_sorts_input():
    pts = [(_t(17, 45), 30.0), (_t(17, 0), 10.0)]      # 역순 입력도 정렬
    assert time_weighted_average(pts, _t(17, 0), _t(18, 0)) == pytest.approx(15.0)


def test_time_weighted_average_clamps_bounding_value():
    """★ 회귀: 창 시작 전 경계값(저부하)이 과대가중되면 안 됨.

    16:00 값100 (창 밖, 램프업 전 저부하) → 17:00 값200 → 17:30 값200.
    버그 버전은 16:00 값을 [16:00,17:00] 통째로 가중해 평균을 100 쪽으로 끌어내렸음.
    클램프하면 창 [17:00,18:00] 안은 전부 200 → 200.
    """
    pts = [(_t(16, 0), 100.0), (_t(17, 0), 200.0), (_t(17, 30), 200.0)]
    assert time_weighted_average(pts, _t(17, 0), _t(18, 0)) == pytest.approx(200.0)


def test_time_weighted_average_clamps_trailing_point():
    # 창 끝(18:00) 이후 점은 창 밖 → 무시. 17:00 값10 전체 창 유지 = 10.
    pts = [(_t(17, 0), 10.0), (_t(18, 30), 99.0)]
    assert time_weighted_average(pts, _t(17, 0), _t(18, 0)) == pytest.approx(10.0)


def test_time_weighted_average_single_point_falls_back_to_simple():
    assert time_weighted_average([(_t(17, 0), 42.0)], _t(17, 0), _t(18, 0)) == pytest.approx(42.0)


def test_time_weighted_average_empty_returns_none():
    assert time_weighted_average([], _t(17, 0), _t(18, 0)) is None
    assert time_weighted_average([(None, 5.0), (_t(17, 0), None)], _t(17, 0), _t(18, 0)) is None


def test_requires_endpoint_or_host():
    with pytest.raises(ValueError):
        OpcUaRimsConnector()


def test_endpoints_from_host():
    c = OpcUaRimsConnector(host="server1")
    eps = c.endpoints()
    assert eps[0] == "opc.tcp://server1:51236/Capstone/UAServer"
    assert all(e.startswith("opc.tcp://server1:") for e in eps)


def test_endpoints_explicit():
    ep = "opc.tcp://h:51236/Capstone/UAServer"
    assert OpcUaRimsConnector(endpoint=ep).endpoints() == [ep]


def test_acquire_assembles_acquiredtest(monkeypatch):
    """_connect_and_read 를 스텁으로 대체 → acquire 가 AcquiredTest 를 올바로 조립."""
    c = OpcUaRimsConnector(host="h")
    captured = {}

    def fake_read(start_dt, end_dt):
        captured["start"] = start_dt
        captured["end"] = end_dt
        return {"cit": 21.0, "pressure": 1005.6, "cc_meas": 400.2,
                "gt_meas": 271.7, "st_meas": 128.4, "rh": 44.0}

    monkeypatch.setattr(c, "_connect_and_read", fake_read)
    acq = c.acquire("2026-05-05", "17:00")
    assert (acq.cit, acq.pressure, acq.cc_meas) == (21.0, 1005.6, 400.2)
    assert acq.gt_meas == 271.7 and acq.st_meas == 128.4
    assert acq.rh == 44.0 and acq.date == "2026-05-05"    # 유효 RH → 실측 사용
    # 창 = 17:00 ~ 18:00 (window_min=60)
    assert (captured["end"] - captured["start"]) == timedelta(minutes=60)


def test_acquire_filters_broken_rh(monkeypatch):
    """센서 고장 RH(예: 2.09, 2026-05 실측)는 None → 이론 60% 고정 폴백."""
    c = OpcUaRimsConnector(host="h")
    base = {"cit": 21.0, "pressure": 1005.6, "cc_meas": 400.2}
    for bad in (2.09, 0.0, 150.0, None, "x"):
        monkeypatch.setattr(c, "_connect_and_read", lambda s, e, b=bad: {**base, "rh": b})
        assert c.acquire("2026-05-05").rh is None, bad
    # 경계값은 유효
    monkeypatch.setattr(c, "_connect_and_read", lambda s, e: {**base, "rh": 5.0})
    assert c.acquire("2026-05-05").rh == 5.0


def test_acquire_raises_when_core_missing(monkeypatch):
    c = OpcUaRimsConnector(host="h")
    monkeypatch.setattr(c, "_connect_and_read",
                        lambda s, e: {"cit": 21.0, "pressure": None, "cc_meas": 400.2})
    with pytest.raises(RuntimeError, match="필수 태그"):
        c.acquire("2026-05-05")


def test_nodeid_cache_roundtrip(tmp_path):
    cache = tmp_path / "nodeids.json"
    c1 = OpcUaRimsConnector(host="serverX", cache_path=str(cache))
    c1.nodeid_map = {f: f"ns=12;i={i}" for i, f in enumerate(CORE_TAGS, start=100)}
    c1._save_cache()
    # 같은 host + cache → 로드됨
    c2 = OpcUaRimsConnector(host="serverX", cache_path=str(cache))
    assert c2.nodeid_map == c1.nodeid_map
    # 다른 host → 로드 안 됨(빈 맵)
    c3 = OpcUaRimsConnector(host="other", cache_path=str(cache))
    assert c3.nodeid_map == {}


# ─────────────────────────────────────────────────────────────────────────────
# 취득 품질 경고 — 2025-10-28 CC실측 +1.73MW 불일치(엑셀1 452.3669 vs Tool 454.10)
# 조사에서 드러난 구멍: 값만 받고 집계 상태·정합성을 아무도 확인하지 않았다.
# ─────────────────────────────────────────────────────────────────────────────
_OK = {"cit": 21.0, "pressure": 1005.6, "rh": 44.0}


def test_no_warning_when_cc_matches_gt_plus_st(monkeypatch):
    """사내 기준(2026-05-05)처럼 CC 와 GT+ST 차이가 0.11MW 면 경고 없음."""
    c = OpcUaRimsConnector(host="h")
    monkeypatch.setattr(c, "_connect_and_read", lambda s, e: {
        **_OK, "gt_meas": 271.7202, "st_meas": 128.4340, "cc_meas": 400.2644})
    assert c.acquire("2026-05-05").warnings == []


def test_warns_when_cc_diverges_from_gt_plus_st(monkeypatch):
    """CC 태그가 GT+ST 합과 1MW 넘게 벌어지면 경고 — 조용히 누적되면 안 된다."""
    c = OpcUaRimsConnector(host="h")
    monkeypatch.setattr(c, "_connect_and_read", lambda s, e: {
        **_OK, "gt_meas": 271.72, "st_meas": 128.43, "cc_meas": 401.88})   # +1.73
    w = c.acquire("2026-05-05").warnings
    assert len(w) == 1
    assert "1.73" in w[0] and "GT+ST" in w[0]


def test_warns_when_aggregate_status_not_good():
    """서버가 값을 주면서 Uncertain 을 함께 내려보내면 경고 (구간 결측·불량 신호)."""
    c = OpcUaRimsConnector(host="h")
    c.quality = {"cc_meas": {"source": "server", "status": "Uncertain_DataSubNormal"}}
    w = c._quality_warnings({"cc_meas": 400.2, "gt_meas": 271.7, "st_meas": 128.4})
    assert any("Uncertain_DataSubNormal" in x for x in w)


def test_warns_when_server_aggregate_fell_back_to_raw():
    """서버 집계 실패 → raw 평균 폴백은 엑셀1 과 경계값 처리가 달라 값이 어긋날 수 있다."""
    c = OpcUaRimsConnector(host="h")
    c.quality = {"cit": {"source": "fallback", "status": "예외 TimeoutError"}}
    w = c._quality_warnings({"cc_meas": 400.2, "gt_meas": 271.7, "st_meas": 128.4})
    assert any("raw 평균" in x for x in w)


def test_quality_resets_between_acquires(monkeypatch):
    """직전 취득의 경고가 다음 취득에 남으면 안 된다."""
    c = OpcUaRimsConnector(host="h")
    c.quality = {"cc_meas": {"source": "fallback", "status": "예외 X"}}
    monkeypatch.setattr(c, "_connect_and_read", lambda s, e: {
        **_OK, "cc_meas": 400.2644, "gt_meas": 271.7202, "st_meas": 128.4340})
    assert c.acquire("2026-05-05").warnings == []
    assert c.quality == {}


def _mock(date="2026-05-05"):
    from wirye_capacity.rims.base import AcquiredTest
    from wirye_capacity.rims.mock import MockRimsConnector
    return MockRimsConnector({date: AcquiredTest(
        date=date, cit=21.0, pressure=1005.6, cc_meas=400.26, rh=44.0)})


def test_pipeline_carries_acq_warnings():
    """커넥터가 올린 경고가 PipelineResult 까지 전달돼야 화면에 띄울 수 있다."""
    from wirye_capacity.pipeline import run_pipeline
    from wirye_capacity.store import MeasurementStore

    st = MeasurementStore()
    st.seed()
    conn = _mock()
    conn.last_warnings = ["테스트 경고"]
    res = run_pipeline(date="2026-05-05", store=st, connector=conn, accumulate=False)
    assert res.acq_warnings == ["테스트 경고"]


def test_pipeline_acq_warnings_empty_for_plain_connector():
    """last_warnings 를 모르는 커넥터도 그대로 동작해야 한다(빈 리스트)."""
    from wirye_capacity.pipeline import run_pipeline
    from wirye_capacity.store import MeasurementStore

    st = MeasurementStore()
    st.seed()
    res = run_pipeline(date="2026-05-05", store=st, connector=_mock(), accumulate=False)
    assert res.acq_warnings == []


# ─────────────────────────────────────────────────────────────────────────────
# 습도 2대 교차 검증 — MBL(10MBL11CM001) 드리프트 대응 (2026-08 확인)
#   정상 27일: MBL 이 담당자 실적표와 일치
#   쟁점  5일: MBL 0.0~36.8% vs CXM=실적표 (|CXM-실적표| 0.01~0.05)
#   (MBL−CXM) 전반 -7.9 → 후반 -17.9 %p 로 계속 낮아지는 방향
# ─────────────────────────────────────────────────────────────────────────────
def test_pick_rh_prefers_mbl_when_valid():
    from wirye_capacity.rims.opcua import pick_rh
    assert pick_rh(33.6, 56.8) == (33.6, "mbl")
    assert pick_rh(5.0, 30.0) == (5.0, "mbl")        # 하한 경계는 유효
    assert pick_rh(100.0, 30.0) == (100.0, "mbl")    # 상한 경계도 유효


def test_pick_rh_falls_back_to_cxm_when_mbl_impossible():
    """2026-02-25 MBL 0.1% / 2026-04-02 MBL 0.0% — 예전엔 60% 고정으로 갔다."""
    from wirye_capacity.rims.opcua import pick_rh
    assert pick_rh(0.1, 18.2) == (18.2, "cxm")
    assert pick_rh(0.0, 27.6) == (27.6, "cxm")
    assert pick_rh(None, 40.0) == (40.0, "cxm")
    assert pick_rh(150.0, 40.0) == (40.0, "cxm")


def test_pick_rh_none_when_both_bad():
    from wirye_capacity.rims.opcua import pick_rh
    assert pick_rh(0.0, 1.0) == (None, "none")
    assert pick_rh(None, None) == (None, "none")


def test_pick_rh_does_not_switch_on_large_gap_alone():
    """편차만으로 자동 교체하지 않는다 — 정상 27일과 쟁점 5일의 편차 구간이 겹친다."""
    from wirye_capacity.rims.opcua import pick_rh
    assert pick_rh(9.7, 35.4) == (9.7, "mbl")        # -25.7%p 지만 MBL 유효 → 유지
    assert pick_rh(36.8, 67.6) == (36.8, "mbl")      # -30.8%p 지만 유지


def test_acquire_uses_cxm_and_warns(monkeypatch):
    c = OpcUaRimsConnector(host="h")
    monkeypatch.setattr(c, "_connect_and_read", lambda s, e: {
        "cit": 15.1, "pressure": 1011.6, "cc_meas": 445.6,
        "gt_meas": 290.6, "st_meas": 155.0, "rh": 0.1, "rh_alt": 18.2})
    acq = c.acquire("2026-02-25")
    assert acq.rh == 18.2 and acq.rh_source == "cxm"
    assert acq.rh_mbl == 0.1 and acq.rh_cxm == 18.2
    assert any("CXM" in w for w in acq.warnings)


def test_acquire_warns_on_large_rh_gap_but_keeps_mbl(monkeypatch):
    c = OpcUaRimsConnector(host="h")
    monkeypatch.setattr(c, "_connect_and_read", lambda s, e: {
        "cit": 11.2, "pressure": 1013.0, "cc_meas": 453.1,
        "gt_meas": 295.6, "st_meas": 157.4, "rh": 9.7, "rh_alt": 35.4})
    acq = c.acquire("2026-03-04")
    assert acq.rh == 9.7 and acq.rh_source == "mbl"
    assert any("벌어짐" in w for w in acq.warnings)


def test_acquire_no_warning_when_gap_normal(monkeypatch):
    """정상 27일의 편차(-23.3~-1.0%p) 안이면 경고 없음."""
    c = OpcUaRimsConnector(host="h")
    monkeypatch.setattr(c, "_connect_and_read", lambda s, e: {
        "cit": 6.0, "pressure": 1014.6, "cc_meas": 459.7,
        "gt_meas": 301.3, "st_meas": 158.3, "rh": 17.2, "rh_alt": 40.5})
    acq = c.acquire("2026-02-24")
    assert acq.rh == 17.2 and acq.rh_source == "mbl"
    assert acq.warnings == []


def test_acquire_works_without_cxm_tag(monkeypatch):
    """CXM 태그가 없는 서버에서도 종전처럼 동작해야 한다."""
    c = OpcUaRimsConnector(host="h")
    monkeypatch.setattr(c, "_connect_and_read", lambda s, e: {
        "cit": 21.0, "pressure": 1005.6, "cc_meas": 400.2,
        "gt_meas": 271.7, "st_meas": 128.4, "rh": 44.0})
    acq = c.acquire("2026-05-05")
    assert acq.rh == 44.0 and acq.rh_source == "mbl"
    assert acq.rh_cxm is None and acq.warnings == []


def test_optional_tag_absence_does_not_force_rebrowse():
    """선택 태그(rh_alt)가 미해결이어도 _required() 에는 안 들어간다.

    들어가면 매 취득마다 BFS 재해결(수십만 노드)이 돌아 취득이 크게 느려진다.
    """
    from wirye_capacity.rims.opcua import OPTIONAL_TAGS
    c = OpcUaRimsConnector(host="h")
    assert "rh_alt" in OPTIONAL_TAGS
    assert "rh_alt" not in c._required()
    assert "rh" in c._required() and "cc_meas" in c._required()
