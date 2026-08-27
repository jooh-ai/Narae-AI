"""시운전 회차 성적표 — 예측 정확도를 통계로 정리한다.

무엇을 재는가 (섞으면 안 된다)
    ① 계산 일치   같은 입력에 같은 이론기준값·보정값이 나오는가. 결정론적 검사다.
                  틀리면 버그다. 통계로 볼 것이 아니다.
    ② 예측 정확도 반영 전에 낸 예측이 실측과 얼마나 맞았는가. 이게 성적이다.

지표를 왜 두 기준으로 내는가
    · **Net 기준**   입찰 관점. 실제로 신고하는 숫자의 오차다. 운영상 이게 중요하다.
    · **보정값 기준** 모델 관점. 이론값은 결정론적으로 계산되므로, 모델이 실제로
      맞혀야 하는 것은 보정값 하나다. 모델 성능은 이쪽으로 봐야 한다.

R² 를 조심할 것
    R² = 1 − SSE/SST 이고 SST 는 '실측값이 평균에서 흩어진 정도'다. 그래서

      · Net 기준 R² 는 거의 항상 1 에 가깝게 나온다. 여름 374 · 봄 401 처럼
        온도로 생기는 큰 분산이 SST 를 채우는데, 그 분산은 이론곡선이 이미
        설명하는 부분이다. 모델의 공헌이 아니다. **의미 없는 좋은 점수다.**
      · 보정값 기준 R² 는 크게 음수로 나올 수 있다. 실측 보정값이 거의 일정하면
        SST 가 0 에 가까워, 예측이 조금만 흔들려도 R² 가 무너진다.
        **모델이 나쁘다는 뜻이 아니라 이 표본으로는 R² 를 쓸 수 없다는 뜻이다.**

    n<10 에서는 R² 를 판단 근거로 쓰지 않는다. MAE·RMSE·편차와 미달 건수를 본다.

R² 대신 무엇을 보는가 — 스킬 점수
    R² 가 안 맞는 근본 원인은 **상대가 잘못됐다**는 것이다. R² 의 상대는 '실측값의
    사후평균'인데, 그 값은 입찰 시점에 알 수 없고 표본이 뭉쳐 있으면 사실상 정답이
    된다. 우리가 실제로 이겨야 하는 상대는 **담당자가 쓰던 일괄 보정**이다.

        스킬 = 1 − SSE(우리 방법) / SSE(일괄 보정)

    해석은 R² 와 같다 — 1.0 완벽, 0 종전과 동등, 음수면 종전보다 나쁘다.
    3회차 결과: 커널 +0.968 · GP +0.919 · 구간평균 +0.865
    (= 일괄 대비 오차제곱을 각각 96.8% · 91.9% · 86.5% 줄였다)

    이 지표는 분모가 '입찰 시점에 실제로 쓸 수 있었던 대안'이므로 표본이 작아도
    해석이 무너지지 않는다. R² 와 달리 순서·크기 모두 그대로 읽을 수 있다.

실행:
    python scripts/commission_stats.py
    python scripts/commission_stats.py --input scripts/data/commission_2026.csv --upto 3
"""
from __future__ import annotations

import argparse
import csv
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wirye_capacity import constants as C  # noqa: E402
from wirye_capacity.curve import CorrectionCurve  # noqa: E402
from wirye_capacity.gp import GPCorrectionCurve  # noqa: E402
from wirye_capacity.simulate import SimInput, simulate  # noqa: E402
from wirye_capacity.store import MeasurementStore  # noqa: E402
from wirye_capacity.theory import TheoryEngine  # noqa: E402

DATA = Path(__file__).resolve().parent / "data" / "commission_2026.csv"
METHODS = (("bin", "구간평균"), ("curve", "커널회귀"), ("gp", "GP"))
BASELINE_DATE = "2026-04-02"      # 이 날짜까지를 학습 출발점으로 되돌린다
LOOCV_REF = {"bin": 1.515, "curve": 1.428, "gp": 1.294}   # 36건 LOOCV MAE (기대치)


def stats(err: list[float]) -> dict:
    """부호 있는 오차 목록 → 지표. err = 실측 − 예측."""
    n = len(err)
    me = sum(err) / n                                   # 편차(bias)
    mae = sum(abs(e) for e in err) / n
    rmse = (sum(e * e for e in err) / n) ** 0.5
    sd = (sum((e - me) ** 2 for e in err) / (n - 1)) ** 0.5 if n > 1 else float("nan")
    return {"n": n, "me": me, "mae": mae, "rmse": rmse, "sd": sd,
            "max": max(abs(e) for e in err)}


