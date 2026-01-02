import { useQuery } from '@tanstack/react-query';
import ForceGraph2D from 'react-force-graph-2d';
import { useRef, useState, useCallback, useMemo, useEffect } from 'react';
import { forceManyBody, forceX, forceY } from 'd3-force';
import { Check, ChevronsUpDown, Loader2, AlertCircle, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { cn } from '@/lib/utils';
const API_BASE = '/api';

function getApiKey() {
  return import.meta.env.VITE_API_KEY;
}
async function fetchJson(url) {
  const apiKey = getApiKey();
  const headers = {
    'Content-Type': 'application/json'
  };

  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }

  const res = await fetch(url, {
    headers
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || `Request failed: ${res.status}`);
  }
  return res.json();
}
export default function GraphBrowser() {
  const fgRef = useRef(null);
  const containerRef = useRef(null);
  const [selectedNodeTypes, setSelectedNodeTypes] = useState([]);
  const [nodeTypeOpen, setNodeTypeOpen] = useState(false);
  const [limit, setLimit] = useState([500]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [hoverNode, setHoverNode] = useState(null);
  const [hoverLink, setHoverLink] = useState(null);
  const [pointer, setPointer] = useState(null);
  const {
    data: nodeTypesData
  } = useQuery({
    queryKey: ['graph-node-types'],
    queryFn: async () => {
      return fetchJson(`${API_BASE}/graph/node-types`);
    }
  });
  const graphParams = useMemo(() => {
    const params = new URLSearchParams();
    if (selectedNodeTypes.length > 0) {
      params.append('node_types', selectedNodeTypes.join(','));
    }
    params.append('limit', limit[0].toString());
    return params.toString();
  }, [selectedNodeTypes, limit]);
  const {
    data: graphData,
    isLoading,
    error
  } = useQuery({
    queryKey: ['graph-data', graphParams],
    queryFn: async () => {
      return fetchJson(`${API_BASE}/graph/data?${graphParams}`);
    },
    refetchOnWindowFocus: false
  });
  const normalizedGraph = useMemo(() => {
    if (!graphData) return null;
    const nodes = (graphData.nodes || []).map(n => ({
      ...n,
      id: String(n.id),
      labels: Array.isArray(n.labels) ? n.labels : []
    }));
    const nodeById = new Map(nodes.map(n => [n.id, n]));
    const links = (graphData.links || []).map(l => {
      const sourceId = typeof l.source === 'string' ? String(l.source) : String(l.source?.id);
      const targetId = typeof l.target === 'string' ? String(l.target) : String(l.target?.id);
      return {
        ...l,
        source: sourceId,
        target: targetId
      };
    }).filter(l => nodeById.has(l.source) && nodeById.has(l.target));
    const neighbors = new Map();
    const addNeighbor = (a, b) => {
      if (!neighbors.has(a)) neighbors.set(a, new Set());
      neighbors.get(a).add(b);
    };
    links.forEach(l => {
      const s = l.source;
      const t = l.target;
      addNeighbor(s, t);
      addNeighbor(t, s);
    });
    return {
      nodes,
      links,
      neighbors,
      metadata: graphData.metadata
    };
  }, [graphData]);
  useEffect(() => {
    if (!fgRef.current || !normalizedGraph) return;
    const nodeTypes = (normalizedGraph.metadata?.node_types || []).filter(t => typeof t === 'string' && t.length > 0).sort();
    const typeIndex = new Map();
    nodeTypes.forEach((t, idx) => typeIndex.set(t, idx));
    const typeCount = Math.max(1, nodeTypes.length);
    const ringRadius = 260;
    const strength = 0.06;
    const fx = forceX(node => {
      const type = String(node.type || 'Unknown');
      const idx = typeIndex.get(type) ?? 0;
      const angle = idx / typeCount * Math.PI * 2;
      return Math.cos(angle) * ringRadius;
    }).strength(strength);
    const fy = forceY(node => {
      const type = String(node.type || 'Unknown');
      const idx = typeIndex.get(type) ?? 0;
      const angle = idx / typeCount * Math.PI * 2;
      return Math.sin(angle) * ringRadius;
    }).strength(strength);
    fgRef.current.d3Force('charge', forceManyBody().strength(-60));
    fgRef.current.d3Force('x', fx);
    fgRef.current.d3Force('y', fy);
    fgRef.current.d3ReheatSimulation();
    setTimeout(() => {
      try {
        fgRef.current.zoomToFit(600, 60);
      } catch {}
    }, 250);
  }, [normalizedGraph]);
  const highlighted = useMemo(() => {
    const focus = selectedNode || hoverNode;
    if (!normalizedGraph || !focus) {
      return {
        focusId: null,
        nodeIds: null,
        linkKeys: null
      };
    }
    const focusId = String(focus.id);
    const nodeIds = new Set([focusId]);
    const nbrs = normalizedGraph.neighbors.get(focusId);
    if (nbrs) {
      nbrs.forEach(id => nodeIds.add(id));
    }
    const linkKeys = new Set();
    normalizedGraph.links.forEach(l => {
      const s = l.source;
      const t = l.target;
      if (nodeIds.has(s) && nodeIds.has(t) && (s === focusId || t === focusId)) {
        linkKeys.add(l.id);
      }
    });
    return {
      focusId,
      nodeIds,
      linkKeys
    };
  }, [normalizedGraph, selectedNode, hoverNode]);
  const availableNodeTypes = useMemo(() => {
    return nodeTypesData?.node_types.filter(nt => nt.count > 0) || [];
  }, [nodeTypesData]);
  const getNodeColor = useCallback(node => {
    const colors = {
      Requirement: '#ef4444',
      Part: '#3b82f6',
      Class: '#8b5cf6',
      Package: '#f59e0b',
      Property: '#10b981',
      Association: '#ec4899',
      Port: '#14b8a6',
      InstanceSpecification: '#6366f1',
      Constraint: '#f97316',
      Material: '#06b6d4',
      Document: '#84cc16',
      Person: '#f43f5e'
    };
    return colors[node.type] || '#6b7280';
  }, []);
  const handleNodeClick = useCallback(node => {
    setSelectedNode(node);
    if (fgRef.current) {
      fgRef.current.centerAt(node.x, node.y, 1000);
      fgRef.current.zoom(2, 1000);
    }
  }, []);
  const handleNodeHover = useCallback(node => {
    setHoverNode(node);
  }, []);
  const handleLinkHover = useCallback(link => {
    setHoverLink(link);
  }, []);
  const handlePointerMove = useCallback(e => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    setPointer({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    });
  }, []);
  const handleZoomIn = () => {
    if (fgRef.current) {
      const currentZoom = fgRef.current.zoom();
      fgRef.current.zoom(currentZoom * 1.5, 500);
    }
  };
  const handleZoomOut = () => {
    if (fgRef.current) {
      const currentZoom = fgRef.current.zoom();
      fgRef.current.zoom(currentZoom / 1.5, 500);
    }
  };
  const handleZoomReset = () => {
    if (fgRef.current) {
      fgRef.current.zoomToFit(500, 50);
    }
  };
  const toggleNodeType = type => {
    setSelectedNodeTypes(prev => prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type]);
  };
  return <div className="flex h-full min-h-[calc(100vh-5rem)] overflow-hidden"><div className="w-80 border-r bg-background overflow-y-auto"><div className="p-6 space-y-6"><div><h2 className="text-2xl font-bold mb-2">Graph Browser</h2><p className="text-sm text-muted-foreground">Visualize MBSE knowledge graph relationships</p></div><div className="space-y-2"><Label>Filter by Node Type</Label><Popover open={nodeTypeOpen} onOpenChange={setNodeTypeOpen}><PopoverTrigger asChild><Button variant="outline" role="combobox" aria-expanded={nodeTypeOpen} className="w-full justify-between">{selectedNodeTypes.length > 0 ? `${selectedNodeTypes.length} selected` : 'All types'}<ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" /></Button></PopoverTrigger><PopoverContent className="w-72 p-0"><Command><CommandInput placeholder="Search node types..." /><CommandList><CommandEmpty>No node type found.</CommandEmpty><CommandGroup>{availableNodeTypes.map(nt => <CommandItem key={nt.type} value={nt.type} onSelect={() => toggleNodeType(nt.type)}><Check className={cn('mr-2 h-4 w-4', selectedNodeTypes.includes(nt.type) ? 'opacity-100' : 'opacity-0')} /><span className="flex-1">{nt.type}</span><span className="text-xs text-muted-foreground">{nt.count}</span></CommandItem>)}</CommandGroup></CommandList></Command></PopoverContent></Popover></div><div className="space-y-2"><Label>Max Nodes: {limit[0]}</Label><Slider value={limit} onValueChange={setLimit} min={50} max={2000} step={50} className="w-full" /><p className="text-xs text-muted-foreground">Limit nodes to improve performance</p></div>{graphData && <Card><CardHeader className="pb-3"><CardTitle className="text-sm">Graph Statistics</CardTitle></CardHeader><CardContent className="text-sm space-y-1"><div className="flex justify-between"><span className="text-muted-foreground">Nodes:</span><span className="font-mono font-semibold">{graphData.metadata.node_count}</span></div><div className="flex justify-between"><span className="text-muted-foreground">Links:</span><span className="font-mono font-semibold">{graphData.metadata.link_count}</span></div><div className="flex justify-between"><span className="text-muted-foreground">Types:</span><span className="font-mono font-semibold">{graphData.metadata.node_types.length}</span></div></CardContent></Card>}<Card><CardHeader className="pb-3"><CardTitle className="text-sm">Node Legend</CardTitle></CardHeader><CardContent className="space-y-1 text-sm">{['Requirement', 'Part', 'Class', 'Package', 'Property', 'Association'].map(type => <div key={type} className="flex items-center gap-2"><div className="w-3 h-3 rounded-full" style={{
                backgroundColor: getNodeColor({
                  type
                })
              }} /><span>{type}</span></div>)}<div className="flex items-center gap-2 pt-1"><div className="w-3 h-3 rounded-full bg-gray-500" /><span className="text-muted-foreground">Other types</span></div></CardContent></Card></div></div><div className="flex-1 relative" ref={containerRef} onPointerMove={handlePointerMove}><div className="absolute top-4 right-4 z-10 flex gap-2"><Button variant="outline" size="icon" onClick={handleZoomIn}><ZoomIn className="h-4 w-4" /></Button><Button variant="outline" size="icon" onClick={handleZoomOut}><ZoomOut className="h-4 w-4" /></Button><Button variant="outline" size="icon" onClick={handleZoomReset}><Maximize2 className="h-4 w-4" /></Button></div>{isLoading && <div className="absolute inset-0 flex items-center justify-center bg-background/80 backdrop-blur-sm z-20"><div className="text-center space-y-4"><Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" /><p className="text-sm text-muted-foreground">Loading graph data...</p></div></div>}{error && <div className="absolute inset-0 flex items-center justify-center bg-background z-20"><Card className="max-w-md"><CardHeader><div className="flex items-center gap-2"><AlertCircle className="h-5 w-5 text-destructive" /><CardTitle>Failed to Load Graph</CardTitle></div><CardDescription>{error instanceof Error ? error.message : 'Unknown error'}</CardDescription></CardHeader></Card></div>}{normalizedGraph && !isLoading && !error && <ForceGraph2D ref={fgRef} graphData={{
        nodes: normalizedGraph.nodes,
        links: normalizedGraph.links
      }} nodeLabel={() => ''} nodeColor={getNodeColor} nodeRelSize={6} nodeCanvasObject={(node, ctx, globalScale) => {
        const id = String(node.id);
        const isFocused = highlighted.focusId === id;
        const isNeighbor = highlighted.nodeIds ? highlighted.nodeIds.has(id) : true;
        const dim = highlighted.nodeIds ? !isNeighbor : false;
        const baseColor = getNodeColor(node);
        const radius = isFocused ? 8 : 6;
        ctx.globalAlpha = dim ? 0.18 : 1;
        ctx.fillStyle = baseColor;
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
        ctx.fill();
        if (isFocused || hoverNode && String(hoverNode.id) === id) {
          ctx.globalAlpha = 1;
          ctx.lineWidth = 2;
          ctx.strokeStyle = '#0f172a';
          ctx.beginPath();
          ctx.arc(node.x, node.y, radius + 2, 0, 2 * Math.PI, false);
          ctx.stroke();
        }
        if (globalScale >= 1.6 && !dim) {
          const label = node.name || node.id;
          const fontSize = 12 / globalScale;
          ctx.font = `${fontSize}px ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'top';
          ctx.fillStyle = '#0f172a';
          ctx.globalAlpha = 0.95;
          ctx.fillText(label, node.x, node.y + radius + 3);
        }
        ctx.globalAlpha = 1;
      }} onNodeClick={handleNodeClick} onNodeHover={handleNodeHover} onLinkHover={handleLinkHover} linkDirectionalParticles={2} linkDirectionalParticleWidth={2} linkColor={l => {
        const id = String(l.id);
        const dim = highlighted.linkKeys ? !highlighted.linkKeys.has(id) : false;
        return dim ? 'rgba(148, 163, 184, 0.20)' : 'rgba(100, 116, 139, 0.85)';
      }} linkWidth={l => {
        const id = String(l.id);
        return highlighted.linkKeys && highlighted.linkKeys.has(id) ? 2.6 : 1.2;
      }} linkDirectionalArrowLength={3} linkDirectionalArrowRelPos={1} cooldownTicks={100} warmupTicks={100} d3VelocityDecay={0.3} enableZoomInteraction enablePanInteraction enableNodeDrag />}{(hoverNode || hoverLink) && pointer && <div className="absolute z-20 pointer-events-none" style={{
        left: pointer.x + 12,
        top: pointer.y + 12,
        maxWidth: 320
      }}><Card className="shadow-lg"><CardHeader className="py-3"><CardTitle className="text-sm">{hoverNode ? hoverNode.name || hoverNode.id : 'Relationship'}</CardTitle><CardDescription className="text-xs">{hoverNode ? hoverNode.type : hoverLink?.type}</CardDescription></CardHeader><CardContent className="py-3 text-xs text-muted-foreground space-y-1">{hoverNode ? <><div><span className="font-medium text-foreground">ID:</span> {hoverNode.id}</div>{hoverNode.ap_schema && <div><span className="font-medium text-foreground">Schema:</span> {hoverNode.ap_schema}</div>}{hoverNode.status && <div><span className="font-medium text-foreground">Status:</span> {hoverNode.status}</div>}</> : <><div><span className="font-medium text-foreground">From:</span> {String(hoverLink?.source)}</div><div><span className="font-medium text-foreground">To:</span> {String(hoverLink?.target)}</div></>}</CardContent></Card></div>}{selectedNode && <Card className="absolute bottom-4 left-4 w-80 z-10"><CardHeader><div className="flex items-center justify-between"><CardTitle className="text-base">{selectedNode.name}</CardTitle><Button variant="ghost" size="icon" onClick={() => setSelectedNode(null)}>×</Button></div><CardDescription>{selectedNode.type}</CardDescription></CardHeader><CardContent className="space-y-2 text-sm">{selectedNode.description && <div><span className="font-medium">Description:</span><p className="text-muted-foreground mt-1">{selectedNode.description}</p></div>}<div><span className="font-medium">Labels:</span><div className="flex flex-wrap gap-1 mt-1">{selectedNode.labels.map(label => <span key={label} className="px-2 py-0.5 bg-secondary text-secondary-foreground rounded text-xs">{label}</span>)}</div></div>{selectedNode.status && <div><span className="font-medium">Status:</span><span className="ml-2 text-muted-foreground">{selectedNode.status}</span></div>}{selectedNode.ap_schema && <div><span className="font-medium">Schema:</span><span className="ml-2 text-muted-foreground">{selectedNode.ap_schema}</span></div>}</CardContent></Card>}</div></div>;
}
