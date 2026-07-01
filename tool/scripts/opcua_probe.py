"""DataPARC OPC UA 직접 취득 probe — 사내 PC에서 실행.

목적(B 방식 실증): 엑셀/엑셀1 없이 DataPARC OPC UA 서버에 직접 붙어
태그를 읽을 수 있는지 확인한다.

설정파일에서 확인된 조건:
  - 엔드포인트: opc.tcp://localhost:51235/Capstone/OPCUAServer (활성)
  - 보안정책 : #None (무보안) 엔드포인트 제공  → 인증서 불필요
  - 인증토큰 : Anonymous 허용                  → 계정 불필요
  (localhost 로 안 되면 사이트 서버 엔드포인트를 인자로 넘기세요.
   내부 서버 주소는 레포에 저장하지 않으려고 하드코딩하지 않았습니다.)

필요:  pip install asyncua
실행:
  python scripts/opcua_probe.py --host <서버이름>              # 접속+태그 자동 매칭 시도
  python scripts/opcua_probe.py --host <서버이름> --browse     # 주소공간 탐색(태그 형식 확인)
  python scripts/opcua_probe.py --host <서버이름> --find 10MBA11CT901  # 태그 이름 검색
  python scripts/opcua_probe.py opc.tcp://<서버>:51236/Capstone/UAServer  # 특정 엔드포인트
"""
from __future__ import annotations

import os
import socket
import sys
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse

DEFAULT_EP = "opc.tcp://localhost:51235/Capstone/OPCUAServer"
# 사이트 서버(UASiteConfiguration.xml)에서 확인된 UA 서버 포트 후보 + 경로
SITE_PORTS = (51236, 51237, 51238, 51239, 51240, 51241, 51242, 51235)
SITE_PATH = "/Capstone/UAServer"
CIT_TAG = "WR.PB.10MBA11CT901////ZQ01"     # 엑셀1 AD11 (CIT). addin TimeAvg(17~18) = 20.98


def _tcp_open(url: str, timeout: float = 2.0) -> bool:
    """OPC UA 핸드셰이크 전에 포트가 살아있는지 빠르게 확인(막힌 포트 매달림 방지)."""
    p = urlparse(url)
    if not p.hostname or not p.port:
        return True                      # 파싱 불가 시 그냥 시도
    try:
        with socket.create_connection((p.hostname, p.port), timeout=timeout):
            return True
    except OSError:
        return False


def _bn(node) -> str:
    try:
        return node.read_browse_name().Name
    except Exception:
        return "?"


def _ncls(node) -> str:
    try:
        return node.read_node_class().name
    except Exception:
        return "?"


def _plain(nid):
    """ReferenceDescription 의 ExpandedNodeId → 순수 NodeId(로컬 서버용)."""
    from asyncua import ua
    return ua.NodeId(nid.Identifier, nid.NamespaceIndex, nid.NodeIdType)


def browse_tree(client, node, max_depth: int, max_children: int, depth: int = 0) -> None:
    """주소공간을 얕게 훑어 NodeId | BrowseName | NodeClass 출력(태그 형식 파악용).

    get_children_descriptions() 한 번으로 자식 메타데이터를 받아 왕복을 줄인다.
    """
    try:
        descs = node.get_children_descriptions()
    except Exception as e:  # noqa: BLE001
        print("     " + "  " * depth + f"(browse 실패: {e!r})")
        return
    for d in descs[:max_children]:
        cls = d.NodeClass.name
        nid = _plain(d.NodeId)
        print("     " + "  " * depth + f"{nid.to_string()} | {d.BrowseName.Name} | {cls}")
        if depth < max_depth and cls in ("Object", "View"):
            browse_tree(client, client.get_node(nid), max_depth, max_children, depth + 1)
    if len(descs) > max_children:
        print("     " + "  " * depth + f"... (+{len(descs) - max_children}개 더)")


def find_tag(client, substr: str, start=None, cap: int = 200000, budget_s: float = 60.0):
    """start(기본 Objects) 하위를 BFS 하며 BrowseName/NodeId 에 substr 포함 노드 탐색.

    태그는 ns=12 숫자 NodeId + BrowseName(사람이 읽는 태그명)로 노출되므로 BrowseName
    부분일치로 찾는다. get_children_descriptions() 로 노드당 왕복 1회만 발생 → 빠름.
    컨테이너(Object/View)만 큐에 넣어 leaf 태그 탐색을 가속. 상한·시간제한·진행표시 내장.
    """
    from collections import deque

    dq = deque([start if start is not None else client.nodes.objects])
    seen = 0
    visited: set[str] = set()          # 순환 참조 방지
    key = substr.lower()
    t0 = time.monotonic()
    while dq and seen < cap:
        if time.monotonic() - t0 > budget_s:
            print(f"  ⏱ 시간제한({budget_s:.0f}s) 도달 — 탐색 {seen} 노드에서 중단.")
            return None
        node = dq.popleft()
        seen += 1
        if seen % 2000 == 0:
            print(f"    … 탐색 {seen} 노드 (대기열 {len(dq)})")
        try:
            descs = node.get_children_descriptions()
        except Exception:
            continue
        for d in descs:
            bn = d.BrowseName.Name or ""
            nid = _plain(d.NodeId)
            sid = nid.to_string()
            if key in bn.lower() or key in sid.lower():
                print(f"  ★ 발견: {sid} | {bn} | {d.NodeClass.name}")
                try:
                    print("      현재값:", client.get_node(nid).read_value())
                except Exception as e:  # noqa: BLE001
                    print("      값 읽기 실패:", repr(e))
                return client.get_node(nid)
            if d.NodeClass.name in ("Object", "View") and sid not in visited:
                visited.add(sid)
                dq.append(client.get_node(nid))
    print(f"  '{substr}' 미발견 (탐색 {seen} 노드, 상한 {cap})")
    return None


