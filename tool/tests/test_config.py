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


# ── 보정 방법 저장 (시운전 중 방법을 바꿔 가며 비교하므로 선택이 남아야 한다) ──

def test_correction_method_default_is_gp_rbf(tmp_path):
    """설정이 없으면 GP·RBF 로 시작한다 (2026-08-25 기본값 변경).

    누적 36건 LOOCV 예측오차가 GP·RBF 1.294 < 구간평균 1.515 < 일괄 3.833 이라
    기본을 GP·RBF 로 옮겼다. 종전 기본은 엑셀4 방식(구간평균)이었다.

    path 를 반드시 넘긴다 — 안 넘기면 개발 PC 의 실제 설정 파일을 읽어서,
    누군가 GUI 에서 방법을 바꿔 둔 것만으로 이 테스트가 깨진다.
    """
    from wirye_capacity.config import correction_method
    assert correction_method(path=tmp_path / "none.json") == "gp:rbf"
    assert DEFAULTS["correction_method"] == "gp:rbf"


def test_correction_method_rejects_unknown_value(tmp_path):
    """설정에 이상한 값이 들어 있으면 조용히 기본값으로 돌아간다."""
    import json

    from wirye_capacity.config import correction_method
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({"correction_method": "gp:nope"}), encoding="utf-8")
    assert correction_method(path=cfg) == "gp:rbf"
    cfg.write_text(json.dumps({"correction_method": "gp:matern52"}), encoding="utf-8")
    assert correction_method(path=cfg) == "gp:matern52"    # 커널별 키는 유효하다


def test_correction_method_roundtrip(tmp_path, monkeypatch):
    from wirye_capacity import config as cf
    monkeypatch.setattr(cf, "HOME_CONFIG_PATH", tmp_path / "home.json")
    monkeypatch.setattr(cf, "app_config_path", lambda: tmp_path / "tool.json")
    for m in ("gp", "curve", "bin"):
        cf.set_config("correction_method", m)
        assert cf.correction_method() == m
    # Tool 폴더에 저장된다 — 폴더째 인수인계하면 선택도 함께 간다
    assert (tmp_path / "tool.json").exists()
    assert not (tmp_path / "home.json").exists()


def test_correction_method_rejects_garbage(tmp_path, monkeypatch):
    """설정파일이 손으로 편집돼 이상한 값이 들어와도 기본값으로 돌린다."""
    from wirye_capacity import config as cf
    monkeypatch.setattr(cf, "HOME_CONFIG_PATH", tmp_path / "home.json")
    monkeypatch.setattr(cf, "app_config_path", lambda: tmp_path / "tool.json")
    cf.set_config("correction_method", "무엄한값")
    assert cf.correction_method() == "gp:rbf"


def test_tool_folder_wins_over_home(tmp_path, monkeypatch):
    """예전 홈 설정은 살아 있고, Tool 폴더 값이 있으면 그것이 이긴다."""
    from wirye_capacity import config as cf
    home, tool = tmp_path / "home.json", tmp_path / "tool.json"
    monkeypatch.setattr(cf, "HOME_CONFIG_PATH", home)
    monkeypatch.setattr(cf, "app_config_path", lambda: tool)
    cf.set_config("opcua_host", "old-home-server", path=home)   # 예전 위치
    assert cf.get_config("opcua_host") == "old-home-server"     # 폴백으로 살아 있음
    cf.set_config("opcua_host", "new-tool-server")              # 기본 저장 = Tool 폴더
    assert cf.get_config("opcua_host") == "new-tool-server"
    assert cf.load_config(home)["opcua_host"] == "old-home-server"   # 홈은 그대로
