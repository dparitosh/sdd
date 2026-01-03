#!/bin/bash

###############################################################################
# MBSE Knowledge Graph - Service Management Script
# Purpose: Start, stop, restart, and monitor services
# Usage: bash deployment/scripts/service_manager.sh [start|stop|restart|status|logs]
###############################################################################

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FRONTEND_DIR="$REPO_ROOT/frontend"

# Check if running with systemd or manual mode
if systemctl list-units --type=service | grep -q "mbse-backend"; then
    USE_SYSTEMD=true
else
    USE_SYSTEMD=false
fi

show_usage() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start      Start backend and frontend services"
    echo "  stop       Stop all services"
    echo "  restart    Restart all services"
    echo "  status     Show service status"
    echo "  logs       Tail service logs"
    echo "  backend    Manage backend only (use with start/stop/restart)"
    echo "  frontend   Manage frontend only (use with start/stop/restart)"
    echo ""
    echo "Examples:"
    echo "  $0 start          # Start all services"
    echo "  $0 backend start  # Start backend only"
    echo "  $0 logs           # View logs"
    echo "  $0 status         # Check status"
    echo ""
    echo "Manual mode env vars (defaults are localhost-only for safety):"
    echo "  BACKEND_HOST   (default: 127.0.0.1)"
    echo "  BACKEND_PORT   (default: 5000)"
    echo "  FRONTEND_HOST  (default: 127.0.0.1)"
    echo "  FRONTEND_PORT  (default: 3001)"
}

start_service() {
    local service=$1
    
    if $USE_SYSTEMD; then
        echo -e "${BLUE}Starting $service with systemd...${NC}"
        sudo systemctl start mbse-$service
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ $service started${NC}"
        else
            echo -e "${RED}✗ Failed to start $service${NC}"
            return 1
        fi
    else
        case $service in
            backend)
                echo -e "${BLUE}Starting backend manually...${NC}"
                if ! command -v python3 >/dev/null 2>&1; then
                    echo -e "${RED}✗ python3 not found in PATH${NC}"
                    return 1
                fi
                pushd "$REPO_ROOT" >/dev/null || return 1
                export PYTHONPATH="$REPO_ROOT"
                # By default bind backend to localhost for security.
                # To allow remote access, set BACKEND_HOST (e.g. 0.0.0.0) and/or BACKEND_PORT.
                BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
                BACKEND_PORT="${BACKEND_PORT:-5000}"
                nohup python3 -m uvicorn src.web.app_fastapi:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" > /tmp/mbse-backend.log 2>&1 &
                echo $! > /tmp/mbse-backend.pid
                sleep 2
                if ps -p $(cat /tmp/mbse-backend.pid) > /dev/null; then
                    echo -e "${GREEN}✓ Backend started (PID: $(cat /tmp/mbse-backend.pid))${NC}"
                    popd >/dev/null || true
                else
                    popd >/dev/null || true
                    echo -e "${RED}✗ Backend failed to start${NC}"
                    return 1
                fi
                ;;
            frontend)
                echo -e "${BLUE}Starting frontend manually...${NC}"
                if [ ! -d "$FRONTEND_DIR" ]; then
                    echo -e "${RED}✗ Frontend directory not found: $FRONTEND_DIR${NC}"
                    return 1
                fi
                if ! command -v npm >/dev/null 2>&1; then
                    echo -e "${RED}✗ npm not found in PATH${NC}"
                    return 1
                fi
                pushd "$FRONTEND_DIR" >/dev/null || return 1
                # By default bind frontend preview to localhost for safety.
                # To allow remote access, set FRONTEND_HOST (e.g. 0.0.0.0) and/or FRONTEND_PORT.
                FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
                FRONTEND_PORT="${FRONTEND_PORT:-3001}"
                nohup npm run preview -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" > /tmp/mbse-frontend.log 2>&1 &
                echo $! > /tmp/mbse-frontend.pid
                sleep 2
                if ps -p $(cat /tmp/mbse-frontend.pid) > /dev/null; then
                    echo -e "${GREEN}✓ Frontend started (PID: $(cat /tmp/mbse-frontend.pid))${NC}"
                    popd >/dev/null || true
                else
                    popd >/dev/null || true
                    echo -e "${RED}✗ Frontend failed to start${NC}"
                    return 1
                fi
                ;;
        esac
    fi
}

