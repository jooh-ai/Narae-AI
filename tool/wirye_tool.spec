# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 스펙 — 위례 공급가능용량 입찰 산정 Tool (GUI, onedir).

빌드 (사내 Windows, tool 폴더에서):
    pip install pyinstaller asyncua PySide6 openpyxl
    pyinstaller --noconfirm wirye_tool.spec
결과:
    dist\\WiryeBidTool\\WiryeBidTool.exe

배포·누적 DB
    누적 DB(wirye_measurements.db)는 번들에 넣지 않는다. 처음 실행할 때 exe 가 있는
    폴더에 만들어지고 기준 실적이 적재된다(constants.db_path 참조).
    → dist\\WiryeBidTool\\ 폴더째 복사하면 데이터도 함께 간다. 담당자 교체 시
      폴더 전체를 인수인계하면 되고, 여러 명이 각자 폴더를 쓰면 누적도 각자 쌓인다.
    → Program Files 처럼 쓰기 불가한 곳에 두면 홈 폴더로 물러난다(폴더 복사로
      데이터가 안 따라가므로 권장하지 않는다).

디버그(실행 즉시 닫히거나 오류 원인 확인 필요 시):
    아래 EXE(...) 의 console=False → True 로 바꿔 재빌드 → 콘솔에 오류 출력.
"""
from PyInstaller.utils.hooks import collect_all

# 번들 데이터: 엑셀3 템플릿 + 시드/베이스 테이블 (constants.resource 가 _MEIPASS 로 참조)
datas = [
    # 템플릿 폴더 전체 — .xlsx 와 DRM 회피용 .tpl 사본을 함께 번들
    ("wirye_capacity/templates", "wirye_capacity/templates"),
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
#
# xlwings 는 여기서 수집하지 않는다(중요).
#   GUI(wirye_gui.py → ui/app.py)는 B 방식(OPC UA)만 쓰고 xlwings 를 참조하지 않는다.
#   그런데 collect_all("xlwings") 는 xlwings 의 모든 하위 모듈을 hiddenimport 로 올리고,
#   그 안의 conversion/pandas_conv·numpy_conv 등이 pandas·numpy·PIL 을 import 하는 탓에
#   pandas → pyarrow(49MB), numpy(20MB), scipy(26MB), PIL(8MB) 이 통째로 딸려 들어왔다.
#   (2026-08 실측: _internal 341MB 중 100MB 이상이 이 경로로 유입)
#   A 방식(엑셀1 경유)은 사내 CLI 에서 소스로 실행하며, 그때 pip install xlwings 하면 된다.
for pkg in ("asyncua",):
    try:
        d, b, h = collect_all(pkg)
    except Exception as e:      # noqa: BLE001 — 미설치 패키지는 조용히 제외
        print(f"[wirye_tool.spec] '{pkg}' 미설치 — 번들에서 제외합니다 ({e})")
        continue
    datas += d
    binaries += b
    hiddenimports += h

# 번들에서 확실히 배제할 것 — 소스 전체를 grep 해 참조가 0건임을 확인한 목록.
#   과학 스택 : GP·커널회귀·차트를 전부 표준 라이브러리와 QPainter 로 직접 구현했으므로
#               numpy/scipy/pandas 계열은 한 줄도 쓰지 않는다. xlwings 재유입 차단용으로
#               루트 패키지까지 함께 막는다.
#   PIL       : openpyxl 이 이미지가 있는 통합문서를 읽을 때만 선택적으로 쓴다.
#               excel3 템플릿에는 래스터 이미지가 없어(vmlDrawing 뿐) 불필요.
#   Qt 미사용 : 우리 UI 는 QtWidgets + QtGui(QPainter) + QtCore 3개뿐이다.
excludes = [
    "tkinter", "matplotlib", "PyQt5", "PyQt6",
    # ── 과학 스택 (참조 0건, xlwings 경유로만 유입되던 것) ──
    "xlwings", "pandas", "pyarrow", "numpy", "scipy", "PIL", "Pillow",
    # ── 쓰지 않는 Qt 바인딩 ──
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtQuickWidgets",
    "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets", "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
    "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.Qt3DCore",
    "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets", "PySide6.QtDesigner",
    "PySide6.QtTest", "PySide6.QtSql", "PySide6.QtBluetooth", "PySide6.QtSerialPort",
]

a = Analysis(
    ["wirye_gui.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

# ── 선택적 추가 감량 (기본 비활성) ─────────────────────────────────────────
# 아래 두 항목은 용량 대비 위험이 있어 기본은 그대로 둔다. 배포 용량을 더
# 줄여야 하면 하나씩 켜고 반드시 사내 PC(특히 원격데스크톱)에서 실행 확인할 것.
#
# 1) opengl32sw.dll (약 20MB) — GPU 드라이버가 없을 때 Qt 가 쓰는 소프트웨어
#    OpenGL 폴백. 우리 화면은 QPainter 뿐이라 보통 필요 없지만, RDP 접속 환경에서
#    창이 검게 뜨는 사례가 있어 남겨 둔다.
# a.binaries = [b for b in a.binaries if "opengl32sw" not in b[0].lower()]
#
# 2) Qt 번역 파일 (약 10MB) — 지우면 QMessageBox 의 "확인/취소" 같은 Qt 기본
#    버튼이 영문으로 바뀐다. 우리 문구는 전부 한국어 하드코딩이라 기능엔 영향 없음.
# a.datas = [d for d in a.datas if "translations" not in d[0].replace("\\", "/")]

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
