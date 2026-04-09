# Testing the Continuous Conversation Flow Fix

**Date:** 2026-02-14
**Status:** Ready for Testing
**Focus:** Verifying auto-start listening and auto-resume after TTS

---

## 🎯 What Was Fixed

Two critical changes to restore the original working flow:

### **Fix 1: Auto-Start Listening on Page Load**
- **File:** `/static/index.html` line 1057
- **Change:** `let sessionWanted = true;`
- **Effect:** When page loads and connects to server, app automatically starts listening without user clicking mic

### **Fix 2: Auto-Resume Listening After TTS**
- **File:** `/static/index.html` lines 1261-1267
- **Change:** Added code to call `startMic()` when transitioning from SPEAKING → READY
- **Effect:** After TTS finishes and server sends `turn_complete`, app automatically resumes listening

### **Fix 3: Server Timeout Increased**
- **File:** `/server_local.py` lines 129, 134
- **Change:** `SILENCE_DURATION_MS = 2000` (was 650ms)
- **Effect:** Server waits 2 seconds before finalizing a turn, allowing natural speaking pauses

---

## 📋 Testing Steps

### **Step 0: Setup**
1. Open terminal and navigate to `/Users/kulturestudios/BelawuOS/flow/`
2. Start the server:
   ```bash
   python server_local.py
   ```
   Should print: `Server running on localhost:8765`
3. Open browser to: `http://localhost:8765`
4. **IMPORTANT:** Hard refresh to clear cache: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows/Linux)

---

### **Test 1: Auto-Start Listening on Page Load**

**Objective:** Verify that the app automatically starts listening when page loads

**Steps:**
1. Page loads
2. Wait 2-3 seconds for connection
3. **Expected:**
   - Status indicator shows "LISTENING" (not "READY")
   - Mic button shows "listening"
   - Diagnostics show: `S.IDLE → S.CONNECTING → S.READY → S.LISTENING`

**Success Criteria:**
- ✅ No click needed to start listening
- ✅ App goes directly to LISTENING on load
- ✅ Mic is ready to capture audio immediately

**If Failed:**
- Check browser console for errors (F12 → Console)
- Check that `sessionWanted = true` is on line 1057
- Verify server is running and WebSocket connects (`wsConnect` in diagnostics)

---

### **Test 2: Continuous Speech (Natural Pauses Don't Cut Off)**

**Objective:** Verify that short pauses don't interrupt the turn

**Steps:**
1. After page loads and starts listening
2. Speak a sentence with a natural pause in the middle:
   - Say: "Hello, how are..."
   - **Pause for 500ms** (natural breathing pause)
   - Continue: "...you doing today?"
3. **Wait for translation and TTS**

**Expected Behavior:**
- Entire sentence is captured as ONE turn (not two)
- TTS response is for the complete sentence
- Diagnostics show single speech event, not split

**Success Criteria:**
- ✅ App doesn't cut off mid-sentence
- ✅ Single TTS response for complete thought
- ✅ 2 second silence timeout respected

**If Failed:**
- Check server `SILENCE_DURATION_MS` is 2000 (not 650)
- Verify VAD hangover is working (diagnostics should show timestamps)

---

### **Test 3: Auto-Resume After TTS (The Main Fix)**

**Objective:** Verify the app automatically resumes listening after TTS finishes

**Steps:**
1. After page loads and auto-starts listening
2. Say: "Hello"
3. Wait for server to translate (diagnostics show TRANSLATING)
4. Wait for TTS to play (you may hear audio, or see SPEAKING state)
5. **When TTS finishes:**
   - App should automatically transition back to LISTENING
   - Status indicator should update
   - Mic button should show "listening"
6. **Immediately say:** "How are you?" (without clicking anything)

**Expected Behavior:**
- After TTS finishes, state transitions: SPEAKING → READY → LISTENING
- No manual mic click needed
- Second sentence is captured and processed

**Transcript Should Show:**
```
1. "Hello"
2. "How are you?"
```
(Two separate entries)

**Success Criteria:**
- ✅ App auto-resumes listening (no click needed)
- ✅ State transitions correctly: SPEAKING → READY → LISTENING
- ✅ Second sentence captured without manual intervention
- ✅ Diagnostics show `turn_complete` followed by auto-resume

