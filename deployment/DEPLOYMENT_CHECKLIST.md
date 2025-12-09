# 🚀 MBSE Knowledge Graph - Quick Deployment Checklist

## Pre-Deployment Checklist

### 1. Cloud VM Preparation
- [ ] VM provisioned (Ubuntu 22.04 LTS, 4 CPU, 8 GB RAM, 50 GB SSD)
- [ ] SSH access configured
- [ ] Security group/firewall rules created (ports: 22, 5000, 3001)
- [ ] VM has internet access

### 2. Neo4j Database
- [ ] Neo4j Aura account created (https://neo4j.com/cloud/aura/)
- [ ] Database instance created and running
- [ ] Connection URI noted (e.g., neo4j+s://xxxxx.databases.neo4j.io)
- [ ] Password saved securely
- [ ] Connection tested from local machine

### 3. Domain & DNS (Optional)
- [ ] Domain name registered
- [ ] DNS A record pointing to VM IP
- [ ] SSL certificate planned (Let's Encrypt)

---

## Deployment Steps (30 minutes)

### Step 1: Connect to VM (2 minutes)
```bash
# SSH into your cloud VM
ssh user@your-vm-ip

# Update system
sudo apt-get update && sudo apt-get upgrade -y
```
- [ ] Connected to VM successfully
- [ ] System updated

### Step 2: Clone Repository (2 minutes)
```bash
# Clone repository
cd /tmp
git clone https://github.com/dparitosh/mbse-neo4j-graph-rep.git
cd mbse-neo4j-graph-rep

# Make scripts executable
chmod +x deployment/scripts/*.sh
chmod +x deployment/diagnostics/*.sh
```
- [ ] Repository cloned
- [ ] Scripts made executable

### Step 3: Run Installation (10 minutes)
```bash
# Run automated installer
sudo bash deployment/scripts/install.sh
```

**What to expect:**
- Python 3.12 installation
- Node.js 20 installation
- Application files copied to `/opt/mbse-neo4j-graph-rep`
- Dependencies installed
- Frontend built
- Systemd services created

- [ ] Installation completed without errors
- [ ] No red ERROR messages in output

### Step 4: Configure Environment (5 minutes)
```bash
# Edit configuration
sudo nano /opt/mbse-neo4j-graph-rep/.env
```

**Required changes:**
```bash
NEO4J_URI=neo4j+s://YOUR-INSTANCE.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=YOUR-PASSWORD

# Optional: Change these if needed
FLASK_PORT=5000
VITE_PORT=3001
```

**Save:** Ctrl+X, Y, Enter

- [ ] NEO4J_URI configured
- [ ] NEO4J_PASSWORD set
- [ ] Configuration saved

### Step 5: Run Diagnostics (3 minutes)
```bash
cd /opt/mbse-neo4j-graph-rep

# Test configuration
bash deployment/diagnostics/health_check.sh
```

**Expected results:**
- ✓ Python version check PASSED
- ✓ Node.js version check PASSED
- ✓ All files present
- ✓ Dependencies installed
- ⚠ Services not running (expected before start)

- [ ] Health check mostly passed
- [ ] No critical failures
- [ ] Database test passed

### Step 6: Start Services (2 minutes)
```bash
# Start backend and frontend
sudo systemctl start mbse-backend
sudo systemctl start mbse-frontend

# Wait 10 seconds for startup
sleep 10

# Check status
sudo systemctl status mbse-backend
sudo systemctl status mbse-frontend
```

**Expected output:**
- Active: active (running)
- No error messages

- [ ] Backend service started
- [ ] Frontend service started
- [ ] Both services showing "active (running)"

### Step 7: Verify Application (3 minutes)
```bash
# Test backend health
curl http://localhost:5000/api/health | jq .

# Expected output:
# {
#   "status": "healthy",
#   "database": {
#     "connected": true,
#     "node_count": 3257
#   }
# }
```

**Browser test:**
1. Open: `http://your-vm-ip:3001`
2. Should see MBSE Knowledge Graph UI
3. Click "Dashboard" - should load

- [ ] Backend health check returned "healthy"
- [ ] Database connected
- [ ] Frontend accessible in browser
- [ ] Dashboard loads data

### Step 8: Configure Auto-Start (1 minute)
```bash
# Enable services on boot
sudo systemctl enable mbse-backend
sudo systemctl enable mbse-frontend

# Verify
systemctl is-enabled mbse-backend
systemctl is-enabled mbse-frontend
# Should output: enabled
```

- [ ] Services enabled for auto-start
- [ ] Verification shows "enabled"

---

## Post-Deployment Verification

### Functional Tests

#### Test 1: Backend API
```bash
# Health check
curl http://your-vm-ip:5000/api/health

# Statistics
curl http://your-vm-ip:5000/api/stats | jq .
```
- [ ] Health endpoint returns 200 OK
- [ ] Stats endpoint shows node counts

#### Test 2: Frontend UI
- [ ] Navigate to `http://your-vm-ip:3001`
- [ ] Dashboard loads with statistics
- [ ] Advanced Search works
- [ ] Query Editor executes queries

#### Test 3: Database Connection
```bash
cd /opt/mbse-neo4j-graph-rep
bash deployment/diagnostics/test_database.sh
```
- [ ] Python driver connects
- [ ] Statistics retrieved
- [ ] Query performance acceptable (<1000ms)

### Performance Tests

#### Test 1: Response Time
```bash
# Test backend response time
time curl -s http://localhost:5000/api/health > /dev/null
# Should be < 1 second
```
- [ ] Response time under 1 second

#### Test 2: Concurrent Requests
```bash
# Test 10 concurrent requests
for i in {1..10}; do
    curl -s http://localhost:5000/api/health &
done
wait
```
- [ ] All requests succeed
- [ ] No timeout errors

#### Test 3: System Resources
```bash
# Check memory and CPU
free -h
top -bn1 | head -20
```
- [ ] Memory usage < 80%
- [ ] CPU load acceptable

---

## Optional: Production Hardening

### 1. Reverse Proxy (Nginx)
```bash
# Install Nginx
sudo apt-get install -y nginx

# Configure (see deployment/README.md for full config)
sudo nano /etc/nginx/sites-available/mbse

# Enable and restart
sudo ln -s /etc/nginx/sites-available/mbse /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```
- [ ] Nginx installed
- [ ] Configuration created
- [ ] Nginx test passed
- [ ] Nginx restarted

### 2. SSL/TLS Certificate
```bash
# Install Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Obtain certificate (replace your-domain.com)
sudo certbot --nginx -d your-domain.com

# Verify auto-renewal
sudo certbot renew --dry-run
```
- [ ] Certbot installed
- [ ] Certificate obtained
- [ ] Auto-renewal working
- [ ] HTTPS accessible

### 3. Firewall Configuration
```bash
# Enable ufw
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# If not using Nginx, also allow:
# sudo ufw allow 5000/tcp
# sudo ufw allow 3001/tcp

# Check status
sudo ufw status
```
- [ ] Firewall enabled
- [ ] Required ports open
- [ ] Unnecessary ports closed

### 4. Automated Backups
```bash
# Create backup script
sudo tee /opt/mbse-backup.sh > /dev/null << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup/mbse"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/app_$DATE.tar.gz /opt/mbse-neo4j-graph-rep
find $BACKUP_DIR -type f -mtime +7 -delete
EOF

sudo chmod +x /opt/mbse-backup.sh

# Schedule daily backup (2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/mbse-backup.sh") | crontab -
```
- [ ] Backup script created
- [ ] Cron job scheduled
- [ ] Test backup runs successfully

### 5. Monitoring Setup
```bash
# Enable backend metrics
curl http://localhost:5000/metrics

# Install Node Exporter (optional)
sudo apt-get install -y prometheus-node-exporter
```
- [ ] Metrics endpoint accessible
- [ ] Node exporter running (if installed)

---

## Troubleshooting Guide

### Issue: Installation Script Fails

**Check:**
```bash
# Verify internet connectivity
ping -c 3 google.com

# Check disk space
df -h

# Check sudo permissions
sudo whoami  # Should output: root
```

**Fix:**
- Ensure VM has internet access
- Free up disk space if needed
- Run with sudo

### Issue: Services Won't Start

**Check:**
```bash
# View detailed errors
sudo journalctl -u mbse-backend -n 50
sudo tail -50 /var/log/mbse/backend-error.log

# Verify configuration
cat /opt/mbse-neo4j-graph-rep/.env
```

**Fix:**
- Check .env file for typos
- Verify Neo4j credentials
- Check file permissions

### Issue: Cannot Access from Browser

**Check:**
```bash
# Verify services are listening
sudo ss -tlnp | grep -E '5000|3001'

# Test locally
curl http://localhost:3001
curl http://localhost:5000/api/health

# Check firewall
sudo ufw status
```

**Fix:**
- Verify cloud security group allows ports
- Check firewall rules
- Test from VM first, then externally

### Issue: Database Connection Failed

**Check:**
```bash
# Test Neo4j connectivity
python3 << 'EOF'
from neo4j import GraphDatabase
uri = "neo4j+s://your-instance.databases.neo4j.io"
driver = GraphDatabase.driver(uri, auth=("neo4j", "password"))
driver.verify_connectivity()
print("Connected!")
driver.close()
EOF
```

**Fix:**
- Verify Neo4j instance is running
- Check credentials in .env
- Ensure outbound HTTPS (443) allowed

---

## Maintenance Schedule

### Daily
- [ ] Check service status: `systemctl status mbse-backend mbse-frontend`
- [ ] Monitor logs for errors: `tail -f /var/log/mbse/backend.log`

### Weekly
- [ ] Run health check: `bash deployment/diagnostics/health_check.sh`
- [ ] Review system resources: `free -h && df -h`
- [ ] Check backup logs

### Monthly
- [ ] Update system: `sudo apt-get update && sudo apt-get upgrade`
- [ ] Review and rotate logs
- [ ] Test backup restoration

### Quarterly
- [ ] Security audit
- [ ] Performance review
- [ ] Capacity planning

---

## Quick Reference Commands

```bash
# Start services
sudo systemctl start mbse-backend mbse-frontend

# Stop services
sudo systemctl stop mbse-backend mbse-frontend

# Restart services
sudo systemctl restart mbse-backend mbse-frontend

# Check status
sudo systemctl status mbse-backend mbse-frontend

# View logs
sudo journalctl -u mbse-backend -f
tail -f /var/log/mbse/backend.log

# Run health check
cd /opt/mbse-neo4j-graph-rep
bash deployment/diagnostics/health_check.sh

# Test database
bash deployment/diagnostics/test_database.sh

# Clean temporary files
bash deployment/scripts/cleanup.sh
```

---

## Success Criteria

Deployment is successful when:

✅ **Installation**
- [ ] All scripts executed without errors
- [ ] No missing dependencies

✅ **Configuration**
- [ ] .env file properly configured
- [ ] Neo4j connection successful

✅ **Services**
- [ ] Backend service running and healthy
- [ ] Frontend service accessible
- [ ] Auto-start enabled

✅ **Functionality**
- [ ] Dashboard loads with data
- [ ] Search functionality works
- [ ] API endpoints respond correctly

✅ **Performance**
- [ ] API response time < 1 second
- [ ] Frontend loads in < 3 seconds
- [ ] System resources < 80%

✅ **Security**
- [ ] Firewall configured
- [ ] Strong passwords set
- [ ] Non-default ports (optional)

---

## Support Resources

- **Deployment Guide**: `/opt/mbse-neo4j-graph-rep/deployment/README.md`
- **User Guide**: `/opt/mbse-neo4j-graph-rep/END_USER_GUIDE.md`
- **Health Check**: `bash deployment/diagnostics/health_check.sh`
- **GitHub Issues**: https://github.com/dparitosh/mbse-neo4j-graph-rep/issues

---

**Checklist Version**: 1.0  
**Last Updated**: December 9, 2025  
**Estimated Deployment Time**: 30-45 minutes
