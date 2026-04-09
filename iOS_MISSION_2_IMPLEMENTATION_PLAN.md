# 📱 iOS Mission 2 Implementation Plan

**Date:** 2026-02-14
**Objective:** Bring Mission 2 features (Turn Boundary & Barge-In) from web to iOS
**Status:** Planning

---

## 🎯 Overview

The web version has completed **Mission 2: Turn Boundary & Barge-In Implementation** with:
- Smart hangover window (250ms) for natural pauses
- Conditional audio streaming (only during speech)
- Barge-in detection (interrupt TTS when user speaks)
- Pause tolerance settings (Normal: 700ms, Long: 1100ms)
- Speech boundary messages (speech_start, speech_end)

**iOS currently has:**
- Basic turn smoothing logic in `TurnSmoothingManager.swift`
- Simple barge-in detection in `FlowCoordinator` (threshold-based on audio level)
- No hangover window support
- No client-side VAD
- No pause tolerance settings

---

## 📋 Required Changes by File

### 1. **AppState.swift** (iOS State Management)

**Add Mission 2 Properties:**
```swift
// Mission 2: VAD hangover and pause tolerance
@AppStorage("pauseTolerance") var pauseToleranceRaw: String = "normal"
@AppStorage("hangoverMs") var hangoverMs: Double = 250

// Computed property for endSilenceMs
var endSilenceMs: Double {
    pauseTolerance == "long" ? 1100 : 700
}

// VAD hangover state
var isInHangover: Bool = false
var lastSpeechEndTime: Date?
var hangoverTimer: Timer?
var speechStartedInTurn: Bool = false

// TTS playback tracking (already present via audioService.isTTSPlaying)

var pauseTolerance: String {
    get { pauseToleranceRaw }
    set { pauseToleranceRaw = newValue }
}
```

**Methods to Add:**
- `resetVADState()` - Clear hangover state and timers (called on session end)
- `startHangoverTimer()` - Begin hangover window countdown

---

### 2. **WebSocketService.swift** (Message Protocol)

**Add Mission 2 Message Types:**

In `ServerMessage` enum:
```swift
case speechStart      // Client VAD: speech detected
case speechEnd        // Client VAD: silence after hangover
case bargeIn         // User interrupted TTS
```

In `parseMessage()`:
```swift
case "speech_start":
    return .speechStart
case "speech_end":
    return .speechEnd
case "barge_in":
    return .bargeIn
```

**Add Sending Methods:**
```swift
func sendSpeechStart() {
    send(["type": "speech_start"])
}

func sendSpeechEnd() {
    send(["type": "speech_end"])
}

func sendBargeIn() {
    send(["type": "barge_in"])
}
```

---

### 3. **AudioService.swift** (Audio Processing)

**Mission 2 Changes:**

```swift
// Add VAD-like state tracking (simple level-based)
private var lastPeakLevel: Float = 0
private var silenceDuration: TimeInterval = 0
private var lastPeakTime: Date?
private var isSpeakingNow: Bool = false

// Flag to track if we're within hangover
var inHangover: Bool = false
```

**In `processInputBuffer()`:**

Currently it just captures audio. Add conditional streaming logic:
```swift
// Mission 2: Only stream if speaking or in hangover
let shouldStream = isSpeakingNow || inHangover

// Update speech detection based on peak level
let threshold = Float(0.015)  // Simple threshold
if peak > threshold {
    isSpeakingNow = true
    lastPeakTime = Date()
} else {
    // Check if we've exceeded silence threshold
    if let lastTime = lastPeakTime,
       Date().timeIntervalSince(lastTime) > 0.25 {  // 250ms hangover
        isSpeakingNow = false
        inHangover = false
    } else if let lastTime = lastPeakTime,
              Date().timeIntervalSince(lastTime) > 0.05 {
        inHangover = true  // Within hangover, still stream
    }
}

if !shouldStream { return }  // Skip sending silent audio
```

---

### 4. **TurnSmoothingManager.swift** (Turn Boundary Logic)

**Major Update - Replace Thresholds:**

Current approach: Fixed silence thresholds (0.4s, 0.7s, 1.0s)
New approach: Dynamic based on `pauseTolerance` setting

