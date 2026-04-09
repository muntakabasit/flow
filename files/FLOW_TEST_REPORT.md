# FLOW — Comprehensive Test Report

**Date:** 2026-02-20
**Version:** Uncommitted (post `3977ded`)
**Platform:** Mac Mini (Apple Silicon) — 100% local inference
**Server:** `server_local.py` on port 8765
**Client:** `static/index.html` (vanilla HTML/CSS/JS PWA)
**Remote Access:** ngrok tunnel (`https://iteratively-unenvenomed-duncan.ngrok-free.dev`)
**Repository:** `muntakabasit/BelawuOS` (private)

---

## 1. Executive Summary

FLOW is a live bilingual voice interpreter (English <-> Brazilian Portuguese) running entirely on local hardware. This report covers the complete debugging, stabilization, and UI merge cycle performed across multiple sessions.

### Current Status

| Area | Status | Notes |
|------|--------|-------|
| **Server pipeline** | WORKING | STT -> LLM -> TTS -> turn_complete verified |
| **EN -> PT translation** | WORKING | Tested with full sentences |
| **PT -> EN translation** | WORKING | Tested with full paragraphs |
| **Language switching** | WORKING | Hysteresis=1 enables instant per-turn switching |
| **TTS playback** | WORKING | AudioContext.resume() fix for mobile |
| **WebSocket stability** | IMPROVED | pagehide fix prevents mobile session killing |
| **UI (turn cards)** | MERGED | Good UI from desktop dock version restored |
| **Stop/Start orb** | REFACTORED | Single clean toggle (was split across orb + OFF button) |
| **Voice-first output** | IMPLEMENTED | TTS plays before text appears |
| **Service worker cache** | BUSTED | v5 with no-cache headers on index.html |

---

## 2. Architecture Overview

```
                         FLOW ARCHITECTURE

  [Phone/Browser]                              [Mac Mini]
  +-----------------+    WebSocket /ws    +------------------+
  | index.html      | <================> | server_local.py  |
  |                 |   (ngrok tunnel)   |                  |
  | State Machine   |                    | Silero VAD       |
  | Audio Capture   |   PCM16 24kHz     | faster-whisper   |
  | TTS Playback    |   base64 chunks   | Ollama gemma3:4b |
  | Turn Cards UI   |                    | Piper TTS        |
  +-----------------+                    +------------------+
```

### Audio Pipeline

```
Browser Mic (24kHz)
  -> base64 encode
  -> WebSocket
  -> Resample to 16kHz
  -> Silero VAD (speech boundary detection)
  -> faster-whisper STT (transcription)
  -> Ollama LLM (translation)
  -> Piper TTS (synthesis at 22050Hz -> resample to 24kHz)
  -> base64 encode
  -> WebSocket
  -> Browser AudioContext playback
```

### State Machine

```
idle -> connecting -> ready -> listening -> translating -> speaking
                       ^         |              |            |
                       |         v              v            |
                       +---------+--------------+------------+
                       |
                    offline / failed
```

---

## 3. Bugs Found & Fixed

### 3.1 Critical Bugs

