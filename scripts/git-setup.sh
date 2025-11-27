#!/bin/bash

# WaveForge Pro - Git Setup and GitHub Push Script
# This script initializes git, commits all files, and pushes to GitHub

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  WaveForge Pro - Git Setup Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Step 1: Initialize Git (if not already)
if [ ! -d .git ]; then
    echo -e "${YELLOW}→ Initializing Git repository...${NC}"
    git init
    echo -e "${GREEN}✓ Git repository initialized${NC}"
else
    echo -e "${GREEN}✓ Git repository already exists${NC}"
fi

# Step 2: Configure Git (if not set)
if [ -z "$(git config user.name)" ]; then
    echo -e "${YELLOW}→ Configuring Git user...${NC}"
    git config user.name "Berthold Maier"
    git config user.email "berthold.maier@gmail.com"  # Update this!
    echo -e "${GREEN}✓ Git user configured${NC}"
    echo -e "${YELLOW}  Note: Update email in .git/config if needed${NC}"
else
    echo -e "${GREEN}✓ Git user already configured: $(git config user.name)${NC}"
fi

# Step 3: Add remote (GitHub)
REPO_URL="https://github.com/bmaier/waveforge.git"

if git remote | grep -q "origin"; then
    echo -e "${YELLOW}→ Updating remote origin...${NC}"
    git remote set-url origin "$REPO_URL"
    echo -e "${GREEN}✓ Remote origin updated${NC}"
else
    echo -e "${YELLOW}→ Adding remote origin...${NC}"
    git remote add origin "$REPO_URL"
    echo -e "${GREEN}✓ Remote origin added${NC}"
fi

echo -e "${BLUE}Remote URL: ${REPO_URL}${NC}"
echo ""

# Step 4: Check status
echo -e "${YELLOW}→ Checking repository status...${NC}"
git status --short
echo ""

# Step 5: Add all files
echo -e "${YELLOW}→ Adding all files to staging...${NC}"
git add .
echo -e "${GREEN}✓ All files staged${NC}"
echo ""

# Step 6: Commit
echo -e "${YELLOW}→ Creating initial commit...${NC}"
git commit -m "Initial commit: WaveForge Pro v1.0.0

- Professional DAW with browser-based audio recording
- CrashGuard system with automatic recovery
- Multi-language support (DE/EN)
- BITV 2.0 accessibility compliance
- Kubernetes deployment with Kustomize
- HTTPS by default with Let's Encrypt
- Comprehensive documentation and testing
- Docker support
- Multi-stage deployment (dev/staging/prod)"

echo -e "${GREEN}✓ Initial commit created${NC}"
echo ""

# Step 7: Rename branch to main (if needed)
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${YELLOW}→ Renaming branch to 'main'...${NC}"
    git branch -M main
    echo -e "${GREEN}✓ Branch renamed to 'main'${NC}"
else
    echo -e "${GREEN}✓ Already on 'main' branch${NC}"
fi
echo ""

# Step 8: Push to GitHub
echo -e "${YELLOW}→ Pushing to GitHub...${NC}"
echo -e "${BLUE}  This will push to: ${REPO_URL}${NC}"
echo ""
read -p "Continue with push? (yes/no): " confirm

if [ "$confirm" = "yes" ]; then
    echo -e "${YELLOW}→ Pushing to origin/main...${NC}"
    git push -u origin main
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ Successfully pushed to GitHub!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}Repository URL:${NC}"
    echo -e "  https://github.com/bmaier/waveforge"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo -e "  1. Visit your repository on GitHub"
    echo -e "  2. Add repository description and topics"
    echo -e "  3. Enable GitHub Pages (optional)"
    echo -e "  4. Configure branch protection rules"
    echo -e "  5. Set up GitHub Actions for CI/CD (optional)"
else
    echo -e "${YELLOW}Push cancelled. You can push later with:${NC}"
    echo -e "  git push -u origin main"
fi

echo ""
