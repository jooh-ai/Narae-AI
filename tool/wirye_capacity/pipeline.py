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

# 입찰파일 도장·화면 표기에 쓰는 방법 이름. 키는 correction_method 인자와 같다.
METHOD_LABEL = {"bin": "구간평균", "curve": "커널회귀", "gp": "GP"}


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
    fingerprint: str = ""            # 보정 테이블 지문 — 입찰파일 최신 여부 검사용
    acq_warnings: list = field(default_factory=list)  # 취득 품질 경고(커넥터가 올린 것)
    correction_method: str = "bin"    # 이번 산출에 쓴 보정 방법 (화면·도장 표기용)


def run_pipeline(*, date: str, store: MeasurementStore, output_path: str | None = None,
                 connector=None, engine: TheoryEngine | None = None,
                 deg: float = C.DEFAULT_DEG,
                 forecast: WeatherForecast | None = None, forecast_path: str | None = None,
                 bid_day: str | None = None, template_path: str | Path = DEFAULT_TEMPLATE,
                 accumulate: bool = False, correction_method: str = "bin",
                 bandwidth: float = 3.5, margin_k: float = 0.0,
                 start: str = "17:00") -> PipelineResult:
    """전 단계 실행. connector 가 있으면 RiMS 자동취득.

    accumulate=False(기본): 취득·보정값 계산만(확인용) — 누적에 저장 안 함.
    accumulate=True: 그 테스트를 누적에 반영(저장). 같은 날짜가 이미 있으면 건너뜀.
    forecast/forecast_path 로 입찰 대기압(예보 중위 − 8) 결정. 없으면 ISO 1013.
    correction_method: 'bin'(구간 평균, 기본) / 'curve'(커널회귀) / 'gp'(가우시안 프로세스).
      실측 32건 LOOCV 예측오차(MAE): bin 1.419 / curve 1.341 / gp 1.243 MW.
    margin_k: 미달 방지 안전마진 계수(0=미적용). 마진 = k × 구간별 실측변동.
      k=0.8 이면 시드 32건에서 미달 0건(오차는 커지지만 전부 안전한 방향).
    output_path 가 있으면 엑셀3 양식 입찰 파일 생성.
    start: 테스트 시작 시각(기본 17:00, 1시간 창). 다른 시각에 수행된 테스트 취득용.
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
    acq_warnings: list = []
    if connector is not None:
        new_record = store.compute_from_rims(connector, date, start=start, engine=eng, deg=deg)
        # 취득 품질 경고(집계 상태·CC vs GT+ST 불일치 등). 지원하는 커넥터만 채운다.
        acq_warnings = list(getattr(connector, "last_warnings", None) or [])
        if accumulate:
            if store.has_date(date):
                duplicate_skipped = True            # 같은 날짜 이미 반영됨 → 중복 방지
            else:
                store.add(new_record)
                reflected = True

    # 3. 보정 테이블 재집계 (+ 보정 방법 · 안전마진)
    table = store.correction_table()
    recs = [{"cit": r.cit, "corr": r.corr} for r in store.all()]
    corrector = None
    if correction_method == "curve":
        from .curve import CorrectionCurve
        corrector = CorrectionCurve(recs, bandwidth=bandwidth)
    elif correction_method == "gp":
        from .gp import GPCorrectionCurve
        corrector = GPCorrectionCurve(recs)
    if margin_k and margin_k > 0:          # 미달 방지 안전마진(실측 변동 비례)
        from .correction import applied_correction
        from .margin import MarginCorrector
        base = corrector if corrector is not None else (
            lambda t: applied_correction(t, table))
        corrector = MarginCorrector(base, recs, k=margin_k)

    # 4. 현실화 Profile + 엑셀3 출력 (보정지문 도장 → check-bid 최신 여부 검사)
    from datetime import datetime

    from .correction import table_fingerprint
    fp = table_fingerprint(table)
    rows = build_profile(eng, table, pressure=pressure, deg=deg, corrector=corrector)
    out = None
    if output_path:
        # 보정방법을 도장에 남긴다. 지문(table_fingerprint)은 구간 테이블만 해싱하므로
        # 같은 누적이면 방법이 달라도 지문이 같다 — 지문만으로는 어느 방법으로 만든
        # 파일인지 구분할 수 없다. 지문 알고리즘 자체는 건드리지 않는다(바꾸면 이미
        # 만들어 둔 입찰파일이 전부 구버전으로 오판된다).
        note = METHOD_LABEL.get(correction_method, correction_method)
        if margin_k and margin_k > 0:
            note += f"+마진{margin_k:g}×"
        stamp = (f"위례입찰툴 | 테스트 {date} | 누적 {store.count()}건 | "
                 f"보정방법 {note} | 보정지문 {fp} | 생성 {datetime.now():%Y-%m-%d %H:%M}")
        out = fill_excel3_template(output_path, engine=eng, correction_table=table,
                                   pressure=pressure, deg=deg, forecast=forecast,
                                   template_path=template_path, corrector=corrector,
                                   test_date=date, stamp=stamp)

    return PipelineResult(date=date, applied_pressure=pressure, deg=deg,
                          measurement_count=store.count(), new_record=new_record,
                          correction_table=table, profile_rows=rows, output_path=out,
                          reflected=reflected, duplicate_skipped=duplicate_skipped,
                          fingerprint=fp, acq_warnings=acq_warnings,
                          correction_method=correction_method)
