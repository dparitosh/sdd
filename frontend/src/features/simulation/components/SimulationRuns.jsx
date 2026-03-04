import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useDebounce } from 'use-debounce';
import { getRuns } from '@/services/simulation.service';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  AlertCircle, 
  Search, 
  RefreshCw,
  Eye,
  Activity,
  Zap,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2
} from 'lucide-react';

// Normalise status so "Completed"/"Complete"/"COMPLETED" all map to one key
const normaliseStatus = (s) => {
  if (!s) return 'Unknown';
  const u = s.toUpperCase();
  if (u.includes('COMPLET')) return 'Completed';
  if (u.includes('RUN') || u.includes('PROGRESS') || u.includes('ACTIVE')) return 'Running';
  if (u.includes('FAIL') || u.includes('ERROR')) return 'Failed';
  if (u.includes('PENDING') || u.includes('QUEUE')) return 'Pending';
  return s;
};

const STATUS_CONFIG = {
  'Completed': { bg: 'bg-emerald-100 text-emerald-800 border border-emerald-200', dot: 'bg-emerald-500', icon: CheckCircle2 },
  'Running':   { bg: 'bg-blue-100 text-blue-800 border border-blue-200',         dot: 'bg-blue-500 animate-pulse', icon: Loader2 },
  'Failed':    { bg: 'bg-red-100 text-red-800 border border-red-200',             dot: 'bg-red-500', icon: XCircle },
  'Pending':   { bg: 'bg-amber-100 text-amber-800 border border-amber-200',       dot: 'bg-amber-400', icon: Clock },
  'Unknown':   { bg: 'bg-slate-100 text-slate-600 border border-slate-200',       dot: 'bg-slate-400', icon: Activity },
};

// Infer sim type from run ID when sim_type field is null
const inferSimType = (id, simType) => {
  if (simType) return simType;
  if (!id) return null;
  const u = id.toUpperCase();
  if (u.includes('MAXWELL') || u.includes('EM') || u.includes('MOTOR')) return 'Electromagnetic';
  if (u.includes('CFD') || u.includes('FLUENT') || u.includes('PUMP')) return 'CFD';
  if (u.includes('THERM') || u.includes('HEAT')) return 'Thermal';
  if (u.includes('NVH') || u.includes('VIBR') || u.includes('ACOUSTIC')) return 'NVH';
  if (u.includes('FEA') || u.includes('STRUCT') || u.includes('CRANE')) return 'Structural';
  if (u.includes('CAD')) return 'CAD-Linked';
  return 'General';
};

const SIM_TYPE_COLORS = {
  'Electromagnetic': 'bg-purple-100 text-purple-800 border border-purple-200',
  'Thermal':         'bg-orange-100 text-orange-800 border border-orange-200',
  'NVH':             'bg-blue-100 text-blue-800 border border-blue-200',
  'Structural':      'bg-slate-100 text-slate-700 border border-slate-200',
  'CFD':             'bg-cyan-100 text-cyan-800 border border-cyan-200',
  'CAD-Linked':      'bg-indigo-100 text-indigo-800 border border-indigo-200',
  'General':         'bg-gray-100 text-gray-700 border border-gray-200',
};

const StatusBadge = ({ status }) => {
  const norm = normaliseStatus(status);
  const cfg = STATUS_CONFIG[norm] ?? STATUS_CONFIG['Unknown'];
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${cfg.bg}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {norm}
    </span>
  );
};

