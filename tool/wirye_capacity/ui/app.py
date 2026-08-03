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
            self._last_bid = None      # 마지막 생성 입찰파일 {path, fp} — 구버전 감지용

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
        def _list_tab(self):
            w = QtWidgets.QWidget()
            lay = QtWidgets.QVBoxLayout(w)
            bar = QtWidgets.QHBoxLayout()
            hint = QtWidgets.QLabel(
                "행을 선택해 [삭제 표시] 후 [💾 저장]을 눌러야 실제로 삭제됩니다. "
                "저장 전에는 [되돌리기]로 취소할 수 있습니다.")
            hint.setWordWrap(True)
            self.datefill_btn = QtWidgets.QPushButton("📅 엑셀4에서 날짜 채우기")
            self.datefill_btn.setToolTip(
                "과거 누적(시드) 32건은 날짜가 비어 있습니다.\n"
                "엑셀4 '실측데이터'를 지정하면 (CC실측·CIT) 매칭으로 날짜를 채웁니다.")
            self.datefill_btn.clicked.connect(self._on_backfill_dates)
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
            bar.addWidget(self.datefill_btn)
            bar.addWidget(self.del_btn)
            bar.addWidget(self.undo_btn)
            bar.addWidget(self.save_btn)
            self.list_tbl = QtWidgets.QTableWidget(0, 6)
            self.list_tbl.setHorizontalHeaderLabels(
                ["날짜", "CIT(°C)", "대기압(mbar)", "CC실측", "보정값", "계절"])
            self.list_tbl.setAlternatingRowColors(True)
            self.list_tbl.horizontalHeader().setStretchLastSection(True)
            self.list_tbl.verticalHeader().setVisible(False)
            self.list_tbl.setSelectionBehavior(
                QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            self.list_tbl.setEditTriggers(
                QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            lay.addLayout(bar)
            lay.addWidget(self.list_tbl)
            self._pending_del = set()          # 삭제 대기 id (저장 시 확정)
            self._update_del_buttons()
            return w

        def _refresh_list(self):
            from PySide6 import QtGui
            self._list_rows = self.store.list_up(order="date")   # id 포함(삭제용)
            self.list_tbl.setRowCount(len(self._list_rows))
            for i, r in enumerate(self._list_rows):
                # 표시 자릿수: CIT 1자리·대기압 1자리·CC 2자리 (저장은 풀 정밀도 — 계산용)
                vals = [r.get("date") or "-", f"{r['cit']:.1f}", f"{r['press']:.1f}",
                        f"{r['cc_meas']:.2f}", f"{r['corr']:+.2f}", r.get("season") or ""]
                marked = r["id"] in getattr(self, "_pending_del", set())
                for j, v in enumerate(vals):
                    item = QtWidgets.QTableWidgetItem(str(v))
                    if marked:                     # 삭제 대기 행: 취소선 + 회색
                        f = item.font(); f.setStrikeOut(True); item.setFont(f)
                        item.setForeground(QtGui.QColor("#B9AFA9"))
                    self.list_tbl.setItem(i, j, item)
            self._update_del_buttons()

        def _update_del_buttons(self):
            n = len(getattr(self, "_pending_del", set()))
            self.save_btn.setEnabled(n > 0)
            self.undo_btn.setEnabled(n > 0)
            self.save_btn.setText(f"💾 저장 ({n}건 삭제)" if n else "💾 저장")

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
            self._refresh_list()

        def _on_save_deletes(self):
            ids = set(self._pending_del)
            if not ids:
                return
            targets = [r for r in self._list_rows if r["id"] in ids]
            lines = [f"  · {t.get('date') or '-'}  (CIT {t['cit']:.1f}°C, "
                     f"보정 {t['corr']:+.2f})" for t in targets]
            if QtWidgets.QMessageBox.warning(
                    self, "삭제 저장",
                    f"다음 {len(targets)}건을 누적에서 삭제합니다.\n"
                    f"(저장 후 보정값이 재집계되며 되돌릴 수 없습니다)\n\n" + "\n".join(lines),
                    QtWidgets.QMessageBox.StandardButton.Yes
                    | QtWidgets.QMessageBox.StandardButton.No
                    ) != QtWidgets.QMessageBox.StandardButton.Yes:
                return
            for rec_id in ids:
                self.store.delete(rec_id)
            self._pending_del.clear()
            self._refresh_list()
            self._refresh_status(self.store.correction_table())   # 즉시 재집계 반영
            self._check_bid_freshness()                            # 기존 입찰파일 구버전 감지

        def _on_backfill_dates(self):
            fn, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "엑셀4 파일 선택 (실측데이터)", "", "Excel (*.xlsx)")
            if not fn:
                return
            try:
                from ..excel4 import load_excel4_records
                recs = load_excel4_records(fn)
                n = self.store.backfill_dates(recs)
            except Exception as e:  # noqa: BLE001
                QtWidgets.QMessageBox.critical(self, "날짜 채우기 오류", str(e))
                return
            self._refresh_list()
            QtWidgets.QMessageBox.information(
                self, "날짜 채우기",
                f"엑셀4 {len(recs)}건을 읽어 날짜 {n}건을 채웠습니다.")

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
                    correction_method="curve" if self.curve_chk.isChecked() else "bin",
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
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":  # pragma: no cover
    main()
