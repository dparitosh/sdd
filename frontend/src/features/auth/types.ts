/** Auth feature types — aligned with backend Pydantic models */

export type UserRole = 'engineer' | 'quality' | 'admin';

export interface AuthUser {
  id: string;
  email: string;
  displayName: string;
  roles: string[];
  /** ISO-8601 timestamp */
  lastLogin?: string;
}

export interface AuthSession {
  accessToken: string;
  refreshToken?: string;
  expiresAt: string;
  user: AuthUser;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthCallbackParams {
  code: string;
  state?: string;
}
