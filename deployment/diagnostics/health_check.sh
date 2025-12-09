#!/bin/bash

###############################################################################
# MBSE Knowledge Graph - Health Check & Diagnostics
# Purpose: Comprehensive system health validation
# Usage: bash deployment/diagnostics/health_check.sh
###############################################################################

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
BACKEND_URL="${BACKEND_URL:-http://localhost:5000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3001}"
TIMEOUT=10

# Counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_WARNING=0

echo -e "${BLUE}"
echo "=========================================="
echo "MBSE Knowledge Graph - Health Check"
echo "=========================================="
echo -e "${NC}"
echo "Backend URL: $BACKEND_URL"
echo "Frontend URL: $FRONTEND_URL"
echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Function to print test result
test_result() {
    local test_name="$1"
    local status="$2"
    local message="$3"
    
    case $status in
        "PASS")
            echo -e "${GREEN}✓ PASS${NC} - $test_name"
            [ -n "$message" ] && echo "         $message"
            ((TESTS_PASSED++))
            ;;
        "FAIL")
            echo -e "${RED}✗ FAIL${NC} - $test_name"
            [ -n "$message" ] && echo "         $message"
            ((TESTS_FAILED++))
            ;;
        "WARN")
            echo -e "${YELLOW}⚠ WARN${NC} - $test_name"
            [ -n "$message" ] && echo "         $message"
            ((TESTS_WARNING++))
            ;;
    esac
}

# Section header
section() {
    echo ""
    echo -e "${BLUE}=== $1 ===${NC}"
}

###############################################################################
# System Prerequisites
###############################################################################
section "System Prerequisites"

# Check Python version
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
        test_result "Python Version" "PASS" "Python $PYTHON_VERSION (>= 3.10 required)"
    else
        test_result "Python Version" "FAIL" "Python $PYTHON_VERSION (<  3.10 required)"
    fi
else
    test_result "Python Installation" "FAIL" "Python 3 not found"
fi

# Check Node.js version
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    NODE_MAJOR=$(echo $NODE_VERSION | cut -d. -f1 | tr -d 'v')
    
    if [ "$NODE_MAJOR" -ge 18 ]; then
        test_result "Node.js Version" "PASS" "Node.js $NODE_VERSION (>= 18 required)"
    else
        test_result "Node.js Version" "FAIL" "Node.js $NODE_VERSION (< 18)"
    fi
else
    test_result "Node.js Installation" "FAIL" "Node.js not found"
fi

# Check npm
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    test_result "npm Installation" "PASS" "npm $NPM_VERSION"
else
    test_result "npm Installation" "FAIL" "npm not found"
fi

# Check pip
if command -v pip3 &> /dev/null || command -v pip &> /dev/null; then
    PIP_VERSION=$(python3 -m pip --version 2>&1 | awk '{print $2}')
    test_result "pip Installation" "PASS" "pip $PIP_VERSION"
else
    test_result "pip Installation" "FAIL" "pip not found"
fi

###############################################################################
# Application Files
###############################################################################
section "Application Files"

# Check critical directories
for dir in src frontend deployment; do
    if [ -d "$dir" ]; then
        test_result "Directory: $dir" "PASS" "Directory exists"
    else
        test_result "Directory: $dir" "FAIL" "Directory not found"
    fi
done

# Check critical files
declare -a CRITICAL_FILES=(
    "src/web/app.py"
    "frontend/src/main.tsx"
    "requirements.txt"
    "package.json"
    ".env"
)

for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        test_result "File: $file" "PASS" "File exists"
    else
        if [ "$file" == ".env" ]; then
            test_result "File: $file" "WARN" "Environment file missing (copy .env.example)"
        else
            test_result "File: $file" "FAIL" "File not found"
        fi
    fi
done

###############################################################################
# Python Dependencies
###############################################################################
section "Python Dependencies"

# Check if in virtual environment
if [ -n "$VIRTUAL_ENV" ]; then
    test_result "Virtual Environment" "PASS" "Active: $VIRTUAL_ENV"
else
    test_result "Virtual Environment" "WARN" "Not using virtual environment"
fi

# Check critical Python packages
declare -a PYTHON_PACKAGES=(
    "flask"
    "neo4j"
    "flask_cors"
    "flask_socketio"
    "authlib"
    "pandas"
    "numpy"
)

for package in "${PYTHON_PACKAGES[@]}"; do
    if python3 -c "import $package" 2>/dev/null; then
        VERSION=$(python3 -c "import $package; print($package.__version__)" 2>/dev/null || echo "unknown")
        test_result "Python package: $package" "PASS" "Version: $VERSION"
    else
        test_result "Python package: $package" "FAIL" "Not installed"
    fi
done

###############################################################################
# Node.js Dependencies
###############################################################################
section "Node.js Dependencies"

