import SwiftUI

@main
struct FlowApp: App {
    @StateObject private var session = FlowSession()

    var body: some Scene {
        WindowGroup {
            RootView(session: session)
                .overlay(alignment: .top) {
                    if let errorText = session.errorText,
                       !errorText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                        Text(errorText)
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundColor(.white)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 6)
                            .background(Color.black.opacity(0.72))
                            .padding(.top, 48)
                    }
                }
        }
    }
}
