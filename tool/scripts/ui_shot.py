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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", help="PNG 를 저장할 폴더")
    ap.add_argument("--size", default="1280x860", help="창 크기 (기본 1280x860)")
    ap.add_argument("--tab", default="", help="캡처할 탭 번호, 쉼표 구분 (기본 전부)")
    ap.add_argument("--db", default="", help="누적 DB 경로 (기본: 임시 폴더에 새로 만든다)")
    ap.add_argument("--run-select", action="store_true",
                    help="[모델 선정 실행] 을 먼저 돌려 표를 채운다 (RiMS 불필요, 수 분 걸린다)")
    a = ap.parse_args()

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

    saved: list[tuple[int, str, Path]] = []

    def shoot():
        win = next(w for w in QtWidgets.QApplication.topLevelWidgets()
                   if isinstance(w, QtWidgets.QMainWindow))
        win.resize(w_, h_)
        tabs = win.findChild(QtWidgets.QTabWidget)
        if a.run_select and hasattr(win, "_on_select"):
            # 빈 표를 캡처하면 색·정렬을 볼 수 없다. 누적 데이터만으로 도는
            # 계산이라 RiMS 없이 채울 수 있다.
            win._on_select()
            for _ in range(5):
                QtWidgets.QApplication.processEvents()
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
