// Service Worker Version - increment to force update
const SW_VERSION = '2.3.3'; // Fixed syntax error (removed duplicate processUploads function)
console.log(`[SW] Service Worker version ${SW_VERSION} initializing...`);

const DB_NAME = 'WaveForgeDB_V4';
const DB_VERSION = 3;
const STORE_UPLOAD_QUEUE = 'upload_queue';

// Retry Configuration
const INITIAL_RETRY_DELAY = 2000; // 2 seconds
const MAX_RETRY_DELAY = 60000; // 60 seconds
const MAX_CONSECUTIVE_FAILURES = 10; // After 10 failures, increase delay significantly

// Connection Check Configuration
const CONNECTION_CHECK_INTERVAL = 1000; // Check connection every 1 second when offline (fast resume)
let isOffline = false; // Track offline state
let connectionCheckInterval = null; // Connection check timer
let isProcessingUploads = false; // Prevent concurrent upload processing
let uploadStartTime = null; // Track upload start time for timeout
const UPLOAD_TIMEOUT = 60000; // 60 seconds maximum upload duration

// NOTE: TUS Upload runs in main thread via tus-upload-manager.js
// Service Worker uses custom upload method (FormData POST to /upload/chunk)
// This avoids "window is not defined" error in Service Worker context

// Open DB Helper
function openDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);
        request.onsuccess = e => resolve(e.target.result);
        request.onerror = e => reject(e);
    });
}

// Queue Assembly Signal for Retry
async function queueAssemblySignal(sessionId, fileName, metadata) {
    console.log(`[SW] 📥 Queuing assembly signal for session ${sessionId}`);
    
    const db = await openDB();
    const tx = db.transaction(STORE_UPLOAD_QUEUE, 'readwrite');
    const store = tx.objectStore(STORE_UPLOAD_QUEUE);
    
    const queueItem = {
        id: `assembly_${sessionId}_${Date.now()}`,
        type: 'assembly_signal',
        sessionId: sessionId,
        fileName: fileName,
        metadata: metadata,
        retryCount: 0,
        nextRetryAt: 0,
        queuedAt: Date.now()
    };
    
    await new Promise((resolve, reject) => {
        const req = store.add(queueItem);
        req.onsuccess = () => {
            console.log(`[SW] ✓ Assembly signal queued: ${queueItem.id}`);
            resolve();
        };
        req.onerror = (e) => {
            console.error('[SW] Failed to queue assembly signal:', e);
            reject(e);
        };
    });
}

// Get Upload Queue Helper
async function getUploadQueue(db) {
    return new Promise((resolve) => {
        if (!db.objectStoreNames.contains(STORE_UPLOAD_QUEUE)) { resolve([]); return; }
        const tx = db.transaction(STORE_UPLOAD_QUEUE, 'readonly');
        const req = tx.objectStore(STORE_UPLOAD_QUEUE).getAll();
        req.onsuccess = () => resolve(req.result);
    });
}

// Remove from Queue Helper
async function removeFromQueue(db, id) {
    return new Promise((resolve, reject) => {
        try {
            console.log(`[SW] 🔧 removeFromQueue called with id: "${id}"`);
            const tx = db.transaction(STORE_UPLOAD_QUEUE, 'readwrite');
            const store = tx.objectStore(STORE_UPLOAD_QUEUE);
            const deleteRequest = store.delete(id);
            
            deleteRequest.onsuccess = () => {
                console.log(`[SW] 🗑️ Delete request successful for: "${id}"`);
            };
            
            deleteRequest.onerror = (e) => {
                console.error(`[SW] ❌ Delete request failed:`, e);
                reject(e);
            };
            
            tx.oncomplete = () => {
                console.log(`[SW] ✅ Transaction complete - chunk deleted`);
                resolve();
            };
            
            tx.onerror = (e) => {
                console.error(`[SW] ❌ Transaction error:`, e);
                reject(e);
            };
        } catch (err) {
            console.error(`[SW] ❌ Exception in removeFromQueue:`, err);
            reject(err);
        }
    });
}

