# 🚀 Cloud VM Deployment Package

## Overview

This deployment package provides everything needed to deploy the MBSE Knowledge Graph application on a cloud VM instance with minimal manual intervention.

## 📦 Package Contents

### 1. Installation Scripts (`scripts/`)
- **`install.sh`**: Fully automated installation script
  - Installs Python 3.12, Node.js 20
  - Copies application files
  - Installs all dependencies
  - Builds frontend
  - Creates systemd services
  - Configures firewall
  
- **`cleanup.sh`**: Remove temporary files and caches
  - Cleans Python cache
  - Removes test artifacts
  - Clears log files
  - Removes old backups

- **`service_manager.sh`**: Service management utility
  - Start/stop/restart services
  - Check service status
  - View logs
  - Manage backend/frontend separately

### 2. Diagnostic Tools (`diagnostics/`)
- **`health_check.sh`**: Comprehensive system validation
  - System prerequisites
  - Application files
  - Dependencies
  - Environment configuration
  - Network connectivity
  - API health
  - System resources
  
- **`test_database.sh`**: Neo4j database diagnostics
  - Connection testing
  - Performance benchmarks
  - Statistics retrieval
  - Index verification

### 3. Documentation
- **`README.md`**: Complete deployment guide
  - Prerequisites
  - Installation steps
  - Configuration
  - Service management
  - Troubleshooting
  - Production hardening
  
- **`DEPLOYMENT_CHECKLIST.md`**: Step-by-step checklist
  - Pre-deployment tasks
  - Installation walkthrough
  - Verification steps
  - Post-deployment tasks

## 🚀 Quick Start (5 minutes)

```bash
# 1. Clone repository
git clone https://github.com/dparitosh/mbse-neo4j-graph-rep.git
cd mbse-neo4j-graph-rep

# 2. Make scripts executable
chmod +x deployment/scripts/*.sh deployment/diagnostics/*.sh

# 3. Run installation
sudo bash deployment/scripts/install.sh

# 4. Configure environment
sudo nano /opt/mbse-neo4j-graph-rep/.env
# Update: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

# 5. Start services
sudo systemctl start mbse-backend mbse-frontend

# 6. Verify
bash /opt/mbse-neo4j-graph-rep/deployment/diagnostics/health_check.sh
```

## 📊 Deployment Architecture

```
Cloud VM (Ubuntu 22.04)
├── Backend Service (Port 5000)
│   ├── Flask Application
│   ├── REST APIs (50+ endpoints)
│   ├── WebSocket Support
│   └── Neo4j Connection
│
├── Frontend Service (Port 3001)
│   ├── React + TypeScript
│   ├── Vite Production Build
│   └── Radix UI Components
│
└── System Services
    ├── systemd (mbse-backend.service)
    ├── systemd (mbse-frontend.service)
    └── Logs (/var/log/mbse/)

External Services
├── Neo4j Cloud (Aura)
│   └── Graph Database
└── OAuth Provider (optional)
    └── Authentication
```

## 🎯 Key Features

### Automated Installation
- ✅ Zero-configuration installation script
- ✅ Detects and installs all prerequisites
- ✅ Builds production-ready application
- ✅ Creates systemd services
- ✅ Configures firewall rules

### Comprehensive Diagnostics
- ✅ 30+ health checks
- ✅ Database connectivity tests
- ✅ Performance benchmarks
- ✅ Resource monitoring
- ✅ Detailed error reporting

### Service Management
- ✅ Systemd integration
- ✅ Auto-start on boot
- ✅ Automatic restart on failure
- ✅ Centralized logging
- ✅ Easy start/stop/restart

### Production-Ready
- ✅ Optimized for cloud VMs
- ✅ Nginx reverse proxy support
- ✅ SSL/TLS configuration
- ✅ Firewall hardening
- ✅ Automated backups

## 📋 System Requirements

### Cloud VM
- **OS**: Ubuntu 22.04 LTS (or 20.04)
- **CPU**: 4 cores recommended (2 minimum)
- **RAM**: 8 GB recommended (4 GB minimum)
- **Disk**: 50 GB SSD recommended
- **Network**: Public IP, ports 5000 and 3001 accessible

