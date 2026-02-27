/** SDD Dossier CRUD service — wraps /simulation/dossiers endpoints */
import { apiClient } from './api';

export const getDossiers = (params?: {
  status?: string; engineer?: string; limit?: number; offset?: number;
}) => apiClient.get<{ count: number; dossiers: any[] }>('/simulation/dossiers', { params });

export const getDossier = (id: string) =>
  apiClient.get<any>(`/simulation/dossiers/${encodeURIComponent(id)}`);

export const createDossier = (data: any) =>
  apiClient.post<any>('/simulation/dossiers', data);

export const updateDossier = (id: string, data: any) =>
  apiClient.patch<any>(`/simulation/dossiers/${encodeURIComponent(id)}`, data);

export const getDossierArtifacts = (params?: {
  dossier_id?: string; artifact_type?: string; artifact_status?: string; limit?: number;
}) => apiClient.get<any[]>('/simulation/artifacts', { params });

export const getDossierArtifact = (id: string) =>
  apiClient.get<any>(`/simulation/artifacts/${encodeURIComponent(id)}`);

export const getDossierStatistics = () =>
  apiClient.get<{
    total_dossiers: number;
    dossier_statuses: any[];
    total_evidence_categories: number;
    total_artifacts: number;
    total_requirements: number;
  }>('/simulation/statistics');

export const getDossierTrace = (requirementId: string) =>
  apiClient.get<any>(`/simulation/trace/${encodeURIComponent(requirementId)}`);
