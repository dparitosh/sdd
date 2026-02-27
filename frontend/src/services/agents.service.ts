/** Agents service — AI orchestrator + agent endpoints */
import { apiClient } from './api';

export const runOrchestrator = (query: string, taskType: string = 'impact_analysis') =>
  apiClient.post<{ status: string; messages: any[]; final_state: any }>(
    '/agents/orchestrator/run',
    { query, task_type: taskType }
  );
