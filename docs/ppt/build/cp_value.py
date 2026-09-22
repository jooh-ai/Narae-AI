#!/usr/bin/env python3
"""공급가능용량 예측 개선의 금액 효과 — 용량요금(CP) 기준.

    python3 docs/ppt/build/cp_value.py

정산식(전력시장운영규칙 [별표 2], 복합발전기)

    TPCP(i,t) = Min( TA, RA, Max(MGO, FCA) ) × (HCF + β) × 1,000
    HCF       = RCP × RCF × TCF × PCF

**Min() 이 전부다.** 이 구조에서 신고값(TA)의 방향에 따라 결과가 비대칭이다.

  · 낮게 신고 (TA < 실제 능력)
        → TA 가 병목이 된다. 실제로 낼 수 있었던 (실제 − TA) 만큼의 용량요금을
          받지 못한다. **금액으로 환산되는 직접 손실이고, 회수 가능하다.**

  · 높게 신고 (TA > 실제 능력)
        → Max(MGO, FCA) 가 병목이 된다. 즉 **용량요금은 실제만큼만 나온다.**
          높게 신고해도 CP 는 늘지 않는다. 늘어나는 것은 기준 미달 위험뿐이다.

따라서 예측 정확도 개선의 **CP 이득은 '낮게 신고한 양' 을 줄인 만큼**이고,
'높게 신고한 양' 을 줄인 것은 CP 증가가 아니라 **미달 위험 감소**로 계상한다.
이 비대칭을 지키지 않으면 금액이 두 배로 부풀려진다.

신고 주기 (2026-09-04 사용자 확인)
  · 공급가능용량 테스트는 **2주마다** 한다. 한 번의 테스트로 얻은 보정값을
    **2주 동안** 쓴다 (14일 × 24h = 336h).
  · 그 2주 안에는 **매일 대기압만 다시 보정해** 용량을 산정하고 매일 입찰한다.
  즉 대기압 오차는 매일 갱신되어 줄지만, **온도별 보정값의 오차는 2주 내내
  고정된다.** 이 과제가 고치는 것이 바로 그 고정 오차다.
  연간 26.1회 × 336h = 8,736h — 8,760h 의 99.7%. 따라서 아래 연 환산에서
  '회당 평균 오차 × 8,760h' 는 가정이 아니라 **실제 운영 주기와 맞는다.**

에너지수익(SMP × 발전량)은 **여기에 넣지 않는다** (2026-09-04 사용자 확정).
두 가지 이유다.
  ① 실발전량은 중앙급전 지시로 정해진다. 공급가능용량을 1 MW 더 정확히
     신고했다고 1 MW 더 발전하는 것이 아니다.
  ② SMP × MWh 는 매출이다. LNG 복합의 변동비(연료비)를 빼지 않은 값을 이익으로
     쓰면 안 된다. 급전 발전기의 SMP 는 한계 발전기의 변동비에 수렴한다.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
DECK = HERE / "deck_data.json"

# ── 정본 단가 (2026-09-07 사용자 제시) ──────────────────────────────
# "CP 용량요금을 kW당 150원으로 잡고, 이게 입찰한 날만 받는 요금이라.
#  정비하면 입찰이 0이므로 못 받는다. 연간 30일(한 달) 정비를 가정하면
#  CP 받는 기간은 11개월."
#
# 단위는 **원/kW·일** 이다. '월' 로 읽으면 150 × 11 = 1,650원/kW·년 =
# 165만원/MW·년인데, 명세서 기준(RCP×RCF = 10,499.6원/MW·h = 252원/kW·일 =
# 7,560원/kW·월)의 1/50 이라 앞뒤가 맞지 않는다. '일' 로 읽으면 150원/kW·일 로
# 명세서 기준 252원/kW·일 의 60% — 시간대별 계수(TCF)·성과계수(PCF)를 반영한
# 보수적 실효 단가로 자연스럽다.
RATE_KW_DAY = 150.0        # 원/kW·일 — 입찰한 날에만 받는다
MAINT_DAYS = 30.0          # 연간 정비 일수. 이 기간은 입찰 0 → CP 0
YEAR_DAYS = 365.0
BID_DAYS = YEAR_DAYS - MAINT_DAYS          # 335일 ≈ 11개월

# ── 참고 단가 (앞서 받은 30일 명세서 분석) ─────────────────────────
# 교차검증용이다. 정본과 얼마나 벌어지는지 보면 TCF×PCF 를 역산할 수 있다.
RCP = 11_580.0             # 기준용량가격 원/MW·h
RCF = 0.9067               # 지역별 용량가격계수 (위례)

MW_PER_YEAR = RATE_KW_DAY * 1000 * BID_DAYS    # 1 MW 를 1년 인정받을 때 원


def summary(impact: dict, n_score: int) -> dict:
    """장표가 쓰는 CP 금액 묶음. deck_data.json 의 'cp' 블록이 된다.

    단가를 바꾸려면 이 파일 맨 위 RATE_KW_DAY 한 줄만 고친다 — 문서와
    발표자료 수치가 함께 갱신된다.
    """
    per_b = impact["blanket"]["opp"] / n_score      # 회당 낮게 신고한 양 MW
    per_g = impact["gp"]["opp"] / n_score
    return {
        "rate_kw_day": RATE_KW_DAY,
        "maint_days": MAINT_DAYS,
        "bid_days": BID_DAYS,
        "mw_year": round(MW_PER_YEAR),              # 1 MW 연간 원
        "per_before": round(per_b, 2),
        "per_after": round(per_g, 2),
        "lost_before": round(per_b * MW_PER_YEAR),  # 종전에 못 받던 원/년
        "lost_after": round(per_g * MW_PER_YEAR),
        "recover": round((per_b - per_g) * MW_PER_YEAR),
        "basis": f"{RATE_KW_DAY:,.0f}원/kW·일 × 입찰일 {BID_DAYS:,.0f}일"
                 f"(정비 {MAINT_DAYS:,.0f}일 제외)",
    }


def won(v: float) -> str:
    """원 → 읽기 쉬운 단위."""
    if abs(v) >= 1e8:
        return f"{v / 1e8:.2f}억원"
    return f"{v / 1e4:,.0f}만원"


def main() -> None:
    D = json.loads(DECK.read_text(encoding="utf-8"))
    I, n, ns = D["impact"], D["n"], D["n_score"]

    print("── 단가 (정본) ──")
    print(f"{RATE_KW_DAY:,.0f} 원/kW·일  ×  입찰일 {BID_DAYS:,.0f}일"
          f" (365 − 정비 {MAINT_DAYS:,.0f}일 ≈ 11개월)")
    print(f"→ 1 MW 를 1년 더 인정받으면  {won(MW_PER_YEAR)}/MW·년")

    ref = RCP * RCF                                  # 원/MW·h
    ref_year = ref * 24 * BID_DAYS
    print("\n── 교차검증 (30일 명세서 기준) ──")
    print(f"RCP {RCP:,.0f} × RCF {RCF} = {ref:,.1f} 원/MW·h = {ref * 24 / 1000:,.0f} 원/kW·일")
    print(f"같은 입찰일수로 환산하면 {won(ref_year)}/MW·년"
          f"   → 정본은 그 {MW_PER_YEAR / ref_year:.0%} 수준")
    print("  차이는 시간대별 계수(TCF)·성과계수(PCF)로 보이며, 정본이 더 보수적이다.")

    # ── 회당 평균 '낮게 신고한 양' ─────────────────────────────
    lo_b, lo_g = I["blanket"]["opp"], I["gp"]["opp"]      # 기회손실 누계 MW
    per_b, per_g = lo_b / ns, lo_g / ns
    print("\n── 우리 데이터: 낮게 신고한 양 (CP 를 못 받은 양) ──")
    print(f"채점 {ns}회  ·  누계 {lo_b:.1f} → {lo_g:.1f} MW"
          f"   회당 평균 {per_b:.2f} → {per_g:.2f} MW")

    y_b, y_g = per_b * MW_PER_YEAR, per_g * MW_PER_YEAR
    print("\n── CP 환산 (연간) ──")
    print(f"종전 방식으로 못 받던 용량요금   {won(y_b)}/년")
    print(f"현재 도구로 못 받는 용량요금     {won(y_g)}/년")
    print(f"→ 회수 효과                      {won(y_b - y_g)}/년"
          f"   (회당 {per_b - per_g:.2f} MW)")

    # ── 높게 신고한 양은 CP 이득이 아니다 ─────────────────────
    hi_b, hi_g = I["blanket"]["over"], I["gp"]["over"]
    print("\n── 높게 신고한 양 — CP 이득으로 계상하지 않는다 ──")
    print(f"누계 {hi_b:.1f} → {hi_g:.1f} MW,  기준 미달 "
          f"{I['blanket']['short']} → {I['gp']['short']}회")
    print("Min() 구조상 높게 신고해도 CP 는 실제만큼만 나온다. 줄어든 것은")
    print("미달 위험이다 — 금액 환산에는 페널티 단가가 따로 필요하다.")

    # ── 민감도 ────────────────────────────────────────────────
    print("\n── 민감도 (회수 효과) ──")
    print(f"{'정비 일수':>10s} {'입찰일':>7s} {'연간 회수':>12s}")
    for md in (0, 15, 30, 45, 60):
        v = (per_b - per_g) * RATE_KW_DAY * 1000 * (YEAR_DAYS - md)
        print(f"{md:>8.0f}일 {YEAR_DAYS - md:>6.0f}일 {won(v):>12s}")
    print(f"\n{'단가':>10s} {'연간 회수':>12s}")
    for rt in (120, 150, 200, 252):
        v = (per_b - per_g) * rt * 1000 * BID_DAYS
        tag = "  ← 정본" if rt == 150 else ("  ← 명세서 기준" if rt == 252 else "")
        print(f"{rt:>8.0f}원 {won(v):>12s}{tag}")

    print("\n※ 용량요금(CP)만이다. 에너지수익은 급전 지시로 정해지고 SMP×MWh 는")
    print("  매출이므로 넣지 않았다(파일 머리말 참조).")
    print(f"※ 오차 지표(MAE {I['blanket']['mae']:.2f} → {I['gp']['mae']:.2f})는 양방향")
    print("  오차의 평균이다. 금액은 그중 '낮게 신고한 쪽' 만으로 계산했다.")


if __name__ == "__main__":
    main()
