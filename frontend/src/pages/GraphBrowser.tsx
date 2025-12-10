import { useQuery } from '@tanstack/react-query';
import ForceGraph2D from 'react-force-graph-2d';
import { useRef, useState, useCallback, useMemo } from 'react';
import { Check, ChevronsUpDown, Loader2, AlertCircle, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { cn } from '@/lib/utils';

const API_BASE = '/api';

interface GraphNode {
  id: string;
  name: string;
  type: string;
  group: string;
  labels: string[];
  description?: string;
  status?: string;
  priority?: string;
  ap_level?: number;
  ap_schema?: string;
  x?: number;
  y?: number;
}

interface GraphLink {
  source: string;
  target: string;
  type: string;
  id: string;
}

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
  metadata: {
    node_count: number;
    link_count: number;
    node_types: string[];
    relationship_types: string[];
    filters_applied: Record<string, any>;
  };
}

interface NodeType {
  type: string;
  count: number;
}

export default function GraphBrowser() {
  const fgRef = useRef<any>(null);
  const [selectedNodeTypes, setSelectedNodeTypes] = useState<string[]>([]);
  const [nodeTypeOpen, setNodeTypeOpen] = useState(false);
  const [limit, setLimit] = useState([500]);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  // Fetch available node types
  const { data: nodeTypesData } = useQuery<{ node_types: NodeType[] }>({
    queryKey: ['graph-node-types'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/graph/node-types`);
      if (!res.ok) throw new Error('Failed to fetch node types');
      return res.json();
    },
  });

  // Build query parameters
  const graphParams = useMemo(() => {
    const params = new URLSearchParams();
    if (selectedNodeTypes.length > 0) {
      params.append('node_types', selectedNodeTypes.join(','));
    }
    params.append('limit', limit[0].toString());
    return params.toString();
  }, [selectedNodeTypes, limit]);

  // Fetch graph data
  const { data: graphData, isLoading, error } = useQuery<GraphData>({
    queryKey: ['graph-data', graphParams],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/graph/data?${graphParams}`);
      if (!res.ok) throw new Error('Failed to fetch graph data');
      return res.json();
    },
    refetchOnWindowFocus: false,
  });

  // Node types for filters (only show types with count > 0)
  const availableNodeTypes = useMemo(() => {
    return nodeTypesData?.node_types.filter(nt => nt.count > 0) || [];
  }, [nodeTypesData]);

  // Color mapping by node type
  const getNodeColor = useCallback((node: GraphNode) => {
    const colors: Record<string, string> = {
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
      Person: '#f43f5e',
    };
    return colors[node.type] || '#6b7280';
  }, []);

  // Handle node click
  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedNode(node);
    // Center on node
    if (fgRef.current) {
      fgRef.current.centerAt(node.x, node.y, 1000);
      fgRef.current.zoom(2, 1000);
    }
  }, []);

  // Zoom controls
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

  // Toggle node type selection
  const toggleNodeType = (type: string) => {
    setSelectedNodeTypes(prev =>
      prev.includes(type)
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Controls Sidebar */}
      <div className="w-80 border-r bg-background overflow-y-auto">
        <div className="p-6 space-y-6">
          <div>
            <h2 className="text-2xl font-bold mb-2">Graph Browser</h2>
            <p className="text-sm text-muted-foreground">
              Visualize MBSE knowledge graph relationships
            </p>
          </div>

          {/* Node Type Filter */}
          <div className="space-y-2">
            <Label>Filter by Node Type</Label>
            <Popover open={nodeTypeOpen} onOpenChange={setNodeTypeOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  role="combobox"
                  aria-expanded={nodeTypeOpen}
                  className="w-full justify-between"
                >
                  {selectedNodeTypes.length > 0
                    ? `${selectedNodeTypes.length} selected`
                    : 'All types'}
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-72 p-0">
                <Command>
                  <CommandInput placeholder="Search node types..." />
                  <CommandList>
                    <CommandEmpty>No node type found.</CommandEmpty>
                    <CommandGroup>
                      {availableNodeTypes.map(nt => (
                        <CommandItem
                          key={nt.type}
                          value={nt.type}
                          onSelect={() => toggleNodeType(nt.type)}
                        >
                          <Check
                            className={cn(
                              'mr-2 h-4 w-4',
                              selectedNodeTypes.includes(nt.type)
                                ? 'opacity-100'
                                : 'opacity-0'
                            )}
                          />
                          <span className="flex-1">{nt.type}</span>
                          <span className="text-xs text-muted-foreground">
                            {nt.count}
                          </span>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>

          {/* Limit Slider */}
          <div className="space-y-2">
            <Label>Max Nodes: {limit[0]}</Label>
            <Slider
              value={limit}
              onValueChange={setLimit}
              min={50}
              max={2000}
              step={50}
              className="w-full"
            />
            <p className="text-xs text-muted-foreground">
              Limit nodes to improve performance
            </p>
          </div>

          {/* Graph Stats */}
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

          {/* Legend */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Node Legend</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-sm">
              {['Requirement', 'Part', 'Class', 'Package', 'Property', 'Association'].map(type => (
                <div key={type} className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: getNodeColor({ type } as GraphNode) }}
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

      {/* Graph Canvas */}
      <div className="flex-1 relative">
        {/* Zoom Controls */}
        <div className="absolute top-4 right-4 z-10 flex gap-2">
          <Button variant="outline" size="icon" onClick={handleZoomIn}>
            <ZoomIn className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon" onClick={handleZoomOut}>
            <ZoomOut className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon" onClick={handleZoomReset}>
            <Maximize2 className="h-4 w-4" />
          </Button>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/80 backdrop-blur-sm z-20">
            <div className="text-center space-y-4">
              <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
              <p className="text-sm text-muted-foreground">Loading graph data...</p>
            </div>
          </div>
        )}

        {/* Error State */}
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

        {/* Graph Visualization */}
        {graphData && !isLoading && !error && (
          <ForceGraph2D
            ref={fgRef}
            graphData={graphData}
            nodeLabel="name"
            nodeColor={getNodeColor}
            nodeRelSize={6}
            nodeCanvasObject={(node: any, ctx, globalScale) => {
              const label = node.name;
              const fontSize = 12 / globalScale;
              ctx.font = `${fontSize}px Sans-Serif`;
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              ctx.fillStyle = getNodeColor(node);
              
              // Draw node circle
              ctx.beginPath();
              ctx.arc(node.x, node.y, 5, 0, 2 * Math.PI, false);
              ctx.fill();

              // Draw label
              if (globalScale >= 1.5) {
                ctx.fillStyle = '#fff';
                ctx.fillText(label, node.x, node.y + 10);
              }
            }}
            onNodeClick={handleNodeClick}
            linkDirectionalParticles={2}
            linkDirectionalParticleWidth={2}
            linkColor={() => '#94a3b8'}
            linkWidth={1.5}
            linkDirectionalArrowLength={3}
            linkDirectionalArrowRelPos={1}
            cooldownTicks={100}
            warmupTicks={100}
            d3VelocityDecay={0.3}
            enableZoomInteraction={true}
            enablePanInteraction={true}
            enableNodeDrag={true}
          />
        )}

        {/* Selected Node Panel */}
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
            <CardContent className="space-y-2 text-sm">
              {selectedNode.description && (
                <div>
                  <span className="font-medium">Description:</span>
                  <p className="text-muted-foreground mt-1">{selectedNode.description}</p>
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
                  <span className="ml-2 text-muted-foreground">{selectedNode.status}</span>
                </div>
              )}
              {selectedNode.ap_schema && (
                <div>
                  <span className="font-medium">Schema:</span>
                  <span className="ml-2 text-muted-foreground">{selectedNode.ap_schema}</span>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
