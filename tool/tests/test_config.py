"""사용자 설정(~/.wirye_tool.json) 저장/로드 — GUI 자동화(호스트 숨김)용."""
from wirye_capacity.config import DEFAULTS, get_config, load_config, set_config


def test_roundtrip(tmp_path):
    p = tmp_path / "cfg.json"
    set_config("opcua_host", "server1", path=p)
    assert get_config("opcua_host", path=p) == "server1"
    # 추가 키 저장 시 기존 키 보존
    set_config("template_path", "C:/x.xlsx", path=p)
    assert get_config("opcua_host", path=p) == "server1"
    assert get_config("template_path", path=p) == "C:/x.xlsx"


def test_missing_file_returns_default(tmp_path):
    p = tmp_path / "none.json"
    assert load_config(p) == {}
    # DEFAULTS 에 없는 키 → default 인자
    assert get_config("no_such_key", default="fallback", path=p) == "fallback"


def test_builtin_default_host(tmp_path):
    """설정파일이 없어도 내장 기본 호스트로 바로 동작(최초 실행 시 묻지 않음)."""
    p = tmp_path / "none.json"
    assert get_config("opcua_host", path=p) == DEFAULTS["opcua_host"]
    # 파일에 저장하면 파일 값이 우선
    set_config("opcua_host", "other", path=p)
    assert get_config("opcua_host", path=p) == "other"


def test_corrupt_file_returns_default(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{{{not json", encoding="utf-8")
    assert load_config(p) == {}
    set_config("k", "v", path=p)            # 손상 파일 위에도 저장 가능
    assert get_config("k", path=p) == "v"


def test_env_override_wins(tmp_path, monkeypatch):
    p = tmp_path / "cfg.json"
    set_config("opcua_host", "from-file", path=p)
    monkeypatch.setenv("WIRYE_OPCUA_HOST", "from-env")
    assert get_config("opcua_host", path=p) == "from-env"
