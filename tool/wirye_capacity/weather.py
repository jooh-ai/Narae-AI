"""날씨 로더 — 엑셀3-1(외부망 크롤링) 파싱 → 입찰 적용 대기압 산정.

엑셀3-1 레이아웃(성남비행장, 7일 × 3시간대):
  A1            : 캡처 시각
  'Pressure'    : 섹션 시작 → 다음 헤더행(시간대 0,3,…,21 + '중위'+'최소'), 이후 일자별 행
  'Tempereture' : 온도 섹션(동일 구조, '중위'+'취약')

적용 대기압 = (해당 일 또는 전체 '중위' 대기압) + 위치보정(−8mbar; 성남비행장↔발전소).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import constants as C


@dataclass
class WeatherForecast:
    capture: str | None
    days: list[str]
    times: list[int]
    pressure_median: dict[str, float]
    pressure_min: dict[str, float] = field(default_factory=dict)
    pressure_grid: dict[str, list[float]] = field(default_factory=dict)   # day → 시간대별 대기압
    temp_median: dict[str, float] = field(default_factory=dict)
    update_time: str | None = None            # 'Update time :' 값 (예: '17:00')


def _grid(path: str):
    from .excel_io import load_workbook_safe
    wb = load_workbook_safe(path, data_only=True)      # 보안/손상 파일 → 친절한 오류
    ws = wb[wb.sheetnames[0]]
    return [[c.value for c in r] for r in ws.iter_rows()]


def _find_label(rows, label: str) -> int | None:
    for i, r in enumerate(rows):
        for v in r:
            if isinstance(v, str) and v.strip() == label:
                return i
    return None


def _parse_block(rows, start: int):
    """섹션 시작행 이후의 (중위dict, 최소dict, grid, days, times) 파싱."""
    hdr = None
    for i in range(start + 1, len(rows)):
        if any(isinstance(v, str) and v.strip() == "중위" for v in rows[i]):
            hdr = i
            break
    if hdr is None:
        return {}, {}, {}, [], []          # 5-tuple (grid 포함) — 헤더 없을 때 안전 반환
    header = rows[hdr]
    med_c = next(j for j, v in enumerate(header) if isinstance(v, str) and v.strip() == "중위")
    min_c = next((j for j, v in enumerate(header)
                  if isinstance(v, str) and v.strip() in ("최소", "취약")), None)
    time_cols = [j for j, v in enumerate(header)
                 if isinstance(v, (int, float)) and not isinstance(v, bool)]
    times = [int(header[j]) for j in time_cols]
    days: list[str] = []
    med: dict[str, float] = {}
    mn: dict[str, float] = {}
    grid: dict[str, list[float]] = {}
    for i in range(hdr + 1, len(rows)):
        label = rows[i][0] if rows[i] else None
        if not isinstance(label, str) or not label.strip():
            break
        if label.strip() in ("Pressure", "Tempereture", "Temperature"):
            break
        days.append(label)
        row = rows[i]
        if med_c < len(row) and isinstance(row[med_c], (int, float)):
            med[label] = float(row[med_c])
        if min_c is not None and min_c < len(row) and isinstance(row[min_c], (int, float)):
            mn[label] = float(row[min_c])
        grid[label] = [float(row[j]) if j < len(row) and isinstance(row[j], (int, float))
                       else None for j in time_cols]
    return med, mn, grid, days, times


def _find_update_time(rows) -> str | None:
    """상단 몇 행에서 'Update time :' 라벨 옆 값을 찾는다 (시간/문자열 모두 허용)."""
    for r in rows[:8]:
        for j, v in enumerate(r):
            if isinstance(v, str) and v.strip().lower().startswith("update time"):
                for nxt in r[j + 1:]:
                    if nxt is None:
                        continue
                    return nxt.strftime("%H:%M") if hasattr(nxt, "strftime") else str(nxt)
    return None


def load_excel3_1(path: str) -> WeatherForecast:
    """엑셀3-1 파일 파싱."""
    rows = _grid(path)
    capture = rows[0][0] if rows and rows[0] else None
    p_i = _find_label(rows, "Pressure")
    t_i = _find_label(rows, "Tempereture") or _find_label(rows, "Temperature")
    if p_i is not None:
        p_med, p_min, p_grid, days, times = _parse_block(rows, p_i)
    else:
        p_med, p_min, p_grid, days, times = {}, {}, {}, [], []
    t_med = _parse_block(rows, t_i)[0] if t_i is not None else {}
    return WeatherForecast(capture=str(capture) if capture is not None else None,
                           days=days, times=times, pressure_median=p_med,
                           pressure_min=p_min, pressure_grid=p_grid, temp_median=t_med,
                           update_time=_find_update_time(rows))


def bid_days(fc: WeatherForecast) -> list[str]:
    """입찰 적용 대기압에 쓰는 예보일 목록 (3~7일차 = D+2~D+6).

    엑셀3 '온도 Profile'!M2 = AVERAGE(Y8:Y12)-8 과 같은 창이다. 양식이 7일 고정이
    아니면 오류로 막는다 — 잘못된 대기압은 프로파일 61행 전체를 조용히 밀어버리고
    (0.4 MW/mbar) 입찰 문서에 그대로 들어간다. 조용히 틀리는 것보다 멈추는 게 낫다.
    """
    lo, hi = C.WEATHER_BID_SLICE
    if len(fc.days) != C.WEATHER_FORECAST_DAYS:
        raise ValueError(
            f"예보 파일의 날짜가 {len(fc.days)}일입니다 — {C.WEATHER_FORECAST_DAYS}일 "
            f"양식이어야 합니다(엑셀3 M2 수식이 {lo + 1}~{hi}일차를 평균하므로). "
            f"읽은 날짜: {fc.days}")
    return fc.days[lo:hi]


def applied_pressure(fc: WeatherForecast, *,
                     offset: float = C.WEATHER_SITE_OFFSET) -> float:
    """입찰 적용 대기압(mbar) = 3~7일차 중위 대기압의 평균 + 위치보정(−8).

    엑셀3 '온도 Profile'!M2 = AVERAGE(Y8:Y12)-8 을 파이썬으로 그대로 옮긴 것이다.
    적용일을 고르는 인자는 없다 — 담당자 실무가 이 창 하나로 고정이고, 고를 수
    있게 두면 M2 표시값과 파일 내용이 어긋난다(2026-08-25 부장님 확인).
    """
    days = bid_days(fc)
    vals = [fc.pressure_median[d] for d in days if d in fc.pressure_median]
    if len(vals) != len(days):
        missing = [d for d in days if d not in fc.pressure_median]
        raise ValueError(f"중위 대기압이 없는 날짜가 있습니다: {missing}")
    return sum(vals) / len(vals) + offset
