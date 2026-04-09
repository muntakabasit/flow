# 🚀 QUICK START: Test TASK 2 VAD Implementation

**Status**: ✅ COMPLETE & DEPLOYED
**Time to Test**: ~10 minutes
**Required**: Browser + microphone + quiet environment

---

## ⚡ Ultra-Quick Start (3 steps)

### Step 1: Hard Refresh Browser
```
Chrome:  Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
Safari:  Cmd+Shift+R (Mac)
Firefox: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
```

### Step 2: Wait for Ready State
- Open: `http://localhost:8765`
- Wait 3-5 seconds for health check
- **Expected**: Green dot appears with "READY" label

### Step 3: Click VAD Button & Test
- Click "VAD" button (bottom-right corner)
- **Expected**: Settings modal appears
- Adjust sliders → values update
- Click "Save & Close"
- Speak normally → verify translation works

---

## 📋 Full Test Checklist

### Test A: Settings UI Works
**Time**: 2 minutes

```
□ Click "VAD" button in toolbar
  Expected: Modal dialog appears with backdrop

□ Sensitivity slider visible
  Expected: Shows "50%" by default

□ End-of-Speech Delay slider visible
  Expected: Shows "650ms" by default

□ Drag Sensitivity slider left
  Expected: Value decreases to 0-20%

□ Drag Sensitivity slider right
  Expected: Value increases to 80-100%

□ Drag Delay slider left
  Expected: Value decreases to 300ms

□ Drag Delay slider right
  Expected: Value increases to 2000ms

□ Click "Save & Close"
  Expected: Modal closes, app returns to normal

□ Click "X" button (without saving)
  Expected: Modal closes, previous values unchanged

□ Click outside modal (backdrop)
  Expected: Modal closes, previous values unchanged
```

### Test B: Sensitivity Detection (Default 50%)
**Time**: 3 minutes

```
NORMAL SPEECH:
□ Speak clearly: "Hello world, how are you"
  Expected: Speech detected immediately
  Expected: "VAD: Speech detected" in diagnostics
  Expected: Audio sent to server
  Expected: Translation appears

BACKGROUND NOISE (no speech):
□ Don't speak, make quiet background noise (shuffle papers)
□ Wait 10 seconds
□ Open diagnostics
  Expected: NO "VAD: Speech detected" messages
  Expected: NO translations
  Expected: NO audio being sent

QUIET WHISPER:
□ Whisper very softly: "can you hear me"
  Expected: Speech NOT detected (sensitivity at 50%)
  Expected: NO translation
```

### Test C: Adjust Sensitivity (More Sensitive)
**Time**: 2 minutes

```
MAKE APP MORE SENSITIVE (to detect whispers):

□ Click VAD button
□ Set Sensitivity to 20%
□ Click Save & Close
□ Whisper softly: "testing whisper detection"
  Expected: Speech detected
  Expected: "VAD: Speech detected" in log
  Expected: Translation appears

□ Make quiet background noise (don't speak)
□ Wait 5 seconds
  Expected: No false positives (still robust)
  Expected: No translations from background noise
```

### Test D: Adjust Sensitivity (Less Sensitive)
**Time**: 2 minutes

```
MAKE APP LESS SENSITIVE (to ignore noise):

□ Click VAD button
□ Set Sensitivity to 80%
□ Click Save & Close
□ Speak LOUDLY: "TESTING LOUD SPEECH"
  Expected: Speech detected
  Expected: Translation appears

□ Make rustling sounds (don't speak)
□ Wait 5 seconds
  Expected: No detection (good noise rejection)
  Expected: No false translations
```

### Test E: Adjust End-of-Speech Delay
**Time**: 2 minutes

```
QUICK FINALIZATION (300ms):

□ Click VAD button
□ Set End-of-Speech Delay to 300ms
□ Click Save & Close
□ Speak: "First test" (then STOP and be silent)
□ Time how long until translation appears
  Expected: ~300-400ms after you stop speaking

SLOW FINALIZATION (1500ms):

□ Click VAD button
□ Set End-of-Speech Delay to 1500ms
□ Click Save & Close
□ Speak: "Second test" (then STOP and be silent)
□ Time how long until translation appears
  Expected: ~1500-1600ms after you stop speaking
```

### Test F: Micro-Pause Protection
**Time**: 2 minutes

