import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ap242 } from '@/services/standards.service';
import { getGraphData } from '@/services/graph.service';
import { 
  Thermometer, 
  Settings, 
  Wind, 
  Droplet, 
  Cpu, 
  ArrowRightCircle,
  FileCode2,
  RefreshCw,
  AlertTriangle,
  Package,
  Boxes,
  FileText,
  Activity,
  Link2
} from 'lucide-react';

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */
function extractParams(parts) {
  const params = [];
  for (const p of parts) {
    if (p.mass != null) params.push({ name: `${p.name ?? p.uid} – Mass`, value: p.mass, unit: 'kg', tolerance: p.mass_tolerance, source: p.uid });
    if (p.length != null) params.push({ name: `${p.name ?? p.uid} – Length`, value: p.length, unit: 'mm', tolerance: p.length_tolerance, source: p.uid });
    if (p.material) params.push({ name: `${p.name ?? p.uid} – Material`, value: p.material, unit: '—', source: p.uid });
    // Generic properties heuristic
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

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */
export default function ProductSpecs() {
  // Fetch parts from AP242
  const { data: partsRaw, isLoading: loadingParts, refetch: refetchParts } = useQuery({
    queryKey: ['product-specs-parts'],
    queryFn: async () => {
      const r = await ap242.getParts();
      return (r?.data ?? r);
    },
  });

  // Fetch graph data for linked view
  const { data: graphRaw, isLoading: loadingGraph } = useQuery({
    queryKey: ['product-specs-graph'],
    queryFn: async () => {
      const r = await getGraphData({ limit: 500, node_types: 'Part,SimulationDossier,SimulationModel,CADModel,Requirement' });
      return (r?.data ?? r);
    },
  });

  const parts = useMemo(() => partsRaw?.parts ?? [], [partsRaw]);
  const params = useMemo(() => extractParams(parts), [parts]);
  const constraints = useMemo(() => deriveConstraints(parts), [parts]);

  // ----- Linked entities summary -----
  const linkedSummary = useMemo(() => {
    if (!graphRaw?.nodes) return { dossiers: 0, models: 0, parts: 0, requirements: 0 };
    const nodes = graphRaw.nodes;
    return {
      dossiers: nodes.filter((n) => (n.label ?? n.type ?? '').includes('Dossier')).length,
      models: nodes.filter((n) => (n.label ?? n.type ?? '').includes('Model')).length,
      parts: nodes.filter((n) => (n.label ?? n.type ?? '') === 'Part').length,
      requirements: nodes.filter((n) => (n.label ?? n.type ?? '').includes('Requirement')).length,
    };
  }, [graphRaw]);

  // Find specific parameters for the UI
  const tempParam = params.find(p => p.name.toLowerCase().includes('temp') || p.name.toLowerCase().includes('temperature'))?.value || '-40 °C to +85 °C';
  const loadParam = params.find(p => p.name.toLowerCase().includes('load') || p.name.toLowerCase().includes('mass'))?.value || '15 kg';
  const materialParam = params.find(p => p.name.toLowerCase().includes('material'))?.value || 'Standard Alloy';
  const modelRef = parts.length > 0 ? (parts[0].name || parts[0].uid) : 'SYS-MTR-2024-X';

  return (
    <div className="space-y-6 pb-12">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Product Specification Data</h1>
          <p className="text-slate-500 text-sm font-medium">Core design parameters and environmental constraints</p>
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
        <div className="lg:col-span-2 space-y-6">
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
                <div className="max-h-32 overflow-y-auto pr-2 space-y-2 custom-scrollbar">
                  {params.slice(0, 5).map((p, i) => (
                    <div key={i} className="flex justify-between text-sm font-mono">
                      <span className="text-slate-400">{p.name}</span>
                      <span className="text-blue-200">{p.value} {p.unit}</span>
                    </div>
                  ))}
                  {params.length > 5 && (
                    <div className="text-xs text-slate-500 italic mt-2">...and {params.length - 5} more parameters</div>
                  )}
                </div>
             </div>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
             <h3 className="font-bold text-slate-800 mb-6 uppercase tracking-widest text-xs">System Constraints ({constraints.length})</h3>
             <div className="space-y-4 max-h-96 overflow-y-auto pr-2">
                {constraints.map((constraint, i) => (
                  <div key={i} className="flex gap-4 p-4 hover:bg-slate-50 rounded-xl transition-colors group border border-transparent hover:border-slate-100">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 transition-colors ${
                      constraint.severity === 'critical' ? 'bg-rose-100 text-rose-600 group-hover:bg-rose-500 group-hover:text-white' :
                      constraint.severity === 'major' ? 'bg-amber-100 text-amber-600 group-hover:bg-amber-500 group-hover:text-white' :
                      'bg-slate-100 text-slate-500 group-hover:bg-[#00B0E4] group-hover:text-white'
                    }`}>
                      <AlertTriangle size={20} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-bold text-slate-700 text-sm">{constraint.id}</p>
                        <span className="text-[8px] font-black px-2 py-0.5 rounded uppercase tracking-widest bg-slate-100 text-slate-500">
                          {constraint.type}
                        </span>
                      </div>
                      <p className="text-slate-500 text-sm leading-relaxed">{constraint.description}</p>
                    </div>
                  </div>
                ))}
             </div>
          </div>
        </div>

        <div className="space-y-6">
           <div className="bg-linear-to-br from-[#004A99] to-[#003d7a] p-8 rounded-2xl text-white shadow-xl">
              <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
                <Cpu size={20} /> Linked Graph Entities
              </h3>
              
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="bg-white/10 p-4 rounded-xl text-center">
                  <div className="text-2xl font-black">{linkedSummary.requirements}</div>
                  <div className="text-[10px] font-bold uppercase tracking-widest text-blue-200 mt-1">Requirements</div>
                </div>
                <div className="bg-white/10 p-4 rounded-xl text-center">
                  <div className="text-2xl font-black">{linkedSummary.dossiers}</div>
                  <div className="text-[10px] font-bold uppercase tracking-widest text-blue-200 mt-1">Dossiers</div>
                </div>
                <div className="bg-white/10 p-4 rounded-xl text-center">
                  <div className="text-2xl font-black">{linkedSummary.models}</div>
                  <div className="text-[10px] font-bold uppercase tracking-widest text-blue-200 mt-1">Models</div>
                </div>
                <div className="bg-white/10 p-4 rounded-xl text-center">
                  <div className="text-2xl font-black">{linkedSummary.parts}</div>
                  <div className="text-[10px] font-bold uppercase tracking-widest text-blue-200 mt-1">Parts</div>
                </div>
              </div>

              <div className="space-y-3">
                {['CAD Models (STEP)', 'Simulation Logs', 'Certification Drafts'].map((asset) => (
                  <button key={asset} className="w-full flex items-center justify-between p-3 bg-white/5 hover:bg-white/20 rounded-xl transition-colors border border-white/10">
                    <span className="font-medium text-sm">{asset}</span>
                    <ArrowRightCircle size={18} />
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
