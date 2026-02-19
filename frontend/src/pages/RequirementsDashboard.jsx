import logger from '@/utils/logger';
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useReactTable, getCoreRowModel, getPaginationRowModel, getSortedRowModel, getFilteredRowModel, flexRender } from '@tanstack/react-table';
import { useDebounce } from 'use-debounce';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, CheckCircle2, Clock, FileText, GitBranch, Loader2, Search, TrendingUp, Plus, Pencil, Trash2, Download, RefreshCw } from 'lucide-react';
import ExportButton from '@/components/ExportButton';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { toast } from 'sonner';

const requirementSchema = z.object({
  uid: z.string().optional(),
  name: z.string().min(1, 'Name is required'),
  description: z.string().optional(),
  type: z.string().optional(),
  status: z.enum(['Draft', 'Approved', 'Implemented', 'Verified', 'Obsolete']).default('Draft'),
  priority: z.enum(['Low', 'Medium', 'High', 'Critical']).default('Medium'),
});

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
const RequirementsDashboard = () => {
  const queryClient = useQueryClient();
  const [selectedReq, setSelectedReq] = useState(null);
  const [typeFilter, setTypeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearchQuery] = useDebounce(searchQuery, 300);
  
  // Manager State
  const [sorting, setSorting] = useState([]);
  const [columnFilters, setColumnFilters] = useState([]);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editingReq, setEditingReq] = useState(null);

  const {
    data: requirementsData,
    isLoading: loadingRequirements,
    error: requirementsError,
    refetch: refetchRequirements
  } = useQuery({
    queryKey: ['ap239-requirements', typeFilter, statusFilter, priorityFilter, debouncedSearchQuery],
    queryFn: () => {
      const params = {};
      if (typeFilter !== 'all') params.type = typeFilter;
      if (statusFilter !== 'all') params.status = statusFilter;
      if (priorityFilter !== 'all') params.priority = priorityFilter;
      if (debouncedSearchQuery) params.search = debouncedSearchQuery;
      return apiService.ap239.getRequirements(params);
    },
    refetchInterval: 30000
  });

  const {
    data: traceabilityData,
    isLoading: loadingTraceability
  } = useQuery({
    queryKey: ['traceability-matrix'],
    queryFn: () => apiService.hierarchy.getTraceabilityMatrix(),
    refetchInterval: 60000
  });

  const {
    data: statisticsData,
    isLoading: loadingStatistics
  } = useQuery({
    queryKey: ['ap239-statistics'],
    queryFn: () => apiService.ap239.getStatistics(),
    refetchInterval: 60000
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: data => apiService.requirements.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ap239-requirements'] });
      queryClient.invalidateQueries({ queryKey: ['ap239-statistics'] });
      toast.success('Requirement created successfully');
      setIsCreateOpen(false);
      resetCreateForm();
    },
    onError: error => toast.error(`Failed to create requirement: ${getErrorMessage(error)}`)
  });

  const updateMutation = useMutation({
    mutationFn: ({ uid, data }) => apiService.requirements.update(uid, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ap239-requirements'] });
      queryClient.invalidateQueries({ queryKey: ['ap239-statistics'] });
      toast.success('Requirement updated successfully');
      setIsEditOpen(false);
      setEditingReq(null);
    },
    onError: error => toast.error(`Failed to update requirement: ${getErrorMessage(error)}`)
  });

  const deleteMutation = useMutation({
    mutationFn: uid => apiService.requirements.delete(uid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ap239-requirements'] });
      queryClient.invalidateQueries({ queryKey: ['ap239-statistics'] });
      toast.success('Requirement deleted successfully');
    },
    onError: error => toast.error(`Failed to delete requirement: ${getErrorMessage(error)}`)
  });

  const createForm = useForm({
    resolver: zodResolver(requirementSchema),
    defaultValues: {
      name: '',
      description: '',
      type: 'Functional',
      status: 'Draft',
      priority: 'Medium'
    }
  });

  const editForm = useForm({
    resolver: zodResolver(requirementSchema)
  });

  const resetCreateForm = () => {
    createForm.reset({
      name: '',
      description: '',
      type: 'Functional',
      status: 'Draft',
      priority: 'Medium'
    });
  };

  const onCreateSubmit = data => createMutation.mutate(data);
  const onEditSubmit = data => {
    if (editingReq && editingReq.uid) {
      updateMutation.mutate({ uid: editingReq.uid, data });
    } else {
        toast.error("Missing UID for update");
    }
  };

  const requirements = requirementsData?.requirements || [];
  const traceability = traceabilityData?.matrix || [];
  const statistics = statisticsData?.statistics || null;

  const getPriorityColor = priority => {
    switch (priority?.toLowerCase()) {
      case 'high': return 'destructive';
      case 'medium': return 'default';
      case 'low': return 'secondary';
      case 'critical': return 'destructive';
      default: return 'outline';
    }
  };

  const getStatusIcon = status => {
    switch (status?.toLowerCase()) {
      case 'approved': return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'draft': return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'obsolete': return <AlertCircle className="h-4 w-4 text-red-500" />;
      case 'verified': return <CheckCircle2 className="h-4 w-4 text-purple-500" />;
      case 'implemented': return <CheckCircle2 className="h-4 w-4 text-blue-500" />;
      default: return <FileText className="h-4 w-4" />;
    }
  };

  const fetchRequirementDetail = async reqId => {
    try {
      const response = await apiService.ap239.getRequirement(reqId);
      setSelectedReq(response);
    } catch (error) {
      logger.error('Error fetching requirement detail:', error);
    }
  };

  const columns = React.useMemo(() => [
    {
      accessorKey: 'id',
      header: 'ID',
      cell: ({ row }) => <span className="font-mono text-sm">{row.getValue('id') || <span className="text-red-500 text-xs italic">Missing ID</span>}</span>
    },
    {
      accessorKey: 'name',
      header: 'Name',
      cell: ({ row }) => <div className="font-medium">{row.getValue('name')}</div>
    },
    {
      accessorKey: 'type',
      header: 'Type',
      cell: ({ row }) => <Badge variant="outline">{row.getValue('type') || 'N/A'}</Badge>
    },
    {
      accessorKey: 'priority',
      header: 'Priority',
      cell: ({ row }) => <Badge variant={getPriorityColor(row.getValue('priority'))}>{row.getValue('priority') || 'N/A'}</Badge>
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => <div className="flex items-center gap-2">{getStatusIcon(row.getValue('status'))}<span>{row.getValue('status') || 'N/A'}</span></div>
    },
    {
      accessorKey: 'satisfied_by_parts',
      header: 'Satisfied By',
      cell: ({ row }) => <Badge variant="secondary">{(row.original.satisfied_by_parts?.length || 0)} parts</Badge>
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => {
        const req = row.original;
        return (
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={() => fetchRequirementDetail(req.id)}>
               <Search className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={() => {
                const formValues = {
                    uid: req.uid,
                    name: req.name, // The backend returns 'name', form uses 'name'
                    description: req.description,
                    type: req.type || 'Functional',
                    status: req.status || 'Draft',
                    priority: req.priority || 'Medium'
                };
                setEditingReq(req);
                editForm.reset(formValues);
                setIsEditOpen(true);
            }}>
              <Pencil className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={() => {
              if (req.uid && confirm('Are you sure you want to delete this requirement?')) {
                deleteMutation.mutate(req.uid);
              } else if (!req.uid) {
                  toast.error("Cannot delete: Missing UID");
              }
            }}>
              <Trash2 className="h-4 w-4 text-red-500" />
            </Button>
          </div>
        );
      }
    }
  ], [deleteMutation]);

  const table = useReactTable({
    data: requirements,
    columns,
    state: { sorting, columnFilters },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  });

  // Calculate dynamic stats from filtered requirements
  const statusData = React.useMemo(() => {
    const stats = {};
    requirements.forEach(req => {
      const status = req.status || 'Unknown';
      stats[status] = (stats[status] || 0) + 1;
    });
    return Object.entries(stats).map(([name, value]) => ({ name, value }));
  }, [requirements]);

  const priorityData = React.useMemo(() => {
    const stats = {};
    requirements.forEach(req => {
      const priority = req.priority || 'Unknown';
      stats[priority] = (stats[priority] || 0) + 1;
    });
    return Object.entries(stats).map(([name, value]) => ({ name, value }));
  }, [requirements]);

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#888888'];


  const isLoading = loadingRequirements || loadingTraceability || loadingStatistics;
  if (isLoading && !requirementsData) {
    return <div className="flex items-center justify-center h-screen"><Loader2 className="h-8 w-8 animate-spin" /></div>;
  }
  return <div className="container mx-auto p-6 space-y-6"><div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Requirements Dashboard</h1>
          <p className="text-muted-foreground">AP239 Product Life Cycle Support - Requirements Management</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => setIsCreateOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            New Requirement
          </Button>
          <Button variant="outline" onClick={() => refetchRequirements()} disabled={isLoading}>
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <RefreshCw className="h-4 w-4 mr-2" />}
            Refresh
          </Button>
        </div>
      </div>{requirementsError && <Alert variant="destructive"><AlertCircle className="h-4 w-4" /><AlertDescription>Failed to load requirements: {requirementsError instanceof Error ? requirementsError.message : 'Unknown error'}</AlertDescription></Alert>}{loadingStatistics ? <div className="grid grid-cols-1 md:grid-cols-4 gap-4">{[1, 2, 3, 4].map(i => <Card key={i}><CardHeader className="pb-2"><Skeleton className="h-4 w-32" /></CardHeader><CardContent><Skeleton className="h-8 w-16" /></CardContent></Card>)}</div> : statistics ? <div className="grid grid-cols-1 md:grid-cols-4 gap-4"><Card><CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2"><CardTitle className="text-sm font-medium">Total Requirements</CardTitle><FileText className="h-4 w-4 text-muted-foreground" /></CardHeader><CardContent><div className="text-2xl font-bold">{statistics.Requirement?.total || 0}</div></CardContent></Card><Card><CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2"><CardTitle className="text-sm font-medium">Approved</CardTitle><CheckCircle2 className="h-4 w-4 text-green-500" /></CardHeader><CardContent><div className="text-2xl font-bold">{statistics.Requirement?.by_status?.Approved || 0}</div></CardContent></Card><Card><CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2"><CardTitle className="text-sm font-medium">Analyses</CardTitle><TrendingUp className="h-4 w-4 text-blue-500" /></CardHeader><CardContent><div className="text-2xl font-bold">{statistics.Analysis?.total || 0}</div></CardContent></Card><Card><CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2"><CardTitle className="text-sm font-medium">Traceability Coverage</CardTitle><GitBranch className="h-4 w-4 text-purple-500" /></CardHeader><CardContent><div className="text-2xl font-bold">{traceability && traceability.length > 0 ? Math.round(traceability.filter(m => m.traceability.length > 0).length / traceability.length * 100) : 0}%</div></CardContent></Card></div> : null}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Requirement Status (Filtered)</CardTitle>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={statusData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Legend />
                <Bar dataKey="value" name="Count" fill="#8884d8" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Priority Distribution (Filtered)</CardTitle>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={priorityData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {priorityData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div><Card><CardHeader className="flex flex-row items-center justify-between"><CardTitle>Filters</CardTitle><ExportButton entityType="requirements" filters={{
          type: typeFilter,
          status: statusFilter,
          priority: priorityFilter,
          search: debouncedSearchQuery
        }} /></CardHeader><CardContent><div className="grid grid-cols-1 md:grid-cols-4 gap-4"><div className="relative"><Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" /><Input placeholder="Search requirements..." value={searchQuery} onChange={e => setSearchQuery(e.target.value)} className="pl-8" /></div><Select value={typeFilter} onValueChange={setTypeFilter}><SelectTrigger><SelectValue placeholder="Type" /></SelectTrigger><SelectContent><SelectItem value="all">All Types</SelectItem><SelectItem value="Performance">Performance</SelectItem><SelectItem value="Functional">Functional</SelectItem><SelectItem value="Safety">Safety</SelectItem><SelectItem value="Interface">Interface</SelectItem></SelectContent></Select><Select value={statusFilter} onValueChange={setStatusFilter}><SelectTrigger><SelectValue placeholder="Status" /></SelectTrigger><SelectContent><SelectItem value="all">All Statuses</SelectItem><SelectItem value="Draft">Draft</SelectItem><SelectItem value="Approved">Approved</SelectItem><SelectItem value="Implemented">Implemented</SelectItem><SelectItem value="Verified">Verified</SelectItem><SelectItem value="Obsolete">Obsolete</SelectItem></SelectContent></Select><Select value={priorityFilter} onValueChange={setPriorityFilter}><SelectTrigger><SelectValue placeholder="Priority" /></SelectTrigger><SelectContent><SelectItem value="all">All Priorities</SelectItem><SelectItem value="Critical">Critical</SelectItem><SelectItem value="High">High</SelectItem><SelectItem value="Medium">Medium</SelectItem><SelectItem value="Low">Low</SelectItem></SelectContent></Select></div></CardContent></Card><Tabs defaultValue="requirements" className="w-full"><TabsList><TabsTrigger value="requirements">Requirements List</TabsTrigger><TabsTrigger value="traceability">Traceability Matrix</TabsTrigger></TabsList><TabsContent value="requirements"><Card><CardHeader><CardTitle>Requirements ({requirements.length})</CardTitle></CardHeader><CardContent>{loadingRequirements ? <div className="space-y-2">{[1, 2, 3, 4, 5].map(i => <Skeleton key={i} className="h-12 w-full" />)}</div> : requirements.length === 0 ? <div className="text-center py-8 text-muted-foreground">No requirements found. Try adjusting your filters.</div> : <><div className="rounded-md border">
                    <Table>
                      <TableHeader>
                        {table.getHeaderGroups().map(headerGroup => (
                          <TableRow key={headerGroup.id}>
                            {headerGroup.headers.map(header => (
                              <TableHead key={header.id}>
                                {header.isPlaceholder
                                  ? null
                                  : flexRender(
                                      header.column.columnDef.header,
                                      header.getContext()
                                    )}
                              </TableHead>
                            ))}
                          </TableRow>
                        ))}
                      </TableHeader>
                      <TableBody>
                        {table.getRowModel().rows?.length ? (
                          table.getRowModel().rows.map(row => (
                            <TableRow
                              key={row.id}
                              data-state={row.getIsSelected() && "selected"}
                            >
                              {row.getVisibleCells().map(cell => (
                                <TableCell key={cell.id}>
                                  {flexRender(
                                    cell.column.columnDef.cell,
                                    cell.getContext()
                                  )}
                                </TableCell>
                              ))}
                            </TableRow>
                          ))
                        ) : (
                          <TableRow>
                            <TableCell
                              colSpan={columns.length}
                              className="h-24 text-center"
                            >
                              No results.
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </div>
                  <div className="flex items-center justify-end space-x-2 py-4">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => table.previousPage()}
                      disabled={!table.getCanPreviousPage()}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => table.nextPage()}
                      disabled={!table.getCanNextPage()}
                    >
                      Next
                    </Button>
                  </div></>}</CardContent></Card></TabsContent><TabsContent value="traceability"><Card><CardHeader><CardTitle>Traceability Matrix</CardTitle><p className="text-sm text-muted-foreground">Complete traceability from requirements through parts to ontologies</p></CardHeader><CardContent>{loadingTraceability ? <div className="space-y-4">{[1, 2, 3].map(i => <Card key={i}><CardHeader><Skeleton className="h-6 w-64" /><Skeleton className="h-4 w-32" /></CardHeader><CardContent><Skeleton className="h-20 w-full" /></CardContent></Card>)}</div> : traceability && traceability.length > 0 ? <div className="space-y-4">{traceability.map((entry, idx) => <Card key={entry.requirement.id || idx}><CardHeader><div className="flex items-center justify-between"><div><CardTitle className="text-base">{entry.requirement.name}</CardTitle><p className="text-sm text-muted-foreground">{entry.requirement.id}</p></div><div className="flex gap-2"><Badge>{entry.requirement.type}</Badge><Badge variant="outline">{entry.requirement.status}</Badge></div></div></CardHeader><CardContent>{entry.traceability.length > 0 ? <div className="space-y-2">{entry.traceability.map((trace, traceIdx) => <div key={traceIdx} className="flex items-center gap-4 p-3 bg-muted rounded-lg"><GitBranch className="h-4 w-4 text-muted-foreground" /><div className="flex-1"><div className="font-medium">{trace.part_name}</div>{trace.materials && trace.materials.length > 0 && <div className="text-sm text-muted-foreground">Materials: {trace.materials.join(', ')}</div>}{trace.ontologies && trace.ontologies.length > 0 && <div className="text-sm text-muted-foreground">Ontologies: {trace.ontologies.join(', ')}</div>}</div></div>)}</div> : <div className="text-center py-4 text-muted-foreground">No traceability data available</div>}</CardContent></Card>)}</div> : <div className="text-center py-8 text-muted-foreground">No traceability data available</div>}</CardContent></Card></TabsContent></Tabs>

      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Requirement</DialogTitle>
          </DialogHeader>
          <Form {...createForm}>
            <form onSubmit={createForm.handleSubmit((data) => createMutation.mutate(data))} className="space-y-4">
              <FormField
                control={createForm.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name</FormLabel>
                    <FormControl><Input {...field} /></FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={createForm.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description</FormLabel>
                    <FormControl><Textarea {...field} /></FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="grid grid-cols-3 gap-4">
                  <FormField
                    control={createForm.control}
                    name="type"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Type</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                            <FormControl><SelectTrigger><SelectValue /></SelectTrigger></FormControl>
                            <SelectContent>
                                <SelectItem value="Functional">Functional</SelectItem>
                                <SelectItem value="Performance">Performance</SelectItem>
                                <SelectItem value="Safety">Safety</SelectItem>
                                <SelectItem value="Interface">Interface</SelectItem>
                            </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={createForm.control}
                    name="priority"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Priority</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                            <FormControl><SelectTrigger><SelectValue /></SelectTrigger></FormControl>
                            <SelectContent>
                                <SelectItem value="Low">Low</SelectItem>
                                <SelectItem value="Medium">Medium</SelectItem>
                                <SelectItem value="High">High</SelectItem>
                                <SelectItem value="Critical">Critical</SelectItem>                                <SelectItem value="Critical">Critical</SelectItem>                            </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={createForm.control}
                    name="status"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Status</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                            <FormControl><SelectTrigger><SelectValue /></SelectTrigger></FormControl>
                            <SelectContent>
                                <SelectItem value="Draft">Draft</SelectItem>
                                <SelectItem value="Approved">Approved</SelectItem>
                                <SelectItem value="Implemented">Implemented</SelectItem>
                                <SelectItem value="Verified">Verified</SelectItem>
                                <SelectItem value="Obsolete">Obsolete</SelectItem>
                            </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
              </div>
              <Button type="submit">Create</Button>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Requirement</DialogTitle>
          </DialogHeader>
          <Form {...editForm}>
            <form onSubmit={editForm.handleSubmit((data) => updateMutation.mutate({ uid: editingReq?.uid, data }))} className="space-y-4">
              <FormField
                control={editForm.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name</FormLabel>
                    <FormControl><Input {...field} /></FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={editForm.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description</FormLabel>
                    <FormControl><Textarea {...field} /></FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
               <div className="grid grid-cols-3 gap-4">
                  <FormField
                    control={editForm.control}
                    name="type"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Type</FormLabel>
                         <Select onValueChange={field.onChange} defaultValue={field.value}>
                            <FormControl><SelectTrigger><SelectValue /></SelectTrigger></FormControl>
                            <SelectContent>
                                <SelectItem value="Functional">Functional</SelectItem>
                                <SelectItem value="Performance">Performance</SelectItem>
                                <SelectItem value="Safety">Safety</SelectItem>
                                <SelectItem value="Interface">Interface</SelectItem>
                            </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={editForm.control}
                    name="priority"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Priority</FormLabel>
                         <Select onValueChange={field.onChange} defaultValue={field.value}>
                            <FormControl><SelectTrigger><SelectValue /></SelectTrigger></FormControl>
                            <SelectContent>
                                <SelectItem value="Low">Low</SelectItem>
                                <SelectItem value="Medium">Medium</SelectItem>
                                <SelectItem value="High">High</SelectItem>
                                <SelectItem value="Critical">Critical</SelectItem>                                <SelectItem value="Critical">Critical</SelectItem>                            </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={editForm.control}
                    name="status"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Status</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                            <FormControl><SelectTrigger><SelectValue /></SelectTrigger></FormControl>
                            <SelectContent>
                                <SelectItem value="Draft">Draft</SelectItem>
                                <SelectItem value="Approved">Approved</SelectItem>
                                <SelectItem value="Implemented">Implemented</SelectItem>
                                <SelectItem value="Verified">Verified</SelectItem>
                                <SelectItem value="Obsolete">Obsolete</SelectItem>
                            </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
              </div>
              <Button type="submit">Update</Button>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

{selectedReq && <Card className="fixed right-4 top-20 w-96 max-h-[80vh] overflow-y-auto shadow-lg z-50"><CardHeader><div className="flex justify-between items-start"><div><CardTitle>{selectedReq.name}</CardTitle><p className="text-sm text-muted-foreground">{selectedReq.id}</p></div><Button variant="ghost" size="sm" onClick={() => setSelectedReq(null)}>✕</Button></div></CardHeader><CardContent className="space-y-4"><div><h4 className="font-semibold mb-2">Description</h4><p className="text-sm text-muted-foreground">{selectedReq.description || 'No description available'}</p></div>{selectedReq.versions && selectedReq.versions.length > 0 && <div><h4 className="font-semibold mb-2">Versions</h4><div className="space-y-1">{selectedReq.versions.map((v, idx) => <div key={idx} className="text-sm">{v.version} - {v.name} ({v.status})</div>)}</div></div>}{selectedReq.analyses && selectedReq.analyses.length > 0 && <div><h4 className="font-semibold mb-2">Analyses</h4><div className="space-y-1">{selectedReq.analyses.map((a, idx) => <Badge key={idx} variant="outline" className="mr-1">{a.name}</Badge>)}</div></div>}{selectedReq.approvals && selectedReq.approvals.length > 0 && <div><h4 className="font-semibold mb-2">Approvals</h4><div className="space-y-1">{selectedReq.approvals.map((a, idx) => <div key={idx} className="text-sm flex items-center gap-2">{getStatusIcon(a.status)}{a.name}</div>)}</div></div>}</CardContent></Card>}</div>;
};
export default RequirementsDashboard;
