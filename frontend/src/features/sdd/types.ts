/** SDD feature types — aligned with backend SDD Pydantic models */

// ── Status & severity enums ───────────────────────────────────
export type DossierStatus =
  | 'Draft'
  | 'UnderReview'
  | 'Approved'
  | 'Rejected'
  | 'Archived';

export type AuditSeverity = 'Critical' | 'Warning' | 'Pass';
export type AuditCategory = 'Compliance' | 'Integrity' | 'Traceability';
export type CredibilityLevel = 'Low' | 'Medium' | 'High' | 'VeryHigh';
export type EvidenceStatus = 'NotStarted' | 'InProgress' | 'Complete';
export type EvidenceCode = 'A1' | 'B1' | 'C1' | 'D1' | 'E1' | 'F1' | 'G1' | 'H1';

// ── MOSSEC relation types ─────────────────────────────────────
export type MOSSECEntityType =
  | 'Requirement' | 'Part' | 'Simulation' | 'Material'
  | 'Ontology' | 'Constraint' | 'Model' | 'Result' | 'Parameter';

export type MOSSECRelationType =
  | 'SATISFIES' | 'DERIVES_FROM' | 'VALIDATES' | 'USES'
  | 'CONSTRAINS' | 'PRODUCES' | 'TRACES_TO' | 'COMPOSED_OF';

// ── Core domain types ─────────────────────────────────────────
export interface Dossier {
  id: string;
  name: string;
  status: DossierStatus;
  type?: string;
  createdAt: string;
  updatedAt: string;
  healthScore: number;
  artifacts: Artifact[];
  mossecLinks: MOSSECLink[];
  evidence: EvidenceCategory[];
  /** Back-compat fields from existing backend */
  title?: string;
  standard_ref?: string;
  owner?: string;
  score?: number;
  motor_id?: string;
  version?: string;
  credibility_level?: string;
  engineer?: string;
  project_name?: string;
  ap_level?: string;
  ap_schema?: string;
  last_updated?: string;
  created_at?: string;
  evidence_categories?: any[];
}

export interface Artifact {
  id: string;
  name: string;
  type: string;
  size: string;
  checksum: string;
  signedBy: string[];
  uploadedAt: string;
  status: string;
}

export interface AuditFinding {
  id: string;
  category: AuditCategory;
  severity: AuditSeverity;
  message: string;
  requirement?: string;
  element_id?: string;
}

export interface AuditResult {
  dossier_id: string;
  score: number;
  findings: AuditFinding[];
  ran_at: string;
}

export interface DecisionLog {
  id: string;
  status: 'approved' | 'rejected';
  timestamp: string;
  reviewer: string;
  comment: string;
  signatureId?: string;
}

export interface ApprovalRecord {
  id: string;
  dossier_id: string;
  decision: 'approved' | 'rejected';
  approver: string;
  rationale: string;
  decided_at: string;
}

export interface MOSSECLink {
  id: string;
  source: string;
  target: string;
  relationType: MOSSECRelationType;
  semanticDescription?: string;
  sourceType?: MOSSECEntityType;
  targetType?: MOSSECEntityType;
}

export interface EvidenceCategory {
  id: string;
  code: EvidenceCode;
  name: string;
  status: EvidenceStatus;
  artifacts: Artifact[];
}

// ── Evidence pipeline category metadata ───────────────────────
export const EVIDENCE_CATEGORIES: { code: EvidenceCode; name: string }[] = [
  { code: 'A1', name: 'Geometry' },
  { code: 'B1', name: 'Mesh' },
  { code: 'C1', name: 'Solver Setup' },
  { code: 'D1', name: 'Run Results' },
  { code: 'E1', name: 'Post-Processing' },
  { code: 'F1', name: 'V&V' },
  { code: 'G1', name: 'Peer Review' },
  { code: 'H1', name: 'Certification' },
];
