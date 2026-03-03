import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@ui/card';
import { Button } from '@ui/button';
import { Lightbulb, TrendingUp, AlertCircle, Sparkles, Shield, Search, RefreshCw, Loader2, Copy } from 'lucide-react';
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

  return (
    <div className="container mx-auto p-6 space-y-6">
      <PageHeader
        title="AI Insights"
        description="Live analytics from your knowledge graph — BOM, traceability, classification, and SHACL compliance"
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
    </div>
  );
}
