"""엔드투엔드 오케스트레이터 — "날짜·시간 입력 → 실행 → 엑셀3 온도 Profile 생성".

한 번의 run_pipeline() 호출이 전 단계를 연결한다:
  1. 날씨(엑셀3-1) 로드 → 입찰 적용 대기압(중위 − 8)
  2. RiMS 자동취득(테스트 날짜) → 이론기준값·보정값 계산 → 누적 저장
  3. 누적 실측 → 온도구간 보정 테이블 재집계
  4. 현실화 Mode3 산출 → 엑셀3 템플릿 채우기 → 최종 입찰 파일

테스트 취득 대기압(보정값 산출용)과 입찰 프로파일 대기압(예보 중위)은 분리된다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import constants as C
from .profile import DEFAULT_TEMPLATE, build_profile, fill_excel3_template
from .store import MeasurementStore
from .theory import TheoryEngine
from .weather import WeatherForecast, applied_pressure, load_excel3_1


@dataclass
class PipelineResult:
    date: str
    applied_pressure: float
    deg: float
    measurement_count: int
    new_record: object | None
    correction_table: dict
    profile_rows: list = field(default_factory=list)
    output_path: str | None = None
    reflected: bool = False          # 이번 테스트가 누적에 반영(저장)됐는지
    duplicate_skipped: bool = False  # 같은 날짜가 이미 있어 반영을 건너뛰었는지


def run_pipeline(*, date: str, store: MeasurementStore, output_path: str | None = None,
                 connector=None, engine: TheoryEngine | None = None,
                 deg: float = C.DEFAULT_DEG,
                 forecast: WeatherForecast | None = None, forecast_path: str | None = None,
                 bid_day: str | None = None, template_path: str | Path = DEFAULT_TEMPLATE,
                 accumulate: bool = False, correction_method: str = "bin",
                 bandwidth: float = 3.5) -> PipelineResult:
    """전 단계 실행. connector 가 있으면 RiMS 자동취득.

    accumulate=False(기본): 취득·보정값 계산만(확인용) — 누적에 저장 안 함.
    accumulate=True: 그 테스트를 누적에 반영(저장). 같은 날짜가 이미 있으면 건너뜀.
    forecast/forecast_path 로 입찰 대기압(예보 중위 − 8) 결정. 없으면 ISO 1013.
    correction_method: 'bin'(구간 평균, 기본) 또는 'curve'(연속 보정곡선).
    output_path 가 있으면 엑셀3 양식 입찰 파일 생성.
    """
    eng = engine or TheoryEngine()

    # 1. 날씨 → 적용 대기압
    if forecast is None and forecast_path:
        forecast = load_excel3_1(forecast_path)
    pressure = (applied_pressure(forecast, day=bid_day) if forecast is not None
                else C.REF_PRESSURE)

    # 2. RiMS 취득 → 보정값 계산(확인용). 반영(저장)은 accumulate=True 일 때만.
    new_record = None
    reflected = False
    duplicate_skipped = False
    if connector is not None:
        new_record = store.compute_from_rims(connector, date, engine=eng, deg=deg)
        if accumulate:
            if store.has_date(date):
                duplicate_skipped = True            # 같은 날짜 이미 반영됨 → 중복 방지
            else:
                store.add(new_record)
                reflected = True

    # 3. 보정 테이블 재집계 (+ 곡선 토글)
    table = store.correction_table()
    corrector = None
    if correction_method == "curve":
        from .curve import CorrectionCurve
        corrector = CorrectionCurve(
            [{"cit": r.cit, "corr": r.corr} for r in store.all()], bandwidth=bandwidth)

    # 4. 현실화 Profile + 엑셀3 출력
    rows = build_profile(eng, table, pressure=pressure, deg=deg, corrector=corrector)
    out = None
    if output_path:
        out = fill_excel3_template(output_path, engine=eng, correction_table=table,
                                   pressure=pressure, deg=deg, forecast=forecast,
                                   template_path=template_path, corrector=corrector)

    return PipelineResult(date=date, applied_pressure=pressure, deg=deg,
                          measurement_count=store.count(), new_record=new_record,
                          correction_table=table, profile_rows=rows, output_path=out,
                          reflected=reflected, duplicate_skipped=duplicate_skipped)
