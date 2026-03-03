/** Validation service — SHACL shape validation */
import { apiClient } from './api';

export const validateSHACL = (data: any, shapeName?: string) =>
  apiClient.post<{ conforms: boolean; violations: any[] }>(
    '/validate/shacl',
    { data, shape_name: shapeName }
  );

// ── Batch SHACL validation ────────────────────────────────────
export const validateLabel = (label: string) =>
  apiClient.get<{ label: string; total_checked: number; violations_found: number; details: any[] }>(
    `/validate/shacl/validate/${encodeURIComponent(label)}`
  );

export const getViolations = (uid: string) =>
  apiClient.get<any[]>(`/validate/shacl/violations/${encodeURIComponent(uid)}`);

export const getSHACLReport = () =>
  apiClient.get<any[]>('/validate/shacl/report');
