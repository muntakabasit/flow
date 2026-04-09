# ✅ FLOW RELIABILITY PATCH — DEPLOYMENT CHECKLIST

**Status**: Ready to Deploy
**Estimated Time**: 2 minutes setup + 75 minutes testing
**Risk Level**: LOW

---

## 📋 Pre-Deployment (Do Before Starting Server)

- [ ] Read QUICK_REFERENCE.md (5 minutes)
- [ ] Verify Python 3 installed: `python3 --version`
- [ ] Verify Ollama running: `curl http://localhost:11434/api/tags`
- [ ] Verify Whisper models downloaded: `ls models/` should exist
- [ ] Close any existing server: `pkill -f server_local.py || true`

---

## 🚀 Deployment (2 Minutes)

### Step 1: Start Server
```bash
cd /Users/kulturestudios/BelawuOS/flow
python3 server_local.py
```

**Expected Output**:
```
[flow-local] Loading Whisper model...
[flow-local] Whisper 'base' loaded
[flow-local] Loading Piper voices...
[flow-local] Piper voices loaded (EN=22050Hz, PT=22050Hz)
[flow-local] Loading Silero VAD...
[flow-local] Silero VAD at: /path/to/silero_vad_v6.onnx
[flow-local] FastAPI app ready at http://localhost:8765
[flow-local] Warming up Ollama (gemma3:4b)...
[flow-local] Ollama ready
[flow-local] Server ready on http://localhost:8765
[flow-local] Waiting for WebSocket connections...
```

**Wait 10 seconds** for Ollama warmup to complete.

- [ ] Server started successfully
- [ ] No error messages in output
- [ ] Ollama warmup completed

### Step 2: Verify Health Check
```bash
curl http://localhost:8765/health
```

**Expected Response**:
```json
{
  "status": "ok",
  "service": "flow-local-interpreter",
  "time": "..."
}
```

- [ ] Health check returns 200 OK
- [ ] Service status is "ok"

### Step 3: Open Browser
```
http://localhost:8765
```

**Expected Behavior**:
- Page loads
- Green dot appears (READY state)
- Microphone button visible
- No JavaScript errors in console (F12)

- [ ] Page loads without errors
- [ ] Green dot visible (READY state)
- [ ] Mic button responsive

### Step 4: Hard Refresh (Clear Cache)
```
Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
```

- [ ] Page reloads with fresh assets
- [ ] Still in READY state
- [ ] Console clean (no errors)

---

## 🧪 Quick Smoke Test (2 Minutes)

**Goal**: Verify basic functionality works

### Test 1: English Transcription
1. Click microphone button
2. Speak clearly: **"Hello, my name is John"**
3. Release button
4. **Expected**: Portuguese translation appears within 2 seconds

- [ ] Transcript appears
- [ ] Translation appears
- [ ] Audio plays back

### Test 2: Portuguese Transcription
1. Click microphone button
2. Speak clearly: **"Olá, meu nome é Maria"**
3. Release button
4. **Expected**: English translation appears within 2 seconds

- [ ] Transcript appears
- [ ] Translation appears
- [ ] Audio plays back

### Test 3: No Language Switch (Key Test)
1. Speak English: **"How are you"**
2. Speak Portuguese: **"Como você está"**
3. Speak Portuguese: **"Tudo bem?"**
4. **Expected**: Language stays in English for turn 2 (hysteresis pending)
5. Turn 3 should finally switch to Portuguese (3 detections satisfied)

- [ ] Language doesn't flip on first Portuguese utterance
- [ ] Eventually switches after 3 Portuguese detections
- [ ] No flip-flopping

**If all above pass**: ✅ Smoke test successful, proceed to full testing

---

## 📊 Full Test Plan (75 Minutes)

### TEST A: Language Stability (30 minutes)
**File**: See "TEST A" section in DEPLOY_RELIABILITY_PATCH.md

**What It Tests**:
- Language hysteresis (3 consecutive detections)
- Language cooldown (2 turns before re-switch)
- High confidence override (0.95+ can override cooldown)

**Pass Criteria**:
- No language flipping
- Hysteresis counter increments properly
- Cooldown blocks switches appropriately
- Server logs show switch_reason correctly

- [ ] All 8 test cases pass
- [ ] Language stable, no flip-flops

### TEST B: Confidence Gating (10 minutes)
**File**: See "TEST B" section in DEPLOY_RELIABILITY_PATCH.md

**What It Tests**:
- STT confidence < 0.55 skips translation
- Clear speech translates normally
- Varying confidence handled correctly

**Pass Criteria**:
- Whispered speech skipped (if confidence < 0.55)
- Clear speech translated
- Server logs show confidence scores

- [ ] Low confidence utterances skipped
- [ ] High confidence utterances translated

### TEST C: Turn Segmentation (10 minutes)
**File**: See "TEST C" section in DEPLOY_RELIABILITY_PATCH.md

**What It Tests**:
- Short noise (< 700ms) ignored
- Natural speech captured
- Pauses don't interrupt (up to 1300ms)

**Pass Criteria**:
- Clicking/tapping sounds ignored
- Full sentences captured
- Silence thresholds respected

