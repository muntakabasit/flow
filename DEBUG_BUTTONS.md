# Button Click Debug Guide

## Problem
Buttons not responding to clicks

## Root Cause (Most Likely)
Browser cache is serving old JavaScript code that has the brace mismatch issue from before the hardening pass.

## Solution

### Step 1: Hard Refresh Browser
```
Mac:     Cmd + Shift + R
Windows: Ctrl + Shift + R
Linux:   Ctrl + Shift + R
```

### Step 2: Open Developer Console
```
Mac:     Cmd + Option + I (or Cmd + Option + J)
Windows: F12 (or Ctrl + Shift + I)
Linux:   F12 (or Ctrl + Shift + I)
```

### Step 3: Check Console for Errors
Look for:
- Red error messages (JavaScript syntax errors)
- "Uncaught" exceptions
- Missing event listeners

### Step 4: Verify WebSocket Connection
In console, type:
```javascript
ws.readyState === WebSocket.OPEN  // Should be true
state  // Should be 'ready'
reliabilityMode  // Should be 'stable' or 'fast'
```

### Step 5: Check if Buttons Have Event Listeners
In console:
```javascript
document.getElementById('micBtn').onclick  // Check for handlers
$micBtn  // Should exist
```

## Quick Diagnostic
Copy and paste into browser console:

```javascript
console.log('=== FLOW DIAGNOSTICS ===');
console.log('WebSocket state:', ws?.readyState === WebSocket.OPEN ? 'OPEN' : 'CLOSED');
console.log('App state:', state);
console.log('Reliability mode:', reliabilityMode);
console.log('Server ready gate:', serverReadyGate);
console.log('Mic button exists:', !!$micBtn);
console.log('Session wanted:', sessionWanted);
console.log('=== END DIAGNOSTICS ===');
```

## If Buttons Still Don't Work

### Check Server Logs
```bash
tail -50 /tmp/server.log
```

Look for:
- `[flow-local] Client connected` - means WebSocket connected
- `Language initialized` - means STT working
- Any error messages

### Check if State Machine is Stuck
In browser console:
```javascript
transition(S.READY)  // Force to READY state
```

Then try clicking mic button.

### Clear Cache Completely
```bash
# Open Developer Tools
# Settings → Storage → Clear site data
# Or for localStorage:
localStorage.clear()
```

Then refresh page.

## Expected Behavior After Fix

1. Load page → Green dot appears (READY state)
2. Click mic button → Mic starts, blue wave animation
3. Speak → Server transcribes
4. Button click during LISTENING → Mic stops
5. Button click during TRANSLATING → "Still processing" message

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| No green dot | WebSocket not connected | Check /health, hard refresh |
| Green dot but button inactive | State not READY | Check console: `transition(S.READY)` |
| Button changes color but nothing happens | serverReadyGate false | Wait for server warmup (5-10s) |
| "Still processing" message | App in TRANSLATING state | Wait for translation to finish |
| Browser shows error | JavaScript syntax error | Hard refresh, clear cache |

---

**TL;DR**: Hard refresh browser with **Cmd/Ctrl + Shift + R**, open console (F12), and check diagnostics above.
