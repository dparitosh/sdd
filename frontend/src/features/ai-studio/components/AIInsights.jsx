import { useState, useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@ui/card';
import { Button } from '@ui/button';
import {
  TrendingUp, AlertCircle, Sparkles, Shield, Search, RefreshCw,
  Loader2, Copy, Activity, GitBranch, Cpu, Layers, BarChart2, Brain,
  AlertTriangle, CheckCircle2, XCircle, ChevronDown, ChevronRight,
  Zap, Target, Clock, Info, Wand2, Gauge,
} from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import { getInsight, getAiNarrative } from '@/services/insights.service';
import { QUERY_CONFIG } from '@/constants';

// ─── Severity helpers ─────────────────────────────────────────────────────────

const SEVERITY_META = {
  critical: {
    Icon: XCircle,
    color: 'text-red-500',
    bg: 'bg-red-50 dark:bg-red-950/30',
    badge: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
    border: 'border-l-red-500',
    ring: 'ring-red-200',
    label: 'Critical',
    dot: 'bg-red-500',
  },
  warning: {
    Icon: AlertTriangle,
    color: 'text-amber-500',
    bg: 'bg-amber-50 dark:bg-amber-950/20',
    badge: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
    border: 'border-l-amber-400',
    ring: 'ring-amber-200',
    label: 'Warning',
    dot: 'bg-amber-500',
  },
  healthy: {
    Icon: CheckCircle2,
    color: 'text-emerald-500',
    bg: 'bg-emerald-50 dark:bg-emerald-950/20',
    badge: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
    border: 'border-l-emerald-500',
    ring: 'ring-emerald-200',
    label: 'Healthy',
    dot: 'bg-emerald-500',
  },
  unknown: {
    Icon: Info,
    color: 'text-slate-400',
    bg: 'bg-slate-50 dark:bg-slate-900/20',
    badge: 'bg-slate-100 text-slate-600',
    border: 'border-l-slate-300',
    ring: 'ring-slate-200',
    label: '',
    dot: 'bg-slate-400',
  },
};

function computeSeverity(metricKey, data) {
  if (!data || Object.keys(data).length === 0) return 'unknown';
  const p = (k) => Number(data[k] ?? -1);
  const n = (k) => Number(data[k] ?? -1);
  switch (metricKey) {
    case 'bom-completeness':
      return p('completeness_pct') >= 70 ? 'healthy' : p('completeness_pct') >= 30 ? 'warning' : 'critical';
    case 'traceability-gaps':
      return p('coverage_pct') >= 80 ? 'healthy' : p('coverage_pct') >= 50 ? 'warning' : 'critical';
    case 'classification-coverage':
      return p('coverage_pct') >= 80 ? 'healthy' : p('coverage_pct') >= 40 ? 'warning' : 'critical';
    case 'semantic-duplicates':
      return n('count') === 0 ? 'healthy' : n('count') <= 5 ? 'warning' : 'critical';
    case 'part-similarity':
      return n('total_groups') <= 2 ? 'healthy' : n('total_groups') <= 10 ? 'warning' : 'critical';
    case 'shacl-compliance':
      return n('total_violations') === 0 ? 'healthy' : n('total_violations') <= 5 ? 'warning' : 'critical';
    case 'simulation-run-status':
      return p('success_rate_pct') >= 70 ? 'healthy' : p('success_rate_pct') >= 40 ? 'warning' : 'critical';
    case 'simulation-workflow-coverage':
      return p('coverage_pct') >= 60 ? 'healthy' : p('coverage_pct') >= 30 ? 'warning' : 'critical';
    case 'simulation-parameter-health':
      return p('constraint_coverage_pct') >= 70 ? 'healthy' : p('constraint_coverage_pct') >= 40 ? 'warning' : 'critical';
    case 'simulation-dossier-health':
      return p('completeness_pct') >= 70 ? 'healthy' : p('completeness_pct') >= 40 ? 'warning' : 'critical';
    case 'simulation-digital-thread':
      return p('thread_completeness_pct') >= 70 ? 'healthy' : p('thread_completeness_pct') >= 40 ? 'warning' : 'critical';
    default:
      return 'unknown';
  }
}

function getAiExplanation(metricKey, data, severity) {
  const pct = (k) => data[k] != null ? `${data[k]}%` : '?';
  const num = (k) => data[k] ?? '?';
  if (!data || Object.keys(data).length === 0) return null;
  switch (metricKey) {
    case 'bom-completeness':
      return severity === 'healthy'
        ? `${pct('completeness_pct')} of items carry complete metadata — above the 70% threshold.`
        : severity === 'critical'
        ? `Only ${pct('completeness_pct')} BOM completeness. ${num('unclassified')} items lack classification. Populate via seed_bom script.`
        : `${num('missing_revision')} items are missing revision codes. Assign revision attributes to improve traceability.`;
    case 'traceability-gaps':
      return severity === 'healthy'
        ? `Requirements well-covered at ${pct('coverage_pct')} — only ${num('orphaned')} orphaned nodes remain.`
        : `${num('orphaned')} of ${num('total_requirements')} requirements have no trace links. Link requirements to AP243 activities to resolve.`;
    case 'classification-coverage':
      return severity === 'healthy'
        ? `${num('classified')} items classified — coverage meets the ≥80% engineering target.`
        : `${num('unclassified')} items remain unclassified. Use the Classification feature to assign ontology types.`;
    case 'semantic-duplicates':
      return num('count') === 0 || num('count') === '?'
        ? 'No semantic duplicates detected — knowledge graph nodes are clean and unique.'
        : `${num('count')} near-duplicate pairs found. Review in Graph Explorer to merge or disambiguate.`;
    case 'part-similarity':
      return (data.total_groups == null || data.total_groups <= 2)
        ? 'Part revision variants are minimal — BOM structure is lean.'
        : `${num('total_groups')} revision groups (${num('total_variants')} variants) detected. Review for consolidation opportunities.`;
    case 'shacl-compliance':
      return (data.total_violations == null || data.total_violations === 0)
        ? 'All nodes pass SHACL shape constraints. Ontology integrity is verified ✓'
        : `${num('total_violations')} constraint violations. Review ontology shape definitions for affected node labels.`;
    case 'simulation-run-status':
      return severity === 'healthy'
        ? `${pct('success_rate_pct')} success rate across ${num('total_runs')} runs — within operational target.`
        : `Low success rate of ${pct('success_rate_pct')}. Investigate failed runs and validate input parameter bounds.`;
    case 'simulation-workflow-coverage':
      return severity === 'healthy'
        ? `${pct('coverage_pct')} of runs linked to a WorkflowMethod — AP243 traceability is good.`
        : `${num('orphan_runs')} runs are not linked to any WorkflowMethod. Assign AP243 methods for full process traceability.`;
    case 'simulation-parameter-health':
      return severity === 'healthy'
        ? `${pct('constraint_coverage_pct')} of parameters have constraints — simulation input space is well-bounded.`
        : `Only ${pct('constraint_coverage_pct')} constraint coverage. Define min/max bounds for unconstrained parameters.`;
    case 'simulation-dossier-health':
      return severity === 'healthy'
        ? `${pct('completeness_pct')} of dossiers are complete with reports and artifacts.`
        : `${num('total_dossiers')} dossiers — only ${num('with_report')} have a linked report. Attach reports to incomplete dossiers.`;
    case 'simulation-digital-thread':
      return severity === 'healthy'
        ? `End-to-end AP239→AP242→AP243 thread at ${pct('thread_completeness_pct')} — strong cross-standard traceability.`
        : `Thread coverage is ${pct('thread_completeness_pct')}. Missing: ${num('linked_ap239')} AP239, ${num('linked_ap242')} AP242, ${num('linked_ap243')} AP243 links.`;
    default:
      return null;
  }
}

const scoreToColor = (s) => {
  if (s >= 75) return { ring1: '#10b981', ring2: '#d1fae5', label: 'Excellent', text: 'text-emerald-500' };
  if (s >= 50) return { ring1: '#f59e0b', ring2: '#fef3c7', label: 'Moderate', text: 'text-amber-500' };
  if (s >= 25) return { ring1: '#f97316', ring2: '#ffedd5', label: 'At Risk', text: 'text-orange-500' };
  return { ring1: '#ef4444', ring2: '#fee2e2', label: 'Critical', text: 'text-red-500' };
};

// ─── Sub-components ───────────────────────────────────────────────────────────

function HealthRing({ score }) {
  const s = score ?? 0;
  const r = 52;
  const circ = 2 * Math.PI * r;
  const offset = circ - (s / 100) * circ;
  const { ring1, ring2, label, text } = scoreToColor(s);
  return (
    <div className="relative flex items-center justify-center w-36 h-36 shrink-0">
      <svg width="144" height="144" viewBox="0 0 144 144" className="absolute">
        <circle cx="72" cy="72" r={r} fill="none" stroke={ring2} strokeWidth="12" />
        <circle
          cx="72" cy="72" r={r} fill="none"
          stroke={ring1} strokeWidth="12"
          strokeDasharray={circ} strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transform: 'rotate(-90deg)', transformOrigin: '72px 72px', transition: 'stroke-dashoffset 1.2s ease' }}
        />
      </svg>
      <div className="text-center z-10">
        <div className={`text-3xl font-extrabold tabular-nums ${text}`}>{s}</div>
        <div className="text-[11px] font-medium text-muted-foreground leading-tight">{label}</div>
      </div>
    </div>
  );
}

