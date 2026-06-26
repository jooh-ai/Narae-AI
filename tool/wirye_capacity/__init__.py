"""위례열병합발전소 공급가능용량 입찰 산정 툴 (Mode3_AOH1000).

Phase 1: 핵심 계산 엔진 (이론·보정·현실화).
Phase 2: 테스트결과 저장·List-up (store).
RiMS 취득·Profile 출력·GUI는 후속 Phase.
"""
from . import constants, correction, store, theory

__all__ = ["constants", "theory", "correction", "store"]
__version__ = "0.2.0"