### External Services
- **Neo4j**: Aura instance or self-hosted Neo4j 4.x/5.x
- **OAuth** (optional): Azure AD, Google, Okta

## 🔧 Configuration

### Minimal Configuration (Required)

Edit `/opt/mbse-neo4j-graph-rep/.env`:

```bash
# Neo4j Connection (REQUIRED)
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-secure-password

# Application Ports (Optional - defaults shown)
FLASK_PORT=5000
VITE_PORT=3001
```

### Full Configuration (Optional)

```bash
# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here

# OAuth2 (Optional)
OAUTH_CLIENT_ID=your-client-id
OAUTH_CLIENT_SECRET=your-client-secret

# Performance
NEO4J_MAX_CONNECTIONS=50
CACHE_TTL=300

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/mbse/app.log
```

## 🧪 Testing & Validation

### Health Check
```bash
bash deployment/diagnostics/health_check.sh
```

**Tests performed:**
- System prerequisites (Python, Node.js)
- Application files and dependencies
- Environment configuration
- Network connectivity
- Backend API health
- Frontend accessibility
- Database connection
- System resources

### Database Test
```bash
bash deployment/diagnostics/test_database.sh
```

**Tests performed:**
- Neo4j driver connectivity
- Database statistics
- Query performance
- Index verification

### Manual Verification
```bash
# Backend health
curl http://localhost:5000/api/health

# Frontend access
curl http://localhost:3001

# Database stats
curl http://localhost:5000/api/stats | jq .
```

## 📝 Service Management

### Using Service Manager Script

```bash
cd /opt/mbse-neo4j-graph-rep

# Start all
bash deployment/scripts/service_manager.sh start

# Stop all
bash deployment/scripts/service_manager.sh stop

# Restart all
bash deployment/scripts/service_manager.sh restart

# Check status
bash deployment/scripts/service_manager.sh status

# View logs
bash deployment/scripts/service_manager.sh logs

# Manage individually
bash deployment/scripts/service_manager.sh backend start
bash deployment/scripts/service_manager.sh frontend restart
```

### Using systemctl (Direct)

```bash
# Start
sudo systemctl start mbse-backend mbse-frontend

# Stop
sudo systemctl stop mbse-backend mbse-frontend

# Restart
sudo systemctl restart mbse-backend

# Status
sudo systemctl status mbse-backend

# Logs
sudo journalctl -u mbse-backend -f
tail -f /var/log/mbse/backend.log
```

## 🔍 Troubleshooting

### Common Issues

#### Issue 1: Installation Fails
**Check:**
- Internet connectivity
- Disk space (df -h)
- Sudo permissions

**Fix:**
```bash
# Re-run installation
sudo bash deployment/scripts/install.sh
```

#### Issue 2: Services Won't Start
**Check logs:**
```bash
sudo journalctl -u mbse-backend -n 50
tail -50 /var/log/mbse/backend-error.log
```

**Fix:**
```bash
# Check configuration
sudo nano /opt/mbse-neo4j-graph-rep/.env

# Restart services
sudo systemctl restart mbse-backend mbse-frontend
```

#### Issue 3: Cannot Connect to Database
**Test connection:**
```bash
bash deployment/diagnostics/test_database.sh
```

**Fix:**
- Verify Neo4j instance is running
- Check credentials in .env
- Ensure firewall allows outbound HTTPS (443)

#### Issue 4: High Memory Usage
**Check resources:**
```bash
free -h
ps aux --sort=-%mem | head -10
```

**Fix:**
```bash
# Restart services
sudo systemctl restart mbse-backend mbse-frontend

# Add swap if needed
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## 🔒 Security Best Practices

### Essential
- ✅ Change default ports (optional but recommended)
- ✅ Use strong Neo4j password
- ✅ Enable firewall (ufw/firewalld)
- ✅ Disable password authentication for SSH
- ✅ Keep system updated

### Recommended
- ✅ Configure SSL/TLS with Let's Encrypt
- ✅ Set up OAuth for authentication
- ✅ Install fail2ban for brute force protection
- ✅ Configure automated backups
- ✅ Monitor logs regularly

### Commands
```bash
# Enable firewall
sudo ufw allow 22/tcp
sudo ufw allow 5000/tcp
sudo ufw allow 3001/tcp
sudo ufw enable

