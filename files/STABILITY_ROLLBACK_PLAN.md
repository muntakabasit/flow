# Stability Fix: Rollback & Recovery Plan

**Task**: iOS WebSocket Code=57 + Mobile Reliability
**Critical**: YES — affects all users on iOS/Android

---

## 📋 What Changed

### Frontend (index.html)
**Lines Modified**: ~150-200 lines across multiple sections
**Key Changes**:
- Added RECONNECTING, FAILED states
- Added keepalive timeout tracking (lastPongTime, keepaliveTimer, clientKeepaliveTask)
- Enhanced wsConnect() with state transitions + keepalive startup
- New startClientKeepalive() function
- Enhanced scheduleReconnect() with exponential backoff + jitter + cap
- Added pong/keepalive_pong message handlers
- Added lifecycle event listeners (visibilitychange, online, offline)

### Backend (server_local.py)
**Lines Modified**: ~30-40 lines
**Key Changes**:
- Enhanced keepalive() to send ping every 20s (not 30s) + logging
- Added handling for keepalive_ping, pong, keepalive_pong message types
- Graceful handling of these messages (respond immediately, no crash)

### No Breaking Changes
✅ All Phase 1 features preserved
✅ All message protocols backward compatible
✅ No database changes
✅ No configuration changes

---

## 🔄 Rollback Procedure (If Critical Bug)

### Quick Rollback (< 5 minutes)

#### Step 1: Revert Frontend
```bash
cd /Users/kulturestudios/BelawuOS/flow
git checkout HEAD -- static/index.html
```

#### Step 2: Revert Backend
```bash
git checkout HEAD -- server_local.py
```

#### Step 3: Restart Server
```bash
pkill -f server_local.py
sleep 2
python server_local.py
```

#### Step 4: Test
- Open http://localhost:8765
- Should load (may show old UI temporarily, that's OK)
- Speak, should translate
- If error persists, contact me

#### Step 5: Investigate
```bash
git diff HEAD~1 static/index.html > /tmp/changes.diff
# Review the diff to find the issue
```

---

## 🧪 Rollback Test (Before Deployment)

### Before Live Deployment
1. [ ] Apply stability fix (current commit)
2. [ ] Run full test checklist (STABILITY_TEST_CHECKLIST.md)
3. [ ] If ALL tests pass, mark "READY FOR DEPLOY"
4. [ ] If ANY test fails:
   - [ ] Note which test failed
   - [ ] Note error details
   - [ ] Do NOT deploy yet
   - [ ] Fix issue or rollback

### Quick Rollback Test
If needed, to verify rollback works:
```bash
git stash                    # Save current changes
python server_local.py        # Verify old code works
git stash pop                # Restore changes
python server_local.py        # Verify new code works
```

---

## ⚠️ Risks & Mitigations

### Risk 1: Keepalive Timeout Too Aggressive
**Symptom**: App disconnects after 40 seconds even on good connection
**Mitigation**: Adjust KEEPALIVE_TIMEOUT in index.html (line ~485)
**Rollback**: Change KEEPALIVE_TIMEOUT back to 60000 or 120000

### Risk 2: Exponential Backoff Too Long
**Symptom**: Users have to wait too long for first reconnect
**Mitigation**: Adjust BACKOFF array (line ~477)
**Rollback**: Change back to [500, 1000, 2000, 5000]

### Risk 3: Client Keepalive Spam
**Symptom**: Network logs show keepalive messages every second
**Mitigation**: Adjust KEEPALIVE_INTERVAL (line ~484, should be 20000ms)
**Rollback**: Increase interval or remove client keepalive

### Risk 4: Lifecycle Handlers Break Something
**Symptom**: App keeps disconnecting on visibilitychange
**Mitigation**: Comment out lifecycle handlers (lines ~1218-1240)
**Rollback**: Delete or disable the entire lifecycle section

### Risk 5: State Machine Breaks Speech Recognition
**Symptom**: Mic button doesn't work / audio doesn't send
**Mitigation**: This is unlikely (we didn't change audio logic), but check transition()
**Rollback**: Revert entire file if necessary

---

## 📊 Rollback Decision Tree

```
Is the app completely broken?
├─ YES → Immediate rollback (git checkout)
└─ NO → Investigate specific issue

Is Phase 1 functionality affected?
├─ YES (speaker labels, confidence, etc. broken) → Rollback
└─ NO → Proceed with debugging

Is it iOS-specific?
├─ YES → May be expected (different behavior on iOS)
└─ NO → Investigate further

Is it a performance issue?
├─ YES (app too slow after reconnect) → Adjust BACKOFF/TIMEOUT
└─ NO → Continue investigation

Is error message wrong/missing?
├─ YES → Edit error message, no rollback needed
└─ NO → Rollback if can't identify fix quickly
```

---

## 🔍 Before/After Comparison

### What Should Change (Improvements)
```
BEFORE:
- Connect with http:// (rare, but happens on iOS)
- No state machine UI feedback
- Simple backoff (no cap, no jitter)
- No client-side keepalive timeout
- No lifecycle handling
- Can hang on network transitions

AFTER:
✅ Always ws:// or wss://
✅ Clear state indication (IDLE, CONNECTING, READY, OFFLINE, FAILED)
✅ Exponential backoff with jitter + cap at 10
✅ Client-side keepalive timeout (40s)
✅ Auto-reconnect on foreground/online
✅ Graceful handling of network transitions
✅ NO MORE Code=57 on iOS network changes
```

### What Should NOT Change (Preserved)
```
✅ Speaker labels ("YOU" / "TRANSLATION")
✅ Confidence scoring (🟢 🟡 🔴)
✅ Session persistence (localStorage)
✅ Error messages (user-friendly)
✅ Audio playback (still works)
✅ Mic capture (still works)
✅ Transcript history (still preserved)
✅ All message protocols (backward compatible)
```

---

## 📞 Emergency Contacts

If rollback fails or something goes wrong:

1. **Immediate**: Run rollback procedure above
2. **If that fails**: Manually revert
   ```bash
   git reset --hard HEAD~1  # Go back 1 commit
   git clean -fd             # Clean up any temp files
   ```
3. **If still broken**: Restore from last known good
   ```bash
   git log --oneline | head -10  # Find last good commit
   git checkout <commit_hash>
   ```

---

## ✅ Sign-Off Before Deploying

Before deploying this fix to production, confirm:

- [ ] All tests in STABILITY_TEST_CHECKLIST.md PASS
- [ ] No Phase 1 regression detected
- [ ] iOS network transition works (no Code=57)
- [ ] Exponential backoff working correctly
- [ ] Keepalive timeout works (40s detection)
- [ ] Lifecycle handlers don't break mobile flow
- [ ] Tested on: Desktop Chrome, iOS Safari, Android Chrome
- [ ] Rollback procedure verified (tested `git checkout`)
- [ ] Ready for production deployment

**Signed by**: _________________
**Date**: _________________
**Status**: ✅ APPROVED FOR DEPLOY / ❌ NOT READY

---

## 🎯 Post-Deployment Checklist

After deploying to production:

1. [ ] Monitor error logs for Code=57
2. [ ] Monitor for "Keepalive timeout" messages
3. [ ] Monitor for reconnect spam
4. [ ] Check error rate (should be < 1%)
5. [ ] Check session completion rate (should be > 90%)
6. [ ] Monitor iOS-specific issues
7. [ ] Collect user feedback (are issues resolved?)

---

**This rollback plan is comprehensive and testable. You can revert this change in < 5 minutes if needed.** ✅

