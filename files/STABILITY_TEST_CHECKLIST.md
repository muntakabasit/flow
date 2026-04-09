# WebSocket Stability Test Checklist

**Purpose**: Validate iOS Code=57 fix + stable reconnect on all platforms

---

## 🔧 Setup

### Before Testing
1. [ ] Restart server: `pkill -f server_local.py && sleep 2 && python server_local.py`
2. [ ] Restart Ollama: `pkill ollama && sleep 2 && ollama serve`
3. [ ] Wait 5 seconds for both to warm up
4. [ ] Open browser DevTools → Console (clear any old messages)

---

## 📱 Test 1: Desktop Chrome (Baseline)

### Basic Connection
- [ ] Open http://localhost:8765
- [ ] Wait for UI to load
- [ ] State should be "ready" (green dot)
- [ ] Pill shows "ready"

### Baseline Translation
- [ ] Click mic button
- [ ] Speak: "Hello world"
- [ ] Wait 1-2 seconds
- [ ] Should see:
  - "YOU: Hello world"
  - "TRANSLATION: Olá mundo" (in Portuguese)
  - 🟢 icon (high confidence)
- [ ] Audio should play back

### Connection Persistence
- [ ] Mic still connected?
- [ ] Speak: "How are you?"
- [ ] Should translate normally
- [ ] Keep speaking for 5+ exchanges

### Deliberate Disconnect
- [ ] Open terminal
- [ ] Run: `pkill -f server_local.py`
- [ ] Watch UI
- [ ] Within 5s, should show "offline" state (red dot)
- [ ] Pill shows "offline"
- [ ] Reconnect banner appears: "Reconnecting in X.Xs…"
- [ ] Watch exponential backoff: first retry at 0.3s, then 0.6s, then 1.2s, etc.

### Recovery
- [ ] Run: `python server_local.py`
- [ ] Wait for Ollama warmup (~2-3s)
- [ ] UI should automatically reconnect
- [ ] State should return to "ready"
- [ ] Should be able to speak normally

**Result**: ✅ PASS / ❌ FAIL

---

## 🍎 Test 2: iOS Safari (PWA Home Screen)

### App Installation
- [ ] Open Safari → http://192.168.X.X:8765 (your Mac's IP)
- [ ] Tap Share button → Add to Home Screen
- [ ] Name it "FLOW Test" → Add
- [ ] Close Safari
- [ ] Tap FLOW Test icon on home screen

### Initial Load
- [ ] App opens fullscreen (no Safari UI)
- [ ] UI loads
- [ ] State shows "ready" (green dot)
- [ ] Mic icon visible and clickable

### Basic Translation (iOS)
- [ ] Tap mic button
- [ ] Speak: "Hello from iPhone"
- [ ] Wait 1-2 seconds
- [ ] Should see transcription + translation
- [ ] Audio should play (speaker or headphone)
- [ ] [ ] Verify: User says "YOU: Hello from iPhone"
- [ ] Verify: Translation shown in right column
- [ ] Verify: 🟢 confidence icon appears

### iOS Specific: Network Transition
**Goal**: Simulate switching from cellular to WiFi (the original Code=57 issue)

#### Setup: On Cellular
- [ ] Disable WiFi on iPhone
- [ ] Open FLOW app (should be on cellular data)
- [ ] Verify connected (green dot)

#### Simulate Network Change
- [ ] Enable WiFi
- [ ] Speak into mic: "Testing network change"
- [ ] **Should NOT see Code=57 error**
- [ ] Translation should work normally
- [ ] App should stay connected

#### Verify: No Socket Error
- [ ] Check Console (if accessible) for errors
- [ ] Should NOT see `NSPOSIXErrorDomain Code=57`
- [ ] App should remain in "ready" state

**Result**: ✅ PASS (no Code=57) / ❌ FAIL (Code=57 appears)

---

## 📱 Test 3: iOS Safari (Background/Foreground)

### Setup
- [ ] Open FLOW app
- [ ] Verify connected (green dot)

