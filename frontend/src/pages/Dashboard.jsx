import { useQuery } from '@tanstack/react-query';
import { graphqlService } from '@/services/graphql';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@ui/card';
import { Skeleton } from '@ui/skeleton';
import { Alert, AlertDescription } from '@ui/alert';
import { Button } from '@ui/button';
import { Badge } from '@ui/badge';
import { Database, Activity, Search, Terminal, FileText, ArrowRight, Sparkles, LayoutDashboard } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import PageHeader from '@/components/PageHeader';
export default function Dashboard() {
  const navigate = useNavigate();
  const {
    data: stats,
    isLoading,
    error
  } = useQuery({
    queryKey: ['statistics'],
    queryFn: graphqlService.getStatistics,
    retry: 1,
    staleTime: 30000
  });
  if (isLoading) {
    return <div className="container mx-auto p-6 space-y-6"><PageHeader title="Dashboard" description="Overview of your knowledge graph and system analytics" icon={<LayoutDashboard className="h-6 w-6 text-primary" />} /><div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">{[...Array(4)].map((_, i) => <Card><CardHeader className="pb-2"><Skeleton className="h-4 w-24" /></CardHeader><CardContent><Skeleton className="h-8 w-16" /></CardContent></Card>)}</div></div>;
  }
  if (error) {
    return <div className="container mx-auto p-6 space-y-6"><PageHeader title="Dashboard" description="Overview of your knowledge graph and system analytics" icon={<LayoutDashboard className="h-6 w-6 text-primary" />} /><Alert variant="destructive"><AlertDescription>Failed to load statistics. Please check your connection and try again.</AlertDescription></Alert></div>;
  }
  const nodeTypes = Object.entries(stats?.node_types || {}).sort(([, a], [, b]) => b - a);
  const relationshipTypes = Object.entries(stats?.relationship_types || {}).sort(([, a], [, b]) => b - a);
  const gridItems = [{
    id: 'total-nodes',
    symbol: 'N',
    name: 'Total Nodes',
    value: stats?.total_nodes || 0,
    category: 'system',
    color: 'from-blue-500 to-blue-600'
  }, {
    id: 'total-rels',
    symbol: 'R',
    name: 'Relationships',
    value: stats?.total_relationships || 0,
    category: 'system',
    color: 'from-cyan-500 to-cyan-600'
  }, {
    id: 'node-types',
    symbol: 'NT',
    name: 'Node Types',
    value: nodeTypes.length,
    category: 'system',
    color: 'from-green-500 to-green-600'
  }, {
    id: 'rel-types',
    symbol: 'RT',
    name: 'Relation Types',
    value: relationshipTypes.length,
    category: 'system',
    color: 'from-purple-500 to-purple-600'
  }, ...nodeTypes.slice(0, 12).map(([type, count], idx) => ({
    id: `node-${type}`,
    symbol: type.substring(0, 2).toUpperCase(),
    name: type,
    value: count,
    category: 'node',
    color: `from-blue-${400 + idx % 3 * 100} to-blue-${500 + idx % 3 * 100}`
  })), ...relationshipTypes.slice(0, 8).map(([type, count], idx) => ({
    id: `rel-${type}`,
    symbol: type.substring(0, 3).toUpperCase(),
    name: type,
    value: count,
    category: 'relationship',
    color: `from-indigo-${400 + idx % 3 * 100} to-indigo-${500 + idx % 3 * 100}`
  }))];
  return <div className="container mx-auto p-6 space-y-6"><PageHeader title="Dashboard" description="Overview of your knowledge graph and system analytics" icon={<LayoutDashboard className="h-6 w-6 text-primary" />} /><div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-primary/10 via-primary/5 to-background border-2 border-primary/20 shadow-lg p-8"><div className="absolute top-0 right-0 -mt-8 -mr-8 h-40 w-40 rounded-full bg-primary/10 blur-3xl" /><div className="absolute bottom-0 left-0 -mb-8 -ml-8 h-40 w-40 rounded-full bg-primary/10 blur-3xl" /><div className="relative"><div className="flex items-center gap-4 mb-4"><div className="h-16 w-16 rounded-2xl bg-gradient-to-br from-primary to-primary/80 flex items-center justify-center shadow-lg"><Database className="h-8 w-8 text-primary-foreground" /></div><div><div className="flex items-center gap-3"><h1 className="text-4xl font-bold tracking-tight">Knowledge Graph Dashboard</h1><Badge className="bg-green-500 text-white">Online</Badge></div><p className="text-lg text-muted-foreground">Periodic table view of system components</p></div></div></div></div><div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 xl:grid-cols-10 gap-2">{gridItems.map((item, index) => <Card className="group relative overflow-hidden cursor-pointer transition-all duration-200 hover:scale-105 hover:shadow-lg hover:z-10" style={{
        animationDelay: `${index * 15}ms`
      }}><div className={`absolute inset-0 bg-gradient-to-br ${item.color} opacity-8 group-hover:opacity-15 transition-opacity`} /><CardContent className="p-3 relative h-full flex flex-col items-center justify-center min-h-[85px]"><div className="text-xs text-muted-foreground mb-2 truncate w-full text-center leading-tight font-medium">{item.name}</div><div className="text-2xl font-bold truncate w-full text-center">{item.value.toLocaleString()}</div><Badge variant="outline" className="text-[8px] px-1 py-0 mt-1.5 leading-none">{item.category === 'system' ? 'SYS' : item.category === 'node' ? 'NOD' : 'REL'}</Badge></CardContent></Card>)}</div><Card><CardHeader><CardTitle className="flex items-center gap-2"><Activity className="h-5 w-5 text-primary" />Quick Actions</CardTitle></CardHeader><CardContent><div className="grid grid-cols-2 md:grid-cols-4 gap-3"><Button variant="outline" className="h-20 flex flex-col gap-2 hover:bg-primary hover:text-primary-foreground transition-colors" onClick={() => navigate('/search')}><Search className="h-5 w-5" /><span className="text-sm font-medium">Search</span></Button><Button variant="outline" className="h-20 flex flex-col gap-2 hover:bg-primary hover:text-primary-foreground transition-colors" onClick={() => navigate('/query-editor')}><Terminal className="h-5 w-5" /><span className="text-sm font-medium">Query</span></Button><Button variant="outline" className="h-20 flex flex-col gap-2 hover:bg-primary hover:text-primary-foreground transition-colors" onClick={() => navigate('/requirements')}><FileText className="h-5 w-5" /><span className="text-sm font-medium">Requirements</span></Button><Button variant="outline" className="h-20 flex flex-col gap-2 hover:bg-primary hover:text-primary-foreground transition-colors" onClick={() => navigate('/api-explorer')}><Activity className="h-5 w-5" /><span className="text-sm font-medium">API</span></Button></div></CardContent></Card><Card className="border-2 border-primary/20 bg-gradient-to-br from-primary/5 to-background"><CardHeader><CardTitle className="flex items-center gap-2"><Sparkles className="h-5 w-5 text-primary" />ISO 10303 Application Protocols</CardTitle><CardDescription>Access standardized engineering data across the product lifecycle</CardDescription></CardHeader><CardContent><div className="grid md:grid-cols-3 gap-4"><Card className="cursor-pointer hover:shadow-lg transition-all hover:scale-105" onClick={() => navigate('/ap239/requirements')}><CardHeader className="pb-3"><div className="flex items-center justify-between"><Badge className="bg-blue-500 text-white">AP239</Badge><ArrowRight className="h-4 w-4 text-muted-foreground" /></div></CardHeader><CardContent><h3 className="font-semibold mb-1">Requirements</h3><p className="text-sm text-muted-foreground mb-3">Product Life Cycle Support</p><div className="text-xs text-muted-foreground space-y-1"><div>• Requirements Management</div><div>• Analysis & Specifications</div><div>• Change Control & Approvals</div></div></CardContent></Card><Card className="cursor-pointer hover:shadow-lg transition-all hover:scale-105" onClick={() => navigate('/ap242/parts')}><CardHeader className="pb-3"><div className="flex items-center justify-between"><Badge className="bg-green-500 text-white">AP242</Badge><ArrowRight className="h-4 w-4 text-muted-foreground" /></div></CardHeader><CardContent><h3 className="font-semibold mb-1">Parts & Engineering</h3><p className="text-sm text-muted-foreground mb-3">3D Managed Product Data</p><div className="text-xs text-muted-foreground space-y-1"><div>• Parts Catalog</div><div>• Materials & Properties</div><div>• CAD Geometry</div></div></CardContent></Card><Card className="cursor-pointer hover:shadow-lg transition-all hover:scale-105" onClick={() => navigate('/traceability')}><CardHeader className="pb-3"><div className="flex items-center justify-between"><Badge className="bg-purple-500 text-white">AP243</Badge><ArrowRight className="h-4 w-4 text-muted-foreground" /></div></CardHeader><CardContent><h3 className="font-semibold mb-1">Reference Data</h3><p className="text-sm text-muted-foreground mb-3">Ontologies & Standards</p><div className="text-xs text-muted-foreground space-y-1"><div>• Units & Measurements</div><div>• Classification Systems</div><div>• Cross-Schema Traceability</div></div></CardContent></Card></div></CardContent></Card><Card className="border-dashed"><CardHeader><CardTitle className="flex items-center gap-2"><Database className="h-5 w-5 text-green-500" />System Status</CardTitle></CardHeader><CardContent><div className="grid gap-4 md:grid-cols-4"><div className="space-y-1"><p className="text-sm text-muted-foreground">Platform</p><div className="flex items-center gap-2"><div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" /><p className="font-semibold">Active</p></div></div><div className="space-y-1"><p className="text-sm text-muted-foreground">Database</p><p className="font-semibold">Neo4j Aura</p></div><div className="space-y-1"><p className="text-sm text-muted-foreground">Protocol</p><p className="font-semibold">ISO 10303 SMRL</p></div><div className="space-y-1"><p className="text-sm text-muted-foreground">Security</p><p className="font-semibold">Enterprise</p></div></div></CardContent></Card></div>;
}
