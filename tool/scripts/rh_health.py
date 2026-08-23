"""상대습도 센서(10MBL11CM001) 건전성 점검 — 읽기 전용.

왜 필요한가
  담당자 원본표의 RH 5일분(02/25·03/04·03/18·03/24·04/02)이 히스토리안 태그값과
  다르다. 태그값(0.1·9.7·36.8·9.1·0.0)이 실제로 그 태그에서 나온다는 건 엑셀1로
  확인됐다. 그렇다면 남은 질문은 하나다 —
      "태그가 맞고 담당자가 잘못 넣은 것" 인가,
      "센서가 고장나서 담당자가 다른 출처로 바로잡은 것" 인가.

어떻게 판별하는가
  고장난 센서는 값만 이상해지지 않고 '신호의 성격'이 바뀐다.
    · 변동폭 붕괴 : 정상 습도는 한 시간에도 수~수십 %p 움직인다. 평평해지면 이상.
    · 표본 수 붕괴 : 히스토리안은 변화가 있을 때만 저장(압축)한다. 안 움직이면 표본이 준다.
    · 물리적 불가능값 : 지상 RH 5% 미만은 사실상 없다.
  이미 확인된 대비:
      2025-10-28  표본 183  범위 19.5~37.1 (17.6%p)   ← 정상
      2026-01-08  표본  34  범위  5.2~ 6.7 ( 1.4%p)   ← 의심
  같은 창의 외기온도(10CXM00CT001) 표본·변동폭을 함께 뽑아 대조군으로 쓴다.
  외기온도는 정상인데 RH 만 평평하면 RH 센서 문제로 특정된다.

주의 — 우리 코드의 유효범위 검사로는 못 잡는다
  rims/opcua.py 는 RH 5~100% 밖이면 60% 고정으로 폴백한다. 0.0·0.1 은 걸리지만
  9.7·36.8·9.1 은 '유효'로 통과한다. 센서가 살아서 틀린 값을 주는 구간은
  범위 검사로 잡을 수 없다. 이 점검이 필요한 이유다.

실행:
    python scripts/rh_health.py                    # 누적 날짜 전부, 17:00 창
    python scripts/rh_health.py --window 1440 --start 00:00   # 하루 전체로 더 확실히
    python scripts/rh_health.py --csv rh점검.csv
"""
from __future__ import annotations

import argparse
import statistics
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wirye_capacity.config import get_config  # noqa: E402
from wirye_capacity.store import MeasurementStore  # noqa: E402

DEFAULT_DB = str(Path.home() / "wirye_measurements.db")
NODEID_CACHE = str(Path.home() / ".wirye_opcua_nodeids.json")

RH_TAG = "10MBL11CM001//XQ01"        # 상대습도 (%)
AMB_TAG = "10CXM00CT001//XQ01"       # 외기온도 (°C) — 대조군

# 담당자 원본표의 RH (히스토리안과 다른 5건은 ★)
E4_RH = {
    "2025-04-15": 35.4, "2025-07-09": 39.7, "2025-07-22": 49.6, "2025-07-29": 52.8,
    "2025-08-05": 47.0, "2025-08-12": 36.0, "2025-08-19": 49.3, "2025-08-21": 38.0,
    "2025-08-27": 49.1, "2025-09-02": 50.0, "2025-09-09": 51.8, "2025-09-18": 49.9,
    "2025-09-23": 44.0, "2025-10-14": 62.8, "2025-10-21": 49.1, "2025-10-28": 24.0,
    "2025-11-04": 33.2, "2025-11-11": 33.4, "2025-11-20": 29.9, "2025-11-26": 32.5,
    "2025-12-02": 8.2, "2026-01-06": 23.0, "2026-01-08": 5.8, "2026-01-13": 13.9,
    "2026-02-04": 38.5, "2026-02-12": 33.6, "2026-02-24": 17.2,
    "2026-02-25": 18.2, "2026-03-04": 35.4, "2026-03-18": 67.6,   # ★
    "2026-03-24": 41.2, "2026-04-02": 27.6,                        # ★
}
DISPUTED = {"2026-02-25", "2026-03-04", "2026-03-18", "2026-03-24", "2026-04-02"}

