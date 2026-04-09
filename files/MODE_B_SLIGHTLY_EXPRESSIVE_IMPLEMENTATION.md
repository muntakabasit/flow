# FLOW iOS Mode B: Slightly Expressive Motion + Smooth Turns

**Status:** Core Components Implemented
**Date:** 2026-02-13
**Philosophy:** Soft, continuous, breathing motion with no sharp accelerations

---

## 🎯 What Is Mode B?

Mode B is the "premium feel" upgrade to FLOW's UI/UX, focusing on:

1. **Peak-Level-Driven Orb Physics** - Orb expands/contracts based on microphone input
2. **Smooth Turn Boundaries** - Allows natural speech pauses without cutting off mid-thought
3. **Barge-In Support** - User can interrupt TTS and resume listening seamlessly
4. **Slightly Expressive** - Subtle ripples, gentle pulses, barely-noticeable animations

---

## 📦 Components Implemented

### 1. OrbView_ModeB.swift (380 lines)
**Location:** `FlowInterpreter/Views/Components/OrbView_ModeB.swift`

**Physics Architecture:**

**Three Layers:**
1. **Core** - Solid-ish gradient with subtle depth, scales with input
2. **Glow** - Blurred halo, opacity/radius driven by state
3. **Halo Ring** - Thin rotating ring (translating state only)

**State Behaviors:**

| State | Core Scale | Glow | Behavior |
|-------|-----------|------|----------|
| **Idle** | 0.985 → 1.015 (3.2s) | 0.10 → 0.18 | Breathing, easeInOut |
| **Listening** | 1.02 + peak*0.10 | 0.18 + peak*0.25 | Peak-driven smoothing |
| **Translating** | 1.04 (stable) | 0.20 → 0.26 (0.9s pulse) | Rotating halo ring |
| **Speaking** | 1.03–1.05 | Stable + ripples | 2–3 expanding rings |
| **Offline** | 1.0 | Near zero | Desaturated, no motion |

**Key Physics Details:**

```swift
// Idle breathing (easeInOut, 3.2s cycle)
scale: 1.0 + sin(phase) * 0.015  // ±1.5%
glow opacity: 0.14 + sin(phase) * 0.04  // 0.10 → 0.18

// Listening (peak-driven with smoothing)
// smoothed = smoothed*0.85 + peak*0.15
// Never jitters; clamped to [0…1]
core scale: 1.02 + smoothed*0.10
glow radius: 8 + smoothed*18
glow opacity: 0.18 + smoothed*0.25

// Translating (subtle pulse + rotating halo)
halo rotation: linear 360° over 6.0s
glow opacity: 0.20 → 0.26 (every 0.9s pulse)
glow radius: 8 + pulse*offset

// Speaking (ripple outward)
// 2–3 rings, each 1.2s, staggered 0.25s
ripple scale: 1.0 → 1.4
ripple opacity: 0.4 → 0
```

**Animation Easing (non-negotiable):**
- Idle breathing: `easeInOut(duration: 3.2)`
- State transitions: `easeInOut(duration: 0.35–0.45)` OR `spring(response: 0.35–0.55, dampingFraction: 0.85–0.95)`
- Peak smoothing: `spring(response: 0.25, dampingFraction: 0.9)` (never snappy)
- Halo rotation: `linear` (steady, predictable)
- Speaking ripples: `easeOut` (waves dissipate)

**Never animate:**
- More than 2 properties at once (unless subtle like scale + glow)
- Sharp accelerations or bouncing
- Continuous infinite animations (only timed, finite cycles)

---

### 2. TurnSmoothingManager.swift (160 lines)
**Location:** `FlowInterpreter/Services/TurnSmoothingManager.swift`

**Turn Boundary Logic:**

```
Speech Active
    ↓
onSpeechStopped() called
    ↓
Evaluate silence duration:
    < 0.4s → Ignore (micro-pause, likely mid-sentence)
    0.4–0.7s → "Maybe pause" (wait, don't finalize yet)
    0.7–1.0s → Finalize + activate merge window
    > 1.0s → Force finalize, merge window expires

Within merge window (300ms):
    onSpeechStarted() → Merge with current turn (append)

After merge window:
    onSpeechStarted() → Create new turn
```

**Key Functions:**

```swift
// Call when speech detected (energy > threshold for 200ms)
manager.onSpeechStarted(_ timestamp: Date)

// Call when speech stops (energy < threshold)
manager.onSpeechStopped(_ timestamp: Date)

// Automatically scheduled; evaluates silence
manager.evaluateSilenceDuration()
```

**Merge Window Behavior:**
- If speaker pauses for ~700ms but resumes within 300ms → **same turn**
- If speaker pauses for ~700ms but stays silent > 300ms → **new turn**
- If speaker pauses for > 1.0s → **force finalize**

