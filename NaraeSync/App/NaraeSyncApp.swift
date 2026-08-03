import SwiftUI

@main
struct NaraeSyncApp: App {
    @StateObject private var viewModel = SyncViewModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(viewModel)
                // Strava OAuth 콜백(naraesync://...) 처리
                .onOpenURL { url in
                    viewModel.handleOAuthCallback(url: url)
                }
        }
    }
}
