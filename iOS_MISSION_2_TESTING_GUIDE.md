# 📱 iOS Mission 2 Testing Guide

**Date:** 2026-02-14
**Status:** Ready for Testing
**App Version:** With Mission 2 Implementation

---

## 🚀 Pre-Testing Setup

### 1. Build the iOS App
```bash
cd /Users/kulturestudios/BelawuOS/flow/FlowInterpreter
# Open in Xcode
open FlowInterpreter.xcodeproj
# Or build from command line
xcodebuild -scheme FlowInterpreter -configuration Debug -destination 'platform=iOS Simulator,name=iPhone 15'
```

### 2. Start the Server
```bash
cd /Users/kulturestudios/BelawuOS/flow
python server_local.py
```
Server should start on `localhost:8765`

### 3. Configure App
1. Open iOS app on simulator
2. Go to Settings
3. Server URL: `localhost:8765` (or IP address if testing on device)
4. Test Connection (should show ✓ Server is running!)

---

## ✅ Test 1: Pause Tolerance Setting

**Objective:** Verify pause tolerance setting is visible, adjustable, and persists.

### Steps:
1. Open the iOS app
2. Tap Settings icon
3. Scroll down to "Turn Boundary" section (should be after Conversation, before Server Connection)
4. See two options:
   - ☐ Normal (700ms)
   - ☐ Long (1100ms)
5. Default should be "Normal"
6. Tap "Long (1100ms)"
7. Close Settings
8. Reopen Settings
9. **Expected:** "Long (1100ms)" should still be selected

### Success Criteria:
- ✅ Section appears in Settings with correct title and icon
- ✅ Both options visible and selectable
- ✅ Setting persists after close/reopen
- ✅ No UI glitches or overlaps

### If Failed:
- Check SettingsView.swift has Turn Boundary section
- Verify pauseToleranceRaw in AppState has @AppStorage decorator
- Check Settings view builds without errors

---

## ✅ Test 2: Speaking with Natural Pauses (Normal Mode)

**Objective:** Verify that normal pauses (< 700ms) don't trigger turn finalization.

### Setup:
1. Settings: Ensure "Normal (700ms)" is selected
2. Go to main conversation view
3. Start a session (tap mic or hold, depending on mode)
4. **Diagnostics:** Open diagnostics panel to watch messages

### Steps:
1. Speak: "Where is the..."
2. **Pause for 200-300ms** (short, natural pause)
3. Continue: "...nearest restaurant?"
4. Wait for TTS to respond
5. **Check transcript:** Should be ONE entry (words merged)

### Expected Behavior:
- During 200ms pause: No "speech_end" in diagnostics
- Audio continues streaming during pause
- Server recognizes as one turn
- TTS responds with single translation
- Transcript shows: "Where is the nearest restaurant?"

### Success Criteria:
- ✅ Pause doesn't split the sentence
- ✅ TTS response is for complete sentence
- ✅ Single transcript entry

### If Failed:
- Check turn finalization happening too early
- Verify hangoverMs = 0.25 in AppState
- Check evaluateSilenceDuration() uses microPauseThreshold

---

## ✅ Test 3: Speaking with Long Pauses (Normal Mode)

**Objective:** Verify that pauses > 700ms finalize the turn (Normal mode).

### Setup:
1. Settings: Ensure "Normal (700ms)" is selected
2. Main conversation view, active session
3. Diagnostics open

### Steps:
1. Speak: "Hello"
2. **Pause for 800-1000ms** (long pause)
3. Speak: "How are you?"
4. Wait for TTS

### Expected Behavior:
- At ~700ms of silence: Turn finalizes
- Server processes "Hello" → Sends TTS for "Hello"
- User hears "Hello" response
- User continues with "How are you?"
- Server processes "How are you?" as separate turn
- User hears response for "How are you?"

### Transcript Should Show:
- Entry 1: "Hello"
- Entry 2: "How are you?"
(Two separate entries, not merged)

### Success Criteria:
- ✅ Two separate transcript entries
- ✅ Two separate TTS responses
- ✅ Turn finalized at correct time threshold

### If Failed:
- Check finalizePauseThreshold returns 0.7 for "normal"
- Verify evaluateSilenceDuration() logic for threshold comparison
- Check TurnSmoothingManager has access to appState

---

## ✅ Test 4: Speaking with Long Pauses (Long Mode)

**Objective:** Verify that pause tolerance changes behavior.

### Setup:
1. Settings: Change to "Long (1100ms)"
2. Close and reopen app to ensure persistence
3. Main conversation, active session
4. Diagnostics open

### Steps:
1. Speak: "Where is..."
2. **Pause for 800ms** (same as Test 3, but now in Long mode)
3. Continue: "...the restaurant?"
4. Wait for TTS

