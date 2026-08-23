"""누적 기록을 OPC UA 로 재취득해 저장값과 대조 — 읽기 전용(DB 변경 없음).

무엇을 확인하는가
  누적 DB 의 저장값은 담당자가 정리한 엑셀4 실측 기록에서 왔고, 재취득값은
  Tool 이 OPC UA(DataPARC)로 직접 읽은 값이다. 둘이 맞는지 날짜별로 대조한다.

1회차 결과 (2026-08, 32건)
  30건은 ΔCC 최대 0.17 MW · 표준편차 0.056 MW 로 사실상 일치 → Tool 검증 완료.
  나머지 2건만 크게 어긋났다(2026-01-08, 2025-04-15). 전체 표준편차 2.104 MW 는
  이 2건이 전부 만든 값이므로, 평균·표준편차만 보면 오해한다. 중앙값을 함께 본다.

  참고: 2025-10-28 은 담당자 정리 파일이 eDNA 애드인
  (DNAHistGetSingleValue, 태그 RIMS.WR.*)을 써서 CC 가 1.73 MW 낮게 기록된
  예외 건이다. 담당자가 준 다른 5건은 모두 fnTagStat 이고 엑셀1과 일치했다.
  즉 히스토리안이 갈린 게 아니라 그 한 건만 다른 도구로 정리된 것이다.

이상치가 뜨는 흔한 이유
  · 날짜 백필 오배정 — backfill-dates 는 값 근사로 매칭하므로 비슷한 값끼리 바뀔 수 있다
  · 그 날 시험 창이 17:00 이 아니었다 (--start 로 확인)
  · 히스토리안 보존기간을 넘긴 오래된 날짜
  CIT 가 크게 어긋나면 이론기준값이 따라 움직여 보정값이 통째로 달라진다
  (2025-04-15: CIT 25.70→12.70 으로 보정값 -1.51→-30.65).

실행:
    python scripts/source_compare.py --csv 소스대조.csv
    python scripts/source_compare.py --date 2026-01-08 --start 15:00   # 한 건만 창 바꿔 확인
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
from wirye_capacity.theory import TheoryEngine, igv_turnup  # noqa: E402

DEFAULT_DB = str(C.db_path())   # Tool 폴더 기준(공용 해석)
NODEID_CACHE = str(Path.home() / ".wirye_opcua_nodeids.json")

# 이상치 판정 문턱 — 넘으면 '확인 필요'로 따로 모아 보여준다.
TOL_CIT, TOL_CC, TOL_CORR = 0.5, 0.5, 0.5


def hr(t):
    print("\n" + "=" * 104 + f"\n{t}\n" + "=" * 104)


def _f(v, w=8, p=2):
    return f"{'':>{w}}" if v is None else f"{v:>{w}.{p}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=None, help="생략 시 Tool 설정값 사용")
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--start", default="17:00")
    ap.add_argument("--date", default=None, help="이 날짜 한 건만 대조")
    ap.add_argument("--deg", type=float, default=C.DEFAULT_DEG)
    ap.add_argument("--csv", default=None, help="결과를 CSV 로 저장할 경로")
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()

    host = a.host or get_config("opcua_host")
    store = MeasurementStore(a.db)
    recs = [r for r in store.all() if r.date and (not a.date or r.date == a.date)]
    undated = store.count() - len([r for r in store.all() if r.date])
    print(f"누적 {store.count()}건 / 대조 대상 {len(recs)}건"
          + (f" (날짜 없음 {undated}건 제외 — backfill-dates 필요)" if undated else ""))
    if a.limit:
        recs = recs[:a.limit]
    if not recs:
        print("대조할 기록이 없습니다.")
        return 1

    from wirye_capacity.rims.opcua import OpcUaRimsConnector
    conn = OpcUaRimsConnector(host=host, cache_path=NODEID_CACHE)
    eng = TheoryEngine()

    hr(f"날짜별 대조 — 저장값(엑셀4 기록)  vs  재취득({a.start} 창, OPC UA/fnTagStat 기준)")
    print(f"  {'날짜':11}{'CIT저장':>8}{'재취득':>8}{'ΔCIT':>7}"
          f"{'RH저장':>7}{'재취득':>7}"
          f"{'CC저장':>9}{'재취득':>9}{'ΔCC':>7}"
          f"{'이론저장':>9}{'재계산':>9}"
          f"{'보정저장':>8}{'재계산':>8}{'Δ보정':>7}  플래그")
    rows, fails = [], []
    for r in recs:
        try:
            acq = conn.acquire(r.date, a.start)
        except Exception as e:                                   # noqa: BLE001
            fails.append((r.date, repr(e)[:70]))
            print(f"  {r.date:11}  취득 실패 — {repr(e)[:70]}")
            continue
        th2 = eng.theory_cc(acq.cit, acq.pressure, a.deg, rh=acq.rh)
        # W 는 정책상 온도밴드값이므로 재취득 CIT 로 다시 산정한다. 저장된 W 를 물려쓰면
        # CIT 가 크게 바뀐 건(2025-04-15: 25.70→13.69)에서 보정값이 엉뚱하게 나온다.
        w2 = igv_turnup(acq.cit)
        corr2 = correction_value(acq.cc_meas, th2, w2)
        dcit, dcc, dcorr = acq.cit - r.cit, acq.cc_meas - r.cc_meas, corr2 - r.corr
        flag = []
        if abs(dcit) > TOL_CIT:
            flag.append("CIT")
        if abs(dcc) > TOL_CC:
            flag.append("CC")
        if abs(dcorr) > TOL_CORR:
            flag.append("보정")
        if getattr(acq, "warnings", None):
            flag.append("취득경고")
        rows.append({
            "date": r.date, "flag": "/".join(flag),
            "cit_old": r.cit, "cit_new": acq.cit, "d_cit": dcit,
            "press_old": r.press, "press_new": acq.pressure,
            "rh_old": r.rh, "rh_new": acq.rh,
            "cc_old": r.cc_meas, "cc_new": acq.cc_meas, "d_cc": dcc,
            "theory_old": r.theory, "theory_new": th2, "d_theory": th2 - r.theory,
            "corr_old": r.corr, "corr_new": corr2, "d_corr": dcorr,
            "w_old": r.w, "w_new": w2, "warn": ";".join(getattr(acq, "warnings", []) or []),
        })
        print(f"  {r.date:11}{r.cit:>8.2f}{acq.cit:>8.2f}{dcit:>+7.2f}"
              f"{_f(r.rh, 7, 1)}{_f(acq.rh, 7, 1)}"
              f"{r.cc_meas:>9.2f}{acq.cc_meas:>9.2f}{dcc:>+7.2f}"
              f"{r.theory:>9.2f}{th2:>9.2f}"
              f"{r.corr:>+8.2f}{corr2:>+8.2f}{dcorr:>+7.2f}"
              f"  {'/'.join(flag)}")

    if not rows:
        print("\n전부 취득 실패 — 서버 접속·보존기간을 확인하세요.")
        return 1

    ok = [x for x in rows if not x["flag"]]
    bad = [x for x in rows if x["flag"]]

    hr("요약")

    def block(title, data):
        if len(data) < 2:
            print(f"  {title}: {len(data)}건 — 통계 생략")
            return
        for name, key, unit in (("ΔCC 실측", "d_cc", "MW"), ("Δ보정값", "d_corr", "MW"),
                                ("ΔCIT", "d_cit", "°C"), ("Δ이론", "d_theory", "MW")):
            v = [x[key] for x in data]
            print(f"  {title:14}{name:10} 평균 {statistics.mean(v):+7.3f}  "
                  f"중앙 {statistics.median(v):+7.3f}  표준편차 {statistics.stdev(v):6.3f}  "
                  f"최소 {min(v):+7.3f}  최대 {max(v):+7.3f}  {unit}")
        print()

    block(f"전체({len(rows)}건)", rows)
    block(f"정상({len(ok)}건)", ok)

    hr("판정")
    print(f"  대조 성공 {len(rows)}건 / 실패 {len(fails)}건 / 확인 필요 {len(bad)}건")
    if ok and len(ok) > 1:
        v = [abs(x["d_cc"]) for x in ok]
        print(f"\n  ▸ 정상 {len(ok)}건: |ΔCC| 최대 {max(v):.3f} MW, "
              f"표준편차 {statistics.stdev([x['d_cc'] for x in ok]):.3f} MW")
        print("    → 저장값과 재취득값이 사실상 일치한다. Tool 의 OPC UA 취득은 정확하다.")
    if bad:
        print(f"\n  ▸ 확인 필요 {len(bad)}건 — 평균·표준편차를 왜곡하므로 개별 확인:")
        for x in bad:
            print(f"      {x['date']}  [{x['flag']}]  ΔCIT {x['d_cit']:+.2f}°C  "
                  f"ΔCC {x['d_cc']:+.2f} MW  Δ보정 {x['d_corr']:+.2f} MW")
        print("\n    흔한 원인: ① 날짜 백필 오배정(값 근사 매칭이라 비슷한 값끼리 바뀔 수 있음)")
        print("               ② 그 날 시험 창이 17:00 이 아니었음")
        print("               ③ 히스토리안 보존기간 초과")
        print("    확인: python scripts/source_compare.py --date <날짜> --start <다른시각>")
        print("          python scripts/cc_diagnose.py --date <날짜>")
    print("\n  ※ 이 스크립트는 DB 를 바꾸지 않았다. 수정은 delete + add 로 직접 한다.")

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
