
import { DossierStatus, EvidenceCategory, Dossier, CredibilityLevel, MOSSECLink } from './types';

export const COLORS = {
  primary: '#004A99', 
  secondary: '#00B0E4', 
  success: '#10B981',
  warning: '#F59E0B',
  danger: '#EF4444',
  gray: '#64748B'
};

export const PRODUCT_SPECS = {
  model: "HDIM-SUGAR-2500",
  application: "Heavy Duty Induction Motor - Cane Juice Extractor",
  tempRange: "-10°C to +85°C",
  loadRating: "2500 kW / 3350 HP",
  shaftFormula: "δL = αL₀ΔT (Cast Steel Grade)",
  lubricant: "ISO VG 100 High Pressure Synthetic",
  constraints: [
    "ISO 9001:2015 Design Control Standards",
    "ISO/IEC 17025 Data Integrity Controls",
    "IEC 61508-3 Engineering Credibility PC3",
    "Continuous 24/7 operation during crushing season"
  ]
};

const MOCK_MOSSEC_LINKS: MOSSECLink[] = [
  // Full Lifecycle Chain for Performance Requirement
  { sourceId: 'REQ-01', sourceType: 'Requirement', targetId: 'SM-EM-01', targetType: 'SimModel', relation: 'represents' },
  { sourceId: 'SM-EM-01', sourceType: 'SimModel', targetId: 'SR-2024-X1', targetType: 'SimulationRun', relation: 'executes' },
  { sourceId: 'SR-2024-X1', sourceType: 'SimulationRun', targetId: 'RES-MAG-01', targetType: 'Result', relation: 'contains' },
  { sourceId: 'RES-MAG-01', sourceType: 'Result', targetId: 'EVD-MAG-PROOFS', targetType: 'Evidence', relation: 'verifies' },
  { sourceId: 'EVD-MAG-PROOFS', sourceType: 'Evidence', targetId: 'A1', targetType: 'Artifact', relation: 'satisfies' },
  { sourceId: 'A1', sourceType: 'Artifact', targetId: 'VC-EM-09', targetType: 'ValidationCase', relation: 'validates' },
  { sourceId: 'VC-EM-09', sourceType: 'ValidationCase', targetId: 'APP-MAG-FINAL', targetType: 'Approval', relation: 'approves' },

  // Added REQ-V1 for the trace link request
  { sourceId: 'REQ-V1', sourceType: 'Requirement', targetId: 'SM-V1-CFD', targetType: 'SimModel', relation: 'represents' },

  // Other specific links
  { sourceId: 'REQ-02', sourceType: 'Requirement', targetId: 'A2', targetType: 'Artifact', relation: 'validates' },
  { sourceId: 'REQ-03', sourceType: 'Requirement', targetId: 'B1', targetType: 'Artifact', relation: 'validates' },
  { sourceId: 'DM-CORE-01', sourceType: 'DesignModel', targetId: 'SM-EM-01', targetType: 'SimModel', relation: 'derivedFrom' },
  { sourceId: 'REQ-04', sourceType: 'Requirement', targetId: 'C1', targetType: 'Artifact', relation: 'validates' },
  { sourceId: 'REQ-05', sourceType: 'Requirement', targetId: 'D1', targetType: 'Artifact', relation: 'validates' },
];

export const MOCK_EVIDENCE_CATEGORIES: EvidenceCategory[] = [
  { id: 1, label: "Performance & Transients (A1/A2)", status: 'Complete' },
  { id: 2, label: "Losses & Efficiency (B1)", status: 'Complete' },
  { id: 3, label: "Cooling & Thermal CFD (C1)", status: 'Complete' },
  { id: 4, label: "Vibration & Modal (D1)", status: 'Complete' },
  { id: 5, label: "Insulation & Aging (E1)", status: 'Complete' },
  { id: 6, label: "Structural Integrity (F1)", status: 'Complete' },
  { id: 7, label: "Tool Qual & Traceability (G1/H1)", status: 'Complete' },
  { id: 8, label: "Final Compliance Release", status: 'Incomplete' }
];

