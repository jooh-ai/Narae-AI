"""Tool UI 테마 v2 「계측 기록지」 — 색·스타일시트 한 곳.

발표자료(docs/ppt/build/theme.js)와 같은 팔레트를 쓴다. 도구 화면과 보고
자료가 같은 색을 쓰면, 발표에서 화면을 띄웠을 때 두 개가 한 물건으로 보인다.

색의 뜻은 세 장 모두 고정이다 — 슬레이트=종전/이론, 앰버=개선/현재, 레드=위험.
그래서 색을 '예쁘라고' 바꾸면 안 된다. 뜻이 바뀐다.

명암비는 배경 #0F1A28 기준이고 전부 WCAG AA(4.5:1)를 넘긴다. 푸른 회색은
명암비가 높아도 남색 바탕에 묻히므로 중립색을 '따뜻한 회색' 으로 잡았다 —
발표자료에서 같은 이유로 내린 결정이다(계획서 §5.2).
"""
from __future__ import annotations

from pathlib import Path

C = {
    "ground":  "#0F1A28",   # 배경
    "panel":   "#132234",   # 카드·그룹박스 면
    "groove":  "#0A1320",   # 데이터가 앉는 홈 면 (표·차트)
    "rule":    "#22354A",   # 헤어라인
    "rule2":   "#182838",   # 더 약한 헤어라인
    "ink":     "#EAE7E0",   # 본문 강조            14.2:1
    "body":    "#CFCBC2",   # 본문                 10.8:1
    "dim":     "#A9A79F",   # 캡션                  7.3:1
    "dim2":    "#8A8880",   # 라벨                  4.9:1
    "brass":   "#EFB13C",   # 개선·핵심             9.2:1
    "brassD":  "#8A6620",
    "brassS":  "#3A2C12",   # 앰버 선택 배경(면)
    "red":     "#FF4D63",   # 위험·미달             5.4:1
    "redD":    "#7E2333",
    "slate":   "#718BA6",   # 종전·이론 — 면        5.0:1
    "slateL":  "#A8BCD1",   # 종전·이론 — 선        9.0:1
    "steel":   "#55708A",
}

FONT_KR = "'Malgun Gothic', 'Segoe UI', sans-serif"
FONT_MONO = "'Consolas', 'D2Coding', monospace"


def qss() -> str:
    """앱 전체 스타일시트. 색은 위 C 에서만 온다 — 리터럴을 박지 않는다."""
    return f"""
* {{ font-family: {FONT_KR}; font-size: 10pt; color: {C['body']}; }}
QMainWindow, QWidget {{ background: {C['ground']}; color: {C['body']}; }}

/* ── 머리글 — 그라데이션을 걷어내고 얇은 앰버 룰 하나로 ── */
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
    background: {C['groove']}; border-top: 2px solid {C['brass']};
    border-bottom: 1px solid {C['rule']};
}}
QLabel#bannertext {{ background: transparent; color: {C['dim']}; font-size: 9.5pt; }}

/* ── 탭 — 선택된 것만 앰버, 나머지는 중립 회색(뜻 없는 색) ── */
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
    background: {C['ground']}; color: {C['dim2']}; border-color: {C['rule2']};
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
    selection-color: {C['brass']}; outline: none;
}}

/* ── 버튼 ── */
QPushButton {{
    background: {C['panel']}; color: {C['body']};
    border: 1px solid {C['rule']}; border-radius: 6px;
    padding: 8px 16px; font-weight: 600;
}}
QPushButton:hover {{ background: {C['rule2']}; border-color: {C['steel']}; color: {C['ink']}; }}
QPushButton:disabled {{ color: {C['dim2']}; border-color: {C['rule2']}; }}
/* 주 버튼은 전폭으로 깔리므로 솔리드 앰버면 화면을 지배한다. 평소에는
   옅은 앰버 면 + 앰버 테두리로 낮추고, 마우스를 올렸을 때만 채운다.
   누를 자리라는 것은 테두리와 글자색으로 이미 충분히 말한다. */
QPushButton#primary {{
    background: {C['brassS']}; color: {C['brass']};
    border: 1px solid {C['brass']}; border-radius: 8px;
    font-weight: 800; font-size: 11.5pt; padding: 11px;
}}
QPushButton#primary:hover {{
    background: {C['brass']}; color: {C['ground']}; border-color: {C['brass']};
}}
QPushButton#primary:pressed {{ background: {C['brassD']}; color: {C['ink']}; }}
QPushButton#primary:disabled {{
    background: transparent; color: {C['dim2']}; border-color: {C['rule']};
}}
QPushButton#danger {{
    background: transparent; color: {C['red']};
    border: 1px solid {C['redD']}; border-radius: 6px;
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
    border: 1px solid {C['rule']}; border-radius: 6px; background: {C['groove']};
    text-align: center; color: {C['ink']}; font-weight: 700; height: 20px;
    font-family: {FONT_MONO};
}}
QProgressBar::chunk {{ border-radius: 5px; background: {C['brass']}; }}

/* ── 표 — 데이터가 앉는 홈 면. 숫자는 Consolas ── */
QTableWidget {{
    background: {C['groove']}; border: 1px solid {C['rule']}; border-radius: 8px;
    gridline-color: {C['rule2']}; alternate-background-color: #0D1826;
    color: {C['body']}; font-family: {FONT_MONO}; font-size: 10pt;
    selection-background-color: {C['brassS']}; selection-color: {C['brass']};
}}
QHeaderView::section {{
    background: {C['ground']}; color: {C['dim2']}; border: none;
    border-bottom: 2px solid {C['brassD']}; padding: 7px;
    font-family: {FONT_KR}; font-weight: 700; letter-spacing: 0.4px;
}}
QTableCornerButton::section {{ background: {C['ground']}; border: none; }}

QLabel#summary {{
    background: {C['groove']}; border: 1px solid {C['rule']};
    border-left: 3px solid {C['brass']}; border-radius: 8px;
    padding: 12px; color: {C['ink']}; font-weight: 600;
}}
QToolTip {{
    background: {C['panel']}; color: {C['ink']};
    border: 1px solid {C['rule']}; padding: 6px;
}}

QScrollBar:vertical {{ background: {C['ground']}; width: 11px; margin: 0; }}
QScrollBar::handle:vertical {{
    background: {C['rule']}; border-radius: 5px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {C['steel']}; }}
QScrollBar:horizontal {{ background: {C['ground']}; height: 11px; margin: 0; }}
QScrollBar::handle:horizontal {{
    background: {C['rule']}; border-radius: 5px; min-width: 30px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
"""


def check_indicator_qss() -> str:
    """체크 표시 PNG 를 만들어 QSS 조각으로 돌려준다. 실패하면 앰버 채움으로 후퇴.

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
