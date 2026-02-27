import { Route } from 'react-router-dom';
import ErrorBoundary from '@/components/ErrorBoundary';

// Feature: telemetry
import Dashboard from '@/features/telemetry/components/Dashboard';
import DashboardEngineer from '@/features/telemetry/components/DashboardEngineer';
import MossecDashboard from '@/features/telemetry/components/MossecDashboard';

// Feature: system-management
import AdvancedSearch from '@/features/system-management/components/AdvancedSearch';
import DataImport from '@/features/system-management/components/DataImport';
import PLMIntegration from '@/features/system-management/components/PLMIntegration';

// Feature: systems-engineering
import RequirementsManager from '@/features/systems-engineering/components/RequirementsManager';
import RequirementsDashboard from '@/features/systems-engineering/components/RequirementsDashboard';
import TraceabilityMatrix from '@/features/systems-engineering/components/TraceabilityMatrix';
import PartsExplorer from '@/features/systems-engineering/components/PartsExplorer';
import ProductSpecs from '@/features/systems-engineering/components/ProductSpecs';

// Feature: graph-explorer
import GraphBrowser from '@/features/graph-explorer/components/GraphBrowser';

// Feature: ai-studio
import AIInsights from '@/features/ai-studio/components/AIInsights';
import SmartAnalysis from '@/features/ai-studio/components/SmartAnalysis';
import ModelChat from '@/features/ai-studio/components/ModelChat';

// Feature: simulation
import ModelRepository from '@/features/simulation/components/ModelRepository';
import WorkflowStudio from '@/features/simulation/components/WorkflowStudio';
import ResultsAnalysis from '@/features/simulation/components/ResultsAnalysis';
import SimulationRuns from '@/features/simulation/components/SimulationRuns';
import SimulationWorkspace from '@/features/simulation/components/SimulationWorkspace';
import SimulationRunDetail from '@/features/simulation/components/SimulationRunDetail';

// Feature: sdd
import DossierList from '@/features/sdd/components/DossierList';
import DossierDetail from '@/features/sdd/components/DossierDetail';

// Feature: semantic-web
import OntologyManager from '@/features/semantic-web/components/OntologyManager';
import OSLCBrowser from '@/features/semantic-web/components/OSLCBrowser';
import SHACLValidator from '@/features/semantic-web/components/SHACLValidator';
import GraphQLPlayground from '@/features/semantic-web/components/GraphQLPlayground';
import TRSFeed from '@/features/semantic-web/components/TRSFeed';
import ExpressExplorer from '@/features/semantic-web/components/ExpressExplorer';
import RDFExporter from '@/features/semantic-web/components/RDFExporter';

/** All child routes for the Simulation Engineer persona. */
export function engineerRoutes() {
  return (
    <>
      {/* Dashboard */}
      <Route index element={<ErrorBoundary><Dashboard /></ErrorBoundary>} />
      <Route path="dashboard" element={<ErrorBoundary><DashboardEngineer /></ErrorBoundary>} />
      <Route path="search" element={<ErrorBoundary><AdvancedSearch /></ErrorBoundary>} />

      {/* Simulation */}
      <Route path="simulation/models" element={<ErrorBoundary><ModelRepository /></ErrorBoundary>} />
      <Route path="simulation/runs" element={<ErrorBoundary><SimulationRuns /></ErrorBoundary>} />
      <Route path="simulation/runs/:runId" element={<ErrorBoundary><SimulationRunDetail /></ErrorBoundary>} />
      <Route path="simulation/workflows" element={<ErrorBoundary><WorkflowStudio /></ErrorBoundary>} />
      <Route path="simulation/results" element={<ErrorBoundary><ResultsAnalysis /></ErrorBoundary>} />
      <Route path="workspace" element={<ErrorBoundary><SimulationWorkspace /></ErrorBoundary>} />

      {/* Dossiers */}
      <Route path="simulation/dossiers" element={<ErrorBoundary><DossierList /></ErrorBoundary>} />
      <Route path="simulation/dossiers/:id" element={<ErrorBoundary><DossierDetail /></ErrorBoundary>} />
      <Route path="mossec-dashboard" element={<ErrorBoundary><MossecDashboard /></ErrorBoundary>} />

      {/* Systems Engineering */}
      <Route path="requirements" element={<ErrorBoundary><RequirementsManager /></ErrorBoundary>} />
      <Route path="ap239/requirements" element={<ErrorBoundary><RequirementsDashboard /></ErrorBoundary>} />
      <Route path="traceability" element={<ErrorBoundary><TraceabilityMatrix /></ErrorBoundary>} />
      <Route path="ap242/parts" element={<ErrorBoundary><PartsExplorer /></ErrorBoundary>} />
      <Route path="product-specs" element={<ErrorBoundary><ProductSpecs /></ErrorBoundary>} />

      {/* Graph & Ontology */}
      <Route path="graph" element={<ErrorBoundary><GraphBrowser /></ErrorBoundary>} />

      {/* AI Studio */}
      <Route path="ai/insights" element={<ErrorBoundary><AIInsights /></ErrorBoundary>} />
      <Route path="ai/analysis" element={<ErrorBoundary><SmartAnalysis /></ErrorBoundary>} />
      <Route path="ai/chat" element={<ErrorBoundary><ModelChat /></ErrorBoundary>} />

      {/* Data Management */}
      <Route path="import" element={<ErrorBoundary><DataImport /></ErrorBoundary>} />
      <Route path="plm" element={<ErrorBoundary><PLMIntegration /></ErrorBoundary>} />

      {/* Semantic Web */}
      <Route path="semantic/ontology" element={<ErrorBoundary><OntologyManager /></ErrorBoundary>} />
      <Route path="semantic/oslc" element={<ErrorBoundary><OSLCBrowser /></ErrorBoundary>} />
      <Route path="semantic/shacl" element={<ErrorBoundary><SHACLValidator /></ErrorBoundary>} />
      <Route path="semantic/graphql" element={<ErrorBoundary><GraphQLPlayground /></ErrorBoundary>} />
      <Route path="semantic/trs" element={<ErrorBoundary><TRSFeed /></ErrorBoundary>} />
      <Route path="semantic/express" element={<ErrorBoundary><ExpressExplorer /></ErrorBoundary>} />
      <Route path="semantic/rdf-export" element={<ErrorBoundary><RDFExporter /></ErrorBoundary>} />
    </>
  );
}

export default engineerRoutes;
