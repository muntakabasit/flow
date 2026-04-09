# FLOW WebSocket Protocol (/ws)

**Server:** FastAPI at `localhost:8765/ws`
**Client:** Browser JavaScript
**Format:** JSON text frames (not binary)
**Audio Encoding:** Base64 PCM16 @ 24kHz

---

## Connection Flow

### 1. Client Connects
```javascript
ws = new WebSocket('ws://localhost:8765/ws')
```

### 2. Server Sends Initial Message
```json
{
  "type": "flow.ready",
  "message": "Local interpreter active. Speak naturally.",
  "reliability_mode": "stable",
  "keepalive_timeout_ms": 90000
}
```

### 3. Client Sends Mode Preference (optional)
```json
{
  "type": "mode_preference",
  "mode": "stable"  // or "fast"
}
```

Server responds:
```json
{
  "type": "mode_confirmed",
  "reliability_mode": "stable",
  "keepalive_timeout_ms": 90000
}
```

---

## Message Types

### CLIENT → SERVER

#### Audio Chunk (Main)
```json
{
  "type": "audio",
  "audio": "AUGBAPwD..."  // base64 PCM16 @ 24kHz
}
```
- Sent continuously while user is speaking
- ~4096 samples per chunk (~170ms at 24kHz)
- Must be base64-encoded PCM16 (16-bit signed int)

#### TTS Playback Done (Echo Suppression)
```json
{
  "type": "tts_playback_done"
}
```
- Sent when browser finishes playing TTS audio
- Signals server to resume mic capture

#### Mode Preference
```json
{
  "type": "mode_preference",
  "mode": "stable" | "fast"
}
```
- Optional; sent if client wants to switch reliability modes
- "stable": 90s keepalive, 1.3s speech detection, higher accuracy
- "fast": 45s keepalive, 650ms speech detection, responsive

#### Keepalive Ping (Optional)
```json
{
  "type": "keepalive_ping"
}
```
- Client may send this instead of waiting for server pings
- Server responds with `{"type": "keepalive_pong"}`

#### Pong Response
```json
{
  "type": "pong"
}
```
- Response to server's `{"type": "ping"}`
- Keeps connection alive

---

### SERVER → CLIENT

#### Flow Ready (on connect)
```json
{
  "type": "flow.ready",
  "message": "Local interpreter active. Speak naturally.",
  "reliability_mode": "stable",
  "keepalive_timeout_ms": 90000
}
```

#### Mode Confirmed
```json
{
  "type": "mode_confirmed",
  "reliability_mode": "stable",
  "keepalive_timeout_ms": 90000
}
```

#### Keepalive Ping
```json
{
  "type": "ping"
}
```
- Sent every 20 seconds (configurable per mode)
- Client must respond with `{"type": "pong"}`
- If client doesn't pong within `keepalive_timeout_ms`, server closes connection

#### Keepalive Pong
```json
{
  "type": "keepalive_pong"
}
```
- Response to client's `keepalive_ping`

#### Speech Started (from Server VAD)
```json
{
  "type": "speech_started"
}
```
- Sent when server detects speech beginning
- Indicates audio is being processed

#### Speech Stopped (from Server VAD)
```json
{
  "type": "speech_stopped"
}
```
- Sent when server VAD detects end of speech (silence for configured duration)
- Server starts STT + translation pipeline

#### TTS Start
```json
{
  "type": "tts_start"
}
```
- Sent when server begins generating TTS audio
- Indicates translation complete, playing response

#### Audio Delta (TTS Chunk)
```json
{
  "type": "audio_delta",
  "audio": "AUGBAPwD..."  // base64 PCM16 @ 24kHz
}
```
- Streamed TTS audio chunks
- Base64 PCM16 @ 24kHz
- Multiple chunks sent sequentially
- Client must queue and play in order

#### Turn Complete
```json
{
  "type": "turn_complete"
}
```
- Sent when translation + TTS finishes
- Signals end of current conversation turn
- Client may return to listening state

---

## Audio Format Details

### Encoding
- **Input:** Mono PCM16 (16-bit signed integers)
- **Sample Rate:** 24kHz
- **Chunk Size:** ~4096 samples (~170ms)
- **Transport:** Base64 encoded JSON

### Conversion (JavaScript)

