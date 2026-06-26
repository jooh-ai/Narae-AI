"""이론(공급가능) 출력 엔진.

엑셀4 '온도 Profile'에 동결(freeze)된 온도별 base 계수를 기준으로, 실시간 대기압·Degradation
보정을 적용해 이론 출력을 산출한다. base 계수는 원래 엑셀2 곡선엔진(온도·대기압·습도·복수기·열화
5중 보정)의 ISO 기준 산출물이다.

  이론기준값 CC (IGV 미반영) = base_cc(CIT) × (1.028 / Deg) / P_corr(대기압)
  이론 CC (IGV 반영, Profile) = 이론기준값 + W(IGV turn-up)

CIT 가 소수(예: 25.5°C)면 1°C 간격 base 테이블을 선형보간한다(기존 수작업과 동일).
"""
from __future__ import annotations

import bisect
import json
from pathlib import Path

from . import constants as C

_DATA = C.resource("data")


def load_base_table(path: str | Path | None = None) -> list[dict]:
    """온도별 base 계수 테이블 로드. 각 행: {t, cc, w, gt} (−20~40°C, 1°C 간격)."""
    p = Path(path) if path else _DATA / "base_table.json"
    rows = json.loads(p.read_text(encoding="utf-8"))
    rows.sort(key=lambda r: r["t"])
    return rows


def rh_corr(rh: float, cit: float) -> float:
    """상대습도 보정계수 K_rh (엑셀2 K열, 기준 RH 60%). RH=60에서 1.0.

    이론기준값(보정값 산출용)은 테스트의 실측 RH를 반영해야 시드 수기값과 일치한다
    (검증: 32건 최대오차 0.18 MW). 입찰 Profile은 미래 습도 미지 → RH=60(=1.0) 사용.
    (엑셀2의 ~1e-17 온도단독 항은 수치적으로 무시.)
    """
    j = rh - C.REF_RH
    return (1 - 3.899067e-5 * j + 3.99928e-7 * j ** 2
            - 7.34811e-7 * cit * j + 6.844623e-8 * j ** 2 * cit
            + 3.040975e-7 * j * cit ** 2 - 2.054733e-9 * cit ** 2 * j ** 2)


def igv_turnup(cit: float) -> float:
    """IGV turn-up 출력 증가분 W (MW).

    엑셀4 Profile 밴드: ≤−2°C → 0 / −1°C → +2 / 0~24°C → +4 / 25°C↑ → +6.
    (실제 테스트에서는 운전 실적값 H열을 직접 사용; 이 함수는 Profile 생성용 기본값.)
    """
    if cit < -1.5:
        return 0.0
    if cit < -0.5:
        return 2.0
    if cit < 24.5:
        return 4.0
    return 6.0


class TheoryEngine:
    """온도별 이론 출력 산출기."""

    def __init__(self, base_table: list[dict] | None = None):
        rows = base_table if base_table is not None else load_base_table()
        self.temps = [r["t"] for r in rows]
        self._cc = [r["cc"] for r in rows]
        self._gt = [r["gt"] for r in rows]

    def p_corr(self, pressure: float) -> float:
        """대기압 보정계수 P_corr(P). 1013 mbar에서 1.0."""
        a, b, c = C.P_CORR
        d = pressure - C.REF_PRESSURE
        return a * d * d + b * d + c

    def _interp(self, arr: list[float], cit: float) -> float:
        ts = self.temps
        if cit <= ts[0]:
            return arr[0]
        if cit >= ts[-1]:
            return arr[-1]
        i = bisect.bisect_right(ts, cit) - 1
        frac = (cit - ts[i]) / (ts[i + 1] - ts[i])
        return arr[i] + frac * (arr[i + 1] - arr[i])

    def base_cc(self, cit: float) -> float:
        """ISO(1013mbar, Deg 1.028) 기준 CC 이론(IGV 미반영, Gross)."""
        return self._interp(self._cc, cit)

    def base_gt(self, cit: float) -> float:
        return self._interp(self._gt, cit)

    def theory_cc(self, cit: float, pressure: float = C.REF_PRESSURE,
                  deg: float = C.DEFAULT_DEG, rh: float | None = None) -> float:
        """이론기준값 CC (Gross, IGV turn-up 미반영). 보정값 산출의 기준.

        rh 지정 시(테스트 실측 습도) 습도보정 반영 — 시드 수기 이론기준값과 정합.
        rh=None 또는 60(기준)이면 습도보정 없음(입찰 Profile용).
        """
        if deg <= 0:
            raise ValueError(f"Degradation 은 0보다 커야 합니다 (입력: {deg})")
        val = self.base_cc(cit) * (C.REF_DEG / deg) / self.p_corr(pressure)
        if rh is not None and rh != C.REF_RH:
            val /= rh_corr(rh, cit)
        return val

    def theory_cc_with_igv(self, cit: float, pressure: float = C.REF_PRESSURE,
                           deg: float = C.DEFAULT_DEG, w: float | None = None,
                           rh: float | None = None) -> float:
        """이론 CC (Gross, IGV turn-up 반영). 현실화값의 기준선.

        Profile 용도이므로 rh 기본 None(=RH 60, 습도보정 없음)."""
        if w is None:
            w = igv_turnup(cit)
        return self.theory_cc(cit, pressure, deg, rh=rh) + w
