/** Telemetry hooks — useKPIs, useDossierHealth, useApprovalQueue */
import { useQuery } from '@tanstack/react-query';
import * as sddService from '@/services/sdd.service';
import * as simService from '@/services/simulation.service';

/* -------------------------------------------------------------------------- */
/*  Types                                                                      */
/* -------------------------------------------------------------------------- */

interface KPIs {
  totalDossiers: number;
  avgHealthScore: number;
  activeSimulations: number;
  pendingReviews: number;
  statusDistribution: { status: string; count: number }[];
  certProgress: { iso10303: number; mossec: number; asme: number; nafems: number };
  recentActivity: { label: string; detail?: string; timestamp?: string }[];
}

interface HealthDatum {
  id?: string;
  name: string;
  score: number;
}

interface ConvergenceDatum {
  iteration: number;
  score: number;
}

interface EvidenceSummaryItem {
  code: string;
  percent: number;
}

interface QueueItem {
  id: string;
  name: string;
  score: number;
  status: string;
}

interface WeeklyThroughput {
  week: string;
  approved: number;
  rejected: number;
}

/* -------------------------------------------------------------------------- */
/*  useKPIs — aggregates dossier + simulation statistics                       */
/* -------------------------------------------------------------------------- */

export function useKPIs() {
  const { data: stats, isLoading: statsLoading, error: statsError } = useQuery({
    queryKey: ['sdd-statistics'],
    queryFn: sddService.getDossierStatistics,
    staleTime: 30_000,
  });

  const { data: runsData, isLoading: runsLoading } = useQuery({
    queryKey: ['simulation-runs-kpi'],
    queryFn: () => simService.getRuns({ run_status: 'running', limit: 100 }),
    staleTime: 15_000,
  });

  const { data: dossiersData, isLoading: dossiersLoading } = useQuery({
    queryKey: ['dossiers-kpi'],
    queryFn: () => sddService.getDossiers({ limit: 200 }),
    staleTime: 30_000,
  });

  const dossiers: any[] = (dossiersData as any)?.dossiers ?? [];
  const runs: any[] = Array.isArray(runsData) ? runsData : [];
  const statObj = (stats ?? {}) as Record<string, any>;

  // Compute status distribution
  const statusMap: Record<string, number> = {};
  for (const d of dossiers) {
    const s = d.status ?? 'Draft';
    statusMap[s] = (statusMap[s] ?? 0) + 1;
  }
  const statusDistribution = Object.entries(statusMap).map(([status, count]) => ({ status, count }));

  // Compute average health score
  const scores = dossiers.map((d: any) => d.health_score ?? d.healthScore).filter((v: any) => typeof v === 'number');
  const avgHealthScore = scores.length > 0 ? Math.round(scores.reduce((a: number, b: number) => a + b, 0) / scores.length) : 0;

  // Pending reviews
  const pendingReviews = statusMap['UnderReview'] ?? 0;

  // Recent activity (last 8 dossiers by updated_at desc)
  const sorted = [...dossiers].sort((a, b) => {
    const ta = a.updated_at ?? a.created_at ?? '';
    const tb = b.updated_at ?? b.created_at ?? '';
    return tb.localeCompare(ta);
  });
  const recentActivity = sorted.slice(0, 8).map((d: any) => ({
    label: d.name ?? d.id,
    detail: `Status: ${d.status ?? 'Draft'}`,
    timestamp: d.updated_at ?? d.created_at ?? '',
  }));

  // Certification progress (derived from evidence completeness — placeholder logic)
  const total = statObj.total_dossiers ?? dossiers.length;
  const approvedCount = statusMap['Approved'] ?? 0;
  const certPct = total > 0 ? Math.round((approvedCount / total) * 100) : 0;
  const certProgress = {
    iso10303: certPct,
    mossec: Math.min(100, certPct + 10),
    asme: Math.max(0, certPct - 5),
    nafems: Math.max(0, certPct - 10),
  };

  const kpis: KPIs = {
    totalDossiers: statObj.total_dossiers ?? dossiers.length,
    avgHealthScore,
    activeSimulations: runs.length,
    pendingReviews,
    statusDistribution,
    certProgress,
    recentActivity,
  };

  return {
    kpis,
    isLoading: statsLoading || runsLoading || dossiersLoading,
    error: statsError,
  };
}

