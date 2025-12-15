#!/bin/bash
# Run all tests and generate combined Allure report
# Usage: ./scripts/run-all-tests.sh

set -e  # Exit on error

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "WaveForge Pro - Test Suite with Allure"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Ensure required CLIs are available
if ! command -v pytest >/dev/null 2>&1; then
    echo -e "${RED}pytest not found. Install test deps: pip install -r tests/requirements-test.txt${NC}"
    exit 1
fi

if ! command -v behave >/dev/null 2>&1; then
    echo -e "${RED}behave not found. Install test deps: pip install -r tests/requirements-test.txt${NC}"
    exit 1
fi

# Clean previous results
echo -e "${YELLOW}Cleaning previous test results...${NC}"
rm -rf allure-results allure-report
rm -rf tests/unit/allure-results tests/unit/allure-report
rm -rf tests/integration/allure-results tests/integration/allure-report
rm -rf tests/bdd/allure-results tests/bdd/allure-report
mkdir -p allure-results
echo ""

# Run Unit Tests
echo -e "${YELLOW}=========================================="
echo "Running Unit Tests..."
echo -e "==========================================${NC}"
pytest tests/unit/ -v --alluredir=allure-results --clean-alluredir || {
    echo -e "${RED}Unit tests failed!${NC}"
}
echo ""

# Run Integration Tests
echo -e "${YELLOW}=========================================="
echo "Running Integration Tests..."
echo -e "==========================================${NC}"
pytest tests/integration/ -v --alluredir=allure-results || {
    echo -e "${RED}Integration tests failed!${NC}"
}
echo ""

# Run BDD Tests (if services are running)
echo -e "${YELLOW}=========================================="
echo "Running BDD Tests..."
echo -e "==========================================${NC}"
echo -e "${YELLOW}Note: Ensure backend (port 8000) and frontend (port 8080) are running${NC}"
read -p "Continue with BDD tests? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd tests/bdd
    behave --format allure_behave.formatter:AllureFormatter \
           --outfile ../../allure-results \
           --format pretty || {
        echo -e "${RED}BDD tests failed!${NC}"
    }
    cd ../..
else
    echo -e "${YELLOW}Skipping BDD tests${NC}"
fi
echo ""

# Generate Combined Report
echo -e "${YELLOW}=========================================="
echo "Generating Allure Report..."
echo -e "==========================================${NC}"

if [ ! -d "allure-results" ] || [ -z "$(ls -A allure-results)" ]; then
    echo -e "${RED}Error: No test results found!${NC}"
    echo "Run tests first before generating report."
    exit 1
fi

allure generate allure-results --clean -o allure-report

echo ""
echo -e "${GREEN}=========================================="
echo "Report generated successfully!"
echo -e "==========================================${NC}"
echo ""
echo "To view the report:"
echo "  1. Serve live: allure open allure-report"
echo "  2. Or open:    open allure-report/index.html"
echo ""

# Ask to open report
read -p "Open Allure report now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    allure open allure-report
fi
