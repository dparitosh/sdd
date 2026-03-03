/** Graph service — visualization data, node/rel types, hierarchy, impact */
import { apiClient } from './api';

export const getGraphData = (params?: { limit?: number; node_types?: string; ap_level?: string }) =>
  apiClient.get<any>('/graph/data', { params, timeout: 120_000 });

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

// ── Path Finder (E2) ─────────────────────────────────────────
export const findShortestPath = (source: string, target: string, maxDepth = 15) =>
  apiClient.get<{
    found: boolean; path_length: number;
    nodes: { id: string; name: string; type: string; labels: string[] }[];
    links: { source: string; target: string; type: string }[];
  }>('/graph/shortest-path', { params: { source, target, max_depth: maxDepth } });

// ── GraphRAG (E3) ────────────────────────────────────────────
export const graphRAGQuery = (question: string, topK = 5) =>
  apiClient.post<{
    answer: string; sources: any[];
    nodes: any[]; links: any[];
  }>('/graph/rag-query', { question, top_k: topK }, { timeout: 150_000 }); // LLM can take up to 120 s

// ── Node Expansion (E1 context menu) ─────────────────────────
export const expandNode = (nodeId: string, depth = 2) =>
  apiClient.get<{ nodes: any[]; links: any[] }>(
    `/graph/expand/${encodeURIComponent(nodeId)}`, { params: { depth } }
  );

// ── Community Detection (E14) ────────────────────────────────
export const getCommunities = () =>
  apiClient.get<{
    communities: { id: string; community: number }[];
    cluster_count: number;
  }>('/graph/communities');

// ── Graph Diff (E20) ────────────────────────────────────────
export const graphDiff = (nodeTypesA: string[], nodeTypesB: string[], limit = 500) =>
  apiClient.post<{
    added_nodes: string[]; removed_nodes: string[];
    added_links: any[]; removed_links: any[];
    summary: Record<string, number>;
  }>('/graph/diff', { node_types_a: nodeTypesA, node_types_b: nodeTypesB, limit });
