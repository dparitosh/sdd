import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@ui/card';
import { Badge } from '@ui/badge';
import { Button } from '@ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@ui/dialog';
import { Input } from '@ui/input';
import { Label } from '@ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@ui/select';
import { apiService } from '@/services/api';
import { toast } from 'sonner';
import { Workflow, Play, Plus, GitBranch, CheckCircle2, Trash2 } from 'lucide-react';
import PageHeader from '@/components/PageHeader';

export default function WorkflowStudio() {
  const [selectedWorkflow, setSelectedWorkflow] = useState(null);
  const [isRunOpen, setIsRunOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [selectedParameterId, setSelectedParameterId] = useState('');
  const [parameterValueText, setParameterValueText] = useState('');
  const [parameterInputs, setParameterInputs] = useState([]);
  const [validationResults, setValidationResults] = useState(null);
  const [isValidating, setIsValidating] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResults, setExecutionResults] = useState(null);

  // NOTE: Workflows are currently hardcoded for demonstration as the backend
  // does not yet support workflow persistence/retrieval.
  const workflows = [
    {
      name: 'Demo: Thermal Analysis',
      steps: 5,
      status: 'active',
      lastRun: '—',
      runs: 0,
    },
    {
      name: 'Demo: Multi-Physics',
      steps: 8,
      status: 'draft',
      lastRun: '—',
      runs: 0,
    },
  ];

  const { data: parametersResponse, isLoading: parametersLoading, refetch: refetchParameters } = useQuery({
    queryKey: ['simulation-parameters', { limit: 250 }],
    queryFn: () => apiService.simulation.getParameters({ limit: 250, include_constraints: false }),
    enabled: isRunOpen,
  });

  const availableParameters = useMemo(() => {
    const list = parametersResponse?.parameters;
    return Array.isArray(list) ? list : [];
  }, [parametersResponse]);

  const selectedParameter = useMemo(() => {
    return availableParameters.find((p) => p?.id === selectedParameterId) || null;
  }, [availableParameters, selectedParameterId]);

  const parseInputValue = (text) => {
    const trimmed = String(text ?? '').trim();
    if (!trimmed) return null;

    // Try JSON for arrays/objects/strings/numbers/bools
    try {
      if (
        trimmed.startsWith('{') ||
        trimmed.startsWith('[') ||
        trimmed === 'true' ||
        trimmed === 'false' ||
        trimmed === 'null' ||
        /^-?\d+(\.\d+)?$/.test(trimmed)
      ) {
        return JSON.parse(trimmed);
      }
    } catch {
      // fall through
    }

    // Fallback: plain string
    return trimmed;
  };

  const resetRunDialog = () => {
    setSelectedParameterId('');
    setParameterValueText('');
    setParameterInputs([]);
    setValidationResults(null);
    setExecutionResults(null);
    setIsValidating(false);
    setIsExecuting(false);
  };

  const openRunDialog = async (workflow) => {
    setSelectedWorkflow(workflow);
    setIsRunOpen(true);
    resetRunDialog();
    // Ensure parameters are fetched on open even if cached disabled/refreshed.
    await refetchParameters();
  };

  const openEditDialog = (workflow) => {
    setSelectedWorkflow(workflow);
    setIsEditOpen(true);
  };

  const addParameterInput = () => {
    if (!selectedParameterId) {
      toast.error('Select a parameter first');
      return;
    }
    const value = parseInputValue(parameterValueText);
    if (value === null) {
      toast.error('Enter a value to validate');
      return;
    }

    const parameterName = selectedParameter?.name || selectedParameterId;
    setParameterInputs((prev) => {
      const withoutExisting = prev.filter((p) => p.id !== selectedParameterId);
      return [...withoutExisting, { id: selectedParameterId, name: parameterName, valueText: String(parameterValueText) }];
    });

    setParameterValueText('');
    setValidationResults(null);
  };

  const removeParameterInput = (id) => {
    setParameterInputs((prev) => prev.filter((p) => p.id !== id));
    setValidationResults(null);
  };

  const validateInputs = async () => {
    if (parameterInputs.length === 0) {
      toast.error('Add at least one parameter input');
      return null;
    }

    setIsValidating(true);
    setValidationResults(null);
    try {
      const payload = parameterInputs.map((p) => ({ id: p.id, value: parseInputValue(p.valueText) }));
      const response = await apiService.simulation.validateParameters(payload);
      setValidationResults(response);

      if (response?.invalid_count > 0) {
        toast.error('Validation failed', {
          description: `${response.invalid_count} parameter(s) invalid`,
        });
      } else {
        toast.success('Validation passed', {
          description: `${response.valid_count} parameter(s) valid`,
        });
      }

      return response;
    } finally {
      setIsValidating(false);
    }
  };

  const runWorkflow = async () => {
    // Phase 1: validate parameters logic (legacy)
    const response = await validateInputs();
    if (!response || response?.invalid_count > 0) return;
    
    // Phase 2: Execute Multi-Agent Orchestrator
    setIsExecuting(true);
    setExecutionResults(null);
    try {
      // Construct a natural language query from the workflow context
      const query = `Execute ${selectedWorkflow?.name || 'simulation workflow'} with parameters: ${parameterInputs.map(p => `${p.name}=${p.valueText}`).join(', ')}`;
      
      toast.info('Starting Multi-Agent Orchestration', {
        description: 'MBSE, PLM, and Simulation agents are collaborating...',
      });

      const result = await apiService.agents.runOrchestrator(query, 'impact_analysis');
      setExecutionResults(result);
      
      if (result.status === 'success') {
        toast.success('Workflow Execution Complete', {
          description: 'Agents successfully coordinated the task.',
        });
      } else {
        toast.error('Workflow Execution Failed', {
          description: result.error || 'Unknown error occurred',
        });
      }
    } catch (error) {
       console.error(error);
       toast.error('Execution Error', { description: error.message });
    } finally {
       setIsExecuting(false);
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <PageHeader
        title="Workflow Studio"
        description="Design and execute automated simulation workflows"
        icon={<Workflow className="h-8 w-8 text-primary" />}
        breadcrumbs={[
          { label: 'Simulation Engineering', href: '/simulation/models' },
          { label: 'Workflow Studio' },
        ]}
        actions={
          <Button
            onClick={() =>
              toast.info('Feature Unavailable', {
                description: 'Workflow creation is currently under development.',
              })
            }
          >
            <Plus className="h-4 w-4 mr-2" />
            Create Workflow
          </Button>
        }
      />

      <div className="space-y-4">
        {workflows.map(workflow => (
          <Card
            key={workflow.name}
            className="hover:shadow-md transition-shadow"
          >
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-3">
                    {workflow.name}
                    <Badge
                      variant={
                        workflow.status === 'active' ? 'default' : 'secondary'
                      }
                    >
                      {workflow.status}
                    </Badge>
                  </CardTitle>
                  <CardDescription className="mt-2">
                    {workflow.steps} steps · {workflow.runs} total runs · Last run{' '}
                    {workflow.lastRun}
                  </CardDescription>
                </div>

                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => openEditDialog(workflow)}>
                    <GitBranch className="h-4 w-4 mr-2" />
                    Edit
                  </Button>
                  <Button size="sm" onClick={() => openRunDialog(workflow)}>
                    <Play className="h-4 w-4 mr-2" />
                    Run
                  </Button>
                </div>
              </div>
            </CardHeader>

            <CardContent>
              <div className="flex items-center gap-2 overflow-x-auto pb-2">
                {Array.from({ length: workflow.steps }).map((_, stepIdx) => (
                  <div
                    key={`${workflow.name}-${stepIdx}`}
                    className="flex items-center"
                  >
                    <div className="flex items-center justify-center h-10 w-10 rounded-full bg-primary/10 text-primary font-medium text-sm shrink-0">
                      {stepIdx + 1}
                    </div>
                    {stepIdx < workflow.steps - 1 && (
                      <div className="h-0.5 w-8 bg-muted mx-1" />
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="bg-linear-to-br from-primary/5 to-primary/10">
        <CardHeader>
          <CardTitle>Visual Workflow Builder</CardTitle>
          <CardDescription>Drag-and-drop interface coming soon</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 border-2 border-dashed rounded-lg text-center">
              <CheckCircle2 className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
              <p className="text-sm font-medium">Input Configuration</p>
              <p className="text-xs text-muted-foreground">Define workflow inputs</p>
            </div>
            <div className="p-4 border-2 border-dashed rounded-lg text-center">
              <Workflow className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
              <p className="text-sm font-medium">Processing Steps</p>
              <p className="text-xs text-muted-foreground">Chain simulation tasks</p>
            </div>
            <div className="p-4 border-2 border-dashed rounded-lg text-center">
              <CheckCircle2 className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
              <p className="text-sm font-medium">Output Collection</p>
              <p className="text-xs text-muted-foreground">Store and analyze results</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">8</div>
            <p className="text-sm text-muted-foreground">Active Workflows</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-green-500">156</div>
            <p className="text-sm text-muted-foreground">Successful Runs</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-blue-500">2.3h</div>
            <p className="text-sm text-muted-foreground">Avg Execution Time</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-amber-500">3</div>
            <p className="text-sm text-muted-foreground">Queued Jobs</p>
          </CardContent>
        </Card>
      </div>

      <Dialog
        open={isEditOpen}
        onOpenChange={(open) => {
          setIsEditOpen(open);
          if (!open) setSelectedWorkflow(null);
        }}
      >
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <GitBranch className="h-5 w-5 text-primary" />
              Edit Workflow
            </DialogTitle>
            <DialogDescription>
              This feature is currently under development.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>Workflow</Label>
              <Input value={selectedWorkflow?.name || ''} readOnly />
            </div>
            <div className="space-y-2">
              <Label>Status</Label>
              <Input value={selectedWorkflow?.status || ''} readOnly />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditOpen(false)}>
              Close
            </Button>
            <Button
              onClick={() =>
                toast.info('Feature Unavailable', {
                  description: 'Workflow persistence is not yet implemented.',
                })
              }
            >
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={isRunOpen}
        onOpenChange={(open) => {
          setIsRunOpen(open);
          if (!open) {
            setSelectedWorkflow(null);
            resetRunDialog();
          }
        }}
      >
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Play className="h-5 w-5 text-primary" />
              Run Workflow
            </DialogTitle>
            <DialogDescription>
              Validate parameters against graph constraints before execution.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Workflow</Label>
                <Input value={selectedWorkflow?.name || ''} readOnly />
              </div>

              <div className="space-y-2">
                <Label>Parameter</Label>
                <Select value={selectedParameterId} onValueChange={setSelectedParameterId}>
                  <SelectTrigger>
                    <SelectValue
                      placeholder={parametersLoading ? 'Loading parameters…' : 'Select a parameter'}
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {availableParameters.slice(0, 200).map((p) => (
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
                  onChange={(e) => setParameterValueText(e.target.value)}
                />
              </div>
              <div className="flex items-end">
                <Button variant="outline" onClick={addParameterInput} disabled={parametersLoading}>
                  Add
                </Button>
              </div>
            </div>

            <div className="rounded-lg border bg-muted/20 p-3">
              <div className="text-sm font-medium mb-2">Inputs</div>
              {parameterInputs.length === 0 ? (
                <div className="text-sm text-muted-foreground">No inputs added yet.</div>
              ) : (
                <div className="space-y-2">
                  {parameterInputs.map((p) => (
                    <div key={p.id} className="flex items-center justify-between gap-3 rounded-md bg-background px-3 py-2">
                      <div className="min-w-0">
                        <div className="text-sm font-medium truncate">{p.name}</div>
                        <div className="text-xs text-muted-foreground truncate">{p.id}</div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge variant="outline" className="max-w-[260px] truncate">
                          {p.valueText}
                        </Badge>
                        <Button variant="ghost" size="sm" onClick={() => removeParameterInput(p.id)} aria-label="Remove input">
                          <Trash2 className="h-4 w-4" />
                        </Button>
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
                    <Badge variant={validationResults.invalid_count > 0 ? 'destructive' : 'secondary'}>
                      Invalid: {validationResults.invalid_count}
                    </Badge>
                  </div>
                </div>
                <div className="space-y-2">
                  {(validationResults.results || []).map((r) => (
                    <div key={r.parameter_id} className="flex items-start justify-between gap-3 rounded-md bg-muted/20 px-3 py-2">
                      <div className="min-w-0">
                        <div className="text-sm font-medium truncate">{r.parameter_name || r.parameter_id}</div>
                        {r.violations?.length > 0 && (
                          <div className="text-xs text-muted-foreground mt-1">
                            {r.violations.join(' • ')}
                          </div>
                        )}
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
                    <Workflow className="h-4 w-4 text-blue-500" />
                    Agent Orchestration
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
            <Button variant="outline" onClick={() => setIsRunOpen(false)}>
              Close
            </Button>
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