// Update Retry Count in Queue
async function updateRetryCount(db, id, retryCount, nextRetryAt) {
    const tx = db.transaction(STORE_UPLOAD_QUEUE, 'readwrite');
    const store = tx.objectStore(STORE_UPLOAD_QUEUE);
    const item = await new Promise((resolve, reject) => {
        const req = store.get(id);
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
    });
    
    if (item) {
        item.retryCount = retryCount;
        item.nextRetryAt = nextRetryAt;
        item.lastError = new Date().toISOString();
        store.put(item);
    }
    
    return new Promise(resolve => tx.oncomplete = resolve);
}

// Calculate exponential backoff delay
function getRetryDelay(retryCount) {
    const delay = INITIAL_RETRY_DELAY * Math.pow(2, retryCount);
    return Math.min(delay, MAX_RETRY_DELAY);
}

// Broadcast Status to Window
async function broadcastStatus(msg) {
    const clients = await self.clients.matchAll();
    clients.forEach(client => client.postMessage(msg));
}

// Check if we can reach the server
async function checkServerConnection() {
    try {
        const response = await fetch('/health', { 
            method: 'HEAD',
            cache: 'no-cache'
        });
        return response.ok;
    } catch (err) {
        return false;
    }
}

// Start periodic connection check when offline
function startConnectionCheck() {
    if (connectionCheckInterval) return; // Already running
    
    console.log('[SW] 🔴 Starting connection check (every 1 second)');
    connectionCheckInterval = setInterval(async () => {
        console.log('[SW] 🔍 Checking server connection...');
        const online = await checkServerConnection();
        
        if (online) {
            console.log('[SW] ✅ Connection restored! Resuming uploads...');
            isOffline = false;
            stopConnectionCheck();
            broadcastStatus({ type: 'CONNECTION_RESTORED' });
            processUploads(); // Resume uploads
        } else {
            console.log('[SW] ⏳ Still offline, waiting...');
        }
    }, CONNECTION_CHECK_INTERVAL);
}

// Stop connection check
function stopConnectionCheck() {
    if (connectionCheckInterval) {
        clearInterval(connectionCheckInterval);
        connectionCheckInterval = null;
        console.log('[SW] ✓ Connection check stopped');
    }
}

// TUS Upload Handler
async function handleTUSChunkUpload(data) {
    const { sessionId, chunkIndex, totalChunks, blob, recordingName, format, fileId, uploadMethod } = data;
    
    console.log(`[SW] Handling TUS chunk upload: ${chunkIndex}/${totalChunks} via ${uploadMethod}`);
    
    // Add to upload queue
    const db = await openDB();
    const tx = db.transaction(STORE_UPLOAD_QUEUE, 'readwrite');
    const store = tx.objectStore(STORE_UPLOAD_QUEUE);
    
    const queueItem = {
        id: `${sessionId}_${chunkIndex}`,
        sessionId,
        chunkIndex,
        totalChunks,
        blob,
        recordingName,
        format,
        fileId,
        uploadMethod: uploadMethod || 'custom',
        retryCount: 0,
        nextRetryAt: 0,
        addedAt: Date.now()
    };
    
    store.put(queueItem);
    
    await new Promise(resolve => tx.oncomplete = resolve);
    db.close();
    
    // Trigger upload processing
    processUploads();
}

// Check Upload Status Handler
async function handleCheckStatus(data) {
    const { sessionId } = data;
    const db = await openDB();
    const queue = await getUploadQueue(db);
    db.close();
    
    const sessionChunks = queue.filter(item => item.sessionId === sessionId);
    const uploaded = queue.filter(item => item.sessionId === sessionId && item.uploaded).length;
    
    broadcastStatus({
        type: 'UPLOAD_STATUS',
        sessionId,
        status: {
            uploaded,
            total: sessionChunks.length,
            pending: sessionChunks.length - uploaded
        }
    });
}

// Cancel Upload Handler
async function handleCancelUpload(data) {
    const { sessionId } = data;
    const db = await openDB();
    const queue = await getUploadQueue(db);
    
    // Remove all chunks for this session
    const tx = db.transaction(STORE_UPLOAD_QUEUE, 'readwrite');
    const store = tx.objectStore(STORE_UPLOAD_QUEUE);
    
    for (const item of queue) {
        if (item.sessionId === sessionId) {
            store.delete(item.id);
        }
    }
    
    await new Promise(resolve => tx.oncomplete = resolve);
    db.close();
    
    console.log(`[SW] Cancelled all uploads for session ${sessionId}`);
}

