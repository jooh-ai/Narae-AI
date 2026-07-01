"""실제 RiMS 커넥터 (B) — DataPARC OPC UA 직접 취득.

엑셀1/Excel 없이 DataPARC OPC UA 서버(익명 접속)에서 태그를 직접 읽는다.
사내 probe(scripts/opcua_probe.py)로 검증된 방식을 정식 커넥터로 구현:
  1. opc.tcp://<host>:5123x/Capstone/UAServer 접속 (SecurityPolicy=None + Anonymous)
  2. 핵심 태그(CIT·대기압·GT·ST·CC)를 BrowseName 으로 1회 해결 → NodeId 캐시
  3. 테스트 창(17~18시) raw history 의 시간가중평균(TimeAvg) 을 읽어 AcquiredTest 반환

NodeId 는 서버 재구성 시 바뀔 수 있어 BrowseName(사람이 읽는 태그명) 기준으로 해결한다.
RH 는 값이 비정상(현장 확인)이라 취득하지 않는다 → 코어에서 60% 고정.
asyncua 는 사내에서만 필요하므로 메서드 내부에서 import 한다.
"""
from __future__ import annotations

import json
import socket
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from .base import AcquiredTest

# 사이트 UA 서버(UASiteConfiguration.xml) 포트 후보 + 경로
SITE_PORTS = (51236, 51237, 51238, 51239, 51240, 51241, 51242, 51235)
SITE_PATH = "/Capstone/UAServer"

# 계산에 사용하는 핵심 태그: field → BrowseName 검색키
# (엑셀 태그 'WR.PB.<KKS>////<suf>' → BrowseName '<KKS>//<suf>'. CIT 로 형식 확인됨)
#
# cc_meas 는 raw 'CC Load' 태그를 쓴다(정규화 CC Gross '공급가능용량' 아님). 근거:
#  - 엑셀4 이론기준값(I)은 실제조건(실측 대기압·실측 RH)에서 계산됨(씨앗 32건 역추적 확인).
#  - 보정값 = CC실측 − I − W 이 성립하려면 CC실측도 실제조건 값(=raw)이어야 함.
#  - 엑셀4 '실측데이터'의 CC실측(G열)이 실제로 raw 값(수동입력)임을 현장 확인(2026-07).
CORE_TAGS = {
    "cit": "10MBA11CT901//ZQ01",       # Comp Inlet Temp (°C)
    "pressure": "10CXM00CP001//XQ01",  # 대기압 (mbar)
    "gt_meas": "10CJA00DE100//XQ12",   # GT Load (MW)
    "st_meas": "10CJA00DE100//XQ11",   # ST Load (MW)
    "cc_meas": "10MBY10CE901//XQ01",   # CC Load raw Gross (MW) — 정규화값 아님
}


def _local(date: str, start: str) -> datetime:
    """'YYYY-MM-DD' + 'HH:MM' → 로컬 시간대(aware) datetime (asyncua 가 UTC 로 전송)."""
    return datetime.strptime(f"{date} {start}", "%Y-%m-%d %H:%M").astimezone()


def _tcp_open(url: str, timeout: float = 2.0) -> bool:
    """OPC UA 핸드셰이크 전에 포트 생존 확인(막힌 포트 매달림 방지)."""
    p = urlparse(url)
    if not p.hostname or not p.port:
        return True
    try:
        with socket.create_connection((p.hostname, p.port), timeout=timeout):
            return True
    except OSError:
        return False


AGG_TIME_AVERAGE = 2343   # OPC UA TimeAverage 집계 함수 NodeId (fnTagStat 'TimeAvg' 와 정합 확인)


def server_time_average(client, nodeid: str, start_dt, end_dt):
    """서버측 TimeAverage 집계(HistoryReadProcessed)로 창 전체 1값 조회.

    fnTagStat 'TimeAvg' 와 동일 알고리즘 → raw 보간의 공백·경계값 왜곡 없음.
    사내 검증(2025-09-23 CIT): 서버값 24.85262 ≡ 애드인 24.8526.
    """
    from asyncua import ua

    node = client.get_node(nodeid)
    details = ua.ReadProcessedDetails()
    details.StartTime = start_dt
    details.EndTime = end_dt
    details.ProcessingInterval = (end_dt - start_dt).total_seconds() * 1000.0  # 창 전체 = 1구간
    details.AggregateType = [ua.NodeId(AGG_TIME_AVERAGE)]
    ac = ua.AggregateConfiguration()
    ac.UseServerCapabilitiesDefaults = True
    details.AggregateConfiguration = ac
    result = node.history_read(details)
    data = result.HistoryData
    vals = [dv.Value.Value for dv in data.DataValues
            if dv.Value is not None and dv.Value.Value is not None]
    return vals[0] if vals else None


