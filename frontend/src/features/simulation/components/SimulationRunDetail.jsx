import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { getRun } from '@/services/simulation.service';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  AlertCircle,
  ArrowLeft,
  Activity,
  Clock,
  Cpu,
  CheckCircle2,
  XCircle,
  FileOutput,
  Zap,
  Shield,
} from 'lucide-react';
import PageHeader from '@/components/PageHeader';

const normaliseStatus = (s) => {
  if (!s) return 'Unknown';
  const lower = s.toLowerCase();
  if (lower === 'completed' || lower === 'complete') return 'Completed';
  if (lower === 'running' || lower === 'in_progress' || lower === 'in progress') return 'Running';
  if (lower === 'failed' || lower === 'error') return 'Failed';
  if (lower === 'pending' || lower === 'queued') return 'Pending';
  return s;
};

const inferSimType = (id) => {
  if (!id) return null;
  const u = id.toUpperCase();
  if (u.includes('MAXWELL') || u.includes('EM-') || u.includes('MOTOR')) return 'Electromagnetic';
  if (u.includes('CFD') || u.includes('FLUENT') || u.includes('PUMP')) return 'CFD';
  if (u.includes('STRUCT') || u.includes('CRANE') || u.includes('STATIC')) return 'Structural';
  if (u.includes('THERMAL') || u.includes('HEAT')) return 'Thermal';
  if (u.includes('NVH') || u.includes('MODAL') || u.includes('VIBR')) return 'NVH';
  if (u.startsWith('FEA-')) return 'Structural';
  return null;
};

const STATUS_CONFIG = {
  Completed: { badge: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-300', dot: 'bg-emerald-500', Icon: CheckCircle2 },
  Running:   { badge: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',     dot: 'bg-blue-500',    Icon: Activity },
  Failed:    { badge: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',         dot: 'bg-red-500',     Icon: XCircle },
  Pending:   { badge: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-300', dot: 'bg-amber-500',   Icon: Clock },
  Unknown:   { badge: 'bg-gray-100 text-gray-600',                                          dot: 'bg-gray-400',    Icon: Activity },
};

const StatusBadge = ({ status }) => {
  const canon = normaliseStatus(status);
  const cfg = STATUS_CONFIG[canon] || STATUS_CONFIG.Unknown;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${cfg.badge}`}>
      <span className={`w-2 h-2 rounded-full ${cfg.dot}`} />
      {canon}
    </span>
  );
};

export default function SimulationRunDetail() {
  const { runId } = useParams();
  const navigate = useNavigate();

  const {
    data: run,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['simulation-run', runId],
    queryFn: () => getRun(runId),
    enabled: !!runId,
  });

  const formatDuration = (start, end) => {
    if (!start) return '-';
    if (!end) return 'Running...';
    const ms = new Date(end) - new Date(start);
    const hours = ms / 1000 / 60 / 60;
    if (hours < 1) return `${(ms / 1000 / 60).toFixed(0)}m`;
    return `${hours.toFixed(1)}h`;
  };

  const formatDate = (ts) => {
    if (!ts) return '-';
    try { return new Date(ts).toLocaleString(); } catch { return ts; }
  };

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-10 w-48" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-28 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 space-y-6">
        <Button variant="ghost" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4 mr-2" /> Back
        </Button>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load simulation run: {error.message}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!run) {
    return (
      <div className="p-6 space-y-6">
        <Button variant="ghost" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4 mr-2" /> Back
        </Button>
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>Simulation run not found.</AlertDescription>
        </Alert>
      </div>
    );
  }

  const simType = run.sim_type || inferSimType(run.id);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4 mr-2" /> Back
        </Button>
        <div className="flex-1">
          <h1 className="text-3xl font-bold tracking-tight font-mono">{run.id}</h1>
          <p className="text-muted-foreground mt-1">Simulation Run Details</p>
        </div>
        <StatusBadge status={run.status} />
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Type</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold">{simType || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Duration</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold">
              {formatDuration(run.start_time, run.end_time)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Solver</CardTitle>
            <Cpu className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold truncate">{run.solver_version || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">CPU Hours</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold">{run.cpu_hours?.toFixed(2) || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Mesh</CardTitle>
            <FileOutput className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold">
              {run.mesh_elements ? run.mesh_elements.toLocaleString() : '-'}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Credibility</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold">{run.credibility_level || 'PC2'}</div>
          </CardContent>
        </Card>
      </div>

      {/* Details */}
      <Card>
        <CardHeader>
          <CardTitle>Run Information</CardTitle>
          <CardDescription>Timestamps and configuration details</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableBody>
              <TableRow>
                <TableCell className="font-medium w-48">Run ID</TableCell>
                <TableCell className="font-mono">{run.id}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell className="font-medium">Simulation Type</TableCell>
                <TableCell>{simType || '-'}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell className="font-medium">Status</TableCell>
                <TableCell><StatusBadge status={run.status} /></TableCell>
              </TableRow>
              <TableRow>
                <TableCell className="font-medium">Start Time</TableCell>
                <TableCell>{formatDate(run.start_time || run.timestamp)}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell className="font-medium">End Time</TableCell>
                <TableCell>{formatDate(run.end_time)}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell className="font-medium">Solver Version</TableCell>
                <TableCell>{run.solver_version || '-'}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell className="font-medium">Credibility Level</TableCell>
                <TableCell>
                  <Badge variant="outline">{run.credibility_level || 'PC2'}</Badge>
                </TableCell>
              </TableRow>
              <TableRow>
                <TableCell className="font-medium">Mesh Elements</TableCell>
                <TableCell>
                  {run.mesh_elements ? run.mesh_elements.toLocaleString() : '-'}
                </TableCell>
              </TableRow>
              <TableRow>
                <TableCell className="font-medium">CPU Hours</TableCell>
                <TableCell>{run.cpu_hours?.toFixed(2) || '-'}</TableCell>
              </TableRow>
              {run.convergence_tolerance && (
                <TableRow>
                  <TableCell className="font-medium">Convergence Tolerance</TableCell>
                  <TableCell>{run.convergence_tolerance}</TableCell>
                </TableRow>
              )}
              <TableRow>
                <TableCell className="font-medium">AP Level</TableCell>
                <TableCell>{run.ap_level || '-'}</TableCell>
              </TableRow>
              {run.dossier_id && (
                <TableRow>
                  <TableCell className="font-medium">Dossier</TableCell>
                  <TableCell>
                    <Button
                      variant="link"
                      className="p-0 h-auto"
                      onClick={() => navigate(`/engineer/simulation/dossiers/${run.dossier_id}`)}
                    >
                      {run.dossier_name || run.dossier_id}
                    </Button>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Generated Artifacts */}
      {run.generated_artifacts && run.generated_artifacts.filter(a => a?.id || a?.name || (typeof a === 'string')).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Generated Artifacts ({run.generated_artifacts.length})</CardTitle>
            <CardDescription>Artifacts produced by this simulation run</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {run.generated_artifacts.filter(a => a?.id || a?.name || (typeof a === 'string')).map((artifact) => (
                  <TableRow key={artifact.id || artifact}>
                    <TableCell className="font-mono text-sm">
                      {typeof artifact === 'string' ? artifact : artifact.id}
                    </TableCell>
                    <TableCell>{typeof artifact === 'object' ? artifact.name : '-'}</TableCell>
                    <TableCell>{typeof artifact === 'object' ? artifact.type : '-'}</TableCell>
                    <TableCell>
                      {typeof artifact === 'object' && artifact.status ? (
                        <Badge variant="outline">{artifact.status}</Badge>
                      ) : (
                        '-'
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
