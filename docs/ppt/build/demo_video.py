#!/usr/bin/env python3
"""Tool 시연 동영상 — 실물 도구를 오프스크린으로 몰아 프레임을 만들고 ffmpeg 로 잇는다.

    python3 docs/ppt/build/demo_video.py --tool-root <tool-v2 체크아웃>/tool \
            --out docs/ppt/assets/시연.mp4 [--until 1] [--fps 25]

무엇을 하는가
  화면이 없는 환경이므로 Qt 오프스크린으로 도구를 띄우고, 위젯을 코드로
  조작하면서 창을 한 장씩 잡아 1920×1080 캔버스에 앉힌다. 캔버스에는
  단계 표시(위) · 각주 띠(아래) · 콜아웃 · 커서를 그려 넣는다. 프레임은
  파일로 쌓지 않고 ffmpeg 파이프로 곧장 흘린다(디스크가 넉넉하지 않다).

왜 이렇게 만드는가
  사람이 마우스를 움직이는 실제 녹화가 아니다. 대신 **표에 찍히는 숫자와
  곡선은 도구가 실제로 계산한 것**이다. 시드 데이터로 돌리므로 RiMS 취득만
  Mock 이고 계산 경로는 실물과 같다. 커서·클릭 파동은 그려 넣는다.

콘티 — docs/ppt/시연콘티.txt (4분 32초 · 6개 탭)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# ── 화면 규격 ────────────────────────────────────────────────────────────
CW, CH = 1920, 1080                 # 캔버스
LOG_W, LOG_H = 1340, 800            # 도구 창(논리 픽셀). QT_SCALE_FACTOR=2 로 잡는다
WIN_W = 1574                         # 캔버스에 앉히는 창 크기
WIN_H = round(WIN_W * LOG_H / LOG_W)          # 940
WIN_X, WIN_Y = (CW - WIN_W) // 2, 52
S = WIN_W / LOG_W                             # 논리 → 캔버스 배율 1.1746
TOP_H = 48
FOOT_Y = WIN_Y + WIN_H + 12                   # 각주 띠 시작

C = {
    "ground": "#FFFFFF", "panel": "#F7F9FB", "rule": "#C9D0D8", "rule2": "#E4E8ED",
    "ink": "#1A1A1A", "body": "#333333", "dim": "#5A5A5A", "dim2": "#6F6F6F",
    "brass": "#EA002C", "brassT": "#C80025", "brassS": "#FDEBEE",
}
FONT = "NanumBarunGothic"
FONT_MONO = "NanumGothicCoding"

SEED_DATE = "2026-08-26"            # 시연에서 산정할 회차 (장표 6장과 같은 날짜)
STAGES = ["공급가능용량 산정", "온도 구간별 보정값 현황", "Test 결과 List-up",
          "출력 시뮬레이션", "출력곡선 비교", "모델 선정"]
CIRCLED = "①②③④⑤⑥"


class _Cut(Exception):
    """--limit 로 앞부분만 뽑을 때 타임라인을 끊는다."""


# ── 캔버스 ───────────────────────────────────────────────────────────────
class Video:
    """프레임을 만들어 ffmpeg 에 흘린다.

    창 그림은 캐시한다 — 커서만 움직이는 구간에서 창을 다시 잡으면 전체
    렌더 시간이 서너 배로 늘어난다. 위젯을 건드린 뒤에는 invalidate().
    """

    def __init__(self, win, out: Path, fps: int, dry: bool = False):
        from PySide6 import QtCore, QtGui
        self.Qt, self.QtGui, self.QtCore = QtCore.Qt, QtGui, QtCore
        self.win = win
        self.fps = fps
        self.t = 0.0                       # 경과 초
        self.total = 272.0                 # 각주 띠 오른쪽에 찍는 총 길이
        self.stage = 0
        self.note_text = ""
        self.callouts: list = []
        self.cur = (CW // 2, CH // 2)
        self.flash = None                  # (x, y, 0..1)
        self.cover = None                  # 표지·마무리 — 창을 덮고 글자만
        self.show_cursor = True
        self._cache = None
        self.dry = dry
        self.limit = 1e9
        self.frames = 0
        self.proc = None
        if not dry:
            out.parent.mkdir(parents=True, exist_ok=True)
            self.proc = subprocess.Popen(
                ["ffmpeg", "-y", "-loglevel", "error",
                 "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{CW}x{CH}",
                 "-r", str(fps), "-i", "-",
                 "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                 "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)],
                stdin=subprocess.PIPE)

    # ── 상태 ────────────────────────────────────────────────────────────
    def invalidate(self):
        self._cache = None

    def set_stage(self, n: int):
        if self.dry:
            print("  %6.1fs 까지  →  다음 단계 %s" % (self.t, CIRCLED[n]))
        self.stage = n
        self.callouts = []

    def note(self, text: str):
        self.note_text = text

    def callout(self, target, label: str, side: str = "right"):
        """target: 위젯 또는 (x, y, w, h) 논리 좌표. 캔버스 좌표로 바꿔 담는다."""
        self.callouts.append((self._rect(target), label, side))

    def clear_callouts(self):
        self.callouts = []

    # ── 좌표 ────────────────────────────────────────────────────────────
    def _rect(self, target):
        from PySide6 import QtCore
        if isinstance(target, (tuple, list)):
            x, y, w, h = target
        else:
            p = target.mapTo(self.win, QtCore.QPoint(0, 0))
            x, y, w, h = p.x(), p.y(), target.width(), target.height()
        return QtCore.QRectF(WIN_X + x * S, WIN_Y + y * S, w * S, h * S)

    def cell(self, table, item):
        """표의 한 칸 — 위젯이 아니므로 뷰포트 좌표를 창 좌표로 옮겨 준다."""
        from PySide6 import QtCore
        r = table.visualItemRect(item)
        off = table.viewport().mapTo(self.win, QtCore.QPoint(0, 0))
        return (off.x() + r.x(), off.y() + r.y(), r.width(), r.height())

    def center(self, target):
        r = self._rect(target)
        return (r.center().x(), r.center().y())

    def left_of(self, target, dx: float = 18):
        """컨트롤 왼쪽 안쪽 — 입력칸을 누르는 자리."""
        r = self._rect(target)
        return (r.left() + dx, r.center().y())

    # ── 창 그림 ─────────────────────────────────────────────────────────
    def _window_image(self):
        if self._cache is None:
            g = self.win.grab().toImage()
            self._cache = g.scaled(
                WIN_W, WIN_H, self.Qt.AspectRatioMode.IgnoreAspectRatio,
                self.Qt.TransformationMode.SmoothTransformation)
            # 원본 grab 은 devicePixelRatio 2 다. 그대로 두면 drawImage 가
            # 절반 크기로 앉혀 창이 화면의 1/4 만 채운다.
            self._cache.setDevicePixelRatio(1.0)
        return self._cache

    # ── 합성 ────────────────────────────────────────────────────────────
    def _font(self, px: float, bold=False, mono=False):
        f = self.QtGui.QFont(FONT_MONO if mono else FONT)
        f.setPixelSize(round(px))
        f.setBold(bold)
        return f

    def _compose(self):
        QtGui, QtCore, Qt = self.QtGui, self.QtCore, self.Qt
        img = QtGui.QImage(CW, CH, QtGui.QImage.Format.Format_ARGB32)
        img.fill(QtGui.QColor(C["panel"]))
        p = QtGui.QPainter(img)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing)

        # 머리 — 제목과 단계 표시
        p.setPen(QtGui.QColor(C["ink"]))
        p.setFont(self._font(22, bold=True))
        p.drawText(QtCore.QRectF(40, 0, 900, TOP_H), Qt.AlignmentFlag.AlignVCenter,
                   "위례 공급가능용량 입찰 산정 Tool  ·  시연")
        x = CW - 40
        for i in range(len(STAGES) - 1, -1, -1):
            on = (i == self.stage)
            p.setFont(self._font(19, bold=on))
            label = CIRCLED[i] + (" " + STAGES[i] if on else "")
            w = p.fontMetrics().horizontalAdvance(label)
            p.setPen(QtGui.QColor(C["brass"] if on else C["rule"]))
            p.drawText(QtCore.QRectF(x - w, 0, w, TOP_H),
                       Qt.AlignmentFlag.AlignVCenter, label)
            x -= w + 14

        # 창
        p.drawImage(WIN_X, WIN_Y, self._window_image())
        p.setPen(QtGui.QPen(QtGui.QColor(C["rule"]), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QtCore.QRectF(WIN_X - 0.5, WIN_Y - 0.5, WIN_W + 1, WIN_H + 1))

        # 표지·마무리 — 창을 흰 면으로 덮고 글자만 앉힌다
        if self.cover is not None:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QtGui.QColor("#FFFFFF"))
            p.drawRect(QtCore.QRectF(WIN_X, WIN_Y, WIN_W, WIN_H))
            lines, fade = self.cover
            y = WIN_Y + WIN_H / 2 - len(lines) * 44
            for txt, px, bold, col in lines:
                c = QtGui.QColor(col)
                c.setAlphaF(fade)
                p.setPen(c)
                p.setFont(self._font(px, bold=bold))
                h = px * 1.7
                p.drawText(QtCore.QRectF(WIN_X, y, WIN_W, h),
                           Qt.AlignmentFlag.AlignCenter, txt)
                y += h + 10

        # 콜아웃 — 테두리 + 라벨 알약
        for rect, label, side in self.callouts:
            p.setPen(QtGui.QPen(QtGui.QColor(C["brass"]), 2.4))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect.adjusted(-4, -4, 4, 4), 5, 5)
            if not label:
                continue
            p.setFont(self._font(19, bold=True))
            tw = p.fontMetrics().horizontalAdvance(label) + 26
            th = 34
            if side == "right":
                lx, ly = rect.right() + 16, rect.center().y() - th / 2
                if lx + tw > CW - 12:
                    lx, side = rect.left() - 16 - tw, "left"
            elif side == "left":
                lx, ly = rect.left() - 16 - tw, rect.center().y() - th / 2
            elif side == "above":
                lx, ly = rect.center().x() - tw / 2, rect.top() - 16 - th
            else:
                lx, ly = rect.center().x() - tw / 2, rect.bottom() + 16
            lx = max(12, min(lx, CW - tw - 12))
            ly = max(TOP_H + 4, min(ly, CH - th - 12))
            chip = QtCore.QRectF(lx, ly, tw, th)
            # 이음선
            p.setPen(QtGui.QPen(QtGui.QColor(C["brass"]), 1.6))
            p.drawLine(chip.center(), rect.center())
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QtGui.QColor(C["brass"]))
            p.drawRoundedRect(chip, 17, 17)
            p.setPen(QtGui.QColor("#FFFFFF"))
            p.drawText(chip, Qt.AlignmentFlag.AlignCenter, label)

        # 커서 — 화살표
        cx, cy = self.cur
        if not self.show_cursor:
            cx, cy = -999, -999
        if self.flash is not None and self.show_cursor:
            fx, fy, k = self.flash
            r = 14 + 34 * k
            col = QtGui.QColor(C["brass"])
            col.setAlphaF(max(0.0, 0.55 * (1 - k)))
            p.setPen(QtGui.QPen(col, 3))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QtCore.QPointF(fx, fy), r, r)
        arrow = QtGui.QPolygonF([QtCore.QPointF(cx, cy),
                                 QtCore.QPointF(cx, cy + 25),
                                 QtCore.QPointF(cx + 6.5, cy + 18.5),
                                 QtCore.QPointF(cx + 11, cy + 27),
                                 QtCore.QPointF(cx + 15.5, cy + 24.5),
                                 QtCore.QPointF(cx + 11, cy + 16),
                                 QtCore.QPointF(cx + 19, cy + 15)])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QColor(0, 0, 0, 60))
        p.drawPolygon(arrow.translated(2, 2))
        p.setPen(QtGui.QPen(QtGui.QColor(C["ink"]), 1.6))
        p.setBrush(QtGui.QColor("#FFFFFF"))
        p.drawPolygon(arrow)

        # 각주 띠
        p.setPen(QtGui.QPen(QtGui.QColor(C["rule"]), 1))
        p.drawLine(QtCore.QPointF(WIN_X, FOOT_Y), QtCore.QPointF(WIN_X + WIN_W, FOOT_Y))
        if self.note_text:
            p.setFont(self._font(26, bold=True))
            p.setPen(QtGui.QColor(C["brass"]))
            p.drawText(QtCore.QRectF(WIN_X, FOOT_Y + 8, 30, 40),
                       Qt.AlignmentFlag.AlignVCenter, "▸")
            p.setPen(QtGui.QColor(C["ink"]))
            p.setFont(self._font(25))
            p.drawText(QtCore.QRectF(WIN_X + 30, FOOT_Y + 8, WIN_W - 240, 40),
                       Qt.AlignmentFlag.AlignVCenter, self.note_text)
        p.setFont(self._font(20, mono=True))
        p.setPen(QtGui.QColor(C["dim2"]))
        p.drawText(QtCore.QRectF(WIN_X + WIN_W - 200, FOOT_Y + 8, 200, 40),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                   "%d:%02d / %d:%02d" % (int(self.t) // 60, int(self.t) % 60,
                                          int(self.total) // 60, int(self.total) % 60))
        p.end()
        return img

    # ── 출력 ────────────────────────────────────────────────────────────
    def _write(self, img):
        self.frames += 1
        self.t = self.frames / self.fps
        if self.t > self.limit:
            raise _Cut()
        if self.dry:
            return
        b = img.constBits()
        self.proc.stdin.write(bytes(b)[: CW * CH * 4])

    def hold(self, sec: float):
        """정지 — 한 장 합성해 같은 프레임을 반복한다."""
        n = max(1, round(sec * self.fps))
        img = self._compose()
        raw = bytes(img.constBits())[: CW * CH * 4] if not self.dry else b""
        for _ in range(n):
            self.frames += 1
            self.t = self.frames / self.fps
            if not self.dry:
                self.proc.stdin.write(raw)
            if self.t > self.limit:
                raise _Cut()

    def anim(self, sec: float, step=None):
        """동작 — 매 프레임 step(k) 를 부르고 합성한다. k 는 0→1."""
        n = max(1, round(sec * self.fps))
        for i in range(n):
            k = (i + 1) / n
            if step is not None:
                step(k)
            self._write(self._compose())

    # ── 동작 도우미 ─────────────────────────────────────────────────────
    def move_to(self, target, sec: float = 0.55, dx: float = 18):
        x0, y0 = self.cur
        x1, y1 = self.left_of(target, dx) if not isinstance(target, tuple) else target

        def step(k):
            e = k * k * (3 - 2 * k)                    # ease in-out
            self.cur = (x0 + (x1 - x0) * e, y0 + (y1 - y0) * e)
        self.anim(sec, step)

    def click(self, sec: float = 0.4, act=None):
        """클릭 파동. act 가 있으면 파동 한가운데에서 실행한다."""
        fx, fy = self.cur
        done = [False]

        def step(k):
            self.flash = (fx, fy, k)
            if not done[0] and k >= 0.45 and act is not None:
                act()
                self.invalidate()
                done[0] = True
        self.anim(sec, step)
        self.flash = None

    def type_text(self, edit, text: str, sec: float = 1.2):
        edit.setFocus()
        edit.clear()
        self.invalidate()
        n = len(text)

        def step(k):
            want = max(1, round(k * n))
            if len(edit.text()) != want:
                edit.setText(text[:want])
                self.invalidate()
        self.anim(sec, step)

    def spin_to(self, spin, value: float, sec: float = 0.8):
        v0 = spin.value()

        def step(k):
            spin.setValue(v0 + (value - v0) * k)
            self.invalidate()
        self.anim(sec, step)

    def scroll(self, table, frm: float, to: float, sec: float = 2.0):
        bar = table.verticalScrollBar()

        def step(k):
            bar.setValue(round(frm + (to - frm) * k))
            self.invalidate()
        self.anim(sec, step)

    def close(self):
        if self.proc is not None:
            self.proc.stdin.close()
            self.proc.wait()


# ── 도구 띄우기 ──────────────────────────────────────────────────────────
def make_forecast(path: Path, date: str) -> Path:
    """윈드파인더(엑셀3-1) 형식 예보 파일 — 시연에서 실제로 올려 쓴다.

    도구는 D+2~D+6 중위 대기압의 평균에서 8 mbar 를 뺀 값을 입찰 적용
    대기압으로 쓴다(엑셀3 '온도 Profile'!M2 와 같은 식). 8월 말 성남
    기준으로 1008~1012 mbar 를 넣었다 — 적용 대기압이 1002 mbar 가 된다.
    파일이 없으면 도구는 ISO 표준 1013 을 쓴다(장표 6장 캡처가 그 경우다).
    """
    from datetime import date as D, timedelta
    from openpyxl import Workbook
    y, m, d = (int(v) for v in date.split("-"))
    d0 = D(y, m, d)
    wb = Workbook()
    ws = wb.active
    ws["A1"] = f"{date} 18:09:12"
    ws["A2"] = "Update time :"
    ws["B2"] = "17:00"
    times = [0, 3, 6, 9, 12, 15, 18, 21]
    ws["A5"] = "Pressure"
    for j, t in enumerate(times):
        ws.cell(row=6, column=2 + j, value=t)
    ws.cell(row=6, column=10, value="중위")
    ws.cell(row=6, column=11, value="최소")
    WD = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    med = [1011, 1010, 1009, 1010, 1011, 1010, 1010]
    for i in range(7):
        dd = d0 + timedelta(days=i)
        r = 7 + i
        ws.cell(row=r, column=1, value=f"{WD[dd.weekday()]}, {dd.month}월 {dd.day}일")
        for j, t in enumerate(times):
            ws.cell(row=r, column=2 + j, value=med[i])
        ws.cell(row=r, column=10, value=med[i])
        ws.cell(row=r, column=11, value=med[i] - 1)
    ws["A19"] = "Tempereture"
    for j, t in enumerate(times):
        ws.cell(row=20, column=2 + j, value=t)
    ws.cell(row=20, column=10, value="중위")
    ws.cell(row=20, column=11, value="취약")
    for i, tm in enumerate([31, 32, 30, 31, 33, 32, 30]):
        dd = d0 + timedelta(days=i)
        ws.cell(row=21 + i, column=1,
                value=f"{WD[dd.weekday()]}, {dd.month}월 {dd.day}일")
        ws.cell(row=21 + i, column=10, value=tm)
    wb.save(path)
    return path


def boot(tool_root: Path):
    """오프스크린으로 도구를 띄우고 (앱, 창, 탭, app모듈) 를 돌려준다."""
    sys.path.insert(0, str(tool_root))
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ["QT_SCALE_FACTOR"] = "2"
    tmp = Path(tempfile.mkdtemp(prefix="wirye_demo_"))
    os.environ["WIRYE_DB_PATH"] = str(tmp / "demo.db")

    from PySide6 import QtWidgets
    from wirye_capacity.ui import app as A

    # 사람이 없는 실행이므로 물어보는 창은 전부 지나간다.
    _Y = QtWidgets.QMessageBox.StandardButton.Yes
    _OK = QtWidgets.QMessageBox.StandardButton.Ok
    QtWidgets.QMessageBox.question = staticmethod(lambda *a, **k: _Y)
    for nm in ("information", "warning", "critical"):
        setattr(QtWidgets.QMessageBox, nm, staticmethod(lambda *a, **k: _OK))
    QtWidgets.QMessageBox.exec = lambda _s: 0
    QtWidgets.QDialog.exec = lambda _s: 0
    return A, tmp


def prepare(win, A, tmp: Path):
    """시연용 상태 만들기 — 누적 39건(시연 날짜 회차를 빼 둔다) + Mock 취득.

    시연 ①-7 에서 '누적에 반영' 을 체크하고 산정하면 그 회차가 실제로
    한 줄 늘어나야 한다(③-2 와 이어지는 장면이다). 이미 40건인 상태로
    돌리면 '중복 — 건너뜀' 이 되어 아무 일도 일어나지 않는다.
    """
    from wirye_capacity import constants as _C
    from wirye_capacity.rims import MockRimsConnector
    from wirye_capacity.rims.base import AcquiredTest
    recs = json.loads(Path(_C.resource("data", "measurements_seed.json"))
                      .read_text(encoding="utf-8"))
    by = {r["date"]: AcquiredTest(
        date=r["date"], cit=r["cit"], pressure=r["press"], cc_meas=r["cc_meas"],
        rh=r.get("rh"), cp_meas=r.get("cp_meas"), cp_design=r.get("cp_design"),
        season=r.get("season")) for r in recs if r.get("date")}
    win._connector = lambda: MockRimsConnector(by)
    win.store.delete_by_date(SEED_DATE)
    from PySide6 import QtWidgets
    for w in win.findChildren(QtWidgets.QWidget):
        if w.objectName() == "banner":
            w.hide()
    try:
        win.statusBar().showMessage(f"누적 {win.store.count()}건")
    except Exception:                                          # noqa: BLE001
        pass
    fc = make_forecast(tmp / f"{SEED_DATE}_windfinder.xlsx", SEED_DATE)
    os.chdir(tmp)
    return fc


def find_button(win, text: str):
    from PySide6 import QtWidgets
    for b in win.findChildren(QtWidgets.QPushButton):
        if b.text().strip() == text:
            return b
    raise LookupError(text)


# ── 콘티 ─────────────────────────────────────────────────────────────────
def run_select_with_frames(V, win, A, target_sec: float):
    """모델 선정을 실제로 돌리면서 진행 막대를 프레임으로 남긴다.

    _sel.run 이 회차마다 progress 를 부르므로 그 자리에서 한 장씩 잡는다.
    계산은 진짜로 돈다 — 진행 막대가 도는 동안 실제로 7가지를 채점한다.
    """
    budget = [round(target_sec * V.fps)]
    orig = A._sel.run

    def patched(*a, progress=None, **k):
        state = {"i": 0}

        def prog(done, total, label):
            if progress is not None:
                progress(done, total, label)
            state["i"] += 1
            if budget[0] > 0 and state["i"] % 2 == 0:
                V.invalidate()
                V._write(V._compose())
                budget[0] -= 1
        return orig(*a, progress=prog, **k)

    A._sel.run = patched
    try:
        win._on_select()
    finally:
        A._sel.run = orig
    V.invalidate()
    if budget[0] > 0:
        V.hold(budget[0] / V.fps)


def timeline(V, win, tabs, A, forecast: Path):
    from PySide6 import QtWidgets
    xl_btn = find_button(win, "엑셀로 저장")
    find_btn = find_button(win, "찾아보기")
    BR, INK, DIM = C["brass"], C["ink"], C["dim"]

    # ══ 표지 6초 ═══════════════════════════════════════════════════════
    V.show_cursor = False
    V.note("")
    V.cover = ([("위례 공급가능용량 입찰 산정 Tool", 54, True, INK),
                ("", 10, False, INK),
                ("엑셀 4개 · 한 회 1시간   →   도구 하나 · 5분", 30, False, BR)], 1.0)
    V.anim(1.2, lambda k: setattr(V, "cover", (V.cover[0], min(1.0, k * 1.6))))
    V.hold(3.6)
    V.anim(1.2, lambda k: setattr(V, "cover", (V.cover[0], max(0.0, 1 - k * 1.6))))
    V.cover = None
    V.show_cursor = True

    # ══ ① 공급가능용량 산정 84초 ═══════════════════════════════════════
    V.set_stage(0)
    tabs.setCurrentIndex(0)
    V.invalidate()
    V.cur = (V._rect(win.date_in).left() + 200, V._rect(win.date_in).top() - 60)

    # 1-1 도입 6초
    V.note("시험 한 회를 처음부터 끝까지 돌려 봅니다")
    V.callout(win.date_in.parentWidget().parentWidget(), "", "right")
    V.hold(6.0)
    V.clear_callouts()

    # 1-2 날짜·시각 14초
    V.note("넣는 값은 날짜와 시각 둘뿐입니다")
    V.move_to(win.date_in, 0.8)
    V.click(0.4)
    V.type_text(win.date_in, SEED_DATE, 2.6)
    V.hold(1.6)
    V.move_to(win.start_in, 0.7)
    V.click(0.4)
    V.type_text(win.start_in, "17:00", 1.6)
    V.callout(win.start_in, "1시간 평균 창", "right")
    V.hold(1.4)
    V.clear_callouts()
    V.hold(3.2)

    # 1-3 습도 14초
    V.note("습도는 60% 로 두거나 RiMS 값을 그대로 받습니다")
    V.move_to(win.rh_auto, 0.8, dx=12)
    V.callout(win.rh_in, "60% 고정 ↔ RiMS 취득값", "right")
    V.click(0.5, lambda: win.rh_auto.setChecked(False))
    V.hold(3.0)
    V.click(0.5, lambda: win.rh_auto.setChecked(True))
    V.hold(2.8)
    V.clear_callouts()
    V.hold(5.9)

    # 1-4 IGV 7초
    V.note("이 조작을 안 한 날은 출력이 낮게 나옵니다")
    V.move_to(win.igv_chk, 0.7, dx=12)
    V.callout(win.igv_chk, "출력을 끝까지 올린 시험인지", "right")
    V.click(0.5, lambda: win.igv_chk.setChecked(False))
    V.hold(1.6)
    V.click(0.5, lambda: win.igv_chk.setChecked(True))
    V.hold(1.4)
    V.clear_callouts()
    V.hold(1.8)

    # 1-5 대기압 예보 업로드 13초
    V.note("윈드파인더에서 받은 예보 파일을 올립니다")
    V.move_to(find_btn, 0.9, dx=40)
    V.callout(win.forecast_in["edit"], "대기압 예보 엑셀", "above")
    V.click(0.5, lambda: win.forecast_in["edit"].setText(forecast.name))
    V.hold(3.2)
    V.clear_callouts()
    V.note("예보 3~7일차 중위 평균에서 8 mbar 를 뺀 값을 씁니다")
    V.hold(9.0)

    # 1-6 보정 방법 8초
    V.note("어떤 회귀 모델로 보정할지 고릅니다")
    V.move_to(win.method_cb, 0.8, dx=30)
    V.callout(win.method_cb, "후보 7가지", "left")
    V.click(0.4)

    def cycle(k):
        i = min(6, int(k * 7))
        if win.method_cb.currentIndex() != i:
            win.method_cb.setCurrentIndex(i)
            V.invalidate()
    V.anim(4.2, cycle)
    win.method_cb.setCurrentIndex(0)
    V.invalidate()
    V.hold(1.4)
    V.clear_callouts()
    V.hold(1.2)

    # 1-7 누적 반영 7초
    V.note("체크하면 이 회차가 실적에 더해집니다")
    V.move_to(win.accum_chk, 0.8, dx=12)
    V.callout(win.accum_chk, "체크해야 실적으로 쌓입니다", "left")
    V.click(0.5, lambda: win.accum_chk.setChecked(True))
    V.hold(3.4)
    V.clear_callouts()
    V.hold(1.3)

    # 1-8 산정 실행 9초 ★
    V.note("온도 61구간이 한 번에 채워집니다")
    V.move_to(win.run_btn, 0.9, dx=300)
    V.click(0.6, win._on_run)
    V.hold(1.2)
    V.callout(win.profile_tbl, "−20 ~ 40℃ · 61줄", "above")
    V.hold(1.0)
    V.clear_callouts()
    V.scroll(win.profile_tbl, 0, win.profile_tbl.verticalScrollBar().maximum(), 6.0)
    V.hold(1.4)
    V.scroll(win.profile_tbl, win.profile_tbl.verticalScrollBar().maximum(), 0, 1.6)
    V.hold(1.0)

    # 1-9 엑셀로 저장 6초
    V.note("지금 쓰는 입찰 엑셀 양식 그대로 나옵니다")
    V.move_to(xl_btn, 0.9, dx=40)
    V.callout(xl_btn, "입찰에 쓰는 그 엑셀", "left")
    V.click(0.5)
    V.hold(3.2)
    V.clear_callouts()

    # ══ ② 온도 구간별 보정값 현황 18초 ═════════════════════════════════
    V.set_stage(1)
    V.note("온도 구간마다 지금 얼마를 더하고 있는지")
    V.move_to((V._rect(tabs)[0] if False else (WIN_X + 240, WIN_Y + 100)), 0.8)
    V.click(0.5, lambda: tabs.setCurrentIndex(1))
    V.hold(6.7)
    V.note("실적이 적은 구간은 도구가 표시해 줍니다")
    V.callout(win.status_tbl, "시험이 적은 구간은 보수적으로", "above")
    V.hold(3.0)
    V.clear_callouts()
    V.hold(7.0)

    # ══ ③ Test 결과 List-up 45초 ═══════════════════════════════════════
    V.set_stage(2)
    V.note("지금까지 쌓인 시험 실적 전부입니다")
    V.move_to((WIN_X + 430, WIN_Y + 100), 0.8)
    V.click(0.5, lambda: tabs.setCurrentIndex(2))
    V.hold(1.4)
    V.scroll(win.list_tbl, 0, win.list_tbl.verticalScrollBar().maximum(), 8.0)

    # 3-2 방금 저장한 회차 9초
    V.note("앞에서 체크한 회차가 여기 쌓였습니다")
    rows = win.list_tbl.rowCount()
    hit = 0
    for r in range(rows):
        it = win.list_tbl.item(r, 0)
        if it is not None and it.text().strip() == SEED_DATE:
            hit = r
            break
    win.list_tbl.selectRow(hit)
    win.list_tbl.scrollToItem(win.list_tbl.item(hit, 0))
    V.invalidate()
    V.callout(win.list_tbl, "방금 저장한 회차", "above")
    V.hold(4.0)
    V.clear_callouts()
    V.hold(6.5)

    # 3-3 셀 편집 11초
    V.note("RiMS 값이 이상할 때 손으로 고칠 수 있습니다")
    # 셀을 고치면 앱이 파생값을 다시 계산하며 표를 새로 그린다 — 그때
    # QTableWidgetItem 이 지워지므로 참조를 들고 있지 말고 매번 다시 찾는다.
    col = next(i for i, c in enumerate(win.LIST_COLS) if "CC" in str(c))
    box = V.cell(win.list_tbl, win.list_tbl.item(hit, col))
    old = win.list_tbl.item(hit, col).text()
    new = "%.2f" % (float(old.replace(",", "")) + 1.5)
    V.callout(box, "센서가 이상하면 여기서", "left")
    V.move_to(tuple(V._rect(box).center().toTuple()), 0.9)
    V.click(0.5)
    V.hold(1.4)
    done = [False]

    def do_edit(k):
        if not done[0] and k > 0.4:
            it = win.list_tbl.item(hit, col)
            if it is not None:
                it.setText(new)
            V.invalidate()
            done[0] = True
    V.anim(1.6, do_edit)
    V.hold(3.0)
    V.clear_callouts()
    V.hold(2.1)

    # 3-4 삭제 표시 9초
    V.note("잘못 쌓인 회차는 골라서 삭제 표시합니다")
    V.move_to(win.del_btn, 0.9, dx=40)
    V.callout(win.del_btn, "행을 골라 삭제 표시", "left")
    V.click(0.5, lambda: (win.list_tbl.selectRow(hit), win._on_mark_delete()))
    V.hold(4.0)
    V.clear_callouts()
    V.hold(2.6)

    # 3-5 저장 7초 — 되돌리기로 취소하고 넘어간다(실적을 지우지 않는다)
    V.note("저장을 눌러야 반영됩니다 — 그 전에는 되돌릴 수 있습니다")
    V.move_to(win.undo_btn, 0.8, dx=40)
    V.callout(win.save_btn, "저장해야 DB 에 남습니다", "left")
    V.click(0.5, win._on_undo_delete)
    V.hold(3.2)
    V.clear_callouts()
    V.hold(1.5)

    # ══ ④ 출력 시뮬레이션 40초 ═════════════════════════════════════════
    V.set_stage(3)
    V.note("시험 전에 그날 조건을 넣어 봅니다")
    V.move_to((WIN_X + 660, WIN_Y + 100), 0.9)
    V.click(0.5, lambda: tabs.setCurrentIndex(3))
    V.hold(0.8)
    V.move_to(win.sim_cit, 0.7, dx=30)
    V.click(0.4)
    V.spin_to(win.sim_cit, 30.0, 1.6)
    V.move_to(win.sim_press, 0.7, dx=30)
    V.click(0.4)
    V.spin_to(win.sim_press, 1013.0, 1.2)
    V.callout(win.sim_w, "IGV turn-up 보정", "right")
    V.hold(2.4)
    V.clear_callouts()
    V.hold(3.4)

    # 4-2 실측 CC 9초
    V.note("시험이 끝난 뒤 실측값과 대 볼 수도 있습니다")
    V.move_to(win.sim_meas_use, 0.8, dx=12)
    V.callout(win.sim_meas, "시험 뒤 대조용", "right")
    V.click(0.5, lambda: win.sim_meas_use.setChecked(True))
    V.hold(0.9)
    V.spin_to(win.sim_meas, 401.5, 1.6)
    V.hold(2.6)
    V.clear_callouts()
    V.hold(1.6)

    # 4-3 보정 방법 6초
    V.note("회귀 모델을 바꿔 가며 볼 수 있습니다")
    V.move_to(win.sim_method, 0.8, dx=30)
    V.click(0.4)

    def cyc2(k):
        i = min(6, int(k * 7))
        if win.sim_method.currentIndex() != i:
            win.sim_method.setCurrentIndex(i)
            V.invalidate()
    V.anim(3.4, cyc2)
    win.sim_method.setCurrentIndex(0)
    V.invalidate()
    V.hold(1.4)

    # 4-4 실행 11초 ★
    V.note("시험 전에 그날 신고할 숫자를 미리 봅니다")
    V.move_to(win.sim_btn, 0.9, dx=120)
    V.click(0.6, win._on_simulate)
    V.hold(1.0)
    V.callout(win.sim_big, "예상 입찰값", "below")
    V.hold(3.2)
    V.clear_callouts()
    V.callout(win.sim_out, "이론값 → 보정값 → 신고값", "above")
    V.hold(3.4)
    V.clear_callouts()
    V.hold(3.9)

    # ══ ⑤ 출력곡선 비교 32초 ═══════════════════════════════════════════
    V.set_stage(4)
    V.note("두 선이 벌어진 만큼이 그 온도에서 더하는 값입니다")
    V.move_to((WIN_X + 840, WIN_Y + 100), 0.9)
    V.click(0.5, lambda: tabs.setCurrentIndex(4))
    V.hold(1.2)
    V.callout(win.chart, "이론값(점선) vs 신고값(빨간 선)", "below")
    V.hold(3.4)
    V.clear_callouts()
    V.hold(2.0)

    # 5-2 모델 바꾸기 12초 ★
    V.note("방법마다 곡선의 성격이 다릅니다")
    V.move_to(win.chart_method, 0.8, dx=30)
    V.click(0.4)
    for idx, name in ((0, "GP · RBF"), (5, "커널회귀"), (4, "GP · 지수"), (0, "GP · RBF")):
        win.chart_method.setCurrentIndex(idx)
        V.invalidate()
        V.hold(2.7)

    # 5-3 커서 올리기 12초
    V.note("온도를 짚으면 그 온도의 값이 나옵니다")
    ch = win.chart
    r = V._rect(ch)
    V.callout(ch, "연한 띠 = 90% 범위", "above")
    V.move_to((r.left() + r.width() * 0.12, r.top() + r.height() * 0.78), 0.9)
    V.clear_callouts()

    def hover(k):
        t = -20 + 60 * k
        ch._hover = t
        ch.update()
        V.cur = (r.left() + r.width() * (0.10 + 0.78 * k),
                 r.top() + r.height() * 0.78)
        V.invalidate()
    V.anim(8.6, hover)
    ch._hover = None
    ch.update()
    V.invalidate()
    V.hold(1.5)

    # ══ ⑥ 모델 선정 40초 ══════════════════════════════════════════════
    V.set_stage(5)
    V.note("실적이 늘면 어떤 모델이 나은지 다시 봅니다")
    V.move_to((WIN_X + 1010, WIN_Y + 100), 0.9)
    V.click(0.5, lambda: tabs.setCurrentIndex(5))
    V.hold(1.0)
    V.callout(list(win.sel_chks.values())[0].parentWidget(), "후보 7가지", "left")
    V.hold(3.6)
    V.clear_callouts()
    V.hold(2.0)

    # 6-2 조건 바꾸기 11초
    V.note("검증 조건을 바꿔 가며 확인할 수 있습니다")
    V.move_to(win.sel_frac, 0.8, dx=30)
    V.click(0.4)
    V.callout(win.sel_frac, "따로 떼어 둘 비율", "right")
    V.spin_to(win.sel_frac, 0.0, 1.8)
    V.hold(1.6)
    V.clear_callouts()
    V.move_to(win.sel_crit, 0.8, dx=30)
    V.click(0.4)

    def cyc3(k):
        i = min(win.sel_crit.count() - 1, int(k * win.sel_crit.count()))
        if win.sel_crit.currentIndex() != i:
            win.sel_crit.setCurrentIndex(i)
            V.invalidate()
    V.anim(2.6, cyc3)
    win.sel_crit.setCurrentIndex(0)
    V.invalidate()
    V.hold(1.8)

    # 6-3 후보 고르기 6초
    V.note("겨루게 할 모델을 골라 담습니다")
    cb = list(win.sel_chks.values())[1]
    V.move_to(cb, 0.8, dx=12)
    V.click(0.5, lambda: cb.setChecked(False))
    V.hold(1.5)
    V.click(0.5, lambda: cb.setChecked(True))
    V.hold(2.2)

    # 6-4 실행 10초 ★
    V.note("한 회를 가리고 나머지로 맞혀 보는 채점입니다")
    V.move_to(win.sel_btn, 0.9, dx=300)
    V.cur = V.left_of(win.sel_btn, 300)
    V.click(0.6)
    run_select_with_frames(V, win, A, 8.0)

    # 6-5 결과 5초
    V.note("사람이 고르지 않고 성적이 고릅니다")
    _b = V.cell(win.sel_loocv, win.sel_loocv.item(0, 0))
    V.callout((_b[0], _b[1], win.sel_loocv.viewport().width(), _b[3]),
              "★ 선정 — 성적이 골랐습니다", "below")
    V.hold(8.0)
    V.clear_callouts()

    # ══ 마무리 7초 ═════════════════════════════════════════════════════
    if V.dry:
        print("  %6.1fs 까지  →  마무리" % V.t)
    V.show_cursor = False
    V.note("")
    V.cover = ([("엑셀 4개 · 1시간   →   도구 하나 · 5분", 34, True, INK),
                ("틀리는 폭  3.9 MW   →   1.3 MW", 34, True, INK),
                ("", 12, False, INK),
                ("한 번 만들고 끝나지 않습니다", 28, False, BR)], 0.0)
    V.anim(1.2, lambda k: setattr(V, "cover", (V.cover[0], min(1.0, k * 1.6))))
    V.hold(4.6)
    V.anim(1.2, lambda k: setattr(V, "cover", (V.cover[0], max(0.0, 1 - k * 1.4))))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool-root", required=True, help="tool-v2 체크아웃의 tool 폴더")
    ap.add_argument("--out", default=str(ROOT / "docs" / "ppt" / "assets" / "시연.mp4"))
    ap.add_argument("--fps", type=int, default=25)
    ap.add_argument("--dry", action="store_true", help="프레임 수·길이만 세고 끝낸다")
    ap.add_argument("--limit", type=float, default=0.0,
                    help="이 초까지만 뽑는다 — 눈으로 확인할 때 쓴다")
    a = ap.parse_args()

    A, tmp = boot(Path(a.tool_root).resolve())
    from PySide6 import QtWidgets

    state = {}

    def go():
        app = QtWidgets.QApplication.instance()
        win = next(w for w in app.topLevelWidgets()
                   if isinstance(w, QtWidgets.QMainWindow))
        win.resize(LOG_W, LOG_H)
        tabs = win.findChild(QtWidgets.QTabWidget)
        for _ in range(6):
            app.processEvents()
        forecast = prepare(win, A, tmp)
        for _ in range(6):
            app.processEvents()
        V = Video(win, Path(a.out), a.fps, dry=a.dry)
        if a.limit:
            V.limit = a.limit
        try:
            timeline(V, win, tabs, A, forecast)
        except _Cut:
            pass
        finally:
            V.close()
        state["n"] = V.frames
        app.quit()

    QtWidgets.QApplication.exec = lambda *_: (go(), 0)[1]
    A.main([])
    n = state.get("n", 0)
    print("프레임 %d · 길이 %d:%05.2f · %s"
          % (n, n // a.fps // 60, (n / a.fps) % 60, a.out))
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
