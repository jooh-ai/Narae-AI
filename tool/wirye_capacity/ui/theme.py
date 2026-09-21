"""Tool UI 테마 「밝은 기록지」 — 색·스타일시트 한 곳.

발표자료(docs/ppt/build/theme_light.js)와 같은 팔레트를 쓴다. 도구 화면과 보고
자료가 같은 색을 쓰면, 발표에서 화면을 띄웠을 때 두 개가 한 물건으로 보인다.

색의 뜻은 고정이다 — 슬레이트=종전/이론, 레드=개선/현재/선정, 주황=주의/위험.
그래서 색을 '예쁘라고' 바꾸면 안 된다. 뜻이 바뀐다.

명암비는 배경 #FFFFFF 와 카드 면 #F7F9FB 기준이고, 글자로 쓰는 색은 전부
WCAG AA(4.5:1)를 넘긴다 — ink 17.4 · body 12.6 · dim 6.9 · dim2 5.0 ·
brass 4.6 · slateL 4.6.

흰 바탕에서는 밝은 색이 글자로 버티지 못한다. 그래서 강조색은 **칠하고 긋는
색과 적는 색을 따로 둔다**.
    brass #EA002C 는 흰 바탕에서 4.63 이지만 옅은 면(brassS) 위에서 4.03 으로
    떨어진다                                        → 글자는 brassT #C80025
    red   #FF6F0F 는 흰 바탕에서 2.79 다(선·면 전용) → 글자는 redT  #B84A00
어두운 테마(v2 「계측 기록지」)는 git 이력에 그대로 있다. 되돌릴 자리는 남겨 둔다.
"""
from __future__ import annotations

from pathlib import Path

C = {
    "ground":  "#FFFFFF",   # 배경
    "panel":   "#F7F9FB",   # 카드·그룹박스 면 · 표 줄무늬
    "groove":  "#FFFFFF",   # 데이터가 앉는 홈 면 (표·차트·입력칸)
    "rule":    "#C9D0D8",   # 헤어라인
    "rule2":   "#E4E8ED",   # 약한 헤어라인 · 옅은 회색 면(표 머리·못 고치는 칸)
    "ink":     "#1A1A1A",   # 본문 강조            17.4:1
    "body":    "#333333",   # 본문                 12.6:1
    "dim":     "#5A5A5A",   # 캡션                  6.9:1
    "dim2":    "#6F6F6F",   # 라벨                  5.0:1
    "brass":   "#EA002C",   # 개선·현재·선정 — 칠하고 긋는 색   4.6:1
    "brassT":  "#C80025",   # 개선·현재·선정 — 적는 색          6.0:1 · 옅은 면 5.3:1
    "brassD":  "#F5A3B0",   # 레드 옅은 선 · 선택 글자 배경
    "brassS":  "#FDEBEE",   # 레드 선택 배경(면)
    "red":     "#FF6F0F",   # 주의·미달 — 칠하고 긋는 색만 (흰 바탕 2.8:1)
    "redT":    "#B84A00",   # 주의·미달 — 적는 색               5.2:1
    "redD":    "#FFD9B8",   # 주황 옅은 면
    "slate":   "#9AA3AC",   # 종전·이론 — 면·축
    "slateL":  "#6E7780",   # 종전·이론 — 선·글자   4.6:1
    "steel":   "#C4CAD1",   # 중립 보조선
}

FONT_KR = "'Malgun Gothic', 'Segoe UI', sans-serif"
FONT_MONO = "'Consolas', 'D2Coding', monospace"


