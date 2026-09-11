# Power Apps 구축 가이드 — 위례 근태 관리

> 사내 VDI 에서 Power Apps 생성 권한·라이선스·네트워크가 모두 확인되었다(2026-09).
> 이 문서만 따라가면 Teams 탭으로 쓰는 근태 앱을 만들 수 있다.
>
> 규칙 원천: [`../../worktime/data/combos.json`](../../worktime/data/combos.json) (106가지 조합)
> 가져오기용 CSV: `worktime/data/sp_*.csv`

## 0. 왜 Power Apps 가 엑셀보다 나은가 — 연쇄 드롭다운

엑셀에서는 유형·출근·퇴근 세 칸이 **서로를 모른다.** 그래서 `오전반 + 08:30~17:30` 같은
불가능한 조합을 넣을 수 있고, 넣은 뒤에 빨갛게 표시해 알려주는 수밖에 없다.

Power Apps 는 앞 칸의 선택에 따라 뒤 칸을 **걸러낸다.**

| 고른 것 | 다음 칸에 남는 항목 |
|---|---|
| 유형 = 오전반 | 출근 **2개** (13:00 · 13:30) |
| 오전반 + 13:00 | 퇴근 **4개** (16:00 · 16:30 · 17:00 · 17:30) |
| 유형 = 오후반반 | 출근 **2개** → 퇴근 **1개** (15:30) |
| 유형 = 오전반반 | 출근 **1개** (10:30) → 퇴근 9개 |
| 유형 = 근무 | 출근 3개 → 퇴근 18개 |

한 번에 보이는 최대 항목이 **18개**이고, 대부분은 1~5개다. 무엇보다
**규칙에 없는 조합은 목록에 나타나지 않으므로 애초에 고를 수 없다.**

## 0-1. SharePoint 목록 vs Dataverse for Teams

사내에서 두 경로 다 열려 있음이 확인되었다. **HTML 도구의 재현도는 둘이 사실상 같다** —
화면과 규칙 로직은 전부 Power Fx 이고 데이터 소스와 무관하다. 차이는 데이터 계층에서만
나며, HTML 의 기능 중 데이터 계층에 의존하는 것은 셋뿐이다.

| HTML 기능 | 데이터 계층 의존 | 판정 |
|---|---|---|
| 월 달력 · 셀 입력 팝업 · 화면 구성 | 없음 | 동일 |
| 연쇄 드롭다운 (규칙 원천 차단) | 없음 — 조합표 조회만 | 동일 |
| 30% 판정 · 조율 후보 (월 단위) | 약함 — 월 기록 수백 행 | 동일 |
| 개인 총량 · OT 잔여 | 없음 | 동일 |
| **탄력근무 3개월 집계** | **있음** | Dataverse 가 편하다 |
| **"본인 것만 수정" 강제** | **있음** | Dataverse 는 데이터 계층에서, SharePoint 는 앱 로직으로만 |
| **앱 없이 데이터 확인 · 엑셀 내보내기** | **있음** | **SharePoint 만 가능** |

### 탄력근무 3개월이 갈리는 이유

SharePoint 는 `Sum` · `CountRows` 같은 집계를 서버에 위임하지 못해 앱으로 끌어와 계산한다.
따라서 `데이터 행 제한`(최대 2000)에 걸린다. 3개월 × 24명 = 최대 2232행이라 이론상 초과다.

다만 이 설계는 **예외만 저장**한다(빈 기록 = 8시간 근무). 대정비 달에 OT 를 많이 써도
월 400~500행 수준이라 3개월 1500행 안쪽이고, 넘더라도 **월별로 세 번 나눠 읽으면** 된다.

```powerfx
// SharePoint 에서 3개월을 안전하게 읽는 법 — 한 번에 읽지 않고 월별로 이어 붙인다
Clear(colFlex);
ForAll(Sequence(3) As Mo,
    With({ ms: DateAdd(gvFlexStart, Mo.Value - 1, TimeUnit.Months) },
        Collect(colFlex,
            Filter(근태기록,
                근무일 >= ms,
                근무일 <= DateAdd(DateAdd(ms, 1, TimeUnit.Months), -1, TimeUnit.Days)))
    )
);
```

Dataverse 는 집계가 위임되므로 이런 우회가 필요 없다.

### 그래서 어느 쪽인가

**SharePoint 목록을 권한다.** 재현도 차이가 위 우회 한 줄로 사라지는 반면,
**앱이 잘못돼도 목록을 직접 열어 보고 고칠 수 있고 엑셀 내보내기가 기본**이라는 점은
Dataverse 로는 얻을 수 없다. 처음 도입할 때 이 안전장치가 가장 크다.

### 권하는 조합 — 앱은 Teams, 데이터는 SharePoint

캡처로 확인된 **Teams 안의 Power Apps 스튜디오에서 앱을 만들고**, 데이터는
**같은 팀 사이트의 SharePoint 목록**에 둔다. SharePoint 는 표준 커넥터라
추가 라이선스가 필요 없다.

- 앱은 Teams 탭으로 바로 열리고 (접근이 쉽다)
- 데이터는 목록에서 눈으로 보이고 엑셀로 빠진다 (안전하다)

나중에 승인 워크플로 · 형평성 집계처럼 확장이 커지면 Dataverse 로 옮긴다. 표·열 이름만
바뀌고 Power Fx 는 거의 그대로여서 이전 부담이 크지 않다.

## 1. 데이터 — SharePoint 목록 5개

두 팀이 함께 접근하는 Teams 채널(또는 SharePoint 사이트) 한 곳에 만든다.
30% 판정이 두 팀 합산이므로 데이터는 반드시 한 곳에 모여야 한다.

### 1-1. `조합표` — 규칙 엔진 (106행, 읽기 전용)

| 열 이름 | 타입 | 비고 |
|---|---|---|
| 조합코드 | 텍스트 (제목 열 이름 변경) | `근무 0830-1730` — **앱 수식에서는 `Title`** (§3-2-1) |
| 유형 | 텍스트 | 근무 · 오전반 · … |
| 출근 | 텍스트 | `08:30` (시각 없는 유형은 빈칸) |
| 퇴근 | 텍스트 | `17:30` |
| 실근로 | 숫자 (소수 2자리) | |
| 휴가 | 숫자 (소수 2자리) | |
| 충족 | 숫자 | 30% 인원 충족이면 1 |
| 구분 | 텍스트 | 근무 · 반차 · 반반차 · 건강검진 · 휴가·사외 |
| 휴가블록 | 텍스트 | 참고용 |

`sp_조합표.csv` 를 가져온다. **이 목록은 손으로 고치지 않는다** — 규칙이 바뀌면
`node worktime/gen_combos.js` 로 다시 뽑아 교체한다.

### 1-2. `명부` — 24행

| 열 이름 | 타입 | 선택지 |
|---|---|---|
| 이름 | 텍스트 (제목 열) | **앱 수식에서는 `Title`** (§3-2-1) |
| 팀 · 파트 · 직책 · 그룹 | 텍스트 | CSV 가져오기로 자동 생성된다 |
| 휴직 | 텍스트 | 휴직자만 `Y`, 나머지는 빈칸 |
| 사용자 | 사용자 또는 그룹 | 본인 근태만 보여주는 데 사용 — 가져오기 뒤 직접 추가 |
| 정렬 | 숫자 | 표시 순서 |

`sp_명부.csv` 를 가져온 뒤 **사용자 열만 추가해서 각자 계정으로 채운다.**

> **선택 항목(Choice) 열을 쓰지 않는 이유**: 드롭다운 목록은 `조합표` 에서 나오므로
> 열 자체를 선택 항목으로 만들 필요가 없다. 텍스트로 두면 **CSV 가져오기만으로 목록과
> 열이 함께 만들어지고**, `Patch` 수식도 `{Value: "..."}` 없이 문자열 그대로 넣으면 된다.

### 1-3. `근태기록` — 예외만 저장 (빈 기록 = 8시간 근무)

| 열 이름 | 타입 | 비고 |
|---|---|---|
| 키 | 텍스트 (제목 열) | `2026-09-07_박상호` — 중복 방지. **앱 수식에서는 `Title`** |
| 근무일 | 날짜 (시간 없음) | |
| 구성원 | 텍스트 | 명부의 이름 |
| 유형 · 출근 · 퇴근 | 텍스트 | 앱의 연쇄 드롭다운이 값을 넣는다 |
| 조합코드 | 텍스트 | 앱이 조립해 저장 |
| 실근로 · 휴가 | 숫자 (소수 2자리) | 조합표에서 읽어 **저장** |
| 충족 | 숫자 | 조합표에서 읽어 저장 |
| 구분 | 텍스트 | 조율 후보 판별용 |
| OT시작 · OT종료 | 텍스트 | `20:30` · `23:15` |
| OT시간 | 숫자 (소수 2자리) | 앱이 계산해 저장 |
| 석식 | 텍스트 | 자동 · 실시 · 미실시 |
| 주 | 숫자 | 그 달의 주 순번 — 주별 집계용 |
| 메모 | 텍스트 여러 줄 | |

> **실근로·휴가·충족을 저장하는 이유**: 매번 조합표를 조회하면 SharePoint 위임 제약에
> 걸려 느려진다. 저장 시점에 한 번 읽어 넣으면 집계가 단순 `Sum` 으로 끝난다.

### 1-4. `월설정` — OT 기본 가능시간 (달마다 다름)

| 열 이름 | 타입 |
|---|---|
| 연월 | 텍스트 (제목 열) — `2026-09`. 앱 수식에서는 `Title` |
| OT기본 | 숫자 |
| 정규종료 | 텍스트 — `17:30` (탄력근무 달은 `17:00` 등). 석식 휴게 계산에 쓴다 |
| 비고 | 텍스트 |

`sp_월설정.csv` 를 가져오면 두 달치가 들어간다. **OT기본은 담당자 확인 후 실제 값으로.**

### 1-5. `공휴일`

| 열 이름 | 타입 |
|---|---|
| 명칭 | 텍스트 (제목 열) — 앱 수식에서는 `Title` |
| 날짜 | 날짜 (시간 없음) |

`sp_공휴일.csv` 를 가져온다. 설날·추석·부처님오신날은 음력이라 매년 확인해 추가한다.

## 2. 작업 순서 — 이 순서대로 하면 된다

열을 30개 손으로 만들지 않는다. **데이터가 있는 목록 4개는 CSV 가져오기로 목록과 열을
한 번에 만들고**, 비어 있는 `근태기록` 만 직접 만든다.

| 단계 | 할 일 | 대략 |
|---|---|---|
| 1 | CSV 4개 가져와 목록 4개 생성 (`조합표` · `명부` · `공휴일` · `월설정`) | 20분 |
| 2 | `근태기록` 목록 생성 — 시작용 CSV 로 열 17개 한 번에 | 10분 |
| 3 | **1차 목표** — 앱에 「내 근태 입력」 화면 하나만 만들어 저장이 되는지 확인 | 40분 |
| 4 | 월 달력 · 30% 판정 · 조율 후보 화면 | 1시간 |
| 5 | 개인 요약 · 탄력근무 화면 | 1시간 |
| 6 | Teams 탭 게시 · 공유 | 10분 |

**3단계까지 되면 나머지는 수식을 붙여 넣는 반복 작업이다.** 한 번에 다 만들지 말고
3단계에서 저장·조회가 되는 것을 꼭 확인하고 넘어간다.

### 2-1. CSV 로 목록 4개 만들기

두 팀이 함께 있는 채널의 SharePoint 사이트에서 한다.

1. 채널 → **파일** 탭 → 우상단 `···` → **`SharePoint에서 열기`**
2. 좌측 **`홈`** → 상단 **`+ 새로 만들기`** → **`목록`**
3. **`Excel에서`**(From Excel) 또는 **`CSV에서`** 선택 → 파일 업로드
4. **「사용자 지정」** 화면에서 열 타입을 확인한다

| 목록 | 「제목」으로 둘 열 | 나머지 |
|---|---|---|
| `월설정` | `연월` | `OT기본` → 숫자 · 나머지 한 줄 텍스트 |
| `공휴일` | `명칭` | **`날짜` → 날짜 및 시간** |
| `명부` | `이름` | `정렬` → 숫자 · 나머지 한 줄 텍스트 |
| `조합표` | `조합코드` | `실근로`·`휴가`·`충족` → 숫자 · 나머지 한 줄 텍스트 |

5. 목록 이름을 표대로 넣고 **만들기** — 이름은 앱 수식이 참조하므로 정확히
6. 네 번 반복

> **「제목」 열은 하나뿐이라 서로 밀어낸다.** 한 열을 제목에서 빼면 다른 열이 자동으로
> 제목이 된다. 제목으로 둘 열을 먼저 지정하면 나머지는 알아서 정리된다.
> 제목 열은 원래 한 줄 텍스트이므로 `2026-09` 같은 값이 날짜로 변환될 걱정은 없다.

> **제목 열의 이름은 가져오기가 끝난 뒤 한 번 더 확인한다.** CSV 첫 열 이름이 그대로
> 제목 열 이름이 되는데, 앞에 보이지 않는 문자가 섞여 들어가는 일이 있다. 목록 화면에서
> 그 열의 `열 설정 → 편집` 을 열어 이름을 **지우고 다시 타이핑**해두면 뒤탈이 없다.

> **시각처럼 생긴 값은 텍스트로.** `07:30` · `17:30` 이 「시간」 타입으로 잡히면 안 된다.
> 진짜 날짜여야 하는 것은 **`공휴일` 의 `날짜` 하나뿐**이다 — 앱이
> `LookUp(공휴일, 날짜 = d)` 로 비교하므로 텍스트로 들어가면 소정근로일 계산이 어긋난다.
> 놓쳤으면 그 목록만 지우고 다시 가져오는 편이 빠르다(21행).

### 2-2. `근태기록` 목록 만들기

열이 17개라 손으로 추가하면 지루하다. **`sp_근태기록_시작.csv` 로 똑같이 가져오면**
목록과 열 17개가 한 번에 만들어진다. 샘플 2행이 들어 있고, 만든 뒤 지운다.

1. `+ 새로 만들기` → `목록` → **`CSV`** → `sp_근태기록_시작.csv`
2. 「사용자 지정」 화면에서 타입 지정

