/** OSLC service — TRS + OSLC client consumer endpoints */
import { apiClient } from './api';

// ── TRS (Tracked Resource Set) ────────────────────────────────
export const getTRSBase = (page: number = 1) =>
  apiClient.get<any>(`/oslc/trs/base?page=${page}`);

export const getTRSChangelog = () =>
  apiClient.get<any>('/oslc/trs/changelog');

export const getTRS = () =>
  apiClient.get<any>('/oslc/trs');

// ── OSLC Client (Consumer) ────────────────────────────────────
export const connectOSLC = (providerData: {
  root_url: string; auth_type?: string; username?: string; password?: string;
}) => apiClient.post<any>('/oslc/client/connect', providerData);

export const queryOSLC = (params: {
  provider_url: string; resource_type?: string; query?: string;
}) => apiClient.post<any>('/oslc/client/query', params);

// ── Service Provider catalog ──────────────────────────────────
export const getRootServices = () =>
  apiClient.get<any>('/oslc/rootservices');

export const getCatalog = () =>
  apiClient.get<any>('/oslc/catalog');

export const getProvider = (providerId: string) =>
  apiClient.get<any>(`/oslc/sp/${encodeURIComponent(providerId)}`);
