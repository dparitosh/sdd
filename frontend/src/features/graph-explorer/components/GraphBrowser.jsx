import { useRef, useState, useCallback, useMemo, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import ForceGraph2D from 'react-force-graph-2d';
import { forceManyBody, forceX, forceY, forceCollide } from 'd3';
import { Check, ChevronsUpDown, Loader2, AlertCircle, ZoomIn, ZoomOut, Maximize2, Pause, Play, Search, X, Network, Share2, Layers, GitMerge } from 'lucide-react';
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
import { getNodeTypes, getGraphData } from '@/services/graph.service';

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
    label: 'STEP Ontology',
    description: 'ISO 10303 STEP ontology — OWL classes, object & data properties (T-Box)',
    apLevel: null,
    fixedNodeTypes: ['Ontology', 'OntologyClass', 'OntologyProperty', 'OWLClass', 'OWLObjectProperty', 'OWLDatatypeProperty'],
    icon: Share2
  },
  OSLC: {
    id: 'OSLC',
    label: 'OSLC Integration',
    description: 'Cross-domain integration fabric: STEP Ontology T-Box ↔ XSD Schema ↔ Requirements via OSLC linkage',
    apLevel: null,
    fixedNodeTypes: ['Ontology', 'OntologyClass', 'OntologyProperty', 'Requirement', 'XSDSchema', 'ExternalOwlClass'],
    icon: Network
  },
  DIGITAL_THREAD: {
    id: 'DIGITAL_THREAD',
    label: 'Digital Thread',
    description: 'Linear flow: Dossier → Run → Artifact → Part → Requirement',
    apLevel: null,
    fixedNodeTypes: ['SimulationDossier', 'SimulationRun', 'SimulationArtifact', 'EvidenceCategory', 'Part', 'Requirement'],
    icon: GitMerge
  }
};

/** Color coding for STEP Ontology relationship types */
const ONTOLOGY_REL_COLORS = {
  SUBCLASS_OF:           '#f97316', // orange  — class inheritance
  HAS_OBJECT_PROPERTY:   '#8b5cf6', // purple  — connects class to object property
  HAS_DATATYPE_PROPERTY: '#10b981', // emerald — connects class to data property
  RANGE_CLASS:           '#3b82f6', // blue    — property → target class
  DOMAIN_CLASS:          '#14b8a6', // teal    — property → source class
  CLASSIFIED_BY:         '#f59e0b', // amber
  MAPS_TO_OSLC:          '#ec4899', // pink
};

/**
 * Color coding for OSLC Integration view — cross-domain linkage relationships
 * (ISO 10303 STEP ↔ OSLC ↔ XSD schema bridge)
 */
const OSLC_REL_COLORS = {
  DEFINES:        '#8b5cf6', // purple  — Ontology module → OntologyClass
  MAPS_TO_SCHEMA: '#3b82f6', // blue    — OntologyClass → XSDSchema
  MAPS_TO_OSLC:   '#ec4899', // pink    — resource mapped to OSLC type
  EXTENDS:        '#f97316', // orange  — class/concept extension
  SUBCLASS_OF:    '#f59e0b', // amber   — OWL subsumption
  TYPED_BY:       '#94a3b8', // slate   — instance → type class
  HAS_OBJECT_PROPERTY:   '#a855f7', // violet — class → object property
  HAS_DATATYPE_PROPERTY: '#10b981', // emerald — class → datatype property
};