| 열 | 타입 |
|---|---|
| `키` | **제목** |
| **`근무일`** | **날짜 및 시간** ← 이 목록에서 유일하게 날짜여야 하는 열 |
| `실근로` · `휴가` · `충족` · `OT시간` · `주` | **숫자** |
| 나머지 전부 (`구성원`·`유형`·`출근`·`퇴근`·`조합코드`·`구분`·`OT시작`·`OT종료`·`석식`·`메모`) | **한 줄 텍스트** |

> `출근` · `퇴근` · `OT시작` · `OT종료` 는 `07:30` 처럼 생겼지만 **텍스트**여야 한다.

3. 목록 이름 **`근태기록`** → 만들기
4. **샘플 2행을 지운다** — 두 행을 선택해 `삭제`

> 샘플은 2020년 날짜에 구성원이 `샘플` 이라 지우지 않아도 집계에 영향은 없다.
> 그래도 지우는 편이 깔끔하다.

이후 이 목록은 **비어 있는 채로 운영한다**. 기록이 없는 날 = 8시간 근무이므로
미리 채워 넣을 것이 없다.

## 3. 앱 만들기 — 1차 목표

Teams → `Power Apps` → `새 앱` → 두 팀이 함께 있는 팀 선택 → 캔버스 앱.
`데이터 추가` 에서 **SharePoint** 커넥터로 목록 5개를 연결한다.

> **앱 설정에서 반드시 바꿀 것**: `설정 → 일반 → 데이터 행 제한` 을 **2000** 으로.
> 기본 500 이면 월 기록이 500행을 넘는 순간 집계가 조용히 틀린다.

**한 번에 다 만들지 않는다.** 먼저 입력 화면 하나로 저장이 되는 것을 확인하고,
그다음에 나머지 화면을 붙인다. 아래가 그 최소 화면이다.

### 3-1. 컨트롤 9개

`삽입` 메뉴에서 넣고, 각 컨트롤을 선택한 뒤 왼쪽 위 속성 목록에서 해당 속성을 골라
수식을 붙여넣는다. 이름은 왼쪽 「트리 뷰」에서 두 번 눌러 바꾼다.

| # | 넣을 컨트롤 | 바꿀 이름 | 역할 (설명일 뿐, 고르는 설정이 아니다) |
|---|---|---|---|
| 1 | 드롭다운 | `ddMe` | 구성원 |
| 2 | 날짜 선택 | `dpDate` | 근무일 |
| 3 | 드롭다운 | `ddType` | 유형 |
| 4 | 드롭다운 | `ddStart` | 출근 |
| 5 | 드롭다운 | `ddEnd` | 퇴근 |
| 6 | 텍스트 레이블 | `lblPreview` | 판정 미리보기 |
| 7 | 단추 | `btnSave` | 저장 |
| 8 | 세로 갤러리 | `galSaved` | 저장 결과 확인 |
| 9 | └ 아이콘 (휴지통) | `icoDel` | 잘못 넣은 기록 지우기 — 갤러리 **안** |

**컨트롤을 그 역할로 만드는 것은 「이름」과 「수식」 두 가지뿐이다.** 오른쪽 「역할」 열은
무엇에 쓰는지 적어둔 설명이고, Power Apps 어딘가에서 고르는 값이 아니다.

- 드롭다운을 넣으면 **「데이터 원본 선택」 패널**이 뜨는데 **닫아도 된다.**
  아래 수식을 `Items` 에 직접 넣는 편이 낫다
- **이름 바꾸기를 건너뛰지 않는다.** 다른 수식이 `ddMe.Selected.Value` 처럼 이름으로
  참조하므로, `Dropdown2` 인 채로 두면 수식을 전부 고쳐야 한다
- 콤보 상자를 넣었다면 **`SelectMultiple` 을 `false`** 로 끈다
- `ddMe` 만 `명부` 를 직접 쓰므로 **가장 먼저 만들면** 데이터 연결이 제대로 됐는지
  바로 확인할 수 있다 (이름 24개가 떠야 한다)

### 3-2. 수식

> **수식 바에는 `=` 오른쪽만 넣는다.** 아래에서 **`ddType.Items`** 처럼 굵게 쓴 것은
> 「`ddType` 을 선택하고 속성 목록에서 `Items` 를 고른 뒤, 그 아래 코드를 붙여넣어라」는
> 뜻이다. `Items = Distinct(...)` 처럼 속성 이름까지 붙여넣으면 Power Fx 가
> **비교식으로 읽어** `'Items'을(를) 인식할 수 없습니다` · `Error 및 Boolean 유형은
> 비교할 수 없습니다` 같은 오류가 난다.

> **모던 컨트롤은 기본 선택이 없다.** 클래식 드롭다운은 첫 항목이 자동 선택되지만
> 모던은 비어 있다. 그래서 `ddType` 에서 유형을 고르기 전에는 `ddStart` 가 비어 있는
> 것이 정상이다. 편하게 하려면 `ddType` 의 `DefaultSelectedItems` 에
> `[{Value: "근무"}]` 를 넣는다.

> **모던 드롭다운을 넣었다면 `ItemDisplayText` 도 확인한다.** 이 속성은 항목 하나의
> 표시 텍스트를 정하는 곳이라 `Distinct` 나 데이터 원본을 쓸 수 없다.
> `Distinct(...)` 는 `Value` 열 하나짜리 표를 돌려주므로 **`ThisItem.Value`** 로 둔다.
> 계속 걸리면 `삽입 → 클래식 → 드롭다운` 으로 바꾸면 이 속성 자체가 없어진다.

**`App.OnStart`** — 트리 뷰 맨 위 `App` 을 선택하고 `OnStart` 속성에

```powerfx
ClearCollect(colCombo, 조합표)
```

> **`OnStart` 는 편집 중에 저절로 실행되지 않는다.** 트리 뷰의 `App` 을 마우스 오른쪽 →
> **`OnStart 실행`** 을 눌러야 `colCombo` 가 채워진다. 이걸 안 하면 드롭다운이 전부
> 비어 보여서 뭔가 잘못된 줄 알게 된다 — 첫 시도에서 가장 많이 걸리는 함정이다.

**`ddMe.Items`**

```powerfx
Distinct(명부, Title)
```

**`ddType.Items`** · **`ddType.OnChange`**

```powerfx
Distinct(colCombo, 유형)
```
```powerfx
Reset(ddStart); Reset(ddEnd)
```

**`ddStart.Items`** · **`ddStart.OnChange`** — 고른 유형에서 가능한 출근만 남는다

```powerfx
Distinct(Filter(colCombo, 유형 = ddType.Selected.Value, !IsBlank(출근)), 출근)
```
```powerfx
Reset(ddEnd)
```

**`ddEnd.Items`** — 유형 + 출근에서 가능한 퇴근만 남는다

```powerfx
Distinct(
    Filter(colCombo, 유형 = ddType.Selected.Value, 출근 = ddStart.Selected.Value),
    퇴근
)
```

> **제목 열은 Power Apps 에서 `Title` 이다 — 아래 수식이 이미 그렇게 되어 있다.**
> SharePoint 목록 화면에는 `조합코드` · `키` 로 보이지만 Power Apps 에는 `Title` 로
> 노출된다(확인됨, §3-2-1). 반대로 CSV 로 만든 사용자 지정 열(`유형`·`출근`·`퇴근`·
> `근태기록` 의 `조합코드` 등)은 이름 그대로 쓴다.

**`lblPreview.Text`** — 저장 전에 판정을 보여준다

```powerfx
With({ code:
    If(IsBlank(ddStart.Selected.Value),
       ddType.Selected.Value,
       ddType.Selected.Value & " "
         & Substitute(ddStart.Selected.Value, ":", "") & "-"
         & Substitute(ddEnd.Selected.Value, ":", ""))
},
    With({ c: LookUp(colCombo, Title = code) },
        If(IsBlank(c),
           "✗ 규칙에 없는 조합 — " & code,
           code & "   실근로 " & c.실근로 & "h · 휴가 " & c.휴가 & "h · "
             & If(c.충족 = 1, "30% 충족", "30% 미충족"))
    )
)
```

**`lblPreview.Color`** — 빨강: 규칙에 없음 · 주황: 30% 미충족 · 초록: 충족

```powerfx
With({ c: LookUp(colCombo, Title =
    If(IsBlank(ddStart.Selected.Value), ddType.Selected.Value,
       ddType.Selected.Value & " " & Substitute(ddStart.Selected.Value, ":", "")
         & "-" & Substitute(ddEnd.Selected.Value, ":", ""))) },
    If(IsBlank(c), RGBA(179, 38, 30, 1),   // 규칙에 없는 조합 — 저장 안 됨
       c.충족 = 1, RGBA(15, 123, 79, 1),   // 8시간 인정 — 30% 인원에 포함
                   RGBA(138, 90, 0, 1))    // 규칙에는 맞지만 30% 인원에 안 들어감
)
```

**`btnSave.OnSelect`** — 조합표에서 값을 읽어 함께 저장한다

```powerfx
Set(gvCode,
    If(IsBlank(ddStart.Selected.Value),
       ddType.Selected.Value,
       ddType.Selected.Value & " "
         & Substitute(ddStart.Selected.Value, ":", "") & "-"
         & Substitute(ddEnd.Selected.Value, ":", "")));
Set(gvC,   LookUp(colCombo, Title = gvCode));
Set(gvKey, Text(dpDate.SelectedDate, "yyyy-mm-dd") & "_" & ddMe.Selected.Value);
Set(gvRec, LookUp(근태기록, Title = gvKey));

If(IsBlank(gvC),
    Notify("규칙에 없는 조합입니다 — " & gvCode, NotificationType.Error),

    Patch(근태기록,
        If(IsBlank(gvRec), Defaults(근태기록), gvRec),
        {
            Title:    gvKey,
            근무일:   dpDate.SelectedDate,
            구성원:   ddMe.Selected.Value,
            유형:     ddType.Selected.Value,
            출근:     ddStart.Selected.Value,
            퇴근:     ddEnd.Selected.Value,
            조합코드: gvCode,
            실근로:   gvC.실근로,
            휴가:     gvC.휴가,
            충족:     gvC.충족,
            구분:     gvC.구분
        });
    Refresh(근태기록);
    Notify("저장 완료 — " & gvKey & " · " & gvCode, NotificationType.Success)
)
```

**`galSaved.Items`** — 저장된 것이 바로 보인다

```powerfx
Sort(Filter(근태기록, 구성원 = ddMe.Selected.Value), 근무일, SortOrder.Descending)
```

갤러리 안 레이블 하나의 `Text`

```powerfx
ThisItem.Title & "   " & ThisItem.조합코드 & "   실근로 " & ThisItem.실근로 & "h"
```

**`icoDel.OnSelect`** — 잘못 넣은 기록 지우기

**삭제는 「기록을 없애는 것」이 아니라 「8시간 정상 근무로 되돌리는 것」이다.**
기록 없음 = 8시간 근무가 이 설계의 전제이므로, 잘못 넣었으면 지우는 것이 정답이다.

`galSaved` 를 **먼저 선택**한 뒤 `삽입 → 아이콘 → 휴지통` 을 넣고 이름을 `icoDel` 로
바꾼다. 트리 뷰에서 `galSaved` 아래에 들여쓰여 들어갔는지 확인한다.

```powerfx
Set(gvDelKey, ThisItem.Title);
Remove(근태기록, ThisItem);
Refresh(근태기록);
ClearCollect(colRec, Filter(근태기록, 근무일 >= gvMonthStart, 근무일 <= gvMonthEnd));
Notify("지웠습니다 — " & gvDelKey & " 는 8시간 근무로 계산됩니다",
       NotificationType.Success)
```

> **`ThisItem.Title` 을 먼저 변수에 담는다.** `Remove` 뒤에는 `ThisItem` 이 사라져
> 알림 문구에 쓸 수 없다.

`icoDel.Color` 는 실수로 누르기 쉬우므로 빨강으로 구분한다 — `RGBA(179, 38, 30, 1)`.
좌표는 행 오른쪽 끝(`X` = 행 너비 − 44 · `Y` 8 · 24 × 24)에 두고 `Title2.Width` 를
그만큼 줄인다.

**실수 방지 — 두 번 눌러야 지워지게 (권장).** `근태기록` 은 전원이 함께 쓰는 목록이라
오클릭이 남의 기록을 지울 수 있다.

```powerfx
If(gvDelArm = ThisItem.Title,
    Set(gvDelKey, ThisItem.Title);
    Remove(근태기록, ThisItem);
    Refresh(근태기록);
    ClearCollect(colRec, Filter(근태기록, 근무일 >= gvMonthStart, 근무일 <= gvMonthEnd));
    Set(gvDelArm, Blank());
    Notify("지웠습니다 — " & gvDelKey & " 는 8시간 근무로 계산됩니다",
           NotificationType.Success),

    Set(gvDelArm, ThisItem.Title);
    Notify("한 번 더 누르면 지워집니다 — " & ThisItem.Title,
           NotificationType.Warning))
```

무장 상태가 보이도록 **`icoDel.Icon`** 도 바꾼다.

```powerfx
If(gvDelArm = ThisItem.Title, Icon.Warning, Icon.Trash)
```

> **앱을 만드는 중이라면 SharePoint 목록에서 직접 지우는 편이 빠르다.** 채널 →
> `파일` → `···` → `SharePoint에서 열기` → `근태기록` → 행 체크 → `삭제`.

### 3-2-0. 수식을 넣을 때 반드시 지킬 세 가지

세 번 다 걸렸던 함정이다. 오류 20개가 한 번에 뜨는 것은 거의 이 중 하나다.

**1. 열거형은 정규화된 이름으로 쓴다.** `Months` · `Days` 는 인식되지 않는다.

| 안 됨 | 됨 |
|---|---|
| `DateAdd(d, 1, Months)` | `DateAdd(d, 1, TimeUnit.Months)` |
| `DateAdd(d, -1, Days)` | `DateAdd(d, -1, TimeUnit.Days)` |
| `DateDiff(a, b, Days)` | `DateDiff(a, b, TimeUnit.Days)` |
| `FontWeight = Bold` | `FontWeight.Bold` |

`'Months'을(를) 인식할 수 없습니다` + `함수 'DateAdd'에 일부 잘못된 인수가 있습니다`
가 **짝으로** 뜨면 이것이다.

