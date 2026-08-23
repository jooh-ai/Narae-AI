"""엑셀1 자동 탐색 검증 — exe/폴더 옆 엑셀1을 날짜·시간만으로 쓰기 위한 A 방식."""
from pathlib import Path

import pytest

from wirye_capacity.rims.locate import app_dir, find_workbook, resolve_workbook


def _touch(p: Path) -> Path:
    p.write_text("x", encoding="utf-8")
    return p


def test_finds_base_load_test_file(tmp_path):
    """실제 파일명('… Base Load Test 실적.xlsx')을 자동 감지."""
    wb = _touch(tmp_path / "1. 위례열병합발전소 Base Load Test 실적.xlsx")
    assert find_workbook(tmp_path) == wb


def test_ignores_unrelated_xlsx(tmp_path):
    """출력 입찰파일·날씨파일 등 무관한 .xlsx 는 잡지 않는다."""
    _touch(tmp_path / "bid_20260415.xlsx")
    _touch(tmp_path / "엑셀3-1_날씨.xlsx")
    assert find_workbook(tmp_path) is None


def test_skips_excel_lock_file(tmp_path):
    """Excel 임시 잠금파일(~$...)은 제외."""
    _touch(tmp_path / "~$1. 위례 Base Load Test.xlsx")
    assert find_workbook(tmp_path) is None
    real = _touch(tmp_path / "위례 Base Load Test.xlsx")
    assert find_workbook(tmp_path) == real


def test_env_workbook_override_relative(tmp_path, monkeypatch):
    wb = _touch(tmp_path / "내엑셀1.xlsx")
    monkeypatch.setenv("WIRYE_WORKBOOK", "내엑셀1.xlsx")
    assert find_workbook(tmp_path) == wb


def test_env_workbook_override_absolute(tmp_path, monkeypatch):
    other = _touch(tmp_path / "별도위치.xlsx")
    monkeypatch.setenv("WIRYE_WORKBOOK", str(other))
    # directory 와 무관하게 절대경로 사용
    assert find_workbook(tmp_path / "다른폴더") == other


def test_env_workbook_override_missing_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("WIRYE_WORKBOOK", "없는파일.xlsx")
    assert find_workbook(tmp_path) is None


def test_app_dir_respects_wirye_home(tmp_path, monkeypatch):
    monkeypatch.setenv("WIRYE_HOME", str(tmp_path))
    assert app_dir() == tmp_path


def test_resolve_workbook_explicit_wins(tmp_path):
    _touch(tmp_path / "위례 Base Load Test.xlsx")
    explicit = tmp_path / "지정한엑셀1.xlsx"
    assert resolve_workbook(str(explicit), directory=tmp_path) == explicit


def test_resolve_workbook_falls_back_to_discovery(tmp_path):
    wb = _touch(tmp_path / "위례 Base Load Test.xlsx")
    assert resolve_workbook(None, directory=tmp_path) == wb


def test_missing_directory_returns_none(tmp_path):
    assert find_workbook(tmp_path / "존재안함") is None
