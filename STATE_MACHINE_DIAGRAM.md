# FLOW State Machine — Visual Guide

## Complete State Flow Diagram

```
                    PAGE LOAD
                        │
                        ▼
    ┌─────────────────────────────────┐
    │  IDLE (initial state)           │
    │  - Not connected to server      │
    │  - Mic disabled                 │
    │  - Pill: Gray                   │
    └─────────────────────────────────┘
                        │ (click mic OR OFF button click)
                        ▼
    ┌─────────────────────────────────┐
    │  CONNECTING                     │
    │  - Health check in progress     │
    │  - WebSocket establishing       │
    │  - Pill: Yellow                 │
    │  - Duration: 1-3 seconds        │
    └─────────────────────────────────┘
            │           │
     OK     │           │  Health check failed
            ▼           ▼
         READY      OFFLINE
            │           │
            │     (auto-reconnect or click reconnect)
            │           │
            └───────────┘
                        │
                        ▼
    ┌─────────────────────────────────┐
    │  READY (stable state)           │
    │  - Connected to server          │
    │  - Waiting for user input       │
    │  - Mic enabled                  │
    │  - Pill: Green                  │
    └─────────────────────────────────┘
                        │ (click mic & serverReadyGate open)
                        ▼
    ┌─────────────────────────────────┐
    │  LISTENING                      │
    │  - Capturing audio              │
    │  - Running VAD                  │
    │  - Pill: Blue                   │
    │  - Waiting for speech pause     │
    └─────────────────────────────────┘
                        │ (speech detected & pause)
                        ▼
    ┌─────────────────────────────────┐
    │  TRANSLATING                    │
    │  - Running Whisper (STT)        │
    │  - Detecting language           │
    │  - Running Ollama (translation) │
    │  - Streaming translation_delta  │
    │  - Pill: Purple                 │
    └─────────────────────────────────┘
                        │ (translation done)
                        ▼
    ┌─────────────────────────────────┐
    │  SPEAKING                       │
    │  - Running Piper (TTS)          │
    │  - Playing audio                │
    │  - Pill: Orange                 │
    └─────────────────────────────────┘
                        │ (audio done)
                        ▼
    ┌─────────────────────────────────┐
    │  READY (back to waiting)        │
    │  - Loop for next utterance      │
    │  - Pill: Green                  │
    └─────────────────────────────────┘
                        │
            ┌───────────┴───────────┐
            │ (click mic again)    │ (click OFF)
            ▼                      ▼
         LISTENING                IDLE
                                (reset)
```

## OFF Button → Restart Flow (NEW)

```
Normal Session Flow:
┌─────────────────────────────────────────────────────────┐
│ READY (listening)                                       │
│ ✓ Connected to server                                   │
│ ✓ serverReadyGate = true                               │
│ ✓ sessionWanted = true                                 │
└─────────────────────────────────────────────────────────┘
                        │ (User clicks OFF button)
                        ▼
┌─────────────────────────────────────────────────────────┐
│ OFF Button Handler Executes:                            │
│ 1. sessionWanted = false      (stop auto-reconnect)     │
│ 2. killMic()                  (stop listening)          │
│ 3. killPlayback()             (stop audio)              │
│ 4. ws.close()                 (close WebSocket)         │
│ 5. clearTimeout(reconnTimer)  (clear pending reconnect) │
│ 6. serverReadyGate = false    (lock gate)              │
│ 7. reconnIdx = 0              (reset backoff) ← NEW     │
│ 8. transition(S.IDLE)         (change state)           │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ IDLE (manual stop)                                      │
│ ✗ Not connected                                         │
│ ✗ serverReadyGate = false                              │
│ ✗ sessionWanted = false                                │
│ ✗ Mic button disabled                                  │
│ 📍 Pill: Gray                                           │
└─────────────────────────────────────────────────────────┘
                        │ (User clicks mic button - FIRST CLICK)
                        ▼
┌─────────────────────────────────────────────────────────┐
│ userStart() Function - IDLE Detection (NEW):            │
│ 1. Detect: state === S.IDLE ✓                          │
│ 2. Call wsConnect()           (initiate reconnect)      │
│ 3. sessionWanted = true       (enable auto-reconnect)   │
│ 4. return                      (DON'T start mic yet)     │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ wsConnect() Function:                                   │
│ 1. Check server health (/health endpoint)              │
│ 2. If OK: call wsConnectNow()                          │
│ 3. transition(S.CONNECTING)   (change state)           │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ CONNECTING                                              │
│ 📍 Pill: Yellow (transitional)                          │
│ ⏱️  Duration: 1-3 seconds                               │
└─────────────────────────────────────────────────────────┘
                        │ (WebSocket opens)
                        ▼
┌─────────────────────────────────────────────────────────┐
│ wsConnectNow() onopen Handler:                          │
│ 1. initSession()              (send initial message)    │
│ 2. serverReadyGate = true     (open gate) ← KEY        │
│ 3. transition(S.READY)        (change state)           │
│ 4. startClientKeepalive()     (start health checks)    │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ READY (reconnected)                                     │
│ ✓ Connected to server                                   │
│ ✓ serverReadyGate = true                               │
│ ✓ sessionWanted = true                                 │
│ 📍 Pill: Green                                          │
└─────────────────────────────────────────────────────────┘
                        │ (User clicks mic button - SECOND CLICK)
                        ▼
┌─────────────────────────────────────────────────────────┐
│ userStart() Function - READY Handling:                  │
│ 1. Detect: state === S.READY ✓                         │
│ 2. Detect: serverReadyGate === true ✓                  │
│ 3. startMic()                 (begin audio capture)     │
│ 4. transition(S.LISTENING)    (change state)           │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ LISTENING (back to normal)                              │
│ 🎙️  Audio streaming                                     │
│ 📍 Pill: Blue                                           │
└─────────────────────────────────────────────────────────┘
                        │
        ┌───────────────┴────────────────┐
        │                                │ (click OFF again)
        ▼                                ▼
   TRANSLATING                      (restart cycle)
        │
        ▼
   SPEAKING
        │
        ▼
     READY
   (loop continues)
```

