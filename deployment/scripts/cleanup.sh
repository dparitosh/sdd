#!/bin/bash

###############################################################################
# MBSE Knowledge Graph - Cleanup Script
# Purpose: Remove temporary files, caches, and build artifacts
# Usage: bash deployment/scripts/cleanup.sh
###############################################################################

set -e

echo "=========================================="
echo "MBSE Knowledge Graph - Cleanup Script"
echo "=========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

cd "$PROJECT_ROOT"

echo "Project root: $PROJECT_ROOT"
echo ""

# Function to safely remove files/directories
safe_remove() {
    local path="$1"
    local description="$2"
    
    if [ -e "$path" ]; then
        echo -e "${YELLOW}Removing: $description${NC}"
        rm -rf "$path"
        echo -e "${GREEN}✓ Removed: $path${NC}"
    else
        echo -e "${GREEN}✓ Already clean: $description${NC}"
    fi
}

echo "=== Removing Python cache files ==="
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -exec rm -f {} + 2>/dev/null || true
find . -type f -name "*.pyo" -exec rm -f {} + 2>/dev/null || true
find . -type f -name "*.pyd" -exec rm -f {} + 2>/dev/null || true
echo -e "${GREEN}✓ Python cache cleaned${NC}"
echo ""

echo "=== Removing test and coverage artifacts ==="
safe_remove ".pytest_cache" "pytest cache"
safe_remove ".coverage" "coverage data"
safe_remove "htmlcov" "HTML coverage report"
safe_remove ".tox" "tox environments"
echo ""

echo "=== Removing build artifacts ==="
safe_remove "build" "build directory"
safe_remove "dist" "distribution directory"
safe_remove "*.egg-info" "egg info"
safe_remove ".eggs" "eggs directory"
echo ""

echo "=== Removing Node.js artifacts ==="
safe_remove "node_modules/.cache" "Vite cache"
safe_remove ".vite" "Vite temp files"
safe_remove "frontend/.vite" "Frontend Vite temp files"
echo ""

echo "=== Removing log files ==="
safe_remove "logs/*.log" "application logs"
safe_remove "/tmp/backend.log" "backend temp log"
safe_remove "/tmp/frontend.log" "frontend temp log"
safe_remove "/tmp/build.log" "build temp log"
echo ""

echo "=== Removing old backup files ==="
find . -type f -name "*.old" -exec rm -f {} + 2>/dev/null || true
find . -type f -name "*.bak" -exec rm -f {} + 2>/dev/null || true
find . -type f -name "*~" -exec rm -f {} + 2>/dev/null || true
echo -e "${GREEN}✓ Backup files removed${NC}"
echo ""

echo "=== Removing OS-specific files ==="
find . -type f -name ".DS_Store" -exec rm -f {} + 2>/dev/null || true
find . -type f -name "Thumbs.db" -exec rm -f {} + 2>/dev/null || true
echo -e "${GREEN}✓ OS files removed${NC}"
echo ""

echo "=== Removing editor temporary files ==="
find . -type f -name "*.swp" -exec rm -f {} + 2>/dev/null || true
find . -type f -name "*.swo" -exec rm -f {} + 2>/dev/null || true
find . -type f -name "*~" -exec rm -f {} + 2>/dev/null || true
echo -e "${GREEN}✓ Editor temp files removed${NC}"
echo ""

echo "=== Optional: Remove node_modules (for fresh install) ==="
read -p "Do you want to remove node_modules? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    safe_remove "node_modules" "Node.js dependencies"
    echo -e "${YELLOW}Note: Run 'npm install' to reinstall dependencies${NC}"
fi
echo ""

echo "=== Cleanup Summary ==="
echo -e "${GREEN}✓ Cleanup completed successfully!${NC}"
echo ""
echo "Cleaned directories:"
echo "  - Python cache (__pycache__, *.pyc)"
echo "  - Test artifacts (.pytest_cache, .coverage)"
echo "  - Build artifacts (dist/, build/)"
echo "  - Log files (logs/*.log)"
echo "  - Temporary files (*.old, *.bak, *~)"
echo "  - OS files (.DS_Store, Thumbs.db)"
echo ""
echo "Ready for deployment!"
