"""시운전 — 새 테스트 결과를 한 회차씩 넣으며 예측이 맞는지 검증한다.

핵심 규칙 : 예측을 먼저 기록하고, 그 다음에 반영한다
    새 실적을 먼저 DB 에 넣고 나서 맞춰보면 모델이 이미 그 값을 본 상태다. 자기
    데이터로 자기를 채점하는 셈이라 항상 좋게 나온다(in-sample). 그래서 이 스크립트는
    반드시 '예측 → 대조 → 반영' 순으로만 진행하고, 반영 시점에 그때의 예측을 함께
    기록해 둔다. 회차 기록(commission_log.csv)이 시운전 결과 보고서가 된다.

무엇을 검증하는가 (섞으면 안 되는 세 가지)
    ① 계산 일치   담당자 표와 같은 입력에 같은 이론기준값·보정값이 나오는가.
                  결정론적 검사다. 허용차 0.25 MW (엔진 vs 엑셀4 I열 기존 차이 0.19).
    ② 예측 정확도 그날 조건에서 툴이 미리 낸 신고값이 실측과 얼마나 맞는가.
                  반영 전에만 측정할 수 있다. 판정은 입찰 허용밴드 ±0.5%.
    ③ 방법 선택   구간평균·커널·GP 를 같은 6건으로 채점해 어느 쪽을 쓸지 정한다.

취득 경로(RiMS 값이 담당자 표와 같은가)는 이 스크립트 밖이다. OPC UA 접속이
필요하므로 `python -m wirye_capacity check-rims` 또는 scripts/source_compare.py 로
따로 확인한다.

사용법
    python scripts/commission.py --init            # 입력 CSV 서식 생성
    python scripts/commission.py --walk            # 사본 DB 로 전 회차 미리보기(안전)
    python scripts/commission.py --step            # 다음 1건 예측·대조 (DB 안 바꿈)
    python scripts/commission.py --step --apply    # 확인 후 반영 + 회차 기록
    python scripts/commission.py --report          # 지금까지 회차 요약
"""
from __future__ import annotations

import argparse
import csv
import shutil
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

METHODS = ("bin", "curve", "gp")
LABEL = {"bin": "구간평균", "curve": "커널회귀", "gp": "GP"}
THEORY_TOL = 0.25          # 담당자 표 대조 허용차 (MW)
FIELDS = ("date", "cit", "press", "rh", "cc_gross", "vac", "igv", "w",
          "ref_theory", "ref_corr")

TEMPLATE = """\
# 시운전 입력 — 담당자 실적표에서 옮겨 적는다. '#' 줄은 무시된다.
#   date       테스트 날짜 (YYYY-MM-DD)
#   cit        Comp. Inlet Temp (°C)
#   press      대기압 (mbar)
#   rh         상대습도 (%)
#   cc_gross   CC(Gross) 실측 (MW)      ← IGV 반영값
#   vac        진공도 (mbar, 없으면 비움)
#   igv        IGV Turn-up 실시 여부. O(기본) / X
#              X 인 회차는 아예 처리하지 않는다 — 담당자 방침이다. IGV 실시 여부에
#              따라 출력 변동이 너무 커서, 일관성을 위해 실시 시험만 보정값에 쓴다.
#   w          W(IGV) 직접 지정. 비우면 온도밴드 기본값(+6/+4/0)
#   ref_theory 담당자 표의 이론기준값 (있으면 계산 일치 검증에 쓴다)
#   ref_corr   담당자 표의 보정값       (같음)
date,cit,press,rh,cc_gross,vac,igv,w,ref_theory,ref_corr
2026-05-12,,,,,O,,,,
"""


def _f(v):
    v = (v or "").strip()
    return float(v) if v else None


def load_input(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"입력 파일이 없습니다: {path}\n  먼저 --init 로 서식을 만드세요.")
    rows = []
    with path.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(l for l in f if not l.lstrip().startswith("#")):
            if not (row.get("date") or "").strip():
                continue
            r = {k: _f(row.get(k)) for k in FIELDS if k not in ("date", "igv")}
            r["date"] = row["date"].strip()
            r["igv"] = (row.get("igv") or "O").strip().upper() != "X"
            missing = [k for k in ("cit", "press", "cc_gross") if r[k] is None]
            if missing:
                raise SystemExit(f"{r['date']}: 필수 항목 누락 {missing}")
            rows.append(r)
    return sorted(rows, key=lambda r: r["date"])


def drop_no_igv(rows: list[dict]) -> list[dict]:
    """IGV 미실시 회차를 걸러낸다(담당자 방침). 걸러낸 것은 화면에 남긴다."""
    keep = [r for r in rows if r["igv"]]
    for r in rows:
        if not r["igv"]:
            print(f"  [제외] {r['date']}  IGV Turn-up 미실시 — 보정값 산출 대상 아님")
    if len(keep) != len(rows):
        print(f"  → 입력 {len(rows)}건 중 {len(keep)}건만 검증합니다.\n")
    return keep


