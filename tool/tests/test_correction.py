"""보정 로직 검증 — 엑셀4 '보정값 현황' / '실측데이터'를 재현하는지 확인."""
import json
from pathlib import Path

import pytest

from wirye_capacity import constants as C
from wirye_capacity.correction import (
    aggregate_bins, applied_correction, bin_for, correction_value, realized_net,
)

SEED = json.loads(
    (Path(__file__).parent.parent / "wirye_capacity" / "data" / "measurements_seed.json")
    .read_text(encoding="utf-8")
)


def test_correction_value_formula():
    # 엑셀4 실측데이터 row5: J = G − I − W = 468.76 − 455.82 − 0
    assert correction_value(468.76, 455.82, 0) == pytest.approx(12.94, abs=1e-2)
    # row24 (25.1°C): 414.54 − 410.65 − 6
    assert correction_value(414.54, 410.65, 6) == pytest.approx(-2.11, abs=1e-2)


def test_seed_corr_consistency():
    # 시드의 corr = cc_meas − theory − w 가 모두 성립
    for r in SEED:
        assert correction_value(r["cc_meas"], r["theory"], r["w"]) == pytest.approx(
            r["corr"], abs=1e-2
        )


def test_bin_assignment():
    assert bin_for(5)[:2] == (0, 10)
    assert bin_for(12.7)[:2] == (10, 15)
    assert bin_for(25.0)[:2] == (25, 30)
    assert bin_for(-1.9)[:2] == (-14, 0)
    assert bin_for(-18)[2] == "shaft_limit"


def test_aggregate_reproduces_excel4_status_sheet():
    table = aggregate_bins(SEED)
    # 엑셀4 '보정값 현황' B열(AVERAGEIFS) 및 건수(E열)
    expect = {
        (0, 10): (5.78, 8),
        (10, 15): (6.28, 6),
        (15, 20): (6.12, 3),
        (20, 25): (2.62, 1),
        (25, 30): (-2.39, 4),
        (30, 41): (-0.32, 9),
    }
    for key, (avg, cnt) in expect.items():
        assert table[key]["count"] == cnt, key
        assert table[key]["avg"] == pytest.approx(avg, abs=0.01), key
    # 고정 구간: 보수적 +8.78 적용 (평균 아님)
    assert table[(-14, 0)]["applied"] == pytest.approx(8.78, abs=1e-9)
    # Shaft Limit: 보정 0
    assert table[(-20, -14)]["applied"] == 0.0


def test_applied_correction_lookup():
    table = aggregate_bins(SEED)
    assert applied_correction(7, table) == pytest.approx(5.78, abs=0.01)
    assert applied_correction(27, table) == pytest.approx(-2.39, abs=0.01)


def test_realized_net_and_cap():
    # 일반: (이론Gross+IGV) + 보정 − Aux
    assert realized_net(418.293, -2.39) == pytest.approx(418.293 - 2.39 - 10.0, abs=1e-6)
    # 상한: Net 462 초과 시 cap
    assert realized_net(500.0, 10.0) == C.BID_CAP_NET
