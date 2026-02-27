
import React from 'react';
import { Dossier, DossierStatus } from '../types';
import { FileBox, ChevronRight, Clock, CheckCircle, AlertCircle } from 'lucide-react';

interface MyDossiersProps {
  dossiers: Dossier[];
  onSelectDossier: (id: string) => void;
}

const MyDossiers: React.FC<MyDossiersProps> = ({ dossiers, onSelectDossier }) => {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">My Simulation Dossiers</h1>
          <p className="text-slate-500 text-sm">Manage and track certification evidence packages</p>
        </div>
        <button className="bg-[#004A99] text-white px-4 py-2 rounded-lg text-sm font-bold hover:bg-[#003d7a]">
          + Create New Dossier
        </button>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-slate-50 border-b border-slate-100">
              <tr>
                <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase">Dossier ID</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase">Project Name</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase">Motor Model</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase">Status</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase">Evidence Progress</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {dossiers.map((dossier) => {
                const completeCount = dossier.categories.filter(c => c.status === 'Complete').length;
                const progress = (completeCount / dossier.categories.length) * 100;

                return (
                  <tr key={dossier.id} className="hover:bg-slate-50/80 transition-colors group">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-slate-100 rounded text-slate-500 group-hover:bg-[#00B0E4] group-hover:text-white transition-colors">
                          <FileBox size={16} />
                        </div>
                        <span className="font-bold text-slate-700">{dossier.id}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600">{dossier.projectName}</td>
                    <td className="px-6 py-4 text-sm text-slate-600">{dossier.motorId}</td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase ${
                        dossier.status === DossierStatus.APPROVED ? 'bg-emerald-100 text-emerald-700' :
                        dossier.status === DossierStatus.PENDING_REVIEW ? 'bg-amber-100 text-amber-700' :
                        dossier.status === DossierStatus.REJECTED ? 'bg-rose-100 text-rose-700' : 'bg-slate-100 text-slate-600'
                      }`}>
                        {dossier.status === DossierStatus.APPROVED && <CheckCircle size={10} />}
                        {dossier.status === DossierStatus.PENDING_REVIEW && <Clock size={10} />}
                        {dossier.status === DossierStatus.REJECTED && <AlertCircle size={10} />}
                        {dossier.status}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden min-w-[100px]">
                          <div className="h-full bg-[#004A99]" style={{ width: `${progress}%` }}></div>
                        </div>
                        <span className="text-xs font-bold text-slate-500">{Math.round(progress)}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button 
                        onClick={() => onSelectDossier(dossier.id)}
                        className="text-[#004A99] hover:text-[#003d7a] font-bold text-sm flex items-center gap-1 ml-auto"
                      >
                        View Details <ChevronRight size={14} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default MyDossiers;
