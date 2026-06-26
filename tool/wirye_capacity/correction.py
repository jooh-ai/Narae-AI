"""보정값 산출·누적·현실화 출력.

엑셀4 방식: 테스트 결과(실측)와 이론기준값의 차이를 온도별로 누적·평균하여 보정값을 만들고,
이론값에 더해 '현실화값'(입찰값)을 만든다. 구 방식(엑셀2 AB6 일괄 +ΔMW)과 달리 온도별로 보정한다.

  보정값  = CC실측(17~18시, IGV 실시) − 이론기준값(IGV 미반영) − W(IGV)
  현실화  = 이론(IGV 반영) + 보정값,   최종 Net = min(Gross − Aux, 462)
"""
from __future__ import annotations

from . import constants as C


def correction_value(cc_meas: float, theory_cc: float, w: float) -> float:
    """보정값 J = 실측 − 이론기준값 − W. (엑셀4 실측데이터 J열과 동일)"""
    return cc_meas - theory_cc - w


def bin_for(cit: float) -> tuple[int, int, str] | None:
    """CIT가 속한 보정 구간 (lo, hi, kind) 반환."""
    for lo, hi, kind in C.BINS:
        if lo <= cit < hi:
            return (lo, hi, kind)
    return None


def _status(kind: str, count: int, target: int | None) -> str:
    """엑셀4 '보정값 현황' G열 신호등 상태."""
    if kind == "shaft_limit":
        return "─ Shaft Limit"
    if kind == "fixed":
        return "△ 보수적 고정"
    if count == 0:
        return "🔴 데이터 없음"
    if target and count < target:
        return f"🔴 {count}/{target}건"
    return f"🟢 {count}건 자동반영"


def aggregate_bins(records: list[dict]) -> dict[tuple[int, int], dict]:
    """온도구간별 보정값 집계 (엑셀4 '보정값 현황' 재현).

    records: [{'cit': float, 'corr': float}, ...]
    반환: {(lo,hi): {kind, count, avg, applied, status}}
      - avg     = 실측 평균(AVERAGEIFS)
      - applied = 최종 적용값 (shaft=0, fixed=보수적 고정, avg=평균)
    """
    out: dict[tuple[int, int], dict] = {}
    for lo, hi, kind in C.BINS:
        vals = [r["corr"] for r in records if lo <= r["cit"] < hi]
        n = len(vals)
        avg = (sum(vals) / n) if n else None
        if kind == "shaft_limit":
            applied = 0.0
        elif kind == "fixed":
            applied = C.FIXED_BIN_VALUE.get((lo, hi), avg)
        else:
            applied = avg
        out[(lo, hi)] = {
            "kind": kind,
            "count": n,
            "avg": avg,
            "applied": applied,
            "status": _status(kind, n, C.BIN_TARGET_COUNT.get((lo, hi))),
        }
    return out


def applied_correction(cit: float, bin_table: dict[tuple[int, int], dict]) -> float:
    """주어진 CIT에 적용할 보정값(현재 구간 방식). 구간 밖이면 0."""
    b = bin_for(cit)
    if b is None:
        return 0.0
    info = bin_table.get((b[0], b[1]))
    if not info or info["applied"] is None:
        return 0.0
    return info["applied"]


def realized_net(theory_gross_with_igv: float, correction: float,
                 cap_net: float = C.BID_CAP_NET, aux: float = C.CC_AUX) -> float:
    """현실화 Net 출력 = min((이론 Gross+IGV) + 보정값 − Aux, 상한 Net)."""
    gross = theory_gross_with_igv + correction
    return min(gross - aux, cap_net)
