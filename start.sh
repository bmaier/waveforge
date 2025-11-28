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

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo ""
    echo -e "${RED}❌ uv is not installed. Installing uv...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo -e "${GREEN}✓ uv installed${NC}"
    echo -e "${YELLOW}ℹ Please restart your terminal and run this script again${NC}"
    exit 0
fi

echo -e "${GREEN}✓ uv package manager: $(uv --version)${NC}"

# Create virtual environment and install dependencies with uv
echo ""
echo -e "${YELLOW}📦 Setting up environment with uv...${NC}"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}→ Creating virtual environment...${NC}"
    uv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"

fi

# Check for .env file
if [ ! -f "backend/.env" ]; then
    if [ -f "backend/.env.example" ]; then
        echo -e "${YELLOW}→ Creating .env from example...${NC}"
        cp backend/.env.example backend/.env
        echo -e "${GREEN}✓ Created backend/.env${NC}"
    else
        echo -e "${YELLOW}⚠ No .env file found and no example available.${NC}"
    fi
fi

# Activate virtual environment
echo ""
echo -e "${YELLOW}🔧 Activating virtual environment...${NC}"
source .venv/bin/activate

# Install dependencies with uv
echo ""
echo -e "${YELLOW}📥 Installing dependencies...${NC}"

if [ -f "backend/requirements.txt" ]; then
    uv pip install -r backend/requirements.txt
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    echo -e "${RED}❌ backend/requirements.txt not found${NC}"
    exit 1
fi

# Create necessary directories
echo ""
echo -e "${YELLOW}📁 Creating necessary directories...${NC}"
mkdir -p backend/uploaded_data/temp
mkdir -p backend/uploaded_data/completed
mkdir -p backend/uploaded_data/tus_uploads
mkdir -p backend/uploaded_data/tus_sessions
mkdir -p backend/uploaded_data/tus_temp
mkdir -p frontend/public

echo -e "${GREEN}✓ Directories ready (including TUS upload storage)${NC}"
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
