"""DataPARC(Capstone) 직접 연결 가능성 자체 점검 — 사내 PC에서 실행 (읽기 전용).

목적(B 방식 사전조사): 엑셀1/Excel을 거치지 않고 Tool이 DataPARC 히스토리안에서
직접 데이터를 취득할 수 있는지, '연결 수단이 존재하는지'를 먼저 확인한다.

이 스크립트는 아무것도 변경하지 않는다(조회·목록만). 화면에 서버주소/계정이 보이면
나에게 공유하기 전에 가려주세요. (필요한 건 '연결 수단의 종류'이지 비밀정보가 아님)

실행:
    python scripts/dataparc_probe.py
"""
from __future__ import annotations

import glob
import os
import platform
import sys

_HINT = ("parc", "capstone", "datparc", "dataparc", "ctc")


def hr(title: str) -> None:
    print("\n" + "=" * 64 + f"\n{title}\n" + "=" * 64)


def check_python() -> None:
    hr("1) 실행 환경")
    print("Python :", sys.version.split()[0], "/", platform.machine())
    print("OS     :", platform.platform())


def check_odbc() -> None:
    hr("2) ODBC 드라이버 / DSN  (가장 유력한 직접 연결 경로)")
    try:
        import pyodbc
    except ImportError:
        print("pyodbc 미설치 → 설치 후 재실행:  pip install pyodbc")
        return
    print("[설치된 ODBC 드라이버]")
    for d in pyodbc.drivers():
        star = "  ★" if any(k in d.lower() for k in _HINT) else ""
        print("   -", d, star)
    print("[등록된 DSN(데이터 원본)]")
    try:
        sources = pyodbc.dataSources()
        if not sources:
            print("   (등록된 DSN 없음)")
        for name, drv in sources.items():
            star = "  ★" if any(k in (name + drv).lower() for k in _HINT) else ""
            print(f"   - {name}  ->  {drv}{star}")
    except Exception as e:  # noqa: BLE001
        print("   DSN 조회 실패:", e)


def check_install() -> None:
    hr("3) DataPARC 설치/설정 파일  (서버 주소·연결방식 단서)")
    roots = [
        r"C:\Program Files\Capstone",
        r"C:\Program Files (x86)\Capstone",
        os.path.expandvars(r"%PROGRAMDATA%\Capstone"),
        os.path.expandvars(r"%APPDATA%\Capstone"),
        os.path.expandvars(r"%LOCALAPPDATA%\Capstone"),
    ]
    found = False
    for root in roots:
        if os.path.isdir(root):
            found = True
            print("폴더:", root)
            for ext in ("ini", "xml", "config", "json", "cfg"):
                hits = glob.glob(os.path.join(root, "**", f"*.{ext}"), recursive=True)
                for f in hits[:40]:
                    print("   설정파일:", f)
    if not found:
        print("표준 위치에서 Capstone 설치 폴더를 못 찾음(다른 경로일 수 있음).")
    print("\n→ 위 설정파일을 열어 server/host/port/endpoint 항목을 확인하세요"
          " (공유 시 주소·계정은 가림).")


def check_rest() -> None:
    hr("4) REST 클라이언트 가용성")
    try:
        import requests  # noqa: F401
        print("requests 사용 가능 → 서버에 REST 엔드포인트가 있으면 probe 가능")
    except ImportError:
        print("requests 미설치(필요 시):  pip install requests")


def main() -> None:
    check_python()
    check_odbc()
    check_install()
    check_rest()
    hr("다음 단계 (이 출력을 보고 알려주세요)")
    print("★ 표시된 ODBC 드라이버/DSN 이 있으면 → 그 이름을 알려주면 직접 조회 probe를 작성합니다.")
    print("  (예: pyodbc.connect('DSN=...') 로 CIT 태그 1건을 17~18시 평균으로 조회해 엑셀1 값과 대조)")
    print("없으면 → PARCview의 '서버 연결 설정'(host/port) 또는 REST API 지원 여부를 확인합니다.")
    print("\n참고 태그(엑셀1 AD열) — 직접 조회 시 사용:")
    print("  CIT      = WR.PB.10MBA11CT901////ZQ01")
    print("  대기압   = WR.PB.10CXM00CP001////XQ01")
    print("  CC Load  = WR.PB.10MBY10CE901////XQ01   (집계: TimeAvg, 창: 17:00~18:00)")


if __name__ == "__main__":
    main()
