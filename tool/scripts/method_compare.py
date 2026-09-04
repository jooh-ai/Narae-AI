"""보정 방식 비교 — 일괄 보정(종전 방식) vs 구간평균 vs GP.

왜 필요한가
  종전 실무는 이론값과 실제값을 비교해 **온도 구간과 무관한 단일 보정값**을
  일괄 적용했다(담당자 Base Load 실적표의 'BLT 적용값' 열). 이 툴은 그 자리를
  온도별 보정곡선으로 대체한다. 그 교체가 실제로 얼마나 이득인지를 같은
  데이터·같은 판정기준으로 수치화한 것이 이 스크립트다.

핵심 — 일괄 보정이 구조적으로 불가능한 이유
  시드 31건의 보정값은 -3.45 ~ +12.95 MW, 폭 16.4 MW 다. 단일 상수로는 양 끝을
  동시에 맞출 수 없다. 실제로 극저온(-1.9°C)에서는 9.7 MW 낮게(기회손실),
  고온(25~33°C)에서는 6~7 MW 높게(미달 위험) 틀린다. 방향이 반대라 상수를
  올리거나 내려도 한쪽이 나빠진다.

판정 기준 (tests/test_gp_margin.py 와 동일)
  미달      : 실측 Net < 입찰 Net × (1 - 0.5%)
  과대입찰합 : 미달 건들의 (입찰 - 실측) 합 — 페널티 위험에 노출된 총량
  기회손실합 : 미달이 아닌 건들의 (실측 - 입찰) 합 — 더 낼 수 있었는데 안 낸 총량

두 가지로 본다
  ① LOOCV        — 1건을 빼고 나머지로 학습해 그 1건을 예측(전 구간 균등 평가)
  ② walk-forward — 날짜순으로 과거만 보고 다음 시험을 예측(실제 운용 순서)
  ②가 더 나쁘게 나오는 게 정상이다. 초기에는 학습 데이터가 온도 범위를 다 덮지
  못하기 때문이다. 방식 간 우열은 둘 다 같은 순서다.

공정성
  '일괄' 은 학습 보정값의 평균(= 최소제곱 최적 상수)을 쓴다. 즉 일괄 방식에
  가능한 최선을 준 것이고, 실제 적용값이 이보다 좋을 수는 없다.

실행:
    python scripts/method_compare.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wirye_capacity import constants as C  # noqa: E402
from wirye_capacity.correction import aggregate_bins, applied_correction  # noqa: E402
from wirye_capacity.curve import CorrectionCurve  # noqa: E402
from wirye_capacity.gp import GPCorrectionCurve  # noqa: E402
from wirye_capacity.margin import MarginCorrector  # noqa: E402
from wirye_capacity.store import _SEED  # noqa: E402
from wirye_capacity.theory import TheoryEngine  # noqa: E402

BAND = 0.005      # 입찰 밴드 ±0.5% — 미달 판정 기준
WF_START = 8      # walk-forward 최초 학습 건수 (GP 가 곡선을 세울 최소 규모)
ROLL = 5          # '직전 N건 평균' 일괄값의 N


def _rec(r: dict) -> dict:
    return {"cit": r["cit"], "corr": r["corr"]}


def _blanket(train: list[dict]) -> float:
    """일괄 보정값 — 온도 무관 단일 상수. 최소제곱 최적값(평균)을 준다."""
    return sum(r["corr"] for r in train) / len(train)


# (이름, 학습기록 → 온도 → 보정값)
METHODS = [
    ("일괄 보정 (종전 방식)", lambda tr: lambda t: _blanket(tr)),
    ("구간평균 (10°C 구간)", lambda tr: (lambda b: lambda t: applied_correction(t, b))(
        aggregate_bins([_rec(r) for r in tr]))),
    ("커널회귀", lambda tr: CorrectionCurve([_rec(r) for r in tr])),
    ("GP (현재 툴 기본)", lambda tr: GPCorrectionCurve([_rec(r) for r in tr])),
    ("GP + 안전마진 K=0.8", lambda tr: MarginCorrector(
        GPCorrectionCurve([_rec(r) for r in tr]), [_rec(r) for r in tr], k=0.8)),
]


def _score(eng: TheoryEngine, cases: list[tuple[dict, float]]) -> tuple:
    """(MAE, 최대오차, 미달건수, 과대입찰합, 기회손실합)."""
    errs, short, over, opp = [], 0, 0.0, 0.0
    for r, pred in cases:
        errs.append(abs(pred - r["corr"]))
        theory = eng.theory_cc(r["cit"], r["press"], rh=r["rh"]) + r["w"]
        bid = min(theory + pred - C.CC_AUX, C.BID_CAP_NET)
        actual = min(r["cc_meas"] - C.CC_AUX, C.BID_CAP_NET)
        if actual < bid * (1 - BAND):
            short += 1
            over += bid - actual
        else:
            opp += max(actual - bid, 0.0)
    return sum(errs) / len(errs), max(errs), short, over, opp


def _header(title: str) -> None:
    print(f"\n── {title} ──")
    print(f"{'방식':26s} {'MAE':>7s} {'최대오차':>9s} {'미달':>5s} "
          f"{'과대입찰합':>11s} {'기회손실합':>11s}")


def _line(name: str, s: tuple) -> None:
    mae, mx, short, over, opp = s
    print(f"{name:26s} {mae:7.3f} {mx:9.3f} {short:3d}건 {over:11.1f} {opp:11.1f}")


def main() -> None:
    seed = json.loads(Path(_SEED).read_text(encoding="utf-8"))
    seed = seed["records"] if isinstance(seed, dict) else seed
    seed = sorted(seed, key=lambda r: r["date"])
    eng = TheoryEngine()

    corrs = [r["corr"] for r in seed]
    print(f"시드 {len(seed)}건 — 보정값 {min(corrs):+.2f} ~ {max(corrs):+.2f} MW "
          f"(폭 {max(corrs) - min(corrs):.2f} MW)")
    print("단일 상수로 이 폭을 덮을 수 없다는 것이 방식 교체의 근거다.")

    # ① LOOCV
    _header("① LOOCV (1건 제외 학습 → 그 1건 예측, 전 구간 균등)")
    loo = {}
    for name, build in METHODS:
        cases = []
        for i, r in enumerate(seed):
            tr = [seed[k] for k in range(len(seed)) if k != i]
            cases.append((r, build(tr)(r["cit"])))
        loo[name] = cases
        _line(name, _score(eng, cases))

    # ② walk-forward
    _header(f"② walk-forward (날짜순, 앞 {WF_START}건 학습 후 "
            f"{len(seed) - WF_START}건 순차 예측)")
    _line(f"일괄 — 직전 {ROLL}건 평균",
          _score(eng, [(seed[i], _blanket(seed[max(0, i - ROLL):i]))
                       for i in range(WF_START, len(seed))]))
    for name, build in METHODS:
        _line(name, _score(eng, [(seed[i], build(seed[:i])(seed[i]["cit"]))
                                 for i in range(WF_START, len(seed))]))

    # 일괄 보정의 실패 지점 — 방향이 반대라 상수 조정으로 못 고친다
    print("\n── 일괄 보정의 오차 상위 6건 (LOOCV, 오차 = 예측 - 실측) ──")
    worst = sorted(loo["일괄 보정 (종전 방식)"],
                   key=lambda c: -abs(c[1] - c[0]["corr"]))[:6]
    print(f"{'날짜':11s} {'CIT':>6s} {'실측보정':>8s} {'일괄예측':>8s} {'오차':>8s}  방향")
    for r, pred in worst:
        e = pred - r["corr"]
        way = "입찰 과소 → 기회손실" if e < 0 else "입찰 과대 → 미달 위험"
        print(f"{r['date']:11s} {r['cit']:6.2f} {r['corr']:+8.3f} {pred:+8.3f} "
              f"{e:+8.3f}  {way}")


if __name__ == "__main__":
    main()