def time_weighted_average(points: list[tuple], start_dt, end_dt) -> float | None:
    """[(timestamp, value), …] 의 [start_dt, end_dt] 구간 시간가중평균 (step 보간).

    fnTagStat 'TimeAvg' 재현. 각 표본값이 다음 표본까지 유지된다고 보되, 각 구간을
    창 [start_dt, end_dt] 로 클램프한다 — 히스토리안이 창 시작 직전에 주는 경계값
    (bounding value)이 창 밖 구간까지 과대가중되어 평균을 왜곡하는 것을 방지.
    points 는 정렬을 가정하지 않으며 내부 정렬한다. 비면 None.
    """
    pts = sorted((t, float(v)) for t, v in points if t is not None and v is not None)
    if not pts:
        return None
    num = den = 0.0
    for i, (t, v) in enumerate(pts):
        nxt = pts[i + 1][0] if i + 1 < len(pts) else end_dt
        seg_start = t if t > start_dt else start_dt        # 창 시작 이전은 창 시작으로 클램프
        seg_end = nxt if nxt < end_dt else end_dt           # 창 끝 이후는 창 끝으로 클램프
        dt = (seg_end - seg_start).total_seconds()
        if dt > 0:
            num += v * dt
            den += dt
    if den <= 0:                       # 유효 구간 없음(표본 1개 등) → 단순평균
        return sum(v for _, v in pts) / len(pts)
    return num / den


