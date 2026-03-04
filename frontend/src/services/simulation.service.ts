/** Simulation service — models, runs, results, parameters */
import { apiClient } from './api';

export const getModels = (params?: { limit?: number }) =>
  apiClient.get<{ total: number; models: any[] }>('/simulation/models', { params });

export const getRuns = (params?: {
  dossier_id?: string; run_status?: string; sim_type?: string; limit?: number;
}) => apiClient.get<any[]>('/simulation/runs', { params });

export const getRun = (id: string) =>
  apiClient.get<any>(`/simulation/runs/${encodeURIComponent(id)}`);

export const createRun = (data: any) =>
  apiClient.post<any>('/simulation/runs', data);

export const getResults = (params?: { limit?: number }) =>
  apiClient.get<{ total: number; results: any[] }>('/simulation/results', { params });

export const getParameters = (params?: {
  class_name?: string; property_name?: string; data_type?: string;
  include_constraints?: boolean; limit?: number; owner_type?: string;
}) => {
  const normalized = { ...params };
  if (!normalized.class_name && normalized.owner_type) {
    normalized.class_name = normalized.owner_type;
    delete (normalized as any).owner_type;
  }
  return apiClient.get<any>('/simulation/parameters', { params: normalized });
};

export const validateParameters = (parameters: Array<{ id: string; value: any }>) =>
  apiClient.post<any>('/simulation/validate', { parameters });

export const getUnits = () =>
  apiClient.get<any>('/simulation/units');

export const getWorkflows = (params?: {
  sim_type?: string; status?: string; limit?: number;
}) => apiClient.get<{ total: number; workflows: any[] }>('/simulation/workflows', { params });

export const getWorkflow = (id: string) =>
  apiClient.get<any>(`/simulation/workflows/${encodeURIComponent(id)}`);

export const getWorkflowGraph = (id: string) =>
  apiClient.get<{ workflow_id: string; nodes: any[]; edges: any[] }>(
    `/simulation/workflows/${encodeURIComponent(id)}/graph`
  );
