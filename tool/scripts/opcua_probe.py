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
  python scripts/opcua_probe.py --host <서버이름>     # 51236~51242 포트 자동 스윕(권장)
  python scripts/opcua_probe.py opc.tcp://<서버>:51236/Capstone/UAServer   # 특정 엔드포인트
  python scripts/opcua_probe.py                        # localhost(로컬 서버 있을 때)
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

DEFAULT_EP = "opc.tcp://localhost:51235/Capstone/OPCUAServer"
# 사이트 서버(UASiteConfiguration.xml)에서 확인된 UA 서버 포트 후보 + 경로
SITE_PORTS = (51236, 51237, 51238, 51239, 51240, 51241, 51242, 51235)
SITE_PATH = "/Capstone/UAServer"
CIT_TAG = "WR.PB.10MBA11CT901////ZQ01"     # 엑셀1 AD11 (CIT). addin TimeAvg(17~18) = 20.98


def build_candidates(argv: list[str]) -> list[str]:
    urls = [a for a in argv if a.startswith("opc.tcp://")]
    if "--host" in argv:
        host = argv[argv.index("--host") + 1]
        urls += [f"opc.tcp://{host}:{p}{SITE_PATH}" for p in SITE_PORTS]
    if not urls:
        urls = [os.environ.get("WIRYE_OPCUA_EP", DEFAULT_EP)]
    return urls


def probe(endpoint: str) -> bool:
    from asyncua.sync import Client

    print("=" * 64)
    print("접속 시도:", endpoint)
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

        # 1) CIT 태그 노드 자동 매칭 (문자열 NodeId: ns=?;s=<tag>)
        found = None
        for nsidx in range(len(ns)):
            nid = f"ns={nsidx};s={CIT_TAG}"
            try:
                node = client.get_node(nid)
                val = node.read_value()
                print(f"  ★ 태그 현재값 읽기 성공: {nid}  →  {val}")
                found = node
                break
            except Exception:
                continue

        if found is None:
            print("  태그 NodeId 자동 매칭 실패 → Objects 폴더 상위 탐색(태그 위치 파악용):")
            try:
                for child in client.nodes.objects.get_children()[:25]:
                    try:
                        print("     ", child.nodeid.to_string(), "|", child.read_browse_name().Name)
                    except Exception:
                        print("     ", child)
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
    endpoints = sys.argv[1:] or [os.environ.get("WIRYE_OPCUA_EP", DEFAULT_EP)]
    ok = False
    for ep in endpoints:
        if probe(ep):
            ok = True
            break
    print("\n결과:", "✅ 접속·읽기 경로 확인" if ok else "❌ 실패 — 위 오류 메시지 공유")


if __name__ == "__main__":
    main()
