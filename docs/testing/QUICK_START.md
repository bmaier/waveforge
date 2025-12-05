# Testing Quick Start Guide

## 🚀 Quick Commands

### Run All Tests with Allure Report
```bash
./scripts/run-all-tests.sh
```

### Run Individual Test Suites
```bash
./scripts/test-unit.sh           # Unit tests only
./scripts/test-integration.sh    # Integration tests only
./scripts/test-bdd.sh            # BDD tests only (requires services)
```

---

## 📋 Prerequisites

### 1. Install Allure CLI
```bash
# macOS
brew install allure

# Linux
wget https://github.com/allure-framework/allure2/releases/download/2.25.0/allure-2.25.0.tgz
tar -zxvf allure-2.25.0.tgz
sudo mv allure-2.25.0 /opt/allure
export PATH="/opt/allure/bin:$PATH"

# Windows
scoop install allure
```

### 2. Install Python Dependencies
```bash
pip install -r tests/requirements-test.txt
playwright install  # For BDD/E2E tests
```

---

## 🧪 Running Tests

### Unit Tests (No Services Required)
```bash
# Simple run
pytest tests/unit/ -v

# With Allure report
./scripts/test-unit.sh

# Manual with Allure
pytest tests/unit/ -v --alluredir=tests/unit/allure-results
cd tests/unit && allure serve allure-results
```

**Expected**: ✅ 25 passed, 1 skipped

---

### Integration Tests (No Services Required)
```bash
# Simple run
pytest tests/integration/ -v

# With Allure report
./scripts/test-integration.sh

# Manual with Allure
pytest tests/integration/ -v --alluredir=tests/integration/allure-results
cd tests/integration && allure serve allure-results
```

**Expected**: ✅ 14 passed

---

### BDD Tests (Requires Services)

#### Start Services
```bash
# Terminal 1: Backend
cd backend
python -m app.main

# Terminal 2: Frontend
cd frontend
python -m http.server 8080
```

#### Run Tests
```bash
# Terminal 3: With script
./scripts/test-bdd.sh

# Or manually
cd tests/bdd
behave --format allure_behave.formatter:AllureFormatter -o allure-results -f pretty
allure serve allure-results
```

**Expected**: ✅ 58 scenarios, 506 steps (when services running)

---

## 📊 Viewing Reports

### Option 1: Live Server (Recommended)
```bash
allure serve allure-results
# Opens browser automatically at http://localhost:PORT
```

### Option 2: Static Report
```bash
allure generate allure-results --clean -o allure-report
allure open allure-report
# Or open allure-report/index.html in browser
```

---

## 📁 Report Locations

```
tests/
├── unit/
│   ├── allure-results/    # Test execution data
│   └── allure-report/     # HTML report
├── integration/
│   ├── allure-results/
│   └── allure-report/
└── bdd/
    ├── allure-results/
    └── allure-report/
```

**Note**: All `allure-*` directories are gitignored automatically.

---

## 🔧 Troubleshooting

### Allure command not found
```bash
# Add to PATH
export PATH="/opt/allure/bin:$PATH"

# Or reinstall
brew reinstall allure  # macOS
```

### No tests collected
```bash
# Verify test discovery
pytest --collect-only tests/unit/

# Check from project root
pwd  # Should be /path/to/waveforge-pro
```

### BDD tests fail
```bash
# Ensure services are running
curl http://localhost:8000/health  # Backend
curl http://localhost:8080         # Frontend

# Check step definitions
cd tests/bdd && behave --dry-run
```

### Empty allure-results
```bash
# Ensure --alluredir flag is used
pytest tests/unit/ -v --alluredir=tests/unit/allure-results

# Check directory
ls -la tests/unit/allure-results/
```

---

## 📚 Full Documentation

See [docs/testing/ALLURE_REPORTING.md](../docs/testing/ALLURE_REPORTING.md) for:
- Detailed installation instructions
- Advanced Allure features
- CI/CD integration
- Custom categories and metadata
- Screenshot capture
- Trend analysis

---

## ✅ Test Status Summary

| Test Suite | Tests | Status | Command |
|------------|-------|--------|---------|
| Unit | 26 | ✅ 25 passed, 1 skipped | `./scripts/test-unit.sh` |
| Integration | 14 | ✅ 14 passed | `./scripts/test-integration.sh` |
| BDD | 58 scenarios | ✅ 506 steps defined | `./scripts/test-bdd.sh` |

---

## 🎯 Quick Examples

### Run specific test
```bash
pytest tests/unit/test_recording_complete.py::test_complete_upload_success -v
```

### Run with coverage
```bash
pytest tests/unit/ -v --cov=backend --cov-report=html
open htmlcov/index.html
```

### Run BDD feature
```bash
cd tests/bdd
behave features/online_recording.feature
```

### Run BDD scenario
```bash
cd tests/bdd
behave features/online_recording.feature:11
```

### Clean all reports
```bash
rm -rf tests/*/allure-* allure-results allure-report
```

---

## 💡 Tips

1. **Always clean results** between test runs for accurate reports
2. **Use scripts** for consistent execution
3. **Check logs** in allure-report for failures
4. **View trends** by keeping old reports
5. **Add screenshots** to BDD tests for better debugging

---

## 🆘 Support

- **Full Guide**: [docs/testing/ALLURE_REPORTING.md](../docs/testing/ALLURE_REPORTING.md)
- **Allure Docs**: https://docs.qameta.io/allure/
- **Issues**: https://github.com/bmaier/waveforge/issues