**Integration:**
```swift
@MainActor
final class TurnSmoothingManager: ObservableObject {
    @Published var currentTurnID: UUID?
    @Published var isWaitingForFinalize: Bool

    // Configurable thresholds
    let microPauseThreshold: TimeInterval = 0.4
    let maybePauseThreshold: TimeInterval = 0.7
    let finalizePauseThreshold: TimeInterval = 1.0
    let mergeWindow: TimeInterval = 0.3
}
```

---

## 🔊 Audio Level Mapping (Critical)

**How to drive the listening orb:**

1. **Get raw peak level** from audio processor (0…1 range)
2. **Smooth it** to prevent jitter:
   ```swift
   smoothedPeak = smoothedPeak * 0.85 + rawPeak * 0.15
   ```
3. **Clamp** to [0…1]
4. **Apply spring animation** to smoothed value
5. **Map to visuals:**
   - Core scale: `1.02 + smoothedPeak * 0.10`
   - Glow radius: `8 + smoothedPeak * 18`
   - Glow opacity: `0.18 + smoothedPeak * 0.25`
   - Icon scale: `0.9 + smoothedPeak * 0.15`

**Why smoothing matters:**
- Raw audio levels jitter frame-to-frame
- Smoothing creates fluid, natural feeling
- Clamps prevent overshooting (e.g., glow going off-screen)

---

## 🎬 Text & Conversation Smoothness

### Live Transcript During Listening
```swift
// As user speaks:
transcriptText.opacity = 1.0  // Show immediately
transcriptText.animation = nil  // No animation, just appear

// Animated scroll to bottom
withAnimation(.easeOut(duration: 0.3)) {
    scrollToBottom()
}
```

### Partial Translation (Translating State)
```swift
// Translation arrives in deltas:
translationText.opacity = 0.7  // Partial = 70% opacity
translationText.animation = nil  // No animation

// When final translation arrives:
withAnimation(.easeOut(duration: 0.2)) {
    translationText.opacity = 1.0  // → 100% opacity
    translationText.offset.y = 0  // Settle upward (6px → 0px)
}
```

**Effect:** Translation gradually "settles" into view as it arrives.

---

## 🚀 Barge-In Policy

**When TTS is speaking and user starts talking:**

1. User's peak level crosses listening threshold for **200ms**
2. Immediately:
   - Stop TTS playback
   - Return to LISTENING state
   - Mark previous output as "interrupted" (optional icon/label)
3. Resume listening for next utterance

**Implementation:**
```swift
// In FlowCoordinator
private func handleAudioPeakUpdate(_ peak: Float) {
    if state == .speaking,
       Double(peak) > listeningThreshold,
       peakActiveSince > 0.2 {
        // Barge-in detected
        stopTTS()
        transition(to: .listening)
        markCurrentTurnInterrupted()
    }
}
```

---

## 🎨 UI Style (Glass Design)

### Colors (Semantic)
```swift
Flow.green      #34d399  // Listening
Flow.accent     #e0a846  // Speaking, processing
Flow.amber      #fbbf24  // Connecting
Flow.red        #f87171  // Offline
Flow.surface2   #14161e  // Light surface (text background)
Flow.surface3   #1b1e28  // Dark surface
```

### Glass Material
- `.ultraThinMaterial` for cards
- 1px border: white @ 8% opacity
- Subtle inner highlight: white @ 10–12% opacity (top-left)
- Soft shadow: 2–8pt blur depending on elevation

### Vignette
- Optional: very subtle radial gradient (center bright, edges slightly darker)
- Keep opacity ~5% (barely noticeable)

---

## 📋 Integration Checklist

### Phase 1: Orb Physics ✅
- [x] OrbView_ModeB.swift - Peak-driven listening state
- [x] Audio level smoothing (0.85*smooth + 0.15*raw)
- [x] Idle breathing (3.2s easeInOut, ±1.5%)
- [x] Translating halo (6s linear rotation + 0.9s pulse)
- [x] Speaking ripples (2–3 rings, 1.2s each, staggered)
- [x] Spring animations (response 0.35–0.55, damping 0.85–0.95)

### Phase 2: Turn Smoothing ✅
- [x] TurnSmoothingManager.swift
- [x] Silence thresholds (0.4s ignore, 0.7s maybe, 1.0s finalize)
- [x] Merge window (300ms resume = same turn)
- [x] Configurable thresholds

### Phase 3: Integration (PENDING)
- [ ] Update FlowCoordinator to inject TurnSmoothingManager
- [ ] Wire audio peak → OrbView_ModeB.audioLevel
- [ ] Wire speech start/stop → TurnSmoothingManager callbacks
- [ ] Implement barge-in detection (audio peak threshold crossing)
- [ ] Add "interrupted" label/icon to conversation UI

