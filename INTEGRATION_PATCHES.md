# Mode B Integration Patches

**Date:** 2026-02-13
**Type:** Minimal patch diffs for Mode B integration
**Format:** Old string → New string for each file

---

## File 1: AppState.swift

### Patch 1a: Add language lock property
```swift
// BEFORE:
    // Current active row for streaming
    var currentEntryID: UUID?

    init() {

// AFTER:
    // Current active row for streaming
    var currentEntryID: UUID?

    // Language lock (prevents changing language mid-session)
    @Published var sessionStartLanguages: (input: FlowLanguage, output: FlowLanguage)?

    init() {
```

### Patch 1b: Add language lock methods
```swift
// BEFORE:
    var languageDirectionLabel: String {
        "\(inputLanguage.shortLabel) → \(outputLanguage.shortLabel)"
    }

    func swapLanguages() {
        let currentInput = inputLanguage
        inputLanguage = outputLanguage
        outputLanguage = currentInput
    }

// AFTER:
    var languageDirectionLabel: String {
        "\(inputLanguage.shortLabel) → \(outputLanguage.shortLabel)"
    }

    var isLanguageLocked: Bool {
        sessionStartLanguages != nil
    }

    func startSession() {
        sessionStartLanguages = (input: inputLanguage, output: outputLanguage)
    }

    func endSession() {
        sessionStartLanguages = nil
    }

    func swapLanguages() {
        if isLanguageLocked {
            addDiag("Language locked during session", type: .info)
            return
        }
        let currentInput = inputLanguage
        inputLanguage = outputLanguage
        outputLanguage = currentInput
    }
```

---

## File 2: FlowCoordinator.swift

### Patch 2a: Add TurnSmoothingManager property
```swift
// BEFORE:
@MainActor
final class FlowCoordinator: ObservableObject {
    let appState: AppState
    let audioService: AudioService
    let wsService: WebSocketService

    private var lastBargeInAt: Date = .distantPast
    private var lastMeterUpdateAt: TimeInterval = 0
    private var pendingTranslationDelta = ""
    private var deltaFlushWork: DispatchWorkItem?

    init() {
        let state = AppState()
        self.appState = state
        self.audioService = AudioService()
        self.wsService = WebSocketService(appState: state)
        wireUp()
    }

// AFTER:
@MainActor
final class FlowCoordinator: ObservableObject {
    let appState: AppState
    let audioService: AudioService
    let wsService: WebSocketService
    let turnSmoothingManager: TurnSmoothingManager

    private var lastBargeInAt: Date = .distantPast
    private var lastMeterUpdateAt: TimeInterval = 0
    private var pendingTranslationDelta = ""
    private var deltaFlushWork: DispatchWorkItem?

    init() {
        let state = AppState()
        self.appState = state
        self.audioService = AudioService()
        self.wsService = WebSocketService(appState: state)
        self.turnSmoothingManager = TurnSmoothingManager()
        wireUp()
    }
```

### Patch 2b: Wire speech stopped to TurnSmoothingManager
```swift
// BEFORE:
        case .speechStopped:
            appState.transition(.finalizing)

// AFTER:
        case .speechStopped:
            appState.transition(.finalizing)
            turnSmoothingManager.onSpeechStopped(Date())
```

### Patch 2c: Update startMic() to lock languages and start turn tracking
```swift
// BEFORE:
    func startMic() {
        do {
            try audioService.startCapture()
            appState.transition(.listening)
        } catch {
            appState.addDiag("Mic error: \(error.localizedDescription)", type: .err)
            appState.addSystemRow("Microphone access denied. Grant permission and try again.")
            appState.sessionWanted = false
            appState.transition(.ready)
        }
    }

// AFTER:
    func startMic() {
        do {
            try audioService.startCapture()
            appState.transition(.listening)
            appState.startSession()  // Lock languages for this session
            turnSmoothingManager.onSpeechStarted(Date())  // Begin turn tracking
        } catch {
            appState.addDiag("Mic error: \(error.localizedDescription)", type: .err)
            appState.addSystemRow("Microphone access denied. Grant permission and try again.")
            appState.sessionWanted = false
            appState.transition(.ready)
        }
    }
```

### Patch 2d: Update stop() to unlock languages
```swift
// BEFORE:
    func stop() {
        appState.sessionWanted = false
        flushPendingDelta()
        audioService.cleanup()
        wsService.disconnect(clean: true)
        appState.transition(.idle)
        hapticMedium()
    }

// AFTER:
    func stop() {
        appState.sessionWanted = false
        flushPendingDelta()
        audioService.cleanup()
        wsService.disconnect(clean: true)
        appState.transition(.idle)
        appState.endSession()  // Unlock languages after session ends
        hapticMedium()
    }
```

### Patch 2e: Update teardown() to ensure session cleanup
```swift
// BEFORE:
    func teardown() {
        appState.sessionWanted = false
        flushPendingDelta()
        audioService.cleanup()
        wsService.disconnect(clean: true)
    }
}

// AFTER:
    func teardown() {
        appState.sessionWanted = false
        flushPendingDelta()
        audioService.cleanup()
        wsService.disconnect(clean: true)
        appState.endSession()  // Ensure session is unlocked
    }
}
```

