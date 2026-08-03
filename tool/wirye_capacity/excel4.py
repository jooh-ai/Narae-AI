"""엑셀4 실측데이터 시트 읽기 — 시드 32건의 날짜 백필용.

시드 JSON(measurements_seed.json)에는 날짜가 없어 List-up 에 '-' 로 표시된다.
원본 엑셀4에는 날짜가 있으므로, (CIT, CC실측) 로 레코드를 매칭해 날짜를 채운다.

엑셀4 실측데이터 헤더(현장 확인):
  날짜 | 온도(°C) | 대기압(mbar) | RH(%) | 복수기압실측 | 복수기설계 | CC실측(MW)
      | W값(IGV) | 이론기준값(MW) | 보정값(MW) | 비고

시트명·헤더 위치는 파일마다 다를 수 있어 **모든 시트를 스캔**해 날짜+CC실측 헤더가
있는 시트를 자동 선택한다. 헤더가 병합셀로 2행에 걸친 경우(예: 상단 '복수기압',
하단 '실측')도 인접 2행을 결합해 인식한다. 실패 시 시트 목록·후보 헤더를 오류에
담아 --sheet 로 직접 지정할 수 있게 한다.
"""
from __future__ import annotations

from datetime import date as _date
from datetime import datetime

SHEET_CANDIDATES = ("실측데이터", "실측 데이터", "실측", "측정데이터")

_DATE_KEYS = ("날짜", "일자", "date", "테스트일", "시험일")
_CC_KEYS = ("cc실측", "실측cc", "cc(mw)", "cc실측(mw)")
_CIT_KEYS = ("온도", "cit", "기온", "대기온도", "흡기온도")


def _norm(v) -> str:
    return str(v).replace(" ", "").replace("\n", "").lower() if v is not None else ""


def _as_date_str(v) -> str | None:
    """셀 값 → 'YYYY-MM-DD' (datetime/date/문자열 허용)."""
    if isinstance(v, (datetime, _date)):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, str):
        s = v.strip().replace(".", "-").replace("/", "-").rstrip("-")
        for fmt in ("%Y-%m-%d", "%y-%m-%d", "%Y-%m", "%m-%d"):
            try:
                d = datetime.strptime(s, fmt)
            except ValueError:
                continue
            if fmt != "%m-%d":            # 연도 없는 형식은 매칭 불가 → 제외
                return d.strftime("%Y-%m-%d")
    return None


def _combined(rows: list[list], i: int) -> list[str]:
    """i행 + i+1행을 열별로 결합(병합셀 2행 헤더 대응)."""
    a = [_norm(v) for v in rows[i]]
    b = [_norm(v) for v in rows[i + 1]] if i + 1 < len(rows) else []
    n = max(len(a), len(b))
    a += [""] * (n - len(a))
    b += [""] * (n - len(b))
    return [x + y for x, y in zip(a, b)]


def _find_header(rows: list[list]) -> tuple[int, int, int, int | None] | None:
    """헤더 행을 찾아 (헤더행, 날짜열, CC실측열, 온도열) 반환. 못 찾으면 None."""
    for i in range(min(len(rows), 40)):
        for cells in (_combined(rows, i), [_norm(v) for v in rows[i]]):
            di = next((j for j, c in enumerate(cells)
                       if any(c.startswith(k) or c == k for k in _DATE_KEYS)), None)
            if di is None:
                continue
            ci = next((j for j, c in enumerate(cells)
                       if any(k in c for k in _CC_KEYS)), None)
            if ci is None:      # 'CC' 와 '실측' 이 같은 셀에 있으면 순서 무관 허용
                ci = next((j for j, c in enumerate(cells)
                           if "cc" in c and "실측" in c), None)
            if ci is None:
                continue
            ti = next((j for j, c in enumerate(cells)
                       if any(c.startswith(k) for k in _CIT_KEYS)), None)
            return i, di, ci, ti
    return None


def _diagnose(wb) -> str:
    """시트별 상단 헤더 후보를 요약 — --sheet 지정에 참고."""
    lines = []
    for name in wb.sheetnames:
        ws = wb[name]
        first = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), ())
        head = " | ".join(str(v)[:12] for v in first[:8] if v is not None)
        lines.append(f"  · {name}: {head or '(빈 행)'}")
    return "\n".join(lines)


def list_excel4_sheets(path) -> str:
    """진단용 — 시트 목록과 각 시트 첫 행 머리글 요약."""
    from .excel_io import load_workbook_safe
    return _diagnose(load_workbook_safe(path, data_only=True))


def load_excel4_records(path, sheet: str | None = None) -> list[dict]:
    """엑셀4 실측데이터에서 [{date, cit, cc_meas}, …] 추출 (매칭용 최소 필드)."""
    from .excel_io import ExcelOpenError, load_workbook_safe

    wb = load_workbook_safe(path, data_only=True)
    if sheet:
        if sheet not in wb.sheetnames:
            raise ExcelOpenError(
                f"'{sheet}' 시트가 없습니다. 이 파일의 시트 목록:\n{_diagnose(wb)}")
        order = [sheet]
    else:   # 이름 후보 우선, 그 다음 전체 시트 스캔
        order = [s for s in SHEET_CANDIDATES if s in wb.sheetnames]
        order += [s for s in wb.sheetnames if s not in order]

    for name in order:
        rows = [[c.value for c in r] for r in wb[name].iter_rows()]
        found = _find_header(rows)
        if found is None:
            continue
        hdr, di, ci, ti = found
        out: list[dict] = []
        for r in rows[hdr + 1:]:
            d = _as_date_str(r[di]) if di < len(r) else None
            ccv = r[ci] if ci < len(r) else None
            if d is None or not isinstance(ccv, (int, float)):
                continue
            citv = r[ti] if ti is not None and ti < len(r) else None
            out.append({"date": d, "cc_meas": float(ccv), "sheet": name,
                        "cit": float(citv) if isinstance(citv, (int, float)) else None})
        if out:                      # 헤더도 맞고 데이터도 있는 시트 = 정답
            return out

    raise ExcelOpenError(
        "엑셀4에서 실측데이터(날짜 + CC실측) 시트를 찾지 못했습니다.\n"
        f"검사한 시트 {len(order)}개:\n{_diagnose(wb)}\n\n"
        "해결: 위 목록에서 실측 기록이 있는 시트명을 --sheet \"시트명\" 으로 지정하세요.\n"
        "(날짜 열과 CC실측 열 머리글이 있어야 합니다)")
