# Mode B: Quick Start Guide for Developers

**Date:** 2026-02-13
**Audience:** iOS developers integrating Mode B
**Read Time:** 5 minutes

---

## 🎯 What is Mode B?

Mode B is FLOW's "Slightly Expressive" motion mode that makes the app feel alive and responsive while maintaining premium polish. Key features:

- **Peak-level-driven orb:** Expands/contracts with your voice
- **Smooth turn boundaries:** Natural speech pauses without cutting off
- **Barge-in support:** Interrupt TTS seamlessly
- **Glass UI:** Modern, professional appearance

---

## 📦 What's Included?

### Core Components (Already Created)
```
OrbView_ModeB.swift          # Peak-responsive orb animation
TurnSmoothingManager.swift   # Turn boundary detection
SplitConversationPanel.swift # Two-column conversation UI
```

### Modified Files
```
AppState.swift        # Added language lock
FlowCoordinator.swift # Wired turn manager + session management
ContentView.swift     # Updated UI layout
```

### Documentation
```
MODE_B_SLIGHTLY_EXPRESSIVE_IMPLEMENTATION.md  # Technical spec
MODE_B_INTEGRATION_SUMMARY.md                 # Integration points
INTEGRATION_PATCHES.md                        # Exact code changes
MODE_B_TESTING_GUIDE.md                       # Testing checklist
```

---

## 🚀 Getting Started (3 Steps)

### Step 1: Review the Documentation (15 min)
```bash
# Read these in order:
1. MODE_B_SLIGHTLY_EXPRESSIVE_IMPLEMENTATION.md
2. MODE_B_INTEGRATION_SUMMARY.md
3. INTEGRATION_PATCHES.md (see exact code changes)
```

### Step 2: Examine the New Components (10 min)
```swift
// OrbView_ModeB.swift
// - 3-layer architecture: core, glow, halo ring
// - Peak-level smoothing: smoothed = smoothed*0.85 + raw*0.15
// - Spring animations: response 0.35-0.55, damping 0.85-0.95

// TurnSmoothingManager.swift
// - Silence thresholds: 0.4s, 0.7s, 1.0s
// - Merge window: 300ms resume = same turn

// SplitConversationPanel.swift
// - Left column: YOU (source)
// - Right column: THEM (translation)
// - Streaming cursor with blinking animation
```

### Step 3: Verify Integration (5 min)
```swift
// Check FlowCoordinator changes:
let turnSmoothingManager = TurnSmoothingManager() // Exists?
turnSmoothingManager.onSpeechStopped(Date())      // Wired?
appState.startSession()                           // Language lock active?

// Check AppState changes:
appState.isLanguageLocked                         // Property exists?
appState.sessionStartLanguages                    // Stored tuple?

// Check ContentView changes:
SoftStatusPill(appState: appState)               // Header updated?
SplitConversationPanel(appState: appState)       // Transcript replaced?
```

---

## 🔑 Key Concepts

### 1. Peak-Level Smoothing
```swift
// Raw audio peaks jitter frame-to-frame (0-60 times/sec)
// Solution: Exponential moving average

smoothedPeak = smoothedPeak * 0.85 + rawPeak * 0.15

// Result: Smooth, responsive expansion without jitter
```

### 2. Turn Boundary Logic
```
Silence detected
    ↓
< 0.4s → Ignore (micro-pause, likely mid-sentence)
0.4-0.7s → Prepare (wait, don't finalize yet)
0.7-1.0s → Finalize + activate merge window
> 1.0s → Force finalize

Within merge window (300ms):
  - If speech resumes → Merge with current turn
  - If silence continues → New turn
```

### 3. Language Lock
```swift
// Prevents confusing language swaps during conversation

startSession() {
    sessionStartLanguages = (current input, current output)
}

swapLanguages() {
    if isLanguageLocked {
        addDiag("Language locked during session")
        return  // Don't swap!
    }
    // Perform swap
}

endSession() {
    sessionStartLanguages = nil  // Unlock
}
```

---

## 📝 Common Tasks

### Task 1: Check If Language Lock Is Working
```swift
// In ContentView.swift, language bar section:

if appState.isLanguageLocked {
    // Show "locked" badge
    // Disable swap button
}

// Verify:
// 1. appState.startSession() called in FlowCoordinator.startMic()
// 2. appState.endSession() called in FlowCoordinator.stop()
```

### Task 2: Wire OrbView_ModeB to Control Dock
```swift
// Replace MicButton with OrbView_ModeB in ContentView.controlDock:

VStack(spacing: 24) {
    OrbView_ModeB(appState: appState) {
        coordinator.userToggle()
    }
    .frame(width: 160, height: 160)

    // Optional: keep waveform
    WaveformView(level: appState.audioLevel, isActive: appState.state.isLive)
        .frame(height: 20)
}
```

### Task 3: Check Turn Boundary Detection
```swift
// In FlowCoordinator, handleServerMessage():

case .speechStopped:
    appState.transition(.finalizing)
    turnSmoothingManager.onSpeechStopped(Date())  // ✓ Wired?

// Verify in AppState diagnostics:
// - "Finalize: silence > 700ms" messages appear
// - Turn IDs change when new turn starts
```

