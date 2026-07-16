# FLOW_FORCE_RELEASE_AUDIT_V1

Date: 2026-07-16  
Mode: audit only  
Application patches made by this audit: none

## Verdict

The legacy `force_release` behavior is `NORMAL_EXPLICIT_RELEASE`. The current
server has already renamed it to `_explicit_orb_release_pending`, and the
current server wording is semantically accurate.

The audit nevertheless found a Case G defect in the canonical PWA: Safari/PWA
lifecycle handlers can report `tts_playback_done` before queued/current audio
has actually stopped or drained. This can clear server playback ownership and
permit takeover while old client audio may still be active.

Final status: `AUDIT_DEFECT_FOUND`

## Scope And Method

Inspected:

- `server_local.py`
- `static/flow-pwa/app.js`
- `flow_turn_lifecycle.py`
- `tests/test_turn_lifecycle.py`
- `docs/FLOW_PROJECT_TRUTH_2026-07-16.md`
- existing Codex audit evidence for the prior freeze-gate and active-response validation

A-G were run through the real FastAPI/WebSocket handler with deterministic
VAD, STT, translation, and TTS substitutes. Session admission, release flags,
turn routing, lifecycle accounting, playback ownership, and cleanup were the
current application code. The harness used 800 ms synthetic TTS audio and a
0.5 s watchdog grace. No production source was changed.

## Flag Trace

The legacy name `force_release` no longer exists in current application code.
Its direct replacement is `_explicit_orb_release_pending`.

Assignment sites:

| Location | Assignment | Meaning |
|---|---|---|
| `server_local.py:2619` | `False` | Per-session initialization. |
| `server_local.py:3681` | `True` | Only after receiving `msg_type == "orb_released"` with audio present. |
| `server_local.py:3699` | `False` | Explicit release produced no VAD event/carryover; no commit follows. |
| `server_local.py:3442` | `False` | Unconditional `_commit_segment` final cleanup. |

Read sites:

| Location | Effect |
|---|---|
| `server_local.py:3455` | Prevents a pending VAD segment committing after explicit release already owns the turn. |
| `server_local.py:3468` | Same duplicate guard after debounce timeout. |
| `server_local.py:3795` | Routes the finalized VAD event to one `explicit_orb_release` commit and clears pending VAD state. |

Related commit-reason reads at `server_local.py:2781`, `2793`, `2843`, and
`3440` only select orb-release diagnostics/reset behavior; they do not create
another commit authority.

UI/runtime origin:

- Canonical PWA `release()` sends `{type: "orb_released"}` only when capture was
  active and streaming (`static/flow-pwa/app.js:563-575`).
- Pointer/touch/keyboard release events call `release()`
  (`static/flow-pwa/app.js:551-603`).
- Blur/visibility safety paths can also call `release()` while capture is active
  (`static/flow-pwa/app.js:608-619`).
- Server VAD `speech_stopped` never sets the flag (`server_local.py:3712-3721`).

## Cases A-F

`force_release` below means the legacy semantic value; in current code it is
the value of `_explicit_orb_release_pending` during dispatch/commit.

| Case | Scenario | turn_id | Commit trigger | force_release | VAD state | STT | Translation | TTS | Completion | Cleanup | Release reason |
|---|---|---|---|---:|---|---:|---:|---:|---|---|---|
| A | Normal EN to PT | `9e4259d9-1` | `explicit_orb_release` | true, then false in cleanup | speaking to finalized/idle | 1 | 1 | 1 | `ok` | `complete` | explicit orb release; playback done |
| B | Normal PT to EN | `64287e85-1` | `explicit_orb_release` | true, then false in cleanup | speaking to finalized/idle | 1 | 1 | 1 | `ok` | `complete` | explicit orb release; playback done |
| C1 | Sequential first turn | `b181e586-1` | `explicit_orb_release` | true, then false | speaking to finalized/idle | 1 | 1 | 1 | `ok` | `complete` | explicit orb release; playback done |
| C2 | Sequential second turn/natural VAD | `b181e586-2` | `vad_silence` | false | speaking to pending; 400 ms debounce; idle | 1 | 1 | 1 | `ok` | `complete` | VAD silence; playback done |
| D | Explicit release with zero audio | N/A, no committed turn | no `_commit_segment` | false (zero-audio guard precedes true assignment) | idle | 0 | 0 | 0 | `skipped:no_audio_received` frame | terminal state clear | explicit orb release |
| E | Incomplete thought | `3611c2e8-1` | `explicit_orb_release` | true, then false | speaking to finalized/idle | 1 | 0 | 0 | `skipped:incomplete_thought` | `complete` | explicit orb release |
| F | No-op output; bounded retry succeeds | `874dd964-1` | `explicit_orb_release` | true, then false | speaking to finalized/idle | 1 | 2 (1 retry) | 1 | `ok` | `complete` | explicit orb release; playback done |

Relevant evidence:

```text
[release_signal] explicit_orb_release
[turn_guard] skip vad commit due to explicit_orb_release
[turn_commit] reason=explicit_orb_release turn_id=9e4259d9-1
TURN_SUMMARY: ... "turn_id":"9e4259d9-1" ... "stt_count":1,
  "translation_count":1, "tts_request_count":1,
  "completion_status":"ok", "cleanup_status":"complete"

[release_signal] vad_silence
[turn_hold] waiting 400ms after VAD silence
[turn_commit] reason=vad_silence turn_id=b181e586-2
TURN_SUMMARY: ... "turn_id":"b181e586-2" ... "completion_status":"ok",
  "cleanup_status":"complete"

[translation_guard] noop_detected -> retry text="hello there friend"
TURN_SUMMARY: ... "turn_id":"874dd964-1" ... "translation_count":2,
  "retry_count":1, "tts_request_count":1, "cleanup_status":"complete"
```

