# 나래싱크 (NaraeSync)

가민(Garmin)에서 기록한 달리기를 **아이폰 건강 앱**에서 읽어 **Strava에 자동 업로드**하는 개인용 iOS 앱입니다.
예전에 손으로 하던 "Health Sync 수동 연동"을 대체·자동화합니다.

## 어떻게 동작하나

1. 아이폰 건강 앱에서 **출처가 Garmin Connect인 달리기 기록만** 읽습니다. (Strava가 다시 써넣은 복사본은 무시 → 중복 방지)
2. 각 기록을 **TCX 파일**로 변환합니다. 시간·누적거리·심박수 트랙포인트가 들어가 Strava가 **정식 활동**으로 인식합니다.
3. Strava 업로드 API로 올립니다.
4. 올린 기록의 ID를 로컬에 저장해 **다시 올리지 않습니다.**
5. 자동 동기화를 켜면 새 가민 기록이 들어올 때 앱이 깨어나 조용히 업로드합니다.

> ⚠️ **지도(경로)는 표시되지 않습니다.** 가민이 건강 앱에 GPS 경로를 남기지 않기 때문입니다.
> 거리·시간·페이스·심박수만 올라가며, 이는 예전 Health Sync 방식과 동일하고 다른 앱의 "인정" 목적에는 충분합니다.

---

## 준비물

- **Mac + Xcode 15 이상**
- **아이폰** (HealthKit은 실기기에서만 정상 동작. 시뮬레이터는 데이터가 없음)
- **무료 Apple 개발자 계정**이면 개인 기기 설치 가능 (7일마다 재설치 필요, 유료면 1년)
- **Strava 계정**

---

## 1단계 — Strava API 앱 등록 (딱 한 번)

1. https://www.strava.com/settings/api 접속
2. 아래처럼 앱을 만듭니다.
   - **Application Name**: 아무거나 (예: NaraeSync)
   - **Category**: 아무거나
   - **Website**: 아무 URL (예: `https://example.com`)
   - **Authorization Callback Domain**: **`oauth-callback`** ← 반드시 이 값
     (Strava는 `redirect_uri`의 host 부분만 검사합니다. 이 앱의 redirect는
      `naraesync://oauth-callback` 이라 host가 `oauth-callback` 입니다)
3. 만들고 나면 나오는 **Client ID**와 **Client Secret**을 복사합니다.

## 2단계 — 설정값 입력

`NaraeSync/Config/StravaConfig.swift`를 열어 두 줄을 본인 값으로 바꿉니다.

```swift
static let clientID = "여기에_Client_ID"
static let clientSecret = "여기에_Client_Secret"
```

> 개인용이라 Secret을 코드에 넣습니다. **이 앱을 남에게 배포/공유하지 마세요.**

## 3단계 — Xcode 프로젝트 열기

이 저장소에는 `.xcodeproj`가 없고 **XcodeGen 설정(`project.yml`)** 만 있습니다. 둘 중 하나를 선택하세요.

### 방법 A — XcodeGen (권장, 깔끔)

```bash
brew install xcodegen   # 처음 한 번
cd Narae-AI
xcodegen generate       # project.yml 로 NaraeSync.xcodeproj 생성
open NaraeSync.xcodeproj
```

### 방법 B — 직접 Xcode 프로젝트 만들기 (XcodeGen 없이)

1. Xcode → **File ▸ New ▸ Project ▸ iOS App** (SwiftUI, Swift)
2. 생성된 기본 파일들을 지우고 `NaraeSync/` 폴더 안의 `.swift` 파일들을 전부 끌어다 넣습니다.
3. **Signing & Capabilities** 에서 **+ Capability ▸ HealthKit** 추가.
4. **Info.plist** 에 이 저장소의 `NaraeSync/Info.plist` 내용을 참고해 아래를 추가:
   - `Privacy - Health Share Usage Description`
   - `URL Types ▸ URL Schemes = naraesync`

## 4단계 — 서명 & 실행

1. Xcode 왼쪽에서 프로젝트 선택 → **Signing & Capabilities** → 본인 **Team** 선택.
2. **Bundle Identifier** 를 유일한 값으로 변경 (예: `com.본인이름.naraesync`).
3. 아이폰을 케이블로 연결하고 상단에서 기기 선택 → **Run(▶)**.
4. 아이폰에서 처음 실행 시 **설정 ▸ 일반 ▸ VPN 및 기기 관리** 에서 개발자 앱을 **신뢰**.

## 5단계 — 앱 사용

1. 앱 실행 → 건강 데이터 접근 팝업에서 **모두 허용**.
2. **Strava로 로그인** 탭 → 브라우저에서 승인.
3. 가민 달리기 목록이 뜨면 **지금 모두 업로드** 또는 각 행의 업로드 버튼.
4. **새 기록 자동 업로드** 토글을 켜두면 이후 자동 처리.

---

## 자주 묻는 것

**Q. 목록이 비어 있어요.**
- 건강 앱에 가민 기록이 실제로 있는지 먼저 확인하세요.
- 이 앱은 출처 이름에 "garmin"이 포함된 기록만 보여줍니다. 가민 앱 이름이 다르면 `HealthKitManager.fetchRuns(garminOnly:)` 필터를 조정하세요.

**Q. 자동 업로드가 항상 즉시 되진 않아요.**
- iOS 백그라운드 전달은 배터리/시스템 상황에 따라 지연될 수 있습니다. 앱을 한 번 열면 밀린 기록이 곧바로 처리됩니다.

**Q. 중복이 생기나요?**
- 업로드한 워크아웃 ID를 저장해 다시 올리지 않습니다. Strava가 중복(409/duplicate)이라고 하면 자동으로 "완료"로 표시합니다.
- 가민↔Strava **직접 연동은 꺼두세요.** 이 앱만 업로드 경로로 쓰면 중복이 없습니다.

---

## 폴더 구조

```
NaraeSync/
├─ App/            앱 진입점
├─ Config/         Strava 설정 · 에러 타입
├─ Health/         HealthKit 읽기 · 모델
├─ Export/         TCX 생성기
├─ Strava/         OAuth · 업로드 · Keychain
├─ Store/          업로드 이력(중복 방지)
├─ ViewModels/     동기화 로직
└─ Views/          SwiftUI 화면
```
