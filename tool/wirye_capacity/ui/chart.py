"""출력곡선 비교 차트 — 이론값 곡선 vs 보정 후 현실화 곡선.

matplotlib 없이 QPainter 로 직접 그린다(의존성·exe 용량 최소화, 한글은 Qt 폰트 사용).

  상단 패널: 이론 CC(보정 없음) / 현실화 Net(보정 반영) / 마진 적용선
  하단 패널: 온도별 보정값 곡선 + 실측 보정값 점 + 예측구간(GP)

마우스를 올리면 해당 온도의 값을 세로선과 함께 표시한다.
"""
from __future__ import annotations

import math

from PySide6 import QtCore, QtGui, QtWidgets

from .. import constants as C

# 색상 (앱 브랜드와 통일)
C_THEORY = QtGui.QColor("#8b94a4")      # 이론 - 회색
C_REAL = QtGui.QColor("#EA002C")        # 현실화 - 적색
C_MARGIN = QtGui.QColor("#1f9254")      # 마진 적용 - 녹색
C_CORR = QtGui.QColor("#0b6bcb")        # 보정값 - 청색
C_BAND = QtGui.QColor(11, 107, 203, 38)  # 예측구간
C_PT = QtGui.QColor("#10141c")          # 실측점
C_GRID = QtGui.QColor("#e6e9ef")
C_AXIS = QtGui.QColor("#9aa3b2")
C_TEXT = QtGui.QColor("#3a4150")


