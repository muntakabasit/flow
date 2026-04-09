# Quick Test Guide - Bridge Mode ⚡

**Time Required:** 5-10 minutes
**Prerequisites:** Server running (`python server_local.py`)

---

## 🚀 Quick Start (2 minutes)

1. **Start server:**
   ```bash
   cd /Users/kulturestudios/BelawuOS/flow
   python server_local.py
   ```

2. **Open browser:**
   - URL: `http://localhost:8765`
   - **Hard refresh:** `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)

3. **Wait for page to load:**
   - Should see animated Voice Orb (breathing gently)
   - Status shows "LISTENING" under orb
   - Language bar shows "English ↔ Português"

---

## ✅ Test Checklist (5-7 minutes)

### Test 1: Voice Orb Animations (1 min)

1. Page loads → Orb is **IDLE** (calm, gray)
2. Open DevTools Console (F12) and watch for state transitions
3. **Expected:** State changes show in console
4. **Result:** ✅ or ❌

### Test 2: Natural Speech (1 min)

1. Speak: "Hello, how are you today?"
2. **Expected:**
   - Orb changes to LISTENING (breathing)
   - Audio streams while you speak
   - NO cut-off mid-sentence
3. **Result:** ✅ or ❌

### Test 3: TTS Playback (1 min)

1. After you finish speaking, wait for response
2. **Expected:**
   - Orb changes to TRANSLATING (fast pulse)
   - Then SPEAKING (glowing)
   - Translation plays as audio
3. **Result:** ✅ or ❌

### Test 4: Barge-In (1 min)

1. Wait for TTS to start playing
2. While TTS is still playing, start speaking again
3. **Expected:**
   - TTS stops immediately
   - Orb returns to LISTENING
   - You can speak without interruption
4. **Result:** ✅ or ❌

### Test 5: Language Switching (1 min)

1. Click settings button (⚙️ gear icon) near mic
2. Find "I speak" and "Translate to" selectors
3. Click "↔ Swap Languages" button
4. **Expected:**
   - Language bar updates to swapped direction
   - Settings close or remain open
   - Can speak in new language direction
5. **Result:** ✅ or ❌

### Test 6: Hold-to-Talk Mode (1 min)

1. Click settings button again
2. Find "Hold to Talk" checkbox
3. Enable it
4. Close settings
5. **Press and hold** mic button, speak, then **release**
6. **Expected:**
   - Mic captures only while holding
   - Releases on button release (no click needed after)
   - Speech is finalized immediately on release
7. **Result:** ✅ or ❌

### Test 7: Premium Bubbles (1 min)

1. Look at the transcript (conversation history)
2. **Expected:**
   - Your text appears in neutral gray bubble
   - Translation appears in warm amber-tinted bubble
   - Each bubble has rounded corners and shadow
   - Hovering over bubble shows enhanced shadow
3. **Result:** ✅ or ❌

---

## 🐛 Troubleshooting

| Issue | Fix |
|-------|-----|
| Orb not animating | Hard refresh browser (Cmd+Shift+R) |
| Settings button missing | Check F12 console for errors |
| Speech gets cut off | Server timeout may be too short; check server logs |
| Barge-in doesn't work | Verify TTS is actually playing; check console |
| Language swap button missing | Clear browser cache, hard refresh |
| Bubbles look flat/ugly | CSS not loading; check console for 404s |

---

## 📸 Visual Checklist

- [ ] Orb is circular SVG (not rectangle)
- [ ] Orb has concentric circles visible
- [ ] Orb center has small filled circle
- [ ] Bubbles have rounded corners (12px)
- [ ] Translation bubble has warm tint
- [ ] Labels are visible and clear
- [ ] Hover effects work smoothly
- [ ] No layout jank or jumping

---

## 🔊 Audio Checklist

- [ ] Mic captures naturally without cuts
- [ ] TTS audio plays clearly
- [ ] Barge-in stops TTS immediately (no delay)
- [ ] Volume levels are appropriate
- [ ] No feedback loops or echo

---

## 📊 Performance Checklist

- [ ] Animations run smoothly (60fps - no stuttering)
- [ ] Orb animations are fluid, not jerky
- [ ] State transitions are instant
- [ ] No lag when typing/clicking
- [ ] Page loads in <2 seconds

---

## ✨ Overall Feel Check

After all tests, ask yourself:

- [ ] Does the app feel **premium** (not generic/demo)?
- [ ] Are interactions **smooth and responsive**?
- [ ] Is the UI **clear and intuitive**?
- [ ] Do I understand what **state the app is in** at all times (via orb + label)?
- [ ] Does the **conversation flow naturally** without interruptions?
- [ ] **Would I use this app daily** to translate conversations?

**If all boxes checked: ✅ Bridge Mode is successful!**

---

## 📝 Notes

- All data persists in localStorage:
  - Hold-to-Talk preference
  - Language settings
  - Sensitivity/delay preferences

- Server must support `language_config` message type
- Barge-in works best if server's TTS implementation supports quick stop

---

**Happy Testing! 🚀**
