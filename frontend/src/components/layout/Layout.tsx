import { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { Button } from '@ui/button';
import { ScrollArea } from '@ui/scroll-area';
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
} from 'lucide-react';

interface LayoutProps {
  children: ReactNode;
}

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Advanced Search', href: '/search', icon: Search },
  { name: 'REST API', href: '/api-explorer', icon: Code },
  { name: 'Query Editor', href: '/query-editor', icon: Terminal },
  { name: 'Requirements', href: '/requirements', icon: FileText },
  { name: 'Traceability', href: '/traceability', icon: GitBranch },
  { name: 'PLM Integration', href: '/plm', icon: Database },
  { name: 'Monitoring', href: '/monitoring', icon: Activity },
];

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside className="w-64 border-r bg-card">
        <div className="flex h-full flex-col">
          {/* Logo */}
          <div className="flex h-16 items-center border-b px-6">
            <h1 className="text-xl font-bold">MBSE Knowledge Graph</h1>
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
                        'w-full justify-start',
                        isActive && 'bg-secondary'
                      )}
                    >
                      <item.icon className="mr-2 h-4 w-4" />
                      {item.name}
                    </Button>
                  </Link>
                );
              })}
            </nav>
          </ScrollArea>

          {/* Footer */}
          <div className="border-t p-4">
            <div className="flex items-center justify-center">
              <span className="text-sm text-muted-foreground">v2.0.0 - Phase 2</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        {/* Top Bar */}
        <div className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="container mx-auto flex h-16 items-center justify-between px-6">
            <div className="text-sm text-muted-foreground">
              MBSE Knowledge Graph Platform
            </div>
            <div className="flex items-center gap-4">
              <ModeToggle />
              <UserMenu />
            </div>
          </div>
        </div>
        
        {/* Content */}
        <div className="container mx-auto p-6">{children}</div>
      </main>
    </div>
  );
}
