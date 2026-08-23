"""누적 32건을 OPC UA(fnTagStat 기준)로 재취득해 저장값과 대조 — 읽기 전용.

배경 (2025-10-28 조사 결론)
  과거 실적을 정리한 담당자 파일은 eDNA 애드인을 쓴다:
      =@'…\\eDNA Data Tool.xla'!DNAHistGetSingleValue($AD17,"avg",AG$9,AG$10,"1h")
      태그: RIMS.WR.10MBY10CE901//XQ01        → CC 452.3669
  우리가 받은 엑셀1은 RiMS fnTagStat(DataPARC)을 쓴다:
      =@fnTagStat(AD17, AG9, AG10, "TimeAvg")
      태그: WR.PB.10MBY10CE901////XQ01        → CC 454.0959
  Tool(OPC UA)은 엑셀1과 소수점 4자리까지 일치한다. 즉 우리 구현은 정확하고,
  '누적 32건이 다른 히스토리안에서 나왔다'는 것이 문제다.

  같은 날 CC = GT+ST 정합성:
      fnTagStat : 295.2690 + 158.7982 = 454.0672  vs CC 454.0959  (+0.03)
      eDNA      : 295.3414 + 158.3559 = 453.6973  vs CC 452.3669  (−1.33)
  CC Gross 는 정의상 GT+ST 이므로 fnTagStat 쪽이 물리적으로 정합적이다.

이 스크립트는 아무것도 바꾸지 않는다. 32건 전부의 편차를 재서
'상수 편차인가(단순 보정 가능) / 날짜마다 다른가(eDNA 압축 잡음)'를 판정한다.
편차가 날짜마다 다르면, 지금 모델이 물리 산포로 학습하던 것 중 일부가
히스토리안 압축 오차였다는 뜻이다.

실행:
    python scripts/source_compare.py                    # 기본 DB, 17:00 창
    python scripts/source_compare.py --csv 대조.csv      # 표를 CSV 로도 저장
"""
from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wirye_capacity import constants as C  # noqa: E402
from wirye_capacity.config import get_config  # noqa: E402
from wirye_capacity.correction import correction_value  # noqa: E402
from wirye_capacity.store import MeasurementStore  # noqa: E402
from wirye_capacity.theory import TheoryEngine  # noqa: E402

DEFAULT_DB = str(Path.home() / "wirye_measurements.db")
NODEID_CACHE = str(Path.home() / ".wirye_opcua_nodeids.json")


