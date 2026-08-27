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
입력: 테스트 날짜·시각 · IGV Turn-up 실시 여부 · Degradation · 대기압 윈드파인더 파일
→ **[▶ 공급가능용량 산정]**.

결과: 온도별 예측 표(GT·ST·CC 이론 / 보정값 / GT·ST·CC 현실화 61구간) + 적용 대기압·
신규 보정값·누적 건수. **List-up 탭**에 누적 테스트.

산정은 계산·표시만 하고 파일을 만들지 않는다. 결과를 보고 저장할 때 표 위의
**[엑셀로 저장]** 을 눌러 그때 경로를 고른다 — 실행할 때마다 파일이 덮어써지지 않는다.
저장 시점에 누적 보정값 기준으로 다시 계산해 쓰며, 산정 이후 누적이 바뀌었으면
먼저 알린다.

**상대습도 RH** — 기본은 `취득값 사용(RiMS)`. MBL 습도 센서가 드리프트 중이라
(10개월에 10%p) 취득값이 담당자 표와 크게 어긋나는 회차가 있다. 두 습도계가
정상 편차를 벗어나면 **누적 반영이 보류**되고, 체크를 풀어 옳은 값을 넣어야
통과한다. 습도 1개가 보정값을 2~4.5 MW 움직인다.

**안전마진 계수는 화면에서 제거됐다**(2026-08-25). 실제로 쓰지 않기로 결정한
항목이다. CLI `--margin` 과 `margin.py` 는 자동화·검증용으로 남아 있다.

### 4.3 보정 방법 고르기 — `🔬 모델 선정` 탭

방법은 7가지다: 구간평균 · 커널회귀 · GP 5종(RBF / Matérn 5/2 / Matérn 3/2 /
지수 / Rational Quadratic). GP 는 **커널이 곡선의 성격**을 정하고 하이퍼파라미터는
커널마다 주변우도로 자동 적합한다 — 사람이 만질 값은 커널 하나다.

    ① 테스트셋 비율(%)·랜덤 시드·층화 여부·선정 기준(RMSE/MAE/R²)·후보 지정
    ② [▶ 모델 선정 실행]
    ③ 결과 두 장 — 학습셋 LOOCV 표 / 테스트셋 검증 표

절차는 **테스트셋 분리 → 학습셋만으로 LOOCV → 고른 모델로 테스트셋 예측**이다.
테스트셋은 선정 단계에서 전혀 쓰이지 않으므로 ②의 성적이 정직하다.

- **랜덤 시드**를 고정하므로 같은 설정이면 같은 분할·같은 결론이 나온다. 시드가
  없으면 누를 때마다 답이 달라져 "왜 이 모델인가" 를 재현할 수 없다.
- **층화 계층은 15~25°C 를 하나로 합친다.** 20~25°C 실측이 1건뿐이라 완전 랜덤이면
  20% 확률로 그 구간 학습 데이터가 0건이 된다. 이 병합은 **추출에만** 적용되고
  실제 보정 테이블(`C.BINS`)은 그대로다 — 보정 테이블까지 합치면 LOOCV 가 나빠지고
  (MAE 1.335 → 1.452) 20~25°C 입찰값이 2.2 MW 높아진다(미달 방향).
- **모든 후보를 같은 평가집합에서 채점한다.** 구간평균은 1건을 빼면 구간이 비어
  예측 불가가 되는 회차가 있어서, 집합이 다르면 n·SST 가 달라져 지표를 나란히
  놓을 수 없다.
- **R² 순위는 RMSE 순위와 항상 같다**(SST 가 후보 전체에 동일). 다른 관점은 MAE 다.
- 테스트셋이 10건 미만이면 경고가 뜬다. 7건 MAE 의 표준오차가 ±0.65 MW 라
  방법 간 차이가 그보다 작으면 우열을 가릴 수 없다.

**결과는 산정 탭에 자동 반영되지 않는다.** 수치를 보고 산정 탭 `보정 방법` 에서
직접 고른다 — 모델이 조용히 바뀌면 안 된다. 선택은 저장되어 다음 실행에도 유지되고
입찰파일 도장에 남는다.

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

## 7. 패키징 (.exe)

**spec 파일을 쓴다.** 옵션을 손으로 나열하면 번들 자원·제외 목록이 빠져 조용히 깨진다.

```powershell
pip install pyinstaller asyncua PySide6 openpyxl
cd tool
pyinstaller --noconfirm wirye_tool.spec
# → dist\WiryeBidTool\WiryeBidTool.exe
```

명령은 **한 줄씩** 붙여넣는다. 여러 줄을 한꺼번에 붙이면 PowerShell 이 뒷줄을 PyInstaller
프롬프트 입력으로 먹어 `Aborted by user request.` 로 끝난다.

빌드 후 번들 확인:

```powershell
python scripts\check_bundle.py dist\WiryeBidTool
```

