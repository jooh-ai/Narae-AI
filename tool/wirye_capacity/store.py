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

_SEED = C.resource("data", "measurements_seed.json")

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


def migrate_legacy_db(target: str | Path | None = None) -> str | None:
    """예전 홈 폴더 DB 를 새 위치(Tool 폴더)로 한 번 복사한다.

    기본 DB 위치를 홈 → Tool 폴더로 옮겼기 때문에, 그냥 두면 기존 누적이
    사라진 것처럼 보인다. 대상이 아직 없고 홈에 파일이 있을 때만 복사하며,
    원본은 지우지 않는다(사용자가 확인한 뒤 직접 지우면 된다).

    반환: 복사했으면 안내 문구, 아니면 None.
    """
    import shutil
    dst = Path(target) if target else C.db_path()
    src = C.legacy_db_path()
    if dst.exists() or not src.exists() or src.resolve() == dst.resolve():
        return None
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    except OSError as e:                                    # noqa: BLE001
        return f"기존 DB 를 옮기지 못했습니다: {e}"
    return (f"기존 누적 DB 를 Tool 폴더로 옮겼습니다.\n"
            f"  이전: {src}\n  현재: {dst}\n"
            f"(이전 파일은 그대로 두었습니다. 확인 후 지우셔도 됩니다)")


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

    def build_record(self, *, cit: float, press: float, cc_meas: float,
                     w: float | None = None, rh: float | None = None,
                     cp_meas: float | None = None, cp_design: float | None = None,
                     season: str | None = None, date: str | None = None,
                     engine: TheoryEngine | None = None,
                     deg: float = C.DEFAULT_DEG) -> TestRecord:
        """이론기준값·보정값을 계산해 TestRecord 를 만든다 (저장은 하지 않음).

        보정값 = CC실측 − 이론기준값(엔진, 실측 RH 반영) − W. W 미지정 시 온도밴드값.
        """
        if w is None:
            w = igv_turnup(cit)
        eng = engine or TheoryEngine()
        theory = eng.theory_cc(cit, press, deg, rh=rh)
        corr = correction_value(cc_meas, theory, w)
        return TestRecord(cit=cit, press=press, cc_meas=cc_meas, w=w, theory=theory,
                          corr=corr, rh=rh, cp_meas=cp_meas, cp_design=cp_design,
                          season=season, date=date)

    def record_test(self, **kwargs) -> TestRecord:
        """build_record + 저장. (계산 후 바로 누적에 반영)"""
        rec = self.build_record(**kwargs)
        self.add(rec)
        return rec

    def has_date(self, date: str | None) -> bool:
        """해당 날짜의 테스트가 이미 누적되어 있는지 (중복 반영 방지용)."""
        if not date:
            return False
        return self.conn.execute(
            "SELECT 1 FROM measurements WHERE date=? LIMIT 1", (date,)).fetchone() is not None

    def compute_from_rims(self, connector, date: str, *, start: str = "17:00",
                          engine: TheoryEngine | None = None, deg: float = C.DEFAULT_DEG,
                          season: str | None = None) -> TestRecord:
        """RiMS에서 테스트 1건 자동취득 → 보정값 계산 (저장은 하지 않음 = 확인용).

        connector 는 .acquire(date, start)→AcquiredTest 인터페이스(mock/실제 동일).
        """
        acq = connector.acquire(date, start)
        return self.build_record(
            cit=acq.cit, press=acq.pressure, cc_meas=acq.cc_meas, w=None,
            rh=getattr(acq, "rh", None), cp_meas=getattr(acq, "cp_meas", None),
            cp_design=getattr(acq, "cp_design", None),
            season=season or getattr(acq, "season", None), date=date,
            engine=engine, deg=deg)

    def record_from_rims(self, connector, date: str, **kwargs) -> TestRecord:
        """compute_from_rims + 저장 (누적 반영)."""
        rec = self.compute_from_rims(connector, date, **kwargs)
        self.add(rec)
        return rec

    # 사용자가 직접 고칠 수 있는 필드. theory·corr 는 파생값이라 여기 없다.
    EDITABLE = ("date", "cit", "press", "rh", "cc_meas", "w", "season")

    def update(self, rec_id: int, *, engine: TheoryEngine | None = None,
               deg: float = C.DEFAULT_DEG, recalc_w: bool = False,
               **fields) -> TestRecord:
        """일부 필드를 고치고 이론기준값·보정값을 다시 계산해 저장한다.

        List-up 셀 편집용. 계절 라벨만 바꾸는 경우에도 재계산은 무해하다(같은 값).
        recalc_w=True 면 W 를 새 CIT 의 온도밴드값으로 다시 산정한다 — CIT 를 크게
        고칠 때 필요하다(정책상 W 는 온도밴드값이므로).
        """
        bad = set(fields) - set(self.EDITABLE)
        if bad:
            raise ValueError(f"수정할 수 없는 필드: {sorted(bad)} "
                             f"(가능: {list(self.EDITABLE)})")
        row = self.conn.execute(
            "SELECT * FROM measurements WHERE id=?", (rec_id,)).fetchone()
        if row is None:
            raise KeyError(f"id {rec_id} 기록이 없습니다.")
        cur = dict(row)
        changed = {k for k, v in fields.items() if cur.get(k) != v}
        cur.update({k: v for k, v in fields.items()})
        if recalc_w and "w" not in fields:
            w2 = igv_turnup(cur["cit"])
            if w2 != cur["w"]:
                cur["w"] = w2
                changed.add("w")
        # 필요한 것만 다시 계산한다. 날짜·계절만 고쳤는데 이론값이 바뀌면 안 된다 —
        # 씨앗 32건은 엑셀4 I열 이론값을 그대로 갖고 있고(엔진 재계산값과 최대
        # 0.19MW 차), 라벨 편집으로 그게 조용히 덮어써지면 기준이 흔들린다.
        if changed & {"cit", "press", "rh"}:
            eng = engine or TheoryEngine()
            cur["theory"] = eng.theory_cc(cur["cit"], cur["press"], deg, rh=cur["rh"])
        if changed & {"cit", "press", "rh", "cc_meas", "w"}:
            cur["corr"] = correction_value(cur["cc_meas"], cur["theory"], cur["w"])
        self.conn.execute(
            f"UPDATE measurements SET {','.join(c + '=?' for c in _COLS)} WHERE id=?",
            tuple(cur[c] for c in _COLS) + (rec_id,))
        self.conn.commit()
        return TestRecord(**{k: cur[k] for k in _COLS}, id=rec_id)

    def delete(self, rec_id: int) -> None:
        self.conn.execute("DELETE FROM measurements WHERE id=?", (rec_id,))
        self.conn.commit()

    def backfill_dates(self, records: list[dict], tol: float = 0.05) -> int:
        """날짜가 빈 레코드에 엑셀4 날짜를 채운다((CC실측[, CIT]) 근사 매칭). 채운 건수 반환.

        시드 32건은 날짜 없이 적재돼 List-up 에 '-' 로 보이므로, 원본 엑셀4에서 날짜를 가져온다.
        """
        rows = self.conn.execute(
            "SELECT id, cit, cc_meas FROM measurements "
            "WHERE date IS NULL OR date=''").fetchall()
        used: set[int] = set()
        filled = 0
        for row in rows:
            for k, rec in enumerate(records):
                if k in used or not rec.get("date"):
                    continue
                if abs(rec["cc_meas"] - row["cc_meas"]) > tol:
                    continue
                if (rec.get("cit") is not None
                        and abs(rec["cit"] - row["cit"]) > 0.15):   # 엑셀4 온도는 1자리 표기
                    continue
                self.conn.execute("UPDATE measurements SET date=? WHERE id=?",
                                  (rec["date"], row["id"]))
                used.add(k)
                filled += 1
                break
        self.conn.commit()
        return filled

    def delete_by_date(self, date: str) -> int:
        """해당 날짜의 테스트 삭제(실수 반영 취소용). 삭제 건수 반환."""
        cur = self.conn.execute("DELETE FROM measurements WHERE date=?", (date,))
        self.conn.commit()
        return cur.rowcount

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
