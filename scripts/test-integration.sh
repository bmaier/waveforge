#!/bin/bash
# Run integration tests with Allure reporting
# Usage: ./scripts/test-integration.sh

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "Running Integration Tests with Allure"
echo "=========================================="
echo ""

# Clean previous results
rm -rf tests/integration/allure-results tests/integration/allure-report

# Run tests
pytest tests/integration/ -v \
    --alluredir=tests/integration/allure-results \
    --clean-alluredir \
    --tb=short

# Generate report
cd tests/integration
allure generate allure-results --clean -o allure-report

echo ""
echo "Report generated at: tests/integration/allure-report/"
echo "To view: allure open tests/integration/allure-report"
echo ""

# Ask to open
read -p "Open report now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    allure open allure-report
fi