**Changes:**
```swift
class TurnSmoothingManager: ObservableObject {
    let microPauseThreshold: TimeInterval = 0.25   // Pre-hangover
    let hangoverMs: TimeInterval = 0.25            // Mission 2 hangover

    // Dynamic finalization based on app setting
    func finalizePauseThreshold(pauseTolerance: String) -> TimeInterval {
        pauseTolerance == "long" ? 1.1 : 0.7
    }

    // New method: Called when speech_end message arrives from client VAD
    func onClientSpeechEnd(timestamp: Date) {
        // Server acknowledges client-side turn boundary
        speechEndTime = timestamp
        isWaitingForFinalize = true
        scheduleDebounce()
    }
}
```

---

### 5. **FlowCoordinator.swift** (Message Handling & Barge-In)

**Update `handleServerMessage()`:**

```swift
case .speechStart:
    // Client VAD: speech detected
    if appState.state != .listening {
        appState.transition(.listening)
    }
    appState.speechStartedInTurn = true
    appState.addDiag("Client VAD: speech_start", type: .ok)

case .speechEnd:
    // Client VAD: silence after hangover
    appState.addDiag("Client VAD: speech_end", type: .ok)
    turnSmoothingManager.onClientSpeechEnd(Date())

case .bargeIn:
    // Server confirms user interrupted TTS
    appState.addDiag("BARGE-IN confirmed by server", type: .ok)
```

**Improve Barge-In Detection:**

Current: Simple peak level threshold during .speaking state
New: More sensitive, incorporates hangover window

```swift
private func handlePossibleBargeIn(level: Float) {
    guard appState.state == .speaking else { return }

    // Mission 2: Use sensitivity + hangover window
    let threshold = Float(max(0.04, min(0.9, appState.vadSensitivity)))
    guard level >= threshold else { return }

    // Debounce: avoid multiple rapid barge-ins (0.3s)
    let now = Date()
    guard now.timeIntervalSince(lastBargeInAt) > 0.3 else { return }

    lastBargeInAt = now

    // Interrupt TTS immediately
    audioService.killPlayback()
    wsService.sendBargeIn()  // Send Mission 2 barge_in message

    // Resume listening
    audioService.startCapture()  // Restart mic capture
    appState.transition(.listening)
    appState.addDiag("User barged in", type: .ok)
    hapticMedium()
}
```

---

### 6. **SettingsView.swift** (UI for Pause Tolerance)

**Add to Settings:**

```swift
// Mission 2: Pause Tolerance Setting
Section("Turn Boundary") {
    Picker("Pause Tolerance", selection: $appState.pauseTolerance) {
        Text("Normal (700ms)")
            .tag("normal")
        Text("Long (1100ms)")
            .tag("long")
    }
    .pickerStyle(.segmented)

    Text("Controls how long the app waits before finalizing a turn")
        .font(.caption)
        .foregroundStyle(.secondary)
}
```

---

### 7. **TranscriptEntry.swift** (Optional: Per-Entry Metadata)

**Add if needed for turn tracking:**
```swift
struct TranscriptEntry: Identifiable {
    // ... existing fields ...

    // Mission 2: Optional turn metadata
    let turnID: UUID?        // Which turn this belongs to
    let isStreaming: Bool    // Is this currently streaming translation

    init(source: String? = nil,
         translation: String? = nil,
         system: String? = nil,
         turnID: UUID? = nil,
         isStreaming: Bool = false) {
        // ... existing init ...
        self.turnID = turnID
        self.isStreaming = isStreaming
    }
}
```

---

## 🔄 Implementation Order

### Phase 1: Message Protocol (Low Risk)
1. Add `speechStart`, `speechEnd`, `bargeIn` to `ServerMessage` enum
2. Add parsing in `parseMessage()`
3. Add sending methods: `sendSpeechStart()`, `sendSpeechEnd()`, `sendBargeIn()`
4. ✅ No UI changes, backward compatible

### Phase 2: State Management
1. Add `pauseTolerance` to `AppState`
2. Add `endSilenceMs` computed property
3. Add `resetVADState()` method
4. Add VAD hangover properties
5. ✅ No behavioral changes yet, just state

### Phase 3: Barge-In Enhancement
1. Improve `handlePossibleBargeIn()` in `FlowCoordinator`
2. Send `sendBargeIn()` instead of just killing playback
3. Add haptic feedback
4. ✅ Immediate TTS interruption works better

