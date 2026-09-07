"""GUI 실행 진입점 (PyInstaller 패키징용).

패키지 상대 import(from .. import ...)가 있는 ui/app.py 를 직접 스크립트로 돌리면
import 가 깨지므로, 절대 import 로 감싸는 런처를 별도로 둔다.

    python wirye_gui.py                 # 소스 실행
    pyinstaller wirye_tool.spec         # exe 빌드(이 파일이 진입점)
    WiryeBidTool.exe --selftest         # 실행 환경 점검(로그 + 대화상자)

왜 런처가 두꺼운가 — '조용한 종료'를 없애기 위해서다
    spec 의 console=False 라서 시작 중 예외가 나면 표준출력이 없다. 더블클릭해도
    아무 반응 없이 프로세스가 사라지고 원인이 남지 않는다(2026-08 타 PC 실제 사례:
    10회 재빌드하며 원인을 못 찾았다). 그래서 전 구간을 감싸 오류를 로그와
    대화상자로 남긴다. 로그·알림 구현은 wirye_capacity/diag.py 에 있고, GUI 도
    같은 파일에 단계를 적으므로 어디서 멈췄는지 한 번의 실행으로 알 수 있다.

    diag 를 module 최상단에서 import 하면 안 된다 — wirye_capacity 자체가 로드되지
    않는 경우(번들 손상, DLL 문제)를 보고할 수 없게 된다. 그래서 run() 안에서
    import 하고, 실패하면 _bare_report 로 자급자족 보고한다.

로그 위치: exe 폴더의 wirye_error.log (쓸 수 없으면 %TEMP% → 홈 폴더)
"""
from __future__ import annotations

import datetime
import os
import sys
import traceback
from pathlib import Path


def _bare_report(text: str) -> None:
    """wirye_capacity 조차 import 되지 않는 최악의 경우 — diag 없이 보고한다."""
    root = (Path(sys.executable).resolve().parent if getattr(sys, "frozen", False)
            else Path(__file__).resolve().parent)
    target = Path("wirye_error.log")
    for d in (root, Path(os.environ.get("TEMP") or "."), Path.home()):
        try:
            target = d / "wirye_error.log"
            with target.open("a", encoding="utf-8") as f:
                f.write(f"\n===== {datetime.datetime.now():%Y-%m-%d %H:%M:%S} "
                        f"패키지 로드 실패 =====\n{text}")
            break
        except OSError:
            continue
    last = text.strip().splitlines()[-1] if text.strip() else "알 수 없는 오류"
    body = f"프로그램을 시작하지 못했습니다 (패키지 로드 실패).\n\n{last}\n\n{target}"
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(   # type: ignore[attr-defined]
                None, body, "위례 입찰 산정 Tool", 0x10 | 0x40000)
            return
        except Exception:          # noqa: BLE001
            pass
    sys.stderr.write(body + "\n")


