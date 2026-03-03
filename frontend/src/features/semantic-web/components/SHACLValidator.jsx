import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@ui/card';
import { Button } from '@ui/button';
import { Badge } from '@ui/badge';
import { Label } from '@ui/label';
import { Input } from '@ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@ui/select';
import { ScrollArea } from '@ui/scroll-area';
import { Alert, AlertDescription } from '@ui/alert';
import { Separator } from '@ui/separator';
import PageHeader from '@/components/PageHeader';
import { ShieldCheck, CheckCircle2, XCircle, AlertTriangle, Loader2, BarChart3 } from 'lucide-react';
import { useSHACL } from '../hooks/useSHACL';
import { validateLabel, getViolations, getSHACLReport } from '@/services/validation.service';

const SHAPE_OPTIONS = [
  { value: 'ap239_requirement', label: 'AP239 Requirement' },
  { value: 'ap242_part', label: 'AP242 Part' },
  { value: 'sdd_dossier', label: 'SDD Dossier' },
  { value: 'approval_record', label: 'Approval Record' },
];

const LABEL_OPTIONS = [
  { value: 'PLMXMLItem', label: 'PLMXMLItem' },
  { value: 'PLMXMLRevision', label: 'PLMXMLRevision' },
  { value: 'PLMXMLBOMLine', label: 'PLMXMLBOMLine' },
  { value: 'PLMXMLDataSet', label: 'PLMXMLDataSet' },
  { value: 'StepFile', label: 'StepFile' },
];

const SEVERITY_COLORS = {
  error: 'bg-red-500 text-white',
  warning: 'bg-amber-500 text-white',
  info: 'bg-yellow-400 text-black',
};

function ComplianceGauge({ violations, total }) {
  const compliant = Math.max(0, total - violations);
  const pct = total > 0 ? Math.round((compliant / total) * 100) : 100;
  const color = pct >= 90 ? 'text-green-500' : pct >= 70 ? 'text-amber-500' : 'text-red-500';
  return (
    <div className="flex items-center gap-3">
      <BarChart3 className={`h-5 w-5 ${color}`} />
      <div className="flex-1">
        <div className="flex justify-between text-sm mb-1">
          <span className="font-medium">Compliance Score</span>
          <span className={`font-bold ${color}`}>{pct}%</span>
        </div>
        <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
          <div className={`h-full rounded-full ${pct >= 90 ? 'bg-green-500' : pct >= 70 ? 'bg-amber-500' : 'bg-red-500'}`} style={{ width: `${pct}%` }} />
        </div>
        <p className="text-xs text-muted-foreground mt-1">{compliant} / {total} nodes compliant</p>
      </div>
    </div>
  );
}

