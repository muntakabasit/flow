# Mode B Testing & Verification Guide

**Date:** 2026-02-13
**Phase:** Post-Integration Testing
**Target Device:** iPhone 14+ (glass effects support)

---

## 🧪 Test Categories

### A. Language Lock System

**Test A1: Lock engages on session start**
```
1. Open FLOW app
2. Tap orb to start mic (or hold for holdToTalk)
3. Observe language bar
   ✓ "locked" badge appears in amber
   ✓ Language swap button grayed out (50% opacity)
   ✓ Swap button is disabled (no tap response)
4. Wait 2 seconds
   ✓ Badge persists
   ✓ Button remains disabled
```

**Test A2: Lock disengages on session stop**
```
1. With active session running
2. Tap orb (or release hold) to stop
3. Observe language bar
   ✓ "locked" badge disappears
   ✓ Language swap button returns to amber/accent color
   ✓ Swap button is re-enabled (tap works)
4. Tap swap button
   ✓ Languages switch (EN → PT-BR becomes PT-BR → EN)
```

**Test A3: Attempted swap during session shows message**
```
1. Start session (languages locked)
2. Tap language swap button
3. Check diagnostics panel (scroll down)
   ✓ Message appears: "Language locked during session"
   ✓ Type is ".info" (not error)
4. Verify languages haven't changed
```

---

### B. Split Conversation Panel

**Test B1: Two-column layout visible**
```
1. Start session, speak: "Hello, how are you?"
2. Observe transcript area
   ✓ Left column header shows: "🇺🇸 YOU EN"
   ✓ Right column header shows: "🇧🇷 THEM PT-BR"
   ✓ Clear 1pt divider between columns
   ✓ Left column has darker background (Flow.surface3)
   ✓ Right column has lighter background (Flow.surface2)
```

**Test B2: Source text appears in left column**
```
1. With active session, speak several phrases
2. Observe left column
   ✓ Your words appear in left column (YOU)
   ✓ Text color is Flow.text1 (light, 225,234,240)
   ✓ Font is 14pt regular weight
   ✓ Line height is 1.4 (readable)
   ✓ Fade-in animation on new entries (0.3s)
```

**Test B3: Translation appears in right column with streaming cursor**
```
1. With active session, wait for translation
2. Observe right column
   ✓ Translation text appears as it arrives (deltas)
   ✓ Streaming cursor (blinking amber line) visible at end of translation
   ✓ Cursor blinks: visible (1.0 opacity) → hidden (0.2 opacity) in 0.4s cycle
   ✓ When translation complete, cursor disappears
   ✓ Amber color matches Flow.accent (#e0a846)
```

**Test B4: Auto-scroll to latest entry**
```
1. With active session, generate 10+ exchanges
2. Scroll up in panel to view old entries
3. Speak new phrase
4. Observe
   ✓ Panel auto-scrolls to bottom (0.2s easeOut animation)
   ✓ New entry becomes visible
   ✓ No jarring jump, smooth scroll
```

---

### C. SoftStatusPill (Connection Status)

**Test C1: Status pill shows in header**
```
1. App starts
2. Look at header (right side, before settings icon)
   ✓ SoftStatusPill visible with animated dots
   ✓ Positioned correctly (before gearshape button)
   ✓ Proper spacing (12pt from button)
```

**Test C2: Status pill colors match state**
```
1. App idle → Ready state
   ✓ Dots are green (#34d399)
   ✓ Label is "READY"

2. Start connecting
   ✓ Dots are amber (#fbbf24)
   ✓ Label is "CONNECTING"

3. During listening
   ✓ Dots are green
   ✓ Label is "LISTENING"

4. During translation
   ✓ Dots are amber (#fbbf24)
   ✓ Label is "THINKING"

5. During TTS playback
   ✓ Dots remain green
   ✓ Label is "SPEAKING"

6. Connection lost
   ✓ Dots are red (#f87171)
   ✓ Label is "OFFLINE"
```

**Test C3: Dot animation timing**
```
1. Observe SoftStatusPill dots
   ✓ 3 dots pulsing
   ✓ Each dot offset by ~0.3s (staggered, not in sync)
   ✓ Animation cycle is 1.2s (dots pulse in/out smoothly)
   ✓ Animation repeats forever (until state changes)
```

---

### D. Turn Boundary Smoothing (TurnSmoothingManager)

**Test D1: Natural speech pauses (< 300ms)**
```
1. Start session
2. Speak sentence, pause briefly (< 100ms), continue same thought
3. Check diagnostics panel
   ✓ Only ONE turn boundary is recorded (same turn ID)
   ✓ Both parts of speech appear as single entry in transcript
4. Verify in UI
   ✓ Source shows full sentence as one block
   ✓ Translation appears as one continuous entry
```

**Test D2: Medium silence (400-700ms)**
```
1. Start session
2. Speak: "Where is the restaurant?" (stop speaking)
3. Wait ~500ms (middle of "maybe pause" window)
4. Resume: "Can you help me find it?"
5. Check diagnostics panel
   ✓ Turn boundary MAY be recorded (depends on exact timing)
   ✓ Two separate entries in transcript (could be same turn or different)
6. Translation should show both statements
```

