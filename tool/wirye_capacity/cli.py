"""명령행 인터페이스 — GUI 없이 파이프라인 실행/조회 (크로스플랫폼).

  python -m wirye_capacity run  --date 2025-09-12 --forecast 엑셀3-1.xlsx \
        --workbook 엑셀1.xlsx --out bid.xlsx --db tests.db --seed
  python -m wirye_capacity list --db tests.db
"""
from __future__ import annotations

import argparse

from . import constants as C
from .pipeline import run_pipeline
from .rims import MockRimsConnector
from .store import MeasurementStore


def _build_connector(args):
    if getattr(args, "mock", False):
        return MockRimsConnector.from_seed()
    if getattr(args, "workbook", None):
        from .rims.excel_addin import ExcelAddinRimsConnector
        return ExcelAddinRimsConnector(args.workbook)
    return None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="wirye_capacity",
                                description="위례 공급가능용량 입찰 산정 Tool")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="테스트 취득→누적→엑셀3 입찰파일 생성")
    r.add_argument("--date", required=True, help="테스트 날짜(키)")
    r.add_argument("--forecast", help="엑셀3-1 날씨 파일 경로")
    r.add_argument("--workbook", help="엑셀1(RiMS 시트) 경로 — 실제 취득(Windows)")
    r.add_argument("--mock", action="store_true", help="mock RiMS(시드) 사용")
    r.add_argument("--db", default="measurements.db", help="누적 DB 경로")
    r.add_argument("--out", help="출력 엑셀3 입찰파일 경로")
    r.add_argument("--deg", type=float, default=C.DEFAULT_DEG)
    r.add_argument("--seed", action="store_true", help="DB가 비었으면 시드 32건 적재")

    li = sub.add_parser("list", help="누적 테스트 List-up")
    li.add_argument("--db", default="measurements.db")

    args = p.parse_args(argv)

    if args.cmd == "run":
        store = MeasurementStore(args.db)
        if args.seed and store.count() == 0:
            store.seed()
        res = run_pipeline(date=args.date, store=store, output_path=args.out,
                           connector=_build_connector(args), forecast_path=args.forecast,
                           deg=args.deg)
        print(f"적용 대기압 : {res.applied_pressure:.1f} mbar")
        if res.new_record is not None:
            print(f"신규 취득   : CIT {res.new_record.cit}°C, "
                  f"보정값 {res.new_record.corr:+.2f} MW")
        print(f"누적 건수   : {res.measurement_count}")
        if res.output_path:
            print(f"입찰 파일   : {res.output_path}")
        store.close()
        return 0

    if args.cmd == "list":
        store = MeasurementStore(args.db)
        rows = store.list_up()
        print(f"누적 {len(rows)}건:")
        for rec in rows:
            print(f"  {str(rec.get('date') or '-'):>12} | CIT {rec['cit']:>5}°C | "
                  f"보정 {rec['corr']:+.2f} MW | {rec.get('season') or ''}")
        store.close()
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
