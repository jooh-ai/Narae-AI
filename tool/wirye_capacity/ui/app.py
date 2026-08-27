"""위례 공급가능용량 입찰 산정 — Windows 데스크톱 GUI (PySide6).

사내 PC에서 실행:  python -m wirye_capacity.ui.app
로직은 pipeline.run_pipeline 에 위임하고, 이 모듈은 입력/표시만 담당하는 얇은 셸이다.

자동화 원칙(사용자 확정): 화면 입력은 날짜·시각 중심. RiMS(OPC UA) 서버 호스트는
설정(Tool 폴더 wirye_tool.json)에 최초 1회 저장 후 화면에서 숨김. 엑셀3 템플릿은
번들 사용(비상시 설정파일 template_path 로 오버라이드).

보정 방법은 화면에서 고르고, 고른 값이 설정에 저장돼 다음 실행에도 유지된다.
방법은 기록마다 붙는 값이 아니라 산출 시점에 누적 전체에 적용되는 값이다
(pipeline.run_pipeline 3단계 참조).

화면:
  [공급가능용량 산정]      날짜·시각 입력 → RiMS 자동취득 → 보정 → 온도별 예측 표시.
                        표 위 [엑셀로 저장] 으로 엑셀3 입찰파일을 만든다(실행은
                        계산만 하고 파일을 만들지 않는다).
  [온도 구간별 보정값 현황] 엑셀4 '보정값 현황' 재현 (실행 시 자동 갱신)
  [Test List-up]           누적 테스트 목록
"""
from __future__ import annotations

import sys
from pathlib import Path

from .. import config as _cf
from .. import constants as C
from ..config import get_config, set_config
from .. import select as _sel
from ..correction import status_rows, table_fingerprint
from ..pipeline import METHOD_LABEL, run_pipeline
from ..profile import PROFILE_COLUMNS, build_profile
from ..store import MeasurementStore
from ..theory import TheoryEngine

# 보정방법 콤보박스 순서 → run_pipeline(correction_method=) 키. 저장값과 같은 문자열이다.
# 'gp:<커널>' 이 커널별로 하나씩 들어간다 — 어느 커널을 쓸지는 사용자가 고르고,
# 하이퍼파라미터는 커널마다 주변우도로 자동 적합한다(선택 편향 없음).
# LOOCV 로 후보를 채점하는 것은 [🔬 모델 선정] 탭이고, 실제 산정에 쓸 방법은
# 여기서 사람이 고른다 — 자동으로 바뀌지 않는다(부장님 방침).
_METHODS = _sel.METHODS
_METHOD_ITEMS = [_sel.METHOD_LABEL[m] for m in _METHODS]


def _method_index(key: str) -> int:
    """저장된 방법 키 → 콤보 인덱스. 예전 'gp' 는 'gp:rbf' 로 해석한다."""
    k = "gp:rbf" if key == "gp" else key
    return _METHODS.index(k) if k in _METHODS else 0

# 온도 프로파일 표의 짧은 머리글. 어떤 열을 어떤 순서로 보일지는 엑셀3 출력과
# 같은 목록(profile.PROFILE_COLUMNS)이 정하고, 여기서는 이름만 줄인다 — 9열이
# 창 폭에 들어가야 읽을 수 있다. 여기에 없는 열은 원래 이름을 그대로 쓴다.
_SHORT_HEAD = {
    "temp": "온도(°C)", "gt_theory": "GT 이론", "st_theory": "ST 이론",
    "cc_theory": "CC 이론", "correction": "보정값",
    "gt_real": "GT 현실", "st_real": "ST 현실",
    "cc_real_gross": "CC 현실 Gross", "cc_real_net": "★ CC 현실 Net",
}

# ── SK 브랜드 스타일시트 (행복날개 레드 #EA002C · 오렌지 #F47725, 플랫 · 카드) ──
QSS = """
* { font-family: 'Malgun Gothic', 'Segoe UI', sans-serif; font-size: 10pt; }
QMainWindow, QWidget { background: #FAF7F5; color: #2B2422; }

QWidget#header {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #EA002C, stop:0.6 #F0431F, stop:1 #F47725);
    border: none;
}
QLabel#headertitle {
    background: transparent; color: #FFFFFF; font-size: 14pt; font-weight: 800;
}
/* 로고는 헤더와 같은 레드·오렌지라 그라데이션 위에 그대로 얹으면 묻힌다.
   흰 칩 안에 넣어 브랜드 색을 살린다. */
QLabel#headermark { background: #FFFFFF; border-radius: 6px; }
QLabel#headersub { color: #FFE3D6; font-size: 9pt; }

QWidget#banner { background: #FFF3EC; border-bottom: 1px solid #FFCDB2; }
QLabel#bannertext { background: transparent; color: #8A2A00; font-size: 9.5pt; }

QTabWidget::pane { border: none; background: transparent; }
QTabBar::tab {
    background: transparent; padding: 10px 20px; margin-right: 2px;
    color: #8A7F7A; border: none; border-bottom: 3px solid transparent;
    font-weight: 600;
}
QTabBar::tab:selected { color: #EA002C; border-bottom: 3px solid #EA002C; }
QTabBar::tab:hover { color: #F0431F; }

QGroupBox {
    background: #FFFFFF; border: 1px solid #EDE4DF; border-radius: 10px;
    margin-top: 14px; padding: 16px 12px 10px 12px; font-weight: 700; color: #5B4A42;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }

QLineEdit, QDoubleSpinBox {
    background: #FFFFFF; border: 1px solid #DCD2CC; border-radius: 6px;
    padding: 7px 9px; selection-background-color: #FFD3C2;
}
QLineEdit:focus, QDoubleSpinBox:focus { border: 2px solid #F0431F; }
QLineEdit:disabled { background: #F5EFEC; color: #A89B94; }

QPushButton {
    background: #F1E9E4; color: #4A3B33; border: none; border-radius: 6px;
    padding: 8px 16px; font-weight: 600;
}
QPushButton:hover { background: #E7DAD2; }
QPushButton#primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #EA002C, stop:1 #F47725);
    color: #FFFFFF; font-weight: 800; font-size: 11.5pt;
    padding: 12px; border-radius: 8px;
}
QPushButton#primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #C50024, stop:1 #DC6414);
}
QPushButton#primary:disabled { background: #F3B7A3; }
QPushButton#danger {
    background: #FFFFFF; color: #C50024; border: 1px solid #F0AAB6;
    border-radius: 6px; padding: 8px 16px; font-weight: 700;
}
QPushButton#danger:hover { background: #FDECEF; border-color: #EA002C; }

QCheckBox { spacing: 8px; padding: 2px; }
QCheckBox::indicator { width: 17px; height: 17px; }
QCheckBox::indicator:checked { background: #EA002C; border-radius: 3px; }

QTableWidget {
    background: #FFFFFF; border: 1px solid #EDE4DF; border-radius: 8px;
    gridline-color: #F7F1EE; alternate-background-color: #FBF7F4;
}
QHeaderView::section {
    background: #F5EDE8; color: #5B4A42; border: none;
    border-bottom: 2px solid #F0B8A0; padding: 7px; font-weight: 700;
}
QLabel#summary {
    background: #FFF3EC; border: 1px solid #FFCDB2; border-radius: 8px;
    padding: 12px; color: #8A2A00; font-weight: 600;
}
QToolTip { background: #3A2E28; color: #FFF7F2; border: none; padding: 6px; }
"""

NODEID_CACHE = str(Path.home() / ".wirye_opcua_nodeids.json")


def _require_qt():
    try:
        from PySide6 import QtWidgets, QtCore  # noqa: F401
    except ImportError as e:  # pragma: no cover
        raise SystemExit("PySide6 가 필요합니다 (사내 PC): pip install PySide6") from e