if [ -d "node_modules" ]; then
    NODE_MODULES_COUNT=$(find node_modules -maxdepth 1 -type d | wc -l)
    test_result "Node modules installed" "PASS" "$NODE_MODULES_COUNT packages"
    
    # Check critical packages
    declare -a NPM_PACKAGES=(
        "react"
        "vite"
        "@radix-ui/react-tabs"
        "axios"
    )
    
    for package in "${NPM_PACKAGES[@]}"; do
        if [ -d "node_modules/$package" ]; then
            VERSION=$(node -p "require('./node_modules/$package/package.json').version" 2>/dev/null || echo "unknown")
            test_result "npm package: $package" "PASS" "Version: $VERSION"
        else
            test_result "npm package: $package" "FAIL" "Not installed"
        fi
    done
else
    test_result "Node modules" "FAIL" "node_modules directory not found. Run: npm install"
fi

###############################################################################
# Environment Configuration
###############################################################################
section "Environment Configuration"

if [ -f ".env" ]; then
    test_result "Environment file" "PASS" ".env file exists"
    
    # Check critical environment variables
    source .env 2>/dev/null || true
    
    [ -n "$NEO4J_URI" ] && test_result "NEO4J_URI" "PASS" "Configured" || test_result "NEO4J_URI" "FAIL" "Not set"
    [ -n "$NEO4J_USER" ] && test_result "NEO4J_USER" "PASS" "Configured" || test_result "NEO4J_USER" "FAIL" "Not set"
    [ -n "$NEO4J_PASSWORD" ] && test_result "NEO4J_PASSWORD" "PASS" "Configured" || test_result "NEO4J_PASSWORD" "FAIL" "Not set"
    [ -n "$FLASK_PORT" ] && test_result "FLASK_PORT" "PASS" "Port: $FLASK_PORT" || test_result "FLASK_PORT" "WARN" "Using default: 5000"
    
else
    test_result "Environment file" "FAIL" ".env file not found. Copy .env.example to .env"
fi

###############################################################################
# Network Connectivity
###############################################################################
section "Network Connectivity"

# Check if ports are available or in use
check_port() {
    local port=$1
    local service=$2
    
    if command -v netstat &> /dev/null; then
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            test_result "Port $port ($service)" "PASS" "Port is listening"
            return 0
        else
            test_result "Port $port ($service)" "WARN" "Port not listening (service may not be started)"
            return 1
        fi
    elif command -v ss &> /dev/null; then
        if ss -tuln 2>/dev/null | grep -q ":$port "; then
            test_result "Port $port ($service)" "PASS" "Port is listening"
            return 0
        else
            test_result "Port $port ($service)" "WARN" "Port not listening (service may not be started)"
            return 1
        fi
    else
        test_result "Port check tool" "WARN" "Neither netstat nor ss available"
        return 1
    fi
}

check_port 5000 "Backend"
BACKEND_RUNNING=$?

check_port 3001 "Frontend"
FRONTEND_RUNNING=$?

###############################################################################
# Backend API Health
###############################################################################
section "Backend API Health"

if [ $BACKEND_RUNNING -eq 0 ]; then
    # Test health endpoint
    HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" --connect-timeout $TIMEOUT "$BACKEND_URL/api/health" 2>/dev/null || echo -e "\n000")
    HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n 1)
    RESPONSE_BODY=$(echo "$HEALTH_RESPONSE" | head -n -1)
    
    if [ "$HTTP_CODE" == "200" ]; then
        test_result "Backend health endpoint" "PASS" "HTTP 200 OK"
        
        # Parse JSON response
        if command -v jq &> /dev/null; then
            STATUS=$(echo "$RESPONSE_BODY" | jq -r '.status' 2>/dev/null || echo "unknown")
            DB_CONNECTED=$(echo "$RESPONSE_BODY" | jq -r '.database.connected' 2>/dev/null || echo "unknown")
            NODE_COUNT=$(echo "$RESPONSE_BODY" | jq -r '.database.node_count' 2>/dev/null || echo "unknown")
            LATENCY=$(echo "$RESPONSE_BODY" | jq -r '.database.latency_ms' 2>/dev/null || echo "unknown")
            
            [ "$STATUS" == "healthy" ] && test_result "Backend status" "PASS" "Status: $STATUS" || test_result "Backend status" "FAIL" "Status: $STATUS"
            [ "$DB_CONNECTED" == "true" ] && test_result "Neo4j connection" "PASS" "Connected" || test_result "Neo4j connection" "FAIL" "Not connected"
            [ "$NODE_COUNT" != "unknown" ] && test_result "Database nodes" "PASS" "Count: $NODE_COUNT" || test_result "Database nodes" "WARN" "Count unknown"
            [ "$LATENCY" != "unknown" ] && test_result "Database latency" "PASS" "Latency: ${LATENCY}ms" || test_result "Database latency" "WARN" "Latency unknown"
        else
            test_result "JSON parsing" "WARN" "jq not installed, cannot parse response"
        fi
    else
        test_result "Backend health endpoint" "FAIL" "HTTP $HTTP_CODE"
    fi
    
    # Test stats endpoint
    STATS_RESPONSE=$(curl -s -w "\n%{http_code}" --connect-timeout $TIMEOUT "$BACKEND_URL/api/stats" 2>/dev/null || echo -e "\n000")
    HTTP_CODE=$(echo "$STATS_RESPONSE" | tail -n 1)
    
    if [ "$HTTP_CODE" == "200" ]; then
        test_result "Backend stats endpoint" "PASS" "HTTP 200 OK"
    else
        test_result "Backend stats endpoint" "FAIL" "HTTP $HTTP_CODE"
    fi
    
