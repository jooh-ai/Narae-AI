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
| 팀 | 선택 항목 | 발전운영팀 · 정비기술팀 |
| 파트 | 선택 항목 | 발전지원 · 기계 · 전기 · 제어 · 정비지원 · 발전팀장 · 정비팀장 |
| 직책 | 선택 항목 | 팀장 · 파트장 · 구성원 |
| 그룹 | 선택 항목 | A · B · C |
| 휴직 | 예/아니요 | 기본값 아니요 |
| 사용자 | 사용자 또는 그룹 | 본인 근태만 보여주는 데 사용 (선택) |
| 정렬 | 숫자 | 표시 순서 |

`sp_명부.csv` 가져온 뒤 **사용자 열만 각자 계정으로 채운다.**

### 1-3. `근태기록` — 예외만 저장 (빈 기록 = 8시간 근무)

| 열 이름 | 타입 | 비고 |
|---|---|---|
| 키 | 텍스트 (제목 열) | `2026-09-07_박상호` — 중복 방지 |
| 근무일 | 날짜 (시간 없음) | |
| 구성원 | 텍스트 | 명부의 이름 |
| 유형 · 출근 · 퇴근 | 선택 항목 | `sp_선택항목.txt` 의 목록 그대로 |
| 조합코드 | 텍스트 | 앱이 조립해 저장 |
| 실근로 · 휴가 | 숫자 (소수 2자리) | 조합표에서 읽어 **저장** |
| 충족 | 숫자 | 조합표에서 읽어 저장 |
| 구분 | 텍스트 | 조율 후보 판별용 |
| OT시작 · OT종료 | 텍스트 | `20:30` · `23:15` |
| OT시간 | 숫자 (소수 2자리) | 앱이 계산해 저장 |
| 석식 | 선택 항목 | 자동 · 실시 · 미실시 |
| 주 | 숫자 | 그 달의 주 순번 — 주별 집계용 |
| 메모 | 텍스트 여러 줄 | |

> **실근로·휴가·충족을 저장하는 이유**: 매번 조합표를 조회하면 SharePoint 위임 제약에
> 걸려 느려진다. 저장 시점에 한 번 읽어 넣으면 집계가 단순 `Sum` 으로 끝난다.

### 1-4. `월설정` — OT 기본 가능시간 (달마다 다름)

| 열 이름 | 타입 |
|---|---|
| 연월 | 텍스트 (제목 열) — `2026-09` |
| OT기본 | 숫자 |
| 비고 | 텍스트 |

### 1-5. `공휴일`

| 열 이름 | 타입 |
|---|---|
| 명칭 | 텍스트 (제목 열) |
| 날짜 | 날짜 (시간 없음) |

`sp_공휴일.csv` 를 가져온다. 설날·추석·부처님오신날은 음력이라 매년 확인해 추가한다.

## 2. 목록 만들기 절차

1. Teams 채널 → `+` → **Lists** → `목록 만들기` → `빈 목록`
2. 이름을 위 표대로 (`조합표` · `명부` · `근태기록` · `월설정` · `공휴일`)
3. **제목 열 이름 바꾸기**: 열 머리글 `제목` → `열 설정` → `이름 바꾸기`
4. `+ 열 추가` 로 나머지 열을 표대로 추가.
   선택 항목은 `sp_선택항목.txt` 에서 복사해 붙여넣으면 된다
5. 데이터 넣기 — 두 가지 방법
   - **그리드 뷰 붙여넣기** (권장): `그리드 뷰에서 편집` → CSV 를 엑셀로 열어 복사 → 붙여넣기
   - **CSV 가져오기**: SharePoint 사이트에서 `새로 만들기 → 목록 → Excel 에서`

> 106행 조합표는 그리드 뷰 붙여넣기가 가장 빠르고 확실하다.

## 3. 앱 만들기

Teams → `Power Apps` → `새 앱` → 두 팀이 함께 있는 팀 선택 → 캔버스 앱.
`데이터 추가` 에서 **SharePoint** 커넥터로 위 5개 목록을 연결한다.

> **앱 설정에서 반드시 바꿀 것**: `설정 → 일반 → 데이터 행 제한` 을 **2000** 으로.
> 기본 500 이면 월 기록이 500행을 넘는 순간 집계가 조용히 틀린다.

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

ClearCollect(colMembers, Filter(명부, 휴직 = false));
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
Set(gvOtBase,   Coalesce(LookUp(월설정, 연월 = gvYM, OT기본), 0));
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
Distinct(조합표, 유형)

// ddStart.Items — 고른 유형에서 가능한 출근만 (오전반이면 2개)
Distinct(Filter(조합표, 유형 = ddType.Selected.Value, 출근 <> ""), 출근)

// ddEnd.Items — 유형 + 출근에서 가능한 퇴근만 (오전반 13:00 이면 4개)
Distinct(
    Filter(조합표, 유형 = ddType.Selected.Value, 출근 = ddStart.Selected.Value),
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
    ds: 17 * 60 + 30,   // 석식 창 시작 = 정규 근로 종료 (선택근로 17:30)
    de: 18 * 60         // 석식 창 종료 = +30분
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

> 탄력근무 기간에는 `ds` · `de` 를 그 기간의 정규 근로 종료로 바꾼다
> (`08:00~17:00` 이면 `17*60` · `17*60+30`). 월설정 목록에 정규 종료 열을 두면 자동화된다.

### 4-6. 저장 — 조합표에서 값을 읽어 함께 저장

`btnSave.OnSelect`

```powerfx
Set(gvCode,
    If(IsBlank(ddStart.Selected.Value) || ddStart.Selected.Value = "",
       ddType.Selected.Value,
       ddType.Selected.Value & " "
         & Substitute(ddStart.Selected.Value, ":", "") & "-"
         & Substitute(ddEnd.Selected.Value,   ":", "")));

Set(gvCombo, LookUp(조합표, 조합코드 = gvCode));

If(IsBlank(gvCombo),
    Notify("규칙에 없는 조합입니다. 유형·출근·퇴근을 다시 고르세요.",
           NotificationType.Error),

    Set(gvKey, Text(dpDate.SelectedDate, "yyyy-mm-dd") & "_" & gvMe);
    Patch(근태기록,
        Coalesce(LookUp(근태기록, 키 = gvKey), Defaults(근태기록)),
        {
            키:       gvKey,
            근무일:   dpDate.SelectedDate,
            구성원:   gvMe,
            유형:     { Value: ddType.Selected.Value },
            출근:     { Value: ddStart.Selected.Value },
            퇴근:     { Value: ddEnd.Selected.Value },
            조합코드: gvCode,
            실근로:   gvCombo.실근로,
            휴가:     gvCombo.휴가,
            충족:     gvCombo.충족,
            구분:     gvCombo.구분,
            OT시작:   txtOtS.Text,
            OT종료:   txtOtE.Text,
            OT시간:   Value(lblOt.Text),
            석식:     { Value: ddDinner.Selected.Value },
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

```powerfx
// btnFlexLoad.OnSelect — 시작 월을 dpFlex 로 고른다
Set(gvFlexStart, Date(Year(dpFlex.SelectedDate), Month(dpFlex.SelectedDate), 1));
Set(gvFlexEnd,   DateAdd(DateAdd(gvFlexStart, 3, Months), -1, Days));
ClearCollect(colFlex, Filter(근태기록, 근무일 >= gvFlexStart, 근무일 <= gvFlexEnd));

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