export default function SHACLValidator() {
  const [shapeName, setShapeName] = useState('');
  const [rdfInput, setRdfInput] = useState('');
  const { validate, result, isValidating, error } = useSHACL();

  // Batch validation by label
  const [batchLabel, setBatchLabel] = useState('');
  const [batchResult, setBatchResult] = useState(null);
  const [batchLoading, setBatchLoading] = useState(false);
  const [batchError, setBatchError] = useState(null);

  // Per-node violation lookup
  const [nodeUid, setNodeUid] = useState('');
  const [nodeViolations, setNodeViolations] = useState(null);
  const [nodeLoading, setNodeLoading] = useState(false);
  const [nodeError, setNodeError] = useState(null);

  // Summary report
  const [report, setReport] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState(null);

  const handleValidate = () => {
    if (!rdfInput.trim()) return;
    validate({ data: rdfInput.trim(), shapeName: shapeName || undefined });
  };

  const handleBatchValidate = async () => {
    if (!batchLabel) return;
    setBatchLoading(true);
    setBatchError(null);
    try {
      const data = await validateLabel(batchLabel);
      setBatchResult(data);
    } catch (err) {
      setBatchError(err.message ?? String(err));
    } finally {
      setBatchLoading(false);
    }
  };

  const handleNodeLookup = async () => {
    if (!nodeUid.trim()) return;
    setNodeLoading(true);
    setNodeError(null);
    try {
      const data = await getViolations(nodeUid.trim());
      setNodeViolations(data);
    } catch (err) {
      setNodeError(err.message ?? String(err));
    } finally {
      setNodeLoading(false);
    }
  };

  const handleReport = async () => {
    setReportLoading(true);
    setReportError(null);
    try {
      const data = await getSHACLReport();
      setReport(data);
    } catch (err) {
      setReportError(err.message ?? String(err));
    } finally {
      setReportLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <PageHeader
        title="SHACL Validator"
        description="Validate RDF data against SHACL shape definitions"
        icon={<ShieldCheck className="h-6 w-6 text-primary" />}
      />

      {/* ── Manual RDF Validation ── */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Input panel */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Manual Input</CardTitle>
            <CardDescription>Paste or type RDF data (Turtle, JSON-LD, or N-Triples) and select a shape</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label>Shape Definition</Label>
              <Select value={shapeName} onValueChange={setShapeName}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a shape…" />
                </SelectTrigger>
                <SelectContent>
                  {SHAPE_OPTIONS.map((s) => (
                    <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label>RDF Data</Label>
              <textarea
                className="w-full h-64 rounded-md border bg-background px-3 py-2 text-sm font-mono resize-y focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                placeholder={'@prefix ex: <http://example.org/> .\n\nex:myResource a ex:Requirement ;\n  ex:name "Sample" .'}
                value={rdfInput}
                onChange={(e) => setRdfInput(e.target.value)}
              />
            </div>

            <Button onClick={handleValidate} disabled={isValidating || !rdfInput.trim()}>
              {isValidating ? 'Validating…' : 'Validate'}
            </Button>
          </CardContent>
        </Card>

        {/* Results panel */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Manual Results</CardTitle>
            <CardDescription>Validation conformance and violation details</CardDescription>
          </CardHeader>
          <CardContent>
            {error && (
              <Alert variant="destructive" className="mb-4"><AlertDescription>{String(error)}</AlertDescription></Alert>
            )}

            {!result ? (
              <p className="text-sm text-muted-foreground text-center py-12">Run validation to see results</p>
            ) : (
              <div className="space-y-4">
                {/* Conformance badge */}
                <div className="flex items-center gap-3">
                  {result.conforms ? (
                    <Badge className="bg-green-500 text-white gap-1"><CheckCircle2 className="h-3 w-3" /> Conforms</Badge>
                  ) : (
                    <Badge variant="destructive" className="gap-1"><XCircle className="h-3 w-3" /> Does Not Conform</Badge>
                  )}
                  <span className="text-sm text-muted-foreground">
                    {(result.violations ?? []).length} violation{(result.violations ?? []).length !== 1 ? 's' : ''}
                  </span>
                </div>

                <Separator />

                {/* Violations list */}
                <ScrollArea className="h-72">
                  {(result.violations ?? []).length === 0 ? (
                    <p className="text-sm text-muted-foreground">No violations found</p>
                  ) : (
                    <ul className="space-y-3">
                      {result.violations.map((v, i) => (
                        <li key={i} className="rounded border p-3 space-y-1">
                          <div className="flex items-center gap-2">
                            <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />
                            <span className="text-sm font-medium">{v.message ?? 'Validation violation'}</span>
                          </div>
                          {v.path && <p className="text-xs text-muted-foreground ml-6">Path: <code className="bg-muted px-1 rounded">{v.path}</code></p>}
                          {v.focus_node && <p className="text-xs text-muted-foreground ml-6">Focus: {v.focus_node}</p>}
                          {v.severity && <Badge variant="outline" className="ml-6 text-xs">{v.severity}</Badge>}
                        </li>
                      ))}
                    </ul>
                  )}
                </ScrollArea>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ── Batch Validation by Label ── */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Batch Validation</CardTitle>
            <CardDescription>Validate all Neo4j nodes of a given label against SHACL shapes</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label>Node Label</Label>
              <Select value={batchLabel} onValueChange={setBatchLabel}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a node label…" />
                </SelectTrigger>
                <SelectContent>
                  {LABEL_OPTIONS.map((l) => (
                    <SelectItem key={l.value} value={l.value}>{l.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button onClick={handleBatchValidate} disabled={batchLoading || !batchLabel}>
              {batchLoading ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Validating…</> : 'Run Validation'}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Batch Results</CardTitle>
            <CardDescription>Violations found across all nodes of the selected label</CardDescription>
          </CardHeader>
          <CardContent>
            {batchError && (
              <Alert variant="destructive" className="mb-4"><AlertDescription>{batchError}</AlertDescription></Alert>
            )}

            {!batchResult ? (
              <p className="text-sm text-muted-foreground text-center py-8">Select a label and run batch validation</p>
            ) : (
              <div className="space-y-4">
                <ComplianceGauge violations={batchResult.violation_count ?? 0} total={batchResult.total_nodes ?? 0} />
                <Separator />
                <ScrollArea className="h-64">
                  {(batchResult.violations ?? []).length === 0 ? (
                    <p className="text-sm text-muted-foreground">All nodes comply with SHACL shapes</p>
                  ) : (
                    <ul className="space-y-3">
                      {batchResult.violations.map((v, i) => (
                        <li key={i} className="rounded border p-3 space-y-1">
                          <div className="flex items-center gap-2">
                            <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />
                            <span className="text-sm font-medium">{v.message ?? 'Violation'}</span>
                          </div>
                          {v.uid && (
                            <a
                              href={`/graph-explorer?uid=${encodeURIComponent(v.uid)}`}
                              className="text-xs text-blue-500 hover:underline ml-6 inline-block"
                            >
                              View in Graph: {v.uid}
                            </a>
                          )}
                          {v.shape && <p className="text-xs text-muted-foreground ml-6">Shape: {v.shape}</p>}
                          {v.severity && (
                            <Badge className={`ml-6 text-xs ${SEVERITY_COLORS[v.severity] ?? 'bg-gray-400 text-white'}`}>
                              {v.severity}
                            </Badge>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </ScrollArea>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ── Per-Node Lookup + Summary Report ── */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Per-node violation lookup */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Per-Node Lookup</CardTitle>
            <CardDescription>Look up SHACL violations for a specific node UID</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <Input
                placeholder="Enter node UID…"
                value={nodeUid}
                onChange={(e) => setNodeUid(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleNodeLookup()}
              />
              <Button onClick={handleNodeLookup} disabled={nodeLoading || !nodeUid.trim()}>
                {nodeLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Look up'}
              </Button>
            </div>

            {nodeError && (
              <Alert variant="destructive"><AlertDescription>{nodeError}</AlertDescription></Alert>
            )}

            {nodeViolations && (
              <ScrollArea className="h-48">
                {(nodeViolations.violations ?? []).length === 0 ? (
                  <div className="flex items-center gap-2 py-4">
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                    <span className="text-sm font-medium">Node is fully compliant</span>
                  </div>
                ) : (
                  <ul className="space-y-2">
                    {nodeViolations.violations.map((v, i) => (
                      <li key={i} className="rounded border p-2 text-sm space-y-1">
                        <div className="flex items-center gap-2">
                          <AlertTriangle className="h-3.5 w-3.5 text-amber-500 shrink-0" />
                          <span>{v.message ?? 'Violation'}</span>
                        </div>
                        {v.shape && <p className="text-xs text-muted-foreground ml-5">Shape: {v.shape}</p>}
                        {v.severity && (
                          <Badge className={`ml-5 text-xs ${SEVERITY_COLORS[v.severity] ?? 'bg-gray-400 text-white'}`}>
                            {v.severity}
                          </Badge>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </ScrollArea>
            )}
          </CardContent>
        </Card>

        {/* Summary report */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Summary Report</CardTitle>
            <CardDescription>Full SHACL compliance report across the entire knowledge graph</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button onClick={handleReport} disabled={reportLoading} variant="outline">
              {reportLoading ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Generating…</> : 'Generate Report'}
            </Button>

            {reportError && (
              <Alert variant="destructive"><AlertDescription>{reportError}</AlertDescription></Alert>
            )}

            {report && (
              <div className="space-y-4">
                <ComplianceGauge violations={report.total_violations ?? 0} total={report.total_nodes ?? 0} />
                <Separator />
                <ScrollArea className="h-48">
                  {(report.by_label ?? []).length === 0 ? (
                    <p className="text-sm text-muted-foreground">No label breakdown available</p>
                  ) : (
                    <ul className="space-y-2">
                      {report.by_label.map((entry, i) => (
                        <li key={i} className="flex items-center justify-between rounded border p-2 text-sm">
                          <span className="font-medium">{entry.label}</span>
                          <div className="flex items-center gap-3">
                            <span className="text-muted-foreground">{entry.checked} checked</span>
                            {entry.violations > 0 ? (
                              <Badge variant="destructive" className="text-xs">{entry.violations} violations</Badge>
                            ) : (
                              <Badge className="bg-green-500 text-white text-xs">Clean</Badge>
                            )}
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </ScrollArea>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
