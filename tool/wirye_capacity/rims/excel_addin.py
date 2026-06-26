"""실제 RiMS 커넥터 — Excel COM + fnTagStat (Windows 사내 PC 전용).

개발 환경(Linux)에서는 동작하지 않는다. 사내 PC에서 결선·검증한다.

동작 방식 — 검증된 엑셀1 'RiMS 계산 Sheet'를 그대로 구동:
  1. 엑셀1 워크북 열기 (RiMS fnTagStat 애드인이 로드된 Excel)
  2. AG9 = 테스트 시작 datetime 기입 → 재계산 (fnTagStat가 [AG9, AG9+1h] 평균 취득)
  3. 8행(좌측 정리행) 읽어 AcquiredTest 반환

CELL_MAP 은 엑셀1 'RiMS 계산 Sheet' 레이아웃에 맞춘 기본값이며, 사내 결선 시 실제 시트와
대조해 확정한다(§ 마스터 리뷰 excel1 분석 기준).
"""
from __future__ import annotations

from .base import AcquiredTest

# 엑셀1 'RiMS 계산 Sheet' 셀 매핑 (8행 정리행) — 사내 결선 시 검증
CELL_MAP = {
    "start": "AG9",      # 테스트 시작 datetime 입력
    "cit": "H8",         # Comp Inlet Temp (°C)
    "pressure": "J8",    # 대기압 (mbar)
    "rh": "K8",          # 상대습도 (%)
    "gt_meas": "M8",     # GT Load (MW)
    "st_meas": "N8",     # ST Load (MW)
    "cc_meas": "O8",     # CC Gross (MW)
}


class ExcelAddinRimsConnector:
    """엑셀1을 xlwings로 구동해 fnTagStat 결과를 취득하는 실제 커넥터.

    사내 Windows PC에서만 동작 (Excel + RiMS 애드인 + xlwings 필요).
    """

    def __init__(self, workbook_path: str, sheet: str = "RiMS 계산 Sheet",
                 cell_map: dict | None = None, visible: bool = False):
        self.workbook_path = workbook_path
        self.sheet = sheet
        self.cell_map = cell_map or CELL_MAP
        self.visible = visible

    def acquire(self, date: str, start: str = "17:00") -> AcquiredTest:
        try:
            import xlwings as xw  # noqa: F401
        except ImportError as e:  # pragma: no cover - 사내 전용
            raise RuntimeError(
                "ExcelAddinRimsConnector 는 사내 Windows PC 전용입니다 "
                "(Excel + RiMS 애드인 + xlwings 필요). pip install xlwings"
            ) from e

        # pragma: no cover  ── 아래는 사내 결선용 흐름. RiMS 애드인이 있어야 실제 값이 채워진다.
        start_dt = f"{date} {start}"
        app = xw.App(visible=self.visible)
        try:
            wb = app.books.open(self.workbook_path)
            ws = wb.sheets[self.sheet]
            ws.range(self.cell_map["start"]).value = start_dt  # AG9 = 시작시각
            app.calculate()                                     # fnTagStat 재계산
            g = lambda key: ws.range(self.cell_map[key]).value
            acq = AcquiredTest(
                date=date,
                cit=g("cit"), pressure=g("pressure"), cc_meas=g("cc_meas"),
                rh=g("rh"), gt_meas=g("gt_meas"), st_meas=g("st_meas"))
            wb.close()
            return acq
        finally:
            app.quit()