/* -------------------------------------------------------------------------- */
/*  useDossierHealth — per-dossier heath data + convergence                    */
/* -------------------------------------------------------------------------- */

export function useDossierHealth() {
  const { data: dossiersData, isLoading } = useQuery({
    queryKey: ['dossiers-health'],
    queryFn: () => sddService.getDossiers({ limit: 200 }),
    staleTime: 30_000,
  });

  const dossiers: any[] = (dossiersData as any)?.dossiers ?? [];

  const healthData: HealthDatum[] = dossiers
    .map((d: any) => ({
      id: d.id,
      name: d.name ?? d.id ?? 'Unknown',
      score: d.health_score ?? d.healthScore ?? 0,
    }))
    .filter((d) => d.score > 0);

  // Convergence trend: simulate iteration-based improvement per dossier average
  const convergenceData: ConvergenceDatum[] = healthData.length > 0
    ? Array.from({ length: 10 }, (_, i) => ({
        iteration: i + 1,
        score: Math.min(
          100,
          Math.round(
            healthData.reduce((sum, d) => sum + d.score, 0) / healthData.length * (0.4 + (i * 0.06))
          ),
        ),
      }))
    : [];

  // Evidence summary: derive from dossier data or use defaults
  const codes = ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1'];
  const evidenceSummary: EvidenceSummaryItem[] = codes.map((code, idx) => {
    // Approximate: earlier categories more complete
    const basePct = healthData.length > 0
      ? Math.round(healthData.reduce((s, d) => s + d.score, 0) / healthData.length)
      : 0;
    return {
      code,
      percent: Math.max(0, Math.min(100, basePct - idx * 8)),
    };
  });

  return { healthData, convergenceData, evidenceSummary, isLoading };
}

/* -------------------------------------------------------------------------- */
/*  useApprovalQueue — pending dossiers + weekly throughput                    */
/* -------------------------------------------------------------------------- */

export function useApprovalQueue() {
  const { data: dossiersData, isLoading } = useQuery({
    queryKey: ['dossiers-approval-queue'],
    queryFn: () => sddService.getDossiers({ limit: 200 }),
    staleTime: 30_000,
  });

  const dossiers: any[] = (dossiersData as any)?.dossiers ?? [];

  // Priority queue: sort by health score ascending
  const queue: QueueItem[] = dossiers
    .filter((d: any) => d.status === 'UnderReview')
    .map((d: any) => ({
      id: d.id,
      name: d.name ?? d.id,
      score: d.health_score ?? d.healthScore ?? 0,
      status: d.status ?? 'Draft',
    }))
    .sort((a, b) => a.score - b.score);

  // Weekly throughput placeholder — derive from dossier updated_at
  const weeklyThroughput: WeeklyThroughput[] = (() => {
    const weeks: Record<string, { approved: number; rejected: number }> = {};
    for (const d of dossiers) {
      if (d.status !== 'Approved' && d.status !== 'Rejected') continue;
      const dateStr = d.updated_at ?? d.created_at ?? '';
      if (!dateStr) continue;
      const dt = new Date(dateStr);
      if (isNaN(dt.getTime())) continue;
      // ISO week label
      const weekStart = new Date(dt);
      weekStart.setDate(weekStart.getDate() - weekStart.getDay());
      const label = `${weekStart.getMonth() + 1}/${weekStart.getDate()}`;
      if (!weeks[label]) weeks[label] = { approved: 0, rejected: 0 };
      if (d.status === 'Approved') weeks[label].approved++;
      else weeks[label].rejected++;
    }
    return Object.entries(weeks)
      .map(([week, counts]) => ({ week, ...counts }))
      .slice(-8);
  })();

  return { queue, weeklyThroughput, isLoading };
}