### Expected Behavior:
- Same 800ms pause that finalized in Normal mode should NOT finalize in Long mode
- Audio continues streaming
- User completes full sentence
- Server processes as single turn: "Where is the restaurant?"
- Single TTS response

### Transcript Should Show:
- Entry 1: "Where is the restaurant?" (single entry)

### Success Criteria:
- ✅ 800ms pause doesn't finalize (different from Normal test)
- ✅ Single merged transcript entry
- ✅ Single TTS response

### If Failed:
- Check finalizePauseThreshold returns 1.1 for "long"
- Verify dynamic threshold calculation in evaluateSilenceDuration()
- Check appState.pauseTolerance is being read correctly

---

## ✅ Test 5: Barge-In (Interrupt TTS)

**Objective:** Verify user can interrupt TTS playback.

### Setup:
1. Settings: Either pause tolerance (doesn't matter for this test)
2. Main conversation, active session
3. Diagnostics open

### Steps:
1. Speak: "What time is it?"
2. **Wait for TTS to start** (you should hear audio/see audio indicator)
3. While TTS is playing, **speak again:** "Never mind, hello!"
4. TTS should **stop immediately**
5. Wait for server response

### Expected Behavior:
- When user speaks during TTS:
  - Playback stops immediately (kill signal works)
  - Diagnostics show "BARGE-IN: User interrupted TTS"
  - App transitions back to LISTENING
  - Mic captures new speech
  - Server processes new speech as new input

### Diagnostics Should Show:
- "tts_start" (when TTS begins)
- "BARGE-IN: User interrupted TTS" (when you speak during TTS)
- "speech_start" (when new speech detected)
- "Client VAD: speech_end" (when you finish new speech)

### Success Criteria:
- ✅ TTS stops when user speaks
- ✅ "BARGE-IN" message in diagnostics
- ✅ New speech captured and processed
- ✅ App transitions correctly

### If Failed:
- Check handlePossibleBargeIn() in FlowCoordinator
- Verify audioService.killPlayback() being called
- Check wsService.sendBargeIn() implementation
- Verify audio level threshold is 0.04 (not too high)

---

## ✅ Test 6: Barge-In Debounce

**Objective:** Verify barge-in doesn't trigger multiple times rapidly.

### Setup:
1. Main conversation, active session
2. Diagnostics open

### Steps:
1. Speak: "What is your name?"
2. Wait for TTS
3. During TTS playback, make quick noises/coughs (3-4 times in < 1 second)
4. **Only one** barge-in should register

### Expected Behavior:
- First noise during TTS → Interrupts, shows "BARGE-IN"
- Subsequent noises within 300ms → Ignored (debounce)
- After 300ms, if speaking again → New barge-in could trigger

### Diagnostics:
- Single "BARGE-IN" message (not multiple)

### Success Criteria:
- ✅ Only one barge-in per TTS session
- ✅ Subsequent attempts ignored (debounce works)
- ✅ No error states

### If Failed:
- Check debounce logic in handlePossibleBargeIn()
- Verify lastBargeInAt timestamp checking
- Check debounce interval is 0.3s (300ms)

---

## ✅ Test 7: Mode B UI Compatibility

**Objective:** Verify Mode B features still work with Mission 2 changes.

### Setup:
1. Close and restart app
2. Main conversation view visible
3. Status indicator (3 pulsing dots) should be visible

### Steps:
1. Check initial state shows 3 pulsing dots (READY state)
2. Verify indicator color is green
3. Start a session (tap mic)
4. Verify dots pulse during LISTENING state
5. Speak something
6. Verify state transitions (colors change):
   - LISTENING: 🟢 Green
   - THINKING/FINALIZING: 🟡 Amber
   - SPEAKING: 🟡 Amber
7. Check language lock badge:
   - Should show "🔒 LOCKED" during session
   - Should disappear when session ends
8. Verify language swap button:
   - Disabled during LISTENING/TRANSLATING/SPEAKING
   - Enabled when session ends

### Expected Behavior:
- All Mode B features work as before
- No visual glitches
- State transitions smooth
- Lock badge appears/disappears correctly

### Success Criteria:
- ✅ 3 dots visible and pulsing
- ✅ Colors change with state
- ✅ Lock badge shows during session
- ✅ Language button locked during session
- ✅ No overlaps or layout issues

### If Failed:
- Check SoftStatusPill.swift still has dot animation
- Verify ContentView still references SoftStatusPill
- Check AppState transition() method still called
- Verify sessionStartLanguages logic untouched

---

## ✅ Test 8: End-to-End Conversation (Multi-Turn)

**Objective:** Full conversation flow with all Mission 2 features.

### Setup:
1. Settings: Normal pause tolerance
2. Clean diagnostics
3. Conversation ready
4. Start session

### Conversation Script:
```
YOU: "Hello, what's your name?"
SERVER: TTS response
YOU: [interrupt during TTS] "Wait, I meant what time is it?"
SERVER: TTS response to new question
YOU: "Never mind. Where is the nearest coffee shop?"
SERVER: TTS response
YOU: [pause 800ms] "And is it open now?"
SERVER: Processes as separate turn (turn boundary)
YOU: TTS response
```

### Verification Checklist:
- [ ] "Hello" turn finalizes after 700ms silence
- [ ] You can barge-in during second TTS
- [ ] New question processed correctly
- [ ] Third question processed
- [ ] 800ms pause causes turn boundary (separate entry)
- [ ] Final question gets its own response
- [ ] No errors in diagnostics
- [ ] Transcript shows 4 separate user entries

### Expected Transcript:
1. "Hello, what's your name?"
2. "Wait, I meant what time is it?"
3. "Where is the nearest coffee shop?"
4. "And is it open now?"

### Success Criteria:
- ✅ All features work together
- ✅ No errors or crashes
- ✅ Correct turn boundaries
- ✅ Barge-in works mid-flow
- ✅ Transcript accurate

---

## 🧪 Diagnostic Checks

### Message Types in Diagnostics
Look for these messages appearing correctly:

**Normal Turn:**
```
Client VAD: speech_start     [When you start speaking]
[TTS playing]
[Turn finalizes after pause]
Client VAD: speech_end       [When silence after hangover detected]
```

**Barge-In Turn:**
```
[TTS starts playing]
BARGE-IN: User interrupted TTS  [When you speak during TTS]
Client VAD: speech_start     [New speech begins]
Client VAD: speech_end       [New speech ends]
```

**Mode B:**
```
[State transitions show colors]
READY → LISTENING → THINKING/FINALIZING → SPEAKING → LISTENING
```

---

## 📊 Expected Results Summary

| Test | Pause Tolerance | Expected Result | Pass/Fail |
|------|-----------------|-----------------|-----------|
| 1. Setting | Normal | Visible, adjustable, persists | |
| 2. Natural pauses | Normal | < 700ms doesn't finalize | |
| 3. Long pauses | Normal | > 700ms finalizes | |
| 4. Long pauses | Long | > 1100ms finalizes | |
| 5. Barge-in | Either | TTS stops on user speech | |
| 6. Debounce | Either | Only one barge-in per session | |
| 7. Mode B | Either | All UI features work | |
| 8. Full flow | Normal | Multi-turn conversation works | |

---

## ⚠️ Troubleshooting

### Issue: App Crashes on Launch
**Check:**
- All Swift files compile (run: `swiftc -parse [file]`)
- AppState initialization complete
- FlowCoordinator properly wired up

### Issue: Pause Tolerance Setting Missing
**Check:**
- SettingsView.swift has Turn Boundary section
- pauseToleranceRaw in AppState has @AppStorage
- Picker uses correct binding

### Issue: Pause Tolerance Not Working
**Check:**
- AppState.endSilenceMs computed property correct
- TurnSmoothingManager has appState reference
- evaluateSilenceDuration() uses dynamic thresholds

### Issue: Barge-In Not Working
**Check:**
- handlePossibleBargeIn() threshold is 0.04
- audioService.killPlayback() implemented
- wsService.sendBargeIn() implemented
- Audio level is being calculated correctly

### Issue: Mode B UI Broken
**Check:**
- SoftStatusPill.swift unchanged
- ContentView still references SoftStatusPill
- AppState.transition() still works
- No changes to language lock logic

### Issue: Diagnostics Show Unknown Messages
**Check:**
- WebSocketService.parseMessage() handles new types
- ServerMessage enum has all three new cases
- Message handlers in FlowCoordinator exist

---

## 🎯 Sign-Off Checklist

Before deploying to production:

- [ ] All 8 tests pass
- [ ] No crashes or errors
- [ ] Diagnostics show correct messages
- [ ] Mode B UI intact and working
- [ ] Settings persist correctly
- [ ] Barge-in responsive (< 300ms delay)
- [ ] Pause tolerance affects behavior correctly
- [ ] Multi-turn conversations work smoothly
- [ ] No memory leaks or hanging tasks
- [ ] Audio quality unchanged

---

## 📱 Testing Environment

**Recommended Setup:**
- **Device:** iPhone 15 simulator (or iPhone 13+)
- **iOS Version:** 16.0+
- **Server:** Running on Mac (localhost:8765)
- **Network:** WiFi (local network)
- **Audio:** Simulator audio working (may need to enable)

**Xcode Version:** 15.0+

---

## 📝 Notes

- Simulator audio may be limited - test on real device if possible
- Barge-in timing is sensitive to audio level threshold
- Pause tolerance is about turn finalization, not TTS cutoff
- All times are in milliseconds (700ms = 0.7 seconds)
- Diagnostics auto-scroll to show latest messages
- SessionWanted flag prevents reconnects during testing

Good luck with testing! 🚀

