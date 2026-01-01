import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@ui/card';
import { Badge } from '@ui/badge';
import { Button } from '@ui/button';
import { Workflow, Play, Plus, GitBranch, CheckCircle2 } from 'lucide-react';
import PageHeader from '@/components/PageHeader';

export default function WorkflowStudio() {
  const workflows = [
    {
      name: 'Standard Thermal Analysis',
      steps: 5,
      status: 'active',
      lastRun: '2 hours ago',
      runs: 45,
    },
    {
      name: 'Multi-Physics Simulation',
      steps: 8,
      status: 'draft',
      lastRun: 'Never',
      runs: 0,
    },
    {
      name: 'Structural Validation Suite',
      steps: 6,
      status: 'active',
      lastRun: '1 day ago',
      runs: 23,
    },
  ];

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
          <Button>
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
                  <Button variant="outline" size="sm">
                    <GitBranch className="h-4 w-4 mr-2" />
                    Edit
                  </Button>
                  <Button size="sm">
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
                    <div className="flex items-center justify-center h-10 w-10 rounded-full bg-primary/10 text-primary font-medium text-sm flex-shrink-0">
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

      <Card className="bg-gradient-to-br from-primary/5 to-primary/10">
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
    </div>
  );
}