def qss() -> str:
    """앱 전체 스타일시트. 색은 위 C 에서만 온다 — 리터럴을 박지 않는다."""
    return f"""
* {{ font-family: {FONT_KR}; font-size: 10pt; color: {C['body']}; }}
QMainWindow, QWidget {{ background: {C['ground']}; color: {C['body']}; }}

/* ── 머리글 — 그라데이션을 걷어내고 얇은 레드 룰 하나로 ── */
QWidget#header {{
    background: {C['ground']};
    border: none; border-bottom: 1px solid {C['rule']};
}}
QLabel#headertitle {{
    background: transparent; color: {C['ink']};
    font-size: 14pt; font-weight: 800; letter-spacing: 0.3px;
}}
QLabel#headermark {{ background: transparent; }}
QLabel#headersub {{ color: {C['dim']}; font-size: 9pt; }}

QWidget#banner {{
    background: {C['panel']}; border-top: 2px solid {C['brass']};
    border-bottom: 1px solid {C['rule']};
}}
QLabel#bannertext {{ background: transparent; color: {C['dim']}; font-size: 9.5pt; }}

/* ── 탭 — 선택된 것만 레드, 나머지는 중립 회색(뜻 없는 색) ── */
QTabWidget::pane {{ border: none; background: transparent; }}
QTabBar::tab {{
    background: transparent; padding: 10px 20px; margin-right: 2px;
    color: {C['dim2']}; border: none; border-bottom: 3px solid transparent;
    font-weight: 600;
}}
QTabBar::tab:selected {{ color: {C['brass']}; border-bottom: 3px solid {C['brass']}; }}
QTabBar::tab:hover {{ color: {C['ink']}; }}

/* ── 카드 ── */
QGroupBox {{
    background: {C['panel']}; border: 1px solid {C['rule']}; border-radius: 10px;
    margin-top: 14px; padding: 16px 12px 10px 12px;
    font-weight: 700; color: {C['dim']};
}}
QGroupBox::title {{
    subcontrol-origin: margin; left: 12px; padding: 0 6px;
    color: {C['dim2']}; font-family: {FONT_MONO}; font-size: 9pt;
    letter-spacing: 1.2px;
}}

/* ── 입력 — 숫자는 Consolas. 자리수가 흔들리지 않아야 눈으로 비교된다 ── */
QLineEdit, QDoubleSpinBox, QSpinBox {{
    background: {C['groove']}; border: 1px solid {C['rule']}; border-radius: 6px;
    padding: 7px 9px; color: {C['ink']};
    font-family: {FONT_MONO}; font-size: 10.5pt;
    selection-background-color: {C['brassD']}; selection-color: {C['ink']};
}}
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {{
    border: 2px solid {C['brass']}; padding: 6px 8px;
}}
QLineEdit:disabled, QDoubleSpinBox:disabled {{
    background: {C['panel']}; color: {C['dim2']}; border-color: {C['rule2']};
}}
QComboBox {{
    background: {C['groove']}; border: 1px solid {C['rule']}; border-radius: 6px;
    padding: 7px 9px; color: {C['ink']};
}}
QComboBox:focus {{ border: 2px solid {C['brass']}; padding: 6px 8px; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {C['panel']}; border: 1px solid {C['rule']};
    color: {C['body']}; selection-background-color: {C['brassS']};
    selection-color: {C['brassT']}; outline: none;
}}

/* ── 버튼 ── */
QPushButton {{
    background: {C['panel']}; color: {C['body']};
    border: 1px solid {C['rule']}; border-radius: 6px;
    padding: 8px 16px; font-weight: 600;
}}
QPushButton:hover {{ background: {C['rule2']}; border-color: {C['steel']}; color: {C['ink']}; }}
QPushButton:disabled {{ color: {C['dim2']}; border-color: {C['rule2']}; }}
/* 어두운 테마에서는 솔리드 앰버가 화면을 지배해서 옅은 면 + 테두리로 낮췄다.
   흰 바탕에서는 거꾸로다 — 옅은 분홍 면에 레드 글자를 올리면 4.03:1 로 떨어져
   AA 를 못 넘긴다. 그래서 밝은 테마의 주 버튼은 솔리드 레드 + 흰 글자(4.63:1)
   다. 흰 바탕에서는 솔리드 한 덩어리가 오히려 조용하다.
   누른 순간만 색을 뒤집어(옅은 면 + 진한 레드 글자) '눌렸다' 를 말한다. */
QPushButton#primary {{
    background: {C['brass']}; color: {C['ground']};
    border: 1px solid {C['brass']}; border-radius: 8px;
    font-weight: 800; font-size: 11.5pt; padding: 11px;
}}
QPushButton#primary:hover {{
    background: {C['brassT']}; color: {C['ground']}; border-color: {C['brassT']};
}}
QPushButton#primary:pressed {{
    background: {C['brassS']}; color: {C['brassT']}; border-color: {C['brassT']};
}}
QPushButton#primary:disabled {{
    background: {C['panel']}; color: {C['dim2']}; border-color: {C['rule']};
}}
QPushButton#danger {{
    background: transparent; color: {C['redT']};
    border: 1px solid {C['red']}; border-radius: 6px;
    padding: 8px 16px; font-weight: 700;
}}
QPushButton#danger:hover {{ background: {C['redD']}; color: {C['ink']}; }}

/* ── 체크박스 ── */
QCheckBox {{ spacing: 8px; padding: 2px; color: {C['body']}; }}
QCheckBox::indicator {{
    width: 17px; height: 17px; border: 1px solid {C['rule']};
    border-radius: 3px; background: {C['groove']};
}}
QCheckBox::indicator:hover {{ border-color: {C['brass']}; }}
QCheckBox::indicator:checked {{ border-color: {C['brass']}; }}
QCheckBox::indicator:disabled {{ background: {C['ground']}; border-color: {C['rule2']}; }}

/* 스핀박스 화살표 — 위치·크기를 명시하지 않으면 위 버튼이 위젯 밖으로 2px
   밀려나고 둥근 모서리에 가려서 클릭이 안 먹는다(2026-08 부장님 지적). */
QDoubleSpinBox, QSpinBox {{ padding-right: 26px; }}
QDoubleSpinBox::up-button, QSpinBox::up-button {{
    subcontrol-origin: border; subcontrol-position: top right;
    width: 22px; margin: 1px 1px 0 0; border-left: 1px solid {C['rule']};
    border-top-right-radius: 5px; background: {C['panel']};
}}
QDoubleSpinBox::down-button, QSpinBox::down-button {{
    subcontrol-origin: border; subcontrol-position: bottom right;
    width: 22px; margin: 0 1px 1px 0; border-left: 1px solid {C['rule']};
    border-bottom-right-radius: 5px; background: {C['panel']};
}}
QDoubleSpinBox::up-button:hover, QSpinBox::up-button:hover,
QDoubleSpinBox::down-button:hover, QSpinBox::down-button:hover {{
    background: {C['rule']};
}}
QDoubleSpinBox::up-arrow, QSpinBox::up-arrow,
QDoubleSpinBox::down-arrow, QSpinBox::down-arrow {{ width: 9px; height: 9px; }}

QProgressBar {{
    border: 1px solid {C['rule']}; border-radius: 6px; background: {C['panel']};
    text-align: center; color: {C['ink']}; font-weight: 700; height: 20px;
    font-family: {FONT_MONO};
}}
QProgressBar::chunk {{ border-radius: 5px; background: {C['brass']}; }}

/* ── 표 — 데이터가 앉는 홈 면. 숫자는 Consolas ── */
QTableWidget {{
    background: {C['groove']}; border: 1px solid {C['rule']}; border-radius: 8px;
    gridline-color: {C['rule2']}; alternate-background-color: {C['panel']};
    color: {C['body']}; font-family: {FONT_MONO}; font-size: 10pt;
    selection-background-color: {C['brassS']}; selection-color: {C['brassT']};
}}
/* 머리는 회색 띠로 세운다 — 흰 표에 흰 머리를 얹으면 줄무늬와 구분되지 않는다.
   밑줄은 옅은 분홍(brassD)이 아니라 레드로 긋는다(흰 바탕에서 분홍은 묻힌다). */
QHeaderView::section {{
    background: {C['rule2']}; color: {C['dim']}; border: none;
    border-bottom: 2px solid {C['brass']}; padding: 7px;
    font-family: {FONT_KR}; font-weight: 700; letter-spacing: 0.4px;
}}
QTableCornerButton::section {{ background: {C['rule2']}; border: none; }}

QLabel#summary {{
    background: {C['groove']}; border: 1px solid {C['rule']};
    border-left: 3px solid {C['brass']}; border-radius: 8px;
    padding: 12px; color: {C['ink']}; font-weight: 600;
}}
QToolTip {{
    background: {C['panel']}; color: {C['ink']};
    border: 1px solid {C['rule']}; padding: 6px;
}}

QScrollBar:vertical {{ background: {C['panel']}; width: 11px; margin: 0; }}
QScrollBar::handle:vertical {{
    background: {C['rule']}; border-radius: 5px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {C['steel']}; }}
QScrollBar:horizontal {{ background: {C['panel']}; height: 11px; margin: 0; }}
QScrollBar::handle:horizontal {{
    background: {C['rule']}; border-radius: 5px; min-width: 30px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
"""