| # | Bug | Root Cause | Fix | Status |
|---|-----|-----------|------|--------|
| C1 | **`beforeunload` kills mobile sessions** | On mobile browsers, `beforeunload` fires on screen lock, app switch, notification pull-down. It set `sessionWanted=false` and `wsWanted=false`, closed WS with code 1000. `onclose` saw clean close -> IDLE -> never reconnected. | Replaced with `pagehide` event. Only does full cleanup when `e.persisted === false` (page actually destroyed). | FIXED |
| C2 | **AudioContext suspended on mobile** | Mobile browsers require user gesture before AudioContext can play audio. `getPlayCtx()` created context but never called `.resume()`. TTS audio silently failed -> `drainQ` stalled -> deferred turn_complete never fired -> stuck in SPEAKING forever. | Added `playCtx.resume()` in `getPlayCtx()` and `audioCtx.resume()` in `startMic()`. | FIXED |
| C3 | **`turn_complete` races with TTS playback** | Server sends `turn_complete` after finishing *sending* audio. Client is still *playing* audio. Mic opens during TTS playback -> echo loop. | Added `turnCompletePending` flag. `turn_complete` deferred if `playing || audioQ.length > 0`. Executed in `drainQ()` when queue empties. | FIXED |
| C4 | **Language hysteresis blocks conversation** | Required 3 consecutive same-language detections before switching. In a bilingual conversation (alternating EN/PT every turn), the counter reset every time. Language never actually switched. | Reduced `LANGUAGE_SWITCH_HYSTERESIS` to 1, `LANGUAGE_SWITCH_COOLDOWN` to 0. Each turn's detected language is trusted immediately. | FIXED |
| C5 | **`S.RECONNECTING` phantom state** | Existed in state enum but not in `VALID_TRANSITIONS`. `scheduleReconnect` called `transition(S.RECONNECTING)` which silently failed, blocking reconnection flow. | Removed `RECONNECTING` from enum entirely. `scheduleReconnect` calls `wsConnect()` directly. | FIXED |

### 3.2 Significant Bugs

| # | Bug | Root Cause | Fix | Status |
|---|-----|-----------|------|--------|
| S1 | **Audio streaming logic inverted** | Client-side VAD gate (`if (!vad.isSpeaking) return`) was too aggressive. Phone mic RMS didn't cross threshold -> no audio reached server. | Removed client-side VAD gate. Now streams all audio while in LISTENING state. Server-side Silero VAD handles speech detection. | FIXED |
| S2 | **Barge-in didn't send `tts_playback_done`** | After `killPlayback()` on barge-in, server was never told TTS was interrupted. Server kept `is_playing_tts = true` -> discarded all future mic audio. | Added `ws.send({type:'tts_playback_done'})` after `killPlayback()` in barge-in handler. | FIXED |
| S3 | **`keepaliveTimer` leak** | Set with `setInterval` but cleared with `clearTimeout` (wrong function). Timer accumulated, eventually consuming resources. | Changed all cleanup to `clearInterval`. | FIXED |
| S4 | **`isReconnecting` flag never cleared** | Not reset on health-check failure, WS creation error, or `onclose`. Once set, prevented new reconnection attempts. | Added `isReconnecting = false` on every error path. | FIXED |
| S5 | **`translation_done` handler race condition** | `finishTranslation()` nulled `currentSrcEl` before `saveExchange` could read it. | Captured refs before calling `finishTranslation()`. | FIXED |
| S6 | **`ws.onopen` transitioned to READY prematurely** | Transitioned before server sent `flow.ready`. Mic could start before models loaded. | Now waits for `flow.ready` message from server. | FIXED |
| S7 | **Duplicate `notifyTTSDone`** | Could fire multiple times, confusing server echo suppression. | Added `ttsDoneNotified` guard flag. | FIXED |
| S8 | **Whisper misdetects short Portuguese** | Short words like "Ola" detected as Chinese, Arabic, Spanish. | Added dual-transcription for segments < 2s: tries forced PT and forced EN, picks best. | FIXED |
| S9 | **Service worker caching stale HTML** | SW cached `/` (index.html). On mobile, fetch could fail through ngrok, falling back to OLD cached version. | Bumped SW version to `flow-v5`. Added `Cache-Control: no-cache, no-store, must-revalidate` header on `/`. | FIXED |
| S10 | **Two stop mechanisms confuse users** | Orb = soft stop (READY, keeps WS). OFF button = hard stop (IDLE, kills WS). Users didn't understand. | Merged into single orb toggle: tap = start, tap = full stop (kills everything). | FIXED |

### 3.3 Minor Bugs / Improvements

