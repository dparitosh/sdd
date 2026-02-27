/** Query service — Cypher execution + artifact search + system stats */
import { apiClient } from './api';

export const executeCypher = (query: string, params?: Record<string, any>) =>
  apiClient.post<{ results: any[]; summary: any }>('/cypher', { query, params });

export const searchArtifacts = (params: {
  type?: string; name?: string; comment?: string; limit?: number;
}) => apiClient.get<any[]>('/artifacts', { params });

export const getArtifact = (type: string, id: string) => {
  if (!type || !id) {
    return Promise.reject(new Error('Type and ID are required'));
  }
  return apiClient.get<any>(`/artifacts/${type.toLowerCase()}/${encodeURIComponent(id)}`);
};

export const getHealth = () =>
  apiClient.get<{ status: string; version: string }>('/health');

export const getStatistics = () =>
  apiClient.get<{
    node_types: Record<string, number>;
    relationship_types: Record<string, number>;
    total_nodes: number;
    total_relationships: number;
  }>('/stats');
