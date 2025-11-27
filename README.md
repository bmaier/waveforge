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
- **🌐 Multi-Language Support** - Full German (DE) and English (EN) localization
- **♿ BITV 2.0 Accessibility** - Complete keyboard navigation and screen reader support
- **📱 Progressive Web App** - Offline capability with Service Worker
- **💾 IndexedDB Storage** - Client-side persistent storage for recordings
- **🎨 Modern UI** - Tailwind CSS with responsive design

### Technical Highlights
- **🔒 HTTPS by Default** - Automatic TLS/SSL with Let's Encrypt
- **🛡️ Security Headers** - HSTS, CSP, X-Frame-Options, and more
- **📦 Chunked Uploads** - Reliable file transfers for large recordings
- **📊 Real-time Waveform** - Live audio visualization
- **✂️ Audio Editing** - Trim and modify recordings
- **📋 Playlist Management** - Organize your recordings
- **⌨️ Keyboard Shortcuts** - Efficient workflow
- **🎨 Theme Support** - Dark/Light mode

## 🚀 Quick Start

### Prerequisites
- **Python 3.13+** installed
- **Git** for cloning the repository

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/waveforge-pro.git
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
- **Deployment**: Kubernetes-ready with Docker support

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
pip install -r tests/requirements-test.txt
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

## 🗺️ Roadmap

- [ ] WebSocket support for real-time collaboration
- [ ] Multi-track editing
- [ ] Audio effects and filters
- [ ] VST plugin support
- [ ] Mobile app versions
- [ ] Cloud storage integrations

---

**Made with ❤️ by Berthold Maier - Herrsching**