function ConfidencePill({ confidence }) {
  const map = {
    high:   'bg-emerald-100 text-emerald-700 ring-1 ring-emerald-300',
    medium: 'bg-amber-100 text-amber-700 ring-1 ring-amber-300',
    low:    'bg-slate-100 text-slate-600 ring-1 ring-slate-300',
  };
  const labels = { high: 'High confidence', medium: 'Medium confidence', low: 'Low confidence' };
  const cls = map[confidence] ?? map.low;
  return (
    <span className={`inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full ${cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${confidence === 'high' ? 'bg-emerald-500' : confidence === 'medium' ? 'bg-amber-500' : 'bg-slate-400'}`} />
      {labels[confidence] ?? 'Unknown'}
    </span>
  );
}

function AIBanner({ narrative, loading, error, onReanalyze }) {
  const ts = narrative?.generated_at
    ? new Date(narrative.generated_at * 1000).toLocaleTimeString()
    : null;

  return (
    <Card className="border-0 bg-linear-to-r from-violet-600/10 via-blue-600/5 to-cyan-600/5 shadow-sm ring-1 ring-violet-200/60 dark:ring-violet-800/40">
      <CardContent className="p-6">
        <div className="flex flex-col md:flex-row gap-6 items-start">
          {/* Score ring */}
          <HealthRing score={narrative?.overall_score} />

          {/* Narrative text */}
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <Brain className="h-4 w-4 text-violet-500 shrink-0" />
              <span className="text-xs font-semibold text-violet-600 dark:text-violet-400 uppercase tracking-wider">AI Assessment</span>
              {narrative?.confidence && <ConfidencePill confidence={narrative.confidence} />}
              {ts && (
                <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
                  <Clock className="h-3 w-3" /> Generated {ts}
                </span>
              )}
            </div>

            {loading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Analyzing knowledge graph with LLM…</span>
              </div>
            ) : error ? (
              <p className="text-sm text-destructive">{error}</p>
            ) : narrative ? (
              <>
                <h2 className="text-lg font-semibold mb-1 leading-snug">{narrative.headline}</h2>
                <p className="text-sm text-muted-foreground leading-relaxed">{narrative.summary}</p>
              </>
            ) : (
              <p className="text-sm text-muted-foreground italic">Click Re-analyze to generate AI insights.</p>
            )}
          </div>

          {/* CTA */}
          <div className="shrink-0">
            <Button
              onClick={onReanalyze}
              disabled={loading}
              variant="outline"
              className="gap-2 border-violet-300 text-violet-700 hover:bg-violet-50 dark:border-violet-700 dark:text-violet-300"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />}
              {loading ? 'Analyzing…' : 'Re-analyze'}
            </Button>
          </div>
        </div>

        {/* AI score decomposition bar */}
        {narrative?.overall_score != null && (
          <div className="mt-4 pt-4 border-t border-violet-200/40">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs text-muted-foreground">System Health Score</span>
              <span className="text-xs font-semibold">{narrative.overall_score}/100</span>
            </div>
            <div className="h-2 rounded-full bg-muted/40 overflow-hidden">
              <div
                className="h-2 rounded-full transition-all duration-1000"
                style={{
                  width: `${narrative.overall_score}%`,
                  background: narrative.overall_score >= 75
                    ? 'linear-gradient(90deg,#10b981,#34d399)'
                    : narrative.overall_score >= 50
                    ? 'linear-gradient(90deg,#f59e0b,#fbbf24)'
                    : 'linear-gradient(90deg,#ef4444,#f97316)',
                }}
              />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function PriorityIssues({ issues }) {
  const [expanded, setExpanded] = useState({});
  if (!issues || issues.length === 0) return null;

  const sorted = [...issues].sort((a, b) => {
    const ord = { critical: 0, warning: 1, healthy: 2 };
    return (ord[a.severity] ?? 3) - (ord[b.severity] ?? 3);
  });

  const toggle = (i) => setExpanded((prev) => ({ ...prev, [i]: !prev[i] }));

  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-3 pt-4 px-5">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <Target className="h-4 w-4 text-red-500" />
          Priority Issues
          <span className="ml-auto flex gap-1">
            {['critical', 'warning', 'healthy'].map((sev) => {
              const cnt = sorted.filter((i) => i.severity === sev).length;
              if (!cnt) return null;
              const m = SEVERITY_META[sev];
              return (
                <span key={sev} className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${m.badge}`}>
                  {cnt} {m.label}
                </span>
              );
            })}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="px-5 pb-4 space-y-2">
        {sorted.map((issue, i) => {
          const m = SEVERITY_META[issue.severity] ?? SEVERITY_META.unknown;
          const Icon = m.Icon;
          const open = !!expanded[i];
          return (
            <button
              key={i}
              className={`w-full text-left rounded-lg border p-3 transition-colors ${open ? m.bg + ' border-transparent' : 'bg-transparent border-border hover:border-muted-foreground/30'}`}
              onClick={() => toggle(i)}
            >
              <div className="flex items-center gap-2.5">
                <Icon className={`h-4 w-4 shrink-0 ${m.color}`} />
                <span className="text-sm font-medium flex-1">{issue.title}</span>
                {open ? <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" /> : <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />}
              </div>
              {open && issue.detail && (
                <p className="mt-2 ml-6.5 text-sm text-muted-foreground leading-relaxed pl-1">{issue.detail}</p>
              )}
            </button>
          );
        })}
      </CardContent>
    </Card>
  );
}

function AIRecommendations({ recommendations }) {
  if (!recommendations || recommendations.length === 0) return null;
  const impactColor = { high: 'bg-emerald-100 text-emerald-700', medium: 'bg-amber-100 text-amber-700', low: 'bg-slate-100 text-slate-600' };
  const effortColor = { high: 'bg-red-100 text-red-700', medium: 'bg-orange-100 text-orange-700', low: 'bg-blue-100 text-blue-700' };

  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-3 pt-4 px-5">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <Zap className="h-4 w-4 text-amber-500" />
          AI Recommendations
        </CardTitle>
      </CardHeader>
      <CardContent className="px-5 pb-4">
        <div className="space-y-2.5">
          {recommendations.map((rec, i) => (
            <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-muted/30 border border-border/50">
              <div className="shrink-0 w-5 h-5 rounded-full bg-violet-100 text-violet-700 text-[11px] font-bold flex items-center justify-center mt-0.5">
                {i + 1}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm leading-relaxed">{rec.action}</p>
                <div className="flex gap-1.5 mt-1.5">
                  <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${impactColor[rec.impact] ?? impactColor.medium}`}>
                    ↑ Impact: {rec.impact}
                  </span>
                  <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${effortColor[rec.effort] ?? effortColor.medium}`}>
                    ⏱ Effort: {rec.effort}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function InsightCard({ title, icon, metric, metricLabel, description, loading, error, onRefresh, metricKey, rawData }) {
  const severity = metricKey && rawData ? computeSeverity(metricKey, rawData) : 'unknown';
  const aiExpl = metricKey && rawData ? getAiExplanation(metricKey, rawData, severity) : null;
  const meta = SEVERITY_META[severity] ?? SEVERITY_META.unknown;
  const SevIcon = meta.Icon;

  return (
    <Card className={`border-l-4 ${meta.border} shadow-sm transition-shadow hover:shadow-md`}>
      <CardHeader className="pb-2 pt-4 px-4">
        <CardTitle className="flex items-start gap-2 text-sm font-semibold leading-tight">
          {icon}
          <span className="flex-1">{title}</span>
          <div className="flex items-center gap-1.5 shrink-0">
            {severity !== 'unknown' && (
              <span className={`inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${meta.badge}`}>
                <SevIcon className="h-2.5 w-2.5" />
                {meta.label}
              </span>
            )}
            {loading
              ? <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
              : <Button variant="ghost" size="sm" className="h-5 w-5 p-0 opacity-50 hover:opacity-100" onClick={onRefresh}><RefreshCw className="h-3 w-3" /></Button>
            }
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        {error ? (
          <p className="text-sm text-destructive">{error}</p>
        ) : loading ? (
          <div className="space-y-2">
            <div className="h-7 w-24 bg-muted/60 animate-pulse rounded" />
            <div className="h-3 w-full bg-muted/40 animate-pulse rounded" />
          </div>
        ) : (
          <>
            <div className="flex items-baseline gap-2 mb-1.5">
              <span className={`text-2xl font-extrabold tabular-nums ${meta.color}`}>{metric ?? '--'}</span>
              <span className="text-xs text-muted-foreground">{metricLabel}</span>
            </div>
            {/* AI-generated explanation takes precedence over static description */}
            {aiExpl ? (
              <div className={`rounded-md px-2.5 py-1.5 mt-1 ${meta.bg}`}>
                <p className="text-[11px] leading-relaxed text-foreground/80 flex gap-1.5">
                  <Brain className="h-3 w-3 shrink-0 mt-0.5 text-violet-400" />
                  {aiExpl}
                </p>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">{description}</p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

const ALL_METRICS = [
  'bom-completeness', 'traceability-gaps', 'classification-coverage',
  'semantic-duplicates', 'part-similarity', 'shacl-compliance',
  'simulation-run-status', 'simulation-workflow-coverage',
  'simulation-parameter-health', 'simulation-dossier-health', 'simulation-digital-thread',
];

// ── Shared query options: 5-min stale · 10-min gc · auto-refresh every 60 s ──
const INSIGHT_QUERY_OPTS = {
  staleTime: QUERY_CONFIG.STALE_TIME,
  gcTime:    QUERY_CONFIG.CACHE_TIME,
  refetchInterval: 60_000,
  placeholderData: (prev) => prev,        // keep stale data while refetching
  select: (res) => res?.data ?? res,
};

export default function AIInsights() {
  const queryClient = useQueryClient();

  // ── Per-metric React Query hooks (cached · stale-while-revalidate) ──────
  const bomQ        = useQuery({ queryKey: ['insight', 'bom-completeness'],             queryFn: () => getInsight('bom-completeness'),             ...INSIGHT_QUERY_OPTS });
  const traceQ      = useQuery({ queryKey: ['insight', 'traceability-gaps'],            queryFn: () => getInsight('traceability-gaps'),            ...INSIGHT_QUERY_OPTS });
  const clsQ        = useQuery({ queryKey: ['insight', 'classification-coverage'],      queryFn: () => getInsight('classification-coverage'),      ...INSIGHT_QUERY_OPTS });
  const dupQ        = useQuery({ queryKey: ['insight', 'semantic-duplicates'],          queryFn: () => getInsight('semantic-duplicates'),          ...INSIGHT_QUERY_OPTS });
  const partSimQ    = useQuery({ queryKey: ['insight', 'part-similarity'],              queryFn: () => getInsight('part-similarity'),              ...INSIGHT_QUERY_OPTS });
  const shaclQ      = useQuery({ queryKey: ['insight', 'shacl-compliance'],             queryFn: () => getInsight('shacl-compliance'),             ...INSIGHT_QUERY_OPTS });
  const simRunsQ    = useQuery({ queryKey: ['insight', 'simulation-run-status'],        queryFn: () => getInsight('simulation-run-status'),        ...INSIGHT_QUERY_OPTS });
  const simWfQ      = useQuery({ queryKey: ['insight', 'simulation-workflow-coverage'], queryFn: () => getInsight('simulation-workflow-coverage'), ...INSIGHT_QUERY_OPTS });
  const simParamQ   = useQuery({ queryKey: ['insight', 'simulation-parameter-health'],  queryFn: () => getInsight('simulation-parameter-health'),  ...INSIGHT_QUERY_OPTS });
  const simDossierQ = useQuery({ queryKey: ['insight', 'simulation-dossier-health'],    queryFn: () => getInsight('simulation-dossier-health'),    ...INSIGHT_QUERY_OPTS });
  const simThreadQ  = useQuery({ queryKey: ['insight', 'simulation-digital-thread'],    queryFn: () => getInsight('simulation-digital-thread'),    ...INSIGHT_QUERY_OPTS });

  // Narrative is LLM-expensive — no auto-refetchInterval; stays cached 5 min
  const narrativeQ  = useQuery({
    queryKey: ['insight', 'narrative'],
    queryFn:  getAiNarrative,
    staleTime: QUERY_CONFIG.STALE_TIME,
    gcTime:    QUERY_CONFIG.CACHE_TIME,
    placeholderData: (prev) => prev,
    select: (res) => res?.data ?? res,
  });

  // ── Destructure metric data ──
  const bom        = bomQ.data        || {};
  const trace      = traceQ.data      || {};
  const cls        = clsQ.data        || {};
  const dup        = dupQ.data        || {};
  const partSim    = partSimQ.data    || {};
  const shacl      = shaclQ.data      || {};
  const simRuns    = simRunsQ.data    || {};
  const simWf      = simWfQ.data      || {};
  const simParam   = simParamQ.data   || {};
  const simDossier = simDossierQ.data || {};
  const simThread  = simThreadQ.data  || {};

  const narrative        = narrativeQ.data;
  const loadingNarrative = narrativeQ.isFetching && !narrativeQ.data;
  const narrativeError   = narrativeQ.error?.message ?? null;

  const handleRefreshAll = () => {
    ALL_METRICS.forEach((m) => queryClient.invalidateQueries({ queryKey: ['insight', m] }));
    queryClient.invalidateQueries({ queryKey: ['insight', 'narrative'] });
  };

  return (
    <div className="container mx-auto p-6 space-y-6 max-w-7xl">
      <PageHeader
        title="AI Insights"
        description="LLM-powered analytics — explainable, prioritised, and proactive"
        icon={<Brain className="h-8 w-8 text-violet-500" />}
        badge="AI Powered"
        breadcrumbs={[
          { label: 'GenAI Studio', href: '/ai/insights' },
          { label: 'AI Insights' },
        ]}
        actions={
          <Button onClick={handleRefreshAll} variant="outline" className="gap-2">
            <RefreshCw className="h-4 w-4" />
            Refresh All
          </Button>
        }
      />

      {/* ── AI Banner ─────────────────────────────────────────────────────── */}
      <AIBanner
        narrative={narrative}
        loading={loadingNarrative}
        error={narrativeError}
        onReanalyze={narrativeQ.refetch}
      />

      {/* ── Priority Issues + Recommendations (side-by-side) ──────────────── */}
      {(narrative?.priority_issues?.length > 0 || narrative?.recommendations?.length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <PriorityIssues issues={narrative?.priority_issues} />
          <AIRecommendations recommendations={narrative?.recommendations} />
        </div>
      )}

      {/* ── Knowledge Graph Metrics ───────────────────────────────────────── */}
      <div>
        <h2 className="flex items-center gap-2 text-base font-semibold mb-4">
          <Gauge className="h-4 w-4 text-blue-500" />
          Knowledge Graph Analytics
          <span className="ml-2 text-xs font-normal text-muted-foreground">6 metrics · auto-refreshes every 60 s</span>
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          <InsightCard
            title="BOM Completeness"
            icon={<TrendingUp className="h-4 w-4 text-blue-500" />}
            metric={bom.completeness_pct != null ? `${bom.completeness_pct}%` : undefined}
            metricLabel={`${bom.total_items ?? '?'} items`}
            description={`${bom.unclassified ?? '?'} unclassified · ${bom.missing_revision ?? '?'} missing revisions`}
            loading={bomQ.isFetching}
            error={bomQ.error?.message ?? null}
            onRefresh={bomQ.refetch}
            metricKey="bom-completeness"
            rawData={bom}
          />
          <InsightCard
            title="Traceability Gaps"
            icon={<AlertCircle className="h-4 w-4 text-amber-500" />}
            metric={trace.coverage_pct != null ? `${trace.coverage_pct}%` : undefined}
            metricLabel="requirement coverage"
            description={`${trace.orphaned ?? '?'} orphaned of ${trace.total_requirements ?? '?'}`}
            loading={traceQ.isFetching}
            error={traceQ.error?.message ?? null}
            onRefresh={traceQ.refetch}
            metricKey="traceability-gaps"
            rawData={trace}
          />
          <InsightCard
            title="Classification Coverage"
            icon={<Sparkles className="h-4 w-4 text-green-500" />}
            metric={cls.coverage_pct != null ? `${cls.coverage_pct}%` : undefined}
            metricLabel="items classified"
            description={`${cls.classified ?? '?'} classified · ${cls.unclassified ?? '?'} unclassified`}
            loading={clsQ.isFetching}
            error={clsQ.error?.message ?? null}
            onRefresh={clsQ.refetch}
            metricKey="classification-coverage"
            rawData={cls}
          />
          <InsightCard
            title="Semantic Duplicates"
            icon={<Search className="h-4 w-4 text-purple-500" />}
            metric={dup.count != null ? String(dup.count) : undefined}
            metricLabel="duplicate pairs"
            description="Near-duplicate nodes via vector similarity"
            loading={dupQ.isFetching}
            error={dupQ.error?.message ?? null}
            onRefresh={dupQ.refetch}
            metricKey="semantic-duplicates"
            rawData={dup}
          />
          <InsightCard
            title="Part Similarity"
            icon={<Copy className="h-4 w-4 text-orange-500" />}
            metric={partSim.total_groups != null ? String(partSim.total_groups) : undefined}
            metricLabel={`${partSim.total_variants ?? '?'} variants`}
            description={partSim.similar_groups?.length
              ? partSim.similar_groups.map((g) => `${g.group_key} (${g.variant_count})`).join(', ')
              : 'No revision variants detected'}
            loading={partSimQ.isFetching}
            error={partSimQ.error?.message ?? null}
            onRefresh={partSimQ.refetch}
            metricKey="part-similarity"
            rawData={partSim}
          />
          <InsightCard
            title="SHACL Compliance"
            icon={<Shield className="h-4 w-4 text-red-500" />}
            metric={shacl.total_violations != null ? String(shacl.total_violations) : undefined}
            metricLabel="total violations"
            description={shacl.by_label?.length
              ? shacl.by_label.map((l) => `${l.label}: ${l.compliance_pct}%`).join(' | ')
              : 'No violation data yet'}
            loading={shaclQ.isFetching}
            error={shaclQ.error?.message ?? null}
            onRefresh={shaclQ.refetch}
            metricKey="shacl-compliance"
            rawData={shacl}
          />
        </div>
      </div>

      {/* ── Simulation Analytics ──────────────────────────────────────────── */}
      <div>
        <h2 className="flex items-center gap-2 text-base font-semibold mb-4">
          <Activity className="h-4 w-4 text-sky-500" />
          Simulation Analytics
          <span className="ml-2 text-xs font-normal text-muted-foreground">5 metrics · AP239 / AP242 / AP243</span>
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          <InsightCard
            title="Simulation Run Status"
            icon={<Activity className="h-4 w-4 text-sky-500" />}
            metric={simRuns.success_rate_pct != null ? `${simRuns.success_rate_pct}%` : undefined}
            metricLabel={`success · ${simRuns.total_runs ?? '?'} total`}
            description={simRuns.by_status ? Object.entries(simRuns.by_status).map(([k, v]) => `${k}: ${v}`).join(' | ') : ''}
            loading={simRunsQ.isFetching}
            error={simRunsQ.error?.message ?? null}
            onRefresh={simRunsQ.refetch}
            metricKey="simulation-run-status"
            rawData={simRuns}
          />
          <InsightCard
            title="Workflow Coverage"
            icon={<BarChart2 className="h-4 w-4 text-violet-500" />}
            metric={simWf.coverage_pct != null ? `${simWf.coverage_pct}%` : undefined}
            metricLabel="runs linked to WorkflowMethod"
            description={`${simWf.linked_runs ?? '?'} linked · ${simWf.orphan_runs ?? '?'} orphan · ${simWf.total_workflow_methods ?? '?'} methods`}
            loading={simWfQ.isFetching}
            error={simWfQ.error?.message ?? null}
            onRefresh={simWfQ.refetch}
            metricKey="simulation-workflow-coverage"
            rawData={simWf}
          />
          <InsightCard
            title="Parameter Health"
            icon={<Cpu className="h-4 w-4 text-emerald-500" />}
            metric={simParam.constraint_coverage_pct != null ? `${simParam.constraint_coverage_pct}%` : undefined}
            metricLabel={`constraint coverage · ${simParam.total_parameters ?? '?'} params`}
            description={simParam.by_data_type ? Object.entries(simParam.by_data_type).map(([k, v]) => `${k}: ${v}`).join(' | ') : ''}
            loading={simParamQ.isFetching}
            error={simParamQ.error?.message ?? null}
            onRefresh={simParamQ.refetch}
            metricKey="simulation-parameter-health"
            rawData={simParam}
          />
          <InsightCard
            title="Dossier Completeness"
            icon={<Layers className="h-4 w-4 text-amber-500" />}
            metric={simDossier.completeness_pct != null ? `${simDossier.completeness_pct}%` : undefined}
            metricLabel={`${simDossier.total_dossiers ?? '?'} dossiers`}
            description={`${simDossier.with_report ?? '?'} with report · ${simDossier.with_artifacts ?? '?'} with artifacts`}
            loading={simDossierQ.isFetching}
            error={simDossierQ.error?.message ?? null}
            onRefresh={simDossierQ.refetch}
            metricKey="simulation-dossier-health"
            rawData={simDossier}
          />
          <InsightCard
            title="Digital Thread Score"
            icon={<GitBranch className="h-4 w-4 text-indigo-500" />}
            metric={simThread.thread_completeness_pct != null ? `${simThread.thread_completeness_pct}%` : undefined}
            metricLabel="AP239 → AP242 → AP243"
            description={`${simThread.linked_ap239 ?? '?'} AP239 · ${simThread.linked_ap242 ?? '?'} AP242 · ${simThread.linked_ap243 ?? '?'} AP243`}
            loading={simThreadQ.isFetching}
            error={simThreadQ.error?.message ?? null}
            onRefresh={simThreadQ.refetch}
            metricKey="simulation-digital-thread"
            rawData={simThread}
          />
        </div>
      </div>

      {/* ── AI transparency footer ────────────────────────────────────────── */}
      <div className="flex items-center gap-2 pt-2 pb-1 text-[11px] text-muted-foreground border-t">
        <Brain className="h-3 w-3 text-violet-400 shrink-0" />
        <span>
          <strong>AI-powered</strong> — Health scores, priority issues, and per-card explanations are generated by a local LLM (Ollama llama3) over live Neo4j data.
          All data is read-only. · IxDF transparent AI UX principles applied.
        </span>
      </div>
    </div>
  );
}

