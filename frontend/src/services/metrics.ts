import { apiClient } from './api';

export interface CacheMetrics {
  hit_rate: number;
  miss_rate: number;
  total_requests: number;
  hits: number;
  misses: number;
  evictions: number;
  size_mb: number;
}

export interface ApiMetrics {
  total_requests: number;
  error_count: number;
  success_rate: number;
  requests_per_second: number;
  avg_response_time_ms: number;
}

export interface DatabaseMetrics {
  connected: boolean;
  node_count?: number;
  relationship_count?: number;
  avg_query_time_ms?: number;
  active_connections?: number;
  error?: string;
}

export interface SystemMetrics {
  cpu_usage: number;
  memory: {
    total_mb: number;
    used_mb: number;
    available_mb: number;
    percent: number;
  };
  disk: {
    total_gb: number;
    used_gb: number;
    free_gb: number;
    percent: number;
  };
}

export interface MetricsSummary {
  timestamp: string;
  cache: CacheMetrics;
  api: ApiMetrics;
  database: DatabaseMetrics;
  system: SystemMetrics;
}

export interface MetricDatapoint {
  timestamp: string;
  value: number;
}

export interface MetricsHistory {
  window: string;
  metric: string;
  interval: string;
  count: number;
  datapoints: MetricDatapoint[];
}

export interface HealthCheck {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  uptime_seconds: number;
  components: {
    api: 'healthy' | 'unhealthy';
    database: 'healthy' | 'unhealthy';
    cache: 'healthy' | 'unhealthy';
  };
}

/**
 * Get aggregated metrics summary
 */
export const getMetricsSummary = async (): Promise<MetricsSummary> => {
  return apiClient.get<MetricsSummary>('/metrics/summary');
};

/**
 * Get time-series metrics history
 */
export const getMetricsHistory = async (
  metric: 'cpu' | 'memory' | 'api_requests' | 'cache_hit_rate',
  window: '1h' | '6h' | '24h' | '7d' | '30d' = '1h'
): Promise<MetricsHistory> => {
  return apiClient.get<MetricsHistory>('/metrics/history', {
    params: { metric, window },
  });
};

/**
 * Get system health status
 */
export const getHealthCheck = async (): Promise<HealthCheck> => {
  return apiClient.get<HealthCheck>('/metrics/health');
};
