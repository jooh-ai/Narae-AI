import Foundation

/// Strava 업로드 API 담당(TCX 파일 업로드 + 처리 상태 폴링).
final class StravaClient {
    static let shared = StravaClient()
    private let auth = StravaAuth.shared
    private init() {}

    /// TCX 문자열을 Strava에 업로드하고, 처리가 끝날 때까지 기다린 뒤 activity id를 반환.
    /// - Parameters:
    ///   - tcx: TCX XML 문자열
    ///   - externalID: 중복 감지를 위한 외부 식별자(워크아웃 uuid 권장)
    ///   - name: 활동 이름(선택)
    /// - Returns: 생성된 Strava activity id
    @discardableResult
    func upload(tcx: String, externalID: String, name: String?) async throws -> Int {
        let token = try await auth.validAccessToken()

        let boundary = "NaraeBoundary-\(externalID)"
        var request = URLRequest(url: URL(string: "\(StravaConfig.apiBase)/uploads")!)
        request.httpMethod = "POST"
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var fields: [String: String] = [
            "data_type": "tcx",
            "external_id": externalID,
        ]
        if let name = name { fields["name"] = name }

        request.httpBody = Self.multipartBody(
            boundary: boundary,
            fields: fields,
            fileField: "file",
            fileName: "\(externalID).tcx",
            fileData: Data(tcx.utf8),
            mimeType: "application/xml"
        )

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw NaraeError.uploadFailed("응답 없음")
        }

        // 409 등: 이미 업로드된 활동
        if http.statusCode == 409 {
            throw NaraeError.duplicateActivity
        }
        guard (200...299).contains(http.statusCode) else {
            let msg = String(data: data, encoding: .utf8) ?? ""
            // Strava는 중복일 때 400 + "duplicate" 메시지를 주기도 함
            if msg.lowercased().contains("duplicate") {
                throw NaraeError.duplicateActivity
            }
            throw NaraeError.http(http.statusCode, msg)
        }

        let initial = try JSONDecoder().decode(UploadStatus.self, from: data)
        return try await pollUntilDone(uploadID: initial.id, token: token)
    }

    /// 업로드 처리 상태를 폴링. Strava가 파일을 파싱하는 데 몇 초 걸릴 수 있음.
    private func pollUntilDone(uploadID: Int, token: String) async throws -> Int {
        for _ in 0..<30 { // 최대 약 60초 (2초 * 30)
            try await Task.sleep(nanoseconds: 2_000_000_000)

            var request = URLRequest(url: URL(string: "\(StravaConfig.apiBase)/uploads/\(uploadID)")!)
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
                continue
            }
            let status = try JSONDecoder().decode(UploadStatus.self, from: data)

            if let error = status.error, !error.isEmpty {
                if error.lowercased().contains("duplicate") {
                    throw NaraeError.duplicateActivity
                }
                throw NaraeError.uploadFailed(error)
            }
            if let activityID = status.activity_id {
                return activityID
            }
            // activity_id가 아직 없으면 계속 폴링
        }
        throw NaraeError.uploadTimedOut
    }

    // MARK: - Multipart 인코딩

    private static func multipartBody(
        boundary: String,
        fields: [String: String],
        fileField: String,
        fileName: String,
        fileData: Data,
        mimeType: String
    ) -> Data {
        var body = Data()
        func append(_ string: String) { body.append(Data(string.utf8)) }

        for (key, value) in fields {
            append("--\(boundary)\r\n")
            append("Content-Disposition: form-data; name=\"\(key)\"\r\n\r\n")
            append("\(value)\r\n")
        }

        append("--\(boundary)\r\n")
        append("Content-Disposition: form-data; name=\"\(fileField)\"; filename=\"\(fileName)\"\r\n")
        append("Content-Type: \(mimeType)\r\n\r\n")
        body.append(fileData)
        append("\r\n")
        append("--\(boundary)--\r\n")
        return body
    }
}

/// Strava 업로드 상태 응답.
private struct UploadStatus: Decodable {
    let id: Int
    let external_id: String?
    let error: String?
    let status: String?
    let activity_id: Int?
}
