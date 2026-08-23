"""CC 실측 불일치 진단 — 사내 PC에서 실행 (읽기 전용).

증상(2025-10-28 17:00): Tool(OPC UA) CC실측 454.10 vs 엑셀1(fnTagStat) 452.3669
                       → +1.73 MW. 같은 창의 CIT·대기압은 일치.

CIT·대기압이 맞는데 CC만 틀리다는 건 '시간창/시간대/집계함수'가 아니라
'그 태그의 데이터 자체' 또는 '집계 품질' 문제라는 뜻이다. 이 스크립트는
한 번 실행으로 아래를 모두 찍어 원인을 좁힌다.

  1) 서버측 TimeAverage 값 + StatusCode      ← Tool 이 실제로 쓰는 값
     (StatusCode 가 Uncertain/SubNormal 이면 구간에 결측·불량이 있다는 신호)
  2) raw 히스토리 표본 개수·처음/끝 타임스탬프·min/max·불량표본 수
  3) 우리 폴백 계산(시간가중평균)과 단순평균 — 세 값이 벌어지면 데이터가 튄 것
  4) GT + ST 합 vs CC Load 태그          ← 엑셀1 CC 셀이 합산식일 가능성 검증
  5) 창을 ±5·±60분 옮겨본 값             ← 시간창 오정렬 여부 확인

실행:
    python scripts/cc_diagnose.py --host <서버이름> --date 2025-10-28 --start 17:00
    python scripts/cc_diagnose.py opc.tcp://<서버>:51236/Capstone/UAServer --date 2025-10-28

출력에 서버주소가 보이면 공유 전에 가려주세요.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wirye_capacity.config import get_config  # noqa: E402
from wirye_capacity.rims.opcua import (  # noqa: E402
    AGG_TIME_AVERAGE, CORE_TAGS, SITE_PATH, SITE_PORTS, _tcp_open,
    time_weighted_average,
)

# 엑셀1(fnTagStat) 기준값을 알고 있으면 여기에 적으면 자동 대조한다.
KNOWN = {
    "2025-10-28 17:00": {"cc_meas": 452.3669},
}


def hr(t):
    print("\n" + "=" * 74 + f"\n{t}\n" + "=" * 74)


def _loc(dt):
    """히스토리안 타임스탬프를 로컬(KST)로 바꿔 표시한다.

    asyncua 는 UTC 로 돌려주므로 그대로 찍으면 17:00~18:00 창이 08:00~09:00 으로
    보여 '창이 어긋난 것처럼' 읽힌다(2025-10-28 진단 1회차에서 실제로 그랬다).
    """
    if dt is None:
        return "?"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone()


def _local(date, hhmm):
    return datetime.strptime(f"{date} {hhmm}", "%Y-%m-%d %H:%M").astimezone()


def open_client(target, timeout=15):
    from asyncua.sync import Client
    eps = ([target] if target.startswith("opc.tcp://")
           else [f"opc.tcp://{target}:{p}{SITE_PATH}" for p in SITE_PORTS])
    errs = []
    for ep in eps:
        if not _tcp_open(ep):
            errs.append(f"{ep}: 포트 닫힘")
            continue
        c = Client(ep, timeout=timeout)
        try:
            c.connect()
            print(f"접속 성공: {ep}")
            return c
        except Exception as e:                                   # noqa: BLE001
            errs.append(f"{ep}: {e!r}")
    raise SystemExit("접속 실패 — " + " / ".join(errs))


def resolve(client, keys):
    """BrowseName BFS 로 field→NodeId 해결 (opcua.py 와 동일 방식)."""
    from collections import deque

    from asyncua import ua
    remaining = {k.lower(): f for f, k in keys.items()}
    out, dq, visited, seen = {}, deque([client.nodes.objects]), set(), 0
    while dq and remaining and seen < 300000:
        node = dq.popleft()
        seen += 1
        try:
            descs = node.get_children_descriptions()
        except Exception:                                        # noqa: BLE001
            continue
        for d in descs:
            bn = (d.BrowseName.Name or "").lower()
            for key in list(remaining):
                if key in bn:
                    nid = ua.NodeId(d.NodeId.Identifier, d.NodeId.NamespaceIndex,
                                    d.NodeId.NodeIdType)
                    out[remaining.pop(key)] = nid.to_string()
                    break
            if d.NodeClass.name in ("Object", "View"):
                nid = ua.NodeId(d.NodeId.Identifier, d.NodeId.NamespaceIndex,
                                d.NodeId.NodeIdType)
                if nid.to_string() not in visited:
                    visited.add(nid.to_string())
                    dq.append(client.get_node(nid))
    if remaining:
        print("  ! 해결 실패:", ", ".join(remaining.values()))
    return out


def timeavg_with_status(client, nodeid, s, e):
    """서버 TimeAverage — 값과 StatusCode 를 함께 돌려준다(Tool 은 값만 쓴다)."""
    from asyncua import ua
    node = client.get_node(nodeid)
    det = ua.ReadProcessedDetails()
    det.StartTime, det.EndTime = s, e
    det.ProcessingInterval = (e - s).total_seconds() * 1000.0
    det.AggregateType = [ua.NodeId(AGG_TIME_AVERAGE)]
    ac = ua.AggregateConfiguration()
    ac.UseServerCapabilitiesDefaults = True
    det.AggregateConfiguration = ac
    res = node.history_read(det)
    dvs = res.HistoryData.DataValues
    if not dvs:
        return None, "결과 없음"
    dv = dvs[0]
    val = dv.Value.Value if dv.Value is not None else None
    sc = getattr(dv, "StatusCode", None)
    return val, (sc.name if hasattr(sc, "name") else str(sc))


def raw_stats(client, nodeid, s, e):
    node = client.get_node(nodeid)
    hist = node.read_raw_history(s, e)
    pts, bad = [], 0
    for dv in hist:
        ts = getattr(dv, "SourceTimestamp", None) or getattr(dv, "ServerTimestamp", None)
        v = dv.Value.Value if dv.Value is not None else None
        sc = getattr(dv, "StatusCode", None)
        if sc is not None and hasattr(sc, "is_good") and not sc.is_good():
            bad += 1
        if ts is not None and v is not None:
            pts.append((ts, float(v)))
    if not pts:
        return None
    vs = [v for _, v in pts]
    return {
        "n": len(pts), "bad": bad,
        "first": min(t for t, _ in pts), "last": max(t for t, _ in pts),
        "min": min(vs), "max": max(vs),
        "twa": time_weighted_average(pts, s, e),
        "mean": sum(vs) / len(vs),
        "buckets": _buckets(pts, s, e),
    }


def _buckets(pts, s, e, minutes=10):
    """10분 구간별 시간가중평균 — 창 안에서 값이 어느 방향으로 움직였는지 본다."""
    out = []
    t = s
    while t < e:
        nxt = min(t + timedelta(minutes=minutes), e)
        out.append((t, time_weighted_average(
            [(ts, v) for ts, v in pts if t <= ts < nxt] or pts, t, nxt)))
        t = nxt
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("endpoint", nargs="?", default=None)
    ap.add_argument("--host", help="생략 시 Tool 이 쓰는 설정값(~/.wirye_tool.json 의 "
                                  "opcua_host, 없으면 내장 기본값)을 그대로 사용")
    ap.add_argument("--date", required=True)
    ap.add_argument("--start", default="17:00")
    ap.add_argument("--window", type=int, default=60)
    a = ap.parse_args()
    # 서버이름을 외우지 않아도 되게, Tool 과 같은 경로로 해결한다.
    target = a.endpoint or a.host or get_config("opcua_host")
    if not target:
        raise SystemExit("--host 또는 엔드포인트를 지정하세요.")
    if not (a.endpoint or a.host):
        print(f"서버: {target}  (설정값 사용 — 다르면 --host 로 지정)")

    s = _local(a.date, a.start)
    e = s + timedelta(minutes=a.window)
    print(f"창: {s:%Y-%m-%d %H:%M %z} ~ {e:%H:%M}  ({a.window}분)")

    client = open_client(target)
    try:
        hr("1. 태그 해결")
        nid = resolve(client, CORE_TAGS)
        for f, v in nid.items():
            print(f"  {f:10} {CORE_TAGS[f]:24} → {v}")

        hr("2. 서버 TimeAverage (Tool 이 쓰는 값) + StatusCode")
        srv = {}
        for f in CORE_TAGS:
            if f not in nid:
                continue
            try:
                v, sc = timeavg_with_status(client, nid[f], s, e)
            except Exception as ex:                              # noqa: BLE001
                v, sc = None, f"예외 {ex!r}"
            srv[f] = v
            flag = "" if sc == "Good" else "   <<< 확인 필요"
            print(f"  {f:10} {('%.4f' % v) if v is not None else '없음':>12}   status={sc}{flag}")

        hr("3. raw 히스토리 통계 + 우리 폴백 계산")
        print(f"  {'태그':10} {'표본':>5} {'불량':>4} {'최소':>10} {'최대':>10} "
              f"{'시간가중평균':>12} {'단순평균':>10}  처음~끝")
        for f in CORE_TAGS:
            if f not in nid:
                continue
            try:
                st = raw_stats(client, nid[f], s, e)
            except Exception as ex:                              # noqa: BLE001
                print(f"  {f:10} 예외 {ex!r}")
                continue
            if not st:
                print(f"  {f:10} raw 없음")
                continue
            print(f"  {f:10} {st['n']:>5} {st['bad']:>4} {st['min']:>10.3f} "
                  f"{st['max']:>10.3f} {st['twa']:>12.4f} {st['mean']:>10.4f}  "
                  f"{_loc(st['first']):%H:%M:%S}~{_loc(st['last']):%H:%M:%S}")
            if srv.get(f) is not None and st["twa"] is not None:
                d = srv[f] - st["twa"]
                if abs(d) > 0.05:
                    print(f"             ^ 서버집계 − 시간가중평균 = {d:+.4f} "
                          f"<<< 두 계산이 다름")
            if f == "cc_meas" and st.get("buckets"):
                seg = "  ".join(f"{t:%H:%M} {v:.2f}" for t, v in st["buckets"]
                                if v is not None)
                print(f"             10분 구간별: {seg}")

        hr("4. GT + ST 합 vs CC Load 태그")
        gt, st_, cc = srv.get("gt_meas"), srv.get("st_meas"), srv.get("cc_meas")
        if None not in (gt, st_, cc):
            print(f"  GT {gt:.4f} + ST {st_:.4f} = {gt + st_:.4f}")
            print(f"  CC Load 태그              = {cc:.4f}")
            print(f"  차이                       = {cc - (gt + st_):+.4f} MW")
            print("  (2026-05-05 애드인 기준 이 차이는 +0.1102 MW 였다. "
                  "여기서 1 MW 이상 벌어지면 엑셀1 CC 셀이 합산식일 가능성)")
        ref = KNOWN.get(f"{a.date} {a.start}", {})
        if ref.get("cc_meas") is not None and cc is not None:
            print(f"\n  엑셀1(fnTagStat) 기준값     = {ref['cc_meas']:.4f}")
            print(f"  Tool(CC Load 태그) − 엑셀1  = {cc - ref['cc_meas']:+.4f} MW")
            if None not in (gt, st_):
                print(f"  (GT+ST) − 엑셀1             = {gt + st_ - ref['cc_meas']:+.4f} MW"
                      "   ← 0 에 가까우면 원인 확정: 엑셀1 CC = GT+ST")

        hr("5. 창을 옮겨본 CC 값 (시간창 오정렬 확인)")
        if "cc_meas" in nid:
            offsets = list(range(-40, 25, 5)) + [-60, 60]
            best = None
            for off in sorted(offsets):
                s2 = s + timedelta(minutes=off)
                e2 = s2 + timedelta(minutes=a.window)
                try:
                    v, sc = timeavg_with_status(client, nid["cc_meas"], s2, e2)
                except Exception as ex:                          # noqa: BLE001
                    print(f"  {off:+4d}분  예외 {ex!r}")
                    continue
                mark = ""
                if v is not None and ref.get("cc_meas") is not None:
                    if abs(v - ref["cc_meas"]) < 0.01:
                        mark = "   <<< 엑셀1 값과 일치! 창이 어긋난 것"
                print(f"  {off:+4d}분  {s2:%H:%M}~{e2:%H:%M}  "
                      f"{('%.4f' % v) if v is not None else '없음':>12}  {sc}{mark}")
                if v is not None and ref.get("cc_meas") is not None:
                    gap = abs(v - ref["cc_meas"])
                    if best is None or gap < best[1]:
                        best = (off, gap, v)
            if best is not None:
                print(f"\n  엑셀1 값({ref['cc_meas']:.4f})에 가장 가까운 창: "
                      f"{best[0]:+d}분 → {best[2]:.4f} (차 {best[1]:.4f} MW)")
                if best[1] > 0.05:
                    print("  어떤 오프셋도 딱 맞지 않음 → 단순한 시간창 밀림이 아니다.")
    finally:
        client.disconnect()

    hr("판정 가이드")
    print("""  · 2번 status 가 Good 이 아니다        → 구간에 결측/불량. 엑셀1 은 그걸 빼고
                                            평균했고 우리는 포함했을 가능성.
  · 3번 서버집계 ≠ 시간가중평균          → 서버 집계 설정(보간/경계값) 차이.
  · 4번 (GT+ST) − 엑셀1 ≈ 0             → 엑셀1 CC 셀이 GT+ST 합산식. 태그를 바꿔야 함.
  · 5번 특정 오프셋에서 엑셀1 값 일치    → 시간창 정의 차이(예: 16~17시 / 종료시각 포함).
  · 전부 해당 없음                      → 엑셀1 CC 셀의 수식을 직접 확인해야 한다
                                            (셀 클릭 → 수식 입력줄).""")


if __name__ == "__main__":
    main()
