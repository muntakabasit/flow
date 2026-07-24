# FLOW_PWA_REPEAT_PARITY_V1_BUILD_REPORT

## Scope

Implemented the approved native Repeat behavior in the canonical Safari/PWA
client. The repair uses the existing server replay protocol and existing PWA
playback-custody machinery. It does not change server code, lease policy,
capture semantics, language behavior, runtime architecture, or interface
layout.

## Protocol Evidence

The current protocol was verified from source:

- Native sends exactly `{"type":"repeat"}` from
  `FlowWSClient.sendRepeat()` (`FlowSession.swift:1096-1103`).
- Server handles `msg_type == "repeat"` (`server_local.py:3593`).
- No cached output returns
  `{"type":"repeat_done","skip_reason":"no_repeat_available"}`.
- A valid replay streams the existing cached approved target text through
  `tts_start` and `audio_delta`, then sends `repeat_done`
  (`server_local.py:3604-3654`).
- The server does not run STT or translation in that branch and does not emit
  `translation_done` for replay.

No new message type or payload was introduced.

## Files Changed

- `static/flow-pwa/index.html`
  - Added Repeat beside Copy and Share using the existing action style.
  - Added an accessible name and hidden/disabled initial state.
  - Added a small repeat icon to the existing SVG sprite.
  - Bumped the canonical script URL from `app.js?v=9` to `app.js?v=10`.
- `static/flow-pwa/app.js`
  - Added replay availability, active-custody, and server-terminal state.
  - Added guarded `repeat` request handling.
  - Added `repeat_done` handling that waits for both server completion and
    actual audio queue drain.
  - Reused the existing one-shot `tts_playback_done` function.
  - Added bounded unavailable, disconnect, and lifecycle cleanup paths.
- `tests/test_pwa_capture_parity.mjs`
  - Added the new DOM control to the existing fixture only.
- `tests/test_pwa_playback_custody.mjs`
  - Added deterministic Repeat and regression coverage.
- `FLOW_PWA_REPEAT_PARITY_V1_BUILD_REPORT.md`
  - This report.

`static/flow-pwa/sw.js` was not changed. `server_local.py` had pre-existing
working-tree changes and was inspected only; its hash remained unchanged during
this build.

## State and Custody

```text
ready + approved target
  -> Repeat activation
  -> send one {"type":"repeat"}
  -> processing (repeat pending; capture blocked)
  -> tts_start/audio_delta
  -> speaking (existing audio queue/source custody)
  -> repeat_done received AND queue/source drained
  -> send one tts_playback_done
  -> clear repeat custody
  -> ready
```

`repeat_done` alone cannot release playback ownership while a source or queued
chunk remains. Queue drain before `repeat_done` also cannot release ownership;
the client waits for the server terminal message. Duplicate activation is
rejected while replay is pending or active.

The Repeat path does not modify `pendingSource`, `pendingTarget`, `currentPair`,
or `turns`. It never starts microphone capture and never sends `orb_released`.

## UI Behavior

- Repeat is hidden and disabled before approved target text exists.
- It appears with Copy and Share after a successful completed turn.
- It is available only in connected ready/idle state.
- The action bar is hidden during listening, processing, and speaking under the
  existing state behavior.
- The control is a native HTML button, supports pointer and keyboard activation,
  and exposes `aria-label="Repeat last translation"`.
- No action-bar redesign or new layout region was added.

## Validation

| Case | Result | Evidence |
|---|---|---|
| Hidden before first successful turn | PASS | Fixture observed hidden and disabled Repeat. |
| Approved target enables Repeat | PASS | Normal completed turn revealed and enabled the control. |
| Existing request contract | PASS | Exactly one `{"type":"repeat"}` was sent. |
| Duplicate activation | PASS | Two pending clicks produced one request. |
| No capture or commit | PASS | Capture remained idle and no `orb_released` was sent. |
| Capture blocked during replay | PASS | Orb activation during replay left capture idle. |
| Speaking state | PASS | `tts_start`/`audio_delta` entered existing speaking state. |
| Server terminal before drain | PASS | `repeat_done` emitted no early playback completion. |
| Partial drain | PASS | First queued source end emitted no completion. |
| Full drain | PASS | Final source end emitted exactly one replay completion and returned ready. |
| Conversation preservation | PASS | Card count/content and language direction were unchanged. |
| No cached server replay | PASS | Skip returned ready without fake playback completion or card mutation. |
| Background before audio | PASS | Pending replay was abandoned without claiming playback completion. |
| Background during audio | PASS | Active source stopped, queue cleared, custody cleared, and one completion followed confirmed cleanup. |
| Existing playback custody | PASS | Stale callback suppression and failed-stop no-ack behavior remained green. |
| Capture parity regression | PASS | `FLOW_CAPTURE_001` through `FLOW_CAPTURE_010` remained green. |

Commands run:

```text
node --check static/flow-pwa/app.js
node --check tests/test_pwa_playback_custody.mjs
node --check tests/test_pwa_capture_parity.mjs
node tests/test_pwa_playback_custody.mjs
node tests/test_pwa_capture_parity.mjs
git diff --check
```

Focused output:

```text
PASS: lifecycle custody, normal drain, and Repeat parity are deterministic
PASS: FLOW_CAPTURE_001 through FLOW_CAPTURE_010
```

## Untouched Systems

Confirmed untouched by this repair:

- `server_local.py` behavior and WebSocket protocol;
- session admission, ownership, and reconnect policy;
- STT, translation, language direction, and language lock;
- TTS generation and server cached-output logic;
- tap-toggle capture timing and commit authority;
- service-worker cache/version;
- native iOS code;
- PWA visual layout.

## Remaining Validation

- The deterministic harness proves client state, messages, playback ordering,
  and card preservation. It does not execute real Piper synthesis or physical
  Safari audio.
- A deployed physical Safari/PWA check should confirm the new `app.js?v=10`
  asset is received, Repeat is announced correctly by VoiceOver, and one real
  cached replay returns to ready.
- Because service-worker activation was not authorized, `sw.js` still
  pre-caches the prior versioned app URL. Online canonical loading uses the new
  query URL; service-worker cache alignment requires separate approval.

## Final Status

BUILD_COMPLETE_VALIDATION_PENDING