def check_indicator_qss() -> str:
    """체크 표시 PNG 를 만들어 QSS 조각으로 돌려준다. 실패하면 레드 채움으로 후퇴.

    QSS 로 QCheckBox::indicator 의 크기를 지정하면 Qt 는 네이티브 체크를 그리지
    않는다(실측 확인). 그래서 체크 모양은 이미지로 넣어야 한다 — 파일을 번들에
    두는 대신 매 실행마다 임시폴더에 그려서 쓴다(PyInstaller 경로 문제가 없다).
    """
    import tempfile

    from PySide6 import QtCore, QtGui
    try:
        n = 17
        for scale in (3, 2, 1):                  # 고DPI 대비 3배로 그려 축소
            s = n * scale
            img = QtGui.QImage(s, s, QtGui.QImage.Format.Format_ARGB32)
            img.fill(QtCore.Qt.GlobalColor.transparent)
            pen = QtGui.QPen(QtGui.QColor(C["brass"]))
            pen.setWidthF(2.2 * scale)
            pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
            pt = QtGui.QPainter(img)
            pt.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            pt.setPen(pen)
            path = QtGui.QPainterPath()
            path.moveTo(0.22 * s, 0.53 * s)
            path.lineTo(0.42 * s, 0.73 * s)
            path.lineTo(0.79 * s, 0.28 * s)
            pt.drawPath(path)
            pt.end()
            out = Path(tempfile.gettempdir()) / f"wirye_check_v2_{scale}x.png"
            if img.save(str(out), "PNG"):
                # Qt QSS 는 항상 슬래시 경로를 쓴다(윈도우 역슬래시는 이스케이프로 먹힘)
                url = out.as_posix()
                return ("QCheckBox::indicator:checked { image: url(%s); }\n"
                        "QCheckBox::indicator:checked:disabled { image: url(%s); }"
                        % (url, url))
    except Exception:                            # noqa: BLE001
        pass
    return "QCheckBox::indicator:checked { background: %s; }" % C["brass"]