def r2(actual: list[float], pred: list[float]) -> float:
    """R² — '사후평균을 찍는 것' 대비 성적. 상대(사후평균)가 이 표본에서 너무 강하다."""
    mu = sum(actual) / len(actual)
    sst = sum((a - mu) ** 2 for a in actual)
    sse = sum((a - p) ** 2 for a, p in zip(actual, pred))
    return float("nan") if sst == 0 else 1 - sse / sst


def skill(actual: list[float], pred: list[float], ref: list[float]) -> float:
    """스킬 점수 — '종전 방식(일괄 보정)' 대비 오차제곱 감소율.

    R² 가 이 문제에 맞지 않는 이유는 상대가 잘못됐기 때문이다. R² 의 상대는
    '실측값의 사후평균'인데, 그건 입찰 시점에 알 수 없는 값이고 표본이 뭉쳐
    있으면 사실상 정답이 된다(3회차 실측 보정값 sd 0.062 MW).

    우리가 실제로 이겨야 하는 상대는 **담당자가 쓰던 일괄 보정**이다. 그래서
    분모를 사후평균이 아니라 일괄 보정의 오차제곱합으로 바꾼다. 해석은 같다 —
    1.0 이면 완벽, 0 이면 종전과 동등, 음수면 종전보다 나쁘다.
    """
    sse = sum((a - p) ** 2 for a, p in zip(actual, pred))
    ref_sse = sum((a - r) ** 2 for a, r in zip(actual, ref))
    return float("nan") if ref_sse == 0 else 1 - sse / ref_sse


