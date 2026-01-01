import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@ui/card';
import { Badge } from '@ui/badge';
import { Button } from '@ui/button';
import { Lightbulb, TrendingUp, AlertCircle, Sparkles } from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import { toast } from 'sonner';
export default function AIInsights() {
  const handleGenerateInsights = () => {
    toast.success('Generating AI Insights', {
      description: 'Analyzing knowledge graph for new recommendations...'
    });
  };
  const handleViewDetails = type => {
    toast.info(`Opening ${type} Details`, {
      description: 'Loading detailed analysis and recommendations...'
    });
  };
  return <div className="container mx-auto p-6 space-y-6"><PageHeader title="AI Insights" description="Intelligent recommendations and insights from your knowledge graph" icon={<Lightbulb className="h-8 w-8 text-primary" />} badge="AI-Powered" breadcrumbs={[{
      label: 'GenAI Studio',
      href: '/ai/insights'
    }, {
      label: 'AI Insights'
    }]} actions={<Button onClick={handleGenerateInsights}><Sparkles className="h-4 w-4 mr-2" />Generate Insights</Button>} /><div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"><Card className="border-l-4 border-l-blue-500"><CardHeader><CardTitle className="flex items-center gap-2"><TrendingUp className="h-5 w-5 text-blue-500" />Requirements Impact</CardTitle><CardDescription>High Priority</CardDescription></CardHeader><CardContent><p className="text-sm">23 requirements may be affected by recent design changes in the propulsion system.</p><Button variant="link" className="mt-2 p-0" onClick={() => handleViewDetails('Requirements Impact')}>View Details →</Button></CardContent></Card><Card className="border-l-4 border-l-amber-500"><CardHeader><CardTitle className="flex items-center gap-2"><AlertCircle className="h-5 w-5 text-amber-500" />Missing Traceability</CardTitle><CardDescription>Attention Needed</CardDescription></CardHeader><CardContent><p className="text-sm">15 components lack traceability links to requirements. AI suggests likely connections.</p><Button variant="link" className="mt-2 p-0" onClick={() => handleViewDetails('Traceability Suggestions')}>Review Suggestions →</Button></CardContent></Card><Card className="border-l-4 border-l-green-500"><CardHeader><CardTitle className="flex items-center gap-2"><Sparkles className="h-5 w-5 text-green-500" />Optimization Opportunity</CardTitle><CardDescription>Recommended</CardDescription></CardHeader><CardContent><p className="text-sm">Similar patterns detected in 3 simulation models. Consider creating reusable template.</p><Button variant="link" className="mt-2 p-0" onClick={() => handleViewDetails('Optimization Patterns')}>Explore →</Button></CardContent></Card></div><Card className="bg-gradient-to-br from-primary/5 to-primary/10"><CardHeader><CardTitle>More AI Features Coming Soon</CardTitle><CardDescription>We're continuously adding new AI capabilities</CardDescription></CardHeader><CardContent className="space-y-2"><div className="flex items-center gap-2"><Badge variant="outline">Coming Soon</Badge><span className="text-sm">Automated risk assessment</span></div><div className="flex items-center gap-2"><Badge variant="outline">Coming Soon</Badge><span className="text-sm">Predictive maintenance suggestions</span></div><div className="flex items-center gap-2"><Badge variant="outline">Coming Soon</Badge><span className="text-sm">Smart documentation generation</span></div></CardContent></Card></div>;
}
