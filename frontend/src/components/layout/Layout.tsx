import { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { Button } from '@ui/button';
import { ScrollArea } from '@ui/scroll-area';
import { Badge } from '@ui/badge';
import { Separator } from '@ui/separator';
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
  ChevronRight,
  Info,
  Settings,
  ClipboardCheck,
  Package,
  Library,
  Network,
} from 'lucide-react';

interface LayoutProps {
  children: ReactNode;
}

// IxDF HMI Principle: Group navigation by task context and frequency of use
const navigationGroups = [
  {
    label: 'Core Operations',
    description: 'Primary tasks and system overview',
    items: [
      { 
        name: 'Dashboard', 
        href: '/dashboard', 
        icon: LayoutDashboard, 
        badge: null,
        description: 'System overview and metrics'
      },
      { 
        name: 'Search', 
        href: '/search', 
        icon: Search, 
        badge: null,
        description: 'Find artifacts and components'
      },
    ],
  },
  {
    label: 'Engineering Workspace',
    description: 'Design and development tools',
    items: [
      { 
        name: 'Requirements', 
        href: '/requirements', 
        icon: FileText, 
        badge: null,
        description: 'Manage requirements'
      },
      { 
        name: 'Traceability', 
        href: '/traceability', 
        icon: GitBranch, 
        badge: null,
        description: 'Trace relationships'
      },
      { 
        name: 'Graph Browser', 
        href: '/graph', 
        icon: Network, 
        badge: 'NEW',
        description: 'Visualize knowledge graph'
      },
      { 
        name: 'Query Editor', 
        href: '/query-editor', 
        icon: Terminal, 
        badge: 'BETA',
        description: 'Run custom Cypher queries'
      },
    ],
  },
  {
    label: 'ISO AP239 - Requirements',
    description: 'Product Life Cycle Support',
    items: [
      { 
        name: 'Requirements', 
        href: '/ap239/requirements', 
        icon: ClipboardCheck, 
        badge: 'AP239',
        description: 'Requirements & Analysis'
      },
    ],
  },
  {
    label: 'ISO AP242 - Engineering',
    description: '3D Engineering & Manufacturing',
    items: [
      { 
        name: 'Parts Explorer', 
        href: '/ap242/parts', 
        icon: Package, 
        badge: 'AP242',
        description: 'Parts, Materials & CAD'
      },
    ],
  },
  {
    label: 'Integration & System',
    description: 'External connections and monitoring',
    items: [
      { 
        name: 'REST API', 
        href: '/api-explorer', 
        icon: Code, 
        badge: 'API',
        description: 'API documentation'
      },
      { 
        name: 'PLM Sync', 
        href: '/plm', 
        icon: Database, 
        badge: null,
        description: 'PLM integration'
      },
      { 
        name: 'Monitoring', 
        href: '/monitoring', 
        icon: Activity, 
        badge: null,
        description: 'System health & performance'
      },
    ],
  },
];

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();

  return (
    <div className="flex h-screen bg-gradient-to-br from-background via-background to-muted/10">
      {/* Sidebar - IxDF: Clear visual hierarchy, consistent spacing, accessible navigation */}
      <aside className="w-72 border-r bg-background shadow-xl">
        <div className="flex h-full flex-col">
          {/* Logo Zone - HMI: High contrast, clear branding, immediate context */}
          <div className="flex h-20 items-center border-b px-6 bg-gradient-to-br from-primary/5 via-primary/3 to-background">
            <div className="flex items-center gap-3">
              <div className="rounded-xl bg-primary p-2.5 shadow-lg">
                <Database className="h-6 w-6 text-primary-foreground" />
              </div>
              <div>
                <h1 className="text-lg font-bold tracking-tight">MBSE-Led</h1>
                <p className="text-xs text-muted-foreground font-medium">Simulation Engineering</p>
              </div>
            </div>
          </div>

          {/* Navigation Zone - IxDF: Grouped by context, scannable, accessible */}
          <ScrollArea className="flex-1 px-4 py-6">
            <nav className="space-y-6" aria-label="Main navigation">
              {navigationGroups.map((group, groupIndex) => (
                <div key={groupIndex}>
                  {/* Group Label - HMI: Clear section headers for mental model */}
                  <div className="mb-3 px-3">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      {group.label}
                    </h3>
                    <p className="text-[10px] text-muted-foreground/70 mt-0.5">
                      {group.description}
                    </p>
                  </div>
                  
                  {/* Navigation Items - IxDF: Large touch targets, clear affordances, immediate feedback */}
                  <div className="space-y-1">
                    {group.items.map((item) => {
                      const isActive = location.pathname === item.href;
                      return (
                        <Link
                          key={item.name}
                          to={item.href}
                          className={cn(
                            'group relative flex items-center gap-3 rounded-xl px-4 py-3.5 text-sm font-medium transition-all duration-200',
                            'hover:shadow-md hover:scale-[1.02] active:scale-[0.98]',
                            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
                            isActive
                              ? 'bg-primary text-primary-foreground shadow-lg'
                              : 'text-foreground hover:bg-accent hover:text-accent-foreground'
                          )}
                          aria-current={isActive ? 'page' : undefined}
                          title={item.description}
                        >
                          {/* Icon - Enhanced visibility and feedback */}
                          <item.icon className={cn(
                            'h-5 w-5 flex-shrink-0 transition-transform group-hover:scale-110',
                            isActive ? 'text-primary-foreground' : 'text-muted-foreground group-hover:text-accent-foreground'
                          )} />
                          
                          {/* Label with badge */}
                          <div className="flex-1 min-w-0 flex items-center gap-2">
                            <span className="truncate">{item.name}</span>
                            {item.badge && (
                              <Badge 
                                variant={isActive ? "secondary" : "outline"} 
                                className="text-[10px] px-2 py-0.5 font-semibold"
                              >
                                {item.badge}
                              </Badge>
                            )}
                          </div>
                          
                          {/* Active indicator - Clear visual feedback */}
                          {isActive && (
                            <ChevronRight className="h-4 w-4 flex-shrink-0 text-primary-foreground" />
                          )}
                        </Link>
                      );
                    })}
                  </div>
                  
                  {/* Visual separator - Clear grouping */}
                  {groupIndex < navigationGroups.length - 1 && (
                    <Separator className="mt-6" />
                  )}
                </div>
              ))}
            </nav>
          </ScrollArea>

          {/* Status Footer - IxDF: Clear system status, always visible */}
          <div className="border-t bg-muted/30 p-4">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <div className="relative">
                  <Activity className="h-4 w-4 text-green-500" />
                  <div className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                </div>
                <div>
                  <div className="font-semibold text-foreground">System Active</div>
                  <div className="text-muted-foreground">All services running</div>
                </div>
              </div>
              <Badge variant="outline" className="font-mono text-[10px]">v2.0</Badge>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header - IxDF: Consistent height, clear zones, accessible controls */}
        <header className="sticky top-0 z-40 border-b bg-background/98 backdrop-blur-md shadow-sm">
          <div className="container mx-auto flex h-20 items-center justify-between px-8">
            {/* Context Information - F-pattern: Important info top-left */}
            <div className="flex items-center gap-4 flex-1 min-w-0">
              <div className="flex items-center gap-3">
                <div className="relative">
                  <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-primary to-primary/80 flex items-center justify-center shadow-md">
                    <Zap className="h-5 w-5 text-primary-foreground" />
                  </div>
                  <div className="absolute -bottom-1 -right-1 h-3 w-3 rounded-full bg-green-500 border-2 border-background animate-pulse" />
                </div>
                <div className="min-w-0">
                  <div className="text-base font-semibold truncate">MBSE-Led Platform</div>
                  <div className="text-xs text-muted-foreground font-medium">Simulation Engineering Collaboration</div>
                </div>
              </div>
            </div>
            
            {/* Action Zone - HMI: High visibility controls, consistent placement */}
            <div className="flex items-center gap-4">
              {/* System Status - Always visible indicator */}
              <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-green-500/10 border border-green-500/20">
                <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                <span className="text-xs font-medium text-green-700 dark:text-green-400">Online</span>
              </div>
              
              {/* Theme Toggle - Accessibility */}
              <ModeToggle />
              
              {/* User Menu - Clear affordance */}
              <UserMenu />
            </div>
          </div>
        </header>

        {/* Content Area - IxDF: Consistent margins, clear focus area */}
        <div className="flex-1 overflow-y-auto">
          <div className="container mx-auto p-8 max-w-[1600px]">
            {/* Content with smooth entrance - Reduced motion respected */}
            <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
              {children}
            </div>
          </div>
        </div>
        
        {/* Footer - Optional system info, non-intrusive */}
        <footer className="border-t bg-muted/20 py-4">
          <div className="container mx-auto px-8 flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center gap-4">
              <span>© 2025 MBSE-Led Platform</span>
              <Separator orientation="vertical" className="h-4" />
              <span>Distributed Infrastructure</span>
            </div>
            <div className="flex items-center gap-2">
              <Info className="h-3 w-3" />
              <span>ISO 10303 SMRL Compliant</span>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
}
