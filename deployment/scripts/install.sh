#!/bin/bash

###############################################################################
# MBSE Knowledge Graph - Installation Script for Cloud VM
# Purpose: Automated installation on fresh Ubuntu/Debian VM
# Usage: sudo bash deployment/scripts/install.sh
###############################################################################

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PYTHON_VERSION="3.12"
NODE_VERSION="20"
APP_USER="mbse"
APP_DIR="/opt/mbse-neo4j-graph-rep"
LOG_DIR="/var/log/mbse"
SERVICE_DIR="/etc/systemd/system"

echo -e "${BLUE}"
echo "=========================================="
echo "MBSE Knowledge Graph - Installation"
echo "=========================================="
echo -e "${NC}"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
   exit 1
fi

echo -e "${YELLOW}This script will install:${NC}"
echo "  - Python $PYTHON_VERSION and dependencies"
echo "  - Node.js $NODE_VERSION and npm"
echo "  - MBSE Knowledge Graph application"
echo "  - Systemd services for backend and frontend"
echo ""
read -p "Continue with installation? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation cancelled."
    exit 0
fi

# Function to print section headers
print_section() {
    echo ""
    echo -e "${BLUE}=== $1 ===${NC}"
}

# Function to check command success
check_success() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $1${NC}"
    else
        echo -e "${RED}✗ $1 failed${NC}"
        exit 1
    fi
}

# Update system
print_section "Updating system packages"
apt-get update -qq
check_success "System update"

# Install essential tools
print_section "Installing essential tools"
apt-get install -y -qq \
    curl \
    wget \
    git \
    build-essential \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    jq
check_success "Essential tools installation"

# Install Python 3.12
print_section "Installing Python $PYTHON_VERSION"
add-apt-repository -y ppa:deadsnakes/ppa 2>/dev/null || true
apt-get update -qq
apt-get install -y -qq \
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-venv \
    python${PYTHON_VERSION}-dev \
    python3-pip
check_success "Python installation"

# Set Python 3.12 as default
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python${PYTHON_VERSION} 1
update-alternatives --set python3 /usr/bin/python${PYTHON_VERSION}
python3 --version
check_success "Python version configuration"

# Install Node.js
print_section "Installing Node.js $NODE_VERSION"
curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - >/dev/null 2>&1
apt-get install -y -qq nodejs
check_success "Node.js installation"

echo "Node.js version: $(node --version)"
echo "npm version: $(npm --version)"

# Create application user
print_section "Creating application user"
if id "$APP_USER" &>/dev/null; then
    echo -e "${YELLOW}User $APP_USER already exists${NC}"
else
    useradd -r -m -s /bin/bash "$APP_USER"
    check_success "User creation"
fi

# Create directories
print_section "Creating application directories"
mkdir -p "$APP_DIR"
mkdir -p "$LOG_DIR"
chown -R $APP_USER:$APP_USER "$APP_DIR"
chown -R $APP_USER:$APP_USER "$LOG_DIR"
check_success "Directory creation"

# Copy application files
print_section "Copying application files"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

echo "Copying from: $PROJECT_ROOT"
echo "Copying to: $APP_DIR"