else
    test_result "Backend service" "FAIL" "Backend not running. Start with: sudo systemctl start mbse-backend"
fi

###############################################################################
# Frontend Health
###############################################################################
section "Frontend Health"

if [ $FRONTEND_RUNNING -eq 0 ]; then
    FRONTEND_RESPONSE=$(curl -s -w "\n%{http_code}" --connect-timeout $TIMEOUT "$FRONTEND_URL" 2>/dev/null || echo -e "\n000")
    HTTP_CODE=$(echo "$FRONTEND_RESPONSE" | tail -n 1)
    
    if [ "$HTTP_CODE" == "200" ]; then
        test_result "Frontend accessibility" "PASS" "HTTP 200 OK"
        
        RESPONSE_BODY=$(echo "$FRONTEND_RESPONSE" | head -n -1)
        if echo "$RESPONSE_BODY" | grep -q "MBSE Knowledge Graph"; then
            test_result "Frontend content" "PASS" "Application loaded correctly"
        else
            test_result "Frontend content" "WARN" "Unexpected content"
        fi
    else
        test_result "Frontend accessibility" "FAIL" "HTTP $HTTP_CODE"
    fi
else
    test_result "Frontend service" "FAIL" "Frontend not running. Start with: sudo systemctl start mbse-frontend"
fi

###############################################################################
# System Resources
###############################################################################
section "System Resources"

# Check disk space
DISK_USAGE=$(df -h . | tail -n 1 | awk '{print $5}' | tr -d '%')
if [ "$DISK_USAGE" -lt 80 ]; then
    test_result "Disk space" "PASS" "Usage: ${DISK_USAGE}%"
elif [ "$DISK_USAGE" -lt 90 ]; then
    test_result "Disk space" "WARN" "Usage: ${DISK_USAGE}% (getting high)"
else
    test_result "Disk space" "FAIL" "Usage: ${DISK_USAGE}% (critically low)"
fi

# Check memory
if command -v free &> /dev/null; then
    MEM_TOTAL=$(free -m | awk 'NR==2{print $2}')
    MEM_USED=$(free -m | awk 'NR==2{print $3}')
    MEM_PERCENT=$((MEM_USED * 100 / MEM_TOTAL))
    
    if [ "$MEM_PERCENT" -lt 80 ]; then
        test_result "Memory usage" "PASS" "Usage: ${MEM_PERCENT}% (${MEM_USED}MB / ${MEM_TOTAL}MB)"
    elif [ "$MEM_PERCENT" -lt 90 ]; then
        test_result "Memory usage" "WARN" "Usage: ${MEM_PERCENT}% (${MEM_USED}MB / ${MEM_TOTAL}MB)"
    else
        test_result "Memory usage" "FAIL" "Usage: ${MEM_PERCENT}% (${MEM_USED}MB / ${MEM_TOTAL}MB)"
    fi
fi

# Check CPU load
if [ -f /proc/loadavg ]; then
    LOAD_AVG=$(cat /proc/loadavg | awk '{print $1}')
    CPU_CORES=$(nproc)
    test_result "CPU load average" "PASS" "Load: $LOAD_AVG (${CPU_CORES} cores)"
fi

###############################################################################
# Summary
###############################################################################
echo ""
echo -e "${BLUE}=========================================="
echo "Health Check Summary"
echo "==========================================${NC}"
echo ""
echo -e "${GREEN}Passed:  $TESTS_PASSED${NC}"
echo -e "${YELLOW}Warnings: $TESTS_WARNING${NC}"
echo -e "${RED}Failed:  $TESTS_FAILED${NC}"
echo -e "Total:   $((TESTS_PASSED + TESTS_WARNING + TESTS_FAILED))"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All critical checks passed!${NC}"
    echo ""
    echo "Application URLs:"
    echo "  Frontend: $FRONTEND_URL"
    echo "  Backend:  $BACKEND_URL"
    echo "  Health:   $BACKEND_URL/api/health"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some checks failed. Please review the issues above.${NC}"
    echo ""
    echo "Common fixes:"
    echo "  - Install missing dependencies: sudo bash deployment/scripts/install.sh"
    echo "  - Configure environment: nano .env"
    echo "  - Start services: sudo systemctl start mbse-backend mbse-frontend"
    echo "  - Check logs: tail -f /var/log/mbse/backend.log"
    echo ""
    exit 1
fi
