/** Simulation feature types — aligned with backend workspace/simulation models */

export type SimulationStatus =
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface SimulationRun {
  id: string;
  name: string;
  status: SimulationStatus;
  model_id: string;
  parameters: Record<string, unknown>;
  started_at?: string;
  completed_at?: string;
  result_summary?: string;
}

export interface SimulationModel {
  id: string;
  name: string;
  description?: string;
  version: string;
  created_at: string;
}

export interface WorkflowDefinition {
  id: string;
  name: string;
  steps: WorkflowStep[];
}

export interface WorkflowStep {
  id: string;
  name: string;
  type: string;
  config: Record<string, unknown>;
  next_step_id?: string;
}