# Disable SSH password auth
sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart sshd

# Install fail2ban
sudo apt-get install -y fail2ban
sudo systemctl enable fail2ban
```

## 📦 File Structure

```
deployment/
├── README.md                    # Complete deployment guide
├── DEPLOYMENT_CHECKLIST.md      # Step-by-step checklist
├── INDEX.md                     # This file
├── scripts/
│   ├── install.sh              # Automated installation
│   ├── cleanup.sh              # Clean temporary files
│   └── service_manager.sh      # Service management
├── diagnostics/
│   ├── health_check.sh         # System health validation
│   └── test_database.sh        # Database diagnostics
└── config/
    └── (runtime configurations)
```

## 📚 Documentation Index

1. **[deployment/README.md](README.md)** - Complete deployment guide
   - Prerequisites
   - Installation steps
   - Configuration
   - Service management
   - Troubleshooting
   - Production hardening

2. **[deployment/DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Interactive checklist
   - Pre-deployment tasks
   - Step-by-step installation
   - Verification procedures
   - Post-deployment tasks

3. **[END_USER_GUIDE.md](../END_USER_GUIDE.md)** - End user documentation
   - Application features
   - Navigation guide
   - Feature walkthroughs

4. **[DOMAIN_FUNCTIONAL_DOCUMENT.md](../DOMAIN_FUNCTIONAL_DOCUMENT.md)** - Business case
   - Problem statement
   - Solution approach
   - Benefits realization
   - ROI analysis

5. **[README.md](../README.md)** - Main project documentation
   - Project overview
   - Features
   - API documentation

## 🎓 Learning Path

### For System Administrators
1. Read `deployment/README.md`
2. Follow `deployment/DEPLOYMENT_CHECKLIST.md`
3. Run health checks and diagnostics
4. Configure production hardening
5. Set up monitoring and backups

### For Developers
1. Read main `README.md`
2. Review API documentation
3. Study `src/web/app.py` for backend
4. Review `frontend/src/` for UI code
5. Run local development environment

### For End Users
1. Read `END_USER_GUIDE.md`
2. Access application UI
3. Follow feature walkthroughs
4. Explore dashboard and search
5. Learn query editor basics

### For Business Stakeholders
1. Read `DOMAIN_FUNCTIONAL_DOCUMENT.md`
2. Review problem statement
3. Understand solution benefits
4. Evaluate ROI analysis
5. Plan deployment strategy

## 🆘 Support

### Self-Service
1. Run health check: `bash deployment/diagnostics/health_check.sh`
2. Check logs: `tail -f /var/log/mbse/backend.log`
3. Review documentation in `deployment/README.md`
4. Search GitHub issues

### Contact
- **GitHub Issues**: https://github.com/dparitosh/mbse-neo4j-graph-rep/issues
- **Documentation**: All guides in repository
- **Email**: Support team contact

## 📈 Metrics & Monitoring

### Health Endpoints
```bash
# Backend health
curl http://localhost:5000/api/health

# Prometheus metrics
curl http://localhost:5000/metrics

# Database statistics
curl http://localhost:5000/api/stats
```

### System Monitoring
```bash
# Service status
systemctl status mbse-backend mbse-frontend

# Resource usage
free -h
df -h
top -bn1 | head -20

# Network connections
ss -tlnp | grep -E '5000|3001'
```

## 🔄 Update Procedure

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

## ✅ Success Criteria

Deployment is successful when:

1. **Installation**: All scripts complete without errors
2. **Configuration**: .env properly configured, Neo4j connected
3. **Services**: Backend and frontend running, auto-start enabled
4. **Functionality**: Dashboard loads, search works, APIs respond
5. **Performance**: Response time < 1s, system resources < 80%
6. **Security**: Firewall configured, strong passwords set

## 📅 Maintenance Schedule

- **Daily**: Monitor logs, check service status
- **Weekly**: Run health checks, review resources
- **Monthly**: System updates, log rotation, backup verification
- **Quarterly**: Security audit, performance review, capacity planning

---

**Package Version**: 1.0  
**Last Updated**: December 9, 2025  
**Tested On**: Ubuntu 22.04 LTS, AWS EC2, Azure VMs, GCP Compute Engine
