import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getConnectors, triggerSync, type PLMConnector } from '@/services/plm';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@ui/card';
import { Button } from '@ui/button';
import { Badge } from '@ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@ui/tabs';
import { Alert, AlertDescription } from '@ui/alert';
import { Skeleton } from '@ui/skeleton';
import { toast } from 'sonner';
import {
  Database,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Play,
  Settings,
  Activity,
} from 'lucide-react';

interface SyncHistory {
  id: string;
  connector: string;
  timestamp: string;
  direction: 'plm_to_neo4j' | 'neo4j_to_plm';
  itemsProcessed: number;
  itemsFailed: number;
  duration: number;
  status: 'success' | 'partial' | 'failed';
}

export default function PLMIntegration() {
  const queryClient = useQueryClient();
  const [selectedConnector, setSelectedConnector] = useState<string | null>(null);

  // Fetch PLM connectors from real API
  const { data: connectorsResponse, isLoading } = useQuery({
    queryKey: ['plm-connectors'],
    queryFn: getConnectors,
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const connectors = connectorsResponse?.connectors;

  // Fetch sync history
  const { data: syncHistory } = useQuery<SyncHistory[]>({
    queryKey: ['plm-sync-history'],
    queryFn: async () => {
      // Mock data
      return [
        {
          id: '1',
          connector: 'Teamcenter Production',
          timestamp: '2025-12-09T10:30:00Z',
          direction: 'plm_to_neo4j',
          itemsProcessed: 150,
          itemsFailed: 0,
          duration: 45,
          status: 'success',
        },
        {
          id: '2',
          connector: 'Windchill Engineering',
          timestamp: '2025-12-09T09:15:00Z',
          direction: 'plm_to_neo4j',
          itemsProcessed: 89,
          itemsFailed: 3,
          duration: 38,
          status: 'partial',
        },
      ];
    },
  });

  // Sync mutation
  // Trigger sync mutation
  const syncMutation = useMutation({
    mutationFn: async (connectorId: string) => {
      return triggerSync(connectorId, { scope: 'incremental' });
    },
    onSuccess: (data) => {
      toast.success(`Sync started: ${data.job_id}`);
      queryClient.invalidateQueries({ queryKey: ['plm-connectors'] });
      queryClient.invalidateQueries({ queryKey: ['plm-sync-history'] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to start sync: ${error.message}`);
    },
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case 'disconnected':
        return <XCircle className="h-5 w-5 text-gray-400" />;
      case 'error':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      default:
        return <AlertCircle className="h-5 w-5 text-yellow-500" />;
    }
  };

  const getHealthBadge = (health: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive'> = {
      healthy: 'default',
      degraded: 'secondary',
      unhealthy: 'destructive',
    };
    return <Badge variant={variants[health] || 'secondary'}>{health}</Badge>;
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">PLM Integration</h1>
        <div className="grid gap-4 md:grid-cols-3">
          {[...Array(3)].map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-4 w-32" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-20 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">PLM Integration</h1>
          <p className="text-muted-foreground">
            Manage connections to enterprise PLM systems
          </p>
        </div>
        <Button onClick={() => queryClient.invalidateQueries({ queryKey: ['plm-connectors'] })}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Connector Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        {connectors?.map((connector) => (
          <Card
            key={connector.id}
            className={`cursor-pointer transition-all hover:shadow-md ${
              selectedConnector === connector.id ? 'ring-2 ring-primary' : ''
            }`}
            onClick={() => setSelectedConnector(connector.id)}
          >
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">{connector.name}</CardTitle>
                {getStatusIcon(connector.status)}
              </div>
              <CardDescription className="uppercase text-xs">
                {connector.type.replace('_', ' ')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Health</span>
                  {getHealthBadge(connector.health)}
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Items Synced</span>
                  <span className="font-medium">{connector.itemsSynced.toLocaleString()}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Last Sync</span>
                  <span className="font-medium">
                    {connector.lastSync
                      ? new Date(connector.lastSync).toLocaleTimeString()
                      : 'Never'}
                  </span>
                </div>
                <div className="pt-2 flex gap-2">
                  <Button
                    size="sm"
                    className="flex-1"
                    onClick={(e) => {
                      e.stopPropagation();
                      syncMutation.mutate(connector.id);
                    }}
                    disabled={connector.status !== 'connected' || syncMutation.isPending}
                  >
                    <Play className="mr-1 h-3 w-3" />
                    Sync
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={(e) => {
                      e.stopPropagation();
                      toast.info('Configuration panel coming soon');
                    }}
                  >
                    <Settings className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Tabs for Details */}
      <Tabs defaultValue="history" className="space-y-4">
        <TabsList>
          <TabsTrigger value="history">
            <Activity className="mr-2 h-4 w-4" />
            Sync History
          </TabsTrigger>
          <TabsTrigger value="config">
            <Settings className="mr-2 h-4 w-4" />
            Configuration
          </TabsTrigger>
          <TabsTrigger value="monitoring">
            <Database className="mr-2 h-4 w-4" />
            Monitoring
          </TabsTrigger>
        </TabsList>

        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Recent Synchronization Operations</CardTitle>
              <CardDescription>View the history of PLM sync operations</CardDescription>
            </CardHeader>
            <CardContent>
              {syncHistory && syncHistory.length > 0 ? (
                <div className="space-y-4">
                  {syncHistory.map((sync) => (
                    <div
                      key={sync.id}
                      className="flex items-center justify-between border-b pb-4 last:border-0 last:pb-0"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{sync.connector}</span>
                          <Badge variant={sync.status === 'success' ? 'default' : 'secondary'}>
                            {sync.status}
                          </Badge>
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {new Date(sync.timestamp).toLocaleString()}
                        </div>
                      </div>
                      <div className="text-right space-y-1">
                        <div className="text-sm">
                          {sync.itemsProcessed} items • {sync.duration}s
                        </div>
                        {sync.itemsFailed > 0 && (
                          <div className="text-sm text-destructive">
                            {sync.itemsFailed} failed
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <Alert>
                  <AlertDescription>No sync history available</AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="config">
          <Card>
            <CardHeader>
              <CardTitle>PLM Connector Configuration</CardTitle>
              <CardDescription>Configure PLM system connections and settings</CardDescription>
            </CardHeader>
            <CardContent>
              <Alert>
                <AlertDescription>
                  Configuration panel is under development. Please use environment variables or
                  configuration files for now.
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="monitoring">
          <Card>
            <CardHeader>
              <CardTitle>PLM Monitoring</CardTitle>
              <CardDescription>Monitor PLM connector health and performance</CardDescription>
            </CardHeader>
            <CardContent>
              <Alert>
                <AlertDescription>
                  Real-time monitoring dashboard is under development. Check Grafana for detailed
                  metrics.
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
