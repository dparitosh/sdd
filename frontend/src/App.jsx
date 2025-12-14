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
import { QUERY_CONFIG } from '@/constants';import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";

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
  // Initialize WebSocket connection for real-time updates (optional)
  const { connected } = useWebSocket(true);

  // Log connection status only when connected
  useEffect(() => {
    if (connected) {
      logger.log('✓ WebSocket connected - real-time updates enabled');
    }
  }, [connected]);

  return (/*#__PURE__*/
    _jsx(Router, { children: /*#__PURE__*/
      _jsxs(Routes, { children: [/*#__PURE__*/

        _jsx(Route, { path: "/login", element: /*#__PURE__*/_jsx(Login, {}) }), /*#__PURE__*/
        _jsx(Route, { path: "/auth/callback", element: /*#__PURE__*/_jsx(AuthCallback, {}) }), /*#__PURE__*/


        _jsx(Route, {
          path: "/*",
          element: /*#__PURE__*/
          _jsx(ProtectedRoute, { children: /*#__PURE__*/
            _jsx(Layout, { children: /*#__PURE__*/
              _jsxs(Routes, { children: [/*#__PURE__*/
                _jsx(Route, { path: "/", element: /*#__PURE__*/_jsx(Navigate, { to: "/dashboard", replace: true }) }), /*#__PURE__*/
                _jsx(Route, { path: "/dashboard", element: /*#__PURE__*/_jsx(ErrorBoundary, { children: /*#__PURE__*/_jsx(Dashboard, {}) }) }), /*#__PURE__*/
                _jsx(Route, { path: "/search", element: /*#__PURE__*/_jsx(ErrorBoundary, { children: /*#__PURE__*/_jsx(AdvancedSearch, {}) }) }), /*#__PURE__*/
                _jsx(Route, { path: "/api-explorer", element: /*#__PURE__*/_jsx(ErrorBoundary, { children: /*#__PURE__*/_jsx(RestApiExplorer, {}) }) }), /*#__PURE__*/
                _jsx(Route, { path: "/query-editor", element: /*#__PURE__*/_jsx(ErrorBoundary, { children: /*#__PURE__*/_jsx(QueryEditor, {}) }) }), /*#__PURE__*/
                _jsx(Route, { path: "/requirements", element: /*#__PURE__*/_jsx(ErrorBoundary, { children: /*#__PURE__*/_jsx(RequirementsManager, {}) }) }), /*#__PURE__*/
                _jsx(Route, { path: "/traceability", element: /*#__PURE__*/_jsx(ErrorBoundary, { children: /*#__PURE__*/_jsx(TraceabilityMatrix, {}) }) }), /*#__PURE__*/
                _jsx(Route, { path: "/plm", element: /*#__PURE__*/_jsx(ErrorBoundary, { children: /*#__PURE__*/_jsx(PLMIntegration, {}) }) }), /*#__PURE__*/
                _jsx(Route, { path: "/monitoring", element: /*#__PURE__*/_jsx(ErrorBoundary, { children: /*#__PURE__*/_jsx(SystemMonitoring, {}) }) }), /*#__PURE__*/
                _jsx(Route, { path: "/ap239/requirements", element: /*#__PURE__*/_jsx(ErrorBoundary, { children: /*#__PURE__*/_jsx(RequirementsDashboard, {}) }) }), /*#__PURE__*/
                _jsx(Route, { path: "/ap242/parts", element: /*#__PURE__*/_jsx(ErrorBoundary, { children: /*#__PURE__*/_jsx(PartsExplorer, {}) }) }), /*#__PURE__*/
                _jsx(Route, { path: "/graph", element: /*#__PURE__*/_jsx(ErrorBoundary, { children: /*#__PURE__*/_jsx(GraphBrowser, {}) }) }), /*#__PURE__*/
                _jsx(Route, { path: "/import", element: /*#__PURE__*/_jsx(ErrorBoundary, { children: /*#__PURE__*/_jsx(DataImport, {}) }) }), /*#__PURE__*/
                _jsx(Route, { path: "/ai/insights", element: /*#__PURE__*/_jsx(ErrorBoundary, { children: /*#__PURE__*/_jsx(AIInsights, {}) }) }), /*#__PURE__*/
                _jsx(Route, { path: "/ai/analysis", element: /*#__PURE__*/_jsx(ErrorBoundary, { children: /*#__PURE__*/_jsx(SmartAnalysis, {}) }) }), /*#__PURE__*/
                _jsx(Route, { path: "/ai/chat", element: /*#__PURE__*/_jsx(ErrorBoundary, { children: /*#__PURE__*/_jsx(ModelChat, {}) }) }), /*#__PURE__*/
                _jsx(Route, { path: "/simulation/models", element: /*#__PURE__*/_jsx(ErrorBoundary, { children: /*#__PURE__*/_jsx(ModelRepository, {}) }) }), /*#__PURE__*/
                _jsx(Route, { path: "/simulation/workflows", element: /*#__PURE__*/_jsx(ErrorBoundary, { children: /*#__PURE__*/_jsx(WorkflowStudio, {}) }) }), /*#__PURE__*/
                _jsx(Route, { path: "/simulation/results", element: /*#__PURE__*/_jsx(ErrorBoundary, { children: /*#__PURE__*/_jsx(ResultsAnalysis, {}) }) })] }
              ) }
            ) }
          ) }

        )] }
      ) }
    ));

}

function App() {
  return (/*#__PURE__*/
    _jsx(ErrorBoundary, { children: /*#__PURE__*/
      _jsx(HelmetProvider, { children: /*#__PURE__*/
        _jsx(ThemeProvider, { defaultTheme: "system", storageKey: "mbse-ui-theme", children: /*#__PURE__*/
          _jsxs(QueryClientProvider, { client: queryClient, children: [/*#__PURE__*/
            _jsx(AppContent, {}), /*#__PURE__*/
            _jsx(Toaster, {})] }
          ) }
        ) }
      ) }
    ));

}

export default App;
