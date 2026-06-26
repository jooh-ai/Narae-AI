"""위례열병합발전소 공급가능용량 산정 — 물리/사이트 상수.

출처: 엑셀2(이론 곡선엔진), 엑셀4(현실화 시스템). 모든 값은 원본 시트 셀과 대조해 확정.
- Mode3_AOH1000 기준, ISO 15°C / 1013 mbar / CC 450.4 MW.
- 온도 기준은 전 과정 CIT(Compressor Inlet Temp). KPX 소명도 CIT 기준.
"""
from __future__ import annotations

# --- 설계 기준 ---
CC_ISO = 450.4           # CC Gross @ ISO 15°C/1013mbar (MW)
REF_PRESSURE = 1013.0    # mbar (ISO 표준 대기압)
REF_RH = 60.0            # % — 이론계산 시 상대습도는 60% 고정(→ 습도보정=1, 실측 RH 미사용)
REF_DEG = 1.028          # base 테이블에 동결된 기준 열화계수
DEFAULT_DEG = 1.028      # 현재 적용 Degradation

# --- 대기압 보정 P_corr(P) = a·(P-1013)² + b·(P-1013) + c  (엑셀1/2/4 동일 확인) ---
P_CORR = (1.208792e-6, -9.82435e-4, 1.0)

# --- 소내전력(Aux) ---
CC_AUX = 10.0            # CC 소내전력 (Gross − 10 = Net)
GT_AUX = 11.5            # GT 소내전력

# --- GT/ST 분배비 (Mode3 Cor. Rev.1 E108/E109). CC = GT + ST, W(IGV)도 이 비율로 분배 ---
GT_RATIO = 0.6570
ST_RATIO = 0.3430

# --- 입찰 상한 (KPX 신고, Mode3) ---
BID_CAP_NET = 462.0      # 사용자 확정: Net 462 MW
BID_CAP_GROSS = BID_CAP_NET + CC_AUX  # 472 MW

# --- 날씨 크롤링(성남비행장) → 발전소 위치 대기압 보정 ---
WEATHER_SITE_OFFSET = -8.0   # mbar

# --- 온도 보정 구간 (현재 방식; lo <= CIT < hi, °C) ---
# kind: shaft_limit=이론값 고정(보정 0), fixed=보수적 고정값, avg=실측 평균(AVERAGEIFS)
BINS = [
    (-20, -14, "shaft_limit"),
    (-14, 0,   "fixed"),
    (0, 10, "avg"),
    (10, 15, "avg"),
    (15, 20, "avg"),
    (20, 25, "avg"),
    (25, 30, "avg"),
    (30, 41, "avg"),
]

# 보수적 고정 구간의 적용 보정값 (실측 1건뿐이라 평균 대신 보수적으로 고정)
FIXED_BIN_VALUE = {(-14, 0): 8.78}

# 구간별 신뢰 목표 건수 (엑셀4 '보정값 현황' F열)
BIN_TARGET_COUNT = {
    (-14, 0): 5, (0, 10): 15, (10, 15): 12, (15, 20): 8,
    (20, 25): 5, (25, 30): 8, (30, 41): 15,
}