**2. 붙여넣기 전에 `Ctrl+A` 로 기존 값을 지운다.** 단추의 `OnSelect` 기본값은 `false`,
레이블의 `Text` 기본값은 `"Text"` 다. 커서만 두고 붙여넣으면 앞에 그대로 남아
`falseSet(gvMonthStart, …)` 같은 것이 된다. 증상은 이렇게 뜬다.

```
'falseSet'은(는) 알 수 없거나 지원되지 않는 함수입니다.
```

**4. 레이블을 좁게 쓸 때는 `PaddingTop` · `PaddingBottom` 을 0 으로 한다.** 기본값이
5 + 5 = 10px 이고 글자 높이(기본 `Size` 13 ≈ 17px)와 합치면 **27px** 가 필요하다.
`Height` 가 그보다 작으면 내용이 넘쳐 **오른쪽 끝에 세로 스크롤바(회색 막대)** 가 생긴다.
칸마다 회색 막대가 보이면 이것이다 — 컨트롤 종류 문제가 아니다.

| `Height` | 기본 여백으로 | 여백 0 으로 |
|---|---|---|
| 28 이상 | 괜찮다 | 괜찮다 |
| 16 · 22 · 24 | ✗ 스크롤바 | 괜찮다 |

두 줄짜리 레이블(`lblCell` 처럼 `Char(10)` 을 쓰는 것)은 글자 높이가 두 배이므로
`Size` 를 9 로 줄이고 `Height` 를 템플릿 전체(26)로 준다.

**3. 갤러리 안 레이블을 복사해 화면에 붙이지 않는다.** 갤러리 안 레이블의 `OnSelect`
기본값은 `Select(Parent)` 인데, 화면으로 나오면 부모가 화면이 되어 오류가 된다.

```
OnSelect 속성이 없는 컨트롤의 Select
```

고치는 법은 그 컨트롤의 **`OnSelect` 를 전체 선택해 지우는 것**이다. 화면에 놓을
레이블은 복사하지 말고 `삽입` 에서 새로 넣는 편이 낫다.

### 3-2-1. 제목(Title) 열은 Power Apps 에서 `Title` 이다 (확인됨)

SharePoint 목록을 만들 때 제목(Title) 열의 **이름을 바꿔도 Power Apps 에는 원래 이름
`Title` 로 노출된다.** 목록 화면에서는 `조합코드` · `키` 로 보이므로 헷갈리기 쉽다.
반대로 CSV 가져오기로 생긴 **사용자 지정 열은 이름이 그대로** 노출된다.

| 목록 | SharePoint 화면 | Power Apps |
|---|---|---|
| `조합표` | 조합코드 | **`Title`** (`조합코드` 는 없다) |
| `근태기록` | 키 | **`Title`** — 단, `조합코드` 는 사용자 지정 열이라 그대로 있다 |
| `명부` | 이름 | **`Title`** |
| `월설정` | 연월 | **`Title`** |
| `공휴일` | 명칭 | **`Title`** |

그래서 증상은 늘 같은 모양이다 — `유형` · `출근` · `퇴근` · `구성원` 같은 **보통 열은 다
되는데 제목 열 하나만** `'조합코드'을(를) 인식할 수 없습니다` 로 뜬다.

**어느 목록이든 30초에 확인하는 법.** 레이블 아무거나 골라 `Text` 수식 바에 이렇게까지만
친다. 마지막 점을 찍는 순간 **그 목록의 열 이름 전체가 자동 완성 목록으로 뜬다.**

```powerfx
First(조합표).
```

**목록에 뜬 이름은 손으로 타이핑하지 말고 자동 완성에서 골라 넣는다.** CSV 가져오기로
만든 열은 이름 앞에 눈에 보이지 않는 문자(BOM)가 붙어 있을 수 있어, 똑같아 보이는
글자를 쳐도 맞지 않는 경우가 있다. 골라 넣으면 이 문제까지 같이 해결된다.

> **`이름` 은 우리가 만든 열이 아니다.** 자동 완성에 `이름` · `만든 날짜` · `수정한 사람`
> · `첨부 파일` · `ID` 같은 것이 섞여 보이는데, SharePoint 가 모든 목록에 자동으로 넣는
> 내장 열이다. 특히 `명부` 에서 `Distinct(명부, 이름)` 이라고 쓰면 우리가 원하는 사람
> 이름이 아니라 **이 내장 열을 읽게 되므로 `Distinct(명부, Title)` 로 써야 한다.**

**제목 열을 아예 안 쓰는 대안.** 계속 헷갈리면 SharePoint 에서 `코드` · `기록키` 같은
**새 사용자 지정 열**(한 줄 텍스트)을 만들어 쓰면 된다. 사용자 지정 열은 이름이 그대로
노출되므로 혼선이 없다. `근태기록` 은 비어 있어 열만 추가하면 되고, `조합표` 는
`sp_조합표.csv` 를 다시 가져와 채운다. 다만 `Title` 로 쓰면 되는 일이라 굳이 권하지 않는다.

> **갤러리에 아무 글자도 안 보이는 것은 오류가 아니다.** `근태기록` 이 비어 있으면
> `galSaved` 에 행이 0개라 레이블도 그려지지 않는다. 이 단계에서 봐야 할 것은 화면이
> 아니라 **왼쪽 `앱 검사 (오류)` 목록**이다.

### 3-3. 확인 — 여기까지 되면 나머지는 반복 작업이다

| 확인할 것 | 기대 |
|---|---|
| `ddType` 을 열면 | 11개 (근무 · 오전반 · … · 휴직) |
| 유형 `오전반` 을 고르면 `ddStart` | **2개** (13:00 · 13:30) |
| `오전반` + `13:00` 에서 `ddEnd` | **4개** (16:00 · 16:30 · 17:00 · 17:30) |
| 유형 `오후반반` 을 고르면 `ddEnd` | **1개** (15:30) |
| 유형 `연차` 를 고르면 `ddStart` | 비어 있음 (시각이 필요 없다) |
| `오전반` + `13:00` + `17:00` 미리보기 | `오전반 1300-1700 실근로 4h · 휴가 4h · 30% 미충족` |
| `근무` + `08:30` + `17:30` 미리보기 | `근무 0830-1730 실근로 8h · 휴가 0h · 30% 충족` |
| 저장 → `galSaved` | 방금 저장한 행이 보인다 |
| SharePoint `근태기록` 목록 | 같은 행이 들어가 있고 실근로 · 휴가 · 충족 · 구분이 채워져 있다 |
| 같은 날짜로 다시 저장 | 행이 늘지 않고 **덮어써진다** (키가 같으므로) |
| 휴지통을 두 번 누르면 | 행이 사라지고 그 날은 다시 8시간 근무로 계산된다 |

**규칙에 없는 조합을 만들 수 없다는 것**이 핵심이다. `오전반` 을 골랐을 때 `08:30` 이
목록에 아예 없으므로 고를 수가 없다. 엑셀에서 사후에 빨갛게 표시하던 것이
입력 단계에서 차단된다.

### 3-4. 다음에 붙일 화면들

1차 목표가 확인되면 아래 화면을 하나씩 붙인다. 수식은 §4 에 있다.

| 화면 | 용도 | 주 사용자 | 단계 |
|---|---|---|---|
| `Screen1` | 내 근태 입력 — 연쇄 드롭다운 | 전원 (매일) | 3단계 ✔ |
| `scrMonth` | 월 달력 — 날짜별 30% 판정 · 미달일 · 조율 후보 | 전원 (조율용) | 4단계 ✔ |
| `scrSummary` | 개인 요약 — 총량 · OT 잔여 · 주별 64h | 본인 | 6-3 (§3-7 5-3 · §4-7) |
| `scrGrid` | 매트릭스 — 23명 × 2주 | 전원 (조율용) | 6단계 ✔ (§3-8) |
| `scrFlex` | 탄력근무 3개월 평균 52h | 관리 | 7단계 (§4-8) |


### 3-5. 4단계 — 월 달력 · 30% 판정 화면 만들기

3단계와 같은 방식이다. **컨트롤을 넣고 이름을 바꾸고 §4 의 수식을 붙인다.**

`새 화면` → 빈 화면 → 트리 뷰에서 이름을 **`scrMonth`** 로 바꾼다.

| # | 넣을 컨트롤 | 이름 | 붙일 수식 |
|---|---|---|---|
| 1 | 텍스트 레이블 | `lblMonth` | §4-2 `lblMonth.Text` — 상단 요약 |
| 2 | 단추 | `btnPrev` | §4-1 `btnPrev.OnSelect` · `Text` 는 `"◀ 이전 달"` |
| 3 | 단추 | `btnNext` | §4-1 `btnNext.OnSelect` · `Text` 는 `"다음 달 ▶"` |
| 4 | 세로 갤러리 | `galMonth` | §4-2 `Items` · `TemplateFill` |
| 5 | └ 갤러리 안 레이블 | `lblDay` | §4-2 `lblDay.Text` |
| 6 | └ 갤러리 안 레이블 | `lblCnt` | §4-2 `lblCnt.Text` |
| 7 | 텍스트 레이블 | `lblCandHead` | §4-3 `lblCandHead.Text` |
| 8 | 세로 갤러리 | `galCandidate` | §4-3 `Items` |
| 9 | └ 갤러리 안 레이블 | `lblCand` | §4-3 `lblCand.Text` |
| 10 | 단추 | `btnToMy` | `Navigate(Screen1)` · `Text` 는 `"근태 입력 ▶"` |

입력 화면(`Screen1`)에도 단추 하나를 더해 오갈 수 있게 한다 — `Navigate(scrMonth)`.

**순서가 중요한 것 세 가지.**

1. **`App.OnStart` 를 §4-1 전체로 먼저 바꾸고 `OnStart 실행`** 을 누른다.
   `galMonth` 가 `gvActive` · `gvNeed` · `colRec` 를 쓰므로 이게 먼저다
2. **`설정 → 일반 → 데이터 행 제한` 을 2000** 으로. 기본 500 이면 기록이 늘었을 때
   집계가 조용히 틀린다
3. 갤러리 안 레이블은 **갤러리를 먼저 선택한 뒤 삽입**해야 갤러리 안으로 들어간다.
   트리 뷰에서 `galMonth` 아래에 들여쓰여 보이는지 확인한다

**좌표 (1366 × 768 기준).** 컨트롤을 선택하고 수식 바에서 `X`·`Y`·`Width`·`Height`
속성을 골라 숫자만 넣는다. 마우스로 끌어 맞추면 갤러리 안 레이블이 밖으로 나가는 사고가
난다.

| 컨트롤 | X | Y | Width | Height | 그 외 |
|---|---|---|---|---|---|
| `lblMonth` | 40 | 24 | 1286 | 40 | `Size` 16 · `FontWeight` `Bold` |
| `btnPrev` | 40 | 76 | 120 | 40 | |
| `btnNext` | 172 | 76 | 120 | 40 | |
| `btnToMy` | 1166 | 76 | 160 | 40 | |
| `galMonth` | 40 | 132 | 430 | 596 | `TemplateSize` 44 |
| └ `lblDay` | 12 | 8 | 110 | 28 | |
| └ `lblCnt` | 130 | 8 | 288 | 28 | |
| `lblCandHead` | 500 | 132 | 826 | 36 | `FontWeight` `Bold` |
| `galCandidate` | 500 | 176 | 826 | 552 | `TemplateSize` 44 |
| └ `lblCand` | 12 | 8 | 800 | 28 | |

> 갤러리는 `삽입 → 갤러리 → 빈 세로` 를 쓴다. `제목 및 부제목` 을 고르면 쓰지 않는
> 레이블이 딸려 들어온다.

> **갤러리 안 레이블의 `X`·`Y` 는 「행 기준」이다.** 갤러리 위치와 무관한 작은 숫자다.
> 이걸 안 넣으면 `lblDay` 와 `lblCnt` 가 둘 다 (0, 0) 에 놓여 **글자가 두 겹으로
> 겹쳐 보인다** — 날짜 숫자가 이상하게 뭉개져 보이면 이것이다.

> **단추의 `Text` 도 넣는다.** 안 넣으면 트리 뷰와 화면에 `버튼` 으로 남는다.
> `btnToMy` 는 `"근태 입력 ▶"`, `btnPrev` 는 `"◀ 이전 달"`, `btnNext` 는 `"다음 달 ▶"`.

**확인표**

| 확인할 것 | 기대 |
|---|---|
| `lblMonth` | `2026-09   모수 23명 · 필요 7명   |   미달일 0일   직책자 없는 날 0일` |
| 갤러리 행 수 | 30개 (9월) |
| 9월 5·6일 (토·일) | 회색 · `휴일` |
| 3단계에서 저장한 9월 10일 | 초록 · `23 / 7명` (8시간 근무라 충족) |
| 입력 화면에서 `연차` 로 저장하고 돌아오면 | 9월 10일이 `22 / 7명` 으로 줄어든다 |
| 같은 날 17명이 연차·반차면 | 빨강 · `6 / 7명   ✗ 1명 부족` |
| 빨간 날을 누르면 `galCandidate` | 바꿀 수 있는 사람만 (건강검진 · 연차 제외) |

> **미달일 0일이 정상이다.** `근태기록` 이 비어 있으면 전원 8시간 근무로 보므로
> 모든 날이 초록이다. 예외를 넣기 시작해야 판정이 움직인다.

### 3-6. 판정이 실제로 움직이는지 확인 — 4건이면 된다

기록이 없으면 전부 초록이라 화면만 보고는 계산이 맞는지 알 수 없다. **조합표에서 고른
실제 값 4건**으로 집계 · 직책자 · 후보 필터를 한 번에 검증한다.

`Screen1` 에서 날짜를 **2026-09-15** 로 두고 4번 저장한다.

| 구성원 | 유형 | 출근 | 퇴근 | 예상 판정 |
|---|---|---|---|---|
| 김동환 (팀장) | `연차` | — | — | 실근로 0h · 휴가 8h · 미충족 |
| 정병철 (파트장) | `오전반` | `13:00` | `17:30` | 실근로 4.5h · 휴가 4h · 미충족 |
| 박상호 | `근무` | `08:30` | `16:30` | 실근로 7h · 휴가 0h · 미충족 |
| 최규석 | `검진` | `08:00` | `12:00` | 실근로 4h · 휴가 4h · 미충족 |

`scrMonth` 에서 9월 15일 행을 본다.

