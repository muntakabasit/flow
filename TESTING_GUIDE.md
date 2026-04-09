# FLOW Testing Guide — OFF Button → Restart Flow

## Quick Test (2 minutes)

1. **Start Fresh**
   ```bash
   # Hard refresh browser (clear cache)
   # Mac: Cmd+Shift+R
   # Windows/Linux: Ctrl+Shift+R
   ```

2. **Verify Startup**
   - Page loads and pill shows **READY** (green)
   - Diagnostic panel shows successful health check
   - No red error messages in console

3. **Test Basic Flow**
   - Click **mic button**
   - Speak English: "Hello, how are you today?"
   - Wait for translation to Portuguese
   - Verify translated text appears (should be natural Portuguese, not English repeated)

4. **Test OFF → Restart**
   - Click **OFF button**
   - Verify:
     - Pill changes to **IDLE** (gray)
     - Diagnostic shows "✅ Session stopped - click mic to restart"
     - Mic button is inactive
   - Click **mic button** again
   - Verify:
     - Diagnostic shows "Reconnecting to server..."
     - Pill transitions: IDLE → CONNECTING (yellow) → READY (green)
     - Takes 1-3 seconds total

5. **Test Reversed Language**
   - Speak Portuguese: "Olá, tudo bem com você?"
   - Wait for translation to English
   - Verify English translation appears
   - Confirm it's NOT just Portuguese repeated

6. **Repeat Cycle**
   - Click OFF again
   - Click mic again
   - Speak another phrase
   - Confirm stable behavior

## Deep Test (5 minutes)

### State Validation
Open browser console (`F12` → Console tab) and look for these messages:

**Good startup sequence:**
```
IDLE → CONNECTING
Checking server health...
Server ready, connecting WebSocket...
WebSocket open
CONNECTING → READY
✅ Server ready gate opened
```

**Good OFF sequence:**
```
🛑 MANUAL STOP - closing session
✅ Session stopped - click mic to restart
READY → IDLE
```

**Good restart sequence:**
```
Reconnecting to server...
IDLE → CONNECTING
Checking server health...
Server ready, connecting WebSocket...
WebSocket open
CONNECTING → READY
✅ Server ready gate opened
```

### Error Checking
- No red messages in diagnostic panel
- No console errors (should show only blue "info" or green "ok" messages)
- No invalid state transitions (should never see "INVALID:" in diagnostics)

### Audio Validation
1. **Mic Test:**
   - Click mic
   - Speak clearly
   - Should see "🎙️ Speech detected" message
   - Should see "🔉 Audio sent" message
   - Should see translated text appear within 2 seconds

2. **Language Confidence:**
   - Speak English multiple times → should stay on English translation
   - Speak Portuguese multiple times → should switch to Portuguese translation
   - Natural speech should not cause false language switches

