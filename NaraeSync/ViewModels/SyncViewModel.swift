import Foundation
import HealthKit
import SwiftUI

/// 화면 상태 + 동기화 로직 총괄.
@MainActor
final class SyncViewModel: ObservableObject {
    // UI 상태
    @Published var runs: [RunWorkout] = []
    @Published var isLoading = false
    @Published var isSyncing = false
    @Published var statusMessage: String?
    @Published var errorMessage: String?
    @Published var isLoggedIn = false
    @Published var athleteName: String?
    @Published var autoSyncEnabled = UserDefaults.standard.bool(forKey: "autoSyncEnabled") {
        didSet {
            UserDefaults.standard.set(autoSyncEnabled, forKey: "autoSyncEnabled")
            Task { await configureBackgroundSync() }
        }
    }

    // 각 워크아웃의 업로드 상태(화면 표시용)
    enum RowState: Equatable {
        case notUploaded
        case uploading
        case uploaded(activityID: Int)
        case failed(String)
    }
    @Published var rowStates: [UUID: RowState] = [:]

    private let health = HealthKitManager.shared
    private let auth = StravaAuth.shared
    private let uploadStore = UploadStore.shared
    private var observerQuery: HKObserverQuery?

    init() {
        isLoggedIn = auth.isLoggedIn
        athleteName = auth.athleteName
    }

    // MARK: - 최초 진입

    func onAppear() async {
        isLoggedIn = auth.isLoggedIn
        athleteName = auth.athleteName
        await requestHealthAccess()
        await refresh()
        await configureBackgroundSync()
    }

    private func requestHealthAccess() async {
        do {
            try await health.requestAuthorization()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    // MARK: - 목록 새로고침

    func refresh() async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }
        do {
            let fetched = try await health.fetchRuns(days: 60, garminOnly: true)
            runs = fetched
            // 저장된 업로드 이력 반영
            for run in fetched {
                if let activityID = uploadStore.activityID(for: run.id) {
                    rowStates[run.id] = .uploaded(activityID: activityID)
                } else if rowStates[run.id] == nil {
                    rowStates[run.id] = .notUploaded
                }
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    // MARK: - Strava 로그인

    func login() async {
        errorMessage = nil
        do {
            try await auth.startLogin()
            isLoggedIn = auth.isLoggedIn
            athleteName = auth.athleteName
            statusMessage = "Strava 로그인 완료"
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func logout() {
        auth.logout()
        isLoggedIn = false
        athleteName = nil
    }

    /// onOpenURL 콜백(스킴으로 들어오는 경우) 처리.
    func handleOAuthCallback(url: URL) {
        Task {
            do {
                try await auth.handleCallback(url: url)
                isLoggedIn = auth.isLoggedIn
                athleteName = auth.athleteName
            } catch {
                // startLogin의 세션 콜백에서 이미 처리되는 경우가 많으므로 조용히 무시 가능
            }
        }
    }

    // MARK: - 업로드

    /// 아직 업로드 안 한 모든 기록을 순서대로 업로드.
    func syncAll() async {
        guard ensureReady() else { return }
        isSyncing = true
        defer { isSyncing = false }

        let pending = runs.filter { !uploadStore.isUploaded($0.id) }
        if pending.isEmpty {
            statusMessage = "새로 올릴 기록이 없습니다."
            return
        }

        var success = 0
        for run in pending {
            let ok = await upload(run)
            if ok { success += 1 }
        }
        statusMessage = "\(success)/\(pending.count)개 업로드 완료"
    }

    /// 개별 기록 업로드.
    @discardableResult
    func upload(_ run: RunWorkout) async -> Bool {
        guard ensureReady() else { return false }
        rowStates[run.id] = .uploading

        let tcx = TCXBuilder.makeTCX(from: run)
        let name = activityName(for: run)
        do {
            let activityID = try await StravaClient.shared.upload(
                tcx: tcx,
                externalID: run.id.uuidString,
                name: name
            )
            uploadStore.markUploaded(run.id, activityID: activityID)
            rowStates[run.id] = .uploaded(activityID: activityID)
            return true
        } catch NaraeError.duplicateActivity {
            // 이미 스트라바에 있으면 성공으로 간주하고 이력에 기록(다음부터 스킵)
            uploadStore.markUploaded(run.id, activityID: -1)
            rowStates[run.id] = .uploaded(activityID: -1)
            return true
        } catch {
            rowStates[run.id] = .failed(error.localizedDescription)
            errorMessage = error.localizedDescription
            return false
        }
    }

    private func activityName(for run: RunWorkout) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "M월 d일 HH시 mm분"
        formatter.locale = Locale(identifier: "ko_KR")
        return "\(formatter.string(from: run.startDate)) 달리기"
    }

    private func ensureReady() -> Bool {
        guard StravaConfig.isConfigured else {
            errorMessage = NaraeError.notConfigured.localizedDescription
            return false
        }
        guard auth.isLoggedIn else {
            errorMessage = NaraeError.notAuthorized.localizedDescription
            return false
        }
        return true
    }

    // MARK: - 백그라운드 자동 동기화

    /// 자동 동기화가 켜져 있으면 새 가민 기록이 들어올 때 앱을 깨워 업로드.
    func configureBackgroundSync() async {
        // 기존 옵저버 제거
        if let existing = observerQuery {
            health.store.stop(existing)
            observerQuery = nil
        }
        let workoutType = HKObjectType.workoutType()

        guard autoSyncEnabled else {
            try? await health.store.disableBackgroundDelivery(for: workoutType)
            return
        }

        let query = HKObserverQuery(sampleType: workoutType, predicate: nil) { [weak self] _, completion, _ in
            guard let self = self else { completion(); return }
            Task { @MainActor in
                await self.refresh()
                await self.syncNewInBackground()
                completion()
            }
        }
        health.store.execute(query)
        observerQuery = query

        do {
            try await health.store.enableBackgroundDelivery(for: workoutType, frequency: .immediate)
        } catch {
            // 백그라운드 전달 실패는 치명적이지 않음(수동 동기화는 여전히 가능)
        }
    }

    /// 백그라운드에서 조용히 미업로드분만 처리.
    private func syncNewInBackground() async {
        guard auth.isLoggedIn, StravaConfig.isConfigured else { return }
        let pending = runs.filter { !uploadStore.isUploaded($0.id) }
        for run in pending {
            _ = await upload(run)
        }
    }
}