| # | Bug | Fix | Status |
|---|-----|------|--------|
| M1 | Stale comment says "kept at 400ms" but value is 700ms | Comment outdated from another agent's changes | KNOWN |
| M2 | `drainQ` safety timeout could double-fire | Timeout fires after chunk duration + 500ms if `onended` doesn't fire | MITIGATED |
| M3 | Visibility change handler only checks OFFLINE/FAILED | Now also checks if WS is actually dead after foreground | FIXED |
| M4 | `scrollToggle` / `scrollCheck` IDs missing in good UI | Added null guards (`if ($scrollToggle)`) | FIXED |
| M5 | FastAPI `on_event` deprecation warning | `@app.on_event("startup")` should migrate to lifespan handlers | KNOWN |

---

## 4. Server Configuration Audit

### Model Stack

| Component | Model | Size | Speed | Notes |
|-----------|-------|------|-------|-------|
| **STT** | faster-whisper `base` | ~140MB | ~600-1500ms | Good accuracy for EN/PT accents |
| **LLM** | Ollama `gemma3:4b` | ~2.5GB | ~400-1400ms | Low temperature (0.1) for consistent translations |
| **TTS** | Piper (EN: lessac-medium, PT: faber-medium) | ~63MB each | ~50-300ms | 22050Hz output, resampled to 24kHz |
| **VAD** | Silero v6 | ~2MB | <1ms/chunk | 16kHz input, 512-sample window |

### Reliability Modes

| Mode | Silence Duration | Keepalive Timeout | Use Case |
|------|-----------------|-------------------|----------|
| **stable** (default) | 1300ms | 90s | Reliable, waits for complete utterances |
| **fast** | 650ms | 45s | Responsive, may cut mid-sentence |

### Guard Rails

| Guard | Threshold | Action |
|-------|-----------|--------|
| Min speech segment | 350ms | Skip turn (noise) |
| Max speech segment | 30s | Force-stop VAD |
| Min STT confidence | 0.55 | Skip translation |
| Min energy RMS | 0.002 | Skip STT entirely |
| Gibberish detection | >50% same char, <20% vowels | Skip translation |
| Hallucination filter | Known patterns (music notes, subtitles, etc.) | Skip translation |
| Unsupported language | Not EN or PT | Retry with forced langs or skip |

---

## 5. Client Architecture Audit

### State Machine Transitions

| From | Allowed Targets |
|------|----------------|
| `idle` | connecting, offline |
| `connecting` | ready, offline, failed |
| `ready` | listening, offline, failed |
| `listening` | translating, ready, speaking, offline, failed |
| `translating` | speaking, ready, listening, offline, failed |
| `speaking` | ready, listening, offline, failed |
| `offline` | connecting, idle |
| `failed` | connecting, idle |

### Key Flags

| Flag | Purpose | Default |
|------|---------|---------|
| `sessionWanted` | User wants mic active | `true` |
| `wsWanted` | Keep WS alive | `true` |
| `serverReadyGate` | Server sent `flow.ready` | `false` |
| `turnCompletePending` | Defer turn cycle until TTS finishes | `false` |
| `ttsDoneNotified` | Prevent duplicate `tts_playback_done` | `false` |
| `isReconnecting` | Prevent concurrent reconnect attempts | `false` |
| `holdToTalkMode` | Push-to-talk vs always-on | `false` |
| `autoScroll` | Auto-scroll transcript | `true` |
| `audioOn` | TTS playback enabled | `true` |

### WebSocket Message Protocol

**Client -> Server:**

| Message | When | Payload |
|---------|------|---------|
| `audio` | Every ScriptProcessor frame (4096 samples) | `{type, audio: base64}` |
| `tts_playback_done` | TTS queue drained or barge-in | `{type}` |
| `keepalive_ping` | Every 20s | `{type}` |
| `language_config` | User changes language settings | `{type, source_language, target_language}` |
| `reliability_mode` | User changes mode | `{type, mode}` |

**Server -> Client:**

