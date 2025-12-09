# Grafana Dashboard Configuration for MBSE Knowledge Graph

## Overview
This guide configures Grafana dashboards for monitoring the MBSE Neo4j Knowledge Graph system.

## Prerequisites
- Prometheus running and scraping `/metrics` endpoint
- Grafana 10.0+ installed
- MBSE backend exposing Prometheus metrics

## Quick Setup

### 1. Install Grafana (Docker)
```bash
# Run Grafana container
docker run -d \
  --name grafana \
  -p 3000:3000 \
  -e GF_SECURITY_ADMIN_PASSWORD=admin \
  -e GF_INSTALL_PLUGINS=grafana-clock-panel \
  grafana/grafana:latest

# Access Grafana at http://localhost:3000
# Default credentials: admin/admin
```

### 2. Add Prometheus Data Source
1. Navigate to **Configuration** → **Data Sources**
2. Click **Add data source**
3. Select **Prometheus**
4. Configure:
   - **Name:** Prometheus
   - **URL:** http://prometheus:9090 (or http://localhost:9090)
   - **Access:** Server (default)
5. Click **Save & Test**

### 3. Import Dashboard

#### Option A: JSON Dashboard (Automated)
```bash
# Import pre-built dashboard
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d @grafana-dashboard.json
```

#### Option B: Manual Creation
See dashboard configuration below.

---

## Dashboard Panels

### Panel 1: API Request Rate
**Type:** Graph  
**Query:**
```promql
rate(mbse_http_requests_total[5m])
```
**Legend:** `{{method}} {{endpoint}} ({{status}})`

**Settings:**
- Title: API Request Rate
- Y-Axis: requests/sec
- Visualization: Time series
- Legend: Bottom

---

### Panel 2: API Response Time (p95)
**Type:** Graph  
**Query:**
```promql
histogram_quantile(0.95, 
  rate(mbse_http_request_duration_seconds_bucket[5m])
)
```
**Legend:** `{{method}} {{endpoint}}`

**Settings:**
- Title: API Response Time (95th percentile)
- Y-Axis: seconds
- Thresholds: 
  - Green: < 0.2s
  - Yellow: 0.2s - 0.5s
  - Red: > 0.5s

---

### Panel 3: Neo4j Query Performance
**Type:** Graph  
**Queries:**
```promql
# Query rate
rate(mbse_neo4j_queries_total{status="success"}[5m])

# Query duration
rate(mbse_neo4j_query_duration_seconds_sum[5m]) / 
rate(mbse_neo4j_query_duration_seconds_count[5m])
```

**Settings:**
- Title: Neo4j Query Performance
- Y-Axis (left): queries/sec
- Y-Axis (right): avg duration (s)
- Legend: Bottom

---

### Panel 4: Cache Hit Rate
**Type:** Gauge  
**Query:**
```promql
(
  rate(mbse_cache_hits_total[5m]) / 
  (rate(mbse_cache_hits_total[5m]) + rate(mbse_cache_misses_total[5m]))
) * 100
```

**Settings:**
- Title: Cache Hit Rate
- Unit: Percent (0-100)
- Thresholds:
  - Red: < 70%
  - Yellow: 70% - 85%
  - Green: > 85%

---

### Panel 5: Active Connections
**Type:** Gauge  
**Query:**
```promql
mbse_active_connections
```

**Settings:**
- Title: Active Database Connections
- Max: 50 (pool size)
- Thresholds:
  - Green: < 40
  - Yellow: 40 - 45
  - Red: > 45

---

### Panel 6: Error Rate
**Type:** Graph  
**Query:**
```promql
rate(mbse_http_requests_total{status=~"5.."}[5m])
```

**Settings:**
- Title: API Error Rate (5xx)
- Y-Axis: errors/sec
- Alert threshold: > 5 errors/min

---

### Panel 7: PLM Sync Operations
**Type:** Graph  
**Queries:**
```promql
# Successful syncs
rate(mbse_plm_sync_total{status="success"}[5m])

# Failed syncs
rate(mbse_plm_sync_total{status="error"}[5m])
```

**Settings:**
- Title: PLM Synchronization
- Legend: `{{plm_system}} - {{direction}} ({{status}})`

---

### Panel 8: Agent Query Performance
**Type:** Graph  
**Queries:**
```promql
# Agent query rate
rate(mbse_agent_queries_total[5m])

# Agent query duration (avg)
rate(mbse_agent_query_duration_seconds_sum[5m]) / 
rate(mbse_agent_query_duration_seconds_count[5m])
```

**Settings:**
- Title: AI Agent Performance
- Y-Axis (left): queries/sec
- Y-Axis (right): avg duration (s)

---

### Panel 9: System Health
**Type:** Stat  
**Queries:**
```promql
# API health
up{job="mbse-api"}

# Database health
mbse_neo4j_queries_total > 0
```

**Settings:**
- Title: System Health
- Value mappings:
  - 1: ✅ Healthy (green)
  - 0: ❌ Down (red)

---

### Panel 10: Request Distribution
**Type:** Pie Chart  
**Query:**
```promql
sum by (endpoint) (
  rate(mbse_http_requests_total[5m])
)
```

**Settings:**
- Title: Request Distribution by Endpoint
- Legend: Values + Percent

---

## Alert Rules

### 1. High API Latency
```yaml
alert: HighAPILatency
expr: |
  histogram_quantile(0.95, 
    rate(mbse_http_request_duration_seconds_bucket[5m])
  ) > 0.5
for: 5m
labels:
  severity: warning
annotations:
  summary: "API latency high (> 500ms p95)"
  description: "95th percentile latency is {{ $value }}s"
```

