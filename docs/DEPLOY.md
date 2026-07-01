# 위례 공급가능용량 입찰 Tool — 사내 배포·RiMS 결선·시운전 가이드

> 대상: 사내 Windows PC(RiMS 애드인 + Excel 보유). 개발 환경에서 구현·검증된 `wirye_capacity`
> 패키지를 사내에서 ① 설치 ② RiMS 실연결 ③ 시운전(±0.5 MW)하는 절차.
> 코드 위치: `tool/wirye_capacity/` · 설계 전반: [`DESIGN.md`](DESIGN.md)

---

## 0. 한눈에

```
[1] 설치           pip install -r requirements + 테스트 57건 통과 확인
[2] RiMS 결선      excel_addin 에 엑셀1 경로·셀매핑 연결 → 수동 취득값과 대조
[3] 날씨 업로드     엑셀3-1(크롤링) 파일 경로 지정
[4] 실행           CLI 또는 GUI → 엑셀3 양식 입찰파일 생성 + 테스트 누적
[5] 시운전          기존 엑셀과 ±0.5 MW 대조(verify) → 합격 후 실입찰 전환
[6] 패키징(선택)    PyInstaller 로 .exe
```

현재 상태: **계산·저장·출력·곡선·엔드투엔드 전부 구현·검증 완료(57 tests).** 사내에서 할 일은
RiMS 실연결과 시운전뿐.

---

## 1. 사전 준비 (사내 PC 요구사항)

| 항목 | 요구 |
|---|---|
| OS | Windows (RiMS 애드인·Excel 구동) |
| Python | 3.10 이상 |
| Excel | RiMS `fnTagStat` 애드인이 로드되는 Excel (기존 사용 PC) |
| 파일 | 엑셀1(`RiMS 계산 Sheet` 포함), 엑셀3-1(날씨 크롤링 결과) |

설치 패키지:
```bat
pip install openpyxl xlwings PySide6
:: 곡선 기본(kernel)은 표준 라이브러리만 사용. 패키징 시 pyinstaller 추가.
```
> `xlwings` = RiMS 애드인 구동(Excel COM). `PySide6` = GUI. 둘 다 사내 전용.

---

## 2. 설치 & 검증

```bat
:: 1) 코드 가져오기 (git 또는 압축 해제) → tool\ 디렉터리
cd tool

:: 2) 의존성
pip install -r requirements.txt

:: 3) 자기검증 (엑셀4 셀값·보정값·곡선 회귀 57건)
python -m pytest -q
:: → 57 passed 확인되면 계산 로직은 정상
```

---

## 3. RiMS 실연결 (핵심)

기존 엑셀1의 `RiMS 계산 Sheet`를 **그대로 구동**한다(AG9에 시작시각 기입 → fnTagStat 재계산 → 8행 읽기).

### 3.1 셀 매핑 확인 — `wirye_capacity/rims/excel_addin.py`

```python
CELL_MAP = {
    "start":    "AG9",   # 테스트 시작 datetime 입력
    "cit":      "H8",    # Comp Inlet Temp (°C)
    "pressure": "J8",    # 대기압 (mbar)
    "rh":       "K8",    # 상대습도 (%)  ← 이론계산엔 60% 고정, 기록용
    "gt_meas":  "M8",    # GT Load (MW)
    "st_meas":  "N8",    # ST Load (MW)
    "cc_meas":  "O8",    # CC Gross (MW)  ← 보정값 산출의 실측값
}
```
> **반드시 실제 엑셀1 시트와 대조**해 셀 위치를 확정할 것. 다르면 `CELL_MAP`만 수정.
> 취득 윈도는 **17:00~18:00(IGV 실시)** 기준. `acquire(date, start="17:00")`.

### 3.2 연결 테스트

```python
from wirye_capacity.rims.excel_addin import ExcelAddinRimsConnector
conn = ExcelAddinRimsConnector(r"C:\경로\엑셀1.xlsx")   # RiMS 애드인 로드된 Excel 필요
acq = conn.acquire("2026-04-15", start="17:00")
print(acq.cit, acq.pressure, acq.cc_meas)
```
**검증**: 같은 날짜·시각을 엑셀1에서 수동 취득(AG9 입력)한 8행 값과 **일치**하는지 확인.
일치하면 RiMS 결선 완료.

---

## 4. 실행 방법

### 4.1 CLI (간단·자동화)

```bat
:: 신규 테스트 1건 취득 → 누적 → 엑셀3 양식 입찰파일 생성
python -m wirye_capacity run ^
    --date 2026-04-15 ^
    --workbook C:\경로\엑셀1.xlsx ^
    --forecast C:\경로\엑셀3-1.xlsx ^
    --db C:\경로\measurements.db ^
    --out C:\경로\입찰_온도Profile.xlsx ^
    --seed                  :: DB가 비었으면 기존 32건 적재(최초 1회)

:: 연속 보정곡선으로 산출하려면 --curve 추가
python -m wirye_capacity run ... --curve

:: 누적 테스트 목록
python -m wirye_capacity list --db C:\경로\measurements.db
```
> 생성된 `.xlsx`는 **Excel에서 열면** 6모드·온도Profile이 자동 재계산된다(fullCalcOnLoad).

