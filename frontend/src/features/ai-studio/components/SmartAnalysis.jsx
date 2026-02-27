import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@ui/card';
import { Badge } from '@ui/badge';
import { Button } from '@ui/button';
import { Brain, Network, Activity, Play } from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import { toast } from 'sonner';

export default function SmartAnalysis() {
  const handleRunAnalysis = () => {
    toast.success('Starting Analysis', {
      description: 'Running AI-powered analysis on your knowledge graph...'
    });
  };
  const handleStartImpactAnalysis = () => {
    toast.info('Impact Analysis', {
      description: 'Identifying affected components and requirements...'
    });
  };
  const handleAnalyzePropagation = () => {
    toast.info('Change Propagation', {
      description: 'Tracing change ripple effects through the system...'
    });
  };
  const handleViewResults = analysisName => {
    toast.info(`${analysisName} Results`, {
      description: 'Loading analysis results and recommendations...'
    });
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <PageHeader
        title="Smart Analysis"
        description="Automated impact analysis and change propagation"
        icon={<Brain className="h-8 w-8 text-primary" />}
        badge="AI-Powered"
        breadcrumbs={[
          { label: 'GenAI Studio', href: '/ai/insights' },
          { label: 'Smart Analysis' }
        ]}
        actions={
          <Button onClick={handleRunAnalysis}>
            <Play className="h-4 w-4 mr-2" />
            Run Analysis
          </Button>
        }
      />

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
              simulations affected by proposed changes.
            </p>
            <Button
              variant="outline"
              className="w-full"
              onClick={handleStartImpactAnalysis}
            >
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
              and identify required updates.
            </p>
            <Button
              variant="outline"
              className="w-full"
              onClick={handleAnalyzePropagation}
            >
              Analyze Propagation
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Analyses</CardTitle>
          <CardDescription>
            Previously run impact and change analyses
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div>
                <p className="font-medium">Propulsion System Update</p>
                <p className="text-sm text-muted-foreground">Analyzed 2 hours ago</p>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline">45 impacts found</Badge>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleViewResults('Propulsion System Update')}
                >
                  View Results
                </Button>
              </div>
            </div>

            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div>
                <p className="font-medium">Thermal Analysis Changes</p>
                <p className="text-sm text-muted-foreground">Analyzed yesterday</p>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline">12 impacts found</Badge>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleViewResults('Thermal Analysis Changes')}
                >
                  View Results
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
