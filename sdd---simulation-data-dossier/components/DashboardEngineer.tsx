
import React from 'react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  LineChart,
  Line,
  Legend
} from 'recharts';
import { 
  Activity, 
  ShieldAlert, 
  Clock, 
  CheckCircle2,
  Filter,
  Download,
  TrendingUp
} from 'lucide-react';
import { Dossier, DossierStatus } from '../types';

interface DashboardEngineerProps {
  dossiers: Dossier[];
}

const DashboardEngineer: React.FC<DashboardEngineerProps> = ({ dossiers }) => {
  // Use the most recently updated dossier as the "Active" context for charts
  const activeDossier = dossiers.sort((a, b) => 
    new Date(b.lastUpdated).getTime() - new Date(a.lastUpdated).getTime()
  )[0];

  const stats = [
    { 
      label: 'Active Dossiers', 
      value: dossiers.filter(d => d.status === DossierStatus.IN_PROGRESS).length.toString(), 
      icon: Activity, 
      color: 'blue' 
    },
    { 
      label: 'Pending Validations', 
      value: dossiers.filter(d => d.status === DossierStatus.PENDING_REVIEW).length.toString(), 
      icon: Clock, 
      color: 'amber' 
    },
    { 
      label: 'Approved Packages', 
      value: dossiers.filter(d => d.status === DossierStatus.APPROVED).length.toString(), 
      icon: CheckCircle2, 
      color: 'emerald' 
    },
    { 
      label: 'Critical Deviations', 
      value: dossiers.filter(d => d.status === DossierStatus.REJECTED).length.toString(), 
      icon: ShieldAlert, 
      color: 'rose' 
    },
  ];

  // Align Line Chart data with the trend arrays in the Active Dossier KPIs
  // We assume the first few KPIs contain the necessary trend data (Efficiency, Torque, etc.)
  const trendData = activeDossier.kpis[0]?.trend.map((_, index) => {
    const entry: any = { time: `Iteration ${index + 1}` };
    activeDossier.kpis.forEach(kpi => {
      if (kpi.trend && kpi.trend[index] !== undefined) {
        entry[kpi.name] = kpi.trend[index];
      }
    });
    return entry;
  }) || [];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 tracking-tight">Engineering Simulation Intelligence</h1>
          <p className="text-slate-500 text-sm font-medium">
            Aggregated telemetry from <span className="text-[#004A99] font-bold">{dossiers.length} dossiers</span> • Primary: {activeDossier.id}
          </p>
        </div>
        <div className="flex gap-2">
          <button className="flex items-center gap-2 bg-white border border-slate-200 px-4 py-2 rounded-lg text-sm font-bold text-slate-600 hover:bg-slate-50 transition-all shadow-sm">
            <Filter size={16} /> Filter View
          </button>
          <button className="flex items-center gap-2 bg-[#004A99] text-white px-4 py-2 rounded-lg text-sm font-bold hover:bg-[#003d7a] transition-all shadow-lg shadow-blue-900/10">
            <Download size={16} /> Export Master Log
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {stats.map((stat, i) => (
          <div key={i} className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex justify-between items-start mb-4">
              <div className={`p-2.5 rounded-xl bg-${stat.color}-50 text-${stat.color}-600`}>
                <stat.icon size={22} />
              </div>
              <TrendingUp size={16} className="text-slate-300" />
            </div>
            <h3 className="text-3xl font-black text-slate-800">{stat.value}</h3>
            <p className="text-slate-400 text-xs font-black uppercase tracking-widest mt-1">{stat.label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
          <div className="flex justify-between items-start mb-8">
            <div>
              <h3 className="font-black text-xs text-slate-400 uppercase tracking-widest flex items-center gap-2">
                <Activity size={16} className="text-blue-500" /> Primary KPI Distribution
              </h3>
              <p className="text-xs text-slate-500 mt-1">Dossier: {activeDossier.id} ({activeDossier.motorId})</p>
            </div>
          </div>
          <div className="h-64 mt-auto">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={activeDossier.kpis}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis 
                  dataKey="name" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fontSize: 10, fontWeight: 700, fill: '#64748b'}} 
                />
                <YAxis 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fontSize: 10, fontWeight: 700, fill: '#64748b'}}
                />
                <Tooltip 
                  cursor={{fill: '#f8fafc'}} 
                  contentStyle={{borderRadius: '12px', border: 'none', boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1)', padding: '12px'}} 
                />
                <Bar dataKey="value" fill="#004A99" radius={[6, 6, 0, 0]} barSize={45} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
          <div className="flex justify-between items-start mb-8">
            <div>
              <h3 className="font-black text-xs text-slate-400 uppercase tracking-widest flex items-center gap-2">
                <TrendingUp size={16} className="text-emerald-500" /> Simulation Convergence Trends
              </h3>
              <p className="text-xs text-slate-500 mt-1">Historical Iterations for {activeDossier.motorId}</p>
            </div>
            <div className="text-[10px] font-black text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full border border-emerald-100 uppercase">
              Live Link
            </div>
          </div>
          <div className="h-64 mt-auto">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis 
                  dataKey="time" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fontSize: 10, fontWeight: 700, fill: '#64748b'}} 
                />
                <YAxis 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fontSize: 10, fontWeight: 700, fill: '#64748b'}}
                />
                <Tooltip 
                   contentStyle={{borderRadius: '12px', border: 'none', boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1)', padding: '12px'}} 
                />
                <Legend iconType="circle" wrapperStyle={{fontSize: '10px', fontWeight: 800, textTransform: 'uppercase', paddingTop: '20px'}} />
                {activeDossier.kpis.map((kpi, idx) => (
                  <Line 
                    key={kpi.name}
                    type="monotone" 
                    dataKey={kpi.name} 
                    stroke={idx === 0 ? '#10B981' : idx === 1 ? '#00B0E4' : '#6366f1'} 
                    strokeWidth={4} 
                    dot={{r: 5, strokeWidth: 2, fill: '#fff'}} 
                    activeDot={{r: 8}}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-8 py-5 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center">
          <h3 className="font-black text-xs text-slate-400 uppercase tracking-widest">
            Evidence Pipeline Status: {activeDossier.id}
          </h3>
          <span className="text-[10px] font-black text-slate-400">MOSSEC COMPLIANCE: {activeDossier.credibilityLevel}</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 divide-x divide-slate-100 divide-y md:divide-y-0">
          <div className="divide-y divide-slate-50">
            {activeDossier.categories.slice(0, 4).map((cat) => (
              <CategoryRow key={cat.id} cat={cat} />
            ))}
          </div>
          <div className="divide-y divide-slate-50">
            {activeDossier.categories.slice(4).map((cat) => (
              <CategoryRow key={cat.id} cat={cat} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

const CategoryRow: React.FC<{cat: any}> = ({ cat }) => (
  <div className="px-8 py-4 flex items-center justify-between group hover:bg-slate-50/50 transition-colors">
    <div className="flex items-center gap-4">
      <span className="text-[10px] font-black text-slate-300 group-hover:text-[#004A99] transition-colors bg-white border border-slate-100 px-2 py-1 rounded shadow-sm uppercase tracking-tighter">CAT-{cat.id}</span>
      <span className="font-bold text-slate-700 text-sm">{cat.label}</span>
    </div>
    <div className="flex items-center gap-6">
      <div className="w-24 h-1.5 bg-slate-100 rounded-full overflow-hidden">
         <div 
          className={`h-full transition-all duration-700 ${
            cat.status === 'Complete' ? 'w-full bg-emerald-500' : 
            cat.status === 'Review Required' ? 'w-2/3 bg-amber-500' : 'w-1/3 bg-slate-200'
          }`}
         />
      </div>
      <span className={`text-[9px] font-black px-2 py-0.5 rounded uppercase tracking-widest border-2 ${
        cat.status === 'Complete' ? 'bg-emerald-50 text-emerald-600 border-emerald-100' : 
        cat.status === 'Review Required' ? 'bg-amber-50 text-amber-600 border-amber-100' : 'bg-slate-50 text-slate-400 border-slate-100'
      }`}>
        {cat.status}
      </span>
    </div>
  </div>
);

export default DashboardEngineer;
