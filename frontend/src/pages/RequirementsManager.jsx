import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import {
  useReactTable,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  getFilteredRowModel,

  flexRender } from


'@tanstack/react-table';
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
  DialogTrigger } from
'@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow } from
'@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue } from
'@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Plus, Pencil, Trash2, Search, Download, RefreshCw, FileText } from 'lucide-react';
import { apiService } from '@/services/api';
import PageHeader from '@/components/PageHeader';
import { toast } from 'sonner';

// Requirement schema for validation
import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";const requirementSchema = z.object({
  uid: z.string().min(1, 'UID is required').optional(),
  name: z.string().min(1, 'Name is required'),
  description: z.string().optional(),
  status: z.enum(['Draft', 'Approved', 'Implemented', 'Verified', 'Obsolete']).default('Draft'),
  priority: z.enum(['Low', 'Medium', 'High', 'Critical']).default('Medium'),
  category: z.string().optional()
});












// Helper to extract error message from various error types
const getErrorMessage = (error) => {
  if (error instanceof Error) return error.message;
  if (typeof error === 'string') return error;
  if (error?.response?.data?.error) {
    const err = error.response.data.error;
    return typeof err === 'string' ? err : err?.message || 'An error occurred';
  }
  if (error?.message) return error.message;
  return 'An unknown error occurred';
};