const MOCK_ARTIFACTS: any[] = [
  { id: 'A1', name: 'Artifact A1 – Electromagnetic Performance', type: 'Report', timestamp: '2024-05-15', size: '5.2 MB', status: 'Validated', checksum: 'sha256:e3b0...', requirementId: 'REQ-01' },
  { id: 'A2', name: 'Artifact A2 – Transient Start Simulation', type: 'Report', timestamp: '2024-05-15', size: '8.7 MB', status: 'Validated', checksum: 'sha256:a2b2...', requirementId: 'REQ-02' },
  { id: 'B1', name: 'Artifact B1 – Loss Segregation', type: 'Report', timestamp: '2024-05-15', size: '4.1 MB', status: 'Validated', checksum: 'sha256:77d4...', requirementId: 'REQ-03' },
  { id: 'C1', name: 'Artifact C1 – Cooling CFD Evidence', type: 'Report', timestamp: '2024-05-14', size: '12.4 MB', status: 'Validated', checksum: 'sha256:c1c1...', requirementId: 'REQ-04' },
  { id: 'D1', name: 'Artifact D1 – Modal & Harmonic Analysis', type: 'Report', timestamp: '2024-05-14', size: '6.8 MB', status: 'Pending', checksum: 'sha256:d1d1...', requirementId: 'REQ-05' },
  { id: 'E1', name: 'Artifact E1 – Insulation Life Assessment', type: 'Report', timestamp: '2024-05-13', size: '3.2 MB', status: 'Validated', checksum: 'sha256:e1e1...', requirementId: 'REQ-06' },
  { id: 'F1', name: 'Artifact F1 – Structural Integrity Report', type: 'Report', timestamp: '2024-05-12', size: '5.5 MB', status: 'Validated', checksum: 'sha256:f1f1...', requirementId: 'REQ-07' },
  { id: 'G1', name: 'Artifact G1 – Solver Validation Record', type: 'Certification', timestamp: '2024-05-15', size: '1.2 MB', status: 'Validated', checksum: 'sha256:f1a2...' },
  { id: 'H1', name: 'Artifact H1 – MOSSEC Traceability Matrix', type: 'CSV', timestamp: '2024-05-15', size: '0.8 MB', status: 'Validated', checksum: 'sha256:a1b2...' }
];

export const MOCK_DOSSIERS: Dossier[] = [
  {
    id: "DOS-2024-001",
    version: "v1.2.0",
    credibilityLevel: CredibilityLevel.PC3,
    motorId: "IM-250-A",
    projectName: "Mudra Sugar Plant Expansion",
    status: DossierStatus.IN_PROGRESS,
    lastUpdated: "2024-05-15",
    engineer: "Alex Rivera",
    categories: [...MOCK_EVIDENCE_CATEGORIES],
    artifacts: MOCK_ARTIFACTS,
    kpis: [
      { name: 'Rated Torque (T_n)', value: 15400, unit: 'Nm', trend: [15200, 15300, 15400] },
      { name: 'Efficiency (B1)', value: 96.4, unit: '%', trend: [95.8, 96.1, 96.4] },
    ],
    mossecLinks: MOCK_MOSSEC_LINKS,
  },
  {
    id: "DOS-2024-002",
    version: "v2.1.0",
    credibilityLevel: CredibilityLevel.PC4,
    motorId: "HD-EM-500",
    projectName: "Offshore Wind Platform Delta",
    status: DossierStatus.PENDING_REVIEW,
    lastUpdated: "2024-05-18",
    engineer: "Alex Rivera",
    categories: [...MOCK_EVIDENCE_CATEGORIES],
    artifacts: MOCK_ARTIFACTS,
    kpis: [
      { name: 'Power Density', value: 4.8, unit: 'kW/kg', trend: [4.5, 4.7, 4.8] },
    ],
    mossecLinks: MOCK_MOSSEC_LINKS,
  },
  {
    id: "DOS-2024-003",
    version: "v0.9.5",
    credibilityLevel: CredibilityLevel.PC2,
    motorId: "EV-P-120",
    projectName: "Compact EV Powertrain Phase 1",
    status: DossierStatus.IN_PROGRESS,
    lastUpdated: "2024-05-20",
    engineer: "Alex Rivera",
    categories: [...MOCK_EVIDENCE_CATEGORIES],
    artifacts: MOCK_ARTIFACTS.slice(0, 4),
    kpis: [
      { name: 'Peak Speed', value: 18000, unit: 'RPM', trend: [16000, 17500, 18000] },
    ],
    mossecLinks: MOCK_MOSSEC_LINKS.slice(0, 3),
  },
  {
    id: "DOS-2024-004",
    version: "v3.0.1",
    credibilityLevel: CredibilityLevel.PC4,
    motorId: "IND-CRANE-10",
    projectName: "Heavy Lift Gantry Integration",
    status: DossierStatus.APPROVED,
    lastUpdated: "2024-05-10",
    engineer: "Alex Rivera",
    categories: [...MOCK_EVIDENCE_CATEGORIES],
    artifacts: MOCK_ARTIFACTS,
    kpis: [
      { name: 'Starting Current', value: 450, unit: 'A', trend: [480, 460, 450] },
    ],
    mossecLinks: MOCK_MOSSEC_LINKS,
  },
  {
    id: "DOS-2024-005",
    version: "v1.0.0",
    credibilityLevel: CredibilityLevel.PC3,
    motorId: "TX-PUMP-22",
    projectName: "Municipal Water Works Upgrade",
    status: DossierStatus.REJECTED,
    lastUpdated: "2024-05-12",
    engineer: "Alex Rivera",
    categories: [...MOCK_EVIDENCE_CATEGORIES],
    artifacts: MOCK_ARTIFACTS,
    kpis: [
      { name: 'Hydraulic Eff.', value: 88, unit: '%', trend: [82, 85, 88] },
    ],
    mossecLinks: MOCK_MOSSEC_LINKS,
  }
];
