#!/bin/bash
# Run unit tests with Allure reporting
# Usage: ./scripts/test-unit.sh

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "Running Unit Tests with Allure"
echo "=========================================="
echo ""

# Clean previous results
rm -rf tests/unit/allure-results tests/unit/allure-report

# Run tests
pytest tests/unit/ -v \
    --alluredir=tests/unit/allure-results \
    --clean-alluredir \
    --tb=short

# Generate report
cd tests/unit
allure generate allure-results --clean -o allure-report

echo ""
echo "Report generated at: tests/unit/allure-report/"
echo "To view: allure open tests/unit/allure-report"
echo ""

# Ask to open
read -p "Open report now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    allure open allure-report
fi
