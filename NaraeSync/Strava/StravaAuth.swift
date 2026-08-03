import Foundation
import AuthenticationServices
import UIKit

/// Strava 토큰 묶음.
struct StravaTokens: Codable {
    var accessToken: String
    var refreshToken: String
    /// access token 만료 시각(Unix epoch 초).
    var expiresAt: TimeInterval
    var athleteName: String?

    var isExpired: Bool {
        // 만료 60초 전이면 갱신 대상으로 본다.
        Date().timeIntervalSince1970 >= (expiresAt - 60)
    }
}

/// Strava OAuth(로그인/토큰 교환/갱신) 담당.
final class StravaAuth: NSObject {
    static let shared = StravaAuth()

    private let tokenKey = "strava.tokens"
    private var webSession: ASWebAuthenticationSession?

    private(set) var tokens: StravaTokens? {
        didSet { persist() }
    }

    private override init() {
        super.init()
        load()
    }

    var isLoggedIn: Bool { tokens != nil }
    var athleteName: String? { tokens?.athleteName }

    // MARK: - 저장/복원

    private func persist() {
        guard let tokens = tokens, let data = try? JSONEncoder().encode(tokens) else {
            Keychain.delete(tokenKey)
            return
        }
        Keychain.set(String(decoding: data, as: UTF8.self), for: tokenKey)
    }

    private func load() {
        guard let raw = Keychain.get(tokenKey),
              let data = raw.data(using: .utf8),
              let decoded = try? JSONDecoder().decode(StravaTokens.self, from: data) else {
            return
        }
        tokens = decoded
    }

    func logout() {
        tokens = nil
    }

    // MARK: - 로그인(Authorization Code Flow)

    /// 브라우저를 띄워 사용자가 Strava에 로그인/승인하게 하고, 콜백 URL을 반환.
    @MainActor
    func startLogin() async throws {
        guard StravaConfig.isConfigured else { throw NaraeError.notConfigured }

        var components = URLComponents(string: StravaConfig.authorizeURL)!
        components.queryItems = [
            URLQueryItem(name: "client_id", value: StravaConfig.clientID),
            URLQueryItem(name: "redirect_uri", value: StravaConfig.redirectURI),
            URLQueryItem(name: "response_type", value: "code"),
            URLQueryItem(name: "approval_prompt", value: "auto"),
            URLQueryItem(name: "scope", value: StravaConfig.scope),
        ]
        guard let authURL = components.url else { throw NaraeError.oauthFailed("URL 생성 실패") }

        let callbackURL: URL = try await withCheckedThrowingContinuation { continuation in
            let session = ASWebAuthenticationSession(
                url: authURL,
                callbackURLScheme: StravaConfig.redirectScheme
            ) { url, error in
                if let error = error {
                    continuation.resume(throwing: NaraeError.oauthFailed(error.localizedDescription))
                    return
                }
                guard let url = url else {
                    continuation.resume(throwing: NaraeError.oauthFailed("콜백 URL 없음"))
                    return
                }
                continuation.resume(returning: url)
            }
            session.presentationContextProvider = self
            session.prefersEphemeralWebBrowserSession = false
            self.webSession = session
            session.start()
        }

        try await exchangeCode(from: callbackURL)
    }

    /// onOpenURL로도 콜백이 들어올 수 있어(스킴 처리) 여기서도 처리 가능.
    func handleCallback(url: URL) async throws {
        try await exchangeCode(from: url)
    }

    private func extractCode(from url: URL) -> String? {
        URLComponents(url: url, resolvingAgainstBaseURL: false)?
            .queryItems?
            .first(where: { $0.name == "code" })?
            .value
    }

    /// authorization code를 access/refresh 토큰으로 교환.
    private func exchangeCode(from callbackURL: URL) async throws {
        guard let code = extractCode(from: callbackURL) else {
            throw NaraeError.oauthFailed("인증 코드가 없습니다(사용자가 취소했을 수 있음)")
        }

        var request = URLRequest(url: URL(string: StravaConfig.tokenURL)!)
        request.httpMethod = "POST"
        let body = [
            "client_id": StravaConfig.clientID,
            "client_secret": StravaConfig.clientSecret,
            "code": code,
            "grant_type": "authorization_code",
        ]
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        request.httpBody = Self.formEncode(body)

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            let msg = String(data: data, encoding: .utf8) ?? ""
            throw NaraeError.tokenExchangeFailed(msg)
        }

        let decoded = try JSONDecoder().decode(TokenResponse.self, from: data)
        tokens = StravaTokens(
            accessToken: decoded.access_token,
            refreshToken: decoded.refresh_token,
            expiresAt: decoded.expires_at,
            athleteName: decoded.athlete?.displayName
        )
    }

    // MARK: - 유효한 access token 확보(필요시 갱신)

    func validAccessToken() async throws -> String {
        guard var current = tokens else { throw NaraeError.notAuthorized }
        if !current.isExpired { return current.accessToken }

        var request = URLRequest(url: URL(string: StravaConfig.tokenURL)!)
        request.httpMethod = "POST"
        let body = [
            "client_id": StravaConfig.clientID,
            "client_secret": StravaConfig.clientSecret,
            "grant_type": "refresh_token",
            "refresh_token": current.refreshToken,
        ]
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        request.httpBody = Self.formEncode(body)

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            let msg = String(data: data, encoding: .utf8) ?? ""
            throw NaraeError.tokenExchangeFailed(msg)
        }

        let decoded = try JSONDecoder().decode(TokenResponse.self, from: data)
        current.accessToken = decoded.access_token
        current.refreshToken = decoded.refresh_token
        current.expiresAt = decoded.expires_at
        tokens = current
        return current.accessToken
    }

    // MARK: - Helpers

    private static func formEncode(_ dict: [String: String]) -> Data {
        var comps = URLComponents()
        comps.queryItems = dict.map { URLQueryItem(name: $0.key, value: $0.value) }
        return Data((comps.percentEncodedQuery ?? "").utf8)
    }
}

// MARK: - 토큰 응답 디코딩

private struct TokenResponse: Decodable {
    let access_token: String
    let refresh_token: String
    let expires_at: TimeInterval
    let athlete: Athlete?

    struct Athlete: Decodable {
        let firstname: String?
        let lastname: String?
        var displayName: String? {
            [firstname, lastname].compactMap { $0 }.joined(separator: " ")
        }
    }
}

// MARK: - 브라우저 표시 컨텍스트

extension StravaAuth: ASWebAuthenticationPresentationContextProviding {
    func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        // 현재 활성 window를 앵커로 사용.
        let scenes = UIApplication.shared.connectedScenes
        let windowScene = scenes.first { $0.activationState == .foregroundActive } as? UIWindowScene
        return windowScene?.keyWindow ?? ASPresentationAnchor()
    }
}
