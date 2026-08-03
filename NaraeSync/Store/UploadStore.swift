import Foundation

/// 이미 업로드한 워크아웃을 기억해 중복 업로드를 막는다.
/// (워크아웃 uuid 문자열 → Strava activity id)
final class UploadStore {
    static let shared = UploadStore()
    private let key = "uploadedWorkouts"
    private let defaults = UserDefaults.standard

    private init() {}

    /// uuid -> activityID
    private var map: [String: Int] {
        get { defaults.dictionary(forKey: key) as? [String: Int] ?? [:] }
        set { defaults.set(newValue, forKey: key) }
    }

    func isUploaded(_ id: UUID) -> Bool {
        map[id.uuidString] != nil
    }

    func activityID(for id: UUID) -> Int? {
        map[id.uuidString]
    }

    func markUploaded(_ id: UUID, activityID: Int) {
        var m = map
        m[id.uuidString] = activityID
        map = m
    }

    func clear() {
        defaults.removeObject(forKey: key)
    }
}
