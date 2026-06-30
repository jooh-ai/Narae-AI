"""위례 공급가능용량 입찰 산정 — Windows 데스크톱 GUI (PySide6).

사내 PC에서 실행:  python -m wirye_capacity.ui.app
로직은 pipeline.run_pipeline 에 위임하고, 이 모듈은 입력/표시만 담당하는 얇은 셸이다.

화면:
  [입력]  테스트 날짜·시각 · Degradation · 엑셀3-1(날씨) · RiMS(실제 엑셀1 / mock) · 출력경로
  [실행]  → run_pipeline → 엑셀3 입찰파일 생성
  [결과]  적용 대기압·신규 보정값·누적건수 · 온도별 현실화 Net 표 · 보정값 현황(신호등)
  [List-up] 누적 테스트 표
"""
from __future__ import annotations

import sys
from pathlib import Path

from .. import constants as C
from ..correction import status_rows
from ..pipeline import run_pipeline
from ..store import MeasurementStore
from ..theory import TheoryEngine


def _require_qt():
    try:
        from PySide6 import QtWidgets, QtCore  # noqa: F401
    except ImportError as e:  # pragma: no cover
        raise SystemExit("PySide6 가 필요합니다 (사내 PC): pip install PySide6") from e


def build_connector(use_mock: bool, workbook_path: str | None):
    if use_mock:
        from ..rims import MockRimsConnector
        return MockRimsConnector.from_seed()
    if workbook_path:
        from ..rims.excel_addin import ExcelAddinRimsConnector
        return ExcelAddinRimsConnector(workbook_path)
    return None