// Check Pending Uploads Handler
async function handleCheckPendingUploads() {
    const db = await openDB();
    const queue = await getUploadQueue(db);
    db.close();
    
    broadcastStatus({
        type: 'PENDING_UPLOADS_COUNT',
        count: queue.length
    });
}

// NOTE: TUS Upload is handled in main thread via tus-upload-manager.js
// Service Worker only uses custom upload method to avoid 'window is not defined' error

// Upload Chunk with Custom Method
async function uploadChunkCustom(item) {
    const formData = new FormData();
    formData.append('session_id', String(item.sessionId));
    formData.append('chunk_index', String(item.chunkIndex));
    formData.append('file', item.blob);
    
    // CRITICAL: Use AbortController for timeout to prevent hanging requests
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
    
    try {
        const response = await fetch('/upload/chunk', {
            method: 'POST',
            body: formData,
            signal: controller.signal
        });
        
        clearTimeout(timeoutId); // Clear timeout if request completes
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error(`[SW Custom] Server error ${response.status}: ${errorText}`);
            throw new Error(`Server error: ${response.status}`);
        }
        
        // CRITICAL: Validate server response to ensure chunk was actually saved
        const result = await response.json();
        
        if (result.status === 'chunk_already_exists') {
            console.log(`[SW Custom] ✓ Chunk ${item.chunkIndex} already exists on server (idempotent retry)`);
        } else if (result.status === 'chunk_received') {
            console.log(`[SW Custom] ✓ Server confirmed chunk ${item.chunkIndex} saved successfully`);
        } else {
            console.error(`[SW Custom] ⚠️ Unexpected server response:`, result);
            throw new Error(`Unexpected server response: ${result.status}`);
        }
        
        // Verify the response matches what we sent
        if (result.chunk_index !== item.chunkIndex) {
            console.error(`[SW Custom] ❌ Chunk index mismatch! Sent ${item.chunkIndex}, server confirmed ${result.chunk_index}`);
            throw new Error(`Chunk index mismatch: sent ${item.chunkIndex}, got ${result.chunk_index}`);
        }
        
        broadcastStatus({
            type: 'CHUNK_UPLOADED',
            sessionId: item.sessionId,
            chunkIndex: item.chunkIndex
        });
    } catch (error) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') {
            console.error(`[SW Custom] ⏱️ Upload timeout for chunk ${item.chunkIndex}`);
            throw new Error(`Upload timeout after 30 seconds`);
        }
        throw error;
    }
}

