import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Boxes, Search, Plus, FileCode, Clock, Eye, Pencil } from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import { getModels, getParameters } from '@/services/simulation.service';
import { toast } from 'sonner';
export default function ModelRepository() {
  const [selectedModel, setSelectedModel] = useState(null);
  const [isViewOpen, setIsViewOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [search, setSearch] = useState('');

  // Form states
  const [formData, setFormData] = useState({ name: '', type: 'Physical', description: '', status: 'draft' });

  const {
    data: modelsResponse,
    isLoading: isModelsLoading,
    isError: isModelsError,
    error: modelsError,
    refetch: refetchModels,
  } = useQuery({
    queryKey: ['simulation-models'],
    queryFn: () => getModels({ limit: 500 }),
  });

  const models = useMemo(() => {
    const raw = modelsResponse?.models ?? [];
    const normalized = raw.map(m => ({
      id: m.id,
      name: m.name,
      parameter_count: m.parameter_count ?? 0,
      constraint_count: m.constraint_count ?? 0,
      status: (m.constraint_count ?? 0) > 0 ? 'validated' : 'draft'
    }));

    const term = search.trim().toLowerCase();
    if (!term) return normalized;
    return normalized.filter(m => (m.name ?? '').toLowerCase().includes(term));
  }, [modelsResponse, search]);

  const {
    data: parametersResponse,
    isLoading: isParametersLoading,
    isError: isParametersError,
    error: parametersError,
    refetch: refetchParameters,
  } = useQuery({
    queryKey: ['simulation-parameters', selectedModel?.name],
    enabled: Boolean(isViewOpen && selectedModel?.name),
    queryFn: () => getParameters({
      class_name: selectedModel?.name,
      include_constraints: false,
      limit: 5000,
    }),
  });
  const getStatusColor = status => {
    switch (status) {
      case 'validated':
        return 'bg-green-500';
      case 'draft':
        return 'bg-amber-500';
      case 'archived':
        return 'bg-gray-500';
      default:
        return 'bg-blue-500';
    }
  };
  const handleView = model => {
    setSelectedModel(model);
    setIsViewOpen(true);
  };
  const handleEdit = model => {
    setSelectedModel(model);
    setFormData({ 
        name: model.name || '', 
        type: model.type || 'Physical', 
        description: model.description || '', 
        status: model.status || 'draft' 
    });
    setIsEditOpen(true);
  };
  const handleAddNew = () => {
    setFormData({ name: '', type: 'Physical', description: '', status: 'draft' });
    setIsCreateOpen(true);
  };
  const handleCreateSubmit = () => {
    toast.info('Feature Unavailable', { 
        description: 'Backend API for creating models is currently under development.' 
    });
  };
  const handleEditSubmit = () => {
    toast.info('Feature Unavailable', { 
        description: 'Backend API for updating models is currently under development.' 
    });
  };
  

  return <div className="container mx-auto p-6 space-y-6"><PageHeader title="Model Repository" description="Centralized library of simulation models and analysis templates" icon={<Boxes className="h-8 w-8 text-primary" />} breadcrumbs={[{
      label: 'Simulation Engineering',
      href: '/simulation/models'
    }, {
      label: 'Model Repository'
    }]} actions={<Button onClick={handleAddNew}><Plus className="h-4 w-4 mr-2" />Add New Model</Button>} />

    <Card>
      <CardContent className="pt-6">
        <div className="flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input placeholder="Search models by class name..." className="pl-10" value={search} onChange={e => setSearch(e.target.value)} />
          </div>
          <Button variant="outline" onClick={() => refetchModels()} disabled={isModelsLoading}>
            <FileCode className="h-4 w-4 mr-2" />Refresh
          </Button>
        </div>
      </CardContent>
    </Card>

    {isModelsError && <Card className="border-destructive/40"><CardHeader><CardTitle>Failed to load models</CardTitle><CardDescription>{String(modelsError?.message || modelsError || 'Unknown error')}</CardDescription></CardHeader><CardContent><Button variant="outline" onClick={() => refetchModels()}>Retry</Button></CardContent></Card>}

    <div className="border rounded-md">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Model Name</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Parameters</TableHead>
            <TableHead>Constraints</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Last Modified</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isModelsLoading ? (
            Array.from({ length: 5 }).map((_, idx) => (
              <TableRow key={`loading-${idx}`}>
                <TableCell><div className="h-4 w-32 bg-muted rounded animate-pulse" /></TableCell>
                <TableCell><div className="h-4 w-16 bg-muted rounded animate-pulse" /></TableCell>
                <TableCell><div className="h-4 w-8 bg-muted rounded animate-pulse" /></TableCell>
                <TableCell><div className="h-4 w-8 bg-muted rounded animate-pulse" /></TableCell>
                <TableCell><div className="h-5 w-16 bg-muted rounded animate-pulse" /></TableCell>
                <TableCell><div className="h-4 w-24 bg-muted rounded animate-pulse" /></TableCell>
                <TableCell className="text-right"><div className="h-8 w-16 bg-muted rounded animate-pulse inline-block" /></TableCell>
              </TableRow>
            ))
          ) : models.length === 0 ? (
            <TableRow>
              <TableCell colSpan={7} className="text-center h-24 text-muted-foreground">
                No models found.
              </TableCell>
            </TableRow>
          ) : (
            models.map(model => (
              <TableRow key={model.id}>
                <TableCell className="font-medium">{model.name}</TableCell>
                <TableCell>{model.type || 'Class'}</TableCell>
                <TableCell>{model.parameter_count}</TableCell>
                <TableCell>{model.constraint_count}</TableCell>
                <TableCell>
                  <Badge variant="outline" className={`capitalize ${model.status === 'validated' ? 'border-green-500 text-green-500' : 'border-amber-500 text-amber-500'}`}>
                    {model.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-muted-foreground text-sm">
                  {model.lastModified || '—'}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-2">
                    <Button variant="ghost" size="sm" onClick={() => handleView(model)}>
                      <Eye className="h-4 w-4 mr-1" /> View
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleEdit(model)}>
                      <Pencil className="h-4 w-4 mr-1" /> Edit
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>

    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <Card><CardContent className="pt-6"><div className="text-2xl font-bold">{modelsResponse?.total ?? 0}</div><p className="text-sm text-muted-foreground">Total Models</p></CardContent></Card>
      <Card><CardContent className="pt-6"><div className="text-2xl font-bold text-green-500">{models.filter(m => m.status === 'validated').length}</div><p className="text-sm text-muted-foreground">Validated</p></CardContent></Card>
      <Card><CardContent className="pt-6"><div className="text-2xl font-bold text-amber-500">{models.filter(m => m.status === 'draft').length}</div><p className="text-sm text-muted-foreground">In Draft</p></CardContent></Card>
      <Card><CardContent className="pt-6"><div className="text-2xl font-bold text-blue-500">—</div><p className="text-sm text-muted-foreground">Total Runs</p></CardContent></Card>
    </div>

    <Dialog open={isViewOpen} onOpenChange={open => {
      setIsViewOpen(open);
      if (open) refetchParameters();
    }}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Eye className="h-5 w-5 text-primary" />{selectedModel?.name}</DialogTitle>
          <DialogDescription>Model details derived from graph schema</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-muted-foreground">Model ID</label>
              <p className="text-sm mt-1 break-all">{selectedModel?.id}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">Status</label>
              <div className="mt-1"><Badge variant="outline" className="capitalize">{selectedModel?.status}</Badge></div>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">Parameter Count</label>
              <p className="text-sm mt-1">{selectedModel?.parameter_count ?? 0}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">Constraint Count</label>
              <p className="text-sm mt-1">{selectedModel?.constraint_count ?? 0}</p>
            </div>
          </div>

          <div>
            <label className="text-sm font-medium text-muted-foreground">Parameters</label>
            <div className="mt-2 border rounded-lg max-h-64 overflow-y-auto">
              {isParametersError && <div className="p-3 text-sm text-destructive">{String(parametersError?.message || parametersError || 'Failed to load parameters')}</div>}
              {isParametersLoading && <div className="p-3 text-sm text-muted-foreground">Loading parameters…</div>}
              {!isParametersLoading && !isParametersError && <div className="divide-y">
                {(parametersResponse?.parameters ?? []).slice(0, 200).map(p => <div key={p.id} className="p-3 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-sm font-medium truncate">{p.name}</div>
                    <div className="text-xs text-muted-foreground truncate">{p.data_type || p.property_type || '—'}</div>
                  </div>
                  <Badge variant="outline" className="shrink-0">{p.id}</Badge>
                </div>)}
                {(parametersResponse?.parameters ?? []).length === 0 && <div className="p-3 text-sm text-muted-foreground">No parameters found for this model.</div>}
              </div>}
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setIsViewOpen(false)}>Close</Button>
          <Button onClick={() => {
            setIsViewOpen(false);
            setIsEditOpen(true);
          }}><Pencil className="h-4 w-4 mr-2" />Edit Model</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Pencil className="h-5 w-5 text-primary" />Edit Model</DialogTitle>
          <DialogDescription>Update model information and metadata</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>Model Name</Label>
            <Input 
                value={formData.name} 
                onChange={e => setFormData({...formData, name: e.target.value})} 
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
                <Label>Type</Label>
                <Select value={formData.type} onValueChange={v => setFormData({...formData, type: v})}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                        <SelectItem value="Physical">Physical</SelectItem>
                        <SelectItem value="Logical">Logical</SelectItem>
                        <SelectItem value="Functional">Functional</SelectItem>
                    </SelectContent>
                </Select>
            </div>
            <div className="space-y-2">
                <Label>Status</Label>
                 <Select value={formData.status} onValueChange={v => setFormData({...formData, status: v})}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                        <SelectItem value="draft">Draft</SelectItem>
                        <SelectItem value="validated">Validated</SelectItem>
                        <SelectItem value="archived">Archived</SelectItem>
                    </SelectContent>
                </Select>
            </div>
          </div>
          <div className="space-y-2">
            <Label>Description</Label>
            <Textarea 
                value={formData.description} 
                onChange={e => setFormData({...formData, description: e.target.value})} 
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setIsEditOpen(false)}>Cancel</Button>
          <Button onClick={handleEditSubmit}>Save Changes</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Plus className="h-5 w-5 text-primary" />Create Model</DialogTitle>
          <DialogDescription>Add a new simulation model to the repository</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>Model Name</Label>
            <Input 
                placeholder="e.g. Thermal System V2"
                value={formData.name} 
                onChange={e => setFormData({...formData, name: e.target.value})} 
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
               <div className="space-y-2">
                <Label>Type</Label>
                <Select value={formData.type} onValueChange={v => setFormData({...formData, type: v})}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                        <SelectItem value="Physical">Physical</SelectItem>
                        <SelectItem value="Logical">Logical</SelectItem>
                        <SelectItem value="Functional">Functional</SelectItem>
                    </SelectContent>
                </Select>
            </div>
            <div className="space-y-2">
                <Label>Status</Label>
                 <Select value={formData.status} onValueChange={v => setFormData({...formData, status: v})}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                        <SelectItem value="draft">Draft</SelectItem>
                        <SelectItem value="validated">Validated</SelectItem>
                        <SelectItem value="archived">Archived</SelectItem>
                    </SelectContent>
                </Select>
            </div>
          </div>
          <div className="space-y-2">
            <Label>Description</Label>
            <Textarea 
                placeholder="Describe the model purpose and scope..."
                value={formData.description} 
                onChange={e => setFormData({...formData, description: e.target.value})} 
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setIsCreateOpen(false)}>Cancel</Button>
          <Button onClick={handleCreateSubmit}>Create Model</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>;
}
