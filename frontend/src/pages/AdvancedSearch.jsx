import { useState, useRef, useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import ForceGraph2D from 'react-force-graph-2d';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@ui/card';
import { Input } from '@ui/input';
import { Button } from '@ui/button';
import { Label } from '@ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@ui/select';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@ui/table';
import { Badge } from '@ui/badge';
import { Skeleton } from '@ui/skeleton';
import { Search, ExternalLink, List, Network, ChevronLeft, ChevronRight, Plus, X, ArrowUpDown, ArrowUp, ArrowDown, Loader2, Download } from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import { toast } from 'sonner';
const ARTIFACT_TYPES = ['All', 'Class', 'Package', 'Property', 'Association', 'Requirement', 'Constraint', 'Enumeration', 'Port', 'Slot', 'InstanceSpecification'];
const NODE_TYPE_PROPERTIES = {
  'All': ['name', 'comment', 'id'],
  'Class': ['name', 'comment', 'qualified_name', 'id', 'isAbstract', 'visibility'],
  'Package': ['name', 'comment', 'qualified_name', 'id', 'uri'],
  'Property': ['name', 'comment', 'qualified_name', 'id', 'aggregation', 'isDerived'],
  'Association': ['name', 'comment', 'qualified_name', 'id', 'isDerived'],
  'Requirement': ['name', 'comment', 'description', 'id', 'status', 'priority'],
  'Constraint': ['name', 'comment', 'specification', 'id'],
  'Enumeration': ['name', 'comment', 'qualified_name', 'id'],
  'Port': ['name', 'comment', 'id', 'direction'],
  'Slot': ['name', 'comment', 'id', 'value'],
  'InstanceSpecification': ['name', 'comment', 'id']
};
const SEARCH_OPERATORS = [{
  value: 'contains',
  label: 'Contains'
}, {
  value: 'equals',
  label: 'Equals'
}, {
  value: 'starts_with',
  label: 'Starts With'
}, {
  value: 'ends_with',
  label: 'Ends With'
}];
const PAGE_SIZE = 25;
export default function AdvancedSearch({ 
    defaultType = 'All', 
    allowedTypes = [], 
    hideTypeSelector = false, 
    title = "Advanced Search",
    enableHeader = true
} = {}) {
  const [searchParams, setSearchParams] = useState({
    type: defaultType,
    name: '',
    comment: ''
  });
  const [viewMode, setViewMode] = useState('table');
  const [currentPage, setCurrentPage] = useState(1);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [sortField, setSortField] = useState('name');
  const [sortOrder, setSortOrder] = useState('asc');
  const [searchCriteria, setSearchCriteria] = useState([{
    id: 1,
    property: 'name',
    operator: 'contains',
    value: '',
    logicOperator: 'AND'
  }]);

  const effectiveArtifactTypes = allowedTypes.length > 0 ? allowedTypes : ARTIFACT_TYPES;
  const availableProperties = NODE_TYPE_PROPERTIES[searchParams.type] || NODE_TYPE_PROPERTIES['All'];
  const addCriterion = () => {
    const newId = Math.max(...searchCriteria.map(c => c.id), 0) + 1;
    setSearchCriteria([...searchCriteria, {
      id: newId,
      property: availableProperties[0],
      operator: 'contains',
      value: '',
      logicOperator: 'AND'
    }]);
  };
  const removeCriterion = id => {
    if (searchCriteria.length > 1) {
      setSearchCriteria(searchCriteria.filter(c => c.id !== id));
    }
  };
  const updateCriterion = (id, field, value) => {
    setSearchCriteria(searchCriteria.map(c => c.id === id ? {
      ...c,
      [field]: value
    } : c));
  };
  const {
    data: results,
    isLoading,
    refetch
  } = useQuery({
    queryKey: ['artifacts', searchParams],
    queryFn: () => apiService.searchArtifacts({
      type: searchParams.type !== 'All' ? searchParams.type : undefined,
      name: searchParams.name || undefined,
      comment: searchParams.comment || undefined,
      limit: 100
    }),
    enabled: false
  });
  const handleSearch = () => {
    setCurrentPage(1);
    refetch();
  };
  const handleReset = () => {
    setSearchParams({
      type: defaultType,
      name: '',
      comment: ''
    });
    setCurrentPage(1);
    setSearchCriteria([{
      id: 1,
      property: 'name',
      operator: 'contains',
      value: '',
      logicOperator: 'AND'
    }]);
  };
  const totalPages = results ? Math.ceil(results.length / PAGE_SIZE) : 0;
  
  const sortedResults = results ? [...results].sort((a, b) => {
    let aVal = a[sortField] || '';
    let bVal = b[sortField] || '';
    aVal = String(aVal).toLowerCase();
    bVal = String(bVal).toLowerCase();
    if (sortOrder === 'asc') {
      return aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
    } else {
      return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
    }
  }) : [];
  const paginatedResults = sortedResults ? sortedResults.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE) : [];
  const handleSort = field => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
    setCurrentPage(1);
  };
  const SortIcon = ({
    field
  }) => {
    if (sortField !== field) {
      return <ArrowUpDown className="h-4 w-4 ml-1 opacity-40" />;
    }
    return sortOrder === 'asc' ? <ArrowUp className="h-4 w-4 ml-1 text-primary" /> : <ArrowDown className="h-4 w-4 ml-1 text-primary" />;
  };
  const goToPage = page => {
    setCurrentPage(Math.max(1, Math.min(page, totalPages)));
  };
  const PaginationControls = () => results && sortedResults.length > PAGE_SIZE ? <div className="flex items-center justify-between py-3 px-4 bg-linear-to-r from-muted/30 to-transparent rounded-lg border"><div className="text-sm text-muted-foreground font-medium">Showing {(currentPage - 1) * PAGE_SIZE + 1} to {Math.min(currentPage * PAGE_SIZE, sortedResults.length)} of {sortedResults.length} results</div><div className="flex items-center gap-2"><Button variant="outline" size="sm" onClick={() => goToPage(currentPage - 1)} disabled={currentPage === 1} className="h-9"><ChevronLeft className="h-4 w-4 mr-1" />Previous</Button><div className="flex items-center gap-1">{Array.from({
          length: Math.min(5, totalPages)
        }, (_, i) => {
          let pageNum;
          if (totalPages <= 5) {
            pageNum = i + 1;
          } else if (currentPage <= 3) {
            pageNum = i + 1;
          } else if (currentPage >= totalPages - 2) {
            pageNum = totalPages - 4 + i;
          } else {
            pageNum = currentPage - 2 + i;
          }
          return <Button key={pageNum} variant={currentPage === pageNum ? "default" : "outline"} size="sm" className="w-9 h-9" onClick={() => goToPage(pageNum)}>{pageNum}</Button>;
        })}{totalPages > 5 && currentPage < totalPages - 2 && <><span className="text-muted-foreground px-1">...</span><Button variant="outline" size="sm" className="w-9 h-9" onClick={() => goToPage(totalPages)}>{totalPages}</Button></>}</div><Button variant="outline" size="sm" onClick={() => goToPage(currentPage + 1)} disabled={currentPage === totalPages} className="h-9">Next<ChevronRight className="h-4 w-4 ml-1" /></Button></div></div> : null;
  const exportToCSV = () => {
    // If results is empty, we just export a CSV with headers
    const dataToExport = (results && results.length > 0) ? results : [{}];
    
    // Determine keys (headers)
    let keys;
    if (results && results.length > 0) {
        keys = Object.keys(results[0]);
    } else {
        // Fallback to available properties if no results
        keys = availableProperties;
    }

    const csv = [keys.join(','), ...dataToExport.map(row => keys.map(key => {
      const value = row[key];
      if (value === null || value === undefined) return '';
      return `"${String(value).replace(/"/g, '""')}"`;
    }).join(','))].join('\n');

    const blob = new Blob([csv], {
      type: 'text/csv'
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `mossec_export_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Results exported to CSV');
  };

  const exportSchema = async () => {
    try {
      // Use direct API path since API_BASE is internal
      // Use apiService.client to ensure auth headers are present, but need to handle full URL
      // Actually fetch is simpler if we include headers.
      // Better: reuse apiService's axios instance but manual GET
      const token = localStorage.getItem('mbse-auth-storage') 
        ? JSON.parse(localStorage.getItem('mbse-auth-storage')).state?.token 
        : null;

      const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
      
      const response = await fetch('/api/export/schema', { headers });
      
      if (!response.ok) throw new Error('Export failed: ' + response.statusText);
      const data = await response.json();
      
      // Check if backend returned error
      if (data.metadata?.error) {
          throw new Error('Backend error: ' + data.metadata.error);
      }

      // Convert Schema JSON to CSV format
      const headersCSV = ['Category', 'Type', 'Count', 'Properties'];
      const rows = [];
      
      // Add Nodes
      if (data.schema?.nodes) {
        data.schema.nodes.forEach(node => {
          rows.push([
            'Node',
            `"${node.label}"`,
            node.count,
            `"${(node.properties || []).join(', ')}"`
          ]);
        });
      }
      
      // Add Relationships
      if (data.schema?.relationships) {
        data.schema.relationships.forEach(rel => {
            rows.push([
                'Relationship',
                `"${rel.type}"`,
                rel.count,
                '""' // Relationships in this API don't have property schema returned yet
            ]);
        });
      }
      
      const csvContent = [
          headersCSV.join(','), 
          ...rows.map(r => r.join(','))
      ].join('\n');

      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `mossec_schema_${new Date().toISOString().split('T')[0]}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Schema exported as CSV');
    } catch (e) {
      toast.error('Failed to export schema: ' + e.message);
      console.error(e);
    }
  };

  const containerClass = enableHeader ? "container mx-auto p-6 space-y-6" : "space-y-6";

  return <div className={containerClass}>{enableHeader && <PageHeader title={title} description="Search for artifacts in the knowledge graph with advanced filtering" icon={<Search className="h-6 w-6 text-primary" />} breadcrumbs={[{
      label: 'Knowledge Graph',
      href: '/graph'
    }, {
      label: 'Search'
    }]} actions={results && <Badge variant="outline">{results.length} {results.length === 1 ? 'result' : 'results'}</Badge>} />}<Card className="card-corporate border-2 shadow-lg"><CardHeader className="border-b bg-linear-to-r from-primary/5 to-primary/10 pb-4"><div className="flex items-center justify-between"><CardTitle className="flex items-center gap-2"><Search className="h-5 w-5 text-primary" />Search Criteria</CardTitle>{isLoading && <Badge variant="outline" className="text-xs"><Loader2 className="h-3 w-3 mr-1 animate-spin" />Searching...</Badge>}</div></CardHeader><CardContent className="pt-6"><div className="space-y-6"><div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3"><div className="space-y-2"><Label htmlFor="type" className="text-sm font-semibold">Artifact Type *</Label>
    {hideTypeSelector ? (
        <div className="p-2 border rounded-md bg-muted/30 font-medium">{searchParams.type}</div>
    ) : (
    <Select value={searchParams.type} onValueChange={value => {
                setSearchParams({
                  ...searchParams,
                  type: value
                });
                setSearchCriteria([{
                  id: 1,
                  property: NODE_TYPE_PROPERTIES[value]?.[0] || 'name',
                  operator: 'contains',
                  value: '',
                  logicOperator: 'AND'
                }]);
              }}><SelectTrigger id="type"><SelectValue /></SelectTrigger><SelectContent>{effectiveArtifactTypes.map(type => <SelectItem key={type} value={type}>{type}</SelectItem>)}</SelectContent></Select>
    )}
    </div></div><div className="space-y-4 mt-6 pt-6 border-t-2"><div className="flex items-center justify-between mb-4"><Label className="text-base font-semibold">Search Criteria</Label><Button variant="outline" size="sm" onClick={addCriterion} className="flex gap-1"><Plus className="h-4 w-4" />Add Criterion</Button></div>{searchCriteria.map((criterion, index) => <div key={criterion.id} className="space-y-3">{index > 0 && <div className="flex items-center gap-2 mb-2"><Select value={criterion.logicOperator} onValueChange={value => updateCriterion(criterion.id, 'logicOperator', value)}><SelectTrigger className="w-24 h-8 bg-primary/10 border-primary/30"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="AND">AND</SelectItem><SelectItem value="OR">OR</SelectItem></SelectContent></Select><div className="h-px flex-1 bg-border" /></div>}<div className="grid gap-3 md:grid-cols-12 items-end bg-muted/30 p-4 rounded-lg border-2"><div className="md:col-span-3 space-y-2"><Label className="text-xs">Property</Label><Select value={criterion.property} onValueChange={value => updateCriterion(criterion.id, 'property', value)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{availableProperties.map(prop => <SelectItem key={prop} value={prop}>{prop.charAt(0).toUpperCase() + prop.slice(1).replace('_', ' ')}</SelectItem>)}</SelectContent></Select></div><div className="md:col-span-3 space-y-2"><Label className="text-xs">Operator</Label><Select value={criterion.operator} onValueChange={value => updateCriterion(criterion.id, 'operator', value)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{SEARCH_OPERATORS.map(op => <SelectItem key={op.value} value={op.value}>{op.label}</SelectItem>)}</SelectContent></Select></div><div className="md:col-span-5 space-y-2"><Label className="text-xs">Value</Label><Input placeholder="Enter search value..." value={criterion.value} onChange={e => updateCriterion(criterion.id, 'value', e.target.value)} onKeyDown={e => e.key === 'Enter' && handleSearch()} /></div><div className="md:col-span-1 flex items-end"><Button variant="ghost" size="sm" onClick={() => removeCriterion(criterion.id)} disabled={searchCriteria.length === 1} className="h-10 w-full text-destructive hover:text-destructive hover:bg-destructive/10"><X className="h-4 w-4" /></Button></div></div></div>)}</div></div><div className="flex items-center justify-between mt-6 pt-6 border-t-2"><div className="flex gap-3"><Button onClick={handleSearch} className="flex gap-2 shadow-md hover:shadow-lg transition-all min-w-[140px]" size="lg"><Search className="h-4 w-4" />Search Now</Button><Button variant="outline" onClick={handleReset} size="lg" className="border-2 min-w-[140px]">Clear All</Button></div>{results && <div className="text-sm text-muted-foreground"><span className="font-semibold text-foreground">{results.length}</span> artifacts match your criteria</div>}</div></CardContent></Card><Card className="card-corporate border-2"><CardHeader className="border-b bg-linear-to-r from-accent/10 to-accent/5"><div className="flex items-center justify-between"><CardTitle>Search Results{results && <span className="ml-2 text-sm font-normal text-muted-foreground">({results.length} found{results.length > PAGE_SIZE ? `, showing ${paginatedResults.length}` : ''})</span>}</CardTitle><div className="flex items-center gap-2">
    <DropdownMenu>
        <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="h-8 gap-1"><Download className="h-3.5 w-3.5" />Export</Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={exportToCSV}>
                Export Results (CSV)
            </DropdownMenuItem>
            <DropdownMenuItem onClick={exportSchema}>
                Export Schema (CSV)
            </DropdownMenuItem>
        </DropdownMenuContent>
    </DropdownMenu>
    <Tabs value={viewMode} onValueChange={v => setViewMode(v)}><TabsList><TabsTrigger value="table" className="flex items-center gap-1"><List className="h-4 w-4" />Table</TabsTrigger><TabsTrigger value="graph" className="flex items-center gap-1"><Network className="h-4 w-4" />Graph</TabsTrigger></TabsList></Tabs></div></div></CardHeader><CardContent>{!isLoading && <PaginationControls />}{isLoading ? <div className="space-y-2 mt-4">{[...Array(5)].map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}</div> : results && results.length > 0 ? <><Tabs value={viewMode}><TabsContent value="table" className="mt-0"><div className="rounded-lg border-2 shadow-sm overflow-hidden"><Table><TableHeader className="bg-muted/50"><TableRow className="hover:bg-muted/50"><TableHead className="cursor-pointer select-none hover:bg-muted transition-colors" onClick={() => handleSort('type')}><div className="flex items-center font-semibold">Type<SortIcon field="type" /></div></TableHead><TableHead className="cursor-pointer select-none hover:bg-muted transition-colors" onClick={() => handleSort('name')}><div className="flex items-center font-semibold">Name<SortIcon field="name" /></div></TableHead><TableHead className="cursor-pointer select-none hover:bg-muted transition-colors" onClick={() => handleSort('id')}><div className="flex items-center font-semibold">UID<SortIcon field="id" /></div></TableHead><TableHead className="cursor-pointer select-none hover:bg-muted transition-colors" onClick={() => handleSort('comment')}><div className="flex items-center font-semibold">Comment<SortIcon field="comment" /></div></TableHead><TableHead className="w-[100px]"><div className="font-semibold">Actions</div></TableHead></TableRow></TableHeader><TableBody>{paginatedResults.map((artifact, index) => <TableRow key={artifact.id || artifact.uid || index}><TableCell><Badge variant="outline">{artifact.type}</Badge></TableCell><TableCell className="font-medium">{artifact.name || '(unnamed)'}</TableCell><TableCell><code className="text-xs">{artifact.id || artifact.uid}</code></TableCell><TableCell className="max-w-md truncate">{artifact.comment || '-'}</TableCell><TableCell><Button variant="ghost" size="sm" disabled={!artifact.id && !artifact.uid} onClick={() => {
                          const artifactId = artifact.id || artifact.uid;
                          const artifactType = artifact.type.toLowerCase();
                          if (artifactId) {
                            if (['class', 'package'].includes(artifactType)) {
                              window.open(`/api/${artifactType}/${encodeURIComponent(artifactId)}`, '_blank');
                            } else {
                              window.alert(`View ${artifact.type} "${artifact.name}" in Graph Browser or use the REST API Explorer to query by ID: ${artifactId}`);
                            }
                          }
                        }}><ExternalLink className="h-4 w-4" /></Button></TableCell></TableRow>)}</TableBody></Table></div></TabsContent><TabsContent value="graph" className="mt-0"><div className="border rounded-lg bg-muted/20 min-h-[500px] relative"><SearchResultsGraph results={paginatedResults} /></div></TabsContent></Tabs><div className="mt-6 pt-4 border-t-2"><PaginationControls /></div></> : <div className="flex h-32 items-center justify-center text-muted-foreground">{results ? 'No results found' : 'Enter search criteria and click Search'}</div>}</CardContent></Card></div>;
}

// Graph visualization component for search results
function SearchResultsGraph({ results }) {
  const fgRef = useRef(null);
  const containerRef = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);
  
  const TYPE_COLORS = {
    'Class': '#22c55e',
    'Package': '#3b82f6',
    'Property': '#f59e0b',
    'Association': '#8b5cf6',
    'Connector': '#ec4899',
    'Constraint': '#ef4444',
    'Port': '#06b6d4',
    'InstanceSpecification': '#14b8a6',
    'XSDComplexType': '#6366f1',
    'XSDElement': '#84cc16',
    'DomainConcept': '#f97316'
  };
  
  const graphData = useMemo(() => {
    if (!results || results.length === 0) return { nodes: [], links: [] };
    
    const nodes = results.map((r, i) => ({
      id: r.id || r.uid || `node-${i}`,
      name: r.name || '(unnamed)',
      type: r.type || 'Unknown',
      val: 3
    }));
    
    // Build links between nodes that share the same type (co-occurrence links)
    const links = [];
    const typeGroups = {};
    nodes.forEach(n => {
      if (!typeGroups[n.type]) typeGroups[n.type] = [];
      typeGroups[n.type].push(n.id);
    });
    Object.values(typeGroups).forEach(group => {
      for (let i = 0; i < group.length - 1 && i < 10; i++) {
        links.push({ source: group[i], target: group[i + 1] });
      }
    });
    
    return { nodes, links };
  }, [results]);
  
  const getNodeColor = useCallback((node) => {
    return TYPE_COLORS[node.type] || '#6b7280';
  }, []);
  
  const handleNodeClick = useCallback((node) => {
    setSelectedNode(node);
    if (fgRef.current) {
      fgRef.current.centerAt(node.x, node.y, 400);
      fgRef.current.zoom(2, 400);
    }
  }, []);
  
  if (!results || results.length === 0) {
    return (
      <div className="flex items-center justify-center h-[500px] text-muted-foreground">
        <Network className="h-8 w-8 mr-2" />
        No results to visualize
      </div>
    );
  }
  
  return (
    <div ref={containerRef} className="relative h-[500px]">
      <ForceGraph2D
        ref={fgRef}
        graphData={graphData}
        width={800}
        height={500}
        nodeLabel={node => `${node.type}: ${node.name}`}
        nodeColor={getNodeColor}
        nodeRelSize={8}
        nodeCanvasObject={(node, ctx, globalScale) => {
          const label = node.name.length > 15 ? node.name.substring(0, 15) + '...' : node.name;
          const fontSize = 10 / globalScale;
          ctx.font = `${fontSize}px Sans-Serif`;
          
          // Draw node circle
          ctx.beginPath();
          ctx.arc(node.x, node.y, 6, 0, 2 * Math.PI);
          ctx.fillStyle = getNodeColor(node);
          ctx.fill();
          
          // Draw label
          ctx.textAlign = 'center';
          ctx.textBaseline = 'top';
          ctx.fillStyle = '#374151';
          ctx.fillText(label, node.x, node.y + 8);
        }}
        onNodeClick={handleNodeClick}
        cooldownTicks={50}
        d3VelocityDecay={0.4}
      />
      {selectedNode && (
        <div className="absolute top-4 left-4 bg-background border rounded-lg p-3 shadow-lg max-w-xs">
          <div className="flex items-center gap-2 mb-2">
            <Badge style={{ backgroundColor: getNodeColor(selectedNode) }}>{selectedNode.type}</Badge>
            <Button variant="ghost" size="sm" className="ml-auto h-6 w-6 p-0" onClick={() => setSelectedNode(null)}>
              <X className="h-4 w-4" />
            </Button>
          </div>
          <div className="text-sm font-medium">{selectedNode.name}</div>
          <div className="text-xs text-muted-foreground mt-1 font-mono">{selectedNode.id}</div>
        </div>
      )}
    </div>
  );
}
