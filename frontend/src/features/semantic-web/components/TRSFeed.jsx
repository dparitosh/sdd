import { useState, useEffect, useCallback, useRef } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@ui/card';
import { Button } from '@ui/button';
import { Badge } from '@ui/badge';
import { Switch } from '@ui/switch';
import { Label } from '@ui/label';
import { ScrollArea } from '@ui/scroll-area';
import { Skeleton } from '@ui/skeleton';
import { Alert, AlertDescription } from '@ui/alert';
import PageHeader from '@/components/PageHeader';
import { Radio, Plus, Pencil, Trash2, RefreshCw } from 'lucide-react';
import { useOSLC } from '../hooks/useOSLC';

const EVENT_ICONS = {
  Creation: Plus,
  Modification: Pencil,
  Deletion: Trash2,
};

const EVENT_COLORS = {
  Creation: 'bg-green-500',
  Modification: 'bg-blue-500',
  Deletion: 'bg-red-500',
};

export default function TRSFeed() {
  const [autoRefresh, setAutoRefresh] = useState(false);
  const intervalRef = useRef(null);
  const { trsBase, trsChangelog, isLoadingTRS, trsError, refreshTRS } = useOSLC();

  // Auto-refresh every 30s
  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(refreshTRS, 30_000);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [autoRefresh, refreshTRS]);

  const baseResources = trsBase?.members ?? trsBase?.resources ?? [];
  const changeEvents = trsChangelog?.events ?? trsChangelog?.changes ?? [];

  return (
    <div className="container mx-auto p-6 space-y-6">
      <PageHeader
        title="TRS Feed"
        description="Tracked Resource Set — base resources and change events"
        icon={<Radio className="h-6 w-6 text-primary" />}
      />

      {/* Controls */}
      <div className="flex items-center gap-4">
        <Button variant="outline" size="sm" onClick={refreshTRS} disabled={isLoadingTRS}>
          <RefreshCw className={`h-4 w-4 mr-2 ${isLoadingTRS ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
        <div className="flex items-center gap-2">
          <Switch checked={autoRefresh} onCheckedChange={setAutoRefresh} id="auto-refresh" />
          <Label htmlFor="auto-refresh" className="text-sm">Auto-refresh (30s)</Label>
        </div>
      </div>

      {trsError && (
        <Alert variant="destructive"><AlertDescription>{String(trsError)}</AlertDescription></Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Base resources */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Base Resources</CardTitle>
            <CardDescription>{baseResources.length} resource{baseResources.length !== 1 ? 's' : ''} in base</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoadingTRS ? (
              <div className="space-y-2">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-5 w-full" />)}</div>
            ) : baseResources.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">No base resources</p>
            ) : (
              <ScrollArea className="h-80">
                <ul className="space-y-2">
                  {baseResources.map((r, i) => (
                    <li key={i} className="flex items-center gap-2 text-sm border rounded p-2">
                      <Badge variant="outline" className="text-xs shrink-0">{r.type ?? 'Resource'}</Badge>
                      <span className="truncate font-mono text-xs">{r.uri ?? r.about ?? String(r)}</span>
                    </li>
                  ))}
                </ul>
              </ScrollArea>
            )}
          </CardContent>
        </Card>

        {/* Change events timeline */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Change Log</CardTitle>
            <CardDescription>Timeline of creation, modification, and deletion events</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoadingTRS ? (
              <div className="space-y-2">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-5 w-full" />)}</div>
            ) : changeEvents.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">No change events</p>
            ) : (
              <ScrollArea className="h-80">
                <ul className="space-y-0">
                  {changeEvents.map((evt, i) => {
                    const type = evt.type ?? evt.change_type ?? 'Modification';
                    const Icon = EVENT_ICONS[type] ?? Pencil;
                    const color = EVENT_COLORS[type] ?? 'bg-gray-500';
                    return (
                      <li key={i} className="flex gap-3 pb-4 last:pb-0">
                        {/* Timeline dot + connector */}
                        <div className="flex flex-col items-center">
                          <div className={`h-6 w-6 rounded-full ${color} flex items-center justify-center shrink-0`}>
                            <Icon className="h-3 w-3 text-white" />
                          </div>
                          {i < changeEvents.length - 1 && <div className="w-px flex-1 bg-muted mt-1" />}
                        </div>
                        {/* Content */}
                        <div className="flex-1 min-w-0 pt-0.5">
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className="text-xs">{type}</Badge>
                            {evt.timestamp && <span className="text-xs text-muted-foreground">{evt.timestamp}</span>}
                          </div>
                          <p className="text-xs font-mono text-muted-foreground truncate mt-0.5">{evt.uri ?? evt.resource ?? '—'}</p>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </ScrollArea>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
