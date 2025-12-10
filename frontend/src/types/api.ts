export interface NodeType {
  label: string;
  count: number;
}

export interface RelationshipType {
  type: string;
  count: number;
}

export interface Statistics {
  node_types: Record<string, number>;
  relationship_types: Record<string, number>;
  total_nodes: number;
  total_relationships: number;
}

export interface Artifact {
  uid: string;
  type: string;
  name: string;
  comment?: string;
  href?: string;
  created_on?: string;
  last_modified?: string;
  created_by?: string;
  modified_by?: string;
}

export interface Requirement extends Artifact {
  type: 'Requirement';
  text: string;
  priority?: 'Critical' | 'High' | 'Medium' | 'Low';
  status?: 'Draft' | 'Approved' | 'Implemented' | 'Verified';
  traceability?: {
    satisfies: Artifact[];
    verified_by: Artifact[];
    refined_by: Artifact[];
  };
}

export interface SearchParams {
  type?: string;
  name?: string;
  comment?: string;
  limit?: number;
  offset?: number;
}

export interface PaginationParams {
  page: number;
  pageSize: number;
}

export interface ApiResponse<T> {
  data: T;
  meta?: {
    total: number;
    page: number;
    pageSize: number;
  };
}

export interface CypherResult {
  results: any[];
  summary: {
    query: string;
    counters: {
      nodes_created?: number;
      nodes_deleted?: number;
      relationships_created?: number;
      relationships_deleted?: number;
      properties_set?: number;
    };
    statistics?: {
      execution_time_ms: number;
    };
  };
}

// ============================================================================
// AP239 Types (Requirements, Analysis, Approvals, Documents)
// ============================================================================

export interface AP239Requirement {
  id: string;
  name: string;
  description?: string;
  type?: 'Performance' | 'Functional' | 'Safety' | 'Interface';
  priority?: 'High' | 'Medium' | 'Low';
  status?: 'Draft' | 'Approved' | 'Obsolete';
  created_at?: string;
  versions?: RequirementVersion[];
  satisfied_by_parts?: string[];
  analyses?: Analysis[];
  approvals?: Approval[];
  documents?: Document[];
  units?: ExternalUnit[];
  ap_level: 1;
  ap_schema: 'AP239';
}

export interface RequirementVersion {
  version: string;
  name: string;
  status: string;
}

export interface Analysis {
  name: string;
  type?: 'ThermalSimulation' | 'StressAnalysis' | 'FluidDynamics' | 'ModalAnalysis';
  method?: string;
  status?: 'Planned' | 'Running' | 'Completed' | 'Failed';
  models?: string[];
  verifies_requirements?: string[];
  geometry_models?: string[];
}

export interface Approval {
  name: string;
  status: 'Pending' | 'Approved' | 'Rejected';
  approved_by?: string;
  approval_date?: string;
  approves_requirements?: string[];
  approved_part_versions?: string[];
}

export interface Document {
  name: string;
  document_id: string;
  version: string;
  type?: 'Specification' | 'Report' | 'Drawing' | 'Manual';
  documents_requirements?: string[];
}

// ============================================================================
// AP242 Types (Parts, Materials, CAD Geometry, Assemblies)
// ============================================================================

export interface AP242Part {
  id: string;
  name: string;
  description?: string;
  part_number?: string;
  status?: 'Released' | 'Development' | 'Obsolete';
  created_at?: string;
  versions?: PartVersion[];
  materials?: Material[];
  geometry?: GeometricModel[];
  assemblies?: string[];
  requirements?: string[];
  approvals?: string[];
  ap_level: 2;
  ap_schema: 'AP242';
}

export interface PartVersion {
  version: string;
  name: string;
  status: string;
}

export interface Assembly {
  name: string;
  type?: 'Mechanical' | 'Electrical' | 'Hydraulic';
  component_count?: number;
  parts?: string[];
}

export interface Material {
  name: string;
  material_type?: 'Metal' | 'Polymer' | 'Composite' | 'Ceramic';
  specification?: string;
  properties?: MaterialProperty[];
  used_in_parts?: string[];
  ontology_classes?: string[];
  requirements?: string[];
  ap_level?: 2;
  ap_schema?: 'AP242';
}

export interface MaterialProperty {
  name: string;
  value: number;
  unit: string;
  temperature?: number;
  unit_name?: string;
}

export interface GeometricModel {
  name: string;
  type?: 'Solid' | 'Surface' | 'Wireframe';
  units?: string;
  representations?: string[];
  parts?: string[];
  analyses?: string[];
}

export interface BOMComponent {
  id: string;
  name: string;
  part_number: string;
}

export interface BOMData {
  root_part: string;
  assembly?: string;
  components: BOMComponent[];
}

// ============================================================================
// AP243 Types (Ontologies, Units, Value Types, Classifications)
// ============================================================================

