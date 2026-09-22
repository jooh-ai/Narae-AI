"""시작 진단 로그 — '조용한 종료' 를 없애기 위한 최소 장치.

spec 의 console=False 때문에 시작 중 무슨 일이 있어도 화면에 남지 않는다. 그래서
런처(wirye_gui.py)와 GUI(ui/app.py)가 같은 파일에 단계를 적는다. 다음 실행 한 번으로
어디서 멈췄는지 알 수 있어야 한다.

로그 위치: exe 폴더의 wirye_error.log (쓸 수 없으면 %TEMP% → 홈 폴더)

알림에 Qt 를 쓰지 않는 이유
    Qt 자체가 못 올라온 경우(플러그인 누락, PATH 의 다른 Qt DLL 충돌)를 보여줄 수
    없기 때문이다. Windows 기본 MessageBox(ctypes)를 쓴다.
"""
from __future__ import annotations

import datetime
import os
import sys
from pathlib import Path

LOG_NAME = "wirye_error.log"
_path: Path | None = None


def app_dir() -> Path:
    """exe 가 놓인 폴더(동결) 또는 tool 폴더(소스).

    onedir 빌드에서 sys._MEIPASS 는 _internal/ 을 가리키므로 쓰지 않는다.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def log_path() -> Path:
    """쓸 수 있는 첫 위치. Program Files 설치·읽기전용 공유에도 대응."""
    global _path
    if _path is not None:
        return _path
    candidates = [app_dir()]
    tmp = os.environ.get("TEMP") or os.environ.get("TMPDIR")
    if tmp:
        candidates.append(Path(tmp))
    candidates.append(Path.home())
    for d in candidates:
        try:
            d.mkdir(parents=True, exist_ok=True)
            p = d / LOG_NAME
            with p.open("a", encoding="utf-8"):
                pass
            _path = p
            return p
        except OSError:
            continue
    _path = Path(LOG_NAME)
    return _path


def write(text: str) -> None:
    try:
        with log_path().open("a", encoding="utf-8") as f:
            f.write(text)
    except OSError:
        pass


def stage(msg: str) -> None:
    """시작 단계 한 줄. 하드 크래시로 죽어도 어디까지 갔는지는 남는다."""
    write(f"    · {datetime.datetime.now():%H:%M:%S}  {msg}\n")


def alert(title: str, body: str) -> None:
    """Qt 를 쓰지 않는 알림 — Qt 가 못 올라온 상황에서도 보여야 한다."""
    if sys.platform == "win32":
        try:
            import ctypes
            MB_ICONERROR, MB_SETFOREGROUND, MB_TOPMOST = 0x10, 0x10000, 0x40000
            ctypes.windll.user32.MessageBoxW(   # type: ignore[attr-defined]
                None, body, title, MB_ICONERROR | MB_SETFOREGROUND | MB_TOPMOST)
            return
        except Exception:          # noqa: BLE001 — 알림 실패로 죽으면 안 된다
            pass
    sys.stderr.write(f"\n{title}\n{body}\n")
