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


def browse_tree(node, max_depth: int, max_children: int, depth: int = 0) -> None:
    """주소공간을 얕게 훑어 NodeId | BrowseName | NodeClass 출력(태그 형식 파악용)."""
    try:
        children = node.get_children()
    except Exception as e:  # noqa: BLE001
        print("     " + "  " * depth + f"(browse 실패: {e!r})")
        return
    for ch in children[:max_children]:
        cls = _ncls(ch)
        print("     " + "  " * depth + f"{ch.nodeid.to_string()} | {_bn(ch)} | {cls}")
        if depth < max_depth and cls in ("Object", "View"):
            browse_tree(ch, max_depth, max_children, depth + 1)
    if len(children) > max_children:
        print("     " + "  " * depth + f"... (+{len(children) - max_children}개 더)")


def find_tag(client, substr: str, cap: int = 4000):
    """Objects 하위를 BFS 하며 NodeId/BrowseName 에 substr 포함 노드 탐색(상한 cap)."""
    from collections import deque

    dq = deque([client.nodes.objects])
    seen = 0
    key = substr.lower()
    while dq and seen < cap:
        node = dq.popleft()
        seen += 1
        try:
            children = node.get_children()
        except Exception:
            continue
        for ch in children:
            sid = ch.nodeid.to_string()
            bn = _bn(ch)
            if key in sid.lower() or key in bn.lower():
                print(f"  ★ 발견: {sid} | {bn} | {_ncls(ch)}")
                try:
                    print("      현재값:", ch.read_value())
                except Exception as e:  # noqa: BLE001
                    print("      값 읽기 실패:", repr(e))
                return ch
            dq.append(ch)
    print(f"  '{substr}' 미발견 (탐색 {seen} 노드, 상한 {cap})")
    return None


def build_candidates(argv: list[str]) -> list[str]:
    urls = [a for a in argv if a.startswith("opc.tcp://")]
    if "--host" in argv:
        host = argv[argv.index("--host") + 1]
        urls += [f"opc.tcp://{host}:{p}{SITE_PATH}" for p in SITE_PORTS]
    if not urls:
        urls = [os.environ.get("WIRYE_OPCUA_EP", DEFAULT_EP)]
    return urls


def probe(endpoint: str, browse: bool = False, find: str | None = None) -> bool:
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

        # 주소 탐색 모드 — 태그 NodeId 형식 확인용
        if browse:
            print("  Objects 하위 주소 탐색(태그 형식 확인):")
            browse_tree(client.nodes.objects, max_depth=3, max_children=15)
            return True
        if find:
            print(f"  태그 검색: '{find}'")
            found = find_tag(client, find)
            if found is None:
                return True
        else:
            # CIT 태그 노드 자동 매칭 (문자열 NodeId 변형 시도)
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
                print("  태그 자동 매칭 실패 → '--browse' 로 주소 형식을 확인하거나 "
                      "'--find 10MBA11CT901' 로 검색하세요. Objects 상위:")
                try:
                    for child in client.nodes.objects.get_children()[:25]:
                        print("     ", child.nodeid.to_string(), "|", _bn(child), "|", _ncls(child))
                except Exception as e:  # noqa: BLE001
                    print("     탐색 실패:", repr(e))
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
    endpoints = build_candidates(argv)
    ok = False
    try:
        for ep in endpoints:
            if probe(ep, browse=browse, find=find):
                ok = True
                break
    except KeyboardInterrupt:
        print("\n(중단됨)")
        return
    print("\n결과:", "✅ 접속·읽기 경로 확인" if ok else "❌ 실패 — 위 오류 메시지 공유")


if __name__ == "__main__":
    main()
