"""GUI 실행 진입점 (PyInstaller 패키징용).

패키지 상대 import(from .. import ...)가 있는 ui/app.py 를 직접 스크립트로 돌리면
import 가 깨지므로, 절대 import 로 감싸는 얇은 런처를 별도로 둔다.

    python wirye_gui.py                 # 소스 실행
    pyinstaller wirye_tool.spec         # exe 빌드(이 파일이 진입점)
    WiryeBidTool.exe --selftest         # 실행 환경 점검(로그 + 대화상자)

왜 런처가 두꺼운가 — '조용한 종료'를 없애기 위해서다
    spec 의 console=False 라서 시작 중 예외가 나면 표준출력이 없다. 더블클릭해도
    아무 반응 없이 프로세스가 사라지고 원인이 남지 않는다(2026-08 타 PC 실제 사례:
    10회 재빌드하며 원인을 못 찾았다). 그래서 전 구간을 감싸 오류를 로그 파일과
    대화상자로 남긴다.

    대화상자를 Qt 로 띄우면 안 된다 — Qt 자체가 못 올라온 경우(플러그인 누락,
    PATH 의 다른 Qt DLL 충돌)를 보여줄 수 없기 때문이다. Windows 기본
    MessageBox(ctypes)를 쓴다.

    로그에 단계 표시를 남기므로, 파이썬 예외가 아닌 하드 크래시(DLL 문제 등)여도
    어디까지 갔는지 알 수 있다. faulthandler 로 네이티브 크래시 흔적도 받는다.

로그 위치: exe 폴더의 wirye_error.log (쓸 수 없으면 %TEMP% → 홈 폴더)
"""
from __future__ import annotations

import datetime
import os
import sys
import traceback
from pathlib import Path

LOG_NAME = "wirye_error.log"