배포는 `dist\WiryeBidTool\` **폴더째** 복사한다. `.exe` 만 옮기면 `_internal\` 이 없어
실행되지 않는다. 누적 DB·설정도 이 폴더에 생기므로 담당자 교체 시 폴더 전체를 넘긴다.

---

## 8. 트러블슈팅

| 증상 | 원인·조치 |
|---|---|
| `PySide6 가 필요합니다` | `pip install PySide6` (GUI 전용) |
| `xlwings ... 사내 Windows 전용` | `pip install xlwings` + Excel·RiMS 애드인 확인 |
| 출력 Profile 값이 옛날 그대로 | **Excel에서 열기**(자동 재계산). 미리보기는 캐시값일 수 있음 |
| 외부링크 `#REF!` 경고 | 엑셀3 Sheet1의 구(舊) 네트워크 링크 — 입찰 계산엔 무관 |
| RiMS 취득값이 수동과 다름 | `CELL_MAP` 셀 위치 재확인(3.1), 취득 시각·윈도 확인 |
| **exe 를 더블클릭했는데 아무 반응 없음** | 아래 8.1 |

### 8.1 더블클릭해도 아무 반응이 없을 때

`console=False` 로 빌드하므로 시작 중 예외가 화면에 남지 않는다. 그래서 런처가 직접
오류를 기록한다. 순서대로 본다.

**1) `dist\WiryeBidTool\wirye_error.log`**

실행할 때마다 시작 단계가 시각과 함께 쌓인다. 예외가 있으면 전체 추적이 들어간다.

```
· 11:11:14  런처: wirye_capacity.ui.app import
· 11:11:15  런처: main() 호출
· 11:11:15  Qt 확인
· 11:11:15  누적 DB 결정 : ...\wirye_measurements.db
· 11:11:15  QApplication 생성
· 11:11:16  Qt 플랫폼 'windows' · 화면 1920x1080@(0,0)
· 11:11:16  MainWindow 생성
· 11:11:17  show() 호출
· 11:11:17  창 상태 visible=True 1020x720@(100,100) 최소화=False
· 11:11:17  이벤트 루프 진입 — 여기까지 찍히면 시작은 성공이다
```

**마지막 줄이 어디인지가 곧 진단이다.**

| 마지막 줄 | 뜻 |
|---|---|
| `런처: main() 호출` 까지 | Qt import 나 그 직전에서 멈췄다 — 번들·DLL 문제 |
| `QApplication 생성` 까지 | Qt 플랫폼 플러그인 초기화에서 죽었다(예외 없이 abort) |
| `MainWindow 생성` 까지 | 창을 만드는 중 멈췄다 — DB·번들 자원 확인 |
| `이벤트 루프 진입` 이 찍혔다 | **시작은 성공했다.** 창이 안 보이면 표시 문제다 |

마지막 경우라면 바로 위의 `창 상태` 줄을 본다. `visible=True` 인데 화면에 없으면
좌표가 연결되지 않은 모니터 영역이거나 원격 세션 문제다. `Qt 플랫폼 · 화면` 줄의
해상도·좌표와 `창 상태` 의 좌표를 비교하면 알 수 있다.

**2) 로그가 아예 없으면** 프로세스가 시작조차 못 한 것이다 — 백신 차단이나 파일 손상.

```powershell
Get-Item .\WiryeBidTool.exe        # 파일이 격리돼 사라졌는지
Get-Process WiryeBidTool          # 떴다가 죽는지 (실행 직후 바로 확인)
python scripts\check_bundle.py .  # 번들 자원 손상 여부
```

**3) 환경 점검** — 번들 자원·DB 폴더 권한·Qt 초기화·PATH 의 다른 Qt DLL 을 한 번에 본다.

```powershell
.\WiryeBidTool.exe --selftest
```

결과가 대화상자로 뜨고 `wirye_error.log` 에도 저장된다. `Qt 초기화 실패` 나
`PATH 의 다른 Qt DLL` 에 ⚠ 가 있으면 그것이 원인이다 — 다른 Qt 프로그램의 DLL 이
먼저 잡히면 번들 DLL 대신 그것이 로드돼 조용히 죽는다.

**4) 그래도 안 잡히면** `wirye_tool.spec` 의 `console=False` → `True` 로 바꿔 재빌드하고
PowerShell 에서 실행한다. 콘솔에 그대로 출력된다.

> 과거 사례(2026-08): 첫 실행에서 누적 DB 를 만들고 **모달 안내 대화상자**를 띄우고
> 있었다. 모달은 이벤트 루프를 잡으므로, 그 대화상자가 뒤로 가거나 화면 밖에 놓이면
> 사용자에게는 "반응 없음" 으로만 보인다. 누적 DB 가 비어 있을 때만 타는 경로라
> **신규 PC 첫 실행에서만** 재현됐고, 지우고 다시 빌드할 때마다 같은 조건이 되살아났다.
> 지금은 모달을 쓰지 않고 창 안 배너로 알린다 — 이 실패 방식 자체가 없어졌다.

---

## 9. 남은 정합 항목 (시운전 중 결정)

1. **이론기준값 ±1~2 MW** — base-table 방식 vs 수기(엑셀2 테스트별 설계복수기압) 차이.
   시운전 체크포인트 ②에서 확인 → 엑셀2 복수기 설계곡선 추출로 정합하거나 base-table 표준화.
2. **곡선 bandwidth(현재 3.5°C)** — 데이터 누적되면 좁혀 정밀도↑.
3. **구간 vs 곡선 최종 채택** — 시운전 결과로 결정(토글로 즉시 전환 가능).

> 확정 파라미터: 입찰 상한 **Net 462 MW** · 온도 기준 **CIT** · W **밴드값(0/2/4/6)** · 대상 **Mode3**.
