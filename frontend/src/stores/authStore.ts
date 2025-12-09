import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  username: string;
  role: string;
  email?: string;
  name?: string;
  roles?: string[];
  avatar?: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  
  // Actions
  setAuth: (token: string, user: User) => void;
  logout: () => void;
  refreshToken: (newToken: string) => void;
  hasRole: (role: string) => boolean;
  hasAnyRole: (roles: string[]) => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,

      setAuth: (token: string, user: User) => {
        set({
          token,
          user,
          isAuthenticated: true,
          isLoading: false,
        });
      },

      logout: () => {
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          isLoading: false,
        });
      },

      refreshToken: (newToken: string) => {
        set({ token: newToken });
      },

      hasRole: (role: string) => {
        const { user } = get();
        if (!user) return false;
        // Support both 'role' (string) and 'roles' (array) fields
        if (user.role) return user.role === role;
        if (user.roles) return user.roles.includes(role);
        return false;
      },

      hasAnyRole: (roles: string[]) => {
        const { user } = get();
        if (!user) return false;
        // Support both 'role' (string) and 'roles' (array) fields
        if (user.role) return roles.includes(user.role);
        if (user.roles) return user.roles.some((r) => roles.includes(r));
        return false;
      },
    }),
    {
      name: 'mbse-auth-storage',
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
