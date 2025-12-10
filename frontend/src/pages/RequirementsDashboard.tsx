import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useDebounce } from 'use-debounce';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, CheckCircle2, Clock, FileText, GitBranch, Loader2, Search, TrendingUp } from 'lucide-react';
import { AP239Requirement, TraceabilityMatrix, AP239Statistics } from '@/types/api';
import ExportButton from '@/components/ExportButton';

const RequirementsDashboard: React.FC = () => {
  const [selectedReq, setSelectedReq] = useState<AP239Requirement | null>(null);
  
  // Filters
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  
  // Debounce search query to prevent excessive API calls
  const [debouncedSearchQuery] = useDebounce(searchQuery, 300);

  // Fetch requirements using React Query
  const { data: requirementsData, isLoading: loadingRequirements, error: requirementsError, refetch: refetchRequirements } = useQuery({
    queryKey: ['ap239-requirements', typeFilter, statusFilter, priorityFilter, debouncedSearchQuery],
    queryFn: () => {
      const params: any = {};
      if (typeFilter !== 'all') params.type = typeFilter;
      if (statusFilter !== 'all') params.status = statusFilter;
      if (priorityFilter !== 'all') params.priority = priorityFilter;
      if (debouncedSearchQuery) params.search = debouncedSearchQuery;
      return apiService.ap239.getRequirements(params);
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Fetch traceability matrix
  const { data: traceabilityData, isLoading: loadingTraceability } = useQuery({
    queryKey: ['traceability-matrix'],
    queryFn: () => apiService.hierarchy.getTraceabilityMatrix(),
    refetchInterval: 60000, // Refresh every minute
  });

  // Fetch statistics
  const { data: statisticsData, isLoading: loadingStatistics } = useQuery({
    queryKey: ['ap239-statistics'],
    queryFn: () => apiService.ap239.getStatistics(),
    refetchInterval: 60000,
  });

  const requirements = requirementsData?.requirements || [];
  const traceability = traceabilityData?.matrix || [];
  const statistics = statisticsData?.statistics || null;

  const fetchRequirementDetail = async (reqId: string) => {
    try {
      const response = await apiService.ap239.getRequirement(reqId);
      setSelectedReq(response.requirement);
    } catch (error) {
      console.error('Error fetching requirement detail:', error);
    }
  };

  const getPriorityColor = (priority?: string) => {
    switch (priority?.toLowerCase()) {
      case 'high':
        return 'destructive';
      case 'medium':
        return 'default';
      case 'low':
        return 'secondary';
      default:
        return 'outline';
    }
  };

  const getStatusIcon = (status?: string) => {
    switch (status?.toLowerCase()) {
      case 'approved':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'draft':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'obsolete':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return <FileText className="h-4 w-4" />;
    }
  };

  const isLoading = loadingRequirements || loadingTraceability || loadingStatistics;

  if (isLoading && !requirementsData) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Requirements Dashboard</h1>
          <p className="text-muted-foreground">AP239 Product Life Cycle Support - Requirements Management</p>
        </div>
        <Button variant="outline" onClick={() => refetchRequirements()} disabled={isLoading}>
          {isLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
          Refresh
        </Button>
      </div>

      {/* Error Alert */}
      {requirementsError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load requirements: {requirementsError instanceof Error ? requirementsError.message : 'Unknown error'}
          </AlertDescription>
        </Alert>
      )}

      {/* Statistics Cards */}
      {loadingStatistics ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardHeader className="pb-2">
                <Skeleton className="h-4 w-32" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-16" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : statistics ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Requirements</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {statistics.Requirement?.total || 0}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Approved</CardTitle>
              <CheckCircle2 className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {statistics.Requirement?.by_status?.Approved || 0}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Analyses</CardTitle>
              <TrendingUp className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {statistics.Analysis?.total || 0}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Traceability Coverage</CardTitle>
              <GitBranch className="h-4 w-4 text-purple-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {traceability && traceability.length > 0
                  ? Math.round((traceability.filter(m => m.traceability.length > 0).length / traceability.length) * 100)
                  : 0}%
              </div>
            </CardContent>
          </Card>
        </div>
      ) : null}

      {/* Filters Section */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Filters</CardTitle>
          <ExportButton 
            entityType="requirements"
            filters={{
              type: typeFilter,
              status: statusFilter,
              priority: priorityFilter,
              search: debouncedSearchQuery
            }}
          />
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="relative">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search requirements..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8"
              />
            </div>

            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger>
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="Performance">Performance</SelectItem>
                <SelectItem value="Functional">Functional</SelectItem>
                <SelectItem value="Safety">Safety</SelectItem>
                <SelectItem value="Interface">Interface</SelectItem>
              </SelectContent>
            </Select>

            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger>
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="Draft">Draft</SelectItem>
                <SelectItem value="Approved">Approved</SelectItem>
                <SelectItem value="Obsolete">Obsolete</SelectItem>
              </SelectContent>
            </Select>

            <Select value={priorityFilter} onValueChange={setPriorityFilter}>
              <SelectTrigger>
                <SelectValue placeholder="Priority" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Priorities</SelectItem>
                <SelectItem value="High">High</SelectItem>
                <SelectItem value="Medium">Medium</SelectItem>
                <SelectItem value="Low">Low</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Main Content */}
      <Tabs defaultValue="requirements" className="w-full">
        <TabsList>
          <TabsTrigger value="requirements">Requirements List</TabsTrigger>
          <TabsTrigger value="traceability">Traceability Matrix</TabsTrigger>
        </TabsList>

        <TabsContent value="requirements">
          <Card>
            <CardHeader>
              <CardTitle>Requirements ({requirements.length})</CardTitle>
            </CardHeader>
            <CardContent>
              {loadingRequirements ? (
                <div className="space-y-2">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : requirements.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No requirements found. Try adjusting your filters.
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Priority</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Satisfied By</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {requirements.map((req) => (
                      <TableRow key={req.name || req.id}>
                        <TableCell className="font-mono text-sm">{req.name || req.id}</TableCell>
                        <TableCell className="font-medium">{req.description || req.name}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{req.type || 'N/A'}</Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant={getPriorityColor(req.priority)}>
                            {req.priority || 'N/A'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getStatusIcon(req.status)}
                            <span>{req.status || 'N/A'}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">
                            {req.satisfied_by_parts?.length || 0} parts
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => fetchRequirementDetail(req.name || req.id)}
                          >
                            View Details
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="traceability">
          <Card>
            <CardHeader>
              <CardTitle>Traceability Matrix</CardTitle>
              <p className="text-sm text-muted-foreground">
                Complete traceability from requirements through parts to ontologies
              </p>
            </CardHeader>
            <CardContent>
              {loadingTraceability ? (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <Card key={i}>
                      <CardHeader>
                        <Skeleton className="h-6 w-64" />
                        <Skeleton className="h-4 w-32" />
                      </CardHeader>
                      <CardContent>
                        <Skeleton className="h-20 w-full" />
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : traceability && traceability.length > 0 ? (
                <div className="space-y-4">
                  {traceability.map((entry, idx) => (
                    <Card key={idx}>
                      <CardHeader>
                        <div className="flex items-center justify-between">
                          <div>
                            <CardTitle className="text-base">
                              {entry.requirement.name}
                            </CardTitle>
                            <p className="text-sm text-muted-foreground">
                              {entry.requirement.id}
                            </p>
                          </div>
                          <div className="flex gap-2">
                            <Badge>{entry.requirement.type}</Badge>
                            <Badge variant="outline">{entry.requirement.status}</Badge>
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent>
                        {entry.traceability.length > 0 ? (
                          <div className="space-y-2">
                            {entry.traceability.map((trace, traceIdx) => (
                              <div key={traceIdx} className="flex items-center gap-4 p-3 bg-muted rounded-lg">
                                <GitBranch className="h-4 w-4 text-muted-foreground" />
                                <div className="flex-1">
                                  <div className="font-medium">{trace.part_name}</div>
                                  {trace.materials && trace.materials.length > 0 && (
                                    <div className="text-sm text-muted-foreground">
                                      Materials: {trace.materials.join(', ')}
                                    </div>
                                  )}
                                  {trace.ontologies && trace.ontologies.length > 0 && (
                                    <div className="text-sm text-muted-foreground">
                                      Ontologies: {trace.ontologies.join(', ')}
                                    </div>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-center py-4 text-muted-foreground">
                            No traceability data available
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  No traceability data available
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Requirement Detail Modal */}
      {selectedReq && (
        <Card className="fixed right-4 top-20 w-96 max-h-[80vh] overflow-y-auto shadow-lg z-50">
          <CardHeader>
            <div className="flex justify-between items-start">
              <div>
                <CardTitle>{selectedReq.name}</CardTitle>
                <p className="text-sm text-muted-foreground">{selectedReq.id}</p>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setSelectedReq(null)}>
                ✕
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h4 className="font-semibold mb-2">Description</h4>
              <p className="text-sm text-muted-foreground">
                {selectedReq.description || 'No description available'}
              </p>
            </div>

            {selectedReq.versions && selectedReq.versions.length > 0 && (
              <div>
                <h4 className="font-semibold mb-2">Versions</h4>
                <div className="space-y-1">
                  {selectedReq.versions.map((v, idx) => (
                    <div key={idx} className="text-sm">
                      {v.version} - {v.name} ({v.status})
                    </div>
                  ))}
                </div>
              </div>
            )}

            {selectedReq.analyses && selectedReq.analyses.length > 0 && (
              <div>
                <h4 className="font-semibold mb-2">Analyses</h4>
                <div className="space-y-1">
                  {selectedReq.analyses.map((a, idx) => (
                    <Badge key={idx} variant="outline" className="mr-1">
                      {a.name}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {selectedReq.approvals && selectedReq.approvals.length > 0 && (
              <div>
                <h4 className="font-semibold mb-2">Approvals</h4>
                <div className="space-y-1">
                  {selectedReq.approvals.map((a, idx) => (
                    <div key={idx} className="text-sm flex items-center gap-2">
                      {getStatusIcon(a.status)}
                      {a.name}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default RequirementsDashboard;