| 확인할 것 | 기대 | 무엇을 증명하나 |
|---|---|---|
| 15일 행 | `19 / 7명` · 초록 | 23 − 4 = 19. 인원 집계 |
| 15일 선택 후 `lblCandHead` | `9월 15일  ✓ 충족  ·  조율 가능 2명` | 연차 · 검진은 후보 제외 |
| `galCandidate` | `정병철 오전반 1300-1730` · `박상호 근무 0830-1630` 두 줄 | 후보 필터 |
| `lblMonth` | `미달일 0일` | 19 ≥ 7 이므로 미달 아님 |

**빨강 · 노랑은 임계값을 잠깐 올려 확인한다** — 17명분을 입력할 필요가 없다.
`App.OnStart` 의 해당 한 줄만 임시로 바꾸고 `OnStart 실행` 을 누른다.

| 임시 교체 | 기대 |
|---|---|
| `Set(gvNeed, 20);` | 15일이 **빨강** · `19 / 20명   ✗ 1명 부족` · `미달일 1일` |
| `Set(gvLeads, 2);` | 15일이 **노랑** · `⚠ 직책자 0명` · `직책자 없는 날 1일` |

> **확인 뒤 반드시 되돌린다.** 빨강이 노랑보다 우선순위가 높으므로 둘을 동시에
> 바꾸면 노랑을 볼 수 없다. 한 번에 하나씩 바꾼다.

```powerfx
Set(gvActive, CountRows(colMembers));
Set(gvNeed,   RoundUp(gvActive * 0.3, 0));
Set(gvLeads,  CountRows(colLeads));
```

> **테스트 기록은 지운다.** `Screen1` 의 `galSaved` 에서 휴지통으로 지우거나,
> SharePoint `근태기록` 목록에서 9월 15일 4행과 3단계에서 넣은 9월 10일 행을 지우면
> 깨끗한 상태로 운영을 시작할 수 있다.


### 3-7. 5단계 — OT 입력과 개인 요약

세 조각으로 나눠 순서대로 한다. 뒤 조각이 앞 조각의 값을 쓴다.

| 조각 | 무엇을 | 왜 먼저인가 |
|---|---|---|
| 5-1 | `App.OnStart` · `btnPrev` · `btnNext` 를 월 갱신 블록으로 통합 (§4-1) | `colDays` · `gvWorkdays` 가 없으면 총량과 주별 집계를 못 한다 |
| 5-2 | `Screen1` 에 OT 입력 4개 추가 · `btnSave` 확장 | OT 시간이 저장되지 않으면 요약에 쓸 값이 없다 |
| 5-3 | `scrSummary` — 개인 요약 (§4-7) | |

#### 5-2. `Screen1` 에 추가할 컨트롤 5개

| # | 컨트롤 | 이름 | 넣을 값 |
|---|---|---|---|
| 10 | 텍스트 입력 | `txtOtS` | `HintText` `"OT 시작 20:30"` · `Default` 는 `""` |
| 11 | 텍스트 입력 | `txtOtE` | `HintText` `"OT 종료 23:15"` · `Default` 는 `""` |
| 12 | 드롭다운 | `ddDinner` | `Items` `["자동", "실시", "미실시"]` — 기본 선택은 넣지 않아도 된다 |
| 13 | 텍스트 레이블 | `lblOt` | §4-5 `lblOt.Text` |
| 14 | 텍스트 입력 | `txtNote` | `HintText` `"메모"` · `Default` 는 `""` |

> **`ddDinner` 의 기본 선택은 수식 안에서 처리한다.** `DefaultSelectedItems` 는 모던
> 드롭다운·콤보 상자에만 있고 **클래식 드롭다운에는 `Default`(문자열)** 다. 컨트롤
> 종류에 따라 이름이 달라 헷갈리므로, `lblOt.Text` 와 저장 수식에서
> `Coalesce(ddDinner.Selected.Value, "자동")` 로 감싸 **비어 있으면 `자동`** 이 되게
> 한다. 그러면 기본 선택 속성을 아예 넣지 않아도 된다.
>
> | 컨트롤 | 속성 | 값 |
> |---|---|---|
> | 모던 드롭다운 · 콤보 상자 | `DefaultSelectedItems` | `[{Value: "자동"}]` |
> | 클래식 드롭다운 | `Default` | `"자동"` |
>
> 왼쪽 위 속성 목록은 자주 쓰는 것만 보여준다. 전체는 **오른쪽 「속성」 창 → 「고급」
> 탭**에 있다.

> **OT 는 「안 넣어도 되는」 칸이다.** 비워두면 `lblOt` 이 `0` 을 돌려주고 OT 0시간으로
> 저장된다. 평일 대부분은 비워둔 채 저장한다.

> **석식 `자동` 의 뜻**: OT 종료가 석식 창(그 달 정규 종료 ~ +30분)을 넘으면 30분을
> 공제한다. `20:30~23:15` 처럼 석식 창을 지나서 시작한 OT 는 겹치는 구간이 없으므로
> 공제되지 않고 `2.75h` 가 된다 — 이 값이 `sp_근태기록_시작.csv` 샘플과 일치한다.

#### 5-2 확인표

| 확인할 것 | 기대 |
|---|---|
| OT 칸을 비우고 저장 | `lblOt` 이 `0` · `근태기록.OT시간` 이 0 |
| `20:30` ~ `23:15` · 석식 `자동` | `lblOt` = **`2.75`** (석식 창과 겹치지 않아 공제 없음) |
| `17:30` ~ `20:00` · 석식 `자동` | `lblOt` = **`2`** (석식 30분 공제) |
| `17:30` ~ `20:00` · 석식 `미실시` | `lblOt` = **`2.5`** (공제 없음) |
| `22:00` ~ `00:30` · 석식 `자동` | `lblOt` = **`2.5`** (자정 넘김) |
| SharePoint `근태기록` | `OT시작` · `OT종료` · `OT시간` · `석식` · `주` 가 채워져 있다 |

#### 5-3. `scrSummary` — 개인 요약 화면

`새 화면` → 이름을 **`scrSummary`** 로. 수식은 §4-7 에 있다.

| # | 컨트롤 | 이름 | X | Y | W | H |
|---|---|---|---|---|---|---|
| 1 | 드롭다운 | `ddWho` | 40 | 24 | 240 | 40 |
| 2 | 텍스트 레이블 | `lblSumHead` | 300 | 24 | 700 | 40 |
| 3 | 단추 | `btnToMonth2` | 1166 | 24 | 160 | 40 |
| 4 | 세로 갤러리 | `galKpi` | 40 | 84 | 430 | 400 |
| 5 | └ 레이블 | `lblKpiName` | 12 | 8 | 130 | 24 |
| 6 | └ 레이블 | `lblKpiVal` | 150 | 8 | 90 | 24 |
| 7 | └ 레이블 | `lblKpiNote` | 250 | 8 | 170 | 24 |
| 8 | 텍스트 레이블 | `lblWeekHead` | 500 | 84 | 826 | 32 |
| 9 | 세로 갤러리 | `galWeek` | 500 | 120 | 826 | 240 |
| 10 | └ 레이블 | `lblWeek` | 12 | 8 | 800 | 28 |
| 11 | 텍스트 레이블 | `lblMyHead` | 500 | 380 | 826 | 32 |
| 12 | 세로 갤러리 | `galMy` | 500 | 416 | 826 | 312 |
| 13 | └ 레이블 | `lblMy` | 12 | 6 | 800 | 28 |

`galKpi` · `galWeek` · `galMy` 의 `TemplateSize` 는 각각 40 · 44 · 40.
`lblWeekHead.Text` 는 `"주별 근로 (한도 64h)"`, `lblMyHead.Text` 는 `"이번 달 기록"`,
`btnToMonth2` 는 `Text` `"◀ 월 달력"` · `OnSelect` `Navigate(scrMonth)`.
`scrMonth` 에도 단추 하나를 더해 `Navigate(scrSummary)` 로 오게 한다.

#### 5-3 확인표 — 2026-09 · §3-6 테스트 4건 기준

**소정근로일 20일 / 기본 총량 160h** (추석 9/24 목 · 9/25 금 제외)

| `ddWho` | 조정 총량 | 실근로 누적 | 차이 |
|---|---|---|---|
| 김동환 (연차 1일) | **152h** | **152h** | **0h** |
| 정병철 (오전반 4.5h) | 156h | 156.5h | **+0.5h** 초과 |
| 박상호 (근무 7h) | 160h | 159h | **−1h** 부족 (빨강) |
| 최규석 (검진 4h) | 156h | 156h | 0h |
| 그 외 (기록 없음) | 160h | 160h | 0h |

> **김동환 152h 는 확정 사항 9번과 정확히 일치한다** — 「하루 연차(8시간)를 쓰면 월
> 총량이 152h로 줄어든다」. 이 한 줄이 총량 계산 전체의 검증 기준이다.

`galWeek` 는 기록이 없는 사람 기준으로 이렇게 나와야 한다.

| 주 | 기간 | 소정 | 근로 |
|---|---|---|---|
| 1 | 9/1 ~ 9/6 | 4일 | 32h |
| 2 | 9/7 ~ 9/13 | 5일 | 40h |
| 3 | 9/14 ~ 9/20 | 5일 | 40h |
| 4 | 9/21 ~ 9/27 | **3일** | 24h |
| 5 | 9/28 ~ 9/30 | 3일 | 24h |

> **주 4 가 3일인 것이 추석 확인**이다 (24 · 25 공휴일 · 26 · 27 주말).
> 소정 합계 4+5+5+3+3 = 20 이 `gvWorkdays` 와 같아야 한다.
> 김동환은 주 3 이 `32h` 로 줄어든다 (연차 1일).

### 3-8. 6단계 — 매트릭스 화면 (23명 × 날짜)

HTML 도구와 체감 차이가 나는 것은 사실상 이 화면 하나다. 조율은 「누구에게 부탁할지」를
한 화면에서 보는 일이고, 그게 매트릭스다.

#### 왜 2주 보기인가

23행 × 30일 = **690개 컨트롤**이고, Power Apps 권장치는 화면당 500개다. 2주(14일)로
줄이면 27행 × 14일 ≈ **480개**로 들어온다. 조율은 실제로 가까운 2주를 보는 일이고,
한 달 전체 조망은 `scrMonth` 의 30% 리스트가 이미 하고 있다.

#### 핵심 기법 — 중첩 갤러리

세로 갤러리(사람) **안에** 가로 갤러리(날짜)를 넣는다. 안쪽 갤러리의 `Items` 는
바깥 갤러리의 템플릿 안에 있으므로 **거기서 `ThisItem` 은 바깥 항목(사람)** 을 가리킨다.
이 성질을 이용해 셀 데이터를 조립한다 — 안쪽 갤러리의 셀 컨트롤에서는 `ThisItem` 이
셀 자신이 되므로, 사람 정보를 미리 셀 레코드에 담아 넣어야 한다.

#### 컨트롤 15개

| # | 컨트롤 | 이름 | X | Y | W | H | 그 외 |
|---|---|---|---|---|---|---|---|
| 1 | 텍스트 레이블 | `lblGridHead` | 40 | 24 | 700 | 32 | `Size` 15 · `Bold` |
| 2 | 단추 | `btnGridPrev` | 760 | 24 | 110 | 32 | `"◀ 2주"` |
| 3 | 단추 | `btnGridToday` | 880 | 24 | 110 | 32 | `"이번 주"` |
| 4 | 단추 | `btnGridNext` | 1000 | 24 | 110 | 32 | `"2주 ▶"` |
| 5 | 단추 | `btnGridToMonth` | 1206 | 24 | 120 | 32 | `"월 달력"` |
| 6 | **가로** 갤러리 | `galDayHead` | 240 | 68 | 1126 | 40 | `TemplateSize` 80 |
| 7 | └ 레이블 | `lblDayNum` | 0 | 2 | 78 | 16 | `Size` 11 · `Align.Center` |
| 8 | └ 레이블 | `lblDow` | 0 | 20 | 78 | 16 | `Size` 9 · `Align.Center` |
| 9 | **가로** 갤러리 | `galNeedHead` | 240 | 110 | 1126 | 26 | `TemplateSize` 80 |
| 10 | └ 레이블 | `lblNeed` | 0 | 2 | 78 | 22 | `Size` 9 · `Align.Center` |
| 11 | 세로 갤러리 | `galGrid` | 40 | 140 | 1326 | 588 | `TemplateSize` 26 |
| 12 | └ 레이블 | `lblRowName` | 8 | 2 | 110 | 22 | |
| 13 | └ 레이블 | `lblRowPart` | 122 | 2 | 76 | 22 | |
| 14 | └ **가로** 갤러리 | `galCell` | 200 | 0 | 1126 | 26 | `TemplateSize` 80 |
| 15 | └└ 레이블 | `lblCell` | 0 | 1 | 78 | 24 | `Size` **9** · `Align.Center` · `Padding` 0 |

> **셀은 단추가 아니라 레이블로 만든다.** 레이블도 `OnSelect` 를 가지고 있고 훨씬
> 가볍다. 378개를 그려야 하므로 이 차이가 크다.

> **색은 레이블이 아니라 갤러리의 `TemplateFill` 로 칠한다.** `galCell` 은 가로
> 갤러리이고 **셀 하나가 곧 갤러리 항목**이므로, `TemplateFill` 이 셀 배경색이 된다.
> `galMonth.TemplateFill` 로 달력 행을 칠한 것과 같은 방식이다.
>
> 이렇게 하면 레이블에 `Fill` · `BorderThickness` 가 필요 없어져 **모던이든 클래식이든
> 상관이 없어진다.** 레이블 속성 이름으로 씨름할 일이 사라진다.
>
> | 색을 넣을 곳 | 속성 |
> |---|---|
> | 셀 배경 | `galCell.TemplateFill` |
> | 인원 행 배경 | `galNeedHead.TemplateFill` |
> | 사람 행 배경 (그룹 헤더) | `galGrid.TemplateFill` |
>
> 클릭도 `lblCell.OnSelect` 가 아니라 **`galCell.OnSelect`** 에 넣는다. 갤러리는
> 항목 아무 데나 누르면 `OnSelect` 가 실행되므로 동작이 같다.

