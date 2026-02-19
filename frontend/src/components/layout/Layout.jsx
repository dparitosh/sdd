import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
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
      {
        name: 'Search & Discovery',
        href: '/search',
        icon: Search,
        badge: null,
        description: 'Intelligent search across knowledge graph',
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

  return (
    <div className="flex h-screen bg-linear-to-br from-background via-background to-muted/10">
      <aside
        className="w-72 border-r bg-background shadow-xl"
        role="navigation"
        aria-label="Main navigation sidebar"
      >
        <div className="flex h-full flex-col">
          <div className="flex h-20 items-center border-b px-6 bg-linear-to-br from-primary/5 via-primary/3 to-background">
            <div className="flex items-center gap-3">
              <div className="rounded-xl bg-linear-to-br from-primary to-primary/80 p-2.5 shadow-lg relative overflow-hidden">
                <Network className="h-6 w-6 text-primary-foreground relative z-10" />
                <div className="absolute inset-0 bg-linear-to-tr from-white/10 to-transparent" />
              </div>
              <div>
                <h1 className="text-lg font-bold tracking-tight bg-linear-to-r from-primary to-primary/70 bg-clip-text text-transparent">
                  KnowledgeGraph AI
                </h1>
                <p className="text-xs text-muted-foreground font-medium">
                  Simulation Engineering Platform
                </p>
              </div>
            </div>
          </div>

          <ScrollArea className="flex-1 px-4 py-6">
            <nav className="space-y-6" aria-label="Main navigation">
              {navigationGroups.map((group, groupIndex) => (
                <div key={group.label || groupIndex}>
                  <div className="mb-3 px-3">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      {group.label}
                    </h3>
                    <p className="text-[10px] text-muted-foreground/70 mt-0.5">
                      {group.description}
                    </p>
                  </div>

                  <div className="space-y-1">
                    {group.items.map((item) => {
                      const isActive = location.pathname === item.href;
                      return (
                        <Link
                          key={item.href || item.name}
                          to={item.href}
                          aria-label={`${item.name}: ${item.description}`}
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
                          <item.icon
                            className={cn(
                              'h-5 w-5 shrink-0 transition-transform group-hover:scale-110',
                              isActive
                                ? 'text-primary-foreground'
                                : 'text-muted-foreground group-hover:text-accent-foreground'
                            )}
                          />
                          <div className="flex-1 min-w-0 flex items-center gap-2">
                            <span className="truncate">{item.name}</span>
                            {item.badge && (
                              <Badge
                                variant={isActive ? 'secondary' : 'outline'}
                                className="text-[10px] px-2 py-0.5 font-semibold"
                              >
                                {item.badge}
                              </Badge>
                            )}
                          </div>
                          {isActive && (
                            <ChevronRight className="h-4 w-4 shrink-0 text-primary-foreground" />
                          )}
                        </Link>
                      );
                    })}
                  </div>

                  {groupIndex < navigationGroups.length - 1 && (
                    <Separator className="mt-6" />
                  )}
                </div>
              ))}
            </nav>
          </ScrollArea>

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
              <Badge variant="outline" className="font-mono text-[10px]">
                v2.0
              </Badge>
            </div>
          </div>
        </div>
      </aside>

      <main className="flex-1 flex flex-col overflow-hidden" role="main" aria-label="Main content">
        <header
          className="sticky top-0 z-40 border-b bg-background/98 backdrop-blur-md shadow-sm"
          role="banner"
          aria-label="Page header"
        >
          <div className="container mx-auto flex h-20 items-center justify-between px-8">
            <div className="flex items-center gap-4 flex-1 min-w-0">
              <div className="flex items-center gap-3">
                <div className="relative">
                  <div className="h-10 w-10 rounded-xl bg-linear-to-br from-primary to-primary/80 flex items-center justify-center shadow-md">
                    <Zap className="h-5 w-5 text-primary-foreground" />
                  </div>
                  <div className="absolute -bottom-1 -right-1 h-3 w-3 rounded-full bg-green-500 border-2 border-background animate-pulse" />
                </div>
                <div className="min-w-0">
                  <div className="text-base font-semibold truncate">MBSE-Led Platform</div>
                  <div className="text-xs text-muted-foreground font-medium">
                    Simulation Engineering Collaboration
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div
                className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-green-500/10 border border-green-500/20"
                role="status"
                aria-label="System status: Online"
              >
                <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                <span className="text-xs font-medium text-green-700 dark:text-green-400">
                  Online
                </span>
              </div>
              <ModeToggle />
              <UserMenu />
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto">
          <div className="container mx-auto p-8 max-w-[1600px]">
            <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
              {children}
            </div>
          </div>
        </div>

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