### 2. High Error Rate
```yaml
alert: HighErrorRate
expr: |
  rate(mbse_http_requests_total{status=~"5.."}[5m]) > 0.1
for: 2m
labels:
  severity: critical
annotations:
  summary: "High API error rate"
  description: "Error rate is {{ $value }} errors/sec"
```

### 3. Low Cache Hit Rate
```yaml
alert: LowCacheHitRate
expr: |
  (
    rate(mbse_cache_hits_total[10m]) / 
    (rate(mbse_cache_hits_total[10m]) + rate(mbse_cache_misses_total[10m]))
  ) < 0.7
for: 10m
labels:
  severity: warning
annotations:
  summary: "Cache hit rate below 70%"
  description: "Current hit rate: {{ $value | humanizePercentage }}"
```

### 4. Connection Pool Exhaustion
```yaml
alert: ConnectionPoolExhaustion
expr: mbse_active_connections > 45
for: 5m
labels:
  severity: critical
annotations:
  summary: "Database connection pool near capacity"
  description: "{{ $value }} connections active (max 50)"
```

### 5. PLM Sync Failures
```yaml
alert: PLMSyncFailures
expr: |
  rate(mbse_plm_sync_total{status="error"}[15m]) > 0.05
for: 5m
labels:
  severity: warning
annotations:
  summary: "PLM sync failing"
  description: "{{ $labels.plm_system }} sync errors: {{ $value }}/sec"
```

---

## Complete Dashboard JSON

Save as `grafana-dashboard.json`:

```json
{
  "dashboard": {
    "title": "MBSE Knowledge Graph - System Monitoring",
    "tags": ["mbse", "neo4j", "system"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "API Request Rate",
        "type": "graph",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
        "targets": [
          {
            "expr": "rate(mbse_http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}} ({{status}})"
          }
        ]
      },
      {
        "id": 2,
        "title": "API Response Time (p95)",
        "type": "graph",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(mbse_http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "id": 3,
        "title": "Neo4j Query Performance",
        "type": "graph",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
        "targets": [
          {
            "expr": "rate(mbse_neo4j_queries_total{status=\"success\"}[5m])",
            "legendFormat": "{{query_type}} queries/sec"
          },
          {
            "expr": "rate(mbse_neo4j_query_duration_seconds_sum[5m]) / rate(mbse_neo4j_query_duration_seconds_count[5m])",
            "legendFormat": "Avg duration",
            "yAxisIndex": 1
          }
        ]
      },
      {
        "id": 4,
        "title": "Cache Hit Rate",
        "type": "gauge",
        "gridPos": {"h": 8, "w": 6, "x": 12, "y": 8},
        "targets": [
          {
            "expr": "(rate(mbse_cache_hits_total[5m]) / (rate(mbse_cache_hits_total[5m]) + rate(mbse_cache_misses_total[5m]))) * 100"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "thresholds": {
              "steps": [
                {"value": 0, "color": "red"},
                {"value": 70, "color": "yellow"},
                {"value": 85, "color": "green"}
              ]
            }
          }
        }
      },
      {
        "id": 5,
        "title": "Active Connections",
        "type": "gauge",
        "gridPos": {"h": 8, "w": 6, "x": 18, "y": 8},
        "targets": [
          {
            "expr": "mbse_active_connections"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "max": 50,
            "thresholds": {
              "steps": [
                {"value": 0, "color": "green"},
                {"value": 40, "color": "yellow"},
                {"value": 45, "color": "red"}
              ]
            }
          }
        }
      }
    ],
    "refresh": "10s",
    "time": {
      "from": "now-1h",
      "to": "now"
    }
  }
}
```

---

## Deployment Steps

### 1. Start Prometheus
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'mbse-api'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'
```

```bash
# Run Prometheus
docker run -d \
  --name prometheus \
  -p 9090:9090 \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus:latest
```

### 2. Start Grafana
```bash
docker run -d \
  --name grafana \
  -p 3000:3000 \
  --link prometheus:prometheus \
  grafana/grafana:latest
```

### 3. Import Dashboard
1. Login to Grafana (http://localhost:3000)
2. Go to **Dashboards** → **Import**
3. Upload `grafana-dashboard.json`
4. Select Prometheus data source
5. Click **Import**

---

## Monitoring Best Practices

1. **Set up alerts:** Configure PagerDuty/Slack notifications
2. **Regular review:** Check dashboards daily
3. **Capacity planning:** Monitor trends over time
4. **SLA tracking:** Set performance targets
5. **Incident response:** Use dashboards for troubleshooting

---

## Screenshots

Expected dashboard appearance:

```
┌─────────────────────────────────────────────────────────────┐
│  MBSE Knowledge Graph - System Monitoring                  │
├───────────────────────────────┬─────────────────────────────┤
│  API Request Rate             │  API Response Time (p95)    │
│  [Line Graph]                 │  [Line Graph]               │
│                               │                             │
├───────────────────────────────┼────────────┬────────────────┤
│  Neo4j Query Performance      │ Cache Hit  │ Active Conn    │
│  [Dual-axis Graph]            │  Rate      │  Pool          │
│                               │  [Gauge]   │  [Gauge]       │
├───────────────────────────────┴────────────┴────────────────┤
│  PLM Sync Operations          │  Agent Performance          │
│  [Stacked Area]               │  [Line Graph]               │
└───────────────────────────────┴─────────────────────────────┘
```

---

## Troubleshooting

**Problem:** Grafana can't connect to Prometheus  
**Solution:** Check network connectivity, verify Prometheus URL

**Problem:** No data showing in panels  
**Solution:** Verify metrics endpoint is accessible, check Prometheus targets

**Problem:** Alert not firing  
**Solution:** Check alert rule syntax, verify alert manager configuration

---

**Last Updated:** December 9, 2025  
**Version:** 1.0  
**Maintainer:** MBSE DevOps Team
