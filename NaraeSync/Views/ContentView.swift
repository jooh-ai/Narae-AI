import SwiftUI

struct ContentView: View {
    @EnvironmentObject var vm: SyncViewModel

    var body: some View {
        NavigationStack {
            List {
                accountSection
                settingsSection
                runsSection
            }
            .navigationTitle("나래싱크")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { await vm.refresh() }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .disabled(vm.isLoading)
                }
            }
            .overlay(alignment: .bottom) {
                if let status = vm.statusMessage {
                    Text(status)
                        .font(.footnote)
                        .padding(10)
                        .background(.thinMaterial, in: Capsule())
                        .padding(.bottom, 8)
                        .transition(.opacity)
                }
            }
            .task { await vm.onAppear() }
            .refreshable { await vm.refresh() }
            .alert("오류", isPresented: Binding(
                get: { vm.errorMessage != nil },
                set: { if !$0 { vm.errorMessage = nil } }
            )) {
                Button("확인", role: .cancel) { vm.errorMessage = nil }
            } message: {
                Text(vm.errorMessage ?? "")
            }
        }
    }

    // MARK: - 섹션들

    private var accountSection: some View {
        Section("Strava 계정") {
            if vm.isLoggedIn {
                HStack {
                    Image(systemName: "checkmark.seal.fill").foregroundStyle(.orange)
                    VStack(alignment: .leading) {
                        Text(vm.athleteName ?? "로그인됨")
                        Text("연결됨").font(.caption).foregroundStyle(.secondary)
                    }
                    Spacer()
                    Button("로그아웃", role: .destructive) { vm.logout() }
                        .buttonStyle(.bordered)
                }
            } else {
                Button {
                    Task { await vm.login() }
                } label: {
                    Label("Strava로 로그인", systemImage: "link")
                }
            }
        }
    }

    private var settingsSection: some View {
        Section("동기화") {
            Toggle("새 기록 자동 업로드", isOn: $vm.autoSyncEnabled)
            Button {
                Task { await vm.syncAll() }
            } label: {
                if vm.isSyncing {
                    HStack { ProgressView(); Text("업로드 중…") }
                } else {
                    Label("지금 모두 업로드", systemImage: "arrow.up.circle.fill")
                }
            }
            .disabled(vm.isSyncing || !vm.isLoggedIn)
        }
    }

    private var runsSection: some View {
        Section("가민 달리기 기록 (최근 60일)") {
            if vm.isLoading && vm.runs.isEmpty {
                HStack { ProgressView(); Text("불러오는 중…") }
            } else if vm.runs.isEmpty {
                Text("가민에서 온 달리기 기록이 없습니다.\n건강 앱 권한과 가민 커넥트 동기화를 확인하세요.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            } else {
                ForEach(vm.runs) { run in
                    WorkoutRow(run: run, state: vm.rowStates[run.id] ?? .notUploaded) {
                        Task { await vm.upload(run) }
                    }
                }
            }
        }
    }
}
