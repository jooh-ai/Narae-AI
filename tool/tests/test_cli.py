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
    # --seed 로 36건 적재 후 신규 1건(T05는 시드와 동일 데이터지만 별도 레코드)
    main(["run", "--date", "2025-T05", "--mock", "--seed", "--accumulate", "--db", db])
    out = capsys.readouterr().out
    assert "누적 건수" in out and ": 37" in out


def test_list_after_run(tmp_path, capsys):
    db = str(tmp_path / "m.db")
    main(["run", "--date", "2025-T01", "--mock", "--accumulate", "--db", db])
    capsys.readouterr()
    rc = main(["list", "--db", db])
    assert rc == 0
    out = capsys.readouterr().out
    assert "누적 1건" in out
    assert "CIT" in out


def test_run_prints_correction_status(tmp_path, capsys):
    """run 출력에 엑셀4식 '보정값 현황' 표가 함께 표시된다."""
    db = str(tmp_path / "m.db")
    main(["run", "--date", "2025-T05", "--mock", "--seed", "--db", db])
    out = capsys.readouterr().out
    assert "보정값 현황" in out
    assert "Shaft Limit" in out          # 구간 종류 표식
    assert "보수적 고정" in out          # 고정 구간 표식


def test_list_prints_correction_status(tmp_path, capsys):
    db = str(tmp_path / "m.db")
    main(["run", "--date", "2025-T01", "--mock", "--seed", "--accumulate", "--db", db])
    capsys.readouterr()
    main(["list", "--db", db])
    out = capsys.readouterr().out
    assert "보정값 현황" in out
    assert "°C" in out                   # 온도구간 라벨


def test_delete_by_date_removes_and_reaggregates(tmp_path, capsys):
    """delete --date: 실수 반영 취소 → 누적·보정값 현황 재집계."""
    db = str(tmp_path / "m.db")
    main(["run", "--date", "2025-T01", "--mock", "--accumulate", "--db", db])
    capsys.readouterr()
    rc = main(["delete", "--date", "2025-T01", "--db", db])
    assert rc == 0
    out = capsys.readouterr().out
    assert "1건 삭제" in out
    assert "누적 건수   : 0" in out
    assert "보정값 현황" in out          # 재집계 표 함께 표시


def test_delete_requires_date_or_id(tmp_path, capsys):
    rc = main(["delete", "--db", str(tmp_path / "m.db")])
    assert rc == 1


def test_check_bid_fresh_then_stale(tmp_path, capsys):
    """check-bid: 생성 직후 ✅최신 → 누적 변경 후 ⚠구버전."""
    db = str(tmp_path / "m.db")
    out = str(tmp_path / "bid.xlsx")
    main(["run", "--date", "2025-T05", "--mock", "--seed", "--accumulate",
          "--db", db, "--out", out])
    capsys.readouterr()
    assert main(["check-bid", "--file", out, "--db", db]) == 0
    assert "✅ 최신" in capsys.readouterr().out
    # 누적 변경(avg 구간 테스트 반영 → 적용 보정값 이동) → 구버전
    # (주: T01·T02 는 -14~0°C '보수적 고정' 구간이라 적용값이 안 변해 지문 유지 —
    #  의도된 동작이므로 avg 구간에 속하는 T03(CIT 1.9°C)을 쓴다)
    main(["run", "--date", "2025-T03", "--mock", "--accumulate", "--db", db])
    capsys.readouterr()
    assert main(["check-bid", "--file", out, "--db", db]) == 2
    assert "구버전" in capsys.readouterr().out


def test_check_bid_no_stamp(tmp_path, capsys):
    """보정지문 없는 파일(외부/구버전 생성) → 경고 리턴 2."""
    from openpyxl import Workbook
    f = str(tmp_path / "plain.xlsx")
    Workbook().save(f)
    assert main(["check-bid", "--file", f, "--db", str(tmp_path / "m.db")]) == 2
    assert "보정지문이 없습니다" in capsys.readouterr().out


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


# ─────────────────────────────────────────────────────────────────────────────
# add — 테스트 1건 수동 입력.
# 자동취득이 틀린 값을 넣었을 때(2025-10-28 CC 454.10 vs 엑셀4 452.3669)
# 엑셀4 확정값으로 되돌릴 경로가 없었다.
# ─────────────────────────────────────────────────────────────────────────────
def test_add_inserts_record(tmp_path, capsys):
    from wirye_capacity.cli import main
    db = str(tmp_path / "a.db")
    rc = main(["add", "--db", db, "--date", "2025-10-28", "--cit", "12.7",
               "--press", "1018.3", "--rh", "24.0", "--cc", "452.3669"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "2025-10-28" in out and "452.3669" in out
    from wirye_capacity.store import MeasurementStore
    st = MeasurementStore(db)
    assert st.count() == 1
    assert st.has_date("2025-10-28")
    st.close()


def test_add_rejects_duplicate_date(tmp_path):
    from wirye_capacity.cli import main
    db = str(tmp_path / "b.db")
    base = ["add", "--db", db, "--date", "2025-10-28", "--cit", "12.7",
            "--press", "1018.3", "--cc", "452.3669"]
    assert main(base) == 0
    assert main(base) == 1                       # 같은 날짜 두 번 → 거부
    assert main(base + ["--force"]) == 0         # --force 면 허용


def test_add_theory_override_preserves_excel4_basis(tmp_path):
    """--theory 로 엑셀4 I열 값을 고정하면 보정값도 그 기준으로 계산된다."""
    from wirye_capacity.cli import main
    from wirye_capacity.store import MeasurementStore
    db = str(tmp_path / "c.db")
    main(["add", "--db", db, "--date", "2025-10-28", "--cit", "12.7", "--press", "1018.3",
          "--rh", "24.0", "--cc", "452.3669", "--theory", "443.53"])
    st = MeasurementStore(db)
    r = st.all()[0]
    st.close()
    assert r.theory == pytest.approx(443.53)
    # 보정값 = CC실측 − 이론 − W(12.7°C 밴드 = +4)
    assert r.corr == pytest.approx(452.3669 - 443.53 - 4.0, abs=1e-6)


def test_add_computes_theory_when_not_given(tmp_path):
    from wirye_capacity.cli import main
    from wirye_capacity.store import MeasurementStore
    from wirye_capacity.theory import TheoryEngine
    from wirye_capacity import constants as C
    db = str(tmp_path / "d.db")
    main(["add", "--db", db, "--date", "2025-10-28", "--cit", "12.7",
          "--press", "1018.3", "--rh", "24.0", "--cc", "452.3669"])
    st = MeasurementStore(db)
    r = st.all()[0]
    st.close()
    expect = TheoryEngine().theory_cc(12.7, 1018.3, C.DEFAULT_DEG, rh=24.0)
    assert r.theory == pytest.approx(expect)
