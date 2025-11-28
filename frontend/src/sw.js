const DB_NAME = 'WaveForgeDB_V4';
const DB_VERSION = 3;
const STORE_UPLOAD_QUEUE = 'upload_queue';

// Retry Configuration
const INITIAL_RETRY_DELAY = 2000; // 2 seconds
const MAX_RETRY_DELAY = 60000; // 60 seconds
const MAX_CONSECUTIVE_FAILURES = 10; // After 10 failures, increase delay significantly

// Connection Check Configuration
const CONNECTION_CHECK_INTERVAL = 5000; // Check connection every 5 seconds when offline
let isOffline = false; // Track offline state
let connectionCheckInterval = null; // Connection check timer
let isProcessingUploads = false; // Prevent concurrent upload processing

// TUS Configuration
const TUS_ENDPOINT = '/files';
const MAX_CONCURRENT_UPLOADS = 3;
let activeUploads = 0;

// Import tus-js-client
importScripts('https://cdn.jsdelivr.net/npm/tus-js-client@3/dist/tus.min.js');

// Open DB Helper
function openDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);
        request.onsuccess = e => resolve(e.target.result);
        request.onerror = e => reject(e);
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
    
    console.log('[SW] 🔴 Starting connection check (every 5 seconds)');
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

// Upload Chunk with TUS
async function uploadChunkWithTUS(item) {
    return new Promise((resolve, reject) => {
        if (activeUploads >= MAX_CONCURRENT_UPLOADS) {
            reject(new Error('Max concurrent uploads reached'));
            return;
        }
        
        activeUploads++;
        
        const upload = new self.tus.Upload(item.blob, {
            endpoint: `${self.location.origin}${TUS_ENDPOINT}/${item.sessionId}/chunks/`,
            metadata: {
                chunkIndex: item.chunkIndex.toString(),
                totalChunks: item.totalChunks.toString(),
                sessionId: item.sessionId,
                recordingName: item.recordingName,
                format: item.format
            },
            chunkSize: 512 * 1024, // 512KB sub-chunks
            retryDelays: [0, 1000, 3000, 5000, 10000],
            onProgress: (bytesUploaded, bytesTotal) => {
                const progress = bytesUploaded / bytesTotal;
                broadcastStatus({
                    type: 'UPLOAD_PROGRESS',
                    sessionId: item.sessionId,
                    fileId: item.fileId,
                    chunkIndex: item.chunkIndex,
                    progress: (item.chunkIndex + progress) / item.totalChunks
                });
            },
            onError: (error) => {
                activeUploads--;
                console.error('[SW TUS] Upload error:', error);
                reject(error);
            },
            onSuccess: () => {
                activeUploads--;
                console.log(`[SW TUS] Chunk ${item.chunkIndex} uploaded successfully`);
                broadcastStatus({
                    type: 'CHUNK_UPLOADED',
                    sessionId: item.sessionId,
                    chunkIndex: item.chunkIndex
                });
                resolve();
            }
        });
        
        upload.start();
    });
}

// Upload Chunk with Custom Method
async function uploadChunkCustom(item) {
    const formData = new FormData();
    formData.append('session_id', String(item.sessionId));
    formData.append('chunk_index', String(item.chunkIndex));
    formData.append('file', item.blob);
    
    const response = await fetch('/upload/chunk', {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        const errorText = await response.text();
        console.error(`[SW Custom] Server error ${response.status}: ${errorText}`);
        throw new Error(`Server error: ${response.status}`);
    }
    
    broadcastStatus({
        type: 'CHUNK_UPLOADED',
        sessionId: item.sessionId,
        chunkIndex: item.chunkIndex
    });
}

// Main Upload Logic
async function processUploads() {
    console.log('[SW] processUploads() called');
    
    // Prevent concurrent execution
    if (isProcessingUploads) {
        console.log('[SW] ⏸ Already processing uploads - skipping');
        return;
    }
    
    // Skip if we're in offline mode
    if (isOffline) {
        console.log('[SW] ⏸ Offline mode - uploads paused');
        return;
    }
    
    isProcessingUploads = true;
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

    // CRITICAL: Sort by sessionId first, then by chunkIndex to ensure correct order
    readyQueue.sort((a, b) => {
        // First compare sessionId
        if (a.sessionId < b.sessionId) return -1;
        if (a.sessionId > b.sessionId) return 1;
        // If same session, sort by chunkIndex
        return (a.chunkIndex || 0) - (b.chunkIndex || 0);
    });
    
    console.log('[SW] Upload order:', readyQueue.map(i => `${i.sessionId}:${i.chunkIndex}`).join(', '));

    for (const item of readyQueue) {
        try {
            // Prepare Form Data
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

            // Perform Upload based on method
            console.log(`[SW] 📤 Sending chunk ${item.chunkIndex} to server...`);
            
            if (uploadMethod === 'tus') {
                try {
                    await uploadChunkWithTUS(item);
                } catch (tusError) {
                    console.warn(`[SW] TUS upload failed, falling back to custom:`, tusError);
                    await uploadChunkCustom(item);
                }
            } else {
                await uploadChunkCustom(item);
            }

            // Success: Remove chunk from DB
            console.log(`[SW] ✓ Chunk ${item.chunkIndex} uploaded successfully (session: ${item.sessionId})`);
            console.log(`[SW] 🗑 Attempting to remove from queue - ID: "${item.id}"`);
            
            try {
                await removeFromQueue(db, item.id);
                console.log(`[SW] ✅ Successfully removed chunk ${item.chunkIndex} from queue`);
            } catch (err) {
                console.error(`[SW] ❌ FAILED to remove chunk from queue:`, err);
                console.error(`[SW] ❌ Chunk ID was: "${item.id}"`);
                throw err; // Re-throw to trigger retry logic
            }
            
            // Clear blob reference to free memory
            item.blob = null;

            // Check if all chunks for this session are uploaded
            const remainingChunks = await getUploadQueue(db);
            const sessionChunks = remainingChunks.filter(c => c.sessionId === item.sessionId);
            
            if (sessionChunks.length === 0) {
                console.log(`[SW] ✅ All chunks uploaded for session ${item.sessionId}`);
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
        console.log('[SW] 🔓 Upload processing unlocked');
    }
}

// Service Worker Lifecycle Events
self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(self.clients.claim());
});

self.addEventListener('sync', (event) => {
    if (event.tag === 'audio-upload') {
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