stop_service() {
    local service=$1
    
    if $USE_SYSTEMD; then
        echo -e "${BLUE}Stopping $service with systemd...${NC}"
        sudo systemctl stop mbse-$service
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ $service stopped${NC}"
        else
            echo -e "${RED}✗ Failed to stop $service${NC}"
            return 1
        fi
    else
        case $service in
            backend)
                if [ -f /tmp/mbse-backend.pid ]; then
                    PID=$(cat /tmp/mbse-backend.pid)
                    echo -e "${BLUE}Stopping backend (PID: $PID)...${NC}"
                    kill $PID 2>/dev/null
                    rm /tmp/mbse-backend.pid
                    echo -e "${GREEN}✓ Backend stopped${NC}"
                else
                    echo -e "${YELLOW}⚠ Backend PID file not found; not attempting broad process kill${NC}"
                    echo -e "${YELLOW}  If backend is running, stop it using its PID or systemd.${NC}"
                fi
                ;;
            frontend)
                if [ -f /tmp/mbse-frontend.pid ]; then
                    PID=$(cat /tmp/mbse-frontend.pid)
                    echo -e "${BLUE}Stopping frontend (PID: $PID)...${NC}"
                    kill $PID 2>/dev/null
                    rm /tmp/mbse-frontend.pid
                    echo -e "${GREEN}✓ Frontend stopped${NC}"
                else
                    echo -e "${YELLOW}⚠ Frontend PID file not found; not attempting broad process kill${NC}"
                    echo -e "${YELLOW}  If frontend is running, stop it using its PID or systemd.${NC}"
                fi
                ;;
        esac
    fi
}

show_status() {
    echo -e "${BLUE}=== Service Status ===${NC}"
    echo ""
    
    if $USE_SYSTEMD; then
        echo "Backend Service:"
        systemctl status mbse-backend --no-pager -l || true
        echo ""
        echo "Frontend Service:"
        systemctl status mbse-frontend --no-pager -l || true
    else
        # Check backend
        if [ -f /tmp/mbse-backend.pid ] && ps -p $(cat /tmp/mbse-backend.pid) > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Backend: Running (PID: $(cat /tmp/mbse-backend.pid))${NC}"
        else
            echo -e "${RED}✗ Backend: Not running${NC}"
        fi
        
        # Check frontend
        if [ -f /tmp/mbse-frontend.pid ] && ps -p $(cat /tmp/mbse-frontend.pid) > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Frontend: Running (PID: $(cat /tmp/mbse-frontend.pid))${NC}"
        else
            echo -e "${RED}✗ Frontend: Not running${NC}"
        fi
        
        echo ""
        echo "Process details:"
        ps aux | grep -E "uvicorn.*src.web.app_fastapi:app|npm run (dev|preview)" | grep -v grep || echo "No processes found"
    fi
}

show_logs() {
    echo -e "${BLUE}=== Service Logs ===${NC}"
    echo "Press Ctrl+C to stop following logs"
    echo ""
    
    if $USE_SYSTEMD; then
        if [ -d "/var/log/mbse" ]; then
            tail -f /var/log/mbse/backend.log /var/log/mbse/frontend.log
        else
            journalctl -u mbse-backend -u mbse-frontend -f
        fi
    else
        if [ -f /tmp/mbse-backend.log ] && [ -f /tmp/mbse-frontend.log ]; then
            tail -f /tmp/mbse-backend.log /tmp/mbse-frontend.log
        elif [ -f /tmp/mbse-backend.log ]; then
            tail -f /tmp/mbse-backend.log
        elif [ -f /tmp/mbse-frontend.log ]; then
            tail -f /tmp/mbse-frontend.log
        else
            echo "No log files found"
        fi
    fi
}

# Main script logic
case "$1" in
    start)
        echo -e "${BLUE}Starting MBSE Knowledge Graph services...${NC}"
        start_service backend
        sleep 2
        start_service frontend
        echo ""
        echo -e "${GREEN}Services started. Check status with: $0 status${NC}"
        ;;
    
    stop)
        echo -e "${BLUE}Stopping MBSE Knowledge Graph services...${NC}"
        stop_service frontend
        stop_service backend
        echo ""
        echo -e "${GREEN}Services stopped${NC}"
        ;;
    
    restart)
        echo -e "${BLUE}Restarting MBSE Knowledge Graph services...${NC}"
        stop_service frontend
        stop_service backend
        sleep 2
        start_service backend
        sleep 2
        start_service frontend
        echo ""
        echo -e "${GREEN}Services restarted${NC}"
        ;;
    
    status)
        show_status
        ;;
    
    logs)
        show_logs
        ;;
    
    backend)
        case "$2" in
            start) start_service backend ;;
            stop) stop_service backend ;;
            restart) stop_service backend; sleep 2; start_service backend ;;
            *) echo "Usage: $0 backend [start|stop|restart]" ;;
        esac
        ;;
    
    frontend)
        case "$2" in
            start) start_service frontend ;;
            stop) stop_service frontend ;;
            restart) stop_service frontend; sleep 2; start_service frontend ;;
            *) echo "Usage: $0 frontend [start|stop|restart]" ;;
        esac
        ;;
    
    *)
        show_usage
        exit 1
        ;;
esac