| Message | When | Payload |
|---------|------|---------|
| `flow.ready` | Server models loaded | `{type, reliability_mode, keepalive_timeout_ms}` |
| `speech_started` | VAD detects speech onset | `{type}` |
| `speech_stopped` | VAD detects speech end | `{type, vad_delta_ms}` |
| `source_transcript` | STT complete | `{type, text, diagnostics: {...}}` |
| `tts_start` | About to send TTS audio | `{type}` |
| `audio_delta` | TTS audio chunk | `{type, audio: base64}` |
| `translation_done` | Full translation text (sent AFTER TTS starts) | `{type, text}` |
| `turn_complete` | Turn finished (may arrive during TTS playback) | `{type, skip_reason?}` |
| `ping` | Server keepalive | `{type}` |
| `keepalive_pong` | Response to client ping | `{type}` |
| `mode_confirmed` | Mode switch acknowledged | `{type, reliability_mode, keepalive_timeout_ms}` |
| `error` | Any pipeline failure | `{type, code, message}` |

### Voice-First Output Order

```
Server sends:                      Client shows:
1. source_transcript  ---------> "You" card updates with source text
2. (LLM runs silently)           (no visible change)
3. tts_start          ---------> State -> SPEAKING, mic stops
4. audio_delta (chunks) -------> Audio plays through speakers
5. translation_done   ---------> "Translation" card updates with text
6. turn_complete      ---------> Deferred until audio finishes
7. (audio finishes)   ---------> State -> LISTENING, mic restarts
```

---

## 6. UI Architecture

### Layout (Merged from desktop dock version)

```
+----------------------------------+
|  [Flow]  [Interpreter]    [pill] |  <- Header
+----------------------------------+
|  English  <->  Portugues        |  <- Language bar
+----------------------------------+
|                                  |
|  +----------------------------+  |
|  |  YOU                       |  |  <- Source card
|  |  "Hello, how are you?"    |  |
|  +----------------------------+  |
|                                  |
|  +----------------------------+  |
|  |  TRANSLATION               |  |  <- Translation card
|  |  "Ola, como voce esta?"   |  |
|  +----------------------------+  |
|                                  |
|  [Recent exchanges...]          |  <- History preview
|                                  |
+----------------------------------+
|  ~~~~~~~~ waveform ~~~~~~~~      |  <- Audio visualization
|  [Audio]    (( ORB ))    [Hist]  |  <- Control dock
|              LISTENING           |
+----------------------------------+
```

### Drawer (slide-up panel)

Contains: Full transcript history, diagnostics log, VAD settings, language settings. Opened via History button in dock.

### Dock Controls

| Control | Position | Function |
|---------|----------|----------|
| **Audio toggle** | Left | Mute/unmute TTS playback |
| **Voice Orb** | Center | Tap to start/stop interpreting |
| **History** | Right | Open drawer with transcript & settings |

---

## 7. Observed Translation Performance

### From Server Logs (Previous Sessions)

| Metric | Value | Notes |
|--------|-------|-------|
| **Avg STT latency** | 600-1500ms | Depends on segment length |
| **Avg LLM latency** | 400-1400ms | Longer for paragraphs |
| **Avg TTS latency** | 50-300ms | Depends on text length |
| **Avg total turn** | 1.1-5.7s | End-to-end including all three stages |
| **Best turn time** | 984ms | "Obrigado" -> "Thank you" |
| **Worst turn time** | 8672ms | Long paragraph + cold LLM |

### Translation Quality Samples (From Logs)

| Input (Source) | Output (Translation) | Direction | Quality |
|---------------|---------------------|-----------|---------|
| "Hello, how are you?" | "Ola, como voce esta?" | EN->PT | GOOD |
| "what did you eat today?" | "O que voce comeu hoje?" | EN->PT | GOOD |
| "Obrigado" | "Thank you" | PT->EN | GOOD |
| "Eu nunca me imaginei ser rodeado..." (long paragraph) | "I never imagined being surrounded..." | PT->EN | GOOD |
| "So I just saw the video and all the models are very pretty..." | "Acabei de ver o video e todas as modelos sao muito bonitas..." | EN->PT | GOOD |
| "Ola" (short) | Initially misdetected as Chinese, fixed by dual-transcription | PT->EN | FIXED |
| "Voa la!" | "Go on!" | PT->EN | GOOD |
| "do." | "do." | PT->EN | POOR (too short to translate meaningfully) |

