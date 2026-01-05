import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@ui/card';
import { Badge } from '@ui/badge';
import { Button } from '@ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@ui/tabs';
import { TrendingUp, Download, Share2, BarChart3, LineChart, PieChart } from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import { apiService } from '@/services/api';
export default function ResultsAnalysis() {
  const [selectedResult, setSelectedResult] = useState(null);
  const [isDetailsOpen, setIsDetailsOpen] = useState(false);

  const {
    data: resultsResponse,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['simulation-results'],
    queryFn: () => apiService.simulation.getResults({ limit: 100 }),
  });

  const results = useMemo(() => {
    const raw = resultsResponse?.results ?? [];
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
  }, [resultsResponse]);

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

    <Card><CardHeader><CardTitle>Result Visualization</CardTitle><CardDescription>Interactive charts and data exploration</CardDescription></CardHeader><CardContent><Tabs defaultValue="charts" className="w-full"><TabsList className="grid w-full grid-cols-3"><TabsTrigger value="charts"><BarChart3 className="h-4 w-4 mr-2" />Charts</TabsTrigger><TabsTrigger value="trends"><LineChart className="h-4 w-4 mr-2" />Trends</TabsTrigger><TabsTrigger value="comparison"><PieChart className="h-4 w-4 mr-2" />Comparison</TabsTrigger></TabsList><TabsContent value="charts" className="space-y-4"><div className="h-64 border-2 border-dashed rounded-lg flex items-center justify-center"><div className="text-center"><BarChart3 className="h-12 w-12 mx-auto mb-2 text-muted-foreground" /><p className="text-sm text-muted-foreground">Interactive charts will be displayed here</p><p className="text-xs text-muted-foreground">Select a result to visualize</p></div></div></TabsContent><TabsContent value="trends" className="space-y-4"><div className="h-64 border-2 border-dashed rounded-lg flex items-center justify-center"><div className="text-center"><LineChart className="h-12 w-12 mx-auto mb-2 text-muted-foreground" /><p className="text-sm text-muted-foreground">Trend analysis coming soon</p><p className="text-xs text-muted-foreground">Track metrics over time</p></div></div></TabsContent><TabsContent value="comparison" className="space-y-4"><div className="h-64 border-2 border-dashed rounded-lg flex items-center justify-center"><div className="text-center"><PieChart className="h-12 w-12 mx-auto mb-2 text-muted-foreground" /><p className="text-sm text-muted-foreground">Comparison view coming soon</p><p className="text-xs text-muted-foreground">Compare multiple results side-by-side</p></div></div></TabsContent></Tabs></CardContent></Card>

    <div className="grid grid-cols-1 md:grid-cols-4 gap-4"><Card><CardContent className="pt-6"><div className="text-2xl font-bold">{totalRuns}</div><p className="text-sm text-muted-foreground">Total Runs</p></CardContent></Card><Card><CardContent className="pt-6"><div className="text-2xl font-bold text-green-500">{successRate}%</div><p className="text-sm text-muted-foreground">Success Rate</p></CardContent></Card><Card><CardContent className="pt-6"><div className="text-2xl font-bold text-blue-500">—</div><p className="text-sm text-muted-foreground">Data Stored</p></CardContent></Card><Card><CardContent className="pt-6"><div className="text-2xl font-bold text-amber-500">—</div><p className="text-sm text-muted-foreground">Avg Runtime</p></CardContent></Card></div>

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
          <Button variant="outline" onClick={() => setIsDetailsOpen(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>;
}
