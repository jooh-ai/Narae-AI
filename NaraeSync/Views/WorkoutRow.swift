import SwiftUI

struct WorkoutRow: View {
    let run: RunWorkout
    let state: SyncViewModel.RowState
    let onUpload: () -> Void

    private static let dateFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "M월 d일 (E) HH:mm"
        f.locale = Locale(identifier: "ko_KR")
        return f
    }()

    var body: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Text(Self.dateFormatter.string(from: run.startDate))
                    .font(.subheadline).fontWeight(.medium)
                Text(run.summary)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                if !run.heartRateSamples.isEmpty {
                    Label("\(run.heartRateSamples.count)개 심박 샘플", systemImage: "heart.fill")
                        .font(.caption2)
                        .foregroundStyle(.pink)
                }
            }
            Spacer()
            trailing
        }
        .padding(.vertical, 2)
    }

    @ViewBuilder
    private var trailing: some View {
        switch state {
        case .notUploaded:
            Button(action: onUpload) {
                Image(systemName: "arrow.up.circle")
                    .font(.title2)
                    .foregroundStyle(.blue)
            }
            .buttonStyle(.plain)
        case .uploading:
            ProgressView()
        case .uploaded:
            Image(systemName: "checkmark.circle.fill")
                .font(.title2)
                .foregroundStyle(.green)
        case .failed:
            Button(action: onUpload) {
                Image(systemName: "exclamationmark.arrow.circlepath")
                    .font(.title2)
                    .foregroundStyle(.red)
            }
            .buttonStyle(.plain)
        }
    }
}
