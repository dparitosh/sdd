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