> **격자선도 갤러리로 만든다.** `TemplatePadding` 을 `1` 로 주면 항목 사이에 1px 틈이
> 생기고, 그 틈으로 갤러리의 `Fill` 이 비쳐 격자선처럼 보인다.
>
> | 속성 | 값 |
> |---|---|
> | `galCell.TemplatePadding` · `galGrid.TemplatePadding` | `1` |
> | `galCell.Fill` · `galGrid.Fill` | `RGBA(227, 230, 234, 1)` |

> **왼쪽 위 속성 목록에는 자주 쓰는 것만 나온다.** 전체 속성은 **오른쪽 「속성」 창 →
> 「고급」 탭**에 있고, 거기 검색창에서 이름으로 찾을 수 있다. 이 화면에서는 위 방식
> 덕분에 고급 탭을 열 일이 없다.

> **요일은 `Text(d, "[$-ko]ddd")` 를 쓰지 않는다.** 한국어 로캘에서 `ddd` 가 `월` 이
> 아니라 **`월요일`** 을 돌려주어 칸을 넘치고 날짜와 겹쳐 보인다. `Switch(Weekday(...))`
> 로 직접 매핑한다 — `colGridDays` 와 `colDays` 양쪽 모두다.

> **`lblCell` 은 두 줄(`유형` + `실근로h`)이라 `Size` 를 9로 줄인다.** 24px 높이에
> 기본 글자 크기(13)로 두 줄은 들어가지 않는다. `PaddingTop` · `PaddingBottom` 도 0 으로.

#### 행 소스 — 그룹 헤더를 섞어 넣는다

`App.OnStart` 의 「한 번만」 블록 **뒤, 월 갱신 블록 앞**에 넣는다.
3개 그룹 + 24명 = 27행. **앞 문장이 `;` 로 끝나는지 반드시 확인한다.**

```powerfx
Clear(colGridRows);
Collect(colGridRows, { 헤더: true,
    이름: "A그룹 · 직책자 (팀장 · 파트장)", 파트: "", 휴직: "" });
Collect(colGridRows, ForAll(Sort(Filter(colAll, 그룹 = "A"), 정렬) As M,
    { 헤더: false, 이름: M.Title, 파트: M.파트, 휴직: Coalesce(M.휴직, "") }));
Collect(colGridRows, { 헤더: true,
    이름: "B그룹 · 기계 · 전기 · 제어 · 정비지원", 파트: "", 휴직: "" });
Collect(colGridRows, ForAll(Sort(Filter(colAll, 그룹 = "B"), 정렬) As M,
    { 헤더: false, 이름: M.Title, 파트: M.파트, 휴직: Coalesce(M.휴직, "") }));
Collect(colGridRows, { 헤더: true,
    이름: "C그룹 · 발전지원", 파트: "", 휴직: "" });
Collect(colGridRows, ForAll(Sort(Filter(colAll, 그룹 = "C"), 정렬) As M,
    { 헤더: false, 이름: M.Title, 파트: M.파트, 휴직: Coalesce(M.휴직, "") }))
```

> **휴직자도 행에 넣는다.** HTML 도구가 그렇게 하고 있고, 명부에서 빠진 게 아니라
> 휴직 중이라는 것이 보여야 한다. 모수(`gvActive` 23명)에서는 이미 빠져 있다.

#### 2주 창 — `gvGridStart` 와 두 컬렉션

**왜 네 곳에 같은 코드를 넣나.** Power Apps 에는 「함수를 만들어 여러 곳에서 부르는」
기능이 없다. 그래서 `gvGridStart`(2주 창의 시작일)가 바뀌는 자리마다 같은 갱신 코드를
복사해 넣어야 한다. 그 자리가 넷이다.

| 자리 | 언제 실행되나 | 하는 일 |
|---|---|---|
| `scrGrid.OnVisible` | 이 화면이 보일 때마다 | 처음이면 이번 주 월요일로 맞춘다 |
| `btnGridPrev.OnSelect` | ◀ 2주 | 14일 뒤로 |
| `btnGridNext.OnSelect` | 2주 ▶ | 14일 앞으로 |
| `btnGridToday.OnSelect` | 이번 주 | 오늘이 든 주로 |

**무엇을 갱신하나.** 컬렉션 두 개다. 월 단위인 `colRec` · `colDays` 를 그대로 쓸 수 없다.

| 컬렉션 | 내용 | 월 단위 컬렉션을 못 쓰는 이유 |
|---|---|---|
| `colGridRec` | 2주 창의 근태 기록 | `colRec` 는 한 달 범위다. 2주 창이 `9/28 ~ 10/11` 처럼 **달을 걸치면** 뒷부분이 비어버린다 |
| `colGridDays` | 2주 창의 날짜 14개 (요일 · 휴일 · 30% 판정) | `colDays` 도 같은 문제 |

> **`scrGrid.OnVisible` 에 넣는 것이 특히 중요하다.** 셀을 눌러 `Screen1` 에서 저장하고
> 돌아오면 `OnVisible` 이 다시 실행되어 **매트릭스가 자동으로 갱신된다.** 따로
> 새로고침 단추가 필요 없다.

네 수식의 **차이는 첫 줄뿐**이고 나머지는 아래 공통 블록이 그대로 붙는다.

**`scrGrid.OnVisible`**

```powerfx
If(IsBlank(gvGridStart),
   Set(gvGridStart, DateAdd(Today(),
       -(Weekday(Today(), StartOfWeek.Monday) - 1), TimeUnit.Days)));
ClearCollect(colGridRec,
    Filter(근태기록, 근무일 >= gvGridStart,
                    근무일 <= DateAdd(gvGridStart, 13, TimeUnit.Days)));
ClearCollect(colGridDays,
    ForAll(Sequence(14) As S,
        With({ d: DateAdd(gvGridStart, S.Value - 1, TimeUnit.Days) },
            With({ hol: Weekday(d, StartOfWeek.Monday) > 5
                        || !IsBlank(LookUp(colHoliday, 날짜 = d)) },
                {
                    날짜: d,
                    일:   Day(d),
                    요일: Switch(Weekday(d, StartOfWeek.Monday),
                             1, "월", 2, "화", 3, "수", 4, "목", 5, "금", 6, "토", 7, "일"),
                    휴일: hol,
                    필요인원: If(hol, 0, gvNeed),
                    충족인원: If(hol, 0,
                        gvActive - CountRows(Filter(colGridRec As R,
                            R.근무일 = d, R.충족 = 0)))
                }
            )
        )
    ))
```

**`btnGridPrev.OnSelect`**

```powerfx
Set(gvGridStart, DateAdd(gvGridStart, -14, TimeUnit.Days));
ClearCollect(colGridRec,
    Filter(근태기록, 근무일 >= gvGridStart,
                    근무일 <= DateAdd(gvGridStart, 13, TimeUnit.Days)));
ClearCollect(colGridDays,
    ForAll(Sequence(14) As S,
        With({ d: DateAdd(gvGridStart, S.Value - 1, TimeUnit.Days) },
            With({ hol: Weekday(d, StartOfWeek.Monday) > 5
                        || !IsBlank(LookUp(colHoliday, 날짜 = d)) },
                {
                    날짜: d,
                    일:   Day(d),
                    요일: Switch(Weekday(d, StartOfWeek.Monday),
                             1, "월", 2, "화", 3, "수", 4, "목", 5, "금", 6, "토", 7, "일"),
                    휴일: hol,
                    필요인원: If(hol, 0, gvNeed),
                    충족인원: If(hol, 0,
                        gvActive - CountRows(Filter(colGridRec As R,
                            R.근무일 = d, R.충족 = 0)))
                }
            )
        )
    ))
```

**`btnGridNext.OnSelect`**

```powerfx
Set(gvGridStart, DateAdd(gvGridStart, 14, TimeUnit.Days));
ClearCollect(colGridRec,
    Filter(근태기록, 근무일 >= gvGridStart,
                    근무일 <= DateAdd(gvGridStart, 13, TimeUnit.Days)));
ClearCollect(colGridDays,
    ForAll(Sequence(14) As S,
        With({ d: DateAdd(gvGridStart, S.Value - 1, TimeUnit.Days) },
            With({ hol: Weekday(d, StartOfWeek.Monday) > 5
                        || !IsBlank(LookUp(colHoliday, 날짜 = d)) },
                {
                    날짜: d,
                    일:   Day(d),
                    요일: Switch(Weekday(d, StartOfWeek.Monday),
                             1, "월", 2, "화", 3, "수", 4, "목", 5, "금", 6, "토", 7, "일"),
                    휴일: hol,
                    필요인원: If(hol, 0, gvNeed),
                    충족인원: If(hol, 0,
                        gvActive - CountRows(Filter(colGridRec As R,
                            R.근무일 = d, R.충족 = 0)))
                }
            )
        )
    ))
```

**`btnGridToday.OnSelect`**

```powerfx
Set(gvGridStart, DateAdd(Today(),
    -(Weekday(Today(), StartOfWeek.Monday) - 1), TimeUnit.Days));
ClearCollect(colGridRec,
    Filter(근태기록, 근무일 >= gvGridStart,
                    근무일 <= DateAdd(gvGridStart, 13, TimeUnit.Days)));
ClearCollect(colGridDays,
    ForAll(Sequence(14) As S,
        With({ d: DateAdd(gvGridStart, S.Value - 1, TimeUnit.Days) },
            With({ hol: Weekday(d, StartOfWeek.Monday) > 5
                        || !IsBlank(LookUp(colHoliday, 날짜 = d)) },
                {
                    날짜: d,
                    일:   Day(d),
                    요일: Switch(Weekday(d, StartOfWeek.Monday),
                             1, "월", 2, "화", 3, "수", 4, "목", 5, "금", 6, "토", 7, "일"),
                    휴일: hol,
                    필요인원: If(hol, 0, gvNeed),
                    충족인원: If(hol, 0,
                        gvActive - CountRows(Filter(colGridRec As R,
                            R.근무일 = d, R.충족 = 0)))
                }
            )
        )
    ))
```

> `scrGrid.OnVisible` 만 `If(IsBlank(...))` 로 감싼다. 처음 열 때만 오늘 기준으로
> 맞추고, 그 뒤로는 사용자가 이동해 둔 위치를 유지하기 위해서다.

#### 수식

**`lblGridHead.Text`**

```powerfx
Text(gvGridStart, "yyyy-mm-dd") & " ~ "
  & Text(DateAdd(gvGridStart, 13, TimeUnit.Days), "yyyy-mm-dd")
  & "     모수 " & gvActive & "명 · 8시간 필수 " & gvNeed & "명"
  & "     미달일 "
  & CountRows(Filter(colGridDays, !휴일, 충족인원 < 필요인원)) & "일"
```

**`galDayHead.Items`** · **`galNeedHead.Items`** — 둘 다 같다

```powerfx
colGridDays
```

**`lblDayNum.Text`** · **`lblDow.Text`**

```powerfx
ThisItem.일
```
```powerfx
ThisItem.요일
```

**`lblDow.Color`** — 토·일·공휴일은 흐리게

```powerfx
If(ThisItem.휴일, RGBA(107, 114, 128, 1), RGBA(22, 24, 29, 1))
```

**`lblNeed.Text`** · **`galNeedHead.TemplateFill`** — HTML 의 「8h 인원 / 필요 인원」 행

```powerfx
If(ThisItem.휴일, "—", ThisItem.충족인원 & "/" & ThisItem.필요인원)
```
```powerfx
If(ThisItem.휴일,                        RGBA(240, 241, 243, 1),
   ThisItem.충족인원 < ThisItem.필요인원, RGBA(251, 234, 233, 1),
                                          RGBA(230, 244, 236, 1))
```

**`galGrid.Items`**

```powerfx
colGridRows
```

**`lblRowName.Text`** · **`lblRowName.FontWeight`** — 헤더 행은 굵게

```powerfx
ThisItem.이름 & If(ThisItem.휴직 = "Y", "  (휴직)", "")
```
```powerfx
If(ThisItem.헤더, FontWeight.Bold, FontWeight.Normal)
```

**`lblRowName.Width`** — 그룹 헤더는 이름 칸을 넘어가므로 헤더 행에서만 넓힌다

```powerfx
If(ThisItem.헤더, 1300, 110)
```

**`lblRowPart.Text`** · **`galGrid.TemplateFill`**

```powerfx
ThisItem.파트
```
```powerfx
If(ThisItem.헤더, RGBA(232, 238, 246, 1), RGBA(255, 255, 255, 1))
```

**`galCell.Items`** ★ — 이 화면의 핵심. 여기서 `ThisItem` 은 **사람**이다

```powerfx
ForAll(colGridDays As D,
    With({ r: LookUp(colGridRec,
                     근무일 = D.날짜 && 구성원 = ThisItem.이름) },
        {
            날짜:   D.날짜,
            휴일:   D.휴일,
            헤더:   ThisItem.헤더,
            이름:   ThisItem.이름,
            휴직:   ThisItem.휴직,
            유형:   Coalesce(r.유형, ""),
            구분:   Coalesce(r.구분, ""),
            실근로: If(IsBlank(r), 8, r.실근로),
            충족:   If(IsBlank(r), 1, r.충족),
            OT:     Coalesce(r.OT시간, 0)
        }
    )
)
```

**`lblCell.Text`** — 8시간 근무(기록 없음)는 빈칸으로 둔다

```powerfx
If(ThisItem.헤더 || ThisItem.휴일 || ThisItem.휴직 = "Y" || ThisItem.유형 = "", "",
   ThisItem.유형 & Char(10) & ThisItem.실근로 & "h"
     & If(ThisItem.OT > 0, " +" & ThisItem.OT, ""))
```

**`galCell.TemplateFill`** — 색이 판정이다 (레이블이 아니라 **갤러리** 속성)

```powerfx
If(ThisItem.헤더,             RGBA(232, 238, 246, 1),
   ThisItem.휴일,             RGBA(240, 241, 243, 1),
   ThisItem.휴직 = "Y",       RGBA(240, 241, 243, 1),
   ThisItem.충족 = 1,         RGBA(230, 244, 236, 1),   // 8시간 인정
   ThisItem.구분 = "휴가·사외", RGBA(232, 238, 246, 1),   // 연차 · 출장 · 교육
                              RGBA(253, 243, 221, 1))   // 반차 · 반반차 · 검진 · 단축
```

**`galCell.OnSelect`** — 셀을 누르면 그 사람 · 그 날짜로 입력 화면이 열린다

