# FLOW PREMIUM — Comprehensive Rebuild Plan

## Overview
This document outlines the complete rebuild to create a premium, smooth bilingual interpreter experience.

## Architecture Changes

### Current State
- ✅ VAD exists but is informational only
- ✅ Server auto-detects language
- ✅ WebSocket connected
- ❌ No client-side endpointing (server decides when to finalize)
- ❌ No language selection UI
- ❌ No premium waveform visuals
- ❌ No "hold to talk" mode
- ❌ No barge-in capability

### Target State
- ✅ Client-side VAD controls turn-taking (SMOOTH)
- ✅ Language preference controls
- ✅ Premium waveform UI with state animations
- ✅ Hold-to-talk vs hands-free modes
- ✅ Barge-in (interrupt TTS)
- ✅ Improved state machine

## PART A — TURN-TAKING: Client-Side VAD Endpointing

### Change 1: Enhance VAD object with finalization logic

**File**: `static/index.html` (VAD object, around line 540-614)

Add to VAD object:
- `finalizeThreshold`: How long silence before sending finalize message (default 650ms)
- `detectFinal()`: Returns true when utterance is complete
- Add hysteresis for language confidence

### Change 2: Modify audio processor to finalize utterances

**File**: `static/index.html` (processor.onaudioprocess, around line 1043-1086)

Current: Always sends audio, server decides endpointing
New:
- Track `isFinalizing` state per utterance
- When VAD detects silence >= threshold: send `{type: 'finalize_utterance'}` message
- Only then transition to TRANSLATING state
- Don't send more audio during finalization

### Change 3: Handle finalization on WebSocket

**File**: `static/index.html` (ws.onmessage handler, around line 1206)

Add message handler:
- `type: 'utterance_finalized'` → transition to TRANSLATING
- Include detected language confidence in response
- Server sends back language pair for this turn

## PART B — LANGUAGE CONTROLS

### Change 4: Add language preference state

**File**: `static/index.html` (global state, around line 600)

Add:
```javascript
let sourceLanguage = 'en';  // 'en' or 'pt-BR'
let targetLanguage = 'pt-BR'; // 'en' or 'pt-BR'
let languageDetectionConfidence = 0;
```

### Change 5: Add language UI controls

**File**: `static/index.html` (HTML structure, find header/controls area around line 400-500)

Add to settings/controls:
```html
<div class="language-controls">
  <div class="language-pair">
    <select id="sourceLang">
      <option value="en">I speak English</option>
      <option value="pt-BR">Falo Português</option>
    </select>

    <button id="swapLangs" class="swap-button">↔</button>

    <select id="targetLang">
      <option value="pt-BR">Traduzir para Português</option>
      <option value="en">Translate to English</option>
    </select>
  </div>
  <div class="confidence-display" id="langConfidence"></div>
</div>
```

### Change 6: Send language preferences to server

**File**: `static/index.html` (initSession or new function)

When WebSocket opens or when language changed:
```javascript
ws.send(JSON.stringify({
  type: 'set_languages',
  source: sourceLanguage,
  target: targetLanguage
}));
```

## PART C — PREMIUM WAVEFORM UI

### Change 7: Replace simple waveform with animated orb

**File**: `static/index.html` (CSS, around line 14-400)

Replace `.wave` styles with:
```css
.voice-orb {
  width: 160px;
  height: 160px;
  border-radius: 50%;
  margin: 0 auto 20px;
  position: relative;
  transition: all 0.3s ease;
}

.voice-orb.idle {
  background: radial-gradient(circle, rgba(100,120,200,0.1) 0%, transparent 70%);
  box-shadow: 0 0 40px rgba(100,120,200,0.1);
}

.voice-orb.listening {
  background: radial-gradient(circle, rgba(100,200,150,0.3) 0%, transparent 70%);
  box-shadow: 0 0 60px rgba(100,200,150,0.4), inset 0 0 40px rgba(100,200,150,0.1);
}

.voice-orb.translating {
  background: radial-gradient(circle, rgba(224,168,70,0.3) 0%, transparent 70%);
  animation: shimmer 0.8s ease-in-out infinite;
}

.voice-orb.speaking {
  background: radial-gradient(circle, rgba(100,180,255,0.3) 0%, transparent 70%);
  animation: wave-pulse 0.6s ease-in-out infinite;
}

@keyframes shimmer {
  0%, 100% { opacity: 0.7; }
  50% { opacity: 1; }
}

@keyframes wave-pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}
```

### Change 8: Update waveform visualization

**File**: `static/index.html` (JavaScript, processor.onaudioprocess)

Instead of updating bars, update orb size/glow based on RMS:
```javascript
// Calculate orb scale from RMS (0.0 → 2.0)
const orbScale = 1 + (rmsSmoothed * 1.5); // Min 1.0, max 2.5
const orbGlow = Math.min(rmsSmoothed * 100, 80); // 0-80px
$voiceOrb.style.transform = `scale(${orbScale})`;
$voiceOrb.style.boxShadow = `0 0 ${orbGlow}px rgba(100,200,150,0.4)`;
```

### Change 9: Add state-based animations

When state changes:
- `IDLE`: calm, gray, small glow
- `CONNECTING`: subtle spinner animation
- `READY`: gentle pulse
- `LISTENING`: green glow, responds to RMS
- `TRANSLATING`: amber shimmer
- `SPEAKING`: blue wave animation
- `OFFLINE`: red/disabled

## PART D — IMPROVED STATE MACHINE & RELIABILITY

