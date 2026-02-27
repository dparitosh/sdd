import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { Badge } from '@ui/badge';
import { Separator } from '@ui/separator';
import { ModeToggle } from '@/components/mode-toggle';
import { useAuthStore } from '@/stores/authStore';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import {
  LayoutDashboard,
  Search,
  Code,
  Terminal,
  FileText,
  GitBranch,
  Database,
  Activity,
  Info,
  Package,
  Network,
  Upload,
  Brain,
  Lightbulb,
  TrendingUp,
  Workflow,
  Boxes,
  Sparkles,
  Share2,
  Bell,
  UserCircle2,
  LogOut,
} from 'lucide-react';

const navigationGroups = [
  {
    label: 'Overview',
    description: 'System dashboard and quick actions',
    items: [
      {
        name: 'Dashboard',
        href: '/dashboard',
        icon: LayoutDashboard,
        badge: null,
        description: 'System overview and KPIs',
      },

    ],
  },
  {
    label: 'Knowledge Graph',
    description: 'Explore and manage knowledge',
    items: [
      {
        name: 'Graph Explorer',
        href: '/graph',
        icon: Network,
        badge: 'Unified',
        description: 'Multi-view graph visualization',
      },
      {
        name: 'Advanced Search',
        href: '/search',
        icon: Search,
        badge: null,
        description: 'Complex queries & filtering',
      },
      {
        name: 'Requirements Management',
        href: '/ap239/requirements',
        icon: FileText,
        badge: null,
        description: 'ISO 10303-239 PLCS Dashboard',
      },
      {
        name: 'MoSSEC (AP243)',
        href: '/mossec-dashboard',
        icon: Database,
        badge: 'NEW',
        description: 'ISO 10303-243 Co-simulation',
      },
      {
        name: 'Traceability Matrix',
        href: '/traceability',
        icon: GitBranch,
        badge: null,
        description: 'End-to-end traceability',
      },
      {
        name: 'Parts & Components',
        href: '/ap242/parts',
        icon: Package,
        badge: null,
        description: 'Product structure and BOM',
      },
      {
        name: 'Query Studio',
        href: '/query-editor',
        icon: Terminal,
        badge: 'ADVANCED',
        description: 'Custom Cypher queries',
      },
    ],
  },
  {
    label: 'GenAI Studio',
    description: 'AI-powered insights and automation',
    items: [
      {
        name: 'AI Insights',
        href: '/ai/insights',
        icon: Lightbulb,
        badge: 'AI',
        description: 'AI-generated recommendations',
      },
      {
        name: 'Smart Analysis',
        href: '/ai/analysis',
        icon: Brain,
        badge: 'AI',
        description: 'Automated impact analysis',
      },
      {
        name: 'Model Chat',
        href: '/ai/chat',
        icon: Sparkles,
        badge: 'BETA',
        description: 'Conversational knowledge query',
      },
    ],
  },
  {
    label: 'Simulation Engineering',
    description: 'Modeling, analysis and validation',
    items: [
      {
        name: 'Dossier Management',
        href: '/simulation/dossiers',
        icon: FileText,
        badge: 'SDD',
        description: 'AP243 simulation data dossiers',
      },
      {
        name: 'Simulation Runs',
        href: '/simulation/runs',
        icon: Activity,
        badge: null,
        description: 'Track simulation executions',
      },
      {
        name: 'Model Repository',
        href: '/simulation/models',
        icon: Boxes,
        badge: null,
        description: 'Simulation model library',
      },
      {
        name: 'Workflow Studio',
        href: '/simulation/workflows',
        icon: Workflow,
        badge: null,
        description: 'Design and execute workflows',
      },
      {
        name: 'Results Analysis',
        href: '/simulation/results',
        icon: TrendingUp,
        badge: null,
        description: 'Analyze simulation outputs',
      },
    ],
  },
  {
    label: 'Data Management',
    description: 'Import, export and integration',
    items: [
      {
        name: 'Data Import',
        href: '/import',
        icon: Upload,
        badge: null,
        description: 'Upload XMI, XML, CSV files',
      },
      {
        name: 'PLM Integration',
        href: '/plm',
        icon: Database,
        badge: null,
        description: 'Sync with external PLM',
      },
      {
        name: 'REST API',
        href: '/api-explorer',
        icon: Code,
        badge: null,
        description: 'API documentation and testing',
      },
    ],
  },
  {
    label: 'System',
    description: 'Monitoring and administration',
    items: [
      {
        name: 'System Health',
        href: '/monitoring',
        icon: Activity,
        badge: null,
        description: 'Performance and diagnostics',
      },
    ],
  },
];

export default function Layout({ children }) {
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const displayName = user?.name || user?.username || 'Guest User';
  const displayRole = user?.role || 'Engineer';
  const initials = displayName.split(' ').map(n => n[0]).join('').toUpperCase() || 'GU';

  return (
    <div className="flex h-screen bg-slate-50">
      <aside
        className="w-64 bg-slate-900 text-white flex flex-col h-screen fixed left-0 top-0 z-40 border-r border-slate-800"
        role="navigation"
        aria-label="Main navigation sidebar"
      >
        <div className="flex h-full flex-col">
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

          <nav className="flex-1 p-4 space-y-2 mt-4 overflow-y-auto">
            {navigationGroups.map((group, groupIndex) => (
              <div key={group.label || groupIndex}>
                {group.items.map((item) => {
                  const isActive = location.pathname === item.href;
                  return (
                    <Link
                      key={item.href || item.name}
                      to={item.href}
                      aria-label={`${item.name}: ${item.description}`}
                      className={cn(
                        'w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group',
                        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#004A99]',
                        isActive
                          ? 'bg-[#004A99] text-white shadow-lg shadow-blue-900/40'
                          : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                      )}
                      aria-current={isActive ? 'page' : undefined}
                      title={item.description}
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

      <main className="flex-1 flex flex-col overflow-hidden ml-64" role="main" aria-label="Main content">
        <header
          className="h-16 bg-white border-b border-slate-200 px-8 flex items-center justify-between sticky top-0 z-30 shadow-sm"
          role="banner"
          aria-label="Page header"
        >
          <div className="flex items-center gap-4 flex-1 min-w-0">
            <div className="relative group">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#004A99]" size={16} />
              <input 
                type="text" 
                placeholder="Search dossiers, requirements, or motor IDs..." 
                className="pl-10 pr-4 py-2 bg-slate-100 border-none rounded-full text-sm w-80 focus:ring-2 focus:ring-[#004A99] focus:bg-white transition-all outline-none" 
              />
            </div>
          </div>

          <div className="flex items-center gap-6">
            <button 
              onClick={() => setIsNotificationsOpen(!isNotificationsOpen)}
              className="relative p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <Bell size={20} />
              <span className="absolute top-2 right-2 w-2 h-2 bg-rose-500 rounded-full border-2 border-white"></span>
            </button>

            <div className="flex items-center gap-3 border-l border-slate-200 pl-6">
              <div className="text-right hidden sm:block">
                <p className="text-sm font-bold text-slate-800">
                  {displayName}
                </p>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">
                  {displayRole}
                </p>
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
          <div className="container mx-auto p-8 max-w-400">
            <div className="animate-in fade-in slide-in-from-bottom-2 duration-500">
              {children}
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
    </div>
  );
}
