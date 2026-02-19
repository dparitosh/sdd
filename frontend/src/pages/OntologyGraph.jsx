import GraphBrowser from '@/pages/GraphBrowser';

export default function OntologyGraph() {
  return (
    <GraphBrowser
      // Expert view: Focus on the metamodel (T-Box)
      fixedNodeTypes={['Ontology', 'OntologyClass', 'OntologyProperty', 'OWLClass', 'OWLProperty']}
      title="Enterprise Ontology — Semantic Metamodel"
      emptyMessage="No semantic definitions found. Ingest OWL/RDF schemas to populate."
    />
  );
}
