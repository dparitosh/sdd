import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Search, Database, Boxes, BookOpen, BarChart3,
  ChevronLeft, ChevronRight, Eye, X, Layers, Tag
} from 'lucide-react';
import { ap243 } from '@/services/standards.service';
import AdvancedSearch from '@/features/system-management/components/AdvancedSearch';

// AP243 domain-specific node types matching actual graph labels
const AP243_SEARCH_TYPES = [
  'Class', 'Property', 'Port', 'Connector', 'Association',
  'Generalization', 'Package', 'Constraint', 'InstanceSpecification',
  'Comment', 'XSDElement', 'XSDSchema', 'StepInstance', 'StepEntityType',
  'ExternalOwlClass'
];

const PAGE_SIZE = 20;

// ------------- Shared helpers ----------------

/** Reusable pagination controls */
function Pagination({ page, totalPages, onPageChange }) {
  if (totalPages <= 1) return null;
  return (
    <div className="flex items-center justify-between mt-4">
      <span className="text-sm text-muted-foreground">Page {page} of {totalPages}</span>
      <div className="flex gap-1">
        <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onPageChange(page - 1)}><ChevronLeft className="h-4 w-4" /></Button>
        <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}><ChevronRight className="h-4 w-4" /></Button>
      </div>
    </div>
  );
}