**Test D3: Long silence (> 1.0s) finalizes turn**
```
1. Start session
2. Speak: "Hello, I'm looking for a hotel."
3. Wait > 1.0 second (silent)
4. Check transcript
   ✓ Entry is marked as finalized (not streaming)
   ✓ Merge window expired
5. Resume: "Do you have any rooms available?"
6. Check transcript
   ✓ New entry appears (different turn)
   ✓ First entry and second entry are separate in UI
```

**Test D4: Resume within merge window (< 300ms)**
```
1. Start session
2. Speak: "Where can I find..." (stop)
3. Wait ~700ms (finalize trigger point)
4. Speech detected (server sends .speechStarted)
5. Within 300ms of finalize, resume speaking: "...a good restaurant?"
6. Check transcript
   ✓ Appears as SAME turn (merged)
   ✓ Source shows: "Where can I find... a good restaurant?"
   ✓ Single translation entry for whole sentence
```

---

### E. OrbView_ModeB Peak-Level Response (When Integrated)

**Test E1: Idle breathing (no audio)**
```
Prerequisite: OrbView_ModeB integrated in control dock

1. App idle (not listening)
2. Observe orb
   ✓ Gentle breathing animation (3.2s cycle)
   ✓ Subtle scale change: ±1.5% (barely noticeable)
   ✓ Glow opacity: 0.10 → 0.18 (soft pulse)
   ✓ Animation feels calm, meditative
```

**Test E2: Listening - responsive to audio level**
```
1. Start mic (listening state)
2. Speak at different volumes
   ✓ Soft speech: Orb scales slightly (core: 1.02 + peak*0.10)
   ✓ Normal speech: Orb expands more (core: ~1.05-1.08)
   ✓ Loud speech: Orb expands most (core: ~1.10-1.12, clamped at 1.12)
   ✓ NO JITTER: Smooth scaling response (not jittery)
   ✓ Glow radius expands with audio (8 + peak*18 range: 8-26)
   ✓ Glow opacity follows (0.18 + peak*0.25 range: 0.18-0.43)
```

**Test E3: Audio smoothing (not snappy)**
```
1. During listening state
2. Create sudden loud sound (clap)
3. Observe orb
   ✓ Expands smoothly (not instant jump)
   ✓ Response time: ~250ms to reach peak (spring response 0.25)
   ✓ NO bounce or overshoot (damping 0.9)
   ✓ Fades back smoothly when sound stops
   ✓ Feels responsive but not twitchy
```

**Test E4: Translating - halo rotation**
```
1. During translation state
2. Observe orb
   ✓ Core scale stable: 1.04 (no breathing)
   ✓ Halo ring rotates slowly (6s per full rotation = 60°/second)
   ✓ Rotation is linear (steady, predictable, no speeding/slowing)
   ✓ Glow pulses subtly (0.9s cycle: 0.20 → 0.26 opacity)
   ✓ Overall effect: "busy, thinking" without frantic motion
```

**Test E5: Speaking - ripple expansion**
```
1. TTS playback (speaking state)
2. Observe orb
   ✓ 2-3 expanding rings appear outward from core
   ✓ Each ring: scale 1.0 → 1.4 over 1.2s
   ✓ Rings staggered 0.25s apart
   ✓ Opacity fades: 0.4 → 0 (easeOut)
   ✓ Effect feels expressive, flowing (not jarring)
```

---

### F. Barge-In Detection (Already Working)

**Test F1: Barge-in interrupts TTS**
```
1. User speaks and completes turn
2. Server sends .ttsStart (app transitions to .speaking)
3. TTS playback begins
4. User interrupts by speaking
5. Audio peak crosses threshold (> VAD sensitivity)
6. Hold peak > threshold for 200ms
7. Observe
   ✓ TTS stops immediately (audio playback halts)
   ✓ App transitions to .listening
   ✓ Diagnostics shows: "Barge-in: user interrupted TTS"
   ✓ User can start speaking new turn
```

**Test F2: Barge-in debounce (0.6s throttle)**
```
1. User triggers barge-in once (TTS stops)
2. Within 0.6s, attempt barge-in again (create loud noise)
3. Observe
   ✓ Second barge-in is ignored (debounced)
   ✓ No diagnostic message (still in cooldown)
4. Wait > 0.6s
5. Attempt barge-in again
   ✓ Third barge-in works (debounce expired)
```

---

### G. Animation Performance & Smoothness

**Test G1: 60 FPS during listening (peak-responsive)**
```
1. Start listening state
2. Speak continuously
3. Use Performance Monitor (Xcode or iPhone Settings → Developer)
   ✓ Frame rate stays at 60 FPS (or Max frame rate on ProMotion)
   ✓ CPU < 15% (audio capture + peak smoothing)
   ✓ GPU < 20% (glass effects + animations)
4. No dropped frames during peak level changes
```

