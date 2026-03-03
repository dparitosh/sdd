import GraphBrowser from '@/features/graph-explorer/components/GraphBrowser';

export default function OntologyGraph() {
  return (
    <GraphBrowser
      initialView="ONTOLOGY"
      fixedNodeTypes={['Ontology', 'OntologyClass', 'OntologyProperty', 'OWLClass', 'OWLProperty']}
      title="Enterprise Ontology — Semantic Metamodel"
      emptyMessage="No semantic definitions found. Ingest OWL/RDF schemas to populate."
    />
  );
}
