/**
 * TUS Upload Manager
 * Manages TUS resumable uploads with Service Worker integration
 * Falls back to custom chunking if TUS fails
 */

class TusUploadManager {
    constructor() {
        this.uploadMethod = localStorage.getItem('uploadMethod') || 'tus';
        this.serviceWorker = null;
        this.eventListeners = {};
        this.uploadStatus = {};
        this.pendingUploads = 0;

        console.log('[TUS Manager] Initialized with method:', this.uploadMethod);
    }

    /**
     * Initialize Service Worker and message handlers
     */
    async init() {
        if ('serviceWorker' in navigator) {
            try {
                const registration = await navigator.serviceWorker.ready;
                this.serviceWorker = registration.active;

                // Listen for messages from Service Worker
                navigator.serviceWorker.addEventListener('message', this.handleMessage.bind(this));

                console.log('[TUS Manager] Service Worker ready');

                // Check for pending uploads
                await this.checkPendingUploads();
            } catch (error) {
                console.error('[TUS Manager] Service Worker initialization failed:', error);
            }
        }
    }

    /**
     * Set upload method (tus or custom)
     */
    setUploadMethod(method) {
        if (method !== 'tus' && method !== 'custom') {
            console.error('[TUS Manager] Invalid upload method:', method);
            return;
        }

        this.uploadMethod = method;
        localStorage.setItem('uploadMethod', method);
        console.log('[TUS Manager] Upload method set to:', method);
        this.emit('methodChanged', { method });
    }

    /**
     * Get current upload method
     */
    getUploadMethod() {
        return this.uploadMethod;
    }

    /**
     * Upload a chunk using the configured method
     */
    async uploadChunk(sessionId, chunkIndex, totalChunks, blob, recordingName, format, fileId) {
        console.log(`[TUS Manager] Uploading chunk ${chunkIndex}/${totalChunks} via ${this.uploadMethod}`);

        if (this.serviceWorker) {
            // Send to Service Worker for background upload
            this.serviceWorker.postMessage({
                type: 'UPLOAD_CHUNK_TUS',
                data: {
                    sessionId,
                    chunkIndex,
                    totalChunks,
                    blob,
                    recordingName,
                    format,
                    fileId,
                    uploadMethod: this.uploadMethod
                }
            });
        } else {
            // Fallback: Upload directly if no Service Worker
            console.warn('[TUS Manager] Service Worker not available, uploading directly');
            await this.uploadChunkDirect(sessionId, chunkIndex, totalChunks, blob, recordingName, format);
        }
    }

    /**
     * Upload chunk directly (fallback when SW unavailable)
     */
    async uploadChunkDirect(sessionId, chunkIndex, totalChunks, blob, recordingName, format) {
        try {
            if (this.uploadMethod === 'tus') {
                await this.uploadChunkWithTUS(sessionId, chunkIndex, totalChunks, blob, recordingName, format);
            } else {
                await this.uploadChunkCustom(sessionId, chunkIndex, totalChunks, blob, recordingName, format);
            }
        } catch (error) {
            console.error('[TUS Manager] Direct upload failed:', error);

            // If TUS failed, try custom as fallback
            if (this.uploadMethod === 'tus') {
                console.log('[TUS Manager] Falling back to custom upload');
                await this.uploadChunkCustom(sessionId, chunkIndex, totalChunks, blob, recordingName, format);
            }
        }
    }

    /**
     * Upload chunk using TUS protocol
     */
    async uploadChunkWithTUS(sessionId, chunkIndex, totalChunks, blob, recordingName, format) {
        return new Promise((resolve, reject) => {
            // Dynamically load tus-js-client if not already loaded
            if (typeof tus === 'undefined') {
                const script = document.createElement('script');
                script.src = 'https://cdn.jsdelivr.net/npm/tus-js-client@3/dist/tus.min.js';
                script.onload = () => {
                    this.performTUSUpload(sessionId, chunkIndex, totalChunks, blob, recordingName, format, resolve, reject);
                };
                script.onerror = () => reject(new Error('Failed to load tus-js-client'));
                document.head.appendChild(script);
            } else {
                this.performTUSUpload(sessionId, chunkIndex, totalChunks, blob, recordingName, format, resolve, reject);
            }
        });
    }

    /**
     * Perform TUS upload
     */
    performTUSUpload(sessionId, chunkIndex, totalChunks, blob, recordingName, format, resolve, reject) {
        const upload = new tus.Upload(blob, {
            endpoint: `${window.location.origin}/files/${sessionId}/chunks/`,
            metadata: {
                chunkIndex: chunkIndex.toString(),
                totalChunks: totalChunks.toString(),
                sessionId: sessionId,
                recordingName: recordingName,
                format: format
            },
            chunkSize: 512 * 1024, // 512KB sub-chunks
            retryDelays: [0, 1000, 3000, 5000, 10000],
            onProgress: (bytesUploaded, bytesTotal) => {
                const progress = bytesUploaded / bytesTotal;
                this.emit('progress', {
                    sessionId,
                    chunkIndex,
                    totalChunks,
                    bytesUploaded,
                    bytesTotal,
                    progress
                });
            },
            onError: (error) => {
                console.error('[TUS Manager] Upload error:', error);
                reject(error);
            },
            onSuccess: () => {
                console.log(`[TUS Manager] Chunk ${chunkIndex} uploaded successfully`);
                this.emit('chunkUploaded', { sessionId, chunkIndex, totalChunks });
                resolve();
            }
        });

        upload.start();
    }

