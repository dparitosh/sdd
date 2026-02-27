
import React, { useState } from 'react';
import { 
  PieChart, 
  Pie, 
  Cell, 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip,
  Legend,
  CartesianGrid
} from 'recharts';
import { 
  FileCheck, 
  FileX, 
  FileClock, 
  Search,
  Download,
  ShieldCheck,
  AlertCircle,
  ChevronRight
} from 'lucide-react';
import { Dossier, DossierStatus } from '../types';

interface QualityDashboardProps {
  dossiers: Dossier[];
  onSelectDossier: (id: string) => void;
}

const QualityDashboard: React.FC<QualityDashboardProps> = ({ dossiers, onSelectDossier }) => {
  const [searchTerm, setSearchTerm] = useState('');

  const pendingDossiers = dossiers.filter(d => d.status === DossierStatus.PENDING_REVIEW);
  const processedDossiers = dossiers.filter(d => d.status !== DossierStatus.PENDING_REVIEW && d.status !== DossierStatus.IN_PROGRESS);

  const statusData = [
    { name: 'Approved', value: dossiers.filter(d => d.status === DossierStatus.APPROVED).length, color: '#10B981' },
    { name: 'Pending', value: dossiers.filter(d => d.status === DossierStatus.PENDING_REVIEW).length, color: '#F59E0B' },
    { name: 'Rejected', value: dossiers.filter(d => d.status === DossierStatus.REJECTED).length, color: '#EF4444' },
  ];

  return (
    <div className="space-y-8 pb-12">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Quality Workflow Manager</h1>
          <p className="text-slate-500 text-sm font-medium">Certification review & compliance release hub</p>
        </div>
        <button className="flex items-center gap-2 bg-white border border-slate-200 px-4 py-2 rounded-lg text-sm font-bold text-slate-600 hover:bg-slate-50 transition-all">
          <Download size={16} /> Download Full Audit Log
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm col-span-1">
          <h3 className="font-bold text-slate-800 mb-6 flex items-center gap-2 uppercase text-xs tracking-widest">
            <ShieldCheck size={18} className="text-blue-500" /> Dossier Health
          </h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie 
                  data={statusData} 
                  innerRadius={60} 
                  outerRadius={80} 
                  paddingAngle={5} 
                  dataKey="value"
                >
                  {statusData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-around mt-4">
            {statusData.map((s) => (
              <div key={s.name} className="text-center">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{s.name}</p>
                <p className="text-lg font-bold" style={{ color: s.color }}>{s.value}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-bold text-slate-800 uppercase text-xs tracking-widest">Certification Throughput</h3>
            <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 px-3 py-1 rounded-lg">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              <span className="text-[10px] font-bold text-slate-500 uppercase">Live Pipeline Tracking</span>
            </div>
          </div>
          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={[
                {day: 'Mon', approved: 2, rejected: 0},
                {day: 'Tue', approved: 1, rejected: 1},
                {day: 'Wed', approved: 3, rejected: 0},
                {day: 'Thu', approved: 0, rejected: 0},
                {day: 'Fri', approved: 2, rejected: 1},
              ]}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="day" axisLine={false} tickLine={false} />
                <YAxis axisLine={false} tickLine={false} />
                <Tooltip cursor={{fill: 'transparent'}} />
                <Legend />
                <Bar dataKey="approved" fill="#10B981" radius={[4, 4, 0, 0]} name="Certification Signed" />
                <Bar dataKey="rejected" fill="#EF4444" radius={[4, 4, 0, 0]} name="Revisions Requested" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Priority Section */}
      {pendingDossiers.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
            <AlertCircle className="text-amber-500" size={20} /> High Priority: Action Required
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {pendingDossiers.map(dossier => (
              <div 
                key={dossier.id} 
                className="bg-white p-6 rounded-2xl border-2 border-amber-100 shadow-xl shadow-amber-500/5 hover:border-amber-300 transition-all group cursor-pointer"
                onClick={() => onSelectDossier(dossier.id)}
              >
                <div className="flex justify-between items-start mb-4">
                  <div className="p-3 bg-amber-50 text-amber-600 rounded-xl group-hover:bg-amber-100 transition-colors">
                    <FileClock size={24} />
                  </div>
                  <span className="text-[10px] font-black bg-amber-100 text-amber-700 px-2 py-1 rounded-full uppercase tracking-widest">Awaiting Decision</span>
                </div>
                <h3 className="font-bold text-xl text-slate-800 mb-1">{dossier.id}</h3>
                <p className="text-sm text-slate-500 mb-6">{dossier.projectName}</p>
                <div className="flex items-center justify-between pt-4 border-t border-slate-50">
                   <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-[10px] font-bold text-slate-500">SR</div>
                      <span className="text-xs font-bold text-slate-600">{dossier.engineer}</span>
                   </div>
                   <button className="bg-[#004A99] text-white p-2 rounded-lg shadow-lg group-hover:scale-110 transition-transform">
                      <ChevronRight size={18} />
                   </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Registry Section */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-800">Certification Registry & Archive</h2>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={14} />
            <input 
              type="text" 
              placeholder="Search history..." 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 pr-4 py-2 bg-white border border-slate-200 rounded-lg text-sm w-80 outline-none focus:ring-2 focus:ring-[#004A99]" 
            />
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-slate-50 border-b border-slate-100 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                <tr>
                  <th className="px-6 py-4">Current Status</th>
                  <th className="px-6 py-4">Dossier ID</th>
                  <th className="px-6 py-4">Engineer</th>
                  <th className="px-6 py-4">Compliance Score</th>
                  <th className="px-6 py-4 text-right">Navigation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {processedDossiers.map((dossier) => (
                  <tr key={dossier.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4">
                      <div className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-tighter ${
                        dossier.status === DossierStatus.APPROVED ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'
                      }`}>
                        {dossier.status === DossierStatus.APPROVED ? <FileCheck size={12} /> : <FileX size={12} />}
                        {dossier.status}
                      </div>
                    </td>
                    <td className="px-6 py-4 font-bold text-slate-700">{dossier.id}</td>
                    <td className="px-6 py-4 text-sm text-slate-600">{dossier.engineer}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div className={`h-full ${dossier.status === DossierStatus.APPROVED ? 'bg-emerald-500' : 'bg-rose-400'}`} style={{ width: '100%' }}></div>
                        </div>
                        <span className="text-[10px] font-bold text-slate-400">PASSED</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button 
                        onClick={() => onSelectDossier(dossier.id)}
                        className="text-[#004A99] font-bold text-sm hover:underline"
                      >
                        Audit Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
};

export default QualityDashboard;
