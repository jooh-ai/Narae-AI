"""출력 시뮬레이션 — 조건을 임의로 넣고 예상 출력을 산출 / 실측과 즉시 대조.

용도:
  1) 사전 검토 — "CIT 32°C, 대기압 1005 이면 얼마 나오나?"
  2) 테스트 직후 대조 — 실측 CC를 함께 넣으면 예상값과의 차이·밴드 판정을 바로 표시

이론식이 실제로 쓰는 입력은 **CIT · 대기압 · RH · Degradation** 이다(+ W는 가산).
복수기압(콘덴서 진공)은 base 테이블 생성 시 ISO 조건으로 동결되어 있어 이론식에
직접 들어가지 않는다 — 입력받아 '유사 온도 실측의 설계값 대비 편차'만 참고로 알린다.
(엑셀2 곡선엔진의 5중 보정 중 복수기 항이 base 계수에 이미 반영된 상태)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import constants as C
from .correction import applied_correction, bin_for, correction_value, realized_net
from .theory import TheoryEngine, igv_turnup

BAND = 0.005          # 입찰 허용밴드 ±0.5%


@dataclass
class SimInput:
    """시뮬레이션 입력. cc_meas 를 주면 실측 대조까지 수행."""
    cit: float
    pressure: float = C.REF_PRESSURE
    rh: float | None = None                  # None = 60%(보정 없음)
    deg: float = C.DEFAULT_DEG
    w: float | None = None                   # None = 온도밴드 자동
    cp_meas: float | None = None             # 복수기압 실측(참고용, 이론식 미반영)
    cc_meas: float | None = None             # CC Gross 실측(선택) — 대조용


@dataclass
class SimResult:
    # 이론
    theory_base: float                       # 이론기준값 (IGV 미반영)
    w: float                                 # IGV turn-up
    theory_cc: float                         # 이론 CC (IGV 반영)
    theory_net: float                        # 이론 Net
    # 보정
    correction: float                         # 적용 보정값
    corr_sigma: float                         # 불확실성(GP만, 없으면 nan)
    margin: float                             # 적용된 안전마진
    bin_label: str
    bin_kind: str
    bin_count: int
    # 현실화(입찰)
    real_gross: float
    real_net: float                           # 최종 입찰값
    # 실측 대조 (cc_meas 입력 시)
    meas_corr: float | None = None            # 실측 보정값 = 실측 − 이론기준 − W
    corr_diff: float | None = None            # 실측보정 − 예상보정
    meas_net: float | None = None
    net_diff: float | None = None             # 실측 Net − 예상 Net (+면 여유)
    in_band: bool | None = None               # ±0.5% 안에 들어오나
    shortfall: bool | None = None             # 미달(실측 < 입찰−0.5%)
    notes: list[str] = field(default_factory=list)


def _cp_reference(records, cit: float, window: float = 2.5):
    """유사 온도(±window) 실측의 복수기압 실측/설계 평균 — 참고 표시용."""
    near = [r for r in records
            if r.get("cp_design") is not None and abs(r["cit"] - cit) <= window]
    if not near:
        return None, None
    meas = [r["cp_meas"] for r in near if r.get("cp_meas") is not None]
    des = [r["cp_design"] for r in near]
    return (sum(meas) / len(meas) if meas else None), sum(des) / len(des)


def simulate(inp: SimInput, *, engine: TheoryEngine | None = None,
             records: list[dict] | None = None, correction_table: dict | None = None,
             corrector=None, margin_k: float = 0.0) -> SimResult:
    """예상 출력 산출. corrector 미지정 시 correction_table(구간 평균) 사용.

    records: 누적 실측 [{cit, corr, cp_meas, cp_design}, ...] — 구간 건수·복수기압 참고용.
    """
    eng = engine or TheoryEngine()
    recs = records or []
    notes: list[str] = []

    w = igv_turnup(inp.cit) if inp.w is None else inp.w
    theory_base = eng.theory_cc(inp.cit, inp.pressure, inp.deg, rh=inp.rh)
    theory_cc = theory_base + w
    theory_net = min(theory_cc - C.CC_AUX, C.BID_CAP_NET)

    # 보정값 (+ 마진). corrector 가 MarginCorrector 면 margin() 을 갖는다.
    if corrector is not None:
        correction = corrector(inp.cit)
        margin = corrector.margin(inp.cit) if hasattr(corrector, "margin") else 0.0
    else:
        table = correction_table if correction_table is not None else {}
        correction = applied_correction(inp.cit, table)
        margin = 0.0
        if margin_k > 0 and recs:
            from .margin import bin_std, margin_for
            margin = margin_for(inp.cit, bin_std(recs), margin_k)
            correction -= margin
    sigma = float("nan")
    if hasattr(corrector, "sigma"):
        try:
            sigma = corrector.sigma(inp.cit)
        except Exception:      # noqa: BLE001 — 부가정보이므로 실패해도 무시
            sigma = float("nan")

    b = bin_for(inp.cit)
    bin_label = f"{b[0]}~{b[1]}°C" if b else "구간 밖"
    bin_kind = b[2] if b else "-"
    bin_count = sum(1 for r in recs if b and b[0] <= r["cit"] < b[1])

    real_gross = min(theory_cc + correction, C.BID_CAP_GROSS)
    real_net = realized_net(theory_cc, correction)

    res = SimResult(
        theory_base=theory_base, w=w, theory_cc=theory_cc, theory_net=theory_net,
        correction=correction, corr_sigma=sigma, margin=margin,
        bin_label=bin_label, bin_kind=bin_kind, bin_count=bin_count,
        real_gross=real_gross, real_net=real_net, notes=notes)

    # ── 안내 메모 ──
    if inp.rh is None:
        notes.append("RH 미입력 → 기준 60%(습도보정 없음)로 계산")
    elif not (5.0 <= inp.rh <= 100.0):
        notes.append(f"RH {inp.rh}% 는 유효범위(5~100%) 밖 — 센서 고장값일 수 있음")
    if inp.cp_meas is not None:
        cp_m, cp_d = _cp_reference(recs, inp.cit)
        if cp_d is not None:
            notes.append(
                f"복수기압 {inp.cp_meas:.1f} — 유사온도({inp.cit:.0f}±2.5°C) 실측 평균 "
                f"{cp_m:.1f} / 설계 {cp_d:.1f} (편차 {inp.cp_meas - cp_d:+.1f})")
        notes.append("복수기압은 base 테이블에 ISO 조건으로 동결 — 이론값에 직접 반영되지 않음")
    if bin_kind == "shaft_limit":
        notes.append("Shaft Limit 구간 — 보정 0(이론값 고정), 안전마진 미적용")
    elif bin_kind == "fixed":
        notes.append("보수적 고정 구간 — 정책값 적용, 안전마진 미적용")
    elif bin_count == 0:
        notes.append("이 구간 실측 0건 — 보정값 근거 없음(주의)")
    elif bin_count < 3:
        notes.append(f"이 구간 실측 {bin_count}건뿐 — 보정값 신뢰도 낮음")

    # ── 실측 대조 ──
    if inp.cc_meas is not None:
        res.meas_corr = correction_value(inp.cc_meas, theory_base, w)
        res.corr_diff = res.meas_corr - correction
        res.meas_net = min(inp.cc_meas - C.CC_AUX, C.BID_CAP_NET)
        res.net_diff = res.meas_net - real_net
        band = real_net * BAND
        res.in_band = abs(res.net_diff) <= band
        res.shortfall = res.meas_net < real_net * (1 - BAND)
        if res.shortfall:
            notes.append(f"⚠ 미달 — 실측이 입찰값−0.5%({real_net * (1 - BAND):.1f} MW)보다 낮음")
        elif res.in_band:
            notes.append(f"✅ 허용밴드(±{band:.2f} MW) 안 — 문제 없음")
        else:
            notes.append(f"실측이 밴드보다 높음(+{res.net_diff:.2f} MW) — 출력을 줄여 대응 가능")
    return res


def format_result(res: SimResult, inp: SimInput) -> str:
    """CLI·GUI 공용 텍스트 리포트."""
    L = [
        f"입력      CIT {inp.cit:.1f}°C · 대기압 {inp.pressure:.1f} mbar"
        + (f" · RH {inp.rh:.1f}%" if inp.rh is not None else " · RH 60%(기본)")
        + f" · Deg {inp.deg:.3f}"
        + (f" · 복수기압 {inp.cp_meas:.1f}" if inp.cp_meas is not None else ""),
        "",
        f"이론기준값(IGV 미반영)   {res.theory_base:8.2f} MW",
        f"W (IGV turn-up)         {res.w:8.2f} MW",
        f"이론 CC (Gross)         {res.theory_cc:8.2f} MW    → Net {res.theory_net:.2f}",
        "",
        f"적용 보정값             {res.correction:+8.2f} MW"
        + (f"  (±{1.645 * res.corr_sigma:.2f}, 90%)" if res.corr_sigma == res.corr_sigma else "")
        + f"   [{res.bin_label} · {res.bin_count}건]",
    ]
    if res.margin:
        L.append(f"  └ 안전마진 반영        −{res.margin:.2f} MW")
    L += [
        "",
        f"현실화 Gross            {res.real_gross:8.2f} MW",
        f"■ 예상 입찰값 (Net)     {res.real_net:8.2f} MW",
    ]
    if res.meas_corr is not None:
        L += [
            "",
            "── 실측 대조 ──",
            f"실측 CC (Gross)         {inp.cc_meas:8.2f} MW    → Net {res.meas_net:.2f}",
            f"실측 보정값             {res.meas_corr:+8.2f} MW"
            f"   (예상 대비 {res.corr_diff:+.2f})",
            f"Net 차이 (실측−예상)    {res.net_diff:+8.2f} MW",
        ]
    if res.notes:
        L.append("")
        L += [f"· {n}" for n in res.notes]
    return "\n".join(L)
