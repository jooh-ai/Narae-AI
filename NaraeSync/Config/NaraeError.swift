import Foundation

/// 앱 전체에서 쓰는 오류 타입.
enum NaraeError: LocalizedError {
    case healthDataUnavailable
    case notConfigured
    case notAuthorized
    case oauthFailed(String)
    case tokenExchangeFailed(String)
    case uploadFailed(String)
    case uploadTimedOut
    case duplicateActivity
    case http(Int, String)

    var errorDescription: String? {
        switch self {
        case .healthDataUnavailable:
            return "이 기기에서 건강 데이터를 사용할 수 없습니다."
        case .notConfigured:
            return "Strava Client ID/Secret이 설정되지 않았습니다. StravaConfig.swift를 확인하세요."
        case .notAuthorized:
            return "Strava 로그인이 필요합니다."
        case .oauthFailed(let msg):
            return "Strava 인증 실패: \(msg)"
        case .tokenExchangeFailed(let msg):
            return "토큰 교환 실패: \(msg)"
        case .uploadFailed(let msg):
            return "업로드 실패: \(msg)"
        case .uploadTimedOut:
            return "업로드 처리 시간이 초과되었습니다. 잠시 후 다시 시도하세요."
        case .duplicateActivity:
            return "Strava에 이미 동일한 활동이 있습니다."
        case .http(let code, let msg):
            return "네트워크 오류(\(code)): \(msg)"
        }
    }
}