// Main Upload Logic
async function processUploads() {
    console.log('[SW] processUploads() called');
    
    // Check if processing is stuck (timeout)
    if (isProcessingUploads) {
        const now = Date.now();
        if (uploadStartTime && (now - uploadStartTime) > UPLOAD_TIMEOUT) {
            console.warn('[SW] ⚠️ Upload processing timeout - forcing unlock');
            isProcessingUploads = false;
            uploadStartTime = null;
        } else {
            console.log('[SW] ⏸ Already processing uploads - skipping');
            return;
        }
    }
    
    // Skip if we're in offline mode
    if (isOffline) {
        console.log('[SW] ⏸ Offline mode - uploads paused');
        return;
    }
    
    isProcessingUploads = true;
    uploadStartTime = Date.now();
    console.log('[SW] 🔒 Upload processing locked');
    
    const db = await openDB();
    const queue = await getUploadQueue(db);

    console.log(`[SW] Found ${queue.length} chunks in upload queue`);
    if (queue.length === 0) return;

    // Filter: Only process chunks that are ready to retry
    const now = Date.now();
    const readyQueue = queue.filter(item => {
        const nextRetryAt = item.nextRetryAt || 0;
        
        // Skip if not yet time to retry (unless retry time is 0, meaning never tried)
        if (nextRetryAt > 0 && nextRetryAt > now) {
            const waitTime = Math.round((nextRetryAt - now) / 1000);
            console.log(`[SW] Chunk ${item.chunkIndex} (session ${item.sessionId}) waiting ${waitTime}s before retry`);
            return false;
        }
        
        return true;
    });

    console.log(`[SW] ${readyQueue.length} chunks ready to upload (${queue.length - readyQueue.length} waiting for retry)`);
    if (readyQueue.length === 0) {
        console.log('[SW] All chunks are waiting for retry delay. Next attempt will be automatic.');
        return;
    }

    // CRITICAL: Sort by sessionId first, then by type (chunks before assembly), then by chunkIndex
    readyQueue.sort((a, b) => {
        // First compare sessionId
        if (a.sessionId < b.sessionId) return -1;
        if (a.sessionId > b.sessionId) return 1;
        
        // CRITICAL: Assembly signals must be processed LAST (after all chunks)
        // If a is assembly but b is not, a comes after
        if (a.type === 'assembly_signal' && b.type !== 'assembly_signal') return 1;
        // If b is assembly but a is not, b comes after
        if (b.type === 'assembly_signal' && a.type !== 'assembly_signal') return -1;
        
        // If same session and both are chunks, sort by chunkIndex
        return (a.chunkIndex || 0) - (b.chunkIndex || 0);
    });
    
    console.log('[SW] Upload order:', readyQueue.map(i => `${i.sessionId}:${i.chunkIndex}`).join(', '));

    for (const item of readyQueue) {
        try {
            // Check if this is an assembly signal instead of a chunk
            if (item.type === 'assembly_signal') {
                const retryCount = item.retryCount || 0;
                const retryInfo = retryCount > 0 ? ` (attempt ${retryCount + 1})` : '';
                console.log(`[SW] 📢 Processing assembly signal for session ${item.sessionId}${retryInfo}`);
                
                // CRITICAL: Check if any chunks for this session are still in queue OR being retried
                const allItems = await getUploadQueue(db);
                const remainingChunks = allItems.filter(i => 
                    i.sessionId === item.sessionId && 
                    i.type !== 'assembly_signal'
                );
                
                if (remainingChunks.length > 0) {
                    // Check if any chunks are waiting for retry (have future nextRetryAt)
                    const now = Date.now();
                    const waitingChunks = remainingChunks.filter(c => (c.nextRetryAt || 0) > now);
                    const readyChunks = remainingChunks.filter(c => (c.nextRetryAt || 0) <= now);
                    
                    console.log(`[SW] ⏸⏸⏸ ASSEMBLY SIGNAL DELAYED - ${remainingChunks.length} chunks still in queue for session ${item.sessionId}`);
                    console.log(`[SW] 📋 Ready to upload: [${readyChunks.map(c => c.chunkIndex).sort((a,b) => a-b).join(', ')}]`);
                    console.log(`[SW] ⏳ Waiting for retry: [${waitingChunks.map(c => c.chunkIndex).sort((a,b) => a-b).join(', ')}]`);
                    console.log(`[SW] 📋 Total pending: [${remainingChunks.map(c => c.chunkIndex).sort((a,b) => a-b).join(', ')}]`);
                    console.log(`[SW] ⏰ Assembly will retry in 5 seconds once all chunks are uploaded`);
                    
                    // Update retry time to check again later (after chunks are done)
                    const retryDelay = 5000;
                    await updateRetryCount(db, item.id, retryCount, Date.now() + retryDelay);
                    
                    // Schedule retry to check again after chunks are uploaded
                    setTimeout(() => {
                        console.log(`[SW] ⏰ Retrying assembly signal check for session ${item.sessionId}`);
                        processUploads();
                    }, retryDelay);
                    
                    continue; // Skip to next item - will retry when chunks are done
                }
                
                console.log(`[SW] ✓ All chunks uploaded for session ${item.sessionId}, sending assembly signal...`);
                
                const formData = new FormData();
                formData.append('session_id', item.sessionId);
                formData.append('file_name', item.fileName);
                formData.append('metadata', JSON.stringify(item.metadata));
                
                const response = await fetch('/recording/complete', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error(`Server error: ${response.status}`);
                }
                
                const result = await response.json();
                console.log(`[SW] ✓ Assembly signal acknowledged:`, result);
                
                // Success: Remove from queue
                await removeFromQueue(db, item.id);
                console.log(`[SW] ✅ Assembly signal removed from queue`);
                
                // Notify main thread
                broadcastStatus({
                    type: 'ASSEMBLY_COMPLETE',
                    sessionId: item.sessionId,
                    fileName: item.fileName
                });
                
                continue; // Skip to next item
            }
            
            // Regular chunk upload processing
            const retryCount = item.retryCount || 0;
            const retryInfo = retryCount > 0 ? ` (attempt ${retryCount + 1})` : '';
            const uploadMethod = item.uploadMethod || 'custom';
            console.log(`[SW] Uploading chunk ${item.chunkIndex} for session ${item.sessionId}${retryInfo} via ${uploadMethod}`);

            // Notify UI
            broadcastStatus({ 
                type: 'UPLOAD_PROGRESS', 
                sessionId: item.sessionId,
                fileId: item.fileId, 
                progress: (item.chunkIndex + 1) / item.totalChunks 
            });

            // Service Worker always uses custom upload
            // TUS upload runs in main thread via tus-upload-manager.js
            console.log(`[SW] 📤 Sending chunk ${item.chunkIndex} to server (custom upload)...`);
            await uploadChunkCustom(item);

            // Success: Chunk uploaded, now verify it exists on server before removing from queue
            console.log(`[SW] ✓ Chunk ${item.chunkIndex} uploaded successfully (session: ${item.sessionId})`);
            console.log(`[SW] 🔍 Verifying chunk exists on server before removing from queue...`);
            
            // CRITICAL: Double-check that chunk actually exists on server with timeout
            const verifyController = new AbortController();
            const verifyTimeoutId = setTimeout(() => verifyController.abort(), 10000); // 10 second timeout for verify
            
            let verifyResponse;
            try {
                verifyResponse = await fetch(`/api/verify/${item.sessionId}/${item.chunkIndex}`, {
                    signal: verifyController.signal
                });
                clearTimeout(verifyTimeoutId);
            } catch (verifyError) {
                clearTimeout(verifyTimeoutId);
                if (verifyError.name === 'AbortError') {
                    console.error(`[SW] ⏱️ Verify timeout for chunk ${item.chunkIndex}`);
                    throw new Error(`Verify timeout after 10 seconds`);
                }
                throw verifyError;
            }
            
            if (!verifyResponse.ok) {
                console.error(`[SW] ⚠️ Verify request failed with status ${verifyResponse.status}`);
                throw new Error(`Failed to verify chunk ${item.chunkIndex} on server (HTTP ${verifyResponse.status})`);
            }
            
            const verifyResult = await verifyResponse.json();
            if (!verifyResult.exists) {
                console.error(`[SW] ❌ CRITICAL: Chunk ${item.chunkIndex} NOT found on server after upload!`);
                if (verifyResult.path) {
                    console.error(`[SW] Expected path: ${verifyResult.path}`);
                }
                throw new Error(`Chunk ${item.chunkIndex} not found on server after upload - will retry`);
            }
            
            console.log(`[SW] ✅ Chunk ${item.chunkIndex} verified on server (${verifyResult.size} bytes)`);
            console.log(`[SW] 🗑 Removing chunk from queue - ID: "${item.id}"`);
            
            try {
                await removeFromQueue(db, item.id);
                console.log(`[SW] ✅ Successfully removed chunk ${item.chunkIndex} from queue`);
            } catch (err) {
                console.error(`[SW] ❌ FAILED to remove chunk from queue:`, err);
                console.error(`[SW] ❌ Chunk ID was: "${item.id}"`);
                throw err; // Re-throw to trigger retry logic
            }
            
            // Count total chunks for this session (including this one + remaining in queue)
            const allRemainingChunks = await getUploadQueue(db);
            const sessionChunksRemaining = allRemainingChunks.filter(c => c.sessionId === item.sessionId);
            const totalChunksForSession = item.chunkIndex + 1 + sessionChunksRemaining.length;
            
            // Notify UploadCoordinator about chunk upload
            broadcastStatus({
                type: 'CHUNK_UPLOADED',
                sessionId: item.sessionId,
                chunkIndex: item.chunkIndex,
                totalChunks: totalChunksForSession
            });
            
            // Clear blob reference to free memory
            item.blob = null;

            // Check if all chunks for this session are uploaded (reuse the already fetched data)
            const sessionChunks = sessionChunksRemaining;
            
            if (sessionChunks.length === 0) {
                console.log(`[SW] ✅ All chunks uploaded for session ${item.sessionId}`);
                broadcastStatus({ 
                    type: 'SESSION_UPLOAD_COMPLETE', 
                    sessionId: item.sessionId 
                });
                // Keep legacy UPLOAD_COMPLETE for compatibility
                broadcastStatus({ 
                    type: 'UPLOAD_COMPLETE', 
                    sessionId: item.sessionId 
                });
            } else {
                console.log(`[SW] 📊 Session ${item.sessionId}: ${sessionChunks.length} chunks remaining`);
            }

        } catch (error) {
            const retryCount = (item.retryCount || 0) + 1;
            console.warn(`[SW] Upload failed for chunk ${item.chunkIndex} (session ${item.sessionId}, attempt ${retryCount}):`, error.message);
            
            // Check if this is a connection error (server unreachable)
            const isConnectionError = error.message.includes('Failed to fetch') || 
                                     error.message.includes('NetworkError') ||
                                     error.message.includes('Server error: 5') ||
                                     error.message.includes('fetch');
            
            // Check for fatal errors (non-recoverable - but only for data corruption, NOT retry count)
            // CRITICAL: Never remove chunks from queue due to retry count - they must be uploaded!
            const isFatalError = !isConnectionError && (
                error.message.includes('Server error: 400') || // Bad request
                error.message.includes('Server error: 413') || // Payload too large
                error.message.includes('Server error: 422') || // Unprocessable entity
                error.message.includes('Invalid chunk data') ||
                error.message.includes('Corrupted')
                // NOTE: We removed "retryCount >= 20" - chunks should NEVER be deleted due to retries
            );
            
            if (isFatalError) {
                console.error(`[SW] 💀 Fatal error detected - stopping retries for chunk ${item.chunkIndex}`);
                
                // Remove from queue - no more retries
                await removeFromQueue(db, item.id);
                
                // Notify UI about fatal error
                broadcastStatus({
                    type: 'UPLOAD_FATAL_ERROR',
                    sessionId: item.sessionId,
                    chunkId: item.chunkIndex,
                    error: error.message,
                    isFatal: true
                });
                
                continue; // Skip to next item
            }
            
            // SAFETY CHECK: If too many retries, increase backoff but KEEP in queue
            if (retryCount >= 20) {
                console.warn(`[SW] ⚠️ Chunk ${item.chunkIndex} has failed ${retryCount} times - extending retry delay`);
                // Use very long backoff for stuck chunks (5 minutes)
                const longBackoff = 300000; // 5 minutes
                await updateRetryCount(db, item.id, retryCount, Date.now() + longBackoff);
                continue; // Skip this attempt, will retry later
            }
            
            // Notify UploadCoordinator about error (only after multiple failures)
            if (retryCount >= 3) {
                broadcastStatus({
                    type: 'UPLOAD_ERROR',
                    sessionId: item.sessionId,
                    chunkId: item.chunkIndex,
                    error: error.message,
                    isFatal: false
                });
            }
            
            if (isConnectionError) {
                console.log('[SW] 🔴 Connection error detected - entering offline mode');
                isOffline = true;
                
                // Update retry time to prevent immediate retry
                await updateRetryCount(db, item.id, retryCount, Date.now() + 60000);
                
                // Broadcast offline status
                broadcastStatus({ 
                    type: 'UPLOAD_OFFLINE',
                    sessionId: item.sessionId
                });
                
                // Start connection check
                startConnectionCheck();
                
                // Stop processing - will resume when connection is restored
                console.log('[SW] ⏸ Pausing all uploads until connection is restored');
                break;
            }
            
            // For non-connection errors (e.g., server errors), use exponential backoff
            let retryDelay;
            if (retryCount > MAX_CONSECUTIVE_FAILURES) {
                retryDelay = MAX_RETRY_DELAY;
                console.log(`[SW] Chunk ${item.chunkIndex}: Many failures detected, using max delay (${MAX_RETRY_DELAY/1000}s)`);
            } else {
                retryDelay = getRetryDelay(retryCount);
            }
            
            const nextRetryAt = Date.now() + retryDelay;
            
            console.log(`[SW] Chunk ${item.chunkIndex} will retry in ${Math.round(retryDelay/1000)}s (kept in queue)`);
            await updateRetryCount(db, item.id, retryCount, nextRetryAt);
            
            // Silent status update - no toast
            broadcastStatus({ 
                type: 'UPLOAD_PENDING',
                sessionId: item.sessionId,
                hasPendingChunks: true
            });
            
            // Schedule automatic retry ONCE
            setTimeout(() => {
                console.log(`[SW] Auto-retry for chunk ${item.chunkIndex}`);
                processUploads();
            }, retryDelay);
            
            // CRITICAL: Stop processing to avoid overlapping retries
            // This ensures chunks are uploaded sequentially and in order
            console.log('[SW] Stopping current batch to retry failed chunk');
            break;
        }
    }
    
    // Close DB connection and release lock
    try {
        db.close();
        console.log('[SW] 🔒 Database connection closed');
    } catch (err) {
        console.error('[SW] Error closing DB:', err);
    } finally {
        isProcessingUploads = false;
        uploadStartTime = null;
        console.log('[SW] 🔓 Upload processing unlocked');
    }
}

