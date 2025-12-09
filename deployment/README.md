# MBSE Knowledge Graph - Cloud VM Deployment Guide

## 📋 Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Detailed Installation](#detailed-installation)
5. [Configuration](#configuration)
6. [Service Management](#service-management)
7. [Diagnostics & Troubleshooting](#diagnostics--troubleshooting)
8. [Production Deployment](#production-deployment)
9. [Maintenance](#maintenance)
10. [Security](#security)

---

## Overview

This deployment package provides everything needed to deploy the MBSE Knowledge Graph application on a cloud VM instance (AWS, Azure, GCP, or any Ubuntu/Debian-based server).

### What's Included

```
deployment/
├── scripts/
│   ├── install.sh           # Automated installation script
│   ├── cleanup.sh            # Clean temporary files
│   └── service_manager.sh    # Start/stop/restart services
├── diagnostics/
│   ├── health_check.sh       # Comprehensive health validation
│   └── test_database.sh      # Neo4j connectivity tests
├── config/
│   └── (runtime configurations)
└── README.md                 # This file
```

### System Architecture

```
┌─────────────────────────────────────┐
│         Cloud VM Instance           │
│  ┌──────────────────────────────┐  │
│  │   Frontend (Port 3001)       │  │
│  │   - React + Vite             │  │
│  │   - Nginx (optional)         │  │
│  └──────────────────────────────┘  │
│  ┌──────────────────────────────┐  │
│  │   Backend (Port 5000)        │  │
│  │   - Flask + Python 3.12      │  │
│  │   - REST APIs                │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
              │
              ↓
┌─────────────────────────────────────┐
│      Neo4j Cloud (Aura)             │
│      - Graph Database               │
│      - 3,257+ Nodes                 │
└─────────────────────────────────────┘
```

---

## Prerequisites

### Cloud VM Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 2 cores | 4 cores |
| **RAM** | 4 GB | 8 GB |
| **Disk** | 20 GB SSD | 50 GB SSD |
| **OS** | Ubuntu 20.04 LTS | Ubuntu 22.04 LTS |
| **Network** | 10 Mbps | 100 Mbps |

### Supported Cloud Providers
- ✅ AWS EC2 (t3.medium or larger)
- ✅ Azure Virtual Machines (Standard_B2s or larger)
- ✅ Google Cloud Compute Engine (e2-medium or larger)
- ✅ DigitalOcean Droplets ($24/month or larger)
- ✅ Any Ubuntu/Debian VPS

### Required External Services
- **Neo4j Aura** (or self-hosted Neo4j 4.x/5.x)
  - Sign up: https://neo4j.com/cloud/aura/
  - Free tier available (sufficient for evaluation)
- **OAuth Provider** (optional, for authentication)
  - Azure AD, Google, Okta, or generic OIDC

### Network Requirements
- **Inbound Ports**:
  - 22 (SSH)
  - 5000 (Backend API)
  - 3001 (Frontend UI)
  - 80/443 (optional, for reverse proxy)
- **Outbound Ports**:
  - 443 (Neo4j Cloud, package repositories)

---

## Quick Start

### 1. Clone Repository to VM

```bash
# SSH into your cloud VM
ssh user@your-vm-ip

# Clone repository
cd /tmp
git clone https://github.com/dparitosh/mbse-neo4j-graph-rep.git
cd mbse-neo4j-graph-rep
```

### 2. Run Automated Installation

```bash
# Make scripts executable
chmod +x deployment/scripts/*.sh
chmod +x deployment/diagnostics/*.sh

# Run installation (requires sudo)
sudo bash deployment/scripts/install.sh
```

The installer will:
- ✅ Install Python 3.12, Node.js 20, and dependencies
- ✅ Create application user and directories
- ✅ Copy application files to `/opt/mbse-neo4j-graph-rep`
- ✅ Install Python and Node.js dependencies
- ✅ Build frontend production bundle
- ✅ Create systemd services
- ✅ Configure firewall rules

**Installation time**: 5-10 minutes

### 3. Configure Environment

```bash
# Edit configuration file
sudo nano /opt/mbse-neo4j-graph-rep/.env
```

**Required settings**:
```bash
# Neo4j Configuration
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-neo4j-password
NEO4J_DATABASE=neo4j

# Flask Configuration
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_ENV=production

# Frontend Configuration
VITE_PORT=3001
```

Save and exit (Ctrl+X, Y, Enter)

### 4. Run Diagnostics

```bash
# Test configuration
cd /opt/mbse-neo4j-graph-rep
bash deployment/diagnostics/health_check.sh
```

If all checks pass, proceed to start services.

### 5. Start Services

```bash
# Start both backend and frontend
sudo systemctl start mbse-backend
sudo systemctl start mbse-frontend

# Check status
sudo systemctl status mbse-backend
sudo systemctl status mbse-frontend
```

### 6. Access Application

Open browser:
- **Frontend UI**: `http://your-vm-ip:3001`
- **Backend API**: `http://your-vm-ip:5000`
- **Health Check**: `http://your-vm-ip:5000/api/health`

---

## Detailed Installation

### Manual Installation Steps

If you prefer manual installation or the automated script fails:

#### Step 1: System Preparation

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install essential tools
sudo apt-get install -y curl wget git build-essential
```

#### Step 2: Install Python 3.12

```bash
# Add deadsnakes PPA
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update

# Install Python 3.12
sudo apt-get install -y python3.12 python3.12-venv python3.12-dev python3-pip

# Set as default
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# Verify
python3 --version  # Should show Python 3.12.x
```

#### Step 3: Install Node.js 20

```bash
# Add NodeSource repository
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -

# Install Node.js
sudo apt-get install -y nodejs

# Verify
node --version  # Should show v20.x.x
npm --version   # Should show 10.x.x
```

#### Step 4: Create Application Structure

```bash
# Create user
sudo useradd -r -m -s /bin/bash mbse

# Create directories
sudo mkdir -p /opt/mbse-neo4j-graph-rep
sudo mkdir -p /var/log/mbse

# Copy application files
sudo cp -r . /opt/mbse-neo4j-graph-rep/

# Set ownership
sudo chown -R mbse:mbse /opt/mbse-neo4j-graph-rep
sudo chown -R mbse:mbse /var/log/mbse
```

#### Step 5: Install Dependencies

```bash
cd /opt/mbse-neo4j-graph-rep

# Python dependencies
sudo -u mbse python3 -m pip install -r requirements.txt

# Node.js dependencies
sudo -u mbse npm install

# Build frontend
sudo -u mbse npm run build
```

#### Step 6: Configure Services

```bash
# Create backend service
sudo tee /etc/systemd/system/mbse-backend.service > /dev/null << 'EOF'
[Unit]
Description=MBSE Knowledge Graph Backend
After=network.target

[Service]
Type=simple
User=mbse
Group=mbse
WorkingDirectory=/opt/mbse-neo4j-graph-rep
Environment="PYTHONPATH=/opt/mbse-neo4j-graph-rep"
ExecStart=/usr/bin/python3 -m src.web.app
Restart=always
RestartSec=10
StandardOutput=append:/var/log/mbse/backend.log
StandardError=append:/var/log/mbse/backend-error.log

[Install]
WantedBy=multi-user.target
EOF

# Create frontend service
sudo tee /etc/systemd/system/mbse-frontend.service > /dev/null << 'EOF'
[Unit]
Description=MBSE Knowledge Graph Frontend
After=network.target mbse-backend.service

[Service]
Type=simple
User=mbse
Group=mbse
WorkingDirectory=/opt/mbse-neo4j-graph-rep
ExecStart=/usr/bin/npm run preview -- --host 0.0.0.0 --port 3001
Restart=always
RestartSec=10
StandardOutput=append:/var/log/mbse/frontend.log
StandardError=append:/var/log/mbse/frontend-error.log

[Install]
WantedBy=multi-user.target
EOF

# Reload and enable
sudo systemctl daemon-reload
sudo systemctl enable mbse-backend
sudo systemctl enable mbse-frontend
```

---

## Configuration

### Environment Variables

Edit `/opt/mbse-neo4j-graph-rep/.env`:

#### Neo4j Configuration
```bash
# Cloud instance (Neo4j Aura)
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io

# Self-hosted
# NEO4J_URI=bolt://localhost:7687

NEO4J_USER=neo4j
NEO4J_PASSWORD=your-secure-password
NEO4J_DATABASE=neo4j
NEO4J_MAX_CONNECTIONS=50
```

#### Flask Backend
```bash
FLASK_HOST=0.0.0.0              # Listen on all interfaces
FLASK_PORT=5000                 # Backend port
FLASK_ENV=production            # production or development
FLASK_DEBUG=False               # Never true in production
SECRET_KEY=your-secret-key      # Generate with: openssl rand -hex 32
```

#### Frontend
```bash
VITE_PORT=3001                  # Frontend port
VITE_API_URL=http://localhost:5000  # Backend URL
```

#### Authentication (Optional)
```bash
# OAuth2 Configuration
OAUTH_CLIENT_ID=your-client-id
OAUTH_CLIENT_SECRET=your-client-secret
OAUTH_REDIRECT_URI=http://your-vm-ip:3001/auth/callback
JWT_SECRET_KEY=your-jwt-secret  # Generate with: openssl rand -hex 32
```

#### Logging
```bash
LOG_LEVEL=INFO                  # DEBUG, INFO, WARNING, ERROR
LOG_FILE=/var/log/mbse/app.log
```

### Firewall Configuration

```bash
# Using ufw (Ubuntu)
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 5000/tcp   # Backend
sudo ufw allow 3001/tcp   # Frontend
sudo ufw enable

# Using firewalld (RHEL/CentOS)
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --permanent --add-port=3001/tcp
sudo firewall-cmd --reload
```

### Cloud Provider Security Groups

#### AWS EC2
- Navigate to EC2 → Security Groups
- Add inbound rules:
  - Type: Custom TCP, Port: 5000, Source: 0.0.0.0/0
  - Type: Custom TCP, Port: 3001, Source: 0.0.0.0/0

#### Azure
- Navigate to Virtual Machines → Networking
- Add inbound port rules: 5000, 3001

#### GCP
- Navigate to VPC Network → Firewall rules
- Create rules for ports: 5000, 3001

---

## Service Management

### Using Service Manager Script

```bash
cd /opt/mbse-neo4j-graph-rep

# Start all services
bash deployment/scripts/service_manager.sh start

# Stop all services
bash deployment/scripts/service_manager.sh stop

# Restart all services
bash deployment/scripts/service_manager.sh restart

# Check status
bash deployment/scripts/service_manager.sh status

# View logs
bash deployment/scripts/service_manager.sh logs

# Manage individual services
bash deployment/scripts/service_manager.sh backend start
bash deployment/scripts/service_manager.sh frontend restart
```

### Using systemctl (Direct)

```bash
# Start services
sudo systemctl start mbse-backend
sudo systemctl start mbse-frontend

# Stop services
sudo systemctl stop mbse-backend
sudo systemctl stop mbse-frontend

# Restart services
sudo systemctl restart mbse-backend
sudo systemctl restart mbse-frontend

# Check status
sudo systemctl status mbse-backend
sudo systemctl status mbse-frontend

# View logs
sudo journalctl -u mbse-backend -f
sudo journalctl -u mbse-frontend -f

# Enable auto-start on boot
sudo systemctl enable mbse-backend
sudo systemctl enable mbse-frontend
```

### Log Locations

```bash
# Systemd services
/var/log/mbse/backend.log
/var/log/mbse/backend-error.log
/var/log/mbse/frontend.log
/var/log/mbse/frontend-error.log

# View logs
tail -f /var/log/mbse/backend.log
tail -f /var/log/mbse/frontend.log

# Search logs
grep "ERROR" /var/log/mbse/backend.log
grep "health" /var/log/mbse/backend.log | tail -20
```

---

## Diagnostics & Troubleshooting

### Health Check Script

```bash
cd /opt/mbse-neo4j-graph-rep

# Run comprehensive health check
bash deployment/diagnostics/health_check.sh
```

**What it checks:**
- ✅ System prerequisites (Python, Node.js, npm)
- ✅ Application files and directories
- ✅ Python and Node.js dependencies
- ✅ Environment configuration
- ✅ Network connectivity
- ✅ Backend API health
- ✅ Frontend accessibility
- ✅ Database connection
- ✅ System resources (CPU, memory, disk)

### Database Test Script

```bash
cd /opt/mbse-neo4j-graph-rep

# Test Neo4j connectivity
bash deployment/diagnostics/test_database.sh
```

**What it tests:**
- ✅ Python Neo4j driver connectivity
- ✅ Database statistics (nodes, relationships)
- ✅ Query performance benchmarks
- ✅ Index verification

### Common Issues & Solutions

#### Issue 1: Services Won't Start

**Symptoms**: `systemctl start` fails

**Solutions**:
```bash
# Check logs for errors
sudo journalctl -u mbse-backend -n 50
sudo tail -50 /var/log/mbse/backend-error.log

# Common fixes:
# 1. Check environment configuration
sudo nano /opt/mbse-neo4j-graph-rep/.env

# 2. Check file permissions
sudo chown -R mbse:mbse /opt/mbse-neo4j-graph-rep

# 3. Check Python dependencies
sudo -u mbse python3 -m pip install -r /opt/mbse-neo4j-graph-rep/requirements.txt

# 4. Test manual start
cd /opt/mbse-neo4j-graph-rep
sudo -u mbse python3 -m src.web.app
```

#### Issue 2: Cannot Connect to Neo4j

**Symptoms**: Health check shows database connection failed

**Solutions**:
```bash
# 1. Test connection manually
python3 << 'EOF'
from neo4j import GraphDatabase
import os
uri = "neo4j+s://your-instance.databases.neo4j.io"
user = "neo4j"
password = "your-password"
driver = GraphDatabase.driver(uri, auth=(user, password))
driver.verify_connectivity()
print("Connection successful!")
driver.close()
EOF

# 2. Check firewall allows outbound HTTPS (port 443)
curl -v https://your-instance.databases.neo4j.io

# 3. Verify credentials in .env
grep NEO4J_ /opt/mbse-neo4j-graph-rep/.env

# 4. Check Neo4j Aura instance is running
# Login to https://console.neo4j.io
```

#### Issue 3: Frontend Shows "Cannot GET /"

**Symptoms**: Frontend returns 404 or blank page

**Solutions**:
```bash
# 1. Check if frontend is running
curl http://localhost:3001

# 2. Rebuild frontend
cd /opt/mbse-neo4j-graph-rep
sudo -u mbse npm run build

# 3. Check frontend logs
tail -50 /var/log/mbse/frontend.log

# 4. Restart frontend service
sudo systemctl restart mbse-frontend
```

#### Issue 4: High Memory Usage

**Symptoms**: Server becomes slow or unresponsive

**Solutions**:
```bash
# 1. Check memory usage
free -h
ps aux --sort=-%mem | head -10

# 2. Restart services to clear memory
sudo systemctl restart mbse-backend mbse-frontend

# 3. Consider upgrading VM size
# or
# 4. Add swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

#### Issue 5: Slow Performance

**Symptoms**: API responses take >5 seconds

**Solutions**:
```bash
# 1. Check Neo4j query performance
bash deployment/diagnostics/test_database.sh

# 2. Clear application cache
# (Backend automatically caches for 5 minutes)

# 3. Check Neo4j indexes
python3 << 'EOF'
from neo4j import GraphDatabase
driver = GraphDatabase.driver("neo4j+s://...", auth=("user", "pass"))
with driver.session() as session:
    result = session.run("SHOW INDEXES")
    for record in result:
        print(record)
driver.close()
EOF

# 4. Monitor system resources
top
htop  # if installed
```

---

## Production Deployment

### Reverse Proxy with Nginx

Install and configure Nginx as reverse proxy:

```bash
# Install Nginx
sudo apt-get install -y nginx

# Create configuration
sudo tee /etc/nginx/sites-available/mbse > /dev/null << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        proxy_pass http://localhost:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /socket.io {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/mbse /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Configure firewall
sudo ufw allow 'Nginx Full'
```

### SSL/TLS with Let's Encrypt

```bash
# Install Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal (already configured by certbot)
sudo certbot renew --dry-run
```

### Monitoring Setup

```bash
# Install monitoring tools
sudo apt-get install -y prometheus-node-exporter

# Configure systemd metrics collection
# Backend already exposes /metrics endpoint

# Access metrics
curl http://localhost:5000/metrics
```

### Backup Strategy

```bash
# Create backup script
sudo tee /opt/mbse-backup.sh > /dev/null << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup/mbse"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup application
tar -czf $BACKUP_DIR/app_$DATE.tar.gz /opt/mbse-neo4j-graph-rep

# Backup environment
cp /opt/mbse-neo4j-graph-rep/.env $BACKUP_DIR/env_$DATE

# Keep only last 7 days
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x /opt/mbse-backup.sh

# Schedule daily backup
sudo crontab -e
# Add: 0 2 * * * /opt/mbse-backup.sh
```

---

## Maintenance

### Update Application

```bash
# Stop services
sudo systemctl stop mbse-frontend mbse-backend

# Backup current version
sudo cp -r /opt/mbse-neo4j-graph-rep /opt/mbse-neo4j-graph-rep.backup

# Pull updates
cd /opt/mbse-neo4j-graph-rep
sudo -u mbse git pull

# Update dependencies
sudo -u mbse python3 -m pip install -r requirements.txt
sudo -u mbse npm install

# Rebuild frontend
sudo -u mbse npm run build

# Restart services
sudo systemctl start mbse-backend mbse-frontend

# Verify
bash deployment/diagnostics/health_check.sh
```

### Clean Temporary Files

```bash
cd /opt/mbse-neo4j-graph-rep
bash deployment/scripts/cleanup.sh
```

### Log Rotation

```bash
# Create logrotate configuration
sudo tee /etc/logrotate.d/mbse > /dev/null << 'EOF'
/var/log/mbse/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 mbse mbse
    sharedscripts
    postrotate
        systemctl reload mbse-backend mbse-frontend > /dev/null 2>&1 || true
    endscript
}
EOF
```

---

## Security

### Hardening Checklist

- ✅ Change default ports (5000, 3001)
- ✅ Use strong Neo4j password
- ✅ Enable firewall (ufw/firewalld)
- ✅ Restrict SSH access (key-based only)
- ✅ Keep system updated (`apt-get update && apt-get upgrade`)
- ✅ Enable SSL/TLS with Let's Encrypt
- ✅ Configure OAuth for authentication
- ✅ Regular backups
- ✅ Monitor logs for suspicious activity

### Security Commands

```bash
# Disable password authentication for SSH
sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart sshd

# Enable automatic security updates
sudo apt-get install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# Install fail2ban
sudo apt-get install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

## Support

### Getting Help

1. **Check Documentation**:
   - `/opt/mbse-neo4j-graph-rep/README.md`
   - `/opt/mbse-neo4j-graph-rep/END_USER_GUIDE.md`
   - `/opt/mbse-neo4j-graph-rep/DOMAIN_FUNCTIONAL_DOCUMENT.md`

2. **Run Diagnostics**:
   ```bash
   bash deployment/diagnostics/health_check.sh
   bash deployment/diagnostics/test_database.sh
   ```

3. **Check Logs**:
   ```bash
   tail -100 /var/log/mbse/backend.log
   tail -100 /var/log/mbse/frontend.log
   ```

4. **Test Manually**:
   ```bash
   curl http://localhost:5000/api/health
   curl http://localhost:3001
   ```

### Contact Information

- **GitHub Issues**: https://github.com/dparitosh/mbse-neo4j-graph-rep/issues
- **Email**: Support team email
- **Documentation**: Project README and guides

---

**Deployment Guide Version**: 1.0  
**Last Updated**: December 9, 2025  
**Tested On**: Ubuntu 22.04 LTS, AWS EC2, Azure VMs
