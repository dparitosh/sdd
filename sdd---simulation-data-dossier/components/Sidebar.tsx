
import React from 'react';
import { 
  LayoutDashboard, 
  FileBox, 
  Settings, 
  ShieldCheck, 
  FileSearch,
  BookOpen,
  HelpCircle,
  Database,
  LucideIcon
} from 'lucide-react';
import { UserRole, DossierStatus, Dossier } from '../types';

interface SidebarProps {
  role: UserRole;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  dossiers: Dossier[];
}

interface MenuItem {
  id: string;
  label: string;
  icon: LucideIcon;
  badge?: number;
}

const Sidebar: React.FC<SidebarProps> = ({ role, activeTab, setActiveTab, dossiers }) => {
  const pendingCount = dossiers.filter(d => d.status === DossierStatus.PENDING_REVIEW).length;

  const engineerMenu: MenuItem[] = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'specs', label: 'Product Specs', icon: BookOpen },
    { id: 'workspace', label: 'Sim Workspace', icon: Database },
    { id: 'dossiers', label: 'My Dossiers', icon: FileBox },
  ];

  const qualityMenu: MenuItem[] = [
    { id: 'approvals', label: 'Approval Queue', icon: ShieldCheck, badge: pendingCount },
    { id: 'reports', label: 'Compliance Reports', icon: FileSearch },
    { id: 'analytics', label: 'Metrics Dashboard', icon: LayoutDashboard },
  ];

  const menu = role === UserRole.SIMULATION_ENGINEER ? engineerMenu : qualityMenu;

  return (
    <aside className="w-64 bg-slate-900 text-white flex flex-col h-screen fixed left-0 top-0 z-40 border-r border-slate-800">
      <div className="p-6 border-b border-slate-800 bg-slate-900">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-9 h-9 bg-[#004A99] rounded-lg flex items-center justify-center font-black text-white text-xs shadow-lg shadow-blue-500/10">
            TCS
          </div>
          <div>
            <span className="font-black text-sm tracking-tight block leading-none">SDD APP</span>
            <span className="text-[8px] text-slate-500 font-black uppercase tracking-widest mt-1 block">Enterprise Sim</span>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-2 mt-4 overflow-y-auto">
        {menu.map((item) => (
          <button
            key={item.id}
            onClick={() => setActiveTab(item.id)}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group ${
              activeTab === item.id 
                ? 'bg-[#004A99] text-white shadow-lg shadow-blue-900/40' 
                : 'text-slate-400 hover:bg-slate-800 hover:text-white'
            }`}
          >
            <item.icon size={18} />
            <span className="font-bold text-xs flex-1 text-left uppercase tracking-widest">{item.label}</span>
            {item.badge !== undefined && item.badge > 0 && (
              <span className="bg-[#00B0E4] text-white text-[9px] font-black px-1.5 py-0.5 rounded-full min-w-[18px] text-center shadow-lg shadow-blue-500/20">
                {item.badge}
              </span>
            )}
          </button>
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
        <button className="w-full flex items-center gap-3 px-2 py-2 text-slate-500 hover:text-white text-xs font-bold transition-colors uppercase tracking-widest">
          <Settings size={14} />
          <span>Config</span>
        </button>
        <button className="w-full flex items-center gap-3 px-2 py-2 text-slate-500 hover:text-white text-xs font-bold transition-colors uppercase tracking-widest">
          <HelpCircle size={14} />
          <span>Support</span>
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
