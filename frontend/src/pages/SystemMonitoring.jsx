import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getMetricsSummary, getMetricsHistory, getHealthCheck } from '@/services/metrics';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@ui/card';
import { Skeleton } from '@ui/skeleton';
import { Badge } from '@ui/badge';
import { Button } from '@ui/button';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, Database, Zap, AlertCircle, TrendingUp, Clock, RefreshCw } from 'lucide-react';
import PageHeader from '@/components/PageHeader';

export default function SystemMonitoring() {
  const queryClient = useQueryClient();
  const {
    data: health,
    isLoading: healthLoading
  } = useQuery({
    queryKey: ['health'],
    queryFn: getHealthCheck,
    refetchInterval: 5000
  });
  const {
    data: metricsSummary,
    isLoading
  } = useQuery({
    queryKey: ['system-metrics'],
    queryFn: getMetricsSummary,
    refetchInterval: 5000
  });
  const metrics = metricsSummary ? {
    apiRequestRate: Math.round(metricsSummary.api.requests_per_second * 60),
    p95Latency: metricsSummary.api.avg_response_time_ms,
    cacheHitRate: metricsSummary.cache.hit_rate * 100,
    activeConnections: metricsSummary.database.active_connections || 0,
    errorRate: (1 - metricsSummary.api.success_rate) * 100,
    neo4jQueryTime: metricsSummary.database.avg_query_time_ms || 0
  } : undefined;
  const {
    data: historicalMetrics
  } = useQuery({
    queryKey: ['historical-metrics'],
    queryFn: () => getMetricsHistory('api_requests', '1h'),
    refetchInterval: 60000
  });
  const historicalData = historicalMetrics?.datapoints.map(dp => ({
    timestamp: new Date(dp.timestamp).toLocaleTimeString(),
    requests: dp.value,
    latency: dp.latency ?? metrics?.p95Latency ?? 0,
    errors: dp.errors ?? metrics?.errorRate ?? 0
  }));
  const metricCards = [{
    title: 'API Request Rate',
    value: `${metrics?.apiRequestRate || 0}/min`,
    icon: Activity,
    trend: '+12%',
    trendUp: true,
    color: 'text-blue-500'
  }, {
    title: 'P95 Latency',
    value: `${metrics?.p95Latency || 0}ms`,
    icon: Clock,
    trend: '-5%',
    trendUp: false,
    color: 'text-green-500'
  }, {
    title: 'Cache Hit Rate',
    value: `${metrics?.cacheHitRate || 0}%`,
    icon: Zap,
    trend: '+2%',
    trendUp: true,
    color: 'text-yellow-500'
  }, {
    title: 'Active Connections',
    value: metrics?.activeConnections || 0,
    icon: Database,
    trend: '23/50',
    trendUp: null,
    color: 'text-purple-500'
  }, {
    title: 'Error Rate',
    value: `${metrics?.errorRate || 0}%`,
    icon: AlertCircle,
    trend: '-0.1%',
    trendUp: false,
    color: 'text-red-500'
  }, {
    title: 'Neo4j Query Time',
    value: `${metrics?.neo4jQueryTime || 0}ms`,
    icon: TrendingUp,
    trend: '-3ms',
    trendUp: false,
    color: 'text-cyan-500'
  }];

  if (isLoading) {
    return (
      <div className="container mx-auto p-6 space-y-6">
        <PageHeader
          title="System Health"
          description="Real-time system performance and health metrics"
          icon={<Activity className="h-6 w-6 text-primary" />}
          breadcrumbs={[
            { label: 'System', href: '/monitoring' },
            { label: 'System Health' }
          ]}
        />

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

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['health'] });
    queryClient.invalidateQueries({ queryKey: ['system-metrics'] });
    queryClient.invalidateQueries({ queryKey: ['historical-metrics'] });
  };

  const overallHealth = health?.status || (healthLoading ? 'loading' : 'unknown');
  const historicalSeries = historicalData ?? [];

  return (
    <div className="container mx-auto p-6 space-y-6">
      <PageHeader
        title="System Health"
        description="Real-time system performance and health metrics"
        icon={<Activity className="h-6 w-6 text-primary" />}
        breadcrumbs={[
          { label: 'System', href: '/monitoring' },
          { label: 'System Health' }
        ]}
      />

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Badge variant={overallHealth === 'healthy' ? 'default' : 'outline'}>
            {overallHealth}
          </Badge>
          <span className="text-sm text-muted-foreground">
            Updates every 5 seconds
          </span>
        </div>
        <Button variant="outline" size="sm" onClick={handleRefresh}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {metricCards.map((metric) => {
          const Icon = metric.icon;
          return (
            <Card key={metric.title}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium">{metric.title}</CardTitle>
                  <Icon className={`h-4 w-4 ${metric.color}`} />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{metric.value}</div>
                <div className="text-xs text-muted-foreground flex items-center gap-1">
                  {metric.trendUp === true && <TrendingUp className="h-3 w-3 text-green-500" />}
                  {metric.trendUp === false && <TrendingUp className="h-3 w-3 text-red-500 rotate-180" />}
                  <span>{metric.trend}</span>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>API Requests (Last Hour)</CardTitle>
            <CardDescription>Requests per minute</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={historicalSeries}>
                <defs>
                  <linearGradient id="colorRequests" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
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
                    borderRadius: '6px'
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
              <LineChart data={historicalSeries}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="timestamp" className="text-xs" />
                <YAxis className="text-xs" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '6px'
                  }}
                />
                <Line type="monotone" dataKey="latency" stroke="#10b981" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>System Health</CardTitle>
          <CardDescription>Overall system status and component health</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[
              {
                name: 'API Server',
                status: health?.components?.api === 'healthy' ? 'healthy' : 'unhealthy',
                uptime: 'n/a'
              },
              {
                name: 'Neo4j Database',
                status: health?.components?.database === 'healthy' ? 'healthy' : 'unhealthy',
                uptime: 'n/a'
              },
              {
                name: 'Cache',
                status: health?.components?.cache === 'healthy' ? 'healthy' : 'unhealthy',
                uptime: 'n/a'
              }
            ].map((component) => (
              <div
                key={component.name}
                className="flex items-center justify-between py-2 border-b last:border-0"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`h-2 w-2 rounded-full ${
                      component.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'
                    }`}
                  />
                  <span className="font-medium">{component.name}</span>
                </div>
                <div className="flex items-center gap-4">
                  <Badge variant="outline">Uptime: {component.uptime}</Badge>
                  <Badge variant={component.status === 'healthy' ? 'default' : 'outline'}>
                    {component.status}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