def main(argv=None):  # pragma: no cover - GUI 셸(사내 실행)
    _require_qt()
    from PySide6 import QtWidgets

    db_default = str(Path.home() / "wirye_measurements.db")

    class MainWindow(QtWidgets.QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("위례 공급가능용량 입찰 산정")
            self.resize(900, 640)
            self.engine = TheoryEngine()
            self.store = MeasurementStore(db_default)
            if self.store.count() == 0:
                self.store.seed()

            tabs = QtWidgets.QTabWidget()
            tabs.addTab(self._run_tab(), "실행")
            tabs.addTab(self._status_tab(), "보정값 현황")
            tabs.addTab(self._list_tab(), "List-up")
            self.setCentralWidget(tabs)
            self._refresh_list()
            self._refresh_status(self.store.correction_table())   # 시작 시 현재 누적 기준

        # ---------- 실행 탭 ----------
        def _run_tab(self):
            w = QtWidgets.QWidget()
            form = QtWidgets.QFormLayout()
            self.date_in = QtWidgets.QLineEdit()
            self.date_in.setPlaceholderText("예: 2025-09-12 (테스트 날짜)")
            self.deg_in = QtWidgets.QDoubleSpinBox()
            self.deg_in.setRange(1.0, 1.2); self.deg_in.setSingleStep(0.001)
            self.deg_in.setDecimals(3); self.deg_in.setValue(C.DEFAULT_DEG)
            self.bidday_in = QtWidgets.QLineEdit()
            self.bidday_in.setPlaceholderText("입찰 적용일 라벨(선택, 미입력 시 전체 중위 평균)")
            self.curve_chk = QtWidgets.QCheckBox("연속 보정곡선 사용")
            self.accum_chk = QtWidgets.QCheckBox("이 테스트를 누적에 반영(저장)")
            self.accum_chk.setToolTip("체크 안 하면 확인용(보정값만 표시, 누적 미저장)")
            self.forecast_in = self._file_row("엑셀3-1 (날씨)")
            self.workbook_in = self._file_row("엑셀1 (RiMS) — 실제 취득")
            self.mock_chk = QtWidgets.QCheckBox("mock RiMS 사용(테스트)")
            self.out_in = self._file_row("출력 엑셀3 입찰파일", save=True)

            form.addRow("테스트 날짜", self.date_in)
            form.addRow("Degradation", self.deg_in)
            form.addRow("입찰 적용일", self.bidday_in)
            form.addRow("날씨", self.forecast_in["row"])
            form.addRow("RiMS", self.workbook_in["row"])
            form.addRow("", self.mock_chk)
            form.addRow("", self.curve_chk)
            form.addRow("", self.accum_chk)
            form.addRow("출력", self.out_in["row"])

            self.run_btn = QtWidgets.QPushButton("▶ 실행 (취득 → 누적 → 입찰파일 생성)")
            self.run_btn.clicked.connect(self._on_run)
            run_btn = self.run_btn
            self.summary = QtWidgets.QLabel("입력 후 실행하세요.")
            self.summary.setWordWrap(True)
            self.profile_tbl = QtWidgets.QTableWidget(0, 4)
            self.profile_tbl.setHorizontalHeaderLabels(
                ["온도(°C)", "CC이론", "보정값", "CC현실화 Net"])

            lay = QtWidgets.QVBoxLayout(w)
            lay.addLayout(form)
            lay.addWidget(run_btn)
            lay.addWidget(self.summary)
            lay.addWidget(self.profile_tbl)
            return w

        def _file_row(self, label, save=False):
            edit = QtWidgets.QLineEdit()
            btn = QtWidgets.QPushButton("...")
            row = QtWidgets.QHBoxLayout()
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

        def _on_run(self):
            from PySide6 import QtCore, QtGui
            use_mock = self.mock_chk.isChecked()
            workbook = self.workbook_in["edit"].text().strip() or None
            if not use_mock and not workbook:
                if QtWidgets.QMessageBox.question(
                        self, "RiMS 미지정",
                        "RiMS(엑셀1) 또는 mock 이 지정되지 않았습니다.\n"
                        "신규 취득 없이 현재 누적값으로 Profile만 재생성할까요?"
                        ) != QtWidgets.QMessageBox.StandardButton.Yes:
                    return
            # 긴 RiMS 취득 동안 UI 가 멈춘 것처럼 보이므로 버튼 비활성·대기 커서
            # (대용량 비동기 취득은 향후 QThread 워커로 분리 권장)
            self.run_btn.setEnabled(False)
            QtGui.QGuiApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)
            try:
                res = run_pipeline(
                    date=self.date_in.text().strip(), store=self.store,
                    output_path=self.out_in["edit"].text().strip() or None,
                    connector=build_connector(use_mock, workbook),
                    engine=self.engine, deg=self.deg_in.value(),
                    bid_day=self.bidday_in.text().strip() or None,
                    accumulate=self.accum_chk.isChecked(),
                    correction_method="curve" if self.curve_chk.isChecked() else "bin",
                    forecast_path=self.forecast_in["edit"].text().strip() or None)
            except Exception as e:  # noqa: BLE001
                QtWidgets.QMessageBox.critical(self, "오류", str(e))
                return
            finally:
                QtGui.QGuiApplication.restoreOverrideCursor()
                self.run_btn.setEnabled(True)
            msg = [f"적용 대기압: {res.applied_pressure:.1f} mbar",
                   f"누적: {res.measurement_count}건"]
            if res.new_record is not None:
                st = ("✅반영" if res.reflected else
                      "⚠중복-건너뜀" if res.duplicate_skipped else "확인용(미반영)")
                msg.append(f"신규 보정값(CIT {res.new_record.cit}°C): "
                           f"{res.new_record.corr:+.2f} MW [{st}]")
            if res.output_path:
                msg.append(f"저장: {res.output_path}")
            self.summary.setText("   |   ".join(msg))
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

        # ---------- 보정값 현황 탭 (엑셀4 '보정값 현황' 재현) ----------
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
            self.status_tbl.horizontalHeader().setStretchLastSection(True)
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
                    item = QtWidgets.QTableWidgetItem(str(v))
                    self.status_tbl.setItem(i, j, item)

        # ---------- List-up 탭 ----------
        def _list_tab(self):
            self.list_tbl = QtWidgets.QTableWidget(0, 5)
            self.list_tbl.setHorizontalHeaderLabels(
                ["날짜", "CIT(°C)", "CC실측", "보정값", "계절"])
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
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":  # pragma: no cover
    main()