/** Reusable card+table section for ClassDetailView (ports, connectors, associations, etc.) */
function DetailSection({ title, items, columns }) {
  if (!items || items.length === 0) return null;
  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle className="text-base">{title} ({items.length})</CardTitle></CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>{columns.map(c => <TableHead key={c.header}>{c.header}</TableHead>)}</TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item, i) => (
              <TableRow key={i}>
                {columns.map(c => (
                  <TableCell key={c.header} className={c.className}>{c.accessor(item)}</TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function StatCard({ title, value, icon, description }) {
  return (
    <Card>
      <CardContent className="pt-4 pb-3">
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">{title}</span>
          {icon && <span className="text-muted-foreground">{icon}</span>}
        </div>
        <div className="text-2xl font-bold mt-1">{value}</div>
        {description && <p className="text-xs text-muted-foreground mt-1">{description}</p>}
      </CardContent>
    </Card>
  );
}

function ReferenceTable({ title, description, loading, items, count, columns }) {
  if (loading) return <LoadingGrid count={2} />;
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg">{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
        {count != null && <span className="text-sm text-muted-foreground">{count} items</span>}
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">No {title.toLowerCase()} found in graph.</div>
        ) : (
          <div className="max-h-[500px] overflow-y-auto">
            <Table>
              <TableHeader><TableRow>{columns.map(c => <TableHead key={c.header}>{c.header}</TableHead>)}</TableRow></TableHeader>
              <TableBody>
                {items.map((item, i) => (
                  <TableRow key={i}>
                    {columns.map(c => (
                      <TableCell key={c.header} className={c.mono ? 'font-mono text-xs' : ''}>{c.accessor(item)}</TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function LoadingGrid({ count = 4 }) {
  return (
    <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
      {Array.from({ length: count }).map((_, i) => <Skeleton key={i} className="h-24 w-full rounded-xl" />)}
    </div>
  );
}

function ErrorCard({ message }) {
  return <Card className="border-destructive"><CardContent className="py-6 text-center text-destructive">{message}</CardContent></Card>;
}

// ------------- Tab components ----------------

/** Overview Tab — graph statistics cards */
function OverviewTab() {
  const { data: overview, isLoading, error } = useQuery({
    queryKey: ['ap243-overview'],
    queryFn: async () => {
      const res = await ap243.getOverview();
      return res.data ?? res;
    },
    staleTime: 60_000,
  });

  if (isLoading) return <LoadingGrid count={6} />;
  if (error) return <ErrorCard message="Failed to load overview" />;
  if (!overview) return null;

  const stats = overview.node_types ?? overview.node_counts ?? {};
  const relStats = overview.relationship_types ?? overview.relationship_counts ?? {};
  const totalNodes = overview.total_nodes ?? Object.values(stats).reduce((a, b) => a + b, 0);
  const totalRels = overview.total_relationships ?? Object.values(relStats).reduce((a, b) => a + b, 0);
  const packages = overview.domain_packages ?? [];

  const sortedLabels = Object.entries(stats).sort(([, a], [, b]) => b - a);
  const sortedRels = Object.entries(relStats).sort(([, a], [, b]) => b - a);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="MoSSEC Nodes" value={totalNodes.toLocaleString()} icon={<Database className="h-4 w-4" />} />
        <StatCard title="MoSSEC Relationships" value={totalRels.toLocaleString()} icon={<Layers className="h-4 w-4" />} />
        <StatCard title="Node Types" value={sortedLabels.length} icon={<Tag className="h-4 w-4" />} />
        <StatCard title="Domain Packages" value={packages.length} icon={<Boxes className="h-4 w-4" />} />
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Node Types</CardTitle>
            <CardDescription>Distribution of nodes by label</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-[400px] overflow-y-auto">
              {sortedLabels.map(([label, count]) => {
                const pct = totalNodes > 0 ? ((count / totalNodes) * 100).toFixed(1) : 0;
                return (
                  <div key={label} className="flex items-center justify-between text-sm">
                    <Badge variant="outline" className="shrink-0">{label}</Badge>
                    <div className="flex items-center gap-2">
                      <div className="w-24 bg-muted rounded-full h-2 overflow-hidden">
                        <div className="bg-primary h-full rounded-full" style={{ width: `${Math.max(pct, 1)}%` }} />
                      </div>
                      <span className="w-16 text-right font-mono text-xs tabular-nums">{count.toLocaleString()}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Relationship Types</CardTitle>
            <CardDescription>Distribution of edges by type</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-[400px] overflow-y-auto">
              {sortedRels.map(([rel, count]) => {
                const pct = totalRels > 0 ? ((count / totalRels) * 100).toFixed(1) : 0;
                return (
                  <div key={rel} className="flex items-center justify-between text-sm">
                    <Badge variant="secondary" className="shrink-0 font-mono text-xs">{rel}</Badge>
                    <div className="flex items-center gap-2">
                      <div className="w-24 bg-muted rounded-full h-2 overflow-hidden">
                        <div className="bg-blue-500 h-full rounded-full" style={{ width: `${Math.max(pct, 1)}%` }} />
                      </div>
                      <span className="w-16 text-right font-mono text-xs tabular-nums">{count.toLocaleString()}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

/** Domain Classes Browser Tab */
function DomainClassesTab() {
  const [search, setSearch] = useState('');
  const [stereotype, setStereotype] = useState('');
  const [pkg, setPkg] = useState('');
  const [abstractFilter, setAbstractFilter] = useState('');
  const [page, setPage] = useState(1);
  const [selectedClass, setSelectedClass] = useState(null);

  const { data: stereotypesData } = useQuery({
    queryKey: ['ap243-stereotypes'],
    queryFn: async () => { const res = await ap243.getStereotypes(); return res.data ?? res; },
    staleTime: 120_000,
  });

  const { data: packagesData } = useQuery({
    queryKey: ['ap243-packages'],
    queryFn: async () => { const res = await ap243.getPackages(); return res.data ?? res; },
    staleTime: 120_000,
  });

  const queryParams = useMemo(() => {
    const p = { skip: (page - 1) * PAGE_SIZE, limit: PAGE_SIZE };
    if (search) p.search = search;
    if (stereotype) p.stereotype = stereotype;
    if (pkg) p.package = pkg;
    if (abstractFilter === 'true') p.is_abstract = true;
    if (abstractFilter === 'false') p.is_abstract = false;
    return p;
  }, [search, stereotype, pkg, abstractFilter, page]);

  const { data: classesData, isLoading } = useQuery({
    queryKey: ['ap243-domain-classes', queryParams],
    queryFn: async () => { const res = await ap243.getDomainClasses(queryParams); return res.data ?? res; },
    staleTime: 30_000,
    keepPreviousData: true,
  });

  const { data: classDetail, isLoading: loadingDetail } = useQuery({
    queryKey: ['ap243-domain-class-detail', selectedClass],
    queryFn: async () => { const res = await ap243.getDomainClassDetail(selectedClass); return res.data ?? res; },
    enabled: !!selectedClass,
    staleTime: 60_000,
  });

  const classes = classesData?.classes ?? [];
  const totalCount = classesData?.count ?? 0;
  const totalPages = Math.ceil(totalCount / PAGE_SIZE);
  const stereotypes = stereotypesData?.stereotypes ?? [];
  const packages = packagesData?.packages ?? [];

  const clearFilters = () => { setSearch(''); setStereotype(''); setPkg(''); setAbstractFilter(''); setPage(1); };
  const hasFilters = search || stereotype || pkg || abstractFilter;

  if (selectedClass) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="sm" onClick={() => setSelectedClass(null)}>
          <ChevronLeft className="h-4 w-4 mr-1" /> Back to Classes
        </Button>
        {loadingDetail ? <LoadingGrid count={3} /> : classDetail ? <ClassDetailView detail={classDetail} /> : <ErrorCard message="Class not found" />}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-3 items-end">
            <div className="flex-1 min-w-[200px]">
              <Label className="text-xs">Search by name</Label>
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input placeholder="Search classes..." value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} className="pl-9" />
              </div>
            </div>
            <div className="w-[160px]">
              <Label className="text-xs">Stereotype</Label>
              <Select value={stereotype} onValueChange={v => { setStereotype(v === '__all__' ? '' : v); setPage(1); }}>
                <SelectTrigger><SelectValue placeholder="All" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">All</SelectItem>
                  {stereotypes.map((s, i) => {
                    const name = typeof s === 'string' ? s : s.name;
                    return <SelectItem key={name ?? i} value={name}>{name}{s.count != null && ` (${s.count})`}</SelectItem>;
                  })}
                </SelectContent>
              </Select>
            </div>
            <div className="w-[180px]">
              <Label className="text-xs">Package</Label>
              <Select value={pkg} onValueChange={v => { setPkg(v === '__all__' ? '' : v); setPage(1); }}>
                <SelectTrigger><SelectValue placeholder="All" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">All</SelectItem>
                  {packages.map((p, i) => {
                    const name = typeof p === 'string' ? p : p.name;
                    const id = p.id ?? name;
                    return (
                      <SelectItem key={`${name}-${id}-${i}`} value={name}>
                        {name} {p.class_count != null && `(${p.class_count})`}
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
            </div>
            <div className="w-[120px]">
              <Label className="text-xs">Abstract</Label>
              <Select value={abstractFilter} onValueChange={v => { setAbstractFilter(v === '__all__' ? '' : v); setPage(1); }}>
                <SelectTrigger><SelectValue placeholder="All" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">All</SelectItem>
                  <SelectItem value="true">Abstract</SelectItem>
                  <SelectItem value="false">Concrete</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {hasFilters && (
              <Button variant="ghost" size="icon" onClick={clearFilters} title="Clear filters">
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">
            Domain Classes
            {totalCount > 0 && <span className="text-sm font-normal text-muted-foreground ml-2">({totalCount} total)</span>}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? <LoadingGrid count={3} /> : classes.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">No classes found matching current filters.</div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Stereotype</TableHead>
                    <TableHead>Package</TableHead>
                    <TableHead className="w-[80px]">Abstract</TableHead>
                    <TableHead className="w-[100px]">Visibility</TableHead>
                    <TableHead className="w-[60px]" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {classes.map((cls, i) => (
                    <TableRow key={cls.xmi_id ?? cls.name ?? i} className="cursor-pointer hover:bg-muted/50" onClick={() => setSelectedClass(cls.name)}>
                      <TableCell className="font-medium">{cls.name}</TableCell>
                      <TableCell>{cls.stereotype ? <Badge variant="secondary">{cls.stereotype}</Badge> : <span className="text-muted-foreground text-xs">—</span>}</TableCell>
                      <TableCell className="text-sm">{cls.package || cls.source_file || '—'}</TableCell>
                      <TableCell>{cls.is_abstract ? <Badge variant="outline">Yes</Badge> : <span className="text-muted-foreground text-xs">No</span>}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">{cls.visibility || 'public'}</TableCell>
                      <TableCell><Eye className="h-4 w-4 text-muted-foreground" /></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

/** Class detail view — properties, ports, generalizations, connectors */
function ClassDetailView({ detail }) {
  if (!detail) return null;
  const cls = detail;
  const properties = cls.properties ?? [];
  const ports = cls.ports ?? [];
  const generalizations = cls.generalizations ?? [];
  const connectors = cls.connectors ?? [];
  const associations = cls.associations ?? [];

  const nameTypeColumns = [
    { header: 'Name', accessor: r => r.name ?? '—', className: 'font-medium' },
    { header: 'Type', accessor: r => r.xmi_type ?? '—', className: 'text-xs font-mono' },
  ];

  const hasAny = properties.length + ports.length + generalizations.length + connectors.length + associations.length > 0;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <CardTitle>{cls.name}</CardTitle>
            {cls.stereotype && <Badge>{cls.stereotype}</Badge>}
            {cls.is_abstract && <Badge variant="outline">Abstract</Badge>}
          </div>
          <CardDescription>
            {cls.xmi_type && <span className="mr-4">Type: {cls.xmi_type}</span>}
            {cls.visibility && <span className="mr-4">Visibility: {cls.visibility}</span>}
            {cls.source_file && <span>Source: {cls.source_file}</span>}
          </CardDescription>
        </CardHeader>
      </Card>

      <DetailSection title="Properties" items={properties} columns={[
        { header: 'Name', accessor: p => p.name ?? '—', className: 'font-medium' },
        { header: 'Type', accessor: p => p.xmi_type ?? p.type ?? '—', className: 'text-xs font-mono' },
        { header: 'Visibility', accessor: p => p.visibility ?? 'public', className: 'text-xs' },
      ]} />

      <DetailSection title="Ports" items={ports} columns={nameTypeColumns} />
      <DetailSection title="Connectors" items={connectors} columns={nameTypeColumns} />
      <DetailSection title="Associations" items={associations} columns={nameTypeColumns} />

      {generalizations.length > 0 && (
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">Generalizations ({generalizations.length})</CardTitle></CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {generalizations.map((g, i) => (
                <Badge key={i} variant="outline">{g.name ?? g.target ?? `Generalization ${i + 1}`}</Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {!hasAny && (
        <Card><CardContent className="py-8 text-center text-muted-foreground">No relationships found for this class.</CardContent></Card>
      )}
    </div>
  );
}

/** Reference Data Tab — ontologies, units, classifications, value types */
function ReferenceDataTab() {
  const [subTab, setSubTab] = useState('ontologies');

  const { data: ontologiesData, isLoading: loadingOnt } = useQuery({
    queryKey: ['ap243-ontologies'],
    queryFn: async () => { const res = await ap243.getOntologies(); return res.data ?? res; },
    staleTime: 120_000,
    enabled: subTab === 'ontologies',
  });

  const { data: unitsData, isLoading: loadingUnits } = useQuery({
    queryKey: ['ap243-units'],
    queryFn: async () => { const res = await ap243.getUnits(); return res.data ?? res; },
    staleTime: 120_000,
    enabled: subTab === 'units',
  });

  const { data: classificationsData, isLoading: loadingClass } = useQuery({
    queryKey: ['ap243-classifications'],
    queryFn: async () => { const res = await ap243.getClassifications(); return res.data ?? res; },
    staleTime: 120_000,
    enabled: subTab === 'classifications',
  });

  const { data: valueTypesData, isLoading: loadingVT } = useQuery({
    queryKey: ['ap243-value-types'],
    queryFn: async () => { const res = await ap243.getValueTypes(); return res.data ?? res; },
    staleTime: 120_000,
    enabled: subTab === 'value-types',
  });

  return (
    <div className="space-y-4">
      <div className="flex gap-2 flex-wrap">
        {['ontologies', 'units', 'classifications', 'value-types'].map(tab => (
          <Button key={tab} variant={subTab === tab ? 'default' : 'outline'} size="sm" onClick={() => setSubTab(tab)}>
            {tab.replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase())}
          </Button>
        ))}
      </div>

      {subTab === 'ontologies' && (
        <ReferenceTable title="OWL Ontologies" description="AP243 reference ontologies (ISO 10303-243)" loading={loadingOnt}
          items={ontologiesData?.ontologies ?? []} count={ontologiesData?.count}
          columns={[
            { header: 'Name', accessor: r => r.name ?? r.label ?? '—' },
            { header: 'URI', accessor: r => r.uri ?? r.iri ?? '—', mono: true },
            { header: 'Type', accessor: r => r.type ?? '—' },
          ]}
        />
      )}
      {subTab === 'units' && (
        <ReferenceTable title="Units of Measure" description="AP243 unit definitions" loading={loadingUnits}
          items={unitsData?.units ?? []} count={unitsData?.count}
          columns={[
            { header: 'Name', accessor: r => r.name ?? '—' },
            { header: 'Symbol', accessor: r => r.symbol ?? '—' },
            { header: 'System', accessor: r => r.system ?? '—' },
          ]}
        />
      )}
      {subTab === 'classifications' && (
        <ReferenceTable title="Classifications" description="Classification codes and categorization" loading={loadingClass}
          items={classificationsData?.classifications ?? []} count={classificationsData?.count}
          columns={[
            { header: 'Name', accessor: r => r.name ?? '—' },
            { header: 'System', accessor: r => r.system ?? '—' },
            { header: 'Code', accessor: r => r.code ?? r.id ?? '—', mono: true },
          ]}
        />
      )}
      {subTab === 'value-types' && (
        <ReferenceTable title="Value Types" description="Typed value definitions" loading={loadingVT}
          items={valueTypesData?.value_types ?? []} count={valueTypesData?.count}
          columns={[
            { header: 'Name', accessor: r => r.name ?? '—' },
            { header: 'Base Type', accessor: r => r.base_type ?? r.type ?? '—' },
          ]}
        />
      )}
    </div>
  );
}

// -------------- Main Dashboard ----------------

export default function MossecDashboard() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex flex-col space-y-2">
        <h1 className="text-3xl font-bold">AP243 MoSSEC Dashboard</h1>
        <p className="text-muted-foreground">
          ISO 10303-243 &mdash; Modeling and Simulation information in a Collaborative Systems Engineering Context
        </p>
      </div>

      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview" className="gap-1"><BarChart3 className="h-4 w-4" /> Overview</TabsTrigger>
          <TabsTrigger value="classes" className="gap-1"><Boxes className="h-4 w-4" /> Domain Classes</TabsTrigger>
          <TabsTrigger value="reference" className="gap-1"><BookOpen className="h-4 w-4" /> Reference Data</TabsTrigger>
          <TabsTrigger value="search" className="gap-1"><Search className="h-4 w-4" /> Search</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4"><OverviewTab /></TabsContent>
        <TabsContent value="classes" className="mt-4"><DomainClassesTab /></TabsContent>
        <TabsContent value="reference" className="mt-4"><ReferenceDataTab /></TabsContent>
        <TabsContent value="search" className="mt-4">
          <AdvancedSearch title="AP243 Search" allowedTypes={AP243_SEARCH_TYPES} defaultType="All" enableHeader={false} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