```powerfx
If(!ThisItem.헤더 && !ThisItem.휴일 && ThisItem.휴직 <> "Y",
   Set(gvPickWho,  ThisItem.이름);
   Set(gvPickDate, ThisItem.날짜);
   Navigate(Screen1))
```

`Screen1` 에서 받는다 — **`dpDate.DefaultDate`**

```powerfx
Coalesce(gvPickDate, Today())
```

구성원 기본 선택은 컨트롤 종류에 따라 다르다 (§3-7 의 `ddDinner` 와 같은 문제).

`ddMe.Items` 가 `Distinct(명부, Title)` 이고 이것은 **`Value` 열 하나짜리 표**다.
그래서 `Default` 는 문자열이 아니라 **그 표의 레코드**를 받는다. 문자열을 넣으면
`잘못된 수식입니다. 'Items'과(와) 호환되는 값이 필요합니다` 가 뜬다.

| `ddMe` 가 | 속성 | 값 |
|---|---|---|
| `Default` 를 가진 경우 | `Default` | `LookUp(Distinct(명부, Title), Value = gvPickWho)` |
| `DefaultSelectedItems` 를 가진 경우 | `DefaultSelectedItems` | `Filter(Distinct(명부, Title), Value = gvPickWho)` |

`gvPickWho` 가 비어 있으면 아무것도 선택되지 않는다 — 오류가 아니다.

**`btnGridToMonth.OnSelect`**

```powerfx
Navigate(scrMonth)
```

`scrMonth` 에도 단추를 더해 `Navigate(scrGrid)` 로 오게 한다.

#### 6-1 확인표 — §3-6 테스트 4건 기준

`btnGridToday` 를 누르고 9월 15일이 들어간 2주 창(9/14 ~ 9/27)에서 본다.

| 확인할 것 | 기대 |
|---|---|
| 행 수 | 27 (그룹 헤더 3 + 명부 24) |
| 그룹 헤더 3줄 | 남색 배경 · 굵게 |
| 윤승현 행 | `윤승현 (휴직)` · 셀 전체 회색 |
| 9/20 · 9/26 · 9/27 열 | 회색 (일 · 토 · 일) |
| **9/24 · 9/25 열** | **회색** (추석) |
| `lblNeed` 행 | 9/15 는 `19/7` · 나머지 평일은 `23/7` · 초록 |
| 김동환 × 9/15 | `연차 0h` · 남색 |
| 정병철 × 9/15 | `오전반 4.5h` · 주황 |
| 박상호 × 9/15 | `근무 7h` · 주황 |
| 최규석 × 9/15 | `검진 4h` · 주황 |
| 그 외 모든 평일 칸 | **빈칸 · 초록** (기록 없음 = 8시간 근무) |
| 아무 초록 칸을 누르면 | `Screen1` 이 그 사람 · 그 날짜로 열린다 |

> **빈칸이 초록인 것이 이 설계의 핵심**이다. 23명 × 22일을 미리 채우지 않고도
> 전원 8시간 근무로 보고, 예외를 넣은 칸만 색이 바뀐다.

#### 성능이 느리면

`galCell` 이 378개를 그리므로 첫 렌더가 1~2초 걸릴 수 있다. 견디기 힘들면 순서대로
줄인다.

1. `Sequence(14)` → `Sequence(7)` (1주 보기, 189칸) — 가장 확실하다
2. `galCell.TemplatePadding` 을 0 으로 (격자선 렌더 비용 제거)
3. `lblRowPart` 를 지우고 `lblRowName` 에 합치기

### 3-9. 6-2단계 — 탭 바와 KPI 카드

둘 다 **`Table()` + 가로 갤러리**다. HTML 도구의 탭 5개와 요약 카드 7개를 컨트롤
7개로 재현한다. 카드 하나에 레이블 3개를 손으로 놓으면 21개가 필요한데, 갤러리로 하면
3개면 된다.

#### 탭 바 — 화면 이동 단추들을 대체한다

지금 화면마다 흩어져 있는 `btnToMy` · `btnGridToMonth` · `btnToMonth2` · `Button2`
같은 이동 단추를 **전부 지우고** 탭 바 하나로 통일한다.

`scrGrid` 에 만들고 나머지 세 화면에 **복사(`Ctrl+C` → 화면 이동 → `Ctrl+V`)** 한다.
복사하면 수식이 그대로 따라온다.

| 컨트롤 | 이름 | X | Y | W | H | 그 외 |
|---|---|---|---|---|---|---|
| **가로** 갤러리 | `galTabs` | 0 | 0 | 1366 | 40 | `TemplateSize` 170 |
| └ 레이블 | `lblTab` | 0 | 0 | 170 | 40 | `Size` 11 · `Align.Center` · `Padding` 0 |

**`galTabs.Items`**

```powerfx
Table(
    { 키: "grid",  이름: "매트릭스" },
    { 키: "month", 이름: "월 달력 · 30%" },
    { 키: "input", 이름: "근태 입력" }
)
```

> **`scrSummary` 를 만든 뒤에 네 번째 탭을 더한다** — `Items` 에
> `{ 키: "summary", 이름: "개인 요약 · OT" }` 한 줄, `OnSelect` 의 `Switch` 에
> `"summary", Navigate(scrSummary)` 한 줄이면 된다.

**`galTabs.OnSelect`**

```powerfx
Set(gvTab, ThisItem.키);
Switch(ThisItem.키,
    "grid",  Navigate(scrGrid),
    "month", Navigate(scrMonth),
    "input", Navigate(Screen1))
```

> `Navigate` 는 문자열이 아니라 화면 자체를 받으므로 `Switch` 로 갈라준다.

**`galTabs.TemplateFill`** · **`lblTab.Text`** · **`lblTab.Color`**

```powerfx
If(ThisItem.키 = gvTab, RGBA(232, 238, 246, 1), RGBA(255, 255, 255, 1))
```
```powerfx
ThisItem.이름
```
```powerfx
If(ThisItem.키 = gvTab, RGBA(28, 78, 128, 1), RGBA(107, 114, 128, 1))
```

`App.OnStart` 의 첫 줄 앞에 한 줄 더한다 — 시작 화면 표시용이다.

```powerfx
Set(gvTab, "input");
```

#### KPI 카드 7개 — `scrMonth` 상단

HTML 도구의 「당월 요약」 카드 줄이다.

| 컨트롤 | 이름 | X | Y | W | H | 그 외 |
|---|---|---|---|---|---|---|
| **가로** 갤러리 | `galKpiTop` | 20 | 96 | 1326 | 86 | `TemplateSize` 188 |
| └ 레이블 | `lblKpiTitle` | 10 | 8 | 168 | 16 | `Size` 9 · `Padding` 0 |
| └ 레이블 | `lblKpiVal` | 10 | 26 | 168 | 30 | `Size` 20 · `Bold` · `Padding` 0 |
| └ 레이블 | `lblKpiNote` | 10 | 58 | 168 | 22 | `Size` 8 · `Padding` 0 |

**`galKpiTop.Items`**

```powerfx
With({
    미달:     CountRows(Filter(galMonth.AllItems, !휴일, 충족인원 < 필요인원)),
    직책미달: CountRows(Filter(galMonth.AllItems, !휴일, 직책자 < 1)),
    공휴:     CountRows(Filter(colDays, 휴일,
                  Weekday(날짜, StartOfWeek.Monday) <= 5))
},
  Table(
    { 제목: "선택근로 모수", 값: gvActive & "명",
      비고: "명부 " & CountRows(colAll) & "명 − 휴직 "
            & (CountRows(colAll) - gvActive) & "명", 경고: false },
    { 제목: "8시간 필수 (30%)", 값: gvNeed & "명",
      비고: gvActive & " × 0.3 올림", 경고: false },
    { 제목: "소정근로일", 값: gvWorkdays & "일",
      비고: "공휴일 " & 공휴 & "일 제외", 경고: false },
    { 제목: "월 소정근로시간", 값: gvWorkdays * 8 & "h",
      비고: gvWorkdays & "일 × 8h", 경고: false },
    { 제목: "30% 미달일", 값: 미달 & "일",
      비고: If(미달 = 0, "전일 충족", "조율 필요"), 경고: 미달 > 0 },
    { 제목: "직책자 미달일", 값: 직책미달 & "일",
      비고: "직책자 1명 이상 필요", 경고: 직책미달 > 0 },
    { 제목: "OT 기본", 값: gvOtBase & "h",
      비고: gvYM & " 월설정", 경고: false }
  )
)
```

**`galKpiTop.TemplateFill`** · 레이블 셋의 `Text` · `lblKpiTitle.Color` · `lblKpiNote.Color`

```powerfx
If(ThisItem.경고, RGBA(251, 234, 233, 1), RGBA(246, 247, 249, 1))
```
```powerfx
ThisItem.제목
```
```powerfx
ThisItem.값
```
```powerfx
ThisItem.비고
```
```powerfx
RGBA(107, 114, 128, 1)
```

#### 좌표 조정 — 탭 바 자리를 만든다

탭 바가 `Y` 0~40 을 차지하므로 네 화면의 기존 컨트롤을 내린다.

| 화면 | 컨트롤 | 새 `Y` | 새 `Height` |
|---|---|---|---|
| `scrGrid` | `lblGridHead` · `btnGridPrev` · `btnGridNext` · `btnGridToday` | 64 | 그대로 |
| | `galDayHead` | 108 | 그대로 |
| | `galNeedHead` | 150 | 그대로 |
| | `galGrid` | 180 | **548** |
| `scrMonth` | `lblMonth` · `btnPrev` · `btnNext` | 52 | 그대로 |
| | `galKpiTop` | 96 | 86 |
| | `galMonth` · `lblCandHead` | 196 | `galMonth` **532** |
| | `galCandidate` | 240 | **488** |
| `Screen1` | 아래 전용 표 참조 | | |

이동 단추(`btnToMy` · `btnGridToMonth` · `btnToMonth2` · `Button2` · `btnTomy`)는
지운다 — 탭 바가 대신한다.

#### `Screen1` 좌표 — 왼쪽 입력 · 오른쪽 저장 목록

3단계·5단계에서 컨트롤만 늘리고 배치는 잡지 않았다. 화면 크기는 다른 화면과 같은
**1366 × 768** 이다. 레이블은 전부 `Padding` 0.

| 컨트롤 | X | Y | W | H | 그 외 |
|---|---|---|---|---|---|
| `galTabs` | 0 | 0 | 1366 | 40 | 다른 화면에서 복사 |
| `lblL1` | 40 | 52 | 220 | 16 | `"구성원"` · Size 9 |
| `lblL2` | 280 | 52 | 220 | 16 | `"근무일"` · Size 9 |
| `ddMe` | 40 | 72 | 220 | 40 | |
| `dpDate` | 280 | 72 | 220 | 40 | |
| `lblL3` | 40 | 124 | 220 | 16 | `"유형"` · Size 9 |
| `lblL4` | 280 | 124 | 160 | 16 | `"출근"` · Size 9 |
| `lblL5` | 460 | 124 | 160 | 16 | `"퇴근"` · Size 9 |
| `ddType` | 40 | 144 | 220 | 40 | |
| `ddStart` | 280 | 144 | 160 | 40 | |
| `ddEnd` | 460 | 144 | 160 | 40 | |
| `lblPreview` | 40 | 196 | 580 | 32 | Size 12 |
| `lblL6` | 40 | 240 | 580 | 16 | Size 9 |
| `txtOtS` | 40 | 260 | 160 | 40 | |
| `txtOtE` | 220 | 260 | 160 | 40 | |
| `ddDinner` | 400 | 260 | 140 | 40 | |
| `lblOt` | 560 | 260 | 60 | 40 | Size 14 · `Align.Center` |
| `txtNote` | 40 | 312 | 580 | 40 | |
| `btnSave` | 40 | 368 | 180 | 44 | |
| `galSaved` | 660 | 52 | 666 | 676 | `TemplateSize` 40 |
| └ `Title2` | 12 | 8 | 560 | 24 | Size 11 |
| └ `icoDel` | 600 | 8 | 24 | 24 | |

**`lblL6.Text`**

```powerfx
"초과근로 (선택 — 비워두면 0) · 오른쪽 숫자가 계산된 OT 시간(h)"
```

> **`lblL1` ~ `lblL6` 은 안내 레이블이다.** 없어도 동작하지만 드롭다운 세 개가 나란히
> 있으면 어느 것이 출근이고 퇴근인지 알 수 없다. `Color` 는 `RGBA(107, 114, 128, 1)`.

> **`lblOt` 은 숫자만 표시해야 한다.** `btnSave` 가 `Value(lblOt.Text)` 로 읽으므로
> `"h"` 를 붙이면 저장이 깨진다.

#### 6-2 확인표

| 확인할 것 | 기대 |
|---|---|
| 탭 4개 | 네 화면 어디서나 같은 자리에 보인다 |
| 현재 탭 | 남색 글자 + 연한 남색 배경 |
| 탭을 누르면 | 그 화면으로 이동하고 강조가 따라온다 |
| `scrMonth` KPI 카드 | `23명` · `7명` · `20일` · `160h` · `0일` · `0일` · `40h` |
| 「소정근로일」 비고 | `공휴일 2일 제외` (추석 9/24 · 9/25) |
| 미달일이 생기면 | 그 카드만 연한 빨강 |

## 4. Power Fx 수식

### 4-1. `App.OnStart` 와 월 갱신 블록

**한 번만 하는 것**과 **달이 바뀔 때마다 하는 것**을 나눈다. 뒤쪽을 「월 갱신 블록」이라
부르고, `App.OnStart` · `btnPrev.OnSelect` · `btnNext.OnSelect` 세 곳에 같은 내용을 넣는다.

**한 번만 — 작은 목록을 전부 올려둔다**

```powerfx
ClearCollect(colCombo,   조합표);      // 106행
ClearCollect(colHoliday, 공휴일);      // 21행 — 달력이 날마다 조회하지 않도록
ClearCollect(colAll,     명부);        // 24행
ClearCollect(colMembers, Filter(colAll, IsBlank(휴직)));
ClearCollect(colLeads,   Filter(colMembers, 직책 <> "구성원"));
Set(gvActive, CountRows(colMembers));                    // 모수 23명
Set(gvNeed,   RoundUp(gvActive * 0.3, 0));               // 필요 7명
Set(gvLeads,  CountRows(colLeads));                      // 직책자 6명
```

