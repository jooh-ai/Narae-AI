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
    With({ ms: DateAdd(gvFlexStart, Mo.Value - 1, Months) },
        Collect(colFlex,
            Filter(근태기록,
                근무일 >= ms,
                근무일 <= DateAdd(DateAdd(ms, 1, Months), -1, Days)))
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
| 조합코드 | 텍스트 (제목 열 이름 변경) | `근무 0830-1730` |
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
| 이름 | 텍스트 (제목 열) | |
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
| 키 | 텍스트 (제목 열) | `2026-09-07_박상호` — 중복 방지 |
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
| 연월 | 텍스트 (제목 열) — `2026-09` |
| OT기본 | 숫자 |
| 정규종료 | 텍스트 — `17:30` (탄력근무 달은 `17:00` 등). 석식 휴게 계산에 쓴다 |
| 비고 | 텍스트 |

`sp_월설정.csv` 를 가져오면 두 달치가 들어간다. **OT기본은 담당자 확인 후 실제 값으로.**

### 1-5. `공휴일`

| 열 이름 | 타입 |
|---|---|
| 명칭 | 텍스트 (제목 열) |
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

### 3-1. 컨트롤 8개

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
Distinct(명부, 이름)
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

> **`'조합코드'을(를) 인식할 수 없습니다` · `'키'을(를) 인식할 수 없습니다`** — 아래
> §3-2-1 을 먼저 읽는다. 제목(Title) 열의 이름이 SharePoint 에서 보이는 것과 Power Apps
> 에 노출되는 것이 다를 수 있다. 나머지 열은 멀쩡한데 **제목 열 하나만** 인식이 안 되는
> 것이 이 문제의 특징이다.

**`lblPreview.Text`** — 저장 전에 판정을 보여준다

```powerfx
With({ code:
    If(IsBlank(ddStart.Selected.Value),
       ddType.Selected.Value,
       ddType.Selected.Value & " "
         & Substitute(ddStart.Selected.Value, ":", "") & "-"
         & Substitute(ddEnd.Selected.Value, ":", ""))
},
    With({ c: LookUp(colCombo, 조합코드 = code) },
        If(IsBlank(c),
           "✗ 규칙에 없는 조합 — " & code,
           code & "   실근로 " & c.실근로 & "h · 휴가 " & c.휴가 & "h · "
             & If(c.충족 = 1, "30% 충족", "30% 미충족"))
    )
)
```

**`lblPreview.Color`** — 규칙에 없으면 빨강

```powerfx
If(IsBlank(LookUp(colCombo, 조합코드 =
    If(IsBlank(ddStart.Selected.Value), ddType.Selected.Value,
       ddType.Selected.Value & " " & Substitute(ddStart.Selected.Value, ":", "")
         & "-" & Substitute(ddEnd.Selected.Value, ":", "")))),
   RGBA(179, 38, 30, 1), RGBA(15, 123, 79, 1))
```

**`btnSave.OnSelect`** — 조합표에서 값을 읽어 함께 저장한다

```powerfx
Set(gvCode,
    If(IsBlank(ddStart.Selected.Value),
       ddType.Selected.Value,
       ddType.Selected.Value & " "
         & Substitute(ddStart.Selected.Value, ":", "") & "-"
         & Substitute(ddEnd.Selected.Value, ":", "")));
Set(gvC,   LookUp(colCombo, 조합코드 = gvCode));
Set(gvKey, Text(dpDate.SelectedDate, "yyyy-mm-dd") & "_" & ddMe.Selected.Value);
Set(gvRec, LookUp(근태기록, 키 = gvKey));

If(IsBlank(gvC),
    Notify("규칙에 없는 조합입니다 — " & gvCode, NotificationType.Error),

    Patch(근태기록,
        If(IsBlank(gvRec), Defaults(근태기록), gvRec),
        {
            키:       gvKey,
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
ThisItem.키 & "   " & ThisItem.조합코드 & "   실근로 " & ThisItem.실근로 & "h"
```

### 3-2-1. 제목(Title) 열 이름이 인식되지 않을 때

`유형` · `출근` · `퇴근` · `구성원` 같은 **보통 열은 다 되는데** `조합표` 의 `조합코드`
와 `근태기록` 의 `키` 만 `인식할 수 없습니다` 로 뜨는 경우가 있다. 이 두 개는 SharePoint
의 **제목(Title) 열을 이름만 바꾼 것**이라, 목록 화면에는 바꾼 이름이 보여도 Power Apps
에는 다른 이름(`Title` · `제목`, 드물게 앞에 보이지 않는 문자가 붙은 이름)으로 노출될 수
있다.

**확인 — 30초면 된다.** 레이블 아무거나 하나 선택하고 `Text` 수식 바에 이렇게까지만 친다.

```powerfx
First(조합표).
```

마지막 점을 찍는 순간 **그 목록의 열 이름 전체가 자동 완성 목록으로 뜬다.** 여기 뜨는
이름이 Power Apps 가 아는 진짜 이름이다. `근태기록` 도 같은 방법으로 확인한다.

```powerfx
First(근태기록).
```

**고치는 법.** 목록에 뜬 이름을 **손으로 타이핑하지 말고 자동 완성에서 골라 넣는다.**
CSV 가져오기로 만든 열은 이름 앞에 눈에 보이지 않는 문자(BOM)가 붙어 있을 수 있어,
똑같아 보이는 글자를 쳐도 맞지 않는 경우가 있다. 골라 넣으면 이 문제까지 같이 해결된다.

노출 이름이 `Title` 이었다면 다음 네 군데를 바꾸면 된다. **`근태기록` 의 `조합코드` 는
진짜 사용자 지정 열이므로 그대로 둔다** — 바꾸는 것은 제목 열뿐이다.

| 수식 | 원래 | 바꿀 것 |
|---|---|---|
| `lblPreview.Text` | `LookUp(colCombo, 조합코드 = code)` | `LookUp(colCombo, Title = code)` |
| `lblPreview.Color` | `LookUp(colCombo, 조합코드 = …)` | `LookUp(colCombo, Title = …)` |
| `btnSave.OnSelect` | `LookUp(colCombo, 조합코드 = gvCode)` | `LookUp(colCombo, Title = gvCode)` |
| `btnSave.OnSelect` | `LookUp(근태기록, 키 = gvKey)` · `키: gvKey` | `LookUp(근태기록, Title = gvKey)` · `Title: gvKey` |
| 갤러리 레이블 `Text` | `ThisItem.키` | `ThisItem.Title` |

**그래도 계속 걸리면 제목 열을 아예 안 쓰는 방법이 있다.** SharePoint 에서 두 목록에
`코드` · `기록키` 같은 **새 사용자 지정 열**(한 줄 텍스트)을 만들고, `조합표` 는
`sp_조합표.csv` 를 다시 가져와 채운다. 사용자 지정 열은 이름이 그대로 노출되므로
이런 혼선이 없다. `근태기록` 은 비어 있으므로 열만 추가하면 되고, 앱에서는
`키` 대신 `기록키` 를 쓰면 된다.

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

**규칙에 없는 조합을 만들 수 없다는 것**이 핵심이다. `오전반` 을 골랐을 때 `08:30` 이
목록에 아예 없으므로 고를 수가 없다. 엑셀에서 사후에 빨갛게 표시하던 것이
입력 단계에서 차단된다.

### 3-4. 다음에 붙일 화면들

1차 목표가 확인되면 아래 화면을 하나씩 붙인다. 수식은 §4 에 있다.

### 화면 구성 (4개)

| 화면 | 용도 | 주 사용자 |
|---|---|---|
| `scrMonth` | 월 달력 — 날짜별 30% 판정 · 미달일 · 조율 후보 | 전원 (조율용) |
| `scrMy` | 내 근태 입력 — 연쇄 드롭다운 | 전원 (매일) |
| `scrSummary` | 개인 요약 — 총량 · OT 잔여 · 주별 64h | 본인 |
| `scrFlex` | 탄력근무 3개월 평균 52h | 관리 |

## 4. Power Fx 수식

### 4-1. `App.OnStart` — 기준값과 이번 달 준비

```powerfx
Set(gvMonthStart, Date(Year(Today()), Month(Today()), 1));
Set(gvMonthEnd,   DateAdd(DateAdd(gvMonthStart, 1, Months), -1, Days));
Set(gvYM,         Text(gvMonthStart, "yyyy-mm"));

// 조합표(106행)와 명부는 작아서 전부 올려두고 로컬로 쓴다 — 위임 걱정이 사라진다
ClearCollect(colCombo,  조합표);
ClearCollect(colMembers, Filter(명부, IsBlank(휴직)));   // 휴직자는 Y, 나머지는 빈칸
Set(gvActive, CountRows(colMembers));
Set(gvNeed,   RoundUp(gvActive * 0.3, 0));
Set(gvLeads,  CountRows(Filter(colMembers, 직책 <> "구성원")));
Set(gvMe,     LookUp(명부, 사용자.Email = User().Email, 이름));

// 이번 달 기록을 한 번만 읽어 온다 — 이후 계산은 전부 이 컬렉션에서
ClearCollect(colRec, Filter(근태기록, 근무일 >= gvMonthStart, 근무일 <= gvMonthEnd));

// 그 달의 날짜 · 요일 · 휴일 · 주 순번
ClearCollect(colDays,
    ForAll(Sequence(Day(gvMonthEnd)) As S,
        With({ d: DateAdd(gvMonthStart, S.Value - 1, Days) },
            {
                날짜: d,
                일:   S.Value,
                요일: Text(d, "[$-ko]ddd"),
                휴일: Weekday(d, StartOfWeek.Monday) > 5
                      || !IsBlank(LookUp(공휴일, 날짜 = d)),
                주:   RoundDown((S.Value - 1
                        + Weekday(gvMonthStart, StartOfWeek.Monday) - 1) / 7, 0) + 1
            }
        )
    )
);
Set(gvWorkdays, CountRows(Filter(colDays, !휴일)));

// 이 달의 OT 기본 가능시간과 정규 근로 종료 (석식 휴게 창의 시작점)
Set(gvMonthCfg, LookUp(월설정, 연월 = gvYM));
Set(gvOtBase,   Coalesce(gvMonthCfg.OT기본, 0));
Set(gvRegEnd,   Value(Left(Coalesce(gvMonthCfg.정규종료, "17:30"), 2)) * 60
                + Value(Right(Coalesce(gvMonthCfg.정규종료, "17:30"), 2)));
```

`colRec` 를 새로 읽어야 할 때(저장 직후 등)는 이 한 줄만 다시 실행한다.

```powerfx
ClearCollect(colRec, Filter(근태기록, 근무일 >= gvMonthStart, 근무일 <= gvMonthEnd));
```

### 4-2. 월 달력 — 날짜별 30% 판정

`galMonth.Items`

```powerfx
AddColumns(colDays,
    "충족인원", If(휴일, 0, gvActive - CountRows(Filter(colRec, 근무일 = 날짜, 충족 = 0))),
    "필요인원", If(휴일, 0, gvNeed),
    "직책자",   If(휴일, 0,
                  gvLeads - CountRows(Filter(colRec, 근무일 = 날짜, 충족 = 0,
                      구성원 in Filter(colMembers, 직책 <> "구성원").이름)))
)
```

행 배경색 — 미달이면 빨강, 직책자 0명이면 노랑

```powerfx
If(ThisItem.휴일,                        RGBA(240, 241, 243, 1),
   ThisItem.충족인원 < ThisItem.필요인원, RGBA(251, 234, 233, 1),
   ThisItem.직책자 < 1,                  RGBA(253, 243, 221, 1),
                                         RGBA(230, 244, 236, 1))
```

미달일 개수 (화면 상단 요약)

```powerfx
CountRows(Filter(galMonth.AllItems, !휴일, 충족인원 < 필요인원))
```

### 4-3. 조율 후보 — 미달일에 8시간으로 바꿔줄 수 있는 사람

출장 · 교육 · 연차 · 건강검진은 바꿀 수 없으므로 제외한다.

`galCandidate.Items`

```powerfx
Filter(colRec,
    근무일 = galMonth.Selected.날짜,
    충족 = 0,
    구분 in ["근무", "반차", "반반차"]
)
```

표시 텍스트

```powerfx
ThisItem.구성원 & " (" & ThisItem.조합코드 & " · " & ThisItem.실근로 & "h)"
```

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

`lblOt.Text` 또는 저장 직전 `Set()`

```powerfx
With({
    a: Value(Left(txtOtS.Text, 2)) * 60 + Value(Right(txtOtS.Text, 2)),
    b: Value(Left(txtOtE.Text, 2)) * 60 + Value(Right(txtOtE.Text, 2)),
    ds: gvRegEnd,       // 석식 창 시작 = 그 달의 정규 근로 종료 (월설정에서 읽는다)
    de: gvRegEnd + 30   // 석식 창 종료 = +30분
},
    With({ e: If(b <= a, b + 1440, b) },   // 자정을 넘긴 OT
        RoundDown(
            ( (e - a)
              - If(ddDinner.Selected.Value = "실시"
                   || (ddDinner.Selected.Value = "자동" && e > de),
                   Max(0, Min(e, de) - Max(a, ds)),
                   0)
            ) / 60 * 100, 0) / 100
    )
)
```

> `gvRegEnd` 는 `월설정` 의 `정규종료` 에서 읽으므로, 탄력근무 달에 `17:00` 로만
> 바꿔 넣으면 석식 창이 `17:00~17:30` 으로 자동 이동한다.

### 4-6. 저장 — 조합표에서 값을 읽어 함께 저장

`btnSave.OnSelect`

```powerfx
Set(gvCode,
    If(IsBlank(ddStart.Selected.Value) || ddStart.Selected.Value = "",
       ddType.Selected.Value,
       ddType.Selected.Value & " "
         & Substitute(ddStart.Selected.Value, ":", "") & "-"
         & Substitute(ddEnd.Selected.Value,   ":", "")));

Set(gvCombo, LookUp(colCombo, 조합코드 = gvCode));

If(IsBlank(gvCombo),
    Notify("규칙에 없는 조합입니다. 유형·출근·퇴근을 다시 고르세요.",
           NotificationType.Error),

    Set(gvKey, Text(dpDate.SelectedDate, "yyyy-mm-dd") & "_" & gvMe);
    Set(gvRec, LookUp(근태기록, 키 = gvKey));
    Patch(근태기록,
        If(IsBlank(gvRec), Defaults(근태기록), gvRec),
        {
            키:       gvKey,
            근무일:   dpDate.SelectedDate,
            구성원:   gvMe,
            유형:     ddType.Selected.Value,
            출근:     ddStart.Selected.Value,
            퇴근:     ddEnd.Selected.Value,
            조합코드: gvCode,
            실근로:   gvCombo.실근로,
            휴가:     gvCombo.휴가,
            충족:     gvCombo.충족,
            구분:     gvCombo.구분,
            OT시작:   txtOtS.Text,
            OT종료:   txtOtE.Text,
            OT시간:   Value(lblOt.Text),
            석식:     ddDinner.Selected.Value,
            주:       LookUp(colDays, 날짜 = dpDate.SelectedDate, 주),
            메모:     txtNote.Text
        }
    );
    ClearCollect(colRec, Filter(근태기록, 근무일 >= gvMonthStart, 근무일 <= gvMonthEnd));
    Notify("저장했습니다", NotificationType.Success)
)
```

기록 지우기(= 8시간 근무로 되돌리기) — `btnClear.OnSelect`

```powerfx
Remove(근태기록, LookUp(근태기록, 키 = gvKey));
ClearCollect(colRec, Filter(근태기록, 근무일 >= gvMonthStart, 근무일 <= gvMonthEnd));
Notify("지웠습니다 — 이 날은 8시간 근무로 계산됩니다", NotificationType.Success)
```

### 4-7. 개인 요약

```powerfx
// 내 이번 달 기록
With({ mine: Filter(colRec, 구성원 = gvMe) },
    With({
        휴가:   Sum(mine, 휴가),
        기록실근로: Sum(mine, 실근로),
        // 기록이 있는 소정근로일 수 (나머지 소정근로일은 8시간으로 계산)
        기록소정: CountRows(Filter(mine,
                    !LookUp(colDays, 날짜 = 근무일, 휴일)))
    },
        {
            기본총량: gvWorkdays * 8,
            휴가:     휴가,
            조정총량: gvWorkdays * 8 - 휴가,
            실근로:   (gvWorkdays - 기록소정) * 8 + 기록실근로,
            차이:     ((gvWorkdays - 기록소정) * 8 + 기록실근로)
                      - (gvWorkdays * 8 - 휴가),
            OT누적:   Sum(mine, OT시간),
            OT한도:   gvOtBase + 휴가,
            OT잔여:   gvOtBase + 휴가 - Sum(mine, OT시간),
            "8시간일수": (gvWorkdays - 기록소정) + CountRows(Filter(mine, 충족 = 1))
        }
    )
)
```

주별 근로시간 (정규 + OT) — `galWeek.Items`

```powerfx
ForAll(Sequence(6) As W,
    With({
        days: Filter(colDays, 주 = W.Value, !휴일),
        recs: Filter(colRec, 구성원 = gvMe, 주 = W.Value)
    },
        {
            주:   W.Value,
            시간: (CountRows(days) - CountRows(Filter(recs, !LookUp(colDays, 날짜 = 근무일, 휴일))))
                  * 8 + Sum(recs, 실근로) + Sum(recs, OT시간)
        }
    )
)
```

64시간 초과 표시

```powerfx
If(ThisItem.시간 > 64, RGBA(179, 38, 30, 1), RGBA(22, 24, 29, 1))
```

### 4-8. 탄력근무 3개월 평균 52시간

단위기간이 달을 넘기므로 `colRec` 대신 기간 전체를 따로 읽는다.
SharePoint 는 집계를 위임하지 못하므로 **월별로 세 번 나눠 읽어** 행 제한을 피한다(§0-1).

```powerfx
// btnFlexLoad.OnSelect — 시작 월을 dpFlex 로 고른다
Set(gvFlexStart, Date(Year(dpFlex.SelectedDate), Month(dpFlex.SelectedDate), 1));
Set(gvFlexEnd,   DateAdd(DateAdd(gvFlexStart, 3, Months), -1, Days));

Clear(colFlex);
ForAll(Sequence(3) As Mo,
    With({ ms: DateAdd(gvFlexStart, Mo.Value - 1, Months) },
        Collect(colFlex,
            Filter(근태기록,
                근무일 >= ms,
                근무일 <= DateAdd(DateAdd(ms, 1, Months), -1, Days)))
    )
);

// 단위기간 소정근로일 수
Set(gvFlexDays,
    CountRows(Filter(
        ForAll(Sequence(DateDiff(gvFlexStart, gvFlexEnd, Days) + 1) As S,
            { d: DateAdd(gvFlexStart, S.Value - 1, Days) }),
        Weekday(d, StartOfWeek.Monday) <= 5 && IsBlank(LookUp(공휴일, 날짜 = d))
    ))
);
Set(gvFlexTotalDays, DateDiff(gvFlexStart, gvFlexEnd, Days) + 1);
```

구성원별 판정 — `galFlex.Items`

```powerfx
ForAll(colMembers As M,
    With({ recs: Filter(colFlex, 구성원 = M.이름) },
        With({
            총근로: (gvFlexDays - CountRows(recs)) * 8
                    + Sum(recs, 실근로) + Sum(recs, OT시간)
        },
            {
                이름:   M.이름,
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
