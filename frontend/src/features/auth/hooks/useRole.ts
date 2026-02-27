import { useCallback } from 'react';
import { useAuthStore } from '@/stores/authStore';
import type { UserRole } from '../types';

const ROLE_STORAGE_KEY = 'mbse-active-role';

/** Resolve the current active role from localStorage → auth store → default. */
function resolveRole(): UserRole {
  const stored = localStorage.getItem(ROLE_STORAGE_KEY);
  if (stored === 'engineer' || stored === 'quality' || stored === 'admin') {
    return stored;
  }
  return 'engineer'; // default persona
}

/**
 * Hook that returns the current active role and a setter.
 * The role is persisted to localStorage so it survives page refresh.
 */
export function useRole() {
  const user = useAuthStore((s) => s.user);
  const role: UserRole = resolveRole();

  const setRole = useCallback((newRole: UserRole) => {
    localStorage.setItem(ROLE_STORAGE_KEY, newRole);
    // Trigger a full route re-evaluation
    window.location.replace(`/${newRole}`);
  }, []);

  return { role, setRole, user } as const;
}

export default useRole;