def show_method(client, nodeid: str) -> None:
    """Method 노드의 InputArguments/OutputArguments 출력(UAData 가 fnTagStat 인지 확인)."""
    m = client.get_node(nodeid)
    print(f"  Method: {nodeid} | {_bn(m)}")
    try:
        children = m.get_children()
    except Exception as e:  # noqa: BLE001
        print("    자식 조회 실패:", repr(e))
        return
    shown = False
    for ch in children:
        bn = _bn(ch)
        if bn in ("InputArguments", "OutputArguments"):
            shown = True
            print(f"    {bn}:")
            try:
                for a in ch.read_value() or []:
                    desc = a.Description.Text if getattr(a, "Description", None) else ""
                    print(f"      - {a.Name}  (DataType={a.DataType}, rank={a.ValueRank})  {desc or ''}")
            except Exception as e:  # noqa: BLE001
                print("      읽기 실패:", repr(e))
    if not shown:
        print("    (InputArguments/OutputArguments 없음 — 자식 목록:)")
        for ch in children[:20]:
            print("     ", ch.nodeid.to_string(), "|", _bn(ch), "|", _ncls(ch))


def read_average(client, nodeid: str, start_dt, end_dt) -> None:
    """[start,end] 구간 raw history 를 읽어 단순평균·시간가중평균(TimeAvg 근사) 출력.

    fnTagStat(tag, start, end, 'TimeAvg') = 시간가중 평균. 안정된 1시간 테스트 구간에서는
    단순평균과 거의 같다. 애드인 값과 대조해 네이티브 취득의 정확도를 확인한다.
    """
    node = client.get_node(nodeid)
    try:
        hist = node.read_raw_history(start_dt, end_dt)
    except Exception as e:  # noqa: BLE001
        print("  History 읽기 실패:", repr(e))
        return
    pts = []
    for dv in hist:
        t = getattr(dv, "SourceTimestamp", None) or getattr(dv, "ServerTimestamp", None)
        v = dv.Value.Value if dv.Value is not None else None
        if t is not None and isinstance(v, (int, float)):
            pts.append((t, float(v)))
    pts.sort()
    print(f"  구간 {start_dt} ~ {end_dt}")
    if not pts:
        print("  구간 내 데이터 0점 — 시간대(TZ)/보존기간 확인 필요.")
        return
    simple = sum(v for _, v in pts) / len(pts)
    tw_num = tw_den = 0.0
    for i, (t, v) in enumerate(pts):
        t_next = pts[i + 1][0] if i + 1 < len(pts) else end_dt
        dt = (t_next - t).total_seconds()
        if dt > 0:
            tw_num += v * dt
            tw_den += dt
    tw = tw_num / tw_den if tw_den else simple
    print(f"  {len(pts)}점  |  단순평균 {simple:.4f}  |  시간가중평균(TimeAvg 근사) {tw:.4f}")
    print(f"  첫점 {pts[0][0]}={pts[0][1]:.3f}  끝점 {pts[-1][0]}={pts[-1][1]:.3f}")
    print("  → 이 값이 엑셀1 애드인의 TimeAvg 값과 ±소수점 수준이면 네이티브 취득 검증 완료.")


def build_candidates(argv: list[str]) -> list[str]:
    urls = [a for a in argv if a.startswith("opc.tcp://")]
    if "--host" in argv:
        host = argv[argv.index("--host") + 1]
        urls += [f"opc.tcp://{host}:{p}{SITE_PATH}" for p in SITE_PORTS]
    if not urls:
        urls = [os.environ.get("WIRYE_OPCUA_EP", DEFAULT_EP)]
    return urls


