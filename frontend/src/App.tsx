import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from '@ui/sonner';
import { ThemeProvider } from '@/components/theme-provider';
import ErrorBoundary from '@/components/ErrorBoundary';
import Layout from '@/components/layout/Layout';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Login from '@/pages/Login';
import AuthCallback from '@/pages/AuthCallback';
import Dashboard from '@/pages/Dashboard';
import AdvancedSearch from '@/pages/AdvancedSearch';
import RestApiExplorer from '@/pages/RestApiExplorer';
import QueryEditor from '@/pages/QueryEditor';
import RequirementsManager from '@/pages/RequirementsManager';
import TraceabilityMatrix from '@/pages/TraceabilityMatrix';
import PLMIntegration from '@/pages/PLMIntegration';
import SystemMonitoring from '@/pages/SystemMonitoring';
import RequirementsDashboard from '@/pages/RequirementsDashboard';
import PartsExplorer from '@/pages/PartsExplorer';
import GraphBrowser from '@/pages/GraphBrowser';
import { useWebSocket } from '@/hooks/useWebSocket';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function AppContent() {
  // Initialize WebSocket connection for real-time updates (optional)
  const { connected } = useWebSocket(true);

  // Log connection status only when connected
  useEffect(() => {
    if (connected) {
      console.log('✓ WebSocket connected - real-time updates enabled');
    }
  }, [connected]);
  
  return (
    <Router>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/auth/callback" element={<AuthCallback />} />

        {/* Protected routes */}
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <Layout>
                <Routes>
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />
                  <Route path="/dashboard" element={<ErrorBoundary><Dashboard /></ErrorBoundary>} />
                  <Route path="/search" element={<ErrorBoundary><AdvancedSearch /></ErrorBoundary>} />
                  <Route path="/api-explorer" element={<ErrorBoundary><RestApiExplorer /></ErrorBoundary>} />
                  <Route path="/query-editor" element={<ErrorBoundary><QueryEditor /></ErrorBoundary>} />
                  <Route path="/requirements" element={<ErrorBoundary><RequirementsManager /></ErrorBoundary>} />
                  <Route path="/traceability" element={<ErrorBoundary><TraceabilityMatrix /></ErrorBoundary>} />
                  <Route path="/plm" element={<ErrorBoundary><PLMIntegration /></ErrorBoundary>} />
                  <Route path="/monitoring" element={<ErrorBoundary><SystemMonitoring /></ErrorBoundary>} />
                  <Route path="/ap239/requirements" element={<ErrorBoundary><RequirementsDashboard /></ErrorBoundary>} />
                  <Route path="/ap242/parts" element={<ErrorBoundary><PartsExplorer /></ErrorBoundary>} />
                  <Route path="/graph" element={<ErrorBoundary><GraphBrowser /></ErrorBoundary>} />
                </Routes>
              </Layout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </Router>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider defaultTheme="system" storageKey="mbse-ui-theme">
        <QueryClientProvider client={queryClient}>
          <AppContent />
          <Toaster />
        </QueryClientProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}export default App;
