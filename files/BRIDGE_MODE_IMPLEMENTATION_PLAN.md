# BRIDGE MODE Implementation Plan

## Current State Analysis

### Existing UI Structure
- Header with logo + state pill
- Reconnect banner
- Language bar (EN ↔ PT)
- Transcript (2-column: source | target)
- Control dock with waveform + mic button + side buttons

### Existing Functionality
✅ State machine (8 states: idle, connecting, ready, listening, translating, speaking, offline, failed)
✅ Pill with state indicators + animations
✅ Reconnect button + backoff logic
✅ Language direction display
✅ Transcript with real-time updates
✅ Mic button with waveform
✅ VAD client-side (RMS-based)
✅ Barge-in support

### Gaps for Bridge Mode
❌ No prominent language direction pill (EN → PT visual)
❌ No orb-style breathing animation
❌ No "hold to center" layout (conversation panes are content-full)
❌ State label not under orb (stuck in header)
❌ Waveform bars not optimized for "invisible UI" feel
❌ No distinct "You said" / "Translation" visual separation

---

## Bridge Mode Design Changes

### Layout Change
**Before:**
```
Header (logo + pill in top-right)
Reconnect banner (conditional)
Language bar
Transcript (2-column grid)
Control dock (waveform + mic + buttons)
```

**After (Bridge Mode):**
```
Header (minimal — just logo)
Language Pair Pill (EN ↔ PT, tappable)
Conversation Panes (live transcript + translation, centered)
Mic Orb (breathing/pulsing) + State Label
Offline banner (conditional, bottom)
```

### Visual Hierarchy Changes

1. **Language Pill** moves to prominence
   - Centered below header
   - Shows EN ↔ PT-BR with arrow
   - Tappable to change direction mode

2. **Conversation Panes** become central focus
   - Two stacked cards (bubbles)
   - Top: "You said" (what was heard)
   - Bottom: "Translation" (what will be spoken)
   - Smooth fade-in animations

3. **Mic Orb** becomes primary control
   - Replaces generic button
   - Breathing pulse while LISTENING
   - Soft glow while SPEAKING
   - Centered below conversation
   - State label underneath (single word)

4. **Offline UX** at bottom
   - Banner shows "Connection lost"
   - Reconnect button visible

---

## Implementation Strategy

### CSS Changes (incremental updates)

1. **Add Bridge Mode layout classes**
   - `.bridge-layout` container wrapper
   - `.lang-pill-bridge` (centered, prominent)
   - `.conversation-hub` (centered panes)
   - `.orb-container` (orb + state label)

2. **Orb animations**
   - `.orb.breathing` (LISTENING state)
   - `.orb.glowing` (SPEAKING state)
   - `.orb.dim` (OFFLINE state)

3. **Typography**
   - Increase transcript font size
   - Add "You said" label above source
   - Add "Translation" label above target
   - Center-align text in panes

4. **Responsive**
   - Mobile-first: full-width panes
   - Tablet+: side-by-side panes (optional)

### JavaScript Changes (minimal)

1. **Map existing state machine to orb animations**
   - LISTENING → breathing pulse
   - SPEAKING → steady glow
   - OFFLINE → dim
   - Trigger via `transition()` function

2. **Language pill tap handler**
   - Show mode selection sheet
   - Store preference
   - Update display

3. **Transcript formatting**
   - Add labels ("You said" | "Translation")
   - Improve styling

---

## Deliverables

### Files to Modify
1. `static/index.html` — CSS + minimal JS

### Changes Summary
- ~200 lines of CSS for Bridge Mode styles
- ~50 lines of JS for language mode handling
- No new files
- Backward compatible (existing functionality untouched)

---

## Testing Checklist
- [ ] Language pill tappable + mode selection works
- [ ] Orb breathes during LISTENING
- [ ] Orb glows during SPEAKING
- [ ] Transcript shows clear "You said" / "Translation" labels
- [ ] Offline banner appears at bottom
- [ ] State transitions smooth and no jank
- [ ] Mobile layout responsive
- [ ] All existing features still work

---

## Non-Breaking Changes
- Keeps existing state machine
- Keeps existing reconnect logic
- Keeps existing VAD logic
- Keeps existing audio pipeline
- Purely cosmetic + UX layering
