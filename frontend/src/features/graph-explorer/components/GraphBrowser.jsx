import { useRef, useState, useCallback, useMemo, useEffect, memo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import ForceGraph2D from 'react-force-graph-2d';
import { forceManyBody, forceX, forceY, forceCollide } from 'd3';
import { Check, ChevronsUpDown, Loader2, AlertCircle, ZoomIn, ZoomOut, Maximize2, Pause, Play, Search, X, Network, Share2, Layers, GitMerge, Route, Brain, Expand, Download, Palette, Hash, Copy, ExternalLink, MousePointerClick, Keyboard, Terminal as TerminalIcon, Boxes, Send, Trash2 } from 'lucide-react';
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { QUERY_CONFIG } from '@/constants';
import { getNodeTypes, getGraphData, findShortestPath, graphRAGQuery, graphRAGQueryStream, expandNode, getCommunities, searchNodes, graphDiff } from '@/services/graph.service';
import { getTRSChangelog } from '@/services/oslc.service';

// ---------------------------------------------------------------------------
// Lightweight inline Markdown renderer (no external dependency)
// Handles: ## headings, **bold**, *italic*, - bullets, 1. numbered lists, --- rules
// ---------------------------------------------------------------------------
function renderInlineMarkdown(text) {
  // **bold** and *italic* within a line
  const parts = [];
  const re = /(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`)/g;
  let last = 0;
  let m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    if (m[2]) parts.push(<strong key={m.index}>{m[2]}</strong>);
    else if (m[3]) parts.push(<em key={m.index}>{m[3]}</em>);
    else if (m[4]) parts.push(<code key={m.index} className="bg-muted px-0.5 rounded text-[10px] font-mono">{m[4]}</code>);
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts.length ? parts : text;
}

function SimpleMarkdown({ text }) {
  if (!text) return null;
  const lines = text.split('\n');
  const elements = [];
  let inList = false;
  let listItems = [];
  let listType = null;

  const flushList = (key) => {
    if (!listItems.length) return;
    const Tag = listType === 'ol' ? 'ol' : 'ul';
    elements.push(
      <Tag key={key} className={`ml-3 space-y-0.5 ${listType === 'ol' ? 'list-decimal' : 'list-disc'} list-outside pl-3`}>
        {listItems.map((li, i) => <li key={i} className="text-xs">{renderInlineMarkdown(li)}</li>)}
      </Tag>
    );
    listItems = [];
    listType = null;
    inList = false;
  };

  lines.forEach((line, i) => {
    if (/^#{1}\s/.test(line)) {
      flushList(i + '-fl');
      elements.push(<h2 key={i} className="text-xs font-bold mt-2 mb-0.5">{renderInlineMarkdown(line.replace(/^#+\s/, ''))}</h2>);
    } else if (/^#{2,3}\s/.test(line)) {
      flushList(i + '-fl');
      elements.push(<h3 key={i} className="text-[11px] font-semibold mt-1.5 mb-0.5 text-foreground/80">{renderInlineMarkdown(line.replace(/^#+\s/, ''))}</h3>);
    } else if (/^[-*]\s/.test(line)) {
      if (!inList || listType !== 'ul') { flushList(i + '-fl'); inList = true; listType = 'ul'; }
      listItems.push(line.replace(/^[-*]\s/, ''));
    } else if (/^\d+\.\s/.test(line)) {
      if (!inList || listType !== 'ol') { flushList(i + '-fl'); inList = true; listType = 'ol'; }
      listItems.push(line.replace(/^\d+\.\s/, ''));
    } else if (/^---+$/.test(line.trim())) {
      flushList(i + '-fl');
      elements.push(<hr key={i} className="my-1 border-border" />);
    } else if (!line.trim()) {
      flushList(i + '-fl');
      elements.push(<div key={i} className="h-1" />);
    } else {
      flushList(i + '-fl');
      elements.push(<p key={i} className="text-xs leading-relaxed">{renderInlineMarkdown(line)}</p>);
    }
  });
  flushList('end-fl');
  return <div className="space-y-0.5">{elements}</div>;
}

const GRAPH_VIEWS = {
  ENTERPRISE: {
    id: 'ENTERPRISE',
    label: 'Enterprise Knowledge Graph',
    description: 'Unified view of all engineering disciplines — AP239 PLCS, AP242 Design, AP243 MoSSEC and cross-domain linkage',
    apLevel: null,
    fixedNodeTypes: [],
    // Enterprise shows ALL node types — limit is the only restriction
    defaultLimit: 500,
    icon: Network
  },
  AP239: {
    id: 'AP239',
    label: 'AP239 (PLCS)',
    description: 'Product Life Cycle Support & Maintenance — product instances, requirements, work orders',
    apLevel: 'AP239',
    // AP239 PLCS core entity types
    fixedNodeTypes: ['Class', 'Slot', 'Requirement', 'Verification', 'WorkOrder', 'Part', 'Document', 'Organization', 'Person', 'Activity'],
    defaultLimit: 500,
    icon: Route
  },
  AP242: {
    id: 'AP242',
    label: 'AP242 (Design)',
    description: 'Complete AP242 Product Model — Parts, Assemblies, BOM hierarchy, Materials, Geometry, Product Definitions and cross-links to requirements',
    apLevel: 'AP242',
    // AP242 Design entity types — full product model graph
    fixedNodeTypes: [
      'Part', 'AP242Product', 'Assembly', 'Component', 'PartVersion',
      'Shape', 'GeometricModel', 'Position', 'Property',
      'Material', 'Document', 'BOMLink', 'ConfigurationItem', 'ProductDefinition',
    ],
    defaultLimit: 500,
    icon: Layers
  },
  AP243: {
    id: 'AP243',
    label: 'AP243 (MoSSEC)',
    description: 'AP243 Simulation Model — dossiers, runs, artifacts, evidence categories, KPIs, workflow methods, parameter studies, model instances',
    // Use fixedNodeTypes for MoSSEC simulation entities (not ap_level filter which returns raw schema classes)
    apLevel: null,
    fixedNodeTypes: [
      // Core AP243 SDD chain
      'SimulationDossier', 'SimulationRun', 'SimulationArtifact', 'EvidenceCategory',
      // AP243 domain model
      'ModelInstance', 'ModelType', 'Study', 'Context', 'AssociativeModelNetwork',
      'ActualActivity', 'MethodActivity', 'Method', 'Result', 'ContextEnvironment',
      // Extended AP243: workflow, KPI, validation
      'WorkflowMethod', 'TaskElement', 'ParameterStudy', 'AnalysisModel',
      'KPI', 'ValidationRecord',
      // Cross-domain anchors
      'MBSEElement', 'Requirement', 'Part',
    ],
    defaultLimit: 500,
    icon: GitMerge
  },
  ONTOLOGY: {
    id: 'ONTOLOGY',
    label: 'STEP Ontology (Merged)',
    description: 'Merged ISO 10303 ontology: AP239 PLCS + AP242 Design + AP243 MoSSEC — OWL T-Box + schema entities',
    apLevel: null,
    // Merged ontology includes all AP-level schema + OWL layer — no ap_level filter so all are included
    fixedNodeTypes: [
      // OWL / T-Box layer
      'Ontology', 'OntologyClass', 'OntologyProperty',
      'OWLClass', 'OWLObjectProperty', 'OWLDatatypeProperty',
      // AP239 PLCS schema classes
      'Class', 'Slot',
      // AP242 Design schema
      'Part', 'Assembly', 'Component', 'PartVersion', 'Shape', 'Property',
      // AP243 MoSSEC schema
      'ModelInstance', 'ModelType', 'Study', 'Context',
      // Shared cross-AP concepts
      'Requirement', 'Document', 'Material',
      // XSD bridge
      'XSDSchema', 'XSDComplexType', 'XSDElement', 'XSDAttribute'
    ],
    defaultLimit: 600,
    icon: Share2
  },
  OSLC: {
    id: 'OSLC',
    label: 'OSLC Integration',
    description: 'Cross-domain integration: STEP T-Box ↔ XSD Schema ↔ Requirements ↔ PLM resources via OSLC linkage',
    apLevel: null,
    // OSLC spans ontology, schema, requirements AND the PLM resources they link to
    fixedNodeTypes: [
      // Ontology layer
      'Ontology', 'OntologyClass', 'OntologyProperty', 'OWLClass', 'OWLObjectProperty',
      // XSD schema bridge
      'XSDSchema', 'XSDComplexType', 'XSDElement', 'XSDAttribute',
      // OSLC service resources
      'ServiceProvider', 'Service', 'Catalog', 'Link', 'ExternalOwlClass',
      // Domain resources linked via OSLC
      'Requirement', 'Part', 'Document'
    ],
    defaultLimit: 400,
    icon: Network
  },
  DIGITAL_THREAD: {
    id: 'DIGITAL_THREAD',
    label: 'Digital Thread',
    description: 'End-to-end lifecycle: AP239 Activity → AP242 Part/Assembly → AP243 Dossier → SimulationRun → EvidenceCategory → Requirement verification',
    apLevel: null,
    fixedNodeTypes: [
      // AP239 traceability anchors
      'Requirement', 'Activity',
      // AP242 product nodes
      'Part', 'Assembly', 'AP242Product',
      // AP243 simulation evidence chain
      'SimulationDossier', 'SimulationRun', 'SimulationArtifact',
      'EvidenceCategory', 'KPI', 'ValidationRecord',
    ],
    defaultLimit: 400,
    icon: GitMerge
  }
};

/** Color coding for STEP Ontology relationship types */
/** Universal relationship → color map covering all views.
 * Checked as a fallback when view-specific maps have no entry. */
const ALL_REL_COLORS = {
  // hierarchy / composition
  HAS_CHILD:                  '#3b82f6',
  HAS_PARENT:                 '#60a5fa',
  CONTAINS:                   '#6366f1',
  PART_OF:                    '#818cf8',
  // requirements / verification
  LINKED_TO_REQUIREMENT:      '#f97316',
  SATISFIED_BY_PART:          '#22c55e',
  VERIFIED_BY:                '#10b981',
  PROVES_COMPLIANCE_TO:       '#ef4444',
  // simulation / dossier
  HAS_SIMULATION_RUN:         '#3b82f6',
  CONTAINS_ARTIFACT:          '#a855f7',
  GENERATED:                  '#0ea5e9',
  HAS_APPROVAL:               '#eab308',
  // ontology / schema
  SUBCLASS_OF:                '#f97316',
  HAS_OBJECT_PROPERTY:        '#8b5cf6',
  HAS_DATATYPE_PROPERTY:      '#10b981',
  RANGE_CLASS:                '#3b82f6',
  DOMAIN_CLASS:               '#14b8a6',
  CLASSIFIED_BY:              '#f59e0b',
  DEFINES:                    '#8b5cf6',
  MAPS_TO_SCHEMA:             '#3b82f6',
  MAPS_TO_OSLC:               '#ec4899',
  EXTENDS:                    '#f97316',
  TYPED_BY:                   '#94a3b8',
  // cross-domain / OSLC
  IMPLEMENTS:                 '#06b6d4',
  REFERENCES:                 '#84cc16',
  RELATED_TO:                 '#a3a3a3',
  ALLOCATED_TO:               '#f43f5e',
  REALIZED_BY:                '#14b8a6',
  TRACED_TO:                  '#fbbf24',
};

/** Safely convert a hex color string to rgba(...). Falls back to dark-slate if not a valid hex. */
const hexToRgba = (hex, a) => {
  if (!hex || !hex.startsWith('#')) return `rgba(15,23,42,${a})`;
  const h = hex.replace('#', '');
  if (h.length < 6) return `rgba(15,23,42,${a})`;
  const r = parseInt(h.substring(0, 2), 16);
  const g = parseInt(h.substring(2, 4), 16);
  const b = parseInt(h.substring(4, 6), 16);
  if (isNaN(r) || isNaN(g) || isNaN(b)) return `rgba(15,23,42,${a})`;
  return `rgba(${r},${g},${b},${a})`;
};

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

/** E15: Unified Ontology Cross-Walk — maps shared concepts across AP239/242/243/OSLC */
const ONTOLOGY_CROSSWALK = {
  Part:                    { ap242: 'product_definition', ap239: 'product_as_individual', ap243: 'analysis_item', oslc: 'oslc:Resource' },
  Requirement:             { ap242: 'requirement_assignment', ap239: 'requirement_property', ap243: 'verification_requirement', oslc: 'oslc_rm:Requirement' },
  SimulationDossier:       { ap242: null, ap239: 'activity_method', ap243: 'simulation_package', oslc: 'oslc_auto:AutomationPlan' },
  SimulationRun:           { ap242: null, ap239: 'executed_action', ap243: 'analysis_run', oslc: 'oslc_auto:AutomationResult' },
  SimulationArtifact:      { ap242: 'document_file', ap239: 'document', ap243: 'result_data_package', oslc: 'oslc_am:Resource' },
  EvidenceCategory:        { ap242: null, ap239: 'classification', ap243: 'evidence_category', oslc: null },
  OntologyClass:           { ap242: 'entity_definition', ap239: 'entity_definition', ap243: 'entity_definition', oslc: 'oslc:ResourceShape' },
  OntologyProperty:        { ap242: 'attribute_definition', ap239: 'attribute_definition', ap243: 'attribute_definition', oslc: 'oslc:Property' },
  XSDSchema:               { ap242: 'schema', ap239: 'schema', ap243: 'schema', oslc: null },
};

const AP_COLORS = {
  ap242: '#3b82f6', // blue
  ap239: '#f97316', // orange
  ap243: '#8b5cf6', // purple
  oslc:  '#ec4899', // pink
};

/** Nodes rendered immediately on first load; the remainder streams in as a background batch. */
const INITIAL_BATCH = 200;

export default memo(function GraphBrowser({ initialView = 'ENTERPRISE' }) {
  const fgRef = useRef(null);
  const containerRef = useRef(null);
  
  // ── E1: Context menu state ──
  const [contextMenu, setContextMenu] = useState(null); // { x, y, node }
  
  // ── E2: Path Finder state ──
  const [pathSource, setPathSource] = useState('');
  const [pathSourceName, setPathSourceName] = useState(''); // display name
  const [pathTarget, setPathTarget] = useState('');
  const [pathTargetName, setPathTargetName] = useState(''); // display name
  const [pathSourceSearch, setPathSourceSearch] = useState('');
  const [pathTargetSearch, setPathTargetSearch] = useState('');
  const [pathSourceOpen, setPathSourceOpen] = useState(false);
  const [pathTargetOpen, setPathTargetOpen] = useState(false);
  const [pathResult, setPathResult] = useState(null);
  const [pathLoading, setPathLoading] = useState(false);
  const [pathHighlight, setPathHighlight] = useState(null); // { nodeIds: Set, linkKeys: Set }
  
  // ── E3: GraphRAG state ──
  const [ragQuestion, setRagQuestion] = useState('');
  const [ragMessages, setRagMessages] = useState([]); // [{ id, role:'user'|'assistant', content, sources, nodes }]
  const [ragLoading, setRagLoading] = useState(false);
  const [ragHighlight, setRagHighlight] = useState(null); // Set<string> of node IDs matched from RAG sources
  const [ragOverlayNodes, setRagOverlayNodes] = useState([]); // RAG result nodes injected into graph
  const [ragOverlayLinks, setRagOverlayLinks] = useState([]); // edges for overlay / search-expansion links
  const chatEndRef = useRef(null); // auto-scroll anchor for chat panel
  const ragStreamRef = useRef(null); // AbortController for active SSE stream
  
  // ── E7: Multi-select state ──
  const [multiSelected, setMultiSelected] = useState(new Set());
  
  // ── E19: Lasso/rectangle selection state ──
  const [lassoStart, setLassoStart] = useState(null); // { x, y } screen coords
  const [lassoEnd, setLassoEnd] = useState(null);
  const lassoActive = useRef(false);
  
  // ── E8: Heatmap mode ──
  const [heatmapMode, setHeatmapMode] = useState('off'); // off | degree | community

  // ── Label display mode ──
  const [labelMode, setLabelMode] = useState('name'); // name | type | id
  
  // ── E11: Export ──
  const [showExport, setShowExport] = useState(false);
  
  // ── E14: Communities ──
  const [communityMap, setCommunityMap] = useState(null); // { id → community_id }
  const [communityColors, setCommunityColors] = useState({});
  
  // ── E6: Advanced property filters ──
  const [propFilters, setPropFilters] = useState([]); // [{ key, op, value }]
  
  // ── E16: Keyboard shortcuts ──
  const [showShortcuts, setShowShortcuts] = useState(false);
  
  // ── E17: Cypher editor ──
  const [cypherQuery, setCypherQuery] = useState('');
  const [cypherLoading, setCypherLoading] = useState(false);
  const [cypherResult, setCypherResult] = useState(null);
  
  // ── E20: Graph diff ──
  const [diffTypesA, setDiffTypesA] = useState('');
  const [diffTypesB, setDiffTypesB] = useState('');
  const [diffResult, setDiffResult] = useState(null);
  const [diffLoading, setDiffLoading] = useState(false);
  const [diffHighlight, setDiffHighlight] = useState(null); // { added: Set, removed: Set }
  
  // ── E13: TRS time-travel ──
  const [trsEvents, setTrsEvents] = useState([]);
  const [trsLoading, setTrsLoading] = useState(false);

  // ── AI Panel ──
  const [aiPanelOpen, setAiPanelOpen] = useState(false);
  const [aiPanelPos, setAiPanelPos] = useState(null); // null = CSS default (bottom-right)
  const [aiPanelSize, setAiPanelSize] = useState({ w: 360, h: 520 });
  const aiPanelRef = useRef(null);
  const aiDragRef = useRef(null);   // { mx, my, ox, oy }
  const aiResizeRef = useRef(null); // { mx, my, ow, oh }

  useEffect(() => {
    const onMove = (e) => {
      if (aiDragRef.current) {
        const d = aiDragRef.current;
        setAiPanelPos({
          x: Math.max(0, d.ox + e.clientX - d.mx),
          y: Math.max(0, d.oy + e.clientY - d.my),
        });
      }
      if (aiResizeRef.current) {
        const d = aiResizeRef.current;
        setAiPanelSize({
          w: Math.max(280, d.ow + e.clientX - d.mx),
          h: Math.max(300, d.oh + e.clientY - d.my),
        });
      }
    };
    const onUp = () => { aiDragRef.current = null; aiResizeRef.current = null; };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
  }, []);

  const startAiDrag = (e) => {
    if (e.button !== 0) return;
    e.preventDefault();
    const el = aiPanelRef.current;
    const container = containerRef.current;
    if (!el || !container) return;
    const elRect = el.getBoundingClientRect();
    const parentRect = container.getBoundingClientRect();
    const ox = elRect.left - parentRect.left;
    const oy = elRect.top - parentRect.top;
    setAiPanelPos({ x: ox, y: oy });
    aiDragRef.current = { mx: e.clientX, my: e.clientY, ox, oy };
  };

  const startAiResize = (e) => {
    if (e.button !== 0) return;
    e.preventDefault();
    e.stopPropagation();
    aiResizeRef.current = { mx: e.clientX, my: e.clientY, ow: aiPanelSize.w, oh: aiPanelSize.h };
  };

  // ── Sidebar tool tab ──
  const [sidebarTab, setSidebarTab] = useState('filters');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  
  const [currentViewId, setCurrentViewId] = useState(initialView);
  const currentView = GRAPH_VIEWS[currentViewId] || GRAPH_VIEWS.ENTERPRISE;
  
  // Create derived state from the current view configuration
  const fixedNodeTypes = currentView.fixedNodeTypes;
  const apLevel = currentView.apLevel;
  
  const [selectedNodeTypes, setSelectedNodeTypes] = useState(fixedNodeTypes);
  
  // When view changes, update selection state and reset limit to view default
  useEffect(() => {
    setSelectedNodeTypes(currentView.fixedNodeTypes);
    // Reset to per-view default limit so Enterprise/ONTOLOGY loads more nodes
    const viewDefault = [currentView.defaultLimit ?? 200];
    setLimit(viewDefault);
    setDebouncedLimit(viewDefault); // sync immediately — no need to wait 600ms on a view switch
    setSearchQuery("");
    setSelectedNode(null);
    setPathHighlight(null);
    setPathResult(null);
    setPathSource('');
    setPathSourceName('');
    setPathTarget('');
    setPathTargetName('');
  }, [currentViewId]);

  const [nodeTypeOpen, setNodeTypeOpen] = useState(false);
  const [nodeTypeSearch, setNodeTypeSearch] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState("");

  // Debounce search query by 250 ms so we don’t fire API on every keystroke
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearchQuery(searchQuery.trim()), 250);
    return () => clearTimeout(t);
  }, [searchQuery]);

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

  const [limit, setLimit] = useState(() => [GRAPH_VIEWS[initialView]?.defaultLimit ?? 200]);
  // Debounce the limit used in query keys — slider drags fire setLimit on every step,
  // so without this each 50-node increment would launch a separate Neo4j query.
  const [debouncedLimit, setDebouncedLimit] = useState(() => [GRAPH_VIEWS[initialView]?.defaultLimit ?? 200]);
  useEffect(() => {
    const t = setTimeout(() => setDebouncedLimit(limit), 600);
    return () => clearTimeout(t);
  }, [limit]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [breadcrumbs, setBreadcrumbs] = useState([]);
  const navigate = useNavigate();
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
    queryFn: () => getNodeTypes(),
    staleTime: 5 * 60 * 1000, // 5 min — node types rarely change
    gcTime: 10 * 60 * 1000,   // keep in cache 10 min
  });

  // ── E2: Path finder node search queries (name → ID resolution) ──
  const { data: pathSourceResults } = useQuery({
    queryKey: ['path-search-source', pathSourceSearch],
    queryFn: () => searchNodes({ q: pathSourceSearch, limit: 8 }),
    enabled: pathSourceSearch.trim().length >= 2,
    staleTime: 30_000,
  });
  const { data: pathTargetResults } = useQuery({
    queryKey: ['path-search-target', pathTargetSearch],
    queryFn: () => searchNodes({ q: pathTargetSearch, limit: 8 }),
    enabled: pathTargetSearch.trim().length >= 2,
    staleTime: 30_000,
  });

  // ── Main graph search (API-backed, searches ALL nodes in DB) ──
  const { data: searchResults, isFetching: searchFetching } = useQuery({
    queryKey: ['graph-search', debouncedSearchQuery],
    queryFn: () => searchNodes({ q: debouncedSearchQuery, limit: 20 }),
    // Backend returns { results: [...], total: N } — normalise to plain array
    select: (data) => (Array.isArray(data) ? data : (data?.results ?? [])),
    enabled: debouncedSearchQuery.length >= 2,
    staleTime: 30_000,
  });

  // ── Phase-1: first INITIAL_BATCH nodes — renders immediately ──────────────
  // Use debouncedLimit in query keys so slider drag doesn't fire a request per step.
  const batch1Limit = Math.min(debouncedLimit[0], INITIAL_BATCH);
  // Only request 1-hop neighbours when the user has manually filtered to a
  // small custom type set (≤4 types). For view-default selections (e.g. AP239
  // with 10 types) neighbours add thousands of extra nodes and slow the load.
  const viewDefaultTypes = currentView.fixedNodeTypes;
  const isUserFilteredTypes =
    selectedNodeTypes.length > 0 &&
    selectedNodeTypes.length <= 4 &&
    !(selectedNodeTypes.length === viewDefaultTypes.length &&
      selectedNodeTypes.every(t => viewDefaultTypes.includes(t)));
  const {
    data: graphDataBatch1,
    isLoading,
    isFetching: isFetchingBatch1,
    error,
  } = useQuery({
    queryKey: ['graph-data', 'b1', selectedNodeTypes, batch1Limit, apLevel],
    queryFn: () => {
      const params = { limit: batch1Limit, skip: 0 };
      if (selectedNodeTypes.length > 0) {
        params.node_types = selectedNodeTypes.join(',');
        if (isUserFilteredTypes) params.include_neighbors = true;
      }
      if (apLevel) params.ap_level = apLevel;
      return getGraphData(params);
    },
    refetchOnWindowFocus: false,
    staleTime: QUERY_CONFIG.STALE_TIME,
    gcTime: QUERY_CONFIG.CACHE_TIME,
    placeholderData: (previousData) => previousData,
  });
  // True when we have stale/placeholder data and a fresh fetch is in-flight.
  // Used to show refreshing indicator during view switches.
  const isGraphRefetching = isFetchingBatch1 && !!graphDataBatch1;

  // ── Phase-2: remaining nodes — loads silently once phase 1 resolves ────────
  const needsSecondBatch = debouncedLimit[0] > INITIAL_BATCH;
  const batch2Limit = debouncedLimit[0] - INITIAL_BATCH;
  const {
    data: graphDataBatch2,
    isFetching: isFetchingMore,
  } = useQuery({
    queryKey: ['graph-data', 'b2', selectedNodeTypes, debouncedLimit, apLevel],
    queryFn: () => {
      const params = { limit: batch2Limit, skip: INITIAL_BATCH };
      if (selectedNodeTypes.length > 0) params.node_types = selectedNodeTypes.join(',');
      // neighbours already loaded in batch 1 — skip for batch 2
      if (apLevel) params.ap_level = apLevel;
      return getGraphData(params);
    },
    enabled: !!graphDataBatch1 && needsSecondBatch,
    refetchOnWindowFocus: false,
    staleTime: QUERY_CONFIG.STALE_TIME,
    gcTime: QUERY_CONFIG.CACHE_TIME,
  });

  // ── Merge batches ─────────────────────────────────────────────────────────
  const graphData = useMemo(() => {
    if (!graphDataBatch1) return null;
    if (!graphDataBatch2) return graphDataBatch1;
    const b1NodeIds = new Set((graphDataBatch1.nodes || []).map(n => String(n.id)));
    const b1LinkIds = new Set(
      (graphDataBatch1.links || []).map(l => String(l.id ?? `${l.source}__${l.target}`))
    );
    const extraNodes = (graphDataBatch2.nodes || []).filter(n => !b1NodeIds.has(String(n.id)));
    const extraLinks = (graphDataBatch2.links || []).filter(l => {
      const lid = String(l.id ?? `${l.source}__${l.target}`);
      return !b1LinkIds.has(lid);
    });
    const allNodeTypes = [
      ...new Set([
        ...(graphDataBatch1.metadata?.node_types || []),
        ...(graphDataBatch2.metadata?.node_types || []),
      ]),
    ];
    return {
      nodes: [...(graphDataBatch1.nodes || []), ...extraNodes],
      links: [...(graphDataBatch1.links || []), ...extraLinks],
      metadata: {
        ...graphDataBatch1.metadata,
        node_count: (graphDataBatch1.nodes || []).length + extraNodes.length,
        link_count: (graphDataBatch1.links || []).length + extraLinks.length,
        node_types: allNodeTypes,
      },
    };
  }, [graphDataBatch1, graphDataBatch2]);
  const normalizedGraph = useMemo(() => {
    if (!graphData) return null;
    // Merge base graph nodes with any RAG overlay nodes
    const baseNodes = graphData.nodes || [];
    const baseIds = new Set(baseNodes.map(n => String(n.id)));
    const overlayFiltered = ragOverlayNodes.filter(n => !baseIds.has(String(n.id)));
    const allNodes = [...baseNodes, ...overlayFiltered];
    const nodes = allNodes.map(n => {
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
    const links = [...(graphData.links || []), ...ragOverlayLinks].map((l, idx) => {
      const sourceId = typeof l.source === 'string' ? String(l.source) : String(l.source?.id);
      const targetId = typeof l.target === 'string' ? String(l.target) : String(l.target?.id);
      return {
        ...l,
        // Ensure every link has a stable id for highlight matching
        id: l.id ?? `${sourceId}__${targetId}__${idx}`,
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
  }, [graphData, ragOverlayNodes, ragOverlayLinks]);

  // ── E6: Client-side property filter ──
  const displayGraph = useMemo(() => {
    if (!normalizedGraph) return null;
    if (!propFilters || propFilters.length === 0) return normalizedGraph;
    const passesFilters = (node) => {
      for (const f of propFilters) {
        if (!f.key || !f.value) continue;
        const val = String(node.properties?.[f.key] ?? node[f.key] ?? '').toLowerCase();
        const target = f.value.toLowerCase();
        switch (f.op) {
          case 'contains': if (!val.includes(target)) return false; break;
          case 'equals': if (val !== target) return false; break;
          case 'starts': if (!val.startsWith(target)) return false; break;
          case 'notcontains': if (val.includes(target)) return false; break;
          default: if (!val.includes(target)) return false;
        }
      }
      return true;
    };
    const nodes = normalizedGraph.nodes.filter(passesFilters);
    const nodeSet = new Set(nodes.map(n => n.id));
    const links = normalizedGraph.links.filter(l => {
      const s = typeof l.source === 'string' ? l.source : String(l.source?.id ?? l.source);
      const t = typeof l.target === 'string' ? l.target : String(l.target?.id ?? l.target);
      return nodeSet.has(s) && nodeSet.has(t);
    });
    const neighbors = new Map();
    const addN = (a, b) => { if (!neighbors.has(a)) neighbors.set(a, new Set()); neighbors.get(a).add(b); };
    links.forEach(l => { const s = typeof l.source === 'string' ? l.source : String(l.source?.id); const t = typeof l.target === 'string' ? l.target : String(l.target?.id); addN(s, t); addN(t, s); });
    return { nodes, links, neighbors, metadata: normalizedGraph.metadata };
  }, [normalizedGraph, propFilters]);

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
    // Collision force — radius controls minimum node separation.
    // Use a generous radius so nodes spread out and labels have breathing room.
    fgRef.current.d3Force('collide', forceCollide().radius(16).strength(0.7));
    
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
  }, [normalizedGraph, selectedNodeTypes, currentViewId]);
  const highlighted = useMemo(() => {
    // E2: If path is highlighted, use path highlight
    if (pathHighlight && pathHighlight.nodeIds.size > 0) {
      return {
        focusId: null,
        nodeIds: pathHighlight.nodeIds,
        linkKeys: pathHighlight.linkKeys,
        isPath: true,
        isRag: false,
      };
    }

    // E3: If RAG result nodes are highlighted, show them
    if (ragHighlight && ragHighlight.size > 0) {
      return {
        focusId: null,
        nodeIds: ragHighlight,
        linkKeys: null,
        isPath: false,
        isRag: true,
      };
    }

    const focus = selectedNode || hoverNode;
    if (!normalizedGraph || !focus) {
      return {
        focusId: null,
        nodeIds: null,
        linkKeys: null,
        isPath: false,
      };
    }
    const focusId = String(focus.id);
    const nodeIds = new Set([focusId]);
    const nbrs = normalizedGraph.neighbors.get(focusId);
    if (nbrs) {
      nbrs.forEach(id => nodeIds.add(id));
    }
    // E7: Include multi-selected nodes
    multiSelected.forEach(id => nodeIds.add(id));
    
    const linkKeys = new Set();
    normalizedGraph.links.forEach(l => {
      const s = typeof l.source === 'object' ? String(l.source?.id) : String(l.source);
      const t = typeof l.target === 'object' ? String(l.target?.id) : String(l.target);
      if (nodeIds.has(s) && nodeIds.has(t) && (s === focusId || t === focusId)) {
        linkKeys.add(l.id);
      }
    });
    return {
      focusId,
      nodeIds,
      linkKeys,
      isPath: false,
      isRag: false,
    };
  }, [normalizedGraph, selectedNode, hoverNode, pathHighlight, ragHighlight, multiSelected]);
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
      Assembly: '#b91c1c',
      Component: '#f87171',
      GeometricModel: '#c2410c',

      // AP239 (PLCS) - Green/Teal Scheme
      Activity: '#34d399',
      Resource: '#047857',
      Breakdown: '#6ee7b7',

      // AP243 (MoSSEC) - Blue/Purple Scheme
      Model: '#2563eb',
      Analysis: '#1d4ed8',
      Scenario: '#60a5fa',

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
    setPointer({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    });
  }, []);

  // ── E1: Context menu handler ──
  const handleNodeRightClick = useCallback((node, event) => {
    event.preventDefault();
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    setContextMenu({
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
      node,
    });
  }, []);

  const dismissContextMenu = useCallback(() => setContextMenu(null), []);

  const handleContextAction = useCallback(async (action, node) => {
    setContextMenu(null);
    if (!node) return;
    switch (action) {
      case 'expand': {
        try {
          const res = await expandNode(String(node.id), 2);
          const data = res?.data ?? res;
          const expNodes = (data.nodes || []).map(nn => ({
            ...nn,
            id: String(nn.id),
            name: nn.name || nn.properties?.label || nn.id,
            labels: Array.isArray(nn.labels) ? nn.labels : [nn.type].filter(Boolean),
            searchLabel: (nn.name || nn.id)?.toLowerCase() || '',
          }));
          const expLinks = (data.links || []).map((l, idx) => ({
            ...l,
            id: l.id ?? `${l.source}__${l.target}__exp${idx}`,
            source: String(l.source?.id ?? l.source),
            target: String(l.target?.id ?? l.target),
          }));
          if (expNodes.length > 0) {
            setRagOverlayNodes(prev => {
              const existing = new Set(prev.map(n => n.id));
              return [...prev, ...expNodes.filter(n => !existing.has(n.id))];
            });
          }
          if (expLinks.length > 0) {
            setRagOverlayLinks(prev => {
              const existing = new Set(prev.map(l => l.id));
              return [...prev, ...expLinks.filter(l => !existing.has(l.id))];
            });
          }
          handleNodeClick(node);
        } catch (err) { console.error('Expand failed', err); }
        break;
      }
      case 'pin':
        // Pin/unpin: fix node position
        if (node.fx != null) { node.fx = undefined; node.fy = undefined; }
        else { node.fx = node.x; node.fy = node.y; }
        if (fgRef.current) fgRef.current.d3ReheatSimulation();
        break;
      case 'copy':
        navigator.clipboard?.writeText(String(node.id));
        break;
      case 'detail':
        setSelectedNode(node);
        break;
      case 'multiselect':
        setMultiSelected(prev => {
          const next = new Set(prev);
          if (next.has(String(node.id))) next.delete(String(node.id));
          else next.add(String(node.id));
          return next;
        });
        break;
      default: break;
    }
  }, [handleNodeClick]);

  // ── E2: Path Finder handler ──
  const handleFindPath = useCallback(async () => {
    if (!pathSource || !pathTarget) return;
    setPathLoading(true);
    setPathResult(null);
    setPathHighlight(null);
    try {
      const res = await findShortestPath(pathSource, pathTarget);
      setPathResult(res);
      if (res.found) {
        const nodeIds = new Set(res.nodes.map(n => n.id));
        const linkKeys = new Set();
        // Match path links to existing graph links
        if (normalizedGraph) {
          for (const pl of res.links) {
            for (const gl of normalizedGraph.links) {
              const gs = typeof gl.source === 'object' ? String(gl.source?.id) : String(gl.source);
              const gt = typeof gl.target === 'object' ? String(gl.target?.id) : String(gl.target);
              if ((gs === pl.source && gt === pl.target) || (gs === pl.target && gt === pl.source)) {
                linkKeys.add(gl.id);
              }
            }
          }
        }
        setPathHighlight({ nodeIds, linkKeys });
      }
    } catch (err) {
      setPathResult({ found: false, error: err.message });
    } finally {
      setPathLoading(false);
    }
  }, [pathSource, pathTarget, normalizedGraph]);

  // ── E3: GraphRAG handler ──
  // Auto-scroll chat to bottom on new message or while loading
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [ragMessages, ragLoading]);

  const handleRAGQuery = useCallback(() => {
    const q = ragQuestion.trim();
    if (!q) return;

    // Cancel any in-flight stream
    if (ragStreamRef.current) {
      ragStreamRef.current.abort();
      ragStreamRef.current = null;
    }

    const userMsg = { id: Date.now(), role: 'user', content: q };
    const assistantId = Date.now() + 1;
    const assistantMsg = {
      id: assistantId,
      role: 'assistant',
      content: '',
      streaming: true,
      sources: [],
      nodes: [],
    };
    setRagMessages(prev => [...prev, userMsg, assistantMsg]);
    setRagQuestion('');
    setRagLoading(true);
    setRagHighlight(null);
    setRagOverlayLinks([]);

    ragStreamRef.current = graphRAGQueryStream(
      q,
      5,
      currentViewId,
      selectedNodeTypes,
      debouncedLimit[0],
      {
        onNodes(data) {
          // Immediately inject graph data before LLM finishes
          const ragNodes = data.nodes || [];
          const ragLinks = data.links || [];
          const sourceUids = new Set((data.sources || []).map(s => s.uid).filter(Boolean));
          if (ragLinks.length > 0) {
            setRagOverlayLinks(ragLinks.map(l => ({ ...l, _ragOverlay: true })));
          }
          if (ragNodes.length > 0) {
            setRagOverlayNodes(ragNodes.map(rn => ({
              id: rn.id,
              name: rn.name || rn.id,
              type: rn.type || 'RAGHit',
              labels: rn.labels || [rn.type || 'RAGHit'],
              properties: { uid: rn.id, score: rn.score },
              _ragOverlay: true,
            })));
          }
          if (sourceUids.size > 0) {
            setRagHighlight(sourceUids);
          } else if (ragNodes.length > 0) {
            setRagHighlight(new Set(ragNodes.map(rn => String(rn.id))));
          }
          setRagMessages(prev => prev.map(m =>
            m.id === assistantId
              ? { ...m, sources: data.sources || [], nodes: ragNodes }
              : m
          ));
        },
        onChunk(text) {
          setRagMessages(prev => prev.map(m =>
            m.id === assistantId
              ? { ...m, content: m.content + text }
              : m
          ));
        },
        onDone() {
          setRagMessages(prev => prev.map(m =>
            m.id === assistantId ? { ...m, streaming: false } : m
          ));
          setRagLoading(false);
          ragStreamRef.current = null;
        },
        onError(msg) {
          setRagMessages(prev => prev.map(m =>
            m.id === assistantId
              ? { ...m, content: m.content || `⚠ ${msg}`, streaming: false }
              : m
          ));
          setRagLoading(false);
          ragStreamRef.current = null;
        },
      },
    );
  }, [ragQuestion, currentViewId, selectedNodeTypes, debouncedLimit]);

  // ── E3: Auto-zoom graph to RAG-highlighted nodes when result arrives ──
  useEffect(() => {
    if (!ragHighlight || ragHighlight.size === 0) return;
    // Brief delay so overlay nodes have time to be injected into the ForceGraph
    const t = setTimeout(() => {
      if (!fgRef.current) return;
      try {
        // Zoom to fit only the matched nodes; fall back to full fit if none visible
        fgRef.current.zoomToFit(700, 80, node => ragHighlight.has(String(node.id)));
      } catch (_) {
        try { fgRef.current.zoomToFit(700, 80); } catch (__) {}
      }
    }, 450);
    return () => clearTimeout(t);
  }, [ragHighlight]);

  // ── E11: Export handlers ──
  const handleExportPNG = useCallback(() => {
    if (!containerRef.current) return;
    const canvas = containerRef.current.querySelector('canvas');
    if (!canvas) return;
    const link = document.createElement('a');
    link.download = `graph-${currentViewId}-${Date.now()}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  }, [currentViewId]);

  const handleExportCSV = useCallback(() => {
    if (!normalizedGraph) return;
    const rows = ['id,name,type,labels'];
    for (const n of normalizedGraph.nodes) {
      rows.push(`"${n.id}","${(n.name || '').replace(/"/g, '""')}","${n.type}","${(n.labels || []).join(';')}"`);
    }
    const blob = new Blob([rows.join('\n')], { type: 'text/csv' });
    const link = document.createElement('a');
    link.download = `graph-nodes-${currentViewId}-${Date.now()}.csv`;
    const url = URL.createObjectURL(blob);
    link.href = url;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  }, [normalizedGraph, currentViewId]);

  const handleExportLinksCSV = useCallback(() => {
    if (!normalizedGraph) return;
    const rows = ['source,target,type'];
    for (const l of normalizedGraph.links) {
      const s = typeof l.source === 'object' ? String(l.source?.id) : String(l.source);
      const t = typeof l.target === 'object' ? String(l.target?.id) : String(l.target);
      rows.push(`"${s}","${t}","${l.type}"`);
    }
    const blob = new Blob([rows.join('\n')], { type: 'text/csv' });
    const link = document.createElement('a');
    link.download = `graph-links-${currentViewId}-${Date.now()}.csv`;
    const url = URL.createObjectURL(blob);
    link.href = url;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  }, [normalizedGraph, currentViewId]);

  // ── E14: Community detection handler ──
  const handleDetectCommunities = useCallback(async () => {
    try {
      const res = await getCommunities();
      const map = {};
      for (const item of res.communities || []) {
        map[item.id] = item.community;
      }
      setCommunityMap(map);
      // Generate distinct colors for each community
      const COMM_PALETTE = [
        '#ef4444','#3b82f6','#10b981','#f59e0b','#8b5cf6','#ec4899',
        '#06b6d4','#84cc16','#f97316','#6366f1','#14b8a6','#e11d48',
        '#0ea5e9','#a855f7','#22c55e','#eab308','#d946ef','#0891b2',
      ];
      const colors = {};
      const uniqueComms = [...new Set(Object.values(map))];
      uniqueComms.forEach((c, i) => { colors[c] = COMM_PALETTE[i % COMM_PALETTE.length]; });
      setCommunityColors(colors);
      setHeatmapMode('community');
    } catch (err) {
      console.error('Community detection failed', err);
    }
  }, []);

  // ── E20: Graph diff handler ──
  const handleGraphDiff = useCallback(async () => {
    if (!diffTypesA && !diffTypesB) return;
    setDiffLoading(true);
    try {
      const typesA = diffTypesA.split(',').map(t => t.trim()).filter(Boolean);
      const typesB = diffTypesB.split(',').map(t => t.trim()).filter(Boolean);
      const res = await graphDiff(typesA, typesB);
      setDiffResult(res);
      setDiffHighlight({
        added: new Set(res.added_nodes || []),
        removed: new Set(res.removed_nodes || []),
      });
    } catch (err) {
      console.error('Graph diff failed:', err);
      setDiffResult({ error: String(err) });
    } finally {
      setDiffLoading(false);
    }
  }, [diffTypesA, diffTypesB]);

  // ── E13: TRS changelog fetch handler ──
  const handleFetchTRS = useCallback(async () => {
    setTrsLoading(true);
    try {
      const res = await getTRSChangelog();
      // Parse RDF/JSON response — extract change events
      // Response might be raw RDF or JSON; handle gracefully
      if (Array.isArray(res)) {
        setTrsEvents(res);
      } else if (res && typeof res === 'object') {
        // Try to extract events from RDF-like response
        const events = [];
        const entries = res.changes || res.events || res['@graph'] || [];
        for (const e of (Array.isArray(entries) ? entries : [])) {
          events.push({
            type: e.type || e['@type'] || 'unknown',
            resource: e.resource || e.changed || e['trs:changed'] || '',
            order: e.order || events.length,
            uri: e.uri || e['@id'] || '',
          });
        }
        setTrsEvents(events.length > 0 ? events : [{ type: 'info', resource: 'No changelog events found', order: 0, uri: '' }]);
      }
    } catch (err) {
      console.error('TRS changelog fetch failed:', err);
      setTrsEvents([{ type: 'error', resource: `Failed: ${err}`, order: 0, uri: '' }]);
    } finally {
      setTrsLoading(false);
    }
  }, []);

  // ── E5: Degree map (node size by connections) ──
  const degreeMap = useMemo(() => {
    if (!normalizedGraph) return {};
    const map = {};
    for (const n of normalizedGraph.nodes) {
      const nbrs = normalizedGraph.neighbors.get(String(n.id));
      map[n.id] = nbrs ? nbrs.size : 0;
    }
    return map;
  }, [normalizedGraph]);

  const maxDegree = useMemo(() => Math.max(1, ...Object.values(degreeMap)), [degreeMap]);

  // ── E16: Keyboard shortcuts ──
  useEffect(() => {
    const handler = (e) => {
      // Don't capture when typing in inputs
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      switch (e.key) {
        case 'f': case 'F':
          if (fgRef.current) fgRef.current.zoomToFit(600, 40);
          break;
        case '+': case '=':
          if (fgRef.current) fgRef.current.zoom(fgRef.current.zoom() * 1.3, 300);
          break;
        case '-':
          if (fgRef.current) fgRef.current.zoom(fgRef.current.zoom() / 1.3, 300);
          break;
        case ' ':
          e.preventDefault();
          toggleLayout();
          break;
        case 'Escape':
          setSelectedNode(null);
          setHoverNode(null);
          setContextMenu(null);
          setPathHighlight(null);
          setMultiSelected(new Set());
          break;
        case '?':
          setShowShortcuts(prev => !prev);
          break;
        default: break;
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [toggleLayout]);

  // ── E19: Lasso rectangle selection (Shift+drag on canvas) ──
  const handleCanvasMouseDown = useCallback((e) => {
    if (!e.shiftKey) return;
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    lassoActive.current = true;
    const pt = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    setLassoStart(pt);
    setLassoEnd(pt);
  }, []);

  const handleCanvasMouseMove = useCallback((e) => {
    if (!lassoActive.current) return;
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    setLassoEnd({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  }, []);

  const handleCanvasMouseUp = useCallback(() => {
    if (!lassoActive.current || !lassoStart || !lassoEnd || !fgRef.current) {
      lassoActive.current = false;
      setLassoStart(null);
      setLassoEnd(null);
      return;
    }
    lassoActive.current = false;
    // Convert screen coords to graph coords
    const s2g = fgRef.current.screen2GraphCoords;
    if (!s2g) { setLassoStart(null); setLassoEnd(null); return; }
    const g1 = s2g(Math.min(lassoStart.x, lassoEnd.x), Math.min(lassoStart.y, lassoEnd.y));
    const g2 = s2g(Math.max(lassoStart.x, lassoEnd.x), Math.max(lassoStart.y, lassoEnd.y));
    const minX = Math.min(g1.x, g2.x), maxX = Math.max(g1.x, g2.x);
    const minY = Math.min(g1.y, g2.y), maxY = Math.max(g1.y, g2.y);
    const selected = new Set();
    for (const n of (displayGraph?.nodes || [])) {
      if (n.x >= minX && n.x <= maxX && n.y >= minY && n.y <= maxY) {
        selected.add(String(n.id));
      }
    }
    setMultiSelected(prev => {
      const next = new Set(prev);
      selected.forEach(id => next.add(id));
      return next;
    });
    setLassoStart(null);
    setLassoEnd(null);
  }, [lassoStart, lassoEnd, displayGraph]);

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
      <div
        className="h-full border-r bg-background overflow-y-auto shrink-0 transition-all duration-300 ease-in-out"
        style={{ width: sidebarCollapsed ? 0 : 320, minWidth: 0, overflow: sidebarCollapsed ? 'hidden' : 'auto' }}
      >
        <div className="p-4 space-y-3" style={{ width: 320 }}>
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

          {/* Sidebar Tab Switcher */}
          <Tabs value={sidebarTab} onValueChange={setSidebarTab} className="w-full">
            <TabsList className="grid w-full grid-cols-3 h-8">
              <TabsTrigger value="filters" className="text-xs px-1">Filters</TabsTrigger>
              <TabsTrigger value="tools" className="text-xs px-1">Tools</TabsTrigger>
              <TabsTrigger value="info" className="text-xs px-1">Info</TabsTrigger>
            </TabsList>

            {/* ─── FILTERS TAB ─── */}
            <TabsContent value="filters" className="space-y-4 mt-3">

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
                        setSearchOpen(true);
                    }}
                    onFocus={() => setSearchOpen(true)}
                    onBlur={() => setTimeout(() => setSearchOpen(false), 150)}
                    className="pl-8"
                />
            </div>
            
            {/* Search Results Dropdown — API-backed */}
            {searchOpen && searchQuery.length >= 2 && (
                <div className="border rounded-md shadow-sm bg-background max-h-64 overflow-y-auto z-50">
                    {searchFetching && (
                        <div className="flex items-center gap-2 px-3 py-3 text-xs text-muted-foreground">
                            <Loader2 className="h-3 w-3 animate-spin" /> Searching…
                        </div>
                    )}
                    {!searchFetching && (!searchResults || searchResults.length === 0) && debouncedSearchQuery.length >= 2 && (
                        <div className="px-3 py-4 text-sm text-center text-muted-foreground">
                            No nodes found.
                        </div>
                    )}
                    {(searchResults || []).map(node => {
                            const rawId = String(node.id || '');
                            const isElementId = /^\d+:[0-9a-f\-]{36}:\d+$/i.test(rawId);
                            const localId = rawId.includes(':') ? rawId.split(':').pop() : rawId;
                            const displayName = node.name
                                || node.properties?.label
                                || node.properties?.local_name
                                || (isElementId ? null : rawId)
                                || `${node.type || 'Node'} #${localId}`;
                            const displayId = isElementId ? null : rawId;
                            // Check if this node is already in the current graph view
                            const inGraph = normalizedGraph?.nodes?.some(n => String(n.id) === String(node.id));
                            return (
                            <div
                                key={node.id}
                                className={cn(
                                    "flex items-center px-3 py-2 text-sm cursor-pointer hover:bg-accent hover:text-accent-foreground",
                                    selectedNode?.id === String(node.id) && "bg-accent"
                                )}
                                onClick={async () => {
                                    const nodeId = String(node.id);
                                    // If the node is already in the graph, select & pan to it immediately
                                    const graphNode = normalizedGraph?.nodes?.find(n => n.id === nodeId);
                                    if (graphNode) {
                                        handleNodeClick(graphNode);
                                    }
                                    // Always expand to inject the node + its immediate neighbours
                                    try {
                                        const res = await expandNode(nodeId, 1);
                                        const data = res?.data ?? res;
                                        const expNodes = (data.nodes || []).map(nn => ({
                                            ...nn,
                                            id: String(nn.id),
                                            name: nn.name || nn.id,
                                            labels: Array.isArray(nn.labels) ? nn.labels : [nn.type].filter(Boolean),
                                            searchLabel: (nn.name || nn.id)?.toLowerCase() || '',
                                        }));
                                        const expLinks = data.links || [];
                                        setRagOverlayNodes(prev => {
                                            const existing = new Set(prev.map(n => n.id));
                                            const toAdd = expNodes.filter(n => !existing.has(n.id));
                                            return toAdd.length ? [...prev, ...toAdd] : prev;
                                        });
                                        setRagOverlayLinks(prev => {
                                            // Deduplicate by rel_id / link id to avoid double-edges
                                            // when adjacent nodes are expanded (A→B added again as B→A)
                                            const existingIds = new Set(
                                                prev.map(l => l.id || l.rel_id).filter(Boolean)
                                            );
                                            const toAdd = expLinks.filter(
                                                l => !(l.id || l.rel_id) || !existingIds.has(l.id || l.rel_id)
                                            );
                                            return toAdd.length ? [...prev, ...toAdd] : prev;
                                        });
                                        // If node wasn't in the original graph, select it directly
                                        // (avoids stale-closure issues with a setTimeout lookup)
                                        if (!graphNode) {
                                            const targetNode = expNodes.find(n => n.id === nodeId)
                                                ?? { id: nodeId, name: displayName, type: node.type };
                                            setSelectedNode(targetNode);
                                        }
                                    } catch {
                                        // Fallback: inject single node if expansion fails
                                        if (!graphNode) {
                                            const normalized = {
                                                ...node,
                                                id: nodeId,
                                                name: displayName,
                                                labels: Array.isArray(node.labels) ? node.labels : [node.type].filter(Boolean),
                                                searchLabel: displayName?.toLowerCase() || '',
                                                x: 0, y: 0,
                                            };
                                            setRagOverlayNodes(prev => {
                                                if (prev.some(n => n.id === nodeId)) return prev;
                                                return [...prev, normalized];
                                            });
                                            setTimeout(() => {
                                                const injected = normalizedGraph?.nodes?.find(n => n.id === nodeId);
                                                if (injected) handleNodeClick(injected);
                                                else setSelectedNode(normalized);
                                            }, 80);
                                        }
                                    }
                                    setSearchOpen(false);
                                    setSearchQuery("");
                                }}
                            >
                                <div className="flex flex-col overflow-hidden flex-1">
                                    <span className="font-medium truncate">{displayName}</span>
                                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                        <span className="bg-secondary px-1.5 py-0.5 rounded-sm text-[10px] uppercase tracking-wider">
                                            {node.type}
                                        </span>
                                        {displayId && <span className="truncate opacity-70">{displayId}</span>}
                                        {!inGraph && (
                                            <span className="text-[10px] text-amber-500 ml-auto shrink-0">not in view</span>
                                        )}
                                    </div>
                                </div>
                                {selectedNode?.id === String(node.id) && <Check className="ml-2 h-4 w-4 opacity-50 shrink-0" />}
                            </div>
                            );
                        })
                    }
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

          {/* Node-type filter - Inline checkbox list */}
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
            {selectedNodeTypes.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {selectedNodeTypes.map(type => (
                  <Badge key={type} variant="secondary" className="hover:bg-secondary/80 pr-1 gap-1">
                    <span
                      className="w-2 h-2 rounded-full inline-block"
                      style={{ backgroundColor: getNodeColor({ type }) }}
                    />
                    {type}
                    <X
                      className="h-3 w-3 cursor-pointer hover:text-destructive transition-colors ml-1"
                      onClick={(e) => { e.stopPropagation(); toggleNodeType(type); }}
                    />
                  </Badge>
                ))}
              </div>
            )}

            {/* Inline search + scrollable checkbox list */}
            <div className="space-y-1.5">
              <div className="relative">
                <Search className="absolute left-2 top-2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
                <Input
                  placeholder="Search types..."
                  value={nodeTypeSearch}
                  onChange={e => setNodeTypeSearch(e.target.value)}
                  className="h-8 pl-7 text-sm"
                />
              </div>
              <div className="border rounded-md max-h-52 overflow-y-auto divide-y divide-border/50">
                {dropdownTypes
                  .filter(nt => !nodeTypeSearch || nt.type.toLowerCase().includes(nodeTypeSearch.toLowerCase()))
                  .map(nt => {
                    const isSelected = selectedNodeTypes.includes(nt.type);
                    return (
                      <div
                        key={nt.type}
                        className={cn(
                          'flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-accent text-sm select-none',
                          isSelected && 'bg-accent/40'
                        )}
                        onClick={() => toggleNodeType(nt.type)}
                      >
                        <div className={cn(
                          'w-4 h-4 rounded border flex items-center justify-center shrink-0 transition-colors',
                          isSelected ? 'bg-primary border-primary' : 'border-input'
                        )}>
                          {isSelected && <Check className="h-3 w-3 text-primary-foreground" />}
                        </div>
                        <div
                          className="w-2.5 h-2.5 rounded-full shrink-0"
                          style={{ backgroundColor: getNodeColor({ type: nt.type }) }}
                        />
                        <span className={cn('flex-1 truncate', isSelected && 'font-medium')}>
                          {nt.type}
                        </span>
                        {nt.count != null && (
                          <span className="text-xs text-muted-foreground tabular-nums">{nt.count}</span>
                        )}
                      </div>
                    );
                  })}
                {dropdownTypes.filter(nt => !nodeTypeSearch || nt.type.toLowerCase().includes(nodeTypeSearch.toLowerCase())).length === 0 && (
                  <div className="px-3 py-4 text-xs text-center text-muted-foreground">No types found.</div>
                )}
              </div>
            </div>
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

          {/* E6: Advanced Property Filters */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Property Filters</Label>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-xs"
                onClick={() => setPropFilters(f => [...f, { key: '', op: 'contains', value: '' }])}
              >
                + Add
              </Button>
            </div>
            {propFilters.length === 0 && (
              <p className="text-[10px] text-muted-foreground">No property filters. Click "+ Add" to filter nodes by property values.</p>
            )}
            {propFilters.map((pf, idx) => (
              <div key={idx} className="flex items-center gap-1">
                <Input
                  placeholder="key"
                  value={pf.key}
                  className="h-7 text-xs flex-1"
                  onChange={e => {
                    const nf = [...propFilters];
                    nf[idx] = { ...nf[idx], key: e.target.value };
                    setPropFilters(nf);
                  }}
                />
                <select
                  value={pf.op}
                  className="h-7 text-xs border rounded px-1 bg-background"
                  onChange={e => {
                    const nf = [...propFilters];
                    nf[idx] = { ...nf[idx], op: e.target.value };
                    setPropFilters(nf);
                  }}
                >
                  <option value="contains">contains</option>
                  <option value="equals">equals</option>
                  <option value="starts">starts with</option>
                  <option value="notcontains">not contains</option>
                </select>
                <Input
                  placeholder="value"
                  value={pf.value}
                  className="h-7 text-xs flex-1"
                  onChange={e => {
                    const nf = [...propFilters];
                    nf[idx] = { ...nf[idx], value: e.target.value };
                    setPropFilters(nf);
                  }}
                />
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 shrink-0"
                  onClick={() => setPropFilters(f => f.filter((_, i) => i !== idx))}
                >
                  <X className="h-3 w-3" />
                </Button>
              </div>
            ))}
            {propFilters.length > 0 && (
              <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                <span>{displayGraph ? displayGraph.nodes.length : '—'} / {normalizedGraph ? normalizedGraph.nodes.length : '—'} nodes shown</span>
                <Button variant="ghost" size="sm" className="h-5 text-[10px]" onClick={() => setPropFilters([])}>Clear All</Button>
              </div>
            )}
          </div>

            </TabsContent>

            {/* ─── TOOLS TAB ─── */}
            <TabsContent value="tools" className="space-y-4 mt-3">

              {/* E2: Path Finder */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Route className="h-4 w-4" /> Path Finder
                  </CardTitle>
                  <CardDescription className="text-xs">Find shortest path between two nodes</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">

                  {/* Source node search */}
                  <div className="space-y-1">
                    <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">Source</p>
                    {pathSource ? (
                      <div className="flex items-center gap-2 px-2 py-1.5 border rounded-md bg-accent/30 text-sm">
                        <div className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
                        <span className="flex-1 truncate font-medium">{pathSourceName || pathSource}</span>
                        <Button
                          variant="ghost" size="icon" className="h-5 w-5 shrink-0"
                          onClick={() => { setPathSource(''); setPathSourceName(''); setPathSourceSearch(''); }}
                        >
                          <X className="h-3 w-3" />
                        </Button>
                      </div>
                    ) : (
                      <div className="relative">
                        <Search className="absolute left-2 top-2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
                        <Input
                          placeholder="Search source node by name..."
                          value={pathSourceSearch}
                          onChange={e => setPathSourceSearch(e.target.value)}
                          className="h-8 pl-7 text-xs"
                        />
                        {pathSourceSearch.trim().length >= 2 && (
                          <div className="absolute z-50 w-full top-full mt-0.5 border rounded-md shadow-md bg-background max-h-44 overflow-y-auto divide-y divide-border/50">
                            {(pathSourceResults?.results || []).length === 0 ? (
                              <div className="px-3 py-3 text-xs text-center text-muted-foreground">No nodes found</div>
                            ) : (pathSourceResults?.results || []).map(n => (
                              <div
                                key={n.id}
                                className="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-accent text-xs select-none"
                                onMouseDown={e => e.preventDefault()}
                                onClick={() => {
                                  setPathSource(String(n.id));
                                  setPathSourceName(n.name || String(n.id));
                                  setPathSourceSearch('');
                                }}
                              >
                                <span className="flex-1 font-medium truncate">{n.name || n.id}</span>
                                <Badge variant="outline" className="text-[9px] shrink-0">{n.type || n.labels?.[0]}</Badge>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Target node search */}
                  <div className="space-y-1">
                    <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">Target</p>
                    {pathTarget ? (
                      <div className="flex items-center gap-2 px-2 py-1.5 border rounded-md bg-accent/30 text-sm">
                        <div className="w-2 h-2 rounded-full bg-rose-500 shrink-0" />
                        <span className="flex-1 truncate font-medium">{pathTargetName || pathTarget}</span>
                        <Button
                          variant="ghost" size="icon" className="h-5 w-5 shrink-0"
                          onClick={() => { setPathTarget(''); setPathTargetName(''); setPathTargetSearch(''); }}
                        >
                          <X className="h-3 w-3" />
                        </Button>
                      </div>
                    ) : (
                      <div className="relative">
                        <Search className="absolute left-2 top-2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
                        <Input
                          placeholder="Search target node by name..."
                          value={pathTargetSearch}
                          onChange={e => setPathTargetSearch(e.target.value)}
                          className="h-8 pl-7 text-xs"
                        />
                        {pathTargetSearch.trim().length >= 2 && (
                          <div className="absolute z-50 w-full top-full mt-0.5 border rounded-md shadow-md bg-background max-h-44 overflow-y-auto divide-y divide-border/50">
                            {(pathTargetResults?.results || []).length === 0 ? (
                              <div className="px-3 py-3 text-xs text-center text-muted-foreground">No nodes found</div>
                            ) : (pathTargetResults?.results || []).map(n => (
                              <div
                                key={n.id}
                                className="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-accent text-xs select-none"
                                onMouseDown={e => e.preventDefault()}
                                onClick={() => {
                                  setPathTarget(String(n.id));
                                  setPathTargetName(n.name || String(n.id));
                                  setPathTargetSearch('');
                                }}
                              >
                                <span className="flex-1 font-medium truncate">{n.name || n.id}</span>
                                <Badge variant="outline" className="text-[9px] shrink-0">{n.type || n.labels?.[0]}</Badge>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      className="flex-1 h-7 text-xs"
                      disabled={pathLoading || !pathSource || !pathTarget}
                      onClick={handleFindPath}
                    >
                      {pathLoading ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Route className="h-3 w-3 mr-1" />}
                      Find Path
                    </Button>
                    {(pathSource || pathTarget || pathHighlight) && (
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 text-xs"
                        onClick={() => {
                          setPathHighlight(null);
                          setPathResult(null);
                          setPathSource('');
                          setPathSourceName('');
                          setPathTarget('');
                          setPathTargetName('');
                          setPathSourceSearch('');
                          setPathTargetSearch('');
                        }}
                      >
                        Clear
                      </Button>
                    )}
                  </div>
                  {pathResult && (
                    <div className={cn("text-xs p-2 rounded border", pathResult.found ? "bg-emerald-50 border-emerald-200 dark:bg-emerald-950/30" : "bg-red-50 border-red-200 dark:bg-red-950/30")}>
                      {pathResult.found
                        ? <><span className="font-medium">{pathSourceName || pathSource}</span> → <span className="font-medium">{pathTargetName || pathTarget}</span>: <span className="font-semibold">{pathResult.path_length}</span> hop{pathResult.path_length !== 1 ? 's' : ''}, <span className="font-semibold">{pathResult.nodes?.length}</span> nodes</>
                        : `No path found between "${pathSourceName || pathSource}" and "${pathTargetName || pathTarget}"`}
                    </div>
                  )}
                  {pathResult?.found && pathResult.nodes && (
                    <div className="space-y-1 max-h-40 overflow-y-auto border rounded p-1">
                      <p className="text-[10px] font-semibold text-muted-foreground uppercase px-1">Path nodes</p>
                      {pathResult.nodes.map((n, i) => (
                        <div key={n.id} className="flex items-center gap-1 text-xs px-1">
                          {i > 0 && <span className="text-muted-foreground shrink-0">→</span>}
                          <Badge variant="outline" className="text-[9px] px-1 py-0 shrink-0">{n.type}</Badge>
                          <span className="truncate font-medium">{n.name || n.id}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* E8: Heatmap / Visualization Mode */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Palette className="h-4 w-4" /> Visualization Mode
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <Select value={heatmapMode} onValueChange={setHeatmapMode}>
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="off">Default Colors</SelectItem>
                      <SelectItem value="degree">Degree Heatmap</SelectItem>
                      <SelectItem value="community">Community Clusters</SelectItem>
                    </SelectContent>
                  </Select>

                  {/* Label display mode */}
                  <div className="space-y-1">
                    <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">Node Labels</p>
                    <div className="flex gap-1">
                      {(['name', 'type', 'id']).map(mode => (
                        <button
                          key={mode}
                          onClick={() => setLabelMode(mode)}
                          className={cn(
                            'flex-1 h-7 rounded text-[10px] font-medium capitalize transition-colors border',
                            labelMode === mode
                              ? 'bg-primary text-primary-foreground border-primary'
                              : 'bg-muted text-muted-foreground border-transparent hover:bg-accent'
                          )}
                        >
                          {mode}
                        </button>
                      ))}
                    </div>
                  </div>
                  {heatmapMode === 'degree' && (
                    <p className="text-[10px] text-muted-foreground">Node size + color scaled by connection count. Blue→Yellow→Red.</p>
                  )}
                  {heatmapMode === 'community' && !communityMap && (
                    <Button size="sm" className="w-full h-7 text-xs" onClick={handleDetectCommunities}>
                      <Boxes className="h-3 w-3 mr-1" /> Detect Communities
                    </Button>
                  )}
                  {heatmapMode === 'community' && communityMap && (
                    <p className="text-[10px] text-muted-foreground">
                      {Object.keys(communityColors).length} communities detected.
                      Nodes colored by cluster membership.
                    </p>
                  )}
                </CardContent>
              </Card>

              {/* E11: Export */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Download className="h-4 w-4" /> Export
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="grid grid-cols-2 gap-2">
                    <Button size="sm" variant="outline" className="h-7 text-xs" onClick={handleExportPNG}>
                      PNG Image
                    </Button>
                    <Button size="sm" variant="outline" className="h-7 text-xs" onClick={handleExportCSV}>
                      Nodes CSV
                    </Button>
                    <Button size="sm" variant="outline" className="h-7 text-xs" onClick={handleExportLinksCSV}>
                      Links CSV
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* E7: Multi-select info */}
              {multiSelected.size > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <MousePointerClick className="h-4 w-4" /> Multi-Selected ({multiSelected.size})
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-1">
                    <div className="max-h-32 overflow-y-auto space-y-1">
                      {[...multiSelected].map(id => {
                        const node = normalizedGraph?.nodes?.find(n => String(n.id) === id);
                        return (
                          <div key={id} className="flex items-center justify-between text-xs">
                            <span className="truncate">{node?.name || id}</span>
                            <Badge variant="outline" className="text-[9px] shrink-0">{node?.type}</Badge>
                          </div>
                        );
                      })}
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="w-full h-6 text-xs"
                      onClick={() => setMultiSelected(new Set())}
                    >
                      Clear Selection
                    </Button>
                  </CardContent>
                </Card>
              )}

              {/* E20: Graph Diff */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Hash className="h-4 w-4" /> Graph Diff
                  </CardTitle>
                  <CardDescription className="text-xs">Compare two sets of node types</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  <Input
                    placeholder="Snapshot A types (e.g. Part,Requirement)"
                    value={diffTypesA}
                    onChange={e => setDiffTypesA(e.target.value)}
                    className="h-7 text-xs"
                  />
                  <Input
                    placeholder="Snapshot B types (e.g. Part,SimulationDossier)"
                    value={diffTypesB}
                    onChange={e => setDiffTypesB(e.target.value)}
                    className="h-7 text-xs"
                  />
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      className="flex-1 h-7 text-xs"
                      disabled={diffLoading || (!diffTypesA && !diffTypesB)}
                      onClick={handleGraphDiff}
                    >
                      {diffLoading ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Hash className="h-3 w-3 mr-1" />}
                      Compare
                    </Button>
                    {diffHighlight && (
                      <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => { setDiffHighlight(null); setDiffResult(null); }}>
                        Clear
                      </Button>
                    )}
                  </div>
                  {diffResult && !diffResult.error && diffResult.summary && (
                    <div className="text-xs space-y-1 p-2 rounded border bg-muted/50">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-green-500" />
                        <span>Added: <strong>{diffResult.summary.added_nodes_count}</strong> nodes, <strong>{diffResult.summary.added_links_count}</strong> links</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-red-500" />
                        <span>Removed: <strong>{diffResult.summary.removed_nodes_count}</strong> nodes, <strong>{diffResult.summary.removed_links_count}</strong> links</span>
                      </div>
                      <div className="text-muted-foreground text-[10px]">
                        A: {diffResult.summary.snapshot_a_nodes} nodes → B: {diffResult.summary.snapshot_b_nodes} nodes
                      </div>
                    </div>
                  )}
                  {diffResult?.error && (
                    <div className="text-xs text-red-500 p-2 rounded border border-red-200">{diffResult.error}</div>
                  )}
                </CardContent>
              </Card>

              {/* E16: Keyboard Shortcuts */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Keyboard className="h-4 w-4" /> Keyboard Shortcuts
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-1 text-xs">
                  {[
                    ['F', 'Fit to screen'],
                    ['+/-', 'Zoom in/out'],
                    ['Space', 'Pause/resume simulation'],
                    ['Esc', 'Clear selection'],
                    ['?', 'Toggle shortcuts panel'],
                    ['Right-click', 'Node context menu'],
                    ['Shift+Drag', 'Lasso rectangle select'],
                  ].map(([key, desc]) => (
                    <div key={key} className="flex items-center justify-between">
                      <kbd className="px-1.5 py-0.5 bg-muted rounded text-[10px] font-mono">{key}</kbd>
                      <span className="text-muted-foreground">{desc}</span>
                    </div>
                  ))}
                </CardContent>
              </Card>

              {/* E17: Cypher Editor */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <TerminalIcon className="h-4 w-4" /> Cypher Query
                  </CardTitle>
                  <CardDescription className="text-xs">Execute raw Cypher queries against the graph</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  <Textarea
                    placeholder="MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 20"
                    value={cypherQuery}
                    onChange={e => setCypherQuery(e.target.value)}
                    className="min-h-16 text-xs font-mono resize-none"
                  />
                  <Button size="sm" className="w-full h-7 text-xs" disabled={cypherLoading || !cypherQuery.trim()}
                    onClick={async () => {
                      setCypherLoading(true); setCypherResult(null);
                      try {
                        const res = await searchNodes({ q: cypherQuery, limit: 50 });
                        setCypherResult({ results: res.results || res, error: null });
                      } catch (err) { setCypherResult({ results: [], error: err.message }); }
                      finally { setCypherLoading(false); }
                    }}>
                    {cypherLoading ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <TerminalIcon className="h-3 w-3 mr-1" />} Execute
                  </Button>
                  {cypherResult?.error && <p className="text-xs text-destructive">{cypherResult.error}</p>}
                  {cypherResult?.results?.length > 0 && (
                    <div className="max-h-40 overflow-y-auto space-y-1 border rounded p-2">
                      {cypherResult.results.slice(0, 20).map((r, i) => (
                        <div key={i} className="text-xs flex items-center gap-1">
                          <Badge variant="outline" className="text-[9px]">{r.type}</Badge>
                          <span className="truncate">{r.name || r.id}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* E13: TRS Change Log */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <ExternalLink className="h-4 w-4" /> TRS Change Log
                  </CardTitle>
                  <CardDescription className="text-xs">OSLC Tracked Resource Set — recent changes</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  <Button size="sm" className="w-full h-7 text-xs" disabled={trsLoading} onClick={handleFetchTRS}>
                    {trsLoading ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <ExternalLink className="h-3 w-3 mr-1" />} Fetch Changelog
                  </Button>
                  {trsEvents.length > 0 && (
                    <div className="max-h-48 overflow-y-auto space-y-1 border rounded p-2">
                      {trsEvents.map((evt, i) => {
                        const typeLabel = String(evt.type).includes('Creation') ? 'Created' : String(evt.type).includes('Modification') ? 'Modified' : String(evt.type).includes('Deletion') ? 'Deleted' : evt.type;
                        const typeColor = typeLabel === 'Created' ? 'text-green-600' : typeLabel === 'Deleted' ? 'text-red-500' : typeLabel === 'Modified' ? 'text-blue-500' : 'text-muted-foreground';
                        return (
                          <div key={i} className="flex items-center gap-2 text-xs">
                            <span className={cn("font-medium shrink-0 w-14", typeColor)}>{typeLabel}</span>
                            <span className="truncate text-muted-foreground">{evt.resource}</span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>

            </TabsContent>

            {/* RAG tab removed — AI assistant lives on the floating Brain panel on the canvas */}
            {false && <TabsContent value="rag-removed">

              {/* ── Chat panel ────────────────────────────────────────── */}
              <div className="flex flex-col flex-1 rounded-xl border border-border bg-background overflow-hidden shadow-sm">

                {/* Header */}
                <div className="flex items-center gap-2 px-3 py-2 border-b border-border bg-muted/40 shrink-0">
                  <Brain className="h-4 w-4 text-violet-500" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold leading-none">KnowledgeGraph AI</p>
                    <p className="text-[10px] text-muted-foreground mt-0.5 truncate">Digital engineering &amp; product ontology assistant</p>
                  </div>
                  <Badge variant="outline" className="text-[9px] shrink-0">Beta</Badge>
                  {ragMessages.length > 0 && (
                    <button
                      className="text-muted-foreground hover:text-destructive transition-colors"
                      title="Clear conversation"
                      onClick={() => { setRagMessages([]); setRagHighlight(null); setRagOverlayNodes([]); setRagOverlayLinks([]); }}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>

                {/* Message area */}
                <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">

                  {/* Welcome state */}
                  {ragMessages.length === 0 && !ragLoading && (
                    <div className="flex flex-col items-center justify-center h-full gap-3 text-center pb-4">
                      <div className="w-10 h-10 rounded-full bg-violet-100 dark:bg-violet-950 flex items-center justify-center">
                        <Brain className="h-5 w-5 text-violet-500" />
                      </div>
                      <div>
                        <p className="text-xs font-semibold">Digital Engineering Assistant</p>
                        <p className="text-[10px] text-muted-foreground mt-1 leading-relaxed max-w-[200px]">
                          Ask about ISO 10303 AP239/AP242/AP243 traceability, product ontology, simulation dossiers, or requirements.
                        </p>
                      </div>
                      {/* Suggested chips */}
                      <div className="flex flex-wrap gap-1 justify-center max-w-[240px]">
                        {({
                          ONTOLOGY: ['Ontology structure overview', 'How are OWL classes connected?', 'AP239 vs AP242 vs AP243'],
                          AP239: ['Traceability overview', 'How are Requirements linked?', 'Part → WorkOrder path'],
                          AP242: ['How are assemblies structured?', 'Part → Assembly connections', 'Material relationships'],
                          AP243: ['How are simulation dossiers linked?', 'Dossier → Evidence traceability', 'Study → Context relationships'],
                          ENTERPRISE: ['Cross-domain traceability', 'Show all node types', 'Network overview'],
                        }[currentViewId] || ['How are nodes connected?', 'Traceability overview', 'List simulation dossiers']
                        ).map(q => (
                          <button
                            key={q}
                            className="text-[9px] px-2 py-1 rounded-full border border-violet-200 dark:border-violet-800 bg-violet-50 dark:bg-violet-950/50 text-violet-700 dark:text-violet-300 hover:bg-violet-100 dark:hover:bg-violet-900 transition-colors"
                            onClick={() => { setRagQuestion(q); }}
                          >{q}</button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Message bubbles */}
                  {ragMessages.map(msg => (
                    <div key={msg.id} className={`flex gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                      {/* Avatar */}
                      <div className={`w-5 h-5 rounded-full shrink-0 flex items-center justify-center text-[9px] font-bold mt-0.5 ${
                        msg.role === 'user'
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-violet-100 dark:bg-violet-950'
                      }`}>
                        {msg.role === 'user' ? 'U' : <Brain className="h-3 w-3 text-violet-500" />}
                      </div>
                      {/* Bubble */}
                      <div className={`flex flex-col gap-1 max-w-[85%] ${
                        msg.role === 'user' ? 'items-end' : 'items-start'
                      }`}>
                        <div className={`rounded-xl px-3 py-2 text-xs leading-relaxed ${
                          msg.role === 'user'
                            ? 'bg-primary text-primary-foreground rounded-tr-sm'
                            : 'bg-muted text-foreground rounded-tl-sm'
                        }`}>
                          {msg.role === 'user'
                            ? msg.content
                            : msg.streaming && !msg.content
                              ? <span className="inline-block w-2 h-3 bg-violet-400 animate-pulse rounded-sm" />
                              : <><SimpleMarkdown text={msg.content} />{msg.streaming && <span className="inline-block w-1.5 h-3 bg-violet-400 animate-pulse rounded-sm ml-0.5 align-middle" />}</>}
                        </div>
                        {/* Sources inline under assistant bubble */}
                        {msg.role === 'assistant' && msg.sources?.length > 0 && (
                          <div className="w-full space-y-0.5 px-1">
                            <p className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wide">Sources</p>
                            {msg.sources.slice(0, 5).map((s, i) => {
                              const isInGraph = ragHighlight?.has(String(s.uid));
                              const focusNode = () => {
                                if (!normalizedGraph || !fgRef.current) return;
                                const node = normalizedGraph.nodes.find(
                                  n => String(n.id) === String(s.uid) || String(n.properties?.uid) === String(s.uid)
                                );
                                if (node && node.x != null) {
                                  fgRef.current.centerAt(node.x, node.y, 600);
                                  fgRef.current.zoom(6, 600);
                                  setSelectedNode(node); // open node detail panel
                                }
                              };
                              return (
                                <div
                                  key={i}
                                  className={`flex items-center gap-1 text-[10px] rounded px-1 py-0.5 cursor-pointer hover:bg-muted/80 transition-colors ${
                                    isInGraph ? 'text-violet-600 dark:text-violet-400' : 'text-muted-foreground'
                                  }`}
                                  onClick={focusNode}
                                  title={isInGraph ? 'Click to focus in graph' : 'Node not in current view'}
                                >
                                  <Hash className="h-2.5 w-2.5 shrink-0" />
                                  <span className="truncate">{s.name || s.uid}</span>
                                  {s.score && <span className="ml-auto shrink-0 opacity-60">{(s.score * 100).toFixed(0)}%</span>}
                                  {isInGraph && <span className="text-violet-500 shrink-0">●</span>}
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}

                  {/* Thinking indicator */}
                  {ragLoading && (
                    <div className="flex gap-2 flex-row">
                      <div className="w-5 h-5 rounded-full shrink-0 bg-violet-100 dark:bg-violet-950 flex items-center justify-center mt-0.5">
                        <Brain className="h-3 w-3 text-violet-500" />
                      </div>
                      <div className="bg-muted rounded-xl rounded-tl-sm px-3 py-2 flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/60 animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/60 animate-bounce" style={{ animationDelay: '150ms' }} />
                        <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/60 animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                    </div>
                  )}

                  {/* Auto-scroll anchor */}
                  <div ref={chatEndRef} />
                </div>

                {/* Suggested chips — shown above input when chat is active */}
                {ragMessages.length > 0 && (
                  <div className="px-3 pb-1 shrink-0">
                    <div className="flex gap-1 overflow-x-auto pb-1 scrollbar-none">
                      {({
                        ONTOLOGY: ['OWL class hierarchy', 'AP239 vs AP242', 'Property relationships'],
                        AP239: ['Requirements traceability', 'Part → WorkOrder', 'Verification links'],
                        AP242: ['Assembly structure', 'Part connections', 'Shape links'],
                        AP243: ['Dossier links', 'Evidence traceability', 'SimulationRun path'],
                        ENTERPRISE: ['Cross-domain', 'All node types', 'Network overview'],
                      }[currentViewId] || ['Traceability', 'Node types', 'Connections']
                      ).map(q => (
                        <button
                          key={q}
                          className="text-[9px] px-2 py-0.5 rounded-full border border-border bg-muted/50 hover:bg-muted whitespace-nowrap text-muted-foreground hover:text-foreground transition-colors shrink-0"
                          onClick={() => setRagQuestion(q)}
                        >{q}</button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Input bar */}
                <div className="px-3 pb-3 pt-1 border-t border-border shrink-0">
                  <div className="flex gap-2 items-end">
                    <Textarea
                      placeholder="Ask about traceability, ontology, simulations…"
                      value={ragQuestion}
                      onChange={e => setRagQuestion(e.target.value)}
                      className="flex-1 min-h-9 max-h-24 text-xs resize-none rounded-xl"
                      onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleRAGQuery(); } }}
                      rows={1}
                    />
                    <Button
                      size="icon"
                      className="h-9 w-9 rounded-xl shrink-0"
                      disabled={ragLoading || !ragQuestion.trim()}
                      onClick={handleRAGQuery}
                    >
                      {ragLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                    </Button>
                  </div>
                  <p className="text-[9px] text-muted-foreground mt-1">Enter to send · Shift+Enter for newline · View: {currentViewId}</p>
                </div>
              </div>

              {/* E17: Cypher Editor */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <TerminalIcon className="h-4 w-4" /> Cypher Query
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Execute raw Cypher queries against the graph
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  <Textarea
                    placeholder="MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 20"
                    value={cypherQuery}
                    onChange={e => setCypherQuery(e.target.value)}
                    className="min-h-16 text-xs font-mono resize-none"
                  />
                  <Button
                    size="sm"
                    className="w-full h-7 text-xs"
                    disabled={cypherLoading || !cypherQuery.trim()}
                    onClick={async () => {
                      setCypherLoading(true);
                      setCypherResult(null);
                      try {
                        // Use the named query endpoint with a custom query
                        // For safety, we pass through the existing search endpoint
                        const res = await searchNodes({ q: cypherQuery, limit: 50 });
                        setCypherResult({ results: res.results || res, error: null });
                      } catch (err) {
                        setCypherResult({ results: [], error: err.message });
                      } finally {
                        setCypherLoading(false);
                      }
                    }}
                  >
                    {cypherLoading ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <TerminalIcon className="h-3 w-3 mr-1" />}
                    Execute
                  </Button>
                  {cypherResult?.error && (
                    <p className="text-xs text-destructive">{cypherResult.error}</p>
                  )}
                  {cypherResult?.results?.length > 0 && (
                    <div className="max-h-40 overflow-y-auto space-y-1 border rounded p-2">
                      {cypherResult.results.slice(0, 20).map((r, i) => (
                        <div key={i} className="text-xs flex items-center gap-1">
                          <Badge variant="outline" className="text-[9px]">{r.type}</Badge>
                          <span className="truncate">{r.name || r.id}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* E13: TRS Time-Travel / Change Log */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <ExternalLink className="h-4 w-4" /> TRS Change Log
                  </CardTitle>
                  <CardDescription className="text-xs">
                    OSLC Tracked Resource Set — recent resource changes
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  <Button
                    size="sm"
                    className="w-full h-7 text-xs"
                    disabled={trsLoading}
                    onClick={handleFetchTRS}
                  >
                    {trsLoading ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <ExternalLink className="h-3 w-3 mr-1" />}
                    Fetch Changelog
                  </Button>
                  {trsEvents.length > 0 && (
                    <div className="max-h-48 overflow-y-auto space-y-1 border rounded p-2">
                      {trsEvents.map((evt, i) => {
                        const typeLabel = String(evt.type).includes('Creation') ? 'Created'
                          : String(evt.type).includes('Modification') ? 'Modified'
                          : String(evt.type).includes('Deletion') ? 'Deleted'
                          : evt.type;
                        const typeColor = typeLabel === 'Created' ? 'text-green-600'
                          : typeLabel === 'Deleted' ? 'text-red-500'
                          : typeLabel === 'Modified' ? 'text-blue-500'
                          : 'text-muted-foreground';
                        return (
                          <div key={i} className="flex items-center gap-2 text-xs">
                            <span className={cn("font-medium shrink-0 w-14", typeColor)}>{typeLabel}</span>
                            <span className="truncate text-muted-foreground">{evt.resource}</span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>

            </TabsContent>}

            {/* ─── INFO TAB ─── */}
            <TabsContent value="info" className="space-y-4 mt-3">

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

              {/* Relationship Legends */}
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
                    {isFetchingMore && (
                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground pt-0.5">
                        <Loader2 className="h-3 w-3 animate-spin shrink-0" />
                        <span>Loading more nodes…</span>
                      </div>
                    )}
                    {heatmapMode === 'degree' && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Max Degree:</span>
                        <span className="font-mono font-semibold">{maxDegree}</span>
                      </div>
                    )}
                    {communityMap && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Communities:</span>
                        <span className="font-mono font-semibold">{Object.keys(communityColors).length}</span>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* E15: Unified Ontology Cross-Walk */}
              {selectedNode && ONTOLOGY_CROSSWALK[selectedNode.type] && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Boxes className="h-4 w-4" /> Cross-Walk: {selectedNode.type}
                    </CardTitle>
                    <CardDescription className="text-[10px]">
                      ISO 10303 &amp; OSLC concept mappings
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-1.5 text-xs">
                    {Object.entries(ONTOLOGY_CROSSWALK[selectedNode.type]).map(([std, concept]) => (
                      <div key={std} className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: AP_COLORS[std] || '#6b7280' }} />
                        <span className="font-mono text-muted-foreground w-10 shrink-0 uppercase text-[9px]">{std}</span>
                        {concept
                          ? <span className="font-medium">{concept}</span>
                          : <span className="text-muted-foreground italic">—</span>
                        }
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}

              {/* Ontology Cross-Walk Reference (no selection needed) */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Boxes className="h-4 w-4" /> Unified Cross-Walk Map
                  </CardTitle>
                  <CardDescription className="text-[10px]">
                    AP239 / AP242 / AP243 / OSLC concept alignments
                  </CardDescription>
                </CardHeader>
                <CardContent className="text-[10px] overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-1 pr-2 font-medium">Type</th>
                        <th className="text-left py-1 px-1 font-medium" style={{color: AP_COLORS.ap242}}>242</th>
                        <th className="text-left py-1 px-1 font-medium" style={{color: AP_COLORS.ap239}}>239</th>
                        <th className="text-left py-1 px-1 font-medium" style={{color: AP_COLORS.ap243}}>243</th>
                        <th className="text-left py-1 px-1 font-medium" style={{color: AP_COLORS.oslc}}>OSLC</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(ONTOLOGY_CROSSWALK).map(([type, mappings]) => (
                        <tr key={type} className={cn("border-b border-muted last:border-0", selectedNode?.type === type && "bg-accent")}>
                          <td className="py-1 pr-2 font-medium">{type}</td>
                          <td className="py-1 px-1 text-muted-foreground">{mappings.ap242 || '—'}</td>
                          <td className="py-1 px-1 text-muted-foreground">{mappings.ap239 || '—'}</td>
                          <td className="py-1 px-1 text-muted-foreground">{mappings.ap243 || '—'}</td>
                          <td className="py-1 px-1 text-muted-foreground">{mappings.oslc || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CardContent>
              </Card>

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

            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* ── Main canvas area ── */}
      <div
        className="flex-1 h-full relative overflow-hidden"
        ref={containerRef}
        onPointerMove={handlePointerMove}
        onMouseDown={handleCanvasMouseDown}
        onMouseMove={handleCanvasMouseMove}
        onMouseUp={handleCanvasMouseUp}
      >
        {/* Sidebar collapse toggle — sits on the left edge of the canvas */}
        <button
          onClick={() => setSidebarCollapsed(v => !v)}
          className="absolute left-0 top-1/2 -translate-y-1/2 z-20 flex items-center justify-center w-4 h-12 rounded-r-lg bg-background border border-l-0 border-border shadow-sm hover:bg-muted transition-colors group"
          title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <svg viewBox="0 0 6 10" className={`w-2.5 h-2.5 text-muted-foreground group-hover:text-foreground transition-transform duration-300 ${sidebarCollapsed ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="5,1 1,5 5,9" />
          </svg>
        </button>
        {/* Loading overlay — full block on first load, translucent badge on refetch */}
        {(isLoading || isGraphRefetching) && (
          <div className={`absolute inset-0 flex items-center justify-center z-20 ${
            isLoading ? 'bg-background/80 backdrop-blur-sm' : 'bg-transparent pointer-events-none'
          }`}>
            <div className={`text-center space-y-4 ${
              isGraphRefetching && !isLoading
                ? 'bg-background/90 backdrop-blur-sm rounded-xl px-5 py-4 shadow-lg border border-border'
                : ''
            }`}>
              <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
              <p className="text-sm text-muted-foreground">
                {isLoading ? 'Loading graph data...' : 'Refreshing view…'}
              </p>
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
        {normalizedGraph && !isLoading && !isGraphRefetching && !error && normalizedGraph.nodes.length === 0 && (
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

        {/* RAG active status badge — shown on graph canvas when RAG highlight is set */}
        {ragHighlight && ragHighlight.size > 0 && (
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10 flex items-center gap-2 px-3 py-1.5 rounded-full bg-background/90 backdrop-blur-sm border border-violet-300 dark:border-violet-700 shadow-lg">
            <span className="w-2 h-2 rounded-full bg-violet-500 animate-pulse shrink-0" />
            <span className="text-[11px] font-medium text-violet-700 dark:text-violet-300 whitespace-nowrap">
              {ragHighlight.size} node{ragHighlight.size !== 1 ? 's' : ''} matched
            </span>
            <button
              className="ml-1 text-muted-foreground hover:text-destructive transition-colors"
              title="Clear graph highlight"
              onClick={() => { setRagHighlight(null); setRagOverlayNodes([]); setRagOverlayLinks([]); }}
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        )}

        {/* Force-directed graph */}
        {displayGraph && !isLoading && !error && displayGraph.nodes.length > 0 && (
          <ForceGraph2D
            width={dimensions.width}
            height={dimensions.height}
            ref={fgRef}
            graphData={{
              nodes: displayGraph.nodes,
              links: displayGraph.links,
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
              const isPathNode = highlighted.isPath && highlighted.nodeIds?.has(id);
              const isMultiSelected = multiSelected.has(id);
              const dim = highlighted.nodeIds ? !isNeighbor : false;

              // E8: Heatmap mode coloring
              let baseColor;
              if (heatmapMode === 'community' && communityMap && communityMap[id] != null) {
                baseColor = communityColors[communityMap[id]] || '#6b7280';
              } else if (heatmapMode === 'degree') {
                const deg = degreeMap[id] || 0;
                const ratio = deg / maxDegree;
                // Heat: blue(0) → yellow(0.5) → red(1)
                const r = Math.round(255 * Math.min(1, ratio * 2));
                const g = Math.round(255 * Math.max(0, 1 - Math.abs(ratio - 0.5) * 2));
                const b = Math.round(255 * Math.max(0, 1 - ratio * 2));
                baseColor = `rgb(${r},${g},${b})`;
              } else {
                baseColor = getNodeColor(node);
              }

              // E5: Node size by degree
              const deg = degreeMap[id] || 0;
              const sizeScale = heatmapMode === 'degree'
                ? 5 + (deg / maxDegree) * 8
                : (isFocused ? 8 : 6);
              const radius = sizeScale;

              // In ONTOLOGY view render OWLObjectProperty as a diamond and
              // OWLDatatypeProperty as a small square; all other nodes get circles.
              if (currentViewId === 'ONTOLOGY' && (node.type === 'OWLObjectProperty' || node.type === 'OWLDatatypeProperty')) {
                const s = node.type === 'OWLObjectProperty' ? 5 : 4;
                ctx.save();
                ctx.globalAlpha = dim ? (highlighted.isRag ? 0.45 : 0.18) : 1;
                ctx.fillStyle = baseColor;
                ctx.translate(node.x, node.y);
                if (node.type === 'OWLObjectProperty') ctx.rotate(Math.PI / 4); // 45° → diamond
                ctx.beginPath();
                ctx.rect(-s, -s, s * 2, s * 2);
                ctx.fill();
                ctx.restore();
              } else {
                ctx.globalAlpha = dim ? (highlighted.isRag ? 0.45 : 0.18) : 1;
                ctx.fillStyle = baseColor;
                ctx.beginPath();
                ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
                ctx.fill();
              }

              // E2: Path node glow ring (cyan)
              if (isPathNode) {
                ctx.globalAlpha = 0.8;
                ctx.lineWidth = 3;
                ctx.strokeStyle = '#06b6d4';
                ctx.beginPath();
                ctx.arc(node.x, node.y, radius + 4, 0, 2 * Math.PI, false);
                ctx.stroke();
              }

              // E3: RAG result node glow ring (violet/purple)
              const isRagNode = highlighted.isRag && highlighted.nodeIds?.has(id);
              if (isRagNode) {
                ctx.globalAlpha = 0.92;
                ctx.lineWidth = 3;
                ctx.strokeStyle = '#a855f7';
                ctx.shadowColor = '#a855f7';
                ctx.shadowBlur = 10;
                ctx.beginPath();
                ctx.arc(node.x, node.y, radius + 5, 0, 2 * Math.PI, false);
                ctx.stroke();
                ctx.shadowBlur = 0;
                ctx.shadowColor = 'transparent';
              }

              // E7: Multi-select ring (amber dashed)
              if (isMultiSelected) {
                ctx.globalAlpha = 0.9;
                ctx.lineWidth = 2;
                ctx.strokeStyle = '#f59e0b';
                ctx.setLineDash([3, 3]);
                ctx.beginPath();
                ctx.arc(node.x, node.y, radius + 3, 0, 2 * Math.PI, false);
                ctx.stroke();
                ctx.setLineDash([]);
              }

              // E20: Diff highlighting (green=added, red=removed)
              if (diffHighlight) {
                if (diffHighlight.added.has(id)) {
                  ctx.globalAlpha = 0.85;
                  ctx.lineWidth = 3;
                  ctx.strokeStyle = '#22c55e'; // green
                  ctx.beginPath();
                  ctx.arc(node.x, node.y, radius + 5, 0, 2 * Math.PI, false);
                  ctx.stroke();
                } else if (diffHighlight.removed.has(id)) {
                  ctx.globalAlpha = 0.85;
                  ctx.lineWidth = 3;
                  ctx.strokeStyle = '#ef4444'; // red
                  ctx.setLineDash([4, 4]);
                  ctx.beginPath();
                  ctx.arc(node.x, node.y, radius + 5, 0, 2 * Math.PI, false);
                  ctx.stroke();
                  ctx.setLineDash([]);
                }
              }

              if (isFocused || (hoverNode && String(hoverNode.id) === id)) {
                ctx.globalAlpha = 1;
                ctx.lineWidth = 2;
                ctx.strokeStyle = '#0f172a';
                ctx.beginPath();
                ctx.arc(node.x, node.y, radius + 2, 0, 2 * Math.PI, false);
                ctx.stroke();
              }

              // E14: Community badge — small number in top-right
              if (heatmapMode === 'community' && communityMap && communityMap[id] != null && globalScale >= 1.5) {
                const commId = communityMap[id];
                const badgeFontSize = 7 / globalScale;
                ctx.font = `bold ${badgeFontSize}px sans-serif`;
                ctx.globalAlpha = 0.85;
                ctx.fillStyle = '#fff';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.beginPath();
                ctx.arc(node.x + radius, node.y - radius, 4 / globalScale, 0, 2 * Math.PI);
                ctx.fillStyle = communityColors[commId] || '#333';
                ctx.fill();
                ctx.fillStyle = '#fff';
                ctx.fillText(String(commId), node.x + radius, node.y - radius);
              }

              // ── Label rendering ──────────────────────────────────────────
              // Show labels: always for highlighted/focused nodes;
              // for others only at a zoom threshold to avoid clutter
              const isHighlightedNode = highlighted.nodeIds ? highlighted.nodeIds.has(id) : false;
              const labelZoomThreshold = currentViewId === 'ONTOLOGY' ? 0.8 : 1.6;
              const showLabel = !dim && (isHighlightedNode || globalScale >= labelZoomThreshold);
              if (showLabel) {
                // Prefer human-readable name; fall back to properties.label then local part of id.
                const rawId = String(node.id || '');
                const isElementId = /^\d+:[0-9a-f\-]{36}:\d+$/i.test(rawId);
                const localId = rawId.includes(':') ? rawId.split(':').pop() : rawId;
                // Build label text based on user-selected label mode
                let fullLabel;
                if (labelMode === 'type') {
                  fullLabel = node.type || 'Unknown';
                } else if (labelMode === 'id') {
                  fullLabel = isElementId ? `${node.type}#${localId}` : localId;
                } else {
                  fullLabel = node.name
                    || node.properties?.label
                    || node.properties?.local_name
                    || (isElementId ? null : localId)
                    || node.type;
                }

                // Truncate: allow slightly more chars for readability
                const MAX_CHARS = 18;
                const label = fullLabel && fullLabel.length > MAX_CHARS
                  ? fullLabel.slice(0, MAX_CHARS - 1) + '…'
                  : (fullLabel || '');

                // Uniform font: same size, weight, and family across all views and states
                const screenPx = 11;
                const fontSize = Math.max(7, screenPx) / globalScale;
                ctx.font = `700 ${fontSize}px 'Inter', 'Segoe UI', system-ui, -apple-system, Arial, sans-serif`;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'top';

                const boxY = node.y + radius + 3 / globalScale;
                const textWidth = ctx.measureText(label).width;
                const padX = 4 / globalScale;
                const padY = 2 / globalScale;

                // Uniform dark pill background (same in every focus area / view)
                ctx.globalAlpha = isHighlightedNode ? 0.97 : 0.85;
                ctx.fillStyle = 'rgba(15, 23, 42, 0.88)'; // slate-900 at 88% — consistent across all views
                const pillW = textWidth + padX * 2;
                const pillH = fontSize + padY * 2;
                const pillX = node.x - pillW / 2;
                const pillR = Math.max(0, Math.min(pillH / 2, 3 / globalScale));
                ctx.beginPath();
                ctx.moveTo(pillX + pillR, boxY - padY);
                ctx.lineTo(pillX + pillW - pillR, boxY - padY);
                ctx.arcTo(pillX + pillW, boxY - padY, pillX + pillW, boxY - padY + pillR, pillR);
                ctx.lineTo(pillX + pillW, boxY - padY + pillH - pillR);
                ctx.arcTo(pillX + pillW, boxY - padY + pillH, pillX + pillW - pillR, boxY - padY + pillH, pillR);
                ctx.lineTo(pillX + pillR, boxY - padY + pillH);
                ctx.arcTo(pillX, boxY - padY + pillH, pillX, boxY - padY + pillH - pillR, pillR);
                ctx.lineTo(pillX, boxY - padY + pillR);
                ctx.arcTo(pillX, boxY - padY, pillX + pillR, boxY - padY, pillR);
                ctx.closePath();
                ctx.fill();

                // Uniform white label text — maximum contrast on dark pill
                ctx.globalAlpha = 1;
                ctx.fillStyle = '#ffffff';
                ctx.fillText(label, node.x, boxY);
              }

              ctx.globalAlpha = 1;
            }}
            onNodeClick={handleNodeClick}
            onNodeDoubleClick={node => {
              // Double-click any node → clear selection and return to normal state
              setSelectedNode(null);
              setHoverNode(null);
              setMultiSelected(new Set());
              setPathHighlight(null);
            }}
            onNodeHover={handleNodeHover}
            onNodeRightClick={handleNodeRightClick}
            onLinkHover={handleLinkHover}
            onBackgroundClick={() => {
              setSelectedNode(null);
              setHoverNode(null);
              setContextMenu(null);
              setMultiSelected(new Set());
              setPathHighlight(null);
            }}
            linkDirectionalParticles={l => {
              const id = String(l.id ?? '');
              // E2: path links always show particles
              if (pathHighlight?.linkKeys?.has(id)) return 4;
              return highlighted.linkKeys && highlighted.linkKeys.has(id) ? 3 : 0;
            }}
            linkDirectionalParticleWidth={l => {
              const id = String(l.id ?? '');
              return pathHighlight?.linkKeys?.has(id) ? 3 : 2;
            }}
            linkDirectionalParticleColor={l => {
              const id = String(l.id ?? '');
              return pathHighlight?.linkKeys?.has(id) ? '#06b6d4' : undefined;
            }}
            // E4: Edge labels rendered on canvas
            linkCanvasObjectMode={() => 'after'}
            linkCanvasObject={(link, ctx, globalScale) => {
              const linkId = String(link.id ?? '');
              const isHighlightedLink = highlighted.linkKeys ? highlighted.linkKeys.has(linkId) : false;
              const isPathLink = pathHighlight?.linkKeys?.has(linkId);
              // Show for: path links, highlighted links, and all edges at zoom >= 2.5
              if (!isPathLink && !isHighlightedLink && globalScale < 2.5) return;
              const relType = link.type || '';
              if (!relType) return;
              const s = typeof link.source === 'object' ? link.source : null;
              const t = typeof link.target === 'object' ? link.target : null;
              if (!s || !t) return;
              const midX = (s.x + t.x) / 2;
              const midY = (s.y + t.y) / 2;
              const fontSize = Math.max(8, 10) / globalScale;
              ctx.font = `${isHighlightedLink ? '600' : '400'} ${fontSize}px sans-serif`;
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              const label = relType.length > 20 ? relType.slice(0, 18) + '…' : relType;

              // Resolve relationship type color from view-specific or universal map
              const relColor = (currentViewId === 'DIGITAL_THREAD' && DT_REL_COLORS[relType])
                ? DT_REL_COLORS[relType]
                : (currentViewId === 'ONTOLOGY' && ONTOLOGY_REL_COLORS[relType])
                  ? ONTOLOGY_REL_COLORS[relType]
                  : (currentViewId === 'OSLC' && OSLC_REL_COLORS[relType])
                    ? OSLC_REL_COLORS[relType]
                    : (ALL_REL_COLORS[relType] || '#64748b');

              // Background pill colored by relationship type
              const lTextW = ctx.measureText(label).width;
              const lPadX = 3 / globalScale;
              const lPadY = 1.5 / globalScale;
              const lPillW = lTextW + lPadX * 2;
              const lPillH = fontSize + lPadY * 2;
              const lPillX = midX - lPillW / 2;
              const lPillY = midY - lPillH / 2;
              const lR = Math.max(0, Math.min(lPillH / 2, 2 / globalScale));

              // Parse relColor hex → rgba
              const hx = relColor.startsWith('#') ? relColor.replace('#', '') : '64748b';
              const lr = parseInt(hx.substring(0, 2), 16) || 100;
              const lg = parseInt(hx.substring(2, 4), 16) || 116;
              const lb = parseInt(hx.substring(4, 6), 16) || 139;

              ctx.globalAlpha = isHighlightedLink ? 0.90 : 0.72;
              ctx.fillStyle = `rgba(${lr},${lg},${lb},${isHighlightedLink ? 0.88 : 0.65})`;
              ctx.beginPath();
              ctx.moveTo(lPillX + lR, lPillY);
              ctx.lineTo(lPillX + lPillW - lR, lPillY);
              ctx.arcTo(lPillX + lPillW, lPillY, lPillX + lPillW, lPillY + lR, lR);
              ctx.lineTo(lPillX + lPillW, lPillY + lPillH - lR);
              ctx.arcTo(lPillX + lPillW, lPillY + lPillH, lPillX + lPillW - lR, lPillY + lPillH, lR);
              ctx.lineTo(lPillX + lR, lPillY + lPillH);
              ctx.arcTo(lPillX, lPillY + lPillH, lPillX, lPillY + lPillH - lR, lR);
              ctx.lineTo(lPillX, lPillY + lR);
              ctx.arcTo(lPillX, lPillY, lPillX + lR, lPillY, lR);
              ctx.closePath();
              ctx.fill();

              // Label text — white on colored pill
              ctx.globalAlpha = isHighlightedLink ? 1 : 0.9;
              ctx.fillStyle = '#ffffff';
              ctx.fillText(label, midX, midY);
              ctx.globalAlpha = 1;
            }}
            linkLabel={l => l.type || ''}
            linkColor={l => {
              const id = String(l.id ?? '');
              // E2: Path links are cyan
              if (pathHighlight?.linkKeys?.has(id)) return '#06b6d4';
              // E3: RAG overlay edges — violet
              if (l._ragOverlay) return 'rgba(168, 85, 247, 0.75)';
              const dim = highlighted.linkKeys
                ? !highlighted.linkKeys.has(id)
                : false;
              if (dim) return 'rgba(148, 163, 184, 0.20)';
              const relType = l.type || l.relationship || '';
              if (currentViewId === 'DIGITAL_THREAD' && DT_REL_COLORS[relType]) return DT_REL_COLORS[relType];
              if (currentViewId === 'ONTOLOGY' && ONTOLOGY_REL_COLORS[relType]) return ONTOLOGY_REL_COLORS[relType];
              if (currentViewId === 'OSLC' && OSLC_REL_COLORS[relType]) return OSLC_REL_COLORS[relType];
              // Universal fallback — color all known rel types consistently across views
              if (ALL_REL_COLORS[relType]) return ALL_REL_COLORS[relType];
              return 'rgba(100, 116, 139, 0.85)';
            }}
            linkWidth={l => {
              const id = String(l.id ?? '');
              if (pathHighlight?.linkKeys?.has(id)) return 3.5;
              if (l._ragOverlay) return 2.0;
              return highlighted.linkKeys && highlighted.linkKeys.has(id)
                ? 2.6
                : 1.2;
            }}
            linkDirectionalArrowLength={3}
            linkDirectionalArrowRelPos={1}
            // Engine Configuration
            cooldownTicks={300}
            cooldownTime={8000}
            d3VelocityDecay={0.3}
            d3AlphaDecay={0.0228}

            onEngineStop={() => {
              setLayoutDone(true);
              // Only update layoutActive if we were tracking it as active (for Play/Pause button)
              if (layoutActive) setLayoutActive(false);
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
            <div className="h-px bg-border my-1" />
            <Button
              variant={aiPanelOpen ? 'default' : 'secondary'}
              size="icon"
              className="w-10 h-10 bg-background/80 backdrop-blur-sm border shadow-sm"
              onClick={() => setAiPanelOpen(v => !v)}
              title="KnowledgeGraph AI"
            >
              <Brain className="h-4 w-4" />
            </Button>
          </div>
        )}

        {/* ── KnowledgeGraph AI floating panel ── */}
        {aiPanelOpen && (
          <div
            ref={aiPanelRef}
            className="absolute z-30 flex flex-col rounded-xl border border-border bg-background shadow-2xl"
            style={aiPanelPos
              ? { left: aiPanelPos.x, top: aiPanelPos.y, width: aiPanelSize.w, height: aiPanelSize.h }
              : { bottom: 16, right: 64, width: aiPanelSize.w, height: aiPanelSize.h }
            }
          >
            {/* Header — drag handle */}
            <div
              className="flex items-center gap-2 px-3 py-2 border-b border-border bg-muted/40 shrink-0 cursor-move select-none rounded-t-xl"
              onMouseDown={startAiDrag}
            >
              <Brain className="h-4 w-4 text-violet-500 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold leading-none">KnowledgeGraph AI</p>
                <p className="text-[10px] text-muted-foreground mt-0.5">Digital engineering &amp; product ontology assistant</p>
              </div>
              <Badge variant="outline" className="text-[9px] shrink-0">Beta</Badge>
              {ragMessages.length > 0 && (
                <button className="text-muted-foreground hover:text-destructive transition-colors ml-1" title="Clear conversation"
                  onClick={() => { setRagMessages([]); setRagHighlight(null); setRagOverlayNodes([]); setRagOverlayLinks([]); }}>
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              )}
              <button className="text-muted-foreground hover:text-foreground transition-colors ml-1" title="Close"
                onClick={() => setAiPanelOpen(false)}>
                <X className="h-3.5 w-3.5" />
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
              {ragMessages.length === 0 && !ragLoading && (
                <div className="flex flex-col items-center justify-center h-full gap-3 text-center pb-4">
                  <div className="w-10 h-10 rounded-full bg-violet-100 dark:bg-violet-950 flex items-center justify-center">
                    <Brain className="h-5 w-5 text-violet-500" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold">Digital Engineering Assistant</p>
                    <p className="text-[10px] text-muted-foreground mt-1 leading-relaxed max-w-[220px]">
                      Ask about ISO 10303 AP239/AP242/AP243 traceability, product ontology, simulation dossiers, or requirements.
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-1 justify-center max-w-[260px]">
                    {({
                      ONTOLOGY: ['Ontology structure overview','How are OWL classes connected?','AP239 vs AP242 vs AP243'],
                      AP239: ['Traceability overview','How are Requirements linked?','Part → WorkOrder path'],
                      AP242: ['How are assemblies structured?','Part → Assembly connections','Material relationships'],
                      AP243: ['How are simulation dossiers linked?','Dossier → Evidence traceability','Study → Context relationships'],
                      ENTERPRISE: ['Cross-domain traceability','Show all node types','Network overview'],
                    }[currentViewId] || ['How are nodes connected?','Traceability overview','List simulation dossiers']
                    ).map(q => (
                      <button key={q}
                        className="text-[9px] px-2 py-1 rounded-full border border-violet-200 dark:border-violet-800 bg-violet-50 dark:bg-violet-950/50 text-violet-700 dark:text-violet-300 hover:bg-violet-100 dark:hover:bg-violet-900 transition-colors"
                        onClick={() => setRagQuestion(q)}>{q}</button>
                    ))}
                  </div>
                </div>
              )}

              {ragMessages.map(msg => (
                <div key={msg.id} className={`flex gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                  <div className={`w-5 h-5 rounded-full shrink-0 flex items-center justify-center text-[9px] font-bold mt-0.5 ${
                    msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-violet-100 dark:bg-violet-950'
                  }`}>
                    {msg.role === 'user' ? 'U' : <Brain className="h-3 w-3 text-violet-500" />}
                  </div>
                  <div className={`flex flex-col gap-1 max-w-[85%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                    <div className={`rounded-xl px-3 py-2 text-xs leading-relaxed ${
                      msg.role === 'user' ? 'bg-primary text-primary-foreground rounded-tr-sm' : 'bg-muted text-foreground rounded-tl-sm'
                    }`}>
                      {msg.role === 'user'
                        ? msg.content
                        : msg.streaming && !msg.content
                          ? <span className="inline-block w-2 h-3 bg-violet-400 animate-pulse rounded-sm" />
                          : <><SimpleMarkdown text={msg.content} />{msg.streaming && <span className="inline-block w-1.5 h-3 bg-violet-400 animate-pulse rounded-sm ml-0.5 align-middle" />}</>}
                    </div>
                    {msg.role === 'assistant' && msg.sources?.length > 0 && (
                      <div className="w-full space-y-0.5 px-1">
                        <p className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wide">Sources</p>
                        {msg.sources.slice(0, 5).map((s, i) => {
                          const isInGraph = ragHighlight?.has(String(s.uid));
                          const focusNode = () => {
                            if (!normalizedGraph || !fgRef.current) return;
                            const node = normalizedGraph.nodes.find(n => String(n.id) === String(s.uid) || String(n.properties?.uid) === String(s.uid));
                            if (node && node.x != null) { fgRef.current.centerAt(node.x, node.y, 600); fgRef.current.zoom(6, 600); setSelectedNode(node); }
                          };
                          return (
                            <div key={i} onClick={focusNode} title={isInGraph ? 'Click to focus in graph' : 'Node not in current view'}
                              className={`flex items-center gap-1 text-[10px] rounded px-1 py-0.5 cursor-pointer hover:bg-muted/80 transition-colors ${
                                isInGraph ? 'text-violet-600 dark:text-violet-400' : 'text-muted-foreground'
                              }`}>
                              <Hash className="h-2.5 w-2.5 shrink-0" />
                              <span className="truncate">{s.name || s.uid}</span>
                              {s.score && <span className="ml-auto shrink-0 opacity-60">{(s.score * 100).toFixed(0)}%</span>}
                              {isInGraph && <span className="text-violet-500 shrink-0">●</span>}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {ragLoading && (
                <div className="flex gap-2">
                  <div className="w-5 h-5 rounded-full shrink-0 bg-violet-100 dark:bg-violet-950 flex items-center justify-center mt-0.5">
                    <Brain className="h-3 w-3 text-violet-500" />
                  </div>
                  <div className="bg-muted rounded-xl rounded-tl-sm px-3 py-2 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/60 animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/60 animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/60 animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Chips */}
            {ragMessages.length > 0 && (
              <div className="px-3 pb-1 shrink-0">
                <div className="flex gap-1 overflow-x-auto pb-1">
                  {({
                    ONTOLOGY: ['OWL class hierarchy','AP239 vs AP242','Property relationships'],
                    AP239: ['Requirements traceability','Part → WorkOrder','Verification links'],
                    AP242: ['Assembly structure','Part connections','Shape links'],
                    AP243: ['Dossier links','Evidence traceability','SimulationRun path'],
                    ENTERPRISE: ['Cross-domain','All node types','Network overview'],
                  }[currentViewId] || ['Traceability','Node types','Connections']
                  ).map(q => (
                    <button key={q}
                      className="text-[9px] px-2 py-0.5 rounded-full border border-border bg-muted/50 hover:bg-muted whitespace-nowrap text-muted-foreground hover:text-foreground transition-colors shrink-0"
                      onClick={() => setRagQuestion(q)}>{q}</button>
                  ))}
                </div>
              </div>
            )}

            {/* Input */}
            <div className="px-3 pb-3 pt-1 border-t border-border shrink-0">
              <div className="flex gap-2 items-end">
                <Textarea
                  placeholder="Ask about traceability, ontology, simulations…"
                  value={ragQuestion}
                  onChange={e => setRagQuestion(e.target.value)}
                  className="flex-1 min-h-9 max-h-24 text-xs resize-none rounded-xl"
                  onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleRAGQuery(); } }}
                  rows={1}
                />
                <Button size="icon" className="h-9 w-9 rounded-xl shrink-0" disabled={ragLoading || !ragQuestion.trim()} onClick={handleRAGQuery}>
                  {ragLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                </Button>
              </div>
              <p className="text-[9px] text-muted-foreground mt-1">Enter to send · Shift+Enter newline · View: {currentViewId}</p>
            </div>

            {/* Resize handle — bottom-right corner */}
            <div
              className="absolute bottom-0 right-0 w-4 h-4 cursor-se-resize z-10"
              onMouseDown={startAiResize}
              title="Drag to resize"
            >
              <svg viewBox="0 0 10 10" className="w-full h-full text-muted-foreground/40">
                <line x1="3" y1="10" x2="10" y2="3" stroke="currentColor" strokeWidth="1.2" />
                <line x1="6" y1="10" x2="10" y2="6" stroke="currentColor" strokeWidth="1.2" />
              </svg>
            </div>
          </div>
        )}

        {/* E1: Right-click Context Menu */}
        {contextMenu && (
          <div
            className="absolute z-50 bg-popover border rounded-lg shadow-lg py-1 min-w-48 animate-in fade-in-0 zoom-in-95"
            style={{ left: contextMenu.x, top: contextMenu.y }}
            onMouseLeave={dismissContextMenu}
          >
            <div className="px-3 py-1.5 text-xs font-semibold text-muted-foreground border-b mb-1 truncate">
              {contextMenu.node?.name || contextMenu.node?.id}
            </div>
            {[
              { key: 'expand', icon: Expand, label: 'Expand 2-hop neighbourhood' },
              { key: 'pin', icon: MousePointerClick, label: contextMenu.node?.fx != null ? 'Unpin node' : 'Pin node position' },
              { key: 'multiselect', icon: Boxes, label: multiSelected.has(String(contextMenu.node?.id)) ? 'Remove from selection' : 'Add to selection' },
              { key: 'detail', icon: ExternalLink, label: 'Show detail panel' },
              { key: 'copy', icon: Copy, label: 'Copy node ID' },
            ].map(({ key, icon: Icon, label }) => (
              <button
                key={key}
                className="flex items-center gap-2 w-full px-3 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground transition-colors"
                onClick={() => handleContextAction(key, contextMenu.node)}
              >
                <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                {label}
              </button>
            ))}
          </div>
        )}

        {/* E19: Lasso selection rectangle */}
        {lassoStart && lassoEnd && (
          <div
            className="absolute border-2 border-dashed border-cyan-400 bg-cyan-400/10 pointer-events-none z-20"
            style={{
              left: Math.min(lassoStart.x, lassoEnd.x),
              top: Math.min(lassoStart.y, lassoEnd.y),
              width: Math.abs(lassoEnd.x - lassoStart.x),
              height: Math.abs(lassoEnd.y - lassoStart.y),
            }}
          />
        )}

        {/* E10: Minimap */}
        {normalizedGraph && !isLoading && normalizedGraph.nodes.length > 0 && normalizedGraph.nodes.length < 2000 && (
          <div className="absolute bottom-4 right-4 w-36 h-28 border rounded bg-background/90 backdrop-blur-sm z-10 overflow-hidden">
            <canvas
              className="w-full h-full"
              ref={el => {
                if (!el || !normalizedGraph) return;
                const ctx = el.getContext('2d');
                if (!ctx) return;
                const dpr = window.devicePixelRatio || 1;
                el.width = 144 * dpr;
                el.height = 112 * dpr;
                ctx.scale(dpr, dpr);
                ctx.clearRect(0, 0, 144, 112);
                // Compute bounds
                let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
                for (const n of normalizedGraph.nodes) {
                  if (n.x == null || n.y == null) continue;
                  minX = Math.min(minX, n.x); maxX = Math.max(maxX, n.x);
                  minY = Math.min(minY, n.y); maxY = Math.max(maxY, n.y);
                }
                const rangeX = Math.max(1, maxX - minX);
                const rangeY = Math.max(1, maxY - minY);
                const pad = 8;
                const mapW = 144 - pad * 2;
                const mapH = 112 - pad * 2;
                // Draw links
                ctx.strokeStyle = 'rgba(148,163,184,0.3)';
                ctx.lineWidth = 0.5;
                for (const l of normalizedGraph.links) {
                  const s = typeof l.source === 'object' ? l.source : null;
                  const t = typeof l.target === 'object' ? l.target : null;
                  if (!s?.x || !t?.x) continue;
                  ctx.beginPath();
                  ctx.moveTo(pad + (s.x - minX) / rangeX * mapW, pad + (s.y - minY) / rangeY * mapH);
                  ctx.lineTo(pad + (t.x - minX) / rangeX * mapW, pad + (t.y - minY) / rangeY * mapH);
                  ctx.stroke();
                }
                // Draw nodes
                for (const n of normalizedGraph.nodes) {
                  if (n.x == null || n.y == null) continue;
                  const x = pad + (n.x - minX) / rangeX * mapW;
                  const y = pad + (n.y - minY) / rangeY * mapH;
                  ctx.fillStyle = highlighted.nodeIds?.has(String(n.id)) ? '#06b6d4' : getNodeColor(n);
                  ctx.globalAlpha = highlighted.nodeIds?.has(String(n.id)) ? 1 : 0.6;
                  ctx.beginPath();
                  ctx.arc(x, y, 1.5, 0, 2 * Math.PI);
                  ctx.fill();
                }
                ctx.globalAlpha = 1;
              }}
            />
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

{/* E9: Enhanced Selected-node detail card */}
        {selectedNode && (
          <Card className="absolute bottom-4 left-4 w-96 z-10 max-h-96 overflow-hidden flex flex-col">
            <CardHeader className="pb-2 shrink-0">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 min-w-0">
                  <div
                    className="w-3 h-3 rounded-full shrink-0"
                    style={{ backgroundColor: getNodeColor(selectedNode) }}
                  />
                  <CardTitle className="text-sm truncate">{selectedNode.name || selectedNode.id}</CardTitle>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    title="Copy ID"
                    onClick={() => navigator.clipboard?.writeText(String(selectedNode.id))}
                  >
                    <Copy className="h-3 w-3" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={() => setSelectedNode(null)}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              </div>
              <div className="flex items-center gap-1 mt-1">
                <Badge variant="secondary" className="text-[10px]">{selectedNode.type}</Badge>
                {selectedNode.ap_level && <Badge variant="outline" className="text-[10px]">{selectedNode.ap_level}</Badge>}
                {selectedNode.ap_schema && <Badge variant="outline" className="text-[10px]">{selectedNode.ap_schema}</Badge>}
                {degreeMap[selectedNode.id] > 0 && (
                  <Badge variant="outline" className="text-[10px]">{degreeMap[selectedNode.id]} connections</Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-2 text-xs overflow-y-auto flex-1 pb-3">
              {/* Node ID */}
              <div className="flex gap-1 items-center">
                <span className="font-medium text-muted-foreground shrink-0">ID:</span>
                <span className="font-mono text-[10px] break-all text-muted-foreground">{String(selectedNode.id)}</span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-4 w-4 ml-auto shrink-0"
                  title="Copy ID"
                  onClick={() => navigator.clipboard?.writeText(String(selectedNode.id))}
                >
                  <Copy className="h-2.5 w-2.5" />
                </Button>
              </div>

              {selectedNode.description && (
                <div>
                  <span className="font-medium text-muted-foreground">Description:</span>
                  <p className="mt-0.5 leading-relaxed">{selectedNode.description}</p>
                </div>
              )}

              {/* Labels */}
              <div>
                <span className="font-medium text-muted-foreground">Labels:</span>
                <div className="flex flex-wrap gap-1 mt-0.5">
                  {selectedNode.labels.map(label => (
                    <span key={label} className="px-1.5 py-0.5 bg-secondary text-secondary-foreground rounded text-[10px]">
                      {label}
                    </span>
                  ))}
                </div>
              </div>

              {selectedNode.status && (
                <div className="flex gap-1">
                  <span className="font-medium text-muted-foreground shrink-0">Status:</span>
                  <span>{selectedNode.status}</span>
                </div>
              )}

              {/* Properties */}
              {selectedNode.properties && Object.keys(selectedNode.properties).length > 0 && (
                <div>
                  <span className="font-medium text-muted-foreground">Properties:</span>
                  <div className="mt-0.5 space-y-0.5 bg-muted/50 rounded p-1.5">
                    {Object.entries(selectedNode.properties).map(([k, v]) => (
                      <div key={k} className="flex gap-1">
                        <span className="text-muted-foreground shrink-0 font-mono text-[10px]">{k}:</span>
                        <span className="break-all">{String(v).length > 80 ? String(v).slice(0, 80) + '…' : String(v)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Neighbours summary */}
              {normalizedGraph?.neighbors?.get(String(selectedNode.id))?.size > 0 && (
                <div>
                  <span className="font-medium text-muted-foreground">
                    Neighbours ({normalizedGraph.neighbors.get(String(selectedNode.id)).size}):
                  </span>
                  <div className="mt-0.5 space-y-0.5 max-h-24 overflow-y-auto">
                    {[...normalizedGraph.neighbors.get(String(selectedNode.id))].slice(0, 15).map(nbId => {
                      const nb = normalizedGraph.nodes.find(n => String(n.id) === nbId);
                      if (!nb) return null;
                      return (
                        <button
                          key={nbId}
                          className="flex items-center gap-1 w-full hover:bg-accent rounded px-1 py-0.5 text-left"
                          onClick={() => handleNodeClick(nb)}
                        >
                          <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: getNodeColor(nb) }} />
                          <span className="truncate">{nb.name || nb.id}</span>
                          <Badge variant="outline" className="text-[8px] ml-auto shrink-0">{nb.type}</Badge>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Community info */}
              {communityMap && communityMap[selectedNode.id] != null && (
                <div className="flex gap-1">
                  <span className="font-medium text-muted-foreground shrink-0">Community:</span>
                  <Badge style={{ backgroundColor: communityColors[communityMap[selectedNode.id]] }} className="text-white text-[10px]">
                    Cluster #{communityMap[selectedNode.id]}
                  </Badge>
                </div>
              )}
            </CardContent>

            {/* Action buttons */}
            <div className="px-4 pb-3 flex gap-1.5 shrink-0 border-t pt-2">
              {currentViewId === 'DIGITAL_THREAD' && selectedNode.type && (
                <Button
                  size="sm"
                  variant="outline"
                  className="flex-1 h-7 text-xs"
                  onClick={() => {
                    const type = selectedNode.type;
                    const id = selectedNode.id;
                    if (type === 'SimulationDossier' || type === 'Dossier') navigate(`/engineer/simulation/dossiers/${id}`);
                    else if (type === 'Requirement') navigate(`/engineer/requirements`);
                    else if (type === 'Part') navigate(`/engineer/ap242/parts`);
                    else navigate(`/engineer/graph`);
                  }}
                >
                  <ExternalLink className="h-3 w-3 mr-1" /> Detail
                </Button>
              )}
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs"
                onClick={() => {
                  setPathSource(String(selectedNode.id));
                  setPathSourceName(selectedNode.name || String(selectedNode.id));
                  setSidebarTab('tools');
                }}
                title="Use as path source"
              >
                <Route className="h-3 w-3 mr-1" /> Path From
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs"
                onClick={() => {
                  setPathTarget(String(selectedNode.id));
                  setPathTargetName(selectedNode.name || String(selectedNode.id));
                  setSidebarTab('tools');
                }}
                title="Use as path target"
              >
                <Route className="h-3 w-3 mr-1" /> Path To
              </Button>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
});