- [ ] Noise fragments ignored
- [ ] Natural speech captured
- [ ] Pauses handled correctly

### TEST D: Network Resilience (15 minutes)
**File**: See "TEST D" section in DEPLOY_RELIABILITY_PATCH.md

**What It Tests**:
- Slow network doesn't timeout (2+ second translations)
- Keepalive timeout adequate (90s in Stable mode)
- Recovery from slowness

**Pass Criteria**:
- No timeout errors on slow network
- Translation eventually appears
- App recovers normally

**Setup Required**:
```
F12 → Network tab → Throttle to "Slow 4G"
```

- [ ] No timeout errors with throttling
- [ ] Translations complete successfully
- [ ] App recovers when throttle removed

### TEST E: 10-Minute Stability Session (10 minutes)
**File**: See "TEST E" section in DEPLOY_RELIABILITY_PATCH.md

**What It Tests**:
- Overall session stability
- No random disconnects
- Language switching under load
- Consistent performance

**Pass Criteria**:
- 10+ turns complete without disconnect
- Language decisions correct
- No JavaScript errors
- WebSocket stays open (1000, not 1006)

**Procedure**:
1. Open DevTools (F12)
2. Open Server terminal
3. Alternate English/Portuguese every 30 seconds
4. Mix in: clear speech, quiet speech, natural pauses
5. Monitor: server logs, browser console, WebSocket status
6. Complete 10+ turns

- [ ] 10+ turns completed
- [ ] No disconnects
- [ ] Language switching correct
- [ ] WebSocket healthy (no 1006 errors)

---

## 📈 Success Criteria

### All Tests Must Pass
- [ ] Smoke test (quick validation): PASS
- [ ] Language stability (A): PASS
- [ ] Confidence gating (B): PASS
- [ ] Turn segmentation (C): PASS
- [ ] Network resilience (D): PASS
- [ ] 10-min stability (E): PASS

### No Errors
- [ ] Server console: No ERROR or CRITICAL logs
- [ ] Browser console: No JavaScript errors
- [ ] WebSocket: No code 1006 (abnormal close)

### Performance
- [ ] STT latency: 100-200ms
- [ ] Translation latency: 800-1500ms
- [ ] TTS latency: 50-200ms
- [ ] Total turn latency: 1000-2000ms

---

## 🎯 Quick Diagnosis

If a test fails, check:

| Symptom | Check | Fix |
|---------|-------|-----|
| Server won't start | `python3 --version`, `pip list` | Install missing packages |
| Health check fails | `curl http://localhost:11434/api/tags` | Start Ollama, run `ollama pull gemma3:4b` |
| Page doesn't load | Clear cache (Cmd+Shift+R) | Browser cache issue |
| Mic doesn't work | Check browser permissions (Settings → Privacy) | Allow microphone access |
| No translation | Check server logs for errors | Look for STT or LLM errors |
| Language keeps switching | Check server logs for confidence scores | Confidence threshold too low? |
| Timeout errors | Check network throttling (F12 → Network) | Remove throttle, test again |
| WebSocket 1006 errors | Check for exceptions in server logs | Server crash? Restart and check logs |

---

## 📝 Logging & Monitoring

### To Monitor Server
```bash
# In separate terminal, follow logs
tail -f /tmp/flow.log  # if redirected
# or just watch the server terminal output
```

### Key Log Patterns to Watch
```
# Language detection working
[flow-local] Language initialized: en
[flow-local] Language candidate pt: count=2/3
[flow-local] Language switched to pt

# Confidence gating working
[flow-local] STT confidence=0.91 text='...'
[flow-local] STT confidence=0.42 < 0.55, skipping

# Keepalive healthy
[flow-local] Keepalive ping #3 sent
[flow-local] Pong received
```

### Browser Console (F12)
```javascript
// Should see these diagnostics
"Server mode: stable (keepalive: 90000ms)"
// No ERROR lines
// No Uncaught Error messages
```

---

## 🔄 Rollback (If Needed)

If something breaks:

```bash
# Stop server
pkill -f "python3 server_local.py"

# Restore previous version
cd /Users/kulturestudios/BelawuOS/flow
git checkout server_local.py static/index.html

# Restart
python3 server_local.py

# Hard refresh browser
```

Estimated rollback time: **1 minute**

---

## ✅ Final Checklist

- [ ] All pre-deployment steps done
- [ ] Server started successfully
- [ ] Health check passes
- [ ] Browser loads and displays READY
- [ ] Smoke test passes (2 min)
- [ ] All 5 full tests pass (75 min)
- [ ] No errors in server logs
- [ ] No errors in browser console
- [ ] WebSocket healthy (no 1006)
- [ ] Documentation reviewed

**Status When All Boxes Checked**: 🟢 **PRODUCTION READY**

---

## 📞 Troubleshooting Support

**For detailed info**:
- Technical details: `FLOW_RELIABILITY_PATCH_IMPLEMENTED.md`
- Deployment steps: `DEPLOY_RELIABILITY_PATCH.md`
- Configuration: `QUICK_REFERENCE.md`
- Overview: `RELIABILITY_PATCH_SUMMARY.md`

---

**FLOW RELIABILITY PATCH v1.0 — READY FOR DEPLOYMENT**
