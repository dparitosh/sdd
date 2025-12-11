import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  useReactTable,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  ColumnDef,
  flexRender,
  SortingState,
  ColumnFiltersState,
} from '@tanstack/react-table';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Plus, Pencil, Trash2, Search, Download, RefreshCw } from 'lucide-react';
import { apiService } from '@/services/api';
import { toast } from 'sonner';

// Requirement schema for validation
const requirementSchema = z.object({
  uid: z.string().min(1, 'UID is required').optional(),
  name: z.string().min(1, 'Name is required'),
  description: z.string().optional(),
  status: z.enum(['Draft', 'Approved', 'Implemented', 'Verified', 'Obsolete']).default('Draft'),
  priority: z.enum(['Low', 'Medium', 'High', 'Critical']).default('Medium'),
  category: z.string().optional(),
});

type RequirementFormData = z.infer<typeof requirementSchema>;

interface Requirement {
  uid: string;
  name: string;
  description?: string;
  status?: string;
  priority?: string;
  category?: string;
}

export default function RequirementsManager() {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [globalFilter, setGlobalFilter] = useState('');
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [selectedReq, setSelectedReq] = useState<Requirement | null>(null);

  const queryClient = useQueryClient();

  // Fetch requirements
  const { data: requirements = [], isLoading, error, refetch } = useQuery({
    queryKey: ['requirements'],
    queryFn: async () => {
      const response = await apiService.requirements.list({ limit: 1000 });
      return response.data || [];
    },
  });

  // Create requirement mutation
  const createMutation = useMutation({
    mutationFn: (data: RequirementFormData) => apiService.requirements.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['requirements'] });
      toast.success('Requirement created successfully');
      setIsCreateOpen(false);
    },
    onError: (error: any) => {
      toast.error(`Failed to create requirement: ${error.message}`);
    },
  });

  // Update requirement mutation
  const updateMutation = useMutation({
    mutationFn: ({ uid, data }: { uid: string; data: RequirementFormData }) =>
      apiService.requirements.update(uid, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['requirements'] });
      toast.success('Requirement updated successfully');
      setIsEditOpen(false);
    },
    onError: (error: any) => {
      toast.error(`Failed to update requirement: ${error.message}`);
    },
  });

  // Delete requirement mutation
  const deleteMutation = useMutation({
    mutationFn: (uid: string) => apiService.requirements.delete(uid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['requirements'] });
      toast.success('Requirement deleted successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to delete requirement: ${error.message}`);
    },
  });

  // Form for create
  const createForm = useForm<RequirementFormData>({
    resolver: zodResolver(requirementSchema),
    defaultValues: {
      name: '',
      description: '',
      status: 'Draft',
      priority: 'Medium',
      category: '',
    },
  });

  // Form for edit
  const editForm = useForm<RequirementFormData>({
    resolver: zodResolver(requirementSchema),
  });

  // Table columns
  const columns: ColumnDef<Requirement>[] = [
    {
      accessorKey: 'uid',
      header: 'UID',
      cell: ({ row }) => (
        <span className="font-mono text-sm">{row.getValue('uid')}</span>
      ),
    },
    {
      accessorKey: 'name',
      header: 'Name',
      cell: ({ row }) => (
        <div className="max-w-[300px] truncate font-medium">
          {row.getValue('name')}
        </div>
      ),
    },
    {
      accessorKey: 'description',
      header: 'Description',
      cell: ({ row }) => (
        <div className="max-w-[400px] truncate text-muted-foreground">
          {row.getValue('description') || '—'}
        </div>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => {
        const status = row.getValue('status') as string;
        const colors: Record<string, string> = {
          Draft: 'bg-gray-500',
          Approved: 'bg-blue-500',
          Implemented: 'bg-green-500',
          Verified: 'bg-purple-500',
          Obsolete: 'bg-red-500',
        };
        return (
          <Badge className={colors[status] || 'bg-gray-500'}>
            {status || 'Draft'}
          </Badge>
        );
      },
    },
    {
      accessorKey: 'priority',
      header: 'Priority',
      cell: ({ row }) => {
        const priority = row.getValue('priority') as string;
        const colors: Record<string, string> = {
          Low: 'bg-green-100 text-green-800',
          Medium: 'bg-yellow-100 text-yellow-800',
          High: 'bg-orange-100 text-orange-800',
          Critical: 'bg-red-100 text-red-800',
        };
        return (
          <Badge variant="outline" className={colors[priority] || ''}>
            {priority || 'Medium'}
          </Badge>
        );
      },
    },
    {
      accessorKey: 'category',
      header: 'Category',
      cell: ({ row }) => row.getValue('category') || '—',
    },
    {
      id: 'actions',
      cell: ({ row }) => {
        const req = row.original;
        return (
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setSelectedReq(req);
                editForm.reset(req);
                setIsEditOpen(true);
              }}
            >
              <Pencil className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                if (confirm('Are you sure you want to delete this requirement?')) {
                  deleteMutation.mutate(req.uid);
                }
              }}
            >
              <Trash2 className="h-4 w-4 text-red-500" />
            </Button>
          </div>
        );
      },
    },
  ];

  const table = useReactTable({
    data: requirements,
    columns,
    state: {
      sorting,
      columnFilters,
      globalFilter,
    },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: {
      pagination: {
        pageSize: 20,
      },
    },
  });

  const onCreateSubmit = (data: RequirementFormData) => {
    createMutation.mutate(data);
  };

  const onEditSubmit = (data: RequirementFormData) => {
    if (selectedReq) {
      updateMutation.mutate({ uid: selectedReq.uid, data });
    }
  };

  const exportToCSV = () => {
    const headers = ['UID', 'Name', 'Description', 'Status', 'Priority', 'Category'];
    const rows = requirements.map((req: Requirement) => [
      req.uid,
      req.name,
      req.description || '',
      req.status || 'Draft',
      req.priority || 'Medium',
      req.category || '',
    ]);

    const csv = [headers, ...rows].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `requirements_${new Date().toISOString()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Requirements exported to CSV');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Requirements Manager</h1>
          <p className="text-muted-foreground">
            Manage and track system requirements
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button variant="outline" onClick={exportToCSV}>
            <Download className="h-4 w-4 mr-2" />
            Export CSV
          </Button>
          <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                New Requirement
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>Create Requirement</DialogTitle>
                <DialogDescription>
                  Add a new requirement to the system
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={createForm.handleSubmit(onCreateSubmit)} className="space-y-4">
                <div>
                  <Label htmlFor="name">Name *</Label>
                  <Input id="name" {...createForm.register('name')} />
                  {createForm.formState.errors.name && (
                    <p className="text-sm text-red-500 mt-1">
                      {createForm.formState.errors.name.message}
                    </p>
                  )}
                </div>
                <div>
                  <Label htmlFor="description">Description</Label>
                  <Textarea id="description" {...createForm.register('description')} rows={3} />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="status">Status</Label>
                    <Select
                      value={createForm.watch('status')}
                      onValueChange={(value) => createForm.setValue('status', value as any)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Draft">Draft</SelectItem>
                        <SelectItem value="Approved">Approved</SelectItem>
                        <SelectItem value="Implemented">Implemented</SelectItem>
                        <SelectItem value="Verified">Verified</SelectItem>
                        <SelectItem value="Obsolete">Obsolete</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="priority">Priority</Label>
                    <Select
                      value={createForm.watch('priority')}
                      onValueChange={(value) => createForm.setValue('priority', value as any)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Low">Low</SelectItem>
                        <SelectItem value="Medium">Medium</SelectItem>
                        <SelectItem value="High">High</SelectItem>
                        <SelectItem value="Critical">Critical</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div>
                  <Label htmlFor="category">Category</Label>
                  <Input id="category" {...createForm.register('category')} />
                </div>
                <DialogFooter>
                  <Button type="button" variant="outline" onClick={() => setIsCreateOpen(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={createMutation.isPending}>
                    {createMutation.isPending ? 'Creating...' : 'Create'}
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>
            Failed to load requirements: {error instanceof Error ? error.message : typeof error === 'object' && error !== null ? JSON.stringify(error) : String(error)}
          </AlertDescription>
        </Alert>
      )}

      {/* Search and Filters */}
      <div className="flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search requirements..."
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      {/* Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
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
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  {columns.map((_, j) => (
                    <TableCell key={j}>
                      <Skeleton className="h-6 w-full" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : table.getRowModel().rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  No requirements found.
                </TableCell>
              </TableRow>
            ) : (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          Showing {table.getRowModel().rows.length} of {requirements.length} requirements
        </div>
        <div className="flex items-center gap-2">
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
        </div>
      </div>

      {/* Edit Dialog */}
      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit Requirement</DialogTitle>
            <DialogDescription>
              Update requirement details
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={editForm.handleSubmit(onEditSubmit)} className="space-y-4">
            <div>
              <Label htmlFor="edit-name">Name *</Label>
              <Input id="edit-name" {...editForm.register('name')} />
              {editForm.formState.errors.name && (
                <p className="text-sm text-red-500 mt-1">
                  {editForm.formState.errors.name.message}
                </p>
              )}
            </div>
            <div>
              <Label htmlFor="edit-description">Description</Label>
              <Textarea id="edit-description" {...editForm.register('description')} rows={3} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="edit-status">Status</Label>
                <Select
                  value={editForm.watch('status')}
                  onValueChange={(value) => editForm.setValue('status', value as any)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Draft">Draft</SelectItem>
                    <SelectItem value="Approved">Approved</SelectItem>
                    <SelectItem value="Implemented">Implemented</SelectItem>
                    <SelectItem value="Verified">Verified</SelectItem>
                    <SelectItem value="Obsolete">Obsolete</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="edit-priority">Priority</Label>
                <Select
                  value={editForm.watch('priority')}
                  onValueChange={(value) => editForm.setValue('priority', value as any)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Low">Low</SelectItem>
                    <SelectItem value="Medium">Medium</SelectItem>
                    <SelectItem value="High">High</SelectItem>
                    <SelectItem value="Critical">Critical</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label htmlFor="edit-category">Category</Label>
              <Input id="edit-category" {...editForm.register('category')} />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsEditOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? 'Saving...' : 'Save'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
