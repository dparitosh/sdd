import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@ui/card';
import { Badge } from '@ui/badge';
import { Button } from '@ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@ui/dialog';
import { Input } from '@ui/input';
import { Label } from '@ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@ui/select';
import { Skeleton } from '@ui/skeleton';
import { Alert, AlertDescription } from '@ui/alert';
import { getParameters, validateParameters, getWorkflows, getWorkflow } from '@/services/simulation.service';
import { runOrchestrator, runWorkflowAgent, runDigitalThread, queryOslcResources, queryApStandard } from '@/services/agents.service';
import { toast } from 'sonner';
import {
  Workflow, Play, Plus, GitBranch, CheckCircle2, Trash2,
  AlertCircle, Cpu, ArrowRight, Layers, Activity, ChevronDown, ChevronUp,
} from 'lucide-react';
import PageHeader from '@/components/PageHeader';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const STEP_TYPE_STYLES = {
  prepare:  { bg: 'bg-blue-100 border-blue-300 text-blue-800',        dot: 'bg-blue-500' },
  execute:  { bg: 'bg-purple-100 border-purple-300 text-purple-800',  dot: 'bg-purple-500' },
  validate: { bg: 'bg-amber-100 border-amber-300 text-amber-800',     dot: 'bg-amber-500' },
  analyze:  { bg: 'bg-emerald-100 border-emerald-300 text-emerald-800', dot: 'bg-emerald-500' },
  report:   { bg: 'bg-slate-100 border-slate-300 text-slate-700',     dot: 'bg-slate-400' },
};

const SIM_TYPE_BADGE = {
  Electromagnetic: 'bg-purple-100 text-purple-800',
  CFD:             'bg-cyan-100 text-cyan-800',
  Structural:      'bg-slate-100 text-slate-700',
  Thermal:         'bg-orange-100 text-orange-800',
  NVH:             'bg-blue-100 text-blue-800',
};

const STATUS_BADGE = {
  active:  'bg-emerald-100 text-emerald-800',
  draft:   'bg-amber-100 text-amber-800',
  retired: 'bg-red-100 text-red-700',
};

// Orchestrator task types exposed in the Run dialog
const TASK_TYPE_OPTIONS = [
  { value: 'workflow_execute',      label: 'Execute Workflow (AP243)', group: 'Workflow' },
  { value: 'workflow_validate',     label: 'Validate Parameters (AP243)', group: 'Workflow' },
  { value: 'workflow_query',        label: 'Query WorkflowMethod Nodes', group: 'Workflow' },
  { value: 'digital_thread_trace',  label: 'Trace Digital Thread (AP239↔242↔243)', group: 'Digital Thread' },
  { value: 'oslc_query',            label: 'Query OSLC Lifecycle Resources', group: 'Digital Thread' },
  { value: 'ap_standard_query',     label: 'Query AP Standard Nodes', group: 'Digital Thread' },
  { value: 'mossec_overview',       label: 'MoSSEC Knowledge Graph Overview', group: 'Digital Thread' },
  { value: 'impact_analysis',       label: 'Impact Analysis (MBSE)', group: 'MBSE' },
  { value: 'traceability',          label: 'Traceability Trace (MBSE)', group: 'MBSE' },
  { value: 'semantic_search',       label: 'Semantic Search (RAG)', group: 'Semantic' },
];

