import { apiClient } from './api';

export interface PLMConnector {
  id: string;
  name: string;
  type: string;
  status: 'connected' | 'disconnected' | 'error';
  url?: string;
  last_sync?: string | null;
  error?: string;
}

export interface SyncJob {
  job_id: string;
  connector_id: string;
  scope: 'full' | 'incremental';
  entity_types: string[];
  status: 'started' | 'running' | 'completed' | 'failed';
  started_at: string;
  completed_at?: string;
  items_synced?: number;
  errors?: string[];
}

export interface ConnectorStatus extends PLMConnector {
  last_sync?: SyncJob;
  sync_history?: SyncJob[];
}

export interface ConnectorsResponse {
  count: number;
  connectors: PLMConnector[];
}

/**
 * Get list of all PLM connectors
 */
export const getConnectors = async (): Promise<ConnectorsResponse> => {
  const response = await apiClient.get<ConnectorsResponse>('/v1/plm/connectors');
  return response.data;
};

/**
 * Trigger sync for a specific connector
 */
export const triggerSync = async (
  connectorId: string,
  options?: {
    scope?: 'full' | 'incremental';
    entity_types?: string[];
  }
): Promise<SyncJob> => {
  const response = await apiClient.post<SyncJob>(
    `/v1/plm/connectors/${connectorId}/sync`,
    options
  );
  return response.data;
};

/**
 * Get detailed status for a specific connector
 */
export const getConnectorStatus = async (
  connectorId: string
): Promise<ConnectorStatus> => {
  const response = await apiClient.get<ConnectorStatus>(
    `/v1/plm/connectors/${connectorId}/status`
  );
  return response.data;
};
