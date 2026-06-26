"""개발/테스트용 mock RiMS 커넥터.

실제 RiMS·Excel 없이 자동취득→누적 경로를 검증하기 위한 것. 시드(엑셀4 실측 32건)를
합성 날짜(2025-T01…)에 매핑해 제공하거나, 임의 AcquiredTest 사전을 직접 주입한다.
"""
from __future__ import annotations

import json
from pathlib import Path

from .base import AcquiredTest

_SEED = Path(__file__).parent.parent / "data" / "measurements_seed.json"


class MockRimsConnector:
    def __init__(self, data: dict[str, AcquiredTest]):
        self._data = dict(data)

    def acquire(self, date: str, start: str = "17:00") -> AcquiredTest:
        if date not in self._data:
            raise KeyError(f"mock RiMS: '{date}' 데이터 없음 (가용: {sorted(self._data)[:3]}…)")
        return self._data[date]

    @property
    def dates(self) -> list[str]:
        return sorted(self._data)

    @classmethod
    def from_seed(cls, path: str | Path = _SEED) -> "MockRimsConnector":
        """시드 32건을 합성 날짜에 매핑한 mock 생성 (CC 실측 = 17~18 IGV 실시값)."""
        recs = json.loads(Path(path).read_text(encoding="utf-8"))
        data: dict[str, AcquiredTest] = {}
        for i, r in enumerate(recs, start=1):
            d = f"2025-T{i:02d}"
            data[d] = AcquiredTest(
                date=d, cit=r["cit"], pressure=r["press"], cc_meas=r["cc_meas"],
                rh=r.get("rh"), cp_meas=r.get("cp_meas"), cp_design=r.get("cp_design"),
                season=r.get("season"))
        return cls(data)
