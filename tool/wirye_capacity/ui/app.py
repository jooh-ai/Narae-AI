"""위례 공급가능용량 입찰 산정 — Windows 데스크톱 GUI (PySide6).

사내 PC에서 실행:  python -m wirye_capacity.ui.app
로직은 pipeline.run_pipeline 에 위임하고, 이 모듈은 입력/표시만 담당하는 얇은 셸이다.

자동화 원칙(사용자 확정): 화면 입력은 날짜·시각 중심. RiMS(OPC UA) 서버 호스트는
설정(~/.wirye_tool.json)에 최초 1회 저장 후 화면에서 숨김. 엑셀3 템플릿은 번들 사용
(비상시 설정파일 template_path 로 오버라이드).

화면:
  [공급가능용량 산정]      날짜·시각 입력 → RiMS 자동취득 → 보정 → 엑셀3 입찰파일
  [온도 구간별 보정값 현황] 엑셀4 '보정값 현황' 재현 (실행 시 자동 갱신)
  [Test List-up]           누적 테스트 목록
"""
from __future__ import annotations

import sys
from pathlib import Path

from .. import constants as C
from ..config import get_config, set_config
from ..correction import status_rows, table_fingerprint
from ..pipeline import run_pipeline
from ..profile import build_profile
from ..store import MeasurementStore
from ..theory import TheoryEngine

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
    _require_qt()
    from PySide6 import QtWidgets

    # 누적 DB 는 Tool 폴더에 둔다 — 담당자가 바뀌면 폴더째 인수인계하면 데이터가 함께 간다.
    # 쓰기 불가(예: Program Files 설치)면 홈 폴더로 폴백. CLI·스크립트와 같은 함수를 쓴다.
    from .. import constants as _C
    from ..store import migrate_legacy_db
    db_default = str(_C.db_path())
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
            self._last_bid = None      # 마지막 생성 입찰파일 {path, fp} — 구버전 감지용

            tabs = QtWidgets.QTabWidget()
            tabs.addTab(self._run_tab(), "공급가능용량 산정")
            tabs.addTab(self._status_tab(), "온도 구간별 보정값 현황")
            tabs.addTab(self._list_tab(), "Test 결과 List-up")
            tabs.addTab(self._sim_tab(), "🧪 출력 시뮬레이션")
            tabs.addTab(self._chart_tab(), "📈 출력곡선 비교")

            header = self._header()
            central = QtWidgets.QWidget()
            v = QtWidgets.QVBoxLayout(central)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(0)
            v.addWidget(header)
            v.addWidget(tabs)
            self.setCentralWidget(central)
            self._refresh_list()
            self._refresh_status(self.store.correction_table())   # 시작 시 현재 누적 기준
            self._refresh_chart()
            # 누적이 어느 파일에 쌓이는지 항상 보이게 한다 — 배포본을 여러 명이 각자
            # 쓰면 DB 도 각자 생기므로, 지금 보고 있는 게 어느 DB 인지 헷갈리면 안 된다.
            self.statusBar().showMessage(f"누적 DB : {db_default}   ({self.store.count()}건)")
            if migrate_note:
                QtWidgets.QMessageBox.information(self, "누적 DB 위치 변경", migrate_note)
            elif self._seeded:
                QtWidgets.QMessageBox.information(
                    self, "누적 DB 생성",
                    f"이 폴더에 새 누적 DB 를 만들고 기준 실적 {self.store.count()}건을 "
                    f"적재했습니다.\n\n{db_default}\n\n"
                    "이 파일에 시험 결과가 쌓입니다. 담당자가 바뀌면 Tool 폴더 전체를 "
                    "넘기면 데이터도 함께 갑니다.")

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
            f1.addRow("테스트 날짜", self.date_in)
            f1.addRow("시작 시각", self.start_in)
            f1.addRow("Degradation", self.deg_in)

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
            self.method_cb.addItems(["구간 평균 (기본)", "커널 보정곡선", "GP (가우시안 프로세스)"])
            self.method_cb.setToolTip(
                "보정값 산출 방법 — 실측 32건 LOOCV 예측오차(MAE)\n"
                "  구간 평균 1.419 MW : 온도구간별 평균을 계단식 적용(엑셀4 방식)\n"
                "  커널 보정곡선 1.341 MW : 이웃 실측의 거리가중 평균으로 1°C 단위 적용\n"
                "  GP 1.243 MW : 커널 + 예측 불확실성 산출. 예측오차 최소\n"
                "결과는 [📈 출력곡선 비교] 탭에서 곡선으로 확인할 수 있습니다.")
            self.margin_sb = QtWidgets.QDoubleSpinBox()
            self.margin_sb.setRange(0.0, 3.0)
            self.margin_sb.setSingleStep(0.1)
            self.margin_sb.setValue(0.0)
            self.margin_sb.setSuffix(" ×")
            self.margin_sb.setToolTip(
                "미달 방지 안전마진 = 계수 × 구간별 실측변동\n"
                "  0     : 마진 없음 — 예측오차 최소(MAE 1.243 MW), 시드 기준 미달 2건\n"
                "  0.8   : 시드 32건 기준 미달 0건 (오차는 커지지만 전부 안전한 방향)\n"
                "실측이 없는 특수구간(Shaft Limit·보수적 고정)에는 적용되지 않습니다.")
            self.out_in = self._file_row("출력 엑셀3 입찰파일(.xlsx)", save=True)
            f3.addRow("", self.accum_chk)
            f3.addRow("보정 방법", self.method_cb)
            f3.addRow("안전마진 계수", self.margin_sb)
            f3.addRow("출력 파일", self.out_in["row"])

            self.run_btn = QtWidgets.QPushButton("▶  공급가능용량 산정 · 입찰파일 생성")
            self.run_btn.setObjectName("primary")
            self.run_btn.clicked.connect(self._on_run)

            self.summary = QtWidgets.QLabel("테스트 날짜·시각을 입력하고 실행하세요. "
                                            "(RiMS 서버는 최초 1회만 설정)")
            self.summary.setObjectName("summary")
            self.summary.setWordWrap(True)

            self.profile_tbl = QtWidgets.QTableWidget(0, 4)
            self.profile_tbl.setHorizontalHeaderLabels(
                ["온도(°C)", "CC 이론", "보정값", "CC 현실화 Net"])
            self.profile_tbl.setAlternatingRowColors(True)
            self.profile_tbl.horizontalHeader().setStretchLastSection(True)
            self.profile_tbl.verticalHeader().setVisible(False)

            lay = QtWidgets.QVBoxLayout(w)
            lay.setSpacing(10)
            lay.addWidget(g1)
            lay.addWidget(g2)
            lay.addWidget(g3)
            lay.addWidget(self.run_btn)
            lay.addWidget(self.summary)
            lay.addWidget(self.profile_tbl, stretch=1)
            return w

        def _file_row(self, label, save=False):
            edit = QtWidgets.QLineEdit()
            edit.setPlaceholderText(label)
            btn = QtWidgets.QPushButton("찾아보기")
            row = QtWidgets.QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(edit); row.addWidget(btn)
            holder = QtWidgets.QWidget(); holder.setLayout(row)

            def pick():
                if save:
                    fn, _ = QtWidgets.QFileDialog.getSaveFileName(self, label, "", "Excel (*.xlsx)")
                else:
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
                    output_path=self.out_in["edit"].text().strip() or None,
                    connector=connector,
                    engine=self.engine, deg=self.deg_in.value(),
                    bid_day=self.bidday_in.text().strip() or None,
                    accumulate=self.accum_chk.isChecked(),
                    correction_method=("gp" if self.method_cb.currentIndex() == 2 else
                                       "curve" if self.method_cb.currentIndex() == 1 else "bin"),
                    margin_k=self.margin_sb.value(),
                    forecast_path=self.forecast_in["edit"].text().strip() or None,
                    template_path=template,
                    start=self.start_in.text().strip() or "17:00")
            except Exception as e:  # noqa: BLE001
                QtWidgets.QMessageBox.critical(self, "오류", str(e))
                return
            finally:
                QtGui.QGuiApplication.restoreOverrideCursor()
                self.run_btn.setEnabled(True)
            msg = [f"적용 대기압 {res.applied_pressure:.1f} mbar",
                   f"누적 {res.measurement_count}건"]
            if res.new_record is not None:
                r = res.new_record
                st = ("✅ 누적 반영됨" if res.reflected else
                      "⚠ 중복 — 건너뜀" if res.duplicate_skipped else "확인용(미반영)")
                rh_txt = f"RH {r.rh:.1f}%" if r.rh is not None else "RH 60%(고정)"
                msg.append(f"신규 취득  CIT {r.cit:.2f}°C · {rh_txt} · CC실측 {r.cc_meas:.2f}"
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
            if res.output_path:
                self._last_bid = {"path": res.output_path, "fp": res.fingerprint}
            elif res.reflected:
                self._check_bid_freshness()   # 파일 생성 없이 누적만 변경 → 기존 파일 구버전?

        def _fill_profile(self, rows):
            self.profile_tbl.setRowCount(len(rows))
            for i, r in enumerate(rows):
                vals = [r.temp, round(r.cc_theory, 2), round(r.correction, 2),
                        round(r.cc_real_net, 2)]
                for j, v in enumerate(vals):
                    self.profile_tbl.setItem(i, j, QtWidgets.QTableWidgetItem(str(v)))

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
            self.sim_method.addItems(["구간 평균 (기본)", "커널 보정곡선", "GP (가우시안 프로세스)"])
            self.sim_margin = QtWidgets.QDoubleSpinBox()
            self.sim_margin.setRange(0.0, 3.0)
            self.sim_margin.setSingleStep(0.1)
            self.sim_margin.setValue(0.0)
            self.sim_margin.setSuffix(" ×")
            f3.addRow("보정 방법", self.sim_method)
            f3.addRow("안전마진 계수", self.sim_margin)

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

            outer.addLayout(left, stretch=0)
            outer.addLayout(right, stretch=1)
            return w

        def _on_simulate(self):
            from ..simulate import SimInput, format_result, simulate

            recs = [{"cit": r["cit"], "corr": r["corr"], "cp_meas": r.get("cp_meas"),
                     "cp_design": r.get("cp_design")} for r in self.store.list_up()]
            table = self.store.correction_table()
            idx = self.sim_method.currentIndex()
            base = None
            if idx == 1:
                from ..curve import CorrectionCurve
                base = CorrectionCurve(recs, method="kernel")
            elif idx == 2:
                from ..gp import GPCorrectionCurve
                base = GPCorrectionCurve(recs)
            corrector = base
            k = self.sim_margin.value()
            if k > 0:
                from ..correction import applied_correction
                from ..margin import MarginCorrector
                inner = base if base is not None else (
                    lambda t: applied_correction(t, table))
                corrector = MarginCorrector(inner, recs, k=k)

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
            self.chart_method.addItems(["구간평균(기본)", "커널회귀", "GP(가우시안 프로세스)"])
            self.chart_method.setToolTip(
                "보정값 산출 방법 — 실측 32건 LOOCV 예측오차(MAE)\n"
                "  구간평균 1.419 / 커널회귀 1.341 / GP 1.243 MW")
            self.chart_method.currentIndexChanged.connect(self._refresh_chart)
            self.chart_margin = QtWidgets.QDoubleSpinBox()
            self.chart_margin.setRange(0.0, 3.0)
            self.chart_margin.setSingleStep(0.1)
            self.chart_margin.setValue(0.0)
            self.chart_margin.setSuffix(" ×")
            self.chart_margin.setToolTip(
                "입찰 안전마진 = 계수 × 구간별 실측변동\n"
                "0 = 마진 없음(오차 최소) · 0.8 = 미달 0건(안전 최우선)\n"
                "마진을 켜면 오차는 커지지만 커지는 방향이 전부 안전한 쪽입니다.")
            self.chart_margin.valueChanged.connect(self._refresh_chart)
            self.chart_pts = QtWidgets.QCheckBox("실측점")
            self.chart_pts.setChecked(True)
            self.chart_pts.stateChanged.connect(self._refresh_chart)
            self.chart_band = QtWidgets.QCheckBox("예측구간(GP)")
            self.chart_band.setChecked(True)
            self.chart_band.stateChanged.connect(self._refresh_chart)
            bar.addWidget(QtWidgets.QLabel("보정 방법"))
            bar.addWidget(self.chart_method)
            bar.addSpacing(10)
            bar.addWidget(QtWidgets.QLabel("안전마진"))
            bar.addWidget(self.chart_margin)
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
            idx = self.chart_method.currentIndex()
            sigma_fn = None
            if idx == 1:
                from ..curve import CorrectionCurve
                base = CorrectionCurve(recs, method="kernel")
            elif idx == 2:
                from ..gp import GPCorrectionCurve
                base = GPCorrectionCurve(recs)
                sigma_fn = base.sigma
            else:
                base = None                      # 구간평균(기본)
            k = self.chart_margin.value()
            margin_fn = None
            corrector = base
            if k > 0:
                from ..margin import MarginCorrector
                from ..correction import applied_correction
                inner = base if base is not None else (
                    lambda t: applied_correction(t, table))
                mc = MarginCorrector(inner, recs, k=k)
                corrector = mc
                margin_fn = mc.margin
            rows = build_profile(self.engine, table, corrector=corrector)
            self.chart.set_toggles(points=self.chart_pts.isChecked(),
                                   band=self.chart_band.isChecked())
            self.chart.set_data(rows, [(r["cit"], r["corr"]) for r in recs],
                                sigma_fn=sigma_fn, margin_fn=margin_fn)
            msg = f"누적 {len(recs)}건"
            if idx == 2 and getattr(base, "hyper", None):
                ls, sf, sn = base.hyper
                msg += f" · GP 길이척도 {ls:.0f}°C 노이즈 {sn:.1f} MW"
            if k > 0:
                mg = [margin_fn(t) for t in range(-14, 41)]
                msg += f" · 마진 {min(mg):.2f}~{max(mg):.2f} MW"
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
                    correction_method=("gp" if self.method_cb.currentIndex() == 2 else
                                       "curve" if self.method_cb.currentIndex() == 1 else "bin"),
                    margin_k=self.margin_sb.value(),
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

    app = QtWidgets.QApplication(argv or sys.argv)
    app.setStyleSheet(QSS)
    _logo = _C.logo_path()
    if _logo:                       # 작업표시줄·창 좌상단 아이콘도 같은 로고로
        from PySide6 import QtGui
        app.setWindowIcon(QtGui.QIcon(str(_logo)))
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":  # pragma: no cover
    main()