// Message handler for force-unlock
self.addEventListener('message', async (event) => {
    console.log('[SW] Received message:', event.data);
    
    if (event.data.type === 'PROCESS_UPLOADS') {
        if (event.data.force) {
            console.log('[SW] 🔓 Force unlocking upload processing');
            isProcessingUploads = false;
            uploadStartTime = null;
        }
        await processUploads();
    }
});

// Service Worker Lifecycle Events
self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    console.log('[SW] 🚀 Service Worker activated - checking for pending uploads');
    event.waitUntil(
        self.clients.claim().then(() => {
            // Immediately process pending uploads when Service Worker activates
            return processUploads();
        })
    );
});

self.addEventListener('sync', (event) => {
    if (event.tag === 'audio-upload' || event.tag === 'upload-chunks') {
        console.log(`[SW] 🔄 Background Sync triggered: ${event.tag}`);
        event.waitUntil(processUploads());
    }
});

// Periodic Background Sync (optional, for long-running uploads)
self.addEventListener('periodicsync', (event) => {
    if (event.tag === 'upload-chunks-periodic') {
        console.log('[SW] 🔄 Periodic Background Sync triggered');
        event.waitUntil(processUploads());
    }
});

self.addEventListener('message', async (event) => {
    const { type, data } = event.data;
    
    if (event.data === 'TRIGGER_UPLOAD' || type === 'TRIGGER_UPLOAD') {
        processUploads();
        return;
    }
    
    switch (type) {
        case 'QUEUE_ASSEMBLY_SIGNAL':
            console.log('[SW] Received QUEUE_ASSEMBLY_SIGNAL request');
            await queueAssemblySignal(
                event.data.sessionId,
                event.data.fileName,
                event.data.metadata
            );
            console.log('[SW] Assembly signal queued, triggering processUploads');
            await processUploads();
            break;
            
        case 'UPLOAD_CHUNK_TUS':
            await handleTUSChunkUpload(data);
            break;
            
        case 'CHECK_UPLOAD_STATUS':
            await handleCheckStatus(data);
            break;
            
        case 'CANCEL_UPLOAD':
            await handleCancelUpload(data);
            break;
            
        case 'RETRY_FAILED_UPLOADS':
            await processUploads();
            break;
            
        case 'CHECK_PENDING_UPLOADS':
            await handleCheckPendingUploads();
            break;
            
        default:
            console.warn('[SW] Unknown message type:', type);
    }
});

// Listen for connection recovery (browser online event)
self.addEventListener('online', () => {
    console.log('[SW] 🌐 Browser reports online - checking server...');
    // Verify server is actually reachable before resuming
    checkServerConnection().then(online => {
        if (online) {
            console.log('[SW] ✅ Server confirmed online - resuming uploads');
            isOffline = false;
            stopConnectionCheck();
            processUploads();
        } else {
            console.log('[SW] ⚠️ Browser online but server unreachable - starting connection check');
            isOffline = true;
            startConnectionCheck();
        }
    });
});

// Listen for offline event
self.addEventListener('offline', () => {
    console.log('[SW] 🔴 Browser offline event - entering offline mode');
    isOffline = true;
    startConnectionCheck();
});