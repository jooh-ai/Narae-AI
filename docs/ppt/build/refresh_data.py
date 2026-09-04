#!/usr/bin/env python3
"""장표 수치 재계산 — 데이터가 갱신되면 이것부터 돌린다.

    python3 docs/ppt/build/refresh_data.py

누적 데이터에서 장표에 쓰는 수치를 전부 다시 계산해 deck_data.json 에 적는다.
슬라이드 코드는 그 파일 하나만 본다. 그래서 회차가 쌓이면

    python3 docs/ppt/build/refresh_data.py    # 수치 재계산
    node    docs/ppt/build/build.js           # 18장 재생성
    python3 docs/ppt/build/verify.py          # 기하 검증

세 줄로 끝난다.

**계산은 전부 도구 코드를 그대로 호출한다.** select.loocv · gp.GPCorrectionCurve ·
method_compare._score · commission_stats.stats/skill — 장표용으로 따로 구현하지
않는다. 그래야 Tool 화면에 뜨는 값과 장표 값이 어긋날 수 없다.

계산하지 않고 손으로 두는 것 (기록이지 계산이 아니다)
    · BLT 적용값 16회차      담당자 실적표에서 옮겨 적은 값 (scripts/period_check.py)
    · 시운전 함정 3건        증상·크기·가드는 서술이다
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / "tool"
sys.path.insert(0, str(TOOL))
sys.path.insert(0, str(TOOL / "scripts"))

from wirye_capacity import constants as C            # noqa: E402
from wirye_capacity import select                    # noqa: E402
from wirye_capacity.correction import aggregate_bins  # noqa: E402
from wirye_capacity.gp import KERNELS, GPCorrectionCurve  # noqa: E402
from wirye_capacity.profile import build_profile      # noqa: E402
from wirye_capacity.theory import TheoryEngine        # noqa: E402
import commission_stats as CS                        # noqa: E402
import method_compare as MC                          # noqa: E402

SEED = TOOL / "wirye_capacity" / "data" / "measurements_seed.json"
OUT = Path(__file__).with_name("deck_data.json")
CURVE_T = (0, 10, 20, 30)          # 방식별 보정 곡선을 재는 온도
WORST_N = 4                        # 오차 상위 몇 건을 장표에 싣는가
PROF_T = tuple(range(-10, 41, 2))  # 곡선 비교 장표를 그리는 온도 (Tool [📈 출력곡선 비교])


def common_set(recs: list[dict]) -> list[int]:
    """방식 7가지가 **모두** 예측할 수 있는 회차의 번호.

    구간평균은 그 회차를 빼면 구간이 비는 자리에서 예측을 못 한다(20~25℃ 1건).
    7가지를 같은 자리에서 겨루려면 그 회차를 빼야 공정하다 — select.loocv 가
    이미 그렇게 한다. 장표의 모든 채점을 **이 집합 하나**로 통일한다.
    그러지 않으면 같은 '예측 오차' 가 표에서는 1.301, 요약에서는 1.286 으로
    나와 청중이 짚었을 때 답이 궁색해진다.
    """
    grid = {}
    for m in select.METHODS:
        col = []
        for i in range(len(recs)):
            train = [recs[k] for k in range(len(recs)) if k != i]
            try:
                col.append(select.predict(m, train, recs[i]["cit"]))
            except Exception:                               # noqa: BLE001
                col.append(None)
        grid[m] = col
    return [i for i in range(len(recs))
            if all(grid[m][i] is not None for m in select.METHODS)]


def blanket_loocv(recs: list[dict], sel: list[int]) -> dict:
    """종전 방식(일괄 보정)을 한 건씩 가려 채점한다.
    일괄값은 나머지의 평균 = 최소제곱 최적 상수. method_compare 와 같은 정의다.

    `flat` 만 전체 회차의 평균이다 — 이 값은 채점 결과가 아니라 '종전에는 이
    숫자 하나였다' 는 설명용 상수이고, 그림의 기준선으로도 쓴다.
    채점(mae·rmse·worst)은 `sel` 집합에서만 한다.
    """
    ys = [r["corr"] for r in recs]
    n, tot = len(ys), sum(ys)
    err, rows = [], []
    for i in sel:
        y = ys[i]
        pred = (tot - y) / (n - 1)
        e = pred - y                              # + 면 높게 신고 = 미달 위험
        err.append(e)
        rows.append({"date": recs[i]["date"], "cit": recs[i]["cit"], "corr": y,
                     "pred": round(pred, 3), "err": round(e, 3)})
    rows.sort(key=lambda d: -abs(d["err"]))
    return {
        "flat": round(tot / n, 3),
        "n_score": len(sel),
        "mae": round(sum(abs(e) for e in err) / len(err), 3),
        "rmse": round((sum(e * e for e in err) / len(err)) ** 0.5, 3),
        "worst": rows[:WORST_N],
    }


def bid_impact(recs: list[dict], sel: list[int]) -> dict:
    """종전 vs 개선을 입찰 관점으로 채점 — 미달 몇 건, 과대 신고 몇 MW.
    밴드(±0.5%)·미달 판정은 method_compare._score 정의를 그대로 쓴다.
    채점 집합은 `sel` — 7가지 비교표와 같은 자리에서 잰다(common_set 주석 참조)."""
    eng = MC.TheoryEngine()
    by = {n: b for n, b in MC.METHODS}
    out = {}
    for key, name in (("blanket", "일괄 보정 (종전 방식)"), ("gp", "GP (현재 툴 기본)")):
        build = by[name]
        cases = [(recs[i], build([recs[k] for k in range(len(recs)) if k != i])(recs[i]["cit"]))
                 for i in sel]
        mae, worst, short, over, opp = MC._score(eng, cases)
        out[key] = {"label": name, "mae": round(mae, 3), "max": round(worst, 3),
                    "short": short, "over": round(over, 1), "opp": round(opp, 1)}
    b, g = out["blanket"], out["gp"]
    out["cut"] = {"mae": round((1 - g["mae"] / b["mae"]) * 100),
                  "short": round((1 - g["short"] / b["short"]) * 100) if b["short"] else None,
                  "over": round((1 - g["over"] / b["over"]) * 100) if b["over"] else None}
    return out


def commission(recs: list[dict]) -> dict:
    """시운전 회차 성적 — BASELINE_DATE 이후 회차를 앞의 누적만으로 예측(walk-forward).
    지표 정의는 commission_stats 의 것을 그대로 쓴다."""
    recs = sorted(recs, key=lambda r: r["date"])
    base = [r for r in recs if r["date"] <= CS.BASELINE_DATE]
    trial = [r for r in recs if r["date"] > CS.BASELINE_DATE]
    if not trial:
        return {"n": 0}
    act, gp, flat = [], [], []
    for i, r in enumerate(trial):
        train = base + trial[:i]
        p = select.predict("gp:rbf", train, r["cit"])
        if p is None:
            continue
        act.append(r["corr"])
        gp.append(p)
        flat.append(sum(t["corr"] for t in train) / len(train))
    st = CS.stats([a - p for a, p in zip(act, gp)])
    return {
        "n": len(act),
        "from": trial[0]["date"], "to": trial[-1]["date"],
        "train_start": len(base),
        "me": round(st["me"], 3), "mae": round(st["mae"], 3), "rmse": round(st["rmse"], 3),
        "skill": round(CS.skill(act, gp, flat), 3),
        "short": sum(1 for a, p in zip(act, gp) if p > a),   # 예측이 높다 = 미달 위험
        "rows": [{"date": r["date"], "cit": r["cit"], "corr": round(a, 3),
                  "pred": round(p, 3), "diff": round(a - p, 3)}
                 for r, a, p in zip(trial, act, gp)],
    }



def _pearson(x: list[float], y: list[float]) -> float:
    n = len(x); mx = sum(x) / n; my = sum(y) / n
    sx = sum((a - mx) ** 2 for a in x) ** 0.5
    sy = sum((b - my) ** 2 for b in y) ** 0.5
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)


def _resid(x: list[float], y: list[float]) -> list[float]:
    """y 에서 x 로 설명되는 부분(직선)을 뺀 나머지."""
    n = len(x); mx = sum(x) / n; my = sum(y) / n
    b = sum((a - mx) * (c - my) for a, c in zip(x, y)) / sum((a - mx) ** 2 for a in x)
    a0 = my - b * mx
    return [c - (a0 + b * xx) for xx, c in zip(x, y)]


def causes(recs: list[dict]) -> dict:
    """원인 규명 — 후보 변수가 보정값을 설명하는가, 3단으로 좁힌다.

      ① 원시        보정값 vs 후보. 여기서는 다섯 개가 다 강하게 보인다.
      ② 온도 통제 후 '온도로 설명 안 되는 후보' vs '온도로 설명 안 되는 보정값'.
                    후보들이 서로 온도에 묶여 있으므로 이게 진짜 질문이다.
      ③ 모델 잔차   '온도로 설명 안 되는 후보' 가 'LOOCV 모델이 못 맞힌 부분' 을
                    설명하는가. vacuum_effect_check.py ③ 과 같은 정의다 —
                    두 곳이 다른 정의를 쓰면 문서끼리 숫자가 어긋난다.
                    남는 것이 있으면 그것이 다음 개선 후보다.

    임계 r 은 α=0.05 양쪽, df=n−2 의 t 표에서 얻는다 (r = t/√(t²+df)).
    이 값을 넘지 못하면 '관계 없음' 이다 — 눈에 보이는 관계도 여기를 넘어야 한다.

    IGV(W) 는 후보에 넣지 않는다. 보정값 정의에서 이미 빼고 있는 값이라
    (보정값 = 실측 − 이론 − W) 환경 원인과 나란히 두면 뜻이 어긋난다.
    IGV 는 가설 1(설비가 달랐다 → IGV 미실시)에서 다룬다.
    """
    T = [r["cit"] for r in recs]
    K = [r["corr"] for r in recs]
    n = len(recs)
    tcrit = 2.024 if n >= 30 else 2.101                 # α=0.05 양쪽, df≈38
    rcrit = tcrit / math.sqrt(tcrit * tcrit + n - 2)

    # 모델이 못 맞힌 부분 — 한 건씩 가리고 맞혀본 잔차(LOOCV)
    mres = []
    for i, d in enumerate(recs):
        f = GPCorrectionCurve([x for j, x in enumerate(recs) if j != i], kernel="rbf")
        mres.append(d["corr"] - f(d["cit"]))

    out = []
    for label, key in (("외기온도", "cit"), ("복수기 진공도", "cp_meas"),
                       ("대기압", "press"), ("상대습도", "rh")):
        X = [r[key] for r in recs]
        row = {"label": label, "key": key, "raw": round(_pearson(X, K), 3)}
        if key == "cit":
            row["vs_t"] = None                          # 온도 자신은 통제 대상이 아니다
            row["part"] = None
            row["model"] = None
        else:
            row["vs_t"] = round(_pearson(T, X), 3)
            row["part"] = round(_pearson(_resid(T, X), _resid(T, K)), 3)
            row["model"] = round(_pearson(_resid(T, X), mres), 3)
        out.append(row)
    return {"n": n, "rcrit": round(rcrit, 3), "rows": out,
            "model_mae": round(sum(abs(v) for v in mres) / n, 3)}

def learning(recs: list[dict], start: int = 12, blocks: int = 4) -> dict:
    """회차가 쌓이면 예측이 나아지는가 — walk-forward 학습 곡선.

    각 회차를 **그 앞의 회차만으로** 학습해 예측하고(뒤를 보지 않는다) 오차를
    구한 뒤, 시간 순으로 몇 구간으로 나눠 구간별 평균 오차를 낸다. 구간 평균을
    쓰는 이유 — 누적 평균은 앞의 큰 오차가 뒤로 갈수록 희석되어 **무조건**
    내려간다. 그건 나아진 게 아니라 평균의 성질이다. 구간 평균은 '그 무렵의
    실력' 을 보여주므로 오르내림도 그대로 드러난다.

    start: 이 회차 수까지는 학습만 하고 채점하지 않는다(너무 적으면 의미 없다).
    """
    rs = sorted(recs, key=lambda r: r["date"])
    pts = []
    for k in range(start, len(rs)):
        try:
            f = GPCorrectionCurve(rs[:k], kernel="rbf")
        except Exception:                                   # noqa: BLE001
            continue
        pts.append({"no": k + 1, "date": rs[k]["date"],
                    "err": round(abs(rs[k]["corr"] - f(rs[k]["cit"])), 3)})
    if not pts:
        return {"n": 0}
    size = len(pts) / blocks
    out = []
    for b in range(blocks):
        seg = pts[int(b * size):int((b + 1) * size)]
        if not seg:
            continue
        out.append({"from": seg[0]["no"], "to": seg[-1]["no"], "n": len(seg),
                    "mae": round(sum(p["err"] for p in seg) / len(seg), 3)})
    return {"n": len(pts), "start": start + 1, "blocks": out,
            "first": out[0]["mae"], "last": out[-1]["mae"],
            "cut": round((1 - out[-1]["mae"] / out[0]["mae"]) * 100)}


def profile_cmp(recs: list[dict], method: str) -> dict:
    """Tool [📈 출력곡선 비교] 탭과 같은 곡선을 장표용으로 뽑는다.

    그 탭은 `build_profile(engine, table, corrector=...)` 결과를 그린다. 여기서도
    같은 함수를 같은 인자로 부른다 — 장표 곡선과 화면 곡선이 어긋날 수 없다.

      이론  = cc_theory      (온도·대기압·열화·IGV 만 반영, 보정 없음)
      실제  = cc_real_gross  (거기에 온도별 보정값을 얹은 값)
      차이  = correction     (그 온도에서 모델이 배운 값)

    실측점은 여기서 만들지 않는다 — 장표 아래 패널은 `scatter`(회차별 실제
    차이)를 그대로 찍는다. 회차의 실측 출력을 기준 대기압 프로파일 위로
    옮겨 찍으면 환산값이 되는데, 그것을 "실제 테스트 결과" 라고 부르면
    설명이 한 겹 틀어진다.

    장표에는 Gross 로 그린다. 화면 상단은 Net(입찰값)이라 상한 462 에서 잘리는데,
    그 평평한 구간이 '이론과 실제의 차이' 를 가려 버린다. 차이를 보이는 장이므로
    잘리지 않는 Gross 를 쓰고, Net·상한은 다른 장에서 설명한다.
    """
    eng = TheoryEngine()
    table = aggregate_bins(recs)
    corrector = select.make_corrector(method, recs)
    rows = {r.temp: r for r in build_profile(eng, table, temps=list(PROF_T),
                                             corrector=corrector)}
    prof = [{"t": t,
             "theory": round(rows[t].cc_theory, 2),
             "real": round(rows[t].cc_real_gross, 2),
             "corr": round(rows[t].correction, 2)} for t in PROF_T]

    gaps = [(p["real"] - p["theory"]) for p in prof]
    return {"method": method, "t": list(PROF_T), "rows": prof,
            "gap_max": round(max(gaps), 2), "gap_min": round(min(gaps), 2),
            "net_cap": C.BID_CAP_NET}

def main() -> None:
    recs = json.loads(SEED.read_text(encoding="utf-8"))
    recs.sort(key=lambda r: r["cit"])
    ys = [r["corr"] for r in recs]

    # ① 구간별 건수 — 도구의 BINS 를 그대로 쓴다
    bins = []
    for lo, hi, _ in C.BINS:
        n = sum(1 for r in recs if lo <= r["cit"] < hi)
        if n:
            bins.append({"lo": lo, "hi": hi,
                         "label": f"{lo} ~ {hi}℃".replace("-", "−"), "n": n})

    # ② 후보 7가지를 같은 평가집합에서 채점 (도구의 loocv 그대로)
    scores = select.loocv(recs, list(select.METHODS))
    scores.sort(key=lambda s: s.mae)
    methods = [{"key": s.method, "label": select.METHOD_LABEL[s.method],
                "n": s.n, "mae": round(s.mae, 3), "rmse": round(s.rmse, 3),
                "r2": round(s.r2, 3), "me": round(s.me, 3), "over": s.over}
               for s in scores]

    # ③ 방식별 보정 곡선
    curves = {}
    for k in KERNELS:
        try:
            f = GPCorrectionCurve(recs, kernel=k)
            curves[k] = [round(f(t), 2) for t in CURVE_T]
        except Exception:                                   # noqa: BLE001
            curves[k] = None

    # ④ 입찰 관점 — 미달 건수·과대 신고 누계.
    #    밴드(±0.5%)와 판정은 method_compare._score 정의를 그대로 쓴다.
    sel = common_set(recs)
    impact = bid_impact(recs, sel)

    flat = blanket_loocv(recs, sel)
    best = methods[0]

    data = {
        "generated": datetime.now(timezone.utc).astimezone().isoformat(timespec="minutes"),
        "source": str(SEED.relative_to(ROOT)),
        "n": len(recs),
        "n_score": len(sel),           # 채점에 쓴 회차 수 (7가지 공통 집합)
        "cit_range": [min(r["cit"] for r in recs), max(r["cit"] for r in recs)],
        "corr_range": [round(min(ys), 3), round(max(ys), 3)],
        "scatter": [[r["cit"], round(r["corr"], 3)] for r in recs],
        "blanket": flat,
        "bins": bins,
        "methods": methods,
        "best": best,
        "impact": impact,
        "curve_t": list(CURVE_T),
        "curves": curves,
        "profile": profile_cmp(recs, best["key"]),
        "causes": causes(recs),
        "learning": learning(recs),
        "commission": commission(recs),
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    # ── 사람이 눈으로 확인하는 요약 ──────────────────────────────
    print(f"누적        {data['n']}건   보정값 {data['corr_range'][0]:+.2f} ~ "
          f"{data['corr_range'][1]:+.2f} MW   외기 {data['cit_range'][0]} ~ {data['cit_range'][1]}℃")
    print(f"채점 집합   {len(sel)}회 (7가지 공통) / 누적 {len(recs)}회")
    print(f"종전 일괄   baseline {flat['flat']:+.2f}   LOOCV MAE {flat['mae']:.3f} · RMSE {flat['rmse']:.3f}")
    print(f"최적 방식   {best['label']}   MAE {best['mae']:.3f} · RMSE {best['rmse']:.3f} · R² {best['r2']:+.3f}")
    print("후보 순위   " + " / ".join(f"{m['label']} {m['mae']:.3f}" for m in methods))
    print("구간별      " + " · ".join(f"{b['label']} {b['n']}건" for b in bins))
    print("오차 상위   " + " / ".join(f"{w['date'][2:]} {w['err']:+.2f}" for w in flat["worst"]))
    b, g, cut = impact["blanket"], impact["gp"], impact["cut"]
    print(f"입찰 관점   평균오차 {b['mae']:.2f} → {g['mae']:.2f} MW ({cut['mae']}%↓)  ·  "
          f"미달 {b['short']} → {g['short']}건 ({cut['short']}%↓)  ·  "
          f"과대신고 {b['over']:.1f} → {g['over']:.1f} MW ({cut['over']}%↓)")
    lz = data["learning"]
    if lz.get("n"):
        print(f"학습 곡선   {lz['start']}회차부터 {lz['n']}건 walk-forward  ·  " +
              "  ".join(f"{b['from']}~{b['to']}회 {b['mae']:.2f}" for b in lz["blocks"]) +
              f"  →  {lz['first']:.2f} → {lz['last']:.2f} MW ({lz['cut']}%↓)")
    cz = data["causes"]
    print(f"원인 규명   임계 r {cz['rcrit']:.3f} (n={cz['n']})  ·  " + "  ·  ".join(
        f"{r['label']} 원시 {r['raw']:+.2f}" +
        (f" → 통제후 {r['part']:+.2f}" if r["part"] is not None else "")
        for r in cz["rows"]))
    pc = data["profile"]
    print(f"곡선 비교   {pc['t'][0]} ~ {pc['t'][-1]}℃  이론 vs 실제  차이 "
          f"{pc['gap_min']:+.2f} ~ {pc['gap_max']:+.2f} MW")
    c = data["commission"]
    if c["n"]:
        print(f"시운전      {c['n']}회차 ({c['from']} ~ {c['to']})  편차 {c['me']:+.3f} · "
              f"MAE {c['mae']:.3f} · RMSE {c['rmse']:.3f} · 스킬 {c['skill']:+.3f} · 미달 {c['short']}건")
    print(f"\n기록됨      {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