const SimulationRuns = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [simTypeFilter, setSimTypeFilter] = useState('all');
  const [debouncedSearchQuery] = useDebounce(searchQuery, 300);

  const {
    data: rawRuns,
    isLoading: loadingRuns,
    error: runsError,
    refetch: refetchRuns
  } = useQuery({
    queryKey: ['simulation-runs', statusFilter, simTypeFilter],
    queryFn: () => {
      const params = {};
      if (statusFilter !== 'all') params.run_status = statusFilter;
      if (simTypeFilter !== 'all') params.sim_type = simTypeFilter;
      return getRuns(params);
    },
    refetchInterval: 30000,
  });

  // Normalise runs — fill inferred fields
  const runs = (rawRuns || []).map(r => ({
    ...r,
    _status: normaliseStatus(r.status),
    _simType: inferSimType(r.id, r.sim_type),
  }));

  const filteredRuns = runs.filter(r => {
    const matchSearch = !debouncedSearchQuery ||
      r.id?.toLowerCase().includes(debouncedSearchQuery.toLowerCase()) ||
      r._simType?.toLowerCase().includes(debouncedSearchQuery.toLowerCase()) ||
      r.solver_version?.toLowerCase().includes(debouncedSearchQuery.toLowerCase());
    const matchStatus = statusFilter === 'all' || r._status === statusFilter;
    const matchType   = simTypeFilter === 'all' || r._simType === simTypeFilter;
    return matchSearch && matchStatus && matchType;
  });

  const countByStatus = (s) => runs.filter(r => r._status === s).length;

  const formatDate = (dt) => {
    if (!dt) return '—';
    return new Date(dt).toLocaleDateString('en-GB', { day:'2-digit', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit' });
  };

  const uniqueTypes = [...new Set(runs.map(r => r._simType).filter(Boolean))].sort();

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Simulation Runs</h1>
          <p className="text-muted-foreground mt-1">Track and analyze AP243 simulation executions</p>
        </div>
        <Button variant="outline" onClick={() => refetchRuns()} disabled={loadingRuns}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loadingRuns ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Runs</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{runs.length}</div>
            <p className="text-xs text-muted-foreground mt-1">AP243 simulation runs</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completed</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-600">{countByStatus('Completed')}</div>
            <p className="text-xs text-muted-foreground mt-1">Successfully finished</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Running</CardTitle>
            <Activity className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{countByStatus('Running')}</div>
            <p className="text-xs text-muted-foreground mt-1">In progress</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed</CardTitle>
            <XCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{countByStatus('Failed')}</div>
            <p className="text-xs text-muted-foreground mt-1">Require attention</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by ID or type..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
        >
          <option value="all">All Statuses</option>
          {Object.keys(STATUS_CONFIG).filter(k => k !== 'Unknown').map(s => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select
          value={simTypeFilter}
          onChange={(e) => setSimTypeFilter(e.target.value)}
          className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
        >
          <option value="all">All Types</option>
          {uniqueTypes.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>

      {/* Table */}
      <Card>
        <CardHeader>
          <CardTitle>Simulation Runs ({filteredRuns.length})</CardTitle>
          <CardDescription>AP243-linked simulation execution records</CardDescription>
        </CardHeader>
        <CardContent>
          {runsError && (
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>Failed to load runs: {runsError.message}</AlertDescription>
            </Alert>
          )}

          {loadingRuns ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-50">
                  <TableHead className="font-semibold">Run ID</TableHead>
                  <TableHead className="font-semibold">Type</TableHead>
                  <TableHead className="font-semibold">Status</TableHead>
                  <TableHead className="font-semibold">AP Level</TableHead>
                  <TableHead className="font-semibold">Start Time</TableHead>
                  <TableHead className="font-semibold">CPU Hours</TableHead>
                  <TableHead className="font-semibold">Mesh Elements</TableHead>
                  <TableHead className="font-semibold">Credibility</TableHead>
                  <TableHead className="font-semibold">Artifacts</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredRuns.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={10} className="text-center text-muted-foreground py-12">
                      No simulation runs found
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredRuns.map((run) => (
                    <TableRow key={run.id} className="hover:bg-slate-50 cursor-pointer" onClick={() => navigate(`/engineer/simulation/runs/${run.id}`)}>
                      <TableCell className="font-mono text-sm font-medium text-slate-800">{run.id}</TableCell>
                      <TableCell>
                        {run._simType && (
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${SIM_TYPE_COLORS[run._simType] ?? SIM_TYPE_COLORS['General']}`}>
                            {run._simType}
                          </span>
                        )}
                      </TableCell>
                      <TableCell><StatusBadge status={run.status} /></TableCell>
                      <TableCell>
                        <span className="text-xs font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">{run.ap_level ?? '—'}</span>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">{formatDate(run.start_time)}</TableCell>
                      <TableCell className="text-sm">{run.cpu_hours != null ? `${run.cpu_hours.toFixed(1)}h` : '—'}</TableCell>
                      <TableCell className="text-sm">{run.mesh_elements != null ? run.mesh_elements.toLocaleString() : '—'}</TableCell>
                      <TableCell>
                        {run.credibility_level
                          ? <Badge variant="outline" className="text-xs">{run.credibility_level}</Badge>
                          : <span className="text-muted-foreground text-sm">—</span>}
                      </TableCell>
                      <TableCell className="text-sm">{run.generated_artifacts?.length ?? 0}</TableCell>
                      <TableCell onClick={(e) => { e.stopPropagation(); navigate(`/engineer/simulation/runs/${run.id}`); }}>
                        <Button variant="ghost" size="sm">
                          <Eye className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default SimulationRuns;
