# Quick Start - Test the Fix

## ⚡ 30-Second Setup

```bash
cd /Users/kulturestudios/BelawuOS/flow
python server_local.py
```

Open browser: `http://localhost:8765`
**Hard refresh:** `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)

---

## ✅ What to Expect (Restored Behavior)

| Step | What Happens | Expected |
|------|-------------|----------|
| Page loads | Auto-connects to server | ✓ Shows LISTENING (not READY) |
| You speak | App captures audio continuously | ✓ Doesn't cut off mid-sentence |
| TTS plays | Server responds with translation | ✓ You hear the response |
| Audio finishes | App auto-resumes listening | ✓ NO CLICK NEEDED - just speak again |

---

## 🎯 Quick Test (1 minute)

1. **Page loads** → Wait 2 seconds → Should show "LISTENING"
2. **Say:** "Hello world" → Wait for response
3. **Immediately say:** "How are you?" → WITHOUT clicking anything
4. **Expected:** Both sentences processed as separate turns

---

## 🐛 If It Doesn't Work

| Problem | Check |
|---------|-------|
| App shows READY (not LISTENING) on load | `sessionWanted = true` on line 1057? |
| App stuck on SPEAKING | Is `turn_complete` arriving? Check diagnostics |
| Can't speak without clicking mic | Is auto-resume code present (lines 1261-1267)? |
| App cuts off mid-sentence | Is server SILENCE_DURATION_MS = 2000? |

---

## 📋 Two Key Changes

### **Change 1: Line 1057**
```javascript
let sessionWanted = true;    // ← Auto-start on page load
```

### **Change 2: Lines 1261-1267**
```javascript
if (sessionWanted && prev === S.SPEAKING) {
  setTimeout(() => { if (state === S.READY) startMic(); }, 100);
}  // ← Auto-resume after TTS
```

---

**That's it!** The app should now work smoothly. 🚀

See `TESTING_FIX_CONTINUOUS_FLOW.md` for detailed testing steps.