def _chevron(direction: str, color: str, scale: int = 3, n: int = 9) -> str | None:
    """작은 꺾쇠(∨ / ∧) PNG 를 임시폴더에 그려 경로를 돌려준다.

    QSS 로 QComboBox::drop-down 이나 스핀박스 버튼의 크기를 지정하면 Qt 는
    네이티브 화살표를 그리지 않는다 — 체크 표시와 같은 사정이다. 밝은 테마에서는
    화살표가 없어도 검은 삼각형이 남아 눈에 띄었지만, 어두운 테마에서는 아무것도
    안 보인다. 그래서 직접 그려 넣는다.
    """
    import tempfile

    from PySide6 import QtCore, QtGui
    try:
        s_ = n * scale
        img = QtGui.QImage(s_, s_, QtGui.QImage.Format.Format_ARGB32)
        img.fill(QtCore.Qt.GlobalColor.transparent)
        pen = QtGui.QPen(QtGui.QColor(color))
        pen.setWidthF(1.6 * scale)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
        pt = QtGui.QPainter(img)
        pt.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        pt.setPen(pen)
        path = QtGui.QPainterPath()
        if direction == "down":
            path.moveTo(0.18 * s_, 0.34 * s_)
            path.lineTo(0.50 * s_, 0.70 * s_)
            path.lineTo(0.82 * s_, 0.34 * s_)
        else:
            path.moveTo(0.18 * s_, 0.66 * s_)
            path.lineTo(0.50 * s_, 0.30 * s_)
            path.lineTo(0.82 * s_, 0.66 * s_)
        pt.drawPath(path)
        pt.end()
        out = Path(tempfile.gettempdir()) / f"wirye_chev_{direction}_{color.lstrip('#')}.png"
        return out.as_posix() if img.save(str(out), "PNG") else None
    except Exception:                            # noqa: BLE001
        return None


def arrow_qss() -> str:
    """콤보·스핀박스 화살표 QSS 조각. 그리기에 실패하면 빈 문자열(네이티브 유지)."""
    dn = _chevron("down", C["dim"])
    up = _chevron("up", C["dim"])
    dn_on = _chevron("down", C["brass"])
    up_on = _chevron("up", C["brass"])
    if not (dn and up):
        return ""
    out = [
        f"QComboBox::down-arrow {{ image: url({dn}); width: 9px; height: 9px; }}",
        f"QComboBox::down-arrow:on {{ image: url({dn_on or dn}); }}",
        f"QDoubleSpinBox::down-arrow, QSpinBox::down-arrow {{ image: url({dn}); }}",
        f"QDoubleSpinBox::up-arrow, QSpinBox::up-arrow {{ image: url({up}); }}",
        f"QDoubleSpinBox::down-arrow:hover, QSpinBox::down-arrow:hover "
        f"{{ image: url({dn_on or dn}); }}",
        f"QDoubleSpinBox::up-arrow:hover, QSpinBox::up-arrow:hover "
        f"{{ image: url({up_on or up}); }}",
    ]
    return "\n".join(out)


def runtime_qss() -> str:
    """QApplication 이 만들어진 뒤에만 그릴 수 있는 조각들(체크·화살표)."""
    return check_indicator_qss() + "\n" + arrow_qss()


QSS = qss()
