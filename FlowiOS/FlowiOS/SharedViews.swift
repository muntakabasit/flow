import SwiftUI

// NOTE: AppState is defined in FlowSession.swift (spec §3):
//   case ready | listening | processing

// MARK: - TrustBarView

struct TrustBarView: View {
    let state: AppState
    let connStatus: ConnStatus        // SC-01: drives connection dot colour
    var onLongPress: (() -> Void)? = nil   // optional: opens URL editor
    @State private var pulse = false

    var body: some View {
        HStack(spacing: 8) {
            // Connection dot — green=online, amber=reconnecting, red=offline
            Circle()
                .fill(dotColor)
                .frame(width: 7, height: 7)
                .scaleEffect(isActive ? (pulse ? 1.3 : 0.7) : 1.0)
                .opacity(isActive ? (pulse ? 1.0 : 0.45) : 0.9)
                .animation(
                    isActive
                        ? .easeInOut(duration: 1.3).repeatForever(autoreverses: true)
                        : .default,
                    value: pulse
                )
                .animation(.easeInOut(duration: 0.3), value: connStatus)

            Text(label)
                .font(.system(size: 10, weight: .semibold))
                .tracking(1.2)
                .foregroundColor(.white.opacity(0.85))
                .textCase(.uppercase)

            Spacer()

            // Connection label — replaces static "EN · PT-BR" when not online
            Group {
                if connStatus == .online {
                    Text("EN  ·  PT-BR")
                        .foregroundColor(.white.opacity(0.35))
                } else {
                    Text(connStatus == .reconnecting ? "RECONNECTING…" : "OFFLINE")
                        .foregroundColor(connStatus == .reconnecting
                                         ? Color(hex: 0xF59E0B).opacity(0.85)
                                         : Color(hex: 0xEF4444).opacity(0.85))
                }
            }
            .font(.system(size: 10, weight: .medium))
            .tracking(0.8)
            .animation(.easeInOut(duration: 0.2), value: connStatus)
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 10)
        .background(Color.black)
        .onAppear { pulse = true }
        // Long-press anywhere on the status bar → URL editor
        .onLongPressGesture(minimumDuration: 0.6) {
            onLongPress?()
        }
    }

    private var isActive: Bool { state != .ready }

    private var label: String {
        switch state {
        case .ready:      return "Ready"
        case .listening:  return "Listening"
        case .processing: return "Translating"
        case .speaking:   return "Speaking"
        }
    }

    private var dotColor: Color {
        switch connStatus {
        case .online:       return Color(hex: 0x10B981)   // green
        case .reconnecting: return Color(hex: 0xF59E0B)   // amber
        case .offline:      return Color(hex: 0xEF4444)   // red
        }
    }
}

// MARK: - HeaderView

struct HeaderView: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("FLOW")
                .font(.system(size: 44, weight: .heavy))
                .tracking(12)
                .foregroundColor(Color(hex: 0x1A1A1A))
                .padding(.bottom, 4)

            Text("Diaspora Interpreter")
                .font(.system(size: 11, weight: .medium))
                .tracking(1.2)
                .foregroundColor(Color(hex: 0xD4AF37))
                .padding(.bottom, 14)

            HStack(spacing: 0) {
                Text("CONVERSATION")
                    .font(.system(size: 9, weight: .semibold))
                    .tracking(2.4)
                    .foregroundColor(Color(hex: 0x1A1A1A).opacity(0.22))
                Spacer()
            }
            .padding(.bottom, 8)

            Rectangle()
                .fill(Color(hex: 0xD4AF37))
                .frame(height: 1)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 22)
        .padding(.top, 18)
    }
}

// MARK: - TurnRowView

struct TurnRowView: View {
    let turn: FlowSession.Turn
    let isLatest: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(turn.sourceLang)
                .font(.system(size: 10, weight: .semibold))
                .tracking(1.0)
                .textCase(.uppercase)
                .foregroundColor(Color(hex: 0x999999))

            Text(turn.sourceText)
                .font(.system(size: 17, weight: .semibold))
                .foregroundColor(Color(hex: 0x1A1A1A))
                .lineSpacing(2)
                .fixedSize(horizontal: false, vertical: true)

            Rectangle()
                .fill(Color(hex: 0xD4AF37))
                .frame(width: 36, height: 1.5)
                .padding(.vertical, 3)

            Text(turn.targetLang)
                .font(.system(size: 10, weight: .semibold))
                .tracking(1.0)
                .textCase(.uppercase)
                .foregroundColor(Color(hex: 0x999999))

