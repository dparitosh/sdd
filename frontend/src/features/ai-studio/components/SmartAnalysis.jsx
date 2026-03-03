import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@ui/card';
import { Badge } from '@ui/badge';
import { Button } from '@ui/button';
import { Textarea } from '@ui/textarea';
import { Input } from '@ui/input';
import { ScrollArea } from '@ui/scroll-area';
import { Brain, Network, Activity, Play, Loader2, CheckCircle2, Clock, Search, Shield, GitBranch } from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import { runOrchestrator } from '@/services/agents.service';
import { runSmartAnalysis } from '@/services/insights.service';

marked.setOptions({ breaks: true });

/** A single completed analysis entry shown in the history list */
function AnalysisEntry({ entry, onViewResults }) {
  return (
    <div className="flex items-center justify-between p-4 border rounded-lg">
      <div className="flex items-center gap-3">
        {entry.loading ? (
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground shrink-0" />
        ) : (
          <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
        )}
        <div>
          <p className="font-medium">{entry.title}</p>
          <p className="text-sm text-muted-foreground flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {entry.ranAt}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        {entry.badge && <Badge variant="outline">{entry.badge}</Badge>}
        {entry.result && !entry.loading && (
          <Button variant="ghost" size="sm" onClick={() => onViewResults(entry)}>
            View Results
          </Button>
        )}
      </div>
    </div>
  );
}