def correctors(recs: list[dict]) -> dict:
    """현재 누적으로 세 방법의 보정기를 만든다. 'bin' 은 구간 테이블을 쓰므로 None."""
    pts = [{"cit": r["cit"], "corr": r["corr"]} for r in recs]
    return {"bin": None, "curve": CorrectionCurve(pts), "gp": GPCorrectionCurve(pts)}


def predict(store: MeasurementStore, rec: dict, eng: TheoryEngine) -> dict:
    """반영 전 예측 + 실측 대조. 세 방법 모두."""
    recs = [{"cit": r.cit, "corr": r.corr} for r in store.all()]
    table = store.correction_table()
    corr = correctors(recs)
    inp = SimInput(cit=rec["cit"], pressure=rec["press"], rh=rec["rh"],
                   w=rec["w"], cp_meas=rec["vac"], cc_meas=rec["cc_gross"])
    out = {"date": rec["date"], "n_train": len(recs), "input": inp, "by": {}}
    for m in METHODS:
        out["by"][m] = simulate(inp, engine=eng, records=recs,
                                correction_table=table, corrector=corr[m])
    return out


def show_round(p: dict, rec: dict) -> None:
    any_res = p["by"]["bin"]
    print(f"\n{'=' * 74}\n회차 대상 : {p['date']}    (학습 누적 {p['n_train']}건 — 이 건은 아직 미반영)")
    print(f"{'=' * 74}")
    i = p["input"]
    rh = f"{i.rh:.1f}%" if i.rh is not None else "미입력(60% 가정)"
    print(f"입력   CIT {i.cit:.2f}°C · 대기압 {i.pressure:.1f} mbar"
          f" · RH {rh} · CC실측 {i.cc_meas:.2f} MW · W {any_res.w:+.0f}")
    print(f"구간   {any_res.bin_label} ({any_res.bin_kind}, 이 구간 실측 {any_res.bin_count}건)")

    # ① 계산 일치 — 담당자 표와 같은 입력에 같은 값이 나오는가
    print("\n① 계산 일치 (담당자 표 대조)")
    if rec["ref_theory"] is None and rec["ref_corr"] is None:
        print("   표 값이 입력되지 않아 건너뜀 (ref_theory·ref_corr 열)")
    else:
        for name, ours, ref in (("이론기준값", any_res.theory_base, rec["ref_theory"]),
                                ("보정값", any_res.meas_corr, rec["ref_corr"])):
            if ref is None:
                continue
            d = ours - ref
            mark = "✅" if abs(d) <= THEORY_TOL else "❌"
            print(f"   {mark} {name:<8} 툴 {ours:8.3f}  표 {ref:8.3f}  차 {d:+.3f} MW"
                  f"{'' if abs(d) <= THEORY_TOL else f'  ← 허용차 {THEORY_TOL} 초과'}")

    # ② 예측 정확도 — 방법별
    print("\n② 예측 정확도 (반영 전 예측 vs 실측)")
    print(f"   실측 신고값(Net) {any_res.meas_net:.2f} MW    허용밴드 ±0.5%")
    print(f"   {'방법':<10} {'예측 보정':>9} {'예측 Net':>9} {'실측-예측':>9}  판정")
    for m in METHODS:
        r = p["by"][m]
        verdict = "⚠ 미달" if r.shortfall else ("✅ 밴드 내" if r.in_band else "밴드 위(안전)")
        print(f"   {LABEL[m]:<10} {r.correction:+9.3f} {r.real_net:9.2f} "
              f"{r.net_diff:+9.2f}  {verdict}")
    print(f"   실측 보정값 {any_res.meas_corr:+.3f} MW")

    notes = [n for n in p["by"]["gp"].notes if not n.startswith(("✅", "⚠", "실측이"))]
    for n in notes:
        print(f"   · {n}")


def append_log(path: Path, p: dict, rec: dict) -> None:
    head = ["date", "n_train", "cit", "press", "rh", "cc_gross", "meas_net", "meas_corr"]
    for m in METHODS:
        head += [f"{m}_corr", f"{m}_net", f"{m}_diff", f"{m}_verdict"]
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if new:
            w.writerow(head)
        a = p["by"]["bin"]
        row = [p["date"], p["n_train"], rec["cit"], rec["press"], rec["rh"],
               rec["cc_gross"], round(a.meas_net, 3), round(a.meas_corr, 4)]
        for m in METHODS:
            r = p["by"][m]
            row += [round(r.correction, 4), round(r.real_net, 3), round(r.net_diff, 3),
                    "미달" if r.shortfall else ("밴드내" if r.in_band else "밴드위")]
        w.writerow(row)


