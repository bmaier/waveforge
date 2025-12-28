# Fix: Chunk Count Display Issue (26/27 instead of 27/27)

## Problem Description

After a network interruption and upload resumption, the UI displays incorrect chunk counts like "26/27" instead of "27/27", even though all chunks have been uploaded successfully.

## Root Cause

The assembly signal is stored in the `upload_queue` IndexedDB store with the same `sessionId` as the chunks. When counting remaining or uploaded chunks, the code was including the assembly signal in the count, causing an off-by-one error.

### Example:
- 27 actual chunks + 1 assembly signal = 28 items in queue
- When 27 chunks upload, 1 item remains (the assembly signal)
- Display shows: 26/27 (27 total - 1 remaining = 26 uploaded)
- **Should show: 27/27**

## Solution

Filter out items with `type: 'assembly_signal'` when counting chunks in all relevant functions.

### Changes Made

#### 1. Frontend - `UploadCoordinator.countUploadedChunks` (`frontend/src/index.html`)

**Before:**
```javascript
const sessionChunks = allItems.filter(item => item.sessionId === sessionId);
```

**After:**
```javascript
const sessionChunks = allItems.filter(item => item.sessionId === sessionId && item.type !== 'assembly_signal');
```

#### 2. Frontend - `UploadCoordinator.loadPendingUploads` (`frontend/src/index.html`)

**Before:**
```javascript
allItems.forEach(item => {
    const sessionId = item.sessionId;
    if (!sessionId) return;
    // ...
});
```

**After:**
```javascript
allItems.forEach(item => {
    const sessionId = item.sessionId;
    if (!sessionId || item.type === 'assembly_signal') return;
    // ...
});
```

#### 3. Service Worker - `handleCheckStatus` (`frontend/src/sw.js`)

**Before:**
```javascript
const sessionChunks = queue.filter(item => item.sessionId === sessionId);
const uploaded = queue.filter(item => item.sessionId === sessionId && item.uploaded).length;
```

**After:**
```javascript
const sessionChunks = queue.filter(item => item.sessionId === sessionId && item.type !== 'assembly_signal');
const uploaded = queue.filter(item => item.sessionId === sessionId && item.type !== 'assembly_signal' && item.uploaded).length;
```

#### 4. Service Worker - Chunk Upload Progress (`frontend/src/sw.js`)

**Before:**
```javascript
const sessionChunksRemaining = allRemainingChunks.filter(c => c.sessionId === item.sessionId);
```

**After:**
```javascript
const sessionChunksRemaining = allRemainingChunks.filter(c => c.sessionId === item.sessionId && c.type !== 'assembly_signal');
```

## Already Correct

The following functions already had the correct filter:
- `saveTrackToDB` in `index.html` (line 4680)
- Assembly signal processing in `sw.js` (line 437)

## Testing

To verify the fix:

1. Start recording
2. Simulate network interruption
3. Stop recording and save
4. Restore network
5. **Verify the upload progress shows correct counts (e.g., 27/27 instead of 26/27)**
6. **Verify the "SYNCED" badge appears when all chunks are uploaded**

## Impact

This fix ensures:
- ✅ Accurate chunk count display during uploads
- ✅ Correct progress percentage calculation
- ✅ Proper completion detection (all chunks uploaded)
- ✅ Consistent behavior between normal and resumed uploads
