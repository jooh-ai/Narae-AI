# 사내 테스트 절차서 (단계별 상세) — 위례 공급가능용량 입찰 Tool

> 사내 Windows PC(Excel + RiMS 애드인)에서 **순서대로** 진행. 각 단계는 **합격 기준(GATE)** 이 있고,
> 통과해야 다음으로 넘어간다. 위험 단계(RiMS 실연결·시운전)는 한 줄 명령으로 확인하도록 구성.
> 사전 개요는 [`DEPLOY.md`](DEPLOY.md), 리뷰 내역은 [`REVIEW.md`](REVIEW.md) 참조.

---

## 준비물 체크
- [ ] Windows PC (RiMS 애드인이 로드되는 Excel 설치)
- [ ] Python 3.10+
- [ ] 코드 (`tool/` 디렉터리 — git clone 또는 압축 해제)
- [ ] 엑셀1 파일 (`RiMS 계산 Sheet` 포함)
- [ ] 엑셀3-1 파일 (날씨 크롤링 결과)
- [ ] **기준 자료 1건**: 과거 특정 테스트의 ① 엑셀1 수동 취득값(8행) ② 그때 제출한 엑셀3 온도 Profile

---

## STEP 0 — 설치 & 엔진 자기검증 (RiMS 없이)

**목적**: 계산 엔진이 이 PC에서 정상 동작하는지 먼저 확인(RiMS와 분리).

```bat
cd tool
pip install -r requirements.txt
pip install xlwings PySide6        :: 사내 전용(RiMS·GUI). 패키징 시 pyinstaller 추가
python -m pytest -q
```
**기대**: `60 passed`
**GATE 0**: 60건 통과해야 진행. 실패 시 Python 버전·openpyxl 설치 확인.

---

## STEP 1 — 엔진 단독 엔드투엔드 (mock, 오프라인)

**목적**: RiMS 없이 전 파이프라인이 돌고 엑셀3 파일이 생성되는지 확인.

```bat
python -m wirye_capacity run --date 2025-T01 --mock --seed ^
       --db %USERPROFILE%\wirye_test.db --out %USERPROFILE%\bid_test.xlsx
```
**기대 출력**: `적용 대기압 … / 신규 취득 CIT … / 누적 건수 : 33 / 입찰 파일 : …bid_test.xlsx`
**확인**: `bid_test.xlsx`를 Excel에서 연다 → `온도 Profile` 시트가 자동 재계산되어 −20~40°C × 6모드 값이 채워짐.
**GATE 1**: 파일이 생성되고 Excel에서 열려 6모드 값이 보이면 통과.

> ⚠ 테스트 끝나면 `%USERPROFILE%\wirye_test.db` 삭제(운영 DB와 분리). 운영은 STEP 5 이후 시작.

---

## STEP 2 — RiMS 셀 매핑 확인 (수작업, 가장 중요)

**목적**: 자동 취득이 읽을 셀이 실제 엑셀1과 맞는지 **눈으로** 확인.

1. 엑셀1을 직접 연다(RiMS 애드인 로드 상태).
2. `RiMS 계산 Sheet`에서 다음을 확인:
   - **시작시각 입력 셀** = `AG9` 가 맞는가?
   - **정리 8행**: `H8`=CIT, `J8`=대기압, `K8`=상대습도, `M8`=GT, `N8`=ST, `O8`=CC Gross 가 맞는가?
3. 다르면 `tool\wirye_capacity\rims\excel_addin.py` 의 `CELL_MAP` 을 실제 셀로 수정.

**GATE 2**: CELL_MAP이 실제 엑셀1과 일치(또는 수정 완료)해야 진행.

---

## STEP 3 — RiMS 실연결 단건 검증 (★ 1순위 리스크)

**목적**: 자동 취득값이 수동 취득값과 **일치**하는지 확인. (datetime·비동기·애드인 문제를 여기서 잡는다.)

1. **수동 기준 확보**: 엑셀1에서 과거 테스트 1건의 시작시각을 AG9에 직접 넣어 8행 값을 메모(CIT·대기압·CC Gross).
2. **자동 취득 실행**:
```bat
python -m wirye_capacity check-rims --workbook "C:\경로\엑셀1.xlsx" --date 2026-04-15 --start 17:00
```
**기대**: CIT/대기압/상대습도/GT·ST/CC Gross 출력.
3. **대조**: 출력값 = 수동 메모값(소수점 오차 무시)인가?

