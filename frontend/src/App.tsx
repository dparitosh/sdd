import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from '@ui/sonner';
import { ThemeProvider } from '@/components/theme-provider';
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

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function App() {
  return (
    <ThemeProvider defaultTheme="system" storageKey="mbse-ui-theme">
      <QueryClientProvider client={queryClient}>
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
                      <Route path="/dashboard" element={<Dashboard />} />
                      <Route path="/search" element={<AdvancedSearch />} />
                      <Route path="/api-explorer" element={<RestApiExplorer />} />
                      <Route path="/query-editor" element={<QueryEditor />} />
                      <Route path="/requirements" element={<RequirementsManager />} />
                      <Route path="/traceability" element={<TraceabilityMatrix />} />
                      <Route path="/plm" element={<PLMIntegration />} />
                      <Route path="/monitoring" element={<SystemMonitoring />} />
                    </Routes>
                  </Layout>
                </ProtectedRoute>
              }
            />
          </Routes>
        </Router>
        <Toaster />
      </QueryClientProvider>
    </ThemeProvider>
  );
}

export default App;
