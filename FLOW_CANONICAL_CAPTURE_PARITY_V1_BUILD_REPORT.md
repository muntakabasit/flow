# FLOW_CANONICAL_CAPTURE_PARITY_V1_BUILD_REPORT

## Scope

Implemented the native-style tap-toggle capture interaction in the canonical
PWA. No commit, freeze, deployment, or hard-cap work was performed.

The named `FLOW_CANONICAL_CAPTURE_PARITY_V1_BUILD_CONTRACT` file was not present
in the workspace. The detailed contract supplied in the task and
`FLOW_CANONICAL_CAPTURE_INTERACTION_AUDIT_V1.md` governed this build.

## Files Changed

- `static/flow-pwa/app.js`
- `static/flow-pwa/index.html`
- `tests/test_pwa_capture_parity.mjs`
- `FLOW_CANONICAL_CAPTURE_PARITY_V1_BUILD_REPORT.md`

`server_local.py` and the native iOS sources already had unrelated working-tree
changes before this task. They were not modified by this build.

## State-Machine Truth

| Area | Before | After |
|---|---|---|
| Normal activation | Pointer/touch down started capture. | One completed button activation starts capture. |
| Normal release | Pointer/touch up, cancel, or lost capture submitted. | No release-family listener submits. Finger-up alone has no capture action. |
| Capture duration | Capture lasted only while the gesture was held. | Capture persists in `recording` until a second completed activation. |
| Second tap | Could start another capture attempt. | Sets the bounded stop-pending state. |
| Commit | Immediate release, conditional on prior streaming. | Second-tap commit stops the mic, sends exactly one `orb_released`, and enters `committing`/`processing`. |
| Busy input | `captureWanted` was the only input guard. | `committing`, processing, speaking, stop-pending, and commit-locked states reject activation. |
| Keyboard | Keydown started and keyup submitted. | Non-repeated keydown uses the same toggle; keyup never toggles or submits. |
| Wording | “Hold to speak.” | “Tap to record.” |

The implemented capture phases are:

```text
idle --first completed tap--> recording
recording --second completed tap--> stop pending
stop pending --800 ms minimum + 150 ms grace--> committing / processing
committing --terminal turn cleanup--> idle / ready
```

## Timing Implementation

- `CAPTURE_MIN_DURATION_MS = 800`
- `CAPTURE_TRAILING_GRACE_MS = 150`
- Capture start is recorded with `performance.now()` when available, with
  `Date.now()` as fallback.
- A stop requested before 800 ms waits only for the remaining minimum duration.
- After the minimum is satisfied, a separate 150 ms timer provides trailing
  capture grace. The microphone and audio streaming remain active through both
  waits.
- A stop requested after 800 ms still receives the full 150 ms grace.

## Commit and Idempotence

The client now maintains:

- `captureGeneration` to invalidate deferred work from an older capture;
- `captureStopPending` to admit only one stop request;
- `captureCommitLocked` to admit only one commit;
- `capturePhase` (`idle`, `recording`, `committing`) for state gating;
- a retained stop timer that is cleared on reset/disconnect;
- generation and state checks in both deferred timer stages.

The normal commit order is:

1. Validate generation, recording phase, stop-pending state, and commit lock.
2. Lock commit and transition capture phase to `committing`.
3. Mark capture unwanted and invalidate pending microphone setup.
4. Stop and release microphone resources.
5. Send one existing `{"type":"orb_released"}` message.
6. Enter processing.

No WebSocket message type or payload was added or changed.

## Validation Results

| ID | Result | Evidence |
|---|---|---|
| `FLOW_CAPTURE_001` | PASS | Ready/open first click entered `recording` and `listening`; microphone streaming persisted. |
| `FLOW_CAPTURE_002` | PASS | No `pointerup`, `pointercancel`, or `lostpointercapture` capture listener remains; no release message followed the first tap. |
| `FLOW_CAPTURE_003` | PASS | Second click stopped capture after timing completion and emitted exactly one `orb_released`. |
| `FLOW_CAPTURE_004` | PASS | At 799 ms capture and track were active with zero commits; minimum-stage completion at 800 ms still did not commit. |
| `FLOW_CAPTURE_005` | PASS | Commit occurred only after the additional 150 ms grace, both for early and post-minimum stop requests. |
| `FLOW_CAPTURE_006` | PASS | Rapid start/stop/extra activation produced one capture and one bounded commit at 950 ms. |
| `FLOW_CAPTURE_007` | PASS | Extra activations during stop-pending and committing states produced no extra capture or release. |
| `FLOW_CAPTURE_008` | PASS | Activation during processing did not call `getUserMedia` again. |
| `FLOW_CAPTURE_009` | PASS | Activation after `tts_start` entered speaking but did not call `getUserMedia` again. |
| `FLOW_CAPTURE_010` | PASS | Space/Enter non-repeated keydown toggled; repeat and keyup did not submit; one commit resulted. |
| `FLOW_CAPTURE_011` | PASS | Existing playback-custody harness still proved confirmed lifecycle stop/clear ordering, stale callback suppression, zero acknowledgment on failed stop, and one natural drain acknowledgment. |

Focused commands:

```text
node --check static/flow-pwa/app.js
node --check tests/test_pwa_capture_parity.mjs
node tests/test_pwa_capture_parity.mjs
node tests/test_pwa_playback_custody.mjs
git diff --check
```

Observed focused output:

```text
PASS: FLOW_CAPTURE_001 through FLOW_CAPTURE_010
PASS: lifecycle playback custody and normal drain are deterministic
```

Static inspection also confirmed both existing HTML semantics are now
`Tap to record` / `TAP TO RECORD`, and no hold-to-speak wording remains in the
canonical PWA files.

## Untouched Systems

Confirmed unchanged by this task:

- `server_local.py` and server startup architecture;
- WebSocket protocol and payload schema;
- lease/session ownership and `SESSION_BUSY` handling;
- reconnect delays, retry limits, and close-code policy;
- translation and language-lock behavior;
- TTS queueing and playback-custody cleanup;
- blur, visibility, pagehide, and session-release event wiring;
- PWA layout and interface element set;
- processing feedback behavior;
- native iOS code.

The existing lifecycle-triggered capture release remains immediate and retains
its prior requirement that streaming must have started before it sends
`orb_released`. This preserves background lifecycle behavior and is separate
from the new normal second-tap timing path.

## Git Diff Summary

Tracked runtime diff at validation time:

```text
static/flow-pwa/app.js     | tap-toggle state, timing, locks, and state resets
static/flow-pwa/index.html | two existing wording changes only
```

One focused test harness and this report are new untracked files. No files were
staged or committed.

## Known Limitations

- Physical Safari and installed-PWA validation remains pending. Local validation
  uses deterministic VM-controlled monotonic time and timers.
- If the socket/server is not ready, activation invokes the existing connection
  path but does not start the microphone. A later ready-state tap is required.
- `FLOW_HARD_CAP_PARITY_V1` remains intentionally unimplemented. The existing
  `speech_stopped` handling was preserved without widening this build.
- Background lifecycle keeps its existing immediate release semantics rather
  than adopting the normal tap timing guards.
- The service-worker cache version and app asset query were not changed because
  they were outside the permitted secondary-target wording scope.

## Final Status

BUILD_COMPLETE_VALIDATION_PENDING
