import { useQuery } from '@tanstack/react-query';
import { graphqlService } from '@/services/graphql';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@ui/card';
import { Skeleton } from '@ui/skeleton';
import { Alert, AlertDescription } from '@ui/alert';
import { Button } from '@ui/button';
import { Badge } from '@ui/badge';
import { Popover, PopoverContent, PopoverTrigger } from '@ui/popover';
import { Database, Activity, Search, Terminal, FileText, ArrowRight, Sparkles, LayoutDashboard, PieChart as PieChartIcon, BarChart3, Info } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import PageHeader from '@/components/PageHeader';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';

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
    return <div className="container mx-auto p-6 space-y-6"><PageHeader title="Dashboard" description="Overview of your knowledge graph and system analytics" icon={<LayoutDashboard className="h-6 w-6 text-primary" />} /><div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">{[...Array(4)].map((_, i) => <Card key={i}><CardHeader className="pb-2"><Skeleton className="h-4 w-24" /></CardHeader><CardContent><Skeleton className="h-8 w-16" /></CardContent></Card>)}</div></div>;
  }
  if (error) {
    return <div className="container mx-auto p-6 space-y-6"><PageHeader title="Dashboard" description="Overview of your knowledge graph and system analytics" icon={<LayoutDashboard className="h-6 w-6 text-primary" />} /><Alert variant="destructive"><AlertDescription>Failed to load statistics. Please check your connection and try again.</AlertDescription></Alert></div>;
  }
  const nodeTypes = Object.entries(stats?.node_types || {}).sort(([, a], [, b]) => b - a);
  const relationshipTypes = Object.entries(stats?.relationship_types || {}).sort(([, a], [, b]) => b - a);

  // Prepare chart data
  const nodeChartData = nodeTypes.slice(0, 10).map(([name, value]) => ({ name, value }));
  const relChartData = relationshipTypes.slice(0, 5).map(([name, value]) => ({ name, value }));
  
  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d', '#ffc658', '#8dd1e1', '#a4de6c', '#d0ed57'];

  const nodeGradientClasses = ['from-blue-400 to-blue-500', 'from-blue-500 to-blue-600', 'from-blue-600 to-blue-700'];
  const relationshipGradientClasses = ['from-indigo-400 to-indigo-500', 'from-indigo-500 to-indigo-600', 'from-indigo-600 to-indigo-700'];
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
    color: nodeGradientClasses[idx % nodeGradientClasses.length]
  })), ...relationshipTypes.slice(0, 8).map(([type, count], idx) => ({
    id: `rel-${type}`,
    symbol: type.substring(0, 3).toUpperCase(),
    name: type,
    value: count,
    category: 'relationship',
    color: relationshipGradientClasses[idx % relationshipGradientClasses.length]
  }))];
  return <div className="container mx-auto p-6 space-y-6"><PageHeader title="Dashboard" description="Overview of your knowledge graph and system analytics" icon={<LayoutDashboard className="h-6 w-6 text-primary" />} /><div className="relative overflow-hidden rounded-2xl bg-linear-to-br from-primary/10 via-primary/5 to-background border-2 border-primary/20 shadow-lg p-8"><div className="absolute top-0 right-0 -mt-8 -mr-8 h-40 w-40 rounded-full bg-primary/10 blur-3xl" /><div className="absolute bottom-0 left-0 -mb-8 -ml-8 h-40 w-40 rounded-full bg-primary/10 blur-3xl" /><div className="relative"><div className="flex items-center gap-4 mb-4"><div className="h-16 w-16 rounded-2xl bg-linear-to-br from-primary to-primary/80 flex items-center justify-center shadow-lg"><Database className="h-8 w-8 text-primary-foreground" /></div><div><div className="flex items-center gap-3"><h1 className="text-4xl font-bold tracking-tight">Knowledge Graph Dashboard</h1><Badge className="bg-green-500 text-white">Online</Badge></div><p className="text-lg text-muted-foreground">Periodic table view of system components</p></div></div></div></div><div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {gridItems.map((item, index) => (
          <Card key={item.id || index} className="group overflow-hidden hover:shadow-md transition-all">
            <div className={`h-1.5 w-full bg-linear-to-r ${item.color}`} />
            <div className="flex items-center justify-between p-4">
              <div className="flex items-center gap-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted text-muted-foreground font-semibold text-sm border">
                    {item.symbol}
                </div>
                <div>
                  <div className="font-semibold">{item.name}</div>
                  <div className="text-xs text-muted-foreground flex items-center gap-1.5">
                    <Badge variant="outline" className="text-[10px] px-1 py-0 h-4">{item.category === 'system' ? 'SYS' : item.category === 'node' ? 'NOD' : 'REL'}</Badge>
                    <span>• {item.value.toLocaleString()} items</span>
                  </div>
                </div>
              </div>
              
              <Popover>
                <PopoverTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-primary">
                    <BarChart3 className="h-4 w-4" />
                    <span className="sr-only">View Chart</span>
                  </Button>
                </PopoverTrigger>
            <PopoverContent className="w-80" align="end">
              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between">
                    <h4 className="font-semibold leading-none">{item.name}</h4>
                    <Badge variant={item.category === 'system' ? 'default' : 'secondary'}>{item.symbol}</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">
                    {item.category === 'system' ? 'System Metric' : item.category === 'node' ? 'Node Type Classification' : 'Relationship Type Classification'}
                  </p>
                </div>
                
                <div className="h-[180px] w-full border rounded-lg p-2 bg-muted/20">
                    <ResponsiveContainer width="100%" height="100%">
                      {(item.id === 'total-nodes' || item.id === 'node-types') ? (
                          <BarChart data={nodeChartData}>
                            <XAxis dataKey="name" hide />
                            <Tooltip cursor={{fill: 'transparent'}} contentStyle={{ fontSize: '12px' }} />
                            <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                          </BarChart>
                      ) : (item.id === 'total-rels' || item.id === 'rel-types') ? (
                          <PieChart>
                            <Pie data={relChartData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={40} outerRadius={60} fill="#8884d8">
                               {relChartData.map((entry, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
                            </Pie>
                            <Tooltip contentStyle={{ fontSize: '12px' }} />
                          </PieChart>
                      ) : (
                          <PieChart>
                            <Pie 
                                data={[
                                  { name: item.name, value: item.value }, 
                                  { name: 'Others', value: (item.category === 'node' ? (stats?.total_nodes || 0) : (stats?.total_relationships || 0)) - item.value }
                                ]} 
                                dataKey="value" 
                                nameKey="name" 
                                cx="50%" 
                                cy="50%" 
                                innerRadius={40} 
                                outerRadius={60} 
                                startAngle={90}
                                endAngle={-270}
                            >
                              <Cell fill={item.category === 'node' ? '#3b82f6' : '#8b5cf6'} />
                              <Cell fill="#e5e7eb" />
                            </Pie>
                            <Tooltip contentStyle={{ fontSize: '12px' }} />
                            <Legend verticalAlign="bottom" height={36} iconType="circle" />
                          </PieChart>
                      )}
                    </ResponsiveContainer>
                </div>

                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="flex flex-col p-2.5 bg-muted rounded-lg">
                    <span className="text-[10px] uppercase text-muted-foreground font-semibold mb-1">Quantitative</span>
                    <span className="font-mono font-bold text-lg">{item.value.toLocaleString()}</span>
                    <span className="text-[10px] text-muted-foreground">
                      {item.category === 'system' ? 'Total Count' : `${((item.value / (item.category === 'node' ? (stats?.total_nodes || 1) : (stats?.total_relationships || 1))) * 100).toFixed(1)}% of Total`}
                    </span>
                  </div>
                    <div className="flex flex-col p-2.5 bg-muted rounded-lg">
                    <span className="text-[10px] uppercase text-muted-foreground font-semibold mb-1">Qualitative</span>
                    <div className="flex items-center gap-2 mt-1">
                      <div className={`h-2 w-2 rounded-full ${item.value > 1000 ? 'bg-green-500' : item.value > 100 ? 'bg-yellow-500' : 'bg-blue-500'}`} />
                      <span className="font-medium">
                        {item.value > 1000 ? 'High Volume' : item.value > 100 ? 'Medium Volume' : 'Standard'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </PopoverContent>
              </Popover>
            </div>
          </Card>
        ))}
      </div>

      <Card><CardHeader><CardTitle className="flex items-center gap-2"><Activity className="h-5 w-5 text-primary" />Quick Actions</CardTitle></CardHeader><CardContent><div className="grid grid-cols-2 md:grid-cols-4 gap-3"><Button variant="outline" className="h-20 flex flex-col gap-2 hover:bg-primary hover:text-primary-foreground transition-colors" onClick={() => navigate('/search')}><Search className="h-5 w-5" /><span className="text-sm font-medium">Search</span></Button><Button variant="outline" className="h-20 flex flex-col gap-2 hover:bg-primary hover:text-primary-foreground transition-colors" onClick={() => navigate('/query-editor')}><Terminal className="h-5 w-5" /><span className="text-sm font-medium">Query</span></Button><Button variant="outline" className="h-20 flex flex-col gap-2 hover:bg-primary hover:text-primary-foreground transition-colors" onClick={() => navigate('/requirements')}><FileText className="h-5 w-5" /><span className="text-sm font-medium">Requirements</span></Button><Button variant="outline" className="h-20 flex flex-col gap-2 hover:bg-primary hover:text-primary-foreground transition-colors" onClick={() => navigate('/api-explorer')}><Activity className="h-5 w-5" /><span className="text-sm font-medium">API</span></Button></div></CardContent></Card><Card className="border-2 border-primary/20 bg-linear-to-br from-primary/5 to-background"><CardHeader><CardTitle className="flex items-center gap-2"><Sparkles className="h-5 w-5 text-primary" />ISO 10303 Application Protocols</CardTitle><CardDescription>Access standardized engineering data across the product lifecycle</CardDescription></CardHeader><CardContent><div className="grid md:grid-cols-3 gap-4"><Card className="cursor-pointer hover:shadow-lg transition-all hover:scale-105" onClick={() => navigate('/ap239/requirements')}><CardHeader className="pb-3"><div className="flex items-center justify-between"><Badge className="bg-blue-500 text-white">AP239</Badge><ArrowRight className="h-4 w-4 text-muted-foreground" /></div></CardHeader><CardContent><h3 className="font-semibold mb-1">Requirements</h3><p className="text-sm text-muted-foreground mb-3">Product Life Cycle Support</p><div className="text-xs text-muted-foreground space-y-1"><div>• Requirements Management</div><div>• Analysis & Specifications</div><div>• Change Control & Approvals</div></div></CardContent></Card><Card className="cursor-pointer hover:shadow-lg transition-all hover:scale-105" onClick={() => navigate('/ap242/parts')}><CardHeader className="pb-3"><div className="flex items-center justify-between"><Badge className="bg-green-500 text-white">AP242</Badge><ArrowRight className="h-4 w-4 text-muted-foreground" /></div></CardHeader><CardContent><h3 className="font-semibold mb-1">Parts & Engineering</h3><p className="text-sm text-muted-foreground mb-3">3D Managed Product Data</p><div className="text-xs text-muted-foreground space-y-1"><div>• Parts Catalog</div><div>• Materials & Properties</div><div>• CAD Geometry</div></div></CardContent></Card><Card className="cursor-pointer hover:shadow-lg transition-all hover:scale-105" onClick={() => navigate('/mossec-dashboard')}><CardHeader className="pb-3"><div className="flex items-center justify-between"><Badge className="bg-purple-500 text-white">AP243</Badge><ArrowRight className="h-4 w-4 text-muted-foreground" /></div></CardHeader><CardContent><h3 className="font-semibold mb-1">MoSSEC</h3><p className="text-sm text-muted-foreground mb-3">Co-simulation & Analysis</p><div className="text-xs text-muted-foreground space-y-1"><div>• Model Instances</div><div>• Study Scenarios</div><div>• Process Traceability</div></div></CardContent></Card></div></CardContent></Card><Card className="border-dashed"><CardHeader><CardTitle className="flex items-center gap-2"><Database className="h-5 w-5 text-green-500" />System Status</CardTitle></CardHeader><CardContent><div className="grid gap-4 md:grid-cols-4"><div className="space-y-1"><p className="text-sm text-muted-foreground">Platform</p><div className="flex items-center gap-2"><div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" /><p className="font-semibold">Active</p></div></div><div className="space-y-1"><p className="text-sm text-muted-foreground">Database</p><p className="font-semibold">Neo4j Aura</p></div><div className="space-y-1"><p className="text-sm text-muted-foreground">Protocol</p><p className="font-semibold">ISO 10303 SMRL</p></div><div className="space-y-1"><p className="text-sm text-muted-foreground">Security</p><p className="font-semibold">Enterprise</p></div></div></CardContent></Card></div>;
}
