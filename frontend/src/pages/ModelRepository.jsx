import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@ui/card';
import { Badge } from '@ui/badge';
import { Button } from '@ui/button';
import { Input } from '@ui/input';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '@ui/dialog';
import { Boxes, Search, Plus, FileCode, Clock, Eye, Pencil } from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import { apiService } from '@/services/api';
import { toast } from 'sonner';
export default function ModelRepository() {
  const [selectedModel, setSelectedModel] = useState(null);
  const [isViewOpen, setIsViewOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [search, setSearch] = useState('');

  const {
    data: modelsResponse,
    isLoading: isModelsLoading,
    isError: isModelsError,
    error: modelsError,
    refetch: refetchModels,
  } = useQuery({
    queryKey: ['simulation-models'],
    queryFn: () => apiService.simulation.getModels({ limit: 500 }),
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
    queryFn: () => apiService.simulation.getParameters({
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
    setIsEditOpen(true);
  };
  const handleAddNew = () => {
    toast.info('Add New Model', {
      description: 'Model creation is not implemented yet.'
    });
  };
  const handleSaveEdit = () => {
    toast.success('Model Updated', {
      description: 'Editing is not implemented yet.'
    });
    setIsEditOpen(false);
    setSelectedModel(null);
  };
  return <div className="container mx-auto p-6 space-y-6"><PageHeader title="Model Repository" description="Centralized library of simulation models and analysis templates" icon={<Boxes className="h-8 w-8 text-primary" />} breadcrumbs={[{
      label: 'Simulation Engineering',
      href: '/simulation/models'
    }, {
      label: 'Model Repository'
    }]} actions={<Button onClick={handleAddNew}><Plus className="h-4 w-4 mr-2" />Add New Model</Button>} /><Card><CardContent className="pt-6"><div className="flex gap-4"><div className="relative flex-1"><Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" /><Input placeholder="Search models by name, type, or tags..." className="pl-10" /></div><Button variant="outline"><FileCode className="h-4 w-4 mr-2" />Filter by Type</Button></div></CardContent></Card><div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">{models.map(model => <Card key={model.id} className="hover:shadow-lg transition-shadow"><CardHeader><div className="flex items-start justify-between"><CardTitle className="text-lg">{model.name}</CardTitle><div className={`h-2 w-2 rounded-full ${getStatusColor(model.status)}`} /></div><CardDescription>{model.type} Model</CardDescription></CardHeader><CardContent className="space-y-4"><div className="flex items-center gap-2 text-sm text-muted-foreground"><Clock className="h-4 w-4" />Modified {model.lastModified}</div><div className="flex gap-2"><Badge variant="outline" className="capitalize">{model.status}</Badge><Badge variant="secondary">{model.type}</Badge></div><div className="flex gap-2 pt-2"><Button variant="outline" size="sm" className="flex-1" onClick={() => handleView(model)}>View</Button><Button variant="outline" size="sm" className="flex-1" onClick={() => handleEdit(model)}>Edit</Button></div></CardContent></Card>)}</div><div className="grid grid-cols-1 md:grid-cols-4 gap-4"><Card><CardContent className="pt-6"><div className="text-2xl font-bold">24</div><p className="text-sm text-muted-foreground">Total Models</p></CardContent></Card><Card><CardContent className="pt-6"><div className="text-2xl font-bold text-green-500">12</div><p className="text-sm text-muted-foreground">Validated</p></CardContent></Card><Card><CardContent className="pt-6"><div className="text-2xl font-bold text-amber-500">8</div><p className="text-sm text-muted-foreground">In Draft</p></CardContent></Card><Card><CardContent className="pt-6"><div className="text-2xl font-bold text-blue-500">156</div><p className="text-sm text-muted-foreground">Total Runs</p></CardContent></Card></div><Dialog open={isViewOpen} onOpenChange={setIsViewOpen}><DialogContent className="max-w-2xl"><DialogHeader><DialogTitle className="flex items-center gap-2"><Eye className="h-5 w-5 text-primary" />{selectedModel?.name}</DialogTitle><DialogDescription>Model Details and Information</DialogDescription></DialogHeader><div className="space-y-4 py-4"><div className="grid grid-cols-2 gap-4"><div><label className="text-sm font-medium text-muted-foreground">Type</label><p className="text-sm mt-1">{selectedModel?.type}</p></div><div><label className="text-sm font-medium text-muted-foreground">Status</label><div className="mt-1"><Badge variant="outline" className="capitalize">{selectedModel?.status}</Badge></div></div><div><label className="text-sm font-medium text-muted-foreground">Version</label><p className="text-sm mt-1">{selectedModel?.version}</p></div><div><label className="text-sm font-medium text-muted-foreground">Author</label><p className="text-sm mt-1">{selectedModel?.author}</p></div></div><div><label className="text-sm font-medium text-muted-foreground">Description</label><p className="text-sm mt-1">{selectedModel?.description}</p></div><div><label className="text-sm font-medium text-muted-foreground">Tags</label><div className="flex gap-2 mt-2">{selectedModel?.tags?.map(tag => <Badge key={tag} variant="secondary">{tag}</Badge>)}</div></div><div><label className="text-sm font-medium text-muted-foreground">Last Modified</label><p className="text-sm mt-1">{selectedModel?.lastModified}</p></div></div><DialogFooter><Button variant="outline" onClick={() => setIsViewOpen(false)}>Close</Button><Button onClick={() => {
            setIsViewOpen(false);
            setIsEditOpen(true);
          }}><Pencil className="h-4 w-4 mr-2" />Edit Model</Button></DialogFooter></DialogContent></Dialog><Dialog open={isEditOpen} onOpenChange={setIsEditOpen}><DialogContent className="max-w-2xl"><DialogHeader><DialogTitle className="flex items-center gap-2"><Pencil className="h-5 w-5 text-primary" />Edit Model</DialogTitle><DialogDescription>Update model information and metadata</DialogDescription></DialogHeader><div className="space-y-4 py-4"><div><label className="text-sm font-medium">Model Name</label><Input defaultValue={selectedModel?.name} className="mt-1" /></div><div className="grid grid-cols-2 gap-4"><div><label className="text-sm font-medium">Type</label><Input defaultValue={selectedModel?.type} className="mt-1" /></div><div><label className="text-sm font-medium">Version</label><Input defaultValue={selectedModel?.version} className="mt-1" /></div></div><div><label className="text-sm font-medium">Description</label><Input defaultValue={selectedModel?.description} className="mt-1" /></div><div><label className="text-sm font-medium">Status</label><div className="flex gap-2 mt-1"><Badge variant={selectedModel?.status === 'validated' ? 'default' : 'outline'} className="cursor-pointer">Validated</Badge><Badge variant={selectedModel?.status === 'draft' ? 'default' : 'outline'} className="cursor-pointer">Draft</Badge><Badge variant={selectedModel?.status === 'archived' ? 'default' : 'outline'} className="cursor-pointer">Archived</Badge></div></div></div><DialogFooter><Button variant="outline" onClick={() => setIsEditOpen(false)}>Cancel</Button><Button onClick={handleSaveEdit}>Save Changes</Button></DialogFooter></DialogContent></Dialog></div>;

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

    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {(isModelsLoading ? Array.from({ length: 6 }).map((_, idx) => ({ id: `loading-${idx}` })) : models).map(model => {
        if (isModelsLoading) {
          return <Card key={model.id} className="animate-pulse"><CardHeader><div className="h-5 bg-muted rounded w-2/3" /><div className="h-4 bg-muted rounded w-1/3 mt-2" /></CardHeader><CardContent><div className="h-4 bg-muted rounded w-1/2" /><div className="h-8 bg-muted rounded w-full mt-4" /></CardContent></Card>;
        }

        return <Card key={model.id} className="hover:shadow-lg transition-shadow">
          <CardHeader>
            <div className="flex items-start justify-between">
              <CardTitle className="text-lg">{model.name}</CardTitle>
              <div className={`h-2 w-2 rounded-full ${getStatusColor(model.status)}`} />
            </div>
            <CardDescription>{model.parameter_count} parameters · {model.constraint_count} constraints</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="h-4 w-4" />From graph schema
            </div>
            <div className="flex gap-2">
              <Badge variant="outline" className="capitalize">{model.status}</Badge>
              <Badge variant="secondary">Class</Badge>
            </div>
            <div className="flex gap-2 pt-2">
              <Button variant="outline" size="sm" className="flex-1" onClick={() => handleView(model)}>View</Button>
              <Button variant="outline" size="sm" className="flex-1" onClick={() => handleEdit(model)}>Edit</Button>
            </div>
          </CardContent>
        </Card>;
      })}
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
          <DialogDescription>Editing is not implemented yet</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div><label className="text-sm font-medium">Model Name</label><Input defaultValue={selectedModel?.name} className="mt-1" /></div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setIsEditOpen(false)}>Cancel</Button>
          <Button onClick={handleSaveEdit}>Save Changes</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>;
}
