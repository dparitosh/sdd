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
import {
  Database,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Play,
  Settings,
  Activity } from
'lucide-react';
import PageHeader from '@/components/PageHeader';

// Helper to extract error message
import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";const getErrorMessage = (error) => {
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

  // Fetch PLM connectors from real API
  const { data: connectorsResponse, isLoading } = useQuery({
    queryKey: ['plm-connectors'],
    queryFn: getConnectors,
    refetchInterval: 30000 // Refresh every 30 seconds
  });

  const connectors = connectorsResponse?.connectors;

  // Fetch sync history
  const { data: syncHistory } = useQuery({
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
        status: 'success'
      },
      {
        id: '2',
        connector: 'Windchill Engineering',
        timestamp: '2025-12-09T09:15:00Z',
        direction: 'plm_to_neo4j',
        itemsProcessed: 89,
        itemsFailed: 3,
        duration: 38,
        status: 'partial'
      }];

    }
  });

  // Sync mutation
  // Trigger sync mutation
  const syncMutation = useMutation({
    mutationFn: async (connectorId) => {
      return triggerSync(connectorId, { scope: 'incremental' });
    },
    onSuccess: (data) => {
      toast.success(`Sync started: ${data.job_id}`);
      queryClient.invalidateQueries({ queryKey: ['plm-connectors'] });
      queryClient.invalidateQueries({ queryKey: ['plm-sync-history'] });
    },
    onError: (error) => {
      toast.error(`Failed to start sync: ${getErrorMessage(error)}`);
    }
  });

  const getStatusIcon = (status) => {
    switch (status) {
      case 'connected':
        return /*#__PURE__*/_jsx(CheckCircle2, { className: "h-5 w-5 text-green-500" });
      case 'disconnected':
        return /*#__PURE__*/_jsx(XCircle, { className: "h-5 w-5 text-gray-400" });
      case 'error':
        return /*#__PURE__*/_jsx(AlertCircle, { className: "h-5 w-5 text-red-500" });
      default:
        return /*#__PURE__*/_jsx(AlertCircle, { className: "h-5 w-5 text-yellow-500" });
    }
  };

  const getHealthBadge = (health) => {
    const variants = {
      healthy: 'default',
      degraded: 'secondary',
      unhealthy: 'destructive'
    };
    return /*#__PURE__*/_jsx(Badge, { variant: variants[health] || 'secondary', children: health });
  };

  if (isLoading) {
    return (/*#__PURE__*/
      _jsxs("div", { className: "space-y-6", children: [/*#__PURE__*/
        _jsx("h1", { className: "text-3xl font-bold", children: "PLM Integration" }), /*#__PURE__*/
        _jsx("div", { className: "grid gap-4 md:grid-cols-3", children:
          [...Array(3)].map((_, i) => /*#__PURE__*/
          _jsxs(Card, { children: [/*#__PURE__*/
            _jsx(CardHeader, { children: /*#__PURE__*/
              _jsx(Skeleton, { className: "h-4 w-32" }) }
            ), /*#__PURE__*/
            _jsx(CardContent, { children: /*#__PURE__*/
              _jsx(Skeleton, { className: "h-20 w-full" }) }
            )] }, i
          )
          ) }
        )] }
      ));

  }

  return (/*#__PURE__*/
    _jsxs("div", { className: "container mx-auto p-6 space-y-6", children: [/*#__PURE__*/
      _jsx(PageHeader, {
        title: "PLM Integration",
        description: "Manage connections to enterprise PLM systems",
        icon: /*#__PURE__*/_jsx(Database, { className: "h-6 w-6 text-primary" }),
        breadcrumbs: [
        { label: 'Data Management', href: '/import' },
        { label: 'PLM Integration' }],

        actions: /*#__PURE__*/
        _jsxs(Button, { onClick: () => queryClient.invalidateQueries({ queryKey: ['plm-connectors'] }), children: [/*#__PURE__*/
          _jsx(RefreshCw, { className: "mr-2 h-4 w-4" }), "Refresh"] }

        ) }

      ), /*#__PURE__*/


      _jsx("div", { className: "grid gap-4 md:grid-cols-3", children:
        connectors?.map((connector) => /*#__PURE__*/
        _jsxs(Card, {

          className: `cursor-pointer transition-all hover:shadow-md ${
          selectedConnector === connector.id ? 'ring-2 ring-primary' : ''}`,

          onClick: () => setSelectedConnector(connector.id), children: [/*#__PURE__*/

          _jsxs(CardHeader, { className: "pb-3", children: [/*#__PURE__*/
            _jsxs("div", { className: "flex items-center justify-between", children: [/*#__PURE__*/
              _jsx(CardTitle, { className: "text-lg", children: connector.name }),
              getStatusIcon(connector.status)] }
            ), /*#__PURE__*/
            _jsx(CardDescription, { className: "uppercase text-xs", children:
              connector.type.replace('_', ' ') }
            )] }
          ), /*#__PURE__*/
          _jsx(CardContent, { children: /*#__PURE__*/
            _jsxs("div", { className: "space-y-2", children: [/*#__PURE__*/
              _jsxs("div", { className: "flex items-center justify-between text-sm", children: [/*#__PURE__*/
                _jsx("span", { className: "text-muted-foreground", children: "Health" }),
                getHealthBadge(connector.health)] }
              ), /*#__PURE__*/
              _jsxs("div", { className: "flex items-center justify-between text-sm", children: [/*#__PURE__*/
                _jsx("span", { className: "text-muted-foreground", children: "Items Synced" }), /*#__PURE__*/
                _jsx("span", { className: "font-medium", children: connector.itemsSynced.toLocaleString() })] }
              ), /*#__PURE__*/
              _jsxs("div", { className: "flex items-center justify-between text-sm", children: [/*#__PURE__*/
                _jsx("span", { className: "text-muted-foreground", children: "Last Sync" }), /*#__PURE__*/
                _jsx("span", { className: "font-medium", children:
                  connector.lastSync ?
                  new Date(connector.lastSync).toLocaleTimeString() :
                  'Never' }
                )] }
              ), /*#__PURE__*/
              _jsxs("div", { className: "pt-2 flex gap-2", children: [/*#__PURE__*/
                _jsxs(Button, {
                  size: "sm",
                  className: "flex-1",
                  onClick: (e) => {
                    e.stopPropagation();
                    syncMutation.mutate(connector.id);
                  },
                  disabled: connector.status !== 'connected' || syncMutation.isPending, children: [/*#__PURE__*/

                  _jsx(Play, { className: "mr-1 h-3 w-3" }), "Sync"] }

                ), /*#__PURE__*/
                _jsx(Button, {
                  size: "sm",
                  variant: "outline",
                  onClick: (e) => {
                    e.stopPropagation();
                    toast.info('Configuration panel coming soon');
                  }, children: /*#__PURE__*/

                  _jsx(Settings, { className: "h-3 w-3" }) }
                )] }
              )] }
            ) }
          )] }, connector.id
        )
        ) }
      ), /*#__PURE__*/


      _jsxs(Tabs, { defaultValue: "history", className: "space-y-4", children: [/*#__PURE__*/
        _jsxs(TabsList, { children: [/*#__PURE__*/
          _jsxs(TabsTrigger, { value: "history", children: [/*#__PURE__*/
            _jsx(Activity, { className: "mr-2 h-4 w-4" }), "Sync History"] }

          ), /*#__PURE__*/
          _jsxs(TabsTrigger, { value: "config", children: [/*#__PURE__*/
            _jsx(Settings, { className: "mr-2 h-4 w-4" }), "Configuration"] }

          ), /*#__PURE__*/
          _jsxs(TabsTrigger, { value: "monitoring", children: [/*#__PURE__*/
            _jsx(Database, { className: "mr-2 h-4 w-4" }), "Monitoring"] }

          )] }
        ), /*#__PURE__*/

        _jsx(TabsContent, { value: "history", className: "space-y-4", children: /*#__PURE__*/
          _jsxs(Card, { children: [/*#__PURE__*/
            _jsxs(CardHeader, { children: [/*#__PURE__*/
              _jsx(CardTitle, { children: "Recent Synchronization Operations" }), /*#__PURE__*/
              _jsx(CardDescription, { children: "View the history of PLM sync operations" })] }
            ), /*#__PURE__*/
            _jsx(CardContent, { children:
              syncHistory && syncHistory.length > 0 ? /*#__PURE__*/
              _jsx("div", { className: "space-y-4", children:
                syncHistory.map((sync) => /*#__PURE__*/
                _jsxs("div", {

                  className: "flex items-center justify-between border-b pb-4 last:border-0 last:pb-0", children: [/*#__PURE__*/

                  _jsxs("div", { className: "space-y-1", children: [/*#__PURE__*/
                    _jsxs("div", { className: "flex items-center gap-2", children: [/*#__PURE__*/
                      _jsx("span", { className: "font-medium", children: sync.connector }), /*#__PURE__*/
                      _jsx(Badge, { variant: sync.status === 'success' ? 'default' : 'secondary', children:
                        sync.status }
                      )] }
                    ), /*#__PURE__*/
                    _jsx("div", { className: "text-sm text-muted-foreground", children:
                      new Date(sync.timestamp).toLocaleString() }
                    )] }
                  ), /*#__PURE__*/
                  _jsxs("div", { className: "text-right space-y-1", children: [/*#__PURE__*/
                    _jsxs("div", { className: "text-sm", children: [
                      sync.itemsProcessed, " items \u2022 ", sync.duration, "s"] }
                    ),
                    sync.itemsFailed > 0 && /*#__PURE__*/
                    _jsxs("div", { className: "text-sm text-destructive", children: [
                      sync.itemsFailed, " failed"] }
                    )] }

                  )] }, sync.id
                )
                ) }
              ) : /*#__PURE__*/

              _jsx(Alert, { children: /*#__PURE__*/
                _jsx(AlertDescription, { children: "No sync history available" }) }
              ) }

            )] }
          ) }
        ), /*#__PURE__*/

        _jsx(TabsContent, { value: "config", children: /*#__PURE__*/
          _jsxs(Card, { children: [/*#__PURE__*/
            _jsxs(CardHeader, { children: [/*#__PURE__*/
              _jsx(CardTitle, { children: "PLM Connector Configuration" }), /*#__PURE__*/
              _jsx(CardDescription, { children: "Configure PLM system connections and settings" })] }
            ), /*#__PURE__*/
            _jsx(CardContent, { children: /*#__PURE__*/
              _jsx(Alert, { children: /*#__PURE__*/
                _jsx(AlertDescription, { children: "Configuration panel is under development. Please use environment variables or configuration files for now." }


                ) }
              ) }
            )] }
          ) }
        ), /*#__PURE__*/

        _jsx(TabsContent, { value: "monitoring", children: /*#__PURE__*/
          _jsxs(Card, { children: [/*#__PURE__*/
            _jsxs(CardHeader, { children: [/*#__PURE__*/
              _jsx(CardTitle, { children: "PLM Monitoring" }), /*#__PURE__*/
              _jsx(CardDescription, { children: "Monitor PLM connector health and performance" })] }
            ), /*#__PURE__*/
            _jsx(CardContent, { children: /*#__PURE__*/
              _jsx(Alert, { children: /*#__PURE__*/
                _jsx(AlertDescription, { children: "Real-time monitoring dashboard is under development. Check Grafana for detailed metrics." }


                ) }
              ) }
            )] }
          ) }
        )] }
      )] }
    ));

}
