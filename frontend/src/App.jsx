import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HelmetProvider } from 'react-helmet-async';
import { Toaster } from '@ui/sonner';
import { ThemeProvider } from '@/components/theme-provider';
import ErrorBoundary from '@/components/ErrorBoundary';
import ProtectedRoute from '@/components/auth/ProtectedRoute';

// Auth pages (outside role routing)
import Login from '@/features/auth/components/Login';
import AuthCallback from '@/features/auth/components/AuthCallback';

// Role-based app layouts
import EngineerLayout from '@/apps/engineer/layout';
import { engineerRoutes } from '@/apps/engineer/routes';
import QualityLayout from '@/apps/quality/layout';
import { qualityRoutes } from '@/apps/quality/routes';
import AdminLayout from '@/apps/admin/layout';
import { adminRoutes } from '@/apps/admin/routes';

import { useWebSocket } from '@/hooks/useWebSocket';
import logger from '@/utils/logger';
import '@/i18n';
import { QUERY_CONFIG } from '@/constants';
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: QUERY_CONFIG.RETRY_ATTEMPTS,
      staleTime: QUERY_CONFIG.STALE_TIME
    }
  }
});

/** Reads stored role from localStorage and redirects to the matching app root. */
function RoleRedirect() {
  const stored = localStorage.getItem('mbse-active-role');
  const role = (stored === 'engineer' || stored === 'quality' || stored === 'admin') ? stored : 'engineer';
  return <Navigate to={`/${role}`} replace />;
}

function AppContent() {
  const {
    connected
  } = useWebSocket(true);
  useEffect(() => {
    if (connected) {
      logger.log('✓ WebSocket connected - real-time updates enabled');
    }
  }, [connected]);
  return (
    <Router>
      <Routes>
        {/* Public routes — outside role routing */}
        <Route path="/login" element={<Login />} />
        <Route path="/auth/callback" element={<AuthCallback />} />

        {/* Role-based app routes */}
        <Route
          path="/engineer/*"
          element={
            <ProtectedRoute>
              <EngineerLayout />
            </ProtectedRoute>
          }
        >
          {engineerRoutes()}
        </Route>

        <Route
          path="/quality/*"
          element={
            <ProtectedRoute>
              <QualityLayout />
            </ProtectedRoute>
          }
        >
          {qualityRoutes()}
        </Route>

        <Route
          path="/admin/*"
          element={
            <ProtectedRoute requiredRoles={['admin']}>
              <AdminLayout />
            </ProtectedRoute>
          }
        >
          {adminRoutes()}
        </Route>

        {/* Default redirect: / → role-based landing page */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <RoleRedirect />
            </ProtectedRoute>
          }
        />

        {/* Catch-all: redirect unknown paths to the role landing page */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}
function App() {
  return <ErrorBoundary><HelmetProvider><ThemeProvider defaultTheme="system" storageKey="mbse-ui-theme"><QueryClientProvider client={queryClient}><AppContent /><Toaster /></QueryClientProvider></ThemeProvider></HelmetProvider></ErrorBoundary>;
}
export default App;
