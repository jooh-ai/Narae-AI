#!/usr/bin/env python3
"""Tool 시연 영상 만들기 — 화면 없이 도구를 돌려 MP4 로 굽는다.

    python3 docs/ppt/build/ui_video.py --tool-root <v2 테마가 있는 체크아웃>/tool

발표장에서 실물 시연이 막힐 때(사내망·프로젝터·백신) 대신 틀 수 있는 영상이고,
장표에 넣어 반복 재생해도 된다.

만드는 방식 — 진짜 화면 녹화는 아니다(디스플레이가 없다). Qt 오프스크린으로
도구를 띄우고, 시나리오를 단계별로 실행하면서 매 단계의 창을 그대로 잡아
장면(scene)으로 쌓은 뒤 ffmpeg 로 이어 붙인다. 그래서

  · 화면에 보이는 값·표·곡선은 **도구가 실제로 계산한 것**이다.
  · 마우스 커서는 화면에 없으므로 **우리가 그려 넣는다**(클릭 위치 표시).
  · RiMS 취득만 시드 기반 Mock 이다. 사내망에 붙을 수 없어서인데,
    취득 이후의 계산 경로는 실물과 같다.

`tool/scripts/ui_shot.py` 와 같은 수법을 쓴다 — `main()` 이 `app.exec()` 로
이벤트 루프에 들어가는 자리를 우리 녹화 루틴으로 바꿔치기한다.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs" / "ppt" / "assets"
FPS = 25
DATE = "2026-08-26"        # 시연에 쓸 회차 (시드에 있는 실제 날짜)


class Rec:
    """장면을 쌓아 두는 통. 같은 그림을 초 단위로 잡아 둔다."""

    def __init__(self, tmp: Path, win, app):
        self.tmp, self.win, self.app, self.n, self.list = tmp, win, app, 0, []

    def hold(self, sec: float, cursor=None, click=False, label="") -> None:
        from PySide6 import QtCore, QtGui
        for _ in range(3):
            self.app.processEvents()
        px = self.win.grab()
        if cursor is not None:
            self._cursor(px, cursor, click)
        self.n += 1
        p = self.tmp / f"f{self.n:04d}.png"
        px.save(str(p))
        self.list.append((p, sec))
        print(f"  {self.n:3d}  {sec:4.1f}s  {label}")

    def _cursor(self, px, pos, click: bool) -> None:
        """마우스 화살표를 그려 넣는다. 없으면 '누가 조작하는' 느낌이 안 난다."""
        from PySide6 import QtCore, QtGui
        p = QtGui.QPainter(px)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        if click:                                   # 클릭 파장
            p.setPen(QtGui.QPen(QtGui.QColor("#EFB13C"), 2))
            p.setBrush(QtCore.Qt.NoBrush)
            for r in (13, 22):
                p.drawEllipse(pos, r, r)
        arrow = QtGui.QPolygonF([QtCore.QPointF(pos.x(), pos.y()),
                                 QtCore.QPointF(pos.x(), pos.y() + 17),
                                 QtCore.QPointF(pos.x() + 4.5, pos.y() + 13),
                                 QtCore.QPointF(pos.x() + 8, pos.y() + 20),
                                 QtCore.QPointF(pos.x() + 11, pos.y() + 18.5),
                                 QtCore.QPointF(pos.x() + 7.5, pos.y() + 11.5),
                                 QtCore.QPointF(pos.x() + 13, pos.y() + 11)])
        p.setPen(QtGui.QPen(QtGui.QColor("#101010"), 1.2))
        p.setBrush(QtGui.QBrush(QtGui.QColor("#FFFFFF")))
        p.drawPolygon(arrow)
        p.end()

    def encode(self, mp4: Path) -> None:
        txt = self.tmp / "list.txt"
        lines = []
        for p, sec in self.list:
            lines.append(f"file '{p.name}'\nduration {sec:.3f}")
        lines.append(f"file '{self.list[-1][0].name}'")     # concat 은 마지막을 한 번 더 적어야 한다
        txt.write_text("\n".join(lines) + "\n", encoding="utf-8")
        ff = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
        subprocess.run(
            [ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(txt),
             "-vf", f"fps={FPS},scale=trunc(iw/2)*2:trunc(ih/2)*2",
             "-c:v", "libx264", "-preset", "slow", "-crf", "20",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(mp4)],
            check=True, cwd=self.tmp)


def center(win, w):
    """위젯의 화면 중앙 좌표 — 커서를 그 위에 얹는다."""
    from PySide6 import QtCore
    r = w.rect()
    return w.mapTo(win, QtCore.QPoint(r.width() // 2, r.height() // 2))


def scenario(win, app, rec) -> None:
    from PySide6 import QtCore, QtWidgets
    tabs = win.findChild(QtWidgets.QTabWidget)

    rec.hold(2.2, label="시작 — 공급가능용량 산정 탭")

    # ① 날짜를 한 글자씩 — '날짜만 넣으면 된다' 가 이 영상의 요점이다
    win.date_in.clear()
    cur = center(win, win.date_in)
    for ch in DATE:
        win.date_in.setText(win.date_in.text() + ch)
        rec.hold(0.09, cursor=cur, label=f"날짜 입력 {win.date_in.text()}" if ch == DATE[-1] else "")
    rec.hold(0.7, cursor=cur, label="날짜 입력 완료")

    # ② 시각
    cur2 = center(win, win.start_in)
    win.start_in.setText("17:00")
    rec.hold(1.0, cursor=cur2, label="시작 시각 17:00")

    # ③ 산정 실행
    btn = next((b for b in win.findChildren(QtWidgets.QPushButton)
                if "산정" in b.text()), None)
    if btn is not None:
        cb = center(win, btn)
        rec.hold(0.6, cursor=cb, label="[공급가능용량 산정] 로 이동")
        rec.hold(0.45, cursor=cb, click=True, label="클릭")
    win.accum_chk.setChecked(False)          # 영상 촬영이 누적을 늘리지 않게
    win._on_run()
    for _ in range(6):
        app.processEvents()
    rec.hold(3.4, label="61개 온도 구간 결과 — 이론 · 보정값 · 현실화")

    # ④ 탭 순회
    for idx, sec, why in ((1, 2.8, "온도 구간별 보정값 현황"),
                          (2, 2.8, "Test 결과 List-up — 누적 40건"),
                          (4, 4.0, "출력곡선 비교 — 이론(점선) vs 실제(주황)")):
        if idx >= tabs.count():
            continue
        bar = tabs.tabBar()
        cur3 = bar.mapTo(win, bar.tabRect(idx).center())
        rec.hold(0.5, cursor=cur3, label=f"[{tabs.tabText(idx)}] 로 이동")
        rec.hold(0.35, cursor=cur3, click=True, label="클릭")
        tabs.setCurrentIndex(idx)
        for _ in range(4):
            app.processEvents()
        rec.hold(sec, label=why)

    tabs.setCurrentIndex(0)
    for _ in range(3):
        app.processEvents()
    rec.hold(1.6, label="처음 화면으로")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool-root", default="", help="v2 테마가 있는 체크아웃의 tool 폴더")
    ap.add_argument("--size", default="1280x860")
    ap.add_argument("--out", default=str(OUT / "tool_demo.mp4"))
    a = ap.parse_args()

    tool = Path(a.tool_root).resolve() if a.tool_root else (ROOT / "tool")
    if not (tool / "wirye_capacity" / "ui" / "theme.py").exists():
        sys.exit(f"v2 테마(ui/theme.py)가 없는 체크아웃입니다: {tool}\n"
                 f"  claude/tool-v2 를 받은 폴더를 --tool-root 로 지정하십시오.")
    sys.path.insert(0, str(tool))
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="wirye_vid_"))
    os.environ["WIRYE_DB_PATH"] = str(tmp / "demo.db")

    from PySide6 import QtWidgets
    from wirye_capacity.ui import app as A

    _Y = QtWidgets.QMessageBox.StandardButton.Yes
    _OK = QtWidgets.QMessageBox.StandardButton.Ok
    QtWidgets.QMessageBox.question = staticmethod(lambda *_a, **_k: _Y)
    QtWidgets.QMessageBox.information = staticmethod(lambda *_a, **_k: _OK)
    QtWidgets.QMessageBox.warning = staticmethod(lambda *_a, **_k: _OK)
    QtWidgets.QMessageBox.critical = staticmethod(lambda *_a, **_k: _OK)
    QtWidgets.QMessageBox.exec = lambda _self: 0
    QtWidgets.QDialog.exec = lambda _self: 0

    mp4 = Path(a.out)

    def record():
        app = QtWidgets.QApplication.instance()
        win = next(w for w in app.topLevelWidgets()
                   if isinstance(w, QtWidgets.QMainWindow))
        w_, h_ = (int(v) for v in a.size.lower().split("x"))
        win.resize(w_, h_)
        for bar in win.findChildren(QtWidgets.QWidget):      # 임시 DB 경로 안내 띠를 감춘다
            if bar.objectName() == "banner":
                bar.hide()
        try:
            win.statusBar().showMessage(f"누적 {win.store.count()}건")
        except Exception:                                     # noqa: BLE001
            pass

        # RiMS 는 사내망이라 여기서 못 붙는다. 취득만 시드로 바꾸고 계산은 그대로.
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

        rec = Rec(tmp, win, app)
        scenario(win, app, rec)
        total = sum(s for _, s in rec.list)
        print(f"\n장면 {rec.n}개 · {total:.1f}초 — 인코딩")
        mp4.parent.mkdir(parents=True, exist_ok=True)
        rec.encode(mp4)
        print(f"완료  {mp4.relative_to(ROOT) if mp4.is_relative_to(ROOT) else mp4}"
              f"  ({mp4.stat().st_size // 1024} KB)")
        QtWidgets.QApplication.quit()

    QtWidgets.QApplication.exec = lambda *_: (record(), 0)[1]
    A.main([])
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