---

## File 3: ContentView.swift

### Patch 3a: Replace StatePill with SoftStatusPill in header
```swift
// BEFORE:
            HStack(spacing: 8) {
                StatePill(state: appState.state)

                Button {
                    showSettings = true
                } label: {
                    Image(systemName: "gearshape")
                        .font(.system(size: 16))
                        .foregroundColor(Flow.text3)
                }
            }

// AFTER:
            HStack(spacing: 12) {
                SoftStatusPill(appState: appState)

                Button {
                    showSettings = true
                } label: {
                    Image(systemName: "gearshape")
                        .font(.system(size: 16))
                        .foregroundColor(Flow.text3)
                }
            }
```

### Patch 3b: Replace TranscriptView with SplitConversationPanel
```swift
// BEFORE:
                // Language bar
                languageBar

                // Transcript
                TranscriptView(entries: appState.transcript)

                // Diagnostics panel (collapsible)

// AFTER:
                // Language bar
                languageBar

                // Split Conversation Panel (replaces TranscriptView)
                SplitConversationPanel(appState: appState)

                // Diagnostics panel (collapsible)
```

### Patch 3c: Update language bar with lock indicator and disabled swap
```swift
// BEFORE:
    // MARK: - Language Bar
    private var languageBar: some View {
        HStack(spacing: 10) {
            Text(appState.languageDirectionLabel)
                .font(.system(size: 11, weight: .semibold))
                .tracking(0.5)
                .foregroundColor(Flow.text3)

            Spacer()

            Button {
                appState.swapLanguages()
            } label: {
                Image(systemName: "arrow.left.arrow.right")
                    .font(.system(size: 13, weight: .bold))
                    .foregroundColor(Flow.accent.opacity(0.8))
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(Flow.surface2)
                    .clipShape(Capsule())
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 6)
        .frame(maxWidth: .infinity)
        .overlay(alignment: .bottom) {
            Flow.border.frame(height: 1)
        }
    }

// AFTER:
    // MARK: - Language Bar
    private var languageBar: some View {
        HStack(spacing: 10) {
            Text(appState.languageDirectionLabel)
                .font(.system(size: 11, weight: .semibold))
                .tracking(0.5)
                .foregroundColor(Flow.text3)

            if appState.isLanguageLocked {
                Text("locked")
                    .font(.system(size: 9, weight: .semibold))
                    .tracking(0.3)
                    .foregroundColor(Flow.amber)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(Flow.amber.opacity(0.1))
                    .clipShape(Capsule())
            }

            Spacer()

            Button {
                appState.swapLanguages()
            } label: {
                Image(systemName: "arrow.left.arrow.right")
                    .font(.system(size: 13, weight: .bold))
                    .foregroundColor(appState.isLanguageLocked ? Flow.text3.opacity(0.5) : Flow.accent.opacity(0.8))
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(Flow.surface2)
                    .clipShape(Capsule())
            }
            .disabled(appState.isLanguageLocked)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 6)
        .frame(maxWidth: .infinity)
        .overlay(alignment: .bottom) {
            Flow.border.frame(height: 1)
        }
    }
```

---

## File 4: SplitConversationPanel.swift (NEW)

**Location:** `FlowInterpreter/Views/SplitConversationPanel.swift`
**Lines:** 180 (includes ConversationColumn + helper views)
**Status:** NEW FILE - see full file in repo

---

## File 5: OrbView_ModeB.swift (EXISTING)

**Location:** `FlowInterpreter/Views/Components/OrbView_ModeB.swift`
**Status:** Already created in Phase 4 (no changes needed for integration)

---

## File 6: TurnSmoothingManager.swift (EXISTING)

**Location:** `FlowInterpreter/Services/TurnSmoothingManager.swift`
**Status:** Already created in Phase 4 (no changes needed for integration)

---

## Summary of Changes

| File | Type | Changes | Lines |
|------|------|---------|-------|
| AppState.swift | MODIFY | Add language lock property + methods | +20 |
| FlowCoordinator.swift | MODIFY | Add TurnSmoothingManager, wire callbacks, add session management | +12 |
| ContentView.swift | MODIFY | Replace StatePill/TranscriptView, add language lock UI | +25 |
| SplitConversationPanel.swift | CREATE | Two-column conversation panel + helpers | 180 |
| OrbView_ModeB.swift | (existing) | No changes needed | — |
| TurnSmoothingManager.swift | (existing) | No changes needed | — |

**Total New Lines:** ~237
**Total Modified Lines:** ~57
**Total Changes:** Non-breaking, minimal modifications to existing code

---

## Integration Verification Checklist

- [x] AppState now supports language lock
- [x] FlowCoordinator instantiates TurnSmoothingManager
- [x] Speech events routed to TurnSmoothingManager
- [x] Session management (start/end) wired
- [x] ContentView displays SoftStatusPill in header
- [x] ContentView displays SplitConversationPanel instead of TranscriptView
- [x] Language bar shows lock badge and disables swap during session
- [x] OrbView_ModeB components ready (Phase 4 completion)

**Status:** Integration complete. Ready for OrbView_ModeB control dock integration and device testing.
