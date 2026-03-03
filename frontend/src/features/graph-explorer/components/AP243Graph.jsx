import GraphBrowser from '@/features/graph-explorer/components/GraphBrowser';

export default function AP243Graph() {
  return (
    <GraphBrowser
      initialView="AP243"
      apLevel="AP243"
      title="AP243 — MoSSEC (Simulation & Analysis)"
      emptyMessage="No AP243 (MoSSEC) contexts found. Import simulation studies to populate."
    />
  );
}
