"""CLI 검증 — run/list/verify (mock RiMS, 크로스플랫폼)."""
from pathlib import Path

import pytest

from wirye_capacity.cli import main


def test_run_creates_bid_file_and_accumulates(tmp_path, capsys):
    db = str(tmp_path / "m.db")
    out = str(tmp_path / "bid.xlsx")
    rc = main(["run", "--date", "2025-T05", "--mock", "--accumulate", "--db", db, "--out", out])
    assert rc == 0
    assert Path(out).exists()
    printed = capsys.readouterr().out
    assert "누적 건수" in printed
    assert "입찰 파일" in printed
    assert "반영" in printed         # 누적 반영 상태 표시


def test_preview_default_does_not_accumulate(tmp_path, capsys):
    """--accumulate 없으면 확인용 — 누적 미저장."""
    db = str(tmp_path / "m.db")
    main(["run", "--date", "2025-T05", "--mock", "--db", db])   # no --accumulate
    out = capsys.readouterr().out
    assert "확인용(미반영)" in out
    # 이어서 list → 0건
    main(["list", "--db", db])
    assert "누적 0건" in capsys.readouterr().out


def test_run_seed_then_count(tmp_path, capsys):
    db = str(tmp_path / "m.db")
    # --seed 로 32건 적재 후 신규 1건(T05는 시드와 동일 데이터지만 별도 레코드)
    main(["run", "--date", "2025-T05", "--mock", "--seed", "--accumulate", "--db", db])
    out = capsys.readouterr().out
    assert "누적 건수" in out and ": 33" in out


def test_list_after_run(tmp_path, capsys):
    db = str(tmp_path / "m.db")
    main(["run", "--date", "2025-T01", "--mock", "--accumulate", "--db", db])
    capsys.readouterr()
    rc = main(["list", "--db", db])
    assert rc == 0
    out = capsys.readouterr().out
    assert "누적 1건" in out
    assert "CIT" in out


def test_verify_cli_self_pass(tmp_path, capsys):
    """verify: Tool 생성본(tool 양식)을 기준으로 자기대조 → PASS."""
    from wirye_capacity.profile import build_profile, write_xlsx
    from wirye_capacity.store import MeasurementStore
    from wirye_capacity.theory import TheoryEngine
    db = str(tmp_path / "m.db")
    s = MeasurementStore(db); s.seed()
    ref = str(tmp_path / "ref.xlsx")
    write_xlsx(build_profile(TheoryEngine(), s.correction_table(), pressure=1013, deg=1.028), ref)
    s.close()
    rc = main(["verify", "--ref", ref, "--layout", "tool", "--db", db,
               "--pressure", "1013", "--deg", "1.028"])
    assert rc == 0
    assert "PASS" in capsys.readouterr().out
