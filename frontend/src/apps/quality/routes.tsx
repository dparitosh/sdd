import { Route } from 'react-router-dom';
import ErrorBoundary from '@/components/ErrorBoundary';

// Feature: sdd
import DossierList from '@/features/sdd/components/DossierList';
import DossierDetail from '@/features/sdd/components/DossierDetail';

// Feature: telemetry
import Dashboard from '@/features/telemetry/components/Dashboard';
import QualityDashboard from '@/features/telemetry/components/QualityDashboard';

// Feature: systems-engineering
import TraceabilityMatrix from '@/features/systems-engineering/components/TraceabilityMatrix';

// Feature: telemetry
import SystemMonitoring from '@/features/telemetry/components/SystemMonitoring';

/** All child routes for the Quality Head persona. */
export function qualityRoutes() {
  return (
    <>
      {/* Approval Queue — index shows pending dossiers */}
      <Route index element={<ErrorBoundary><DossierList /></ErrorBoundary>} />

      {/* Quality Dashboard */}
      <Route path="dashboard" element={<ErrorBoundary><QualityDashboard /></ErrorBoundary>} />
      <Route path="overview" element={<ErrorBoundary><Dashboard /></ErrorBoundary>} />

      {/* Compliance — audit reports (reuses dossier detail with audit focus) */}
      <Route path="audit" element={<ErrorBoundary><SystemMonitoring /></ErrorBoundary>} />

      {/* Traceability */}
      <Route path="traceability" element={<ErrorBoundary><TraceabilityMatrix /></ErrorBoundary>} />

      {/* Change Feed */}
      <Route path="dossiers" element={<ErrorBoundary><DossierList /></ErrorBoundary>} />
      <Route path="dossiers/:id" element={<ErrorBoundary><DossierDetail /></ErrorBoundary>} />
      <Route path="feed" element={<ErrorBoundary><SystemMonitoring /></ErrorBoundary>} />
    </>
  );
}

export default qualityRoutes;
