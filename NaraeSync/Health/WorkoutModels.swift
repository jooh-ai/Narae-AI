import Foundation

/// 심박수 한 개 샘플.
struct HeartRateSample: Equatable {
    let date: Date
    let bpm: Double
}

/// 업로드 대상 달리기 기록(HealthKit에서 읽어온 요약).
struct RunWorkout: Identifiable, Equatable {
    /// HKWorkout.uuid — 중복 업로드 방지 키로 사용.
    let id: UUID
    let startDate: Date
    let endDate: Date
    /// 총 이동 거리(미터). 없으면 nil.
    let distanceMeters: Double?
    /// 활동 시간(초).
    let duration: TimeInterval
    /// 소모 칼로리(kcal). 없으면 nil.
    let activeEnergyKcal: Double?
    /// 데이터 출처 앱 이름(예: "Garmin Connect").
    let sourceName: String
    /// 심박수 시계열(오름차순). 비어 있을 수 있음.
    var heartRateSamples: [HeartRateSample]

    static func == (lhs: RunWorkout, rhs: RunWorkout) -> Bool {
        lhs.id == rhs.id
    }

    var distanceKm: Double? {
        guard let d = distanceMeters else { return nil }
        return d / 1000.0
    }

    /// 목록 표시용 짧은 요약.
    var summary: String {
        var parts: [String] = []
        if let km = distanceKm {
            parts.append(String(format: "%.2f km", km))
        }
        let minutes = Int(duration) / 60
        let seconds = Int(duration) % 60
        parts.append(String(format: "%d:%02d", minutes, seconds))
        return parts.joined(separator: " · ")
    }
}