3. **No Hallucinations:**
   - Transcriptions should only contain what you actually said
   - Common false positives to watch for:
     - "Thank you for watching" (when you didn't say it)
     - "Subscribe" or "Like and subscribe" (when you didn't say it)
     - "Obrigado por assistir" in Portuguese context
   - If you see these without saying them, hallucination filter needs adjustment

### Translation Quality
- Preserve tone and meaning
- No addition of politeness ("please", "thank you", "senhor/senhores")
- No explanation or paraphrasing
- Natural, conversational flow

Examples:
```
English IN:  "I'm tired"
Portuguese OUT: "Estou cansado"  ✓ (correct)
Portuguese OUT: "Estou muito cansado, obrigado" ✗ (added content)

Portuguese IN: "Qual é seu nome?"
English OUT: "What's your name?" ✓ (correct)
English OUT: "Hello, what's your name please?" ✗ (added content)
```

## Troubleshooting

### Issue: OFF button doesn't work
**Symptom:** Clicking OFF doesn't stop audio or change pill color

**Check:**
1. Is the OFF button visible on page? (should be in toolbar)
2. Open console (`F12`), look for errors
3. Try hard refresh: Cmd+Shift+R
4. Check `/index.html` line 1556-1574 has full OFF handler

**Fix:**
```bash
# Restart server
kill $(ps aux | grep server_local.py | grep -v grep | awk '{print $2}')
python server_local.py
```

### Issue: OFF → restart doesn't work
**Symptom:** After OFF, clicking mic doesn't show "Reconnecting..." message

**Probable cause:** The IDLE state detection (lines 1503-1509) might be missing

**Check:**
1. View page source (Cmd+Option+U / Ctrl+Shift+U)
2. Search for "if (state === S.IDLE)"
3. Should appear around line 1504 in index.html

**Verify code:**
```javascript
if (state === S.IDLE) {
  diagLog('Reconnecting to server...', 'info');
  wsConnect();
  sessionWanted = true;
  return;
}
```

### Issue: Restart hangs at CONNECTING
**Symptom:** Pill stuck on CONNECTING (yellow), never transitions to READY

**Probable cause:** Server health check or WebSocket connection timing out

**Check:**
1. Server running? `ps aux | grep server_local`
2. Server logs for errors: `tail -50 /tmp/flow.log` (if logging enabled)
3. Network tab (F12 → Network): Look for `/health` request
   - Should return HTTP 200 with `{"status": "ok"}`
   - If 500 or timeout, server is overloaded/crashed

**Fix:**
```bash
# Restart server with fresh models
python server_local.py
# Wait 30-60 seconds for model loading
# Then refresh browser
```

### Issue: Doubled/repeated speech
**Symptom:** English phrase translated to "English English English" or Portuguese repeated

**Probable cause:** Language detection stuck on wrong language

**Check:**
1. Click OFF to reset
2. Wait 5 seconds
3. Hard refresh browser (Cmd+Shift+R)
4. Test again with different language

**Server check:**
1. Look at server logs for language detection confidence
2. Should see something like: `[STT] lang=en confidence=0.95`
3. If confidence is low (<0.7), the language might not be detected correctly

### Issue: Hallucinations appearing
**Symptom:** See text like "Thank you for watching" when you didn't say it

**Probable cause:** Whisper model's false positives not being filtered

**Check:**
1. What exact text is being hallucinated?
2. Is it in the HALLUCINATION_PATTERNS in server_local.py?

**Fix in server:**
1. Add to `HALLUCINATION_PATTERNS` set (around line 190)
2. Restart server

### Issue: Very slow translation
**Symptom:** Speak phrase, wait 10+ seconds before translation appears

**Probable cause:**
- Server model loading time (first request of session)
- Ollama taking time to process
- Network latency

**Check:**
1. First request of session always slower (30-60s to load models)
2. Subsequent requests should be 2-3 seconds
3. Check server resources: `top` or Activity Monitor
4. If CPU at 100%, server is overloaded

**Optimize:**
- Reduce WHISPER_MODEL_SIZE from "base" to "tiny" in server_local.py
- Stop other apps using CPU
- Increase available RAM if possible

## Server Health Diagnostics

### Check Server Status
```bash
# Is server running?
ps aux | grep server_local | grep -v grep

# Check server logs (if available)
tail -100 /tmp/flow.log

# Manual health check
curl http://localhost:5000/health

# Expected response:
# {"status": "ok", "models_loaded": true, ...}
```

### Restart Server (Clean)
```bash
# Kill existing process
kill $(ps aux | grep server_local.py | grep -v grep | awk '{print $2}')

# Wait 2 seconds
sleep 2

# Restart
cd /Users/kulturestudios/BelawuOS/flow
python server_local.py
```

### Monitor Server (Real-time)
```bash
# Watch logs while testing
tail -f /tmp/flow.log

# In another terminal, trigger test
# Then watch for:
# - [VAD] speech detected
# - [STT] transcribed: "..."
# - [LLM] translating
# - [TTS] synthesizing
```

## Expected Timing

### Successful Session Timing

**First request (cold start):**
- Click mic: immediate
- Speak 2-3 second phrase
- Pause 0.7 second
- Wait 30-60 seconds for Whisper/Ollama/Piper to initialize
- Translation appears

**Subsequent requests (warm):**
- Click mic: immediate
- Speak 2-3 second phrase
- Pause 0.7 second
- Wait 2-3 seconds
- Translation appears

**OFF → restart:**
- Click OFF: immediate
- Pill transitions to IDLE: instant
- Click mic: immediate
- Wait 1-3 seconds for reconnect
- Pill transitions IDLE → CONNECTING → READY
- Ready for next utterance

## Validation Checklist

- [ ] Page loads without errors
- [ ] Pill shows READY (green) on startup
- [ ] English→Portuguese translation works
- [ ] Portuguese→English translation works
- [ ] OFF button stops session
- [ ] OFF → restart cycle works smoothly
- [ ] State transitions are logged (IDLE → CONNECTING → READY)
- [ ] No hallucinations in transcriptions
- [ ] No invalid state transitions in console
- [ ] No red error messages
- [ ] Audio plays back correctly
- [ ] Multiple OFF/restart cycles work without errors

---

**Test Status:** [  ] PASS  [  ] FAIL

**Notes:**
```
[space for tester to add notes]
```
