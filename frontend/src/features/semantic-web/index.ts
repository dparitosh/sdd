// Semantic-web feature barrel

// ── Components ─────────────────────────────────────────────────
export { default as OntologyManager } from './components/OntologyManager';
export { default as OSLCBrowser } from './components/OSLCBrowser';
export { default as SHACLValidator } from './components/SHACLValidator';
export { default as GraphQLPlayground } from './components/GraphQLPlayground';
export { default as TRSFeed } from './components/TRSFeed';
export { default as ExpressExplorer } from './components/ExpressExplorer';
export { default as RDFExporter } from './components/RDFExporter';

// ── Hooks ──────────────────────────────────────────────────────
export { useOSLC } from './hooks/useOSLC';
export { useOntology } from './hooks/useOntology';
export { useSHACL } from './hooks/useSHACL';