**If Failed:**
- Check lines 1261-1267 exist and have auto-resume logic
- Verify `turn_complete` handler transitions to READY (line 2058)
- Check console for errors during state transitions
- Verify `startMic()` is being called (should see "Starting mic..." in diagnostics)

---

### **Test 4: Multi-Turn Conversation (Full Flow)**

**Objective:** Verify entire conversation works smoothly

**Script:**
```
YOU:   "What is your name?"
[Server translates, plays TTS - app should auto-resume]
YOU:   "That's nice. How long have you been alive?"
[Server translates, plays TTS - app should auto-resume]
YOU:   "Interesting. Tell me about yourself."
```

**Expected:**
- 3 separate conversation turns
- No manual clicks needed between turns
- Transcript shows all 3 entries
- No errors or crashes

**Success Criteria:**
- ✅ Entire flow works smoothly
- ✅ No freezing or stuck states
- ✅ Each turn completes and auto-resumes

---

## 🧪 Diagnostics to Watch For

### **Successful Sequence:**
```
ws connecting...
ws OPEN
S.IDLE → S.CONNECTING
S.CONNECTING → S.READY
Session wanted - starting mic automatically...
S.READY → S.LISTENING
[User speaks]
VAD: Speech detected...
[Audio streaming to server]
[Server processes]
audio_delta: [chunks received]
S.LISTENING → S.TRANSLATING
tts_start
S.TRANSLATING → S.SPEAKING
[TTS playing]
TTS playback finished
turn_complete
S.SPEAKING → S.READY
Starting mic... [AUTO-RESUME]
S.READY → S.LISTENING
[Ready for next turn]
```

### **Error Signs (What NOT to See):**
```
❌ S.SPEAKING → S.READY (but stays in READY, doesn't go to LISTENING)
❌ "Mic stopped" message when you didn't click it
❌ turn_complete never arrives
❌ tts_playback_done not sent
❌ State stuck on SPEAKING
```

---

## 📱 Browser Console Checks

1. Open DevTools: `F12` (Windows/Linux) or `Cmd+Option+I` (Mac)
2. Go to **Console** tab
3. Look for errors (red text) - there should be none
4. Look for warnings (yellow text) - some are OK, but no WebSocket errors
5. Look for diagnostics (black text) - should show the state transitions

---

## 🔧 If Something's Wrong

**Issue: App stuck on SPEAKING state**
- ✅ Check: Is `turn_complete` arriving? (search diagnostics for "turn_complete")
- ✅ Check: Is `tts_playback_done` being sent? (search for "playback finished")
- ✅ Fix: May need to restart server or refresh browser

**Issue: App goes to READY but doesn't auto-resume listening**
- ✅ Check: Is auto-resume code present? (lines 1261-1267)
- ✅ Check: Is `sessionWanted` set to `true`? (line 1057)
- ✅ Check: Do you see "Starting mic..." in diagnostics after READY?
- ✅ Fix: Hard refresh browser (Cmd+Shift+R)

**Issue: App cuts off mid-sentence**
- ✅ Check: Is `SILENCE_DURATION_MS = 2000` in server? (line 129, 134)
- ✅ Check: Is server running in correct mode?
- ✅ Fix: Restart server, verify configuration

**Issue: WebSocket won't connect**
- ✅ Check: Is server running? (`python server_local.py`)
- ✅ Check: Is browser accessing correct URL? (`http://localhost:8765`)
- ✅ Check: No firewall blocking port 8765?
- ✅ Fix: Restart server, check console for error messages

---

## ✅ Sign-Off Checklist

After testing, verify:
- [ ] Test 1: Auto-start listening works (no click needed on page load)
- [ ] Test 2: Natural pauses don't cut off sentences (2s timeout works)
- [ ] Test 3: App auto-resumes after TTS (main fix working)
- [ ] Test 4: Multi-turn conversation works smoothly
- [ ] No errors in browser console
- [ ] Diagnostics show correct state transitions
- [ ] Transcript shows all turns correctly

---

## 📝 Notes

- The app should feel "alive" - always listening, no frozen states
- You should NOT need to click the mic button after the first automatic start
- Each turn should complete naturally and smoothly flow to the next
- If you see any "INVALID" transition errors, report those immediately

Good luck! 🚀