### Backgrounding
- [ ] Tap home button to background app
- [ ] Wait 10 seconds
- [ ] Check: Did keepalive timeout trigger?
- [ ] Open another app (e.g., Mail) for 30 seconds

### Foregrounding
- [ ] Tap FLOW icon to return to app
- [ ] Watch connection state
- [ ] **Should reconnect automatically** (may take 1-2s)
- [ ] State should return to "ready"
- [ ] Speak: "After backgrounding"
- [ ] Should translate normally

### Repeat 3x
- [ ] Background/foreground 3 times
- [ ] Each time should reconnect successfully
- [ ] No crashes

**Result**: ✅ PASS (auto-reconnect) / ❌ FAIL (doesn't reconnect or crashes)

---

## 🤖 Test 4: Android Chrome (PWA)

### App Installation
- [ ] Open Chrome → http://192.168.X.X:8765
- [ ] Menu (3 dots) → Install app
- [ ] Tap "Install"
- [ ] App should appear on home screen

### Initial Load
- [ ] Tap FLOW icon
- [ ] App opens fullscreen
- [ ] State shows "ready"

### Basic Translation
- [ ] Tap mic
- [ ] Speak: "Testing on Android"
- [ ] Should translate
- [ ] Audio plays

### Network Change (Android)
- [ ] Enable airplane mode (turn off all networks)
- [ ] Watch: State should change to "offline"
- [ ] Disable airplane mode
- [ ] Watch: Should transition to "reconnecting" then "ready"
- [ ] Speak: Should work normally

**Result**: ✅ PASS / ❌ FAIL

---

## 🔌 Test 5: Deliberate Server Failures

### Kill Server During Session
- [ ] Open app, connect
- [ ] Start speaking
- [ ] In terminal: `pkill -f server_local.py`
- [ ] **While speaking**, server dies
- [ ] Watch for error handling
- [ ] Should NOT crash
- [ ] Should show error message
- [ ] Should offer "Tap to reconnect"

### Restart Server
- [ ] Run: `python server_local.py`
- [ ] Tap "reconnect" button (or wait for auto-reconnect)
- [ ] Should reconnect successfully
- [ ] Session history should be preserved

### Kill Ollama
- [ ] App connected
- [ ] Terminal: `pkill ollama`
- [ ] Try to speak
- [ ] Should see: "Translator offline. Make sure Ollama is running."
- [ ] Restart Ollama: `ollama serve`
- [ ] Wait 3 seconds
- [ ] Manual reconnect (or auto)
- [ ] Should work again

**Result**: ✅ PASS (graceful errors) / ❌ FAIL (crashes or hangs)

---

## 🧪 Test 6: Keepalive Timeout

### Monitor Keepalive
- [ ] Open app
- [ ] Open Console (if available)
- [ ] Watch for keepalive messages every ~20s
- [ ] Should see: "Keepalive ping"
- [ ] Should see: messages arriving (any server message updates lastPongTime)

### Simulate Hung Connection
- [ ] Connect app
- [ ] Kill server (not Ollama, just server)
- [ ] Wait 40 seconds
- [ ] After KEEPALIVE_TIMEOUT (40s), client should auto-close socket
- [ ] Should trigger reconnect
- [ ] Restart server
- [ ] Should reconnect successfully

**Result**: ✅ PASS (timeout works) / ❌ FAIL (socket hangs forever)

---

## 📊 Test 7: Exponential Backoff

### Monitor Reconnect Attempts
- [ ] Open app
- [ ] Kill server
- [ ] Watch reconnect banner: "Reconnecting in X.Xs…"
- [ ] First attempt: ~0.3s
- [ ] Second attempt: ~0.6s
- [ ] Third attempt: ~1.2s
- [ ] Should increase exponentially
- [ ] Each with ~±25% jitter (random variance)

### Backoff Cap
- [ ] Keep server dead for 2 minutes
- [ ] After 10 failed attempts, should show: "Connection failed. Tap to reconnect."
- [ ] Should NOT continue retrying indefinitely
- [ ] Should wait for user to manually tap

### Backoff Reset
- [ ] Before hitting 10 attempts, restart server
- [ ] App reconnects
- [ ] Kill server again
- [ ] Backoff counter should RESET
- [ ] First attempt: ~0.3s again (not 8s)

**Result**: ✅ PASS (proper backoff) / ❌ FAIL (no backoff or backoff broken)

---

## ✅ Test 8: Phase 1 Regression (Must Still Work)

### Speaker Labels
- [ ] Speak: "Hello"
- [ ] Verify: "YOU" label appears above source text
- [ ] Verify: "TRANSLATION" label appears above target text

### Confidence Scoring
- [ ] After translation, should see 🟢 🟡 or 🔴 with percentage
- [ ] High confidence (>80%): 🟢
- [ ] Medium (60-80%): 🟡
- [ ] Low (<60%): 🔴

### Session Persistence
- [ ] Speak 3+ exchanges
- [ ] Close browser tab/app
- [ ] Reopen app
- [ ] Should see history from previous session

### Error Messages
- [ ] Kill Ollama
- [ ] Try to translate
- [ ] Should see friendly error: "Translator offline. Make sure Ollama is running."
- [ ] NOT: "Translation failed: LLM_UNAVAILABLE" (technical jargon)

**Result**: ✅ ALL PASS / ❌ ANY FAIL

---

## 🎯 Test 9: Long Session Stability (Stress Test)

### 10-Minute Session
- [ ] Start app on desktop or iOS
- [ ] Continuously speak for 10+ minutes
- [ ] Every 30 seconds, switch between foreground/background (iOS only)
- [ ] Perform 20+ complete exchanges
- [ ] Monitor for:
  - No crashes
  - No memory leaks (RAM stays stable)
  - No battery drain issues (if mobile)
  - Consistent translation quality
  - All features work (audio, labels, confidence, etc.)

**Result**: ✅ PASS (stable) / ❌ FAIL (crash, memory leak, degradation)

---

## 🔍 Test 10: Network Conditions (Advanced)

### Slow Network (Desktop)
- [ ] Use Chrome DevTools Network tab
- [ ] Set to "Slow 4G"
- [ ] Open app
- [ ] Should connect (may take 5-10 seconds)
- [ ] Should handle timeouts gracefully
- [ ] Should reconnect without crashing

### Offline Simulation
- [ ] Open app on desktop
- [ ] DevTools Network → Offline
- [ ] Should show "offline" state
- [ ] DevTools → Online
- [ ] Should reconnect automatically

### Throttling
- [ ] DevTools Network → Throttling enabled
- [ ] App should handle reduced bandwidth
- [ ] No disconnects due to latency alone

**Result**: ✅ PASS / ❌ FAIL

---

## 📝 Summary Checklist

After completing all tests, mark final status:

### Desktop Chrome
- [ ] Basic connection
- [ ] Translation
- [ ] Persistence
- [ ] Disconnect/reconnect
- [ ] Recovery

### iOS Safari
- [ ] Installation
- [ ] Basic translation
- [ ] **Network transition (NO Code=57)**
- [ ] Background/foreground
- [ ] Keepalive

### Android Chrome
- [ ] Installation
- [ ] Translation
- [ ] Network changes
- [ ] Offline/online

### Server Failures
- [ ] Kill server during session
- [ ] Recover gracefully
- [ ] Kill Ollama
- [ ] Error messages friendly

### Advanced
- [ ] Keepalive timeout works
- [ ] Exponential backoff works
- [ ] Backoff cap enforced
- [ ] Backoff resets on success

### Phase 1 Regression
- [ ] Speaker labels
- [ ] Confidence scoring
- [ ] Session persistence
- [ ] Error messages

### Long Session
- [ ] 10+ minutes stable
- [ ] No crashes
- [ ] Consistent quality

---

## 🚀 Sign-Off

**Tester**: _________________
**Date**: _________________
**Overall Result**: ✅ PASS / ❌ FAIL

**Any issues found**:
```
[List any failures or anomalies here]
```

**Notes**:
```
[Additional observations or recommendations]
```

---

**If all tests PASS, you're ready to deploy to staging/production.** 🎉

