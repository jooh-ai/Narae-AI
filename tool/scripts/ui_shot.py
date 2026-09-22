#!/usr/bin/env python3
"""Tool UI 오프스크린 캡처 — 화면 없이 탭별 PNG 를 뽑는다.

    python3 tool/scripts/ui_shot.py <출력폴더> [--size 1280x860] [--tab 0,4]

디자인을 고칠 때 눈으로 확인하는 수단이다. 사내 PC 없이도 색·간격·정렬을
바로 볼 수 있다. RiMS 연결은 하지 않는다 — 시드 데이터로 그려지는 화면만 본다.

리눅스에서는 Qt 오프스크린 플랫폼과 libEGL 이 필요하다:
    pip install PySide6-Essentials
    apt-get install -y libegl1 libgl1 libxkbcommon0 libdbus-1-3 libfontconfig1
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tool"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


# 발표자료에 넣을 조각들. (탭 번호, 찾는 방법, 설명)
#   attr:<이름>   MainWindow 의 속성
#   group:<제목>  그 탭 안의 QGroupBox 제목
#   window        창 전체
SHOTS = {
    "tool_window":     (0, "window",            "창 전체 (산정 탭)"),
    "tool_input":      (0, "group:테스트 정보",   "날짜·시각만 넣는 입력 카드"),
    "tool_bidcond":    (0, "group:입찰 조건",     "대기압 윈드파인더 업로드"),
    "tool_profile":    (0, "attr:profile_tbl",   "온도별 프로파일 표"),
    "tool_status":     (1, "attr:status_tbl",    "온도 구간별 보정값 현황 표"),
    "tool_list":       (2, "attr:list_tbl",      "Test 결과 List-up 표"),
    "tool_curve":      (4, "attr:chart",         "출력곡선 비교 차트"),
    "tool_models":     (5, "group:후보 모델",     "후보 모델 7가지 체크리스트"),
    "tool_split":      (5, "group:데이터 분할",   "테스트셋 분할 조건"),
}


def _find(win, how: str):
    """프리셋의 '찾는 방법' 문자열을 실제 위젯으로 바꾼다."""
    from PySide6 import QtWidgets
    if how == "window":
        return win
    kind, _, arg = how.partition(":")
    if kind == "attr":
        return getattr(win, arg, None)
    if kind == "group":
        for g in win.findChildren(QtWidgets.QGroupBox):
            if g.title().strip() == arg:
                return g
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", help="PNG 를 저장할 폴더")
    ap.add_argument("--size", default="1280x860", help="창 크기 (기본 1280x860)")
    ap.add_argument("--tab", default="", help="캡처할 탭 번호, 쉼표 구분 (기본 전부)")
    ap.add_argument("--db", default="", help="누적 DB 경로 (기본: 임시 폴더에 새로 만든다)")
    ap.add_argument("--run-select", action="store_true",
                    help="[모델 선정 실행] 을 먼저 돌려 표를 채운다 (RiMS 불필요, 수 분 걸린다)")
    ap.add_argument("--run-profile", default="",
                    help="[공급가능용량 산정] 을 이 날짜로 한 번 돌려 프로파일 표를 채운다 "
                         "(RiMS 대신 시드 기반 Mock 커넥터를 쓴다. 예: 2026-08-26)")
    ap.add_argument("--clean", action="store_true",
                    help="발표용 — 첫 실행 안내 띠를 감추고 하단 DB 경로를 건수만 남긴다")
    ap.add_argument("--shots", default="",
                    help="위젯 단위 캡처. 쉼표로 프리셋 이름 (전체 목록은 --list-shots)")
    ap.add_argument("--list-shots", action="store_true", help="프리셋 이름 목록만 출력")
    a = ap.parse_args()

    if a.list_shots:
        for k, (tab, how, _) in SHOTS.items():
            print(f"{k:<16s} 탭 {tab}  {how}")
        return 0

    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    w_, h_ = (int(v) for v in a.size.lower().split("x"))
    want = {int(v) for v in a.tab.split(",") if v.strip()} if a.tab else None

    # 캡처용 DB 는 리포지토리를 더럽히지 않게 임시 폴더에 만든다.
    if not a.db:
        import tempfile
        a.db = str(Path(tempfile.mkdtemp(prefix="wirye_shot_")) / "shot.db")
    os.environ["WIRYE_DB_PATH"] = a.db          # constants.db_path 가 읽는 이름

    from PySide6 import QtWidgets
    from wirye_capacity.ui import app as A

    # 모달 대화상자는 오프스크린에서도 이벤트 루프를 잡는다. 캡처는 사람이 없는
    # 실행이므로 물어보는 창은 전부 '예' 로 답하고 지나간다.
    _Y = QtWidgets.QMessageBox.StandardButton.Yes
    _OK = QtWidgets.QMessageBox.StandardButton.Ok
    QtWidgets.QMessageBox.question = staticmethod(lambda *_a, **_k: _Y)
    QtWidgets.QMessageBox.information = staticmethod(lambda *_a, **_k: _OK)
    QtWidgets.QMessageBox.warning = staticmethod(lambda *_a, **_k: _OK)
    QtWidgets.QMessageBox.critical = staticmethod(lambda *_a, **_k: _OK)
    QtWidgets.QMessageBox.exec = lambda _self: 0
    QtWidgets.QDialog.exec = lambda _self: 0

    saved: list[tuple[int, str, Path]] = []

    def shoot():
        win = next(w for w in QtWidgets.QApplication.topLevelWidgets()
                   if isinstance(w, QtWidgets.QMainWindow))
        win.resize(w_, h_)
        tabs = win.findChild(QtWidgets.QTabWidget)
        if a.clean:
            # 첫 실행 안내 띠에는 임시 DB 경로가 찍힌다. 발표자료에 들어갈 그림에
            # /tmp 경로가 보이면 안 된다. 상태줄도 건수만 남긴다.
            for bar in win.findChildren(QtWidgets.QWidget):
                if bar.objectName() == "banner":
                    bar.hide()
            try:
                win.statusBar().showMessage(f"누적 {win.store.count()}건")
            except Exception:                                     # noqa: BLE001
                pass
            QtWidgets.QApplication.processEvents()
        if a.run_profile:
            # 산정 탭의 표는 실행 전에는 비어 있다. 발표자료에 빈 표를 넣을 수는
            # 없으므로 한 번 돌려 채운다. RiMS 는 사내망이라 여기서 못 붙지만,
            # 계산 경로는 같다 — 취득만 시드 기반 Mock 으로 바꾼다.
            # Mock.from_seed() 는 합성 날짜(2025-T01…)로 키를 만든다. 발표자료에
            # 그 문자열이 보이면 안 되므로 실제 날짜로 키를 다시 세운다.
            import json

            from wirye_capacity import constants as _C
            from wirye_capacity.rims import MockRimsConnector
            from wirye_capacity.rims.base import AcquiredTest
            recs = json.loads(Path(_C.resource("data", "measurements_seed.json"))
                              .read_text(encoding="utf-8"))
            by_date = {r["date"]: AcquiredTest(
                date=r["date"], cit=r["cit"], pressure=r["press"],
                cc_meas=r["cc_meas"], rh=r.get("rh"), cp_meas=r.get("cp_meas"),
                cp_design=r.get("cp_design"), season=r.get("season"))
                for r in recs if r.get("date")}
            if a.run_profile not in by_date:
                print(f"!! 시드에 없는 날짜: {a.run_profile}  "
                      f"(가용 예: {sorted(by_date)[-3:]})")
            win._connector = lambda: MockRimsConnector(by_date)
            win.date_in.setText(a.run_profile)
            win.accum_chk.setChecked(False)          # 캡처가 누적을 늘리지 않게
            win._on_run()
            for _ in range(5):
                QtWidgets.QApplication.processEvents()
        if a.run_select and hasattr(win, "_on_select"):
            # 빈 표를 캡처하면 색·정렬을 볼 수 없다. 누적 데이터만으로 도는
            # 계산이라 RiMS 없이 채울 수 있다.
            win._on_select()
            for _ in range(5):
                QtWidgets.QApplication.processEvents()
        if a.shots:
            for name in (n.strip() for n in a.shots.split(",") if n.strip()):
                if name not in SHOTS:
                    print(f"!! 모르는 프리셋: {name}")
                    continue
                tab, how, desc = SHOTS[name]
                tabs.setCurrentIndex(tab)
                for _ in range(3):
                    QtWidgets.QApplication.processEvents()
                wgt = _find(win, how)
                if wgt is None:
                    print(f"!! 위젯을 못 찾음: {name} ({how})")
                    continue
                p = out / f"{name}.png"
                wgt.grab().save(str(p))
                saved.append((tab, f"{name} — {desc}", p))
            QtWidgets.QApplication.quit()
            return
        for i in range(tabs.count()):
            if want is not None and i not in want:
                continue
            tabs.setCurrentIndex(i)
            # 탭을 바꾼 뒤 한 번 더 이벤트를 돌려야 새 탭이 실제로 그려진다.
            # 이걸 빼면 직전 탭 화면이 저장된다(처음에 그렇게 당했다).
            for _ in range(3):
                QtWidgets.QApplication.processEvents()
            p = out / f"tab{i}.png"
            win.grab().save(str(p))
            saved.append((i, tabs.tabText(i), p))
        QtWidgets.QApplication.quit()

    # main() 은 app.exec() 로 이벤트 루프에 들어간다. 그 자리를 캡처로 바꾼다.
    QtWidgets.QApplication.exec = lambda *_: (shoot(), 0)[1]
    A.main([])

    for i, t, p in saved:
        print(f"{i}  {t:<22s} → {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
