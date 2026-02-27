
export enum UserRole {
  SIMULATION_ENGINEER = 'SIMULATION_ENGINEER',
  QUALITY_HEAD = 'QUALITY_HEAD'
}

export enum SimulationType {
  THERMAL = 'Thermal',
  ELECTROMECHANICAL = 'Electromechanical',
  NVH = 'Noise and Vibration',
  MULTI_PHYSICS = 'Multi-Physics Solver'
}

export enum DossierStatus {
  IN_PROGRESS = 'In Progress',
  PENDING_REVIEW = 'Pending Review',
  APPROVED = 'Approved',
  REJECTED = 'Rejected'
}

export enum CredibilityLevel {
  PC1 = 'Exploratory',
  PC2 = 'Verified Process',
  PC3 = 'Qualified Evidence',
  PC4 = 'Safety Certified'
}

export interface MOSSECLink {
  sourceId: string;
  sourceType: 'Requirement' | 'DesignModel' | 'SimModel' | 'SimulationRun' | 'Result' | 'Evidence' | 'Artifact' | 'Approval' | 'ValidationCase';
  targetId: string;
  targetType: 'Requirement' | 'DesignModel' | 'SimModel' | 'SimulationRun' | 'Result' | 'Evidence' | 'Artifact' | 'Approval' | 'ValidationCase';
  relation: 'validates' | 'derivedFrom' | 'represents' | 'executes' | 'contains' | 'verifies' | 'approves' | 'satisfies';
}

export interface Artifact {
  id: string;
  name: string;
  type: 'Report' | 'Plot' | 'CSV' | '3D Model' | 'Certification';
  timestamp: string;
  size: string;
  status: 'Validated' | 'Pending';
  checksum?: string;
  requirementId?: string;
  fileUrl?: string; 
}

export interface AuditFinding {
  id: string;
  category: 'Compliance' | 'Integrity' | 'Traceability';
  severity: 'Critical' | 'Warning' | 'Pass';
  message: string;
  requirement?: string;
}

export interface KPIData {
  name: string;
  value: number;
  unit: string;
  trend: number[];
}

export interface EvidenceCategory {
  id: number;
  label: string;
  status: 'Complete' | 'Incomplete' | 'Review Required';
}

export interface DecisionLog {
  status: DossierStatus;
  timestamp: string;
  reviewer: string;
  comment?: string;
  signatureId?: string;
}

export interface Dossier {
  id: string;
  version: string;
  credibilityLevel: CredibilityLevel;
  motorId: string;
  projectName: string;
  status: DossierStatus;
  lastUpdated: string;
  engineer: string;
  categories: EvidenceCategory[];
  artifacts: Artifact[];
  kpis: KPIData[];
  decisionHistory?: DecisionLog[];
  mossecLinks?: MOSSECLink[]; 
}