# 문턱은 창 길이에 비례해야 한다 — 1시간 기준을 하루(1440분)에 그대로 쓰면 전부 정상으로
# 보인다(표본이 24배 많으니까). --window 에 맞춰 환산한다.
FLAT_PER_HOUR = 3.0       # 시간당 변동폭이 이보다 작으면 '평평'
SAMPLES_PER_HOUR = 60     # 시간당 표본이 이보다 적으면 '표본 적음'
FLAT_CAP = 12.0           # 하루 창이라도 이 이상 요구하지는 않는다(일변화 폭 감안)


def thresholds(window_min: int):
    h = max(window_min / 60.0, 1.0)
    return min(FLAT_PER_HOUR * (h ** 0.5), FLAT_CAP), SAMPLES_PER_HOUR * h


def hr(t):
    print("\n" + "=" * 100 + f"\n{t}\n" + "=" * 100)


def stats_for(client, nodeid, s, e):
    node = client.get_node(nodeid)
    pts = []
    for dv in node.read_raw_history(s, e):
        v = dv.Value.Value if dv.Value is not None else None
        if v is not None:
            pts.append(float(v))
    if not pts:
        return None
    return {"n": len(pts), "min": min(pts), "max": max(pts),
            "rng": max(pts) - min(pts), "mean": statistics.fmean(pts)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=None)
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--start", default="17:00")
    ap.add_argument("--window", type=int, default=60, help="분 단위 (1440 = 하루)")
    ap.add_argument("--csv", default=None)
    a = ap.parse_args()

    from wirye_capacity.rims.opcua import OpcUaRimsConnector, _local
    conn = OpcUaRimsConnector(host=a.host or get_config("opcua_host"),
                              cache_path=NODEID_CACHE,
                              tag_keys={"rh": RH_TAG, "amb": AMB_TAG})
    store = MeasurementStore(a.db)
    dates = sorted({r.date for r in store.all() if r.date})
    store.close()
    if not dates:
        print("날짜 있는 기록이 없습니다.")
        return 1
    flat_tol, low_n = thresholds(a.window)
    print(f"점검 대상 {len(dates)}일   창 {a.start} +{a.window}분")
    print(f"판정 문턱: 변동폭 < {flat_tol:.1f} %p 면 '평평', 표본 < {low_n:.0f} 개면 '표본적음'")

    client = conn._open_client()
    try:
        conn._resolve_nodeids(client)
        nid = conn.nodeid_map
        print(f"RH  태그 {RH_TAG} → {nid.get('rh')}")
        print(f"외기 태그 {AMB_TAG} → {nid.get('amb')}")

        hr("날짜별 — RH 신호의 성격 (표본 수·변동폭이 붕괴하면 센서 이상)")
        print(f"  {'날짜':12}{'RH표본':>7}{'RH최소':>8}{'RH최대':>8}{'변동폭':>7}{'RH평균':>8}"
              f"{'원본표':>7}{'차':>7}   {'외기표본':>8}{'외기변동':>8}  판정")
        rows = []
        for d in dates:
            s = _local(d, a.start)
            e = s + timedelta(minutes=a.window)
            try:
                rh = stats_for(client, nid["rh"], s, e)
                amb = stats_for(client, nid["amb"], s, e)
            except Exception as ex:                              # noqa: BLE001
                print(f"  {d:12}  실패 {ex!r}")
                continue
            if rh is None:
                print(f"  {d:12}  RH raw 없음")
                continue
            ref = E4_RH.get(d)
            diff = (ref - rh["mean"]) if ref is not None else None
            verdict = []
            if rh["mean"] < 5.0:
                verdict.append("불가능값")
            if rh["rng"] < flat_tol:
                verdict.append("평평")
            if rh["n"] < low_n:
                verdict.append("표본적음")
            if amb and amb["rng"] >= 0.5 and rh["rng"] < flat_tol:
                verdict.append("외기는정상")
            if d in DISPUTED:
                verdict.append("★원본표불일치")
            rows.append({"date": d, "rh_n": rh["n"], "rh_min": rh["min"], "rh_max": rh["max"],
                         "rh_rng": rh["rng"], "rh_mean": rh["mean"], "e4_rh": ref,
                         "diff": diff, "amb_n": amb["n"] if amb else None,
                         "amb_rng": amb["rng"] if amb else None,
                         "verdict": "/".join(verdict)})
            print(f"  {d:12}{rh['n']:>7}{rh['min']:>8.1f}{rh['max']:>8.1f}{rh['rng']:>7.1f}"
                  f"{rh['mean']:>8.1f}"
                  + (f"{ref:>7.1f}" if ref is not None else f"{'-':>7}")
                  + (f"{diff:>+7.1f}" if diff is not None else f"{'-':>7}")
                  + (f"{amb['n']:>8}{amb['rng']:>8.1f}" if amb else f"{'-':>8}{'-':>8}")
                  + f"  {'/'.join(verdict)}")

        if not rows:
            print("\n수집된 데이터가 없습니다.")
            return 1

        hr("판정")
        bad = [r for r in rows if any(k in r["verdict"] for k in ("불가능값", "평평", "표본적음"))]
        good = [r for r in rows if r not in bad]
        if good:
            print(f"  정상으로 보이는 {len(good)}일: 표본 중앙 "
                  f"{statistics.median([r['rh_n'] for r in good]):.0f}, "
                  f"변동폭 중앙 {statistics.median([r['rh_rng'] for r in good]):.1f} %p")
        if bad:
            print(f"  이상 징후 {len(bad)}일: 표본 중앙 "
                  f"{statistics.median([r['rh_n'] for r in bad]):.0f}, "
                  f"변동폭 중앙 {statistics.median([r['rh_rng'] for r in bad]):.1f} %p")
            print("    " + ", ".join(r["date"] for r in bad))
            first = min(r["date"] for r in bad)
            print(f"\n  이상이 처음 나타난 날: {first}")
            after = [r for r in rows if r["date"] >= first]
            n_bad = sum(1 for r in after if r in bad)
            print(f"  그 날 이후 {len(after)}일 중 {n_bad}일이 이상 "
                  f"({n_bad/len(after)*100:.0f}%)")
            if n_bad / len(after) > 0.6:
                print("  → 특정 시점부터 계속 이상하다. 센서 고장으로 보는 게 타당하고,")
                print("     그렇다면 담당자가 다른 출처로 바로잡은 원본표 값이 맞다.")
            else:
                print("  → 산발적이다. 센서 상시 고장이라기보다 그 날들만의 문제일 수 있다.")
        dis = [r for r in rows if r["date"] in DISPUTED]
        if dis:
            print(f"\n  원본표와 다른 5일의 신호 성격:")
            for r in dis:
                print(f"    {r['date']}  표본 {r['rh_n']:>4}  변동폭 {r['rh_rng']:>5.1f} %p  "
                      f"태그평균 {r['rh_mean']:>5.1f}  원본표 {r['e4_rh']:>5.1f}  "
                      f"[{r['verdict']}]")
        print("\n  ※ 우리 코드의 유효범위(5~100%)는 0.0·0.1 만 걸러낸다. 9.7·36.8·9.1 처럼")
        print("     '살아서 틀린' 값은 통과하므로, 고장 구간이 확인되면 별도 처리가 필요하다.")

        if a.csv:
            import csv
            with open(a.csv, "w", encoding="utf-8-sig", newline="") as f:
                wr = csv.DictWriter(f, fieldnames=list(rows[0]))
                wr.writeheader()
                wr.writerows(rows)
            print(f"\n  CSV 저장: {a.csv}")
    finally:
        client.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
