# Background Sync Testing Guide

## Quick Test Scenarios

### Test 1: Basic Upload with Status Badge (2 minutes)

**Objective:** Verify status badges appear and update correctly

1. Open http://localhost:8000 in Chrome/Edge
2. Click "Record" button
3. Record for 5 seconds
4. Click "Stop" button
5. **Expected:** Blue badge appears with "⇪ X%" showing progress
6. Wait for upload to complete
7. **Expected:** Badge changes to "✓ SYNCED" (green) for 5 seconds, then disappears

**Success Criteria:**
- ✅ Badge appears immediately after recording stops
- ✅ Progress percentage increases (0% → 100%)
- ✅ Badge turns green when complete
- ✅ Badge disappears after 5 seconds

---

### Test 2: Offline Recording (5 minutes)

**Objective:** Verify uploads pause/resume on connection changes

1. Open http://localhost:8000
2. Click "Record" button
3. Record for 3 seconds
4. **While recording:** Open DevTools Network tab → Set "Offline"
5. **Expected:** Badge changes to "⏸ PAUSED" (yellow)
6. Continue recording for 3 more seconds
7. Click "Stop"
8. **Expected:** Badge still shows "⏸ PAUSED"
9. **Check Console:** Should see "Connection lost" messages
10. Set Network back to "Online"
11. **Expected:** Badge changes to "⇪ X%" (blue) and uploads resume
12. Wait for completion
13. **Expected:** Badge changes to "✓ SYNCED" (green)

**Success Criteria:**
- ✅ Badge turns yellow when offline
- ✅ Chunks queue in IndexedDB (check Application tab)
- ✅ Badge turns blue when back online
- ✅ Uploads resume automatically
- ✅ All chunks eventually upload

**Console Output to Look For:**
```
📴 UploadCoordinator: Connection lost - pausing all uploads
[SW] 🔴 Connection error detected - entering offline mode
🌐 UploadCoordinator: Connection restored - resuming uploads
[SW] ✅ Connection restored! Resuming uploads...
```

---

### Test 3: Tab Close (Background Sync) (5 minutes)

**Objective:** Verify uploads continue when tab is closed

**Prerequisites:** Chrome/Edge browser (required for Background Sync)

1. Open http://localhost:8000
2. Click "Record" button
3. Record for 10 seconds (longer recording = more chunks)
4. Click "Stop"
5. **Immediately close the browser tab** (while badge shows "⇪ X%")
6. Wait 30 seconds
7. Re-open http://localhost:8000
8. **Expected:** See completed recording in playlist with "✓ SYNCED" badge

**Success Criteria:**
- ✅ Recording appears in playlist after re-opening
- ✅ File is complete (can play it)
- ✅ No chunks remain in upload queue (check Application → IndexedDB)

**Console Output After Re-opening:**
```
🎯 UploadCoordinator initialized
✓ Background Sync API supported
[SW] ✅ All chunks uploaded for session sess_...
✅ Upload completed: sess_...
```

