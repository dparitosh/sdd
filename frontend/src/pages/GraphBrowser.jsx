import { useRef, useState, useCallback, useMemo, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import ForceGraph2D from 'react-force-graph-2d';
import { forceManyBody, forceX, forceY, forceCollide } from 'd3';
import { Check, ChevronsUpDown, Loader2, AlertCircle, ZoomIn, ZoomOut, Maximize2, Pause, Play, Search, X, Network, Share2, Layers } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { cn } from '@/lib/utils';
import { apiService } from '@/services/api';

const GRAPH_VIEWS = {
  ENTERPRISE: {
    id: 'ENTERPRISE',
    label: 'Enterprise Knowledge Graph',
    description: 'Unified view of all engineering disciplines (PLCS, Design, Simulation)',
    apLevel: null,
    fixedNodeTypes: [],
    icon: Network
  },
  AP239: {
    id: 'AP239',
    label: 'AP239 (PLCS)',
    description: 'Product Life Cycle Support & Maintenance',
    apLevel: 'AP239',
    fixedNodeTypes: [],
    icon: Layers
  },
  AP242: {
    id: 'AP242',
    label: 'AP242 (Design)',
    description: 'Managed Model Based 3D Engineering',
    apLevel: 'AP242',
    fixedNodeTypes: [],
    icon: Layers
  },
  AP243: {
    id: 'AP243',
    label: 'AP243 (MoSSEC)',
    description: 'Simulation & Analysis Context',
    apLevel: 'AP243',
    fixedNodeTypes: [],
    icon: Layers
  },
  ONTOLOGY: {
    id: 'ONTOLOGY',
    label: 'Semantic Ontology',
    description: 'Data definitions & Metamodels (T-Box)',
    apLevel: null,
    fixedNodeTypes: ['Ontology', 'OntologyClass', 'OntologyProperty', 'OWLClass', 'OWLProperty'],
    icon: Share2
  },
  OSLC: {
    id: 'OSLC',
    label: 'OSLC Integration',
    description: 'Linked Data Services & Connectors',
    apLevel: null,
    fixedNodeTypes: ['ServiceProvider', 'Service', 'Catalog', 'CreationFactory', 'QueryCapability', 'Link', 'ExternalModel'],
    icon: Network
  }
};

export default function GraphBrowser({ initialView = 'ENTERPRISE' }) {
  const fgRef = useRef(null);
  const containerRef = useRef(null);
  
  const [currentViewId, setCurrentViewId] = useState(initialView);
  const currentView = GRAPH_VIEWS[currentViewId] || GRAPH_VIEWS.ENTERPRISE;
  
  // Create derived state from the current view configuration
  const fixedNodeTypes = currentView.fixedNodeTypes;
  const apLevel = currentView.apLevel;
  
  const [selectedNodeTypes, setSelectedNodeTypes] = useState(fixedNodeTypes);
  
  // When view changes, update selection state
  useEffect(() => {
    setSelectedNodeTypes(currentView.fixedNodeTypes);
    // Reset other states if needed
    setSearchQuery("");
    setSelectedNode(null);
  }, [currentViewId]);

  const [nodeTypeOpen, setNodeTypeOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [layoutDone, setLayoutDone] = useState(false);
  const [layoutActive, setLayoutActive] = useState(true); // Start active so graph lays out
  const graphIdRef = useRef(null); // Track which graph we've laid out
  
  const toggleLayout = useCallback(() => {
    if (!fgRef.current) return;
    if (layoutActive) {
        // Stop the simulation by cooling it down immediately
        fgRef.current.d3AlphaTarget(0);
        // Increase decay to stop movement quickly
        fgRef.current.d3VelocityDecay(1);
        
        setLayoutActive(false);
        setLayoutDone(true);
    } else {
        // Resume simulation
        fgRef.current.d3VelocityDecay(0.3); // Reset decay
        fgRef.current.d3AlphaDecay(0.0228); // Standard alpha decay
        fgRef.current.resumeAnimation(); // Ensure animation loop is running
        fgRef.current.d3ReheatSimulation(); // Restart physics
        setLayoutActive(true);
        setLayoutDone(false);
    }
  }, [layoutActive]);

  const [limit, setLimit] = useState([500]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [hoverNode, setHoverNode] = useState(null);
  const [hoverLink, setHoverLink] = useState(null);
  const [pointer, setPointer] = useState({ x: 0, y: 0 });
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  // Memoised tooltip properties for hover node
  const hoverTooltipProps = useMemo(() => {
    if (!hoverNode) return null;
    const props = {
      ...(hoverNode.description ? { description: hoverNode.description } : {}),
      ...(hoverNode.status ? { status: hoverNode.status } : {}),
      ...(hoverNode.priority ? { priority: hoverNode.priority } : {}),
      ...(hoverNode.ap_schema ? { schema: hoverNode.ap_schema } : {}),
      ...(hoverNode.ap_level ? { level: hoverNode.ap_level } : {}),
      ...(hoverNode.properties || {}),
    };
    return Object.keys(props).length > 0 ? props : null;
  }, [hoverNode]);

  useEffect(() => {
    if (!containerRef.current) return;
    
    const el = containerRef.current;
    
    // Measure container dimensions
    const measure = () => {
      if (!el) return;
      const { clientWidth, clientHeight } = el;
      if (clientWidth > 0 && clientHeight > 0) {
        setDimensions({ width: clientWidth, height: clientHeight });
      }
    };
    
    measure();

    const ro = new ResizeObserver(() => measure());
    ro.observe(el);
    
    return () => ro.disconnect();
  }, []);

  const {
    data: nodeTypesData
  } = useQuery({
    queryKey: ['graph-node-types'],
    queryFn: () => apiService.graph.getNodeTypes()
  });

  const {
    data: graphData,
    isLoading,
    error
  } = useQuery({
    queryKey: ['graph-data', selectedNodeTypes, limit, apLevel],
    queryFn: () => {
      const params = {};
      if (selectedNodeTypes.length > 0) {
        params.node_types = selectedNodeTypes.join(',');
      }
      params.limit = limit[0];
      if (apLevel) {
        params.ap_level = apLevel;
      }
      return apiService.graph.getData(params);
    },
    refetchOnWindowFocus: false
  });
  const normalizedGraph = useMemo(() => {
    if (!graphData) return null;
    const nodes = (graphData.nodes || []).map(n => {
      // Pre-compute universal search terms
      // Includes: Name, ID, Type, Labels, and all Property Values
      const searchTerms = [
        n.id,
        n.name,
        n.type,
        ...(Array.isArray(n.labels) ? n.labels : []),
        // Convert all property values to string for search
        ...Object.entries(n.properties || {}).map(([k, v]) => `${k} ${v}`)
      ].filter(Boolean).join(" ").toLowerCase();

      return {
        ...n,
        id: String(n.id),
        labels: Array.isArray(n.labels) ? n.labels : [],
        searchLabel: searchTerms
      };
    });
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
    
    // Create a unique ID for this graph configuration
    const graphId = `${selectedNodeTypes.join(',')}-${limit[0]}-${normalizedGraph.nodes.length}`;
    
    // Only set up forces and reheat if this is a new graph
    if (graphIdRef.current === graphId) return;
    graphIdRef.current = graphId;
    setLayoutDone(false);
    setLayoutActive(true);
    
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
    fgRef.current.d3Force('charge', forceManyBody().strength(-80));
    fgRef.current.d3Force('x', fx);
    fgRef.current.d3Force('y', fy);
    // Add collision force to prevent overlap
    fgRef.current.d3Force('collide', forceCollide().radius(8).strength(0.5));
    
    // Cooldown improvements:
    // Reheat simulation with specific alpha to smooth out initial burst
    fgRef.current.d3ReheatSimulation();
    
    // Auto-fit view after layout stabilizes
    // Using a longer timeout to allow force layout to settle better
    setTimeout(() => {
      try {
        if (fgRef.current) {
          fgRef.current.zoomToFit(600, 60);
        }
      } catch {}
    }, 1200); // 1.2s delay for initial settle
  }, [normalizedGraph, selectedNodeTypes, limit]);
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
      // After force-graph runs, source/target become object refs; extract id safely
      const s = typeof l.source === 'object' ? String(l.source?.id) : String(l.source);
      const t = typeof l.target === 'object' ? String(l.target?.id) : String(l.target);
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
    // When an apLevel is active, derive types from actual loaded graph data
    // so the sidebar only shows entity types present at that AP level
    if (apLevel && normalizedGraph?.nodes?.length > 0) {
      const typeCounts = {};
      for (const n of normalizedGraph.nodes) {
        const t = n.type || 'Unknown';
        typeCounts[t] = (typeCounts[t] || 0) + 1;
      }
      return Object.entries(typeCounts)
        .map(([type, count]) => ({ type, count }))
        .sort((a, b) => a.type.localeCompare(b.type));
    }
    return (nodeTypesData?.node_types.filter(nt => nt.count > 0) || [])
      .sort((a, b) => a.type.localeCompare(b.type));
  }, [nodeTypesData, apLevel, normalizedGraph]);
  const getNodeColor = useCallback(node => {
    const type = String(node.type || 'Unknown');

    // AP243 (MoSSEC) - Blue/Purple Scheme
    if (['ModelInstance', 'Study', 'Context', 'ModelType', 'AssociativeModelNetwork'].includes(type)) return '#3b82f6'; // Blue
    if (['ActualActivity', 'MethodActivity', 'Method', 'Result'].includes(type)) return '#8b5cf6'; // Purple

    // AP242 (CAD) - Red/Orange Scheme
    if (['Part', 'Assembly', 'Component'].includes(type)) return '#ef4444'; // Red
    if (['Position', 'Shape'].includes(type)) return '#f97316'; // Orange

    // AP239 (PLCS) - Green/Teal Scheme
    if (type === 'Requirement') return '#10b981'; // Emerald
    if (['Verification', 'WorkOrder'].includes(type)) return '#14b8a6'; // Teal
    
    // General type colors (only for types not matched above)
    const colors = {
      // AP242 (CAD) - Red/Orange Scheme
      Part: '#ef4444', 
      Assembly: '#b91c1c', 
      Component: '#f87171',
      Shape: '#f97316',
      GeometricModel: '#c2410c',

      // AP239 (PLCS) - Green/Teal Scheme
      Requirement: '#10b981', 
      WorkOrder: '#059669',
      Activity: '#34d399',
      Resource: '#047857',
      Breakdown: '#6ee7b7',

      // AP243 (MoSSEC) - Blue/Purple Scheme
      Study: '#3b82f6', 
      Model: '#2563eb',
      Analysis: '#1d4ed8',
      Scenario: '#60a5fa',
      Result: '#93c5fd',

      // Ontology & Metadata
      Class: '#8b5cf6',
      Property: '#d946ef',
      Association: '#ec4899',
      Ontology: '#0284c7',
      OntologyClass: '#7c3aed',
      OntologyProperty: '#059669',
      
      // OSLC
      ServiceProvider: '#e11d48',
      Service: '#be123c',
      Catalog: '#9f1239',
      Link: '#fb7185',
      
      // Generic & UML
      Package: '#f59e0b',
      Port: '#14b8a6',
      InstanceSpecification: '#6366f1',
      Constraint: '#f97316',
      Material: '#06b6d4',
      Document: '#84cc16',
      Person: '#f43f5e',
      Comment: '#94a3b8',
      
      MBSEElement: '#64748b',
      Connector: '#a855f7',
      Generalization: '#d946ef',
      // XSD Schema types
      XSDSchema: '#0369a1',
      XSDComplexType: '#b45309',
      XSDSimpleType: '#a16207',
      XSDElement: '#0d9488',
      XSDAttribute: '#7c3aed',
      XSDGroup: '#be185d',
      XSDAttributeGroup: '#9d174d',
      // OWL Ontology Layer types
      OWLClass: '#2563eb',
      OWLObjectProperty: '#dc2626',
      OWLDatatypeProperty: '#16a34a',
      OWLProperty: '#6d28d9'
    };
    return colors[type] || '#6b7280';
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
  const isFixedMode = fixedNodeTypes && fixedNodeTypes.length > 0;

  // Empty state message based on current view
  const emptyMessage = useMemo(() => {
    if (selectedNodeTypes.length > 0) {
      return `No nodes found for the selected type filter(s). Try removing filters or increasing the node limit.`;
    }
    if (apLevel) {
      return `No ${currentView.label} data found in the knowledge graph. Ensure the ${apLevel} schema has been ingested.`;
    }
    return 'No graph data available. Try adjusting filters or importing data.';
  }, [selectedNodeTypes, apLevel, currentView.label]);
  
  // Available types for dropdown - if fixed mode, use fixed list, otherwise use API types
  const dropdownTypes = isFixedMode 
      ? fixedNodeTypes.map(t => ({ type: t, count: null })).sort((a, b) => a.type.localeCompare(b.type))
      : availableNodeTypes;

  const toggleNodeType = useCallback((typeInput) => {
    // cmdk lowercases values, so we need to find the original case
    // First check if it's already in the dropdown list (exact match)
    const exactMatch = dropdownTypes.find(t => t.type === typeInput);
    // If not found, try case-insensitive match
    const caseInsensitiveMatch = dropdownTypes.find(t => 
      t.type.toLowerCase() === String(typeInput).toLowerCase()
    );
    const typeStr = exactMatch?.type || caseInsensitiveMatch?.type || String(typeInput);
    
    setSelectedNodeTypes(prev => {
        // Handle selection toggle
        const exists = prev.includes(typeStr);
        // If it exists, remove it. If not, add it.
        const newSelection = exists 
            ? prev.filter(t => t !== typeStr) 
            : [...prev, typeStr];
        return newSelection;
    });
  }, [dropdownTypes]);

  const legendTypes = useMemo(() => {
    if (selectedNodeTypes.length > 0) {
      // If we have specific types selected (or fixed), show those
      return selectedNodeTypes.slice(0, 8); // Limit to top 8 to avoid clogging UI
    }
    // Show actual types present in the loaded graph data
    if (normalizedGraph?.nodes?.length > 0) {
      const typeCounts = {};
      for (const n of normalizedGraph.nodes) {
        const t = n.type || 'Unknown';
        typeCounts[t] = (typeCounts[t] || 0) + 1;
      }
      return Object.entries(typeCounts)
        .sort((a, b) => b[1] - a[1]) // Sort by count descending
        .slice(0, 10)
        .map(([type]) => type);
    }
    // Default fallback
    return ['Requirement', 'Part', 'Class', 'Package', 'Property', 'Association'];
  }, [selectedNodeTypes, normalizedGraph]);

  return (
    <div className="flex h-full w-full overflow-hidden">
      {/* ── Sidebar ── */}
      <div className="w-80 border-r bg-background overflow-y-auto">
        <div className="p-6 space-y-6">
          {/* View Selector (Replaces Title) */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
                {currentView.icon && (
                    <div className="p-2 bg-primary/10 rounded-md">
                        <currentView.icon className="h-5 w-5 text-primary" />
                    </div>
                )}
                <div>
                    <h2 className="text-lg font-bold leading-tight">{currentView.label}</h2>
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">
                        {currentViewId === 'ENTERPRISE' ? 'Global View' : 'Focus Area'}
                    </p>
                </div>
            </div>
            
            <Select value={currentViewId} onValueChange={(val) => {
                setCurrentViewId(val);
                // Reset limit for larger views if needed, or keep user preference
            }}>
                <SelectTrigger className="w-full h-9">
                    <SelectValue placeholder="Switch View..." />
                </SelectTrigger>
                <SelectContent>
                    {Object.values(GRAPH_VIEWS).map((view) => (
                        <SelectItem key={view.id} value={view.id} className="text-sm">
                            <span className="font-medium">{view.label}</span>
                        </SelectItem>
                    ))}
                </SelectContent>
            </Select>
            
            <div className="text-xs text-muted-foreground border-l-2 pl-3 border-border">
                {currentView.description}
            </div>
          </div>

          {/* Search Nodes - Dedicated Search Bar */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Search Graph</Label>
              {selectedNode && (
                <Button 
                    variant="ghost" 
                    size="sm" 
                    className="h-6 px-2 text-xs text-muted-foreground hover:text-destructive"
                    onClick={() => {
                        setSelectedNode(null);
                        setHoverNode(null);
                        if(fgRef.current) fgRef.current.zoomToFit(400);
                    }}
                >
                    Clear Focus
                </Button>
              )}
            </div>
            
            <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground pointer-events-none" />
                <Input
                    placeholder="Search nodes..."
                    value={searchQuery}
                    onChange={(e) => {
                        setSearchQuery(e.target.value);
                        if (!searchOpen && e.target.value) setSearchOpen(true);
                    }}
                    onFocus={() => setSearchOpen(true)}
                    className="pl-8"
                />
            </div>
            
            {/* Search Results Dropdown (Inline) */}
            {searchOpen && searchQuery && (
                <div className="border rounded-md shadow-sm bg-background max-h-60 overflow-y-auto z-50">
                    {(normalizedGraph?.nodes || [])
                        .filter(node => (node.searchLabel || "").includes(searchQuery.toLowerCase()))
                        .slice(0, 20)
                        .map(node => (
                            <div 
                                key={node.id}
                                className={cn(
                                    "flex items-center px-3 py-2 text-sm cursor-pointer hover:bg-accent hover:text-accent-foreground",
                                    selectedNode?.id === node.id && "bg-accent"
                                )}
                                onClick={() => {
                                    handleNodeClick(node);
                                    setSearchOpen(false);
                                    setSearchQuery("");
                                }}
                            >
                                <div className="flex flex-col overflow-hidden">
                                     <span className="font-medium truncate">{node.name || node.id}</span>
                                     <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                        <span className="bg-secondary px-1.5 py-0.5 rounded-sm text-[10px] uppercase tracking-wider">
                                            {node.type}
                                        </span>
                                        <span className="truncate opacity-70">ID: {node.id}</span>
                                     </div>
                                </div>
                                {selectedNode?.id === node.id && <Check className="ml-auto h-4 w-4 opacity-50" />}
                            </div>
                        ))
                    }
                    {normalizedGraph?.nodes && normalizedGraph.nodes.filter(n => (n.searchLabel||"").includes(searchQuery.toLowerCase())).length === 0 && (
                        <div className="px-3 py-4 text-sm text-center text-muted-foreground">
                            No nodes found.
                        </div>
                    )}
                </div>
            )}
            
            {/* Active Selection Display */}
            {selectedNode && (
                <div className="mt-2 p-2 border rounded-md bg-accent/20 flex items-start justify-between group">
                    <div>
                        <div className="text-sm font-medium">{selectedNode.name || selectedNode.id}</div>
                        <div className="text-xs text-muted-foreground">{selectedNode.type}</div>
                    </div>
                    <Button 
                        variant="ghost" 
                        size="icon" 
                        className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                        onClick={() => setSelectedNode(null)}
                    >
                        <X className="h-3 w-3" />
                    </Button>
                </div>
            )}
          </div>

          {/* Node-type filter - Tag/Chip Style */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Filter Node Types</Label>
              {selectedNodeTypes.length > 0 && (
                <Button 
                    variant="ghost" 
                    size="sm" 
                    className="h-6 px-2 text-xs text-muted-foreground hover:text-foreground"
                    onClick={() => setSelectedNodeTypes([])}
                >
                    Clear All
                </Button>
              )}
            </div>
            
            {/* Active Filter Chips */}
            <div className="flex flex-wrap gap-1 mb-2">
                {selectedNodeTypes.map(type => (
                    <Badge key={type} variant="secondary" className="hover:bg-secondary/80 pr-1 gap-1">
                        <span 
                            className="w-2 h-2 rounded-full inline-block"
                            style={{ backgroundColor: getNodeColor({ type }) }}
                        />
                        {type}
                        <X 
                            className="h-3 w-3 cursor-pointer hover:text-destructive transition-colors ml-1" 
                            onClick={(e) => {
                                e.stopPropagation();
                                toggleNodeType(type);
                            }}
                        />
                    </Badge>
                ))}
            </div>

            <Popover open={nodeTypeOpen} onOpenChange={setNodeTypeOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  role="combobox"
                  aria-expanded={nodeTypeOpen}
                  className="w-full justify-between font-normal text-muted-foreground"
                >
                  <span className="truncate">
                    {selectedNodeTypes.length === 0 ? "Add type filter..." : "Add more types..."}
                  </span>
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-72 p-0" align="start">
                <Command>
                  <CommandInput placeholder="Search available types..." />
                  <CommandList>
                    <CommandEmpty>No type found.</CommandEmpty>
                    <CommandGroup heading="Available Types">
                      {dropdownTypes.map(nt => {
                        const isSelected = selectedNodeTypes.includes(nt.type);
                        return (
                        <CommandItem
                          key={nt.type}
                          value={nt.type}
                          onSelect={() => toggleNodeType(nt.type)}
                        >
                          <Checkbox 
                            checked={isSelected}
                            className="mr-2"
                          />
                          <div 
                             className="mr-2 h-3 w-3 rounded-full"
                             style={{ backgroundColor: getNodeColor({ type: nt.type }) }} 
                          />
                          <span className={cn("flex-1", isSelected && "font-medium")}>
                            {nt.type}
                          </span>
                          {nt.count && (
                            <span className="text-xs text-muted-foreground ml-2">
                              {nt.count}
                            </span>
                          )}
                        </CommandItem>
                      )})}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>

          {/* Limit slider */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label>Max Nodes</Label>
              <Input
                type="number"
                value={limit[0]}
                onChange={(e) => {
                  const val = parseInt(e.target.value);
                  if (!isNaN(val) && val > 0) {
                    setLimit([val]);
                  }
                }}
                className="w-20 h-8 text-right font-mono"
              />
            </div>
            <Slider
              value={limit}
              onValueChange={setLimit}
              min={50}
              max={10000}
              step={50}
              className="w-full"
            />
            <p className="text-[10px] text-muted-foreground flex items-center gap-1">
              {limit[0] > 2000 && <AlertCircle className="h-3 w-3 text-yellow-500" />}
              {limit[0] > 2000 ? "High node counts may reduce performance" : "Limit nodes to improve performance"}
            </p>
          </div>

          {/* Graph statistics */}
          {graphData && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Graph Statistics</CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-1">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Nodes:</span>
                  <span className="font-mono font-semibold">
                    {graphData.metadata.node_count}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Links:</span>
                  <span className="font-mono font-semibold">
                    {graphData.metadata.link_count}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Types:</span>
                  <span className="font-mono font-semibold">
                    {graphData.metadata.node_types.length}
                  </span>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Node legend */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Node Legend</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-sm">
              {legendTypes.map(type => (
                <div key={type} className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: getNodeColor({ type }) }}
                  />
                  <span>{type}</span>
                </div>
              ))}
              <div className="flex items-center gap-2 pt-1">
                <div className="w-3 h-3 rounded-full bg-gray-500" />
                <span className="text-muted-foreground">Other types</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* ── Main canvas area ── */}
      <div
        className="flex-1 relative"
        ref={containerRef}
        onPointerMove={handlePointerMove}
      >
        {/* Loading overlay */}
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/80 backdrop-blur-sm z-20">
            <div className="text-center space-y-4">
              <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
              <p className="text-sm text-muted-foreground">Loading graph data...</p>
            </div>
          </div>
        )}

        {/* Error overlay */}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-background z-20">
            <Card className="max-w-md">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-5 w-5 text-destructive" />
                  <CardTitle>Failed to Load Graph</CardTitle>
                </div>
                <CardDescription>
                  {error instanceof Error ? error.message : 'Unknown error'}
                </CardDescription>
              </CardHeader>
            </Card>
          </div>
        )}

        {/* Empty-data overlay */}
        {normalizedGraph && !isLoading && !error && normalizedGraph.nodes.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center z-20">
            <Card className="max-w-md">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-5 w-5 text-muted-foreground" />
                  <CardTitle>No Data Found</CardTitle>
                </div>
                <CardDescription>{emptyMessage}</CardDescription>
              </CardHeader>
            </Card>
          </div>
        )}

        {/* Force-directed graph */}
        {normalizedGraph && !isLoading && !error && normalizedGraph.nodes.length > 0 && (
          <ForceGraph2D
            width={dimensions.width}
            height={dimensions.height}
            ref={fgRef}
            graphData={{
              nodes: normalizedGraph.nodes,
              links: normalizedGraph.links,
            }}
            nodeLabel={node => node.name || node.type || node.id}
            nodeColor={getNodeColor}
            nodeRelSize={6}
            nodeCanvasObject={(node, ctx, globalScale) => {
              const id = String(node.id);
              const isFocused = highlighted.focusId === id;
              const isNeighbor = highlighted.nodeIds
                ? highlighted.nodeIds.has(id)
                : true;
              const dim = highlighted.nodeIds ? !isNeighbor : false;
              const baseColor = getNodeColor(node);
              const radius = isFocused ? 8 : 6;

              ctx.globalAlpha = dim ? 0.18 : 1;
              ctx.fillStyle = baseColor;
              ctx.beginPath();
              ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
              ctx.fill();

              if (isFocused || (hoverNode && String(hoverNode.id) === id)) {
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
            }}
            onNodeClick={handleNodeClick}
            onNodeHover={handleNodeHover}
            onLinkHover={handleLinkHover}
            linkDirectionalParticles={l => {
              const id = String(l.id ?? '');
              return highlighted.linkKeys && highlighted.linkKeys.has(id) ? 3 : 0;
            }}
            linkDirectionalParticleWidth={2}
            linkColor={l => {
              const id = String(l.id ?? '');
              const dim = highlighted.linkKeys
                ? !highlighted.linkKeys.has(id)
                : false;
              return dim
                ? 'rgba(148, 163, 184, 0.20)'
                : 'rgba(100, 116, 139, 0.85)';
            }}
            linkWidth={l => {
              const id = String(l.id ?? '');
              return highlighted.linkKeys && highlighted.linkKeys.has(id)
                ? 2.6
                : 1.2;
            }}
            linkDirectionalArrowLength={3}
            linkDirectionalArrowRelPos={1}
            // Engine Configuration for "Cooling Down"
            // Increased ticks to allow complex graphs to untangle
            cooldownTicks={layoutActive ? 300 : 0} 
            // Sufficient time (8s) for larger graphs to settle
            cooldownTime={layoutActive ? 8000 : 0}
            // Standard decay to prevent perpetual jitter
            d3VelocityDecay={layoutActive ? 0.3 : 1}

            d3AlphaDecay={layoutActive ? 0.0228 : 1} // Fast decay when paused
            onEngineStop={() => {
              setLayoutDone(true);
              if (layoutActive) setLayoutActive(false); // Only update if we were active
            }}
            enableZoomInteraction
            enablePanInteraction
            enableNodeDrag
          />
        )}

        {/* Graph Controls */}
        {normalizedGraph && !isLoading && !error && normalizedGraph.nodes.length > 0 && (
          <div className="absolute top-4 right-4 flex flex-col gap-2 z-10">
            <Button
              variant="secondary"
              size="icon"
              className="w-10 h-10 bg-background/80 backdrop-blur-sm border shadow-sm"
              onClick={toggleLayout}
              title={layoutActive ? "Pause Simulation" : "Resume Simulation"}
            >
              {layoutActive ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            </Button>
            <div className="h-px bg-border my-1" />
            <Button
              variant="secondary"
              size="icon"
              className="w-10 h-10 bg-background/80 backdrop-blur-sm border shadow-sm"
              onClick={() => {
                if (fgRef.current) {
                  // zoom in relative to center
                  fgRef.current.zoom(fgRef.current.zoom() * 1.2, 300);
                }
              }}
              title="Zoom In"
            >
              <ZoomIn className="h-4 w-4" />
            </Button>
            <Button
              variant="secondary"
              size="icon"
              className="w-10 h-10 bg-background/80 backdrop-blur-sm border shadow-sm"
              onClick={() => {
                if (fgRef.current) {
                  fgRef.current.zoom(fgRef.current.zoom() / 1.2, 300);
                }
              }}
              title="Zoom Out"
            >
              <ZoomOut className="h-4 w-4" />
            </Button>
            <Button
              variant="secondary"
              size="icon"
              className="w-10 h-10 bg-background/80 backdrop-blur-sm border shadow-sm"
              onClick={() => {
                if (fgRef.current) {
                  fgRef.current.zoomToFit(1000, 20);
                }
              }}
              title="Fit to Screen"
            >
              <Maximize2 className="h-4 w-4" />
            </Button>
          </div>
        )}

        {/* Hover tooltip */}
        {(hoverNode || hoverLink) && (() => {
          const TOOLTIP_W = 320;
          const TOOLTIP_H_EST = 160;
          const OFFSET = 12;
          const left = pointer.x + OFFSET + TOOLTIP_W > dimensions.width
            ? Math.max(0, pointer.x - TOOLTIP_W - OFFSET)
            : pointer.x + OFFSET;
          const top = pointer.y + OFFSET + TOOLTIP_H_EST > dimensions.height
            ? Math.max(0, pointer.y - TOOLTIP_H_EST - OFFSET)
            : pointer.y + OFFSET;
          return (
            <div
              className="absolute z-50 pointer-events-none rounded-md border bg-popover px-3 py-2 text-xs text-popover-foreground shadow-md animate-in fade-in-0 zoom-in-95"
              style={{ left, top, maxWidth: TOOLTIP_W }}
            >
              <div className="font-semibold mb-0.5">
                {hoverNode
                  ? hoverNode.name || hoverNode.id
                  : hoverLink?.type || 'Relationship'}
              </div>
              <div className="text-muted-foreground opacity-90 mb-1">
                {hoverNode
                  ? hoverNode.type
                  : (
                    <>
                      <span className="opacity-70">to</span>{' '}
                      {hoverLink?.target?.name
                        || hoverLink?.target?.id
                        || String(hoverLink?.target)}
                    </>
                  )}
              </div>
              {hoverNode && hoverTooltipProps && (() => {
                const entries = Object.entries(hoverTooltipProps).slice(0, 8);
                return (
                  <div className="border-t border-border/50 pt-1 mt-1 space-y-0.5">
                    {entries.map(([k, v]) => (
                      <div key={k} className="flex gap-1">
                        <span className="text-muted-foreground shrink-0">{k}:</span>
                        <span className="truncate">{String(v).length > 60 ? String(v).slice(0, 60) + '…' : String(v)}</span>
                      </div>
                    ))}
                    {Object.keys(hoverTooltipProps).length > 8 && (
                      <div className="text-muted-foreground italic">+{Object.keys(hoverTooltipProps).length - 8} more…</div>
                    )}
                  </div>
                );
              })()}
            </div>
          );
        })()}

        {/* Selected-node detail card */}
        {selectedNode && (
          <Card className="absolute bottom-4 left-4 w-80 z-10">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">{selectedNode.name}</CardTitle>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setSelectedNode(null)}
                >
                  ×
                </Button>
              </div>
              <CardDescription>{selectedNode.type}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm max-h-72 overflow-y-auto">
              {selectedNode.description && (
                <div>
                  <span className="font-medium">Description:</span>
                  <p className="text-muted-foreground mt-1">
                    {selectedNode.description}
                  </p>
                </div>
              )}
              <div>
                <span className="font-medium">Labels:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {selectedNode.labels.map(label => (
                    <span
                      key={label}
                      className="px-2 py-0.5 bg-secondary text-secondary-foreground rounded text-xs"
                    >
                      {label}
                    </span>
                  ))}
                </div>
              </div>
              {selectedNode.status && (
                <div>
                  <span className="font-medium">Status:</span>
                  <span className="ml-2 text-muted-foreground">
                    {selectedNode.status}
                  </span>
                </div>
              )}
              {selectedNode.ap_schema && (
                <div>
                  <span className="font-medium">Schema:</span>
                  <span className="ml-2 text-muted-foreground">
                    {selectedNode.ap_schema}
                  </span>
                </div>
              )}
              {selectedNode.properties && Object.keys(selectedNode.properties).length > 0 && (
                <div>
                  <span className="font-medium">Properties:</span>
                  <div className="mt-1 space-y-1">
                    {Object.entries(selectedNode.properties).map(([k, v]) => (
                      <div key={k} className="flex gap-1 text-xs">
                        <span className="text-muted-foreground shrink-0">{k}:</span>
                        <span className="break-all">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