**GATE 3 (핵심)**:
- ✅ 일치 → RiMS 결선 완료.
- ❌ `숫자가 아님(#N/A/None)` 오류 → fnTagStat가 아직 서버 조회 중(비동기). `visible=True`로 Excel을 띄워 재계산 완료를 눈으로 확인하거나, 이미 RiMS 애드인이 켜진 **실행 중 Excel**에 붙이는 방식으로 조정.
- ❌ 값이 다름 → CELL_MAP(STEP 2) 또는 시작시각/시간창 재확인.

---

## STEP 4 — 엔드투엔드 단건 (실 RiMS → 입찰 파일)

**목적**: 실제 RiMS + 날씨로 입찰 파일을 생성.

```bat
python -m wirye_capacity run --date 2026-04-15 ^
       --workbook "C:\경로\엑셀1.xlsx" ^
       --forecast "C:\경로\엑셀3-1.xlsx" ^
       --bid-day "수요일, 4월 15일" ^
       --db %USERPROFILE%\wirye_commission.db --seed ^
       --out %USERPROFILE%\bid_20260415.xlsx
```
(`--bid-day` 라벨은 엑셀3-1 일자 첫 열 문자열 그대로. 생략 시 7일 중위 평균.)
**확인**: 출력 `적용 대기압(기준: …)`·`신규 취득 CIT/보정값`·`누적 건수`. 파일을 Excel에서 열어 온도 Profile 확인.
**GATE 4**: 파일 생성 + 신규 보정값이 상식 범위(겨울 +, 여름 −, 수 MW)면 통과.

---

## STEP 5 — 시운전 대조 (Commissioning, ±0.5 MW)

**목적**: 기존 검증된 엑셀 결과를 "정답"으로 Tool 출력이 ±0.5 MW 내인지 확인.

```bat
:: 기준 = 기존 방식으로 만든 온도 Profile(엑셀4 또는 엑셀3). 같은 대기압·Deg 조건으로 비교.
python -m wirye_capacity verify ^
       --ref "C:\경로\기존_온도Profile.xlsx" --layout excel4 ^
       --db %USERPROFILE%\wirye_commission.db ^
       --pressure 1013 --deg 1.028 --tol 0.5
```
**기대**: `PASS ✅ — N/N 합격, 최대 차이 … MW`
**GATE 5 (입찰 전환 기준)**:
- ✅ PASS → 정확도 검증 완료.
- ❌ FAIL → 출력되는 불합격 온도·항목(`✗ 25°C cc_real_gross …`)을 보고, 체크포인트별로 원인 추적
  (① 실측=STEP3 / ② 이론기준값=대기압·Deg·RH / ③ 보정값 / ④ Profile). REVIEW.md §3·§5 참조.
- `--layout` 은 기준 파일이 엑셀4 양식이면 `excel4`, Tool 생성본이면 `tool`.

---

## STEP 6 — 병행운전 (신뢰 확보)

**목적**: 실제 테스트 2~3 사이클(약 1~2개월) 동안 Tool과 수기 엑셀을 나란히.

1. 매 테스트마다 STEP 4 실행(운영 DB `wirye_commission.db` 계속 사용 → 누적).
2. 매번 STEP 5로 수기 결과와 대조, 차이 기록.
3. `python -m wirye_capacity list --db %USERPROFILE%\wirye_commission.db` 로 누적 확인.
**GATE 6**: 2~3회 연속 ±0.5 MW 유지되면 실입찰 전환.

> 누적될수록 정확↑. 데이터 충분해지면 `--curve`(연속 보정곡선)도 같은 명령에 붙여 비교 가능.

---

## STEP 7 — 패키징 (.exe, 선택)

GUI를 단독 실행파일로:
```bat
pip install pyinstaller
pyinstaller --noconfirm --windowed --name 위례입찰툴 ^
  --add-data "wirye_capacity\templates\excel3_profile_template.xlsx;wirye_capacity\templates" ^
  --add-data "wirye_capacity\data;wirye_capacity\data" ^
  --hidden-import win32com --hidden-import win32com.client ^
  wirye_capacity\ui\app.py
```
**확인**: `dist\위례입찰툴\위례입찰툴.exe` 실행 → 입력·실행·List-up 동작. **반드시 .exe 자체로 STEP 4 재확인**(스크립트 아닌 패키지에서 템플릿·xlwings 동작).

---

## 막히면
- 트러블슈팅 표: `DEPLOY.md` §8.
- RiMS/시운전에서 막힌 화면·오류 메시지를 캡처해 알려주시면 맞춰 조정합니다.
- GUI 실행: `python -m wirye_capacity.ui.app` (CLI 대신 화면으로 STEP 4·5 가능).
