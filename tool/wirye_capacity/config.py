"""사용자 설정 저장 — GUI 자동화용.

RiMS(OPC UA) 서버 호스트나 보정 방법처럼 "한 번 정하면 잘 바뀌지 않는" 값을
화면에서 치우고 여기 저장한다.

저장 위치 — 누적 DB 와 같은 원칙(Tool 폴더)
    쓰기 : Tool 폴더의 wirye_tool.json. 담당자가 바뀌어 폴더째 인수인계하면
           설정도 함께 간다. 보정 방법은 입찰 신고값을 바꾸는 값이라 DB 와
           떨어져 있으면 안 된다.
    읽기 : 홈 폴더(~/.wirye_tool.json) → Tool 폴더 순으로 겹쳐 읽고 Tool 폴더가
           이긴다. 예전 홈 설정(opcua_host 등)이 그대로 살아 있게 하는 장치다.
    Tool 폴더에 쓸 수 없으면(예: Program Files 설치) 홈 폴더로 물러난다.

우선순위: 환경변수(WIRYE_<KEY 대문자>) > Tool 폴더 > 홈 폴더 > DEFAULTS > 인자
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from . import constants as C

CONFIG_NAME = "wirye_tool.json"
HOME_CONFIG_PATH = Path.home() / ".wirye_tool.json"     # 예전 위치 (읽기 전용 폴백)
CONFIG_PATH = HOME_CONFIG_PATH                          # 하위호환 별칭

# 사내 기본값 — 설정파일/환경변수가 없어도 바로 동작(자동화 원칙: 묻지 않는다)
DEFAULTS = {
    "opcua_host": "skes-rimspall1",   # DataPARC OPC UA 사이트 서버
    "correction_method": "bin",       # 'bin' | 'curve' | 'gp' — 화면에서 고른 값이 남는다
}

# 선택 가능한 보정 방법 — 'bin'/'curve' + GP 커널별. 'gp' 는 예전 설정 파일에
# 저장돼 있을 수 있어 별칭으로 계속 허용한다(읽을 때 gp:rbf 로 해석된다).
from .select import METHODS as _SEL_METHODS  # noqa: E402

CORRECTION_METHODS = ("gp", *_SEL_METHODS)


def app_config_path() -> Path:
    """Tool 폴더의 설정파일 경로 (기본 저장 위치)."""
    return C.app_dir() / CONFIG_NAME


def _read(path: str | Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def load_config(path: str | Path | None = None) -> dict:
    """설정 전체. path 를 주면 그 파일만 읽는다(테스트·명시 지정용)."""
    if path is not None:
        return _read(path)
    merged = _read(HOME_CONFIG_PATH)
    merged.update(_read(app_config_path()))      # Tool 폴더가 홈보다 우선
    return merged


def get_config(key: str, default=None, path: str | Path | None = None):
    """우선순위: 환경변수 > Tool 폴더 > 홈 폴더 > 내장 기본값(DEFAULTS) > default."""
    env = os.environ.get(f"WIRYE_{key.upper()}")
    if env:
        return env
    data = load_config(path)
    if key in data:
        return data[key]
    return DEFAULTS.get(key, default)


def set_config(key: str, value, path: str | Path | None = None) -> None:
    """Tool 폴더에 저장. 쓸 수 없으면 홈 폴더로 물러난다."""
    targets = [Path(path)] if path is not None else [app_config_path(), HOME_CONFIG_PATH]
    for p in targets:
        data = _read(p)
        data[key] = value
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return
        except OSError:
            continue


def correction_method(default: str | None = None,
                      path: str | Path | None = None) -> str:
    """저장된 보정 방법. 값이 깨져 있으면 기본값('bin')으로 돌린다.

    path 는 설정 파일을 직접 지정할 때 쓴다 — 없으면 실제 설정 파일을 읽으므로
    테스트가 개발 PC 의 설정에 오염된다(2026-08-25에 실제로 겪었다).
    """
    v = get_config("correction_method", default, path=path)
    return v if v in CORRECTION_METHODS else DEFAULTS["correction_method"]
