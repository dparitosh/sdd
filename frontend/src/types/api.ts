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
