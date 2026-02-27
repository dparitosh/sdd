import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldCheck,
  Clock,
  AlertTriangle,
  TrendingUp,
  Download,
  Search,
  FileClock,
  ChevronRight,
  FileCheck,
  FileX
} from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { useKPIs, useDossierHealth, useApprovalQueue } from '../hooks/useMetrics';

const STATUS_COLORS = {
  Draft: '#94a3b8',
  UnderReview: '#f59e0b',
  Approved: '#10B981',
  Rejected: '#EF4444',
  Archived: '#6b7280',
};

const PIE_COLORS = ['#94a3b8', '#f59e0b', '#10B981', '#EF4444', '#6b7280'];

export default function QualityDashboard() {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  
  const { kpis, isLoading: kpiLoading, error: kpiError } = useKPIs();
  const { healthData, isLoading: healthLoading } = useDossierHealth();
  const { queue, weeklyThroughput, isLoading: queueLoading } = useApprovalQueue();

  const isLoading = kpiLoading || healthLoading || queueLoading;

  if (isLoading) {
    return (
      <div className="p-8 space-y-8">
        <div className="h-12 bg-slate-200 animate-pulse rounded-xl w-1/3" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="h-64 bg-slate-200 animate-pulse rounded-2xl" />
          <div className="h-64 bg-slate-200 animate-pulse rounded-2xl lg:col-span-2" />
        </div>
      </div>
    );
  }

  if (kpiError) {
    return (
      <div className="p-8">
        <div className="p-6 bg-red-50 border-2 border-red-200 rounded-2xl flex items-start gap-4">
          <AlertTriangle className="h-6 w-6 text-red-600 shrink-0 mt-1" />
          <div>
            <h3 className="font-bold text-red-800 text-lg mb-1">Failed to Load Quality Data</h3>
            <p className="text-red-600 text-sm">Please check your connection to the metrics service.</p>
          </div>
        </div>
      </div>
    );
  }

  // Build status distribution from KPIs
  const statusDist = kpis.statusDistribution ?? [];
  
  // Map to prototype's expected format
  const statusData = statusDist.map(s => ({
    name: s.status,
    value: s.count,
    color: STATUS_COLORS[s.status] || '#94a3b8'
  }));

  // Priority queue — dossiers sorted by health score ascending (worst first)
  const priorityQueue = [...(healthData || [])].sort((a, b) => a.score - b.score).slice(0, 10);
  
  // Processed dossiers for the registry table
  const processedDossiers = (healthData || []).filter(d => d.status === 'Approved' || d.status === 'Rejected');

  return (
    <div className="space-y-8 pb-12">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Quality Workflow Manager</h1>
          <p className="text-slate-500 text-sm font-medium">Certification review & compliance release hub</p>
        </div>
        <button className="flex items-center gap-2 bg-white border border-slate-200 px-4 py-2 rounded-lg text-sm font-bold text-slate-600 hover:bg-slate-50 transition-all shadow-sm">
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
                <Tooltip contentStyle={{borderRadius: '12px', border: 'none', boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1)'}} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-around mt-4 flex-wrap gap-2">
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
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="text-[10px] font-bold text-slate-500 uppercase">Live Pipeline Tracking</span>
            </div>
          </div>
          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={weeklyThroughput.length > 0 ? weeklyThroughput : [
                {week: 'W1', approved: 2, rejected: 0},
                {week: 'W2', approved: 1, rejected: 1},
                {week: 'W3', approved: 3, rejected: 0},
                {week: 'W4', approved: 0, rejected: 0},
                {week: 'W5', approved: 2, rejected: 1},
              ]}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="week" axisLine={false} tickLine={false} tick={{fontSize: 10, fontWeight: 700, fill: '#64748b'}} />
                <YAxis axisLine={false} tickLine={false} tick={{fontSize: 10, fontWeight: 700, fill: '#64748b'}} />
                <Tooltip cursor={{fill: '#f8fafc'}} contentStyle={{borderRadius: '12px', border: 'none', boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1)'}} />
                <Legend iconType="circle" wrapperStyle={{fontSize: '10px', fontWeight: 800, textTransform: 'uppercase'}} />
                <Bar dataKey="approved" fill="#10B981" radius={[4, 4, 0, 0]} name="Certification Signed" />
                <Bar dataKey="rejected" fill="#EF4444" radius={[4, 4, 0, 0]} name="Revisions Requested" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Priority Section */}
      {priorityQueue.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
            <AlertTriangle className="text-amber-500" size={20} /> High Priority: Action Required
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {priorityQueue.map(dossier => (
              <div 
                key={dossier.id || dossier.name} 
                className="bg-white p-6 rounded-2xl border-2 border-amber-100 shadow-xl shadow-amber-500/5 hover:border-amber-300 transition-all group cursor-pointer"
                onClick={() => navigate(`/quality/dossiers/${dossier.id || dossier.name}`)}
              >
                <div className="flex justify-between items-start mb-4">
                  <div className="p-3 bg-amber-50 text-amber-600 rounded-xl group-hover:bg-amber-100 transition-colors">
                    <FileClock size={24} />
                  </div>
                  <span className="text-[10px] font-black bg-amber-100 text-amber-700 px-2 py-1 rounded-full uppercase tracking-widest">
                    {dossier.score < 40 ? 'Critical Review' : 'Awaiting Decision'}
                  </span>
                </div>
                <h3 className="font-bold text-xl text-slate-800 mb-1">{dossier.name || dossier.id}</h3>
                <p className="text-sm text-slate-500 mb-6">Health Score: {dossier.score}</p>
                <div className="flex items-center justify-between pt-4 border-t border-slate-50">
                   <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-[10px] font-bold text-slate-500">SYS</div>
                      <span className="text-xs font-bold text-slate-600">System Generated</span>
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
                  <th className="px-6 py-4">Health Score</th>
                  <th className="px-6 py-4">Compliance</th>
                  <th className="px-6 py-4 text-right">Navigation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {processedDossiers.length > 0 ? processedDossiers.map((dossier) => (
                  <tr key={dossier.id || dossier.name} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4">
                      <div className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-tighter ${
                        dossier.status === 'Approved' ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'
                      }`}>
                        {dossier.status === 'Approved' ? <FileCheck size={12} /> : <FileX size={12} />}
                        {dossier.status}
                      </div>
                    </td>
                    <td className="px-6 py-4 font-bold text-slate-700">{dossier.name || dossier.id}</td>
                    <td className="px-6 py-4 text-sm text-slate-600 font-mono">{dossier.score}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div className={`h-full ${dossier.status === 'Approved' ? 'bg-emerald-500' : 'bg-rose-400'}`} style={{ width: `${dossier.score}%` }}></div>
                        </div>
                        <span className="text-xs font-bold text-slate-500">{dossier.score}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button 
                        onClick={() => navigate(`/quality/dossiers/${dossier.id || dossier.name}`)}
                        className="text-[#004A99] hover:text-[#00B0E4] font-bold text-sm transition-colors"
                      >
                        View Audit
                      </button>
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-slate-500 text-sm">
                      No processed dossiers found in the registry.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}
