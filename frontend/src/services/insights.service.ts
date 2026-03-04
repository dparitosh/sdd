/** Insights service — AI analytics + SmartAnalysis */
import { apiClient } from './api';

// ── Pre-computed insight metrics ──────────────────────────────
export type InsightMetric =
  | 'bom-completeness'
  | 'traceability-gaps'
  | 'classification-coverage'
  | 'semantic-duplicates'
  | 'part-similarity'
  | 'shacl-compliance'
  // Simulation
  | 'simulation-run-status'
  | 'simulation-workflow-coverage'
  | 'simulation-parameter-health'
  | 'simulation-dossier-health'
  | 'simulation-digital-thread';

export const getInsight = (metric: InsightMetric) =>
  apiClient.get<Record<string, any>>(`/insights/${metric}`);

export const getAllInsights = () =>
  Promise.all([
    getInsight('bom-completeness'),
    getInsight('traceability-gaps'),
    getInsight('classification-coverage'),
    getInsight('semantic-duplicates'),
    getInsight('shacl-compliance'),
  ]).then(([bom, trace, cls, dup, shacl]) => ({
    bomCompleteness: bom,
    traceabilityGaps: trace,
    classificationCoverage: cls,
    semanticDuplicates: dup,
    shaclCompliance: shacl,
  }));

export const getSimulationInsights = () =>
  Promise.all([
    getInsight('simulation-run-status'),
    getInsight('simulation-workflow-coverage'),
    getInsight('simulation-parameter-health'),
    getInsight('simulation-dossier-health'),
    getInsight('simulation-digital-thread'),
  ]).then(([runs, workflows, params, dossiers, thread]) => ({
    runStatus: runs,
    workflowCoverage: workflows,
    parameterHealth: params,
    dossierHealth: dossiers,
    digitalThread: thread,
  }));

// ── AI Narrative (LLM-powered) ────────────────────────────────
export interface AiNarrativeResult {
  overall_score: number;
  headline: string;
  summary: string;
  confidence: 'high' | 'medium' | 'low';
  generated_at: number;
  priority_issues: Array<{
    severity: 'critical' | 'warning' | 'healthy';
    title: string;
    detail: string;
    metric_key: string;
  }>;
  recommendations: Array<{
    action: string;
    impact: 'high' | 'medium' | 'low';
    effort: 'high' | 'medium' | 'low';
  }>;
}

export const getAiNarrative = () =>
  apiClient.post<AiNarrativeResult>('/insights/ai-narrative', {});

// ── SmartAnalysis per-node pipeline ───────────────────────────
export interface SmartAnalysisResult {
  uid: string;
  overview: Record<string, any>;
  ontology: Record<string, any>;
  similar: any[];
  violations: any[];
  graph: Record<string, any>;
}

export const runSmartAnalysis = (uid: string) =>
  apiClient.post<SmartAnalysisResult>(`/insights/smart-analysis/${encodeURIComponent(uid)}`);