export interface ExternalOntology {
  name: string;
  ontology: string;
  uri: string;
  description?: string;
  classified_materials?: string[];
  related_parts?: string[];
  related_requirements?: string[];
  ap_level?: 3;
  ap_schema?: 'AP243';
}

export interface ExternalUnit {
  name: string;
  symbol: string;
  type?: string;
  si_conversion?: number;
  used_in_properties?: string[];
  used_in_requirements?: string[];
}

export interface ValueType {
  name: string;
  data_type: string;
  unit_reference?: string;
  used_in_properties?: string[];
}

export interface Classification {
  name: string;
  system: string;
  code: string;
  classified_parts?: string[];
}

// ============================================================================
// Hierarchy & Traceability Types
// ============================================================================

export interface TraceabilityEntry {
  requirement: {
    id: string;
    name: string;
    type?: string;
    status?: string;
  };
  traceability: TraceabilityChain[];
}

export interface TraceabilityChain {
  part_id?: string;
  part_name?: string;
  materials?: string[];
  ontologies?: string[];
}

export interface TraceabilityMatrix {
  count: number;
  matrix: TraceabilityEntry[];
}

export interface NavigationNode {
  type: string;
  id: string;
  name: string;
  level: number;
}

export interface HierarchyNavigation {
  source: {
    type: string;
    id: string;
  };
  upstream?: NavigationNode[];
  downstream?: NavigationNode[];
}

export interface CrossLevelSearchResult {
  query: string;
  levels_searched: number[];
  results: {
    ap239: SearchResultNode[];
    ap242: SearchResultNode[];
    ap243: SearchResultNode[];
  };
  total: number;
}

export interface SearchResultNode {
  type: string;
  id: string;
  name: string;
  description?: string;
  schema: string;
}

export interface ImpactAnalysis {
  source: {
    type: string;
    id: string;
  };
  affected_nodes: AffectedNode[];
}

export interface AffectedNode {
  type: string;
  id: string;
  name: string;
  level: number;
  distance: number;
}

export interface AP239Statistics {
  ap_level: 1;
  ap_schema: 'AP239';
  statistics: Record<string, { total: number; by_status: Record<string, number> }>;
}

export interface AP242Statistics {
  ap_level: 2;
  ap_schema: 'AP242';
  statistics: Record<string, { total: number; breakdown: Record<string, number> }>;
}

export interface AP243Statistics {
  ap_level: 3;
  ap_schema: 'AP243';
  statistics: Record<string, number>;
}

export interface HierarchyStatistics {
  nodes_by_level: Record<string, Record<string, number>>;
  cross_level_relationships: CrossLevelRelationship[];
  total_cross_level_links: number;
}

export interface CrossLevelRelationship {
  from: string;
  to: string;
  relationship: string;
  count: number;
}

// AP239 - Product Life Cycle Support Types
export interface AP239Requirement {
  id: string;
  name: string;
  description: string | null;
  status: string;
  priority: string;
  type: string | null;
  created_at: string | null;
  satisfied_by_parts: string[];
  versions: Array<{
    version: string;
    status: string;
    effective_date: string;
  }>;
}

export interface AP239Approval {
  id: string;
  status: string;
  date: string;
  approver: string | null;
  requirement_id: string | null;
  requirement_name: string | null;
}

export interface AP239Analysis {
  id: string;
  name: string;
  type: string;
  requirement_id: string | null;
  requirement_name: string | null;
}

export interface AP239Document {
  id: string;
  name: string;
  type: string;
  requirement_id: string | null;
  requirement_name: string | null;
}

// AP242 - 3D Engineering Types
export interface AP242Part {
  id: string;
  name: string;
  description: string | null;
  part_number: string | null;
  status: string;
  material: string | null;
  geometry_type: string | null;
  assembly_name: string | null;
}

export interface Material {
  name: string;
  type: string | null;
  specification: string | null;
  properties: Array<{
    name: string;
    value: string;
    unit: string;
  }>;
  used_in_parts: string[];
  ontology_classes: string[];
}

export interface BOMData {
  part: AP242Part;
  components: Array<{
    component_id: string;
    component_name: string;
    quantity: number;
  }>;
}

export interface Assembly {
  name: string;
  description: string | null;
  parts_count: number;
  parts: string[];
}

export interface Geometry {
  id: string;
  type: string;
  part_id: string | null;
  part_name: string | null;
}

// Traceability Types
export interface TraceabilityMatrix {
  count: number;
  matrix: Array<{
    requirement_id: string;
    requirement_name: string;
    target_id: string;
    target_name: string;
    target_type: string;
    relationship_type: string;
  }>;
}

export interface TraceabilityLink {
  requirement: {
    uid: string;
    name: string;
    status?: string;
  };
  target: {
    uid: string;
    name: string;
    type: string;
  };
  relationship: string;
  satisfied: boolean;
}
