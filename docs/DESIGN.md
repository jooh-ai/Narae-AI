# 위례 공급가능용량 입찰 산정 Tool — 설계서

> 마스터 리뷰(7개 엑셀/PPT 분석)에서 확정된 내용을 바탕으로 한 통합 자동화 툴 설계.
> 기준: Mode3_AOH1000 · ISO 15°C/1013mbar · CC 450.4 MW · 온도축 = CIT · 입찰 cap = Net 462.

## 1. 목표 (한 줄)

**날짜·시간 입력 → 실행 → RiMS 자동취득 → 엑셀4식 온도별 누적보정 → 엑셀3 형식 '온도 Profile' 자동생성 + 테스트결과 List-up.**

## 2. 기반 결정 (사용자 확정 2026-06-26)

| 항목 | 결정 | 함의 |
|---|---|---|
| RiMS 연동 | 기존 `fnTagStat` 애드인 경유 | Tool이 Excel COM으로 애드인 구동(이 부분만 Windows·Excel 의존) |
| 실행 플랫폼 | Windows 데스크톱 앱 | 버튼 클릭 GUI, RiMS·Excel 있는 사내 PC |
| 계산 엔진 | Python 재구현 | 물리식·보정·Profile은 코드, RiMS만 커넥터 분리 |
| 입찰 상한 | Net 462 MW | Gross 472 (= Net + CC Aux 10) |
| 대상 모드 | Mode3(M3) 전용 | 나머지 모드는 수식 자동산출 |

## 3. 아키텍처

```
wirye_capacity_tool/
├─ wirye_capacity/            # ── 순수 Python 코어 (OS·Excel 무관, 테스트 가능)
│  ├─ constants.py            #   물리/사이트 상수 (P_corr, 450.4, W밴드, cap, 구간)   ✅Phase1
│  ├─ data/
│  │   ├─ base_table.json     #   온도별 base 계수 61행(−20~40°C) = 엑셀2 곡선 동결값   ✅Phase1
│  │   └─ measurements_seed.json  # 실측 32건 시드(엑셀4 실측데이터)                    ✅Phase1
│  ├─ theory.py               #   이론엔진: base×(1.028/Deg)/P_corr (+W)                ✅Phase1
│  ├─ correction.py           #   보정값=실측−이론−W, 구간집계, 현실화 Net              ✅Phase1
│  ├─ profile.py              #   온도 Profile 생성 → 엑셀3 형식 .xlsx                  ▢Phase3
│  └─ curve.py                #   연속 보정곡선(국소가중/회귀) — 구간→1도별 전환        ▢Phase6
├─ rims/                      # ── RiMS 취득 (커넥터 추상화)
│  ├─ base.py                 #   RimsConnector 인터페이스 (acquire(window)→TagSet)     ▢Phase4
│  ├─ excel_addin.py          #   실제: Excel COM + fnTagStat (Windows, 사내 결선)      ▢Phase4
│  └─ mock.py                 #   개발/테스트용 mock (시드 기반)                        ▢Phase4
├─ store/
│  └─ repo.py                 #   테스트결과 저장·List-up (SQLite)                      ▢Phase2
├─ weather/
│  └─ loader.py               #   엑셀3-1 파싱 → 중위 대기압 −8mbar                     ▢Phase5
├─ ui/
│  └─ app.py                  #   Windows 데스크톱 GUI (PySide6)                        ▢Phase5
└─ tests/                     #   엑셀 셀값 대조 검증                                   ✅Phase1
```

## 4. 데이터 흐름 (실행 클릭 1회)

```
[입력] 테스트 날짜·시작시각, (선택)Deg, 엑셀3-1 업로드
   │
   ▼ rims.acquire(16~17), acquire(17~18)              # fnTagStat 1시간 평균
[실측] CIT·대기압·RH·GT/ST/CC·복수기압·EBH …
   │
   ▼ theory.theory_cc(CIT, 실측대기압, Deg)            # 이론기준값(IGV 미반영)
[이론] I
   │
   ▼ correction.correction_value(CC실측, I, W)         # 보정값 = 실측 − I − W
[보정] J  ──► store.repo.add(record)                   # List-up 누적
   │
   ▼ correction.aggregate_bins(전체 누적)              # 온도구간 평균(→향후 곡선)
[보정테이블] 온도별 적용 보정값
   │
   ▼ profile.build(Deg, 입찰대기압)                    # 이론(base+W) + 보정, MIN(Net462)
[출력] 엑셀3 형식 '온도 Profile' .xlsx  +  테스트 List-up 화면
```

## 5. 단계별 로드맵

| Phase | 내용 | 산출물 | 환경 |
|---|---|---|---|
| **1 ✅** | 핵심 계산 엔진 | constants·theory·correction + 검증 14건 | 여기(완료) |
| 2 | 테스트결과 저장·List-up | store/repo (SQLite), CRUD + 시드 적재 | 여기 |
| 3 | 온도 Profile 생성 | profile → 엑셀3 형식 .xlsx (openpyxl) | 여기 |
| 4 | RiMS 커넥터 | base/mock(여기) + excel_addin 명세(사내 결선) | 분리 |
| 5 | GUI + 날씨 업로드 | PySide6 앱, 엑셀3-1 로더 | 여기(빌드)/사내(실행) |
| 6 | 연속 보정곡선 | curve (구간→1도별), 패키징(.exe), 사내 실연결 검증 | 사내 |

> Phase 1~3·5(빌드)는 이 환경에서 구현·테스트, RiMS 실연결(Phase 4 excel_addin)·최종 검증은 사내 PC에서.

## 6. 핵심 수식 (코드 반영 완료)

```
P_corr(P)   = 1.208792e-6·(P−1013)² − 9.82435e-4·(P−1013) + 1
이론기준값  = base_cc(CIT) × (1.028/Deg) / P_corr(대기압)     # IGV 미반영, CIT 소수는 선형보간
이론(Profile)= 이론기준값 + W(IGV: ≤−2:0/−1:+2/0~24:+4/25↑:+6)
보정값      = CC실측(17~18,IGV) − 이론기준값 − W
현실화 Net  = min( (이론 + 보정값) − CC_Aux(10), 462 )
```
검증: 엑셀4 Profile `D6(−20°C)=444.567`, `D51(25°C)=418.293`, `D50(24°C)=419.257` 및 보정값현황
`0~10:+5.78(8건)·10~15:+6.28(6)·15~20:+6.12(3)·20~25:+2.62(1)·25~30:−2.39(4)·30~41:−0.32(9)` 전부 일치.

## 7. 미해결/정합 항목 (Phase 진행 중 확인)

1. **이론기준값 정합** — base-table 방식이 엑셀4 Profile은 정확히 재현하나, 수기 산출 32건의 I열과는
   평균 −0.19 / 최대 2.6 MW 차이(테스트별 설계복수기압 차이 추정). Phase 4에서 엑셀2의 복수기 설계곡선을
   추출해 정합할지, base-table 일관값을 표준으로 둘지 결정 필요.
2. **W 입력원** — 테스트별 W(IGV)는 실적값(운전/RiMS)을 직접 사용. Profile 생성 시에는 밴드함수 기본값.
3. **연속곡선 전환 기준** — 구간(bin)→1도별 전환 시점/방식(국소가중 vs 회귀). 데이터 누적 추이 보며 결정.
4. **엑셀3-1 포맷 고정** — 크롤러 산출 엑셀의 시트/셀 레이아웃을 로더가 의존하므로 포맷 합의 필요.