export default function RequirementsManager() {
  const [sorting, setSorting] = useState([]);
  const [columnFilters, setColumnFilters] = useState([]);
  const [globalFilter, setGlobalFilter] = useState('');
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [selectedReq, setSelectedReq] = useState(null);

  const queryClient = useQueryClient();

  // Fetch requirements
  const { data: requirements = [], isLoading, error, refetch } = useQuery({
    queryKey: ['requirements'],
    queryFn: async () => {
      const response = await apiService.requirements.list({ limit: 1000 });
      return response.data || [];
    }
  });

  // Create requirement mutation
  const createMutation = useMutation({
    mutationFn: (data) => apiService.requirements.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['requirements'] });
      toast.success('Requirement created successfully');
      setIsCreateOpen(false);
    },
    onError: (error) => {
      toast.error(`Failed to create requirement: ${getErrorMessage(error)}`);
    }
  });

  // Update requirement mutation
  const updateMutation = useMutation({
    mutationFn: ({ uid, data }) =>
    apiService.requirements.update(uid, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['requirements'] });
      toast.success('Requirement updated successfully');
      setIsEditOpen(false);
    },
    onError: (error) => {
      toast.error(`Failed to update requirement: ${getErrorMessage(error)}`);
    }
  });

  // Delete requirement mutation
  const deleteMutation = useMutation({
    mutationFn: (uid) => apiService.requirements.delete(uid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['requirements'] });
      toast.success('Requirement deleted successfully');
    },
    onError: (error) => {
      toast.error(`Failed to delete requirement: ${getErrorMessage(error)}`);
    }
  });

  // Form for create
  const createForm = useForm({
    resolver: zodResolver(requirementSchema),
    defaultValues: {
      name: '',
      description: '',
      status: 'Draft',
      priority: 'Medium',
      category: ''
    }
  });

  // Form for edit
  const editForm = useForm({
    resolver: zodResolver(requirementSchema)
  });

  // Table columns
  const columns = [
  {
    accessorKey: 'uid',
    header: 'UID',
    cell: ({ row }) => /*#__PURE__*/
    _jsx("span", { className: "font-mono text-sm", children: row.getValue('uid') })

  },
  {
    accessorKey: 'name',
    header: 'Name',
    cell: ({ row }) => /*#__PURE__*/
    _jsx("div", { className: "max-w-[300px] truncate font-medium", children:
      row.getValue('name') }
    )

  },
  {
    accessorKey: 'description',
    header: 'Description',
    cell: ({ row }) => /*#__PURE__*/
    _jsx("div", { className: "max-w-[400px] truncate text-muted-foreground", children:
      row.getValue('description') || '—' }
    )

  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => {
      const status = row.getValue('status');
      const colors = {
        Draft: 'bg-gray-500',
        Approved: 'bg-blue-500',
        Implemented: 'bg-green-500',
        Verified: 'bg-purple-500',
        Obsolete: 'bg-red-500'
      };
      return (/*#__PURE__*/
        _jsx(Badge, { className: colors[status] || 'bg-gray-500', children:
          status || 'Draft' }
        ));

    }
  },
  {
    accessorKey: 'priority',
    header: 'Priority',
    cell: ({ row }) => {
      const priority = row.getValue('priority');
      const colors = {
        Low: 'bg-green-100 text-green-800',
        Medium: 'bg-yellow-100 text-yellow-800',
        High: 'bg-orange-100 text-orange-800',
        Critical: 'bg-red-100 text-red-800'
      };
      return (/*#__PURE__*/
        _jsx(Badge, { variant: "outline", className: colors[priority] || '', children:
          priority || 'Medium' }
        ));

    }
  },
  {
    accessorKey: 'category',
    header: 'Category',
    cell: ({ row }) => row.getValue('category') || '—'
  },
  {
    id: 'actions',
    cell: ({ row }) => {
      const req = row.original;
      return (/*#__PURE__*/
        _jsxs("div", { className: "flex gap-2", children: [/*#__PURE__*/
          _jsx(Button, {
            variant: "ghost",
            size: "sm",
            onClick: () => {
              setSelectedReq(req);
              editForm.reset(req);
              setIsEditOpen(true);
            }, children: /*#__PURE__*/

            _jsx(Pencil, { className: "h-4 w-4" }) }
          ), /*#__PURE__*/
          _jsx(Button, {
            variant: "ghost",
            size: "sm",
            onClick: () => {
              if (confirm('Are you sure you want to delete this requirement?')) {
                deleteMutation.mutate(req.uid);
              }
            }, children: /*#__PURE__*/

            _jsx(Trash2, { className: "h-4 w-4 text-red-500" }) }
          )] }
        ));

    }
  }];


  const table = useReactTable({
    data: requirements,
    columns,
    state: {
      sorting,
      columnFilters,
      globalFilter
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
        pageSize: 20
      }
    }
  });

  const onCreateSubmit = (data) => {
    createMutation.mutate(data);
  };

  const onEditSubmit = (data) => {
    if (selectedReq) {
      updateMutation.mutate({ uid: selectedReq.uid, data });
    }
  };

  const exportToCSV = () => {
    const headers = ['UID', 'Name', 'Description', 'Status', 'Priority', 'Category'];
    const rows = requirements.map((req) => [
    req.uid,
    req.name,
    req.description || '',
    req.status || 'Draft',
    req.priority || 'Medium',
    req.category || '']
    );

    const csv = [headers, ...rows].map((row) => row.map((cell) => `"${cell}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `requirements_${new Date().toISOString()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Requirements exported to CSV');
  };

  return (/*#__PURE__*/
    _jsxs("div", { className: "container mx-auto p-6 space-y-6", children: [/*#__PURE__*/
      _jsx(PageHeader, {
        title: "Requirements Manager",
        description: "Manage and track system requirements",
        icon: /*#__PURE__*/_jsx(FileText, { className: "h-6 w-6 text-primary" }),
        breadcrumbs: [
        { label: 'Knowledge Graph', href: '/graph' },
        { label: 'Requirements' }],

        actions: /*#__PURE__*/
        _jsxs("div", { className: "flex gap-2", children: [/*#__PURE__*/
          _jsxs(Button, { variant: "outline", onClick: () => refetch(), children: [/*#__PURE__*/
            _jsx(RefreshCw, { className: "h-4 w-4 mr-2" }), "Refresh"] }

          ), /*#__PURE__*/
          _jsxs(Button, { variant: "outline", onClick: exportToCSV, children: [/*#__PURE__*/
            _jsx(Download, { className: "h-4 w-4 mr-2" }), "Export CSV"] }

          ), /*#__PURE__*/
          _jsxs(Dialog, { open: isCreateOpen, onOpenChange: setIsCreateOpen, children: [/*#__PURE__*/
            _jsx(DialogTrigger, { asChild: true, children: /*#__PURE__*/
              _jsxs(Button, { children: [/*#__PURE__*/
                _jsx(Plus, { className: "h-4 w-4 mr-2" }), "New Requirement"] }

              ) }
            ), /*#__PURE__*/
            _jsxs(DialogContent, { className: "max-w-2xl", children: [/*#__PURE__*/
              _jsxs(DialogHeader, { children: [/*#__PURE__*/
                _jsx(DialogTitle, { children: "Create Requirement" }), /*#__PURE__*/
                _jsx(DialogDescription, { children: "Add a new requirement to the system" }

                )] }
              ), /*#__PURE__*/
              _jsxs("form", { onSubmit: createForm.handleSubmit(onCreateSubmit), className: "space-y-4", children: [/*#__PURE__*/
                _jsxs("div", { children: [/*#__PURE__*/
                  _jsx(Label, { htmlFor: "name", children: "Name *" }), /*#__PURE__*/
                  _jsx(Input, { id: "name", ...createForm.register('name') }),
                  createForm.formState.errors.name && /*#__PURE__*/
                  _jsx("p", { className: "text-sm text-red-500 mt-1", children:
                    createForm.formState.errors.name.message }
                  )] }

                ), /*#__PURE__*/
                _jsxs("div", { children: [/*#__PURE__*/
                  _jsx(Label, { htmlFor: "description", children: "Description" }), /*#__PURE__*/
                  _jsx(Textarea, { id: "description", ...createForm.register('description'), rows: 3 })] }
                ), /*#__PURE__*/
                _jsxs("div", { className: "grid grid-cols-2 gap-4", children: [/*#__PURE__*/
                  _jsxs("div", { children: [/*#__PURE__*/
                    _jsx(Label, { htmlFor: "status", children: "Status" }), /*#__PURE__*/
                    _jsxs(Select, {
                      value: createForm.watch('status'),
                      onValueChange: (value) => createForm.setValue('status', value), children: [/*#__PURE__*/

                      _jsx(SelectTrigger, { children: /*#__PURE__*/
                        _jsx(SelectValue, {}) }
                      ), /*#__PURE__*/
                      _jsxs(SelectContent, { children: [/*#__PURE__*/
                        _jsx(SelectItem, { value: "Draft", children: "Draft" }), /*#__PURE__*/
                        _jsx(SelectItem, { value: "Approved", children: "Approved" }), /*#__PURE__*/
                        _jsx(SelectItem, { value: "Implemented", children: "Implemented" }), /*#__PURE__*/
                        _jsx(SelectItem, { value: "Verified", children: "Verified" }), /*#__PURE__*/
                        _jsx(SelectItem, { value: "Obsolete", children: "Obsolete" })] }
                      )] }
                    )] }
                  ), /*#__PURE__*/
                  _jsxs("div", { children: [/*#__PURE__*/
                    _jsx(Label, { htmlFor: "priority", children: "Priority" }), /*#__PURE__*/
                    _jsxs(Select, {
                      value: createForm.watch('priority'),
                      onValueChange: (value) => createForm.setValue('priority', value), children: [/*#__PURE__*/

                      _jsx(SelectTrigger, { children: /*#__PURE__*/
                        _jsx(SelectValue, {}) }
                      ), /*#__PURE__*/
                      _jsxs(SelectContent, { children: [/*#__PURE__*/
                        _jsx(SelectItem, { value: "Low", children: "Low" }), /*#__PURE__*/
                        _jsx(SelectItem, { value: "Medium", children: "Medium" }), /*#__PURE__*/
                        _jsx(SelectItem, { value: "High", children: "High" }), /*#__PURE__*/
                        _jsx(SelectItem, { value: "Critical", children: "Critical" })] }
                      )] }
                    )] }
                  )] }
                ), /*#__PURE__*/
                _jsxs("div", { children: [/*#__PURE__*/
                  _jsx(Label, { htmlFor: "category", children: "Category" }), /*#__PURE__*/
                  _jsx(Input, { id: "category", ...createForm.register('category') })] }
                ), /*#__PURE__*/
                _jsxs(DialogFooter, { children: [/*#__PURE__*/
                  _jsx(Button, { type: "button", variant: "outline", onClick: () => setIsCreateOpen(false), children: "Cancel" }

                  ), /*#__PURE__*/
                  _jsx(Button, { type: "submit", disabled: createMutation.isPending, children:
                    createMutation.isPending ? 'Creating...' : 'Create' }
                  )] }
                )] }
              )] }
            )] }
          )] }
        ) }

      ),


      error && /*#__PURE__*/
      _jsx(Alert, { variant: "destructive", children: /*#__PURE__*/
        _jsxs(AlertDescription, { children: ["Failed to load requirements: ",
          error instanceof Error ? error.message : typeof error === 'object' && error !== null ? JSON.stringify(error) : String(error)] }
        ) }
      ), /*#__PURE__*/



      _jsx("div", { className: "flex gap-4", children: /*#__PURE__*/
        _jsxs("div", { className: "relative flex-1", children: [/*#__PURE__*/
          _jsx(Search, { className: "absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" }), /*#__PURE__*/
          _jsx(Input, {
            placeholder: "Search requirements...",
            value: globalFilter,
            onChange: (e) => setGlobalFilter(e.target.value),
            className: "pl-10" }
          )] }
        ) }
      ), /*#__PURE__*/


      _jsx("div", { className: "rounded-md border", children: /*#__PURE__*/
        _jsxs(Table, { children: [/*#__PURE__*/
          _jsx(TableHeader, { children:
            table.getHeaderGroups().map((headerGroup) => /*#__PURE__*/
            _jsx(TableRow, { children:
              headerGroup.headers.map((header) => /*#__PURE__*/
              _jsx(TableHead, { children:
                header.isPlaceholder ?
                null :
                flexRender(
                  header.column.columnDef.header,
                  header.getContext()
                ) }, header.id
              )
              ) }, headerGroup.id
            )
            ) }
          ), /*#__PURE__*/
          _jsx(TableBody, { children:
            isLoading ?
            Array.from({ length: 5 }).map((_, i) => /*#__PURE__*/
            _jsx(TableRow, { children:
              columns.map((_, j) => /*#__PURE__*/
              _jsx(TableCell, { children: /*#__PURE__*/
                _jsx(Skeleton, { className: "h-6 w-full" }) }, j
              )
              ) }, i
            )
            ) :
            table.getRowModel().rows.length === 0 ? /*#__PURE__*/
            _jsx(TableRow, { children: /*#__PURE__*/
              _jsx(TableCell, { colSpan: columns.length, className: "h-24 text-center", children: "No requirements found." }

              ) }
            ) :

            table.getRowModel().rows.map((row) => /*#__PURE__*/
            _jsx(TableRow, { children:
              row.getVisibleCells().map((cell) => /*#__PURE__*/
              _jsx(TableCell, { children:
                flexRender(cell.column.columnDef.cell, cell.getContext()) }, cell.id
              )
              ) }, row.id
            )
            ) }

          )] }
        ) }
      ), /*#__PURE__*/


      _jsxs("div", { className: "flex items-center justify-between", children: [/*#__PURE__*/
        _jsxs("div", { className: "text-sm text-muted-foreground", children: ["Showing ",
          table.getRowModel().rows.length, " of ", requirements.length, " requirements"] }
        ), /*#__PURE__*/
        _jsxs("div", { className: "flex items-center gap-2", children: [/*#__PURE__*/
          _jsx(Button, {
            variant: "outline",
            size: "sm",
            onClick: () => table.previousPage(),
            disabled: !table.getCanPreviousPage(), children:
            "Previous" }

          ), /*#__PURE__*/
          _jsx(Button, {
            variant: "outline",
            size: "sm",
            onClick: () => table.nextPage(),
            disabled: !table.getCanNextPage(), children:
            "Next" }

          )] }
        )] }
      ), /*#__PURE__*/


      _jsx(Dialog, { open: isEditOpen, onOpenChange: setIsEditOpen, children: /*#__PURE__*/
        _jsxs(DialogContent, { className: "max-w-2xl", children: [/*#__PURE__*/
          _jsxs(DialogHeader, { children: [/*#__PURE__*/
            _jsx(DialogTitle, { children: "Edit Requirement" }), /*#__PURE__*/
            _jsx(DialogDescription, { children: "Update requirement details" }

            )] }
          ), /*#__PURE__*/
          _jsxs("form", { onSubmit: editForm.handleSubmit(onEditSubmit), className: "space-y-4", children: [/*#__PURE__*/
            _jsxs("div", { children: [/*#__PURE__*/
              _jsx(Label, { htmlFor: "edit-name", children: "Name *" }), /*#__PURE__*/
              _jsx(Input, { id: "edit-name", ...editForm.register('name') }),
              editForm.formState.errors.name && /*#__PURE__*/
              _jsx("p", { className: "text-sm text-red-500 mt-1", children:
                editForm.formState.errors.name.message }
              )] }

            ), /*#__PURE__*/
            _jsxs("div", { children: [/*#__PURE__*/
              _jsx(Label, { htmlFor: "edit-description", children: "Description" }), /*#__PURE__*/
              _jsx(Textarea, { id: "edit-description", ...editForm.register('description'), rows: 3 })] }
            ), /*#__PURE__*/
            _jsxs("div", { className: "grid grid-cols-2 gap-4", children: [/*#__PURE__*/
              _jsxs("div", { children: [/*#__PURE__*/
                _jsx(Label, { htmlFor: "edit-status", children: "Status" }), /*#__PURE__*/
                _jsxs(Select, {
                  value: editForm.watch('status'),
                  onValueChange: (value) => editForm.setValue('status', value), children: [/*#__PURE__*/

                  _jsx(SelectTrigger, { children: /*#__PURE__*/
                    _jsx(SelectValue, {}) }
                  ), /*#__PURE__*/
                  _jsxs(SelectContent, { children: [/*#__PURE__*/
                    _jsx(SelectItem, { value: "Draft", children: "Draft" }), /*#__PURE__*/
                    _jsx(SelectItem, { value: "Approved", children: "Approved" }), /*#__PURE__*/
                    _jsx(SelectItem, { value: "Implemented", children: "Implemented" }), /*#__PURE__*/
                    _jsx(SelectItem, { value: "Verified", children: "Verified" }), /*#__PURE__*/
                    _jsx(SelectItem, { value: "Obsolete", children: "Obsolete" })] }
                  )] }
                )] }
              ), /*#__PURE__*/
              _jsxs("div", { children: [/*#__PURE__*/
                _jsx(Label, { htmlFor: "edit-priority", children: "Priority" }), /*#__PURE__*/
                _jsxs(Select, {
                  value: editForm.watch('priority'),
                  onValueChange: (value) => editForm.setValue('priority', value), children: [/*#__PURE__*/

                  _jsx(SelectTrigger, { children: /*#__PURE__*/
                    _jsx(SelectValue, {}) }
                  ), /*#__PURE__*/
                  _jsxs(SelectContent, { children: [/*#__PURE__*/
                    _jsx(SelectItem, { value: "Low", children: "Low" }), /*#__PURE__*/
                    _jsx(SelectItem, { value: "Medium", children: "Medium" }), /*#__PURE__*/
                    _jsx(SelectItem, { value: "High", children: "High" }), /*#__PURE__*/
                    _jsx(SelectItem, { value: "Critical", children: "Critical" })] }
                  )] }
                )] }
              )] }
            ), /*#__PURE__*/
            _jsxs("div", { children: [/*#__PURE__*/
              _jsx(Label, { htmlFor: "edit-category", children: "Category" }), /*#__PURE__*/
              _jsx(Input, { id: "edit-category", ...editForm.register('category') })] }
            ), /*#__PURE__*/
            _jsxs(DialogFooter, { children: [/*#__PURE__*/
              _jsx(Button, { type: "button", variant: "outline", onClick: () => setIsEditOpen(false), children: "Cancel" }

              ), /*#__PURE__*/
              _jsx(Button, { type: "submit", disabled: updateMutation.isPending, children:
                updateMutation.isPending ? 'Saving...' : 'Save' }
              )] }
            )] }
          )] }
        ) }
      )] }
    ));

}
