/** Agents service — AI orchestrator + agent endpoints */
import { apiClient } from './api';

export const runOrchestrator = (query: string, taskType: string = 'impact_analysis') =>
  apiClient.post<{ status: string; messages: any[]; final_state: any }>(
    '/agents/orchestrator/run',
    { query, task_type: taskType }
  );

// ── Semantic search & insight (RAG pipeline) ──────────────────
export const semanticSearch = (query: string, topK: number = 10) =>
  apiClient.post<{ hits: any[]; context: any }>(
    '/agents/semantic/search',
    { query, top_k: topK, expand: false }
  );

export const semanticInsight = (question: string, topK: number = 10) =>
  apiClient.post<{ answer: string; sources: any[] }>(
    '/agents/semantic/insight',
    { question, top_k: topK }
  );

// ── Workflow orchestration (AP243 WorkflowMethod / TaskElement) ───────────
/** Execute a named AP243 WorkflowMethod with validated parameters */
export const runWorkflowAgent = (query: string, taskType: 'workflow_execute' | 'workflow_validate' | 'workflow_query' = 'workflow_execute') =>
  apiClient.post<{ status: string; messages: any[]; final_state: any }>(
    '/agents/orchestrator/run',
    { query, task_type: taskType }
  );

/** Validate parameters against AP243 constraints for a workflow */
export const validateWorkflow = (workflowId: string, paramSummary: string) =>
  runWorkflowAgent(
    `Validate workflow ${workflowId}: ${paramSummary}`,
    'workflow_validate'
  );

// ── Digital Thread (AP239 ↔ AP242 ↔ AP243 + OSLC) ─────────────────────────
/** Trace the full AP239 → AP242 → AP243 digital thread for an artefact */
export const runDigitalThread = (query: string) =>
  apiClient.post<{ status: string; messages: any[]; final_state: any }>(
    '/agents/orchestrator/run',
    { query, task_type: 'digital_thread_trace' }
  );

/** Query OSLC lifecycle resources and their STEP traceability links */
export const queryOslcResources = (query: string) =>
  apiClient.post<{ status: string; messages: any[]; final_state: any }>(
    '/agents/orchestrator/run',
    { query, task_type: 'oslc_query' }
  );

/** Query a specific AP standard level (AP239 / AP242 / AP243) nodes */
export const queryApStandard = (query: string) =>
  apiClient.post<{ status: string; messages: any[]; final_state: any }>(
    '/agents/orchestrator/run',
    { query, task_type: 'ap_standard_query' }
  );

/** Get a full MoSSEC knowledge graph overview */
export const getMossecOverview = () =>
  apiClient.post<{ status: string; messages: any[]; final_state: any }>(
    '/agents/orchestrator/run',
    { query: 'Show full MoSSEC knowledge graph overview', task_type: 'mossec_overview' }
  );

