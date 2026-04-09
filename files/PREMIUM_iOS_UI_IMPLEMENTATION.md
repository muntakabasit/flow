# FLOW iOS Premium UI Implementation Guide

**Status:** Foundation Components Complete
**Date:** 2026-02-13
**Architecture:** SwiftUI MVVM with state-driven animations

---

## 🎯 Completed Components

### ✅ 1. OrbView.swift
**Location:** `FlowInterpreter/Views/Components/OrbView.swift`

**Features:**
- 140x140pt animated breathing orb
- State-driven amplitude: idle (2-4px), listening (4-8px), translating (6-10px), speaking (8-12px)
- Harmonic resonance for processing states (multi-frequency oscillation)
- Color-coded by state: green (ready/listening), amber (connecting/translating), gold (speaking), red (offline)
- Soft glow radius scales with state intensity
- Inner glass highlight for premium feel
- Respects `accessibilityReduceMotion`
- Spring animation on state transitions (0.4s, damping 0.75)
- Icon changes based on state (mic, hourglass, speaker)

**Animation Engine:**
- TimelineView refresh at 0.016s (60fps)
- Sine-wave based amplitude computation
- Harmonic layering for complex states
- Smooth interpolation between amplitude values

---

### ✅ 2. GlassCard.swift
**Location:** `FlowInterpreter/Views/Components/GlassCard.swift`

**Features:**
- `.ultraThinMaterial` background with subtle blur
- 3 elevation levels: soft (4pt shadow), medium (8pt), prominent (12pt)
- Optional glow color for state feedback
- 1px border with white opacity gradient (glass effect)
- 16pt corner radius (continuous curve)
- Flexible content view builder
- Multiple convenient initializers

**Use Cases:**
- Transcript panes (medium elevation, optional glow)
- Status indicators (soft elevation)
- Language selector (medium elevation)

---

### ✅ 3. SoftStatusPill.swift
**Location:** `FlowInterpreter/Views/Components/SoftStatusPill.swift`

**Features:**
- Staggered pulsing dots (3 dots, offset animation)
- Color-coded status: green (ready), amber (processing), red (offline)
- Uppercase label with letter tracking
- Glass card material with subtle shadow
- Smooth dot animation (1.2s cycle)
- Positioned for header integration

**States:**
- Ready → Green + "Ready"
- Connecting → Amber + "Connecting"
- Listening → Green + "Listening"
- Translating → Amber + "Thinking"
- Speaking → Green + "Speaking"
- Offline → Red + "Offline"

---

## 🔨 Remaining Components (Specifications)

### 4. SplitConversationPanel.swift (NEXT)
**Location:** `FlowInterpreter/Views/SplitConversationPanel.swift`

**Specification:**
```swift
struct SplitConversationPanel: View {
    @ObservedObject var appState: AppState

    var body: some View {
        ScrollViewReader { proxy in
            VStack(spacing: 0) {
                HStack(spacing: 1) {
                    // YOU (Source) column
                    ConversationColumn(
                        title: "YOU",
                        emoji: "🇺🇸",
                        language: "EN",
                        entries: sourceEntries,
                        backgroundColor: Flow.surface3
                    )

                    // Divider
                    Divider()
                        .background(Flow.border)

                    // THEM (Translation) column
                    ConversationColumn(
                        title: "THEM",
                        emoji: "🇧🇷",
                        language: "PT-BR",
                        entries: translationEntries,
                        backgroundColor: Flow.surface2,
                        isStreaming: appState.state == .translating,
                        streamingCursorColor: Flow.accent
                    )
                }
                .frame(maxHeight: .infinity)
            }
        }
    }
}
```

**Key Points:**
- Two-column layout with 1pt divider
- Left (YOU): source transcript, muted colors
- Right (THEM): translation, emphasized, with cursor animation
- Full-height scrollable
- Turn separation with optional badges
- Fade-in animation on new entries (0.3s stagger)

---

### 5. TurnManager.swift (NEXT)
**Location:** `FlowInterpreter/Services/TurnManager.swift`

**Specification:**
```swift
@MainActor
class TurnManager: ObservableObject {
    @Published var turns: [ConversationTurn] = []
    @Published var currentTurnID: UUID?

    // Debounce logic:
    // < 400ms silence: ignore, continue
    // 400-700ms: prepare (hold state)
    // > 700ms: finalize
    // < 300ms resume: merge with current

    func onSpeechStopped(_ timestamp: Date)
    func onSpeechResumed(_ timestamp: Date)
    func evaluateSilenceDuration()
    func finalizeTurn()
    func startNewTurn()
    func mergeWithCurrentTurn()
}
```

**Turn Model:**
```swift
struct ConversationTurn: Identifiable {
    let id: UUID
    let sourceEntry: TranscriptEntry
    let translationEntry: TranscriptEntry
    let startTime: Date
    let endTime: Date?
}
```

---

### 6. FlowCoordinator.swift (MODIFICATION)
**Location:** `FlowInterpreter/Services/FlowCoordinator.swift`

**Changes (minimal):**
```swift
@MainActor
final class FlowCoordinator: ObservableObject {
    @Published var appState = AppState()
    private let turnManager = TurnManager()  // NEW

    // Wire turn boundaries
    private func handleSpeechStopped() {
        turnManager.onSpeechStopped(Date())  // NEW
        // ... existing logic
    }

    private func handleSpeechResumed() {
        turnManager.onSpeechResumed(Date())  // NEW
        // ... existing logic
    }
}
```

**Non-breaking:** Existing message handlers unchanged; TurnManager is orthogonal overlay.

---

### 7. AppState.swift (MODIFICATION)
**Location:** `FlowInterpreter/Models/AppState.swift`

