import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HelmetProvider } from 'react-helmet-async';
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
import MossecDashboard from '@/pages/MossecDashboard';
import PartsExplorer from '@/pages/PartsExplorer';
import GraphBrowser from '@/pages/GraphBrowser';
import DataImport from '@/pages/DataImport';
import AIInsights from '@/pages/AIInsights';
import SmartAnalysis from '@/pages/SmartAnalysis';
import ModelChat from '@/pages/ModelChat';
import ModelRepository from '@/pages/ModelRepository';
import WorkflowStudio from '@/pages/WorkflowStudio';
import ResultsAnalysis from '@/pages/ResultsAnalysis';
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
        <Route path="/login" element={<Login />} />
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <Layout>
                <Routes>
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />
                  <Route
                    path="/dashboard"
                    element={
                      <ErrorBoundary>
                        <Dashboard />
                      </ErrorBoundary>
                    }
                  />
                  <Route
                    path="/search"
                    element={
                      <ErrorBoundary>
                        <AdvancedSearch />
                      </ErrorBoundary>
                    }
                  />
                  <Route
                    path="/api-explorer"
                    element={
                      <ErrorBoundary>
                        <RestApiExplorer />
                      </ErrorBoundary>
                    }
                  />
                  <Route
                    path="/query-editor"
                    element={
                      <ErrorBoundary>
                        <QueryEditor />
                      </ErrorBoundary>
                    }
                  />
                  <Route
                    path="/requirements"
                    element={
                      <ErrorBoundary>
                        <RequirementsManager />
                      </ErrorBoundary>
                    }
                  />
                  <Route
                    path="/traceability"
                    element={
                      <ErrorBoundary>
                        <TraceabilityMatrix />
                      </ErrorBoundary>
                    }
                  />
                  <Route
                    path="/plm"
                    element={
                      <ErrorBoundary>
                        <PLMIntegration />
                      </ErrorBoundary>
                    }
                  />
                  <Route
                    path="/monitoring"
                    element={
                      <ErrorBoundary>
                        <SystemMonitoring />
                      </ErrorBoundary>
                    }
                  />
                  <Route
                    path="/ap239/requirements"
                    element={
                      <ErrorBoundary>
                        <RequirementsDashboard />
                      </ErrorBoundary>
                    }
                  />
                  <Route
                    path="/mossec-dashboard"
                    element={
                      <ErrorBoundary>
                        <MossecDashboard />
                      </ErrorBoundary>
                    }
                  />
                  <Route
                    path="/ap242/parts"
                    element={
                      <ErrorBoundary>
                        <PartsExplorer />
                      </ErrorBoundary>
                    }
                  />
                  <Route
                    path="/graph"
                    element={
                      <ErrorBoundary>
                        <GraphBrowser />
                      </ErrorBoundary>
                    }
                  />
                  <Route
                    path="/import"
                    element={
                      <ErrorBoundary>
                        <DataImport />
                      </ErrorBoundary>
                    }
                  />
                  <Route
                    path="/ai/insights"
                    element={
                      <ErrorBoundary>
                        <AIInsights />
                      </ErrorBoundary>
                    }
                  />
                  <Route
                    path="/ai/analysis"
                    element={
                      <ErrorBoundary>
                        <SmartAnalysis />
                      </ErrorBoundary>
                    }
                  />
                  <Route
                    path="/ai/chat"
                    element={
                      <ErrorBoundary>
                        <ModelChat />
                      </ErrorBoundary>
                    }
                  />
                  <Route
                    path="/simulation/models"
                    element={
                      <ErrorBoundary>
                        <ModelRepository />
                      </ErrorBoundary>
                    }
                  />
                  <Route
                    path="/simulation/workflows"
                    element={
                      <ErrorBoundary>
                        <WorkflowStudio />
                      </ErrorBoundary>
                    }
                  />
                  <Route
                    path="/simulation/results"
                    element={
                      <ErrorBoundary>
                        <ResultsAnalysis />
                      </ErrorBoundary>
                    }
                  />
                  <Route
                    path="*"
                    element={
                      <div className="flex flex-col items-center justify-center h-[60vh] space-y-4">
                        <h1 className="text-4xl font-bold">404</h1>
                        <p className="text-muted-foreground">Page not found</p>
                        <a href="/dashboard" className="text-primary underline">Back to Dashboard</a>
                      </div>
                    }
                  />
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
  return <ErrorBoundary><HelmetProvider><ThemeProvider defaultTheme="system" storageKey="mbse-ui-theme"><QueryClientProvider client={queryClient}><AppContent /><Toaster /></QueryClientProvider></ThemeProvider></HelmetProvider></ErrorBoundary>;
}
export default App;
