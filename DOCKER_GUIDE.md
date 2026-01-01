# Phase 2 Docker Deployment Guide

## 🐳 Docker Setup

### Prerequisites
```bash
# Install Docker (includes the `docker compose` subcommand)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

### Build and Run

#### Development Mode
```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

#### Production Mode
```bash
# Build containers
docker compose -f docker-compose.prod.yml build

# Start services
docker compose -f docker-compose.prod.yml up -d

# Monitor
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend

# Stop
docker compose -f docker-compose.prod.yml down
```

### Individual Container Management

#### Backend
```bash
# Build
docker build -t mbse-backend:latest .

# Run standalone
docker run -d \
  --name mbse-backend \
  -p 5000:5000 \
  -e NEO4J_URI=bolt://host.docker.internal:7687 \
  -e NEO4J_USER=neo4j \
  -e NEO4J_PASSWORD=your-password \
  mbse-backend:latest

# Check logs
docker logs -f mbse-backend

# Shell access
docker exec -it mbse-backend /bin/bash
```

#### Frontend
```bash
# Build
docker build -f Dockerfile.frontend -t mbse-frontend:latest .

# Run standalone
docker run -d \
  --name mbse-frontend \
  -p 3001:3001 \
  mbse-frontend:latest

# Check logs
docker logs -f mbse-frontend
```

### Health Checks
```bash
# Check backend health
curl http://localhost:5000/api/health

# Check frontend health
curl http://localhost:3001/health

# Check Neo4j
curl http://localhost:7474
```

### Data Persistence
```bash
# Backup Neo4j data
docker exec mbse-neo4j neo4j-admin dump --to=/data/backup-$(date +%Y%m%d).dump

# Copy backup out
docker cp mbse-neo4j:/data/backup-$(date +%Y%m%d).dump ./backups/

# Restore from backup
docker exec mbse-neo4j neo4j-admin load --from=/data/backup.dump --force
```

### Troubleshooting

#### Container won't start
```bash
# Check logs
docker logs mbse-backend

# Inspect container
docker inspect mbse-backend

# Check resources
docker stats
```

#### Network issues
```bash
# List networks
docker network ls

# Inspect network
docker network inspect mbse-network

# Test connectivity
docker exec mbse-backend ping neo4j
```

#### Permission issues
```bash
# Fix ownership
sudo chown -R 1000:1000 ./data ./logs

# Check user
docker exec mbse-backend whoami
```

## 🚀 Kubernetes Deployment (Optional)

See `kubernetes/` directory for:
- Deployments
- Services  
- Ingress
- ConfigMaps
- Secrets

```bash
# Apply manifests
kubectl apply -f kubernetes/

# Check status
kubectl get pods -n mbse
kubectl get services -n mbse

# View logs
kubectl logs -f deployment/mbse-backend -n mbse
```

## 📊 Monitoring

### Prometheus Metrics
Available at: http://localhost:5000/metrics

### Grafana Dashboard
Import dashboard from `monitoring/grafana-dashboard.json`

### Health Endpoints
- Backend: http://localhost:5000/api/health
- Frontend: http://localhost:3001/health
- Neo4j: http://localhost:7474

## 🔐 Security

### Production Checklist
- [ ] Change default Neo4j password
- [ ] Use secrets management (not env files)
- [ ] Enable HTTPS/TLS
- [ ] Configure firewall rules
- [ ] Set up log aggregation
- [ ] Enable authentication on all services
- [ ] Regular security updates

### Environment Variables
```bash
# Required
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<strong-password>

# Optional
FLASK_ENV=production
LOG_LEVEL=INFO
JWT_SECRET_KEY=<random-secret>
OPENAI_API_KEY=<your-key>
```

## 📦 CI/CD Integration

### GitHub Actions Example
```yaml
name: Build and Deploy

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker images
        run: |
          docker build -t mbse-backend:${{ github.sha }} .
          docker build -f Dockerfile.frontend -t mbse-frontend:${{ github.sha }} .
      
      - name: Push to registry
        run: |
          docker push mbse-backend:${{ github.sha }}
          docker push mbse-frontend:${{ github.sha }}
      
      - name: Deploy to production
        run: |
          kubectl set image deployment/mbse-backend mbse-backend=mbse-backend:${{ github.sha }}
```

---

**Last Updated**: December 8, 2025