def hr(t):
    print("\n" + "=" * 96 + f"\n{t}\n" + "=" * 96)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=None, help="생략 시 Tool 설정값 사용")
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--start", default="17:00")
    ap.add_argument("--deg", type=float, default=C.DEFAULT_DEG)
    ap.add_argument("--csv", default=None, help="결과를 CSV 로 저장할 경로")
    ap.add_argument("--limit", type=int, default=None, help="앞 N건만 (시험용)")
    a = ap.parse_args()

    host = a.host or get_config("opcua_host")
    store = MeasurementStore(a.db)
    recs = [r for r in store.all() if r.date]
    undated = store.count() - len(recs)
    print(f"누적 {store.count()}건 중 날짜 있는 {len(recs)}건 대조"
          + (f" (날짜 없음 {undated}건은 건너뜀 — backfill-dates 필요)" if undated else ""))
    if a.limit:
        recs = recs[:a.limit]
    if not recs:
        print("대조할 기록이 없습니다.")
        return 1

    from wirye_capacity.rims.opcua import OpcUaRimsConnector
    conn = OpcUaRimsConnector(host=host, cache_path=NODEID_CACHE)
    eng = TheoryEngine()

    hr("날짜별 대조 (저장값 = eDNA 기준 / 재취득 = fnTagStat 기준)")
    print(f"  {'날짜':12}{'CIT 저장':>9}{'재취득':>9}{'Δ':>7}"
          f"{'CC 저장':>10}{'재취득':>10}{'ΔCC':>8}"
          f"{'보정 저장':>10}{'재계산':>9}{'Δ보정':>8}  경고")
    rows, fails = [], []
    for r in recs:
        try:
            acq = conn.acquire(r.date, a.start)
        except Exception as e:                                   # noqa: BLE001
            fails.append((r.date, repr(e)[:60]))
            print(f"  {r.date:12}  취득 실패 — {repr(e)[:60]}")
            continue
        rh = acq.rh
        th2 = eng.theory_cc(acq.cit, acq.pressure, a.deg, rh=rh)
        corr2 = correction_value(acq.cc_meas, th2, r.w)
        warn = ";".join(getattr(acq, "warnings", []) or [])
        rows.append({
            "date": r.date,
            "cit_old": r.cit, "cit_new": acq.cit,
            "press_old": r.press, "press_new": acq.pressure,
            "rh_old": r.rh, "rh_new": rh,
            "cc_old": r.cc_meas, "cc_new": acq.cc_meas,
            "theory_old": r.theory, "theory_new": th2,
            "corr_old": r.corr, "corr_new": corr2,
            "w": r.w, "warn": warn,
        })
        print(f"  {r.date:12}{r.cit:>9.2f}{acq.cit:>9.2f}{acq.cit - r.cit:>+7.2f}"
              f"{r.cc_meas:>10.2f}{acq.cc_meas:>10.2f}{acq.cc_meas - r.cc_meas:>+8.2f}"
              f"{r.corr:>+10.2f}{corr2:>+9.2f}{corr2 - r.corr:>+8.2f}"
              f"  {warn[:28]}")

    if not rows:
        print("\n전부 취득 실패 — 서버 접속/보존기간을 확인하세요.")
        return 1

    dcc = [x["cc_new"] - x["cc_old"] for x in rows]
    dco = [x["corr_new"] - x["corr_old"] for x in rows]
    dci = [x["cit_new"] - x["cit_old"] for x in rows]

    hr("요약")
    def stat(name, v, unit="MW"):
        sd = statistics.stdev(v) if len(v) > 1 else 0.0
        print(f"  {name:14} 평균 {statistics.mean(v):+7.3f}  중앙 "
              f"{statistics.median(v):+7.3f}  표준편차 {sd:6.3f}  "
              f"최소 {min(v):+7.3f}  최대 {max(v):+7.3f}  {unit}")
    stat("ΔCC 실측", dcc)
    stat("Δ보정값", dco)
    stat("ΔCIT", dci, "°C")

    sd_cc = statistics.stdev(dcc) if len(dcc) > 1 else 0.0
    hr("판정")
    print(f"  대조 성공 {len(rows)}건 / 실패 {len(fails)}건")
    if sd_cc < 0.3:
        print(f"  ΔCC 표준편차 {sd_cc:.3f} MW — 거의 일정한 편차다.")
        print(f"  → 두 히스토리안의 계통 차이. 상수 {statistics.mean(dcc):+.3f} MW 로 "
              "환산하거나, 소스만 통일하면 산포는 늘지 않는다.")
    else:
        print(f"  ΔCC 표준편차 {sd_cc:.3f} MW — 날짜마다 편차가 다르다.")
        print("  → eDNA 압축 오차가 날짜별로 다르게 섞여 있었다는 뜻이다. 지금까지 모델이")
        print("     '물리 산포'로 학습해 온 것 중 이만큼이 측정 잡음이었을 수 있다.")
        print(f"     (참고: 현재 GP 예측오차 1.24 MW, 추정 불가피 잡음 1.20~1.52 MW)")
    print("\n  ※ 이 스크립트는 DB를 바꾸지 않았다. 소스를 어느 쪽으로 통일할지는")
    print("     담당자·조교와 합의가 필요한 사안이다(공식 실적 기록이 eDNA 기준).")

    if a.csv:
        import csv
        with open(a.csv, "w", encoding="utf-8-sig", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=list(rows[0]))
            wr.writeheader()
            wr.writerows(rows)
        print(f"\n  CSV 저장: {a.csv}")
    store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
