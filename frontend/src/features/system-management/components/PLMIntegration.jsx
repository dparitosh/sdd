import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getConnectors, triggerSync } from '@/services/plm';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@ui/card';
import { Button } from '@ui/button';
import { Badge } from '@ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@ui/tabs';
import { Alert, AlertDescription } from '@ui/alert';
import { Skeleton } from '@ui/skeleton';
import { toast } from 'sonner';
import { Database, RefreshCw, CheckCircle2, XCircle, AlertCircle, Play, Settings, Activity } from 'lucide-react';
import PageHeader from '@/components/PageHeader';
const getErrorMessage = error => {
  if (error instanceof Error) return error.message;
  if (typeof error === 'string') return error;
  if (error?.response?.data?.error) {
    const err = error.response.data.error;
    return typeof err === 'string' ? err : err?.message || 'An error occurred';
  }
  if (error?.message) return error.message;
  return 'An unknown error occurred';
};
export default function PLMIntegration() {
  const queryClient = useQueryClient();
  const [selectedConnector, setSelectedConnector] = useState(null);
  const {
    data: connectorsResponse,
    isLoading
  } = useQuery({
    queryKey: ['plm-connectors'],
    queryFn: getConnectors,
    refetchInterval: 30000
  });
  const connectors = connectorsResponse?.connectors;
  const {
    data: syncHistory
  } = useQuery({
    queryKey: ['plm-sync-history'],
    queryFn: async () => {
      // Aggregate sync_history from all connected connectors
      if (!connectors || connectors.length === 0) return [];
      try {
        const { getConnectorStatus } = await import('@/services/plm');
        const statuses = await Promise.allSettled(
          connectors.map(c => getConnectorStatus(c.id))
        );
        const history = statuses
          .filter(s => s.status === 'fulfilled' && s.value?.sync_history)
          .flatMap(s => s.value.sync_history.map(h => ({
            ...h,
            connector: connectors.find(c => c.id === h.connector_id)?.name || h.connector_id
          })))
          .sort((a, b) => new Date(b.started_at) - new Date(a.started_at))
          .slice(0, 20);
        return history;
      } catch {
        return [];
      }
    },
    enabled: !!connectors && connectors.length > 0
  });
  const syncMutation = useMutation({
    mutationFn: async connectorId => {
      return triggerSync(connectorId, {
        scope: 'incremental'
      });
    },
    onSuccess: data => {
      toast.success(`Sync started: ${data.job_id}`);
      queryClient.invalidateQueries({
        queryKey: ['plm-connectors']
      });
      queryClient.invalidateQueries({
        queryKey: ['plm-sync-history']
      });
    },
    onError: error => {
      toast.error(`Failed to start sync: ${getErrorMessage(error)}`);
    }
  });
  const getStatusIcon = status => {
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
  const getHealthBadge = health => {
    const variants = {
      healthy: 'default',
      degraded: 'secondary',
      unhealthy: 'destructive'
    };
    return <Badge variant={variants[health] || 'secondary'}>{health}</Badge>;
  };
  if (isLoading) {
    return <div className="space-y-6"><h1 className="text-3xl font-bold">PLM Integration</h1><div className="grid gap-4 md:grid-cols-3">{[...Array(3)].map((_, i) => <Card key={i}><CardHeader><Skeleton className="h-4 w-32" /></CardHeader><CardContent><Skeleton className="h-20 w-full" /></CardContent></Card>)}</div></div>;
  }
  return <div className="container mx-auto p-6 space-y-6"><PageHeader title="PLM Integration" description="Manage connections to enterprise PLM systems" icon={<Database className="h-6 w-6 text-primary" />} breadcrumbs={[{
      label: 'Data Management',
      href: '/import'
    }, {
      label: 'PLM Integration'
    }]} actions={<Button onClick={() => queryClient.invalidateQueries({
      queryKey: ['plm-connectors']
    })}><RefreshCw className="mr-2 h-4 w-4" />Refresh</Button>} /><div className="grid gap-4 md:grid-cols-3">{connectors?.map(connector => <Card key={connector.id} className={`cursor-pointer transition-all hover:shadow-md ${selectedConnector === connector.id ? 'ring-2 ring-primary' : ''}`} onClick={() => setSelectedConnector(connector.id)}><CardHeader className="pb-3"><div className="flex items-center justify-between"><CardTitle className="text-lg">{connector.name}</CardTitle>{getStatusIcon(connector.status)}</div><CardDescription className="uppercase text-xs">{connector.type.replace('_', ' ')}</CardDescription></CardHeader><CardContent><div className="space-y-2"><div className="flex items-center justify-between text-sm"><span className="text-muted-foreground">Health</span>{getHealthBadge(connector.health)}</div><div className="flex items-center justify-between text-sm"><span className="text-muted-foreground">Items Synced</span><span className="font-medium">{(connector.itemsSynced ?? 0).toLocaleString()}</span></div><div className="flex items-center justify-between text-sm"><span className="text-muted-foreground">Last Sync</span><span className="font-medium">{connector.lastSync ? new Date(connector.lastSync).toLocaleTimeString() : 'Never'}</span></div><div className="pt-2 flex gap-2"><Button size="sm" className="flex-1" onClick={e => {
                e.stopPropagation();
                syncMutation.mutate(connector.id);
              }} disabled={connector.status !== 'connected' || syncMutation.isPending}><Play className="mr-1 h-3 w-3" />Sync</Button><Button size="sm" variant="outline" onClick={e => {
                e.stopPropagation();
                toast.info('Configuration panel coming soon');
              }}><Settings className="h-3 w-3" /></Button></div></div></CardContent></Card>)}</div><Tabs defaultValue="history" className="space-y-4"><TabsList><TabsTrigger value="history"><Activity className="mr-2 h-4 w-4" />Sync History</TabsTrigger><TabsTrigger value="config"><Settings className="mr-2 h-4 w-4" />Configuration</TabsTrigger><TabsTrigger value="monitoring"><Database className="mr-2 h-4 w-4" />Monitoring</TabsTrigger></TabsList><TabsContent value="history" className="space-y-4"><Card><CardHeader><CardTitle>Recent Synchronization Operations</CardTitle><CardDescription>View the history of PLM sync operations</CardDescription></CardHeader><CardContent>{syncHistory && syncHistory.length > 0 ? <div className="space-y-4">{syncHistory.map(sync => <div key={sync.job_id || sync.id} className="flex items-center justify-between border-b pb-4 last:border-0 last:pb-0"><div className="space-y-1"><div className="flex items-center gap-2"><span className="font-medium">{sync.connector}</span><Badge variant={sync.status === 'completed' || sync.status === 'success' ? 'default' : 'secondary'}>{sync.status}</Badge></div><div className="text-sm text-muted-foreground">{new Date(sync.started_at || sync.timestamp).toLocaleString()}</div></div><div className="text-right space-y-1"><div className="text-sm">{sync.items_synced ?? sync.itemsProcessed ?? 0} items{sync.duration ? ` • ${sync.duration}s` : ''}</div>{(sync.errors?.length > 0 || sync.itemsFailed > 0) && <div className="text-sm text-destructive">{sync.errors?.length || sync.itemsFailed} failed</div>}</div></div>)}</div> : <Alert><AlertDescription>No sync history available</AlertDescription></Alert>}</CardContent></Card></TabsContent><TabsContent value="config"><Card><CardHeader><CardTitle>PLM Connector Configuration</CardTitle><CardDescription>Configure PLM system connections and settings</CardDescription></CardHeader><CardContent><Alert><AlertDescription>Configuration panel is under development. Please use environment variables or configuration files for now.</AlertDescription></Alert></CardContent></Card></TabsContent><TabsContent value="monitoring"><Card><CardHeader><CardTitle>PLM Monitoring</CardTitle><CardDescription>Monitor PLM connector health and performance</CardDescription></CardHeader><CardContent><Alert><AlertDescription>Real-time monitoring dashboard is under development. Check Grafana for detailed metrics.</AlertDescription></Alert></CardContent></Card></TabsContent></Tabs></div>;
}
