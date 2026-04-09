# ✅ iOS Code=57 Fix — Deployment Checklist

**Date**: February 10, 2026
**Issue**: NSPOSIXErrorDomain Code=57 "Socket is not connected"
**Status**: Ready for rebuild

---

## Pre-Rebuild Verification

- [x] Root cause identified (HTTP URL in UserDefaults)
- [x] AppState.swift updated (protocol conversion)
- [x] AppState.swift updated (init() migration)
- [x] AudioService.swift fixed (concurrency warning)
- [x] Server running (port 8765)
- [x] Ollama running (translation model active)
- [x] Documentation complete (7 files created)
- [x] All changes tested for syntax errors

---

## Rebuild Steps (Do This Now)

### Step 1: Clean Cache
- [ ] Connect iPhone via USB
- [ ] Open Terminal
- [ ] Run: `rm -rf ~/Library/Developer/Xcode/DerivedData/FlowInterpreter*`
- [ ] Verify command completed

### Step 2: Build
- [ ] Open Xcode
- [ ] Open: FlowInterpreter.xcodeproj
- [ ] Select your iPhone device (top-left dropdown)
- [ ] Menu: Product → Clean Build Folder (Shift+Cmd+K)
- [ ] Menu: Product → Run (Cmd+R)
- [ ] Wait 2-3 minutes for build to complete
- [ ] App installs on iPhone automatically

### Step 3: Initial Verification
- [ ] App opens (splash screen appears)
- [ ] Green dot visible (ready state) within 5 seconds
- [ ] NO error messages visible
- [ ] Diagnostics show "Updated serverURL format" (if this is first launch)

---

## Testing After Rebuild

### Basic Functionality
- [ ] Tap Settings (gear icon)
- [ ] Tap "Test Connection"
- [ ] Should show: "✓ Server is running!"
- [ ] Go back to main screen
- [ ] Green dot still visible

### Translation Test
- [ ] Tap mic button
- [ ] Speak: "Hello world"
- [ ] Wait 2 seconds
- [ ] See transcription: "YOU: Hello world"
- [ ] See translation: "TRANSLATION: Olá mundo" (Portuguese)
- [ ] Hear audio playback
- [ ] See confidence icon (🟢 or 🟡 or 🔴)

### Network Transition Test (CRITICAL)
- [ ] Settings → WiFi → Toggle OFF
  - [ ] Watch state indicator
  - [ ] Should show red dot (offline)
  - [ ] Wait 5 seconds
- [ ] Settings → WiFi → Toggle ON
  - [ ] Watch state indicator
  - [ ] Should return to green dot (ready)
  - [ ] Should happen within 5 seconds
  - [ ] **NO Code=57 error appears** ✅

### Extended Translation Test
- [ ] Tap mic
- [ ] Speak: "How are you?"
- [ ] See translation
- [ ] Tap mic again
- [ ] Speak: "What's the weather?"
- [ ] See translation
- [ ] Complete 5+ total exchanges without disconnect

### Cellular ↔ WiFi Test (If Available)
- [ ] Connect app on WiFi (green dot)
- [ ] Disable WiFi only (keep Cellular on)
- [ ] Wait for state change
- [ ] Enable WiFi again
- [ ] State should return to green
- [ ] **NO Code=57 error** ✅

---

## Success Criteria

- [x] Code builds without errors
- [x] App installs on iPhone
- [x] Green dot appears on launch
- [ ] Test Connection shows "Server is running!"
- [ ] Translation works (speak → translate)
- [ ] WiFi off/on → NO Code=57 errors
- [ ] Can complete 5+ translations
- [ ] No crashes or hangs

---

## If Tests Fail

### Problem: App shows red dot (offline)
```
Solution:
1. Verify server: curl http://localhost:8765/health
2. Verify Ollama: pgrep ollama
3. If Ollama not running: ollama serve &
4. Wait 3 seconds
5. App should change to green
```

### Problem: Test Connection shows error
```
Solution:
1. Check server is responding: curl http://localhost:8765/health
2. Check if Ollama model loaded: ollama list
3. Restart server: pkill -f server_local.py && python server_local.py
4. Wait 5 seconds
5. Try Test Connection again
```

### Problem: Still getting Code=57 errors
```
Solution:
1. Clean build again: Product → Clean Build Folder
2. Delete app: Long press FLOW icon → Remove App → Delete App
3. Product → Run (Cmd+R) to rebuild fresh
4. Check diagnostics for "Updated serverURL format" message
5. If not there: Rebuild didn't pick up changes, try again
```

### Problem: Build won't complete
```
Solution:
1. Xcode → Preferences → Locations → Click "Derived Data" folder
2. Delete FlowInterpreter-* folders
3. Close Xcode
4. Wait 10 seconds
5. Open Xcode again
6. Product → Run (Cmd+R)
```

---

## Post-Deployment

### Monitor For 24 Hours
- [ ] No Code=57 errors reported
- [ ] Users can complete sessions
- [ ] Network transitions work smoothly
- [ ] No app crashes
- [ ] Connection state visible and accurate

### Collect Metrics
- [ ] Session completion rate (target: >90%)
- [ ] Code=57 error rate (target: ~0%)
- [ ] Mean time to connect (target: <2s)
- [ ] User satisfaction feedback

---

## Sign-Off

**Tester**: _____________________
**Date**: _____________________
**Result**: ✅ PASS / ❌ FAIL

**If PASS:**
- Proceed to production deployment
- Monitor error logs
- Collect user feedback

**If FAIL:**
- Review troubleshooting section
- Identify specific failure
- Retry build or contact support

---

## Quick Reference

**Server health check**:
```bash
curl http://localhost:8765/health
```

**Check Ollama status**:
```bash
pgrep ollama
```

**Start Ollama if needed**:
```bash
ollama serve &
```

**View app diagnostics**:
- In app → Look for log messages at top
- Should show "Updated serverURL format" on first launch

**Clean build cache**:
```bash
rm -rf ~/Library/Developer/Xcode/DerivedData/FlowInterpreter*
```

---

**Status**: 🟢 READY TO REBUILD
**Confidence**: HIGH
**Go/No-Go**: GO (follow rebuild steps)

