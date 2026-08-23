"""런처(wirye_gui) — 조용한 종료 금지. 오류가 로그와 알림으로 남아야 한다.

console=False 로 빌드하면 시작 중 예외가 표준출력에 남지 않는다. 실제로 타 PC 에서
더블클릭해도 아무 반응이 없어 원인을 못 찾은 사례가 있었다(2026-08). 그 재발 방지.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import wirye_gui  # noqa: E402


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """로그·알림을 가로채 tmp 로 보낸다."""
    log = tmp_path / wirye_gui.LOG_NAME
    monkeypatch.setattr(wirye_gui, "log_path", lambda: log)
    seen = []
    monkeypatch.setattr(wirye_gui, "alert", lambda t, b: seen.append((t, b)))
    return log, seen


def test_startup_failure_is_logged_and_alerted(sandbox, monkeypatch):
    log, seen = sandbox
    real = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

    def boom(name, *a, **k):
        if name == "wirye_capacity.ui.app":
            raise ImportError("DLL load failed: 모의 실패")
        return real(name, *a, **k)

    monkeypatch.setattr("builtins.__import__", boom)
    assert wirye_gui.run() == 1                  # 예외를 밖으로 던지지 않는다
    body = log.read_text(encoding="utf-8")
    assert "[1/3]" in body                       # 어디까지 갔는지 남는다
    assert "DLL load failed" in body
    assert len(seen) == 1 and "시작 실패" in seen[0][0]
    assert "DLL load failed" in seen[0][1] and str(log) in seen[0][1]


def test_success_path_logs_stages(sandbox, monkeypatch):
    log, seen = sandbox
    import wirye_capacity.ui.app as uiapp
    monkeypatch.setattr(uiapp, "main", lambda *a, **k: 0)
    assert wirye_gui.run() == 0
    body = log.read_text(encoding="utf-8")
    assert "[2/3]" in body and "[3/3]" in body
    assert seen == []                            # 정상 실행에서는 알림 없음


def test_selftest_reports_and_creates_no_db(sandbox, monkeypatch, tmp_path):
    """점검이 실제 누적 DB 를 만들어 버리면 '첫 실행' 상태가 오염된다."""
    log, seen = sandbox
    db = tmp_path / "should_not_exist.db"
    monkeypatch.setenv("WIRYE_DB_PATH", str(db))
    monkeypatch.setattr(sys, "argv", ["wirye_gui.py", "--selftest"])
    assert wirye_gui.run() == 0
    report = log.read_text(encoding="utf-8")
    for section in ("실행 환경", "번들 자원", "누적 DB", "Qt", "PATH"):
        assert section in report, section
    assert "base_table.json" in report
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
    monkeypatch.setattr(wirye_gui, "app_dir", lambda: blocker / "sub")
    monkeypatch.setenv("TEMP", str(fallback))
    assert wirye_gui.log_path().parent == fallback
