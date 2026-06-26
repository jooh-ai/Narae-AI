"""날씨 로더(Phase 5) 검증 — 엑셀3-1 형식 합성 픽스처로 파싱·적용대기압 확인."""
import pytest

from wirye_capacity import constants as C
from wirye_capacity.weather import applied_pressure, load_excel3_1


def _make_excel3_1(path):
    """엑셀3-1 레이아웃(Pressure/Tempereture 섹션) 합성 픽스처."""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws["A1"] = "2026-04-15 18:09:12"
    # Pressure 섹션
    ws["A5"] = "Pressure"
    times = [0, 3, 6, 9, 12, 15, 18, 21]
    for j, t in enumerate(times):
        ws.cell(row=6, column=2 + j, value=t)
    ws.cell(row=6, column=10, value="중위")
    ws.cell(row=6, column=11, value="최소")
    days = ["수요일, 4월 15일", "목요일, 4월 16일", "금요일, 4월 17일"]
    medians = [1010, 1015, 1013]
    mins = [1009, 1014, 1012]
    for i, (d, med, mn) in enumerate(zip(days, medians, mins)):
        r = 7 + i
        ws.cell(row=r, column=1, value=d)
        for j, t in enumerate(times):
            ws.cell(row=r, column=2 + j, value=med)  # 단순화
        ws.cell(row=r, column=10, value=med)
        ws.cell(row=r, column=11, value=mn)
    # Tempereture 섹션
    ws["A15"] = "Tempereture"
    for j, t in enumerate(times):
        ws.cell(row=16, column=2 + j, value=t)
    ws.cell(row=16, column=10, value="중위")
    ws.cell(row=16, column=11, value="취약")
    for i, (d, tm) in enumerate(zip(days, [20, 18, 17])):
        r = 17 + i
        ws.cell(row=r, column=1, value=d)
        ws.cell(row=r, column=10, value=tm)
    wb.save(path)
    return path, days, medians


def test_parse_and_applied_pressure(tmp_path):
    path, days, medians = _make_excel3_1(str(tmp_path / "w.xlsx"))
    fc = load_excel3_1(path)
    assert fc.capture.startswith("2026-04-15")
    assert fc.days == days
    assert fc.times == [0, 3, 6, 9, 12, 15, 18, 21]
    assert fc.pressure_median[days[0]] == pytest.approx(1010)
    assert fc.temp_median[days[0]] == pytest.approx(20)

    # 특정일 적용 대기압 = 중위 − 8
    assert applied_pressure(fc, day=days[0]) == pytest.approx(1010 + C.WEATHER_SITE_OFFSET)
    # 전체 평균 중위 − 8
    mean_med = sum(medians) / len(medians)
    assert applied_pressure(fc) == pytest.approx(mean_med + C.WEATHER_SITE_OFFSET)


def test_site_offset_is_minus_8():
    assert C.WEATHER_SITE_OFFSET == -8.0