class CurveChart(QtWidgets.QWidget):
    """이론/현실화/보정값 곡선 비교 위젯.

    set_data(rows, points, sigma_fn=None, margin_fn=None) 로 갱신.
      rows      : profile.build_profile 결과 (temp, cc_theory, cc_real_net, correction)
      points    : [(cit, corr), ...] 실측 보정값 산점
      sigma_fn  : 온도→표준편차 (GP). None 이면 예측구간 미표시
      margin_fn : 온도→마진(MW). None 이면 마진선 미표시
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(430)
        self.setMouseTracking(True)
        self._rows = []
        self._pts = []
        self._sigma = None
        self._margin = None
        self._hover = None                      # 마우스 온도
        self.show_points = True
        self.show_band = True
        self.show_margin = True

    # ── 데이터 ──
    def set_data(self, rows, points, sigma_fn=None, margin_fn=None):
        self._rows = list(rows)
        self._pts = list(points)
        self._sigma = sigma_fn
        self._margin = margin_fn
        self.update()

    def set_toggles(self, *, points=None, band=None, margin=None):
        if points is not None:
            self.show_points = points
        if band is not None:
            self.show_band = band
        if margin is not None:
            self.show_margin = margin
        self.update()

    # ── 마우스 ──
    def mouseMoveEvent(self, e):
        if not self._rows:
            return
        g = self._geom()
        x = e.position().x() if hasattr(e, "position") else e.x()
        if g["px"] <= x <= g["px"] + g["pw"]:
            t0, t1 = self._rows[0].temp, self._rows[-1].temp
            self._hover = t0 + (x - g["px"]) / max(g["pw"], 1) * (t1 - t0)
        else:
            self._hover = None
        self.update()

    def leaveEvent(self, e):
        self._hover = None
        self.update()

    # ── 레이아웃 ──
    def _geom(self):
        """상·하 두 패널. 각 패널 아래 34px(틱+축라벨), 사이 12px 를 확보한다."""
        w, h = self.width(), self.height()
        px, pw = 62, max(w - 62 - 16, 10)
        avail = max(h - 110, 40)                 # 26(위) + 34 + 12 + 34(아래)
        top_h = int(avail * 0.60)
        bot_h = avail - top_h
        return {"px": px, "pw": pw, "ty": 26, "th": max(top_h, 10),
                "by": 26 + top_h + 46, "bh": max(bot_h, 10)}

    @staticmethod
    def _nice_range(lo, hi, ticks=5):
        """축 범위를 보기 좋은 값으로 반올림."""
        if hi - lo < 1e-9:
            lo, hi = lo - 1, hi + 1
        raw = (hi - lo) / ticks
        mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1.0
        step = mag
        for m in (1, 2, 2.5, 5, 10):
            step = mag * m
            if step >= raw:
                break
        lo2 = step * math.floor(lo / step)
        hi2 = step * math.ceil(hi / step)
        return lo2, hi2, step

    def paintEvent(self, _e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.fillRect(self.rect(), QtGui.QColor("#ffffff"))
        if not self._rows:
            p.setPen(C_TEXT)
            p.drawText(self.rect(), QtCore.Qt.AlignCenter,
                       "테스트를 누적하거나 [산정 실행] 후 곡선이 표시됩니다.")
            return

        g = self._geom()
        temps = [r.temp for r in self._rows]
        t0, t1 = temps[0], temps[-1]

        def tx(t):
            return g["px"] + (t - t0) / max(t1 - t0, 1) * g["pw"]

        # ── 상단: 이론 vs 현실화 ──
        # 이론도 현실화와 같은 Net 기준으로 환산 — 두 곡선의 간격이 곧 보정 효과
        th = [self._theory_net(r) for r in self._rows]
        rn = [r.cc_real_net for r in self._rows]
        lo = min(min(th), min(rn))
        hi = max(max(th), max(rn))
        ylo, yhi, ystep = self._nice_range(lo - 4, hi + 4)

        def ty(v):
            return g["ty"] + g["th"] - (v - ylo) / max(yhi - ylo, 1e-9) * g["th"]

        self._axes(p, g, "ty", "th", ylo, yhi, ystep, tx, ty, t0, t1, "출력 (MW)")
        self._series(p, [(tx(r.temp), ty(self._theory_net(r))) for r in self._rows],
                     C_THEORY, dash=True)
        if self.show_margin and self._margin is not None:
            base = [(tx(r.temp), ty(r.cc_real_net + self._margin(r.temp)))
                    for r in self._rows]
            self._series(p, base, C_MARGIN, dash=True, width=1.4)
        self._series(p, [(tx(r.temp), ty(r.cc_real_net)) for r in self._rows],
                     C_REAL, width=2.2)
        items = [(C_THEORY, "이론값 Net (보정 없음)", True),
                 (C_REAL, "현실화 Net (보정 반영 = 입찰값)", False)]
        if self.show_margin and self._margin is not None:
            items.insert(1, (C_MARGIN, "마진 적용 전", True))
        self._legend(p, g["px"] + 8, g["ty"] + 6, items)

        # ── 하단: 보정값 ──
        cs = [r.correction for r in self._rows]
        clo, chi = min(cs), max(cs)
        if self._pts:
            clo = min(clo, min(c for _, c in self._pts))
            chi = max(chi, max(c for _, c in self._pts))
        if self.show_band and self._sigma is not None:
            for r in self._rows:
                s = self._sigma(r.temp)
                if s == s:
                    clo = min(clo, r.correction - 1.645 * s)
                    chi = max(chi, r.correction + 1.645 * s)
        clo, chi, cstep = self._nice_range(clo - 1, chi + 1)

        def cy(v):
            return g["by"] + g["bh"] - (v - clo) / max(chi - clo, 1e-9) * g["bh"]

        self._axes(p, g, "by", "bh", clo, chi, cstep, tx, cy, t0, t1, "보정값 (MW)")
        if abs(clo) < 1e-9 or (clo < 0 < chi):        # 0 기준선
            p.setPen(QtGui.QPen(C_AXIS, 1, QtCore.Qt.DashLine))
            p.drawLine(QtCore.QPointF(g["px"], cy(0)),
                       QtCore.QPointF(g["px"] + g["pw"], cy(0)))
        if self.show_band and self._sigma is not None:
            poly = QtGui.QPolygonF()
            up, dn = [], []
            for r in self._rows:
                s = self._sigma(r.temp)
                if s != s:
                    continue
                up.append(QtCore.QPointF(tx(r.temp), cy(r.correction + 1.645 * s)))
                dn.append(QtCore.QPointF(tx(r.temp), cy(r.correction - 1.645 * s)))
            if up:
                for q in up:
                    poly.append(q)
                for q in reversed(dn):
                    poly.append(q)
                p.setPen(QtCore.Qt.NoPen)
                p.setBrush(C_BAND)
                p.drawPolygon(poly)
                p.setBrush(QtCore.Qt.NoBrush)
        self._series(p, [(tx(r.temp), cy(r.correction)) for r in self._rows],
                     C_CORR, width=2.0)
        if self.show_points:
            p.setPen(QtGui.QPen(QtGui.QColor("#ffffff"), 1))
            p.setBrush(C_PT)
            for t, c in self._pts:
                if t0 <= t <= t1:
                    p.drawEllipse(QtCore.QPointF(tx(t), cy(c)), 3.1, 3.1)
            p.setBrush(QtCore.Qt.NoBrush)
        li = [(C_CORR, "보정값 곡선", False)]
        if self.show_band and self._sigma is not None:
            li.append((QtGui.QColor("#7fb3e8"), "90% 예측구간", False))
        if self.show_points:
            li.append((C_PT, "실측 보정값", "dot"))
        self._legend(p, g["px"] + 8, g["by"] + 6, li)

        # ── 호버 ──
        if self._hover is not None:
            self._hover_draw(p, g, tx, ty, cy)

    @staticmethod
    def _theory_net(row) -> float:
        """이론값을 입찰과 같은 Net 기준으로 — min(Gross − 소내전력, 상한)."""
        return min(row.cc_theory - C.CC_AUX, C.BID_CAP_NET)

    # ── 그리기 도우미 ──
    def _axes(self, p, g, ykey, hkey, ylo, yhi, step, tx, yf, t0, t1, label):
        y0, hgt = g[ykey], g[hkey]
        p.setPen(QtGui.QPen(C_GRID, 1))
        v = ylo
        while v <= yhi + 1e-9:
            yy = yf(v)
            p.drawLine(QtCore.QPointF(g["px"], yy), QtCore.QPointF(g["px"] + g["pw"], yy))
            v += step
        for t in range(int(t0), int(t1) + 1, 5):
            p.drawLine(QtCore.QPointF(tx(t), y0), QtCore.QPointF(tx(t), y0 + hgt))
        p.setPen(QtGui.QPen(C_AXIS, 1.2))
        p.drawLine(QtCore.QPointF(g["px"], y0), QtCore.QPointF(g["px"], y0 + hgt))
        p.drawLine(QtCore.QPointF(g["px"], y0 + hgt),
                   QtCore.QPointF(g["px"] + g["pw"], y0 + hgt))
        f = p.font()
        f.setPointSizeF(8.0)
        p.setFont(f)
        p.setPen(C_TEXT)
        v = ylo
        while v <= yhi + 1e-9:
            p.drawText(QtCore.QRectF(2, yf(v) - 8, g["px"] - 8, 16),
                       QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
                       f"{v:.0f}" if abs(v) >= 10 or v == int(v) else f"{v:.1f}")
            v += step
        for t in range(int(t0), int(t1) + 1, 5):
            p.drawText(QtCore.QRectF(tx(t) - 18, y0 + hgt + 3, 36, 14),
                       QtCore.Qt.AlignCenter, f"{t}")
        p.drawText(QtCore.QRectF(g["px"], y0 + hgt + 17, g["pw"], 14),
                   QtCore.Qt.AlignCenter, "외기온도 CIT (°C)")
        p.save()
        p.translate(13, y0 + hgt / 2)
        p.rotate(-90)
        p.drawText(QtCore.QRectF(-hgt / 2, -12, hgt, 14), QtCore.Qt.AlignCenter, label)
        p.restore()

    @staticmethod
    def _series(p, pts, color, dash=False, width=1.8):
        if len(pts) < 2:
            return
        pen = QtGui.QPen(color, width)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        if dash:
            pen.setStyle(QtCore.Qt.DashLine)
        p.setPen(pen)
        path = QtGui.QPainterPath(QtCore.QPointF(*pts[0]))
        for q in pts[1:]:
            path.lineTo(QtCore.QPointF(*q))
        p.drawPath(path)

    @staticmethod
    def _legend(p, x, y, items):
        f = p.font()
        f.setPointSizeF(8.0)
        p.setFont(f)
        for color, text, dash in items:
            if dash == "dot":                      # 산점 표식
                p.setPen(QtGui.QPen(QtGui.QColor("#ffffff"), 1))
                p.setBrush(color)
                p.drawEllipse(QtCore.QPointF(x + 9, y + 7), 3.1, 3.1)
                p.setBrush(QtCore.Qt.NoBrush)
            else:
                pen = QtGui.QPen(color, 2.0)
                if dash:
                    pen.setStyle(QtCore.Qt.DashLine)
                p.setPen(pen)
                p.drawLine(QtCore.QPointF(x, y + 7), QtCore.QPointF(x + 18, y + 7))
            p.setPen(C_TEXT)
            p.drawText(QtCore.QRectF(x + 23, y, 200, 14),
                       QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, text)
            x += 23 + p.fontMetrics().horizontalAdvance(text) + 16

    def _hover_draw(self, p, g, tx, ty, cy):
        t = int(round(self._hover))
        row = next((r for r in self._rows if r.temp == t), None)
        if row is None:
            return
        x = tx(t)
        p.setPen(QtGui.QPen(QtGui.QColor("#b9c0cc"), 1, QtCore.Qt.DashLine))
        p.drawLine(QtCore.QPointF(x, g["ty"]), QtCore.QPointF(x, g["by"] + g["bh"]))
        for yy, col in ((ty(self._theory_net(row)), C_THEORY), (ty(row.cc_real_net), C_REAL),
                        (cy(row.correction), C_CORR)):
            p.setPen(QtGui.QPen(QtGui.QColor("#ffffff"), 1))
            p.setBrush(col)
            p.drawEllipse(QtCore.QPointF(x, yy), 3.4, 3.4)
        p.setBrush(QtCore.Qt.NoBrush)
        lines = [f"{t}°C",
                 f"이론 Net {self._theory_net(row):.1f} MW",
                 f"현실화 Net {row.cc_real_net:.1f} MW",
                 f"보정 {row.correction:+.2f} MW"]
        if self._margin is not None:
            lines.append(f"마진 −{self._margin(t):.2f} MW")
        if self._sigma is not None:
            s = self._sigma(t)
            if s == s:
                lines.append(f"불확실성 ±{1.645 * s:.2f} MW")
        f = p.font()
        f.setPointSizeF(8.2)
        p.setFont(f)
        fm = p.fontMetrics()
        w = max(fm.horizontalAdvance(s) for s in lines) + 16
        h = len(lines) * (fm.height() + 1) + 10
        bx = min(x + 12, g["px"] + g["pw"] - w)
        by = g["ty"] + 4
        p.setPen(QtGui.QPen(QtGui.QColor("#d8dde6"), 1))
        p.setBrush(QtGui.QColor(255, 255, 255, 242))
        p.drawRoundedRect(QtCore.QRectF(bx, by, w, h), 4, 4)
        p.setPen(C_TEXT)
        for i, s in enumerate(lines):
            r = QtCore.QRectF(bx + 8, by + 5 + i * (fm.height() + 1), w - 16, fm.height())
            if i == 0:
                fb = p.font()
                fb.setBold(True)
                p.setFont(fb)
                p.drawText(r, QtCore.Qt.AlignLeft, s)
                fb.setBold(False)
                p.setFont(fb)
            else:
                p.drawText(r, QtCore.Qt.AlignLeft, s)