**Changes (add language lock):**
```swift
@Published var sessionStartLanguages: (input: FlowLanguage, output: FlowLanguage)? = nil

var isLanguageLocked: Bool { sessionStartLanguages != nil }

func startSession() {
    sessionStartLanguages = (input: inputLanguage, output: outputLanguage)
}

func endSession() {
    sessionStartLanguages = nil
}

func attemptLanguageSwap() {
    if !isLanguageLocked {
        swapLanguages()
    } else {
        addDiag("Language locked during session", type: .info)
    }
}
```

---

### 8. ContentView.swift (MODIFICATION)
**Location:** `FlowInterpreter/Views/ContentView.swift`

**Changes (layout redesign):**
```swift
VStack(spacing: 0) {
    // Header + SoftStatusPill
    HStack {
        // Brand on left
        // SoftStatusPill on right (NEW)
    }
    .padding(.horizontal, 16)
    .padding(.vertical, 12)

    // Conversation panel (replaces TranscriptView)
    SplitConversationPanel(appState: appState)

    // Control dock (redesigned)
    VStack(spacing: 16) {
        // Large OrbView (primary control, 140x140)
        OrbView(appState: appState) {
            coordinator.handleMicTap()
        }
        .frame(height: 160)

        // Optional: waveform below orb (secondary)
        WaveformView(audioLevel: $appState.audioLevel)
            .frame(height: 20)
    }
    .padding(.vertical, 24)
}
```

---

## 📋 Implementation Checklist

### Phase 1: Components ✅
- [x] OrbView.swift - Breathing animation core
- [x] GlassCard.swift - Reusable glass component
- [x] SoftStatusPill.swift - Connection indicator
- [ ] SplitConversationPanel.swift - Two-column layout
- [ ] ConversationColumn.swift - Individual column logic
- [ ] ConversationTurn.swift - Data model

### Phase 2: Services
- [ ] TurnManager.swift - Debounce + turn boundaries
- [ ] SoundCueManager.swift - Soft audio cues (optional)
- [ ] FlowAnimation.swift - Preset animations (optional)

### Phase 3: Integration
- [ ] FlowCoordinator.swift - TurnManager wiring
- [ ] AppState.swift - Language lock
- [ ] ContentView.swift - Layout redesign

### Phase 4: Polish
- [ ] Haptic feedback
- [ ] Accessibility refinement
- [ ] Animation timing tweaks
- [ ] Testing on devices (iPhone 14+ for glass effects)

---

## 🎨 Design Specifications

### Animation Timings

| Component | Duration | Easing | Notes |
|-----------|----------|--------|-------|
| Orb breathing | 1.8s | Sine wave | Primary amplitude cycle |
| State transition | 0.4s | Spring (0.75 damp) | Orb → new state |
| Pane entry | 0.3s | EaseOut | Fade + slide up |
| Cursor blink | 0.4s | RepeatForever | Translation streaming |
| Dot pulse | 1.2s | Linear | Status pill stagger |

### Color Palette (Glass Semantic)

| Usage | Color | Hex | Opacity |
|-------|-------|-----|---------|
| Listening state | Green | #34d399 | 100% |
| Processing state | Amber | #fbbf24 | 100% |
| Speaking state | Gold/Accent | #e0a846 | 100% |
| Error/Offline | Red | #f87171 | 100% |
| Glow overlay | State color | — | 10-50% |
| Glass border | White | #ffffff | 8% |

---

## 📱 Responsive Design

- **iPhone SE/13mini:** Scaled orb (120x120), tight spacing
- **iPhone 14/15 (Standard):** Full orb (140x140), optimal spacing
- **iPhone 14/15 Pro (Max):** Full orb + generous padding
- **iPad:** Landscape split panes side-by-side (if needed)

---

## 🔗 Integration Points

### With WebSocketService
- Existing messages unchanged
- TurnManager subscribes to state transitions
- Passes turn boundaries to UI layer

### With AudioService
- Volume level → OrbView opacity modulation (future enhancement)
- Speech callbacks → TurnManager

### With Settings
- Language lock toggle (Settings → User disabled mid-session lock)
- Sound cue volume toggle
- Motion reduction respected throughout

---

## 🚀 Deployment Strategy

1. **Week 1:** Implement components + TurnManager
2. **Week 2:** Integrate ContentView + FlowCoordinator
3. **Week 3:** Polish animations + test on devices
4. **Week 4:** Optional: Waveform + sound cues

---

## 📊 Performance Targets

- ✅ 60 FPS smooth animations (Spring + TimelineView)
- ✅ <1% CPU at rest (breathing only when visible)
- ✅ <50MB memory (glass effects are GPU-resident)
- ✅ Fast state transitions (0.4s max latency)

---

## 🎓 Key Architectural Insights

1. **State-Driven Animation:** All visual changes derive from `AppState.state`
2. **Orthogonal Concerns:** TurnManager doesn't modify AppState; separate overlay
3. **Glass Material:** iOS 18+ `.ultraThinMaterial` handles blur + vibrancy
4. **Sine-Wave Amplitude:** Smooth, natural-feeling breathing vs. step-based
5. **Spring Animations:** Damping 0.7-0.8 feels premium without overshoot

---

## ✨ Expected Outcome

When complete, FLOW will feel like:
- A professional conversation bridge (not a tech demo)
- Calm, responsive, trustworthy
- Modern glass-based interface (Apple-grade polish)
- Natural, breathing animations (not mechanical)
- Clear turn-taking with smooth transitions

---

## 📝 Next Steps

1. **SplitConversationPanel.swift** - Implement two-column layout
2. **TurnManager.swift** - Debounce + turn boundaries
3. **ContentView.swift** - Wire OrbView + SplitPanel
4. **Test on device** - Verify glass effects + animations

---

**Foundation is solid. Ready to build conversational UX on top.** 🚀
