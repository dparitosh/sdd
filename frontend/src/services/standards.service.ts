/** Standards service — AP239, AP242, AP243, SMRL, Requirements */
import { apiClient } from './api';

// ── AP239 (PLCS) ──────────────────────────────────────────────
export const ap239 = {
  getRequirements: (params?: { type?: string; status?: string; priority?: string; search?: string }) =>
    apiClient.get<{ count: number; requirements: any[] }>('/ap239/requirements', { params }),
  getRequirement: (id: string) =>
    apiClient.get<any>(`/ap239/requirements/${encodeURIComponent(id)}`),
  getRequirementTraceability: (id: string) =>
    apiClient.get<any>(`/ap239/requirements/${encodeURIComponent(id)}/traceability`),
  getBulkRequirementTraceability: (requirementIds: string[]) =>
    apiClient.post<{ count: number; results: any[] }>('/ap239/requirements/traceability/bulk', { requirement_ids: requirementIds }),
  getApprovals: () =>
    apiClient.get<{ count: number; approvals: any[] }>('/ap239/approvals'),
  getAnalyses: () =>
    apiClient.get<{ count: number; analyses: any[] }>('/ap239/analyses'),
  getDocuments: () =>
    apiClient.get<{ count: number; documents: any[] }>('/ap239/documents'),
  getStatistics: () =>
    apiClient.get<any>('/ap239/statistics'),
};

// ── AP242 (Product Data) ──────────────────────────────────────
export const ap242 = {
  getParts: (params?: { status?: string; search?: string }) =>
    apiClient.get<{ count: number; parts: any[] }>('/ap242/parts', { params }),
  getPart: (id: string) =>
    apiClient.get<any>(`/ap242/parts/${encodeURIComponent(id)}`),
  getPartBOM: (id: string) =>
    apiClient.get<any>(`/ap242/parts/${encodeURIComponent(id)}/bom`),
  getMaterials: (params?: { type?: string; search?: string }) =>
    apiClient.get<{ count: number; materials: any[] }>('/ap242/materials', { params }),
  getMaterial: (name: string) =>
    apiClient.get<any>(`/ap242/materials/${encodeURIComponent(name)}`),
  getAssemblies: () =>
    apiClient.get<{ count: number; assemblies: any[] }>('/ap242/assemblies'),
  getGeometry: () =>
    apiClient.get<{ count: number; geometries: any[] }>('/ap242/geometry'),
  getStatistics: () =>
    apiClient.get<any>('/ap242/statistics'),
};

// ── AP243 (Reference Data & Domain Model) ─────────────────────
export const ap243 = {
  getOverview: () =>
    apiClient.get<any>('/ap243/overview'),
  getDomainClasses: (params?: { search?: string; stereotype?: string; is_abstract?: boolean; package?: string; skip?: number; limit?: number }) =>
    apiClient.get<{ count: number; classes: any[] }>('/ap243/domain-classes', { params }),
  getDomainClassDetail: (name: string) =>
    apiClient.get<any>(`/ap243/domain-classes/${encodeURIComponent(name)}`),
  domainSearch: (params: { q: string; node_type?: string; skip?: number; limit?: number }) =>
    apiClient.get<{ count: number; results: any[] }>('/ap243/domain-search', { params }),
  getPackages: () =>
    apiClient.get<{ count: number; packages: any[] }>('/ap243/packages'),
  getStereotypes: () =>
    apiClient.get<{ count: number; stereotypes: any[] }>('/ap243/stereotypes'),
  getOntologies: (params?: { ontology?: string; search?: string }) =>
    apiClient.get<{ count: number; ontologies: any[] }>('/ap243/ontologies', { params }),
  getOntologyDetail: (name: string) =>
    apiClient.get<any>(`/ap243/ontologies/${encodeURIComponent(name)}`),
  getUnits: () =>
    apiClient.get<{ count: number; units: any[] }>('/ap243/units'),
  getUnit: (id: string) =>
    apiClient.get<any>(`/ap243/units/${encodeURIComponent(id)}`),
  getValueTypes: () =>
    apiClient.get<{ count: number; value_types: any[] }>('/ap243/value-types'),
  getClassifications: (params?: { system?: string }) =>
    apiClient.get<{ count: number; classifications: any[] }>('/ap243/classifications', { params }),
  getStatistics: () =>
    apiClient.get<any>('/ap243/statistics'),
};

// ── SMRL generic CRUD ─────────────────────────────────────────
export const smrl = {
  getResource: (type: string, uid: string) =>
    apiClient.get<any>(`/v1/${type}/${encodeURIComponent(uid)}`),
  listResources: (type: string, params?: { limit?: number; offset?: number }) =>
    apiClient.get<any>(`/v1/${type}`, { params }),
  createResource: (type: string, data: any) =>
    apiClient.post<any>(`/v1/${type}`, data),
  updateResource: (type: string, uid: string, data: any) =>
    apiClient.put<any>(`/v1/${type}/${encodeURIComponent(uid)}`, data),
  patchResource: (type: string, uid: string, data: any) =>
    apiClient.patch<any>(`/v1/${type}/${encodeURIComponent(uid)}`, data),
  deleteResource: (type: string, uid: string) =>
    apiClient.delete<any>(`/v1/${type}/${encodeURIComponent(uid)}`),
};

// ── Requirements convenience ──────────────────────────────────
export const requirements = {
  list: (params?: { limit?: number; offset?: number }) =>
    apiClient.get<any[]>('/v1/Requirement', { params }),
  get: (uid: string) =>
    apiClient.get<any>(`/v1/Requirement/${encodeURIComponent(uid)}`),
  create: (data: any) =>
    apiClient.post<any>('/v1/Requirement', data),
  update: (uid: string, data: any) =>
    apiClient.put<any>(`/v1/Requirement/${encodeURIComponent(uid)}`, data),
  delete: (uid: string) =>
    apiClient.delete<any>(`/v1/Requirement/${encodeURIComponent(uid)}`),
  getTraceability: (uid: string) =>
    apiClient.get<any>(`/ap239/requirements/${encodeURIComponent(uid)}/traceability`),
};
