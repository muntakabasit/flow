# FLOW_PWA_PLAYBACK_CUSTODY_REPAIR_V1_BUILD_REPORT

## Scope

Implemented the bounded client repair in `static/flow-pwa/app.js`. No server,
lease-policy, reconnect, input, language, scaling, or UI code was changed.
A deterministic Node VM harness was added at
`tests/test_pwa_playback_custody.mjs`.

## Repair

- The current `AudioBufferSourceNode` is retained in `activeAudioSource`.
- Lifecycle cleanup invalidates the playback generation before touching the
  source, which makes any captured stale `onended` callback inert.
- Cleanup ordering is: detach `onended`, stop the active source, clear the
  queue, clear playback flags and source custody, disconnect the source, prove
  the cleared state, then send `tts_playback_done`.
- A failed `source.stop()` marks cleanup unconfirmed. Local audio is abandoned,
  but `tts_playback_done` is not sent; server disconnect/watchdog recovery keeps
  ownership conservative.
- Hidden-page audio deltas are suppressed so late network delivery cannot
  restart playback after cleanup. Suppression clears when the page returns or a
  new user turn begins.
- `tts_playback_done` becomes sent only after it enters an open WebSocket, and
  duplicate lifecycle signals remain idempotent.
- Normal queue drain still advances source by source and emits one
  `playback_complete` acknowledgment.

## Validation

| Check | Result | Evidence |
|---|---|---|
| JavaScript syntax | PASS | `node --check static/flow-pwa/app.js` |
| Diff whitespace/errors | PASS | `git diff --check` |
| Deterministic Case G2 | PASS | Active source stopped once and disconnected; queued chunk removed; source custody, `playingAudio`, and `ttsStarted` cleared before acknowledgment. |
| Stale callback | PASS | Captured pre-cleanup `onended` callback did not create or start another source. |
| Late hidden audio | PASS | Post-cleanup `audio_delta` did not create another source. |
| Duplicate lifecycle events | PASS | `visibilitychange` followed by `pagehide` emitted exactly one `tts_playback_done`. |
| Unconfirmed cleanup | PASS | Forced `source.stop()` failure emitted zero `tts_playback_done` messages. |
| Normal playback regression | PASS | Two queued sources drained in order and emitted exactly one `playback_complete`. |

Harness command:

```text
node tests/test_pwa_playback_custody.mjs
PASS: lifecycle playback custody and normal drain are deterministic
```

## Admission Safety

The harness snapshots playback state synchronously when
`tts_playback_done` enters the WebSocket. The snapshot proves no active source,
queued audio, playing flag, or TTS-started flag remains at that point. When stop
is unconfirmed, no playback acknowledgment is sent.

The unchanged server policy checks `is_speaking` before `backgrounded` and
returns `active_playback`. Therefore `session_release` alone cannot admit a new
client while the old client still retains server-side playback ownership; only
confirmed client cleanup or the existing bounded watchdog can clear it.

## Risks

- Browser lifecycle WebSocket delivery remains best effort. If delivery fails,
  disconnect or the existing server watchdog remains the recovery path.
- A browser that rejects `AudioBufferSourceNode.stop()` takes the conservative
  zero-acknowledgment path and may delay takeover until disconnect/watchdog.
- Validation is deterministic local client simulation, not a physical Safari
  run.

## Files Modified

- `static/flow-pwa/app.js`
- `tests/test_pwa_playback_custody.mjs`
- `FLOW_PWA_PLAYBACK_CUSTODY_REPAIR_V1_BUILD_REPORT.md`

## Final Status

BUILD_PASS
