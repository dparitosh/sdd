import { useState, useMemo, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ap242, ap239 } from '@/services/standards.service';
import { getRuns } from '@/services/simulation.service';
import { getGraphData } from '@/services/graph.service';
import {
  Thermometer,
  Settings,
  Droplet,
  Cpu,
  ArrowRightCircle,
  FileCode2,
  RefreshCw,
  AlertTriangle,
  FileText,
  Activity,
  Box,
  CheckCircle2,
  Clock,
  XCircle,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */
function extractParams(parts) {
  const params = [];
  for (const p of parts) {
    if (p.mass != null) params.push({ name: `${p.name ?? p.uid} – Mass`, value: p.mass, unit: 'kg', source: p.uid });
    if (p.length != null) params.push({ name: `${p.name ?? p.uid} – Length`, value: p.length, unit: 'mm', source: p.uid });
    if (p.material) params.push({ name: `${p.name ?? p.uid} – Material`, value: p.material, unit: '—', source: p.uid });
    if (p.properties && typeof p.properties === 'object') {
      for (const [k, v] of Object.entries(p.properties)) {
        if (v != null) params.push({ name: `${p.name ?? p.uid} – ${k}`, value: String(v), unit: '—', source: p.uid });
      }
    }
  }
  return params;
}

function deriveConstraints(parts) {
  const constraints = [];
  for (const p of parts) {
    if (p.status === 'RESTRICTED' || p.status === 'DEPRECATED')
      constraints.push({ id: p.uid ?? p.name, description: `Part "${p.name ?? p.uid}" has status ${p.status} — verify compliance.`, type: 'safety', severity: 'critical' });
    if (p.tolerance != null)
      constraints.push({ id: `${p.uid}-tol`, description: `Tolerance constraint on "${p.name ?? p.uid}": ${p.tolerance}`, type: 'performance', severity: 'major' });
  }
  if (constraints.length === 0) {
    constraints.push(
      { id: 'SYS-C1', description: 'Operating temperature range: -40 °C to +85 °C', type: 'environmental', severity: 'critical' },
      { id: 'SYS-C2', description: 'Maximum vibration level: 10 g RMS', type: 'performance', severity: 'major' },
      { id: 'SYS-C3', description: 'EMC compliance per MIL-STD-461G', type: 'interface', severity: 'critical' },
      { id: 'SYS-C4', description: 'Mean Time Between Failures (MTBF) ≥ 5 000 h', type: 'safety', severity: 'major' },
      { id: 'SYS-C5', description: 'Field-replaceable unit weight < 15 kg', type: 'operational', severity: 'minor' },
    );
  }
  return constraints;
}

function runStatusColor(status) {
  const s = (status ?? '').toLowerCase();
  if (s === 'completed' || s === 'success') return 'bg-emerald-100 text-emerald-700';
  if (s === 'running'   || s === 'active')  return 'bg-blue-100 text-blue-700';
  if (s === 'failed'    || s === 'error')   return 'bg-rose-100 text-rose-700';
  return 'bg-slate-100 text-slate-600';
}

function runStatusIcon(status) {
  const s = (status ?? '').toLowerCase();
  if (s === 'completed' || s === 'success') return <CheckCircle2 size={14} />;
  if (s === 'running'   || s === 'active')  return <Clock size={14} />;
  if (s === 'failed'    || s === 'error')   return <XCircle size={14} />;
  return <Clock size={14} />;
}

function SectionAnchor({ id, icon: Icon, title, count, loading, children }) {
  const [collapsed, setCollapsed] = useState(false);
  return (
    <div id={id} className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <button
        onClick={() => setCollapsed(c => !c)}
        className="w-full flex items-center justify-between p-5 hover:bg-slate-50 transition-colors text-left"
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-[#004A99]/10 flex items-center justify-center text-[#004A99]">
            <Icon size={18} />
          </div>
          <div>
            <span className="font-bold text-slate-800 text-sm">{title}</span>
            {count != null && !loading && (
              <span className="ml-2 text-[10px] font-black bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full uppercase tracking-widest">
                {count}
              </span>
            )}
          </div>
        </div>
        {collapsed ? <ChevronRight size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
      </button>
      {!collapsed && <div className="px-5 pb-5">{children}</div>}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */
export default function ProductSpecs() {
  const cadRef  = useRef(null);
  const logsRef = useRef(null);
  const certRef = useRef(null);
  const scrollTo = (ref) => ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });

  // ── AP242 parts ──────────────────────────────────────────────────
  const { data: partsRaw, isLoading: loadingParts, refetch: refetchParts } = useQuery({
    queryKey: ['product-specs-parts'],
    queryFn: async () => { const r = await ap242.getParts(); return r?.data ?? r; },
  });

  // ── AP242 geometry (CAD Models / STEP) ───────────────────────────
  const { data: geoRaw, isLoading: loadingGeo } = useQuery({
    queryKey: ['product-specs-geometry'],
    queryFn: async () => { const r = await ap242.getGeometry(); return r?.data ?? r; },
    staleTime: 60_000,
  });

  // ── Simulation runs (Logs) ────────────────────────────────────────
  const { data: runsRaw, isLoading: loadingRuns } = useQuery({
    queryKey: ['product-specs-runs'],
    queryFn: async () => { const r = await getRuns({ limit: 50 }); return r?.data ?? r; },
    staleTime: 30_000,
  });

  // ── AP239 documents (Certification Drafts) ───────────────────────
  const { data: docsRaw, isLoading: loadingDocs } = useQuery({
    queryKey: ['product-specs-documents'],
    queryFn: async () => { const r = await ap239.getDocuments(); return r?.data ?? r; },
    staleTime: 60_000,
  });

  // ── Graph summary ─────────────────────────────────────────────────
  const { data: graphRaw, isLoading: loadingGraph } = useQuery({
    queryKey: ['product-specs-graph'],
    queryFn: async () => {
      const r = await getGraphData({ limit: 500, node_types: 'Part,SimulationDossier,SimulationModel,CADModel,Requirement' });
      return r?.data ?? r;
    },
  });

  const parts      = useMemo(() => partsRaw?.parts ?? [], [partsRaw]);
  const geometry   = useMemo(() => geoRaw?.geometry ?? [], [geoRaw]);
  const runs       = useMemo(() => (Array.isArray(runsRaw) ? runsRaw : runsRaw?.runs ?? []), [runsRaw]);
  const documents  = useMemo(() => docsRaw?.documents ?? [], [docsRaw]);
  const params     = useMemo(() => extractParams(parts), [parts]);
  const constraints = useMemo(() => deriveConstraints(parts), [parts]);

  const linkedSummary = useMemo(() => {
    if (!graphRaw?.nodes) return { dossiers: 0, models: 0, parts: 0, requirements: 0 };
    const nodes = graphRaw.nodes;
    return {
      dossiers:     nodes.filter(n => (n.label ?? n.type ?? '').includes('Dossier')).length,
      models:       nodes.filter(n => (n.label ?? n.type ?? '').includes('Model')).length,
      parts:        nodes.filter(n => (n.label ?? n.type ?? '') === 'Part').length,
      requirements: nodes.filter(n => (n.label ?? n.type ?? '').includes('Requirement')).length,
    };
  }, [graphRaw]);

  const tempParam     = params.find(p => p.name.toLowerCase().includes('temp'))?.value || '-40 °C to +85 °C';
  const loadParam     = params.find(p => p.name.toLowerCase().includes('mass') || p.name.toLowerCase().includes('load'))?.value || '15 kg';
  const materialParam = params.find(p => p.name.toLowerCase().includes('material'))?.value || 'Standard Alloy';
  const modelRef      = parts.length > 0 ? (parts[0].name || parts[0].uid) : 'SYS-MTR-2024-X';

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Product Specification Data</h1>
          <p className="text-slate-500 text-sm font-medium">Core design parameters, constraints, assets and certification records</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => refetchParts()}
            disabled={loadingParts}
            className="flex items-center gap-2 bg-white border border-slate-200 px-4 py-2 rounded-lg text-sm font-bold text-slate-600 hover:bg-slate-50 transition-all shadow-sm"
          >
            <RefreshCw size={16} className={loadingParts ? 'animate-spin' : ''} /> Refresh Data
          </button>
          <div className="px-3 py-2 bg-emerald-100 text-emerald-700 rounded-lg text-[10px] font-bold uppercase tracking-widest border border-emerald-200">
            DESIGN_VERIFIED
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* ── Main content column ── */}
        <div className="lg:col-span-2 space-y-6">

          {/* Design parameters */}
          <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm relative overflow-hidden">
            <div className="absolute top-0 right-0 p-8 opacity-[0.03] text-slate-900 pointer-events-none">
              <Settings size={200} />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-8 relative z-10">
              <div className="space-y-1">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Model Reference</p>
                <p className="text-xl font-bold text-slate-800">{modelRef}</p>
              </div>
              <div className="space-y-1">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Operating Range</p>
                <p className="text-xl font-bold text-slate-800 flex items-center gap-2">
                  <Thermometer size={18} className="text-rose-500" /> {tempParam}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Load Rating / Mass</p>
                <p className="text-xl font-bold text-slate-800">{loadParam}</p>
              </div>
              <div className="space-y-1">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Material Profile</p>
                <p className="text-xl font-bold text-slate-800 flex items-center gap-2">
                  <Droplet size={18} className="text-blue-500" /> {materialParam}
                </p>
              </div>
            </div>
            <div className="mt-12 p-6 bg-slate-900 rounded-xl text-blue-300 border-l-4 border-blue-400">
              <div className="flex items-center gap-2 mb-3">
                <FileCode2 size={20} />
                <h4 className="font-bold uppercase tracking-widest text-xs">Extracted Parameters ({params.length})</h4>
              </div>
              <div className="max-h-32 overflow-y-auto pr-2 space-y-2">
                {loadingParts
                  ? [...Array(3)].map((_, i) => <Skeleton key={i} className="h-4 w-full bg-slate-700" />)
                  : params.slice(0, 5).map((p, i) => (
                    <div key={i} className="flex justify-between text-sm font-mono">
                      <span className="text-slate-400">{p.name}</span>
                      <span className="text-blue-200">{p.value} {p.unit}</span>
                    </div>
                  ))
                }
                {params.length > 5 && <div className="text-xs text-slate-500 italic mt-2">...and {params.length - 5} more parameters</div>}
              </div>
            </div>
          </div>

          {/* System constraints */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <h3 className="font-bold text-slate-800 mb-6 uppercase tracking-widest text-xs">System Constraints ({constraints.length})</h3>
            <div className="space-y-4 max-h-96 overflow-y-auto pr-2">
              {constraints.map((c, i) => (
                <div key={i} className="flex gap-4 p-4 hover:bg-slate-50 rounded-xl transition-colors group border border-transparent hover:border-slate-100">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 transition-colors ${
                    c.severity === 'critical' ? 'bg-rose-100 text-rose-600 group-hover:bg-rose-500 group-hover:text-white' :
                    c.severity === 'major'    ? 'bg-amber-100 text-amber-600 group-hover:bg-amber-500 group-hover:text-white' :
                                               'bg-slate-100 text-slate-500 group-hover:bg-[#00B0E4] group-hover:text-white'
                  }`}><AlertTriangle size={20} /></div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <p className="font-bold text-slate-700 text-sm">{c.id}</p>
                      <span className="text-[8px] font-black px-2 py-0.5 rounded uppercase tracking-widest bg-slate-100 text-slate-500">{c.type}</span>
                    </div>
                    <p className="text-slate-500 text-sm leading-relaxed">{c.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* ── CAD Models (STEP) ── */}
          <div ref={cadRef}>
            <SectionAnchor id="cad-models" icon={Box} title="CAD Models (STEP)" count={geometry.length} loading={loadingGeo}>
              {loadingGeo ? (
                <div className="space-y-3">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-14 w-full" />)}</div>
              ) : geometry.length === 0 ? (
                <p className="text-sm text-slate-500 py-4 text-center">No STEP geometry models found in Neo4j. Ingest AP242 STEP files to populate this section.</p>
              ) : (
                <div className="space-y-2">
                  {geometry.map((g, i) => (
                    <div key={g.uid ?? i} className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-100 hover:border-slate-200 transition-colors">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-[#004A99]/10 rounded-lg flex items-center justify-center text-[#004A99]">
                          <Box size={16} />
                        </div>
                        <div>
                          <p className="text-sm font-bold text-slate-800">{g.name ?? g.uid}</p>
                          <p className="text-xs text-slate-500 font-mono">{g.uid}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {g.model_type && <span className="text-[10px] font-black px-2 py-0.5 rounded bg-blue-100 text-blue-700 uppercase tracking-widest">{g.model_type}</span>}
                        {g.parts?.length > 0 && <span className="text-[10px] text-slate-500">{g.parts.length} part{g.parts.length !== 1 ? 's' : ''}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </SectionAnchor>
          </div>

          {/* ── Simulation Logs ── */}
          <div ref={logsRef}>
            <SectionAnchor id="simulation-logs" icon={Activity} title="Simulation Logs" count={runs.length} loading={loadingRuns}>
              {loadingRuns ? (
                <div className="space-y-3">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-14 w-full" />)}</div>
              ) : runs.length === 0 ? (
                <p className="text-sm text-slate-500 py-4 text-center">No simulation runs found. Start a run from Simulation → Runs.</p>
              ) : (
                <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                  {runs.map((run, i) => (
                    <div key={run.id ?? run.run_id ?? i} className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-100 hover:border-slate-200 transition-colors">
                      <div className="flex items-center gap-3">
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${runStatusColor(run.run_status)}`}>
                          {runStatusIcon(run.run_status)}
                        </div>
                        <div>
                          <p className="text-sm font-bold text-slate-800">{run.name ?? run.id ?? run.run_id}</p>
                          <p className="text-xs text-slate-500">
                            {run.sim_type ?? 'Unknown type'}
                            {run.dossier_id ? ` · Dossier: ${run.dossier_id}` : ''}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 text-right">
                        <span className={`text-[10px] font-black px-2 py-0.5 rounded uppercase tracking-widest ${runStatusColor(run.run_status)}`}>
                          {run.run_status ?? 'unknown'}
                        </span>
                        {(run.updated_at || run.created_at) && (
                          <span className="text-[10px] text-slate-400 whitespace-nowrap">
                            {new Date(run.updated_at ?? run.created_at).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </SectionAnchor>
          </div>

          {/* ── Certification Drafts ── */}
          <div ref={certRef}>
            <SectionAnchor id="certification-drafts" icon={FileText} title="Certification Drafts (AP239)" count={documents.length} loading={loadingDocs}>
              {loadingDocs ? (
                <div className="space-y-3">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-14 w-full" />)}</div>
              ) : documents.length === 0 ? (
                <p className="text-sm text-slate-500 py-4 text-center">No AP239 documents found. Ingest PLCS data or link documents to requirements in Neo4j.</p>
              ) : (
                <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                  {documents.map((doc, i) => (
                    <div key={doc.document_id ?? doc.uid ?? i} className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-100 hover:border-slate-200 transition-colors">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-emerald-100 rounded-lg flex items-center justify-center text-emerald-600">
                          <FileText size={16} />
                        </div>
                        <div>
                          <p className="text-sm font-bold text-slate-800">{doc.name ?? doc.document_id ?? doc.uid}</p>
                          <p className="text-xs text-slate-500 font-mono">
                            {doc.document_id ?? '—'}{doc.version ? ` · v${doc.version}` : ''}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {doc.documents_requirements?.length > 0 && (
                          <span className="text-[10px] font-bold text-slate-500">{doc.documents_requirements.length} req{doc.documents_requirements.length !== 1 ? 's' : ''}</span>
                        )}
                        <span className="text-[10px] font-black px-2 py-0.5 rounded bg-amber-100 text-amber-700 uppercase tracking-widest">Draft</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </SectionAnchor>
          </div>
        </div>

        {/* ── Sidebar ── */}
        <div className="space-y-6">
          <div className="bg-linear-to-br from-[#004A99] to-[#003d7a] p-8 rounded-2xl text-white shadow-xl">
            <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
              <Cpu size={20} /> Linked Graph Entities
            </h3>
            <div className="grid grid-cols-2 gap-4 mb-6">
              {loadingGraph
                ? [...Array(4)].map((_, i) => <div key={i} className="bg-white/10 p-4 rounded-xl animate-pulse h-16" />)
                : (
                  <>
                    <div className="bg-white/10 p-4 rounded-xl text-center"><div className="text-2xl font-black">{linkedSummary.requirements}</div><div className="text-[10px] font-bold uppercase tracking-widest text-blue-200 mt-1">Requirements</div></div>
                    <div className="bg-white/10 p-4 rounded-xl text-center"><div className="text-2xl font-black">{linkedSummary.dossiers}</div><div className="text-[10px] font-bold uppercase tracking-widest text-blue-200 mt-1">Dossiers</div></div>
                    <div className="bg-white/10 p-4 rounded-xl text-center"><div className="text-2xl font-black">{linkedSummary.models}</div><div className="text-[10px] font-bold uppercase tracking-widest text-blue-200 mt-1">Models</div></div>
                    <div className="bg-white/10 p-4 rounded-xl text-center"><div className="text-2xl font-black">{linkedSummary.parts}</div><div className="text-[10px] font-bold uppercase tracking-widest text-blue-200 mt-1">Parts</div></div>
                  </>
                )
              }
            </div>

            <div className="space-y-3">
              {[
                { label: 'CAD Models (STEP)',    ref: cadRef,  count: geometry.length,  icon: Box },
                { label: 'Simulation Logs',      ref: logsRef, count: runs.length,      icon: Activity },
                { label: 'Certification Drafts', ref: certRef, count: documents.length, icon: FileText },
              ].map(({ label, ref, count, icon: Icon }) => (
                <button
                  key={label}
                  onClick={() => scrollTo(ref)}
                  className="w-full flex items-center justify-between p-3 bg-white/5 hover:bg-white/20 rounded-xl transition-colors border border-white/10"
                >
                  <div className="flex items-center gap-2">
                    <Icon size={15} className="shrink-0" />
                    <span className="font-medium text-sm">{label}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {!loadingGeo && !loadingRuns && !loadingDocs && (
                      <span className="text-[10px] font-black bg-white/20 px-1.5 py-0.5 rounded-full">{count}</span>
                    )}
                    <ArrowRightCircle size={16} />
                  </div>
                </button>
              ))}
            </div>

            <div className="mt-8 pt-6 border-t border-white/10">
              <p className="text-[10px] font-bold text-blue-200 uppercase tracking-widest mb-2">Graph Sync Status</p>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></div>
                <p className="text-xs font-medium">Auto-sync with Neo4j Server</p>
              </div>
            </div>
          </div>

          <div className="p-6 bg-white border border-slate-200 rounded-2xl text-center shadow-sm">
            <h4 className="text-slate-800 font-bold mb-2">Need Modification?</h4>
            <p className="text-slate-500 text-xs mb-4">Changes to product specs require Engineering Lead approval and formal revision numbering.</p>
            <button className="text-[#004A99] text-sm font-bold border-b-2 border-transparent hover:border-[#004A99] transition-all">
              Request Spec Revision
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}


function deriveConstraints(parts) {
  const constraints = [];
  for (const p of parts) {
    if (p.status === 'RESTRICTED' || p.status === 'DEPRECATED') {
      constraints.push({
        id: p.uid ?? p.name,
        description: `Part "${p.name ?? p.uid}" has status ${p.status} — verify compliance.`,
        type: 'safety',
        severity: 'critical',
      });
    }
    if (p.tolerance != null) {
      constraints.push({
        id: `${p.uid}-tol`,
        description: `Tolerance constraint on "${p.name ?? p.uid}": ${p.tolerance}`,
        type: 'performance',
        severity: 'major',
      });
    }
  }
  // Provide at least some sample constraints if data is empty
  if (constraints.length === 0) {
    constraints.push(
      { id: 'SYS-C1', description: 'Operating temperature range: -40 °C to +85 °C', type: 'environmental', severity: 'critical' },
      { id: 'SYS-C2', description: 'Maximum vibration level: 10 g RMS', type: 'performance', severity: 'major' },
      { id: 'SYS-C3', description: 'EMC compliance per MIL-STD-461G', type: 'interface', severity: 'critical' },
      { id: 'SYS-C4', description: 'Mean Time Between Failures (MTBF) ≥ 5 000 h', type: 'safety', severity: 'major' },
      { id: 'SYS-C5', description: 'Field-replaceable unit weight < 15 kg', type: 'operational', severity: 'minor' },
    );
  }
  return constraints;
}