**Float32 → PCM16 → Base64:**
```javascript
function f32toI16(f32) {
  const i16 = new Int16Array(f32.length);
  for (let i = 0; i < f32.length; i++) {
    i16[i] = Math.max(-1, Math.min(1, f32[i])) < 0
      ? i16[i] * 0x8000
      : i16[i] * 0x7FFF;
  }
  return i16;
}

function i16toB64(i16) {
  const bytes = new Uint8Array(i16.buffer);
  let b64 = '';
  for (let i = 0; i < bytes.length; i++) {
    b64 += String.fromCharCode(bytes[i]);
  }
  return btoa(b64);
}
```

**Base64 → PCM16 → Float32:**
```javascript
function b64toF32(b64) {
  const raw = atob(b64);
  const bytes = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) {
    bytes[i] = raw.charCodeAt(i);
  }
  const i16 = new Int16Array(bytes.buffer);
  const f32 = new Float32Array(i16.length);
  for (let i = 0; i < i16.length; i++) {
    f32[i] = i16[i] / 32768;
  }
  return f32;
}
```

---

## Server-Side VAD

Server uses **Silero VAD** for speech detection:

- **Sample Rate:** 16kHz (resampled from browser's 24kHz)
- **Speech Start Threshold:** ~0.5 (confidence)
- **Silence Duration (mode):**
  - `stable`: 1300ms
  - `fast`: 650ms
- **Timeout:** 60 seconds of silence or 120 seconds total = force end turn

When VAD detects speech end, server:
1. Sends `{"type": "speech_stopped"}` to client
2. Runs STT (faster-whisper)
3. Runs translation (Ollama gemma3:4b)
4. Sends `{"type": "tts_start"}`
5. Streams TTS chunks via multiple `audio_delta` messages
6. Sends `{"type": "turn_complete"}` when done

---

## Keepalive Logic

### Client Side (Recommended)
```javascript
const KEEPALIVE_INTERVAL = 20000; // 20 seconds
const KEEPALIVE_TIMEOUT = 90000;  // 90 seconds (from server)

setInterval(() => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'keepalive_ping' }));
  }
}, KEEPALIVE_INTERVAL);

let lastPongTime = Date.now();
let timeoutCheck = setInterval(() => {
  if (Date.now() - lastPongTime > KEEPALIVE_TIMEOUT) {
    // Close and reconnect
    ws.close();
  }
}, KEEPALIVE_TIMEOUT);
```

### Server Side
- Sends `ping` every 20 seconds (per mode)
- Expects `pong` within `keepalive_timeout_ms`
- Closes connection if no pong received

---

## Reconnection Strategy

### Exponential Backoff
```
Attempt 1: 0.5s delay
Attempt 2: 1.0s delay
Attempt 3: 2.0s delay
Attempt 4: 5.0s delay (cap)
Attempt 5+: 5.0s delay
```

### Reset on Success
- After successful connection + 2000ms stable, reset backoff index to 0

---

## Echo Suppression

Server has `is_playing_tts` flag:
- When server sends `tts_start`, it sets flag = true
- While flag is true, server **discards incoming audio chunks**
- Client must send `tts_playback_done` when audio finishes playing
- Server sets flag = false, resumes accepting audio

---

## Error Handling

Currently **no explicit error messages** sent to client. Server logs errors and sends `turn_complete` to signal end of bad turn.

For future: Could send:
```json
{
  "type": "error",
  "message": "Could not understand speech. Please try again.",
  "code": "STT_FAILED"
}
```

---

## Summary Table

| Direction | Type | Purpose | Sent By |
|-----------|------|---------|---------|
| ← | `flow.ready` | Initial connection signal | Server |
| ← | `mode_confirmed` | Mode change ack | Server |
| → | `mode_preference` | Request mode change | Client |
| → | `audio` | Stream audio chunk | Client |
| ← | `speech_started` | VAD detected speech | Server |
| ← | `speech_stopped` | VAD detected silence | Server |
| ← | `tts_start` | TTS generation beginning | Server |
| ← | `audio_delta` | TTS audio chunk | Server |
| → | `tts_playback_done` | TTS playback finished | Client |
| ← | `turn_complete` | Turn finished, ready for next | Server |
| ← | `ping` | Keepalive heartbeat | Server |
| → | `pong` | Keepalive response | Client |
| → | `keepalive_ping` | (Optional) client heartbeat | Client |
| ← | `keepalive_pong` | Response to keepalive_ping | Server |

---

**This is the complete, exact protocol. No guessing needed.** ✅
