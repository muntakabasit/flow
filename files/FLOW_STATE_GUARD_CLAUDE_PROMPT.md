# FLOW_STATE_GUARD_CLAUDE_PROMPT.md

Implement `FlowStateGuard` for the Flow iOS app as an engine-only refactor.

## Scope
- Project: `FlowInterpreter` (SwiftUI app)
- Create `FlowInterpreter/Engine/FlowStateGuard.swift`
- Wire into existing `FlowCoordinator` + websocket/audio/TTS services
- Do not change UI layout/styling

## Mission
Centralize conversation state and enforce legal transitions + runtime invariants.

## Required state enum
Use:
- idle
- connecting
- ready
- listening
- finalizing
- translating
- speaking
- offline
- failed

## Allowed transitions
- idle -> connecting, ready
- connecting -> ready, offline, failed
- ready -> listening, offline, failed, idle
- listening -> finalizing, offline, failed
- finalizing -> translating, listening, offline, failed
- translating -> speaking, listening, offline, failed
- speaking -> listening, ready, offline, failed
- offline -> connecting, idle
- failed -> idle

Any other transition is illegal.

## Guard API (minimum)
- `transition(to:reason:)`
- transport hooks: `onWebSocketConnecting/opened/closed`, `onServerReady`, `onServerOfflineError`
- speech hooks: `onSpeechStarted`, `onSpeechEnded`, `onFinalTranscriptReceived`
- translation hooks: `onTranslationStarted`, `onTranslationFinished`
- TTS hooks: `onTTSStarted`, `onTTSPlaybackFinished`, `onTTSCancelledByBargeIn`
- turn hook: `onTurnComplete`
- user hooks: `onUserMicTapped`, `onUserHoldStart`, `onUserHoldEnd`, `onUserPressedOff`

## Core flags
Inside guard:
- `ttsActive`
- `pendingTurnComplete`
- `ttsDoneNotified`

## Mandatory behavior
1. `onTTSStarted`: set `ttsActive=true`, `ttsDoneNotified=false`, transition to speaking.
2. `onTurnComplete`:
   - if `ttsActive`, set `pendingTurnComplete=true` and do not transition.
   - else complete turn immediately.
3. `onTTSPlaybackFinished`:
   - set `ttsActive=false`
   - notify `tts_playback_done` once
   - if pending, complete turn now.
4. `onTTSCancelledByBargeIn` (only valid while speaking):
   - stop TTS lifecycle
   - notify done once
   - transition to listening.
5. OFF must fully cleanup mic + TTS + websocket, then idle.

## Side-effects injection
Use callbacks (not UI access):
- startMic / stopMic
- openWebSocket / closeWebSocket
- stopTTS
- notifyTTSDone

## Diagnostics and failure policy
- Emit diagnostic entries for transitions + violations.
- Debug: `assertionFailure` on illegal transition.
- Release: auto-recover to idle and cleanup resources.

## Wiring constraints
- Replace direct `AppState.state` writes with guard-driven transitions.
- Bridge guard state back to app state via one path (`onStateChanged`).
- Any direct state write outside guard/bridge is not allowed.

## Validation required before completion
Run and report:
1. normal turn lifecycle
2. deferred turn_complete during TTS
3. barge-in
4. offline reconnect cycle
5. OFF cleanup
6. hold-to-talk release flow

Return:
- files changed
- key code snippets
- test results against the six checks
- any known edge cases