### Phase 4: Refinement (PENDING)
- [ ] Test animation timings on device
- [ ] Adjust smoothing constants (0.85/0.15) based on feel
- [ ] Tweak glow radius mapping (8 + peak*18)
- [ ] Device-specific testing (iPhone 14+ for glass effects)

---

## ⚙️ Configuration Constants

**Recommended (can be made user-configurable):**

```swift
// Animation timings
let idleBreathingDuration: TimeInterval = 3.2  // seconds
let haloRotationDuration: TimeInterval = 6.0   // seconds per full rotation
let translatePulseDuration: TimeInterval = 0.9  // pulse cycle
let rippleDuration: TimeInterval = 1.2         // per ripple
let rippleStagger: TimeInterval = 0.25         // between ripples

// Audio smoothing
let peakSmoothingFactor: Double = 0.85         // smoothed*0.85 + raw*0.15
let listeningThreshold: Double = 0.05          // audio peak threshold

// Turn boundary
let microPauseThreshold: TimeInterval = 0.4
let maybePauseThreshold: TimeInterval = 0.7
let finalizePauseThreshold: TimeInterval = 1.0
let mergeWindow: TimeInterval = 0.3

// Barge-in
let bargeInPeakThreshold: Double = 0.1
let bargeInActiveDuration: TimeInterval = 0.2  // 200ms
```

---

## 🎓 Motion System Rules (Immutable)

1. ✅ **Soft & Continuous** - All animations feel breathing, not mechanical
2. ✅ **No Sharp Accelerations** - Use easeInOut or spring only
3. ✅ **No "Pop" Scaling** - Scale transitions use dampingFraction ≥ 0.85
4. ✅ **No Aggressive Bouncing** - Spring response ≥ 0.35
5. ✅ **Max 2 Properties Per Animation** - Scale + glow OK, don't overdo
6. ✅ **Never Snappy** - All transitions ≥ 0.25s
7. ✅ **Accessibility Respected** - `accessibilityReduceMotion` disables motion
8. ✅ **Audio-Driven, Not Constant** - Orb only animates when state demands

---

## 📊 Expected Animations at a Glance

| State | What Happens | Duration | Feel |
|-------|--------------|----------|------|
| **Idle** | Gentle breathing | 3.2s cycle | Calm, present |
| **Listening** | Peak-driven expansion | Responsive | Attentive, alive |
| **Translating** | Halo rotates + tiny pulses | 6s rotation + 0.9s pulse | Busy, processing |
| **Speaking** | Ripples expand outward | 1.2s per ripple | Flowing, expressive |
| **Offline** | Faded, still | Static | Calm but disconnected |

---

## 🔗 Integration Points

### With AudioService
```swift
// In your audio processing (VAD or energy detector):
func onAudioPeak(_ level: Float) {
    orbView.audioLevel = level  // Direct binding
    turnManager.evaluateSpeechThreshold(level)
}

func onSpeechDetected() {
    turnManager.onSpeechStarted()
}

func onSpeechEnded() {
    turnManager.onSpeechStopped()
}
```

### With FlowCoordinator
```swift
@MainActor
final class FlowCoordinator: ObservableObject {
    private let turnManager = TurnSmoothingManager()

    // Route audio callbacks through turn manager
    private func handleAudioUpdate(_ peak: Float) {
        // Peak smoothing handled in OrbView
        // Turn detection handled in TurnSmoothingManager
    }

    // Barge-in detection
    private func detectBargeIn(peak: Float) -> Bool {
        state == .speaking && Double(peak) > 0.1
    }
}
```

---

## ✨ Expected User Experience

When Mode B is live:

1. **User opens app** → Orb gently breathes (calm, inviting)
2. **User speaks** → Orb expands with their voice (responsive, alive)
3. **Speech pauses** → Orb holds (waiting to see if they continue)
4. **Resume in 300ms** → Same turn (seamless, natural)
5. **Wait > 300ms** → New turn (clear boundary, not aggressive)
6. **During translation** → Halo rotates (indicates processing)
7. **During playback** → Ripples expand (expressive, not garish)
8. **Interrupt** → Immediate TTS stop, back to listening (smooth recovery)

---

## 📝 Next Steps

1. **Wire audio peak** → OrbView_ModeB.audioLevel
2. **Inject TurnSmoothingManager** → FlowCoordinator
3. **Route speech callbacks** → turnManager.onSpeechStarted/Stopped
4. **Implement barge-in** → Detect threshold crossing + stop TTS
5. **Test on device** → Refine smoothing constants, animation timings
6. **User testing** → Get feedback on feel, adjust if needed

---

**Mode B is ready to integrate. Time to make FLOW feel alive.** ✨