def selftest() -> str:
    """실행 환경 점검 보고서. 예외를 내지 않고 문자열로 돌려준다.

    한 줄씩 즉시 로그에 쓴다(마지막에 한 번에 쓰면 안 된다). Qt 플랫폼 플러그인이
    없거나 PATH 의 다른 Qt DLL 과 충돌하면 QApplication 생성이 qFatal 로 프로세스를
    abort 시킨다 — 예외가 아니라 즉사이므로 그때까지의 내용이 이미 파일에 있어야
    한다. 정작 점검이 가장 필요한 상황이 그 경우다.
    """
    from wirye_capacity.diag import app_dir, write
    out: list[str] = []

    def add(text: str) -> None:
        out.append(text)
        write(text + "\n")

    def line(k: str, v) -> None:
        add(f"  {k:<22} {v}")

    add("── 실행 환경 ──")
    line("exe", sys.executable)
    line("frozen", getattr(sys, "frozen", False))
    line("_MEIPASS", getattr(sys, "_MEIPASS", "(없음 — 소스 실행)"))
    line("Tool 폴더", app_dir())
    line("Python", sys.version.split()[0])
    line("플랫폼", f"{sys.platform} / {os.name}")

    add("\n── 번들 자원 ──")
    try:
        from wirye_capacity import constants as C
        for rel in ("data/base_table.json", "data/measurements_seed.json",
                    "templates/excel3_profile_template.xlsx",
                    "templates/excel3_profile_template.tpl"):
            p = C.resource(*rel.split("/"))
            line(rel, f"{p.stat().st_size:,} 바이트" if p.exists() else "❌ 없음")
        line("logo.png", "있음" if C.logo_path() else "없음(이모지로 대체)")
    except Exception as e:                     # noqa: BLE001
        add(f"  ❌ wirye_capacity import 실패: {e!r}")
        return "\n".join(out)

    add("\n── 누적 DB ──")
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
        add(f"  ❌ DB 폴더에 쓸 수 없음: {e!r}")

    add("\n── Qt ──")
    try:
        from PySide6 import QtCore, QtWidgets
        line("PySide6", QtCore.__version__)
        # 플러그인 위치는 배포 형태마다 다르다(Windows 휠 / Linux 휠 / 동결 번들).
        root = Path(QtCore.__file__).resolve().parent
        found = next((p for p in (root / "plugins" / "platforms",
                                  root / "Qt" / "plugins" / "platforms")
                      if p.is_dir()), None)
        line("platforms 폴더", found or f"❌ 못 찾음 (기준 {root})")
        add("  (QApplication 생성 시도 — 이 줄이 마지막이면 Qt 플랫폼 초기화에서 죽었다)")
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        line("QApplication", "생성 성공")
        line("플랫폼 플러그인", app.platformName())
        for i, sc in enumerate(app.screens()):
            g = sc.geometry()
            line(f"화면 {i}", f"{g.width()}x{g.height()} @({g.x()},{g.y()}) "
                              f"배율 {sc.devicePixelRatio():g}")
    except Exception as e:                     # noqa: BLE001
        add(f"  ❌ Qt 초기화 실패: {e!r}")
        add("     → PATH 에 다른 프로그램의 Qt DLL 이 있으면 이 오류가 난다.")

    # PATH 오염 검사 — 사내 PC 에서 흔한 원인. 다른 앱의 Qt DLL 이 먼저 잡히면
    # 우리 번들 DLL 대신 그것이 로드돼 조용히 죽는다.
    add("\n── PATH 의 다른 Qt DLL (있으면 충돌 위험) ──")
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
    for h in hits:
        add(f"  ⚠ {h}")
    if not hits:
        add("  없음 (정상)")
    return "\n".join(out)


def run() -> int:
    try:
        from wirye_capacity import diag
    except BaseException:                       # noqa: BLE001
        _bare_report(traceback.format_exc())
        return 1

    log = diag.log_path()
    diag.write(f"\n===== {datetime.datetime.now():%Y-%m-%d %H:%M:%S} 시작 "
               f"| exe={sys.executable} | frozen={getattr(sys, 'frozen', False)} =====\n")
    try:                                        # 네이티브 크래시도 로그로 받는다
        import faulthandler
        faulthandler.enable(log.open("a", encoding="utf-8", buffering=1))
    except Exception:                           # noqa: BLE001
        pass

    if "--selftest" in sys.argv[1:]:
        report = selftest()           # 진행하며 이미 로그에 쓰였다
        diag.alert("위례 입찰 산정 Tool — 환경 점검",
                   f"{report}\n\n이 내용을 아래 파일에도 저장했습니다.\n{log}")
        return 0

    try:
        diag.stage("런처: wirye_capacity.ui.app import")
        from wirye_capacity.ui.app import main
        diag.stage("런처: main() 호출")
        rc = main()
        diag.stage(f"런처: 정상 종료 (rc={rc})")
        return int(rc or 0)
    except SystemExit:
        raise
    except BaseException:                       # noqa: BLE001 — 조용한 종료 금지
        tb = traceback.format_exc()
        diag.write(tb)
        last = tb.strip().splitlines()[-1] if tb.strip() else "알 수 없는 오류"
        diag.alert("위례 입찰 산정 Tool — 시작 실패",
                   "프로그램을 시작하지 못했습니다.\n\n"
                   f"{last}\n\n"
                   f"자세한 내용을 아래 파일에 저장했습니다.\n{log}\n\n"
                   "환경 점검:  WiryeBidTool.exe --selftest")
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