def summarize(rounds: list[dict]) -> None:
    if not rounds:
        print("요약할 회차가 없습니다.")
        return
    n = len(rounds)
    print(f"\n{'=' * 74}\n종합 판정 — {n}회차\n{'=' * 74}")
    print(f"{'방법':<10} {'평균오차':>9} {'최대오차':>9} {'밴드 내':>8} {'미달':>6}")
    best = None
    for m in METHODS:
        d = [abs(p["by"][m].net_diff) for p in rounds]
        mae, mx = sum(d) / n, max(d)
        inb = sum(1 for p in rounds if p["by"][m].in_band)
        short = sum(1 for p in rounds if p["by"][m].shortfall)
        print(f"{LABEL[m]:<10} {mae:9.3f} {mx:9.3f} {inb:6d}/{n} {short:5d}건")
        # 미달이 적은 쪽이 우선, 같으면 오차가 작은 쪽
        key = (short, mae)
        if best is None or key < best[0]:
            best = (key, m)
    print("\n판정 기준 : 미달 0건이 최우선(페널티), 그 다음 평균오차")
    print(f"이 {n}건에서는 {LABEL[best[1]]} 가 가장 낫습니다.")
    if best[0][0] > 0:
        print("⚠ 미달이 있습니다 — 안전마진(K=0.8)을 켜고 다시 판단하세요.")
    if n < 6:
        print(f"※ {n}건은 표본이 작습니다. 회차를 더 쌓아 다시 확인하세요.")


def main() -> None:
    ap = argparse.ArgumentParser(description="시운전 — 회차별 예측·대조·반영")
    ap.add_argument("--db", default=str(C.db_path()))
    ap.add_argument("--input", default=None, help="입력 CSV (기본: DB 폴더의 commission_input.csv)")
    ap.add_argument("--init", action="store_true", help="입력 CSV 서식을 만든다")
    ap.add_argument("--walk", action="store_true", help="사본 DB 로 전 회차 미리보기(원본 불변)")
    ap.add_argument("--step", action="store_true", help="다음 1건만 예측·대조")
    ap.add_argument("--apply", action="store_true", help="--step 과 함께: 대조 후 실제 반영")
    ap.add_argument("--report", action="store_true", help="회차 기록 요약")
    ap.add_argument("--deg", type=float, default=C.DEFAULT_DEG)
    a = ap.parse_args()

    db = Path(a.db)
    inp_path = Path(a.input) if a.input else db.parent / "commission_input.csv"
    log_path = db.parent / "commission_log.csv"

    if a.init:
        if inp_path.exists():
            raise SystemExit(f"이미 있습니다: {inp_path}")
        inp_path.write_text(TEMPLATE, encoding="utf-8-sig")
        print(f"입력 서식을 만들었습니다: {inp_path}\n엑셀로 열어 담당자 표를 옮겨 적으세요.")
        return

    if a.report:
        if not log_path.exists():
            raise SystemExit(f"회차 기록이 없습니다: {log_path}")
        print(log_path.read_text(encoding="utf-8-sig"))
        return

    eng = TheoryEngine()
    pending_all = drop_no_igv(load_input(inp_path))

    if a.walk:
        # 원본을 건드리지 않도록 사본에서 돌린다. 회차마다 예측 → 반영 순서를 지킨다.
        tmp = Path(tempfile.mkdtemp()) / db.name
        shutil.copy2(db, tmp)
        store = MeasurementStore(str(tmp))
        print(f"사본 DB 로 미리보기 — 원본은 바뀌지 않습니다\n  원본 {db} ({store.count()}건)")
        rounds = []
        for rec in pending_all:
            if store.has_date(rec["date"]):
                print(f"\n[건너뜀] {rec['date']} 는 이미 누적에 있습니다.")
                continue
            p = predict(store, rec, eng)
            show_round(p, rec)
            rounds.append(p)
            store.add(store.build_record(
                cit=rec["cit"], press=rec["press"], cc_meas=rec["cc_gross"],
                w=rec["w"], rh=rec["rh"], cp_meas=rec["vac"],
                date=rec["date"], engine=eng, deg=a.deg))
        summarize(rounds)
        print(f"\n실제 반영은 회차별로:  python scripts/commission.py --step --apply")
        return

    if not a.step:
        ap.print_help()
        return

    store = MeasurementStore(str(db))
    pending = [r for r in pending_all if not store.has_date(r["date"])]
    if not pending:
        print(f"반영할 회차가 없습니다 (입력 {len(pending_all)}건 모두 누적에 있음).")
        return
    rec = pending[0]
    print(f"누적 DB : {db} ({store.count()}건)   남은 회차 {len(pending)}건")
    p = predict(store, rec, eng)
    show_round(p, rec)

    if not a.apply:
        print(f"\n미리보기입니다(DB 안 바꿈). 반영하려면 --apply 를 붙이세요.")
        return
    store.add(store.build_record(
        cit=rec["cit"], press=rec["press"], cc_meas=rec["cc_gross"], w=rec["w"],
        rh=rec["rh"], cp_meas=rec["vac"], date=rec["date"], engine=eng, deg=a.deg))
    append_log(log_path, p, rec)
    print(f"\n✅ 반영 완료 — 누적 {store.count()}건")
    print(f"   회차 기록 : {log_path}")
    left = len(pending) - 1
    print(f"   남은 회차 {left}건" + ("  → 다시 --step" if left else "  → --walk 로 종합 판정 확인"))


if __name__ == "__main__":
    main()
