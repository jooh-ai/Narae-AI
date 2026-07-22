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
hiddenimports = []

# asyncua: 동적 import·노드셋 데이터가 있어 통째로 수집(누락 시 런타임 ImportError 방지)
for pkg in ("asyncua",):
    d, b, h = collect_all(pkg)
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
    upx=True,
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
    upx=True,
    upx_exclude=[],
    name="WiryeBidTool",
)
