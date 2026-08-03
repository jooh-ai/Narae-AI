import Foundation

/// Strava API 설정.
///
/// ⚠️ 사용 전 반드시 본인 값으로 바꾸세요.
/// 1. https://www.strava.com/settings/api 에서 앱을 만들면
///    Client ID와 Client Secret을 받습니다.
/// 2. 그 앱의 "Authorization Callback Domain"에는  `oauth-callback`  을 넣으세요.
///    (Strava는 redirect_uri의 host 부분만 검사합니다. 아래 redirectURI가
///     naraesync://oauth-callback 이므로 host = oauth-callback 입니다)
///
/// 개인용 앱이라 Client Secret을 코드에 넣습니다. 앱을 배포/공유하지 마세요.
enum StravaConfig {
    static let clientID = "YOUR_STRAVA_CLIENT_ID"
    static let clientSecret = "YOUR_STRAVA_CLIENT_SECRET"

    /// Info.plist의 CFBundleURLSchemes 값과 반드시 일치해야 합니다.
    static let redirectScheme = "naraesync"
    /// 콜백 URL. 예: naraesync://oauth-callback
    static let redirectURI = "naraesync://oauth-callback"

    /// 업로드 권한(activity:write) + 읽기 권한.
    static let scope = "activity:write,read"

    static let authorizeURL = "https://www.strava.com/oauth/authorize"
    static let tokenURL = "https://www.strava.com/oauth/token"
    static let apiBase = "https://www.strava.com/api/v3"

    /// 설정이 실제 값으로 채워졌는지 확인.
    static var isConfigured: Bool {
        clientID != "YOUR_STRAVA_CLIENT_ID"
            && !clientID.isEmpty
            && clientSecret != "YOUR_STRAVA_CLIENT_SECRET"
            && !clientSecret.isEmpty
    }
}
