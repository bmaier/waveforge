#!/bin/bash

# WaveForge Pro - Unified Start Script
# This script sets up and starts the application for demo/development purposes

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           WAVEFORGE PRO - Starting Application            ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed. Please install Python 3.9 or higher.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}✓ Python version: $PYTHON_VERSION${NC}"

# Check if virtual environment exists in project root
if [ ! -d ".venv" ]; then
    echo ""
    echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
    python3 -m venv .venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
echo ""
echo -e "${YELLOW}🔧 Activating virtual environment...${NC}"
source .venv/bin/activate

# Install/upgrade dependencies
echo ""
echo -e "${YELLOW}📥 Installing dependencies...${NC}"
pip install -q --upgrade pip
pip install -q -r backend/requirements.txt

echo -e "${GREEN}✓ Dependencies installed${NC}"

# Create necessary directories
echo ""
echo -e "${YELLOW}📁 Creating necessary directories...${NC}"
mkdir -p backend/uploaded_data
mkdir -p frontend/public

echo -e "${GREEN}✓ Directories ready${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  🚀 Server starting on: http://localhost:8000${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}  • Access the application in your browser${NC}"
echo -e "${YELLOW}  • Press CTRL+C to stop the server${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Start the server
cd backend/app
python3 server.py
