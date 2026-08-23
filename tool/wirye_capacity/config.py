"""사용자 설정 저장 (~/.wirye_tool.json) — GUI 자동화용.

RiMS(OPC UA) 서버 호스트처럼 "한 번 정하면 바뀌지 않는" 값을 화면에서 치우고
여기 저장한다. 우선순위: 환경변수(WIRYE_<KEY 대문자>) > 설정파일 > default.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG_PATH = Path.home() / ".wirye_tool.json"

# 사내 기본값 — 설정파일/환경변수가 없어도 바로 동작(자동화 원칙: 묻지 않는다)
DEFAULTS = {
    "opcua_host": "skes-rimspall1",   # DataPARC OPC UA 사이트 서버
}


def load_config(path: str | Path = CONFIG_PATH) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def get_config(key: str, default=None, path: str | Path = CONFIG_PATH):
    """우선순위: 환경변수 > 설정파일 > 내장 기본값(DEFAULTS) > default 인자."""
    env = os.environ.get(f"WIRYE_{key.upper()}")
    if env:
        return env
    data = load_config(path)
    if key in data:
        return data[key]
    return DEFAULTS.get(key, default)


def set_config(key: str, value, path: str | Path = CONFIG_PATH) -> None:
    data = load_config(path)
    data[key] = value
    p = Path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass
