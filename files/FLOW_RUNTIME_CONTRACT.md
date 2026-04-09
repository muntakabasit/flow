# FLOW_RUNTIME_CONTRACT.md

Single source of truth for Flow web runtime behavior.

## Core states
- `idle`
- `connecting`
- `ready`
- `listening`
- `translating`
- `speaking`
- `offline`
- `failed`

## Legal transitions
- `idle -> connecting, offline`
- `connecting -> ready, offline, failed`
- `ready -> listening, offline, failed`
- `listening -> translating, ready, speaking, offline, failed`
- `translating -> speaking, ready, listening, offline, failed`
- `speaking -> ready, listening, offline, failed`
- `offline -> connecting, idle`
- `failed -> connecting, idle`

## Invariants
1. **Mic/TTS separation**
   - mic must not be active during `speaking`.
2. **Turn completion discipline**
   - if server sends `turn_complete` while TTS is active/playing/queued, defer completion (`pendingTurnComplete=true`).
   - complete turn only after playback drain/cancel and `tts_playback_done` handling.
3. **TTS done notification**
   - `tts_playback_done` should be sent once per playback cycle.
4. **Barge-in discipline**
   - barge-in only applies in `speaking`.
   - barge-in path: stop playback -> mark TTS inactive -> notify done -> return to listening.

## Enforcement points (web)
- `flow/static/flow_contract_guard.js`
- `flow/static/index.html` transition gate + runtime snapshot checks

## Failure policy
- Invalid transitions are rejected and logged.
- Contract violations are logged to diagnostics.
- Dev fail-fast can be enabled in guard construction if desired.
