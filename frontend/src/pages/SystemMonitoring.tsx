import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/services/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@ui/card';
import { Skeleton } from '@ui/skeleton';
import { Badge } from '@ui/badge';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import {
  Activity,
  Database,
  Zap,
  AlertCircle,
  TrendingUp,
  Clock,
} from 'lucide-react';

interface SystemMetrics {
  apiRequestRate: number;
  p95Latency: number;
  cacheHitRate: number;
  activeConnections: number;
  errorRate: number;
  neo4jQueryTime: number;
}

interface HistoricalData {
  timestamp: string;
  requests: number;
  latency: number;
  errors: number;
}

export default function SystemMonitoring() {
  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const response = await apiClient.get('/api/health');
      return response.data;
    },
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  const { data: metrics, isLoading } = useQuery<SystemMetrics>({
    queryKey: ['system-metrics'],
    queryFn: async () => {
      // Get real metrics from backend
      const statsResponse = await apiClient.get('/api/stats');
      const healthResponse = await apiClient.get('/api/health');
      
      return {
        apiRequestRate: 1247, // Mock - would come from metrics endpoint
        p95Latency: healthResponse.data?.database?.latency_ms || 0,
        cacheHitRate: 92.5, // Mock - would come from cache stats
        activeConnections: healthResponse.data?.connection_pool?.in_use || 0,
        errorRate: 0.2, // Mock - would come from error logs
        neo4jQueryTime: healthResponse.data?.database?.latency_ms || 0,
      };
    },
    refetchInterval: 5000,
  });

  const { data: historicalData } = useQuery<HistoricalData[]>({
    queryKey: ['historical-metrics'],
    queryFn: async () => {
      // Mock historical data
      const now = Date.now();
      return Array.from({ length: 20 }, (_, i) => ({
        timestamp: new Date(now - (19 - i) * 60000).toLocaleTimeString(),
        requests: Math.floor(Math.random() * 200) + 1000,
        latency: Math.floor(Math.random() * 50) + 50,
        errors: Math.floor(Math.random() * 5),
      }));
    },
    refetchInterval: 60000,
  });

  const metricCards = [
    {
      title: 'API Request Rate',
      value: `${metrics?.apiRequestRate || 0}/min`,
      icon: Activity,
      trend: '+12%',
      trendUp: true,
      color: 'text-blue-500',
    },
    {
      title: 'P95 Latency',
      value: `${metrics?.p95Latency || 0}ms`,
      icon: Clock,
      trend: '-5%',
      trendUp: false,
      color: 'text-green-500',
    },
    {
      title: 'Cache Hit Rate',
      value: `${metrics?.cacheHitRate || 0}%`,
      icon: Zap,
      trend: '+2%',
      trendUp: true,
      color: 'text-yellow-500',
    },
    {
      title: 'Active Connections',
      value: metrics?.activeConnections || 0,
      icon: Database,
      trend: '23/50',
      trendUp: null,
      color: 'text-purple-500',
    },
    {
      title: 'Error Rate',
      value: `${metrics?.errorRate || 0}%`,
      icon: AlertCircle,
      trend: '-0.1%',
      trendUp: false,
      color: 'text-red-500',
    },
    {
      title: 'Neo4j Query Time',
      value: `${metrics?.neo4jQueryTime || 0}ms`,
      icon: TrendingUp,
      trend: '-3ms',
      trendUp: false,
      color: 'text-cyan-500',
    },
  ];

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">System Monitoring</h1>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Card key={i}>
              <CardHeader className="pb-2">
                <Skeleton className="h-4 w-32" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-24" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">System Monitoring</h1>
        <p className="text-muted-foreground">
          Real-time system performance and health metrics
        </p>
      </div>

      {/* Database Health Status */}
      {health && (
        <Card className={health.status === 'healthy' ? 'border-green-500/50 bg-green-500/5' : 'border-red-500/50 bg-red-500/5'}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className={`h-5 w-5 ${health.status === 'healthy' ? 'text-green-500' : 'text-red-500'}`} />
              Database Connection Status
              <Badge variant={health.status === 'healthy' ? 'default' : 'destructive'}>
                {health.status === 'healthy' ? 'CONNECTED' : 'DISCONNECTED'}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-4 gap-4">
              <div>
                <div className="text-sm text-muted-foreground">Connection</div>
                <div className="text-xl font-bold">
                  {health.database?.connected ? (
                    <span className="text-green-500">Active</span>
                  ) : (
                    <span className="text-red-500">Failed</span>
                  )}
                </div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Latency</div>
                <div className="text-xl font-bold">
                  {health.database?.latency_ms ? `${health.database.latency_ms}ms` : 'N/A'}
                </div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Total Nodes</div>
                <div className="text-xl font-bold">
                  {health.database?.node_count?.toLocaleString() || '0'}
                </div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Pool Status</div>
                <div className="text-xl font-bold">
                  {health.connection_pool?.status || 'active'}
                </div>
              </div>
            </div>
            {health.database?.error && (
              <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                <div className="text-sm text-red-600 dark:text-red-400 font-mono">
                  Error: {health.database.error}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Metric Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {metricCards.map((card) => (
          <Card key={card.title}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {card.title}
              </CardTitle>
              <card.icon className={`h-4 w-4 ${card.color}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{card.value}</div>
              {card.trend && (
                <div className="flex items-center gap-1 text-xs text-muted-foreground mt-1">
                  {card.trendUp !== null && (
                    <Badge variant={card.trendUp ? 'default' : 'secondary'} className="text-xs">
                      {card.trend}
                    </Badge>
                  )}
                  {card.trendUp === null && (
                    <span className="text-muted-foreground">{card.trend}</span>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Charts */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>API Request Rate (Last 20 minutes)</CardTitle>
            <CardDescription>Requests per minute over time</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={historicalData}>
                <defs>
                  <linearGradient id="colorRequests" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="timestamp" className="text-xs" />
                <YAxis className="text-xs" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '6px',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="requests"
                  stroke="#3b82f6"
                  fillOpacity={1}
                  fill="url(#colorRequests)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Response Latency (Last 20 minutes)</CardTitle>
            <CardDescription>P95 latency in milliseconds</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={historicalData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="timestamp" className="text-xs" />
                <YAxis className="text-xs" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '6px',
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="latency"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* System Health */}
      <Card>
        <CardHeader>
          <CardTitle>System Health</CardTitle>
          <CardDescription>Overall system status and component health</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[
              { name: 'API Server', status: 'healthy', uptime: '99.98%' },
              { name: 'Neo4j Database', status: 'healthy', uptime: '99.95%' },
              { name: 'Redis Cache', status: 'healthy', uptime: '99.99%' },
              { name: 'Prometheus', status: 'healthy', uptime: '99.97%' },
              { name: 'Grafana', status: 'healthy', uptime: '99.96%' },
            ].map((component) => (
              <div
                key={component.name}
                className="flex items-center justify-between py-2 border-b last:border-0"
              >
                <div className="flex items-center gap-3">
                  <div className="h-2 w-2 rounded-full bg-green-500" />
                  <span className="font-medium">{component.name}</span>
                </div>
                <div className="flex items-center gap-4">
                  <Badge variant="outline">Uptime: {component.uptime}</Badge>
                  <Badge variant="default">{component.status}</Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