**월 갱신 블록** — `gvMonthStart` 가 정해진 뒤에 실행되는 부분

```powerfx
Set(gvMonthEnd, DateAdd(DateAdd(gvMonthStart, 1, TimeUnit.Months), -1, TimeUnit.Days));
Set(gvYM,       Text(gvMonthStart, "yyyy-mm"));
Set(gvMonthCfg, LookUp(월설정, Title = gvYM));
Set(gvOtBase,   Coalesce(gvMonthCfg.OT기본, 0));
Set(gvRegEnd,   Value(Left(Coalesce(gvMonthCfg.정규종료, "17:30"), 2)) * 60
                + Value(Right(Coalesce(gvMonthCfg.정규종료, "17:30"), 2)));

// 그 달의 날짜 · 요일 · 휴일 · 주 순번 — 개인 요약과 주별 64h 가 이걸 쓴다
ClearCollect(colDays,
    ForAll(Sequence(Day(gvMonthEnd)) As S,
        With({ d: DateAdd(gvMonthStart, S.Value - 1, TimeUnit.Days) },
            {
                날짜: d,
                일:   S.Value,
                요일: Switch(Weekday(d, StartOfWeek.Monday),
                             1, "월", 2, "화", 3, "수", 4, "목", 5, "금", 6, "토", 7, "일"),
                휴일: Weekday(d, StartOfWeek.Monday) > 5
                      || !IsBlank(LookUp(colHoliday, 날짜 = d)),
                주:   RoundDown((S.Value - 1
                        + Weekday(gvMonthStart, StartOfWeek.Monday) - 1) / 7, 0) + 1
            }
        )
    )
);
Set(gvWorkdays, CountRows(Filter(colDays, !휴일)));

ClearCollect(colRec, Filter(근태기록, 근무일 >= gvMonthStart, 근무일 <= gvMonthEnd))
```

> **문장 사이의 `;` 를 빠뜨리면 `연산자가 필요합니다` 가 뜬다.** 블록을 이어 붙일 때
> 앞 블록의 마지막 문장에 `;` 가 없으면 두 문장이 한 식으로 읽힌다. 규칙은 하나다 —
> **마지막 문장 빼고 전부 `;` 로 끝난다.** `App.OnStart` 는 맨 끝
> `ClearCollect(colRec, ...)` 뒤에만 `;` 가 없다.

**`App.OnStart`** = 이번 달 시작 + 한 번만 블록 + 월 갱신 블록

```powerfx
Set(gvMonthStart, Date(Year(Today()), Month(Today()), 1));
```

**`btnPrev.OnSelect`** = 달 이동 + 월 갱신 블록

```powerfx
Set(gvMonthStart, DateAdd(gvMonthStart, -1, TimeUnit.Months));
```

**`btnNext.OnSelect`** = 달 이동 + 월 갱신 블록

```powerfx
Set(gvMonthStart, DateAdd(gvMonthStart, 1, TimeUnit.Months));
```

> **`galMonth.Items` 는 손대지 않는다.** `colHoliday` 가 로컬 컬렉션이라 날마다 조회해도
> 비용이 없고, 이미 검증된 수식이다. `colDays` 는 개인 요약 · 주별 64h 를 위해 추가하는
> 것이고 달력과는 별개다.

> **`명부` 의 `사용자` 열을 아직 안 만들었으면 `gvMe` 를 넣지 않는다.** 없는 열을
> 참조하면 앱 전체가 오류가 된다. 열을 추가한 뒤 아래 한 줄을 「한 번만」 블록에 더하면
> 본인 자동 선택이 된다 — `Set(gvMe, LookUp(명부, 사용자.Email = User().Email, Title))`

### 4-2. 월 달력 — 날짜별 30% 판정

**`galMonth.Items`** — 이 하나가 30% 판정의 전부다

```powerfx
ForAll(Sequence(Day(gvMonthEnd)) As S,
    With({ d: DateAdd(gvMonthStart, S.Value - 1, TimeUnit.Days) },
        With({ hol: Weekday(d, StartOfWeek.Monday) > 5
                    || !IsBlank(LookUp(colHoliday, 날짜 = d)) },
            {
                날짜: d,
                일:   S.Value,
                요일: Switch(Weekday(d, StartOfWeek.Monday),
                             1, "월", 2, "화", 3, "수", 4, "목", 5, "금", 6, "토", 7, "일"),
                휴일: hol,
                필요인원: If(hol, 0, gvNeed),
                충족인원: If(hol, 0,
                    gvActive - CountRows(Filter(colRec As R,
                        R.근무일 = d, R.충족 = 0))),
                직책자: If(hol, 0,
                    gvLeads - CountRows(Filter(colRec As R,
                        R.근무일 = d, R.충족 = 0,
                        !IsBlank(LookUp(colLeads, Title = R.구성원)))))
            }
        )
    )
)
```

> **핵심은 `gvActive - (충족=0 인 기록 수)` 다.** 기록이 없는 날은 8시간 근무이므로
> 전원이 충족으로 시작하고, 예외를 넣은 사람만 빠진다. `근태기록` 을 비워둔 채
> 운영하는 이유가 이것이다 — 23명 × 22일을 미리 채울 필요가 없다.

행 배경색 — **`galMonth.TemplateFill`**

```powerfx
If(ThisItem.휴일,                        RGBA(240, 241, 243, 1),
   ThisItem.충족인원 < ThisItem.필요인원, RGBA(251, 234, 233, 1),
   ThisItem.직책자 < 1,                  RGBA(253, 243, 221, 1),
                                         RGBA(230, 244, 236, 1))
```

행 안의 레이블 두 개 — **`lblDay.Text`** · **`lblCnt.Text`**

```powerfx
ThisItem.일 & " (" & ThisItem.요일 & ")"
```
```powerfx
If(ThisItem.휴일,
   "휴일",
   ThisItem.충족인원 & " / " & ThisItem.필요인원 & "명"
     & If(ThisItem.충족인원 < ThisItem.필요인원,
          "   ✗ " & (ThisItem.필요인원 - ThisItem.충족인원) & "명 부족", "")
     & If(ThisItem.직책자 < 1, "   ⚠ 직책자 0명", ""))
```

화면 상단 요약 — **`lblMonth.Text`**

```powerfx
gvYM & "   모수 " & gvActive & "명 · 필요 " & gvNeed & "명"
  & "   |   미달일 "
  & CountRows(Filter(galMonth.AllItems, !휴일, 충족인원 < 필요인원)) & "일"
  & "   직책자 없는 날 "
  & CountRows(Filter(galMonth.AllItems, !휴일, 직책자 < 1)) & "일"
```

### 4-3. 조율 후보 — 미달일에 8시간으로 바꿔줄 수 있는 사람

건강검진 · 연차 · 출장 · 교육은 본인이 바꿀 수 없으므로 후보에서 뺀다.
바꿀 수 있는 것은 **근무 시각 조정 · 반차 · 반반차**뿐이다.

**`galCandidate.Items`** — 달력에서 고른 날짜의 후보

```powerfx
Filter(colRec As R,
    R.근무일 = galMonth.Selected.날짜,
    R.충족 = 0,
    R.구분 in ["근무", "반차", "반반차"]
)
```

표시 텍스트 — **`lblCand.Text`**

```powerfx
ThisItem.구성원 & "   " & ThisItem.조합코드
  & "   (실근로 " & ThisItem.실근로 & "h · 휴가 " & ThisItem.휴가 & "h)"
```

후보 목록 머리글 — **`lblCandHead.Text`**

```powerfx
If(IsBlank(galMonth.Selected),
   "달력에서 날짜를 고르세요",
   Text(galMonth.Selected.날짜, "m월 d일")
     & If(galMonth.Selected.충족인원 < galMonth.Selected.필요인원,
          "  ✗ " & (galMonth.Selected.필요인원 - galMonth.Selected.충족인원)
            & "명 부족",
          "  ✓ 충족")
     & "   ·   조율 가능 " & CountRows(galCandidate.AllItems) & "명")
```

> **여기까지가 엑셀로 하던 작업의 대체다.** 미달일이 빨갛게 보이고, 그 날을 누르면
> 「누구에게 부탁하면 되는지」가 바로 나온다. 엑셀에서는 사람 23명 × 날짜 22일을
> 눈으로 세야 했던 일이다.

### 4-4. 내 근태 입력 — 연쇄 드롭다운 ★

이 앱의 핵심이다. 세 컨트롤의 `Items` 만 이렇게 넣으면 규칙 위반이 원천 차단된다.

```powerfx
// ddType.Items — 유형 11개
Distinct(colCombo, 유형)

// ddStart.Items — 고른 유형에서 가능한 출근만 (오전반이면 2개)
Distinct(Filter(colCombo, 유형 = ddType.Selected.Value, !IsBlank(출근)), 출근)

// ddEnd.Items — 유형 + 출근에서 가능한 퇴근만 (오전반 13:00 이면 4개)
Distinct(
    Filter(colCombo, 유형 = ddType.Selected.Value, 출근 = ddStart.Selected.Value),
    퇴근
)

// 시각이 필요 없는 유형(연차 · 출장 · 교육 · 기타 · 휴직)이면 두 칸을 숨긴다
// ddStart.Visible · ddEnd.Visible
CountRows(ddStart.Items) > 0
```

유형을 바꾸면 출근·퇴근 선택을 비운다 — `ddType.OnChange`

```powerfx
Reset(ddStart); Reset(ddEnd)
```

### 4-5. OT 시간 — 분 단위 · 자정 넘김 · 석식 공제

**`lblOt.Text`**

```powerfx
If(Len(txtOtS.Text) < 5 || Len(txtOtE.Text) < 5,
   "0",
   With({
       a:  Value(Left(txtOtS.Text, 2)) * 60 + Value(Right(txtOtS.Text, 2)),
       b:  Value(Left(txtOtE.Text, 2)) * 60 + Value(Right(txtOtE.Text, 2)),
       ds: gvRegEnd,       // 석식 창 시작 = 그 달의 정규 근로 종료 (월설정에서 읽는다)
       de: gvRegEnd + 30,  // 석식 창 종료 = +30분
       dn: Coalesce(ddDinner.Selected.Value, "자동")
   },
       With({ e: If(b <= a, b + 1440, b) },   // 자정을 넘긴 OT
           Text(RoundDown(
               ( (e - a)
                 - If(dn = "실시" || (dn = "자동" && e > de),
                      Max(0, Min(e, de) - Max(a, ds)),
                      0)
               ) / 60 * 100, 0) / 100)
       )
   )
)
```

> **OT 칸이 비면 `"0"` 을 돌려준다.** `Len(...) < 5` 로 `20:30` 형식이 갖춰졌는지만
> 본다. 평일 대부분은 비워둔 채 저장하므로 이 분기가 기본 경로다.

> `gvRegEnd` 는 `월설정` 의 `정규종료` 에서 읽으므로, 탄력근무 달에 `17:00` 로만
> 바꿔 넣으면 석식 창이 `17:00~17:30` 으로 자동 이동한다.

**석식 공제가 걸리는 조건.** 석식 창(`정규종료` ~ `+30분`)과 OT 구간이 **겹칠 때만**
공제한다. `20:30~23:15` 는 석식 창 `17:30~18:00` 을 이미 지나서 시작하므로 겹치는
구간이 0분 → 공제 없이 `2.75h`. `17:30~20:00` 은 30분이 겹치므로 `2h`.

### 4-6. 저장 — 조합표에서 값을 읽어 함께 저장

**`btnSave.OnSelect`** (5단계 확장판 — OT · 주 · 메모까지 저장)

```powerfx
Set(gvCode,
    If(IsBlank(ddStart.Selected.Value),
       ddType.Selected.Value,
       ddType.Selected.Value & " "
         & Substitute(ddStart.Selected.Value, ":", "") & "-"
         & Substitute(ddEnd.Selected.Value,   ":", "")));
Set(gvC,   LookUp(colCombo, Title = gvCode));
Set(gvKey, Text(dpDate.SelectedDate, "yyyy-mm-dd") & "_" & ddMe.Selected.Value);
Set(gvRec, LookUp(근태기록, Title = gvKey));

If(IsBlank(gvC),
    Notify("규칙에 없는 조합입니다 — " & gvCode, NotificationType.Error),

    Patch(근태기록,
        If(IsBlank(gvRec), Defaults(근태기록), gvRec),
        {
            Title:    gvKey,
            근무일:   dpDate.SelectedDate,
            구성원:   ddMe.Selected.Value,
            유형:     ddType.Selected.Value,
            출근:     ddStart.Selected.Value,
            퇴근:     ddEnd.Selected.Value,
            조합코드: gvCode,
            실근로:   gvC.실근로,
            휴가:     gvC.휴가,
            충족:     gvC.충족,
            구분:     gvC.구분,
            OT시작:   txtOtS.Text,
            OT종료:   txtOtE.Text,
            OT시간:   Value(lblOt.Text),
            석식:     Coalesce(ddDinner.Selected.Value, "자동"),
            주:       LookUp(colDays, 날짜 = dpDate.SelectedDate, 주),
            메모:     txtNote.Text
        });
    Refresh(근태기록);
    ClearCollect(colRec, Filter(근태기록, 근무일 >= gvMonthStart, 근무일 <= gvMonthEnd));
    Notify("저장 완료 — " & gvKey & " · " & gvCode
             & If(Value(lblOt.Text) > 0, " · OT " & lblOt.Text & "h", ""),
           NotificationType.Success))
```

> **`주` 는 `colDays` 에서 읽는다.** 그래서 5-1(월 갱신 블록)을 먼저 해야 한다.
> 주별 64시간 판정이 이 값을 쓴다.

> **`ddMe` 로 저장한다.** `명부` 에 `사용자` 열을 만들어 `gvMe` 를 쓰게 되면
> `ddMe.Selected.Value` 를 `gvMe` 로 바꾸면 된다.

기록 지우기는 §3-2 의 `icoDel.OnSelect` 를 쓴다 — 저장 목록에서 행마다 지우는 편이
날짜를 다시 맞춰 지우는 것보다 안전하다.

### 4-7. 개인 요약

**대상자는 변수 하나로 다룬다.** `Screen1` 에서 고른 사람이 기본이 되게 한다.

