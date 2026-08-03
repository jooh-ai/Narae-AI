"""엑셀 파일 열기 공통 처리 — 사내 보안(DRM)·손상 파일을 사람이 읽을 수 있는 오류로.

openpyxl 은 암호화·손상 파일에서 `BadZipFile: File is not a zip file` 를 던지는데,
현장에서는 "사내 문서 보안이 걸린 파일"이 가장 흔한 원인이다. 원인·해결책을 담은
ExcelOpenError 로 바꿔 GUI 팝업/CLI 에 그대로 노출한다.
"""
from __future__ import annotations

from pathlib import Path


class ExcelOpenError(RuntimeError):
    """엑셀 파일을 열 수 없음(보안/손상). 메시지에 해결 방법 포함."""


def load_workbook_safe(path, **kwargs):
    """openpyxl.load_workbook 래퍼 — 보안/손상 파일을 ExcelOpenError 로 변환."""
    import zipfile

    from openpyxl import load_workbook
    p = Path(path)
    if not p.exists():
        raise ExcelOpenError(f"파일이 없습니다:\n{p}")
    try:
        return load_workbook(p, **kwargs)
    except zipfile.BadZipFile as e:
        raise ExcelOpenError(
            f"엑셀 파일을 열 수 없습니다:\n{p.name}\n\n"
            "원인: 사내 문서 보안(DRM)이 걸려 있거나, 다운로드 중 파일이 손상되었습니다.\n\n"
            "해결: 파일을 Excel 에서 열어 [파일 → 다른 이름으로 저장]으로 "
            "보안이 해제된 사본(.xlsx)을 만든 뒤 그 파일을 지정하세요."
        ) from e
    except Exception as e:   # noqa: BLE001 — 암호 보호 등
        raise ExcelOpenError(f"엑셀 파일을 열 수 없습니다:\n{p.name}\n\n{e}") from e
