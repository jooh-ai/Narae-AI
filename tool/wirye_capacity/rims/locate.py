"""엑셀1(RiMS 워크북) 자동 탐색 — 실행파일(exe)과 같은 폴더에서 찾기.

A 방식: 매번 파일을 첨부하지 않고, exe 옆에 둔 엑셀1을 자동으로 찾아
'날짜·시간만 입력'하면 되도록 한다.

기준 폴더(app_dir):
  - 동결(PyInstaller exe): 실행파일이 있는 폴더
  - 스크립트 실행: 현재 작업 폴더
  - 환경변수 WIRYE_HOME 이 있으면 그 경로 우선(개발/테스트용 오버라이드)

파일명:
  - 환경변수 WIRYE_WORKBOOK 이 있으면 그 이름/경로를 그대로 사용
  - 없으면 WORKBOOK_PATTERNS 우선순위로 .xlsx 탐색
    (출력 입찰파일·엑셀3-1 날씨파일을 잘못 잡지 않도록 '엑셀1'스러운 패턴만 사용)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 엑셀1 기본 파일명 패턴 (exe 폴더 기준, 우선순위 순).
# 실제 파일: "1. 위례열병합발전소 Base Load Test 실적.xlsx" → 첫 패턴에 매칭.
WORKBOOK_PATTERNS = ("*Base Load Test*.xlsx", "*Base Load*.xlsx", "*위례*Test*.xlsx")


def app_dir() -> Path:
    """엑셀1을 두는 기준 폴더. exe면 실행파일 폴더, 아니면 cwd(또는 WIRYE_HOME)."""
    override = os.environ.get("WIRYE_HOME")
    if override:
        return Path(override)
    if getattr(sys, "frozen", False):                 # PyInstaller로 동결된 exe
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def find_workbook(directory: Path | None = None,
                  patterns: tuple[str, ...] = WORKBOOK_PATTERNS) -> Path | None:
    """기준 폴더에서 엑셀1로 보이는 .xlsx를 패턴 우선순위로 탐색. 없으면 None.

    WIRYE_WORKBOOK 환경변수가 있으면 그 이름/경로를 우선(절대경로 또는 폴더 상대).
    Excel 임시 잠금파일(~$...)은 제외.
    """
    directory = Path(directory) if directory is not None else app_dir()
    name = os.environ.get("WIRYE_WORKBOOK")
    if name:
        p = Path(name)
        if not p.is_absolute():
            p = directory / name
        return p if p.exists() else None
    if not directory.exists():
        return None
    for pat in patterns:
        hits = [h for h in sorted(directory.glob(pat)) if not h.name.startswith("~$")]
        if hits:
            return hits[0]
    return None


def resolve_workbook(explicit: str | None = None,
                     directory: Path | None = None) -> Path | None:
    """명시 경로가 있으면 그것을, 없으면 기준 폴더에서 자동 탐색한 경로를 반환."""
    if explicit:
        return Path(explicit)
    return find_workbook(directory)
