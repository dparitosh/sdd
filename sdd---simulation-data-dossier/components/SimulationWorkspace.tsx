
import React, { useState } from 'react';
import { 
  Play, 
  Upload, 
  FileText, 
  CheckCircle, 
  Clock, 
  ShieldCheck, 
  Activity, 
  Fingerprint, 
  Link as LinkIcon, 
  Cpu,
  Search,
  ExternalLink,
  Zap,
  Box,
  Wind,
  Waves,
  Shield,
  Info
} from 'lucide-react';
import { SimulationType, Artifact } from '../types';
import { MOCK_DOSSIERS } from '../constants';

const SimulationWorkspace: React.FC = () => {
  const [activeSim, setActiveSim] = useState<SimulationType>(SimulationType.ELECTROMECHANICAL);
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [logMessages, setLogMessages] = useState<string[]>([]);
  const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null);

  const startSimulation = () => {
    setIsRunning(true);
    setProgress(0);
    setLogMessages(["Initiating ISO 17025 Tool Check...", "Validating Solver License...", "Verifying mesh integrity..."]);
    
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsRunning(false);
          setLogMessages(prev => [...prev, "Simulation Complete.", "Generating Digital Fingerprints (SHA-256)...", "Artifact H1 Traceability Matrix Updated."]);
          return 100;
        }
        if (prev === 40) setLogMessages(prev => [...prev, "Converging EM Fields (IEC 60034 Cl 9)..."]);
        if (prev === 70) setLogMessages(prev => [...prev, "Performing Stress Sensitivity Analysis..."]);
        return prev + 5;
      });
    }, 150);
  };

  const currentArtifacts = MOCK_DOSSIERS[0].artifacts;

  const getIcon = (id: string) => {
    if (id.startsWith('A')) return <Zap size={14} className="text-amber-500" />;
    if (id.startsWith('B')) return <Zap size={14} className="text-emerald-500" />;
    if (id.startsWith('C')) return <Wind size={14} className="text-cyan-500" />;
    if (id.startsWith('D')) return <Waves size={14} className="text-violet-500" />;
    if (id.startsWith('E')) return <Shield size={14} className="text-rose-500" />;
    if (id.startsWith('F')) return <Box size={14} className="text-slate-500" />;
    return <FileText size={14} className="text-blue-500" />;
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Verified Workspace</h1>
          <p className="text-slate-500 text-sm font-medium">Simulation Source Hub (ISO 17025 & MOSSEC)</p>
        </div>
        <button 
          onClick={startSimulation}
          disabled={isRunning}
          className={`flex items-center gap-2 px-6 py-2.5 rounded-lg font-bold text-white transition-all ${
            isRunning ? 'bg-slate-400 cursor-not-allowed' : 'bg-emerald-600 hover:bg-emerald-700 shadow-lg shadow-emerald-200'
          }`}
        >
          <Play size={18} fill="currentColor" /> {isRunning ? 'EXECUTING VERIFIED SOLVER...' : 'RUN VERIFIED SIM'}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm relative overflow-hidden min-h-[400px] flex flex-col">
            <div className="flex justify-between items-center mb-6">
                <h3 className="font-bold text-xs uppercase tracking-widest text-slate-400">Simulation Terminal & Evidence Generator</h3>
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                    <span className="text-[10px] font-bold text-slate-500">QUALIFIED SOLVER: V8.2.1</span>
                </div>
            </div>

            <div className="flex-1 bg-slate-900 rounded-lg p-6 font-mono text-sm text-blue-400 overflow-y-auto max-h-[300px] border-l-4 border-blue-500">
                {logMessages.map((msg, i) => (
                    <div key={i} className="mb-1 flex gap-2">
                        <span className="text-slate-600">[{new Date().toLocaleTimeString()}]</span>
                        <span>{msg}</span>
                    </div>
                ))}
                {isRunning && (
                    <div className="mt-4 flex items-center gap-2 text-white">
                        <Activity size={14} className="animate-spin" /> 
                        <span>Processing block {(progress * 42).toFixed(0)}...</span>
                    </div>
                )}
            </div>

            <div className="mt-6 flex gap-4">
                <div className="flex-1 bg-slate-50 border border-slate-200 rounded-lg p-3 flex items-center gap-3">
                    <Fingerprint className="text-blue-600" size={20} />
                    <div>
                        <p className="text-[10px] font-black text-slate-400 uppercase">Integrity</p>
                        <p className="text-xs font-bold text-slate-700">SHA-256 Validated</p>
                    </div>
                </div>
                <button 
                  className="flex-1 bg-white border-2 border-emerald-100 rounded-lg p-3 flex items-center gap-3 hover:bg-emerald-50 transition-all group relative overflow-hidden"
                  onClick={() => alert("MOSSEC Trace REQ-V1 is active and synchronized with the digital thread repository.")}
                >
                    <div className="absolute top-0 right-0 p-1">
                      <div className="w-2 h-2 bg-emerald-500 rounded-full animate-ping"></div>
                    </div>
                    <LinkIcon className="text-emerald-600 group-hover:scale-110 transition-transform" size={20} />
                    <div className="text-left">
                        <p className="text-[10px] font-black text-slate-400 uppercase flex items-center gap-1">
                          MOSSEC Trace <span className="text-emerald-600 tracking-tighter font-black ml-1">LIVE</span>
                        </p>
                        <p className="text-xs font-bold text-slate-800">Linking Requirement <span className="text-[#004A99] font-black">REQ-V1</span></p>
                    </div>
                    <Info size={14} className="ml-auto text-slate-300 group-hover:text-emerald-600 transition-colors" />
                </button>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center">
              <h3 className="font-bold text-xs uppercase tracking-widest text-slate-400">Dossier Evidence Explorer (A1-F1)</h3>
              <div className="relative">
                <Search size={14} className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400" />
                <input type="text" placeholder="Filter artifacts..." className="pl-8 pr-4 py-1.5 bg-slate-100 border-none rounded text-xs outline-none focus:ring-1 focus:ring-blue-500" />
              </div>
            </div>
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-400 font-black uppercase tracking-widest border-b border-slate-100">
                <tr>
                  <th className="px-6 py-3">Artifact</th>
                  <th className="px-6 py-3">MOSSEC Mapping</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3 text-right">Access</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {currentArtifacts.filter(a => a.id.startsWith('A') || a.id.startsWith('B') || a.id.startsWith('C') || a.id.startsWith('D') || a.id.startsWith('E') || a.id.startsWith('F')).map((art) => (
                  <tr key={art.id} className="hover:bg-slate-50 transition-colors group">
                    <td className="px-6 py-4 font-bold text-slate-700 flex items-center gap-2">
                      {getIcon(art.id)} {art.name}
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-[10px] font-black bg-blue-50 text-blue-600 px-2 py-0.5 rounded border border-blue-100">
                        {art.requirementId || 'UNMAPPED'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="flex items-center gap-1 font-bold text-emerald-600 uppercase">
                        <CheckCircle size={10} /> Valid
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button className="text-[#004A99] font-bold flex items-center gap-1 hover:underline ml-auto">
                        Open <ExternalLink size={12} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-slate-900 text-white p-6 rounded-xl shadow-lg border-t-4 border-blue-500">
              <h3 className="font-bold text-sm mb-4 flex items-center gap-2">
                <ShieldCheck size={18} className="text-[#00B0E4]" /> ISO Compliance Panel
              </h3>
              <div className="space-y-3">
                <div className="p-3 bg-white/5 rounded-lg border border-white/10">
                    <p className="text-[10px] font-black text-slate-400 uppercase mb-1">Dossier Revision</p>
                    <p className="text-sm font-bold">Current: v1.2.0-FINAL</p>
                </div>
                <div className="p-3 bg-white/5 rounded-lg border border-white/10">
                    <p className="text-[10px] font-black text-slate-400 uppercase mb-1">Credibility Index</p>
                    <p className="text-sm font-bold text-emerald-400">LEVEL PC3: QUALIFIED</p>
                </div>
              </div>
          </div>

          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h3 className="font-bold text-xs uppercase tracking-widest text-slate-400 mb-6">Recent Solver Benchmarks</h3>
            <div className="space-y-4">
               {[
                 { label: 'Electromagnetic (A1)', val: '99.9%' },
                 { label: 'Thermal CFD (C1)', val: '98.5%' },
                 { label: 'Modal Analysis (D1)', val: '99.2%' }
               ].map(b => (
                 <div key={b.label} className="flex justify-between items-center text-xs">
                   <span className="text-slate-500 font-bold">{b.label}</span>
                   <span className="text-emerald-600 font-black">{b.val}</span>
                 </div>
               ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SimulationWorkspace;
