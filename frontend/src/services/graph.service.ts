/** Graph service — visualization data, node/rel types, hierarchy, impact */
import { apiClient } from './api';

export const getGraphData = (params?: { limit?: number; skip?: number; node_types?: string; ap_level?: string; include_neighbors?: boolean }) =>
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
export const graphRAGQuery = (
  question: string,
  topK = 5,
  focusArea?: string,
  nodeTypes?: string[],
  maxNodes = 500,
) =>
  apiClient.post<{
    answer: string; sources: any[];
    nodes: any[]; links: any[];
  }>('/graph/rag-query', {
    question,
    top_k: topK,
    focus_area: focusArea,
    node_types: nodeTypes,
    max_nodes: maxNodes,
  }, { timeout: 150_000 }); // LLM can take up to 120 s

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

// ── GraphRAG Streaming (E3 — SSE) ────────────────────────────
export function graphRAGQueryStream(
  question: string,
  topK = 5,
  focusArea?: string,
  nodeTypes?: string[],
  maxNodes = 500,
  callbacks: {
    onChunk: (text: string) => void;
    onNodes: (data: { sources: any[]; nodes: any[]; links: any[] }) => void;
    onDone: () => void;
    onError: (msg: string) => void;
  },
): AbortController {
  const controller = new AbortController();
  (async () => {
    try {
      const apiKey = (import.meta as any).env?.VITE_API_KEY ?? '';
      let authHeader = '';
      try {
        const raw = localStorage.getItem('mbse-auth-storage');
        if (raw) {
          const { state } = JSON.parse(raw) as { state?: { token?: string } };
          if (state?.token) authHeader = `Bearer ${state.token}`;
        }
      } catch { /* ignore */ }

      const res = await fetch('/api/graph/rag-query/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(apiKey ? { 'X-API-Key': apiKey } : {}),
          ...(authHeader ? { Authorization: authHeader } : {}),
        },
        body: JSON.stringify({
          question,
          top_k: topK,
          focus_area: focusArea,
          node_types: nodeTypes,
          max_nodes: maxNodes,
        }),
        signal: controller.signal,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const reader = res.body!.getReader();
      const dec = new TextDecoder();
      let buf = '';
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const lines = buf.split('\n');
        buf = lines.pop() ?? '';
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const ev = JSON.parse(line.slice(6)) as any;
            if (ev.type === 'chunk') callbacks.onChunk(ev.text ?? '');
            else if (ev.type === 'nodes') callbacks.onNodes(ev);
            else if (ev.type === 'done') callbacks.onDone();
            else if (ev.type === 'error') callbacks.onError(ev.text ?? 'Unknown error');
          } catch { /* skip malformed SSE line */ }
        }
      }
    } catch (err: any) {
      if (err?.name !== 'AbortError') callbacks.onError(err?.message ?? 'Stream failed');
    }
  })();
  return controller;
}
