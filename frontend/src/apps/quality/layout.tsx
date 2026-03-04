import { Link, useLocation, Outlet } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { Badge } from '@ui/badge';
import { Separator } from '@ui/separator';
import RoleSelector from '@/features/auth/components/RoleSelector';
import { useAuthStore } from '@/stores/authStore';
import { useState } from 'react';
import {
  ClipboardCheck,
  BarChart3,
  ShieldCheck,
  GitBranch,
  RefreshCw,
  FileText,
  Activity,
  Info,
  Bell,
  Search,
  UserCircle2,
  LogOut,
} from 'lucide-react';

const navigationItems = [
  { name: 'PENDING REVIEWS', href: '/quality', icon: ClipboardCheck, badge: 'QUEUE' },
  { name: 'QUALITY OVERVIEW', href: '/quality/dashboard', icon: BarChart3 },
  { name: 'AUDIT REPORTS', href: '/quality/audit', icon: ShieldCheck },
  { name: 'TRACEABILITY MATRIX', href: '/quality/traceability', icon: GitBranch },
  { name: 'DOSSIER HISTORY', href: '/quality/dossiers', icon: FileText },
  { name: 'ACTIVITY FEED', href: '/quality/feed', icon: RefreshCw },
];

export default function QualityLayout() {
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const [showUserMenu, setShowUserMenu] = useState(false);

  const handleLogout = () => {
    logout();
  };

  const displayName = user?.name || user?.email?.split('@')[0] || 'User';
  const displayRole = 'Quality Head';

  return (
    <div className="flex h-screen bg-slate-50">
      {/* Sidebar */}
      <aside className="fixed inset-y-0 left-0 z-50 w-64 bg-slate-900 border-r border-slate-800 flex flex-col">
        {/* Sidebar Header */}
        <div className="h-16 px-6 flex items-center gap-3 border-b border-slate-800">
          <div className="w-9 h-9 rounded bg-[#004A99] flex items-center justify-center shrink-0 shadow-lg shadow-blue-900/40">
            <span className="text-white font-black text-xl tracking-tighter">TCS</span>
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-white font-bold text-sm tracking-wide truncate">SDD PLATFORM</h1>
            <p className="text-slate-400 text-xs truncate">Quality Control</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-4 py-6">
          <div className="space-y-2">
            {navigationItems.map((item) => {
              const isActive = location.pathname === item.href;
              return (
                <Link
                  key={item.href}
                  to={item.href}
                  className={cn(
                    'flex items-center gap-3 px-4 py-3 rounded-lg text-xs font-bold uppercase tracking-widest transition-all duration-200',
                    isActive
                      ? 'bg-[#004A99] text-white shadow-lg shadow-blue-900/40'
                      : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                  )}
                >
                  <item.icon className="h-4 w-4 shrink-0" />
                  <span className="flex-1 truncate">{item.name}</span>
                  {item.badge && (
                    <Badge className="bg-[#00B0E4] text-white text-[10px] px-2 py-0.5 border-0">
                      {item.badge}
                    </Badge>
                  )}
                </Link>
              );
            })}
          </div>
        </nav>

        {/* Sidebar Footer */}
        <div className="p-4 border-t border-slate-800">
          <div className="bg-slate-800/50 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-2">
              <div className="relative">
                <Activity className="h-4 w-4 text-green-400" />
                <div className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-green-400 animate-pulse" />
              </div>
              <span className="text-xs font-semibold text-white">System Operational</span>
            </div>
            <div className="flex items-center justify-between text-[10px] text-slate-400">
              <span>v4.1.0-ENTERPRISE</span>
              <span>ISO 17025 / MOSSEC</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="ml-64 flex-1 flex flex-col">
        {/* Header */}
        <header className="sticky top-0 z-40 bg-white border-b border-slate-200 h-16">
          <div className="h-full px-8 flex items-center justify-between">
            {/* Search Bar */}
            <div className="flex-1 max-w-xl">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <input
                  type="search"
                  placeholder="Search quality items, audits, compliance..."
                  className="w-full pl-10 pr-4 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#004A99] focus:border-transparent"
                />
              </div>
            </div>

            {/* Right Section */}
            <div className="flex items-center gap-4 ml-6">
              <RoleSelector />
              
              {/* Notification Bell */}
              <button 
                className="relative p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors"
                title="Notifications"
              >
                <Bell className="h-5 w-5" />
                <span className="absolute top-1 right-1 h-2 w-2 bg-red-500 rounded-full" />
              </button>

              {/* User Section */}
              <div className="flex items-center gap-3 pl-4 border-l border-slate-200">
                <div className="text-right">
                  <div className="text-sm font-semibold text-slate-900">{displayName}</div>
                  <div className="text-xs text-slate-500">{displayRole}</div>
                </div>
                <div className="h-9 w-9 rounded-full bg-[#004A99] flex items-center justify-center">
                  <UserCircle2 className="h-5 w-5 text-white" />
                </div>
                <button
                  onClick={handleLogout}
                  className="p-2 text-slate-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  title="Logout"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 overflow-y-auto">
          <div className="p-8 max-w-[1600px] mx-auto">
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <Outlet />
            </div>
          </div>
        </main>

        {/* Footer */}
        <footer className="border-t border-slate-200 bg-slate-100 py-4">
          <div className="px-8 flex items-center justify-between text-xs">
            <div className="flex items-center gap-4 text-slate-600">
              <span>© 2025 TCS - Simulation Data Dossier Platform</span>
              <Separator orientation="vertical" className="h-4" />
              <span>Quality Compliance</span>
            </div>
            <div className="flex items-center gap-2 text-slate-500">
              <Info className="h-3 w-3" />
              <span>ISO 10303 SMRL / IEC 6034 Compliant</span>
            </div>
          </div>
        </footer>
      </div>

    </div>
  );
}