// ---------------------------------------------------------------------------
// StepChain
// ---------------------------------------------------------------------------
function StepChain({ steps, compact = false }) {
  if (!steps || steps.length === 0) return null;
  const sorted = [...steps].sort((a, b) => (a.seq || 0) - (b.seq || 0));
  return (
    <div className="flex items-start gap-0 overflow-x-auto pb-2 min-w-0">
      {sorted.map((step, idx) => {
        const style = STEP_TYPE_STYLES[step.type] || STEP_TYPE_STYLES.prepare;
        return (
          <div key={step.uid || idx} className="flex items-center shrink-0">
            <div className="group relative flex flex-col items-center">
              <div className={`flex items-center justify-center w-8 h-8 rounded-full border-2 text-xs font-bold ${style.bg}`}>
                {step.seq}
              </div>
              {!compact && (
                <div className="mt-1 text-center w-20">
                  <p className="text-[9px] font-semibold leading-tight text-muted-foreground line-clamp-2">{step.name}</p>
                  <span className={`inline-block mt-0.5 w-1.5 h-1.5 rounded-full ${style.dot}`} />
                </div>
              )}
              <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 hidden group-hover:flex flex-col bg-popover border rounded-md shadow-md p-2 z-50 w-48 text-xs">
                <span className="font-semibold">{step.seq}. {step.name}</span>
                <span className={`mt-1 inline-flex items-center gap-1 capitalize text-[10px] font-medium ${style.bg} px-1.5 py-0.5 rounded border`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />{step.type}
                </span>
                {step.desc && <span className="mt-1 text-muted-foreground">{step.desc}</span>}
              </div>
            </div>
            {idx < sorted.length - 1 && (
              <ArrowRight className="h-3 w-3 text-muted-foreground mx-1 shrink-0 mt-[-16px]" />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// WorkflowCard
// ---------------------------------------------------------------------------
function WorkflowCard({ summary, onRun, onEdit }) {
  const [expanded, setExpanded] = useState(false);
  const { data: detail, isLoading } = useQuery({
    queryKey: ['workflow-detail', summary.id],
    queryFn: () => getWorkflow(summary.id),
    enabled: expanded,
  });
  const steps     = detail?.steps     || [];
  const runs      = detail?.runs      || [];
  const resources = detail?.resources || [];

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <CardTitle className="flex flex-wrap items-center gap-2 text-base">
              <Workflow className="h-4 w-4 text-primary shrink-0" />
              <span className="truncate">{summary.name}</span>
              <Badge className={STATUS_BADGE[summary.status] || 'bg-gray-100'}>{summary.status || 'unknown'}</Badge>
              {summary.sim_type && <Badge className={SIM_TYPE_BADGE[summary.sim_type] || 'bg-gray-100'}>{summary.sim_type}</Badge>}
              <span className="text-xs text-muted-foreground font-normal">v{summary.version}</span>
            </CardTitle>
            <CardDescription className="mt-1 text-xs line-clamp-1">{summary.purpose}</CardDescription>
            <p className="text-xs text-muted-foreground mt-0.5">
              {summary.step_count} steps · {(summary.run_ids || []).filter(Boolean).length} linked run{(summary.run_ids || []).filter(Boolean).length !== 1 ? 's' : ''}
            </p>
          </div>
          <div className="flex gap-2 shrink-0">
            <Button variant="outline" size="sm" onClick={() => onEdit(summary)}><GitBranch className="h-4 w-4 mr-1" /> Edit</Button>
            <Button size="sm" onClick={() => onRun(summary)}><Play className="h-4 w-4 mr-1" /> Run</Button>
            <Button variant="ghost" size="sm" onClick={() => setExpanded(v => !v)}>
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {summary.step_count > 0 && (
          <div className="mb-3">
            <StepChain
              steps={expanded && steps.length > 0 ? steps : Array.from({ length: summary.step_count }, (_, i) => ({ seq: i + 1, uid: `ph-${i}`, type: 'prepare' }))}
              compact={!expanded || steps.length === 0}
            />
          </div>
        )}
        {expanded && (
          <>
            {isLoading ? (
              <div className="space-y-2 mt-3"><Skeleton className="h-4 w-full" /><Skeleton className="h-4 w-3/4" /></div>
            ) : (
              <div className="space-y-4 mt-3 border-t pt-3">
                {detail?.consequence && (
                  <div>
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1">Consequence</p>
                    <p className="text-sm">{detail.consequence}</p>
                  </div>
                )}
                {steps.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Steps</p>
                    <div className="space-y-1">
                      {steps.map(step => {
                        const style = STEP_TYPE_STYLES[step.type] || STEP_TYPE_STYLES.prepare;
                        return (
                          <div key={step.uid} className="flex items-start gap-3 rounded-md px-3 py-2 bg-muted/30">
                            <div className={`flex items-center justify-center w-6 h-6 rounded-full border text-[10px] font-bold shrink-0 ${style.bg}`}>{step.seq}</div>
                            <div className="min-w-0">
                              <p className="text-sm font-medium">{step.name}</p>
                              <p className="text-xs text-muted-foreground">{step.desc}</p>
                            </div>
                            <span className={`shrink-0 text-[10px] capitalize font-semibold px-1.5 py-0.5 rounded border ${style.bg}`}>{step.type}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
                {resources.filter(r => r?.id).length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2"><Cpu className="inline h-3 w-3 mr-1" />Resources</p>
                    <div className="flex flex-wrap gap-2">
                      {resources.filter(r => r?.id).map(r => (
                        <Badge key={r.id} variant="outline" className="text-xs">{r.name}{r.type && <span className="ml-1 text-muted-foreground">({r.type})</span>}</Badge>
                      ))}
                    </div>
                  </div>
                )}
                {runs.filter(r => r?.id).length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2"><Activity className="inline h-3 w-3 mr-1" />Linked Simulation Runs</p>
                    <div className="flex flex-wrap gap-2">
                      {runs.filter(r => r?.id).map(r => (
                        <Badge key={r.id} variant="outline" className="font-mono text-xs">
                          {r.id}
                          {r.status && <span className={`ml-1.5 w-1.5 h-1.5 rounded-full inline-block ${r.status === 'Completed' ? 'bg-emerald-500' : r.status === 'Running' ? 'bg-blue-500' : 'bg-gray-400'}`} />}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
export default function WorkflowStudio() {
  const navigate = useNavigate();
  const [selectedWorkflow, setSelectedWorkflow] = useState(null);
  const [isRunOpen, setIsRunOpen]   = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [simTypeFilter, setSimTypeFilter] = useState('all');
  const [agentTaskType, setAgentTaskType] = useState('workflow_execute');
  const [selectedParameterId, setSelectedParameterId] = useState('');
  const [parameterValueText, setParameterValueText]   = useState('');
  const [parameterInputs, setParameterInputs]         = useState([]);
  const [validationResults, setValidationResults]     = useState(null);
  const [isValidating, setIsValidating]               = useState(false);
  const [isExecuting, setIsExecuting]                 = useState(false);
  const [executionResults, setExecutionResults]       = useState(null);

  const { data: workflowsResponse, isLoading: loadingWorkflows, error: workflowsError } = useQuery({
    queryKey: ['workflows', simTypeFilter],
    queryFn: () => getWorkflows(simTypeFilter !== 'all' ? { sim_type: simTypeFilter } : undefined),
    staleTime: 60_000,
  });
  const workflows = workflowsResponse?.workflows || [];

  const { data: parametersResponse, isLoading: parametersLoading, refetch: refetchParameters } = useQuery({
    queryKey: ['simulation-parameters', { limit: 250 }],
    queryFn: () => getParameters({ limit: 250, include_constraints: false }),
    enabled: isRunOpen,
  });
  const availableParameters = useMemo(() => {
    const list = parametersResponse?.parameters;
    return Array.isArray(list) ? list : [];
  }, [parametersResponse]);
  const selectedParameter = useMemo(
    () => availableParameters.find(p => p?.id === selectedParameterId) || null,
    [availableParameters, selectedParameterId]
  );

  const totalRuns = useMemo(
    () => workflows.reduce((sum, wf) => sum + (wf.run_ids || []).filter(Boolean).length, 0),
    [workflows]
  );
  const totalResources = useMemo(
    () => new Set(workflows.flatMap(wf => (wf.resources || []).filter(r => r?.id).map(r => r.id))).size,
    [workflows]
  );

  const parseInputValue = (text) => {
    const trimmed = String(text ?? '').trim();
    if (!trimmed) return null;
    try {
      if (trimmed.startsWith('{') || trimmed.startsWith('[') || trimmed === 'true' ||
          trimmed === 'false' || trimmed === 'null' || /^-?\d+(\.\d+)?$/.test(trimmed)) {
        return JSON.parse(trimmed);
      }
    } catch { /* fallthrough */ }
    return trimmed;
  };

  const resetRunDialog = () => {
    setSelectedParameterId(''); setParameterValueText('');
    setParameterInputs([]); setValidationResults(null);
    setExecutionResults(null); setIsValidating(false); setIsExecuting(false);
  };

  const openRunDialog = async (workflow) => {
    setSelectedWorkflow(workflow); setIsRunOpen(true); resetRunDialog();
    await refetchParameters();
  };

  const addParameterInput = () => {
    if (!selectedParameterId) { toast.error('Select a parameter first'); return; }
    const value = parseInputValue(parameterValueText);
    if (value === null) { toast.error('Enter a value to validate'); return; }
    const parameterName = selectedParameter?.name || selectedParameterId;
    setParameterInputs(prev => {
      const without = prev.filter(p => p.id !== selectedParameterId);
      return [...without, { id: selectedParameterId, name: parameterName, valueText: String(parameterValueText) }];
    });
    setParameterValueText(''); setValidationResults(null);
  };

  const removeParameterInput = (id) => {
    setParameterInputs(prev => prev.filter(p => p.id !== id));
    setValidationResults(null);
  };

  const validateInputs = async () => {
    if (parameterInputs.length === 0) { toast.error('Add at least one parameter input'); return null; }
    setIsValidating(true); setValidationResults(null);
    try {
      const payload = parameterInputs.map(p => ({ id: p.id, value: parseInputValue(p.valueText) }));
      const response = await validateParameters(payload);
      setValidationResults(response);
      if (response?.invalid_count > 0) {
        toast.error('Validation failed', { description: `${response.invalid_count} parameter(s) invalid` });
      } else {
        toast.success('Validation passed', { description: `${response.valid_count} parameter(s) valid` });
      }
      return response;
    } finally { setIsValidating(false); }
  };

  const runWorkflow = async () => {
    const response = await validateInputs();
    if (!response || response?.invalid_count > 0) return;
    setIsExecuting(true); setExecutionResults(null);
    try {
      const paramStr = parameterInputs.map(p => `${p.name}=${p.valueText}`).join(', ');
      const query = `${agentTaskType === 'workflow_execute' ? 'Execute' : 'Process'} `
        + `${selectedWorkflow?.name || 'workflow'}`
        + (paramStr ? ` with parameters: ${paramStr}` : '');

      const taskLabel = TASK_TYPE_OPTIONS.find(t => t.value === agentTaskType)?.label || agentTaskType;
      toast.info(`Starting: ${taskLabel}`, { description: 'Routing to orchestrator agent…' });

      let result;
      if (agentTaskType === 'digital_thread_trace') {
        result = await runDigitalThread(query);
      } else if (agentTaskType === 'oslc_query') {
        result = await queryOslcResources(query);
      } else if (agentTaskType === 'ap_standard_query') {
        result = await queryApStandard(query);
      } else if (['workflow_execute', 'workflow_validate', 'workflow_query'].includes(agentTaskType)) {
        result = await runWorkflowAgent(query, agentTaskType);
      } else {
        result = await runOrchestrator(query, agentTaskType);
      }

      setExecutionResults(result);
      if (result.status === 'success') {
        toast.success('Agent Task Complete', { description: taskLabel });
      } else {
        toast.error('Agent Task Failed', { description: result.error || 'Unknown error' });
      }
    } catch (error) {
      console.error(error); toast.error('Execution Error', { description: error.message });
    } finally { setIsExecuting(false); }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <PageHeader
        title="Workflow Studio"
        description="STEP AP243 simulation workflows — WorkflowMethod nodes with ordered TaskElement step chains"
        icon={<Workflow className="h-8 w-8 text-primary" />}
        breadcrumbs={[
          { label: 'Simulation Engineering', href: '/simulation/models' },
          { label: 'Workflow Studio' },
        ]}
        actions={
          <Button onClick={() => toast.info('Feature Unavailable', { description: 'Workflow creation is currently under development.' })}>
            <Plus className="h-4 w-4 mr-2" /> Create Workflow
          </Button>
        }
      />

      {/* Step type legend */}
      <div className="flex flex-wrap gap-2 text-xs">
        <span className="text-muted-foreground font-medium">Step types:</span>
        {Object.entries(STEP_TYPE_STYLES).map(([type, s]) => (
          <span key={type} className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border capitalize ${s.bg}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} /> {type}
          </span>
        ))}
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-muted-foreground">Sim type:</span>
        {['all', 'Electromagnetic', 'CFD', 'Structural', 'Thermal', 'NVH'].map(t => (
          <Button key={t} variant={simTypeFilter === t ? 'default' : 'outline'} size="sm" onClick={() => setSimTypeFilter(t)}>
            {t === 'all' ? 'All' : t}
          </Button>
        ))}
      </div>

      {/* Error */}
      {workflowsError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>Failed to load workflows: {workflowsError.message}</AlertDescription>
        </Alert>
      )}

      {/* Workflow cards */}
      <div className="space-y-4">
        {loadingWorkflows ? (
          [...Array(3)].map((_, i) => <Skeleton key={i} className="h-40 w-full" />)
        ) : workflows.length === 0 ? (
          <Card>
            <CardContent className="pt-8 pb-8 text-center text-muted-foreground">
              <Workflow className="h-10 w-10 mx-auto mb-3 opacity-30" />
              <p className="font-medium">No workflows found</p>
              <p className="text-sm mt-1">
                Run <code className="bg-muted px-1 rounded text-xs">python backend/scripts/seed_workflows.py</code> to seed AP243 workflow nodes.
              </p>
            </CardContent>
          </Card>
        ) : (
          workflows.map(wf => (
            <WorkflowCard
              key={wf.id}
              summary={wf}
              onRun={openRunDialog}
              onEdit={(w) => { setSelectedWorkflow(w); setIsEditOpen(true); }}
            />
          ))
        )}
      </div>

      {/* Visual Builder placeholder */}
      <Card className="bg-gradient-to-br from-primary/5 to-primary/10">
        <CardHeader>
          <CardTitle>Visual Workflow Builder</CardTitle>
          <CardDescription>Drag-and-drop interface coming soon</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { Icon: CheckCircle2, title: 'Input Configuration', desc: 'Define workflow inputs' },
              { Icon: Workflow,     title: 'Processing Steps',    desc: 'Chain simulation tasks' },
              { Icon: Layers,       title: 'Output Collection',   desc: 'Store and analyze results' },
            ].map(({ Icon, title, desc }) => (
              <div key={title} className="p-4 border-2 border-dashed rounded-lg text-center">
                <Icon className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                <p className="text-sm font-medium">{title}</p>
                <p className="text-xs text-muted-foreground">{desc}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card><CardContent className="pt-6">
          <div className="text-2xl font-bold">{loadingWorkflows ? '—' : workflows.length}</div>
          <p className="text-sm text-muted-foreground">Workflow Methods</p>
        </CardContent></Card>
        <Card><CardContent className="pt-6">
          <div className="text-2xl font-bold text-green-500">{loadingWorkflows ? '—' : totalRuns}</div>
          <p className="text-sm text-muted-foreground">Linked Simulation Runs</p>
        </CardContent></Card>
        <Card><CardContent className="pt-6">
          <div className="text-2xl font-bold text-blue-500">
            {loadingWorkflows ? '—' : workflows.reduce((s, wf) => s + (wf.step_count || 0), 0)}
          </div>
          <p className="text-sm text-muted-foreground">Total Task Elements</p>
        </CardContent></Card>
        <Card><CardContent className="pt-6">
          <div className="text-2xl font-bold text-amber-500">{loadingWorkflows ? '—' : totalResources}</div>
          <p className="text-sm text-muted-foreground">Action Resources</p>
        </CardContent></Card>
      </div>

      {/* Edit Dialog */}
      <Dialog open={isEditOpen} onOpenChange={(o) => { setIsEditOpen(o); if (!o) setSelectedWorkflow(null); }}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2"><GitBranch className="h-5 w-5 text-primary" /> Edit Workflow</DialogTitle>
            <DialogDescription>Workflow persistence is currently under development.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2"><Label>Workflow</Label><Input value={selectedWorkflow?.name || ''} readOnly /></div>
            <div className="space-y-2"><Label>Status</Label><Input value={selectedWorkflow?.status || ''} readOnly /></div>
            <div className="space-y-2"><Label>Sim Type</Label><Input value={selectedWorkflow?.sim_type || ''} readOnly /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditOpen(false)}>Close</Button>
            <Button onClick={() => toast.info('Feature Unavailable', { description: 'Workflow persistence is not yet implemented.' })}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Run Dialog */}
      <Dialog open={isRunOpen} onOpenChange={(o) => { setIsRunOpen(o); if (!o) { setSelectedWorkflow(null); resetRunDialog(); } }}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2"><Play className="h-5 w-5 text-primary" /> Run Workflow</DialogTitle>
            <DialogDescription>Validate parameters against graph constraints before execution.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2"><Label>Workflow</Label><Input value={selectedWorkflow?.name || ''} readOnly /></div>
              <div className="space-y-2">
                <Label>Agent Task Type</Label>
                <Select value={agentTaskType} onValueChange={setAgentTaskType}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {['Workflow', 'Digital Thread', 'MBSE', 'Semantic'].map(group => (
                      <>
                        <div key={group} className="px-2 py-1 text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">{group}</div>
                        {TASK_TYPE_OPTIONS.filter(t => t.group === group).map(t => (
                          <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                        ))}
                      </>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Parameter</Label>
                <Select value={selectedParameterId} onValueChange={setSelectedParameterId}>
                  <SelectTrigger>
                    <SelectValue placeholder={parametersLoading ? 'Loading parameters…' : 'Select a parameter'} />
                  </SelectTrigger>
                  <SelectContent>
                    {availableParameters.slice(0, 200).map(p => (
                      <SelectItem key={p.id} value={p.id}>
                        {p.owner?.name ? `${p.owner.name} :: ` : ''}{p.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-[1fr_auto]">
              <div className="space-y-2">
                <Label>Value (JSON supported)</Label>
                <Input
                  placeholder={selectedParameter ? `Value for ${selectedParameter.name}` : 'Enter a value'}
                  value={parameterValueText}
                  onChange={e => setParameterValueText(e.target.value)}
                />
              </div>
              <div className="flex items-end">
                <Button variant="outline" onClick={addParameterInput} disabled={parametersLoading}>Add</Button>
              </div>
            </div>
            <div className="rounded-lg border bg-muted/20 p-3">
              <div className="text-sm font-medium mb-2">Inputs</div>
              {parameterInputs.length === 0 ? (
                <div className="text-sm text-muted-foreground">No inputs added yet.</div>
              ) : (
                <div className="space-y-2">
                  {parameterInputs.map(p => (
                    <div key={p.id} className="flex items-center justify-between gap-3 rounded-md bg-background px-3 py-2">
                      <div className="min-w-0">
                        <div className="text-sm font-medium truncate">{p.name}</div>
                        <div className="text-xs text-muted-foreground truncate">{p.id}</div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge variant="outline" className="max-w-[260px] truncate">{p.valueText}</Badge>
                        <Button variant="ghost" size="sm" onClick={() => removeParameterInput(p.id)}><Trash2 className="h-4 w-4" /></Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            {validationResults && (
              <div className="rounded-lg border p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="text-sm font-medium">Validation Results</div>
                  <div className="flex gap-2">
                    <Badge variant="outline">Valid: {validationResults.valid_count}</Badge>
                    <Badge variant={validationResults.invalid_count > 0 ? 'destructive' : 'secondary'}>Invalid: {validationResults.invalid_count}</Badge>
                  </div>
                </div>
                <div className="space-y-2">
                  {(validationResults.results || []).map(r => (
                    <div key={r.parameter_id} className="flex items-start justify-between gap-3 rounded-md bg-muted/20 px-3 py-2">
                      <div className="min-w-0">
                        <div className="text-sm font-medium truncate">{r.parameter_name || r.parameter_id}</div>
                        {r.violations?.length > 0 && <div className="text-xs text-muted-foreground mt-1">{r.violations.join(' • ')}</div>}
                      </div>
                      <Badge variant={r.valid ? 'secondary' : 'destructive'}>{r.valid ? 'Valid' : 'Invalid'}</Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {executionResults && (
              <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-4 mt-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="text-sm font-semibold flex items-center gap-2">
                    <Workflow className="h-4 w-4 text-blue-500" /> Agent Orchestration
                  </div>
                  <Badge variant={executionResults.status === 'success' ? 'default' : 'destructive'}>
                    {(executionResults.status || 'unknown').toUpperCase()}
                  </Badge>
                </div>
                <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2">
                  {executionResults.messages?.map((msg, idx) => (
                    <div key={idx} className={`flex gap-3 text-sm ${msg.role === 'ai' ? 'bg-background p-2 rounded-lg border' : 'pl-4'}`}>
                      <div className={`mt-0.5 shrink-0 ${msg.role === 'ai' ? 'text-blue-500' : 'text-muted-foreground'}`}>
                        {msg.role === 'ai' ? '🤖' : '👤'}
                      </div>
                      <div className="space-y-1">
                        <div className="font-medium text-xs text-muted-foreground uppercase">{msg.type?.replace('Message', '') || msg.role}</div>
                        <div className="whitespace-pre-wrap">{msg.content}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsRunOpen(false)}>Close</Button>
            <Button variant="outline" onClick={validateInputs} disabled={isValidating || isExecuting || parametersLoading}>
              {isValidating ? 'Validating…' : 'Validate'}
            </Button>
            <Button onClick={runWorkflow} disabled={isValidating || isExecuting || parametersLoading}>
              {isExecuting ? 'Running Agents...' : 'Run Agents'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