### Task 4: Debug Streaming Cursor
```swift
// In SplitConversationPanel.swift, ConversationColumn:

StreamingCursor(color: streamingCursorColor)  // Should blink

// Expected behavior:
// 1. Blinking at end of translation text
// 2. Amber color during translation
// 3. 0.4s blink cycle (visible → faded → visible)
```

---

## 🐛 Troubleshooting

### Issue: Language lock badge not appearing
```
✓ Check: appState.sessionStartLanguages not nil
✓ Check: startSession() called in startMic()
✓ Check: isLanguageLocked computed property returns true
✓ Debug: Add appState.addDiag("Lock: \(appState.isLanguageLocked)", type: .ok)
```

### Issue: Orb not responding to audio (when integrated)
```
✓ Check: appState.audioLevel is updating (FlowCoordinator line 37)
✓ Check: OrbView_ModeB observing audioLevel changes
✓ Check: Smoothing running: smoothedPeak = smoothed*0.85 + raw*0.15
✓ Check: Spring animation active (response 0.25, damping 0.9)
```

### Issue: Turn boundaries not detected
```
✓ Check: TurnSmoothingManager instantiated in FlowCoordinator.init()
✓ Check: onSpeechStopped() called in handleServerMessage
✓ Check: Silence thresholds configured (0.4, 0.7, 1.0)
✓ Debug: appState.addDiag("Turn finalized", type: .ok) in evaluateSilenceDuration()
```

### Issue: Split panel not showing entries
```
✓ Check: SplitConversationPanel(appState: appState) in ContentView
✓ Check: appState.transcript populated with entries
✓ Check: TranscriptEntry has id, source, translation fields
✓ Check: ForEach iterating correctly over entries
```

---

## ✅ Pre-Flight Checklist

Before testing on device:

- [ ] All files compile without errors
- [ ] No warnings in Xcode build log
- [ ] OrbView_ModeB imported in views that use it
- [ ] TurnSmoothingManager imported in FlowCoordinator
- [ ] SplitConversationPanel replaced TranscriptView in ContentView
- [ ] appState.startSession() called in startMic()
- [ ] appState.endSession() called in stop()
- [ ] Language bar shows lock badge during session
- [ ] Swap button disabled when isLanguageLocked == true

---

## 📊 Performance Targets

When testing on device:

```
✓ Animations: 60 FPS (no dropped frames)
✓ CPU (listening): < 20% usage
✓ Memory: < 50MB total app memory
✓ Latency: Peak response < 250ms (audio to visual)
✓ Smoothness: No jitter or stuttering
```

---

## 🔗 Key Files at a Glance

| File | Purpose | Key Classes |
|------|---------|------------|
| OrbView_ModeB.swift | Peak-responsive orb | `OrbView_ModeB` |
| TurnSmoothingManager.swift | Turn boundaries | `TurnSmoothingManager` |
| SplitConversationPanel.swift | Two-column UI | `SplitConversationPanel`, `ConversationColumn` |
| AppState.swift | State management | `@Published var sessionStartLanguages` |
| FlowCoordinator.swift | Service wiring | `turnSmoothingManager` property |
| ContentView.swift | Main layout | Header + SplitPanel + ControlDock |

---

## 🎓 Learn More

**Full Documentation:**
- `MODE_B_SLIGHTLY_EXPRESSIVE_IMPLEMENTATION.md` (technical deep dive)
- `MODE_B_INTEGRATION_SUMMARY.md` (architecture overview)
- `MODE_B_TESTING_GUIDE.md` (comprehensive test cases)
- `INTEGRATION_PATCHES.md` (exact code diffs)

**Code References:**
```swift
// OrbView_ModeB: Lines 50-100 (audio smoothing)
// TurnSmoothingManager: Lines 60-120 (debounce logic)
// SplitConversationPanel: Lines 50-120 (split layout)
```

---

## ❓ FAQ

**Q: Can I test without device?**
A: Yes! Simulator works, but glass effects won't be visible. Use Preview for quick iteration.

**Q: Can I adjust animation timings?**
A: Yes! See configuration constants in OrbView_ModeB.swift (idleBreathingDuration, haloRotationDuration, etc.)

**Q: What if turn detection fails?**
A: Check server is sending .speechStarted/.speechStopped messages. Enable diagnostics panel to debug.

**Q: Can I disable language lock?**
A: Yes, comment out appState.startSession() in startMic(). But don't recommend for users!

**Q: Is barge-in configurable?**
A: Yes! Threshold = appState.vadSensitivity (0.08-0.9). Debounce = 0.6s (in handlePossibleBargeIn).

---

## 🚀 Next Steps

1. **Review Documentation** (15 min)
2. **Examine Components** (10 min)
3. **Verify Integration** (5 min)
4. **Build & Test on Simulator** (10 min)
5. **Test on Device** (30 min + refinement)

**Total estimated time:** 1-2 hours for full integration review

---

**Mode B is ready to integrate. Good luck!** 🎉

For questions, see MODE_B_TESTING_GUIDE.md or reach out to the team.
