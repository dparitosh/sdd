/** useSimRunner — manages execute → poll → complete lifecycle for simulation runs */
import { useState, useCallback, useRef } from 'react';
import * as simService from '@/services/simulation.service';

export interface SimRunConfig {
  model_id: string;
  dossier_id?: string;
  parameters?: Record<string, unknown>;
}

type RunStatus = 'idle' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';

interface SimRunnerState {
  status: RunStatus;
  progress: number;
  logs: string[];
  error: string | null;
  resultId: string | null;
}

const POLL_INTERVAL = 2000;

export function useSimRunner() {
  const [state, setState] = useState<SimRunnerState>({
    status: 'idle',
    progress: 0,
    logs: [],
    error: null,
    resultId: null,
  });

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const runIdRef = useRef<string | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const appendLog = useCallback((line: string) => {
    setState((prev) => ({ ...prev, logs: [...prev.logs, line] }));
  }, []);

  const pollStatus = useCallback(async () => {
    if (!runIdRef.current) return;
    try {
      const run = await simService.getRun(runIdRef.current);
      const runStatus: string = run?.status ?? 'running';
      const pct: number = run?.progress ?? state.progress;

      // Append any new log lines from the run result
      if (run?.log_line) {
        appendLog(run.log_line);
      }

      if (runStatus === 'completed') {
        stopPolling();
        setState((prev) => ({
          ...prev,
          status: 'completed',
          progress: 100,
          resultId: run?.result_id ?? run?.id ?? null,
        }));
        appendLog('[✓] Simulation completed successfully');
        if (run?.iso_compliance) {
          appendLog(`[ISO] Compliance: ${run.iso_compliance}`);
        }
      } else if (runStatus === 'failed') {
        stopPolling();
        setState((prev) => ({
          ...prev,
          status: 'failed',
          error: run?.error ?? 'Simulation failed',
        }));
        appendLog(`[✗] Simulation failed: ${run?.error ?? 'Unknown error'}`);
      } else {
        setState((prev) => ({
          ...prev,
          status: runStatus as RunStatus,
          progress: Math.min(99, pct),
        }));
      }
    } catch (err: any) {
      // Network errors during polling — log but don't stop
      appendLog(`[WARN] Poll error: ${err?.message ?? String(err)}`);
    }
  }, [appendLog, stopPolling, state.progress]);

  const execute = useCallback(
    async (config: SimRunConfig) => {
      stopPolling();
      runIdRef.current = null;

      setState({
        status: 'queued',
        progress: 0,
        logs: [],
        error: null,
        resultId: null,
      });

      appendLog(`[>] Starting simulation — model: ${config.model_id}`);
      if (config.dossier_id) appendLog(`[>] Target dossier: ${config.dossier_id}`);
      appendLog('[>] Submitting run…');

      try {
        const created = await simService.createRun({
          model_id: config.model_id,
          dossier_id: config.dossier_id,
          parameters: config.parameters ?? {},
          name: `Run-${Date.now()}`,
        });

        const id = created?.id ?? created?.run_id;
        if (!id) {
          setState((prev) => ({ ...prev, status: 'failed', error: 'No run ID returned' }));
          appendLog('[✗] Failed: No run ID returned from API');
          return;
        }

        runIdRef.current = id;
        setState((prev) => ({ ...prev, status: 'running', progress: 5 }));
        appendLog(`[>] Run created: ${id}`);
        appendLog('[>] Polling for status…');

        // Start polling
        pollRef.current = setInterval(pollStatus, POLL_INTERVAL);
      } catch (err: any) {
        const msg = err?.response?.data?.detail ?? err?.message ?? String(err);
        setState((prev) => ({ ...prev, status: 'failed', error: msg }));
        appendLog(`[✗] Execution error: ${msg}`);
      }
    },
    [appendLog, stopPolling, pollStatus],
  );

  const reset = useCallback(() => {
    stopPolling();
    runIdRef.current = null;
    setState({ status: 'idle', progress: 0, logs: [], error: null, resultId: null });
  }, [stopPolling]);

  return {
    execute,
    status: state.status,
    progress: state.progress,
    logs: state.logs,
    isRunning: state.status === 'running' || state.status === 'queued',
    error: state.error,
    resultId: state.resultId,
    reset,
  };
}