class OpcUaRimsConnector:
    """DataPARC OPC UA 직접 취득 커넥터 (RimsConnector 인터페이스: acquire→AcquiredTest).

    endpoint 또는 host 중 하나 필요. host 만 주면 SITE_PORTS 를 순차 시도.
    nodeid_map(field→NodeId) 를 주거나 cache_path 에 저장된 걸 쓰면 BFS 해결을 건너뛴다.
    """

    def __init__(self, endpoint: str | None = None, host: str | None = None, *,
                 ports=SITE_PORTS, path: str = SITE_PATH, tag_keys: dict | None = None,
                 nodeid_map: dict | None = None, cache_path: str | Path | None = None,
                 window_min: int = 60, timeout: int = 15):
        if not endpoint and not host:
            raise ValueError("OpcUaRimsConnector: endpoint 또는 host 가 필요합니다.")
        self.endpoint = endpoint
        self.host = host
        self.ports = tuple(ports)
        self.path = path
        self.tag_keys = dict(tag_keys or CORE_TAGS)
        self.nodeid_map = dict(nodeid_map or {})
        self.cache_path = Path(cache_path) if cache_path else None
        self.window_min = window_min
        self.timeout = timeout
        self._cache_key = endpoint or host
        if self.cache_path and not self.nodeid_map:
            self._load_cache()

    # ---------------- 공개 인터페이스 ----------------
    def acquire(self, date: str, start: str = "17:00") -> AcquiredTest:
        start_dt = _local(date, start)
        end_dt = start_dt + timedelta(minutes=self.window_min)
        vals = self._connect_and_read(start_dt, end_dt)
        missing = [f for f in ("cit", "pressure", "cc_meas") if vals.get(f) is None]
        if missing:
            raise RuntimeError(f"OPC UA 취득 실패: 필수 태그 값 없음 {missing} "
                               f"(태그 해결/시간창/보존기간 확인)")
        return AcquiredTest(
            date=date, cit=vals["cit"], pressure=vals["pressure"], cc_meas=vals["cc_meas"],
            gt_meas=vals.get("gt_meas"), st_meas=vals.get("st_meas"), rh=None)

    # ---------------- 네트워크 (사내 전용, 테스트 시 오버라이드 가능) ----------------
    def endpoints(self) -> list[str]:
        if self.endpoint:
            return [self.endpoint]
        return [f"opc.tcp://{self.host}:{p}{self.path}" for p in self.ports]

    def _open_client(self):
        try:
            from asyncua.sync import Client
        except ImportError as e:  # pragma: no cover - 사내 전용
            raise RuntimeError(
                "OpcUaRimsConnector 는 asyncua 가 필요합니다: pip install asyncua") from e
        errors = []
        for ep in self.endpoints():
            if not _tcp_open(ep):
                errors.append(f"{ep}: 포트 닫힘/필터")
                continue
            client = Client(ep, timeout=self.timeout)     # None + Anonymous
            try:
                client.connect()
                self.endpoint = ep
                return client
            except Exception as e:  # noqa: BLE001
                errors.append(f"{ep}: {e!r}")
        raise RuntimeError("OPC UA 접속 실패 — " + " / ".join(errors))

    def _connect_and_read(self, start_dt, end_dt) -> dict:
        client = self._open_client()
        try:
            if not all(f in self.nodeid_map for f in self.tag_keys):
                self._resolve_nodeids(client)
            out: dict = {}
            for field, nid in self.nodeid_map.items():
                try:
                    out[field] = self._read_timeavg(client, nid, start_dt, end_dt)
                except Exception:  # noqa: BLE001 — NodeId stale 가능 → 1회 재해결
                    out[field] = None
            if any(out.get(f) is None for f in self.tag_keys):
                self._resolve_nodeids(client, force=True)
                for field, nid in self.nodeid_map.items():
                    if out.get(field) is None:
                        out[field] = self._read_timeavg(client, nid, start_dt, end_dt)
            return out
        finally:
            client.disconnect()

    def _read_timeavg(self, client, nodeid: str, start_dt, end_dt):
        # 서버측 TimeAverage 집계(fnTagStat 정합). 실패 시 raw 시간가중평균 폴백.
        try:
            val = server_time_average(client, nodeid, start_dt, end_dt)
            if val is not None:
                return val
        except Exception:  # noqa: BLE001 — 구버전/미지원 서버 → 폴백
            pass
        node = client.get_node(nodeid)
        hist = node.read_raw_history(start_dt, end_dt)
        points = [(getattr(dv, "SourceTimestamp", None) or getattr(dv, "ServerTimestamp", None),
                   dv.Value.Value if dv.Value is not None else None) for dv in hist]
        return time_weighted_average(points, start_dt, end_dt)

    def _resolve_nodeids(self, client, force: bool = False) -> dict:
        """BrowseName BFS 로 tag_keys 를 NodeId 로 해결(1회). get_children_descriptions 사용."""
        from collections import deque

        from asyncua import ua

        remaining = {k.lower(): f for f, k in self.tag_keys.items()
                     if force or f not in self.nodeid_map}
        if not remaining:
            return self.nodeid_map
        dq = deque([client.nodes.objects])
        visited: set[str] = set()
        seen = 0
        while dq and remaining and seen < 300000:
            node = dq.popleft()
            seen += 1
            try:
                descs = node.get_children_descriptions()
            except Exception:  # noqa: BLE001
                continue
            for d in descs:
                bn = (d.BrowseName.Name or "").lower()
                for key in list(remaining):
                    if key in bn:
                        field = remaining.pop(key)
                        nid = ua.NodeId(d.NodeId.Identifier, d.NodeId.NamespaceIndex,
                                        d.NodeId.NodeIdType)
                        self.nodeid_map[field] = nid.to_string()
                        break
                if d.NodeClass.name in ("Object", "View"):
                    nid = ua.NodeId(d.NodeId.Identifier, d.NodeId.NamespaceIndex,
                                    d.NodeId.NodeIdType)
                    sid = nid.to_string()
                    if sid not in visited:
                        visited.add(sid)
                        dq.append(client.get_node(nid))
        if remaining:
            raise RuntimeError(
                "OPC UA 태그 해결 실패(BrowseName 미발견): "
                + ", ".join(f"{f}={k}" for k, f in remaining.items()))
        self._save_cache()
        return self.nodeid_map

    # ---------------- NodeId 캐시 (BFS 재실행 회피) ----------------
    def _load_cache(self) -> None:
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        entry = data.get(self._cache_key) if isinstance(data, dict) else None
        if isinstance(entry, dict):
            self.nodeid_map.update({f: v for f, v in entry.items() if f in self.tag_keys})

    def _save_cache(self) -> None:
        if not self.cache_path:
            return
        data = {}
        if self.cache_path.exists():
            try:
                data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            except ValueError:
                data = {}
        if not isinstance(data, dict):
            data = {}
        data[self._cache_key] = dict(self.nodeid_map)
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
        except OSError:
            pass
