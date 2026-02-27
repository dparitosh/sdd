
import React from 'react';
import { PRODUCT_SPECS } from '../constants';
import { 
  Thermometer, 
  Settings, 
  Wind, 
  Droplet, 
  Cpu, 
  ArrowRightCircle,
  FileCode2
} from 'lucide-react';

const ProductSpecs: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Motor Specification Data</h1>
          <p className="text-slate-500 text-sm font-medium">Core design parameters and environmental constraints</p>
        </div>
        <div className="px-3 py-1 bg-emerald-100 text-emerald-700 rounded-full text-[10px] font-bold uppercase tracking-widest border border-emerald-200">
          DESIGN_VERIFIED
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
                  <p className="text-xl font-bold text-slate-800">{PRODUCT_SPECS.model}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Operating Range</p>
                  <p className="text-xl font-bold text-slate-800 flex items-center gap-2">
                    <Thermometer size={18} className="text-rose-500" /> {PRODUCT_SPECS.tempRange}
                  </p>
                </div>
                <div className="space-y-1">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Load Rating</p>
                  <p className="text-xl font-bold text-slate-800">{PRODUCT_SPECS.loadRating}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Lubricant Profile</p>
                  <p className="text-xl font-bold text-slate-800 flex items-center gap-2">
                    <Droplet size={18} className="text-blue-500" /> {PRODUCT_SPECS.lubricant}
                  </p>
                </div>
             </div>

             <div className="mt-12 p-6 bg-slate-900 rounded-xl text-blue-300 border-l-4 border-blue-400">
                <div className="flex items-center gap-2 mb-3">
                  <FileCode2 size={20} />
                  <h4 className="font-bold uppercase tracking-widest text-xs">Shaft Expansion Formula</h4>
                </div>
                <code className="text-lg font-mono font-semibold block">{PRODUCT_SPECS.shaftFormula}</code>
             </div>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
             <h3 className="font-bold text-slate-800 mb-6 uppercase tracking-widest text-xs">Application Constraints (Sugar Processing)</h3>
             <div className="space-y-4">
                {PRODUCT_SPECS.constraints.map((constraint, i) => (
                  <div key={i} className="flex gap-4 p-4 hover:bg-slate-50 rounded-xl transition-colors group">
                    <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center shrink-0 group-hover:bg-[#00B0E4] group-hover:text-white transition-colors">
                      <Wind size={20} />
                    </div>
                    <div>
                      <p className="font-bold text-slate-700 text-sm mb-1">Standard Constraint #{i + 1}</p>
                      <p className="text-slate-500 text-sm leading-relaxed">{constraint}</p>
                    </div>
                  </div>
                ))}
             </div>
          </div>
        </div>

        <div className="space-y-6">
           <div className="bg-gradient-to-br from-[#004A99] to-[#003d7a] p-8 rounded-2xl text-white shadow-xl">
              <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
                <Cpu size={20} /> System Assets
              </h3>
              <div className="space-y-4">
                {['CAD Models (STEP)', 'Simulation Logs', 'Certification Drafts'].map((asset) => (
                  <button key={asset} className="w-full flex items-center justify-between p-3 bg-white/10 hover:bg-white/20 rounded-xl transition-colors">
                    <span className="font-medium text-sm">{asset}</span>
                    <ArrowRightCircle size={18} />
                  </button>
                ))}
              </div>
              <div className="mt-10 pt-6 border-t border-white/10">
                <p className="text-[10px] font-bold text-blue-200 uppercase tracking-widest mb-2">Compliance Check</p>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></div>
                  <p className="text-xs font-medium">Auto-sync with MOSSEC Server</p>
                </div>
              </div>
           </div>
           
           <div className="p-6 bg-white border border-slate-200 rounded-2xl text-center">
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
};

export default ProductSpecs;