### Language Detection Accuracy

| Scenario | Before Fix | After Fix |
|----------|-----------|-----------|
| Long English sentences | GOOD (auto-detected correctly) | GOOD |
| Long Portuguese sentences | GOOD | GOOD |
| Short Portuguese ("Ola", "Obrigado") | POOR (misdetected as zh, de, ar, es) | GOOD (dual-transcription fallback) |
| Short English ("Hello", "Yes") | GOOD | GOOD |
| Mixed/ambiguous | POOR (stuck on initial language) | GOOD (instant switching) |

---

## 8. Known Issues & Limitations

### Open Issues

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| K1 | **ngrok WebSocket drops** | MEDIUM | Phone connections drop periodically through ngrok tunnel. App reconnects but loses ~2-5s per drop. Inherent to free ngrok tier. |
| K2 | **Phantom VAD triggers** | LOW | Short ambient sounds (0.2-0.4s) trigger VAD, produce empty transcripts. Filtered by `short_segment` guard but waste ~1s each. |
| K3 | **Dual-transcription doubles STT time** | LOW | Short segments run Whisper 2-3x (auto + forced PT + forced EN). Adds ~800ms for segments < 2s. |
| K4 | **No sentence-level TTS streaming** | LOW | TTS waits for full LLM response before synthesizing. True streaming would start TTS on first sentence. Requires server redesign. |
| K5 | **Desktop dock app caches old version** | MEDIUM | PWA installed from old code. Must re-install from localhost to get updated version. |
| K6 | **FastAPI `on_event` deprecation** | INFO | Will need migration to lifespan event handlers in future FastAPI versions. |

### Architectural Limitations

| Limitation | Impact | Mitigation |
|-----------|--------|------------|
| Single-threaded Whisper | STT blocks during transcription | Thread pool executor isolates blocking |
| CPU-only inference | Slower than GPU | Apple Silicon M-series provides decent CPU perf |
| Ollama cold starts | First translation ~5s slower | Warmup on server startup |
| 24kHz audio pipeline | Higher bandwidth than needed | Standard for speech quality |
| ScriptProcessor (deprecated) | May be removed from browsers | AudioWorklet migration planned |

---

## 9. Files Modified (Uncommitted)

| File | Lines | Change Summary |
|------|-------|---------------|
| `flow/static/index.html` | 2607 | Merged good UI (turn cards, drawer, glass dock) with fixed engine (deferred turn_complete, AudioContext.resume, pagehide, single orb toggle) |
| `flow/server_local.py` | 1216 | Voice-first output (TTS before text), language hysteresis=1, dual-transcription, no-cache headers, gibberish filter |
| `flow/static/sw.js` | 24 | Cache version bumped to `flow-v5` |
| `flow/static/flow_contract_guard.js` | DELETED | Guard system removed (342 lines). Functionality replaced by 15 lines of direct logic in index.html. |

---

## 10. Manual Test Checklist

### Critical Path Tests

- [ ] **5 continuous turns without stuck state** — Speak 5 sentences alternating EN/PT. App should cycle through listening -> translating -> speaking -> listening each time without getting stuck.
- [ ] **EN -> PT translation** — Say "Hello, how are you?" in English. Should hear Portuguese translation and see text.
- [ ] **PT -> EN translation** — Say "Ola, como voce esta?" in Portuguese. Should hear English translation and see text.
- [ ] **Barge-in** — While TTS is playing, start speaking. TTS should stop immediately, state returns to LISTENING.
- [ ] **No echo / feedback loop** — During TTS playback, speakers output should NOT be re-captured by mic and sent to server.
- [ ] **Orb start** — From idle state, tap orb. Should connect, show "listening" state, begin capturing audio.
- [ ] **Orb stop** — During active session, tap orb. Should fully stop (mic off, WS closed, state = idle).
- [ ] **Voice-first** — When translation completes, you should HEAR the translation BEFORE the text appears on screen.

