#!/bin/bash

# WaveForge Pro - Stop Script
# This script stops all running WaveForge Pro server instances

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           WAVEFORGE PRO - Stopping Server...              ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Find and kill processes running server.py
SERVER_PIDS=$(pgrep -f "python.*server.py" || true)

if [ -z "$SERVER_PIDS" ]; then
    echo -e "${YELLOW}ℹ No running WaveForge server found${NC}"
    exit 0
fi

echo -e "${YELLOW}→ Found running server processes: $SERVER_PIDS${NC}"

# Kill each process
for PID in $SERVER_PIDS; do
    echo -e "${YELLOW}→ Stopping process $PID...${NC}"
    kill -TERM $PID 2>/dev/null || kill -KILL $PID 2>/dev/null
    
    # Wait for process to terminate
    sleep 1
    
    if ps -p $PID > /dev/null 2>&1; then
        echo -e "${RED}✗ Failed to stop process $PID${NC}"
    else
        echo -e "${GREEN}✓ Process $PID stopped${NC}"
    fi
done

echo ""
echo -e "${GREEN}✓ WaveForge server stopped successfully${NC}"
echo ""

# Also check for uvicorn processes
UVICORN_PIDS=$(pgrep -f "uvicorn.*server:app" || true)

if [ ! -z "$UVICORN_PIDS" ]; then
    echo -e "${YELLOW}→ Found uvicorn processes: $UVICORN_PIDS${NC}"
    for PID in $UVICORN_PIDS; do
        echo -e "${YELLOW}→ Stopping uvicorn process $PID...${NC}"
        kill -TERM $PID 2>/dev/null || kill -KILL $PID 2>/dev/null
        sleep 1
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${RED}✗ Failed to stop process $PID${NC}"
        else
            echo -e "${GREEN}✓ Process $PID stopped${NC}"
        fi
    done
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  All server instances stopped${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
