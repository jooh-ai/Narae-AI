"""입찰 안전마진 — 미달(약속 용량 못 냄) 리스크를 줄이는 구간별 차등 마진.

손실 구조가 단측(one-sided)이다:
  · 실제 출력 > 입찰값          → 무해 (출력을 줄여 맞춤). 대가는 기회손실
  · 실제 출력 < 입찰값 − 0.5%   → 문제 (약속 용량 미달)

따라서 입찰값을 조금 낮추면 미달을 막을 수 있고, 그 마진을 **구간별 실측 변동에
비례**시키면 같은 미달률에서 기회손실이 가장 작다. 실측 32건 LOOCV 검증:

    미달 0건 달성에 필요한 마진 / 그때의 평균 기회손실
      균일 마진            1.25 MW        → 2.00 MW/건
      GP σ 비례            1.0σ           → 2.15 MW/건   (σ가 구간별로 균일해 불리)
      구간 실측변동 비례    0.6×           → 1.68 MW/건   ← 최소

계수 K 는 0.6 이 32건 기준 '미달 0'의 최소값이지만, 그 값에 딱 맞추면 새 데이터에서
미달이 생길 수 있어(선택 편향) 기본값은 여유를 둔 0.8 로 한다.
  K=0.8 → 미달 0건, MAE 1.243 → 1.635 (오차 +31%는 전부 안전한 방향)
"""
from __future__ import annotations

import math

from . import constants as C
from .correction import bin_for

DEFAULT_K = 0.8          # 마진 계수 (실측 변동의 배수)
FALLBACK_SD = 1.5        # 구간 실측 2건 미만 → 변동 추정 불가 시 사용(MW)


def bin_std(records) -> dict[tuple[int, int], float | None]:
    """온도구간별 보정값 표본표준편차. 2건 미만이면 None."""
    out: dict[tuple[int, int], float | None] = {}
    for lo, hi, _kind in C.BINS:
        v = [r["corr"] for r in records if lo <= r["cit"] < hi]
        if len(v) < 2:
            out[(lo, hi)] = None
            continue
        m = sum(v) / len(v)
        out[(lo, hi)] = math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))
    return out


def margin_for(cit: float, sd_table: dict[tuple[int, int], float | None],
               k: float = DEFAULT_K) -> float:
    """해당 온도에 적용할 안전마진(MW, 0 이상). 구간 밖이면 0.

    특수구간(Shaft Limit / 보수적 고정)은 **마진을 적용하지 않는다**:
      · Shaft Limit(−20~−14) 는 축 제한에 따른 이론 고정값
      · 보수적 고정(−14~0) 은 이미 사람이 낮춰 정한 값(실측 +12.95 → 고정 +8.78)
    둘 다 정책적으로 보수화된 값이라 마진을 또 빼면 이중 보수화가 된다.
    마진은 '실측 변동에 비례'하는 값이므로 실측 기반 구간(avg)에만 의미가 있다.
    """
    if k <= 0:
        return 0.0
    b = bin_for(cit)
    if b is None or b[2] != "avg":
        return 0.0
    sd = sd_table.get((b[0], b[1]))
    return k * (FALLBACK_SD if sd is None else sd)


class MarginCorrector:
    """보정기를 감싸 안전마진을 적용하는 래퍼.

    base 가 산출한 보정값에서 구간별 마진을 뺀다 → 현실화 출력이 그만큼 낮아진다.
    profile/pipeline 의 corrector 자리에 그대로 넣어 쓸 수 있다.

        corrector = MarginCorrector(CorrectionCurve(recs), recs, k=0.8)
    """

    def __init__(self, base, records, k: float = DEFAULT_K):
        self.base = base
        self.k = k
        self.sd_table = bin_std(records)

    def margin(self, cit: float) -> float:
        return margin_for(cit, self.sd_table, self.k)

    def __call__(self, cit: float) -> float:
        return self.base(cit) - self.margin(cit)

    def __getattr__(self, name):
        """sigma()/interval() 등 base 의 부가기능을 그대로 노출."""
        return getattr(self.base, name)


def margin_rows(records, k: float = DEFAULT_K) -> list[dict]:
    """구간별 마진 표(GUI·CLI 표시용).

    각 행: {bin, bin_label, count, sd, margin}
      sd = None 이면 표본 부족(2건 미만) → FALLBACK_SD 로 대체 적용
    """
    sd_table = bin_std(records)
    rows: list[dict] = []
    for lo, hi, kind in C.BINS:
        n = sum(1 for r in records if lo <= r["cit"] < hi)
        sd = sd_table[(lo, hi)]
        rows.append({
            "bin": (lo, hi),
            "bin_label": f"{lo}~{hi}°C",
            "kind": kind,
            "count": n,
            "sd": sd,
            "margin": margin_for(lo + 0.5, sd_table, k),
        })
    return rows