export default function SmartAnalysis() {
  const [searchParams] = useSearchParams();
  const [analyses, setAnalyses] = useState([]);
  const [activeResult, setActiveResult] = useState(null);
  const [subjectInput, setSubjectInput] = useState('');
  const [nodeUid, setNodeUid] = useState(searchParams.get('uid') || '');
  const [nodeAnalysis, setNodeAnalysis] = useState(null);
  const [nodeLoading, setNodeLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  const runAnalysis = async (title, query, taskType) => {
    const entry = {
      id: Date.now(),
      title,
      ranAt: new Date().toLocaleString(),
      loading: true,
      result: null,
      badge: null,
    };
    setAnalyses((prev) => [entry, ...prev]);
    setActiveResult(null);

    try {
      const res = await runOrchestrator(query, taskType);
      const data = res?.data ?? res;
      const content =
        data?.messages?.length > 0
          ? data.messages[data.messages.length - 1]?.content ?? ''
          : data?.final_state
            ? JSON.stringify(data.final_state, null, 2)
            : 'No results returned.';

      // Count distinct impacts mentioned (lines starting with '-')
      const impactCount = (content.match(/^\s*-/gm) ?? []).length;

      const completed = {
        ...entry,
        loading: false,
        result: content,
        badge: impactCount > 0 ? `${impactCount} items found` : null,
      };
      setAnalyses((prev) => prev.map((e) => (e.id === entry.id ? completed : e)));
      setActiveResult(completed);
    } catch (err) {
      const failed = {
        ...entry,
        loading: false,
        result: `Error: ${err instanceof Error ? err.message : String(err)}`,
        badge: 'error',
      };
      setAnalyses((prev) => prev.map((e) => (e.id === entry.id ? failed : e)));
      setActiveResult(failed);
    }
  };

  const handleRunAnalysis = () =>
    runAnalysis(
      'Knowledge Graph Analysis',
      'Give me a full knowledge graph overview including node distribution, AP coverage, ontologies, simulations, and requirements.',
      'knowledge_query',
    );

  const handleStartImpactAnalysis = () => {
    const subject = subjectInput.trim() || 'all requirements';
    runAnalysis(
      `Impact Analysis: ${subject}`,
      `Impact analysis: what components, requirements, and artifacts are affected by changes to ${subject}?`,
      'impact_analysis',
    );
  };

  const handleAnalyzePropagation = () => {
    const subject = subjectInput.trim() || 'the system';
    runAnalysis(
      `Change Propagation: ${subject}`,
      `Trace change propagation and ripple effects through ${subject} in the knowledge graph.`,
      'impact_analysis',
    );
  };

  const handleNodeAnalysis = async () => {
    const uid = nodeUid.trim();
    if (!uid) return;
    setNodeLoading(true);
    setNodeAnalysis(null);
    try {
      const res = await runSmartAnalysis(uid);
      setNodeAnalysis(res?.data ?? res);
      setActiveTab('overview');
    } catch (err) {
      setNodeAnalysis({ uid, overview: { error: err instanceof Error ? err.message : String(err) } });
    } finally {
      setNodeLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <PageHeader
        title="Smart Analysis"
        description="Automated impact analysis and change propagation using the AI knowledge graph"
        icon={<Brain className="h-8 w-8 text-primary" />}
        badge="AI-Powered"
        breadcrumbs={[
          { label: 'GenAI Studio', href: '/ai/insights' },
          { label: 'Smart Analysis' },
        ]}
        actions={
          <Button onClick={handleRunAnalysis}>
            <Play className="h-4 w-4 mr-2" />
            Run Analysis
          </Button>
        }
      />

      {/* Subject input */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Analysis Subject</CardTitle>
          <CardDescription>Optionally enter a specific component, requirement, or topic to focus the analysis on</CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea
            placeholder="e.g. propulsion system, REQ-001, thermal constraints..."
            value={subjectInput}
            onChange={(e) => setSubjectInput(e.target.value)}
            rows={2}
            className="resize-none"
          />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="hover:shadow-lg transition-shadow">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Network className="h-5 w-5 text-primary" />
              Impact Analysis
            </CardTitle>
            <CardDescription>Understand downstream effects of changes</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm mb-4">
              AI-powered analysis to identify all components, requirements, and
              simulations affected by proposed changes to the subject above.
            </p>
            <Button variant="outline" className="w-full" onClick={handleStartImpactAnalysis}>
              Start Impact Analysis
            </Button>
          </CardContent>
        </Card>

        <Card className="hover:shadow-lg transition-shadow">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              Change Propagation
            </CardTitle>
            <CardDescription>Trace change ripple effects</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm mb-4">
              Automatically propagate design changes through the knowledge graph
              and identify required updates in related nodes.
            </p>
            <Button variant="outline" className="w-full" onClick={handleAnalyzePropagation}>
              Analyze Propagation
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Active result panel */}
      {activeResult && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              {activeResult.title}
            </CardTitle>
            <CardDescription>{activeResult.ranAt}</CardDescription>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-80 pr-4">
              <div
                className="text-sm prose prose-sm dark:prose-invert max-w-none
                  [&_h3]:text-base [&_h3]:font-semibold [&_h3]:mt-3 [&_h3]:mb-1
                  [&_h2]:text-base [&_h2]:font-semibold [&_h2]:mt-3 [&_h2]:mb-1
                  [&_ul]:mt-1 [&_ul]:mb-1 [&_li]:my-0 [&_table]:text-xs
                  [&_strong]:font-semibold [&_code]:text-xs [&_p]:my-1"
                dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(marked.parse(activeResult.result ?? '')) }}
              />
            </ScrollArea>
          </CardContent>
        </Card>
      )}

      {/* Analysis history */}
      <Card>
        <CardHeader>
          <CardTitle>Analysis History</CardTitle>
          <CardDescription>Analyses run during this session</CardDescription>
        </CardHeader>
        <CardContent>
          {analyses.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No analyses run yet. Use the buttons above to start.
            </p>
          ) : (
            <div className="space-y-3">
              {analyses.map((entry) => (
                <AnalysisEntry
                  key={entry.id}
                  entry={entry}
                  onViewResults={setActiveResult}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── SmartAnalysis per-node panel ─────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5 text-primary" />
            Node SmartAnalysis
          </CardTitle>
          <CardDescription>Enter a node UID for a 5-step deep analysis</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder="Node UID (e.g., item-001)"
              value={nodeUid}
              onChange={(e) => setNodeUid(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleNodeAnalysis()}
              className="flex-1"
            />
            <Button onClick={handleNodeAnalysis} disabled={nodeLoading || !nodeUid.trim()}>
              {nodeLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Analyse'}
            </Button>
          </div>

          {nodeAnalysis && (
            <>
              {/* Tab bar */}
              <div className="flex gap-1 border-b">
                {[
                  { key: 'overview', label: 'Overview' },
                  { key: 'ontology', label: 'Ontology' },
                  { key: 'similar', label: 'Similar' },
                  { key: 'violations', label: 'Violations' },
                  { key: 'graph', label: 'Graph' },
                ].map((t) => (
                  <button
                    key={t.key}
                    className={`px-3 py-1.5 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === t.key
                        ? 'border-primary text-primary'
                        : 'border-transparent text-muted-foreground hover:text-foreground'
                    }`}
                    onClick={() => setActiveTab(t.key)}
                  >
                    {t.label}
                  </button>
                ))}
              </div>

              {/* Tab content */}
              <ScrollArea className="h-64">
                {activeTab === 'overview' && (
                  <div className="space-y-2 text-sm">
                    {nodeAnalysis.overview?.error ? (
                      <p className="text-destructive">{nodeAnalysis.overview.error}</p>
                    ) : (
                      <>
                        <p><strong>Labels:</strong> {(nodeAnalysis.overview?.labels || []).join(', ')}</p>
                        <div className="grid grid-cols-2 gap-1">
                          {Object.entries(nodeAnalysis.overview?.properties || {}).map(([k, v]) => (
                            <div key={k} className="truncate">
                              <span className="font-medium">{k}:</span> {String(v)}
                            </div>
                          ))}
                        </div>
                      </>
                    )}
                  </div>
                )}

                {activeTab === 'ontology' && (
                  <div className="space-y-2 text-sm">
                    {(nodeAnalysis.ontology?.classifications || []).length === 0 ? (
                      <p className="text-muted-foreground">No ontology classifications found.</p>
                    ) : (
                      (nodeAnalysis.ontology.classifications || []).map((c, i) => (
                        <div key={i} className="flex items-center gap-2 p-2 border rounded">
                          <Badge variant="outline">{c.ap_level || '?'}</Badge>
                          <span className="font-medium">{c.name}</span>
                          <span className="text-xs text-muted-foreground truncate">{c.uri}</span>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {activeTab === 'similar' && (
                  <div className="space-y-2 text-sm">
                    {(nodeAnalysis.similar || []).length === 0 ? (
                      <p className="text-muted-foreground">No similar nodes found.</p>
                    ) : (
                      (nodeAnalysis.similar || []).map((s, i) => (
                        <div key={i} className="flex items-center gap-2 p-2 border rounded">
                          <GitBranch className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                          <span className="font-medium">{s.uid}</span>
                          <span className="truncate">{s.name}</span>
                          <Badge variant="outline" className="ml-auto text-xs">
                            {(s.labels || []).join(', ')}
                          </Badge>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {activeTab === 'violations' && (
                  <div className="space-y-2 text-sm">
                    {(nodeAnalysis.violations || []).length === 0 ? (
                      <p className="text-green-600">No SHACL violations — node is compliant.</p>
                    ) : (
                      (nodeAnalysis.violations || []).map((v, i) => (
                        <div key={i} className="p-2 border rounded flex items-start gap-2">
                          <Shield className={`h-4 w-4 shrink-0 mt-0.5 ${
                            v.severity === 'Violation' ? 'text-red-500' : 'text-amber-500'
                          }`} />
                          <div>
                            <p className="font-medium">{v.shape}</p>
                            <p className="text-muted-foreground">{v.message}</p>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {activeTab === 'graph' && (
                  <div className="space-y-2 text-sm">
                    <p>
                      <strong>Nodes:</strong> {nodeAnalysis.graph?.node_count ?? 0} |{' '}
                      <strong>Edges:</strong> {nodeAnalysis.graph?.edge_count ?? 0}
                    </p>
                    {(nodeAnalysis.graph?.edges || []).slice(0, 30).map((e, i) => (
                      <div key={i} className="flex items-center gap-1 text-xs">
                        <span className="font-mono">{e.source}</span>
                        <span className="text-primary">—[{e.relationship}]→</span>
                        <span className="font-mono">{e.target}</span>
                      </div>
                    ))}
                  </div>
                )}
              </ScrollArea>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
