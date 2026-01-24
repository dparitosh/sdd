import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@ui/card';
import { Badge } from '@ui/badge';
import { Button } from '@ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@ui/dialog';
import { TrendingUp, Download, Share2, Activity as ActivityIcon } from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import { apiService } from '@/services/api';

export default function ResultsAnalysis() {
  const [selectedResult, setSelectedResult] = useState(null);
  const [isDetailsOpen, setIsDetailsOpen] = useState(false);

  // Queries
  const resultsQuery = useQuery({
    queryKey: ['simulation-results'],
    queryFn: () => apiService.simulation.getResults({ limit: 100 }),
  });

  const { isLoading, isError, error, refetch } = resultsQuery;

  const trsQuery = useQuery({
    queryKey: ['oslc-trs-changelog'],
    queryFn: () => apiService.trs.getChangeLog(),
  });

  const results = useMemo(() => {
    const raw = resultsQuery.data?.results ?? [];
    return raw.map(r => {
      const ts = r.last_modified || r.created_on || '—';
      const status = r.status || 'unknown';

      let metric = '—';
      const m = r.metrics;
      if (typeof m === 'string' && m.trim()) {
        metric = m;
      } else if (m && typeof m === 'object') {
        const firstKey = Object.keys(m)[0];
        if (firstKey) {
          const val = m[firstKey];
          metric = val === null || val === undefined ? firstKey : `${firstKey}: ${String(val)}`;
        }
      }

      return {
        id: r.id,
        name: r.name || `Result ${r.id}`,
        timestamp: ts,
        status,
        metric,
        raw: r,
      };
    });
  }, [resultsQuery.data]);

  const changeLog = useMemo(() => {
    const raw = trsQuery.data ?? [];
    // Assuming JSON-LD or Turtle content, we might need a parser in production
    // For now, if the response is JSON, we try to extract events
    // If text/turtle, we might display raw or need parsing logic
    return Array.isArray(raw) ? raw : [];
  }, [trsQuery.data]);


  const openDetails = (result) => {
    setSelectedResult(result);
    setIsDetailsOpen(true);
  };

  const totalRuns = results.length;
  const completedRuns = results.filter(r => r.status === 'completed' || r.status === 'success').length;
  const successRate = totalRuns === 0 ? 0 : Math.round(completedRuns / totalRuns * 1000) / 10;

  return <div className="container mx-auto p-6 space-y-6"><PageHeader title="Results Analysis" description="Analyze and visualize simulation outputs" icon={<TrendingUp className="h-8 w-8 text-primary" />} breadcrumbs={[{
      label: 'Simulation Engineering',
      href: '/simulation/models'
    }, {
      label: 'Results Analysis'
    }]} actions={<><Button variant="outline" onClick={() => refetch()} disabled={isLoading}><Download className="h-4 w-4 mr-2" />Refresh</Button><Button variant="outline" disabled><Share2 className="h-4 w-4 mr-2" />Share</Button></>} />

    <Card><CardHeader><CardTitle>Recent Simulation Results</CardTitle><CardDescription>Results stored in the knowledge graph</CardDescription></CardHeader><CardContent>
      {isError && <div className="p-4 border rounded-lg text-sm text-destructive">{String(error?.message || error || 'Failed to load results')}</div>}
      {!isError && results.length === 0 && !isLoading && <div className="p-4 border rounded-lg text-sm text-muted-foreground">No stored `SimulationResult` nodes found yet. Run/ingest simulations to populate results.</div>}
      <div className="space-y-3">
        {(isLoading ? Array.from({ length: 3 }).map((_, idx) => ({ id: `loading-${idx}` })) : results).map(r => {
          if (isLoading) {
            return <div key={r.id} className="p-4 border rounded-lg animate-pulse"><div className="h-4 bg-muted rounded w-1/2" /><div className="h-3 bg-muted rounded w-1/3 mt-2" /></div>;
          }
          return <div key={r.id} className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent/50 transition-colors"><div className="min-w-0"><p className="font-medium truncate">{r.name}</p><p className="text-sm text-muted-foreground truncate">{r.timestamp}</p></div><div className="flex items-center gap-3"><Badge variant="outline">{r.metric}</Badge><Badge className={r.status === 'completed' || r.status === 'success' ? 'bg-green-500' : 'bg-muted text-foreground'}>{r.status}</Badge><Button variant="ghost" size="sm" onClick={() => openDetails(r)}>View Details</Button></div></div>;
        })}
      </div>
    </CardContent></Card>

    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <Card>
        <CardContent className="pt-6">
          <div className="text-2xl font-bold">{totalRuns}</div>
          <p className="text-sm text-muted-foreground">Total Runs</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-6">
          <div className="text-2xl font-bold text-green-500">{successRate}%</div>
          <p className="text-sm text-muted-foreground">Success Rate</p>
        </CardContent>
      </Card>
    </div>

    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ActivityIcon className="h-5 w-5 text-primary" />
          Live OSLC Change Log
        </CardTitle>
        <CardDescription>Real-time tracked resource set events</CardDescription>
      </CardHeader>
      <CardContent>
        {trsQuery.isLoading ? (
          <div className="text-sm text-muted-foreground p-4 text-center">Loading ChangeLog...</div>
        ) : trsQuery.isError ? (
          <div className="text-sm text-destructive p-4">Failed to load ChangeLog</div>
        ) : (
            <div className="space-y-2 max-h-60 overflow-y-auto">
              <div className="text-xs text-muted-foreground mb-2">Displaying raw RDF/Turtle response from /oslc/trs/changelog</div>
              <pre className="text-xs font-mono bg-muted p-2 rounded whitespace-pre-wrap">
                {typeof trsQuery.data === 'string' ? trsQuery.data : JSON.stringify(trsQuery.data, null, 2)}
              </pre>
            </div>
        )}
      </CardContent>
    </Card>

    <Dialog open={isDetailsOpen} onOpenChange={setIsDetailsOpen}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Result Details</DialogTitle>
          <DialogDescription>Raw data from the graph node</DialogDescription>
        </DialogHeader>
        <div className="space-y-3 py-2">
          <div>
            <div className="text-sm font-medium">Name</div>
            <div className="text-sm text-muted-foreground">{selectedResult?.name}</div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-sm font-medium">Timestamp</div>
              <div className="text-sm text-muted-foreground">{selectedResult?.timestamp}</div>
            </div>
            <div>
              <div className="text-sm font-medium">Status</div>
              <div className="text-sm text-muted-foreground">{selectedResult?.status}</div>
            </div>
          </div>
          <div>
            <div className="text-sm font-medium">Metrics</div>
            <pre className="text-xs bg-muted/50 p-3 rounded-lg overflow-auto max-h-64">{JSON.stringify(selectedResult?.raw?.metrics ?? null, null, 2)}</pre>
          </div>
          <div>
            <div className="text-sm font-medium">Parameters</div>
            <pre className="text-xs bg-muted/50 p-3 rounded-lg overflow-auto max-h-64">{JSON.stringify(selectedResult?.raw?.parameters ?? null, null, 2)}</pre>
          </div>
        </div>
        <DialogFooter>
            <Button onClick={() => setIsDetailsOpen(false)}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>;
}
