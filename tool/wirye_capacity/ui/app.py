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
from ..correction import status_rows
from ..pipeline import run_pipeline
from ..store import MeasurementStore
from ..theory import TheoryEngine

# ── SK 브랜드 스타일시트 (행복날개 레드 #EA002C · 오렌지 #F47725, 플랫 · 카드) ──
QSS = """
* { font-family: 'Malgun Gothic', 'Segoe UI', sans-serif; font-size: 10pt; }
QMainWindow, QWidget { background: #FAF7F5; color: #2B2422; }

QLabel#header {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #EA002C, stop:0.6 #F0431F, stop:1 #F47725);
    color: #FFFFFF; font-size: 14pt; font-weight: 800;
    padding: 14px 18px; border: none;
}
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

    db_default = str(Path.home() / "wirye_measurements.db")

    class MainWindow(QtWidgets.QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("위례 공급가능용량 입찰 산정 Tool")
            self.resize(1020, 720)
            self.engine = TheoryEngine()
            self.store = MeasurementStore(db_default)
            if self.store.count() == 0:
                self.store.seed()

            tabs = QtWidgets.QTabWidget()
            tabs.addTab(self._run_tab(), "공급가능용량 산정")
            tabs.addTab(self._status_tab(), "온도 구간별 보정값 현황")
            tabs.addTab(self._list_tab(), "Test 결과 List-up")

            header = QtWidgets.QLabel("🦋  위례 공급가능용량 입찰 산정")
            header.setObjectName("header")
            central = QtWidgets.QWidget()
            v = QtWidgets.QVBoxLayout(central)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(0)
            v.addWidget(header)
            v.addWidget(tabs)
            self.setCentralWidget(central)
            self._refresh_list()
            self._refresh_status(self.store.correction_table())   # 시작 시 현재 누적 기준

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
            self.curve_chk = QtWidgets.QCheckBox("연속 보정곡선 사용(실험적)")
            self.curve_chk.setToolTip(
                "기본(구간 평균): 온도구간별 평균 보정값을 계단식으로 적용.\n"
                "연속 곡선: 누적 실측점에 곡선을 맞춰 1°C 단위로 부드럽게 적용.\n"
                "데이터가 충분히 쌓인 뒤 구간 방식과 비교 검증 후 전환 권장.")
            self.out_in = self._file_row("출력 엑셀3 입찰파일(.xlsx)", save=True)
            f3.addRow("", self.accum_chk)
            f3.addRow("", self.curve_chk)
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
                    correction_method="curve" if self.curve_chk.isChecked() else "bin",
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
            self._fill_profile(res.profile_rows)
            self._refresh_status(res.correction_table)
            self._refresh_list()

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

        # ---------- Test List-up 탭 ----------
        def _list_tab(self):
            self.list_tbl = QtWidgets.QTableWidget(0, 5)
            self.list_tbl.setHorizontalHeaderLabels(
                ["날짜", "CIT(°C)", "CC실측", "보정값", "계절"])
            self.list_tbl.setAlternatingRowColors(True)
            self.list_tbl.horizontalHeader().setStretchLastSection(True)
            self.list_tbl.verticalHeader().setVisible(False)
            return self.list_tbl

        def _refresh_list(self):
            rows = self.store.list_up(order="date")
            self.list_tbl.setRowCount(len(rows))
            for i, r in enumerate(rows):
                vals = [r.get("date") or "-", r["cit"], r["cc_meas"],
                        round(r["corr"], 2), r.get("season") or ""]
                for j, v in enumerate(vals):
                    self.list_tbl.setItem(i, j, QtWidgets.QTableWidgetItem(str(v)))

    app = QtWidgets.QApplication(argv or sys.argv)
    app.setStyleSheet(QSS)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":  # pragma: no cover
    main()