/** Color coding for Digital Thread relationship types (matched to actual DB schema) */
const DT_REL_COLORS = {
  HAS_SIMULATION_RUN:       '#3b82f6', // blue       — Dossier → Run
  CONTAINS_ARTIFACT:        '#a855f7', // purple     — Run → Artifact
  GENERATED:                '#0ea5e9', // sky        — Run/Artifact → Artifact
  LINKED_TO_REQUIREMENT:    '#f97316', // orange     — Artifact → Requirement
  SATISFIED_BY_PART:        '#22c55e', // green      — Requirement → Part
  TYPED_BY:                 '#94a3b8', // slate-grey — Part → Class (structural)
  PROVES_COMPLIANCE_TO:     '#ef4444', // red        — legacy
  HAS_APPROVAL:             '#eab308', // gold       — legacy
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
        // d3AlphaTarget/d3VelocityDecay are props, not ref methods.
        // pauseAnimation() is the correct imperative call to stop the loop.
        fgRef.current.pauseAnimation();
        setLayoutActive(false);
        setLayoutDone(true);
    } else {
        // resumeAnimation() restarts the render loop;
        // d3ReheatSimulation() re-energises the force engine.
        fgRef.current.resumeAnimation();
        fgRef.current.d3ReheatSimulation();
        setLayoutActive(true);
        setLayoutDone(false);
    }
  }, [layoutActive]);

  const [limit, setLimit] = useState([500]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [breadcrumbs, setBreadcrumbs] = useState([]);
  const navigate = useNavigate();
  const [hoverNode, setHoverNode] = useState(null);
  const [hoverLink, setHoverLink] = useState(null);
    const pointerRef = useRef({ x: 0, y: 0 });
    const tooltipRef = useRef(null);
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
    
    // Measure container dimensions.
    // Width: use the element's own clientWidth (correct — sidebar excluded).
    // Height: use window.innerHeight minus the element's top offset so the
    //         canvas always fills the remaining viewport height regardless of
    //         how much padding/header chrome the parent layout adds.
    const measure = () => {
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const width = Math.floor(rect.width);
      const height = Math.floor(window.innerHeight - rect.top);
      if (width > 0 && height > 0) {
        setDimensions({ width, height: Math.max(300, height) });
      }
    };
    
    measure();

    const ro = new ResizeObserver(() => measure());
    ro.observe(el);
    // Also re-measure on window resize (viewport height can change)
    window.addEventListener('resize', measure);
    
    return () => {
      ro.disconnect();
      window.removeEventListener('resize', measure);
    };
  }, []);

  const {
    data: nodeTypesData
  } = useQuery({
    queryKey: ['graph-node-types'],
    queryFn: () => getNodeTypes()
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
      return getGraphData(params);
    },
    refetchOnWindowFocus: false
  });
  const normalizedGraph = useMemo(() => {
    if (!graphData) return null;
    const nodes = (graphData.nodes || []).map(n => {
      // Derive the best human-readable display name.
      // Priority: backend name > properties.label > properties.local_name > non-elementId id
      const rawId = String(n.id || '');
      const isElementId = /^\d+:[0-9a-f\-]{36}:\d+$/i.test(rawId);
      const resolvedName = n.name
        || n.properties?.label
        || n.properties?.local_name
        || (isElementId ? null : rawId)
        || null;

      // Pre-compute universal search terms
      // Includes: Name, ID, Type, Labels, and all Property Values
      const searchTerms = [
        resolvedName,
        n.id,
        n.type,
        ...(Array.isArray(n.labels) ? n.labels : []),
        // Convert all property values to string for search
        ...Object.entries(n.properties || {}).map(([k, v]) => `${k} ${v}`)
      ].filter(Boolean).join(" ").toLowerCase();

      return {
        ...n,
        id: String(n.id),
        name: resolvedName,
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

    let fx, fy;
    if (currentViewId === 'DIGITAL_THREAD') {
      // Hierarchical top-to-bottom layout matching the flow:
      // SimulationDossier → SimulationRun → SimulationArtifact/EvidenceCategory → Part → Requirement
      const DT_TIER = {
        SimulationDossier:  0,
        SimulationRun:      1,
        SimulationArtifact: 2,
        EvidenceCategory:   2,
        Part:               3,
        Requirement:        4,
      };
      const tierCount = 5;
      const ySpacing = 140;
      const yOffset = -((tierCount - 1) / 2) * ySpacing;
      fy = forceY(node => {
        const tier = DT_TIER[node.type] ?? 2;
        return yOffset + tier * ySpacing;
      }).strength(0.55);
      fx = forceX(0).strength(0.02);
      fgRef.current.d3Force('charge', forceManyBody().strength(-160));
    } else if (currentViewId === 'OSLC') {
      // 3-tier layout: Ontology module (top) → Classes/Properties (middle) → Schema/Requirements (bottom)
      const OSLC_TIER = {
        Ontology:         0,
        OntologyClass:    1,
        OntologyProperty: 1,
        Requirement:      2,
        XSDSchema:        2,
        ExternalOwlClass: 2,
      };
      const tierCount = 3;
      const ySpacing = 200;
      const yOffset = -((tierCount - 1) / 2) * ySpacing;
      fy = forceY(node => {
        const tier = OSLC_TIER[node.type] ?? 1;
        return yOffset + tier * ySpacing;
      }).strength(0.50);
      fx = forceX(0).strength(0.02);
      fgRef.current.d3Force('charge', forceManyBody().strength(-120));
    } else {
      // Default ring layout for all other views
      const ringRadius = 260;
      const strength = 0.06;
      fx = forceX(node => {
        const type = String(node.type || 'Unknown');
        const idx = typeIndex.get(type) ?? 0;
        const angle = idx / typeCount * Math.PI * 2;
        return Math.cos(angle) * ringRadius;
      }).strength(strength);
      fy = forceY(node => {
        const type = String(node.type || 'Unknown');
        const idx = typeIndex.get(type) ?? 0;
        const angle = idx / typeCount * Math.PI * 2;
        return Math.sin(angle) * ringRadius;
      }).strength(strength);
      fgRef.current.d3Force('charge', forceManyBody().strength(-80));
    }
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
  }, [normalizedGraph, selectedNodeTypes, limit, currentViewId]);
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
    return (nodeTypesData?.node_types?.filter(nt => nt.count > 0) ?? [])
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

    // AP243 Simulation
    if (type === 'SimulationArtifact') return '#0ea5e9'; // Sky
    if (type === 'EvidenceCategory') return '#38bdf8';   // Light sky
    if (['SimulationDossier', 'SimulationRun', 'SimulationModel', 'CADModel'].includes(type)) return '#7c3aed'; // Violet
    
    // General type colors (only for types not matched above)
    const colors = {
      // AP242 (CAD) - Red/Orange Scheme
      Part: '#ef4444', 
      Assembly: '#b91c1c', 
      Component: '#f87171',
      Shape: '#f97316',
      GeometricModel: '#c2410c',

      // AP239 (PLCS) - Green/Teal Scheme
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
      Organization: '#0891b2',
      Person: '#f43f5e',
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
    if (selectedNode && selectedNode.id === node.id) {
      setSelectedNode(null);
      setHoverNode(null);
      if (fgRef.current) fgRef.current.zoomToFit(400);
      return;
    }
    setSelectedNode(node);
    setHoverNode(null); // clear hover so only the click selection drives highlight
    // In Digital Thread mode, add to breadcrumb trail
    if (currentViewId === 'DIGITAL_THREAD' && node) {
      setBreadcrumbs(prev => {
        const exists = prev.findIndex(b => b.id === String(node.id));
        if (exists >= 0) return prev.slice(0, exists + 1);
        return [...prev, { id: String(node.id), name: node.name || node.id, type: node.type }];
      });
    }
    if (fgRef.current) {
      // Freeze simulation immediately so the graph is fully static when
      // navigating to the selected node (prevents bounce/drift after zoom).
      fgRef.current.pauseAnimation();
      setLayoutActive(false);
      setLayoutDone(true);

      // Build the set of ids to show: focus node + all 1-hop neighbours
      const focusId = String(node.id);
      const nbrs = normalizedGraph?.neighbors?.get(focusId) || new Set();
      const clusterIds = new Set([focusId, ...nbrs]);

      if (nbrs.size > 0) {
        // Zoom to fit the entire 1-hop cluster so neighbours stay on-screen
        // even when the force layout has placed them far from the focus node.
        fgRef.current.zoomToFit(600, 80, n => clusterIds.has(String(n.id)));
      } else {
        // Isolated node — just centre and zoom in
        fgRef.current.centerAt(node.x, node.y, 600);
        fgRef.current.zoom(2.5, 600);
      }
    }
  }, [currentViewId, normalizedGraph]);
  const handleNodeHover = useCallback(node => {
    setHoverNode(node);
  }, []);
  const handleLinkHover = useCallback(link => {
    setHoverLink(link);
  }, []);
  const handlePointerMove = useCallback(e => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    pointerRef.current = { x, y };

    if (tooltipRef.current) {
      const TOOLTIP_W = 320;
      const TOOLTIP_H_EST = 160;
      const OFFSET = 12;
      const left = x + OFFSET + TOOLTIP_W > dimensions.width
        ? Math.max(0, x - TOOLTIP_W - OFFSET)
        : x + OFFSET;
      const top = y + OFFSET + TOOLTIP_H_EST > dimensions.height
        ? Math.max(0, y - TOOLTIP_H_EST - OFFSET)
        : y + OFFSET;
      
      tooltipRef.current.style.left = `${left}px`;
      tooltipRef.current.style.top = `${top}px`;
    }
  }, [dimensions]);
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
        // If the currently selected node is of the type being removed, clear it
        if (exists && selectedNode?.type === typeStr) {
          setSelectedNode(null);
          setHoverNode(null);
        }
        return newSelection;
    });
  }, [dropdownTypes, selectedNode]);

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
    // Break out of the layout's p-8 + max-w wrapper so the graph fills edge-to-edge.
    // -mx-8 / -mt-8 cancel the parent p-8 padding.
    // Width  = calc(100% + 4rem)  restores the 2×32px horizontal gap.
    // Height = calc(100vh - 124px): viewport minus the app header (64px)
    //          and footer (py-3 ≈ 48px) plus a small 12px buffer.
    <div
      className="flex overflow-hidden -mx-8 -mt-8"
      style={{ height: 'calc(100vh - 124px)', width: 'calc(100% + 4rem)' }}
    >
      {/* ── Sidebar ── */}
      <div className="w-80 h-full border-r bg-background overflow-y-auto shrink-0">
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

          {/* Digital Thread Breadcrumb Trail */}
          {currentViewId === 'DIGITAL_THREAD' && breadcrumbs.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Thread Path</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                {breadcrumbs.map((crumb, i) => (
                  <div key={crumb.id} className="flex items-center gap-1 text-xs">
                    {i > 0 && <span className="text-muted-foreground mx-1">→</span>}
                    <button
                      className="hover:underline text-primary font-medium truncate max-w-48"
                      onClick={() => {
                        const node = normalizedGraph?.nodes.find(n => String(n.id) === crumb.id);
                        if (node) handleNodeClick(node);
                      }}
                    >
                      {crumb.name}
                    </button>
                    <Badge variant="outline" className="text-[9px] px-1 py-0 shrink-0">{crumb.type}</Badge>
                  </div>
                ))}
                <Button variant="ghost" size="sm" className="h-6 text-xs mt-1" onClick={() => setBreadcrumbs([])}>
                  Clear Path
                </Button>
              </CardContent>
            </Card>
          )}

          {/* STEP Ontology Relationship Legend */}
          {currentViewId === 'ONTOLOGY' && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Relationship Colors</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1 text-xs">
                {Object.entries(ONTOLOGY_REL_COLORS).map(([rel, color]) => (
                  <div key={rel} className="flex items-center gap-2">
                    <div className="w-6 h-0.5 rounded" style={{ backgroundColor: color }} />
                    <span className="text-muted-foreground">{rel.replace(/_/g, ' ')}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* OSLC Integration Relationship Legend */}
          {currentViewId === 'OSLC' && (
            <>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Layer Architecture</CardTitle>
                </CardHeader>
                <CardContent className="space-y-1.5 text-xs">
                  {[
                    { tier: 'Top',    label: 'Ontology Modules',        types: ['Ontology'] },
                    { tier: 'Middle', label: 'Classes & Properties',    types: ['OntologyClass', 'OntologyProperty'] },
                    { tier: 'Bottom', label: 'Schema · Requirements',   types: ['XSDSchema', 'Requirement', 'ExternalOwlClass'] },
                  ].map(({ tier, label, types }) => (
                    <div key={tier} className="flex items-start gap-2">
                      <span className="w-14 shrink-0 text-muted-foreground font-medium">{tier}</span>
                      <div>
                        <div className="font-medium">{label}</div>
                        <div className="text-muted-foreground">{types.join(', ')}</div>
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Relationship Colors</CardTitle>
                </CardHeader>
                <CardContent className="space-y-1 text-xs">
                  {Object.entries(OSLC_REL_COLORS).map(([rel, color]) => (
                    <div key={rel} className="flex items-center gap-2">
                      <div className="w-6 h-0.5 rounded" style={{ backgroundColor: color }} />
                      <span className="text-muted-foreground">{rel.replace(/_/g, ' ')}</span>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </>
          )}

          {/* Digital Thread Relationship Legend */}
          {currentViewId === 'DIGITAL_THREAD' && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Relationship Colors</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1 text-xs">
                {Object.entries(DT_REL_COLORS).map(([rel, color]) => (
                  <div key={rel} className="flex items-center gap-2">
                    <div className="w-6 h-0.5 rounded" style={{ backgroundColor: color }} />
                    <span className="text-muted-foreground">{rel.replace(/_/g, ' ')}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Search Nodes - Dedicated Search Bar */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Search Graph</Label>
              {(selectedNode || hoverNode) && (
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
                        .map(node => {
                            // Build a human-readable display label:
                            // prefer node.name, then properties.label, then a
                            // sanitised id (strip Neo4j internal element IDs like '4:uuid:12345')
                            const rawId = String(node.id || '');
                            const isElementId = /^\d+:[0-9a-f\-]{36}:\d+$/i.test(rawId);
                            const localId = rawId.includes(':') ? rawId.split(':').pop() : rawId;
                            const displayName = node.name
                                || node.properties?.label
                                || node.properties?.local_name
                                || (isElementId ? null : rawId)
                                || `${node.type || 'Node'} #${localId}`;
                            const displayId = isElementId ? null : rawId;
                            return (
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
                                     <span className="font-medium truncate">{displayName}</span>
                                     <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                        <span className="bg-secondary px-1.5 py-0.5 rounded-sm text-[10px] uppercase tracking-wider">
                                            {node.type}
                                        </span>
                                        {displayId && <span className="truncate opacity-70">{displayId}</span>}
                                     </div>
                                </div>
                                {selectedNode?.id === node.id && <Check className="ml-auto h-4 w-4 opacity-50" />}
                            </div>
                            );
                        })
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
                        <div className="text-sm font-medium">
                          {selectedNode.name
                            || selectedNode.properties?.label
                            || selectedNode.properties?.local_name
                            || selectedNode.type}
                        </div>
                        <div className="text-xs text-muted-foreground">{selectedNode.type}</div>
                    </div>
                    <Button 
                        variant="ghost" 
                        size="icon" 
                        className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                        onClick={() => {
                          setSelectedNode(null);
                          setHoverNode(null);
                          if (fgRef.current) fgRef.current.zoomToFit(400);
                        }}
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
                    onClick={() => {
                      setSelectedNodeTypes([]);
                      setSelectedNode(null);
                      setHoverNode(null);
                    }}
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
                    {graphData.metadata?.node_count ?? 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Links:</span>
                  <span className="font-mono font-semibold">
                    {graphData.metadata?.link_count ?? 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Types:</span>
                  <span className="font-mono font-semibold">
                    {graphData.metadata?.node_types?.length ?? 0}
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
              {currentViewId === 'ONTOLOGY' ? (
                <>
                  {[
                    { type: 'OWLClass',            label: 'OWL Class',           shape: 'circle'  },
                    { type: 'OWLObjectProperty',   label: 'Object Property',     shape: 'diamond' },
                    { type: 'OWLDatatypeProperty', label: 'Datatype Property',   shape: 'square'  },
                    { type: 'Ontology',            label: 'Ontology Module',     shape: 'circle'  },
                    { type: 'OntologyClass',       label: 'Ontology Class',      shape: 'circle'  },
                    { type: 'OntologyProperty',    label: 'Ontology Property',   shape: 'circle'  },
                  ].map(({ type, label, shape }) => (
                    <div key={type} className="flex items-center gap-2">
                      <svg width="14" height="14" viewBox="0 0 14 14">
                        {shape === 'diamond' ? (
                          <rect x="2" y="2" width="10" height="10" rx="0"
                            fill={getNodeColor({ type })}
                            transform="rotate(45 7 7)" />
                        ) : shape === 'square' ? (
                          <rect x="2" y="2" width="10" height="10" rx="1"
                            fill={getNodeColor({ type })} />
                        ) : (
                          <circle cx="7" cy="7" r="5.5"
                            fill={getNodeColor({ type })} />
                        )}
                      </svg>
                      <span>{label}</span>
                    </div>
                  ))}
                </>
              ) : (
                <>
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
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* ── Main canvas area ── */}
      <div
        className="flex-1 h-full relative overflow-hidden"
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
            nodeLabel={node => {
                const rawId = String(node.id || '');
                const isElementId = /^\d+:[0-9a-f\-]{36}:\d+$/i.test(rawId);
                const localId = rawId.includes(':') ? rawId.split(':').pop() : rawId;
                return node.name
                  || node.properties?.label
                  || node.properties?.local_name
                  || (isElementId ? `${node.type} #${localId}` : rawId);
              }}
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

              // In ONTOLOGY view render OWLObjectProperty as a diamond and
              // OWLDatatypeProperty as a small square; all other nodes get circles.
              if (currentViewId === 'ONTOLOGY' && (node.type === 'OWLObjectProperty' || node.type === 'OWLDatatypeProperty')) {
                const s = node.type === 'OWLObjectProperty' ? 5 : 4;
                ctx.save();
                ctx.globalAlpha = dim ? 0.18 : 1;
                ctx.fillStyle = baseColor;
                ctx.translate(node.x, node.y);
                if (node.type === 'OWLObjectProperty') ctx.rotate(Math.PI / 4); // 45° → diamond
                ctx.beginPath();
                ctx.rect(-s, -s, s * 2, s * 2);
                ctx.fill();
                ctx.restore();
              } else {
                ctx.globalAlpha = dim ? 0.18 : 1;
                ctx.fillStyle = baseColor;
                ctx.beginPath();
                ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
                ctx.fill();
              }

              if (isFocused || (hoverNode && String(hoverNode.id) === id)) {
                ctx.globalAlpha = 1;
                ctx.lineWidth = 2;
                ctx.strokeStyle = '#0f172a';
                ctx.beginPath();
                ctx.arc(node.x, node.y, radius + 2, 0, 2 * Math.PI, false);
                ctx.stroke();
              } else if (highlighted.focusId && isNeighbor) {
                ctx.globalAlpha = 1;
                ctx.lineWidth = 2;
                ctx.strokeStyle = '#f59e0b';
                ctx.beginPath();
                ctx.arc(node.x, node.y, radius + 1.5, 0, 2 * Math.PI, false);
                ctx.stroke();
              }

              // Show labels: ONTOLOGY view at zoom >= 0.5; all other views at zoom >= 1.2.
              const labelZoomThreshold = currentViewId === 'ONTOLOGY' ? 0.5 : 1.2;
              const showLabel = !dim && globalScale >= labelZoomThreshold;
              if (showLabel) {
                // Prefer human-readable name; fall back to properties.label then local part of id.
                const rawId = String(node.id || '');
                const isElementId = /^\d+:[0-9a-f\-]{36}:\d+$/i.test(rawId);
                const localId = rawId.includes(':') ? rawId.split(':').pop() : rawId;
                const fullLabel = node.name
                  || node.properties?.label
                  || node.properties?.local_name
                  || (isElementId ? null : localId)
                  || node.type;
                // Truncate long labels so they don't overflow into neighbors.
                const MAX_CHARS = 18;
                const label = fullLabel && fullLabel.length > MAX_CHARS
                  ? fullLabel.slice(0, MAX_CHARS - 1) + '…'
                  : fullLabel;

                // Clamp screen-space font size to 9–13 px regardless of zoom level.
                const screenFontSize = Math.max(9, Math.min(13, 11));
                const fontSize = screenFontSize / globalScale;
                ctx.font = `500 ${fontSize}px ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial`;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'top';

                const textWidth = ctx.measureText(label).width;
                const padX = fontSize * 0.35;
                const padY = fontSize * 0.20;
                const boxX = node.x - textWidth / 2 - padX;
                const boxY = node.y + radius + 3;
                const boxW = textWidth + padX * 2;
                const boxH = fontSize + padY * 2;
                const r2 = Math.min(boxH / 2, 2 / globalScale);

                // Background pill for readability
                ctx.globalAlpha = 0.82;
                ctx.fillStyle = '#ffffff';
                ctx.beginPath();
                ctx.moveTo(boxX + r2, boxY);
                ctx.lineTo(boxX + boxW - r2, boxY);
                ctx.arcTo(boxX + boxW, boxY, boxX + boxW, boxY + r2, r2);
                ctx.lineTo(boxX + boxW, boxY + boxH - r2);
                ctx.arcTo(boxX + boxW, boxY + boxH, boxX + boxW - r2, boxY + boxH, r2);
                ctx.lineTo(boxX + r2, boxY + boxH);
                ctx.arcTo(boxX, boxY + boxH, boxX, boxY + boxH - r2, r2);
                ctx.lineTo(boxX, boxY + r2);
                ctx.arcTo(boxX, boxY, boxX + r2, boxY, r2);
                ctx.closePath();
                ctx.fill();

                // Label text
                ctx.globalAlpha = 0.95;
                ctx.fillStyle = '#0f172a';
                ctx.fillText(label, node.x, boxY + padY);
              }

              ctx.globalAlpha = 1;
            }}
            onNodeClick={handleNodeClick}
            onNodeHover={handleNodeHover}
            onLinkHover={handleLinkHover}
            onBackgroundClick={() => {
              setSelectedNode(null);
              setHoverNode(null);
            }}
            linkDirectionalParticles={l => {
              const id = String(l.id ?? '');
              return highlighted.linkKeys && highlighted.linkKeys.has(id) ? 3 : 0;
            }}
            linkDirectionalParticleWidth={2}
            linkLabel={l => l.type || ''}
            linkColor={l => {
              const id = String(l.id ?? '');
              const dim = highlighted.linkKeys
                ? !highlighted.linkKeys.has(id)
                : false;
              if (dim) return 'rgba(148, 163, 184, 0.20)';
              const relType = l.type || l.relationship || '';
              if (currentViewId === 'DIGITAL_THREAD') {
                if (DT_REL_COLORS[relType]) return DT_REL_COLORS[relType];
              }
              if (currentViewId === 'ONTOLOGY') {
                if (ONTOLOGY_REL_COLORS[relType]) return ONTOLOGY_REL_COLORS[relType];
              }
              if (currentViewId === 'OSLC') {
                if (OSLC_REL_COLORS[relType]) return OSLC_REL_COLORS[relType];
              }
              return 'rgba(100, 116, 139, 0.85)';
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
        {((hoverNode && hoverNode.id !== selectedNode?.id) || hoverLink) && (() => {
          const TOOLTIP_W = 320;
          const TOOLTIP_H_EST = 160;
          const OFFSET = 12;
          const ptr = pointerRef.current;
          const left = ptr.x + OFFSET + TOOLTIP_W > dimensions.width
            ? Math.max(0, ptr.x - TOOLTIP_W - OFFSET)
            : ptr.x + OFFSET;
          const top = ptr.y + OFFSET + TOOLTIP_H_EST > dimensions.height
            ? Math.max(0, ptr.y - TOOLTIP_H_EST - OFFSET)
            : ptr.y + OFFSET;
          return (
            <div
              ref={tooltipRef}
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
            {currentViewId === 'DIGITAL_THREAD' && selectedNode.type && (
              <div className="px-6 pb-4">
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full"
                  onClick={() => {
                    const type = selectedNode.type;
                    const id = selectedNode.id;
                    if (type === 'SimulationDossier' || type === 'Dossier') navigate(`/engineer/simulation/dossiers/${id}`);
                    else if (type === 'Requirement') navigate(`/engineer/requirements`);
                    else if (type === 'Part') navigate(`/engineer/ap242/parts`);
                    else navigate(`/engineer/graph`);
                  }}
                >
                  Open Detail Page
                </Button>
              </div>
            )}
          </Card>
        )}
      </div>
    </div>
  );
}
