import { useQuery } from '@tanstack/react-query';
import ForceGraph2D from 'react-force-graph-2d';
import { useRef, useState, useCallback, useMemo, useEffect } from 'react';
import { forceManyBody, forceX, forceY } from 'd3-force';
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
  CommandList } from
'@/components/ui/command';
import {
  Popover,
  PopoverContent,
  PopoverTrigger } from
'@/components/ui/popover';
import { cn } from '@/lib/utils';import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";

const API_BASE = '/api';

function getApiKeyOrThrow() {
  const apiKey = import.meta.env.VITE_API_KEY;
  if (!apiKey) {
    throw new Error('VITE_API_KEY environment variable is not set');
  }
  return apiKey;
}

async function fetchJson(url) {
  const apiKey = getApiKeyOrThrow();
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': apiKey
    }
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

  // Fetch available node types
  const { data: nodeTypesData } = useQuery({
    queryKey: ['graph-node-types'],
    queryFn: async () => {
      return fetchJson(`${API_BASE}/graph/node-types`);
    }
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
  const { data: graphData, isLoading, error } = useQuery({
    queryKey: ['graph-data', graphParams],
    queryFn: async () => {
      return fetchJson(`${API_BASE}/graph/data?${graphParams}`);
    },
    refetchOnWindowFocus: false
  });

  const normalizedGraph = useMemo(() => {
    if (!graphData) return null;

    const nodes = (graphData.nodes || []).map((n) => ({
      ...n,
      id: String(n.id),
      labels: Array.isArray(n.labels) ? n.labels : []
    }));

    const nodeById = new Map(nodes.map((n) => [n.id, n]));

    const links = (graphData.links || []).
    map((l) => {
      const sourceId = typeof l.source === 'string' ? String(l.source) : String(l.source?.id);
      const targetId = typeof l.target === 'string' ? String(l.target) : String(l.target?.id);
      return { ...l, source: sourceId, target: targetId };
    }).
    filter((l) => nodeById.has(l.source) && nodeById.has(l.target));

    const neighbors = new Map();
    const addNeighbor = (a, b) => {
      if (!neighbors.has(a)) neighbors.set(a, new Set());
      neighbors.get(a).add(b);
    };

    links.forEach((l) => {
      const s = l.source;
      const t = l.target;
      addNeighbor(s, t);
      addNeighbor(t, s);
    });

    return { nodes, links, neighbors, metadata: graphData.metadata };
  }, [graphData]);

  // Arrange node groups in a “transformation map” style ring layout.
  // This keeps the experience interactive while improving readability and cluster separation.
  useEffect(() => {
    if (!fgRef.current || !normalizedGraph) return;

    const nodeTypes = (normalizedGraph.metadata?.node_types || []).
    filter((t) => typeof t === 'string' && t.length > 0).
    sort();

    const typeIndex = new Map();
    nodeTypes.forEach((t, idx) => typeIndex.set(t, idx));
    const typeCount = Math.max(1, nodeTypes.length);

    const ringRadius = 260;
    const strength = 0.06;

    const fx = forceX((node) => {
      const type = String(node.type || 'Unknown');
      const idx = typeIndex.get(type) ?? 0;
      const angle = idx / typeCount * Math.PI * 2;
      return Math.cos(angle) * ringRadius;
    }).strength(strength);

    const fy = forceY((node) => {
      const type = String(node.type || 'Unknown');
      const idx = typeIndex.get(type) ?? 0;
      const angle = idx / typeCount * Math.PI * 2;
      return Math.sin(angle) * ringRadius;
    }).strength(strength);

    fgRef.current.d3Force('charge', forceManyBody().strength(-60));
    fgRef.current.d3Force('x', fx);
    fgRef.current.d3Force('y', fy);

    // Nudge simulation and then fit
    fgRef.current.d3ReheatSimulation();
    setTimeout(() => {
      try {
        fgRef.current.zoomToFit(600, 60);
      } catch {

        // ignore
      }}, 250);
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
      nbrs.forEach((id) => nodeIds.add(id));
    }

    const linkKeys = new Set();
    normalizedGraph.links.forEach((l) => {
      const s = l.source;
      const t = l.target;
      if (nodeIds.has(s) && nodeIds.has(t) && (s === focusId || t === focusId)) {
        linkKeys.add(l.id);
      }
    });

    return { focusId, nodeIds, linkKeys };
  }, [normalizedGraph, selectedNode, hoverNode]);

  // Node types for filters (only show types with count > 0)
  const availableNodeTypes = useMemo(() => {
    return nodeTypesData?.node_types.filter((nt) => nt.count > 0) || [];
  }, [nodeTypesData]);

  // Color mapping by node type
  const getNodeColor = useCallback((node) => {
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

  // Handle node click
  const handleNodeClick = useCallback((node) => {
    setSelectedNode(node);
    // Center on node
    if (fgRef.current) {
      fgRef.current.centerAt(node.x, node.y, 1000);
      fgRef.current.zoom(2, 1000);
    }
  }, []);

  const handleNodeHover = useCallback((node) => {
    setHoverNode(node);
  }, []);

  const handleLinkHover = useCallback((link) => {
    setHoverLink(link);
  }, []);

  const handlePointerMove = useCallback((e) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    setPointer({ x: e.clientX - rect.left, y: e.clientY - rect.top });
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
  const toggleNodeType = (type) => {
    setSelectedNodeTypes((prev) =>
    prev.includes(type) ?
    prev.filter((t) => t !== type) :
    [...prev, type]
    );
  };

  return (/*#__PURE__*/
    _jsxs("div", { className: "flex h-full min-h-[calc(100vh-5rem)] overflow-hidden", children: [/*#__PURE__*/

      _jsx("div", { className: "w-80 border-r bg-background overflow-y-auto", children: /*#__PURE__*/
        _jsxs("div", { className: "p-6 space-y-6", children: [/*#__PURE__*/
          _jsxs("div", { children: [/*#__PURE__*/
            _jsx("h2", { className: "text-2xl font-bold mb-2", children: "Graph Browser" }), /*#__PURE__*/
            _jsx("p", { className: "text-sm text-muted-foreground", children: "Visualize MBSE knowledge graph relationships" }

            )] }
          ), /*#__PURE__*/


          _jsxs("div", { className: "space-y-2", children: [/*#__PURE__*/
            _jsx(Label, { children: "Filter by Node Type" }), /*#__PURE__*/
            _jsxs(Popover, { open: nodeTypeOpen, onOpenChange: setNodeTypeOpen, children: [/*#__PURE__*/
              _jsx(PopoverTrigger, { asChild: true, children: /*#__PURE__*/
                _jsxs(Button, {
                  variant: "outline",
                  role: "combobox",
                  "aria-expanded": nodeTypeOpen,
                  className: "w-full justify-between", children: [

                  selectedNodeTypes.length > 0 ?
                  `${selectedNodeTypes.length} selected` :
                  'All types', /*#__PURE__*/
                  _jsx(ChevronsUpDown, { className: "ml-2 h-4 w-4 shrink-0 opacity-50" })] }
                ) }
              ), /*#__PURE__*/
              _jsx(PopoverContent, { className: "w-72 p-0", children: /*#__PURE__*/
                _jsxs(Command, { children: [/*#__PURE__*/
                  _jsx(CommandInput, { placeholder: "Search node types..." }), /*#__PURE__*/
                  _jsxs(CommandList, { children: [/*#__PURE__*/
                    _jsx(CommandEmpty, { children: "No node type found." }), /*#__PURE__*/
                    _jsx(CommandGroup, { children:
                      availableNodeTypes.map((nt) => /*#__PURE__*/
                      _jsxs(CommandItem, {

                        value: nt.type,
                        onSelect: () => toggleNodeType(nt.type), children: [/*#__PURE__*/

                        _jsx(Check, {
                          className: cn(
                            'mr-2 h-4 w-4',
                            selectedNodeTypes.includes(nt.type) ?
                            'opacity-100' :
                            'opacity-0'
                          ) }
                        ), /*#__PURE__*/
                        _jsx("span", { className: "flex-1", children: nt.type }), /*#__PURE__*/
                        _jsx("span", { className: "text-xs text-muted-foreground", children:
                          nt.count }
                        )] }, nt.type
                      )
                      ) }
                    )] }
                  )] }
                ) }
              )] }
            )] }
          ), /*#__PURE__*/


          _jsxs("div", { className: "space-y-2", children: [/*#__PURE__*/
            _jsxs(Label, { children: ["Max Nodes: ", limit[0]] }), /*#__PURE__*/
            _jsx(Slider, {
              value: limit,
              onValueChange: setLimit,
              min: 50,
              max: 2000,
              step: 50,
              className: "w-full" }
            ), /*#__PURE__*/
            _jsx("p", { className: "text-xs text-muted-foreground", children: "Limit nodes to improve performance" }

            )] }
          ),


          graphData && /*#__PURE__*/
          _jsxs(Card, { children: [/*#__PURE__*/
            _jsx(CardHeader, { className: "pb-3", children: /*#__PURE__*/
              _jsx(CardTitle, { className: "text-sm", children: "Graph Statistics" }) }
            ), /*#__PURE__*/
            _jsxs(CardContent, { className: "text-sm space-y-1", children: [/*#__PURE__*/
              _jsxs("div", { className: "flex justify-between", children: [/*#__PURE__*/
                _jsx("span", { className: "text-muted-foreground", children: "Nodes:" }), /*#__PURE__*/
                _jsx("span", { className: "font-mono font-semibold", children:
                  graphData.metadata.node_count }
                )] }
              ), /*#__PURE__*/
              _jsxs("div", { className: "flex justify-between", children: [/*#__PURE__*/
                _jsx("span", { className: "text-muted-foreground", children: "Links:" }), /*#__PURE__*/
                _jsx("span", { className: "font-mono font-semibold", children:
                  graphData.metadata.link_count }
                )] }
              ), /*#__PURE__*/
              _jsxs("div", { className: "flex justify-between", children: [/*#__PURE__*/
                _jsx("span", { className: "text-muted-foreground", children: "Types:" }), /*#__PURE__*/
                _jsx("span", { className: "font-mono font-semibold", children:
                  graphData.metadata.node_types.length }
                )] }
              )] }
            )] }
          ), /*#__PURE__*/



          _jsxs(Card, { children: [/*#__PURE__*/
            _jsx(CardHeader, { className: "pb-3", children: /*#__PURE__*/
              _jsx(CardTitle, { className: "text-sm", children: "Node Legend" }) }
            ), /*#__PURE__*/
            _jsxs(CardContent, { className: "space-y-1 text-sm", children: [
              ['Requirement', 'Part', 'Class', 'Package', 'Property', 'Association'].map((type) => /*#__PURE__*/
              _jsxs("div", { className: "flex items-center gap-2", children: [/*#__PURE__*/
                _jsx("div", {
                  className: "w-3 h-3 rounded-full",
                  style: { backgroundColor: getNodeColor({ type }) } }
                ), /*#__PURE__*/
                _jsx("span", { children: type })] }, type
              )
              ), /*#__PURE__*/
              _jsxs("div", { className: "flex items-center gap-2 pt-1", children: [/*#__PURE__*/
                _jsx("div", { className: "w-3 h-3 rounded-full bg-gray-500" }), /*#__PURE__*/
                _jsx("span", { className: "text-muted-foreground", children: "Other types" })] }
              )] }
            )] }
          )] }
        ) }
      ), /*#__PURE__*/


      _jsxs("div", { className: "flex-1 relative", ref: containerRef, onPointerMove: handlePointerMove, children: [/*#__PURE__*/

        _jsxs("div", { className: "absolute top-4 right-4 z-10 flex gap-2", children: [/*#__PURE__*/
          _jsx(Button, { variant: "outline", size: "icon", onClick: handleZoomIn, children: /*#__PURE__*/
            _jsx(ZoomIn, { className: "h-4 w-4" }) }
          ), /*#__PURE__*/
          _jsx(Button, { variant: "outline", size: "icon", onClick: handleZoomOut, children: /*#__PURE__*/
            _jsx(ZoomOut, { className: "h-4 w-4" }) }
          ), /*#__PURE__*/
          _jsx(Button, { variant: "outline", size: "icon", onClick: handleZoomReset, children: /*#__PURE__*/
            _jsx(Maximize2, { className: "h-4 w-4" }) }
          )] }
        ),


        isLoading && /*#__PURE__*/
        _jsx("div", { className: "absolute inset-0 flex items-center justify-center bg-background/80 backdrop-blur-sm z-20", children: /*#__PURE__*/
          _jsxs("div", { className: "text-center space-y-4", children: [/*#__PURE__*/
            _jsx(Loader2, { className: "h-8 w-8 animate-spin mx-auto text-primary" }), /*#__PURE__*/
            _jsx("p", { className: "text-sm text-muted-foreground", children: "Loading graph data..." })] }
          ) }
        ),



        error && /*#__PURE__*/
        _jsx("div", { className: "absolute inset-0 flex items-center justify-center bg-background z-20", children: /*#__PURE__*/
          _jsx(Card, { className: "max-w-md", children: /*#__PURE__*/
            _jsxs(CardHeader, { children: [/*#__PURE__*/
              _jsxs("div", { className: "flex items-center gap-2", children: [/*#__PURE__*/
                _jsx(AlertCircle, { className: "h-5 w-5 text-destructive" }), /*#__PURE__*/
                _jsx(CardTitle, { children: "Failed to Load Graph" })] }
              ), /*#__PURE__*/
              _jsx(CardDescription, { children:
                error instanceof Error ? error.message : 'Unknown error' }
              )] }
            ) }
          ) }
        ),



        normalizedGraph && !isLoading && !error && /*#__PURE__*/
        _jsx(ForceGraph2D, {
          ref: fgRef,
          graphData: { nodes: normalizedGraph.nodes, links: normalizedGraph.links },
          nodeLabel: () => '',
          nodeColor: getNodeColor,
          nodeRelSize: 6,
          nodeCanvasObject: (node, ctx, globalScale) => {
            const id = String(node.id);
            const isFocused = highlighted.focusId === id;
            const isNeighbor = highlighted.nodeIds ? highlighted.nodeIds.has(id) : true;
            const dim = highlighted.nodeIds ? !isNeighbor : false;

            const baseColor = getNodeColor(node);
            const radius = isFocused ? 8 : 6;

            ctx.globalAlpha = dim ? 0.18 : 1;

            // Node fill
            ctx.fillStyle = baseColor;
            ctx.beginPath();
            ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
            ctx.fill();

            // Focus/hover ring
            if (isFocused || hoverNode && String(hoverNode.id) === id) {
              ctx.globalAlpha = 1;
              ctx.lineWidth = 2;
              ctx.strokeStyle = '#0f172a';
              ctx.beginPath();
              ctx.arc(node.x, node.y, radius + 2, 0, 2 * Math.PI, false);
              ctx.stroke();
            }

            // Labels only when zoomed in, and only for focused neighborhood
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
          },
          onNodeClick: handleNodeClick,
          onNodeHover: handleNodeHover,
          onLinkHover: handleLinkHover,
          linkDirectionalParticles: 2,
          linkDirectionalParticleWidth: 2,
          linkColor: (l) => {
            const id = String(l.id);
            const dim = highlighted.linkKeys ? !highlighted.linkKeys.has(id) : false;
            return dim ? 'rgba(148, 163, 184, 0.20)' : 'rgba(100, 116, 139, 0.85)';
          },
          linkWidth: (l) => {
            const id = String(l.id);
            return highlighted.linkKeys && highlighted.linkKeys.has(id) ? 2.6 : 1.2;
          },
          linkDirectionalArrowLength: 3,
          linkDirectionalArrowRelPos: 1,
          cooldownTicks: 100,
          warmupTicks: 100,
          d3VelocityDecay: 0.3,
          enableZoomInteraction: true,
          enablePanInteraction: true,
          enableNodeDrag: true }
        ),



        (hoverNode || hoverLink) && pointer && /*#__PURE__*/
        _jsx("div", {
          className: "absolute z-20 pointer-events-none",
          style: { left: pointer.x + 12, top: pointer.y + 12, maxWidth: 320 }, children: /*#__PURE__*/

          _jsxs(Card, { className: "shadow-lg", children: [/*#__PURE__*/
            _jsxs(CardHeader, { className: "py-3", children: [/*#__PURE__*/
              _jsx(CardTitle, { className: "text-sm", children:
                hoverNode ? hoverNode.name || hoverNode.id : 'Relationship' }
              ), /*#__PURE__*/
              _jsx(CardDescription, { className: "text-xs", children:
                hoverNode ? hoverNode.type : hoverLink?.type }
              )] }
            ), /*#__PURE__*/
            _jsx(CardContent, { className: "py-3 text-xs text-muted-foreground space-y-1", children:
              hoverNode ? /*#__PURE__*/
              _jsxs(_Fragment, { children: [/*#__PURE__*/
                _jsxs("div", { children: [/*#__PURE__*/_jsx("span", { className: "font-medium text-foreground", children: "ID:" }), " ", hoverNode.id] }),
                hoverNode.ap_schema && /*#__PURE__*/
                _jsxs("div", { children: [/*#__PURE__*/_jsx("span", { className: "font-medium text-foreground", children: "Schema:" }), " ", hoverNode.ap_schema] }),

                hoverNode.status && /*#__PURE__*/
                _jsxs("div", { children: [/*#__PURE__*/_jsx("span", { className: "font-medium text-foreground", children: "Status:" }), " ", hoverNode.status] })] }

              ) : /*#__PURE__*/

              _jsxs(_Fragment, { children: [/*#__PURE__*/
                _jsxs("div", { children: [/*#__PURE__*/_jsx("span", { className: "font-medium text-foreground", children: "From:" }), " ", String(hoverLink?.source)] }), /*#__PURE__*/
                _jsxs("div", { children: [/*#__PURE__*/_jsx("span", { className: "font-medium text-foreground", children: "To:" }), " ", String(hoverLink?.target)] })] }
              ) }

            )] }
          ) }
        ),



        selectedNode && /*#__PURE__*/
        _jsxs(Card, { className: "absolute bottom-4 left-4 w-80 z-10", children: [/*#__PURE__*/
          _jsxs(CardHeader, { children: [/*#__PURE__*/
            _jsxs("div", { className: "flex items-center justify-between", children: [/*#__PURE__*/
              _jsx(CardTitle, { className: "text-base", children: selectedNode.name }), /*#__PURE__*/
              _jsx(Button, {
                variant: "ghost",
                size: "icon",
                onClick: () => setSelectedNode(null), children:
                "\xD7" }

              )] }
            ), /*#__PURE__*/
            _jsx(CardDescription, { children: selectedNode.type })] }
          ), /*#__PURE__*/
          _jsxs(CardContent, { className: "space-y-2 text-sm", children: [
            selectedNode.description && /*#__PURE__*/
            _jsxs("div", { children: [/*#__PURE__*/
              _jsx("span", { className: "font-medium", children: "Description:" }), /*#__PURE__*/
              _jsx("p", { className: "text-muted-foreground mt-1", children: selectedNode.description })] }
            ), /*#__PURE__*/

            _jsxs("div", { children: [/*#__PURE__*/
              _jsx("span", { className: "font-medium", children: "Labels:" }), /*#__PURE__*/
              _jsx("div", { className: "flex flex-wrap gap-1 mt-1", children:
                selectedNode.labels.map((label) => /*#__PURE__*/
                _jsx("span", {

                  className: "px-2 py-0.5 bg-secondary text-secondary-foreground rounded text-xs", children:

                  label }, label
                )
                ) }
              )] }
            ),
            selectedNode.status && /*#__PURE__*/
            _jsxs("div", { children: [/*#__PURE__*/
              _jsx("span", { className: "font-medium", children: "Status:" }), /*#__PURE__*/
              _jsx("span", { className: "ml-2 text-muted-foreground", children: selectedNode.status })] }
            ),

            selectedNode.ap_schema && /*#__PURE__*/
            _jsxs("div", { children: [/*#__PURE__*/
              _jsx("span", { className: "font-medium", children: "Schema:" }), /*#__PURE__*/
              _jsx("span", { className: "ml-2 text-muted-foreground", children: selectedNode.ap_schema })] }
            )] }

          )] }
        )] }

      )] }
    ));

}