**`scrSummary.OnVisible`**

```powerfx
Set(gvWho, Coalesce(ddWho.Selected.Value, ddMe.Selected.Value))
```

**`ddWho.Items`** · **`ddWho.OnChange`**

```powerfx
Distinct(명부, Title)
```
```powerfx
Set(gvWho, ddWho.Selected.Value)
```

**`lblSumHead.Text`**

```powerfx
Coalesce(gvWho, "구성원을 고르세요") & "   ·   " & gvYM
```

**`galKpi.Items`** — 총량 · 휴가 · 실근로 · OT 를 한 표로

```powerfx
With({ mine: Filter(colRec As R, R.구성원 = gvWho) },
  With({
      휴가:       Coalesce(Sum(mine, 휴가), 0),
      기록실근로: Coalesce(Sum(mine, 실근로), 0),
      기록소정:   CountRows(Filter(mine As M,
                     !LookUp(colDays, 날짜 = M.근무일, 휴일))),
      OT누적:     Coalesce(Sum(mine, OT시간), 0)
  },
    With({
        조정총량: gvWorkdays * 8 - 휴가,
        실근로:   (gvWorkdays - 기록소정) * 8 + 기록실근로
    },
      Table(
        { 항목: "소정근로일",   값: gvWorkdays & "일",
          비고: "기본 총량 " & gvWorkdays * 8 & "h" },
        { 항목: "휴가 사용",     값: 휴가 & "h",           비고: "" },
        { 항목: "조정 총량",     값: 조정총량 & "h",       비고: "기본 총량 − 휴가" },
        { 항목: "실근로 누적",   값: 실근로 & "h",         비고: "기록 없는 날은 8h" },
        { 항목: "차이",         값: If(실근로 - 조정총량 >= 0, "+", "")
                                    & (실근로 - 조정총량) & "h",
          비고: If(실근로 < 조정총량, "부족",
                   If(실근로 > 조정총량, "초과", "정확")) },
        { 항목: "OT 기본",      값: gvOtBase & "h",       비고: gvYM & " 월설정" },
        { 항목: "OT 한도",      값: (gvOtBase + 휴가) & "h",
          비고: "휴가 " & 휴가 & "h 가산" },
        { 항목: "OT 누적",      값: OT누적 & "h",         비고: "" },
        { 항목: "OT 잔여",      값: (gvOtBase + 휴가 - OT누적) & "h", 비고: "" }
      )
    )
  )
)
```

> **`기록 없는 날은 8h`** 가 이 계산의 전부다. 소정근로일 20일 중 기록이 1건이면
> 나머지 19일은 8시간씩 근무한 것으로 보고, 기록이 있는 1일만 실제 값을 쓴다.

> **`OT 한도 = OT기본 + 휴가` 는 아직 확인이 필요하다.** 휴가를 쓴 만큼 총량이
> 줄어드니 OT 여유가 그만큼 생긴다는 해석인데, 규정상 그렇게 되는지, 반차 · 반반차에도
> 비례 적용되는지 담당자 확인이 필요하다 (§6).

행 안의 레이블 셋 — **`lblKpiName.Text`** · **`lblKpiVal.Text`** · **`lblKpiNote.Text`**

```powerfx
ThisItem.항목
```
```powerfx
ThisItem.값
```
```powerfx
ThisItem.비고
```

**`lblKpiVal.Color`** — 부족은 빨강, 초과는 주황

```powerfx
If(ThisItem.비고 = "부족", RGBA(179, 38, 30, 1),
   ThisItem.비고 = "초과", RGBA(138, 90, 0, 1),
                           RGBA(22, 24, 29, 1))
```

**`galWeek.Items`** — 주별 64시간 한도

```powerfx
ForAll(Sequence(Max(colDays, 주)) As W,
    With({
        소정: CountRows(Filter(colDays, 주 = W.Value, !휴일)),
        recs: Filter(colRec As R, R.구성원 = gvWho, R.주 = W.Value)
    },
        {
            주:   W.Value,
            기간: Text(LookUp(colDays, 주 = W.Value, 날짜), "m/d") & " ~ "
                  & Text(Last(Filter(colDays, 주 = W.Value)).날짜, "m/d"),
            소정: 소정,
            근로: (소정 - CountRows(recs)) * 8
                  + Coalesce(Sum(recs, 실근로), 0)
                  + Coalesce(Sum(recs, OT시간), 0)
        }
    )
)
```

> **`주` 는 저장할 때 `colDays` 에서 읽어 넣은 값이다.** 그래서 5-1 을 먼저 해야 한다.
> `(소정 - CountRows(recs))` 는 기록이 소정근로일에만 있다고 가정한 근사다 — 휴일
> 근무를 기록하기 시작하면 `Filter(recs As M, !LookUp(colDays, 날짜 = M.근무일, 휴일))`
> 로 걸러야 정확하다.

**`lblWeek.Text`** · **`galWeek.TemplateFill`**

```powerfx
"주 " & ThisItem.주 & "   " & ThisItem.기간
  & "   소정 " & ThisItem.소정 & "일   근로 " & ThisItem.근로 & "h"
  & If(ThisItem.근로 > 64, "   ✗ 64h 초과", "")
```
```powerfx
If(ThisItem.근로 > 64, RGBA(251, 234, 233, 1), RGBA(246, 247, 249, 1))
```

**`galMy.Items`** — 이 사람의 이번 달 기록

```powerfx
Sort(Filter(colRec As R, R.구성원 = gvWho), 근무일, SortOrder.Ascending)
```

**`lblMy.Text`**

```powerfx
Text(ThisItem.근무일, "[$-ko]m/d (ddd)") & "   " & ThisItem.조합코드
  & "   실근로 " & ThisItem.실근로 & "h"
  & If(ThisItem.휴가 > 0, " · 휴가 " & ThisItem.휴가 & "h", "")
  & If(Coalesce(ThisItem.OT시간, 0) > 0, " · OT " & ThisItem.OT시간 & "h", "")
```

### 4-8. 탄력근무 3개월 평균 52시간

단위기간이 달을 넘기므로 `colRec` 대신 기간 전체를 따로 읽는다.
SharePoint 는 집계를 위임하지 못하므로 **월별로 세 번 나눠 읽어** 행 제한을 피한다(§0-1).

```powerfx
// btnFlexLoad.OnSelect — 시작 월을 dpFlex 로 고른다
Set(gvFlexStart, Date(Year(dpFlex.SelectedDate), Month(dpFlex.SelectedDate), 1));
Set(gvFlexEnd,   DateAdd(DateAdd(gvFlexStart, 3, TimeUnit.Months), -1, TimeUnit.Days));

Clear(colFlex);
ForAll(Sequence(3) As Mo,
    With({ ms: DateAdd(gvFlexStart, Mo.Value - 1, TimeUnit.Months) },
        Collect(colFlex,
            Filter(근태기록,
                근무일 >= ms,
                근무일 <= DateAdd(DateAdd(ms, 1, TimeUnit.Months), -1, TimeUnit.Days)))
    )
);

// 단위기간 소정근로일 수
Set(gvFlexDays,
    CountRows(Filter(
        ForAll(Sequence(DateDiff(gvFlexStart, gvFlexEnd, TimeUnit.Days) + 1) As S,
            { d: DateAdd(gvFlexStart, S.Value - 1, TimeUnit.Days) }),
        Weekday(d, StartOfWeek.Monday) <= 5 && IsBlank(LookUp(colHoliday, 날짜 = d))
    ))
);
Set(gvFlexTotalDays, DateDiff(gvFlexStart, gvFlexEnd, TimeUnit.Days) + 1);
```

구성원별 판정 — `galFlex.Items`

```powerfx
ForAll(colMembers As M,
    With({ recs: Filter(colFlex, 구성원 = M.Title) },
        With({
            총근로: (gvFlexDays - CountRows(recs)) * 8
                    + Sum(recs, 실근로) + Sum(recs, OT시간)
        },
            {
                이름:   M.Title,
                총근로: 총근로,
                평균주: Round(총근로 / (gvFlexTotalDays / 7), 1),
                적합:   총근로 / (gvFlexTotalDays / 7) <= 52
            }
        )
    )
)
```

> `(gvFlexDays - CountRows(recs))` 는 기록이 소정근로일에만 있다고 가정한 근사다.
> 휴일 근무 기록이 있으면 `Filter(recs, !휴일)` 로 걸러야 정확하다 — HTML 도구의
> 계산과 대조해 검증하는 것을 권한다.

## 4-8-1. 위임 경고 — 무해하지만 없애는 편이 낫다

`대규모 데이터 세트에서는 이 수식의 "휴직" 부분이 제대로 작동하지 않을 수 있습니다`
같은 노란 경고가 뜬다. 데이터가 500행을 넘으면 부정확해질 수 있다는 뜻이고,
`명부` 24행 · `공휴일` 21행이라 실제로는 문제가 없다.

그래도 **`공휴일` 조회는 성능 때문에 반드시 컬렉션으로 바꾼다.**
`galMonth.Items` 안의 `LookUp(공휴일, 날짜 = d)` 는 `ForAll` 안에 있어
**한 달 그릴 때마다 SharePoint 를 30번 왕복**한다. `App.OnStart` 에서
`ClearCollect(colHoliday, 공휴일)` 로 한 번만 읽고 `colHoliday` 를 쓰면
왕복이 1번으로 줄고 경고도 함께 사라진다.

| 원래 | 바꿀 것 | 이유 |
|---|---|---|
| `LookUp(공휴일, 날짜 = d)` | `LookUp(colHoliday, 날짜 = d)` | 30번 왕복 → 1번 |
| `Filter(명부, IsBlank(휴직))` | `Filter(colAll, IsBlank(휴직))` | `IsBlank` 는 위임되지 않는다 |

**`근태기록` 조회는 그대로 둔다.** `Filter(근태기록, 근무일 >= …, 근무일 <= …)` 는
날짜 비교라 SharePoint 로 위임되고, 여기만은 컬렉션으로 올릴 수 없다 — 다른 사람이
방금 저장한 것을 읽어야 하므로 매번 새로 읽는 것이 맞다.

## 4-9. 배치와 디자인은 마지막에 한 번에

**기능이 먼저다.** 수식이 흔들리는 동안 배치까지 잡으면 두 번 일하게 되고, Power Apps
에서 배치는 컨트롤이 다 있는 상태에서 `X`·`Y`·`Width`·`Height` 에 숫자를 넣는 편이
훨씬 빠르다. 각 화면 절에 좌표표를 두고, 색·글꼴 통일은 5단계가 끝난 뒤 한 번에 한다.

**색은 새로 정하지 않는다** — HTML 도구(`worktime/index.html`)의 팔레트를 그대로 쓴다.
두 도구가 같은 판정을 같은 색으로 보여줘야 혼선이 없다.

| 용도 | HTML 도구 | Power Fx |
|---|---|---|
| 충족 | `#0f7b4f` / 배경 `#e6f4ec` | `RGBA(15,123,79,1)` / `RGBA(230,244,236,1)` |
| 미달 | `#b3261e` / 배경 `#fbeae9` | `RGBA(179,38,30,1)` / `RGBA(251,234,233,1)` |
| 주의 | `#8a5a00` / 배경 `#fdf3dd` | `RGBA(138,90,0,1)` / `RGBA(253,243,221,1)` |
| 강조 | `#1c4e80` / 배경 `#e8eef6` | `RGBA(28,78,128,1)` / `RGBA(232,238,246,1)` |
| 휴일 · 비활성 | `#f0f1f3` | `RGBA(240,241,243,1)` |
| 본문 · 흐린 글자 | `#16181d` · `#6b7280` | `RGBA(22,24,29,1)` · `RGBA(107,114,128,1)` |
| 테두리 | `#e3e6ea` | `RGBA(227,230,234,1)` |

마지막 디자인 단계에서 할 일:

- 화면 네 개의 머리글 · 여백 · 글자 크기 통일 (위 표의 좌표 규칙을 그대로 적용)
- Teams 모바일 대응 여부 결정 — 지금은 PC 기준 고정 좌표다
- 탭 이름 · 아이콘, 팀원 공유 (§5)

## 5. Teams 탭으로 게시

1. Power Apps 편집기 → `게시`(Publish)
2. Teams 앱 목록에서 앱 → `Teams 에 추가`
3. 두 팀이 함께 있는 채널 → `+` → 만든 앱 선택 → 탭 이름 `근태`
4. 구성원에게 공유 — 앱은 **편집자(Can edit)** 가 아니라 **사용자(Can use)** 로

## 6. 반드시 확인할 것

| 항목 | 왜 |
|---|---|
| **데이터 행 제한 2000** | 기본 500 이면 월 기록이 넘는 순간 집계가 조용히 틀린다 |
| **`근무일` 은 「시간 없음」 날짜** | 시간이 붙으면 `근무일 = 날짜` 비교가 어긋난다 |
| **`명부.사용자` 채우기** | 비어 있으면 `gvMe` 가 빈값이 되어 본인 근태를 못 찾는다 |
| **휴직자는 기록을 남기지 않는다** | 30% 계산이 `활성 − 충족0 기록수` 이므로 |
| **`공휴일.날짜` 는 날짜 타입** | 텍스트로 들어가면 소정근로일 계산이 전부 어긋난다 |
| **`명부.휴직` 은 `Y` 또는 빈칸** | `IsBlank(휴직)` 으로 활성 여부를 판정한다 |
| **월설정에 그 달 OT기본 넣기** | 없으면 OT 한도가 휴가분만 잡힌다 |
| **개인정보 취급 승인** | 구성원 근태 데이터라 사내 등록·승인 절차가 있을 수 있다 |

## 7. 엑셀 · HTML 도구와의 관계

세 산출물이 **같은 규칙 원천**(`combos.json`)을 쓴다. 규칙이 바뀌면

```
worktime/index.html  (규칙 엔진 수정)
        │
        ▼  node worktime/gen_combos.js
worktime/data/combos.json
        ├─▶ python worktime/build_xlsx.py     → 엑셀 드롭다운 갱신
        └─▶ worktime/data/sp_조합표.csv       → 조합표 목록 교체
```

Power Apps 가 안정화되면 엑셀은 백업·내보내기 용도로 남기고, HTML 도구는
**규칙을 고치고 검증하는 개발 도구**로 쓴다(자가검증 38사례 · 90단정).
