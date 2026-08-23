"""누적 기록 정정 — 기본은 미리보기(dry-run), --apply 로만 실제 변경.

정정 대상 (2026-08 원본표 대조 결과)
  담당자 실적표(2026-07-29 수령)와 히스토리안이 서로 일치하는데 우리 DB 만
  다른 기록을 갖고 있던 2건. 근거가 확정된 것만 넣는다.

    2025-04-15  DB: CIT 25.70 / CC 411.51   →  정답: CIT 13.69 / CC 438.10
                이 날만 Data 취득창이 16:00~17:00 이다(Test 종료도 17:00).
                17:00 창으로 읽으면 시험 종료 후 감발 구간이 섞여 409.95 가 나온다.
    2026-01-08  DB: CIT  6.90 / CC 460.70   →  정답: CIT -1.45 / CC 472.49
                히스토리안 17:00 창이 원본표(-1.5 / 472.5)와 일치. GT+ST 정합.

  값은 코드에 박아 넣지 않고 히스토리안에서 다시 읽어 온다. 읽어온 값이 원본표와
  허용범위 안에서 맞는지 검증한 뒤에만 반영한다 — 엉뚱한 값으로 덮어쓰지 않도록.

습도 정정 5일 (02/25·03/04·03/18·03/24·04/02)
  MBL(10MBL11CM001) 이 드리프트 중이어서 담당자가 그 5일만 CXM(10CXM00CM001)
  값을 실적표에 넣었다. 교차 대조에서 CXM 이 실적표와 소수 둘째자리까지 일치
  (|CXM-실적표| 0.01~0.05)했고, 정상 27일은 MBL 이 일치했다.
  CIT·대기압·CC 는 그대로 두고 RH 만 CXM 으로 바꾼다. --skip-rh 로 건너뛸 수 있다.

여기서 다루지 않는 것
  · 2026-01-06 "C/T Cell #2 정지로 미반영" — 학습 제외 여부. --drop-0106 으로 처리 가능.
  · 2025-10-28 — 원본표가 eDNA 애드인으로 정리된 예외 건. 담당자 확인 중.

실행:
    python scripts/fix_records.py                  # 미리보기만 (DB 변경 없음)
    python scripts/fix_records.py --apply          # 실제 반영
    python scripts/fix_records.py --apply --drop-0106
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wirye_capacity import constants as C  # noqa: E402
from wirye_capacity.config import get_config  # noqa: E402
from wirye_capacity.correction import status_rows  # noqa: E402
from wirye_capacity.store import MeasurementStore  # noqa: E402
from wirye_capacity.theory import TheoryEngine, igv_turnup  # noqa: E402

DEFAULT_DB = str(C.db_path())   # Tool 폴더 기준(공용 해석)
NODEID_CACHE = str(Path.home() / ".wirye_opcua_nodeids.json")

# 원본표(담당자 실적표) 기준값 — 히스토리안에서 읽은 값이 이것과 맞는지 검증용.
FIXES = [
    {"date": "2025-04-15", "start": "16:00",
     "ref": {"cit": 13.7, "press": 995.8, "cc": 438.1},
     "why": "Data 취득창이 16:00~17:00 (Test 종료 17:00). 32건 중 유일"},
    {"date": "2026-01-08", "start": "17:00",
     "ref": {"cit": -1.5, "press": 1017.0, "cc": 472.5},
     "why": "DB 기록(CIT 6.90/CC 460.70)이 원본표·히스토리안과 불일치"},
]
TOL = {"cit": 0.3, "press": 1.5, "cc": 0.5}     # 원본표는 소수 1자리 표기

# 습도 정정 5일 — MBL(10MBL11CM001) 드리프트로 담당자가 CXM(10CXM00CM001) 값을 쓴 날.
# 2026-08 교차 대조에서 CXM 이 원본표와 소수 둘째자리까지 일치함을 확인했다
# (|CXM-원본| 0.01~0.05). 정상 27일은 MBL 이 일치했으므로 이 5일만 대상이다.
# CIT·대기압·CC 는 그대로 두고 RH 만 교체한다.
RH_TAG = "10CXM00CM001//XQ01"
RH_TOL = 0.5
RH_FIXES = [
    {"date": "2026-02-25", "start": "17:00", "ref": 18.2, "mbl": 0.1},
    {"date": "2026-03-04", "start": "17:00", "ref": 35.4, "mbl": 9.7},
    {"date": "2026-03-18", "start": "17:00", "ref": 67.6, "mbl": 36.8},
    {"date": "2026-03-24", "start": "17:00", "ref": 41.2, "mbl": 9.1},
    {"date": "2026-04-02", "start": "17:00", "ref": 27.6, "mbl": 0.0},
]


def read_cxm_rh(conn_cls, host, dates_starts):
    """CXM 습도를 한 번의 접속으로 여러 날짜분 읽는다. {날짜: 값}.

    acquire() 를 쓰지 않고 태그를 직접 읽는다 — acquire 는 이제 MBL/CXM 중 하나를
    골라주므로, 여기서 필요한 '가공 안 된 CXM 값'을 얻으려면 직접 읽어야 한다.
    """
    from datetime import timedelta

    from wirye_capacity.rims.opcua import _local, server_time_average, time_weighted_average
    c = conn_cls(host=host, cache_path=None, tag_keys={"rh_alt": RH_TAG})
    client = c._open_client()
    out = {}
    try:
        c._resolve_nodeids(client)
        nid = c.nodeid_map.get("rh_alt")
        if not nid:
            return out
        for d, start, minutes in dates_starts:
            s = _local(d, start)
            e = s + timedelta(minutes=minutes)
            try:
                r = server_time_average(client, nid, s, e)
                v = r[0] if isinstance(r, tuple) else r
            except Exception:                                    # noqa: BLE001
                v = None
            if v is None:                                        # 서버 집계 실패 → raw 평균
                pts = []
                for dv in client.get_node(nid).read_raw_history(s, e):
                    ts = (getattr(dv, "SourceTimestamp", None)
                          or getattr(dv, "ServerTimestamp", None))
                    x = dv.Value.Value if dv.Value is not None else None
                    if ts is not None and x is not None:
                        pts.append((ts, float(x)))
                v = time_weighted_average(pts, s, e)
            out[d] = None if v is None else float(v)
    finally:
        client.disconnect()
    return out


def hr(t):
    print("\n" + "=" * 88 + f"\n{t}\n" + "=" * 88)


def snapshot(store):
    """구간 → (건수, 실측평균, 적용값) — 변경 전/후 비교용."""
    return {r["bin_label"]: (r["count"], r["avg"], r["applied"], r["kind"])
            for r in status_rows(store.correction_table())}


def show_diff(before, after):
    """값이 바뀐 구간만 출력한다(61개 구간 전체를 찍으면 읽을 수 없다)."""
    changed = [k for k in before
               if before[k][:3] != after.get(k, (None,))[:3]]
    if not changed:
        print("  바뀐 구간 없음")
        return
    print(f"  {'구간':13}{'건수':>10}{'실측평균':>18}{'적용값':>18}   종류")
    for k in changed:
        b, af = before[k], after[k]
        fmt = lambda v: "  -  " if v is None else f"{v:+.3f}"
        print(f"  {k:13}{b[0]:>4} → {af[0]:<4}"
              f"{fmt(b[1]):>9} → {fmt(af[1]):<8}"
              f"{fmt(b[2]):>9} → {fmt(af[2]):<8}   {af[3]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--host", default=None)
    ap.add_argument("--apply", action="store_true", help="실제로 DB 를 변경한다")
    ap.add_argument("--skip-rh", action="store_true",
                    help="습도 5일 정정을 건너뛴다")
    ap.add_argument("--drop-0106", action="store_true",
                    help="2026-01-06(C/T Cell #2 정지로 미반영) 을 학습에서 제외(삭제)")
    ap.add_argument("--deg", type=float, default=C.DEFAULT_DEG)
    a = ap.parse_args()

    from wirye_capacity.rims.opcua import OpcUaRimsConnector
    store = MeasurementStore(a.db)
    eng = TheoryEngine()
    conn = OpcUaRimsConnector(host=a.host or get_config("opcua_host"),
                              cache_path=NODEID_CACHE)

    print(f"DB {a.db}   누적 {store.count()}건")
    print("모드: " + ("★ 실제 반영(--apply)" if a.apply else "미리보기 (DB 변경 없음)"))

    plan = []
    hr("1. 히스토리안 재취득 + 원본표 대조")
    for f in FIXES:
        old = next((r for r in store.all() if r.date == f["date"]), None)
        print(f"\n[{f['date']}]  {f['why']}")
        if old is None:
            print("  DB 에 이 날짜 기록이 없습니다 — 건너뜁니다.")
            continue
        try:
            acq = conn.acquire(f["date"], f["start"])
        except Exception as e:                                   # noqa: BLE001
            print(f"  취득 실패 — {e!r}  (건너뜀)")
            continue
        ref, bad = f["ref"], []
        for k, got in (("cit", acq.cit), ("press", acq.pressure), ("cc", acq.cc_meas)):
            if abs(got - ref[k]) > TOL[k]:
                bad.append(f"{k} {got:.2f} vs 원본 {ref[k]:.1f} (허용 ±{TOL[k]})")
        print(f"  취득({f['start']} 창) : CIT {acq.cit:7.2f}  대기압 {acq.pressure:7.2f}  "
              f"RH {('%.1f' % acq.rh) if acq.rh is not None else '무효':>6}  CC {acq.cc_meas:8.2f}")
        print(f"  원본표             : CIT {ref['cit']:7.1f}  대기압 {ref['press']:7.1f}  "
              f"{'':>6}  CC {ref['cc']:8.1f}")
        if bad:
            print("  ✗ 원본표와 맞지 않아 반영하지 않습니다: " + " / ".join(bad))
            continue
        # getattr 로 접근한다 — AcquiredTest.warnings 는 저장소에서 추가된 필드이고,
        # 사내 PC 는 git 이 없어 패키지를 못 받은 상태라 아직 없다.
        acq_warn = getattr(acq, "warnings", None) or []
        if acq_warn:
            print("  ! 취득 경고: " + " / ".join(acq_warn))
        # W 는 정책상 온도밴드값 — 새 CIT 로 다시 산정한다(기존 W 를 물려쓰면 안 된다)
        w = igv_turnup(acq.cit)
        new = store.build_record(cit=acq.cit, press=acq.pressure, cc_meas=acq.cc_meas,
                                 w=w, rh=acq.rh, season=old.season, date=f["date"],
                                 engine=eng, deg=a.deg)
        print(f"  ✓ 대조 통과")
        print(f"     기존  CIT {old.cit:7.2f}  CC {old.cc_meas:8.2f}  이론 {old.theory:7.2f}  "
              f"W {old.w:+3.0f}  보정 {old.corr:+7.3f}")
        print(f"     신규  CIT {new.cit:7.2f}  CC {new.cc_meas:8.2f}  이론 {new.theory:7.2f}  "
              f"W {new.w:+3.0f}  보정 {new.corr:+7.3f}   (Δ보정 {new.corr - old.corr:+.3f} MW)")
        plan.append((f["date"], old, new))

    hr("2. 습도 정정 5일 — MBL 드리프트 → CXM 값으로 교체 (CIT·대기압·CC 는 유지)")
    if a.skip_rh:
        print("  --skip-rh 지정 — 건너뜁니다.")
    else:
        cxm = read_cxm_rh(OpcUaRimsConnector, a.host or get_config("opcua_host"),
                          [(f["date"], f["start"], 60) for f in RH_FIXES])
        if not cxm:
            print(f"  CXM 태그({RH_TAG})를 못 찾았습니다 — 건너뜁니다.")
        for f in RH_FIXES:
            d = f["date"]
            old = next((r for r in store.all() if r.date == d), None)
            got = cxm.get(d)
            if old is None:
                print(f"  {d}  DB 에 없음 — 건너뜀")
                continue
            if got is None:
                print(f"  {d}  CXM 읽기 실패 — 건너뜀")
                continue
            if abs(got - f["ref"]) > RH_TOL:
                print(f"  {d}  ✗ CXM {got:.2f}% 가 원본표 {f['ref']:.1f}% 와 "
                      f"{got - f['ref']:+.2f}%p 차 (허용 ±{RH_TOL}) — 반영하지 않음")
                continue
            if old.rh is not None and abs(old.rh - got) < 0.05:
                print(f"  {d}  이미 CXM 값({got:.2f}%) — 건너뜀")
                continue
            new = store.build_record(cit=old.cit, press=old.press, cc_meas=old.cc_meas,
                                     w=old.w, rh=got, season=old.season, date=d,
                                     engine=eng, deg=a.deg)
            print(f"  {d}  ✓ RH {old.rh:.1f}% (MBL) → {got:.2f}% (CXM, 원본표 {f['ref']:.1f})")
            print(f"        이론 {old.theory:.2f} → {new.theory:.2f}   "
                  f"보정 {old.corr:+.3f} → {new.corr:+.3f}  (Δ {new.corr - old.corr:+.3f} MW)")
            plan.append((d, old, new))

    drop = None
    if a.drop_0106:
        drop = next((r for r in store.all() if r.date == "2026-01-06"), None)
        hr("3. 2026-01-06 제외 (C/T Cell #2 정지로 미반영)")
        if drop is None:
            print("  해당 날짜 기록이 없습니다 — 건너뜁니다.")
        else:
            print(f"  삭제 대상  CIT {drop.cit:.2f}  CC {drop.cc_meas:.2f}  "
                  f"보정 {drop.corr:+.3f} MW")

    before = snapshot(store)

    if not a.apply:
        hr("미리보기 종료")
        print(f"  변경 예정 {len(plan)}건(기록 교체 + 습도 정정)"
              + (" + 삭제 1건" if drop else ""))
        print("  실제로 반영하려면 같은 명령에 --apply 를 붙이세요.")
        store.close()
        return 0

    hr("4. 반영")
    for date, old, new in plan:
        n = store.delete_by_date(date)
        store.add(new)
        print(f"  {date}: 기존 {n}건 삭제 → 신규 1건 추가")
    if drop is not None:
        n = store.delete_by_date("2026-01-06")
        print(f"  2026-01-06: {n}건 삭제(학습 제외)")
    print(f"\n  누적 건수 {store.count()}건")

    hr("5. 보정값 현황 — 바뀐 구간")
    show_diff(before, snapshot(store))
    print("\n  ※ 입찰파일은 다시 생성해야 반영됩니다(보정지문이 바뀝니다).")
    store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
