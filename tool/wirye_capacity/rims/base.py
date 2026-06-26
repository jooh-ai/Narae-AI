"""RiMS 커넥터 인터페이스 + 취득 데이터모델."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class AcquiredTest:
    """RiMS에서 취득한 공급가능용량 테스트 1건 (17~18시 IGV 실시 윈도, 1시간 평균).

    cit=Comp Inlet Temp(°C), pressure=대기압(mbar), cc_meas=CC Gross 실측(MW).
    W(IGV)는 코어에서 온도밴드로 산정하므로 여기서 받지 않는다(사용자 확정: 밴드 유지).
    """
    date: str
    cit: float
    pressure: float
    cc_meas: float
    rh: float | None = None
    cp_meas: float | None = None
    cp_design: float | None = None
    gt_meas: float | None = None
    st_meas: float | None = None
    season: str | None = None


@runtime_checkable
class RimsConnector(Protocol):
    """RiMS 취득 인터페이스. mock / 실제(Excel-COM) 모두 이 형태를 따른다."""

    def acquire(self, date: str, start: str = "17:00") -> AcquiredTest:
        """date 의 start 시각부터 1시간(예: 17:00~18:00) 태그 평균을 취득."""
        ...
