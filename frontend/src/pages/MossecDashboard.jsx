import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Search, FileText, Share2, Eye, Loader2 } from 'lucide-react';
import GraphBrowser from './GraphBrowser'; // Importing the existing GraphBrowser component
import { apiService } from '@/services/api';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import AdvancedSearch from './AdvancedSearch';

const MOSSEC_TYPES = [
    'ModelInstance', 
    'Study', 
    'ActualActivity', 
    'AssociativeModelNetwork',
    'ModelType',
    'Method',
    'Result',
    'Verification'
];

export default function MossecDashboard() {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeView, setActiveView] = useState('models');
  
  // Fetch Model Instances
  const { data: modelInstances, isLoading: loadingModels } = useQuery({
    queryKey: ['mossec-models'],
    queryFn: async () => {
       try {
         const res = await apiService.smrl.listResources('ModelInstance');
         return Array.isArray(res) ? res : (res.data || []);
       } catch (e) {
         console.warn("Failed to fetch ModelInstances", e);
         return [];
       }
    }
  });

  // Fetch Studies
  const { data: studies, isLoading: loadingStudies } = useQuery({
    queryKey: ['mossec-studies'],
    queryFn: async () => {
       try {
         const res = await apiService.smrl.listResources('Study');
         return Array.isArray(res) ? res : (res.data || []);
       } catch (e) {
         console.warn("Failed to fetch Studies", e);
         return [];
       }
    }
  });

  // Fetch Activities
  const { data: activities, isLoading: loadingActivities } = useQuery({
    queryKey: ['mossec-activities'],
    queryFn: async () => {
       try {
         const res = await apiService.smrl.listResources('ActualActivity');
         return Array.isArray(res) ? res : (res.data || []);
       } catch (e) {
         console.warn("Failed to fetch Activities", e);
         return [];
       }
    }
  });

  const renderContent = () => {
    if (activeView === 'models') {
       if (loadingModels) return <div className="flex justify-center p-8"><Loader2 className="h-8 w-8 animate-spin" /></div>;
       return (
            <Table>
                <TableHeader>
                <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Format</TableHead>
                    <TableHead>Status</TableHead>
                </TableRow>
                </TableHeader>
                <TableBody>
                {modelInstances && modelInstances.length > 0 ? (
                    modelInstances.map((model, idx) => (
                    <TableRow key={idx}>
                        <TableCell className="font-mono">{model.id || model.uid || 'N/A'}</TableCell>
                        <TableCell>{model.name || 'Unnamed Model'}</TableCell>
                        <TableCell>{model.format || 'Unknown'}</TableCell>
                        <TableCell>
                        <Badge variant="outline">{model.status || 'Active'}</Badge>
                        </TableCell>
                    </TableRow>
                    ))
                ) : (
                    <TableRow>
                    <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">
                        No Model Instances found.
                    </TableCell>
                    </TableRow>
                )}
                </TableBody>
            </Table>
       );
    }
    if (activeView === 'studies') {
        if (loadingStudies) return <div className="flex justify-center p-8"><Loader2 className="h-8 w-8 animate-spin" /></div>;
        return (
             <Table>
                 <TableHeader>
                 <TableRow>
                     <TableHead>ID</TableHead>
                     <TableHead>Title</TableHead>
                     <TableHead>Phase</TableHead>
                     <TableHead>Assigned To</TableHead>
                 </TableRow>
                 </TableHeader>
                 <TableBody>
                 {studies && studies.length > 0 ? (
                     studies.map((study, idx) => (
                     <TableRow key={idx}>
                         <TableCell className="font-mono">{study.id || study.uid || 'N/A'}</TableCell>
                         <TableCell>{study.name || study.title || 'Unnamed Study'}</TableCell>
                         <TableCell><Badge>{study.phase || 'Initiation'}</Badge></TableCell>
                         <TableCell>{study.owner || 'Unassigned'}</TableCell>
                     </TableRow>
                     ))
                 ) : (
                     <TableRow>
                     <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">
                         No Studies found.
                     </TableCell>
                     </TableRow>
                 )}
                 </TableBody>
             </Table>
        );
     }
     if (activeView === 'activities') {
        if (loadingActivities) return <div className="flex justify-center p-8"><Loader2 className="h-8 w-8 animate-spin" /></div>;
        return (
             <Table>
                 <TableHeader>
                 <TableRow>
                     <TableHead>ID</TableHead>
                     <TableHead>Name</TableHead>
                     <TableHead>Method</TableHead>
                     <TableHead>Status</TableHead>
                 </TableRow>
                 </TableHeader>
                 <TableBody>
                 {activities && activities.length > 0 ? (
                     activities.map((act, idx) => (
                     <TableRow key={idx}>
                         <TableCell className="font-mono">{act.id || act.uid || 'N/A'}</TableCell>
                         <TableCell>{act.name || 'Unnamed Activity'}</TableCell>
                         <TableCell>{act.method || 'Standard'}</TableCell>
                         <TableCell>
                         <Badge variant={act.status === 'Complete' ? 'default' : 'secondary'}>{act.status || 'Planned'}</Badge>
                         </TableCell>
                     </TableRow>
                     ))
                 ) : (
                     <TableRow>
                     <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">
                         No Activities found.
                     </TableCell>
                     </TableRow>
                 )}
                 </TableBody>
             </Table>
        );
     }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex flex-col space-y-2">
        <h1 className="text-3xl font-bold">AP243 MoSSEC Dashboard</h1>
        <p className="text-muted-foreground">
          ISO 10303-243: Modeling and Simulation information in a Collaborative Systems Engineering Context
        </p>
      </div>

      <Tabs defaultValue="views" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="views">Domain Views</TabsTrigger>
          <TabsTrigger value="search">Search</TabsTrigger>
          <TabsTrigger value="graph">Graph</TabsTrigger>
        </TabsList>
        
        <TabsContent value="views" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                    <CardTitle>MoSSEC Domain Entities</CardTitle>
                    <CardDescription>
                        Explore the core entities of the MoSSEC standard.
                    </CardDescription>
                </div>
                <div className="flex space-x-2">
                    <Button variant={activeView === 'models' ? 'default' : 'outline'} onClick={() => setActiveView('models')} size="sm">Models</Button>
                    <Button variant={activeView === 'studies' ? 'default' : 'outline'} onClick={() => setActiveView('studies')} size="sm">Studies</Button>
                    <Button variant={activeView === 'activities' ? 'default' : 'outline'} onClick={() => setActiveView('activities')} size="sm">Activities</Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {renderContent()}
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="search" className="space-y-4">
            <AdvancedSearch 
                title="MoSSEC Resource Search" 
                allowedTypes={MOSSEC_TYPES} 
                defaultType="ModelInstance"
            />
        </TabsContent>
        
        <TabsContent value="graph" className="h-[800px]">
           <Card className="h-full border-0 shadow-none">
             <CardContent className="p-0 h-full">
               <GraphBrowser fixedNodeTypes={MOSSEC_TYPES} />
             </CardContent>
           </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