**Test G2: Glass effects smooth on iPhone 14+**
```
1. View SplitConversationPanel
2. Scroll transcript while translating
   ✓ Smooth scroll (60 FPS, no jank)
   ✓ Glass material blurs nicely (ultraThinMaterial)
   ✓ Border gradient visible (8% white opacity)
3. Tap orb (state transition)
   ✓ Spring animation smooth (0.4s response, 0.75 damping)
   ✓ No stuttering on older devices
```

**Test G3: Reduce Motion support**
```
Device Settings → Accessibility → Motion → Reduce Motion: ON

1. Start app
2. Observe animations
   ✓ Breathing animation disabled/minimal
   ✓ Orb still changes state (no animation)
   ✓ Status pill dots still pulse (but may be less frequent)
   ✓ Transitions instant or minimal (linear, 0.1s)
   ✓ App fully functional, not broken
```

---

### H. State Transitions & Edge Cases

**Test H1: Offline → Connecting → Ready**
```
1. App starts, server unreachable
   ✓ State: .offline (red status pill)
   ✓ Orb: desaturated, no glow, no animation
2. User hits "Reconnect"
3. Server responds
   ✓ State transitions: .offline → .connecting (amber) → .ready (green)
   ✓ Status pill color changes smoothly
   ✓ Each transition uses spring animation (0.4s, damping 0.75)
```

**Test H2: Session abort (network error mid-speech)**
```
1. User speaking, network drops
2. Observe
   ✓ State transitions to .offline (red)
   ✓ Transcript frozen (no new entries)
   ✓ Language lock still active
3. Tap "Reconnect"
   ✓ Language lock releases (if session properly terminated)
```

**Test H3: Hold-to-talk mode (press & release)**
```
Settings → Conversation Mode: "Hold-to-talk"

1. Press and hold orb
   ✓ Mic starts (.listening state)
   ✓ Status pill: green, "LISTENING"
2. Speak
3. Release orb
   ✓ Mic stops (.finalizing state)
   ✓ Status pill: amber, "PAUSING"
   ✓ Turn finalizes
4. Wait for translation
   ✓ Translating state activates
   ✓ TTS plays
```

---

## 📋 Regression Checklist

**Ensure existing functionality still works:**

- [ ] WebSocket connects correctly
- [ ] Audio capture starts/stops properly
- [ ] Transcript entries appear in correct order
- [ ] Settings (language, VAD, server URL) persist
- [ ] Diagnostics panel shows all events
- [ ] Reconnect banner works
- [ ] Audio toggle (speaker) works
- [ ] Hold-to-talk mode functional
- [ ] Hands-free mode functional
- [ ] Settings sheet opens/closes smoothly
- [ ] Voice activity detection still working
- [ ] TTS playback works
- [ ] No memory leaks during long sessions

---

## 🐛 Debugging Tips

### If language lock not showing:
```swift
// In ContentView.swift, check language bar:
if appState.isLanguageLocked {
    Text("locked") // Should appear
}

// Verify startSession/endSession are called:
// FlowCoordinator.startMic() → appState.startSession()
// FlowCoordinator.stop() → appState.endSession()
```

### If split panel not showing entries:
```swift
// Check TranscriptEntry model has id, source, translation
// Verify appState.transcript is populated
// Check ForEach loop in SplitConversationPanel

// Debug in diagnostics:
appState.addDiag("Transcript count: \(appState.transcript.count)", type: .info)
```

### If streaming cursor not blinking:
```swift
// Check StreamingCursor timer:
// onReceive(Timer.publish(every: 0.5, on: .main, in: .common))

// Verify animation runs:
withAnimation(.easeInOut(duration: 0.4)) {
    opacity = opacity == 1.0 ? 0.2 : 1.0
}
```

### If OrbView_ModeB not responding to audio:
```swift
// Check peak smoothing in OrbView_ModeB:
// onReceive(appState.$audioLevel) { level in
//    updateSmoothedPeak(Float(level))
// }

// Verify smoothing constant: 0.85*smooth + 0.15*raw
```

---

## ✅ Sign-Off Checklist

Before marking Mode B as complete:

- [ ] All UI components render without crashes
- [ ] Language lock prevents swap during session
- [ ] SplitConversationPanel shows both columns
- [ ] Streaming cursor animates correctly
- [ ] SoftStatusPill displays correct state with colors
- [ ] Turn boundaries detected (check diagnostics)
- [ ] OrbView_ModeB responds smoothly to audio (when integrated)
- [ ] Barge-in interrupts TTS
- [ ] No jank at 60 FPS
- [ ] Reduce Motion respected
- [ ] All existing features still work
- [ ] Tested on iPhone 14+ (glass effects)
- [ ] Tested on older iPhone (graceful degradation)

**Sign-off:** Once all checkboxes pass, Mode B is production-ready.

---

## 📝 Notes for Next Testing Phase

1. **OrbView_ModeB Integration:** Final integration into control dock pending
2. **Device Testing:** Requires physical iPhone 14+ for glass material effects validation
3. **Animation Tuning:** May need adjustment of smoothing constants (0.85/0.15) based on feel
4. **Performance Profile:** Use Xcode Instruments to profile on target device

---

**Testing guide created: 2026-02-13**
**Update interval: Before each deployment**
