/** Auth service — login, logout, session management */
import { apiClient } from './api';

export const login = (credentials: { username: string; password: string }) =>
  apiClient.post<{ access_token: string; user: any }>('/auth/login', credentials);

export const refresh = () =>
  apiClient.post<{ access_token: string }>('/auth/refresh');

export const logout = () =>
  apiClient.post<void>('/auth/logout');

export const verify = () =>
  apiClient.get<{ valid: boolean; user: any }>('/auth/verify');

export const changePassword = (data: { old_password: string; new_password: string }) =>
  apiClient.post<void>('/auth/change-password', data);

export const getSessions = () =>
  apiClient.get<any[]>('/auth/sessions');

export const adminGetSessions = () =>
  apiClient.get<any[]>('/auth/admin/sessions');

export const deleteSession = (sessionId: string) =>
  apiClient.delete<void>(`/auth/sessions/${encodeURIComponent(sessionId)}`);