### Phase 4: Turn Smoothing Integration
1. Update `TurnSmoothingManager` with dynamic thresholds
2. Add `onClientSpeechEnd()` method
3. Handle new message types in `FlowCoordinator.handleServerMessage()`
4. ✅ Smooth turn boundaries working

### Phase 5: Audio Streaming (Conditional)
1. Add `isSpeakingNow` and `inHangover` tracking to `AudioService`
2. Add simple peak-level-based speech detection
3. Implement `shouldStream` logic to skip silent frames
4. ⚠️ More invasive change, test carefully

### Phase 6: UI Settings
1. Add "Turn Boundary" section to `SettingsView`
2. Add "Pause Tolerance" picker (Normal/Long)
3. Wire to `appState.pauseTolerance`
4. ✅ Non-critical, can be added last

---

## ⚡ Quick Implementation Checklist

- [ ] **AppState.swift**: Add `pauseTolerance`, `endSilenceMs`, VAD state properties
- [ ] **WebSocketService.swift**: Add speech_start/end/barge_in message types
- [ ] **WebSocketService.swift**: Add `sendSpeechStart()`, `sendSpeechEnd()`, `sendBargeIn()` methods
- [ ] **FlowCoordinator.swift**: Improve `handlePossibleBargeIn()` with new logic
- [ ] **FlowCoordinator.swift**: Add handlers for `.speechStart`, `.speechEnd`, `.bargeIn`
- [ ] **TurnSmoothingManager.swift**: Add dynamic pause threshold based on setting
- [ ] **TurnSmoothingManager.swift**: Add `onClientSpeechEnd()` method
- [ ] **AudioService.swift**: Add simple speech detection (optional Phase 5)
- [ ] **SettingsView.swift**: Add "Pause Tolerance" picker UI
- [ ] **Testing**: Verify hangover window, barge-in, and settings persistence

---

## 🧪 Testing Strategy

### Test 1: Speech Boundary Messages
1. Speak with normal pause (200ms) → Should NOT generate speech_end
2. Speak with long pause (800ms) → Should generate speech_end after 700ms/1100ms
3. Verify server logs show speech_start/end messages

### Test 2: Barge-In Functionality
1. Ask question → Wait for TTS to start
2. Speak again → TTS should stop immediately
3. Verify "BARGE-IN: User interrupted" in diagnostics

### Test 3: Pause Tolerance Setting
1. Open Settings → Find "Turn Boundary" section
2. Toggle between "Normal (700ms)" and "Long (1100ms)"
3. Test speaking with pauses → Behavior should change

### Test 4: End-to-End Conversation
1. Both Normal and Long pause tolerance settings
2. Multiple back-and-forth exchanges
3. Verify transcript accuracy and timing

---

## 📊 Complexity Assessment

| Component | Risk | Effort | Notes |
|-----------|------|--------|-------|
| Message types | 🟢 Low | 30m | Backward compatible addition |
| AppState changes | 🟢 Low | 30m | Just adding properties |
| Barge-in improvement | 🟠 Medium | 1h | Existing logic, enhance it |
| Turn smoothing update | 🟠 Medium | 1h | Moderate logic change |
| Audio streaming (optional) | 🔴 High | 2h | Touches real-time audio path |
| Settings UI | 🟢 Low | 30m | Straightforward UI addition |
| **Total** | | **4-5h** | Phase 5 (audio streaming) optional |

---

## 🚀 Success Criteria

✅ All new message types work (speech_start/end/barge_in)
✅ Barge-in immediately stops TTS playback
✅ Pause tolerance setting persists and affects turn boundaries
✅ Hangover window prevents premature turn finalization
✅ No regression in existing functionality
✅ Mode B UI remains intact and working
✅ App builds and runs on simulator/device without errors

---

## 📝 Notes

- iOS already has better turn smoothing than web (TurnSmoothingManager)
- Barge-in logic already exists, just needs improvement
- Audio streaming optimization (Phase 5) is optional - the web version streams all audio
- Settings persistence via `@AppStorage` is already set up
- Keep Mode B UI changes (SoftStatusPill, OrbView_ModeB) intact throughout

