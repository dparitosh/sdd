/** Insights service — AI analytics + SmartAnalysis */
import { apiClient } from './api';

// ── Pre-computed insight metrics ──────────────────────────────
export type InsightMetric =
  | 'bom-completeness'
  | 'traceability-gaps'
  | 'classification-coverage'
  | 'semantic-duplicates'
  | 'shacl-compliance';

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