## Critical Gate: serverReadyGate

```
Timeline:
─────────────────────────────────────────────────────────

Page Load:
  serverReadyGate = false  ← Blocks mic until server ready

wsConnect() Called:
  Health check starts
  │
  ├─ Server responds: continue
  │
  └─ Server error: transition to OFFLINE, retry

WebSocket Opens (onopen):
  serverReadyGate = true   ← Gate opens!
  🔓 Mic now enabled

Click Mic:
  Check: serverReadyGate === true? → Yes ✓
  Call: startMic()

OFF Button:
  serverReadyGate = false  ← Gate closes
  🔒 Mic disabled

Restart (OFF → Click Mic → wsConnect):
  serverReadyGate = false  ← Still closed
  wsConnect() called
  → WebSocket opens
  → serverReadyGate = true ← Gate opens
  → Ready for second click
```

## State Transition Validation Table

| From | To | Allowed? | Triggers |
|------|----|----|----------|
| IDLE | CONNECTING | ✓ | wsConnect() call |
| IDLE | OFFLINE | ✓ | Network error |
| CONNECTING | READY | ✓ | WebSocket opens |
| CONNECTING | OFFLINE | ✓ | Health check fails |
| CONNECTING | FAILED | ✓ | WebSocket error |
| READY | LISTENING | ✓ | Click mic |
| READY | IDLE | ✓ | Click OFF |
| READY | OFFLINE | ✓ | Connection lost |
| READY | FAILED | ✓ | Connection error |
| LISTENING | TRANSLATING | ✓ | Speech detected |
| LISTENING | READY | ✓ | Timeout |
| LISTENING | OFFLINE | ✓ | Connection lost |
| TRANSLATING | SPEAKING | ✓ | Translation done |
| TRANSLATING | READY | ✓ | Error/timeout |
| SPEAKING | READY | ✓ | Audio playback done |
| OFFLINE | CONNECTING | ✓ | Auto-reconnect |
| OFFLINE | IDLE | ✓ | User action |
| FAILED | CONNECTING | ✓ | Auto-reconnect |
| FAILED | IDLE | ✓ | User action |

**Any other transition:** ❌ BLOCKED (invalid state change error)

## Key Timing Points

```
Cold Start (First Session):
────────────────────────────────────
Page load                         0.0s
→ wsConnect()                     0.1s
→ Health check request            0.2s
→ Server responds                 0.5s (models loading)
→ WebSocket established           1.0s
→ serverReadyGate = true          1.0s
→ Pill: READY                     1.0s
→ Ready for first mic click       1.0s

Click Mic (Cold):
────────────────────────────────────
User speaks                       2.0s (duration)
→ Pause detected                  2.7s
→ VAD→STT→LLM→TTS                30-60s (model inference)
→ Audio playback                  variable
→ Back to READY                   35-65s total (first utterance)

Warm Session (Subsequent Utterances):
────────────────────────────────────
Previous audio done               0.0s
→ Ready for next click            0.0s
→ User speaks                     2.0s
→ Pause detected                  2.7s
→ VAD→STT→LLM→TTS                2-3s (models warm)
→ Audio playback                  variable
→ Back to READY                   5-10s total

OFF → Restart:
────────────────────────────────────
Click OFF                         0.0s
→ Pill: IDLE                      0.1s
→ sessionWanted = false           0.1s
→ reconnIdx = 0                   0.1s
Click mic (first click)           0.0s
→ wsConnect() call                0.1s
→ Health check                    0.2s-0.5s
→ WebSocket open                  0.5-1.0s
→ Pill: READY                     1.0s
→ serverReadyGate = true          1.0s
Click mic (second click)          0.0s
→ Pill: LISTENING                 0.1s
→ Ready for speech                0.1s
```

## Error Paths

```
Connection Lost (READY or LISTENING):
────────────────────────────────────
WebSocket closed (unintended)
  → Pong timeout detection
  → transition(S.OFFLINE)
  → scheduleReconnect() (if sessionWanted=true)
  → exponential backoff with reconnIdx
  → retry after 2^reconnIdx * base_delay

Recovery (if sessionWanted=true):
  → wsConnect() called automatically
  → OFFLINE → CONNECTING
  → Health check
  → WebSocket reconnect
  → CONNECTING → READY
  → Resume listening (if was in LISTENING state)

Manual OFF:
  → sessionWanted = false
  → WebSocket closes
  → reconnIdx = 0
  → transition(S.IDLE)
  → NO auto-reconnect
  → User must click mic to restart

Health Check Fails:
  → Server not ready (models loading, memory issues, etc.)
  → transition(S.OFFLINE)
  → If sessionWanted: retry after delay
  → If manual OFF: stay IDLE
```

---

**This diagram shows:**
1. ✅ Complete state machine with all transitions
2. ✅ OFF button flow (old broken behavior)
3. ✅ New restart flow (FIX #12 + #13)
4. ✅ Critical gates and timing
5. ✅ Error recovery paths

**Key insight:** The IDLE state detection (Fix #13) bridges the gap between OFF (READY→IDLE) and restart (IDLE→CONNECTING) by detecting when state is IDLE and calling wsConnect() to reconnect before attempting to start the mic.