            Text(turn.targetText)
                .font(.system(size: 16, weight: .regular))
                .foregroundColor(Color(hex: 0x333333))
                .lineSpacing(2)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(Color.white)
                .shadow(
                    color: Color.black.opacity(isLatest ? 0.07 : 0.025),
                    radius: isLatest ? 8 : 3,
                    x: 0,
                    y: isLatest ? 3 : 1
                )
        )
    }
}

// MARK: - TranslationPanelView

struct TranslationPanelView: View {
    let turns: [FlowSession.Turn]
    let state: AppState

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 10) {
                    if turns.isEmpty {
                        emptyState.padding(.top, 44)
                    } else {
                        ForEach(turns.prefix(6)) { turn in
                            TurnRowView(turn: turn, isLatest: turn.id == turns.first?.id)
                                .id(turn.id)
                        }
                    }
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 14)
            }
            .onChange(of: turns.first?.id) { newID in
                if let id = newID {
                    withAnimation(.easeOut(duration: 0.3)) {
                        proxy.scrollTo(id, anchor: .top)
                    }
                }
            }
        }
    }

    private var emptyState: some View {
        VStack(spacing: 12) {
            skeletonCard(wide: true)
            skeletonCard(wide: false)
            Text("Your conversation appears here")
                .font(.system(size: 11, weight: .regular))
                .tracking(0.2)
                .foregroundColor(Color(hex: 0xC0C0C0))
                .padding(.top, 6)
        }
        .frame(maxWidth: .infinity)
        .padding(.horizontal, 16)
    }

    private func skeletonCard(wide: Bool) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            RoundedRectangle(cornerRadius: 2).fill(Color(hex: 0xE8E2D9)).frame(width: 28, height: 7)
            RoundedRectangle(cornerRadius: 2).fill(Color(hex: 0xE8E2D9)).frame(height: 10)
            RoundedRectangle(cornerRadius: 2).fill(Color(hex: 0xE8E2D9))
                .frame(width: wide ? nil : 160, height: 10)
            Rectangle().fill(Color(hex: 0xD4AF37).opacity(0.25)).frame(width: 28, height: 1.5).padding(.top, 2)
            RoundedRectangle(cornerRadius: 2).fill(Color(hex: 0xEDEAE4)).frame(height: 9)
            RoundedRectangle(cornerRadius: 2).fill(Color(hex: 0xEDEAE4))
                .frame(width: wide ? 180 : nil, height: 9)
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(Color.white.opacity(0.7))
                .overlay(RoundedRectangle(cornerRadius: 10).stroke(Color(hex: 0xE4DDD4), lineWidth: 1))
        )
    }
}

// MARK: - FlowWaveformView
//
// Single source of truth for all state-driven orb animation.
// Four scale behaviours, each driven by a cancellable async loop via .task(id: state).
//
//   .ready      → slow breath  (±2.5%,  2.8s)   "waiting, alive"
//   .listening  → held scale   (1.08, instant)   "you are live"
//   .processing → compressed   (0.95,  1.2s)     "system working"
//   .speaking   → rhythmic     (±6%,   0.7s)     "output, not input"
//
// Press-down scale (0.94) is applied by OrbView on top of waveScale — they compose.

struct FlowWaveformView: View {
    let state: AppState

    @State private var waveScale: CGFloat = 1.0
    @State private var spinAngle: Double  = 0

    var body: some View {
        ZStack {
            // Outer glow — ready only
            Circle()
                .fill(Color(hex: 0xD4AF37).opacity(state == .ready ? 0.06 : 0))
                .frame(width: 134, height: 134)
                .animation(.easeInOut(duration: 0.4), value: state)

            // Ring — width and colour shift per state
            Circle()
                .stroke(ringColor, lineWidth: ringWidth)
                .frame(width: 118, height: 118)
                .animation(.easeInOut(duration: 0.25), value: state)

            // Spinning dashes — processing only
            Circle()
                .stroke(style: StrokeStyle(lineWidth: 1.5, dash: [5, 8]))
                .foregroundColor(Color(hex: 0xD4AF37).opacity(0.55))
                .frame(width: 118, height: 118)
                .rotationEffect(.degrees(spinAngle))
                .opacity(state == .processing ? 1 : 0)
                .animation(.easeInOut(duration: 0.3), value: state)

            // Fill
            Circle()
                .fill(Color(hex: 0x111111))
                .frame(width: 104, height: 104)

            // Inner highlight ring
            Circle()
                .stroke(Color.white.opacity(0.04), lineWidth: 1)
                .frame(width: 102, height: 102)

            // Icon
            Image(systemName: icon)
                .foregroundColor(iconColor)
                .font(.system(size: 30, weight: .medium))
                .animation(.easeInOut(duration: 0.2), value: state)
        }
        .scaleEffect(waveScale)
        .task(id: state) { await driveScale(for: state) }
        .onAppear {
            withAnimation(.linear(duration: 3.5).repeatForever(autoreverses: false)) {
                spinAngle = 360
            }
        }
    }