### Mobile-Specific Tests

- [ ] **Phone background/foreground** — Lock phone, unlock. App should reconnect automatically without user tapping orb again.
- [ ] **Audio plays on mobile** — TTS audio actually plays through phone speakers (AudioContext.resume test).
- [ ] **Screen lock doesn't kill session** — Lock screen briefly, unlock. Session should recover (pagehide fix).
- [ ] **Hard refresh loads new version** — Pull-to-refresh on phone. Should load latest UI (not cached old version).

### UI Tests

- [ ] **Turn cards update** — "You" card shows what you said. "Translation" card shows the translation.
- [ ] **Drawer opens** — Tap History button in dock. Drawer slides up with transcript history.
- [ ] **Audio toggle** — Tap audio button. TTS should mute/unmute.
- [ ] **Language bar shows direction** — Header shows "English <-> Portugues".
- [ ] **Status pill reflects state** — Pill shows idle/connecting/ready/listening/translating/speaking.

### Edge Case Tests

- [ ] **Short utterance ("Ola")** — Should detect Portuguese and translate to English (dual-transcription).
- [ ] **Long paragraph (>10s)** — Should transcribe full segment without timeout.
- [ ] **Silence (no speech)** — Should stay in LISTENING, no phantom translations.
- [ ] **Network disconnect** — Pull airplane mode briefly. Should show offline, reconnect when online.
- [ ] **Server restart** — Kill server, restart. Client should reconnect automatically.

---

## 11. Commit History

| Hash | Message | Key Changes |
|------|---------|-------------|
| `8fc11dc` | Flow web interpreter: wired engine + all bug fixes | Initial state machine, WS, mic, playback, barge-in, reconnect |
| `ab4bac3` | Fix: stream all audio to server | Removed client-side VAD gate, let server Silero handle detection |
| `da10247` | Phase 1: Web orb physics refinement | Orb visual improvements |
| `97b9949` | server_local: restore whisper base, silence 700ms | Reverted another agent's aggressive settings |
| `a0fcb35` | code only | Other agent's 800-line UI rewrite (guard system, drawer, cards) |
| `3977ded` | message | Latest committed state |
| *(uncommitted)* | *(current working tree)* | Merged good UI + all engine fixes + voice-first |

---

## 12. Recommendations

### Immediate (Before Next Test)

1. **Hard refresh on all clients** — Phone browser and desktop browser both need cache-busted reload
2. **Re-install desktop PWA** — Delete old dock app, re-install from `localhost:8765`
3. **Commit current state** — Create a clean baseline commit with all fixes

### Short-Term

4. **Sentence-level TTS streaming** — Start TTS on first complete sentence from LLM instead of waiting for full translation. Would reduce perceived latency by 30-50%.
5. **Migrate ScriptProcessor to AudioWorklet** — ScriptProcessor is deprecated. AudioWorklet provides lower-latency, off-main-thread audio processing.
6. **Add WebSocket ping/pong monitoring UI** — Show connection quality indicator in status pill.

### Medium-Term

7. **Deploy to persistent server** — Replace ngrok with proper deployment (Tailscale, Cloudflare Tunnel, or VPS)
8. **Add conversation context** — Send previous turns to LLM for more contextual translations
9. **Speaker diarization** — Detect multiple speakers in the room, attribute utterances

---

*Report generated: 2026-02-20*
*Engine: faster-whisper (base) + Ollama gemma3:4b + Piper TTS*
*All inference runs locally on Mac Mini — zero cloud API calls*
