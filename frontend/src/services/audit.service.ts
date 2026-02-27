/** Audit service — ISO-CASCO compliance audit endpoints */
import { apiClient } from './api';

export const runAudit = (dossierId: string) =>
  apiClient.post<{ score: number; findings: any[]; ran_at: string }>(
    `/simulation/dossiers/${encodeURIComponent(dossierId)}/audit`
  );

export const getAuditFindings = (dossierId: string) =>
  apiClient.get<{ findings: any[] }>(
    `/simulation/dossiers/${encodeURIComponent(dossierId)}/audit`
  );
