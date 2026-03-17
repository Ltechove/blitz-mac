import SwiftUI

// MARK: - Full-screen overlay (WelcomeWindow)

/// Full-screen update card that blocks the welcome window UI.
struct UpdateOverlay: View {
    @Bindable var autoUpdate: AutoUpdateManager

    var body: some View {
        ZStack {
            // Dim background — blocks interaction with content beneath
            Rectangle()
                .fill(.ultraThinMaterial)
                .ignoresSafeArea()

            card
                .frame(width: 380)
                .padding(32)
                .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16))
                .shadow(color: .black.opacity(0.2), radius: 24, y: 8)
        }
    }

    @ViewBuilder
    private var card: some View {
        switch autoUpdate.state {
        case .available(let version, let notes):
            VStack(spacing: 20) {
                Image(systemName: "arrow.down.circle.fill")
                    .font(.system(size: 44))
                    .foregroundStyle(.blue)

                VStack(spacing: 6) {
                    Text("Update Available")
                        .font(.title2.weight(.semibold))
                    Text("Version \(version)")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                if !notes.isEmpty {
                    Text(notes)
                        .font(.callout)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                        .lineLimit(6)
                }

                VStack(spacing: 8) {
                    Button("Update Now") {
                        Task { await autoUpdate.performUpdate() }
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.large)
                    .frame(maxWidth: .infinity)

                    Button("Later") {
                        autoUpdate.dismiss()
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(.secondary)
                }
            }

        case .downloading(let percent):
            VStack(spacing: 20) {
                Image(systemName: "arrow.down.circle")
                    .font(.system(size: 44))
                    .foregroundStyle(.blue)

                VStack(spacing: 6) {
                    Text("Downloading Update")
                        .font(.title2.weight(.semibold))
                    if percent >= 0 {
                        Text("\(percent)%")
                            .font(.subheadline.monospacedDigit())
                            .foregroundStyle(.secondary)
                    }
                }

                if percent >= 0 {
                    ProgressView(value: Double(percent), total: 100)
                        .progressViewStyle(.linear)
                        .frame(maxWidth: .infinity)
                } else {
                    ProgressView()
                        .progressViewStyle(.linear)
                        .frame(maxWidth: .infinity)
                }

                Text("Please wait...")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }

        case .installing:
            VStack(spacing: 20) {
                ProgressView()
                    .controlSize(.large)

                VStack(spacing: 6) {
                    Text("Installing Update")
                        .font(.title2.weight(.semibold))
                    Text("Blitz will restart automatically.")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                Text("Please wait...")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }

        case .failed(let message):
            VStack(spacing: 20) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .font(.system(size: 44))
                    .foregroundStyle(.orange)

                VStack(spacing: 6) {
                    Text("Update Failed")
                        .font(.title2.weight(.semibold))
                    Text(message)
                        .font(.callout)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                        .lineLimit(4)
                }

                HStack(spacing: 12) {
                    Button("Retry") {
                        Task { await autoUpdate.performUpdate() }
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.large)

                    Button("Dismiss") {
                        autoUpdate.dismiss()
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.large)
                }
            }

        default:
            EmptyView()
        }
    }
}

// MARK: - Compact banner (SettingsView)

/// Small inline update banner used in Settings.
struct UpdateBanner: View {
    @Bindable var autoUpdate: AutoUpdateManager

    var body: some View {
        switch autoUpdate.state {
        case .idle, .checking:
            EmptyView()

        case .available(let version, let notes):
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Image(systemName: "arrow.down.circle.fill")
                        .foregroundStyle(.blue)
                    Text("Update Available")
                        .font(.headline)
                    Spacer()
                    Text("v\(version)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                if !notes.isEmpty {
                    Text(notes)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(3)
                }

                HStack {
                    Button("Update Now") {
                        Task { await autoUpdate.performUpdate() }
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.small)

                    Button("Later") {
                        autoUpdate.dismiss()
                    }
                    .controlSize(.small)
                }
            }
            .padding(12)
            .background(Color.blue.opacity(0.1), in: RoundedRectangle(cornerRadius: 8))
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.blue.opacity(0.2), lineWidth: 1))

        case .downloading(let percent):
            VStack(spacing: 6) {
                HStack {
                    Text("Downloading update...")
                        .font(.caption)
                    Spacer()
                    if percent >= 0 {
                        Text("\(percent)%")
                            .font(.caption.monospacedDigit())
                            .foregroundStyle(.secondary)
                    }
                }
                if percent >= 0 {
                    ProgressView(value: Double(percent), total: 100)
                        .progressViewStyle(.linear)
                } else {
                    ProgressView()
                        .progressViewStyle(.linear)
                }
            }
            .padding(12)
            .background(Color.blue.opacity(0.1), in: RoundedRectangle(cornerRadius: 8))

        case .installing:
            HStack(spacing: 8) {
                ProgressView()
                    .controlSize(.small)
                Text("Installing update...")
                    .font(.caption)
            }
            .padding(12)
            .background(Color.blue.opacity(0.1), in: RoundedRectangle(cornerRadius: 8))

        case .failed(let message):
            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundStyle(.orange)
                    Text("Update failed")
                        .font(.caption.weight(.medium))
                }
                Text(message)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)

                Button("Retry") {
                    Task { await autoUpdate.performUpdate() }
                }
                .controlSize(.small)
            }
            .padding(12)
            .background(Color.orange.opacity(0.1), in: RoundedRectangle(cornerRadius: 8))
        }
    }
}
