# Plan: Build Local Voice API for Flow

Replace OpenAI Realtime API with a fully local pipeline. Zero cloud calls.

## Architecture

```
Browser (unchanged index.html)
  ↓ WebSocket /ws — PCM16 24kHz base64 audio chunks
  ↓
server_local.py (FastAPI)
  ├─ [1] Resample 24kHz → 16kHz (numpy)
  ├─ [2] Silero VAD — detect speech start/stop
  ├─ [3] faster-whisper — transcribe speech segment
  ├─ [4] Ollama (gemma3:4b) — translate EN↔PT-BR (streaming)
  ├─ [5] Piper TTS — synthesize spoken translation
  └─ [6] Send same events back to browser
```

Browser client needs ZERO changes — same WebSocket protocol, same event types.

## Steps

1. **Install deps** — `piper-tts` into dawt_bridge_backend/.venv (already has torch, faster-whisper, onnxruntime)
2. **Pull Ollama model** — `ollama pull gemma3:4b` (~3GB, fast, multilingual)
3. **Download Piper voices** — en_US-lessac-medium + pt_BR-faber-medium
4. **Build `flow/server_local.py`** — single file, ~400 lines:
   - Streaming Silero VAD (ONNX direct, persistent LSTM state)
   - faster-whisper batch transcription on speech segments
   - Ollama streaming translation via httpx
   - Piper TTS synthesis → PCM16 24kHz → base64 chunks
5. **Test** — run with dawt_bridge_backend/.venv, open browser, speak

## Latency Target

~1.3–2.1s from end of speech to first translated word (comparable to OpenAI path).

## Memory Budget (~3.5GB of 16GB)

- Whisper base: ~150MB
- Silero VAD: ~5MB
- Piper TTS (2 voices): ~120MB
- Ollama gemma3:4b: ~3GB
