"""습도계 2대 교차 대조 — MBL(압축기 흡입부) vs CXM(기상 관측) — 읽기 전용.

두 태그
  10MBL11CM001//XQ01   현재 Tool·엑셀1이 쓰는 태그. 압축기 흡입부 계열.
  10CXM00CM001//XQ01   같은 CXM 계열(대기압 10CXM00CP001, 외기온도 10CXM00CT001)의
                       기상 관측 습도. 물리적으로 50m 내라 완전히 같지는 않아도
                       크게 다를 수 없는 위치.

무엇을 가리려는 것인가
  담당자 원본표의 RH 5일분(02/25·03/04·03/18·03/24·04/02)이 MBL 태그값과 다르다.
  앞선 점검에서 MBL 은 32일 내내 살아 있었지만(표본 985~3788/일, 일변동 22~79%p),
  건조한 날 일최소가 0.0% 까지 내려가 저역이 의심스러웠다.
  두 센서를 붙이면 세 가지가 한 번에 갈린다:
    1) 정상 구간에서 두 센서가 얼마나 붙어 다니는가 → 정상 편차의 크기
    2) 어느 시점부터 벌어지는가                     → MBL 드리프트 시작 시점
    3) 쟁점 5일에 원본표와 가까운 쪽이 어느 센서인가 → 담당자가 쓴 출처

  특히 2026-03-24 는 원본표 41.2% 가 그날 MBL 일최대(26.6%)를 넘었다.
  CXM 이 41 근처면 담당자가 CXM 을 봤다는 뜻이고, 그러면 결론이 확정된다.

실행:
    python scripts/rh_compare.py                              # 17:00 창(시험 조건)
    python scripts/rh_compare.py --window 1440 --start 00:00  # 하루 창(통계 안정)
    python scripts/rh_compare.py --csv 습도대조.csv
"""
from __future__ import annotations

import argparse
import statistics
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wirye_capacity import constants as C  # noqa: E402
from wirye_capacity.config import get_config  # noqa: E402
from wirye_capacity.store import MeasurementStore  # noqa: E402

DEFAULT_DB = str(C.db_path())   # Tool 폴더 기준(공용 해석)
NODEID_CACHE = str(Path.home() / ".wirye_opcua_nodeids.json")

TAGS = {
    "mbl": "10MBL11CM001//XQ01",     # 압축기 흡입부 습도 (현재 사용)
    "cxm": "10CXM00CM001//XQ01",     # 기상 관측 습도 (대조)
    "amb": "10CXM00CT001//XQ01",     # 외기온도 — 통신·수집 정상 확인용 대조군
}

# 담당자 원본표의 17~18시 RH. ★ = MBL 태그값과 불일치한 5일
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

IMPOSSIBLE = 3.0     # 지상 RH 가 이보다 낮게 나오면 센서 문제로 본다


def hr(t):
    print("\n" + "=" * 104 + f"\n{t}\n" + "=" * 104)


def _n(v, w=7, p=1):
    return f"{'-':>{w}}" if v is None else f"{v:>{w}.{p}f}"


def timeavg(client, nodeid, s, e, *, _seen=[]):
    """창 평균 1값. 사내 PC 의 opcua.py 버전에 상관없이 동작해야 한다.

    server_time_average 는 저장소에서 (값, StatusCode) 튜플을 돌려주도록 바뀌었지만,
    사내 PC 는 git 이 없어 패키지를 못 받은 상태라 예전처럼 값만 돌려준다.
    두 형태를 모두 받아들이고, 그마저 실패하면 raw 시간가중평균으로 내려간다.
    (1회차에 이 불일치로 전 항목이 '-' 로 나왔는데, bare except 가 원인을 숨겼다.)
    """
    from wirye_capacity.rims.opcua import server_time_average, time_weighted_average
    try:
        r = server_time_average(client, nodeid, s, e)
        v = r[0] if isinstance(r, tuple) else r
        if v is not None:
            return float(v)
    except Exception as ex:                                      # noqa: BLE001
        if not _seen:
            _seen.append(1)
            print(f"  ! 서버 집계 실패 → raw 평균으로 대체: {type(ex).__name__}: {ex}")
    pts = []
    for dv in client.get_node(nodeid).read_raw_history(s, e):
        ts = getattr(dv, "SourceTimestamp", None) or getattr(dv, "ServerTimestamp", None)
        v = dv.Value.Value if dv.Value is not None else None
        if ts is not None and v is not None:
            pts.append((ts, float(v)))
    return time_weighted_average(pts, s, e)


