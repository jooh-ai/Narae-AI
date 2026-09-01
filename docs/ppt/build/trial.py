#!/usr/bin/env python3
"""시운전 회차 입력 — 예측을 먼저 남기고, 실측이 나오면 대조한다.

    ① 실측 전 (신고 직전)
       python3 docs/ppt/build/trial.py predict --date 2026-08-12 --cit 30.2 --press 1004.3 --rh 62.5

    ② 실측이 나온 뒤
       python3 docs/ppt/build/trial.py record --date 2026-08-12 --cc 388.4 --apply

    ③ 지금까지의 시운전 원장
       python3 docs/ppt/build/trial.py status

왜 예측을 먼저 남기는가
    시운전에서 재는 것은 '반영 전에 낸 예측이 실측과 얼마나 맞았는가' 다
    (tool/scripts/commission_stats.py 의 정의). 실측을 보고 나서 채점해도
    코드가 그 회차를 학습에서 빼주므로 방법론상 문제는 없지만, 예측을 먼저
    적어 둔 기록이 있으면 '맞히고 나서 설명한 것이 아니다' 를 증명할 수 있다.
    그 기록이 trial_log.json 이다.

계산은 전부 도구 코드가 한다
    이론기준값·보정값   store.MeasurementStore.build_record
    예측                select.predict('gp:rbf', 앞의 누적, cit)
    신고값(Net)          method_compare 와 같은 식 — min(이론+W+보정 − 소내, 상한)
    이 스크립트는 값을 옮기고 가드를 걸 뿐, 따로 계산하지 않는다.

반영 가드 (계획서 §6 '시운전 함정')
    IGV 미실시    --no-igv → 누적 반영 차단. 원장에는 남기고 학습에서만 뺀다.
    습도계 이탈   --rh2 를 주면 두 값을 비교해 --rh-gap(기본 10%p) 을 넘으면 보류.
                  실제로 겪은 사례는 취득 19.6% vs 실제 68.5% (48.9%p 벌어짐).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / "tool"
sys.path.insert(0, str(TOOL))

from wirye_capacity import constants as C            # noqa: E402
from wirye_capacity import select                    # noqa: E402
from wirye_capacity.store import MeasurementStore    # noqa: E402
from wirye_capacity.theory import TheoryEngine, igv_turnup  # noqa: E402

SEED = TOOL / "wirye_capacity" / "data" / "measurements_seed.json"
LOG = Path(__file__).with_name("trial_log.json")
METHOD = "gp:rbf"


def load_seed() -> list[dict]:
    return json.loads(SEED.read_text(encoding="utf-8"))


def load_log() -> list[dict]:
    return json.loads(LOG.read_text(encoding="utf-8")) if LOG.exists() else []


def save_log(rows: list[dict]) -> None:
    LOG.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def bid_net(theory: float, w: float, corr: float) -> float:
    """신고값(Net) — method_compare 와 같은 식."""
    return min(theory + w + corr - C.CC_AUX, C.BID_CAP_NET)


def guards(a) -> list[str]:
    """반영을 막아야 하는 사유. 비어 있으면 반영해도 된다."""
    out = []
    if a.no_igv:
        out.append("IGV 미실시 — 이 회차는 학습에 넣지 않는다 (함정 1)")
    if a.rh is not None and a.rh2 is not None and abs(a.rh - a.rh2) > a.rh_gap:
        out.append(f"습도계 두 대가 {abs(a.rh - a.rh2):.1f}%p 벌어졌다 "
                   f"({a.rh} vs {a.rh2}, 기준 {a.rh_gap}%p) — 반영 보류 (함정 2)")
    return out


def cmd_predict(a) -> None:
    seed = load_seed()
    train = [r for r in seed if r.get("date", "") < a.date] or seed
    w = 0.0 if a.no_igv else (a.w if a.w is not None else igv_turnup(a.cit))
    theory = a.theory if a.theory is not None else TheoryEngine().theory_cc(a.cit, a.press, rh=a.rh)
    pred = select.predict(METHOD, train, a.cit)
    if pred is None:
        sys.exit("이 온도에서는 예측할 수 없다 — 누적이 부족하다.")
    net = bid_net(theory, w, pred)

    print(f"회차        {a.date}   CIT {a.cit}℃ · 대기압 {a.press} mbar"
          + (f" · 습도 {a.rh}%" if a.rh is not None else " · 습도 미입력(60% 고정 계산)"))
    print(f"학습 누적   {len(train)}건 (이 회차 이전만)")
    print(f"이론기준값  {theory:.2f} MW" + (f"   W(IGV) {w:+.2f}" if w else "   W(IGV) 0 — 미실시"))
    print(f"예측 보정값 {pred:+.3f} MW")
    print(f"예상 신고값 {net:.2f} MW  (Net)")
    for g in guards(a):
        print(f"⚠ 가드      {g}")

    rows = [r for r in load_log() if r["date"] != a.date]
    rows.append({"date": a.date, "status": "predicted",
                 "at": datetime.now().astimezone().isoformat(timespec="minutes"),
                 "cit": a.cit, "press": a.press, "rh": a.rh, "rh2": a.rh2,
                 "no_igv": a.no_igv, "w": w, "theory": round(theory, 3),
                 "pred_corr": round(pred, 3), "pred_net": round(net, 2),
                 "train_n": len(train)})
    rows.sort(key=lambda r: r["date"])
    save_log(rows)
    print(f"\n기록됨      {LOG.relative_to(ROOT)}  — 실측이 나오면 record 로 대조한다")


def cmd_record(a) -> None:
    seed = load_seed()
    if any(r.get("date") == a.date and not a.force for r in seed):
        sys.exit(f"{a.date} 는 이미 누적에 있다. 다시 넣으려면 --force.")
    rows = load_log()
    prior = next((r for r in rows if r["date"] == a.date and r["status"] == "predicted"), None)

    # 예측 때 준 값을 그대로 이어 쓴다 — 두 번 적지 않게
    for k in ("cit", "press", "rh", "rh2", "w", "theory"):
        if getattr(a, k, None) is None and prior:
            setattr(a, k, prior.get(k))
    if a.no_igv is False and prior:
        a.no_igv = prior.get("no_igv", False)
    if a.cit is None or a.press is None:
        sys.exit("--cit 과 --press 가 필요하다 (predict 를 먼저 돌렸다면 자동으로 이어진다).")

    w = 0.0 if a.no_igv else a.w
    rec = MeasurementStore().build_record(
        cit=a.cit, press=a.press, cc_meas=a.cc, w=w, rh=a.rh,
        cp_meas=a.cp, cp_design=a.cp_design, season=a.season, date=a.date)

    print(f"회차        {a.date}   CIT {a.cit}℃ · 대기압 {a.press} mbar · CC 실측 {a.cc} MW")
    print(f"이론기준값  {rec.theory:.2f} MW   W(IGV) {rec.w:+.2f}")
    print(f"실측 보정값 {rec.corr:+.3f} MW   ← 도구의 build_record 가 계산")
    if prior:
        d = rec.corr - prior["pred_corr"]
        print(f"예측 보정값 {prior['pred_corr']:+.3f} MW  (예측 시각 {prior['at']})")
        print(f"차이        {d:+.3f} MW   " +
              ("낮게 신고 = 안전" if d > 0 else "높게 신고 = 미달 위험" if d < 0 else "일치"))
    else:
        print("예측 기록   없음 — 실측 전에 predict 를 돌리지 않았다. 채점은 되지만"
              " '먼저 적어 두고 맞혔다' 는 증거는 남지 않는다.")

    g = guards(a)
    for s in g:
        print(f"⚠ 가드      {s}")

    row = {"date": a.date, "status": "recorded",
           "at": datetime.now().astimezone().isoformat(timespec="minutes"),
           "cit": a.cit, "press": a.press, "rh": a.rh, "rh2": a.rh2,
           "no_igv": a.no_igv, "w": rec.w, "theory": round(rec.theory, 3),
           "cc_meas": a.cc, "corr": round(rec.corr, 3),
           "pred_corr": prior["pred_corr"] if prior else None,
           "diff": round(rec.corr - prior["pred_corr"], 3) if prior else None,
           "applied": not g}
    rows = [r for r in rows if r["date"] != a.date] + [row]
    rows.sort(key=lambda r: r["date"])

    entry = {k: getattr(rec, k) for k in
             ("cit", "press", "rh", "cp_meas", "cp_design", "cc_meas", "w", "theory", "corr")}
    entry["corr"] = round(entry["corr"], 3)
    entry["theory"] = round(entry["theory"], 2)
    entry.update(season=rec.season, date=rec.date)

    if g:
        print("\n반영 보류   가드에 걸렸다. 누적에 넣지 않는다 — 원장에만 남긴다.")
        save_log(rows)
        return
    if not a.apply:
        print("\n미리보기    (--apply 를 붙이면 누적에 넣는다)")
        print("            " + json.dumps(entry, ensure_ascii=False))
        return

    seed = [r for r in seed if r.get("date") != a.date] + [entry]
    seed.sort(key=lambda r: (r.get("date") or ""))
    SEED.write_text(json.dumps(seed, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    save_log(rows)
    print(f"\n반영됨      {SEED.relative_to(ROOT)}  (누적 {len(seed)}건)")
    print("다음        python3 docs/ppt/build/refresh_data.py"
          "  →  node docs/ppt/build/build.js  →  python3 docs/ppt/build/verify.py")


def cmd_status(a) -> None:
    rows = load_log()
    if not rows:
        print("원장이 비어 있다. predict 부터 돌린다.")
        return
    print(f"{'날짜':12s} {'상태':10s} {'예측':>8s} {'실측':>8s} {'차이':>8s}  반영")
    for r in rows:
        p = f"{r['pred_corr']:+.3f}" if r.get("pred_corr") is not None else "—"
        m = f"{r['corr']:+.3f}" if r.get("corr") is not None else "—"
        d = f"{r['diff']:+.3f}" if r.get("diff") is not None else "—"
        ap = "○" if r.get("applied") else ("×" if r["status"] == "recorded" else "—")
        print(f"{r['date']:12s} {r['status']:10s} {p:>8s} {m:>8s} {d:>8s}   {ap}")
    done = [r for r in rows if r.get("diff") is not None]
    if done:
        errs = [abs(r["diff"]) for r in done]
        print(f"\n{len(done)}회차 대조   평균 오차 {sum(errs) / len(errs):.3f} MW · "
              f"최대 {max(errs):.3f} MW")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, need_env: bool):
        p.add_argument("--date", required=True, help="회차 날짜 (예: 2026-08-12)")
        p.add_argument("--cit", type=float, required=need_env, help="외기온도 CIT (℃)")
        p.add_argument("--press", type=float, required=need_env, help="대기압 (mbar)")
        p.add_argument("--rh", type=float, help="상대습도 (%%) — 생략하면 60%% 고정으로 계산한다")
        p.add_argument("--rh2", type=float, help="두 번째 습도계 값 — 주면 이탈을 검사한다")
        p.add_argument("--rh-gap", type=float, default=10.0, dest="rh_gap",
                       help="습도계 이탈 판정 기준 %%p (기본 10)")
        p.add_argument("--no-igv", action="store_true", dest="no_igv",
                       help="IGV Turn-up 미실시 — 누적 반영을 차단한다")
        p.add_argument("--w", type=float, help="W(IGV) 직접 지정. 생략 시 온도밴드값")
        p.add_argument("--theory", type=float, help="이론기준값을 엑셀4 I열 값으로 고정")

    pr = sub.add_parser("predict", help="실측 전 예측을 내고 원장에 남긴다")
    common(pr, True)
    pr.set_defaults(func=cmd_predict)

    rc = sub.add_parser("record", help="실측을 넣어 대조하고 누적에 반영한다")
    common(rc, False)
    rc.add_argument("--cc", type=float, required=True, help="CC Gross 실측 (MW)")
    rc.add_argument("--cp", type=float, help="진공도 실측 (mbar)")
    rc.add_argument("--cp-design", type=float, dest="cp_design", help="진공도 설계값 (mbar)")
    rc.add_argument("--season", help="시즌 라벨 (엑셀4 표기)")
    rc.add_argument("--apply", action="store_true", help="실제로 누적에 반영한다")
    rc.add_argument("--force", action="store_true", help="같은 날짜가 있어도 덮어쓴다")
    rc.set_defaults(func=cmd_record)

    st = sub.add_parser("status", help="시운전 원장 요약")
    st.set_defaults(func=cmd_status)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
