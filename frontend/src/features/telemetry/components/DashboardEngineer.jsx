import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@ui/card';
import { Badge } from '@ui/badge';
import { Skeleton } from '@ui/skeleton';
import { Alert, AlertDescription } from '@ui/alert';
import { Progress } from '@ui/progress';
import PageHeader from '@/components/PageHeader';
import {
  FileText,
  HeartPulse,
  Play,
  ClipboardCheck,
  Clock,
  ArrowUpRight,
  BarChart3,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { useKPIs, useDossierHealth } from '../hooks/useMetrics';

const EVIDENCE_LABELS = ['A1 Geometry', 'B1 Mesh', 'C1 Solver', 'D1 Results', 'E1 Post', 'F1 V&V', 'G1 Review', 'H1 Cert'];

function KPICard({ icon: Icon, label, value, subtitle, color = 'primary' }) {
  const colorMap = {
    primary: 'from-blue-500 to-blue-600',
    green: 'from-green-500 to-green-600',
    amber: 'from-amber-500 to-amber-600',
    purple: 'from-purple-500 to-purple-600',
  };
  return (
    <Card className="overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
        <div className={`h-9 w-9 rounded-lg bg-gradient-to-br ${colorMap[color] || colorMap.primary} flex items-center justify-center`}>
          <Icon className="h-5 w-5 text-white" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-bold">{value}</div>
        {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
      </CardContent>
    </Card>
  );
}

export default function DashboardEngineer() {
  const { kpis, isLoading: kpiLoading, error: kpiError } = useKPIs();
  const { healthData, convergenceData, evidenceSummary, isLoading: healthLoading } = useDossierHealth();

  if (kpiLoading || healthLoading) {
    return (
      <div className="container mx-auto p-6 space-y-6">
        <PageHeader
          title="Engineer Dashboard"
          description="KPIs, health analytics, and evidence pipeline overview"
          icon={<BarChart3 className="h-6 w-6 text-primary" />}
        />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardHeader className="pb-2"><Skeleton className="h-4 w-24" /></CardHeader>
              <CardContent><Skeleton className="h-8 w-16" /></CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (kpiError) {
    return (
      <div className="container mx-auto p-6 space-y-6">
        <PageHeader
          title="Engineer Dashboard"
          description="KPIs, health analytics, and evidence pipeline overview"
          icon={<BarChart3 className="h-6 w-6 text-primary" />}
        />
        <Alert variant="destructive">
          <AlertDescription>Failed to load dashboard data. Check your connection and try again.</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <PageHeader
        title="Engineer Dashboard"
        description="KPIs, health analytics, and evidence pipeline overview"
        icon={<BarChart3 className="h-6 w-6 text-primary" />}
      />

      {/* KPI cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KPICard icon={FileText} label="Total Dossiers" value={kpis.totalDossiers} subtitle="All simulation dossiers" color="primary" />
        <KPICard icon={HeartPulse} label="Avg. Health Score" value={`${kpis.avgHealthScore}%`} subtitle="Across active dossiers" color="green" />
        <KPICard icon={Play} label="Active Simulations" value={kpis.activeSimulations} subtitle="Currently running" color="amber" />
        <KPICard icon={ClipboardCheck} label="Pending Reviews" value={kpis.pendingReviews} subtitle="Awaiting approval" color="purple" />
      </div>

      {/* Charts row */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Health score bar chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Dossier Health Scores</CardTitle>
            <CardDescription>Health score per dossier (0–100)</CardDescription>
          </CardHeader>
          <CardContent>
            {healthData.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">No dossier data available</p>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={healthData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="score" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Convergence trend line chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Convergence Trend</CardTitle>
            <CardDescription>Health score over simulation iterations</CardDescription>
          </CardHeader>
          <CardContent>
            {convergenceData.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">No convergence data available</p>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={convergenceData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="iteration" tick={{ fontSize: 12 }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="score" stroke="hsl(var(--primary))" strokeWidth={2} dot={{ r: 3 }} name="Health Score" />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Evidence pipeline summary */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Evidence Pipeline Summary</CardTitle>
          <CardDescription>Aggregate completion across all dossiers (A1–H1)</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {evidenceSummary.map((item, idx) => (
            <div key={idx} className="flex items-center gap-4">
              <span className="w-28 text-sm font-medium truncate">{EVIDENCE_LABELS[idx] ?? item.code}</span>
              <Progress value={item.percent} className="flex-1" />
              <span className="text-sm text-muted-foreground w-12 text-right">{item.percent}%</span>
            </div>
          ))}
          {evidenceSummary.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-4">No evidence data available</p>
          )}
        </CardContent>
      </Card>

      {/* Recent activity */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent Activity</CardTitle>
          <CardDescription>Latest dossier and simulation events</CardDescription>
        </CardHeader>
        <CardContent>
          {kpis.recentActivity.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">No recent activity</p>
          ) : (
            <ul className="space-y-3">
              {kpis.recentActivity.map((event, idx) => (
                <li key={idx} className="flex items-start gap-3 text-sm">
                  <Clock className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
                  <div className="flex-1">
                    <span className="font-medium">{event.label}</span>
                    {event.detail && <span className="text-muted-foreground"> — {event.detail}</span>}
                  </div>
                  {event.timestamp && (
                    <span className="text-xs text-muted-foreground whitespace-nowrap">{event.timestamp}</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