### 4.2 GUI

```bat
python -m wirye_capacity.ui.app
```
입력: 테스트 날짜 · Degradation · 엑셀3-1(날씨) · 엑셀1(RiMS) · 출력경로 → **[▶ 실행]**.
결과: 온도별 현실화 Net 표 + 적용 대기압·신규 보정값·누적 건수, **List-up 탭**에 누적 테스트.

---

## 5. 시운전 (Commissioning) — 실입찰 전환 전 필수

**목적**: 기존 검증된 엑셀 결과를 "정답"으로, Tool이 **±0.5 MW 이내** 재현함을 확인.

### 5.1 골든 케이스 준비
(입력 + 정답출력) 한 세트. 예:
- 기존 엑셀4/엑셀3에서 특정 대기압·Deg로 산출한 **온도 Profile**(정답)
- 같은 입력으로 Tool 실행 → 출력

### 5.2 단계별 대조 (`verify`)

```python
from wirye_capacity.theory import TheoryEngine
from wirye_capacity.store import MeasurementStore
from wirye_capacity.profile import build_profile
from wirye_capacity.verify import read_reference_xlsx, compare_profile

eng = TheoryEngine(); s = MeasurementStore(r"C:\경로\measurements.db")
rows = build_profile(eng, s.correction_table(), pressure=1013, deg=1.028)

# 기존 엑셀4 'Mode3' Profile(A온도/D CC이론/G CC현실화)을 기준으로 대조
ref = read_reference_xlsx(r"C:\경로\기존_엑셀4.xlsx", layout="excel4")
rep = compare_profile(rows, ref, tol=0.5, fields=["cc_theory", "cc_real_gross"])
print(rep.summary())          # PASS/FAIL, 최대 차이 MW
for f in rep.failures:        # 불합격 항목(온도·필드·차이)
    print(f)
```
체크포인트: ① 실측(엑셀1 8행) ② 이론기준값(엑셀2 O열) ③ 보정값(엑셀4 J열) ④ 온도 Profile(엑셀3).

### 5.3 병행운전
배포 후 실제 테스트 **2~3 사이클** 동안 Tool과 수기 엑셀을 나란히 돌려 매번 대조 →
차이 로그 누적 → 신뢰 확보 후 전환.

---

## 6. 운영 (누적·갱신)

- **새 테스트마다**: `run --date ...` → 자동 취득·보정값 계산·DB 누적 → 보정 정확도 향상.
- **누적 위치**: `--db` SQLite 파일(백업 권장). `list`로 조회.
- **구간 vs 곡선**: 기본 구간(설명 쉬움), `--curve`로 연속곡선(매끄러움). 시운전에서 둘 다 비교 후 선택.
- **보정값 업데이트는 자동** — 별도 수기 입력 불필요(수기 입력은 백필/예외 fallback).

---

## 7. 패키징 (.exe, 선택)

```bat
pip install pyinstaller
pyinstaller --noconfirm --windowed --name 위례입찰툴 ^
    --add-data "wirye_capacity\templates\excel3_profile_template.xlsx;wirye_capacity\templates" ^
    --add-data "wirye_capacity\data;wirye_capacity\data" ^
    wirye_capacity\ui\app.py
:: dist\위례입찰툴\ 에 실행파일 생성. (xlwings·Excel은 PC에 설치돼 있어야 함)
```

---

## 8. 트러블슈팅

| 증상 | 원인·조치 |
|---|---|
| `PySide6 가 필요합니다` | `pip install PySide6` (GUI 전용) |
| `xlwings ... 사내 Windows 전용` | `pip install xlwings` + Excel·RiMS 애드인 확인 |
| 출력 Profile 값이 옛날 그대로 | **Excel에서 열기**(자동 재계산). 미리보기는 캐시값일 수 있음 |
| 외부링크 `#REF!` 경고 | 엑셀3 Sheet1의 구(舊) 네트워크 링크 — 입찰 계산엔 무관 |
| RiMS 취득값이 수동과 다름 | `CELL_MAP` 셀 위치 재확인(3.1), 취득 시각·윈도 확인 |

---

## 9. 남은 정합 항목 (시운전 중 결정)

1. **이론기준값 ±1~2 MW** — base-table 방식 vs 수기(엑셀2 테스트별 설계복수기압) 차이.
   시운전 체크포인트 ②에서 확인 → 엑셀2 복수기 설계곡선 추출로 정합하거나 base-table 표준화.
2. **곡선 bandwidth(현재 3.5°C)** — 데이터 누적되면 좁혀 정밀도↑.
3. **구간 vs 곡선 최종 채택** — 시운전 결과로 결정(토글로 즉시 전환 가능).

> 확정 파라미터: 입찰 상한 **Net 462 MW** · 온도 기준 **CIT** · W **밴드값(0/2/4/6)** · 대상 **Mode3**.
