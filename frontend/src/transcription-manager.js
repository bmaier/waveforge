
class TranscriptionManager {
    constructor() {
        this.socket = null;
        this.isEnabled = false;
        this.isProcessing = false;
        this.sessionId = null;

        // UI Elements
        this.toggle = document.getElementById('liveTranscriptToggle');
        this.display = document.getElementById('transcriptDisplay');
        this.content = document.getElementById('transcriptContent');
        this.badge = document.getElementById('liveBadge');
        this.formatSelect = document.getElementById('recordingFormat');

        // Bind events
        if (this.formatSelect) {
            this.formatSelect.addEventListener('change', () => this.checkEligibility());
        }

        // Initial check
        this.checkEligibility();

        // Listen for online status
        window.addEventListener('online', () => this.checkEligibility());
        window.addEventListener('offline', () => this.checkEligibility());
    }

    checkEligibility() {
        // Only enabled checking online status
        // We now support WebM via backend conversion
        const isOnline = navigator.onLine;

        if (this.toggle) {
            if (!isOnline) {
                this.toggle.disabled = true;
                this.toggle.checked = false;
                this.isEnabled = false;
                this.toggle.parentElement.title = "Live Transcription requires Internet connection";
            } else {
                this.toggle.disabled = false;
                this.toggle.parentElement.title = "Enable Live Transcription (Gemini AI)";
                this.isEnabled = this.toggle.checked;
            }
        }
    }

    toggleLiveTranscript(checkbox) {
        this.isEnabled = checkbox.checked;
        if (this.isEnabled) {
            this.display.classList.add('active');
            this.content.innerHTML = '<div class="transcript-placeholder">Waiting for recording to start...</div>';
        } else {
            // Only hide if not recording, otherwise we might want to keep showing what we have?
            // Requirement said "if active". Let's hide it to disable.
            this.display.classList.remove('active');
        }
    }

    startParams(sessionId) {
        if (!this.isEnabled) return;

        this.sessionId = sessionId;
        this.isProcessing = true;
        this.badge.classList.remove('hidden');
        this.content.innerHTML = ''; // Clear previous
        this.connectWebSocket();
    }

    connectWebSocket() {
        if (this.socket) {
            this.socket.close();
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        // Handle port mapping if needed (e.g. dev environment vs prod)
        const host = window.location.host;
        const wsUrl = `${protocol}//${host}/ws/transcribe`;

        console.log("Connecting to Transcription WS:", wsUrl);

        try {
            this.socket = new WebSocket(wsUrl);

            this.socket.onopen = () => {
                console.log("Transcript WS connected");
            };

            this.socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            };

            this.socket.onerror = (error) => {
                console.error("Transcript WS Error:", error);
                this.appendError("Connection error - Transcription stopped");
                this.stop();
            };

            this.socket.onclose = () => {
                console.log("Transcript WS closed");
                if (this.isProcessing) {
                    this.appendError("Connection lost");
                    this.stop();
                }
            };
        } catch (e) {
            console.error("WS Setup Failed", e);
            this.isEnabled = false;
            this.stop();
        }
    }

    sendAudioChunk(chunk) {
        if (!this.isEnabled || !this.isProcessing || !this.socket || this.socket.readyState !== WebSocket.OPEN) return;
        this.socket.send(chunk);
    }

    stop() {
        this.isProcessing = false;
        if (this.badge) this.badge.classList.add('hidden');
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
    }

    handleMessage(data) {
        if (data.error) {
            this.appendError(data.error);
            return;
        }

        if (data.text) {
            this.appendText(data.text, "Speaker");
        }
    }

    appendText(text, speaker = "Unknown") {
        const line = document.createElement('div');
        line.className = 'transcript-line';
        // Add timestamp if available?
        line.innerHTML = `<span class="speaker-label">${speaker}:</span> <span class="transcript-text">${text}</span>`;

        this.content.appendChild(line);
        this.content.scrollTop = this.content.scrollHeight;
    }

    appendError(msg) {
        const line = document.createElement('div');
        line.className = 'transcript-line';
        line.innerHTML = `<span style="color: #f87171">[System]: ${msg}</span>`;
        this.content.appendChild(line);
    }

    async triggerPostProcess(sessionId) {
        console.log(`Triggering post-process for ${sessionId}`);

        // Find the button (assuming we add a data attribute or class in playlist)
        // This is a bit loose since we don't have the button ref passed in directly usually
        // But let's assume UI calling logic handles button state, or we try to find it.

        showToast("Starting transcription...", false);

        try {
            const response = await fetch(`/transcribe/${sessionId}`, { method: 'POST' });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || "Processing failed");
            }

            const result = await response.json();

            showToast("Transcription complete!");

            // If this session is the one currently loaded/visible in transcript box
            // Or if we decide to show the transcript box
            this.display.classList.add('active');

            // Format transcript text (assuming plain text for now, maybe parse it)
            this.content.innerHTML = '';

            // Split by lines or simple display
            // Mock result has "Speaker: Text" format
            const lines = result.transcript_preview.split('\n'); // Or full transcript
            // Note: result.file_path implies we might need to load the full file content if prompt said "display".
            // The API returns "transcript_preview". Let's use that for now + msg.

            this.appendError("Post-processing complete. Showing preview:");

            // Naive display
            const div = document.createElement('div');
            div.className = 'transcript-text';
            div.style.whiteSpace = 'pre-wrap';
            div.textContent = result.transcript_preview; // Or fetch full file if needed
            this.content.appendChild(div);

        } catch (e) {
            console.error(e);
            showToast(`Transcription failed: ${e.message}`, true);
        }
    }
}

// Global instance
window.TranscriptionManager = new TranscriptionManager();

// Helper for HTML interaction
window.toggleLiveTranscript = function (el) {
    if (window.TranscriptionManager) {
        window.TranscriptionManager.toggleLiveTranscript(el);
    }
};
