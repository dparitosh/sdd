import GraphBrowser from '@/features/graph-explorer/components/GraphBrowser';

export default function AP242Graph() {
  return (
    <GraphBrowser
      apLevel="AP242"
      title="AP242 — Managed Model Based 3D Engineering"
      emptyMessage="No AP242 (CAD/PDM) artifacts found. Ingest STEP or Semantic models to populate."
    />
  );
}