### Change 10: Tighten state transitions

**File**: `static/index.html` (VALID_TRANSITIONS, around line 712)

Update to:
```javascript
const VALID_TRANSITIONS = {
  [S.IDLE]:        [S.CONNECTING, S.OFFLINE],
  [S.CONNECTING]:  [S.READY, S.OFFLINE, S.FAILED],
  [S.READY]:       [S.LISTENING, S.OFFLINE, S.FAILED, S.IDLE],
  [S.LISTENING]:   [S.TRANSLATING, S.READY, S.OFFLINE, S.FAILED],
  [S.TRANSLATING]: [S.SPEAKING, S.READY, S.OFFLINE, S.FAILED],
  [S.SPEAKING]:    [S.READY, S.OFFLINE, S.FAILED],
  [S.OFFLINE]:     [S.CONNECTING, S.IDLE],
  [S.FAILED]:      [S.CONNECTING, S.IDLE],
};
```

### Change 11: Add mode toggle (hold-to-talk)

**File**: `static/index.html` (global state)

```javascript
let micMode = 'hands-free'; // 'hands-free' or 'hold-to-talk'
```

**File**: `static/index.html` (userStart function)

In hold-to-talk mode, capture button press/release:
- Press: start mic
- Release: finalize immediately (don't wait for silence)

### Change 12: Implement barge-in

**File**: `static/index.html` (startMic function)

Before starting mic:
```javascript
if (state === S.SPEAKING) {
  // Stop TTS immediately
  if (playCtx) playCtx.close();
  playCtx = null;
  diagLog('Barge-in: stopping TTS', 'info');
}
```

### Change 13: Better reconnection

**File**: `static/index.html` (wsConnect/scheduleReconnect)

Add exponential backoff visualization:
```javascript
const backoffMs = BACKOFF[reconnIdx] || BACKOFF[BACKOFF.length - 1];
diagLog(`Reconnecting in ${backoffMs}ms... (attempt ${reconnIdx + 1})`, 'info');
```

## PART E — TRANSCRIPT & UX IMPROVEMENTS

### Change 14: Enhanced transcript bubbles

**File**: `static/index.html` (saveExchange function, around line 960)

Add to exchange:
- `timestamp`: Date.now()
- `confidence`: language detection confidence
- `sourceLanguage`: detected language
- `targetLanguage`: target language for this turn

Update bubble HTML:
```html
<div class="t-row">
  <div class="t-bubble source">
    <div class="bubble-label">YOU</div>
    <div class="bubble-text">${source}</div>
    <div class="bubble-meta">
      <span class="time">${time}</span>
      <span class="lang">${sourceLang}</span>
    </div>
  </div>
  <div class="t-bubble target">
    <div class="bubble-label">TRANSLATION</div>
    <div class="bubble-text">${target}</div>
    <div class="bubble-meta">
      <span class="time">${targetLang}</span>
    </div>
  </div>
</div>
```

### Change 15: Auto-scroll logic

**File**: `static/index.html` (scrollTranscript function)

Add pause-on-user-scroll:
```javascript
function scrollTranscript() {
  if (autoScroll && !userScrolledUp) {
    $transcript.scrollTop = $transcript.scrollHeight;
  }
}

$transcript.addEventListener('wheel', () => {
  const atBottom = Math.abs($transcript.scrollTop - ($transcript.scrollHeight - $transcript.clientHeight)) < 50;
  userScrolledUp = !atBottom;
});
```

## Implementation Order

1. **First**: VAD endpointing (PART A)
   - Modify audio processor
   - Add finalize logic
   - Test turn-taking smoothness

2. **Second**: Language controls (PART B)
   - Add state variables
   - Add UI controls
   - Send to server

3. **Third**: Waveform UI (PART C)
   - Replace visualization
   - Add state animations
   - Polish transitions

4. **Fourth**: State machine & reliability (PART D)
   - Tighten transitions
   - Add modes (hold-to-talk, barge-in)
   - Improve reconnection messaging

5. **Fifth**: Transcript & UX (PART E)
   - Better bubbles
   - Better auto-scroll
   - Confidence/timestamp display

## Testing Checklist

- [ ] **Turn-taking**: Speak, pause, speak again - should finalize correctly
- [ ] **Language selection**: Change source/target languages before speaking
- [ ] **Swap button**: ↔ should swap source/target
- [ ] **Waveform**: Orb should respond smoothly to voice level
- [ ] **State animations**: Visual feedback for each state
- [ ] **Hold-to-talk**: Release button should finalize immediately
- [ ] **Barge-in**: Start speaking during TTS - should stop immediately
- [ ] **Reconnection**: Lose WiFi and regain - should reconnect with feedback
- [ ] **Transcript**: Bubbles show source, target, timestamp, language
- [ ] **Auto-scroll**: Pause when user scrolls up, resume when at bottom
- [ ] **Mobile**: Haptics work, waveform smooth at 60fps
- [ ] **Offline**: Red orb, clear "reconnect" message

## Files to Modify

1. `static/index.html` - Main UI and client logic
2. `server_local.py` - Add language preference handling (minimal)

## Estimated Changes

- **HTML**: ~200 lines added/modified (VAD logic, UI, controls, animations)
- **CSS**: ~100 lines added (orb styling, animations, state classes)
- **JavaScript**: ~400 lines added/modified (finalization, language, modes)
- **Server**: ~50 lines added (language preference message handling)

**Total**: ~750 lines of changes in a minimal, surgical fashion

---

This plan maintains the existing architecture while adding premium features systematically.

