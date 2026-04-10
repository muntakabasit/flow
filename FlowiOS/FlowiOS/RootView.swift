import SwiftUI

struct RootView: View {
    @StateObject private var session = FlowSession()

    // URL editor — triggered by long-pressing the status bar.
    // Lets you update the Cloudflare tunnel URL without rebuilding the app.
    @State private var showURLEditor = false
    @State private var editedURL     = ""

    private var activeSourceLang: String? {
        session.pendingSourceLang ?? session.turns.first?.sourceLang
    }

    var body: some View {
        GeometryReader { geo in
            VStack(spacing: 0) {

                // ── READING ZONE ───────────────────────────────────────────
                VStack(spacing: 0) {
                    TrustBarView(
                        state: session.state,
                        connStatus: session.connStatus,
                        onLongPress: {
                            editedURL = session.serverURL
                            showURLEditor = true
                        }
                    )
                    .padding(.top, geo.safeAreaInsets.top)

                    HeaderView()

                    TranslationPanelView(
                        turns: session.turns,
                        state: session.state
                    )
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(Color(hex: 0xFFFEF9))

                // ── ZONE SEPARATOR — 1pt solid gold ───────────────────────
                Rectangle()
                    .fill(Color(hex: 0xD4AF37))
                    .frame(height: 1)

                // ── ACTION ZONE ───────────────────────────────────────────
                VStack(spacing: 0) {
                    OrbView(
                        state: session.state,
                        pendingSourceLang: activeSourceLang,
                        liveTranscript: session.liveTranscript,
                        skipFlash: session.skipFlash,
                        onPressDown: { session.pressDown() },
                        onRelease:   { session.pressUp() }
                    )
                    .padding(.top, 28)
                    .padding(.bottom, 20)

                    // Last completed turn — copy / share. Hidden during active capture.
                    if let lastTurn = session.turns.first, session.state == .ready {
                        LastTurnActionsView(turn: lastTurn)
                            .transition(.opacity.combined(with: .move(edge: .bottom)))
                    }

                    Rectangle()
                        .fill(Color(hex: 0xD4AF37).opacity(0.45))
                        .frame(width: 32, height: 1)
                        .padding(.top, session.turns.isEmpty ? 0 : 12)
                        .padding(.bottom, geo.safeAreaInsets.bottom + 20)
                }
                .frame(maxWidth: .infinity)
                .background(Color(hex: 0x0D0D0D))
                .animation(.easeInOut(duration: 0.22), value: session.state == .ready && !session.turns.isEmpty)
            }
            .ignoresSafeArea()
            // ── URL editor alert (long-press the status bar) ──────────────
            // Lets you paste a new Cloudflare tunnel URL at runtime —
            // no Xcode rebuild needed when the quick tunnel URL rotates.
            .alert("Server URL", isPresented: $showURLEditor) {
                TextField("wss://…trycloudflare.com/ws", text: $editedURL)
                    .autocapitalization(.none)
                    .disableAutocorrection(true)
                Button("Connect") {
                    let trimmed = editedURL.trimmingCharacters(in: .whitespacesAndNewlines)
                    guard !trimmed.isEmpty else { return }
                    session.setServerURL(trimmed)
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("Long-press to update when the Cloudflare tunnel URL rotates.\nStarts with wss://")
            }
        }
    }
}
