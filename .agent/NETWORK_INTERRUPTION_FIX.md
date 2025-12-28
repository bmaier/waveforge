# Fix: Upload Resumption After Network Interruption

## Problem Description

When a network interruption occurs during recording and the recording is stopped while offline, the remaining chunks do not upload automatically when the connection is restored.

### Scenario
1. Recording starts online → Chunks upload live
2. Network interruption occurs → Chunks queue in IndexedDB with retry delays
3. Service Worker detects offline state → Sets `isOffline = true`
4. Recording is stopped (while still offline)
5. User saves the recording → Triggers `TRIGGER_UPLOAD`
6. **Service Worker skips upload processing because `isOffline` is still `true`**
7. Connection is restored → SW detects it but timing is off
8. **Result: Chunks never upload to server**

## Root Cause

The Service Worker's `processUploads()` function has an early return when `isOffline` is true:

```javascript
// Skip if we're in offline mode
if (isOffline) {
    console.log('[SW] ⏸ Offline mode - uploads paused');
    return;
}
```

When `TRIGGER_UPLOAD` or `PROCESS_UPLOADS` messages are received, the SW doesn't check if the connection has been restored - it just trusts the `isOffline` flag, which might be stale.

## Solution

Force a connection check when `TRIGGER_UPLOAD` or `PROCESS_UPLOADS` messages are received, before processing uploads. If the connection is available but the SW thinks it's offline, reset the offline flag and resume uploads.

### Changes Made

#### 1. Service Worker - TRIGGER_UPLOAD Handler (`frontend/src/sw.js`)

**Before:**
```javascript
if (event.data === 'TRIGGER_UPLOAD' || type === 'TRIGGER_UPLOAD') {
    processUploads();
    return;
}
```

**After:**
```javascript
if (event.data === 'TRIGGER_UPLOAD' || type === 'TRIGGER_UPLOAD') {
    // CRITICAL: Force connection check before processing
    // This handles the case where network was restored but SW still thinks it's offline
    console.log('[SW] 🔔 TRIGGER_UPLOAD received - checking connection first');
    const online = await checkServerConnection();
    if (online && isOffline) {
        console.log('[SW] ✅ Connection restored (was offline) - resetting offline flag');
        isOffline = false;
        stopConnectionCheck();
        broadcastStatus({ type: 'CONNECTION_RESTORED' });
    }
    processUploads();
    return;
}
```

#### 2. Service Worker - PROCESS_UPLOADS Handler (`frontend/src/sw.js`)

**Before:**
```javascript
if (event.data.type === 'PROCESS_UPLOADS') {
    if (event.data.force) {
        console.log('[SW] 🔓 Force unlocking upload processing');
        isProcessingUploads = false;
        uploadStartTime = null;
    }
    await processUploads();
}
```

**After:**
```javascript
if (event.data.type === 'PROCESS_UPLOADS') {
    // CRITICAL: Check connection before processing (same as TRIGGER_UPLOAD)
    console.log('[SW] 🔔 PROCESS_UPLOADS received - checking connection first');
    const online = await checkServerConnection();
    if (online && isOffline) {
        console.log('[SW] ✅ Connection restored (was offline) - resetting offline flag');
        isOffline = false;
        stopConnectionCheck();
        broadcastStatus({ type: 'CONNECTION_RESTORED' });
    }
    
    if (event.data.force) {
        console.log('[SW] 🔓 Force unlocking upload processing');
        isProcessingUploads = false;
        uploadStartTime = null;
    }
    await processUploads();
}
```

## How It Works Now

1. Recording starts online → Chunks upload live
2. Network interruption → Chunks queue with retry delays, `isOffline = true`
3. Recording is stopped (while offline)
4. User saves → `saveTrackToDB()` resets retry delays and sends `TRIGGER_UPLOAD`
5. **SW receives `TRIGGER_UPLOAD` → Checks server connection first**
6. **If online: Resets `isOffline` flag and broadcasts `CONNECTION_RESTORED`**
7. **Calls `processUploads()` which now proceeds normally**
8. Chunks upload successfully!

## Testing

To test this fix:

1. Start recording with network connection
2. Simulate network interruption (disable WiFi or use browser DevTools offline mode)
3. Wait a few seconds (chunks will queue)
4. Stop recording
5. Save the recording
6. Restore network connection
7. **Verify chunks upload automatically**
8. Check server logs for chunk uploads and assembly completion

## Additional Benefits

- More resilient to timing issues between network restoration and upload triggers
- Handles cases where browser's `navigator.onLine` is unreliable
- Provides explicit logging for debugging connection state transitions
- Works for both manual triggers (`TRIGGER_UPLOAD`) and automatic resumption (`PROCESS_UPLOADS`)