def app_dir() -> Path:
    """exe 가 놓인 폴더(동결) 또는 이 파일이 있는 폴더(소스).

    onedir 빌드에서 sys._MEIPASS 는 _internal/ 을 가리키므로 쓰지 않는다.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def log_path() -> Path:
    """쓸 수 있는 첫 위치를 고른다. Program Files 설치나 읽기전용 공유에도 대응."""
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
            return p
        except OSError:
            continue
    return Path(LOG_NAME)


def _write(path: Path, text: str) -> None:
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(text)
    except OSError:
        pass


def alert(title: str, body: str) -> None:
    """Qt 를 쓰지 않는 알림 — Qt 가 못 올라온 상황에서도 보여야 한다."""
    if sys.platform == "win32":
        try:
            import ctypes
            MB_ICONERROR, MB_SETFOREGROUND, MB_TOPMOST = 0x10, 0x10000, 0x40000
            ctypes.windll.user32.MessageBoxW(   # type: ignore[attr-defined]
                None, body, title, MB_ICONERROR | MB_SETFOREGROUND | MB_TOPMOST)
            return
        except Exception:                      # noqa: BLE001 — 알림 실패로 죽으면 안 된다
            pass
    sys.stderr.write(f"\n{title}\n{body}\n")


def selftest() -> str:
    """실행 환경 점검 보고서. 예외를 내지 않고 문자열로 돌려준다."""
    out: list[str] = []

    def line(k: str, v) -> None:
        out.append(f"  {k:<22} {v}")

    out.append("── 실행 환경 ──")
    line("exe", sys.executable)
    line("frozen", getattr(sys, "frozen", False))
    line("_MEIPASS", getattr(sys, "_MEIPASS", "(없음 — 소스 실행)"))
    line("Tool 폴더", app_dir())
    line("Python", sys.version.split()[0])
    line("플랫폼", f"{sys.platform} / {os.name}")

    out.append("\n── 번들 자원 ──")
    try:
        from wirye_capacity import constants as C
        for rel in ("data/base_table.json", "data/measurements_seed.json",
                    "templates/excel3_profile_template.xlsx",
                    "templates/excel3_profile_template.tpl"):
            p = C.resource(*rel.split("/"))
            line(rel, f"{p.stat().st_size:,} 바이트" if p.exists() else "❌ 없음")
        line("logo.png", "있음" if C.logo_path() else "없음(이모지로 대체)")
    except Exception as e:                     # noqa: BLE001
        out.append(f"  ❌ wirye_capacity import 실패: {e!r}")
        return "\n".join(out)

    out.append("\n── 누적 DB ──")
    # 점검이 실제 DB 를 만들면 안 된다(sqlite3.connect 는 파일을 생성한다).
    # 같은 폴더에 임시 파일로만 확인하고 지운다.
    try:
        import sqlite3
        db = Path(C.db_path())
        line("경로", db)
        line("존재", "예" if db.exists() else "아니오(첫 실행에서 생성)")
        probe = db.with_name(".wirye_probe.db")
        conn = sqlite3.connect(str(probe))
        conn.execute("CREATE TABLE t(x)")
        conn.commit()
        conn.close()
        probe.unlink(missing_ok=True)
        line("폴더 읽기·쓰기", "정상")
    except Exception as e:                     # noqa: BLE001
        out.append(f"  ❌ DB 폴더에 쓸 수 없음: {e!r}")

    out.append("\n── Qt ──")
    try:
        from PySide6 import QtCore, QtWidgets
        line("PySide6", QtCore.__version__)
        # 플러그인 위치는 배포 형태마다 다르다(Windows 휠 / Linux 휠 / 동결 번들).
        root = Path(QtCore.__file__).resolve().parent
        found = next((p for p in (root / "plugins" / "platforms",
                                  root / "Qt" / "plugins" / "platforms")
                      if p.is_dir()), None)
        line("platforms 폴더", found or f"❌ 못 찾음 (기준 {root})")
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        line("QApplication", "생성 성공")
        line("플랫폼 플러그인", app.platformName())
        for i, sc in enumerate(app.screens()):
            g = sc.geometry()
            line(f"화면 {i}", f"{g.width()}x{g.height()} @({g.x()},{g.y()}) "
                              f"배율 {sc.devicePixelRatio():g}")
    except Exception as e:                     # noqa: BLE001
        out.append(f"  ❌ Qt 초기화 실패: {e!r}")
        out.append("     → PATH 에 다른 프로그램의 Qt DLL 이 있으면 이 오류가 난다.")

    # PATH 오염 검사 — 사내 PC 에서 가장 흔한 원인. 다른 앱의 Qt DLL 이 먼저
    # 잡히면 우리 번들 DLL 대신 그것이 로드돼 조용히 죽는다.
    out.append("\n── PATH 의 다른 Qt DLL (있으면 충돌 위험) ──")
    hits = []
    for d in (os.environ.get("PATH") or "").split(os.pathsep):
        if not d:
            continue
        try:
            for name in ("Qt6Core.dll", "Qt5Core.dll"):
                if (Path(d) / name).exists():
                    hits.append(f"{name}  ←  {d}")
        except OSError:
            continue
    if hits:
        out.extend(f"  ⚠ {h}" for h in hits)
    else:
        out.append("  없음 (정상)")
    return "\n".join(out)


def run() -> int:
    log = log_path()
    _write(log, f"\n===== {datetime.datetime.now():%Y-%m-%d %H:%M:%S} 시작 "
                f"| exe={sys.executable} | frozen={getattr(sys, 'frozen', False)} =====\n")
    try:                                        # 네이티브 크래시도 로그로 받는다
        import faulthandler
        faulthandler.enable(log.open("a", encoding="utf-8", buffering=1))
    except Exception:                           # noqa: BLE001
        pass

    if "--selftest" in sys.argv[1:]:
        report = selftest()
        _write(log, report + "\n")
        alert("위례 입찰 산정 Tool — 환경 점검",
              f"{report}\n\n이 내용을 아래 파일에도 저장했습니다.\n{log}")
        return 0

    try:
        _write(log, "  [1/3] wirye_capacity import\n")
        from wirye_capacity.ui.app import main
        _write(log, "  [2/3] GUI 시작\n")
        rc = main()
        _write(log, f"  [3/3] 종료 (rc={rc})\n")
        return int(rc or 0)
    except SystemExit:
        raise
    except BaseException:                       # noqa: BLE001 — 조용한 종료 금지
        tb = traceback.format_exc()
        _write(log, tb)
        last = tb.strip().splitlines()[-1] if tb.strip() else "알 수 없는 오류"
        alert("위례 입찰 산정 Tool — 시작 실패",
              "프로그램을 시작하지 못했습니다.\n\n"
              f"{last}\n\n"
              f"자세한 내용을 아래 파일에 저장했습니다.\n{log}\n\n"
              "환경 점검:  WiryeBidTool.exe --selftest")
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
