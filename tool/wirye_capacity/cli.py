"""명령행 인터페이스 — GUI 없이 파이프라인 실행/조회 (크로스플랫폼).

  python -m wirye_capacity run  --date 2025-09-12 --forecast 엑셀3-1.xlsx \
        --workbook 엑셀1.xlsx --out bid.xlsx --db tests.db --seed
  python -m wirye_capacity list --db tests.db
"""
from __future__ import annotations

import argparse
from pathlib import Path

from . import constants as C
from .pipeline import run_pipeline
from .rims import MockRimsConnector
from .store import MeasurementStore

# CLI·GUI 공용 기본 누적 DB (홈 디렉터리)
DEFAULT_DB = str(Path.home() / "wirye_measurements.db")


def _disp_width(s: str) -> int:
    """터미널 표시 폭 (한글·CJK = 2칸)."""
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in str(s))


def _pad(s, width: int, right: bool = False) -> str:
    """표시 폭 기준 정렬 패딩 (한글 폭 보정)."""
    s = str(s)
    gap = max(0, width - _disp_width(s))
    return (" " * gap + s) if right else (s + " " * gap)


def _print_status(table) -> None:
    """온도구간별 보정값 현황 출력 (엑셀4 '보정값 현황' 시트)."""
    from .correction import status_rows
    print("\n보정값 현황 (엑셀4 '보정값 현황'):")
    print("  " + _pad("구간", 11) + _pad("종류", 24) + _pad("건수", 8, True)
          + _pad("실측평균", 11, True) + _pad("적용값", 10, True) + "  상태")
    for r in status_rows(table):
        cnt = f"{r['count']}/{r['target']}" if r["target"] else str(r["count"])
        avg = f"{r['avg']:+.2f}" if r["avg"] is not None else "-"
        applied = f"{r['applied']:+.2f}" if r["applied"] is not None else "-"
        print("  " + _pad(r["bin_label"], 11) + _pad(r["kind_label"], 24)
              + _pad(cnt, 8, True) + _pad(avg, 11, True) + _pad(applied, 10, True)
              + "  " + r["status"])


DEFAULT_OPCUA_CACHE = str(Path.home() / ".wirye_opcua_nodeids.json")


