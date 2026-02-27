/** Graph service — visualization data, node/rel types, hierarchy, impact */
import { apiClient } from './api';

export const getGraphData = (params?: { limit?: number; node_types?: string; ap_level?: string }) =>
  apiClient.get<any>('/graph/data', { params });

export const getNodeTypes = () =>
  apiClient.get<any>('/graph/node-types');

export const getRelationshipTypes = () =>
  apiClient.get<any>('/graph/relationship-types');

// ── Hierarchy navigation ──────────────────────────────────────
export const getHierarchy = (nodeType: string, nodeId: string, params?: { depth?: number; direction?: string }) =>
  apiClient.get<any>(`/hierarchy/navigate/${encodeURIComponent(nodeType)}/${encodeURIComponent(nodeId)}`, { params });

export const getTraceabilityMatrix = () =>
  apiClient.get<{ count: number; matrix: any[] }>('/hierarchy/traceability-matrix');

export const searchHierarchy = (params: { q: string; levels?: string }) =>
  apiClient.get<any[]>('/hierarchy/search', { params });

export const getImpact = (nodeType: string, nodeId: string) =>
  apiClient.get<any>(`/hierarchy/impact/${encodeURIComponent(nodeType)}/${encodeURIComponent(nodeId)}`);

// ── Authoring ─────────────────────────────────────────────────
export const searchNodes = (params: { q: string; node_type?: string; limit?: number }) =>
  apiClient.get<any[]>('/graph/search', { params });

export const createRelationship = (data: {
  source_id: string; target_id: string; relationship_type: string; properties?: Record<string, any>;
}) => apiClient.post<any>('/graph/relationships', data);
