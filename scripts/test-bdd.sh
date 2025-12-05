#!/bin/bash
# Run BDD tests with Allure reporting
# Usage: ./scripts/test-bdd.sh

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "Running BDD Tests with Allure"
echo "=========================================="
echo ""

# Check if services are running
echo "Prerequisites:"
echo "  - Backend running on http://localhost:8000"
echo "  - Frontend running on http://localhost:8080"
echo ""

read -p "Are services running? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Please start services first:"
    echo "  Terminal 1: cd backend && python -m app.main"
    echo "  Terminal 2: cd frontend && python -m http.server 8080"
    exit 1
fi

# Clean previous results
rm -rf tests/bdd/allure-results tests/bdd/allure-report

# Run tests
cd tests/bdd
behave \
    --format allure_behave.formatter:AllureFormatter \
    --outdir allure-results \
    --format pretty \
    --no-capture

# Generate report
allure generate allure-results --clean -o allure-report

echo ""
echo "Report generated at: tests/bdd/allure-report/"
echo "To view: allure open tests/bdd/allure-report"
echo ""

# Ask to open
read -p "Open report now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    allure open allure-report
fi
