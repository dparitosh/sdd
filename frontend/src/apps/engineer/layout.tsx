import { Link, useLocation, Outlet } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { Badge } from '@ui/badge';
import { Separator } from '@ui/separator';
import RoleSelector from '@/features/auth/components/RoleSelector';
import Chatbot from '@/features/ai-studio/components/Chatbot';
import { useAuthStore } from '@/stores/authStore';
import { useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Search,
  FileText,
  GitBranch,
  Network,
  Upload,
  Database,
  Brain,
  Lightbulb,
  Sparkles,
  Activity,
  Boxes,
  Workflow,
  TrendingUp,
  Package,
  Info,
  Globe,
  ShieldCheck,
  Code,
  FileOutput,
  Ruler,
  UserCircle2,
  LogOut,
} from 'lucide-react';

const navigationGroups = [
  {
    label: 'Dashboard',
    items: [
      { name: 'Dashboard', href: '/engineer', icon: LayoutDashboard, badge: null },
      { name: 'Search & Discovery', href: '/engineer/search', icon: Search, badge: null },
    ],
  },
  {
    label: 'Simulation',
    items: [
      { name: 'Models', href: '/engineer/simulation/models', icon: Boxes, badge: null },
      { name: 'Runs', href: '/engineer/simulation/runs', icon: Activity, badge: null },
      { name: 'Workflows', href: '/engineer/simulation/workflows', icon: Workflow, badge: null },
      { name: 'Results', href: '/engineer/simulation/results', icon: TrendingUp, badge: null },
    ],
  },
  {
    label: 'Dossiers',
    items: [
      { name: 'Dossier List', href: '/engineer/simulation/dossiers', icon: FileText, badge: 'SDD' },
      { name: 'MoSSEC (AP243)', href: '/engineer/mossec-dashboard', icon: Database, badge: 'NEW' },
    ],
  },
  {
    label: 'Systems Engineering',
    items: [
      { name: 'Requirements', href: '/engineer/requirements', icon: FileText, badge: null },
      { name: 'AP239 Dashboard', href: '/engineer/ap239/requirements', icon: FileText, badge: null },
      { name: 'Traceability', href: '/engineer/traceability', icon: GitBranch, badge: null },
      { name: 'Parts (AP242)', href: '/engineer/ap242/parts', icon: Package, badge: null },
      { name: 'Product Specs', href: '/engineer/product-specs', icon: Ruler, badge: 'NEW' },
    ],
  },
  {
    label: 'Graph & Ontology',
    items: [
      { name: 'Graph Explorer', href: '/engineer/graph', icon: Network, badge: 'Unified' },
    ],
  },
  {
    label: 'AI Studio',
    items: [
      { name: 'AI Insights', href: '/engineer/ai/insights', icon: Lightbulb, badge: 'AI' },
      { name: 'Smart Analysis', href: '/engineer/ai/analysis', icon: Brain, badge: 'AI' },
      { name: 'Model Chat', href: '/engineer/ai/chat', icon: Sparkles, badge: 'BETA' },
    ],
  },
  {
    label: 'Semantic Web',
    items: [
      { name: 'Ontology Manager', href: '/engineer/semantic/ontology', icon: Globe, badge: null },
      { name: 'OSLC Browser', href: '/engineer/semantic/oslc', icon: Network, badge: null },
      { name: 'SHACL Validator', href: '/engineer/semantic/shacl', icon: ShieldCheck, badge: null },
      { name: 'GraphQL', href: '/engineer/semantic/graphql', icon: Code, badge: null },
      { name: 'RDF Export', href: '/engineer/semantic/rdf-export', icon: FileOutput, badge: null },
    ],
  },
  {
    label: 'Data Management',
    items: [
      { name: 'Data Import', href: '/engineer/import', icon: Upload, badge: null },
      { name: 'PLM Integration', href: '/engineer/plm', icon: Database, badge: null },
    ],
  },
];