def main(argv=None):  # pragma: no cover - GUI 셸(사내 실행)
    # 시작 단계를 로그에 남긴다. console=False 라 화면에 아무것도 안 남으므로,
    # 창이 안 뜬다는 신고를 받았을 때 어디까지 갔는지가 유일한 단서다.
    from ..diag import stage
    stage("Qt 확인")
    _require_qt()
    from PySide6 import QtWidgets

    # 누적 DB 는 Tool 폴더에 둔다 — 담당자가 바뀌면 폴더째 인수인계하면 데이터가 함께 간다.
    # 쓰기 불가(예: Program Files 설치)면 홈 폴더로 폴백. CLI·스크립트와 같은 함수를 쓴다.
    from .. import constants as _C
    from ..store import migrate_legacy_db
    db_default = str(_C.db_path())
    stage(f"누적 DB 결정 : {db_default}")
    migrate_note = migrate_legacy_db(db_default)   # 예전 홈 폴더 DB 를 1회 이관

    class MainWindow(QtWidgets.QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("위례 공급가능용량 입찰 산정 Tool")
            self.resize(1020, 720)
            self.engine = TheoryEngine()
            self.store = MeasurementStore(db_default)
            self._seeded = False
            if self.store.count() == 0:
                self.store.seed()
                self._seeded = True
            self._last_bid = None      # 마지막 저장 입찰파일 {path, fp} — 구버전 감지용
            self._last_run = None      # 마지막 산정 조건 — [엑셀로 저장] 재계산용

            tabs = QtWidgets.QTabWidget()
            tabs.addTab(self._run_tab(), "공급가능용량 산정")
            tabs.addTab(self._status_tab(), "온도 구간별 보정값 현황")
            tabs.addTab(self._list_tab(), "Test 결과 List-up")
            tabs.addTab(self._sim_tab(), "🧪 출력 시뮬레이션")
            tabs.addTab(self._chart_tab(), "📈 출력곡선 비교")
            tabs.addTab(self._select_tab(), "🔬 모델 선정")

            header = self._header()
            central = QtWidgets.QWidget()
            v = QtWidgets.QVBoxLayout(central)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(0)
            v.addWidget(header)
            # 시작 안내는 모달 대화상자로 띄우지 않는다. 모달은 이벤트 루프를 잡고,
            # 뒤로 가거나 화면 밖에 놓이면 사용자에게는 '더블클릭했는데 아무 반응
            # 없음' 으로만 보인다(2026-08 타 PC 사례). 창 안 배너면 그럴 일이 없다.
            banner = self._startup_banner(migrate_note, db_default)
            if banner is not None:
                v.addWidget(banner)
            v.addWidget(tabs)
            self.setCentralWidget(central)
            self._refresh_list()
            self._refresh_status(self.store.correction_table())   # 시작 시 현재 누적 기준
            self._refresh_chart()
            # 누적이 어느 파일에 쌓이는지 항상 보이게 한다 — 배포본을 여러 명이 각자
            # 쓰면 DB 도 각자 생기므로, 지금 보고 있는 게 어느 DB 인지 헷갈리면 안 된다.
            self.statusBar().showMessage(f"누적 DB : {db_default}   ({self.store.count()}건)")


        # ---------- 🔬 모델 선정 (테스트셋 분리 → 학습셋 LOOCV → 테스트셋 검증) ----------
        def _select_tab(self):
            from PySide6 import QtCore
            """모델 선정 탭.

            여기서 고른 결과가 산정 탭에 자동으로 반영되지는 않는다(부장님 방침).
            LOOCV 는 후보를 비교해 '수치를 확인' 하는 용도이고, 실제 산정에 쓸
            방법은 산정 탭에서 사람이 고른다. 모델이 조용히 바뀌면 안 된다.
            """
            w = QtWidgets.QWidget()

            g1 = QtWidgets.QGroupBox("데이터 분할")
            f1 = QtWidgets.QFormLayout(g1)
            self.sel_frac = QtWidgets.QDoubleSpinBox()
            self.sel_frac.setRange(0.0, 40.0); self.sel_frac.setDecimals(0)
            self.sel_frac.setSingleStep(5.0); self.sel_frac.setValue(20.0)
            self.sel_frac.setSuffix(" %")
            self.sel_frac.setToolTip(
                "전체 누적에서 테스트셋으로 떼어낼 비율.\n"
                "0 으로 두면 테스트셋 없이 LOOCV 만 봅니다.")
            self.sel_seed = QtWidgets.QSpinBox()
            self.sel_seed.setRange(0, 999999); self.sel_seed.setValue(42)
            self.sel_seed.setToolTip(
                "난수 시드. 같은 설정이면 같은 분할이 나옵니다.\n"
                "시드를 고정하지 않으면 누를 때마다 답이 달라져\n"
                "'왜 이 모델을 골랐나' 를 나중에 재현할 수 없습니다.")
            self.sel_strat = QtWidgets.QCheckBox("온도구간 층화 추출")
            self.sel_strat.setChecked(True)
            self.sel_strat.setToolTip(
                "온도구간별로 같은 비율씩 뽑아 학습셋에 빈 구간이 생기지 않게 합니다.\n"
                "층화 계층은 15~25°C 를 하나로 합칩니다 — 20~25°C 실측이 1건뿐이라\n"
                "완전 랜덤이면 그 구간 학습 데이터가 0건이 될 수 있습니다.\n"
                "(이 병합은 추출에만 적용되고 실제 보정 테이블은 바뀌지 않습니다.)")
            self.sel_crit = QtWidgets.QComboBox()
            self.sel_crit.addItems([_sel.CRITERION_LABEL[c] for c in _sel.CRITERIA])
            self.sel_crit.setToolTip(
                "최종 모델 선정 기준.\n"
                "R² 순위는 RMSE 순위와 수학적으로 항상 같습니다(SST 가 후보 전체에\n"
                "동일하므로). 다른 관점을 보려면 MAE 를 쓰십시오.")
            f1.addRow("테스트셋 비율", self.sel_frac)
            f1.addRow("랜덤 시드", self.sel_seed)
            f1.addRow("", self.sel_strat)
            f1.addRow("선정 기준", self.sel_crit)

            g2 = QtWidgets.QGroupBox("후보 모델")
            f2 = QtWidgets.QVBoxLayout(g2)
            self.sel_chks = {}
            for m in _METHODS:
                cb = QtWidgets.QCheckBox(_sel.METHOD_LABEL[m])
                cb.setChecked(True)
                self.sel_chks[m] = cb
                f2.addWidget(cb)
            f2.addStretch(1)

            self.sel_btn = QtWidgets.QPushButton("▶  모델 선정 실행")
            self.sel_btn.setObjectName("primary")
            self.sel_btn.clicked.connect(self._on_select)

            self.sel_head = QtWidgets.QLabel(
                "테스트셋 비율·시드·기준을 정하고 실행하세요. "
                "결과는 산정 탭에 자동 반영되지 않습니다 — 보고 직접 고르십시오.")
            self.sel_head.setObjectName("summary")
            self.sel_head.setWordWrap(True)

            self.sel_loocv = QtWidgets.QTableWidget(0, 8)
            self.sel_loocv.setHorizontalHeaderLabels(
                ["방법", "n", "MAE", "RMSE", "R²", "편차", "과대(미달위험)", "판정"])
            self.sel_test = QtWidgets.QTableWidget(0, 5)
            self.sel_test.setHorizontalHeaderLabels(
                ["CIT(°C)", "실측 보정값", "예측", "오차", "방향"])
            for tb in (self.sel_loocv, self.sel_test):
                tb.setAlternatingRowColors(True)
                tb.verticalHeader().setVisible(False)
                tb.horizontalHeader().setSectionResizeMode(
                    QtWidgets.QHeaderView.ResizeMode.Stretch)
                tb.setMinimumHeight(60)
            self.sel_test_head = QtWidgets.QLabel("② 테스트셋 검증 — 아직 실행하지 않았습니다")
            self.sel_test_head.setWordWrap(True)

            top = QtWidgets.QHBoxLayout()
            top.addWidget(g1, stretch=3)
            top.addWidget(g2, stretch=2)

            inner = QtWidgets.QWidget()
            iv = QtWidgets.QVBoxLayout(inner)
            iv.setContentsMargins(0, 0, 0, 0)
            iv.setSpacing(8)
            iv.addLayout(top)
            iv.addWidget(self.sel_btn)
            iv.addWidget(self.sel_head)
            scroll = QtWidgets.QScrollArea()
            scroll.setWidget(inner)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(
                QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setMinimumHeight(120)

            below = QtWidgets.QWidget()
            bv = QtWidgets.QVBoxLayout(below)
            bv.setContentsMargins(0, 0, 0, 0)
            bv.setSpacing(6)
            bv.addWidget(QtWidgets.QLabel("① 학습셋 LOOCV — 테스트셋은 쓰이지 않습니다"))
            bv.addWidget(self.sel_loocv, stretch=3)
            bv.addWidget(self.sel_test_head)
            bv.addWidget(self.sel_test, stretch=2)

            split = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
            split.addWidget(scroll)
            split.addWidget(below)
            split.setStretchFactor(0, 0)
            split.setStretchFactor(1, 1)
            split.setSizes([300, 420])
            split.setChildrenCollapsible(False)

            lay = QtWidgets.QVBoxLayout(w)
            lay.setContentsMargins(8, 8, 8, 8)
            lay.addWidget(split)
            return w

        def _on_select(self):
            from PySide6 import QtCore, QtGui
            cand = [m for m, cb in self.sel_chks.items() if cb.isChecked()]
            if not cand:
                QtWidgets.QMessageBox.warning(self, "후보 없음", "후보 모델을 하나 이상 고르세요.")
                return
            recs = [{"cit": r["cit"], "corr": r["corr"]} for r in self.store.list_up()]
            if len(recs) < 6:
                QtWidgets.QMessageBox.warning(
                    self, "데이터 부족", f"누적이 {len(recs)}건입니다. 최소 6건은 필요합니다.")
                return
            self.sel_btn.setEnabled(False)
            QtGui.QGuiApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)
            try:
                res = _sel.run(recs, test_frac=self.sel_frac.value() / 100.0,
                               seed=self.sel_seed.value(),
                               stratified=self.sel_strat.isChecked(),
                               criterion=_sel.CRITERIA[self.sel_crit.currentIndex()],
                               methods=cand)
            except Exception as e:  # noqa: BLE001
                QtWidgets.QMessageBox.critical(self, "모델 선정 오류", str(e))
                return
            finally:
                QtGui.QGuiApplication.restoreOverrideCursor()
                self.sel_btn.setEnabled(True)
            self._fill_select(res)

        def _fill_select(self, res):
            from PySide6 import QtCore
            crit = _sel.CRITERION_LABEL[res.criterion]
            head = [f"학습 {res.n_train}건 / 테스트 {res.n_test}건",
                    f"시드 {res.seed}", ("층화" if res.stratified else "완전 랜덤"),
                    f"기준 {crit}"]
            if res.best:
                head.append(f"선정 → {_sel.METHOD_LABEL[res.best]}")
            self.sel_head.setText("    |    ".join(head))

            rows = sorted(res.loocv, key=lambda s: s.value(res.criterion))
            self.sel_loocv.setRowCount(len(rows))
            for i, s in enumerate(rows):
                cells = [_sel.METHOD_LABEL[s.method], str(s.n), f"{s.mae:.3f}",
                         f"{s.rmse:.3f}", f"{s.r2:.3f}", f"{s.me:+.3f}",
                         f"{s.over}건",
                         "★ 선정" if s.method == res.best else ""]
                for c, txt in enumerate(cells):
                    it = QtWidgets.QTableWidgetItem(txt)
                    if c:
                        it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight
                                            | QtCore.Qt.AlignmentFlag.AlignVCenter)
                    self.sel_loocv.setItem(i, c, it)

            h = res.holdout
            if h is None:
                self.sel_test_head.setText(
                    "② 테스트셋 검증 — 테스트셋이 없습니다(비율 0% 또는 예측 불가)")
                self.sel_test.setRowCount(0)
            else:
                self.sel_test_head.setText(
                    f"② 테스트셋 검증 — {_sel.METHOD_LABEL[res.best]} · 학습에 쓰이지 않은 "
                    f"{h.n}건    MAE {h.mae:.3f}  RMSE {h.rmse:.3f}  R² {h.r2:.3f}  "
                    f"편차 {h.me:+.3f}  과대 {h.over}건")
                vis = [r for r in res.holdout_rows]
                self.sel_test.setRowCount(len(vis))
                for i, r in enumerate(vis):
                    if r["pred"] is None:
                        cells = [f"{r['cit']:.1f}", f"{r['corr']:+.3f}", "예측 불가", "", ""]
                    else:
                        cells = [f"{r['cit']:.1f}", f"{r['corr']:+.3f}",
                                 f"{r['pred']:+.3f}", f"{r['err']:+.3f}",
                                 "안전(낮게)" if r["err"] > 0 else "미달 위험(높게)"]
                    for c, txt in enumerate(cells):
                        it = QtWidgets.QTableWidgetItem(txt)
                        if 0 < c < 4:
                            it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight
                                                | QtCore.Qt.AlignmentFlag.AlignVCenter)
                        self.sel_test.setItem(i, c, it)
            if res.warnings:
                QtWidgets.QMessageBox.information(
                    self, "확인 사항", "\n\n".join(f"· {x}" for x in res.warnings))

        # ---------- 시작 안내 배너 (모달 아님) ----------
        def _startup_banner(self, migrate_note, db_default):
            """첫 실행·DB 이관 안내. 닫기 버튼이 있는 한 줄 배너."""
            if migrate_note:
                text = migrate_note.replace("\n", "  ")
            elif self._seeded:
                text = (f"이 폴더에 새 누적 DB 를 만들고 기준 실적 {self.store.count()}건을 "
                        f"적재했습니다 — {db_default}   "
                        "담당자가 바뀌면 Tool 폴더 전체를 넘기면 데이터도 함께 갑니다.")
            else:
                return None
            bar = QtWidgets.QWidget()
            bar.setObjectName("banner")
            h = QtWidgets.QHBoxLayout(bar)
            h.setContentsMargins(18, 8, 10, 8)
            lab = QtWidgets.QLabel("ℹ  " + text)
            lab.setObjectName("bannertext")
            lab.setWordWrap(True)
            close = QtWidgets.QPushButton("닫기")
            close.setFixedWidth(60)
            close.clicked.connect(bar.hide)
            h.addWidget(lab, 1)
            h.addWidget(close)
            return bar

        # ---------- 헤더 ----------
        def _header(self):
            """행복날개 로고 + 제목. 로고 파일이 없으면 이모지로 폴백한다."""
            from PySide6 import QtCore, QtGui

            bar = QtWidgets.QWidget()
            bar.setObjectName("header")
            hb = QtWidgets.QHBoxLayout(bar)
            hb.setContentsMargins(18, 12, 18, 12)
            hb.setSpacing(12)

            path = _C.logo_path()
            pm = QtGui.QPixmap(str(path)) if path else QtGui.QPixmap()
            if pm.isNull():
                text = "🦋  위례 공급가능용량 입찰 산정"
            else:
                text = "위례 공급가능용량 입찰 산정"
                # 원본은 120px 높이로 두고 여기서 줄인다. 배율 화면(125·150%)에서도
                # 흐려지지 않게 devicePixelRatio 만큼 크게 만든 뒤 비율을 심어 준다.
                h, dpr = 30, self.devicePixelRatioF() or 1.0
                sc = pm.scaledToHeight(round(h * dpr), QtCore.Qt.SmoothTransformation)
                sc.setDevicePixelRatio(dpr)
                mark = QtWidgets.QLabel()
                mark.setObjectName("headermark")
                mark.setPixmap(sc)
                mark.setAlignment(QtCore.Qt.AlignCenter)
                mark.setFixedSize(round(sc.width() / dpr) + 16, h + 12)
                hb.addWidget(mark)

            title = QtWidgets.QLabel(text)
            title.setObjectName("headertitle")
            hb.addWidget(title)
            hb.addStretch(1)
            return bar

        # ---------- 공급가능용량 산정 탭 ----------
        def _run_tab(self):
            from PySide6 import QtCore
            w = QtWidgets.QWidget()

            # ① 테스트 정보
            g1 = QtWidgets.QGroupBox("테스트 정보")
            f1 = QtWidgets.QFormLayout(g1)
            self.date_in = QtWidgets.QLineEdit()
            self.date_in.setPlaceholderText("예: 2026-01-06")
            self.start_in = QtWidgets.QLineEdit("17:00")
            self.start_in.setPlaceholderText("HH:MM (1시간 평균 창)")
            self.deg_in = QtWidgets.QDoubleSpinBox()
            self.deg_in.setRange(1.0, 1.2); self.deg_in.setSingleStep(0.001)
            self.deg_in.setDecimals(3); self.deg_in.setValue(C.DEFAULT_DEG)
            # IGV turn-up 실시 여부 — 보정값 = CC실측 − 이론 − W(IGV) 이므로, 안 한
            # turn-up 을 빼면 보정값이 4~6 MW 낮게 기록된다. 2026-08 시운전에서 8건 중
            # 3건이 미실시였고 그것이 미달로 오판됐다. 기본은 실시(체크).
            self.igv_chk = QtWidgets.QCheckBox("IGV Turn-up 실시")
            self.igv_chk.setChecked(True)
            self.igv_chk.setToolTip(
                "체크 : W(IGV) 를 온도밴드 기본값으로 적용 (여름 +6 / 봄·가을 +4 / 극저온 0)\n"
                "해제 : IGV Turn-up 미실시 시험 — 취득값만 보여 주고\n"
                "       '누적에 반영' 을 체크해도 누적에는 넣지 않습니다.\n\n"
                "담당자 방침입니다. IGV 실시 여부에 따라 출력 변동이 너무 커서,\n"
                "일관성을 위해 IGV 실시 시험만 보정값에 사용합니다.\n"
                "잘못 두고 반영하면 그 회차만이 아니라 보정곡선 전체가 오염됩니다.")
            # 상대습도 재정의 — MBL 습도 센서가 드리프트 중이라(10개월에 10%p) 취득값이
            # 담당자 표와 크게 어긋나는 회차가 있다(2026-05-27: MBL 32.5% vs 표 74.1%).
            # 습도 1개가 이론기준값과 보정값을 2.14 MW 움직이므로 손으로 고칠 수 있어야
            # 한다. 자동 대체는 하지 않는다 — 편차만으로는 정상·고장을 못 가른다.
            self.rh_in = QtWidgets.QDoubleSpinBox()
            self.rh_in.setRange(0.0, 100.0); self.rh_in.setDecimals(1)
            self.rh_in.setSingleStep(0.1); self.rh_in.setSuffix(" %")
            self.rh_in.setValue(60.0); self.rh_in.setEnabled(False)
            self.rh_auto = QtWidgets.QCheckBox("취득값 사용(RiMS)")
            self.rh_auto.setChecked(True)
            self.rh_auto.toggled.connect(
                lambda: self.rh_in.setEnabled(not self.rh_auto.isChecked()))
            self.rh_auto.setToolTip(
                "체크 : RiMS 취득 습도를 그대로 사용 (기본)\n"
                "해제 : 왼쪽 값으로 계산 — 취득 습도가 담당자 표와 크게 다를 때\n\n"
                "MBL 습도 센서가 드리프트 중입니다(10개월에 10%p).\n"
                "습도 1개가 보정값을 2 MW 넘게 움직이므로, 취득값이 의심되면\n"
                "담당자 표 값을 직접 넣으십시오. 수동 지정은 경고창에 기록됩니다.")
            f1.addRow("테스트 날짜", self.date_in)
            f1.addRow("시작 시각", self.start_in)
            f1.addRow("Degradation", self.deg_in)
            f1.addRow("상대습도 RH", self.rh_in)
            f1.addRow("", self.rh_auto)
            f1.addRow("", self.igv_chk)

            # ② 입찰 조건
            g2 = QtWidgets.QGroupBox("입찰 조건")
            f2 = QtWidgets.QFormLayout(g2)
            self.bidday_in = QtWidgets.QLineEdit()
            self.bidday_in.setPlaceholderText("입찰 적용일 라벨(선택, 미입력 시 7일 중위 평균)")
            self.forecast_in = self._file_row("대기압 윈드파인더 파일(.xlsx)")
            f2.addRow("입찰 적용일", self.bidday_in)
            f2.addRow("대기압 윈드파인더", self.forecast_in["row"])

            # ③ 실행 옵션 · 출력
            g3 = QtWidgets.QGroupBox("실행 옵션 · 출력")
            f3 = QtWidgets.QFormLayout(g3)
            self.accum_chk = QtWidgets.QCheckBox("이 테스트를 누적에 반영(저장)")
            self.accum_chk.setToolTip("체크 안 하면 확인용 — 보정값만 표시하고 누적에 저장하지 않습니다")
            self.method_cb = QtWidgets.QComboBox()
            self.method_cb.addItems(_METHOD_ITEMS)
            self.method_cb.setToolTip(
                "보정값 산출 방법\n"
                "  구간 평균     : 온도구간별 평균을 계단식 적용(엑셀4 방식)\n"
                "  커널회귀      : 이웃 실측의 거리가중 평균으로 1°C 단위 적용\n"
                "  GP · <커널>   : 가우시안 프로세스. 커널이 곡선의 성격을 정한다\n"
                "     RBF/Matérn 5/2/Matérn 3/2/지수 순으로 거칠어진다.\n"
                "     거친 커널은 실측을 잘 따라가지만 외삽·잡음에 약하다.\n"
                "     하이퍼파라미터는 커널마다 주변우도로 자동 적합한다.\n"
                "\n"
                "어느 방법이 나은지는 [🔬 모델 선정] 탭에서 LOOCV 로 확인하고,\n"
                "여기서 직접 고르십시오 — 자동으로 바뀌지 않습니다.\n"
                "\n"
                "선택한 방법은 누적 전체에 적용됩니다 — 과거 기록에 방법이 따로\n"
                "붙지 않습니다. 오늘 GP 로 돌리면 누적 전건을 GP 로 다시 적합합니다.\n"
                "선택은 저장되어 다음 실행에도 유지되고, 입찰파일 도장에 남습니다.\n"
                "결과는 [📈 출력곡선 비교] 탭에서 곡선으로 확인할 수 있습니다.")
            # 저장된 선택 복원 + 바꾸면 즉시 저장 (실행하지 않고 바꿔도 남는다)
            self.method_cb.setCurrentIndex(_method_index(_cf.correction_method()))
            self.method_cb.currentIndexChanged.connect(
                lambda i: _cf.set_config("correction_method", _METHODS[i]))
            # 출력 파일 경로는 여기서 받지 않는다. 실행은 계산·표시만 하고, 저장은
            # 아래 온도 프로파일 표의 [엑셀로 저장] 으로 그때 경로를 고른다 —
            # 실행할 때마다 파일이 덮어써지는 것을 막고, 결과를 보고 저장할지
            # 정할 수 있다.
            f3.addRow("", self.accum_chk)
            f3.addRow("보정 방법", self.method_cb)

            self.run_btn = QtWidgets.QPushButton("▶  공급가능용량 산정")
            self.run_btn.setObjectName("primary")
            self.run_btn.clicked.connect(self._on_run)

            self.summary = QtWidgets.QLabel("테스트 날짜·시각을 입력하고 실행하세요. "
                                            "(RiMS 서버는 최초 1회만 설정)")
            self.summary.setObjectName("summary")
            self.summary.setWordWrap(True)

            # 표 구성은 엑셀3 출력과 같은 목록(profile.PROFILE_COLUMNS)을 쓴다 —
            # 화면에서 본 것과 저장한 파일이 어긋나면 안 된다.
            self.profile_tbl = QtWidgets.QTableWidget(0, len(PROFILE_COLUMNS))
            self.profile_tbl.setHorizontalHeaderLabels(
                [_SHORT_HEAD.get(attr, h) for h, attr in PROFILE_COLUMNS])
            self.profile_tbl.setAlternatingRowColors(True)
            self.profile_tbl.verticalHeader().setVisible(False)
            hh = self.profile_tbl.horizontalHeader()
            hh.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)

            head = QtWidgets.QHBoxLayout()
            head.addWidget(QtWidgets.QLabel("온도별 예측 (−20 ~ 40°C, 61구간)"))
            head.addStretch(1)
            self.save_btn = QtWidgets.QPushButton("엑셀로 저장")
            self.save_btn.setEnabled(False)          # 산정 전에는 저장할 것이 없다
            self.save_btn.setToolTip(
                "지금 표에 있는 온도 프로파일을 엑셀3 입찰 양식으로 저장합니다.\n"
                "저장 시점의 누적 보정값 기준으로 다시 계산해 씁니다.")
            self.save_btn.clicked.connect(self._on_save_profile)
            head.addWidget(self.save_btn)

            # 레이아웃 — 두 가지 문제를 함께 고친다(2026-08 부장님 지적)
            #
            #  ⑦ 전체화면에서 입력부가 세로로 눌려 보인다
            #     세로로 쌓으면 입력 그룹은 최소 높이에 고정되고 표만 커져서,
            #     화면이 클수록 위쪽이 상대적으로 납작해 보인다.
            #     → 입력 그룹을 가로로 배치한다(테스트 정보 | 입찰 조건 + 실행 옵션).
            #
            #  ⑧ 창을 위에서 세로로 줄일 수 없다
            #     세로 최소 높이가 954px 이었다 — 270+132+153(입력) + 43+43+33+70.
            #     1080p 실사용 높이(~1040px)와 거의 같아 사실상 못 줄였다.
            #     → 입력부를 스크롤 영역에 담아 최소 높이를 풀고, 입력부와 표를
            #       QSplitter 로 나눠 비율을 사용자가 직접 잡게 한다.
            right = QtWidgets.QVBoxLayout()
            right.setContentsMargins(0, 0, 0, 0)
            right.addWidget(g2)
            right.addWidget(g3)
            right.addStretch(1)
            rw = QtWidgets.QWidget(); rw.setLayout(right)

            topw = QtWidgets.QWidget()
            top = QtWidgets.QHBoxLayout(topw)
            top.setContentsMargins(0, 0, 0, 0)
            top.setSpacing(10)
            top.addWidget(g1, stretch=1)
            top.addWidget(rw, stretch=1)

            inner = QtWidgets.QWidget()
            iv = QtWidgets.QVBoxLayout(inner)
            iv.setContentsMargins(0, 0, 0, 0)
            iv.setSpacing(8)
            iv.addWidget(topw)
            iv.addWidget(self.run_btn)
            iv.addWidget(self.summary)

            scroll = QtWidgets.QScrollArea()
            scroll.setWidget(inner)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(
                QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            # 스크롤 영역 자체의 최소 높이를 작게 잡아야 창이 줄어든다.
            scroll.setMinimumHeight(120)

            below = QtWidgets.QWidget()
            bv = QtWidgets.QVBoxLayout(below)
            bv.setContentsMargins(0, 0, 0, 0)
            bv.setSpacing(6)
            bv.addLayout(head)
            bv.addWidget(self.profile_tbl, stretch=1)

            self.profile_tbl.setMinimumHeight(80)
            split = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
            split.addWidget(scroll)
            split.addWidget(below)
            split.setStretchFactor(0, 0)
            split.setStretchFactor(1, 1)
            split.setSizes([330, 400])
            split.setChildrenCollapsible(False)

            lay = QtWidgets.QVBoxLayout(w)
            lay.setContentsMargins(8, 8, 8, 8)
            lay.addWidget(split)
            return w

        def _file_row(self, label):
            """파일 열기 입력줄. 저장 경로 입력은 없다 — 저장은 [엑셀로 저장] 버튼에서."""
            edit = QtWidgets.QLineEdit()
            edit.setPlaceholderText(label)
            btn = QtWidgets.QPushButton("찾아보기")
            row = QtWidgets.QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(edit); row.addWidget(btn)
            holder = QtWidgets.QWidget(); holder.setLayout(row)

            def pick():
                fn, _ = QtWidgets.QFileDialog.getOpenFileName(self, label, "", "Excel (*.xlsx)")
                if fn:
                    edit.setText(fn)
            btn.clicked.connect(pick)
            return {"row": holder, "edit": edit}

        # ---------- RiMS 커넥터 (설정 기반 — 화면에서 숨김) ----------
        def _connector(self):
            host = get_config("opcua_host")
            if not host:
                host, ok = QtWidgets.QInputDialog.getText(
                    self, "RiMS 서버 설정 (최초 1회)",
                    "DataPARC OPC UA 서버 호스트를 입력하세요.\n"
                    "저장 후에는 다시 묻지 않습니다 (~/.wirye_tool.json).")
                host = (host or "").strip()
                if not ok or not host:
                    return None
                set_config("opcua_host", host)
            from ..rims.opcua import OpcUaRimsConnector
            return OpcUaRimsConnector(host=host, cache_path=NODEID_CACHE)

        def _on_run(self):
            from PySide6 import QtCore, QtGui
            connector = self._connector()
            if connector is None:
                if QtWidgets.QMessageBox.question(
                        self, "RiMS 미설정",
                        "RiMS 서버가 설정되지 않았습니다.\n"
                        "신규 취득 없이 현재 누적값으로 입찰파일만 재생성할까요?"
                        ) != QtWidgets.QMessageBox.StandardButton.Yes:
                    return
            template = get_config("template_path") or C.resource(
                "templates", "excel3_profile_template.xlsx")
            # 긴 RiMS 취득 동안 UI 가 멈춘 것처럼 보이므로 버튼 비활성·대기 커서
            self.run_btn.setEnabled(False)
            QtGui.QGuiApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)
            try:
                res = run_pipeline(
                    date=self.date_in.text().strip(), store=self.store,
                    output_path=None,          # 저장은 [엑셀로 저장] 에서
                    connector=connector,
                    engine=self.engine, deg=self.deg_in.value(),
                    bid_day=self.bidday_in.text().strip() or None,
                    accumulate=self.accum_chk.isChecked(),
                    correction_method=_METHODS[self.method_cb.currentIndex()],
                    igv=self.igv_chk.isChecked(),
                    rh=None if self.rh_auto.isChecked() else self.rh_in.value(),
                    forecast_path=self.forecast_in["edit"].text().strip() or None,
                    template_path=template,
                    start=self.start_in.text().strip() or "17:00")
            except Exception as e:  # noqa: BLE001
                QtWidgets.QMessageBox.critical(self, "오류", str(e))
                return
            finally:
                QtGui.QGuiApplication.restoreOverrideCursor()
                self.run_btn.setEnabled(True)
            # 보정방법을 항상 보여 준다 — 시운전 중 방법을 바꿔 가며 비교할 때
            # 이 결과가 어느 방법으로 나온 건지 화면에서 바로 확인돼야 한다.
            msg = [f"적용 대기압 {res.applied_pressure:.1f} mbar",
                   f"누적 {res.measurement_count}건 전체를 "
                   f"{METHOD_LABEL.get(res.correction_method, res.correction_method)} 로 보정"]
            if res.new_record is not None:
                r = res.new_record
                st = ("⛔ IGV 미실시 — 누적 제외(방침)" if res.igv_skipped else
                      "⛔ 습도 확인 필요 — 누적 보류" if res.rh_unconfirmed else
                      "✅ 누적 반영됨" if res.reflected else
                      "⚠ 중복 — 건너뜀" if res.duplicate_skipped else "확인용(미반영)")
                if r.rh is None:
                    rh_txt = "RH 60%(고정)"
                else:
                    rh_txt = f"RH {r.rh:.1f}%"
                    if not self.rh_auto.isChecked():
                        rh_txt += "(수동)"
                    else:
                        # 취득 습도를 입력칸에 채워 둔다 — 값이 의심스러울 때
                        # 체크만 풀고 바로 고칠 수 있게(다시 입력하지 않도록).
                        self.rh_in.setValue(r.rh)
                # 취득 대기압을 반드시 같이 보여 준다 — 이론기준값은 대기압에
                # 0.4 MW/mbar 로 민감해서, 이 값이 없으면 담당자 표와 대조할 때
                # 0.1 MW 차이의 원인을 짚을 수 없다(2026-08 시운전 1회차에서 확인).
                msg.append(f"신규 취득  CIT {r.cit:.2f}°C · 취득 대기압 {r.press:.2f} mbar"
                           f" · {rh_txt} · CC실측 {r.cc_meas:.2f}"
                           f" · 이론 {r.theory:.2f} · W {r.w:+.0f}"
                           f" · 보정값 {r.corr:+.2f} MW  [{st}]")
            if res.output_path:
                msg.append(f"입찰 파일: {res.output_path}")
            self.summary.setText("    |    ".join(msg))
            # 취득 품질 경고는 요약줄에 묻히면 안 된다(CC실측 오차는 그대로 보정값 오차).
            if res.acq_warnings:
                QtWidgets.QMessageBox.warning(
                    self, "취득 값 확인 필요",
                    "RiMS 취득값에 확인이 필요한 사항이 있습니다.\n\n"
                    + "\n".join(f"· {w}" for w in res.acq_warnings)
                    + "\n\n엑셀1(fnTagStat) 값과 대조한 뒤 사용하세요.\n"
                      "진단: python scripts/cc_diagnose.py --host <서버> "
                      f"--date {res.date}")
            self._fill_profile(res.profile_rows)
            self._refresh_status(res.correction_table)
            self._refresh_list()
            self._refresh_chart()
            # [엑셀로 저장] 에서 같은 조건으로 다시 계산해 쓰기 위해 입력을 보관한다.
            # 결과 행을 그대로 들고 있지 않는 이유 — 엑셀3 양식은 템플릿을 채우는
            # 방식이라 run_pipeline 을 다시 타는 것이 유일한 정합 경로다.
            self._last_run = {
                "date": res.date, "deg": self.deg_in.value(),
                "bid_day": self.bidday_in.text().strip() or None,
                "method": _METHODS[self.method_cb.currentIndex()],
                "margin_k": 0.0,          # 안전마진은 화면에서 제거됨(CLI 전용)
                "forecast_path": self.forecast_in["edit"].text().strip() or None,
                "template": template, "fp": res.fingerprint,
            }
            self.save_btn.setEnabled(True)
            if res.reflected:
                self._check_bid_freshness()   # 누적이 변했으니 기존 파일은 구버전?

        def _fill_profile(self, rows):
            from PySide6 import QtCore
            self.profile_tbl.setRowCount(len(rows))
            for i, r in enumerate(rows):
                for j, (_, attr) in enumerate(PROFILE_COLUMNS):
                    v = getattr(r, attr)
                    txt = str(v) if attr == "temp" else f"{v:.2f}"
                    it = QtWidgets.QTableWidgetItem(txt)
                    it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight
                                        | QtCore.Qt.AlignmentFlag.AlignVCenter)
                    self.profile_tbl.setItem(i, j, it)

        # ---------- 온도 프로파일 → 엑셀3 입찰파일 저장 ----------
        def _on_save_profile(self):
            """표에 있는 프로파일을 엑셀3 양식으로 저장한다.

            결과 행을 그대로 쓰지 않고 run_pipeline 을 다시 탄다 — 엑셀3 는 템플릿
            셀을 채우는 방식이라 그 경로만이 양식과 정합한다. connector=None ·
            accumulate 안 함이므로 누적은 건드리지 않는다.
            """
            from PySide6 import QtCore, QtGui
            if not self._last_run:
                return
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "엑셀3 입찰파일로 저장",
                f"입찰_온도Profile_{self._last_run['date']}.xlsx",
                "Excel 파일 (*.xlsx)")
            if not path:
                return
            r = self._last_run
            # 산정 이후 누적이 바뀌었으면 저장되는 값이 화면과 달라진다. 먼저 알린다.
            fp_now = table_fingerprint(self.store.correction_table())
            if fp_now != r["fp"] and QtWidgets.QMessageBox.question(
                    self, "누적이 변경됨",
                    "산정 이후 누적 보정값이 바뀌었습니다.\n"
                    "지금 저장하면 화면의 값이 아니라 현재 누적 기준으로 저장됩니다.\n\n"
                    "계속할까요? (표도 새 값으로 갱신됩니다)"
                    ) != QtWidgets.QMessageBox.StandardButton.Yes:
                return
            QtGui.QGuiApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)
            try:
                res = run_pipeline(
                    date=r["date"], store=self.store, output_path=path, connector=None,
                    engine=self.engine, deg=r["deg"], bid_day=r["bid_day"],
                    correction_method=r["method"], margin_k=r["margin_k"],
                    forecast_path=r["forecast_path"], template_path=r["template"])
            except Exception as e:  # noqa: BLE001
                QtWidgets.QMessageBox.critical(self, "저장 실패", str(e))
                return
            finally:
                QtGui.QGuiApplication.restoreOverrideCursor()
            self._fill_profile(res.profile_rows)
            self._last_run["fp"] = res.fingerprint
            self._last_bid = {"path": res.output_path, "fp": res.fingerprint}
            self.summary.setText(f"엑셀3 입찰파일 저장 완료  —  {res.output_path}"
                                 f"    |    누적 {res.measurement_count}건 · "
                                 f"{METHOD_LABEL.get(res.correction_method)} · "
                                 f"적용 대기압 {res.applied_pressure:.1f} mbar")

        # ---------- 온도 구간별 보정값 현황 탭 (엑셀4 '보정값 현황' 재현) ----------
        def _status_tab(self):
            w = QtWidgets.QWidget()
            lay = QtWidgets.QVBoxLayout(w)
            cap = QtWidgets.QLabel(
                "온도구간별 보정값 현황 (엑셀4 '보정값 현황' 시트와 동일). "
                "🟢 자동반영 · 🔴 데이터 부족 · △ 보수적 고정 · ─ Shaft Limit")
            cap.setWordWrap(True)
            self.status_tbl = QtWidgets.QTableWidget(0, 6)
            self.status_tbl.setHorizontalHeaderLabels(
                ["온도구간", "종류", "건수/목표", "실측평균", "적용 보정값", "상태"])
            self.status_tbl.setAlternatingRowColors(True)
            self.status_tbl.horizontalHeader().setStretchLastSection(True)
            self.status_tbl.verticalHeader().setVisible(False)
            lay.addWidget(cap)
            lay.addWidget(self.status_tbl)
            return w

        def _refresh_status(self, table):
            rows = status_rows(table)
            self.status_tbl.setRowCount(len(rows))
            for i, r in enumerate(rows):
                cnt = f"{r['count']}/{r['target']}" if r["target"] else str(r["count"])
                avg = f"{r['avg']:+.2f}" if r["avg"] is not None else "-"
                applied = f"{r['applied']:+.2f}" if r["applied"] is not None else "-"
                vals = [r["bin_label"], r["kind_label"], cnt, avg, applied, r["status"]]
                for j, v in enumerate(vals):
                    self.status_tbl.setItem(i, j, QtWidgets.QTableWidgetItem(str(v)))

        # ---------- Test 결과 List-up 탭 ----------
        # ---------- 출력 시뮬레이션 탭 ----------
        def _sim_tab(self):
            from PySide6 import QtCore
            w = QtWidgets.QWidget()
            outer = QtWidgets.QHBoxLayout(w)

            # ── 좌: 조건 입력 ──
            left = QtWidgets.QVBoxLayout()
            g1 = QtWidgets.QGroupBox("운전 조건 (출력에 영향을 주는 값)")
            f1 = QtWidgets.QFormLayout(g1)

            def spin(lo, hi, val, dec=1, step=0.1, suffix=""):
                s = QtWidgets.QDoubleSpinBox()
                s.setRange(lo, hi)
                s.setDecimals(dec)
                s.setSingleStep(step)
                s.setValue(val)
                if suffix:
                    s.setSuffix(suffix)
                return s

            self.sim_cit = spin(-20, 40, 25.0, 1, 0.5, " °C")
            self.sim_press = spin(950, 1050, C.REF_PRESSURE, 1, 0.5, " mbar")
            self.sim_rh = spin(0, 100, 60.0, 1, 1.0, " %")
            self.sim_rh_auto = QtWidgets.QCheckBox("기준 60% 사용(습도보정 없음)")
            self.sim_rh_auto.setChecked(True)
            self.sim_rh_auto.setToolTip(
                "체크: 입찰 Profile과 동일하게 RH 60%(보정 없음)\n"
                "해제: 실측 RH를 반영 — 테스트 대조 시에는 해제하고 실측값 입력")
            self.sim_rh_auto.stateChanged.connect(
                lambda: self.sim_rh.setEnabled(not self.sim_rh_auto.isChecked()))
            self.sim_rh.setEnabled(False)
            self.sim_deg = spin(1.0, 1.2, C.DEFAULT_DEG, 3, 0.001)
            self.sim_w = spin(0, 12, 0.0, 1, 1.0, " MW")
            self.sim_w_auto = QtWidgets.QCheckBox("온도밴드 자동")
            self.sim_w_auto.setChecked(True)
            self.sim_w_auto.setToolTip(
                "IGV turn-up 자동 산정: ≤−2°C=0 / −1°C=+2 / 0~24°C=+4 / 25°C↑=+6")
            self.sim_w_auto.stateChanged.connect(
                lambda: self.sim_w.setEnabled(not self.sim_w_auto.isChecked()))
            self.sim_w.setEnabled(False)
            self.sim_cp = spin(0, 200, 0.0, 1, 0.5)
            self.sim_cp_use = QtWidgets.QCheckBox("복수기압 입력(참고용)")
            self.sim_cp_use.setToolTip(
                "복수기(콘덴서) 보정은 base 테이블에 ISO 조건으로 동결되어 있어\n"
                "이론값 계산에 직접 반영되지 않습니다.\n"
                "입력하면 유사 온도 실측의 설계값 대비 편차를 참고로 표시합니다.")
            self.sim_cp_use.stateChanged.connect(
                lambda: self.sim_cp.setEnabled(self.sim_cp_use.isChecked()))
            self.sim_cp.setEnabled(False)

            f1.addRow("외기온도 CIT", self.sim_cit)
            f1.addRow("대기압", self.sim_press)
            f1.addRow("상대습도 RH", self.sim_rh)
            f1.addRow("", self.sim_rh_auto)
            f1.addRow("Degradation", self.sim_deg)
            f1.addRow("W (IGV turn-up)", self.sim_w)
            f1.addRow("", self.sim_w_auto)
            f1.addRow("복수기압 실측", self.sim_cp)
            f1.addRow("", self.sim_cp_use)

            # ② 실측 대조
            g2 = QtWidgets.QGroupBox("실측 대조 (테스트 후 입력 — 선택)")
            f2 = QtWidgets.QFormLayout(g2)
            self.sim_meas = spin(0, 600, 0.0, 2, 0.1, " MW")
            self.sim_meas_use = QtWidgets.QCheckBox("실측 CC(Gross)와 비교")
            self.sim_meas_use.setToolTip(
                "테스트가 끝난 뒤 실측 CC Gross를 넣으면\n"
                "실측 보정값·예상과의 차이·±0.5% 밴드 판정을 바로 보여줍니다.")
            self.sim_meas_use.stateChanged.connect(
                lambda: self.sim_meas.setEnabled(self.sim_meas_use.isChecked()))
            self.sim_meas.setEnabled(False)
            f2.addRow("실측 CC (Gross)", self.sim_meas)
            f2.addRow("", self.sim_meas_use)

            # ③ 보정 옵션
            g3 = QtWidgets.QGroupBox("보정 옵션")
            f3 = QtWidgets.QFormLayout(g3)
            self.sim_method = QtWidgets.QComboBox()
            self.sim_method.addItems(_METHOD_ITEMS)
            # 입찰에 쓰는 방법과 같은 값으로 시작한다 — 예측 vs 실측 대조가 어긋나면
            # 안 되기 때문이다. 여기서 바꾸는 것은 저장하지 않는다(비교는 자유롭게).
            self.sim_method.setCurrentIndex(_method_index(_cf.correction_method()))
            f3.addRow("보정 방법", self.sim_method)

            self.sim_btn = QtWidgets.QPushButton("🧪  시뮬레이션 실행")
            self.sim_btn.setObjectName("primary")
            self.sim_btn.clicked.connect(self._on_simulate)

            left.addWidget(g1)
            left.addWidget(g2)
            left.addWidget(g3)
            left.addWidget(self.sim_btn)
            left.addStretch(1)

            # ── 우: 결과 ──
            right = QtWidgets.QVBoxLayout()
            self.sim_big = QtWidgets.QLabel("조건을 입력하고 [시뮬레이션 실행]")
            self.sim_big.setObjectName("summary")
            self.sim_big.setWordWrap(True)
            self.sim_out = QtWidgets.QPlainTextEdit()
            self.sim_out.setReadOnly(True)
            self.sim_out.setStyleSheet(
                "font-family: 'Consolas','D2Coding',monospace; font-size: 10pt;"
                "background:#FFFFFF; border:1px solid #EDE4DF; border-radius:8px; padding:8px;")
            right.addWidget(self.sim_big)
            right.addWidget(self.sim_out, stretch=1)

            # 좌측 입력 열은 스크롤 영역에 담는다 — 이 탭의 세로 최소높이가 673px
            # 이어서 창 전체 축소를 막고 있었다(2026-08 부장님 지적 ⑧).
            lw = QtWidgets.QWidget(); lw.setLayout(left)
            lscroll = QtWidgets.QScrollArea()
            lscroll.setWidget(lw)
            lscroll.setWidgetResizable(True)
            lscroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
            lscroll.setHorizontalScrollBarPolicy(
                QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            lscroll.setMinimumHeight(120)
            lscroll.setMinimumWidth(lw.sizeHint().width() + 24)
            lscroll.setMaximumWidth(lw.sizeHint().width() + 24)
            outer.addWidget(lscroll, stretch=0)
            outer.addLayout(right, stretch=1)
            return w

        def _on_simulate(self):
            from ..simulate import SimInput, format_result, simulate

            recs = [{"cit": r["cit"], "corr": r["corr"], "cp_meas": r.get("cp_meas"),
                     "cp_design": r.get("cp_design")} for r in self.store.list_up()]
            table = self.store.correction_table()
            corrector = _sel.make_corrector(
                _METHODS[self.sim_method.currentIndex()], recs)

            inp = SimInput(
                cit=self.sim_cit.value(),
                pressure=self.sim_press.value(),
                rh=None if self.sim_rh_auto.isChecked() else self.sim_rh.value(),
                deg=self.sim_deg.value(),
                w=None if self.sim_w_auto.isChecked() else self.sim_w.value(),
                cp_meas=self.sim_cp.value() if self.sim_cp_use.isChecked() else None,
                cc_meas=self.sim_meas.value() if self.sim_meas_use.isChecked() else None)
            try:
                res = simulate(inp, engine=self.engine, records=recs,
                               correction_table=table, corrector=corrector)
            except Exception as e:  # noqa: BLE001
                QtWidgets.QMessageBox.critical(self, "시뮬레이션 오류", str(e))
                return
            big = f"예상 입찰값 (Net)   {res.real_net:.2f} MW"
            if res.meas_net is not None:
                verdict = ("⚠ 미달" if res.shortfall else
                           "✅ 밴드 안" if res.in_band else "실측이 밴드보다 높음")
                big += (f"\n실측 Net {res.meas_net:.2f} MW"
                        f"  ·  차이 {res.net_diff:+.2f} MW  ·  {verdict}")
            self.sim_big.setText(big)
            self.sim_out.setPlainText(format_result(res, inp))

        # ---------- 출력곡선 비교 탭 ----------
        def _chart_tab(self):
            from .chart import CurveChart

            w = QtWidgets.QWidget()
            lay = QtWidgets.QVBoxLayout(w)

            bar = QtWidgets.QHBoxLayout()
            self.chart_method = QtWidgets.QComboBox()
            self.chart_method.addItems(_METHOD_ITEMS)
            self.chart_method.setCurrentIndex(_method_index(_cf.correction_method()))
            self.chart_method.setToolTip(
                "보정값 산출 방법. GP 는 커널별로 곡선 성격이 다르다 —\n"
                "여기서 바꿔 가며 눈으로 비교할 수 있다.")
            self.chart_method.currentIndexChanged.connect(self._refresh_chart)
            self.chart_pts = QtWidgets.QCheckBox("실측점")
            self.chart_pts.setChecked(True)
            self.chart_pts.stateChanged.connect(self._refresh_chart)
            self.chart_band = QtWidgets.QCheckBox("예측구간(GP)")
            self.chart_band.setChecked(True)
            self.chart_band.stateChanged.connect(self._refresh_chart)
            bar.addWidget(QtWidgets.QLabel("보정 방법"))
            bar.addWidget(self.chart_method)
            bar.addSpacing(10)
            bar.addWidget(self.chart_pts)
            bar.addWidget(self.chart_band)
            bar.addStretch(1)
            self.chart_info = QtWidgets.QLabel()
            self.chart_info.setStyleSheet("color:#6b7382;")
            bar.addWidget(self.chart_info)

            self.chart = CurveChart()
            lay.addLayout(bar)
            lay.addWidget(self.chart, stretch=1)
            note = QtWidgets.QLabel(
                "위 곡선: 이론값(보정 없음) vs 현실화 Net(보정 반영, 입찰값) · "
                "아래 곡선: 온도별 보정값과 실측점. 마우스를 올리면 해당 온도 값이 표시됩니다.")
            note.setWordWrap(True)
            note.setStyleSheet("color:#6b7382; font-size:11px;")
            lay.addWidget(note)
            return w

        def _refresh_chart(self, *_):
            """누적 실측 기준으로 곡선 재생성."""
            if not hasattr(self, "chart"):
                return
            recs = [{"cit": r["cit"], "corr": r["corr"]} for r in self.store.list_up()]
            if not recs:
                self.chart.set_data([], [])
                self.chart_info.setText("누적 데이터 없음")
                return
            table = self.store.correction_table()
            method = _METHODS[self.chart_method.currentIndex()]
            corrector = _sel.make_corrector(method, recs)
            sigma_fn = getattr(corrector, "sigma", None)
            rows = build_profile(self.engine, table, corrector=corrector)
            self.chart.set_toggles(points=self.chart_pts.isChecked(),
                                   band=self.chart_band.isChecked())
            self.chart.set_data(rows, [(r["cit"], r["corr"]) for r in recs],
                                sigma_fn=sigma_fn, margin_fn=None)
            msg = f"누적 {len(recs)}건 · {_sel.METHOD_LABEL[method]}"
            if getattr(corrector, "hyper", None):
                ls, _sf, sn = corrector.hyper
                msg += f" · 길이척도 {ls:.0f}°C 노이즈 {sn:.1f} MW"
            self.chart_info.setText(msg)

        def _list_tab(self):
            w = QtWidgets.QWidget()
            lay = QtWidgets.QVBoxLayout(w)
            bar = QtWidgets.QHBoxLayout()
            hint = QtWidgets.QLabel(
                "셀을 더블클릭하면 값을 고칠 수 있습니다(날짜·CIT·대기압·RH·CC실측·W·계절). "
                "이론기준값·보정값은 저장할 때 자동으로 다시 계산됩니다.\n"
                "삭제는 행을 선택해 [삭제 표시]. 편집·삭제 모두 [💾 저장]을 눌러야 반영되고, "
                "그 전에는 [되돌리기]로 취소할 수 있습니다.")
            hint.setWordWrap(True)
            self.del_btn = QtWidgets.QPushButton("🗑 삭제 표시")
            self.del_btn.setObjectName("danger")
            self.del_btn.clicked.connect(self._on_mark_delete)
            self.undo_btn = QtWidgets.QPushButton("되돌리기")
            self.undo_btn.clicked.connect(self._on_undo_delete)
            self.save_btn = QtWidgets.QPushButton("💾 저장")
            self.save_btn.setObjectName("primary")
            self.save_btn.setMaximumWidth(140)
            self.save_btn.clicked.connect(self._on_save_deletes)
            bar.addWidget(hint, stretch=1)
            bar.addWidget(self.del_btn)
            bar.addWidget(self.undo_btn)
            bar.addWidget(self.save_btn)
            self.list_tbl = QtWidgets.QTableWidget(0, len(self.LIST_COLS))
            self.list_tbl.setHorizontalHeaderLabels([c[1] for c in self.LIST_COLS])
            self.list_tbl.setAlternatingRowColors(True)
            self.list_tbl.horizontalHeader().setStretchLastSection(True)
            self.list_tbl.verticalHeader().setVisible(False)
            self.list_tbl.setSelectionBehavior(
                QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            # 더블클릭으로만 편집 — 클릭 한 번에 값이 바뀌면 사고가 난다.
            self.list_tbl.setEditTriggers(
                QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked
                | QtWidgets.QAbstractItemView.EditTrigger.EditKeyPressed)
            self.list_tbl.itemChanged.connect(self._on_cell_edited)
            lay.addLayout(bar)
            lay.addWidget(self.list_tbl)
            self._pending_del = set()          # 삭제 대기 id (저장 시 확정)
            self._pending_edit = {}            # id → {필드: 새값} (저장 시 확정)
            self._loading_list = False         # 표 채우는 중 itemChanged 무시용
            self._update_del_buttons()
            return w

        # (필드, 헤더, 소수자리, 편집가능) — 필드 None 은 표시 전용
        LIST_COLS = (
            ("date", "날짜", None, True),
            ("cit", "CIT(°C)", 1, True),
            ("press", "대기압(mbar)", 1, True),
            ("rh", "RH(%)", 1, True),
            ("cc_meas", "CC실측", 2, True),
            ("w", "W(IGV)", 0, True),
            ("theory", "이론기준값", 2, False),
            ("corr", "보정값", 2, False),
            ("season", "계절", None, True),
        )

        def _cell_text(self, r, field, dp):
            v = r.get(field)
            if v is None:
                return "" if field in ("season", "rh") else "-"
            if dp is None:
                return str(v)
            return f"{v:+.{dp}f}" if field in ("corr", "w") else f"{v:.{dp}f}"

        def _refresh_list(self):
            from PySide6 import QtCore, QtGui
            self._loading_list = True            # 채우는 동안 itemChanged 무시
            try:
                self._list_rows = self.store.list_up(order="date")   # id 포함
                self.list_tbl.setRowCount(len(self._list_rows))
                for i, r in enumerate(self._list_rows):
                    edits = self._pending_edit.get(r["id"], {})
                    marked = r["id"] in self._pending_del
                    for j, (field, _h, dp, editable) in enumerate(self.LIST_COLS):
                        # 편집 대기값이 있으면 그걸 보여준다(저장 전 확인용)
                        src = dict(r, **edits) if edits else r
                        item = QtWidgets.QTableWidgetItem(self._cell_text(src, field, dp))
                        if not editable:         # 파생값 — 편집 불가 + 회색 배경
                            item.setFlags(item.flags()
                                          & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                            item.setBackground(QtGui.QColor("#F6F2F0"))
                            item.setToolTip("이론기준값·보정값은 저장 시 자동 재계산됩니다.")
                        if field in edits:       # 고친 셀 — 주황 강조
                            item.setBackground(QtGui.QColor("#FFE8D8"))
                            f = item.font(); f.setBold(True); item.setFont(f)
                        if marked:               # 삭제 대기 행 — 취소선 + 회색
                            f = item.font(); f.setStrikeOut(True); item.setFont(f)
                            item.setForeground(QtGui.QColor("#B9AFA9"))
                        self.list_tbl.setItem(i, j, item)
            finally:
                self._loading_list = False
            self._update_del_buttons()

        # ---------- 셀 편집 ----------
        def _on_cell_edited(self, item):
            """편집된 값을 검증해 _pending_edit 에 담는다. DB 는 저장 시에만 바꾼다."""
            if self._loading_list:
                return
            row, col = item.row(), item.column()
            if row >= len(self._list_rows):
                return
            rec = self._list_rows[row]
            field, header, dp, editable = self.LIST_COLS[col]
            if not editable:
                return
            text = item.text().strip()
            old = self._pending_edit.get(rec["id"], {}).get(field, rec.get(field))
            try:
                new = self._parse_cell(field, text)
            except ValueError as e:
                QtWidgets.QMessageBox.warning(self, "값 확인", f"{header}: {e}")
                self._refresh_list()             # 원래 값으로 되돌림
                return
            # 표시 자릿수 때문에 같은 값이 '변경'으로 잡히지 않게 반올림 비교
            same = (new == old) or (
                isinstance(new, float) and isinstance(old, (int, float))
                and dp is not None and round(new, dp) == round(old, dp))
            edits = self._pending_edit.setdefault(rec["id"], {})
            if same:
                edits.pop(field, None)
                if not edits:
                    self._pending_edit.pop(rec["id"], None)
            else:
                edits[field] = new
            self._refresh_list()

        @staticmethod
        def _parse_cell(field, text):
            """셀 문자열 → 저장할 값. 물리적으로 불가능한 값은 여기서 막는다."""
            if field == "season":
                return text or None
            if field == "date":
                if not text or text == "-":
                    return None
                from datetime import datetime
                try:
                    datetime.strptime(text, "%Y-%m-%d")
                except ValueError:
                    raise ValueError("날짜는 YYYY-MM-DD 형식으로 입력하세요 (예: 2026-03-04)")
                return text
            if field == "rh" and text in ("", "-"):
                return None                      # 비우면 이론계산 60% 고정
            try:
                v = float(text.replace("+", ""))
            except ValueError:
                raise ValueError(f"숫자를 입력하세요 (입력값: '{text}')")
            limits = {"cit": (-40.0, 60.0, "°C"), "press": (900.0, 1100.0, "mbar"),
                      "rh": (0.0, 100.0, "%"), "cc_meas": (0.0, 600.0, "MW"),
                      "w": (-20.0, 20.0, "MW")}
            lo, hi, unit = limits[field]
            if not lo <= v <= hi:
                raise ValueError(f"{lo:g} ~ {hi:g} {unit} 범위로 입력하세요 (입력값: {v:g})")
            return v

        def _update_del_buttons(self):
            nd = len(getattr(self, "_pending_del", set()))
            ne = len(getattr(self, "_pending_edit", {}))
            self.save_btn.setEnabled(nd + ne > 0)
            self.undo_btn.setEnabled(nd + ne > 0)
            parts = ([f"{ne}건 수정"] if ne else []) + ([f"{nd}건 삭제"] if nd else [])
            self.save_btn.setText("💾 저장" + (f" ({' · '.join(parts)})" if parts else ""))

        def _on_mark_delete(self):
            sel = sorted({ix.row() for ix in self.list_tbl.selectedIndexes()})
            if not sel:
                QtWidgets.QMessageBox.information(self, "선택 없음", "삭제할 행을 선택하세요.")
                return
            for r in sel:
                self._pending_del.add(self._list_rows[r]["id"])
            self._refresh_list()               # 취소선 표시(아직 DB 반영 없음)

        def _on_undo_delete(self):
            self._pending_del.clear()
            self._pending_edit.clear()
            self._refresh_list()

        def _on_save_deletes(self):
            """편집·삭제를 한 번에 확정한다. 수정 먼저, 그다음 삭제."""
            edits = {k: dict(v) for k, v in self._pending_edit.items() if v}
            ids = set(self._pending_del)
            if not edits and not ids:
                return
            by_id = {r["id"]: r for r in self._list_rows}
            lines = []
            for rid, ch in edits.items():
                r = by_id.get(rid, {})
                what = ", ".join(
                    f"{h}: {self._cell_text(r, f, dp)} → "
                    f"{self._cell_text(ch, f, dp) if ch.get(f) is not None else '(비움)'}"
                    for f, h, dp, _e in self.LIST_COLS if f in ch)
                lines.append(f"  [수정] {r.get('date') or '-'}  {what}")
            for t in (by_id[i] for i in ids if i in by_id):
                lines.append(f"  [삭제] {t.get('date') or '-'}  "
                             f"(CIT {t['cit']:.1f}°C, 보정 {t['corr']:+.2f})")
            if QtWidgets.QMessageBox.warning(
                    self, "변경 저장",
                    f"다음 {len(edits)}건 수정 / {len(ids)}건 삭제를 반영합니다.\n"
                    "(이론기준값·보정값이 다시 계산되고 보정 테이블이 재집계됩니다. "
                    "되돌릴 수 없습니다)\n\n" + "\n".join(lines),
                    QtWidgets.QMessageBox.StandardButton.Yes
                    | QtWidgets.QMessageBox.StandardButton.No
                    ) != QtWidgets.QMessageBox.StandardButton.Yes:
                return
            failed = []
            for rid, ch in edits.items():
                try:
                    # CIT 를 고쳤고 W 는 손대지 않았다면 W 를 온도밴드로 다시 산정
                    self.store.update(rid, recalc_w=("cit" in ch and "w" not in ch), **ch)
                except Exception as e:                       # noqa: BLE001
                    failed.append(f"id {rid}: {e}")
            for rec_id in ids:
                self.store.delete(rec_id)
            self._pending_del.clear()
            self._pending_edit.clear()
            self._refresh_list()
            if failed:
                QtWidgets.QMessageBox.critical(
                    self, "일부 저장 실패", "\n".join(failed))
            self._refresh_status(self.store.correction_table())   # 즉시 재집계 반영
            self._refresh_chart()
            self._check_bid_freshness()                            # 기존 입찰파일 구버전 감지

        # ---------- 입찰파일 최신성 감시 (누적 변경 → 재생성 유도) ----------
        def _check_bid_freshness(self):
            if not self._last_bid:
                return
            fp_now = table_fingerprint(self.store.correction_table())
            if fp_now == self._last_bid["fp"]:
                return
            name = Path(self._last_bid["path"]).name
            if QtWidgets.QMessageBox.warning(
                    self, "입찰파일 구버전 경고",
                    f"누적이 변경되어 보정값이 바뀌었습니다.\n"
                    f"이미 생성한 입찰파일이 이전 보정값 기준입니다:\n\n    {name}\n\n"
                    f"현재 누적 기준으로 다시 생성할까요? (RiMS 재취득 없이 빠르게 재생성)",
                    QtWidgets.QMessageBox.StandardButton.Yes
                    | QtWidgets.QMessageBox.StandardButton.No
                    ) != QtWidgets.QMessageBox.StandardButton.Yes:
                self._last_bid = None      # 사용자가 거부 → 더 묻지 않음(파일은 구버전 상태)
                return
            self._regenerate_bid()

        def _regenerate_bid(self):
            """RiMS 재취득 없이 현재 누적으로 마지막 입찰파일을 다시 생성."""
            from PySide6 import QtCore, QtGui
            template = get_config("template_path") or C.resource(
                "templates", "excel3_profile_template.xlsx")
            QtGui.QGuiApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)
            try:
                res = run_pipeline(
                    date=self.date_in.text().strip(), store=self.store,
                    output_path=self._last_bid["path"], connector=None,
                    engine=self.engine, deg=self.deg_in.value(),
                    bid_day=self.bidday_in.text().strip() or None,
                    correction_method=_METHODS[self.method_cb.currentIndex()],
                    igv=self.igv_chk.isChecked(),
                    forecast_path=self.forecast_in["edit"].text().strip() or None,
                    template_path=template,
                    start=self.start_in.text().strip() or "17:00")
            except Exception as e:  # noqa: BLE001
                QtWidgets.QMessageBox.critical(self, "재생성 오류", str(e))
                return
            finally:
                QtGui.QGuiApplication.restoreOverrideCursor()
            self._last_bid = {"path": res.output_path, "fp": res.fingerprint}
            self.summary.setText(f"♻ 입찰파일 재생성 완료 (현재 누적 {res.measurement_count}건 기준)"
                                 f"    |    {res.output_path}")
            self._fill_profile(res.profile_rows)

    stage("QApplication 생성")
    app = QtWidgets.QApplication(argv or sys.argv)
    stage(f"Qt 플랫폼 '{app.platformName()}' · 화면 "
          + " / ".join(f"{s.geometry().width()}x{s.geometry().height()}"
                       f"@({s.geometry().x()},{s.geometry().y()})"
                       for s in app.screens()))
    app.setStyleSheet(QSS)
    _logo = _C.logo_path()
    if _logo:                       # 작업표시줄·창 좌상단 아이콘도 같은 로고로
        from PySide6 import QtGui
        app.setWindowIcon(QtGui.QIcon(str(_logo)))
    stage("MainWindow 생성")
    win = MainWindow()
    stage("show() 호출")
    win.show()
    # 창이 '보이는 상태' 로 어디에 놓였는지 남긴다. 사용자는 아무것도 못 봤는데
    # 여기에 visible=True 로 찍히면 표시 문제(화면 밖·다른 모니터·원격세션)다.
    g = win.geometry()
    stage(f"창 상태 visible={win.isVisible()} "
          f"{g.width()}x{g.height()}@({g.x()},{g.y()}) 최소화={win.isMinimized()}")
    stage("이벤트 루프 진입 — 여기까지 찍히면 시작은 성공이다")
    rc = app.exec()
    stage(f"이벤트 루프 종료 (rc={rc})")
    return rc


if __name__ == "__main__":  # pragma: no cover
    main()
