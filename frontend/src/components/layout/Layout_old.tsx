import { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { Button } from '@ui/button';
import { ScrollArea } from '@ui/scroll-area';
import { Badge } from '@ui/badge';
import { ModeToggle } from '@/components/mode-toggle';
import UserMenu from '@/components/auth/UserMenu';
import {
  LayoutDashboard,
  Search,
  Code,
  Terminal,
  FileText,
  GitBranch,
  Database,
  Activity,
  Zap,
} from 'lucide-react';

interface LayoutProps {
  children: ReactNode;
}

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, badge: null },
  { name: 'Advanced Search', href: '/search', icon: Search, badge: null },
  { name: 'REST API', href: '/api-explorer', icon: Code, badge: 'API' },
  { name: 'Query Editor', href: '/query-editor', icon: Terminal, badge: null },
  { name: 'Requirements', href: '/requirements', icon: FileText, badge: null },
  { name: 'Traceability', href: '/traceability', icon: GitBranch, badge: null },
  { name: 'PLM Integration', href: '/plm', icon: Database, badge: 'BETA' },
  { name: 'Monitoring', href: '/monitoring', icon: Activity, badge: null },
];

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();

  return (
    <div className="flex h-screen bg-gradient-to-br from-background via-background to-muted/20">
      {/* Sidebar */}
      <aside className="w-64 border-r bg-card/50 backdrop-blur-xl shadow-lg">
        <div className="flex h-full flex-col">
          {/* Logo */}
          <div className="flex h-16 items-center border-b px-6 bg-gradient-to-r from-primary/10 to-primary/5">
            <div className="flex items-center gap-2">
              <div className="rounded-lg bg-primary p-1.5">
                <Database className="h-5 w-5 text-primary-foreground" />
              </div>
              <div>
                <h1 className="text-base font-bold leading-tight">MBSE-Led</h1>
                <p className="text-xs text-muted-foreground">Simulation Collaboration</p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <ScrollArea className="flex-1 px-3 py-4">
            <nav className="space-y-1">
              {navigation.map((item) => {
                const isActive = location.pathname === item.href;
                return (
                  <Link key={item.name} to={item.href}>
                    <Button
                      variant={isActive ? 'secondary' : 'ghost'}
                      className={cn(
                        'w-full justify-start group transition-all duration-200',
                        isActive && 'bg-primary text-primary-foreground shadow-md',
                        !isActive && 'hover:bg-muted hover:translate-x-1'
                      )}
                    >
                      <item.icon className={cn(
                        "mr-2 h-4 w-4 transition-transform",
                        isActive && "scale-110"
                      )} />
                      <span className="flex-1 text-left">{item.name}</span>
                      {item.badge && (
                        <Badge variant="secondary" className="ml-auto text-xs">
                          {item.badge}
                        </Badge>
                      )}
                    </Button>
                  </Link>
                );
              })}
            </nav>
          </ScrollArea>

          {/* Footer */}
          <div className="border-t p-4 bg-muted/30">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">v2.0.0 • Phase 2</span>
              <div className="flex items-center gap-1">
                <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                <span className="text-xs text-muted-foreground">Live</span>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        {/* Top Bar */}
        <div className="sticky top-0 z-10 border-b bg-background/80 backdrop-blur-md supports-[backdrop-filter]:bg-background/60 shadow-sm">
          <div className="container mx-auto flex h-16 items-center justify-between px-6">
            <div className="flex items-center gap-3">
              <Zap className="h-5 w-5 text-primary animate-pulse" />
              <div>
                <div className="text-sm font-medium">MBSE-Led Simulation Engineering Collaboration</div>
                <div className="text-xs text-muted-foreground">Distributed Infrastructure • Multi-Tool Integration</div>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <ModeToggle />
              <UserMenu />
            </div>
          </div>
        </div>
        
        {/* Content */}
        <div className="container mx-auto p-6">
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            {children}
          </div>
        </div>
      </main>
    </div>
  );
}
