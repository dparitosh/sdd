import { Route } from 'react-router-dom';
import ErrorBoundary from '@/components/ErrorBoundary';

// Feature: telemetry
import SystemMonitoring from '@/features/telemetry/components/SystemMonitoring';

// Feature: system-management
import DataImport from '@/features/system-management/components/DataImport';
import RestApiExplorer from '@/features/system-management/components/RestApiExplorer';
import QueryEditor from '@/features/system-management/components/QueryEditor';
import PLMIntegration from '@/features/system-management/components/PLMIntegration';
import AdvancedSearch from '@/features/system-management/components/AdvancedSearch';

// Feature: graph-explorer
import GraphBrowser from '@/features/graph-explorer/components/GraphBrowser';

// Feature: semantic-web
import OntologyManager from '@/features/semantic-web/components/OntologyManager';
import GraphQLPlayground from '@/features/semantic-web/components/GraphQLPlayground';
import ExpressExplorer from '@/features/semantic-web/components/ExpressExplorer';
import OSLCBrowser from '@/features/semantic-web/components/OSLCBrowser';

/** All child routes for the System Administrator persona. */
export function adminRoutes() {
  return (
    <>
      {/* System Health — index */}
      <Route index element={<ErrorBoundary><SystemMonitoring /></ErrorBoundary>} />

      {/* Data Import */}
      <Route path="import" element={<ErrorBoundary><DataImport /></ErrorBoundary>} />

      {/* Graph Explorer */}
      <Route path="graph" element={<ErrorBoundary><GraphBrowser /></ErrorBoundary>} />
      <Route path="query-editor" element={<ErrorBoundary><QueryEditor /></ErrorBoundary>} />

      {/* API & PLM */}
      <Route path="api-explorer" element={<ErrorBoundary><RestApiExplorer /></ErrorBoundary>} />
      <Route path="plm" element={<ErrorBoundary><PLMIntegration /></ErrorBoundary>} />

      {/* Search */}
      <Route path="search" element={<ErrorBoundary><AdvancedSearch /></ErrorBoundary>} />

      {/* Semantic Web */}
      <Route path="semantic/ontology" element={<ErrorBoundary><OntologyManager /></ErrorBoundary>} />
      <Route path="semantic/graphql" element={<ErrorBoundary><GraphQLPlayground /></ErrorBoundary>} />
      <Route path="semantic/express" element={<ErrorBoundary><ExpressExplorer /></ErrorBoundary>} />
      <Route path="semantic/oslc" element={<ErrorBoundary><OSLCBrowser /></ErrorBoundary>} />
    </>
  );
}

export default adminRoutes;