    /**
     * Upload chunk using custom method (fallback)
     */
    async uploadChunkCustom(sessionId, chunkIndex, totalChunks, blob, recordingName, format) {
        const formData = new FormData();
        formData.append('session_id', sessionId);
        formData.append('chunk_index', chunkIndex);
        formData.append('file', blob);
        formData.append('total_chunks', totalChunks);
        formData.append('recording_name', recordingName);
        formData.append('format', format);

        const response = await fetch('/upload/chunk', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Upload failed: ${response.status}`);
        }

        this.emit('chunkUploaded', { sessionId, chunkIndex, totalChunks });
    }

    /**
     * Get upload status for a session
     */
    async getUploadStatus(sessionId) {
        if (this.serviceWorker) {
            this.serviceWorker.postMessage({
                type: 'CHECK_UPLOAD_STATUS',
                data: { sessionId }
            });
        }

        return this.uploadStatus[sessionId] || { uploaded: 0, total: 0 };
    }

    /**
     * Cancel all uploads for a session
     */
    async cancelSession(sessionId) {
        if (this.serviceWorker) {
            this.serviceWorker.postMessage({
                type: 'CANCEL_UPLOAD',
                data: { sessionId }
            });
        }

        this.emit('sessionCancelled', { sessionId });
    }

    /**
     * Retry failed uploads
     */
    async retryFailedUploads() {
        if (this.serviceWorker) {
            this.serviceWorker.postMessage({
                type: 'RETRY_FAILED_UPLOADS'
            });
        }
    }

    /**
     * Check for pending uploads
     */
    async checkPendingUploads() {
        if (this.serviceWorker) {
            this.serviceWorker.postMessage({
                type: 'CHECK_PENDING_UPLOADS'
            });
        }
    }

    /**
     * Handle messages from Service Worker
     */
    handleMessage(event) {
        const { type, data } = event.data;

        switch (type) {
            case 'UPLOAD_PROGRESS':
                this.updateProgressUI(data);
                this.emit('progress', data);
                break;

            case 'UPLOAD_COMPLETE':
                console.log('[TUS Manager] Session complete:', data.sessionId);
                this.emit('sessionComplete', data);
                break;

            case 'UPLOAD_OFFLINE':
                console.log('[TUS Manager] Uploads paused (offline)');
                this.emit('offline', data);
                break;

            case 'CONNECTION_RESTORED':
                console.log('[TUS Manager] Connection restored, resuming uploads');
                this.emit('online', data);
                break;

            case 'UPLOAD_PENDING':
                this.emit('pending', data);
                break;

            case 'UPLOAD_STATUS':
                this.uploadStatus[data.sessionId] = data.status;
                this.emit('status', data);
                break;

            case 'PENDING_UPLOADS_COUNT':
                this.pendingUploads = data.count;
                this.emit('pendingCount', data);
                break;

            case 'CHUNK_UPLOADED':
                this.emit('chunkUploaded', data);
                break;

            case 'CHUNK_FAILED':
                this.emit('chunkFailed', data);
                break;

            default:
                console.warn('[TUS Manager] Unknown message type:', type);
        }
    }

    /**
     * Update progress UI
     */
    updateProgressUI(data) {
        // Emit progress event for UI to handle
        this.emit('progress', data);
    }

    /**
     * Event listener registration
     */
    on(event, callback) {
        if (!this.eventListeners[event]) {
            this.eventListeners[event] = [];
        }
        this.eventListeners[event].push(callback);
    }

    /**
     * Remove event listener
     */
    off(event, callback) {
        if (!this.eventListeners[event]) return;

        const index = this.eventListeners[event].indexOf(callback);
        if (index > -1) {
            this.eventListeners[event].splice(index, 1);
        }
    }

    /**
     * Emit event
     */
    emit(event, data) {
        if (!this.eventListeners[event]) return;

        this.eventListeners[event].forEach(callback => {
            try {
                callback(data);
            } catch (error) {
                console.error(`[TUS Manager] Error in ${event} listener:`, error);
            }
        });
    }

    /**
     * Handle session complete
     */
    async handleSessionComplete(sessionId) {
        console.log('[TUS Manager] Triggering assembly for session:', sessionId);

        try {
            // Trigger server-side assembly
            await this.assembleRecording(sessionId);
        } catch (error) {
            console.error('[TUS Manager] Assembly failed:', error);
            this.emit('error', { sessionId, error: 'Assembly failed' });
        }
    }

    /**
     * Trigger server-side assembly of uploaded chunks
     */
    async assembleRecording(sessionId) {
        const response = await fetch(`/files/${sessionId}/assemble`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ sessionId })
        });

        if (!response.ok) {
            throw new Error(`Assembly failed: ${response.status}`);
        }

        const result = await response.json();
        console.log('[TUS Manager] Assembly complete:', result);

        return result;
    }
}

// Export for use in index.html
window.TusUploadManager = TusUploadManager;
