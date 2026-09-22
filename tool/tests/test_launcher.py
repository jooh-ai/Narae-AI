"""런처(wirye_gui) + 시작 진단(diag) — 조용한 종료 금지.

console=False 로 빌드하면 시작 중 무슨 일이 있어도 표준출력에 남지 않는다. 실제로 타
PC 에서 더블클릭해도 아무 반응이 없어 원인을 못 찾은 사례가 있었다(2026-08). 그때
로그가 '[2/3] GUI 시작' 에서 멈춰 main() 안쪽을 알 수 없었으므로, 단계 기록을
main() 내부까지 넣었다. 그 장치들이 계속 동작하는지 지킨다.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import wirye_gui  # noqa: E402
from wirye_capacity import diag  # noqa: E402


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """로그를 tmp 로 보내고 알림을 가로챈다."""
    log = tmp_path / diag.LOG_NAME
    monkeypatch.setattr(diag, "_path", log)          # 캐시에 직접 심는다
    seen = []
    monkeypatch.setattr(diag, "alert", lambda t, b: seen.append((t, b)))
    return log, seen


def test_startup_failure_is_logged_and_alerted(sandbox, monkeypatch):
    log, seen = sandbox
    real = __import__

    def boom(name, *a, **k):
        if name == "wirye_capacity.ui.app":
            raise ImportError("DLL load failed: 모의 실패")
        return real(name, *a, **k)

    monkeypatch.setattr("builtins.__import__", boom)
    assert wirye_gui.run() == 1                      # 예외를 밖으로 던지지 않는다
    body = log.read_text(encoding="utf-8")
    assert "런처: wirye_capacity.ui.app import" in body      # 어디까지 갔는지 남는다
    assert "DLL load failed" in body
    assert len(seen) == 1 and "시작 실패" in seen[0][0]
    assert "DLL load failed" in seen[0][1] and str(log) in seen[0][1]


def test_success_path_logs_stages(sandbox, monkeypatch):
    log, seen = sandbox
    import wirye_capacity.ui.app as uiapp
    monkeypatch.setattr(uiapp, "main", lambda *a, **k: 0)
    assert wirye_gui.run() == 0
    body = log.read_text(encoding="utf-8")
    assert "런처: main() 호출" in body
    assert "런처: 정상 종료" in body
    assert seen == []                                # 정상 실행에서는 알림 없음


def test_selftest_reports_and_creates_no_db(sandbox, monkeypatch, tmp_path):
    """점검이 실제 누적 DB 를 만들면 '첫 실행' 상태가 오염된다."""
    log, seen = sandbox
    db = tmp_path / "should_not_exist.db"
    monkeypatch.setenv("WIRYE_DB_PATH", str(db))
    # 화면 없는 환경에서 QApplication 이 qFatal 로 프로세스를 죽이지 않게 한다.
    # 이 테스트는 보고서 내용과 부작용을 보는 것이고, 실제 Qt 초기화 검증이 아니다.
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setattr(sys, "argv", ["wirye_gui.py", "--selftest"])
    assert wirye_gui.run() == 0
    report = log.read_text(encoding="utf-8")
    for section in ("실행 환경", "번들 자원", "누적 DB", "Qt", "PATH"):
        assert section in report, section
    assert "base_table.json" in report
    # abort 되더라도 그때까지의 내용이 남아야 한다 — 마지막에 한 번에 쓰면 안 된다
    assert "QApplication 생성 시도" in report
    assert not db.exists()
    assert len(seen) == 1 and "환경 점검" in seen[0][0]


def test_log_path_falls_back_when_folder_unwritable(monkeypatch, tmp_path):
    """Program Files 처럼 쓸 수 없는 곳에 설치돼도 로그는 남아야 한다.

    chmod 로 막으면 root 로 돌 때 권한이 무시돼 검증이 무효가 된다. 그래서 평범한
    파일 아래의 경로를 준다 — mkdir 이 NotADirectoryError(OSError)를 낸다.
    """
    blocker = tmp_path / "iam_a_file"
    blocker.write_text("", encoding="utf-8")
    fallback = tmp_path / "temp"
    fallback.mkdir()
    monkeypatch.setattr(diag, "_path", None)         # 캐시 비우기
    monkeypatch.setattr(diag, "app_dir", lambda: blocker / "sub")
    monkeypatch.setenv("TEMP", str(fallback))
    assert diag.log_path().parent == fallback


def test_stage_writes_one_line(sandbox):
    log, _ = sandbox
    diag.stage("테스트 단계")
    assert "테스트 단계" in log.read_text(encoding="utf-8")


def test_bare_report_survives_without_package(tmp_path, monkeypatch):
    """wirye_capacity 자체가 로드되지 않는 경우에도 파일에 남아야 한다."""
    monkeypatch.setattr(wirye_gui, "__file__", str(tmp_path / "wirye_gui.py"))
    monkeypatch.setenv("TEMP", str(tmp_path))
    wirye_gui._bare_report("Traceback...\nImportError: 번들 손상")
    logs = list(tmp_path.glob("wirye_error.log"))
    assert logs, "로그가 남지 않았다"
    assert "번들 손상" in logs[0].read_text(encoding="utf-8")