def probe(endpoint: str, browse: bool = False, find: str | None = None,
          node_start: str | None = None, method_id: str | None = None,
          avg=None) -> bool:
    from asyncua.sync import Client

    print("=" * 64)
    print("접속 시도:", endpoint)
    if not _tcp_open(endpoint):
        print("  · TCP 포트 닫힘/필터됨 — 건너뜀 (2s)")
        return False
    client = Client(endpoint, timeout=8)        # 기본 SecurityPolicy=None + Anonymous
    try:
        client.connect()
    except Exception as e:  # noqa: BLE001
        print("  ❌ 접속 실패:", repr(e))
        return False

    try:
        print("  ✅ 접속 성공")
        # 서버가 실제로 제공하는 엔드포인트/보안/토큰 열람(진단용)
        try:
            for ep in client.get_endpoints():
                pol = ep.SecurityPolicyUri.split("#")[-1]
                toks = ",".join(t.TokenType.name for t in ep.UserIdentityTokens)
                print(f"    엔드포인트: {ep.EndpointUrl}  [{pol} / {toks}]")
        except Exception:
            pass
        ns = client.get_namespace_array()
        print("  네임스페이스:")
        for i, u in enumerate(ns):
            print(f"    [{i}] {u}")

        # 시간가중평균 검증 모드 (애드인 대조)
        if avg is not None:
            node_id, start_dt, end_dt = avg
            print(f"  TimeAvg 검증: {node_id}")
            read_average(client, node_id, start_dt, end_dt)
            return True
        # 메서드 인자 확인 모드
        if method_id:
            show_method(client, method_id)
            return True
        # 태그 검색 모드 (--node 지정 시 그 서브트리만, 아니면 Objects 전체)
        if find:
            start = client.get_node(node_start) if node_start else None
            scope = node_start or "Objects"
            print(f"  태그 검색: '{find}'  (범위: {scope})")
            found = find_tag(client, find, start=start)
            if found is None:
                return True
            # 찾으면 아래 History 블록으로 흘러감
        elif node_start:
            print(f"  주소 탐색 시작: {node_start}")
            browse_tree(client, client.get_node(node_start), max_depth=2, max_children=30)
            return True
        elif browse:
            print("  Objects 하위 주소 탐색(태그 형식 확인):")
            browse_tree(client, client.nodes.objects, max_depth=3, max_children=15)
            return True
        else:
            # CIT 태그 노드 자동 매칭 (문자열 NodeId 변형 시도 — 실패 시 --find 안내)
            found = None
            variants = [CIT_TAG, CIT_TAG.split("////")[0]]
            for v in variants:
                for nsidx in range(len(ns)):
                    nid = f"ns={nsidx};s={v}"
                    try:
                        node = client.get_node(nid)
                        val = node.read_value()
                        print(f"  ★ 태그 현재값 읽기 성공: {nid}  →  {val}")
                        found = node
                        break
                    except Exception:
                        continue
                if found is not None:
                    break
            if found is None:
                print("  태그 자동 매칭 실패(태그는 숫자 NodeId) → "
                      "'--node <계층> --find 10MBA11CT901' 로 서브트리 검색하세요.")
                return True   # 접속 자체는 성공

        # 2) 과거 데이터 접근 확인 (최근 3시간 raw)
        try:
            end = datetime.now()
            start = end - timedelta(hours=3)
            hist = found.read_raw_history(start, end)
            vals = [dv.Value.Value for dv in hist
                    if dv.Value is not None and dv.Value.Value is not None]
            if vals:
                print(f"  ★ History 접근 성공: 최근 3h {len(vals)}점, "
                      f"단순평균 {sum(vals) / len(vals):.4f}")
                print("    → 특정 테스트일 17~18시 시간가중평균(TimeAvg) 대조는 다음 단계에서 "
                      "TZ·집계함수 맞춰 진행.")
            else:
                print("  History 응답 OK, 데이터 0점(시간대/보존기간/권한 확인 필요).")
        except Exception as e:  # noqa: BLE001
            print("  History 읽기 실패(현재값 취득은 성공):", repr(e))
        return True
    finally:
        client.disconnect()


def main() -> None:
    try:
        import asyncua  # noqa: F401
    except ImportError:
        print("asyncua 미설치 →  pip install asyncua")
        return
    argv = sys.argv[1:]
    browse = "--browse" in argv
    find = argv[argv.index("--find") + 1] if "--find" in argv else None
    node_start = argv[argv.index("--node") + 1] if "--node" in argv else None
    method_id = argv[argv.index("--method") + 1] if "--method" in argv else None
    avg = None
    if "--avg" in argv:
        node_id = argv[argv.index("--avg") + 1]
        date = argv[argv.index("--date") + 1] if "--date" in argv else None
        stime = argv[argv.index("--start") + 1] if "--start" in argv else "17:00"
        etime = argv[argv.index("--end") + 1] if "--end" in argv else "18:00"
        if not date:
            print("--avg 에는 --date YYYY-MM-DD 가 필요합니다.")
            return
        # 로컬 시간대(KST)로 해석 → asyncua 가 UTC 로 변환 전송
        start_dt = datetime.strptime(f"{date} {stime}", "%Y-%m-%d %H:%M").astimezone()
        end_dt = datetime.strptime(f"{date} {etime}", "%Y-%m-%d %H:%M").astimezone()
        avg = (node_id, start_dt, end_dt)
    endpoints = build_candidates(argv)
    ok = False
    try:
        for ep in endpoints:
            if probe(ep, browse=browse, find=find, node_start=node_start,
                     method_id=method_id, avg=avg):
                ok = True
                break
    except KeyboardInterrupt:
        print("\n(중단됨)")
        return
    print("\n결과:", "✅ 접속·읽기 경로 확인" if ok else "❌ 실패 — 위 오류 메시지 공유")


if __name__ == "__main__":
    main()
