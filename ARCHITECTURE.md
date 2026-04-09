# Flow — Live Bilingual Interpreter Prototype

## What This Is

A throwaway proof-of-concept to validate the UX feel of a live bilingual
interpreter (English ↔ Brazilian Portuguese). Uses OpenAI's Realtime API
as a temporary stand-in. The final product will be local-first (Ollama-based).

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                     BROWSER                         │
│                                                     │
│  Microphone ──→ PCM16 @ 24kHz ──→ WebSocket /ws     │
│                                                     │
│  ← source_transcript   (what speaker said)          │
│  ← translation_delta   (streaming translation)      │
│  ← translation_done    (final translation)          │
│  ← audio_delta         (spoken translation)         │
│                                                     │
│  Rolling captions displayed in real-time             │
└──────────────────┬──────────────────────────────────┘
                   │ WebSocket
                   │
┌──────────────────▼──────────────────────────────────┐
│              FLOW SERVER (FastAPI)                   │
│                                                     │
│  /ws endpoint:                                      │
│    1. Accepts browser WebSocket                     │
│    2. Opens WebSocket to OpenAI Realtime API        │
│    3. Sends session.update with interpreter prompt   │
│    4. Relays audio: browser → OpenAI                │
│    5. Relays events: OpenAI → browser               │
│                                                     │
│  Thin proxy. No state. No business logic.           │
└──────────────────┬──────────────────────────────────┘
                   │ WebSocket
                   │
┌──────────────────▼──────────────────────────────────┐
│          OPENAI REALTIME API                        │
│                                                     │
│  Model: gpt-4o-realtime-preview                     │
│  Input: PCM16 audio stream                          │
│  Output: text translation + spoken audio            │
│  VAD: server-side (700ms silence detection)         │
│  Transcription: whisper-1 (input side)              │
│                                                     │
│  System prompt enforces pure interpreter behavior   │
└─────────────────────────────────────────────────────┘
```

---

## Audio Flow (detailed)

```
1. Browser captures mic at 24kHz mono PCM16
2. ScriptProcessor sends 4096-sample chunks
3. Each chunk: Float32 → Int16 → base64 → JSON → WebSocket
4. Server receives { type: "audio", audio: "base64..." }
5. Server forwards as { type: "input_audio_buffer.append", audio: "base64..." }
6. OpenAI VAD detects speech boundaries
7. On speech end, model generates translation
8. Server relays:
   - response.audio_transcript.delta → translation_delta (streaming text)
   - response.audio_transcript.done  → translation_done  (final text)
   - response.audio.delta            → audio_delta        (spoken translation)
   - conversation.item.input_audio_transcription.completed → source_transcript
9. Browser renders captions and optionally plays audio
```

---

## System Prompt

The interpreter prompt is the behavioral core. It enforces:
- Automatic language detection (EN → pt-BR, PT → EN)
- Literal translation only
- No additions, corrections, or expansions
- Preservation of tone, fragments, and hesitations
- Silence unless translating

Full prompt is in `server.py` → `INTERPRETER_PROMPT`.

---

## Event Protocol (Browser ↔ Server)

### Browser → Server
| Type | Payload | Purpose |
|------|---------|---------|
| `audio` | `{ audio: "base64..." }` | Mic audio chunk |

### Server → Browser
| Type | Payload | Purpose |
|------|---------|---------|
| `flow.ready` | `{ message }` | Session initialized |
| `source_transcript` | `{ text }` | What the speaker said (original) |
| `translation_delta` | `{ text }` | Streaming translation fragment |
| `translation_done` | `{ text }` | Complete translation |
| `audio_delta` | `{ audio }` | Spoken translation audio chunk |
| `turn_complete` | `{}` | Turn boundary |
| `speech_started` | `{}` | VAD: speaker started |
| `speech_stopped` | `{}` | VAD: speaker stopped |
| `error` | `{ message }` | Error from OpenAI |

---

## Latency Profile

Expected end-to-end latency for this prototype:

| Stage | Latency | Notes |
|-------|---------|-------|
| Mic capture → server | ~10ms | Local network |
| Server → OpenAI | ~50-100ms | WS to OpenAI servers |
| VAD detection | ~700ms | Configurable silence_duration_ms |
| Model inference | ~200-500ms | First token |
| Streaming back | ~10ms/chunk | Streamed, not batched |
| **Total (first word)** | **~1-1.5s** | After speaker stops |

The dominant bottleneck is VAD silence detection (700ms). Lowering it increases
responsiveness but also increases false triggers on pauses.

Audio output adds ~100ms additional delay for buffering.

---

## Tradeoffs in This Prototype

| Decision | Why | Cost |
|----------|-----|------|
| ScriptProcessor (deprecated) | Simpler than AudioWorklet for a prototype | Will need migration |
| Server VAD (not client) | Simpler; OpenAI handles speech detection | 700ms minimum latency |
| Full audio+text modality | Get both captions AND spoken output | Higher API cost |
| Single WebSocket proxy | Minimal server code | Single point of failure |
| No reconnection logic | Prototype | Session dies on disconnect |
| No authentication | Prototype | Anyone on network can connect |

---

## Migration to Local/Ollama Backend

To replace OpenAI with a local-first stack:

### 1. Speech-to-Text (replace OpenAI Realtime input)
- **Whisper.cpp** or **faster-whisper** running locally
- Already partially exists in `dawt_bridge_backend/app/whisper_local.py`
- Need: streaming mode (not batch file upload)
- Consider: **whisper-streaming** project for real-time chunked inference

### 2. Translation (replace GPT-4o)
- **Ollama** with a translation-capable model
- Options: `llama3`, `mistral`, `command-r` with translation prompt
- Or dedicated: **NLLB** (No Language Left Behind) by Meta — 200 languages
- Or: **MarianMT** models from Helsinki-NLP (fast, small, pairs-specific)
- Key: response time must be <500ms for live feel

### 3. Text-to-Speech (replace OpenAI Realtime output)
- **Piper TTS** — fast, local, good quality
- **Coqui TTS** — more voices, slightly heavier
- **eSpeak** — fastest, lowest quality (fallback)
- Need: <200ms latency for first audio chunk

### 4. VAD (replace OpenAI server VAD)
- **Silero VAD** — small, fast, accurate
- **WebRTC VAD** — built into browsers
- Run client-side to reduce round-trip latency

### 5. Architecture Changes
```
Current:  Mic → Server → OpenAI → Server → Browser
Local:    Mic → Client VAD → Server → Whisper → Ollama → Piper → Browser
                                      (local)   (local)  (local)
```

The server becomes a local orchestrator instead of a cloud proxy.
All processing stays on-device or LAN. No data leaves the network.

### 6. What Stays the Same
- WebSocket protocol between browser and server
- Caption rendering in the browser
- The event types (source_transcript, translation_delta, etc.)
- The interpreter prompt (adapted for the local model)
- Audio format (PCM16 @ 24kHz)

---

## Running the Prototype

```bash
cd /path/to/BelawuOS/flow

# Install dependencies
pip install -r requirements.txt

# Start the server
python server.py

# Open browser to http://localhost:8765
# Click "Start Interpreting"
# Speak in English or Portuguese
```

Requires:
- Python 3.9+
- OpenAI API key with Realtime API access (set in dawt_bridge_backend/.env)
- A microphone
- A modern browser (Chrome, Firefox, Safari)
