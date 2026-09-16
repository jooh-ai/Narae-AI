#!/usr/bin/env python3
"""Tool 화면 캡처 — 발표자료에 넣을 조각만 골라 뽑는다.

    python3 docs/ppt/build/ui_shots.py --tool-root /path/to/checkout/tool

tool-v2 체크아웃의 `tool/scripts/ui_shot.py` 와 같은 수법이다. 다만 그 쪽에는
**결과가 채워진** 시뮬레이션 화면과 모델 선정 표 프리셋이 없다. 빈 화면을
장표에 넣을 수는 없으니 여기서 한 번 돌려 놓고 잡는다.

  tool_sim    출력 시뮬레이션 탭 — 조건을 넣고 실행한 뒤 (결과가 보이는 상태)
  tool_loocv  모델 선정 탭의 교차검증 표 — 후보 7가지를 실제로 겨룬 결과

화면이 없는 서버라 Qt 오프스크린으로 그린다. 화면에 뜨는 값은 도구가 실제로
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool-root", default="", help="v2 테마가 있는 체크아웃의 tool 폴더")
    ap.add_argument("--size", default="1280x860")
    ap.add_argument("--scale", default="2")
    ap.add_argument("--out", default=str(OUT))
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
        w_, h_ = (int(v) for v in a.size.lower().split("x"))
        win.resize(w_, h_)
        tabs = win.findChild(QtWidgets.QTabWidget)
        for bar in win.findChildren(QtWidgets.QWidget):     # 임시 DB 경로 안내 띠
            if bar.objectName() == "banner":
                bar.hide()
        try:
            win.statusBar().showMessage(f"누적 {win.store.count()}건")
        except Exception:                                    # noqa: BLE001
            pass

        def pump(n=5):
            for _ in range(n):
                app.processEvents()

        def grab(widget, name):
            p = out / f"{name}.png"
            widget.grab().save(str(p))
            saved.append((name, p))

        # ── ① 출력 시뮬레이션 — 조건을 넣고 실행한 화면
        # 결과 칸은 늘어나는 칸이라 창이 높으면 아래가 텅 빈다. 장표에 넣을
        # 그림이므로 결과 줄 수에 맞춰 창을 낮춰 잡는다(왼쪽 입력 열은
        # 스크롤 영역이라 줄어들어도 잘리지 않는다).
        tabs.setCurrentIndex(3)
        pump()
        win.sim_cit.setValue(SIM["cit"])
        win.sim_press.setValue(SIM["press"])
        win._on_simulate()
        pump()
        win.resize(w_, 560)
        pump()
        grab(tabs.widget(3), "tool_sim")
        win.resize(w_, h_)
        pump()

        # ── ② 모델 선정 — 후보 7가지를 실제로 겨룬 교차검증 표
        tabs.setCurrentIndex(5)
        pump()
        win._on_select()
        pump(8)
        grab(win.sel_loocv, "tool_loocv")
        grab(tabs.widget(5), "tool_select")

        QtWidgets.QApplication.quit()

    QtWidgets.QApplication.exec = lambda *_: (shoot(), 0)[1]
    A.main([])
    for name, p in saved:
        print(f"  {name:12s}  {p}  ({p.stat().st_size // 1024} KB)")
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