```
NATURAL PAUSES IN SPEECH:

□ Set End-of-Speech Delay to 650ms (default)
□ Speak: "I like to travel, (small pause), to different countries"
   - Do NOT move or breathe during the pause
   - Continue speaking after 2-3 seconds
□ Check final translation
  Expected: Entire sentence captured
  Expected: NO early finalization during pause
  Expected: NOT split into two translations
```

### Test G: Settings Persistence
**Time**: 1 minute

```
SETTINGS SURVIVE PAGE REFRESH:

□ Click VAD button
□ Set Sensitivity to 75%
□ Set End-of-Speech Delay to 900ms
□ Click Save & Close
□ Refresh page (Cmd+R)
□ Wait for app to load (green dot)
□ Click VAD button again
  Expected: Sensitivity shows 75%
  Expected: Delay shows 900ms

SETTINGS SURVIVE BROWSER CLOSE:

□ Close entire browser
□ Reopen browser
□ Navigate to http://localhost:8765
□ Wait for app load
□ Click VAD button
  Expected: Settings still at 75% and 900ms
```

---

## 📊 Expected Behavior

### ✅ Speech Detection
- RMS threshold calculated: `0.004 + (sensitivity * 0.011)`
- At 50% sensitivity: threshold = 0.0095
- At 0% sensitivity: threshold = 0.004 (very sensitive)
- At 100% sensitivity: threshold = 0.015 (not sensitive)

### ✅ Finalization
- After RMS drops below stop threshold (70% of start threshold)
- Wait for configured `endDelayMs` of continuous silence
- Send `end_of_speech` message to server
- Server transcribes and translates the audio

### ✅ No False Positives
- Background noise RMS typically 0.001-0.003 (below 0.004 threshold)
- Ambient sound (HVAC, traffic) rarely exceeds threshold
- Only speech with 0.005+ RMS detected

---

## 🐛 Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| Still shows OFFLINE | Cached old HTML | Hard refresh: Cmd+Shift+R |
| VAD button doesn't exist | Outdated page | Hard refresh browser |
| Settings modal doesn't open | JavaScript error | Check F12 console for errors |
| Sliders don't respond | Event listener failed | Refresh page, check console |
| Detects everything as speech | Sensitivity too high | Increase slider (right) to 70-80% |
| Misses quiet speech | Sensitivity too low | Decrease slider (left) to 20-30% |
| Cuts off mid-sentence | Delay too short | Increase slider to 800-1000ms |
| Waits too long after speech | Delay too long | Decrease slider to 300-400ms |

---

## 🔍 Diagnostics Panel

Click "DIAG" button (bottom-right) to see:

```
[12:34:56] Flow client loaded
[12:34:57] Checking server health...
[12:34:58] Server ready, connecting WebSocket...
[12:34:58] IDLE → CONNECTING
[12:34:58] CONNECTING → READY
[12:35:00] VAD: Speech detected (RMS: 0.0156)
[12:35:00] READY → LISTENING
[12:35:02] LISTENING → TRANSLATING
[12:35:03] (translation result)
[12:35:03] TRANSLATING → SPEAKING
[12:35:04] VAD: Silence 651ms (RMS: 0.0032)
[12:35:04] SPEAKING → READY
```

---

## ✅ Success Criteria

**You'll know it's working if:**

- ✅ App shows green dot (READY state)
- ✅ VAD button visible and clickable
- ✅ Settings modal opens/closes smoothly
- ✅ Sliders move and update values
- ✅ Normal speech detected and translated
- ✅ Background noise doesn't cause false positives
- ✅ Settings persist after page refresh
- ✅ Diagnostics show VAD events (speech_start, silence_XXXms)

**If ALL of above work → TASK 2 is complete and functioning correctly ✅**

---

## 🎯 What This Proves

✅ **RMS-based VAD works** - Correctly detects speech vs silence
✅ **Hysteresis prevents flickering** - Two thresholds stabilize detection
✅ **Silence timer accurate** - Finalization happens at configured delay
✅ **Sensitivity is adjustable** - User can tune for their environment
✅ **Settings persist** - localStorage successfully stores preferences
✅ **No spam on noise** - Robustly ignores background noise
✅ **Micro-pauses protected** - Natural speech patterns not interrupted

---

**Ready to test? Start with the Ultra-Quick Start at the top of this document!**