def raw_stats(client, nodeid, s, e):
    pts = []
    for dv in client.get_node(nodeid).read_raw_history(s, e):
        v = dv.Value.Value if dv.Value is not None else None
        if v is not None:
            pts.append(float(v))
    if not pts:
        return None
    return {"n": len(pts), "min": min(pts), "max": max(pts), "mean": statistics.fmean(pts)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=None)
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--start", default="17:00")
    ap.add_argument("--window", type=int, default=60)
    ap.add_argument("--csv", default=None)
    a = ap.parse_args()

    from wirye_capacity.rims.opcua import OpcUaRimsConnector, _local
    conn = OpcUaRimsConnector(host=a.host or get_config("opcua_host"),
                              cache_path=None, tag_keys=TAGS)   # 캐시 안 씀(태그 구성 다름)
    store = MeasurementStore(a.db)
    dates = sorted({r.date for r in store.all() if r.date})
    store.close()
    if not dates:
        print("날짜 있는 기록이 없습니다.")
        return 1
    print(f"대조 대상 {len(dates)}일   창 {a.start} +{a.window}분")

    client = conn._open_client()
    try:
        conn._resolve_nodeids(client)
        nid = conn.nodeid_map
        for k, t in TAGS.items():
            print(f"  {k:4} {t:24} → {nid.get(k)}")
        if "cxm" not in nid:
            print("\n! CXM 습도 태그를 찾지 못했습니다. 태그명을 확인하세요.")
            return 1

        hr("날짜별 — MBL vs CXM (창 평균은 TimeAverage, 최소/최대는 raw)")
        print(f"  {'날짜':12}{'MBL':>7}{'CXM':>7}{'차':>7}"
              f"{'원본표':>7}{'|MBL-원본|':>11}{'|CXM-원본|':>11}{'가까운쪽':>9}"
              f"  {'MBL최소':>8}{'CXM최소':>8}  비고")
        rows, errors = [], []
        for d in dates:
            s = _local(d, a.start)
            e = s + timedelta(minutes=a.window)
            val, st_ = {}, {}
            for k in ("mbl", "cxm", "amb"):
                if k not in nid:
                    continue
                try:
                    val[k] = timeavg(client, nid[k], s, e)
                    st_[k] = raw_stats(client, nid[k], s, e)
                except Exception as ex:                          # noqa: BLE001
                    val[k], st_[k] = None, None
                    errors.append(f"{d} {k}: {type(ex).__name__}: {ex}")
            m, c, ref = val.get("mbl"), val.get("cxm"), E4_RH.get(d)
            dm = abs(m - ref) if None not in (m, ref) else None
            dc = abs(c - ref) if None not in (c, ref) else None
            closer = ""
            if None not in (dm, dc):
                closer = "CXM" if dc < dm - 0.3 else ("MBL" if dm < dc - 0.3 else "비슷")
            note = []
            if m is not None and m < IMPOSSIBLE:
                note.append("MBL 불가능값")
            if c is not None and c < IMPOSSIBLE:
                note.append("CXM 불가능값")
            if d in DISPUTED:
                note.append("★쟁점")
            rows.append({"date": d, "mbl": m, "cxm": c,
                         "gap": (m - c) if None not in (m, c) else None,
                         "e4": ref, "d_mbl": dm, "d_cxm": dc, "closer": closer,
                         "mbl_min": st_.get("mbl", {}).get("min") if st_.get("mbl") else None,
                         "cxm_min": st_.get("cxm", {}).get("min") if st_.get("cxm") else None,
                         "mbl_n": st_.get("mbl", {}).get("n") if st_.get("mbl") else None,
                         "cxm_n": st_.get("cxm", {}).get("n") if st_.get("cxm") else None,
                         "amb": val.get("amb"), "note": "/".join(note)})
            print(f"  {d:12}{_n(m)}{_n(c)}"
                  + (f"{m - c:>+7.1f}" if None not in (m, c) else f"{'-':>7}")
                  + f"{_n(ref)}{_n(dm, 11, 2)}{_n(dc, 11, 2)}{closer:>9}"
                  + f"  {_n(rows[-1]['mbl_min'], 8)}{_n(rows[-1]['cxm_min'], 8)}  "
                  + "/".join(note))

        if errors:
            print(f"\n  ! 읽기 실패 {len(errors)}건 — 앞 5건:")
            for m_ in errors[:5]:
                print(f"      {m_}")
        if not any(r["mbl"] is not None or r["cxm"] is not None for r in rows):
            print("\n  전 항목 읽기 실패 — 위 오류를 확인하세요. 통계를 낼 수 없습니다.")
            return 1

        ok = [r for r in rows if r["gap"] is not None and r["date"] not in DISPUTED]
        dis = [r for r in rows if r["date"] in DISPUTED and r["gap"] is not None]

        hr("1. 두 센서가 평소 얼마나 붙어 다니는가")
        if len(ok) > 1:
            g = [r["gap"] for r in ok]
            print(f"  일치하는 {len(ok)}일의 (MBL − CXM): 평균 {statistics.fmean(g):+.2f}  "
                  f"중앙 {statistics.median(g):+.2f}  표준편차 {statistics.stdev(g):.2f} %p")
            print(f"      범위 {min(g):+.1f} ~ {max(g):+.1f} %p")
            print("  → 이 폭이 '같은 부지 두 센서의 정상 편차'다. 쟁점일이 이 폭을 크게")
            print("     넘으면 한쪽이 틀린 것이다.")

        hr("2. 시간에 따라 벌어지는가 (드리프트)")
        half = len(ok) // 2
        if half >= 2:
            early, late = ok[:half], ok[half:]
            ge = statistics.fmean([r["gap"] for r in early])
            gl = statistics.fmean([r["gap"] for r in late])
            print(f"  전반 {len(early)}일({early[0]['date']}~{early[-1]['date']}) "
                  f"평균 차 {ge:+.2f} %p")
            print(f"  후반 {len(late)}일({late[0]['date']}~{late[-1]['date']}) "
                  f"평균 차 {gl:+.2f} %p")
            print(f"  변화 {gl - ge:+.2f} %p"
                  + ("   → 후반에 MBL 이 낮아졌다. 드리프트로 볼 근거."
                     if gl - ge < -3 else "   → 뚜렷한 드리프트는 안 보인다."))

        hr("3. 쟁점 5일 — 담당자는 어느 센서를 봤나")
        if dis:
            print(f"  {'날짜':12}{'MBL':>8}{'CXM':>8}{'원본표':>8}"
                  f"{'|MBL-원본|':>11}{'|CXM-원본|':>11}{'가까운쪽':>9}")
            for r in dis:
                print(f"  {r['date']:12}{_n(r['mbl'],8)}{_n(r['cxm'],8)}{_n(r['e4'],8)}"
                      f"{_n(r['d_mbl'],11,2)}{_n(r['d_cxm'],11,2)}{r['closer']:>9}")
            nc = sum(1 for r in dis if r["closer"] == "CXM")
            nm = sum(1 for r in dis if r["closer"] == "MBL")
            print(f"\n  CXM 이 더 가까운 날 {nc}일 / MBL 이 더 가까운 날 {nm}일")
            if nc >= 4:
                print("  → 담당자는 이 5일에 CXM 을 본 것으로 판단된다. 그렇다면 원본표 값이")
                print("     맞고, 우리도 MBL 이 의심스러운 구간에는 CXM 을 써야 한다.")
            elif nm >= 4:
                print("  → CXM 도 원본표와 멀다. 원본표는 제3의 출처(기상청 등)로 보인다.")
            else:
                print("  → 섞여 있다. 날짜별로 개별 판단이 필요하다.")
        if ok:
            nc = sum(1 for r in ok if r["closer"] == "MBL")
            print(f"\n  참고: 일치하는 {len(ok)}일 중 MBL 이 더 가까운 날 {nc}일 "
                  f"— 평소엔 담당자가 MBL 을 썼다는 확인")

        hr("4. 불가능값 출현")
        for k, lab in (("mbl_min", "MBL"), ("cxm_min", "CXM")):
            bad = [r["date"] for r in rows if r[k] is not None and r[k] < IMPOSSIBLE]
            print(f"  {lab} 창 최소가 {IMPOSSIBLE}% 미만인 날: "
                  + (f"{len(bad)}일 — " + ", ".join(bad) if bad else "없음"))
        print("\n  ※ DB 를 바꾸지 않았다. 결론이 나면 fix_records.py 에 반영한다.")

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