    // ── Animation driver ─────────────────────────────────────────────────────
    // .task(id: state) cancels the previous task automatically on every state change,
    // so each case can loop freely without manual cancellation bookkeeping.

    @MainActor
    private func driveScale(for s: AppState) async {
        switch s {

        case .ready:
            withAnimation(.easeOut(duration: 0.2)) { waveScale = 1.0 }
            while !Task.isCancelled {
                withAnimation(.easeInOut(duration: 2.8)) { waveScale = 1.025 }
                try? await Task.sleep(for: .seconds(2.8))
                guard !Task.isCancelled else { return }
                withAnimation(.easeInOut(duration: 2.8)) { waveScale = 1.0 }
                try? await Task.sleep(for: .seconds(2.8))
            }

        case .listening:
            // Instant scale-up. Held static — no loop needed.
            withAnimation(.easeOut(duration: 0.12)) { waveScale = 1.08 }

        case .processing:
            withAnimation(.easeOut(duration: 0.15)) { waveScale = 0.95 }
            while !Task.isCancelled {
                withAnimation(.easeInOut(duration: 1.2)) { waveScale = 0.97 }
                try? await Task.sleep(for: .seconds(1.2))
                guard !Task.isCancelled else { return }
                withAnimation(.easeInOut(duration: 1.2)) { waveScale = 0.95 }
                try? await Task.sleep(for: .seconds(1.2))
            }

        case .speaking:
            withAnimation(.easeOut(duration: 0.15)) { waveScale = 1.0 }
            while !Task.isCancelled {
                withAnimation(.easeInOut(duration: 0.7)) { waveScale = 1.06 }
                try? await Task.sleep(for: .seconds(0.7))
                guard !Task.isCancelled else { return }
                withAnimation(.easeInOut(duration: 0.7)) { waveScale = 1.0 }
                try? await Task.sleep(for: .seconds(0.7))
            }
        }
    }

    // ── Appearance ────────────────────────────────────────────────────────────

    private var icon: String {
        switch state {
        case .ready, .listening: return "mic.fill"
        case .processing:        return "waveform"
        case .speaking:          return "speaker.wave.2.fill"
        }
    }

    private var iconColor: Color {
        switch state {
        case .ready:      return .white.opacity(0.75)
        case .listening:  return .white
        case .processing: return Color(hex: 0xD4AF37)
        case .speaking:   return Color(hex: 0xD4AF37)
        }
    }

    private var ringColor: Color {
        switch state {
        case .ready:      return Color(hex: 0xD4AF37).opacity(0.72)
        case .listening:  return Color(hex: 0xD4AF37)
        case .processing: return Color(hex: 0xD4AF37).opacity(0.65)
        case .speaking:   return Color(hex: 0xD4AF37).opacity(0.65)
        }
    }

    private var ringWidth: CGFloat {
        switch state {
        case .ready:      return 2.0
        case .listening:  return 3.5
        case .processing: return 2.5
        case .speaking:   return 2.5
        }
    }
}

// MARK: - OrbView
//
// Touch handler only. All visual/animation logic lives in FlowWaveformView.
// Press-down scale (0.94) is layered here, on top of FlowWaveformView's waveScale.

struct OrbView: View {
    let state: AppState
    let pendingSourceLang: String?
    let liveTranscript: String
    let skipFlash: String              // SC-03: "Nothing heard" on VAD idle release
    let onPressDown: () -> Void
    let onRelease:   () -> Void

    @State private var pressed = false

