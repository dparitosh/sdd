/** Approval service — Quality Head sign-off endpoints */
import { apiClient } from './api';

export interface ApprovalPayload {
  decision: 'approved' | 'rejected';
  approver: string;
  rationale: string;
}

export const submitApproval = (dossierId: string, payload: ApprovalPayload) =>
  apiClient.post<any>(
    `/simulation/dossiers/${encodeURIComponent(dossierId)}/approve`,
    {
      status: payload.decision === 'approved' ? 'Approved' : 'Rejected',
      reviewer: payload.approver,
      comment: payload.rationale,
    }
  );

export const getApprovalHistory = (dossierId: string) =>
  apiClient.get<{ history: any[] }>(
    `/simulation/dossiers/${encodeURIComponent(dossierId)}/approvals`
  );
