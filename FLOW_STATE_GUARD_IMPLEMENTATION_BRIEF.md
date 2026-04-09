# FLOW_STATE_GUARD_IMPLEMENTATION_BRIEF.md

## Objective
Implement a **single source of truth** conversation state controller for Flow iOS called `FlowStateGuard`, and wire all runtime state transitions through it.

This is an **engine hardening task only**.

- ✅ Allowed: state/engine/wiring/diagnostics changes
- ❌ Not allowed: visual or SwiftUI layout/styling changes

---

## 1) Context
Current Flow behavior is fragile because state mutations are scattered across:
- UI actions
- coordinator logic
- websocket callbacks
- VAD/audio callbacks
- TTS callbacks

We need deterministic lifecycle handling for:
- state transitions
- mic ownership
- TTS ownership
- turn completion timing
- barge-in
- websocket/offline handling

---

## 2) Required module
Create:

`FlowInterpreter/Engine/FlowStateGuard.swift`

The guard must:
1. Own interpreter state.
2. Validate legal transitions.
3. Coordinate side-effects through injected callbacks (not UI).
4. Correctly handle TTS + `turn_complete` + barge-in.
5. Emit diagnostics for key events and violations.

---

## 3) State model
```swift
enum FlowState: String {
    case idle
    case connecting
    case ready
    case listening
    case finalizing
    case translating
    case speaking
    case offline
    case failed
}
```

Allowed transitions:
- `idle -> connecting, ready`
- `connecting -> ready, offline, failed`
- `ready -> listening, offline, failed, idle`
- `listening -> finalizing, offline, failed`
- `finalizing -> translating, listening, offline, failed`
- `translating -> speaking, listening, offline, failed`
- `speaking -> listening, ready, offline, failed`
- `offline -> connecting, idle`
- `failed -> idle`

Any other transition is illegal.

---

## 4) API contract
```swift
final class FlowStateGuard {
    private(set) var state: FlowState = .idle

    private var ttsActive = false
    private var pendingTurnComplete = false
    private var ttsDoneNotified = false

    struct DiagEntry: Identifiable {
        enum Kind { case info, warn, error, illegalTransition }
        let id = UUID()
        let time: Date
        let kind: Kind
        let message: String
    }

    var onDiagnostic: ((DiagEntry) -> Void)?
    var onStateChanged: ((FlowState) -> Void)?

    struct SideEffects {
        let startMic: () -> Void
        let stopMic: () -> Void
        let openWebSocket: () -> Void
        let closeWebSocket: () -> Void
        let stopTTS: () -> Void
        let notifyTTSDone: () -> Void
    }

    init(initialState: FlowState = .idle, effects: SideEffects, isHandsFreeMode: @escaping () -> Bool)

    func transition(to next: FlowState, reason: String)
}
```

Transition behavior:
- Validate with local transition table.
- Illegal transition handling:
  - DEBUG: `assertionFailure(...)`
  - RELEASE: log + recover to `.idle` + stop mic/TTS + close WS
- Run `applySideEffectsBeforeTransition`, set `state`, run `applySideEffectsAfterTransition`.
- Emit diagnostics and `onStateChanged`.

---

## 5) Event hooks
Provide these methods and map to transitions/invariants:

```swift
// Transport
func onWebSocketConnecting()
func onWebSocketOpened()
func onWebSocketClosed(code: Int, reason: String)
func onServerReady()
func onServerOfflineError(_ err: Error)

// Speech / VAD
func onSpeechStarted()
func onSpeechEnded()
func onFinalTranscriptReceived()

// Translation
func onTranslationStarted()
func onTranslationFinished()

// TTS
func onTTSStarted()
func onTTSPlaybackFinished()
func onTTSCancelledByBargeIn()

// Turn
func onTurnComplete()

// User
func onUserMicTapped()
func onUserHoldStart()
func onUserHoldEnd()
func onUserPressedOff()
```

---

## 6) Invariants

### 6.1 Mic/WebSocket lifecycle
- Mic active only in `.listening` (optionally `.finalizing` if architecture requires).
- Mic never active in `.speaking`, `.translating`, `.ready`, `.idle`, `.offline`, `.failed`.
- `onUserPressedOff()` must:
  - stop mic
  - stop TTS
  - close websocket
  - transition to `.idle`

### 6.2 TTS + turn_complete discipline
Internal flags:
- `ttsActive`
- `pendingTurnComplete`
- `ttsDoneNotified`

Rules:
1. `onTTSStarted()`:
   - `ttsActive = true`
   - `ttsDoneNotified = false`
   - `transition(to: .speaking, reason: "tts_start")`

2. `onTurnComplete()`:
   - if `ttsActive == true`: set `pendingTurnComplete = true`, no state change
   - else: complete turn immediately

3. `onTTSPlaybackFinished()`:
   - `ttsActive = false`
   - `notifyTTSDoneIfNeeded()`
   - if `pendingTurnComplete`: clear it + `completeTurnAfterTTS()`

4. `onTTSCancelledByBargeIn()`:
   - only valid in `.speaking`
   - set `ttsActive = false`
   - set `pendingTurnComplete = false`
   - `notifyTTSDoneIfNeeded()`
   - `transition(to: .listening, reason: "barge_in")`

Helper methods:
```swift
private func notifyTTSDoneIfNeeded() {
    guard !ttsDoneNotified else { return }
    ttsDoneNotified = true
    effects.notifyTTSDone()
}

private func completeTurnAfterTTS() {
    if isHandsFreeMode() {
        transition(to: .listening, reason: "turn_complete_after_tts")
    } else {
        transition(to: .ready, reason: "turn_complete_after_tts")
    }
}
```

---

## 7) Wiring requirements
In `FlowCoordinator`:
1. Instantiate `FlowStateGuard` with side-effect closures wired to existing services.
2. Route all callbacks/events through guard methods.
3. Replace direct state writes with guard-driven state.
4. Bridge guard state to `AppState.state` via `onStateChanged`.
5. Bridge diagnostics via `onDiagnostic` into existing log pane.

**Hard rule:** Any non-guard `AppState.state = ...` mutation is a review blocker.

---

## 8) Acceptance criteria
Implementation is complete only if all are true:
1. No direct state mutations outside guard/bridge.
2. Illegal transitions assert in debug.
3. Barge-in during speaking always:
   - stops TTS
   - sends `tts_playback_done` exactly once
   - transitions to `.listening`
4. `turn_complete` during active TTS is deferred until playback finish.
5. Mic is never active in `.speaking`.
6. OFF fully tears down and lands in `.idle`.
7. Hands-free and hold-to-talk both still function.

---

## 9) Required deterministic test matrix (minimum)
Run and document pass/fail for:
1. **Normal turn**: listening -> finalizing -> translating -> speaking -> listening
2. **Deferred turn_complete**: receive turn_complete before TTS drain; state must not jump early
3. **Barge-in**: speaking + user speech -> stop TTS -> single done notify -> listening
4. **Offline reconnect**: close socket unexpectedly -> offline -> connecting -> ready
5. **OFF cleanup**: from active session, OFF must stop mic/TTS/ws and set idle
6. **Hold-to-talk release**: press/hold starts capture, release finalizes cleanly

Include logs for transition reasons and violations (if any).
