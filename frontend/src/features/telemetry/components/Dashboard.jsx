import { useQuery } from '@tanstack/react-query';
import { graphqlService } from '@/services/graphql';
import { getDossiers } from '@/services/sdd.service';
import { 
  Database, 
  Activity, 
  Search, 
  Terminal, 
  FileText, 
  ArrowRight, 
  Sparkles, 
  LayoutDashboard, 
  PieChart as PieChartIcon, 
  BarChart3, 
  Info,
  ShieldAlert,
  Clock,
  CheckCircle2,
  Filter,
  Download,
  TrendingUp
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line
} from 'recharts';

export default function Dashboard() {
  const navigate = useNavigate();
  
  // Fetch graph statistics
  const {
    data: stats,
    isLoading: statsLoading,
    error: statsError
  } = useQuery({
    queryKey: ['statistics'],
    queryFn: graphqlService.getStatistics,
    retry: 1,
    staleTime: 30000
  });

  // Fetch dossiers for engineering metrics
  const {
    data: dossiersData,
    isLoading: dossiersLoading
  } = useQuery({
    queryKey: ['simulation-dossiers', 'all'],
    queryFn: () => getDossiers({}),
    staleTime: 30000
  });

  const isLoading = statsLoading || dossiersLoading;
  const dossiers = dossiersData?.dossiers || [];

  if (isLoading) {
    return (
      <div className="p-8 space-y-8">
        <div className="h-12 bg-slate-200 animate-pulse rounded-xl w-1/3" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[1,2,3,4].map(i => <div key={i} className="h-32 bg-slate-200 animate-pulse rounded-2xl" />)}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-80 bg-slate-200 animate-pulse rounded-3xl" />
          <div className="h-80 bg-slate-200 animate-pulse rounded-3xl" />
        </div>
      </div>
    );
  }

  if (statsError) {
    return (
      <div className="p-8">
        <div className="p-6 bg-red-50 border-2 border-red-200 rounded-2xl flex items-start gap-4">
          <ShieldAlert className="h-6 w-6 text-red-600 shrink-0 mt-1" />
          <div>
            <h3 className="font-bold text-red-800 text-lg mb-1">Failed to Load Telemetry</h3>
            <p className="text-red-600 text-sm">Please check your connection to the Neo4j graph database.</p>
          </div>
        </div>
      </div>
    );
  }

  // Calculate Engineering Stats
  const engStats = [
    { 
      label: 'Active Dossiers', 
      value: dossiers.filter(d => d.status === 'IN_PROGRESS').length.toString(), 
      icon: Activity, 
      color: 'blue' 
    },
    { 
      label: 'Pending Validations', 
      value: dossiers.filter(d => d.status === 'PENDING_REVIEW').length.toString(), 
      icon: Clock, 
      color: 'amber' 
    },
    { 
      label: 'Approved Packages', 
      value: dossiers.filter(d => d.status === 'APPROVED').length.toString(), 
      icon: CheckCircle2, 
      color: 'emerald' 
    },
    { 
      label: 'Critical Deviations', 
      value: dossiers.filter(d => d.status === 'REJECTED').length.toString(), 
      icon: ShieldAlert, 
      color: 'rose' 
    },
  ];

  // Prepare Graph Data
  const nodeTypes = Object.entries(stats?.node_types || {})
    .filter(([type]) => type && type.trim())
    .sort(([, a], [, b]) => b - a);
    
  const relationshipTypes = Object.entries(stats?.relationship_types || {})
    .filter(([type]) => type && type.trim())
    .sort(([, a], [, b]) => b - a);

  const nodeChartData = nodeTypes.slice(0, 10).map(([name, value]) => ({ name, value }));
  const relChartData = relationshipTypes.slice(0, 5).map(([name, value]) => ({ name, value }));
  
  const COLORS = ['#004A99', '#00B0E4', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899', '#F43F5E'];

  // Mock trend data for the convergence chart (since Neo4j doesn't store historical iterations yet)
  const trendData = [
    { time: 'Iteration 1', Efficiency: 82, Torque: 45, Thermal: 95 },
    { time: 'Iteration 2', Efficiency: 85, Torque: 48, Thermal: 92 },
    { time: 'Iteration 3', Efficiency: 89, Torque: 52, Thermal: 88 },
    { time: 'Iteration 4', Efficiency: 92, Torque: 55, Thermal: 85 },
    { time: 'Iteration 5', Efficiency: 94, Torque: 58, Thermal: 82 },
  ];

  return (
    <div className="space-y-8 pb-12">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 tracking-tight">Engineering Simulation Intelligence</h1>
          <p className="text-slate-500 text-sm font-medium">
            Aggregated telemetry from <span className="text-[#004A99] font-bold">{dossiers.length} dossiers</span> and <span className="text-[#00B0E4] font-bold">{stats?.total_nodes || 0} graph nodes</span>
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

      {/* Engineering Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {engStats.map((stat, i) => (
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

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Graph Distribution Chart */}
        <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
          <div className="flex justify-between items-start mb-8">
            <div>
              <h3 className="font-black text-xs text-slate-400 uppercase tracking-widest flex items-center gap-2">
                <Database size={16} className="text-[#004A99]" /> Knowledge Graph Distribution
              </h3>
              <p className="text-xs text-slate-500 mt-1">Top Entity Types in Neo4j</p>
            </div>
            <div className="text-[10px] font-black text-[#004A99] bg-blue-50 px-2 py-1 rounded-full border border-blue-100 uppercase">
              Live Sync
            </div>
          </div>
          <div className="h-64 mt-auto">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={nodeChartData}>
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
                <Bar dataKey="value" fill="#004A99" radius={[6, 6, 0, 0]} barSize={45}>
                  {nodeChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Simulation Convergence Trends */}
        <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
          <div className="flex justify-between items-start mb-8">
            <div>
              <h3 className="font-black text-xs text-slate-400 uppercase tracking-widest flex items-center gap-2">
                <TrendingUp size={16} className="text-emerald-500" /> Simulation Convergence Trends
              </h3>
              <p className="text-xs text-slate-500 mt-1">Historical Iterations (Aggregated)</p>
            </div>
            <div className="text-[10px] font-black text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full border border-emerald-100 uppercase">
              Predictive
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
                <Line type="monotone" dataKey="Efficiency" stroke="#10B981" strokeWidth={4} dot={{r: 5, strokeWidth: 2, fill: '#fff'}} activeDot={{r: 8}} />
                <Line type="monotone" dataKey="Torque" stroke="#00B0E4" strokeWidth={4} dot={{r: 5, strokeWidth: 2, fill: '#fff'}} activeDot={{r: 8}} />
                <Line type="monotone" dataKey="Thermal" stroke="#6366f1" strokeWidth={4} dot={{r: 5, strokeWidth: 2, fill: '#fff'}} activeDot={{r: 8}} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Graph Topology Summary */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-8 py-5 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center">
          <h3 className="font-black text-xs text-slate-400 uppercase tracking-widest flex items-center gap-2">
            <Activity size={16} /> Graph Topology Summary
          </h3>
          <span className="text-[10px] font-black text-slate-400">TOTAL RELATIONSHIPS: {stats?.total_relationships || 0}</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 divide-x divide-slate-100 divide-y md:divide-y-0">
          <div className="divide-y divide-slate-50">
            {relationshipTypes.slice(0, 4).map(([type, count], idx) => (
              <div key={type} className="px-8 py-4 flex items-center justify-between group hover:bg-slate-50/50 transition-colors">
                <div className="flex items-center gap-4">
                  <span className="text-[10px] font-black text-slate-300 group-hover:text-[#004A99] transition-colors bg-white border border-slate-100 px-2 py-1 rounded shadow-sm uppercase tracking-tighter">
                    REL-{idx + 1}
                  </span>
                  <span className="font-bold text-slate-700 text-sm">{type}</span>
                </div>
                <div className="flex items-center gap-6">
                  <span className="text-[10px] font-black px-2 py-0.5 rounded uppercase tracking-widest border-2 bg-blue-50 text-blue-600 border-blue-100">
                    {count} Links
                  </span>
                </div>
              </div>
            ))}
          </div>
          <div className="divide-y divide-slate-50">
            {relationshipTypes.slice(4, 8).map(([type, count], idx) => (
              <div key={type} className="px-8 py-4 flex items-center justify-between group hover:bg-slate-50/50 transition-colors">
                <div className="flex items-center gap-4">
                  <span className="text-[10px] font-black text-slate-300 group-hover:text-[#004A99] transition-colors bg-white border border-slate-100 px-2 py-1 rounded shadow-sm uppercase tracking-tighter">
                    REL-{idx + 5}
                  </span>
                  <span className="font-bold text-slate-700 text-sm">{type}</span>
                </div>
                <div className="flex items-center gap-6">
                  <span className="text-[10px] font-black px-2 py-0.5 rounded uppercase tracking-widest border-2 bg-blue-50 text-blue-600 border-blue-100">
                    {count} Links
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

