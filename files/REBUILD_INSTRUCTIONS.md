# 🚀 Rebuild Instructions — iOS App Fix

**Problem**: Code=57 "Socket is not connected" errors on iOS
**Solution**: Rebuild app with fixed AppState.swift
**Time to fix**: 5 minutes

---

## ⚡ Quick Steps

### 1️⃣ Connect Your iPhone
```
1. Plug iPhone into Mac via USB cable
2. Trust this computer (if prompted on iPhone)
3. Wait 10 seconds for device to appear in Xcode
```

### 2️⃣ Clean Everything
```bash
# Delete old build cache
rm -rf ~/Library/Developer/Xcode/DerivedData/FlowInterpreter*
```

### 3️⃣ Rebuild in Xcode
```
1. Open Xcode
2. File → Open → Select FlowInterpreter.xcodeproj
3. Select your iPhone device in the top dropdown (NOT "iPhone Simulator")
4. Product → Clean Build Folder (Shift+Cmd+K)
5. Product → Run (Cmd+R)

Wait 2-3 minutes for build to complete...
App will install on your iPhone automatically
```

### 4️⃣ Verify on iPhone
```
1. Unlock your iPhone
2. FLOW app should open automatically
3. Should show green dot (ready state)
4. Tap Settings (gear icon)
5. Tap "Test Connection"
   → Should show ✓ "Server is running!"
6. Go back
7. Tap mic button
8. Speak: "Hello world"
9. Should show translation within 2 seconds

✅ If you see translation, the fix worked!
```

### 5️⃣ Test Network Transition (THE CRITICAL TEST)
```
1. App is open and connected (green dot)
2. Disable WiFi on iPhone (Settings → WiFi → toggle off)
3. App should show red dot (offline state)
   Wait 5 seconds
4. Enable WiFi (Settings → WiFi → toggle on)
5. App should return to green dot (ready state)

🎉 IF NO CODE=57 ERROR APPEARS → FIX IS WORKING! 🎉

Speak again to confirm translation still works
```

---

## 🔍 Troubleshooting

### Problem: "Device not showing in Xcode"
```
Solution:
1. Unplug iPhone
2. Restart Xcode
3. Wait 30 seconds
4. Plug iPhone back in
5. Trust this computer on iPhone
6. Try again
```

### Problem: "Build failed - provisioning profile"
```
Solution:
1. In Xcode, select FlowInterpreter project
2. Select FlowInterpreter target
3. General tab
4. Team: Select your personal team (should say "None")
5. Bundle Identifier: com.belawuos.flow.FlowInterpreter
6. Try Product → Run again
```

### Problem: "App shows red dot (offline) after rebuild"
```
Solution:
1. Check server is running: curl http://localhost:8765/health
   (Should show: {"status":"ok",...})
2. Check Ollama is running: pgrep ollama
   (Should show a number)
3. Wait 3 seconds
4. Tap Settings → Test Connection
   (Should show: ✓ Server is running!)
5. If test passes, tap back and wait 2 seconds
6. State should change to green (ready)
```

### Problem: "Still getting Code=57 error"
```
This means the old cached URL wasn't cleared. Try:
1. In Xcode, Product → Clean Build Folder (Shift+Cmd+K)
2. Delete app from iPhone (long press FLOW → Remove App → Delete App)
3. Product → Run (Cmd+R) to reinstall fresh
4. Check diagnostics on app for "Updated serverURL format" message
5. If not there, the fix didn't apply (contact support)
```

---

## ✅ Success Indicators

You'll know the fix worked when:
- ✅ App shows green dot (ready) without errors
- ✅ "Test Connection" shows "Server is running!"
- ✅ Speak → translation appears within 2 seconds
- ✅ Can complete 5+ translations
- ✅ NO Code=57 errors in device logs
- ✅ **WiFi off/on cycle works smoothly (no errors)**

---

## 📊 What Changed

**AppState.swift:**
- Default URL changed from `"http://192.168.0.116:8765"` to `"192.168.0.116:8765"`
- Added init() method to migrate old cached URLs
- Enhanced wsURL property to guarantee ws:// protocol

**Result:**
- All URLs now use ws:// protocol (not http://)
- URLSessionWebSocketTask won't reject with Code=57
- Network transitions work seamlessly

---

## 🎯 Next Steps After Rebuild

### If it works:
1. ✅ Test on WiFi
2. ✅ Test switching to Cellular (if available)
3. ✅ Test WiFi off/on cycle
4. ✅ Complete 10+ translations
5. ✅ Leave running for 5+ minutes

### If you encounter issues:
1. Check troubleshooting section above
2. Verify server/Ollama are running
3. Try clean rebuild (follow "Clean Everything" step)

---

## 🆘 Emergency Rollback

If something is completely broken and you need the old app back:
```bash
cd /Users/kulturestudios/BelawuOS/flow
git log --oneline FlowInterpreter/FlowInterpreter/Models/AppState.swift | head -5
# Find the commit before the fix
git checkout <previous-commit> -- FlowInterpreter/FlowInterpreter/Models/AppState.swift
# Rebuild with old version
```

---

## 💡 Key Points

- **DO NOT** change the server URL in Settings (should stay at 192.168.0.116:8765)
- **The app will automatically convert it to ws:// protocol**
- **Network transitions (WiFi ↔ Cellular) should now work**
- **No more Code=57 "Socket is not connected" errors**

---

**Time estimate**: 5 minutes
**Difficulty**: Easy
**Confidence**: High

**Let's fix this! 🚀**

