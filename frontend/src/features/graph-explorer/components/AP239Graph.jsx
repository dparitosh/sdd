import GraphBrowser from '@/features/graph-explorer/components/GraphBrowser';

export default function AP239Graph() {
  return (
    <GraphBrowser
      apLevel="AP239"
      title="AP239 — Product Life Cycle Support (PLCS)"
      emptyMessage="No AP239 (PLCS) artifacts found. Ingest PLCS XML or RDF to populate."
    />
  );
}
