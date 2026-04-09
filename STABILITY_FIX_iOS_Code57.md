# STABILITY FIX: iOS Socket Code=57 Error

## 🔍 DIAGNOSIS

### The Problem: NSPOSIXErrorDomain Code=57
**What it means**: "Socket is not connected"
**Root cause**: Attempting to establish WebSocket over HTTP protocol instead of WS protocol

### Why This Happens on iOS Safari
1. **iOS Safari PWA limitations** — Sometimes doesn't properly detect `https://` on first load
2. **Network transition** — When switching from cellular to WiFi (or vice versa), socket state can get confused
3. **Fragile reconnect** — Without state machine, client thrashes attempting connections
4. **No keepalive timeout** — Connection appears alive but is actually dead, leading to hung state
5. **No lifecycle handling** — App backgrounded/foregrounded without proper socket cleanup

### Current Code Issues
```javascript
// Line 893-894 in index.html
const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
ws = new WebSocket(`${proto}//${location.host}/ws`);
```

**Why this fails on iOS**:
- ✅ URL construction is actually correct
- ❌ But NO state machine to track actual connection state
- ❌ But NO client-side keepalive timeout (relies only on server ping)
- ❌ But NO lifecycle handlers (backgrounding breaks connection)
- ❌ But NO exponential backoff (thrashing reconnects drain battery)

### The Real Problem
iOS has aggressive connection cleanup. When the browser is backgrounded or network changes, iOS closes sockets. Without proper lifecycle handling + timeout detection, client is left in `CONNECTING` state forever, unable to recover.

---

## ✅ THE FIX

### 1. Client-Side State Machine (ws:// is already correct, but state tracking is missing)
Add proper connection state + UI indication

### 2. Client-Side Keepalive Timeout
Server sends ping, client MUST respond with pong within timeout or DIE socket

### 3. Mobile Lifecycle Handlers
- `visibilitychange` → Reconnect on foreground
- `online`/`offline` events → Respect network state
- `beforeunload` → Clean disconnect

### 4. Exponential Backoff with Jitter
Stop thrashing, be respectful to battery/network

### 5. Connection State UI
Show user what's happening

---

## 📋 CHANGES REQUIRED

### A. Frontend (index.html)
1. Add `lastPongTime` tracking
2. Add connection state enum + UI indicator
3. Add `checkKeepalive()` timer (validates pong responses)
4. Add lifecycle event handlers
5. Enhance `scheduleReconnect()` with exponential backoff + cap

### B. Server (server_local.py)
1. Enhance keepalive to send ping every 20s (not 30s, for iOS responsiveness)
2. Add pong receipt tracking (optional, for advanced diagnostics)
3. No major changes needed — keep simple

---

## 🎯 SUCCESS CRITERIA

After fix, iOS Safari should:
1. ✅ Connect on first load (ws:// not http://)
2. ✅ Show connection state visually
3. ✅ Survive network transitions (cellular → WiFi)
4. ✅ Recover from backgrounding
5. ✅ Not thrash on reconnect (exponential backoff)
6. ✅ Timeout on hung socket (client-side keepalive)
7. ✅ Show "Tap to reconnect" after X failed attempts

---

## 🧪 TEST PLAN

### Desktop Chrome
- [ ] Open app
- [ ] Should show "ready" state
- [ ] Stop server, wait 20s
- [ ] Should transition to "offline"
- [ ] Restart server within 2 min
- [ ] Should reconnect automatically
- [ ] Should recover conversation history

### iOS Safari
- [ ] Open app on home screen
- [ ] Should show "ready" state
- [ ] Background app (home button)
- [ ] Wait 10s
- [ ] Foreground app (tap icon)
- [ ] Should reconnect to server
- [ ] Speak, should translate

### iOS Safari (Network Change)
- [ ] Open app on cellular
- [ ] Should connect
- [ ] Switch to WiFi mid-session
- [ ] Should NOT show Code=57
- [ ] Should continue translating

### Android Chrome
- [ ] Open app
- [ ] Should show "ready"
- [ ] Go offline (airplane mode)
- [ ] Should show "offline"
- [ ] Go online
- [ ] Should reconnect

---

## ⚠️ CONSTRAINTS MET

✅ Minimal diffs — only touch WebSocket + lifecycle
✅ No new frameworks — vanilla JS only
✅ Preserve Phase 1 — all features untouched
✅ Backward compatible — server changes minimal
✅ Revertible — can roll back in <5 min

