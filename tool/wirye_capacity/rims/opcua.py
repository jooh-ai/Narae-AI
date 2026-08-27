"""실제 RiMS 커넥터 (B) — DataPARC OPC UA 직접 취득.

엑셀1/Excel 없이 DataPARC OPC UA 서버(익명 접속)에서 태그를 직접 읽는다.
사내 probe(scripts/opcua_probe.py)로 검증된 방식을 정식 커넥터로 구현:
  1. opc.tcp://<host>:5123x/Capstone/UAServer 접속 (SecurityPolicy=None + Anonymous)
  2. 핵심 태그(CIT·대기압·GT·ST·CC)를 BrowseName 으로 1회 해결 → NodeId 캐시
  3. 테스트 창(17~18시) raw history 의 시간가중평균(TimeAvg) 을 읽어 AcquiredTest 반환

NodeId 는 서버 재구성 시 바뀔 수 있어 BrowseName(사람이 읽는 태그명) 기준으로 해결한다.
RH 는 취득하되 유효범위(5~100%) 검사 후 사용 — 센서 고장값(예: 2.09, 2026-05 확인)이면
None(→코어 60% 고정 폴백). 과거 테스트는 정상 RH 라 엑셀4 이론값(I열)과 정합됨
(실사례: 2026-01-06 RH 23% — 60% 고정 시 이론 +1.01MW 어긋남).
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
    "rh": "10MBL11CM001//XQ01",        # 상대습도 (%) — 압축기 흡입부. 1순위
    "rh_alt": "10CXM00CM001//XQ01",    # 상대습도 (%) — 기상 관측. MBL 실패 시 대체
}

# 필수가 아닌 태그 — 해결 실패해도 취득을 중단하지 않는다(없으면 그냥 대체를 못 쓸 뿐).
OPTIONAL_TAGS = frozenset({"rh_alt"})

# 상대습도 유효범위(%) — 밖이면 센서 고장으로 보고 대체 센서 → 없으면 None(이론 60% 고정)
RH_VALID_RANGE = (5.0, 100.0)

# MBL 과 CXM 습도의 정상 편차 한계(%p). 넘으면 경고만 하고 값은 바꾸지 않는다.
#
# 근거(2026-08, 32일 17:00 창 실측): 담당자 실적표와 일치하는 27일의 (MBL − CXM) 은
# 평균 -13.1, 표준편차 6.7, 범위 -23.3 ~ -1.0 %p 였다. 원래도 MBL 이 낮게 나온다
# (흡입부 공기가 외기보다 약간 따뜻하면 상대습도가 내려간다 — 물리적으로 정상).
#
# 주의: MBL 은 드리프트 중이다(전반 -7.9 → 후반 -17.9 %p, 10개월에 10%p).
# 그래서 이 문턱은 시간이 지나면 정상일까지 걸러내게 된다. 자동 대체 판정에
# 쓰지 않고 '사람이 확인하라'는 경고에만 쓰는 이유다. 센서 교정이 근본 해결이다.
RH_GAP_WARN = 25.0


def _num(v):
    """숫자면 float, 아니면 None (태그가 문자열·None 을 줄 수 있다)."""
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _rh_ok(v) -> bool:
    return v is not None and RH_VALID_RANGE[0] <= v <= RH_VALID_RANGE[1]


def pick_rh(mbl, cxm):
    """습도 2대 교차 검증 — 쓸 값과 출처를 돌려준다.

    MBL(압축기 흡입부)이 이론상 맞는 위치이므로 1순위다. 유효범위를 벗어나면
    CXM(기상 관측)으로 대체한다. 둘 다 실패하면 None(코어가 60% 고정으로 계산).

    왜 '크게 벌어지면 자동 교체'를 하지 않는가:
      2026-08 실측에서 정상 27일의 (MBL−CXM)이 -23.3 ~ -1.0 %p 였고 쟁점 5일은
      -32.1 ~ -18.1 %p 로 구간이 겹친다. 편차만으로는 못 가른다. 게다가 MBL 이
      드리프트 중이라(10개월 10%p) 어떤 문턱을 잡아도 곧 정상일을 걸러낸다.
      그래서 명백한 경우(유효범위 이탈)만 자동 대체하고, 나머지는 경고만 남긴다.
      (2026-02-25 MBL 0.1% · 2026-04-02 MBL 0.0% 가 자동 대체에 해당한다.)
    """
    m, c = _num(mbl), _num(cxm)
    if _rh_ok(m):
        return m, "mbl"
    if _rh_ok(c):
        return c, "cxm"
    return None, "none"


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

    반환: (값, StatusCode 이름).  StatusCode 를 반드시 함께 본다 — 구간에 결측·불량이
    섞이면 서버는 값을 주면서 Uncertain_DataSubNormal 등을 함께 내려보낸다. 이걸 버리면
    '평균이 일부 구간으로만 계산된 값'을 정상 측정값으로 오인한다.
    (2025-10-28 CC 실측 +1.73MW 불일치 조사 중 발견 — 예전에는 상태를 버렸다.)
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
    for dv in result.HistoryData.DataValues:
        if dv.Value is None or dv.Value.Value is None:
            continue
        sc = getattr(dv, "StatusCode", None)
        name = getattr(sc, "name", None) or (str(sc) if sc is not None else "미확인")
        return dv.Value.Value, name
    return None, "결과 없음"


# CC Load 태그와 GT+ST 합의 허용 차이(MW). 사내 기준값(2026-05-05)에서 +0.1102 였다.
# 이보다 크게 벌어지면 태그가 다른 지점을 보고 있거나 한쪽 데이터가 튄 것이다.
CC_SUM_TOL = 1.0


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
        self.quality: dict[str, dict] = {}   # field → {source, status} (취득 경로·집계 상태)
        self.last_warnings: list[str] = []   # 직전 acquire 의 품질 경고
        self._cache_key = endpoint or host
        if self.cache_path and not self.nodeid_map:
            self._load_cache()

    # ---------------- 공개 인터페이스 ----------------
    def acquire(self, date: str, start: str = "17:00") -> AcquiredTest:
        self.quality = {}                   # 이번 취득의 경로·집계 상태만 남긴다
        start_dt = _local(date, start)
        end_dt = start_dt + timedelta(minutes=self.window_min)
        vals = self._connect_and_read(start_dt, end_dt)
        missing = [f for f in ("cit", "pressure", "cc_meas") if vals.get(f) is None]
        if missing:
            raise RuntimeError(f"OPC UA 취득 실패: 필수 태그 값 없음 {missing} "
                               f"(태그 해결/시간창/보존기간 확인)")
        rh, rh_src = pick_rh(vals.get("rh"), vals.get("rh_alt"))
        # 파이프라인이 화면에 띄울 수 있게 커넥터에도 남긴다(store 는 AcquiredTest 를 버린다).
        self.last_warnings = self._quality_warnings(vals, rh_src)
        acq = AcquiredTest(
            date=date, cit=vals["cit"], pressure=vals["pressure"], cc_meas=vals["cc_meas"],
            gt_meas=vals.get("gt_meas"), st_meas=vals.get("st_meas"), rh=rh,
            rh_mbl=_num(vals.get("rh")), rh_cxm=_num(vals.get("rh_alt")), rh_source=rh_src,
            warnings=list(self.last_warnings))
        # 습도를 손으로 바꾼 경우 '무엇을 무엇으로 바꿨는지' 를 화면에 남기려면
        # 원래 취득값이 필요하다. store 는 AcquiredTest 를 버리므로 여기 보관한다.
        self.last_acquired = acq
        return acq

    def _quality_warnings(self, vals: dict, rh_src: str = "mbl") -> list[str]:
        """취득값을 그대로 쓰되, 사람이 확인해야 할 사항을 문장으로 모은다.

        보정값 = CC실측 − 이론 − W 이므로 CC실측 오차는 그대로 보정값 오차가 된다.
        GP 예측오차가 1.24MW 인데 CC 가 1MW 어긋나면 모델보다 데이터가 더 틀린 셈이라,
        조용히 누적하지 않고 반드시 화면에 띄운다.
        """
        w: list[str] = []
        mbl, cxm = _num(vals.get("rh")), _num(vals.get("rh_alt"))
        if rh_src == "cxm":
            w.append(f"습도: MBL({mbl if mbl is None else f'{mbl:.1f}'}%)이 유효범위 밖 → "
                     f"CXM({cxm:.1f}%) 사용")
        elif rh_src == "none":
            w.append("습도: MBL·CXM 둘 다 유효범위 밖 → 이론계산 60% 고정")
        elif None not in (mbl, cxm) and abs(mbl - cxm) > RH_GAP_WARN:
            w.append(f"습도: MBL {mbl:.1f}% 와 CXM {cxm:.1f}% 가 {mbl - cxm:+.1f}%p 벌어짐 "
                     f"(정상 -23~-1%p) — MBL 드리프트 확인 필요. 값은 MBL 유지")
        gt, st, cc = vals.get("gt_meas"), vals.get("st_meas"), vals.get("cc_meas")
        if None not in (gt, st, cc):
            gap = cc - (gt + st)
            if abs(gap) > CC_SUM_TOL:
                w.append(f"CC 태그({cc:.2f}) 와 GT+ST 합({gt + st:.2f}) 이 "
                         f"{gap:+.2f} MW 벌어짐 — 엑셀1 값과 대조 필요")
        for field, q in self.quality.items():
            if q.get("source") == "fallback":
                w.append(f"{field}: 서버 집계 실패로 raw 평균 사용 ({q.get('status')}) "
                         "— 엑셀1 과 값이 다를 수 있음")
            elif q.get("status") not in ("Good", "미확인"):
                w.append(f"{field}: 집계 상태 {q.get('status')} — 구간에 결측·불량 가능")
        return w

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

    def _required(self) -> list[str]:
        """해결·읽기 완료를 따질 때 기준이 되는 태그. 선택 태그는 제외한다.

        선택 태그(rh_alt)를 여기 포함하면, 그 태그가 서버에 없을 때 매 취득마다
        BFS 재해결(수십만 노드 탐색)이 돌아 취득이 크게 느려진다.
        """
        return [f for f in self.tag_keys if f not in OPTIONAL_TAGS]

    def _connect_and_read(self, start_dt, end_dt) -> dict:
        client = self._open_client()
        try:
            if not all(f in self.nodeid_map for f in self._required()):
                self._resolve_nodeids(client)
            out: dict = {}
            for field, nid in self.nodeid_map.items():
                try:
                    out[field] = self._read_timeavg(client, nid, start_dt, end_dt, field)
                except Exception:  # noqa: BLE001 — NodeId stale 가능 → 1회 재해결
                    out[field] = None
            if any(out.get(f) is None for f in self._required()):
                self._resolve_nodeids(client, force=True)
                for field, nid in self.nodeid_map.items():
                    if out.get(field) is None:
                        out[field] = self._read_timeavg(client, nid, start_dt, end_dt, field)
            return out
        finally:
            client.disconnect()

    def _read_timeavg(self, client, nodeid: str, start_dt, end_dt, field: str = "?"):
        # 서버측 TimeAverage 집계(fnTagStat 정합). 실패 시 raw 시간가중평균 폴백.
        # 어느 경로로 읽었는지·집계 상태가 무엇이었는지 self.quality 에 남긴다.
        # 폴백은 fnTagStat 와 경계값 처리가 미묘하게 달라 값이 어긋날 수 있으므로
        # 조용히 넘기지 않고 반드시 기록한다.
        try:
            val, status = server_time_average(client, nodeid, start_dt, end_dt)
            if val is not None:
                self.quality[field] = {"source": "server", "status": status}
                return val
            self.quality[field] = {"source": "fallback", "status": status}
        except Exception as e:  # noqa: BLE001 — 구버전/미지원 서버 → 폴백
            self.quality[field] = {"source": "fallback", "status": f"예외 {type(e).__name__}"}
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
        # 선택 태그(rh_alt)는 못 찾아도 취득을 중단하지 않는다 — 대체 습도를 못 쓸 뿐이다.
        missing_req = {k: f for k, f in remaining.items() if f not in OPTIONAL_TAGS}
        if missing_req:
            raise RuntimeError(
                "OPC UA 태그 해결 실패(BrowseName 미발견): "
                + ", ".join(f"{f}={k}" for k, f in missing_req.items()))
        for k, f in remaining.items():
            self.quality[f] = {"source": "unresolved", "status": f"BrowseName '{k}' 미발견"}
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
