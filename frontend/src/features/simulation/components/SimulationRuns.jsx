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
  Plus, 
  Eye,
  Activity,
  Zap,
  Clock,
  CheckCircle2
} from 'lucide-react';
import logger from '@/utils/logger';

const STATUS_COLORS = {
  'Running': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
  'Complete': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  'Failed': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
};

const SIMULATION_TYPE_COLORS = {
  'Electromagnetic': 'bg-purple-100 text-purple-800',
  'Thermal': 'bg-orange-100 text-orange-800',
  'NVH': 'bg-blue-100 text-blue-800',
  'Structural': 'bg-gray-100 text-gray-800',
  'CFD': 'bg-cyan-100 text-cyan-800',
};

const SimulationRuns = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [simTypeFilter, setSimTypeFilter] = useState('all');
  const [debouncedSearchQuery] = useDebounce(searchQuery, 300);

  // Fetch simulation runs
  const {
    data: runs,
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

  const filteredRuns = (runs || []).filter(r => 
    !debouncedSearchQuery || 
    r.id?.toLowerCase().includes(debouncedSearchQuery.toLowerCase()) ||
    r.sim_type?.toLowerCase().includes(debouncedSearchQuery.toLowerCase()) ||
    r.solver_version?.toLowerCase().includes(debouncedSearchQuery.toLowerCase())
  );

  const formatDuration = (start, end) => {
    if (!start) return '-';
    if (!end) return 'Running...';
    
    const startTime = new Date(start);
    const endTime = new Date(end);
    const duration = (endTime - startTime) / 1000 / 60 / 60; // hours
    return `${duration.toFixed(1)}h`;
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Simulation Runs</h1>
          <p className="text-muted-foreground mt-1">
            Track and analyze AP243 simulation executions
          </p>
        </div>
        <Button onClick={() => navigate('/simulation/runs/create')}>
          <Plus className="h-4 w-4 mr-2" />
          Create Run
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Runs</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{runs?.length || 0}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Running</CardTitle>
            <Activity className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {runs?.filter(r => r.status === 'Running').length || 0}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completed</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {runs?.filter(r => r.status === 'Complete').length || 0}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg CPU Time</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {runs && runs.length > 0
                ? (runs.reduce((sum, r) => sum + (r.cpu_hours || 0), 0) / runs.length).toFixed(1) 
                : '0'}h
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by ID, type, or solver..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8"
                />
              </div>
            </div>
            <div className="w-48">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
              >
                <option value="all">All Statuses</option>
                <option value="Running">Running</option>
                <option value="Complete">Complete</option>
                <option value="Failed">Failed</option>
              </select>
            </div>
            <div className="w-48">
              <select
                value={simTypeFilter}
                onChange={(e) => setSimTypeFilter(e.target.value)}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
              >
                <option value="all">All Types</option>
                <option value="Electromagnetic">Electromagnetic</option>
                <option value="Thermal">Thermal</option>
                <option value="NVH">NVH</option>
                <option value="Structural">Structural</option>
                <option value="CFD">CFD</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Runs Table */}
      <Card>
        <CardHeader>
          <CardTitle>Simulation Runs ({filteredRuns.length})</CardTitle>
          <CardDescription>
            View and manage simulation executions
          </CardDescription>
        </CardHeader>
        <CardContent>
          {runsError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Failed to load runs: {runsError.message}
              </AlertDescription>
            </Alert>
          )}

          {loadingRuns ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Run ID</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Start Time</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Solver</TableHead>
                  <TableHead>Credibility</TableHead>
                  <TableHead>CPU Hours</TableHead>
                  <TableHead>Artifacts</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredRuns.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={10} className="text-center text-muted-foreground">
                      No simulation runs found
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredRuns.map((run) => (
                    <TableRow key={run.id}>
                      <TableCell className="font-mono text-sm">{run.id}</TableCell>
                      <TableCell>
                        <Badge className={SIMULATION_TYPE_COLORS[run.sim_type] || 'bg-gray-100'}>
                          {run.sim_type}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm">
                        {run.start_time ? new Date(run.start_time).toLocaleString() : '-'}
                      </TableCell>
                      <TableCell className="text-sm">
                        {formatDuration(run.start_time, run.end_time)}
                      </TableCell>
                      <TableCell>
                        <Badge className={STATUS_COLORS[run.status] || 'bg-gray-100'}>
                          {run.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {run.solver_version || '-'}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{run.credibility_level || 'PC2'}</Badge>
                      </TableCell>
                      <TableCell className="text-sm">
                        {run.cpu_hours?.toFixed(2) || '-'}
                      </TableCell>
                      <TableCell className="text-sm">
                        {run.generated_artifacts?.length || 0}
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => navigate(`/engineer/simulation/runs/${run.id}`)}
                        >
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
