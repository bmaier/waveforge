# Test Execution and Allure Reporting Guide

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running Tests](#running-tests)
- [Generating Allure Reports](#generating-allure-reports)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software
1. **Python 3.13+**
2. **Allure Command-Line Tool**

### Installing Allure CLI

#### macOS
```bash
brew install allure
```

#### Linux
```bash
# Download and install
wget https://github.com/allure-framework/allure2/releases/download/2.25.0/allure-2.25.0.tgz
tar -zxvf allure-2.25.0.tgz
sudo mv allure-2.25.0 /opt/allure
echo 'export PATH="/opt/allure/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

#### Windows
```powershell
# Using Scoop
scoop install allure

# Or download from: https://github.com/allure-framework/allure2/releases
```

#### Verify Installation
```bash
allure --version
# Should output: 2.25.0 or higher
```

---

## Installation

### 1. Install Test Dependencies
```bash
# Navigate to project root
cd /path/to/waveforge-pro

# Install test requirements
pip install -r tests/requirements-test.txt
```

### 2. Install Playwright Browsers (for BDD/E2E tests)
```bash
playwright install
```

### 3. Verify Installation
```bash
# Check pytest
pytest --version

# Check behave
behave --version

# Check allure
allure --version
```

---

## Running Tests

### Unit Tests

#### Run All Unit Tests
```bash
# From project root
pytest tests/unit/ -v

# With coverage
pytest tests/unit/ -v --cov=backend --cov-report=html

# With Allure reporting
pytest tests/unit/ -v --alluredir=tests/unit/allure-results
```

#### Run Specific Test File
```bash
pytest tests/unit/test_recording_complete.py -v
```

#### Run Specific Test
```bash
pytest tests/unit/test_recording_complete.py::test_complete_upload_success -v
```

#### Expected Results
```
======================== test session starts =========================
collected 26 items

tests/unit/test_recording_complete.py::test_complete_upload_success PASSED
tests/unit/test_server.py::test_recording_complete_route PASSED
...

=================== 25 passed, 1 skipped in 2.34s ===================
```

---

### Integration Tests

#### Prerequisites
- Backend server running (or use test fixtures)

#### Run All Integration Tests
```bash
# From project root
pytest tests/integration/ -v

# With Allure reporting
pytest tests/integration/ -v --alluredir=tests/integration/allure-results
```

#### Run Specific Integration Test
```bash
pytest tests/integration/test_hybrid_upload.py::test_online_recording_complete -v
```

#### Expected Results
```
======================== test session starts =========================
collected 14 items

tests/integration/test_hybrid_upload.py::test_online_recording_complete PASSED
...

======================== 14 passed in 3.87s =========================
```

---

### BDD Tests (Behave)

#### Prerequisites
1. Backend server running on `http://localhost:8000`
2. Frontend served on `http://localhost:8080`

#### Start Services
```bash
# Terminal 1: Backend
cd backend
python -m app.main

# Terminal 2: Frontend
cd frontend
python -m http.server 8080
```

#### Run All BDD Tests
```bash
# Terminal 3: Tests
cd tests/bdd
behave --format allure_behave.formatter:AllureFormatter --outdir allure-results
```

#### Run Specific Feature
```bash
cd tests/bdd
behave features/online_recording.feature
```

#### Run Specific Scenario
```bash
cd tests/bdd
behave features/online_recording.feature:11
```

#### Run with Tags
```bash
cd tests/bdd
behave --tags=@smoke
behave --tags=@critical
behave --tags=@online
```

#### Dry Run (Check Step Definitions)
```bash
cd tests/bdd
behave --dry-run --summary
```

#### Expected Results
```
Feature: Online Recording with Server Assembly

  Scenario: Record audio with online connection
    Given the user has an active internet connection ... passed
    And the WaveForge Pro application is loaded ... passed
    ...

6 features passed, 0 failed, 0 skipped
58 scenarios passed, 0 failed, 0 skipped
506 steps passed, 0 failed, 0 skipped
```

---

### E2E Tests (Playwright)

#### Run All E2E Tests
```bash
pytest tests/e2e/ -v --headed
```

#### Run Headless
```bash
pytest tests/e2e/ -v
```

#### With Allure
```bash
pytest tests/e2e/ -v --alluredir=tests/e2e/allure-results
```

---

## Generating Allure Reports

### Unit Test Reports

#### Generate Report
```bash
# Step 1: Run tests and generate results
pytest tests/unit/ -v --alluredir=tests/unit/allure-results --clean-alluredir

# Step 2: Generate and open HTML report
cd tests/unit
allure serve allure-results

# Or generate static report
allure generate allure-results --clean -o allure-report
```

#### View Static Report
```bash
cd tests/unit
allure open allure-report
```

---

### Integration Test Reports

#### Generate Report
```bash
# Step 1: Run tests
pytest tests/integration/ -v --alluredir=tests/integration/allure-results --clean-alluredir

# Step 2: Serve report
cd tests/integration
allure serve allure-results
```

---

### BDD Test Reports

#### Generate Report
```bash
# Step 1: Run tests with Allure formatter
cd tests/bdd
behave --format allure_behave.formatter:AllureFormatter --outdir allure-results --format pretty

# Step 2: Generate report
allure serve allure-results

# Or static report
allure generate allure-results --clean -o allure-report
allure open allure-report
```

---

### Combined Report (All Tests)

#### Run All Tests and Generate Combined Report
```bash
#!/bin/bash
# From project root

# Clean previous results
rm -rf allure-results allure-report

# Run all test types
pytest tests/unit/ -v --alluredir=allure-results
pytest tests/integration/ -v --alluredir=allure-results
cd tests/bdd && behave --format allure_behave.formatter:AllureFormatter --outdir ../../allure-results
cd ../..

# Generate combined report
allure generate allure-results --clean -o allure-report
allure open allure-report
```

#### Using Script
```bash
# Create convenience script
chmod +x scripts/run-all-tests.sh
./scripts/run-all-tests.sh
```

---

## Allure Report Features

### What's Included in Reports

1. **Overview Dashboard**
   - Total tests run
   - Pass/Fail rate
   - Duration
   - Flaky tests
   - Trend graphs

2. **Test Suites**
   - Organized by test type (unit/integration/BDD)
   - Duration per suite
   - Status per suite

3. **Graphs**
   - Status distribution
   - Severity distribution
   - Duration trends
   - Categories

4. **Timeline**
   - Parallel execution visualization
   - Test duration timeline

5. **Behaviors (BDD)**
   - Features
   - Stories
   - Scenarios

6. **Test Details**
   - Steps
   - Parameters
   - Attachments (screenshots, logs)
   - Error traces
   - Duration

---

## Advanced Usage

### Add Screenshots to Reports (BDD)

```python
# In tests/bdd/environment.py
import allure
from allure_commons.types import AttachmentType

def after_step(context, step):
    if step.status == 'failed':
        # Capture screenshot on failure
        allure.attach(
            context.page.screenshot(),
            name=f"screenshot_{step.name}",
            attachment_type=AttachmentType.PNG
        )
```

### Add Test Metadata (Pytest)

```python
import allure

@allure.feature('Recording')
@allure.story('Online Recording')
@allure.severity(allure.severity_level.CRITICAL)
@allure.title('Test complete upload success')
def test_complete_upload_success():
    with allure.step('Setup test session'):
        # Test code
        pass
    
    with allure.step('Upload chunks'):
        # Test code
        pass
    
    with allure.step('Verify assembly'):
        # Test code
        pass
```

### Add Custom Categories

Create `categories.json` in allure-results directory:

```json
[
  {
    "name": "Backend Errors",
    "matchedStatuses": ["failed"],
    "messageRegex": ".*backend.*"
  },
  {
    "name": "Frontend Errors",
    "matchedStatuses": ["failed"],
    "messageRegex": ".*frontend.*"
  },
  {
    "name": "Connection Issues",
    "matchedStatuses": ["failed"],
    "messageRegex": ".*connection.*"
  }
]
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests with Allure

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.13'
    
    - name: Install dependencies
      run: |
        pip install -r tests/requirements-test.txt
        playwright install
    
    - name: Run Unit Tests
      run: |
        pytest tests/unit/ -v --alluredir=allure-results
    
    - name: Run Integration Tests
      run: |
        pytest tests/integration/ -v --alluredir=allure-results
    
    - name: Get Allure history
      uses: actions/checkout@v3
      if: always()
      continue-on-error: true
      with:
        ref: gh-pages
        path: gh-pages
    
    - name: Allure Report
      uses: simple-elf/allure-report-action@master
      if: always()
      with:
        allure_results: allure-results
        allure_history: allure-history
        keep_reports: 20
    
    - name: Deploy report to Github Pages
      if: always()
      uses: peaceiris/actions-gh-pages@v3
      with:
        github_token: ${{ secrets.GITHUB_TOKEN }}
        publish_branch: gh-pages
        publish_dir: allure-history
```

---

## Troubleshooting

### Issue: Allure command not found
```bash
# Solution: Add to PATH
export PATH="/opt/allure/bin:$PATH"

# Or reinstall
brew reinstall allure  # macOS
```

### Issue: No tests collected
```bash
# Solution: Check test discovery
pytest --collect-only tests/unit/

# Verify pytest.ini configuration
cat pytest.ini
```

### Issue: Allure results directory empty
```bash
# Solution: Ensure --alluredir flag is used
pytest tests/unit/ -v --alluredir=tests/unit/allure-results

# Check directory exists
ls -la tests/unit/allure-results/
```

### Issue: BDD tests fail to generate Allure results
```bash
# Solution: Verify formatter is loaded
cd tests/bdd
behave --format help | grep allure

# If not found, reinstall
pip install --force-reinstall allure-behave
```

### Issue: Report shows no data
```bash
# Solution: Clean and regenerate
rm -rf allure-results allure-report
pytest tests/unit/ -v --alluredir=allure-results --clean-alluredir
allure generate allure-results --clean -o allure-report
```

### Issue: Port already in use (Allure serve)
```bash
# Solution: Kill existing process
pkill -f "allure"

# Or use different port
allure open allure-report -p 8081
```

---

## Directory Structure

```
waveforge-pro/
├── tests/
│   ├── unit/
│   │   ├── allure-results/       # Generated test results
│   │   ├── allure-report/        # Generated HTML report
│   │   └── test_*.py
│   ├── integration/
│   │   ├── allure-results/
│   │   ├── allure-report/
│   │   └── test_*.py
│   ├── bdd/
│   │   ├── allure-results/
│   │   ├── allure-report/
│   │   ├── features/
│   │   └── steps/
│   └── e2e/
│       ├── allure-results/
│       ├── allure-report/
│       └── test_*.py
├── allure-results/               # Combined results (gitignored)
├── allure-report/                # Combined report (gitignored)
└── pytest.ini
```

---

## Quick Reference

### Common Commands

```bash
# Run all tests with Allure
pytest -v --alluredir=allure-results

# Serve report
allure serve allure-results

# Generate static report
allure generate allure-results --clean -o allure-report

# Open existing report
allure open allure-report

# Clean results
rm -rf allure-results allure-report

# Run specific test type
pytest tests/unit/ -v --alluredir=tests/unit/allure-results
pytest tests/integration/ -v --alluredir=tests/integration/allure-results
cd tests/bdd && behave -f allure_behave.formatter:AllureFormatter -o allure-results
```

---

## Report Access

### Local Development
- **Live Server**: `http://localhost:PORT` (random port assigned by `allure serve`)
- **Static Report**: Open `allure-report/index.html` in browser

### Production/CI
- **GitHub Pages**: `https://<username>.github.io/<repo>/`
- **Standalone Server**: Deploy `allure-report/` directory to web server

---

## Best Practices

1. **Always clean results between runs** to avoid stale data
   ```bash
   pytest -v --alluredir=allure-results --clean-alluredir
   ```

2. **Use descriptive test names** for better reports
   ```python
   def test_user_can_upload_recording_after_connection_restored():
       pass
   ```

3. **Add allure decorators** for rich metadata
   ```python
   @allure.feature('Recording')
   @allure.severity(allure.severity_level.CRITICAL)
   def test_critical_feature():
       pass
   ```

4. **Capture screenshots on failures** (BDD/E2E tests)

5. **Generate reports regularly** to track trends

6. **Keep reports in history** for trend analysis (20-50 runs)

7. **Exclude report directories from git** (already done in `.gitignore`)

---

## Support

For issues or questions:
- Allure Documentation: https://docs.qameta.io/allure/
- Pytest-Allure: https://github.com/allure-framework/allure-python
- Behave-Allure: https://github.com/allure-framework/allure-python
- WaveForge Pro Issues: https://github.com/bmaier/waveforge/issues
