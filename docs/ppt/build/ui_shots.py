#!/usr/bin/env python3
"""Tool 화면 캡처 — 발표자료에 넣을 창 그림을 뽑는다.

    python3 docs/ppt/build/ui_shots.py --tool-root <claude/tool-v2 체크아웃>/tool

2026-09-17 회신이 이 파일을 다시 쓰게 했다.
  · "Tool에서 가져 왔다는 느낌이 잘 없음. 우리가 따로 그래프를 만드는 것
     같으니, Tool 이라는 느낌이 더 들도록 캡쳐 범위를 넓게"
  · "PPT를 밝게 했으니 Tool 캡쳐도 밝은 느낌으로 수정하고, 실제 Tool 색
     변경은 추후에 작업 하자."

그래서 두 가지를 바꿨다.
  ① 위젯 하나만 오리지 않고 **창 전체**를 잡는다. 제목줄("위례 공급가능용량
     입찰 산정")과 탭줄이 같이 보여야 "도구 화면" 으로 읽힌다.
  ② 도구 색을 건드리지 않고, **캡처할 때만** 밝은 팔레트를 얹는다.
     `theme.C` 를 제자리에서 갈아 끼우고 QSS 를 다시 굽는다 — 저장소의 도구
     코드는 그대로다. 실제 도구 테마 교체는 tool-v2 에서 따로 한다.
     색 이름과 뜻(슬레이트=종전, 강조=현재/개선, 붉은=위험)은 그대로 두고
     값만 밝은 쪽으로 옮겼으므로, 화면 구조·글자·숫자는 실물과 같다.

화면이 없는 서버라 Qt 오프스크린으로 그린다. 표·곡선의 값은 도구가 실제로
계산한 것이다. RiMS 취득만 시드 기반 Mock 이다(사내망에 붙을 수 없다).
QT_SCALE_FACTOR=2 로 두 배 크기로 그려야 장표에서 글자가 또렷하다.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs" / "ppt" / "assets"

SIM = dict(cit=30.0, press=1013.0)      # 여름 한낮 — 보정값이 음수로 뒤집히는 구간
RUN_DATE = "2026-08-26"                 # 시드에 있는 실제 회차

# 발표자료(theme_light.js)와 같은 팔레트. 뜻은 그대로, 값만 밝은 쪽으로.
LIGHT = {
    "ground":  "#FFFFFF",
    "panel":   "#F7F9FB",
    "groove":  "#FFFFFF",
    "rule":    "#C9D0D8",
    "rule2":   "#E4E8ED",
    "ink":     "#1A1A1A",
    "body":    "#333333",
    "dim":     "#5A5A5A",
    "dim2":    "#8C8C8C",
    "brass":   "#EA002C",   # SK 레드 — 개선·현재·선정
    "brassD":  "#F5A3B0",
    "brassS":  "#FDEBEE",
    "red":     "#FF6F0F",   # 주의·위험 — 주황
    "redD":    "#FFD9B8",
    "slate":   "#9AA3AC",   # 종전·이론 — 면
    "slateL":  "#6E7780",   # 종전·이론 — 선
    "steel":   "#C4CAD1",
}

# (파일명, 탭 번호, 창 크기, 설명)
SHOTS = [
    ("tool_win_run",   0, (1340, 900), "공급가능용량 산정 — 온도 61구간 결과"),
    ("tool_win_sim",   3, (1340, 440), "출력 시뮬레이션 — 조건을 넣고 실행한 화면"),
    ("tool_win_curve", 4, (1340, 860), "출력곡선 비교 — 이론(점선) vs 도구가 신고하는 값"),
    ("tool_win_curve_s", 4, (1340, 470), "출력곡선 비교 — 낮은 창(장표 띠용)"),
    ("tool_win_sel",   5, (1340, 980), "모델 선정 — 후보 7가지 교차검증 결과"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool-root", default="", help="v2 테마가 있는 체크아웃의 tool 폴더")
    ap.add_argument("--scale", default="2")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--dark", action="store_true", help="도구 원래(어두운) 색으로 잡는다")
    a = ap.parse_args()

    tool = Path(a.tool_root).resolve() if a.tool_root else (ROOT / "tool")
    if not (tool / "wirye_capacity" / "ui" / "theme.py").exists():
        sys.exit(f"v2 테마(ui/theme.py)가 없는 체크아웃입니다: {tool}")
    sys.path.insert(0, str(tool))
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_SCALE_FACTOR", a.scale)

    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="wirye_shots_"))
    os.environ["WIRYE_DB_PATH"] = str(tmp / "shots.db")

    # ── 색 갈아 끼우기. app 을 불러오기 전에 해야 한다 — app 은 import 시점에
    #    theme.QSS 값을 그대로 받아 간다.
    from wirye_capacity.ui import theme as th
    if not a.dark:
        th.C.update(LIGHT)              # chart.py 도 같은 dict 를 본다
        # 줄무늬 색 하나만 스타일시트에 직접 박혀 있다(theme.py:182
        # `alternate-background-color: #0D1826`). 갈아 끼우지 않으면 표의
        # 짝수 줄만 검게 남는다. 도구 쪽은 tool-v2 에서 C 로 빼는 게 맞다.
        th.QSS = th.qss().replace('#0D1826', LIGHT['panel'])

    from PySide6 import QtWidgets
    from wirye_capacity.ui import app as A

    _OK = QtWidgets.QMessageBox.StandardButton.Ok
    _Y = QtWidgets.QMessageBox.StandardButton.Yes
    QtWidgets.QMessageBox.question = staticmethod(lambda *_a, **_k: _Y)
    for nm in ("information", "warning", "critical"):
        setattr(QtWidgets.QMessageBox, nm, staticmethod(lambda *_a, **_k: _OK))
    QtWidgets.QMessageBox.exec = lambda _self: 0
    QtWidgets.QDialog.exec = lambda _self: 0

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    saved: list[tuple[str, Path]] = []

    def shoot():
        app = QtWidgets.QApplication.instance()
        win = next(w for w in app.topLevelWidgets()
                   if isinstance(w, QtWidgets.QMainWindow))
        tabs = win.findChild(QtWidgets.QTabWidget)
        for bar in win.findChildren(QtWidgets.QWidget):     # 임시 DB 경로 안내 띠
            if bar.objectName() == "banner":
                bar.hide()

        def pump(n=6):
            for _ in range(n):
                app.processEvents()

        # ── 산정 한 회 돌려 표를 채운다. RiMS 는 사내망이라 취득만 Mock.
        import json
        from wirye_capacity import constants as _C
        from wirye_capacity.rims import MockRimsConnector
        from wirye_capacity.rims.base import AcquiredTest
        recs = json.loads(Path(_C.resource("data", "measurements_seed.json"))
                          .read_text(encoding="utf-8"))
        by_date = {r["date"]: AcquiredTest(
            date=r["date"], cit=r["cit"], pressure=r["press"], cc_meas=r["cc_meas"],
            rh=r.get("rh"), cp_meas=r.get("cp_meas"), cp_design=r.get("cp_design"),
            season=r.get("season")) for r in recs if r.get("date")}
        win._connector = lambda: MockRimsConnector(by_date)
        win.date_in.setText(RUN_DATE)
        win.accum_chk.setChecked(False)          # 캡처가 누적을 늘리지 않게
        win._on_run()
        pump()

        # ── 시뮬레이션 · 모델 선정도 미리 돌려 둔다. 빈 화면을 장표에 넣을 수 없다.
        win.sim_cit.setValue(SIM["cit"])
        win.sim_press.setValue(SIM["press"])
        win._on_simulate()
        pump()
        # 테스트셋 비율을 0 으로 두고 돌린다. 기본값 20% 로 두면 학습셋이 32건이
        # 되어 화면의 MAE 가 1.493 로 적히고, 장표 본문(누적 40회 전부로 채점,
        # MAE 1.301)과 어긋난다. 같은 장에 표와 화면을 나란히 두는데 숫자가
        # 다르면 "왜 다릅니까" 에 답할 것이 없다. 0 으로 두면 LOOCV 가 전부를
        # 쓰므로 화면 숫자가 deck_data.methods 와 그대로 맞는다.
        win.sel_frac.setValue(0.0)
        pump()
        win._on_select()
        pump(12)

        try:
            win.statusBar().showMessage(f"누적 {win.store.count()}건")
        except Exception:                                    # noqa: BLE001
            pass

        for name, tab, (w_, h_), _why in SHOTS:
            tabs.setCurrentIndex(tab)
            win.resize(w_, h_)
            pump()
            p = out / f"{name}.png"
            win.grab().save(str(p))
            saved.append((name, p))

        QtWidgets.QApplication.quit()

    QtWidgets.QApplication.exec = lambda *_: (shoot(), 0)[1]
    A.main([])
    import struct
    for name, p in saved:
        d = p.open("rb").read(24)
        wh = struct.unpack(">II", d[16:24])
        print(f"  {name:16s} {wh[0]}x{wh[1]}  ({p.stat().st_size // 1024} KB)")
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
