"""CLI 검증 — run/list (mock RiMS, 크로스플랫폼)."""
from pathlib import Path

from wirye_capacity.cli import main


def test_run_creates_bid_file_and_accumulates(tmp_path, capsys):
    db = str(tmp_path / "m.db")
    out = str(tmp_path / "bid.xlsx")
    rc = main(["run", "--date", "2025-T05", "--mock", "--db", db, "--out", out])
    assert rc == 0
    assert Path(out).exists()
    printed = capsys.readouterr().out
    assert "누적 건수" in printed
    assert "입찰 파일" in printed


def test_run_seed_then_count(tmp_path, capsys):
    db = str(tmp_path / "m.db")
    # --seed 로 32건 적재 후 신규 1건(T05는 시드와 동일 데이터지만 별도 레코드)
    main(["run", "--date", "2025-T05", "--mock", "--seed", "--db", db])
    out = capsys.readouterr().out
    assert "누적 건수" in out and ": 33" in out


def test_list_after_run(tmp_path, capsys):
    db = str(tmp_path / "m.db")
    main(["run", "--date", "2025-T01", "--mock", "--db", db])
    capsys.readouterr()
    rc = main(["list", "--db", db])
    assert rc == 0
    out = capsys.readouterr().out
    assert "누적 1건" in out
    assert "CIT" in out
