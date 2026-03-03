import logger from '@/utils/logger';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Download, RefreshCw, Search, CheckCircle2, AlertCircle, XCircle, GitBranch, PanelRightOpen, PanelRightClose } from 'lucide-react';
import { requirements as requirementsApi, ap239 } from '@/services/standards.service';
import { toast } from 'sonner';
import PageHeader from '@/components/PageHeader';
import MossecInspector from '@/features/sdd/components/MossecInspector';

const TRACE_STATUS_COLORS = {
  satisfied: 'bg-green-100 text-green-800 hover:bg-green-200',
  partial: 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200',
  missing: 'bg-red-100 text-red-800 hover:bg-red-200',
  unknown: 'bg-gray-100 text-gray-800 hover:bg-gray-200'
};
const TRACE_STATUS_ICONS = {
  satisfied: CheckCircle2,
  partial: AlertCircle,
  missing: XCircle,
  unknown: AlertCircle
};
export default function TraceabilityMatrix() {
  const [filter, setFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [inspectorLinks, setInspectorLinks] = useState([]);
  const [dossierFilter, setDossierFilter] = useState('');
  const {
    data: requirements = [],
    isLoading: reqLoading
  } = useQuery({
    queryKey: ['requirements-traceability'],
    queryFn: async () => {
      const response = await requirementsApi.list({
        limit: 1000
      });
      // Backend /api/v1/Requirement returns {resources: [...], count: N}
      return Array.isArray(response) ? response : (response.resources || response.data || []);
    }
  });
  const {
    data: traceabilityData = [],
    isLoading: traceLoading,
    refetch
  } = useQuery({
    queryKey: ['traceability-all', requirements.map(r => r.uid).join(',')],
    queryFn: async () => {
      const reqSlice = requirements.slice(0, 200);
      const uids = reqSlice.map(r => r.uid).filter(Boolean);
      if (uids.length === 0) return [];

      // Use bulk endpoint if available, fall back to parallel batch
      const traces = [];
      try {
        if (ap239?.getBulkRequirementTraceability) {
          const bulkResponse = await ap239.getBulkRequirementTraceability(uids);
          const bulkData = Array.isArray(bulkResponse) ? bulkResponse : (bulkResponse.results || bulkResponse.data || []);
          const reqByUid = Object.fromEntries(reqSlice.map(r => [r.uid, r]));
          bulkData.forEach(item => {
            const req = reqByUid[item.requirement_id || item.requirement_uid || item.uid];
            const links = Array.isArray(item.traceability) ? item.traceability : (Array.isArray(item.links) ? item.links : (item.traces || []));
            links.forEach(link => {
              traces.push({
                requirement: {
                  uid: req?.uid || item.requirement_id || item.requirement_uid,
                  name: req?.name || item.requirement_name || item.name,
                  status: req?.status || 'Unknown'
                },
                target: {
                  uid: link.target?.uid || link.uid || link.part_id || link.ontology_id || link.sa_id || 'unknown',
                  name: link.target?.name || link.name || link.part_name || link.ontology_name || link.sa_name || (link.ontologies && link.ontologies[0]) || 'Unknown',
                  type: link.target?.type || link.type || (link.part_id ? 'Part' : (link.ontology_id ? link.ontology_type : (link.sa_id ? 'SimulationArtifact' : 'Unknown')))
                },
                relationship: link.relationship || (link.part_id ? 'SATISFIED_BY_PART' : (link.ontology_id ? 'MAPS_TO_OSLC' : (link.sa_id ? 'VERIFIED_BY' : 'traces'))),
                satisfied: link.satisfied !== false
              });
            });
          });
        } else {
          // Fallback: parallel batch (up to 10 concurrent)
          const batchSize = 10;
          for (let i = 0; i < reqSlice.length; i += batchSize) {
            const batch = reqSlice.slice(i, i + batchSize);
            const results = await Promise.allSettled(
              batch.map(req => requirementsApi.getTraceability(req.uid))
            );
            results.forEach((result, idx) => {
              if (result.status !== 'fulfilled') return;
              const links = Array.isArray(result.value) ? result.value : (result.value?.data || []);
              const req = batch[idx];
              links.forEach(link => {
                traces.push({
                  requirement: {
                    uid: req.uid,
                    name: req.name,
                    status: req.status
                  },
                  target: {
                    uid: link.target?.uid || link.uid,
                    name: link.target?.name || link.name,
                    type: link.target?.type || link.type || 'Unknown'
                  },
                  relationship: link.relationship || 'traces',
                  satisfied: link.satisfied !== false
                });
              });
            });
          }
        }
      } catch (error) {
        logger.error('Failed to fetch traceability data:', error);
        toast.error('Some traceability data could not be loaded');
      }
      // Deduplicate: same requirement → target → relationship should only appear once
      const seen = new Set();
      return traces.filter(t => {
        const key = `${t.requirement.uid}|${t.target.uid}|${t.relationship}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });
    },
    enabled: requirements.length > 0
  });
  const isLoading = reqLoading || traceLoading;
  // Filter requirements with no traceability for display
  const requirementsWithNoTrace = requirements.filter(r =>
    !traceabilityData.some(t => t.requirement.uid === r.uid || t.requirement.uid === r.id)
  );

  const filteredData = traceabilityData.filter(link => {
    const matchesFilter = filter === '' || (link.requirement.name || '').toLowerCase().includes(filter.toLowerCase()) || (link.target.name || '').toLowerCase().includes(filter.toLowerCase());
    const matchesStatus = statusFilter === 'all' || statusFilter === 'satisfied' && link.satisfied || statusFilter === 'missing' && !link.satisfied;
    // Also apply dossier filter if set
    const matchesDossier = dossierFilter === '' || (link.target.name || '').toLowerCase().includes(dossierFilter.toLowerCase());
    return matchesFilter && matchesStatus && matchesDossier;
  });
  const groupedData = filteredData.reduce((acc, link) => {
    if (!acc[link.requirement.uid]) {
      acc[link.requirement.uid] = {
        requirement: link.requirement,
        targets: []
      };
    }
    acc[link.requirement.uid].targets.push(link);
    return acc;
  }, {});
  const totalRequirements = requirements.length;       // All loaded requirements
  const tracedRequirements = Object.keys(groupedData).length; // Requirements with links
  const totalLinks = filteredData.length;
  const satisfiedLinks = filteredData.filter(l => l.satisfied).length;
  const missingLinks = filteredData.filter(l => !l.satisfied).length;
  const coverage = totalRequirements > 0 ? (tracedRequirements / totalRequirements * 100).toFixed(1) : '0';
  const exportToCSV = () => {
    const headers = ['Requirement UID', 'Requirement Name', 'Target Type', 'Target UID', 'Target Name', 'Relationship', 'Status'];
    const rows = filteredData.map(link => [link.requirement.uid, link.requirement.name, link.target.type, link.target.uid, link.target.name, link.relationship, link.satisfied ? 'Satisfied' : 'Missing']);
    const csv = [headers, ...rows].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');
    const blob = new Blob([csv], {
      type: 'text/csv'
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `traceability_matrix_${new Date().toISOString()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Traceability matrix exported to CSV');
  };

  return (
    <div className="flex gap-6">
      {/* Main content area */}
      <div className={`flex-1 min-w-0 space-y-6 ${inspectorOpen ? '' : ''}`}>
        <PageHeader
          title="Traceability Matrix"
          description="Visualize and analyze requirement traceability relationships"
          icon={<GitBranch className="h-6 w-6 text-primary" />}
          breadcrumbs={[
            { label: 'Knowledge Graph', href: '/engineer/graph' },
          ]}
          actions={
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setInspectorOpen(!inspectorOpen)}>
                {inspectorOpen ? <PanelRightClose className="h-4 w-4 mr-2" /> : <PanelRightOpen className="h-4 w-4 mr-2" />}
                Inspector
              </Button>
              <Button variant="outline" onClick={() => refetch()}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
              <Button
                variant="outline"
                onClick={exportToCSV}
                disabled={filteredData.length === 0}
              >
                <Download className="h-4 w-4 mr-2" />
                Export CSV
              </Button>
            </div>
          }
        />

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Requirements
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalRequirements}</div>
            <div className="text-xs text-muted-foreground mt-1">{tracedRequirements} traced</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Links
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalLinks}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Satisfied Links
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{satisfiedLinks}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Coverage
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{coverage}%</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="search">Search</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="search"
                  placeholder="Search requirements or targets..."
                  value={filter}
                  onChange={e => setFilter(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <div>
              <Label htmlFor="status-filter">Status Filter</Label>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger id="status-filter">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="satisfied">Satisfied Only</SelectItem>
                  <SelectItem value="missing">Missing Only</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Traceability Links</CardTitle>
          <CardDescription>
            Showing {filteredData.length} traceability links
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-24 w-full" />
              ))}
            </div>
          ) : Object.keys(groupedData).length === 0 ? (
            <Alert>
              <AlertDescription>
                {requirements.length === 0
                  ? 'Loading requirements from the database…'
                  : `${requirements.length} requirement${requirements.length !== 1 ? 's' : ''} loaded but no traceability links match the current filter. Try clearing filters or check that requirements have LINKED_TO_REQUIREMENT / SATISFIED_BY_PART / MAPS_TO_OSLC relationships in Neo4j.`
                }
              </AlertDescription>
            </Alert>
          ) : (
            <div className="space-y-4 max-h-150 overflow-auto">
              {Object.values(groupedData).map(({ requirement, targets }) => (
                <div
                  key={requirement.uid}
                  className="border rounded-lg p-4 hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="font-semibold text-sm">{requirement.name}</div>
                      <div className="text-xs text-muted-foreground font-mono mt-1">
                        {requirement.uid}
                      </div>
                    </div>
                    {requirement.status && (
                      <Badge variant="outline">{requirement.status}</Badge>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                    {targets.map(link => {
                      const status = link.satisfied ? 'satisfied' : 'missing';
                      const StatusIcon = TRACE_STATUS_ICONS[status];
                      return (
                        <div
                          key={`${link.target.uid}-${link.relationship}`}
                          className={`flex items-center gap-2 p-2 rounded-md text-xs cursor-pointer ${TRACE_STATUS_COLORS[status]}`}
                          onClick={() => {
                            setInspectorLinks([{
                              id: `${link.requirement?.uid}-${link.target.uid}`,
                              source: link.requirement?.name || link.requirement?.uid,
                              target: link.target.name,
                              relationType: link.relationship,
                              sourceType: 'Requirement',
                              targetType: link.target.type,
                            }]);
                            setInspectorOpen(true);
                          }}
                        >
                          <StatusIcon className="h-3 w-3 shrink-0" />
                          <div className="flex-1 min-w-0">
                            <div className="font-medium truncate">{link.target.name}</div>
                            <div className="text-xs opacity-75">
                              {link.target.type} · {link.relationship}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
      </div>

      {/* Right-side MossecInspector panel */}
      {inspectorOpen && (
        <div className="w-96 shrink-0">
          <MossecInspector
            links={inspectorLinks}
            open={true}
            onClose={() => setInspectorOpen(false)}
            onNavigate={() => {}}
            embedded
          />
        </div>
      )}
    </div>
  );
}
