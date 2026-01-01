import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@ui/card';
import { Badge } from '@ui/badge';
import { Button } from '@ui/button';
import { Input } from '@ui/input';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '@ui/dialog';
import { Boxes, Search, Plus, FileCode, Clock, Eye, Pencil } from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import { toast } from 'sonner';
export default function ModelRepository() {
  const [selectedModel, setSelectedModel] = useState(null);
  const [isViewOpen, setIsViewOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const models = [{
    id: 1,
    name: 'Thermal Analysis v2.3',
    type: 'CFD',
    lastModified: '2 days ago',
    status: 'validated',
    description: 'Comprehensive thermal analysis model for propulsion systems',
    author: 'Engineering Team',
    version: '2.3.1',
    tags: ['thermal', 'cfd', 'propulsion']
  }, {
    id: 2,
    name: 'Structural FEA Model',
    type: 'FEA',
    lastModified: '1 week ago',
    status: 'draft',
    description: 'Finite element analysis for structural integrity',
    author: 'Structures Team',
    version: '1.0.0',
    tags: ['structural', 'fea', 'analysis']
  }, {
    id: 3,
    name: 'Propulsion Simulation',
    type: 'System',
    lastModified: '3 days ago',
    status: 'validated',
    description: 'End-to-end propulsion system simulation',
    author: 'Systems Team',
    version: '3.2.0',
    tags: ['propulsion', 'system', 'dynamics']
  }, {
    id: 4,
    name: 'Aerodynamics Study',
    type: 'CFD',
    lastModified: '5 days ago',
    status: 'archived',
    description: 'Aerodynamic flow analysis and optimization',
    author: 'Aero Team',
    version: '1.5.2',
    tags: ['aerodynamics', 'cfd', 'flow']
  }];
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
      description: 'Opening model creation wizard...'
    });
  };
  const handleSaveEdit = () => {
    toast.success('Model Updated', {
      description: `${selectedModel?.name} has been updated successfully.`
    });
    setIsEditOpen(false);
    setSelectedModel(null);
  };
  return <div className="container mx-auto p-6 space-y-6"><PageHeader title="Model Repository" description="Centralized library of simulation models and analysis templates" icon={<Boxes className="h-8 w-8 text-primary" />} breadcrumbs={[{
      label: 'Simulation Engineering',
      href: '/simulation/models'
    }, {
      label: 'Model Repository'
    }]} actions={<Button onClick={handleAddNew}><Plus className="h-4 w-4 mr-2" />Add New Model</Button>} /><Card><CardContent className="pt-6"><div className="flex gap-4"><div className="relative flex-1"><Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" /><Input placeholder="Search models by name, type, or tags..." className="pl-10" /></div><Button variant="outline"><FileCode className="h-4 w-4 mr-2" />Filter by Type</Button></div></CardContent></Card><div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">{models.map((model, idx) => <Card className="hover:shadow-lg transition-shadow"><CardHeader><div className="flex items-start justify-between"><CardTitle className="text-lg">{model.name}</CardTitle><div className={`h-2 w-2 rounded-full ${getStatusColor(model.status)}`} /></div><CardDescription>{model.type} Model</CardDescription></CardHeader><CardContent className="space-y-4"><div className="flex items-center gap-2 text-sm text-muted-foreground"><Clock className="h-4 w-4" />Modified {model.lastModified}</div><div className="flex gap-2"><Badge variant="outline" className="capitalize">{model.status}</Badge><Badge variant="secondary">{model.type}</Badge></div><div className="flex gap-2 pt-2"><Button variant="outline" size="sm" className="flex-1" onClick={() => handleView(model)}>View</Button><Button variant="outline" size="sm" className="flex-1" onClick={() => handleEdit(model)}>Edit</Button></div></CardContent></Card>)}</div><div className="grid grid-cols-1 md:grid-cols-4 gap-4"><Card><CardContent className="pt-6"><div className="text-2xl font-bold">24</div><p className="text-sm text-muted-foreground">Total Models</p></CardContent></Card><Card><CardContent className="pt-6"><div className="text-2xl font-bold text-green-500">12</div><p className="text-sm text-muted-foreground">Validated</p></CardContent></Card><Card><CardContent className="pt-6"><div className="text-2xl font-bold text-amber-500">8</div><p className="text-sm text-muted-foreground">In Draft</p></CardContent></Card><Card><CardContent className="pt-6"><div className="text-2xl font-bold text-blue-500">156</div><p className="text-sm text-muted-foreground">Total Runs</p></CardContent></Card></div><Dialog open={isViewOpen} onOpenChange={setIsViewOpen}><DialogContent className="max-w-2xl"><DialogHeader><DialogTitle className="flex items-center gap-2"><Eye className="h-5 w-5 text-primary" />{selectedModel?.name}</DialogTitle><DialogDescription>Model Details and Information</DialogDescription></DialogHeader><div className="space-y-4 py-4"><div className="grid grid-cols-2 gap-4"><div><label className="text-sm font-medium text-muted-foreground">Type</label><p className="text-sm mt-1">{selectedModel?.type}</p></div><div><label className="text-sm font-medium text-muted-foreground">Status</label><div className="mt-1"><Badge variant="outline" className="capitalize">{selectedModel?.status}</Badge></div></div><div><label className="text-sm font-medium text-muted-foreground">Version</label><p className="text-sm mt-1">{selectedModel?.version}</p></div><div><label className="text-sm font-medium text-muted-foreground">Author</label><p className="text-sm mt-1">{selectedModel?.author}</p></div></div><div><label className="text-sm font-medium text-muted-foreground">Description</label><p className="text-sm mt-1">{selectedModel?.description}</p></div><div><label className="text-sm font-medium text-muted-foreground">Tags</label><div className="flex gap-2 mt-2">{selectedModel?.tags?.map((tag, idx) => <Badge variant="secondary">{tag}</Badge>)}</div></div><div><label className="text-sm font-medium text-muted-foreground">Last Modified</label><p className="text-sm mt-1">{selectedModel?.lastModified}</p></div></div><DialogFooter><Button variant="outline" onClick={() => setIsViewOpen(false)}>Close</Button><Button onClick={() => {
            setIsViewOpen(false);
            setIsEditOpen(true);
          }}><Pencil className="h-4 w-4 mr-2" />Edit Model</Button></DialogFooter></DialogContent></Dialog><Dialog open={isEditOpen} onOpenChange={setIsEditOpen}><DialogContent className="max-w-2xl"><DialogHeader><DialogTitle className="flex items-center gap-2"><Pencil className="h-5 w-5 text-primary" />Edit Model</DialogTitle><DialogDescription>Update model information and metadata</DialogDescription></DialogHeader><div className="space-y-4 py-4"><div><label className="text-sm font-medium">Model Name</label><Input defaultValue={selectedModel?.name} className="mt-1" /></div><div className="grid grid-cols-2 gap-4"><div><label className="text-sm font-medium">Type</label><Input defaultValue={selectedModel?.type} className="mt-1" /></div><div><label className="text-sm font-medium">Version</label><Input defaultValue={selectedModel?.version} className="mt-1" /></div></div><div><label className="text-sm font-medium">Description</label><Input defaultValue={selectedModel?.description} className="mt-1" /></div><div><label className="text-sm font-medium">Status</label><div className="flex gap-2 mt-1"><Badge variant={selectedModel?.status === 'validated' ? 'default' : 'outline'} className="cursor-pointer">Validated</Badge><Badge variant={selectedModel?.status === 'draft' ? 'default' : 'outline'} className="cursor-pointer">Draft</Badge><Badge variant={selectedModel?.status === 'archived' ? 'default' : 'outline'} className="cursor-pointer">Archived</Badge></div></div></div><DialogFooter><Button variant="outline" onClick={() => setIsEditOpen(false)}>Cancel</Button><Button onClick={handleSaveEdit}>Save Changes</Button></DialogFooter></DialogContent></Dialog></div>;
}
