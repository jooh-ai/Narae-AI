"""위례열병합발전소 공급가능용량 입찰 산정 툴 (Mode3_AOH1000).

Phase 1: 핵심 계산 엔진 (이론·보정·현실화).
Phase 2: 테스트결과 저장·List-up (store).
Phase 3: 온도 Profile 생성 (profile → 엑셀3 형식 .xlsx).
Phase 4: RiMS 커넥터 (rims: 인터페이스·mock·자동취득→누적; 실제 Excel-COM은 사내 결선).
Phase 5: 날씨 로더(weather, 엑셀3-1) + 검증 모드(verify, 시운전 대조).
엔드투엔드: pipeline.run_pipeline + cli (GUI는 ui.app, PySide6 — 사내 실행, 자동 import 안 함).
"""
from . import (constants, correction, curve, pipeline, profile, rims, store,
               theory, verify, weather)

__all__ = ["constants", "theory", "correction", "store", "profile", "rims",
           "weather", "verify", "pipeline", "curve"]
__version__ = "0.7.0"