# Copy application files (excluding unnecessary directories)
rsync -av --progress \
    --exclude 'node_modules' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.git' \
    --exclude '.pytest_cache' \
    --exclude 'htmlcov' \
    --exclude '.coverage' \
    --exclude 'logs/*.log' \
    --exclude 'dist' \
    "$PROJECT_ROOT/" "$APP_DIR/"
check_success "Application files copy"

# Set ownership
chown -R $APP_USER:$APP_USER "$APP_DIR"

# Install Python dependencies
print_section "Installing Python dependencies"
cd "$APP_DIR"
sudo -u $APP_USER python3 -m pip install --upgrade pip
sudo -u $APP_USER python3 -m pip install -r requirements.txt
check_success "Python dependencies installation"

# Install Node.js dependencies
print_section "Installing Node.js dependencies"
cd "$APP_DIR"
sudo -u $APP_USER npm install --production=false
check_success "Node.js dependencies installation"

# Build frontend
print_section "Building frontend application"
cd "$APP_DIR"
sudo -u $APP_USER npm run build
check_success "Frontend build"

# Create environment file
print_section "Creating environment configuration"
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env" 2>/dev/null || \
    cp "$APP_DIR/.env.production.template" "$APP_DIR/.env" 2>/dev/null || \
    cat > "$APP_DIR/.env" << 'EOF'
# Neo4j Configuration
NEO4J_URI=neo4j+s://your-neo4j-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j

# API Configuration
API_HOST=0.0.0.0
API_PORT=5000

# Frontend Configuration
VITE_PORT=3001
VITE_API_URL=http://localhost:5000

# Security
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)

# Logging
LOG_LEVEL=INFO
EOF
    chown $APP_USER:$APP_USER "$APP_DIR/.env"
    echo -e "${YELLOW}⚠ Environment file created. Please edit $APP_DIR/.env with your settings${NC}"
else
    echo -e "${GREEN}✓ Environment file already exists${NC}"
fi

# Create systemd service for backend
print_section "Creating systemd services"
cat > "$SERVICE_DIR/mbse-backend.service" << EOF
[Unit]
Description=MBSE Knowledge Graph Backend
After=network.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PYTHONPATH=$APP_DIR"
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/python3 -m uvicorn src.web.app_fastapi:app --host 0.0.0.0 --port 5000
Restart=always
RestartSec=10
StandardOutput=append:$LOG_DIR/backend.log
StandardError=append:$LOG_DIR/backend-error.log

[Install]
WantedBy=multi-user.target
EOF
check_success "Backend service creation"

# Create systemd service for frontend (production server)
cat > "$SERVICE_DIR/mbse-frontend.service" << EOF
[Unit]
Description=MBSE Knowledge Graph Frontend
After=network.target mbse-backend.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/npm run preview -- --host 0.0.0.0 --port 3001
Restart=always
RestartSec=10
StandardOutput=append:$LOG_DIR/frontend.log
StandardError=append:$LOG_DIR/frontend-error.log

[Install]
WantedBy=multi-user.target
EOF
check_success "Frontend service creation"

# Reload systemd
systemctl daemon-reload
check_success "Systemd reload"

# Enable services (don't start yet - user needs to configure .env)
systemctl enable mbse-backend.service
systemctl enable mbse-frontend.service
check_success "Service enablement"

# Create firewall rules (if ufw is installed)
if command -v ufw &> /dev/null; then
    print_section "Configuring firewall"
    ufw allow 5000/tcp comment "MBSE Backend API"
    ufw allow 3001/tcp comment "MBSE Frontend UI"
    check_success "Firewall configuration"
fi

# Installation complete
echo ""
echo -e "${GREEN}"
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo -e "${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo "1. Configure environment variables:"
echo "   sudo nano $APP_DIR/.env"
echo ""
echo "2. Test the configuration:"
echo "   sudo bash $APP_DIR/deployment/diagnostics/health_check.sh"
echo ""
echo "3. Start the services:"
echo "   sudo systemctl start mbse-backend"
echo "   sudo systemctl start mbse-frontend"
echo ""
echo "4. Check service status:"
echo "   sudo systemctl status mbse-backend"
echo "   sudo systemctl status mbse-frontend"
echo ""
echo "5. View logs:"
echo "   tail -f $LOG_DIR/backend.log"
echo "   tail -f $LOG_DIR/frontend.log"
echo ""
echo -e "${BLUE}Application URLs:${NC}"
echo "  - Frontend UI: http://$(hostname -I | awk '{print $1}'):3001"
echo "  - Backend API: http://$(hostname -I | awk '{print $1}'):5000"
echo "  - Health Check: http://$(hostname -I | awk '{print $1}'):5000/api/health"
echo ""
echo -e "${GREEN}Installation location: $APP_DIR${NC}"
echo -e "${GREEN}Logs location: $LOG_DIR${NC}"
echo ""
