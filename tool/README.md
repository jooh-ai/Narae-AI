# wirye_capacity — 위례 공급가능용량 입찰 산정 Tool

위례열병합발전소(Mode3_AOH1000) 공급가능용량 입찰값을, 공급가능용량 테스트 실측을 온도별로
누적·보정하여 자동 산정하는 툴. 설계 전반은 [`../docs/DESIGN.md`](../docs/DESIGN.md) 참조.

## 현재 상태 — Phase 1 (핵심 계산 엔진)

순수 Python 코어만 구현됨. RiMS 취득·Profile 출력·GUI는 후속 Phase.

```
wirye_capacity/
  constants.py     물리/사이트 상수 (P_corr, 450.4, W밴드, cap 462, 온도구간)
  theory.py        이론엔진: base_cc(CIT)×(1.028/Deg)/P_corr  (+W)
  correction.py    보정값 = 실측 − 이론 − W, 구간집계, 현실화 Net
  data/            base_table.json(61행), measurements_seed.json(실측 32건)
tests/             엑셀4 셀값 대조 검증 (14건)
```

## 빠른 사용 예

```python
from wirye_capacity.theory import TheoryEngine
from wirye_capacity.correction import correction_value, aggregate_bins, realized_net
import json, pathlib

eng = TheoryEngine()
# 이론기준값(IGV 미반영) — CIT 25.5°C, 대기압 1008 mbar, Deg 1.028
I = eng.theory_cc(25.5, 1008, 1.028)

# 새 테스트 1건의 보정값
corr = correction_value(cc_meas=414.5, theory_cc=I, w=6)

# 누적 실측으로 온도구간 보정 테이블
seed = json.loads((pathlib.Path("wirye_capacity/data/measurements_seed.json")).read_text())
table = aggregate_bins(seed)   # {(0,10): {'avg':5.78,'count':8,...}, ...}

# 현실화 Net (상한 462)
net = realized_net(eng.theory_cc_with_igv(25, 1013, 1.028), correction=-2.39)
```

## 테스트

```bash
cd tool && PYTHONPATH=. python3 -m pytest -q
```