def build_baseline(path: Path) -> MeasurementStore:
    """시드에서 BASELINE_DATE 이후를 지운 사본 DB."""
    st = MeasurementStore(str(path))
    st.seed()
    for r in [r for r in st.all() if r.date > BASELINE_DATE]:
        st.delete_by_date(r.date)
    return st


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(DATA))
    ap.add_argument("--upto", type=int, default=0, help="앞 N 회차만 (0=전부)")
    a = ap.parse_args()

    rows = [r for r in csv.DictReader(
        l for l in Path(a.input).read_text(encoding="utf-8-sig").splitlines()
        if not l.lstrip().startswith("#")) if (r.get("date") or "").strip()]
    if a.upto:
        rows = rows[:a.upto]

    tmp = Path(tempfile.mkdtemp())
    st = build_baseline(tmp / "t.db")
    eng = TheoryEngine()
    n0 = st.count()

    per: list[dict] = []
    for i, r in enumerate(rows, 1):
        cit, press, rh, cc = (float(r[k]) for k in ("cit", "press", "rh", "cc_gross"))
        vac = float(r["vac"]) if (r.get("vac") or "").strip() else None
        recs = [{"cit": x.cit, "corr": x.corr} for x in st.all()]
        tbl = st.correction_table()
        corr = {"bin": None, "curve": CorrectionCurve(recs), "gp": GPCorrectionCurve(recs)}
        inp = SimInput(cit=cit, pressure=press, rh=rh, w=None, cp_meas=vac, cc_meas=cc)
        R = {m: simulate(inp, engine=eng, records=recs, correction_table=tbl,
                         corrector=corr[m]) for m, _ in METHODS}
        # 종전 방식(일괄 보정 = 누적 전체 평균) 도 같은 조건으로 계산해 기준선으로 쓴다
        blanket = sum(x["corr"] for x in recs) / len(recs)
        per.append({"i": i, "date": r["date"], "cit": cit, "n_train": len(recs),
                    "R": R, "blanket": blanket})
        st.add(st.build_record(cit=cit, press=press, cc_meas=cc, w=None, rh=rh,
                              cp_meas=vac, date=r["date"], engine=eng))

    print("=" * 76)
    print(f"시운전 성적표 — {len(per)}회차  (학습 출발 {n0}건, ~{BASELINE_DATE})")
    print("=" * 76)

    print("\n① 계산 일치 (결정론적 — 틀리면 버그)")
    print(f"   {'#':>2} {'날짜':12}{'CIT':>6}{'이론기준값':>11}{'실측 보정값':>12}")
    for p in per:
        b = p["R"]["bin"]
        print(f"   {p['i']:2} {p['date']:12}{p['cit']:6.1f}"
              f"{b.theory_base:11.2f}{b.meas_corr:+12.3f}")

    print("\n② 회차별 예측 (반영 전) vs 실측 — Net 기준")
    print(f"   {'#':>2} {'날짜':12}{'누적':>5}{'실측Net':>9}"
          + "".join(f"{lab:>10}" for _, lab in METHODS)
          + f"{'밴드':>8}")
    for p in per:
        b = p["R"]["bin"]
        line = f"   {p['i']:2} {p['date']:12}{p['n_train']:5}{b.meas_net:9.2f}"
        for m, _ in METHODS:
            line += f"{p['R'][m].real_net:10.2f}"
        print(line + f"{b.meas_net * 0.005:8.2f}")

    print(f"\n   {'#':>2} {'날짜':12}" + "".join(f"{'차(' + lab + ')':>12}" for _, lab in METHODS))
    for p in per:
        line = f"   {p['i']:2} {p['date']:12}"
        for m, _ in METHODS:
            line += f"{p['R'][m].net_diff:+12.2f}"
        print(line)
    print("   (차 = 실측 − 예측.  + 는 낮게 신고 = 안전,  − 는 높게 신고 = 미달 위험)")

    for basis, get_a, get_p, unit in (
            ("Net 기준 (입찰 관점)", lambda r: r.meas_net, lambda r: r.real_net, "MW"),
            ("보정값 기준 (모델 관점)", lambda r: r.meas_corr, lambda r: r.correction, "MW")):
        print(f"\n③ 종합 — {basis}")
        print(f"   {'방법':<10}{'편차ME':>9}{'MAE':>8}{'RMSE':>8}{'최대':>8}"
              f"{'R²':>11}{'스킬':>8}{'밴드내':>8}{'미달':>7}  LOOCV")
        # 일괄 보정 기준선 — 같은 회차·같은 조건. 스킬 점수의 분모다.
        ref = [(min(p["R"]["bin"].theory_cc + p["blanket"], C.BID_CAP_GROSS) - C.CC_AUX)
               if basis.startswith("Net") else p["blanket"] for p in per]
        for m, lab in list(METHODS) + [("__ref", "일괄(종전)")]:
            if m == "__ref":
                act = [get_a(p["R"]["bin"]) for p in per]
                prd, sk = ref, "기준선"
            else:
                act = [get_a(p["R"][m]) for p in per]
                prd = [get_p(p["R"][m]) for p in per]
                sk = f"{skill(act, prd, ref):+.3f}"
            s = stats([x - y for x, y in zip(act, prd)])
            # 밴드·미달 판정은 언제나 Net 기준이다(입찰 허용밴드 ±0.5%). 보정값 기준
            # 행에서도 같은 판정을 그대로 쓴다 — 오차가 동일하므로 결과가 같다.
            nets = [x.meas_net for x in (p["R"]["bin"] for p in per)]
            if m == "__ref":
                nref = [(min(p["R"]["bin"].theory_cc + p["blanket"], C.BID_CAP_GROSS)
                         - C.CC_AUX) for p in per]
                inb = sum(1 for a, r_ in zip(nets, nref) if abs(a - r_) <= 0.005 * a)
                sh = sum(1 for a, r_ in zip(nets, nref) if a - r_ < -0.005 * a)
            else:
                inb = sum(1 for p in per if p["R"][m].in_band)
                sh = sum(1 for p in per if p["R"][m].shortfall)
            loo = f"{LOOCV_REF[m]:.3f}" if m in LOOCV_REF else "3.833"
            print(f"   {lab:<10}{s['me']:+9.3f}{s['mae']:8.3f}{s['rmse']:8.3f}"
                  f"{s['max']:8.3f}{r2(act, prd):11.3f}{sk:>8}{inb:5d}/{len(per)}"
                  f"{sh:6d}건  {loo}")

    sd = stats([p["R"]["bin"].meas_corr - 0 for p in per])
    print(f"\n   ※ 실측 보정값의 산포 sd {sd['sd']:.3f} MW — 이 표본은 거의 일정하다.")
    print("     보정값 기준 R² 가 음수인 것은 SST 가 0 에 가까워서다. 모델 성능이")
    print("     나쁘다는 뜻이 아니라 이 표본으로 R² 를 쓸 수 없다는 뜻이다.")
    print("     Net 기준 R² 가 1 에 가까운 것도 의미 없다 — 온도로 생기는 분산은")
    print("     이론곡선이 설명하는 부분이고 모델의 공헌이 아니다.")
    if len(per) < 10:
        print(f"\n   ⚠ {len(per)}회차는 표본이 작다. MAE·편차·미달 건수로 판단하고,")
        print("     방법 확정은 회차를 더 쌓은 뒤에 한다.")


if __name__ == "__main__":
    main()
