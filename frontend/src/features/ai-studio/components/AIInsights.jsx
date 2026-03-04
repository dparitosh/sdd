import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@ui/card';
import { Button } from '@ui/button';
import { Lightbulb, TrendingUp, AlertCircle, Sparkles, Shield, Search, RefreshCw, Loader2, Copy, Activity, GitBranch, Cpu, Layers, BarChart2 } from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import { getInsight } from '@/services/insights.service';

function InsightCard({ title, icon, color, metric, metricLabel, description, loading, error, onRefresh }) {
  return (
    <Card className={`border-l-4 border-l-${color}-500`}>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          {icon}
          {title}
          {loading && <Loader2 className="h-3.5 w-3.5 animate-spin ml-auto" />}
          {!loading && (
            <Button variant="ghost" size="sm" className="ml-auto h-6 w-6 p-0" onClick={onRefresh}>
              <RefreshCw className="h-3 w-3" />
            </Button>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {error ? (
          <p className="text-sm text-destructive">{error}</p>
        ) : loading ? (
          <p className="text-sm text-muted-foreground">Loading...</p>
        ) : (
          <>
            <div className="flex items-baseline gap-2 mb-1">
              <span className="text-2xl font-bold">{metric ?? '--'}</span>
              <span className="text-xs text-muted-foreground">{metricLabel}</span>
            </div>
            <p className="text-sm text-muted-foreground">{description}</p>
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default function AIInsights() {
  const [data, setData] = useState({});
  const [loading, setLoading] = useState({});
  const [errors, setErrors] = useState({});

  const metrics = [
    'bom-completeness',
    'traceability-gaps',
    'classification-coverage',
    'semantic-duplicates',
    'part-similarity',
    'shacl-compliance',
    // Simulation
    'simulation-run-status',
    'simulation-workflow-coverage',
    'simulation-parameter-health',
    'simulation-dossier-health',
    'simulation-digital-thread',
  ];

  const fetchMetric = useCallback(async (metric) => {
    setLoading((prev) => ({ ...prev, [metric]: true }));
    setErrors((prev) => ({ ...prev, [metric]: null }));
    try {
      const res = await getInsight(metric);
      setData((prev) => ({ ...prev, [metric]: res?.data ?? res }));
    } catch (err) {
      setErrors((prev) => ({
        ...prev,
        [metric]: err instanceof Error ? err.message : 'Failed to load',
      }));
    } finally {
      setLoading((prev) => ({ ...prev, [metric]: false }));
    }
  }, []);

  const fetchAll = useCallback(() => {
    metrics.forEach(fetchMetric);
  }, [fetchMetric]);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 60000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  const bom = data['bom-completeness'] || {};
  const trace = data['traceability-gaps'] || {};
  const cls = data['classification-coverage'] || {};
  const dup = data['semantic-duplicates'] || {};
  const partSim = data['part-similarity'] || {};
  const shacl = data['shacl-compliance'] || {};

  // Simulation metrics
  const simRuns = data['simulation-run-status'] || {};
  const simWf = data['simulation-workflow-coverage'] || {};
  const simParam = data['simulation-parameter-health'] || {};
  const simDossier = data['simulation-dossier-health'] || {};
  const simThread = data['simulation-digital-thread'] || {};

  return (
    <div className="container mx-auto p-6 space-y-6">
      <PageHeader
        title="AI Insights"
        description="Live analytics from your knowledge graph — BOM, traceability, classification, SHACL compliance, and simulation"
        icon={<Lightbulb className="h-8 w-8 text-primary" />}
        badge="Live"
        breadcrumbs={[
          { label: 'GenAI Studio', href: '/ai/insights' },
          { label: 'AI Insights' },
        ]}
        actions={
          <Button onClick={fetchAll} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh All
          </Button>
        }
      />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <InsightCard
          title="BOM Completeness"
          icon={<TrendingUp className="h-5 w-5 text-blue-500" />}
          color="blue"
          metric={bom.completeness_pct != null ? `${bom.completeness_pct}%` : undefined}
          metricLabel={`${bom.total_items ?? '?'} items total`}
          description={`${bom.unclassified ?? '?'} unclassified, ${bom.missing_revision ?? '?'} missing revisions`}
          loading={loading['bom-completeness']}
          error={errors['bom-completeness']}
          onRefresh={() => fetchMetric('bom-completeness')}
        />

        <InsightCard
          title="Traceability Gaps"
          icon={<AlertCircle className="h-5 w-5 text-amber-500" />}
          color="amber"
          metric={trace.coverage_pct != null ? `${trace.coverage_pct}%` : undefined}
          metricLabel="requirement coverage"
          description={`${trace.orphaned ?? '?'} requirements with no trace links out of ${trace.total_requirements ?? '?'}`}
          loading={loading['traceability-gaps']}
          error={errors['traceability-gaps']}
          onRefresh={() => fetchMetric('traceability-gaps')}
        />

        <InsightCard
          title="Classification Coverage"
          icon={<Sparkles className="h-5 w-5 text-green-500" />}
          color="green"
          metric={cls.coverage_pct != null ? `${cls.coverage_pct}%` : undefined}
          metricLabel="items classified"
          description={`${cls.classified ?? '?'} classified, ${cls.unclassified ?? '?'} unclassified`}
          loading={loading['classification-coverage']}
          error={errors['classification-coverage']}
          onRefresh={() => fetchMetric('classification-coverage')}
        />

        <InsightCard
          title="Semantic Duplicates"
          icon={<Search className="h-5 w-5 text-purple-500" />}
          color="purple"
          metric={dup.count != null ? String(dup.count) : undefined}
          metricLabel="duplicate pairs"
          description="Near-duplicate nodes detected via vector similarity"
          loading={loading['semantic-duplicates']}
          error={errors['semantic-duplicates']}
          onRefresh={() => fetchMetric('semantic-duplicates')}
        />

        <InsightCard
          title="Part Similarity"
          icon={<Copy className="h-5 w-5 text-orange-500" />}
          color="orange"
          metric={partSim.total_groups != null ? String(partSim.total_groups) : undefined}
          metricLabel={`${partSim.total_variants ?? '?'} total variants`}
          description={
            partSim.similar_groups?.length
              ? partSim.similar_groups.map((g) => `${g.group_key} (${g.variant_count} revisions)`).join(', ')
              : 'No revision variants detected'
          }
          loading={loading['part-similarity']}
          error={errors['part-similarity']}
          onRefresh={() => fetchMetric('part-similarity')}
        />

        <InsightCard
          title="SHACL Compliance"
          icon={<Shield className="h-5 w-5 text-red-500" />}
          color="red"
          metric={shacl.total_violations != null ? String(shacl.total_violations) : undefined}
          metricLabel="total violations"
          description={
            shacl.by_label?.length
              ? shacl.by_label.map((l) => `${l.label}: ${l.compliance_pct}%`).join(' | ')
              : 'No violation data yet'
          }
          loading={loading['shacl-compliance']}
          error={errors['shacl-compliance']}
          onRefresh={() => fetchMetric('shacl-compliance')}
        />
      </div>

      {/* ── Simulation Analytics ─────────────────────────────────────────── */}
      <div>
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Activity className="h-5 w-5 text-sky-500" />
          Simulation Analytics
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <InsightCard
            title="Simulation Run Status"
            icon={<Activity className="h-5 w-5 text-sky-500" />}
            color="sky"
            metric={simRuns.success_rate_pct != null ? `${simRuns.success_rate_pct}%` : undefined}
            metricLabel={`success rate · ${simRuns.total_runs ?? '?'} total runs`}
            description={
              simRuns.by_status
                ? Object.entries(simRuns.by_status).map(([k, v]) => `${k}: ${v}`).join(' | ')
                : 'Run breakdown loading…'
            }
            loading={loading['simulation-run-status']}
            error={errors['simulation-run-status']}
            onRefresh={() => fetchMetric('simulation-run-status')}
          />

          <InsightCard
            title="Workflow Coverage"
            icon={<BarChart2 className="h-5 w-5 text-violet-500" />}
            color="violet"
            metric={simWf.coverage_pct != null ? `${simWf.coverage_pct}%` : undefined}
            metricLabel="runs linked to a WorkflowMethod"
            description={`${simWf.linked_runs ?? '?'} linked · ${simWf.orphan_runs ?? '?'} orphan · ${simWf.total_workflow_methods ?? '?'} methods`}
            loading={loading['simulation-workflow-coverage']}
            error={errors['simulation-workflow-coverage']}
            onRefresh={() => fetchMetric('simulation-workflow-coverage')}
          />

          <InsightCard
            title="Parameter Health"
            icon={<Cpu className="h-5 w-5 text-emerald-500" />}
            color="emerald"
            metric={simParam.constraint_coverage_pct != null ? `${simParam.constraint_coverage_pct}%` : undefined}
            metricLabel={`constraint coverage · ${simParam.total_parameters ?? '?'} params`}
            description={
              simParam.by_data_type
                ? Object.entries(simParam.by_data_type).map(([k, v]) => `${k}: ${v}`).join(' | ')
                : 'Parameter type breakdown loading…'
            }
            loading={loading['simulation-parameter-health']}
            error={errors['simulation-parameter-health']}
            onRefresh={() => fetchMetric('simulation-parameter-health')}
          />

          <InsightCard
            title="Dossier Completeness"
            icon={<Layers className="h-5 w-5 text-amber-500" />}
            color="amber"
            metric={simDossier.completeness_pct != null ? `${simDossier.completeness_pct}%` : undefined}
            metricLabel={`${simDossier.total_dossiers ?? '?'} dossiers`}
            description={`${simDossier.with_report ?? '?'} with report · ${simDossier.with_artifacts ?? '?'} with artifacts`}
            loading={loading['simulation-dossier-health']}
            error={errors['simulation-dossier-health']}
            onRefresh={() => fetchMetric('simulation-dossier-health')}
          />

          <InsightCard
            title="Digital Thread Score"
            icon={<GitBranch className="h-5 w-5 text-indigo-500" />}
            color="indigo"
            metric={simThread.thread_completeness_pct != null ? `${simThread.thread_completeness_pct}%` : undefined}
            metricLabel="AP239 → AP242 → AP243 coverage"
            description={`${simThread.linked_ap239 ?? '?'} AP239 · ${simThread.linked_ap242 ?? '?'} AP242 · ${simThread.linked_ap243 ?? '?'} AP243 links`}
            loading={loading['simulation-digital-thread']}
            error={errors['simulation-digital-thread']}
            onRefresh={() => fetchMetric('simulation-digital-thread')}
          />
        </div>
      </div>
    </div>
  );
}