def _build_connector(args):
    if getattr(args, "mock", False):
        return MockRimsConnector.from_seed()
    # B: DataPARC OPC UA 직접 취득 (엑셀 불필요)
    host = getattr(args, "opcua_host", None)
    ep = getattr(args, "opcua_endpoint", None)
    if host or ep:
        from .rims.opcua import OpcUaRimsConnector
        cache = getattr(args, "opcua_cache", None) or DEFAULT_OPCUA_CACHE
        print(f"RiMS 취득 방식 : OPC UA ({ep or host})")
        return OpcUaRimsConnector(endpoint=ep, host=host, cache_path=cache)
    # A: 엑셀1 경유 (exe/현재 폴더의 엑셀1 자동 감지)
    wb = getattr(args, "workbook", None)
    if not wb:
        from .rims.locate import resolve_workbook
        found = resolve_workbook()
        if found and found.exists():
            wb = str(found)
            print(f"엑셀1 자동 감지 : {found.name}  ({found.parent})")
    if wb:
        from .rims.excel_addin import ExcelAddinRimsConnector
        return ExcelAddinRimsConnector(wb)
    return None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="wirye_capacity",
                                description="위례 공급가능용량 입찰 산정 Tool")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="테스트 취득→누적→엑셀3 입찰파일 생성")
    r.add_argument("--date", required=True, help="테스트 날짜(키)")
    r.add_argument("--forecast", help="엑셀3-1 날씨 파일 경로")
    r.add_argument("--workbook", help="엑셀1(RiMS 시트) 경로 — A: 엑셀 경유 취득")
    r.add_argument("--opcua-host", dest="opcua_host",
                   help="B: DataPARC OPC UA 서버 호스트로 직접 취득(엑셀 불필요)")
    r.add_argument("--opcua-endpoint", dest="opcua_endpoint",
                   help="B: OPC UA 엔드포인트 전체 URL(호스트 대신 지정)")
    r.add_argument("--opcua-cache", dest="opcua_cache",
                   help="OPC UA 태그 NodeId 캐시 경로(기본 ~/.wirye_opcua_nodeids.json)")
    r.add_argument("--mock", action="store_true", help="mock RiMS(시드) 사용")
    r.add_argument("--db", default=DEFAULT_DB, help="누적 DB 경로")
    r.add_argument("--out", help="출력 엑셀3 입찰파일 경로")
    r.add_argument("--template", help="엑셀3 템플릿(입찰 양식) 경로. 미지정 시 번들 템플릿 사용")
    r.add_argument("--deg", type=float, default=C.DEFAULT_DEG)
    r.add_argument("--bid-day", dest="bid_day", default=None,
                   help="입찰 적용일(엑셀3-1 일자 라벨). 미지정 시 전체 중위 평균")
    r.add_argument("--curve", action="store_true", help="연속 보정곡선 사용(기본: 구간 평균)")
    r.add_argument("--accumulate", action="store_true",
                   help="이 테스트를 누적에 반영(저장). 기본은 확인용(미반영)")
    r.add_argument("--seed", action="store_true", help="DB가 비었으면 시드 32건 적재")

    li = sub.add_parser("list", help="누적 테스트 List-up")
    li.add_argument("--db", default=DEFAULT_DB)

    ck = sub.add_parser("check-rims", help="RiMS 단건 취득값 출력(수동값과 대조용)")
    ck.add_argument("--workbook", help="엑셀1(RiMS 시트) 경로. 생략 시 exe/현재 폴더에서 자동 감지")
    ck.add_argument("--date", required=True)
    ck.add_argument("--start", default="17:00")
    ck.add_argument("--sheet", default="RiMS 계산 Sheet")

    vf = sub.add_parser("verify", help="시운전: 기준 엑셀 ↔ Tool Profile 대조(±tol)")
    vf.add_argument("--ref", required=True, help="기준 엑셀(기존 온도 Profile) 경로")
    vf.add_argument("--layout", default="excel4", choices=["excel4", "tool"])
    vf.add_argument("--db", default=DEFAULT_DB)
    vf.add_argument("--pressure", type=float, default=C.REF_PRESSURE)
    vf.add_argument("--deg", type=float, default=C.DEFAULT_DEG)
    vf.add_argument("--curve", action="store_true")
    vf.add_argument("--tol", type=float, default=0.5)

    args = p.parse_args(argv)

    if args.cmd == "run":
        store = MeasurementStore(args.db)
        if args.seed and store.count() == 0:
            store.seed()
        from .profile import DEFAULT_TEMPLATE
        res = run_pipeline(date=args.date, store=store, output_path=args.out,
                           connector=_build_connector(args), forecast_path=args.forecast,
                           deg=args.deg, bid_day=args.bid_day, accumulate=args.accumulate,
                           correction_method="curve" if args.curve else "bin",
                           template_path=args.template or DEFAULT_TEMPLATE)
        src = f"'{args.bid_day}'" if args.bid_day else "전체 중위 평균"
        print(f"적용 대기압 : {res.applied_pressure:.1f} mbar  (기준: {src})")
        if res.new_record is not None:
            status = ("✅ 누적 반영됨" if res.reflected else
                      "⚠ 이미 반영된 날짜 — 건너뜀" if res.duplicate_skipped else
                      "확인용(미반영)")
            print(f"신규 취득   : CIT {res.new_record.cit}°C, "
                  f"보정값 {res.new_record.corr:+.2f} MW  [{status}]")
        print(f"누적 건수   : {res.measurement_count}")
        if res.output_path:
            print(f"입찰 파일   : {res.output_path}")
        _print_status(res.correction_table)
        store.close()
        return 0

    if args.cmd == "list":
        store = MeasurementStore(args.db)
        rows = store.list_up()
        print(f"누적 {len(rows)}건:")
        for rec in rows:
            print(f"  {str(rec.get('date') or '-'):>12} | CIT {rec['cit']:>5}°C | "
                  f"보정 {rec['corr']:+.2f} MW | {rec.get('season') or ''}")
        _print_status(store.correction_table())
        store.close()
        return 0

    if args.cmd == "check-rims":
        from .rims.excel_addin import ExcelAddinRimsConnector
        from .rims.locate import resolve_workbook
        wb = resolve_workbook(args.workbook)
        if wb is None or not wb.exists():
            print("엑셀1을 찾지 못했습니다. --workbook 로 경로를 지정하거나 "
                  "exe/현재 폴더에 엑셀1(.xlsx)을 두세요.")
            return 1
        if not args.workbook:
            print(f"엑셀1 자동 감지 : {wb.name}  ({wb.parent})")
        conn = ExcelAddinRimsConnector(str(wb), sheet=args.sheet)
        acq = conn.acquire(args.date, args.start)
        print(f"RiMS 취득 ({args.date} {args.start}~):")
        print(f"  CIT        : {acq.cit} °C")
        print(f"  대기압     : {acq.pressure} mbar")
        print(f"  상대습도   : {acq.rh} %")
        print(f"  GT/ST      : {acq.gt_meas} / {acq.st_meas} MW")
        print(f"  CC Gross   : {acq.cc_meas} MW")
        print("→ 엑셀1을 같은 날짜·시각으로 수동 취득한 8행 값과 일치하는지 대조하세요.")
        return 0

    if args.cmd == "verify":
        from .profile import build_profile
        from .theory import TheoryEngine
        from .verify import compare_profile, read_reference_xlsx
        eng = TheoryEngine()
        store = MeasurementStore(args.db)
        corrector = None
        if args.curve:
            from .curve import CorrectionCurve
            corrector = CorrectionCurve(
                [{"cit": r.cit, "corr": r.corr} for r in store.all()])
        rows = build_profile(eng, store.correction_table(), pressure=args.pressure,
                             deg=args.deg, corrector=corrector)
        ref = read_reference_xlsx(args.ref, layout=args.layout)
        fields = ["cc_theory", "cc_real_gross"] if args.layout == "excel4" else None
        rep = compare_profile(rows, ref, tol=args.tol,
                              fields=fields or ["cc_theory", "cc_real_gross", "cc_real_net"])
        print(rep.summary())
        for f in rep.failures[:20]:
            print(f"  ✗ {f['temp']:>3}°C {f['field']:<14} Tool {f['tool']:.2f} "
                  f"vs 기준 {f['ref']:.2f}  (차이 {f['diff']:+.2f})")
        store.close()
        return 0 if rep.passed else 2

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