export default function EngineerLayout() {
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const displayName = user?.name || user?.username || 'Guest User';
  const displayRole = 'Simulation Engineer';

  return (
    <div className="flex h-screen bg-slate-50">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 text-white flex flex-col h-screen fixed left-0 top-0 z-40 border-r border-slate-800" role="navigation" aria-label="Engineer navigation">
        <div className="flex h-full flex-col">
          {/* Brand header */}
          <div className="p-6 border-b border-slate-800 bg-slate-900">
            <div className="flex items-center gap-3 mb-1">
              <div className="w-9 h-9 bg-[#004A99] rounded-lg flex items-center justify-center font-black text-white text-xs shadow-lg shadow-blue-500/10">
                TCS
              </div>
              <div>
                <span className="font-black text-sm tracking-tight block leading-none">SDD PLATFORM</span>
                <span className="text-[8px] text-slate-500 font-black uppercase tracking-widest mt-1 block">Enterprise Simulation</span>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1 mt-4 overflow-y-auto">
            {navigationGroups.map((group) => (
              <div key={group.label} className="mb-3">
                <p className="px-4 py-1 text-[9px] font-black text-slate-500 uppercase tracking-widest">
                  {group.label}
                </p>
                {group.items.map((item) => {
                  const isActive = location.pathname === item.href;
                  return (
                    <Link
                      key={item.href}
                      to={item.href}
                      className={cn(
                        'w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group',
                        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#004A99]',
                        isActive
                          ? 'bg-[#004A99] text-white shadow-lg shadow-blue-900/40'
                          : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                      )}
                      aria-current={isActive ? 'page' : undefined}
                    >
                      <item.icon size={18} />
                      <span className="font-bold text-xs flex-1 text-left uppercase tracking-widest">{item.name}</span>
                      {item.badge && (
                        <span className="bg-[#00B0E4] text-white text-[9px] font-black px-1.5 py-0.5 rounded-full min-w-[18px] text-center shadow-lg shadow-blue-500/20">
                          {item.badge}
                        </span>
                      )}
                    </Link>
                  );
                })}
              </div>
            ))}
          </nav>

          {/* Status footer */}
          <div className="p-6 border-t border-slate-800 space-y-2">
            <div className="bg-slate-800/50 rounded-xl p-3 mb-4">
              <p className="text-[8px] font-black text-slate-500 uppercase tracking-widest mb-1">System Health</p>
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500"></div>
                <span className="text-[10px] font-bold text-slate-300">MOSSEC Sync Active</span>
              </div>
            </div>
            <div className="flex justify-between items-center text-[9px] text-slate-500 font-black uppercase tracking-widest pt-2 border-t border-slate-800">
              <span>v4.1.0-ENTERPRISE</span>
            </div>
            <div className="text-[9px] text-slate-500 font-black uppercase tracking-widest">
              <span>ISO 17025 / MOSSEC</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 flex flex-col overflow-hidden ml-64" role="main">
        <header className="h-16 bg-white border-b border-slate-200 px-8 flex items-center justify-end sticky top-0 z-30 shadow-sm">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-3">
              <div className="text-right hidden sm:block">
                <p className="text-sm font-bold text-slate-800">{displayName}</p>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">{displayRole}</p>
              </div>
              <div className="w-10 h-10 bg-slate-100 rounded-full flex items-center justify-center border border-slate-200">
                <UserCircle2 size={24} className="text-slate-500" />
              </div>
              <button 
                onClick={handleLogout}
                className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors ml-2"
                title="Switch Role / Logout"
              >
                <LogOut size={20} />
              </button>
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto">
          <div className="p-8 max-w-[1600px] w-full mx-auto">
            <div className="animate-in fade-in slide-in-from-bottom-2 duration-500">
              <Outlet />
            </div>
          </div>
        </div>

        <footer className="border-t bg-slate-100 py-3">
          <div className="container mx-auto px-8 flex items-center justify-between text-xs text-slate-600">
            <div className="flex items-center gap-4">
              <span className="font-bold">© 2025 TCS - Simulation Data Dossier Platform</span>
              <Separator orientation="vertical" className="h-4" />
              <span>Enterprise Compliance System</span>
            </div>
            <div className="flex items-center gap-2">
              <Info className="h-3 w-3" />
              <span className="font-semibold">ISO 10303 SMRL / IEC 6034 Compliant</span>
            </div>
          </div>
        </footer>
      </main>
      <Chatbot />
    </div>
  );
}
