# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 스펙 — 위례 공급가능용량 입찰 산정 Tool (GUI, onedir).

빌드 (사내 Windows, tool 폴더에서):
    pip install pyinstaller asyncua PySide6 openpyxl
    pyinstaller --noconfirm wirye_tool.spec
결과:
    dist\\WiryeBidTool\\WiryeBidTool.exe

디버그(실행 즉시 닫히거나 오류 원인 확인 필요 시):
    아래 EXE(...) 의 console=False → True 로 바꿔 재빌드 → 콘솔에 오류 출력.
"""
from PyInstaller.utils.hooks import collect_all

# 번들 데이터: 엑셀3 템플릿 + 시드/베이스 테이블 (constants.resource 가 _MEIPASS 로 참조)
datas = [
    ("wirye_capacity/templates/excel3_profile_template.xlsx", "wirye_capacity/templates"),
    ("wirye_capacity/data", "wirye_capacity/data"),
]
binaries = []

# 지연(함수 내부) import 모듈은 정적 분석이 놓칠 수 있어 명시한다.
hiddenimports = [
    "wirye_capacity.gp",              # GP 보정기 (ui/app, pipeline 에서 지연 import)
    "wirye_capacity.margin",          # 안전마진
    "wirye_capacity.curve",           # 커널 보정곡선
    "wirye_capacity.simulate",        # 출력 시뮬레이션
    "wirye_capacity.excel4",          # 엑셀4 날짜 백필
    "wirye_capacity.excel_io",        # 엑셀 열기 가드
    "wirye_capacity.ui.chart",        # 출력곡선 비교 차트
    "wirye_capacity.rims.opcua",      # B: OPC UA 취득
    "wirye_capacity.rims.excel_addin",  # A: 엑셀1 경유 취득
    "wirye_capacity.rims.locate",     # 엑셀1 자동 탐색
]

# 동적 import·데이터 파일이 있는 패키지는 통째로 수집(누락 시 런타임 ImportError).
#   asyncua : B 방식(OPC UA 직접 취득) — 노드셋 XML 데이터 포함
#   xlwings : A 방식(엑셀1 경유 취득) — Windows 전용. 빌드 PC에 없으면 건너뜀
#             (A 방식을 쓸 계획이면 빌드 전에 pip install xlwings 필요)
for pkg in ("asyncua", "xlwings"):
    try:
        d, b, h = collect_all(pkg)
    except Exception as e:      # noqa: BLE001 — 미설치 패키지는 조용히 제외
        print(f"[wirye_tool.spec] '{pkg}' 미설치 — 번들에서 제외합니다 ({e})")
        continue
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ["wirye_gui.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "PyQt5", "PyQt6"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="WiryeBidTool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                # UPX 비활성 (COLLECT 주석 참조)
    console=False,            # 디버그 시 True
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,                # SK 아이콘(.ico) 있으면 경로 지정
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    # UPX 비활성: 압축이 DLL·번들 데이터를 손상시켜 실행 시점에 원인 불명 오류를
    # 내는 사례가 있다(예: 번들 xlsx 템플릿이 zip 으로 인식되지 않음).
    # 폴더 용량은 다소 커지지만 안정성을 우선한다.
    upx=False,
    upx_exclude=[],
    name="WiryeBidTool",
)
