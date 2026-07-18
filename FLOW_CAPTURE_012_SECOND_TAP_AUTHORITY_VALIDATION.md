# FLOW_CAPTURE_012_SECOND_TAP_AUTHORITY_VALIDATION

## Mode

Validation only. No application or test code was modified.

## Method

The validation ran the current `server_local.py` production server on local port
8765 with its real Silero VAD, `mlx-whisper`, Ollama `gemma3:4b`, and Piper TTS.
The current canonical `static/flow-pwa/app.js` was executed unchanged in a
VM-backed browser surface connected to the real server WebSocket.

Input was real synthesized English speech, “Hello, how are you today?”, decoded
to 48 kHz float PCM and passed through the PWA microphone processor. The PWA
performed its normal 48 kHz to 24 kHz conversion and WebSocket transport. After
speech, silent microphone chunks continued for 1,684 ms without a second tap.

TTS output used the unchanged PWA queue and completion logic. The browser audio
node was simulated at the real PCM duration so playback custody and readiness
could complete deterministically.

## Before Second Tap

Observed after 1,684 ms of continuous silent capture:

| Evidence | Value |
|---|---|
| Client application state | `listening` |
| Client capture phase | `recording` |
| `captureWanted` | `true` |
| Microphone streaming | `true` |
| Stop pending | `false` |
| Commit locked | `false` |
| `orb_released` sent | 0 |
| `source_transcript` received / STT result count | 0 |
| `translation_done` received | 0 |
| `tts_start` received | 0 |
| `turn_complete` received | 0 |
| Server `active_capture` | 1 |
| Server `active_stt` | 0 |
| Server `active_translation` | 0 |
| Server `active_tts` | 0 |
| Server successful turns | 0 |
| Server failed turns | 0 |

The server log window was ordered as follows:

```text
[flow-local] First audio chunk received
[flow-local] Speech started
... 1,684 ms silence and pre-second-tap metrics read ...
[release_signal] explicit_orb_release
```

There was no `[release_signal] vad_silence`, `[turn_commit]`, STT, translation,
TTS, processing transition, or speaking transition before the explicit release.

## After Second Tap

The second completed tap used the PWA timing path and sent one release. The real
server then completed one successful turn.

| Evidence | Value |
|---|---|
| `orb_released` sent | 1 |
| Server turn commits | 1 |
| Commit reason | `explicit_orb_release` |
| STT count | 1 |
| Translation count | 1 |
| TTS request count | 1 |
| `source_transcript` received | 1 |
| `translation_done` received | 1 |
| `tts_start` received | 1 |
| `turn_complete` received | 1 |
| `tts_playback_done` sent | 1 |
| Completion status | `ok` |
| Cleanup status | `complete` |
| Client final application state | `ready` |
| Client final capture phase | `idle` |
| Server successful turns | 1 |
| Server failed turns | 0 |

Authoritative server lines:

```text
[release_signal] explicit_orb_release
[flow-local] orb_released → explicit_vad_finalize (1 event(s))
[turn_guard] skip vad commit due to explicit_orb_release
[turn_commit] reason=explicit_orb_release turn_id=79c8a195-1
[flow-local] STT (1013ms): [en] confidence=0.99 text='Hello, how are you today?'
[flow-local] Translation done: TTFT=1089ms
[tts_boundary] approved_payload='Olá, como você está hoje?' lang=pt-BR
[speaking_state] client_playback_complete reason=tts_playback_done was_active=true
```

The bounded turn summary was:

```json
{
  "turn_id": "79c8a195-1",
  "stt_count": 1,
  "translation_count": 1,
  "retry_count": 0,
  "tts_request_count": 1,
  "completion_status": "ok",
  "cleanup_status": "complete"
}
```

Only one `turn_commit`, one `TURN_SUMMARY`, one release message, and one response
completion were observed. No `vad_silence` commit occurred anywhere in the case.

## Server Compatibility

Current server-side behavior is compatible with tap-to-start / tap-to-submit:

- `StreamingVAD.process_chunk()` tracks silence but deliberately suppresses the
  silence threshold as a turn boundary (`server_local.py:561-564`).
- Natural server VAD can stop only at the 300-second hard cap
  (`server_local.py:564-573`). That intentional safety boundary was not reached.
- While recording, the canonical PWA sends only `audio`; it does not send the
  legacy `speech_stopped` message.
- The PWA sends `orb_released` only after the second tap timing completes.
- The server's `vad_silence` route remains reachable if some client explicitly
  sends `speech_stopped`, but the canonical PWA does not use that route.

Therefore 1.5 seconds or more of natural silence cannot commit a canonical PWA
turn before the second tap under the current routing law.

## Limits

- The browser surface was deterministic rather than physical Safari. The PWA
  source, real WebSocket, server VAD, STT, translation, TTS, metrics, and server
  lifecycle were real.
- The intentional 300-second server hard cap remains an authorized exception to
  second-tap authority and was outside this bounded case.

## Final Status

SECOND_TAP_AUTHORITY_PASS
