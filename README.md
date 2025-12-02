# WaveForge Pro 🎙️

**WaveForge Pro** is a professional-grade, browser-based Digital Audio Workstation (DAW) featuring advanced recording capabilities with crash recovery, cloud synchronization, and full accessibility compliance (BITV 2.0).

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](docs/LICENSE.md)
[![Accessibility](https://img.shields.io/badge/BITV_2.0-Compliant-success.svg)](docs/ACCESSIBILITY_COMPLIANCE.md)

## ✨ Features

### Core Capabilities
- **🎤 Professional Audio Recording** - High-quality browser-based audio recording with Web Audio API
- **🛡️ CrashGuard System** - Advanced crash recovery with automatic state restoration
- **☁️ Cloud Synchronization** - Seamless upload of recordings with chunked transfer for large files
- **🔄 TUS Resumable Uploads** - Industry-standard resumable uploads (tus.io) with automatic retry
- **🌐 Multi-Language Support** - Full German (DE) and English (EN) localization
- **♿ BITV 2.0 Accessibility** - Complete keyboard navigation and screen reader support
- **📱 Progressive Web App** - Offline capability with Service Worker
- **💾 IndexedDB Storage** - Client-side persistent storage for recordings
- **🎨 Modern UI** - Tailwind CSS with responsive design

### Technical Highlights
- **🔒 HTTPS by Default** - Automatic TLS/SSL with Let's Encrypt
- **🛡️ Security Headers** - HSTS, CSP, X-Frame-Options, and more
- **📦 Chunked Uploads** - Reliable file transfers for large recordings
- **🔄 Resumable Uploads** - TUS protocol with automatic offset detection and resume capability
- **📡 Offline Support** - Background sync when connection is restored
- **⚡ Parallel Uploads** - Up to 3 concurrent chunk uploads
- **🔀 Hybrid Upload System** - TUS primary with custom chunking fallback
- **📊 Real-time Waveform** - Live audio visualization
- **✂️ Audio Editing** - Trim and modify recordings
- **📋 Playlist Management** - Organize your recordings
- **⌨️ Keyboard Shortcuts** - Efficient workflow
- **🎨 Theme Support** - Dark/Light mode

## 🚀 Quick Start

### Two Usage Modes

WaveForge Pro supports **two deployment modes** with automatic feature detection:

1. **🌐 HTTP Mode (Full Features)** - All features including cloud sync
2. **📁 Offline Mode (file://)** - Local-only features, no server required

### Prerequisites
- **Python 3.13+** installed (only for HTTP mode)
- **uv** package manager (installs automatically if not present)
- **Git** for cloning the repository
- **Modern Browser** with Web Audio API support

> **Note:** The start script will automatically install `uv` if it's not found. Alternatively, you can install it manually:
> ```bash
> # macOS/Linux
> curl -LsSf https://astral.sh/uv/install.sh | sh
> 
> # Or with pip
> pip install uv
> 
> # Or with cargo
> cargo install uv
> ```

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/bmaier/waveforge.git
cd waveforge-pro
```

2. **Start the application:**
```bash
./start.sh
```

That's it! The script will automatically:
- Create a virtual environment
- Install all dependencies
- Create necessary directories
- Start the FastAPI server

3. **Access the application:**
   Open your browser and navigate to:
   ```
   http://localhost:8000
   ```

### Stopping the Server
```bash
./stop.sh
```

## 📁 Offline Mode (file:// URL)

**WaveForge Pro can run without a web server** by opening `index.html` directly in your browser. Perfect for offline use or quick testing!

### What Works in Offline Mode

✅ **Available Features:**
- Audio Recording (Microphone) up to 8+ hours
- Web Audio API (EQ, Visualizer, Playback)
- IndexedDB Storage (local persistence)
- Local Download (WAV, WebM, MP3)
- Playback with Speed Control
- CrashGuard (local chunk recovery)

❌ **Unavailable Features:**
- Service Worker (browser security restriction)
- Cloud Synchronization (no backend)
- Background Upload Queue (requires Service Worker)
- TUS Resumable Uploads (requires server)
- Offline Sync (requires Service Worker API)

### How to Use Offline Mode

1. **Open directly in browser:**
   ```bash
   # macOS
   open frontend/src/index.html
   
   # Linux
   xdg-open frontend/src/index.html
   
   # Windows
   start frontend/src/index.html
   ```

2. **Yellow warning banner appears:** "⚠ OFFLINE MODE: Running from file:// - Cloud features disabled"

3. **Use local features:** Record, playback, download - all work perfectly!

4. **Upload buttons disabled:** Cloud icon (☁) is grayed out automatically

### Recommendation: Local Web Server

For **full functionality** including cloud sync, use a local web server (no internet required!):

```bash
# Simple Python server
python3 -m http.server 8080
# Then open: http://localhost:8080/frontend/src/index.html

# Benefits:
✅ All features work (Service Worker, Upload Queue, etc.)
✅ No internet connection needed
✅ Same as production environment
```

### Technical Details

The app uses **automatic protocol detection** to enable/disable features:

```javascript
// Automatic environment detection
const RuntimeEnvironment = {
    isFileProtocol: location.protocol === 'file:',
    isHTTP: location.protocol.startsWith('http'),
    
    features: {
        serviceWorker: false,  // ❌ Blocked by browser in file://
        cloudUpload: false,     // ❌ No server available
        localRecording: true,   // ✅ Always works
        downloadBlob: true      // ✅ Always works
    }
};
```

**Your existing HTTP installation is NOT affected** - both modes coexist perfectly!

## 📋 Project Structure

```
waveforge-pro/
├── backend/                    # Backend application
│   ├── app/                    # FastAPI application
│   │   ├── server.py           # Main server file
│   │   └── main.py             # Application entry point
│   ├── config/                 # Configuration files
│   ├── uploaded_data/          # Uploaded audio storage
│   ├── requirements.txt        # Python dependencies
│   └── pyproject.toml          # Project metadata
│
├── frontend/                   # Frontend application
│   ├── src/                    # Source files
│   │   ├── index.html          # Main application UI
│   │   └── sw.js               # Service Worker
│   └── public/                 # Static assets
│       └── favicon.svg         # Application icon
│
├── docs/                       # Documentation
│   ├── architecture/           # Architecture documentation
│   ├── api/                    # API documentation
│   ├── user-guide/             # User guides
│   ├── ACCESSIBILITY_COMPLIANCE.md
│   ├── BUGFIXES.md
│   ├── INSTALLATION.md
│   └── LICENSE.md
│
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests (pytest)
│   ├── integration/            # BDD integration tests (Behave)
│   │   ├── features/           # Gherkin feature files
│   │   └── steps/              # Step definitions
│   └── e2e/                    # End-to-end GUI tests
│       ├── features/           # Gherkin scenarios
│       └── steps/              # Playwright step definitions
│
├── deployment/                 # Deployment configurations
│   ├── k8s/                    # Kubernetes manifests
│   └── docker/                 # Docker configurations
│
├── scripts/                    # Utility scripts
├── start.sh                    # Application startup script
└── stop.sh                     # Application stop script
```

## 🏗️ Architecture

WaveForge Pro follows a clean separation of concerns with a modern architecture:

- **Backend**: FastAPI-based REST API for audio processing and storage
- **Frontend**: Vanilla JavaScript with Web Audio API for audio manipulation
- **Storage**: Dual-layer storage (IndexedDB + Server-side)
- **Upload System**: Hybrid TUS + Custom chunking with Service Worker
- **Deployment**: Kubernetes-ready with Docker support

### 🔄 Upload Architecture

WaveForge Pro uses a sophisticated dual-upload system:

#### **TUS Protocol (Primary)**
- **Industry Standard**: Implements [tus.io](https://tus.io/) v1.0.0 resumable upload protocol
- **Chunk-by-Chunk**: Uploads during recording (not whole file at end)
- **Resumability**: HEAD endpoint checks offset, PATCH resumes from exact position
- **512KB Sub-chunks**: Efficient TUS chunk size for optimal resumability
- **Automatic Assembly**: Server assembles chunks when upload completes
- **Checksum Support**: SHA-1/SHA-256 verification (optional)
- **Metadata**: Recording name, format, chunk info in base64-encoded headers

#### **Custom Chunking (Fallback)**
- **Reliability**: Falls back automatically if TUS fails
- **1MB Chunks**: Proven reliable for large file transfers
- **Sequential Upload**: Ordered chunk upload with retry logic
- **IndexedDB Queue**: Persistent queue survives page reloads

#### **Service Worker Integration**
- **Background Sync**: Uploads continue when app is closed
- **Offline Support**: Queues chunks when offline, uploads when online
- **Connection Detection**: Automatic retry when connection restored
- **Concurrent Uploads**: Max 3 simultaneous uploads to avoid overwhelming network
- **Exponential Backoff**: Smart retry delays (2s → 60s max)

#### **Configuration**
Users can choose upload method via UI selector (bottom-right corner):
- **TUS (Default)**: Resumable uploads with automatic retry
- **Custom**: Legacy chunking system as fallback

Configuration persists in LocalStorage across sessions.

For detailed architecture documentation, see [docs/architecture/](docs/architecture/).

## 🧪 Testing

WaveForge Pro includes a comprehensive test suite:

### Run Unit Tests
```bash
pytest tests/unit/
```

### Run Integration Tests (BDD)
```bash
behave tests/integration/
```

### Run E2E Tests (Playwright)
```bash
pytest tests/e2e/
```

### Run All Tests with Coverage
```bash
pytest tests/ --cov=backend --cov-report=html
```

For more details, see [Testing Guide](docs/user-guide/TESTING.md).

## 📚 Documentation

- **[Installation Guide](docs/INSTALLATION.md)** - Detailed installation instructions
- **[User Guide](docs/user-guide/)** - End-user documentation
- **[API Documentation](docs/api/)** - REST API reference
- **[Architecture](docs/architecture/)** - System design and architecture
- **[Accessibility](docs/ACCESSIBILITY_COMPLIANCE.md)** - BITV 2.0 compliance details
- **[Bug Fixes](docs/BUGFIXES.md)** - Known issues and resolutions

## 🔧 Development

### Setting Up Development Environment

1. **Clone and setup:**
```bash
git clone https://github.com/yourusername/waveforge-pro.git
cd waveforge-pro
./start.sh
```

2. **Install test dependencies:**
```bash
source .venv/bin/activate
uv pip install -r tests/requirements-test.txt
```

3. **Install Playwright browsers:**
```bash
playwright install
```

### Running in Development Mode
```bash
cd backend/app
python3 -m uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

### Code Style
- Python: PEP 8
- JavaScript: ES6+
- HTML/CSS: BEM methodology

## 🐳 Docker Deployment

### Build and Run with Docker
```bash
cd deployment/docker
docker-compose up -d
```

### Using Dockerfile
```bash
docker build -t waveforge-pro -f deployment/docker/Dockerfile .
docker run -p 8000:8000 waveforge-pro
```

## ☸️ Kubernetes Deployment

### Multi-Stage Deployment with Kustomize

WaveForge Pro uses **Kustomize** for professional multi-stage deployments with automatic HTTPS/TLS:

```bash
# Deploy to development
./scripts/deploy-k8s.sh deploy development

# Deploy to staging
./scripts/deploy-k8s.sh deploy staging

# Deploy to production
./scripts/deploy-k8s.sh deploy production
```

### 🔒 HTTPS by Default

All deployments automatically enforce HTTPS with:
- ✅ Automatic TLS/SSL certificates via Let's Encrypt
- ✅ Forced HTTPS redirect (HTTP → HTTPS)
- ✅ HSTS enabled in production (1 year max-age)
- ✅ Security headers (X-Frame-Options, CSP, etc.)
- ✅ Auto-renewal of certificates

### Environment Comparison

| Environment | URL | Replicas | TLS | HSTS |
|------------|-----|----------|-----|------|
| Development | https://dev.waveforge-pro.example.com | 1 | ✅ Staging | ❌ |
| Staging | https://staging.waveforge-pro.example.com | 2 | ✅ Staging | ❌ |
| Production | https://waveforge-pro.example.com | 3-10 | ✅ Production | ✅ |

### Check Deployment Status
```bash
./scripts/deploy-k8s.sh status <environment>
```

### Rollback
```bash
./scripts/rollback-k8s.sh <environment>
```

### Documentation

- **[Kustomize Deployment Guide](docs/deployment/KUSTOMIZE_DEPLOYMENT.md)** - Complete deployment guide
- **[HTTPS Configuration](docs/deployment/HTTPS_CONFIGURATION.md)** - SSL/TLS setup and security
- **[Quick Reference](docs/deployment/KUSTOMIZE_QUICK_REFERENCE.md)** - Command cheat sheet

## 🌍 Multi-Language Support

WaveForge Pro supports multiple languages:
- **German (DE)** - Default language
- **English (EN)**

Toggle language using the language selector in the UI or by pressing **Alt+L**.

## ♿ Accessibility

WaveForge Pro is fully compliant with **BITV 2.0** (German accessibility standard):

- ✅ Complete keyboard navigation
- ✅ Screen reader support (ARIA labels)
- ✅ High contrast mode
- ✅ Configurable font sizes
- ✅ Focus indicators
- ✅ Alternative text for all media

See [Accessibility Compliance](docs/ACCESSIBILITY_COMPLIANCE.md) for details.

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Contribution Guidelines
- Write tests for new features
- Follow code style guidelines
- Update documentation
- Ensure all tests pass

## 📄 License

This project is licensed under the MIT License - see [LICENSE.md](docs/LICENSE.md) for details.

## 👤 Author

**Berthold Maier**
- Version: 1.0.0
- GitHub: [@bmaier](https://github.com/bmaier)

## 🙏 Acknowledgments

- FastAPI for the excellent web framework
- Tailwind CSS for the utility-first CSS framework
- Web Audio API for audio processing capabilities
- All contributors and users

## 📞 Support

If you encounter any issues:

1. Check the [Troubleshooting Guide](docs/user-guide/TROUBLESHOOTING.md)
2. Review [Known Issues](docs/BUGFIXES.md)
3. Open an issue on GitHub

## 🔄 Upload System Features

### TUS Resumable Uploads

WaveForge Pro implements the [TUS protocol](https://tus.io/) for reliable, resumable uploads:

#### **How It Works**
1. **During Recording**: Chunks are uploaded in real-time as audio is recorded
2. **Connection Loss**: If connection drops, uploads pause automatically
3. **Reconnection**: When online, Service Worker resumes from exact byte offset
4. **No Data Loss**: Already-uploaded chunks are never re-sent
5. **Automatic Assembly**: Server assembles chunks into final file when complete

#### **TUS Endpoints**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/files/{session_id}/chunks/` | Create new chunk upload |
| PATCH | `/files/{session_id}/chunks/{chunk_id}` | Upload chunk data at offset |
| HEAD | `/files/{session_id}/chunks/{chunk_id}` | Check current upload offset (resume) |
| GET | `/files/{session_id}/status` | Get upload session status |
| POST | `/files/{session_id}/assemble` | Manually trigger assembly |
| DELETE | `/files/{session_id}` | Cancel upload and cleanup |

#### **TUS Headers**
- `Tus-Resumable: 1.0.0` - Protocol version
- `Upload-Offset: <bytes>` - Current upload position
- `Upload-Length: <bytes>` - Total file size
- `Upload-Metadata: <base64>` - Recording metadata
- `Location: <url>` - Chunk upload URL

#### **Configuration**

Upload method is configurable via UI (bottom-right corner):

```javascript
// Programmatic configuration
localStorage.setItem('uploadMethod', 'tus');    // Use TUS (default)
localStorage.setItem('uploadMethod', 'custom'); // Use custom chunking
```

#### **Monitoring Uploads**

Check pending uploads:
- UI shows badge with count in upload method selector
- Service Worker tracks all pending chunks
- Console logs show upload progress and retry attempts

#### **Benefits**
- ✅ **Reliable**: Survives network interruptions, browser crashes, page reloads
- ✅ **Efficient**: Only uploads missing data, never duplicates
- ✅ **Real-time**: Chunks uploaded during recording (memory efficient)
- ✅ **Standard**: Uses industry-standard TUS protocol (tus.io)
- ✅ **Automatic**: No user intervention needed for resume/retry
- ✅ **Fallback**: Automatically switches to custom chunking if TUS fails

## 🗺️ Roadmap

- [x] TUS resumable upload protocol implementation
- [x] Service Worker background upload with offline support
- [x] Hybrid upload system (TUS + Custom fallback)
- [ ] WebSocket support for real-time collaboration
- [ ] Multi-track editing
- [ ] Audio effects and filters
- [ ] VST plugin support
- [ ] Mobile app versions
- [ ] Cloud storage integrations (S3, Google Drive, Dropbox)

---

**Made with ❤️ by Berthold Maier - Herrsching**
