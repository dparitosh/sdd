import GraphBrowser from '@/features/graph-explorer/components/GraphBrowser';

export default function OSLCGraph() {
  return (
    <GraphBrowser
      // Expert view: Focus on the Linked Data Services (L-Box / Integration)
      fixedNodeTypes={['ServiceProvider', 'Service', 'Catalog', 'CreationFactory', 'QueryCapability', 'Link', 'ExternalModel']}
      title="OSLC — Linked Data & Integration Services"
      emptyMessage="No OSLC services or linked resources found. Configure OSLC Connectors to populate."
    />
  );
}
