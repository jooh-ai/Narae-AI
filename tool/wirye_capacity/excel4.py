"""엑셀4 '실측데이터' 시트 읽기 — 시드 32건의 날짜 백필용.

시드 JSON(measurements_seed.json)에는 날짜가 없어 List-up 에 '-' 로 표시된다.
원본 엑셀4에는 날짜가 있으므로, (CIT, CC실측) 로 레코드를 매칭해 날짜를 채운다.

엑셀4 '실측데이터' 헤더(현장 확인):
  날짜 | 온도(°C) | 대기압(mbar) | RH(%) | 복수기압실측 | 복수기설계 | CC실측(MW)
      | W값(IGV) | 이론기준값(MW) | 보정값(MW) | 비고
"""
from __future__ import annotations

from datetime import date as _date
from datetime import datetime

SHEET_CANDIDATES = ("실측데이터", "실측 데이터")


def _norm(v) -> str:
    return str(v).replace(" ", "").replace("\n", "").lower() if v is not None else ""


def _as_date_str(v) -> str | None:
    """셀 값 → 'YYYY-MM-DD' (datetime/date/문자열 허용)."""
    if isinstance(v, (datetime, _date)):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, str):
        s = v.strip().replace(".", "-").replace("/", "-")
        for fmt in ("%Y-%m-%d", "%y-%m-%d"):
            try:
                return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
    return None


def load_excel4_records(path, sheet: str | None = None) -> list[dict]:
    """엑셀4 실측데이터에서 [{date, cit, cc_meas}, …] 추출 (매칭용 최소 필드)."""
    from .excel_io import ExcelOpenError, load_workbook_safe

    wb = load_workbook_safe(path, data_only=True)
    names = [sheet] if sheet else [s for s in SHEET_CANDIDATES if s in wb.sheetnames]
    if not names:
        names = [wb.sheetnames[0]]
    ws = wb[names[0]]
    rows = [[c.value for c in r] for r in ws.iter_rows()]

    hdr = ci = cc = ct = None
    for i, r in enumerate(rows[:30]):                 # 상단에서 헤더 행 탐색
        cells = [_norm(v) for v in r]
        if any(c.startswith("날짜") for c in cells):
            hdr = i
            ci = next((j for j, c in enumerate(cells) if c.startswith("날짜")), None)
            cc = next((j for j, c in enumerate(cells) if "cc실측" in c), None)
            ct = next((j for j, c in enumerate(cells)
                       if c.startswith("온도") or "cit" in c), None)
            break
    if hdr is None or ci is None or cc is None:
        raise ExcelOpenError(
            f"'{names[0]}' 시트에서 날짜/CC실측 헤더를 찾지 못했습니다. "
            "엑셀4 '실측데이터' 시트인지 확인하세요.")

    out: list[dict] = []
    for r in rows[hdr + 1:]:
        if ci >= len(r):
            continue
        d = _as_date_str(r[ci])
        ccv = r[cc] if cc < len(r) else None
        if d is None or not isinstance(ccv, (int, float)):
            continue
        citv = r[ct] if ct is not None and ct < len(r) else None
        out.append({"date": d, "cc_meas": float(ccv),
                    "cit": float(citv) if isinstance(citv, (int, float)) else None})
    return out
