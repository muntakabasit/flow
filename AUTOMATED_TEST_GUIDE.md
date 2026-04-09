# FLOW Automated & Manual Test Guide

**Status:** Server running at http://localhost:8765
**Test Date:** 2026-02-17
**Focus:** Auto-Resume Listening Fix Verification

---

## Quick Start (2 minutes)

1. **Server is already running** in background (`python3 server_local.py`)
2. **Open browser:** http://localhost:8765
3. **Hard refresh:** Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
4. **Open DevTools:** F12
5. **Paste test script:** Copy entire TEST_RUNNER.js code into console
6. **Run tests:** Type `runAllTests()` in console and press Enter

---

## Automated Tests (Run in Console)

### Setup
```javascript
// Copy TEST_RUNNER.js into browser console
// Then run:
runAllTests()
```

**What it checks automatically:**
- ✅ Test 1: Page loads with orb button visible
- ✅ Test 2: Mic button click changes state
- ✅ Test 3: Console is clean (no errors)
- ✅ VAD settings configured
- ✅ Language config in localStorage
- ✅ Auto-resume logic in place

---

## Manual Tests (Critical for User Experience)

### Test 3: Natural Speech with Pauses

**What to do:**
1. Click the orb mic button
2. Speak: **"Hello, how are you doing today?"** (pause after "how are you")
3. Important: Make a natural pause mid-sentence
4. Continue speaking: "...doing?"

**Expected:**
- App does NOT cut off during pause
- After you finish (silence), state changes: LISTENING → TRANSLATING → SPEAKING
- You hear the translation

**Result:** ✅ or ❌

---

### Test 4: Barge-In (Interrupt TTS)

**What to do:**
1. Speak: **"What's the weather like?"**
2. Wait for TTS to start playing the response
3. While audio is STILL PLAYING, speak: **"Never mind, tell me a joke"**

**Expected:**
- TTS stops immediately
- State returns to LISTENING
- You can continue speaking without waiting

**Result:** ✅ or ❌

---

### Test 5: Network Disconnect

**What to do:**
1. Open DevTools (F12)
2. Go to Network tab
3. Click the "Offline" checkbox (simulate network down)
4. Observe the app

**Expected:**
- State changes to OFFLINE (red)
- Mic stops working
- "Reconnect" button appears

**Result:** ✅ or ❌

---

### Test 6: Reconnect

**What to do:**
1. DevTools Network tab → uncheck "Offline"
2. Click the "Reconnect" button in the app
3. Check console for errors

**Expected:**
- App reconnects to server
- State returns to LISTENING
- Console shows no duplicate timer messages

**Result:** ✅ or ❌

---

### Test 7: Language Swap

**What to do:**
1. Click settings button (⚙️ gear near mic)
2. Find "↔ Swap Languages" button
3. Click it
4. Close settings
5. Speak to test new direction

**Expected:**
- Language bar updates (EN→PT becomes PT→EN)
- Translation works in new direction
- Can swap back again

**Result:** ✅ or ❌

---

### Test 8: VAD Sliders

**What to do:**
1. Open settings (⚙️ gear)
2. Find "Sensitivity" slider (0-100%)
3. Move left (more sensitive) and right (less sensitive)
4. Find "Delay" slider (300-2000ms)
5. Move left (faster) and right (slower)
6. Speak at different volumes/speeds
7. Observe if behavior changes

**Expected:**
- Sensitivity affects how readily speech is detected
- Delay affects how quickly silence ends a turn
- Changes are noticeable

**Result:** ✅ or ❌

---

### Test 9: Animation Smoothness

**What to do:**
1. Watch the orb during a full turn (speak → response → resume)
2. Look for smooth breathing animation
3. Watch state transitions
4. Check for layout jank when bubbles appear

**Expected:**
- Orb animation is smooth (no stuttering)
- State label updates smoothly
- Transcript bubbles appear without jumping
- 60fps smooth (no visible frame drops)

**Result:** ✅ or ❌

---

### Test 10: Console Clean

**What to do:**
1. Open DevTools (F12)
2. Go to Console tab
3. Look for red errors or yellow warnings
4. Do a few turns of conversation

**Expected:**
- NO red error messages
- NO yellow warning messages
- Only normal log output

**Result:** ✅ or ❌

---

### Test A: Auto-Resume (CRITICAL)

**What to do:**
1. Make sure "Hold to Talk" is DISABLED in settings
2. Speak: **"Hello"**
3. Wait for TTS response to finish playing
4. Watch carefully

**Expected:**
- After response finishes, app goes back to LISTENING
- NO click required
- Ready for next input immediately

**This is the main fix we implemented!**

**Result:** ✅ or ❌

---

### Test B: Hold-to-Talk Mode

**What to do:**
1. Open settings (⚙️ gear)
2. Enable "Hold to Talk" checkbox
3. Close settings
4. PRESS AND HOLD the orb (don't release)
5. While holding, speak: **"Tell me a joke"**
6. RELEASE the button (don't click again)

**Expected:**
- Mic captures only while you're holding
- Audio is finalized when you release
- After response, app is in READY state
- Next turn requires another hold

**Result:** ✅ or ❌

---

### Test C: Full Conversation Flow

**What to do:**
1. Disable "Hold to Talk" if enabled
2. Have a 3-4 turn conversation:
   - You: "What's your name?"
   - (AUTO-RESUME - no click)
   - You: "Where are you from?"
   - (AUTO-RESUME - no click)
   - You: "Teach me a word in Portuguese"
   - (AUTO-RESUME - no click)

**Expected:**
- Smooth, continuous conversation
- No clicking between turns
- Feels natural and flowing
- Like talking to a real person

**Result:** ✅ or ❌

---

## Test Result Template

Copy and paste results below:

```
TEST RESULTS:
=============

AUTOMATED TESTS (Console):
[ ] Test 1: Page Load - ✅ or ❌
[ ] Test 2: Mic Button - ✅ or ❌
[ ] Test 3: Console Check - ✅ or ❌
[ ] VAD Settings - ✅ or ❌
[ ] Language Config - ✅ or ❌
[ ] Auto-Resume Logic - ✅ or ❌

MANUAL TESTS (Browser):
[ ] Test 3: Natural Speech - ✅ or ❌
[ ] Test 4: Barge-In - ✅ or ❌
[ ] Test 5: Disconnect - ✅ or ❌
[ ] Test 6: Reconnect - ✅ or ❌
[ ] Test 7: Language Swap - ✅ or ❌
[ ] Test 8: VAD Sliders - ✅ or ❌
[ ] Test 9: Animations - ✅ or ❌
[ ] Test 10: Console Clean - ✅ or ❌
[ ] Test A: Auto-Resume ★ - ✅ or ❌
[ ] Test B: Hold-to-Talk - ✅ or ❌
[ ] Test C: Full Conversation ★ - ✅ or ❌

NOTES:
- ★ = Most important tests
- Report any ❌ failures with details
```

---

## If Any Tests Fail

1. **Note which test failed** and what went wrong
2. **Check browser console** (F12) for error messages
3. **Report the error** and I'll fix it
4. **Retest** after fix

---

## Success Criteria

✅ **All 13 tests pass** = App is production-ready
❌ **Any test fails** = We fix it and retest

Expected outcome: **All tests should pass** ✅

---

## Server Health Check

```bash
# Check if server is running
curl -s http://localhost:8765/ | head -5

# Should output HTML with "FLOW" in title
```

---

**Ready to test?** Open http://localhost:8765 and follow the procedures above!