All emitted summary invariants were true. Case D intentionally has no turn ID
or `TURN_SUMMARY` because no audio segment was committed; its terminal frame
and lease state both showed zero active processing/speaking state.

## Case G

### G1 - Disconnect During Playback

| Field | Evidence |
|---|---|
| turn_id | `9fe500a0-1` |
| Commit trigger / flag | `explicit_orb_release` / true, then false in cleanup |
| VAD | speaking to finalized/idle |
| Counts | STT 1; translation 1; TTS 1 |
| Completion / cleanup | `ok` / `complete` |
| Before disconnect | `capturing=false processing=false speaking=true` |
| Audio behavior | Server delivery completed. On client/document teardown, remaining browser playback is abandoned rather than retained by the server. |
| Ownership | Disconnect finalizer cleared speaking/deadline and removed the lease. |
| Lease availability | Immediately after disconnect; next connection received `flow.ready`. |

```text
[speaking_state] server_tts_delivery_complete audio_ms=800 ...
TURN_SUMMARY: ... "turn_id":"9fe500a0-1" ... "cleanup_status":"complete"
[flow-local] Client disconnected
[session] Released by case-g1-owner
[session] Acquired by case-g1-next
```

No stale server speaking state or stderr failure was observed.

### G2 - Release/Background During Playback

Server behavior for `session_release` alone is correct:

| Field | Evidence |
|---|---|
| turn_id | `cb955f64-1` |
| Commit trigger / flag | `explicit_orb_release` / true, then false in cleanup |
| VAD | finalized/idle; lease speaking remains true for playback |
| Counts | STT 1; translation 1; TTS 1 |
| Completion / cleanup | `ok` / `complete` |
| After release | `capturing=false processing=false speaking=true backgrounded=true` |
| Early takeover | Blocked with `SESSION_BUSY`, reason `active_playback`. |
| After playback done | `speaking=false backgrounded=true`. |
| Lease availability | Immediate `clean_release`; next client received `flow.ready`. |

```text
[session] Release signal received from case-g2-owner speaking=True
[session] lease_eligibility=blocked reason=active_playback ... backgrounded=True
[speaking_state] client_playback_complete reason=tts_playback_done was_active=true
[session] lease_eligibility=eligible reason=clean_release ...
[session] Acquired by case-g2-next
```

The next device completed turn `3a441a3f-1` with STT 1, translation 1, TTS 1,
`completion_status=ok`, `cleanup_status=complete`, and all invariants true.

### G Defect

The canonical PWA does not preserve the distinction tested above:

- On `visibilitychange` hidden it calls
  `signalPlaybackDone('visibility_hidden')` whenever playback is active or
  queued (`static/flow-pwa/app.js:613-619`).
- On `pagehide` it calls `signalPlaybackDone('pagehide')` under the same
  condition (`static/flow-pwa/app.js:668-679`).
- Playback uses an untracked local `AudioBufferSourceNode`; queued audio is
  removed only by natural `onended` chaining (`static/flow-pwa/app.js:715-742`).
- Neither lifecycle path empties `audioQueue`, stops the current source, marks
  `playingAudio=false`, nor waits for natural drain before reporting done.

Therefore the server can receive `tts_playback_done`, clear `is_speaking`, and
admit a clean-release takeover while the old page's current/queued audio has
not been proven stopped. Safari may suspend or terminate audio, but the code
does not establish that invariant. Duplicate/stale audio safety is therefore
not proven and can fail on a lifecycle implementation that continues or later
resumes the AudioContext.

No repair was made because this task authorizes audit only.

## Audit Questions

1. **Where is force_release set?** Only the current equivalent is set true at
   `server_local.py:3681`, inside the `orb_released` branch after the zero-audio
   guard. All assignments are listed above.
2. **Which UI or runtime event sets it?** Canonical PWA capture release sends
   `orb_released`; server receipt sets it. VAD silence does not.
3. **Does natural VAD completion commit without it?** Yes. Case C2 committed
   `b181e586-2` as `vad_silence` while the flag was false, after the 400 ms
   debounce.
4. **Is it expected on every normal browser turn?** It is expected for every
   canonical push-to-talk browser turn that actually streamed audio, because
   normal finger/key/safety release sends `orb_released`. It is not required by
   the runtime's separate natural-VAD path.
5. **Does it bypass speech-end or cleanup?** No. It intentionally bypasses only
   the VAD debounce. It calls `vad.force_finalize()`, consumes the resulting
   speech-stopped event, enters `_commit_segment`, emits lifecycle completion,
   and runs the same `finally` cleanup.
6. **Can it produce premature or duplicate commit?** The commit is immediate by
   explicit user intent, not premature. Pending VAD state is canceled and all
   three flag reads suppress a second VAD commit. The PWA's `captureWanted`
   guard and pointer/touch ownership also suppress duplicate release sends.
   No duplicate commit appeared in A-G.
7. **Is the log wording misleading even if behavior is correct?** The old
   `force_release` wording was misleading. Current `explicit_orb_release`
   wording is accurate. The method name `vad.force_finalize()` describes a VAD
   buffer flush, not abnormal turn completion, and is not used as the logged
   commit reason.

## Validation

- Deterministic live WebSocket audit A-G: completed.
- `python -m py_compile server_local.py flow_turn_lifecycle.py`: pass.
- `python tests/test_turn_lifecycle.py`: 9/9 pass.
- `node --check static/flow-pwa/app.js`: pass.
- `git diff --check -- server_local.py static/flow-pwa/app.js`: pass.
- Harness stderr markers: none in the successful run.
- `pytest` was unavailable in the project virtual environment; the lifecycle
  test module's built-in runner was used instead.

## Final Status

`AUDIT_DEFECT_FOUND`
