"""테스트결과 저장·List-up (SQLite).

공급가능용량 테스트 결과를 누적 저장하고 온도구간 보정 집계에 연결한다.
- 새 테스트 추가 시 이론기준값·보정값을 TheoryEngine으로 계산해 함께 저장.
- 시드(엑셀4 실측 32건)는 원본 수기 산출값(theory/corr)을 그대로 보존해 적재
  (엑셀4 '보정값 현황'과의 일치를 유지하기 위함; §7.1 정합 항목 참조).
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from . import constants as C
from .correction import aggregate_bins, correction_value
from .theory import TheoryEngine, igv_turnup

_DATA = Path(__file__).parent / "data"
_SEED = _DATA / "measurements_seed.json"

# DB 컬럼 (id 제외, 삽입 순서)
_COLS = ["date", "cit", "press", "rh", "cp_meas", "cp_design",
         "cc_meas", "w", "theory", "corr", "season"]


@dataclass
class TestRecord:
    """공급가능용량 테스트 1건. cit=CIT(°C), press=실측 대기압(mbar)."""
    __test__ = False  # pytest 가 테스트 클래스로 오인하지 않도록

    cit: float
    press: float
    cc_meas: float
    w: float
    theory: float
    corr: float
    rh: float | None = None
    cp_meas: float | None = None
    cp_design: float | None = None
    season: str | None = None
    date: str | None = None
    id: int | None = None


class MeasurementStore:
    """SQLite 기반 테스트결과 저장소."""

    def __init__(self, db_path: str | Path = ":memory:"):
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._create()

    def _create(self) -> None:
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS measurements(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT, cit REAL NOT NULL, press REAL NOT NULL,
                rh REAL, cp_meas REAL, cp_design REAL,
                cc_meas REAL NOT NULL, w REAL NOT NULL,
                theory REAL NOT NULL, corr REAL NOT NULL, season TEXT)"""
        )
        self.conn.commit()

    # ---------------- 쓰기 ----------------
    def add(self, rec: TestRecord) -> int:
        cur = self.conn.execute(
            f"INSERT INTO measurements ({','.join(_COLS)}) "
            f"VALUES ({','.join('?' * len(_COLS))})",
            tuple(getattr(rec, c) for c in _COLS),
        )
        self.conn.commit()
        rec.id = cur.lastrowid
        return rec.id

    def record_test(self, *, cit: float, press: float, cc_meas: float,
                    w: float | None = None,
                    rh: float | None = None, cp_meas: float | None = None,
                    cp_design: float | None = None, season: str | None = None,
                    date: str | None = None, engine: TheoryEngine | None = None,
                    deg: float = C.DEFAULT_DEG) -> TestRecord:
        """새 테스트 1건 등록 — 이론기준값·보정값을 계산해 저장.

        보정값 = CC실측 − 이론기준값(엔진) − W.
        W 미지정 시 온도밴드값(igv_turnup) 사용 (사용자 확정: 밴드 유지).
        """
        if w is None:
            w = igv_turnup(cit)
        eng = engine or TheoryEngine()
        theory = eng.theory_cc(cit, press, deg)
        corr = correction_value(cc_meas, theory, w)
        rec = TestRecord(cit=cit, press=press, cc_meas=cc_meas, w=w, theory=theory,
                         corr=corr, rh=rh, cp_meas=cp_meas, cp_design=cp_design,
                         season=season, date=date)
        self.add(rec)
        return rec

    def record_from_rims(self, connector, date: str, *, start: str = "17:00",
                         engine: TheoryEngine | None = None, deg: float = C.DEFAULT_DEG,
                         season: str | None = None) -> TestRecord:
        """RiMS에서 테스트 1건 자동취득 → 보정값 계산 → 누적 저장.

        ("날짜·시간 → 자동 누적" 경로. connector 는 .acquire(date, start)→AcquiredTest 를
        가진 객체이면 됨; mock / 실제 Excel-COM 모두 동일 인터페이스.)
        W 는 밴드값(igv_turnup) 사용.
        """
        acq = connector.acquire(date, start)
        return self.record_test(
            cit=acq.cit, press=acq.pressure, cc_meas=acq.cc_meas, w=None,
            rh=getattr(acq, "rh", None), cp_meas=getattr(acq, "cp_meas", None),
            cp_design=getattr(acq, "cp_design", None),
            season=season or getattr(acq, "season", None), date=date,
            engine=engine, deg=deg)

    def delete(self, rec_id: int) -> None:
        self.conn.execute("DELETE FROM measurements WHERE id=?", (rec_id,))
        self.conn.commit()

    def clear(self) -> None:
        self.conn.execute("DELETE FROM measurements")
        self.conn.commit()

    # ---------------- 읽기 ----------------
    def all(self) -> list[TestRecord]:
        rows = self.conn.execute("SELECT * FROM measurements ORDER BY cit").fetchall()
        return [TestRecord(**{k: r[k] for k in r.keys()}) for r in rows]

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]

    def list_up(self, order: str = "cit") -> list[dict]:
        """List-up 표시용 — 레코드 dict 목록 (온도순 기본, 'date'도 가능)."""
        col = "date" if order == "date" else "cit"
        rows = self.conn.execute(f"SELECT * FROM measurements ORDER BY {col}").fetchall()
        return [dict(r) for r in rows]

    def correction_table(self) -> dict:
        """현재 누적 실측 기반 온도구간 보정 테이블 (엑셀4 '보정값 현황')."""
        return aggregate_bins([{"cit": r.cit, "corr": r.corr} for r in self.all()])

    # ---------------- 시드 ----------------
    def seed(self, path: str | Path = _SEED) -> int:
        """엑셀4 실측 32건 적재 (원본 수기 theory/corr 보존)."""
        recs = json.loads(Path(path).read_text(encoding="utf-8"))
        for r in recs:
            self.add(TestRecord(
                cit=r["cit"], press=r["press"], cc_meas=r["cc_meas"], w=r["w"],
                theory=r["theory"], corr=r["corr"], rh=r.get("rh"),
                cp_meas=r.get("cp_meas"), cp_design=r.get("cp_design"),
                season=r.get("season"), date=r.get("date")))
        return len(recs)

    def close(self) -> None:
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