    var body: some View {
        VStack(spacing: 16) {

            // Direction label — only visible during processing
            Text(directionLabel)
                .font(.system(size: 10, weight: .semibold))
                .tracking(1.6)
                .textCase(.uppercase)
                .foregroundColor(Color(hex: 0xD4AF37))
                .frame(height: 14)
                .opacity(state == .processing ? 1 : 0)
                .animation(.easeInOut(duration: 0.18), value: state)

            FlowWaveformView(state: state)
                .scaleEffect(pressed ? 0.94 : 1.0)
                .animation(.spring(response: 0.28, dampingFraction: 0.65), value: pressed)
                .defersSystemGestures(on: .bottom)
                .highPriorityGesture(
                    DragGesture(minimumDistance: 0)
                        .onChanged { _ in
                            if !pressed { pressed = true; onPressDown() }
                        }
                        .onEnded { _ in
                            pressed = false; onRelease()
                        }
                )

            // Label below orb — priority: liveTranscript > skipFlash > state label
            Group {
                if (state == .processing || state == .speaking) && !liveTranscript.isEmpty {
                    Text(liveTranscript)
                        .font(.body)
                        .foregroundColor(.white.opacity(0.85))
                        .multilineTextAlignment(.center)
                } else if state == .ready && !skipFlash.isEmpty {
                    Text(skipFlash)
                        .font(.system(size: 11, weight: .semibold))
                        .tracking(1.6)
                        .textCase(.uppercase)
                        .foregroundColor(.white.opacity(0.30))   // dimmer — it's informational, not a prompt
                        .frame(height: 14)
                } else {
                    Text(orbLabel)
                        .font(.system(size: 11, weight: .semibold))
                        .tracking(1.6)
                        .textCase(.uppercase)
                        .foregroundColor(.white.opacity(0.45))
                        .frame(height: 14)
                }
            }
            .animation(.easeInOut(duration: 0.2), value: liveTranscript)
            .animation(.easeInOut(duration: 0.2), value: skipFlash)
            .animation(.easeInOut(duration: 0.15), value: state)
        }
    }

    private var directionLabel: String {
        if let lang = pendingSourceLang {
            return lang.hasPrefix("pt") ? "TRANSLATING → ENGLISH" : "TRANSLATING → PORTUGUÊS"
        }
        return "INTERPRETING…"
    }

    private var orbLabel: String {
        switch state {
        case .ready:      return "READY"       // SC-04: no instruction, just state
        case .listening:  return "LISTENING…"
        case .processing: return "HEARD YOU"
        case .speaking:   return "SPEAKING…"
        }
    }
}

// MARK: - LastTurnActionsView
//
// Shows the most recently completed turn with Copy and Share actions.
// Voice-first: appears only after a turn completes; never during capture or processing.
// Single turn only — no history, no editing.

struct LastTurnActionsView: View {
    let turn: FlowSession.Turn

    @State private var copied = false

    private var formatted: String {
        "\(turn.sourceLang): \(turn.sourceText)\n\(turn.targetLang): \(turn.targetText)"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {

            // Source line
            Text("\(turn.sourceLang): \(turn.sourceText)")
                .font(.system(size: 12, weight: .medium))
                .foregroundColor(.white.opacity(0.70))
                .lineLimit(2)
                .frame(maxWidth: .infinity, alignment: .leading)

            // Translated line
            Text("\(turn.targetLang): \(turn.targetText)")
                .font(.system(size: 12, weight: .regular))
                .foregroundColor(.white.opacity(0.42))
                .lineLimit(2)
                .frame(maxWidth: .infinity, alignment: .leading)

            // Actions
            HStack(spacing: 16) {
                Button {
                    UIPasteboard.general.string = formatted
                    copied = true
                    DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { copied = false }
                } label: {
                    Label(copied ? "Copied" : "Copy", systemImage: copied ? "checkmark" : "doc.on.doc")
                        .font(.system(size: 11, weight: .medium))
                        .tracking(0.4)
                        .foregroundColor(copied ? .white.opacity(0.55) : Color(hex: 0xD4AF37))
                }
                .animation(.easeInOut(duration: 0.15), value: copied)

                ShareLink(item: formatted) {
                    Label("Share", systemImage: "square.and.arrow.up")
                        .font(.system(size: 11, weight: .medium))
                        .tracking(0.4)
                        .foregroundColor(Color(hex: 0xD4AF37))
                }
            }
            .padding(.top, 2)
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            Rectangle()
                .fill(Color(hex: 0x161616))
        )
        .overlay(
            Rectangle()
                .fill(Color(hex: 0xD4AF37).opacity(0.18))
                .frame(height: 1),
            alignment: .top
        )
    }
}

// MARK: - Color hex extension

extension Color {
    init(hex: UInt32) {
        let r = Double((hex >> 16) & 0xFF) / 255.0
        let g = Double((hex >> 8)  & 0xFF) / 255.0
        let b = Double(hex         & 0xFF) / 255.0
        self.init(red: r, green: g, blue: b)
    }
}
