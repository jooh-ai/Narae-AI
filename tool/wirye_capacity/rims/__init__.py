"""RiMS 취득 커넥터.

- base.py        : RimsConnector 인터페이스 + AcquiredTest 데이터모델
- mock.py        : 개발/테스트용 mock (시드 기반)
- excel_addin.py : 실제 — Excel COM + fnTagStat (Windows 사내 PC 결선)

코어(theory/correction/store)는 커넥터 구현에 의존하지 않는다(덕 타이핑).
"""
from .base import AcquiredTest, RimsConnector
from .mock import MockRimsConnector
from .opcua import OpcUaRimsConnector

__all__ = ["AcquiredTest", "RimsConnector", "MockRimsConnector", "OpcUaRimsConnector"]
