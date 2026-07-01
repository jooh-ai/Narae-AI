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
    assert time_weighted_average(pts, _t(18, 0)) == pytest.approx(15.0)


def test_time_weighted_average_unequal_weights():
    # 17:00 값10 (45분) → 17:45 값30 (15분) = (10*2700+30*900)/3600 = 15
    pts = [(_t(17, 0), 10.0), (_t(17, 45), 30.0)]
    assert time_weighted_average(pts, _t(18, 0)) == pytest.approx(15.0)


def test_time_weighted_average_sorts_input():
    pts = [(_t(17, 45), 30.0), (_t(17, 0), 10.0)]      # 역순 입력도 정렬
    assert time_weighted_average(pts, _t(18, 0)) == pytest.approx(15.0)


def test_time_weighted_average_single_point_falls_back_to_simple():
    assert time_weighted_average([(_t(17, 0), 42.0)], _t(18, 0)) == pytest.approx(42.0)


def test_time_weighted_average_empty_returns_none():
    assert time_weighted_average([], _t(18, 0)) is None
    assert time_weighted_average([(None, 5.0), (_t(17, 0), None)], _t(18, 0)) is None


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
                "gt_meas": 271.7, "st_meas": 128.4}

    monkeypatch.setattr(c, "_connect_and_read", fake_read)
    acq = c.acquire("2026-05-05", "17:00")
    assert (acq.cit, acq.pressure, acq.cc_meas) == (21.0, 1005.6, 400.2)
    assert acq.gt_meas == 271.7 and acq.st_meas == 128.4
    assert acq.rh is None and acq.date == "2026-05-05"
    # 창 = 17:00 ~ 18:00 (window_min=60)
    assert (captured["end"] - captured["start"]) == timedelta(minutes=60)


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