**Note:** If this doesn't work, check:
- Browser supports Background Sync (chrome://serviceworker-internals)
- Service Worker is active (Application tab → Service Workers)
- Background Sync permission granted

---

### Test 4: Upload Error Handling (3 minutes)

**Objective:** Verify error badge appears on upload failure

1. Open http://localhost:8000
2. Record for 3 seconds
3. Stop recording
4. **While uploading:** Stop the backend server:
   ```bash
   pkill -9 python3
   ```
5. **Expected:** Badge changes to "⏸ PAUSED" (yellow)
6. **Check Console:** Should see retry messages
7. Restart server: `./start.sh`
8. **Expected:** Badge changes to "⇪ X%" and uploads resume
9. Wait for completion
10. **Expected:** Badge shows "✓ SYNCED"

**Success Criteria:**
- ✅ Badge shows paused state when server down
- ✅ Automatic retry attempts (check console)
- ✅ Uploads resume when server back online
- ✅ Badge shows success after recovery

**Console Output:**
```
[SW] Upload failed for chunk X: Failed to fetch
[SW] 🔴 Connection error detected - entering offline mode
[SW] Chunk X will retry in 2s
[SW] ✅ Server confirmed online - resuming uploads
```

---

### Test 5: Multiple Sessions (5 minutes)

**Objective:** Verify multiple uploads are tracked independently

1. Open http://localhost:8000
2. Record Session 1 (3 seconds) → Stop
3. Record Session 2 (5 seconds) → Stop
4. Record Session 3 (3 seconds) → Stop
5. **Expected:** See 3 recordings with separate badges
6. Watch all badges update independently:
   - Session 1: "⇪ 80%"
   - Session 2: "⇪ 45%"
   - Session 3: "⇪ 90%"
7. Wait for all to complete
8. **Expected:** All show "✓ SYNCED" independently

**Success Criteria:**
- ✅ Each session has its own badge
- ✅ Progress updates independently
- ✅ All complete without conflicts
- ✅ No upload method conflicts (TUS vs Custom)

---

### Test 6: Stagnation Detection (3 minutes)

**Objective:** Verify stuck uploads are automatically unlocked

1. Open http://localhost:8000
2. Record for 10 seconds (many chunks)
3. Stop recording
4. **While uploading:** Pause DevTools in debugger
5. Wait 5+ seconds (no progress)
6. Resume debugger
7. **Expected:** See console message "Force trigger Service Worker"
8. Uploads resume

**Success Criteria:**
- ✅ System detects stagnation after 5 seconds
- ✅ Force unlock message sent
- ✅ Uploads resume automatically
- ✅ Badge updates show progress again

---

## DevTools Debugging

### Check Service Worker Status
1. Open DevTools → Application tab
2. Service Workers section
3. Verify:
   - Status: "activated and is running"
   - Source: `/sw.js`
   - "Update on reload" unchecked (for testing)

### Check Background Sync
1. DevTools → Application → Background Sync
2. After recording, should see:
   - Tag: `upload-chunks`
   - Status: `resolved` (after completion)

### Check IndexedDB Queue
1. DevTools → Application → IndexedDB → WaveForgeDB_V4
2. Open `upload_queue` store
3. During upload: See queued chunks
4. After completion: Should be empty

### Check Console Messages
Enable verbose logging:
```javascript
// In console:
localStorage.setItem('debug', 'true');
```

Key messages to look for:
- `🎯 UploadCoordinator initialized`
- `✓ Background Sync API supported`
- `📝 Registered custom upload for session: sess_...`
- `📊 Upload progress: X%`
- `✅ Upload completed: sess_...`
- `[SW] 🔄 Background Sync triggered`

---

## Common Issues

### Badge Not Appearing
**Symptom:** No status badge after recording

**Check:**
1. Console for errors
2. sessionId is set: `console.log(currentSessionId)`
3. UploadCoordinator initialized: `console.log(UploadCoordinator)`

**Fix:**
```javascript
// In console:
UploadCoordinator.init();
```

---

### Badge Stuck on "⇪ X%"
**Symptom:** Badge never reaches 100%

**Check:**
1. IndexedDB upload_queue (should be empty)
2. Console for upload errors
3. Server is running and reachable

**Fix:**
```javascript
// In console:
await UploadCoordinator.countUploadedChunks('sess_YOUR_SESSION_ID');
```

---

### Background Sync Not Working
**Symptom:** Uploads stop when tab closed

**Check:**
1. Browser compatibility (Chrome/Edge required)
2. Service Worker active
3. Background Sync permission

**Test:**
```javascript
// In console:
navigator.serviceWorker.ready.then(reg => {
  return reg.sync.register('test-sync');
}).then(() => {
  console.log('✓ Background Sync working');
}).catch(err => {
  console.error('❌ Background Sync failed:', err);
});
```

---

### Upload Loop/Infinite Retry
**Symptom:** Same chunks upload repeatedly

**Check:**
1. Chunks being removed from queue
2. Server returning success (200 OK)
3. IndexedDB delete operations

**Fix:**
```javascript
// Clear stuck queue:
const db = await new Promise((resolve) => {
  const req = indexedDB.open('WaveForgeDB_V4', 3);
  req.onsuccess = e => resolve(e.target.result);
});
const tx = db.transaction('upload_queue', 'readwrite');
tx.objectStore('upload_queue').clear();
```

---

## Performance Testing

### Memory Usage
1. Open DevTools → Memory
2. Take heap snapshot before recording
3. Record 1 minute of audio
4. Take heap snapshot after upload completes
5. **Expected:** Minimal memory increase (<10MB)

### Network Traffic
1. Open DevTools → Network
2. Filter: `/upload/chunk`
3. Record and upload
4. **Expected:**
   - Sequential chunk uploads (no parallel conflicts)
   - Each chunk ~1MB
   - All chunks return 200 OK

### CPU Usage
1. Open DevTools → Performance
2. Record profile during upload
3. **Expected:**
   - Service Worker processing visible
   - No long tasks (>50ms)
   - Smooth UI updates

---

## Automated Testing (Future)

### Playwright Test Example
```javascript
test('Background Sync uploads continue after tab close', async ({ page, context }) => {
  await page.goto('http://localhost:8000');
  
  // Start recording
  await page.click('#recordButton');
  await page.waitForTimeout(5000);
  await page.click('#stopButton');
  
  // Wait for badge to appear
  await page.waitForSelector('.upload-status-badge');
  
  // Close tab (but not context)
  await page.close();
  
  // Wait 30 seconds
  await new Promise(resolve => setTimeout(resolve, 30000));
  
  // Re-open tab
  const newPage = await context.newPage();
  await newPage.goto('http://localhost:8000');
  
  // Check for completed recording
  const badge = await newPage.locator('.status-synced');
  await expect(badge).toBeVisible();
});
```

---

## Test Results Template

```markdown
# Background Sync Test Results

**Date:** YYYY-MM-DD
**Browser:** Chrome 120 / Edge 120 / Firefox 121
**Environment:** Local Development / Production

## Test Summary
- ✅ Test 1: Basic Upload - PASSED
- ✅ Test 2: Offline Recording - PASSED
- ✅ Test 3: Tab Close - PASSED
- ⚠️ Test 4: Upload Error - PARTIAL (retries work, badge needs fix)
- ✅ Test 5: Multiple Sessions - PASSED
- ✅ Test 6: Stagnation Detection - PASSED

## Issues Found
1. Badge sometimes doesn't update on first chunk
   - **Severity:** Low
   - **Workaround:** Wait 1 second, updates automatically
   - **Fix:** Add debouncing to UI updates

## Performance Notes
- Upload speed: ~2MB/s (local network)
- Memory usage: +8MB during recording
- CPU usage: <5% during upload
- Battery impact: Minimal

## Browser Compatibility
- ✅ Chrome 120: Full support
- ✅ Edge 120: Full support
- ⚠️ Firefox 121: No Background Sync (fallback works)
- ❌ Safari 17: No Service Worker upload (not tested)
```

---

## Production Readiness Checklist

Before deploying to production:

- [ ] All 6 test scenarios pass
- [ ] No console errors during normal operation
- [ ] Memory usage acceptable (<20MB per session)
- [ ] Upload success rate >99%
- [ ] Background Sync works in Chromium browsers
- [ ] Fallback works in non-Chromium browsers
- [ ] Status badges accurate in all scenarios
- [ ] Documentation complete and accurate
- [ ] Error handling covers all edge cases
- [ ] Performance acceptable under load
- [ ] Security review complete (no sensitive data logged)
- [ ] Accessibility review complete (ARIA labels correct)

---

## Next Steps

After successful testing:

1. **Monitor in Production:**
   - Track upload success rate
   - Monitor retry patterns
   - Analyze failure reasons

2. **User Feedback:**
   - Survey about status badge clarity
   - Test with different connection types
   - Validate on mobile devices

3. **Optimization:**
   - Tune retry delays based on data
   - Adjust timeout values
   - Optimize chunk size

4. **Documentation:**
   - Update user guide
   - Create troubleshooting FAQ
   - Document known limitations
