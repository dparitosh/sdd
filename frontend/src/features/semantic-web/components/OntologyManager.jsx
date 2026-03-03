import { useState, useRef, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@ui/card';
import { Button } from '@ui/button';
import { Badge } from '@ui/badge';
import { ScrollArea } from '@ui/scroll-area';
import { Skeleton } from '@ui/skeleton';
import { Alert, AlertDescription } from '@ui/alert';
import { Separator } from '@ui/separator';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@ui/select';
import PageHeader from '@/components/PageHeader';
import { Upload, ChevronRight, ChevronDown, FileCode2, Layers, Loader2, Database, AlertTriangle } from 'lucide-react';
import { useOntology } from '../hooks/useOntology';
import { ingestStandardOntologies, getClassificationStats } from '@/services/ontology.service';

function ClassTree({ classes, onSelect, selectedId, depth = 0 }) {
  const [expanded, setExpanded] = useState({});

  if (!classes || classes.length === 0) return null;
  return (
    <ul className={depth > 0 ? 'ml-4 border-l border-muted pl-2' : ''}>
      {classes.map((cls, idx) => {
        const nodeId = cls.uri ?? cls.id ?? `class-${depth}-${idx}`;
        const hasChildren = cls.children && cls.children.length > 0;
        const isExpanded = expanded[nodeId];
        const isSelected = selectedId === nodeId;
        return (
          <li key={nodeId}>
            <button
              type="button"
              className={`flex items-center gap-1 text-sm py-1 px-1 w-full text-left rounded hover:bg-muted/50 ${isSelected ? 'bg-primary/10 font-medium' : ''}`}
              onClick={() => {
                onSelect({ ...cls, id: nodeId, name: cls.label ?? cls.name ?? nodeId });
                if (hasChildren) setExpanded((p) => ({ ...p, [nodeId]: !p[nodeId] }));
              }}
            >
              {hasChildren ? (
                isExpanded ? <ChevronDown className="h-3.5 w-3.5 shrink-0" /> : <ChevronRight className="h-3.5 w-3.5 shrink-0" />
              ) : (
                <span className="w-3.5" />
              )}
              <span className="truncate">{cls.label ?? cls.name ?? nodeId}</span>
            </button>
            {hasChildren && isExpanded && (
              <ClassTree classes={cls.children} onSelect={onSelect} selectedId={selectedId} depth={depth + 1} />
            )}
          </li>
        );
      })}
    </ul>
  );
}

export default function OntologyManager() {
  const fileRef = useRef(null);
  const [selectedClass, setSelectedClass] = useState(null);
  const [apFilter, setApFilter] = useState('all');
  const { ontologies, classHierarchy, ingest, isIngesting, ingestResult, isLoading, error, refetch } = useOntology();

  // Standard ontology ingestion
  const [standardLoading, setStandardLoading] = useState(false);
  const [standardResult, setStandardResult] = useState(null);
  const [standardError, setStandardError] = useState(null);

  // Classification stats
  const [classStats, setClassStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(false);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    setStatsLoading(true);
    try {
      const resp = await getClassificationStats();
      setClassStats(resp.data ?? resp);
    } catch { /* ignore */ }
    finally { setStatsLoading(false); }
  };

  const handleUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) ingest(file);
  };

  const handleIngestStandard = async () => {
    setStandardLoading(true);
    setStandardError(null);
    try {
      const resp = await ingestStandardOntologies();
      setStandardResult(resp.data ?? resp);
      refetch();
      fetchStats();
    } catch (err) {
      setStandardError(err.message ?? String(err));
    } finally {
      setStandardLoading(false);
    }
  };

  // Filter ontologies by AP level
  const filteredOntologies = apFilter === 'all'
    ? (ontologies ?? [])
    : (ontologies ?? []).filter((o) => {
        const name = (o.name ?? o.uri ?? '').toLowerCase();
        return name.includes(apFilter.toLowerCase());
      });

  const totalClassified = (classStats ?? []).reduce((s, r) => s + (r.classified ?? 0), 0);
  const totalUnclassified = (classStats ?? []).reduce((s, r) => s + (r.unclassified ?? 0), 0);

  return (
    <div className="container mx-auto p-6 space-y-6">
      <PageHeader
        title="Ontology Manager"
        description="Upload OWL/RDF ontologies and browse class hierarchies"
        icon={<Layers className="h-6 w-6 text-primary" />}
      />

      {/* Upload + Standard Ingest */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Ingest Ontology</CardTitle>
            <CardDescription>Upload an OWL or RDF file to ingest into the knowledge graph</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-4">
              <input ref={fileRef} type="file" accept=".owl,.rdf,.ttl,.xml,.jsonld" className="hidden" onChange={handleUpload} />
              <Button onClick={() => fileRef.current?.click()} disabled={isIngesting}>
                <Upload className="h-4 w-4 mr-2" />
                {isIngesting ? 'Ingesting…' : 'Upload OWL/RDF File'}
              </Button>
              {ingestResult && (
                <Badge variant="outline" className="text-green-600">
                  Ingested {ingestResult.triples ?? 0} triples
                </Badge>
              )}
            </div>
            <Separator />
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">Or ingest the three standard MoSSEC ontologies (AP243, STEP-Core, PLCS-4439):</p>
              <Button variant="secondary" onClick={handleIngestStandard} disabled={standardLoading}>
                {standardLoading ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Ingesting…</> : <><Database className="h-4 w-4 mr-2" /> Ingest Standard Ontologies</>}
              </Button>
              {standardError && (
                <Alert variant="destructive"><AlertDescription>{standardError}</AlertDescription></Alert>
              )}
              {standardResult && (
                <div className="space-y-1">
                  {(standardResult.results ?? []).map((r, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm">
                      {r.error ? (
                        <Badge variant="destructive" className="text-xs">Error</Badge>
                      ) : (
                        <Badge className="bg-green-500 text-white text-xs">OK</Badge>
                      )}
                      <span>{r.name}</span>
                      {r.triples != null && <span className="text-muted-foreground">({r.triples} triples)</span>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Classification Stats */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Classification Coverage</CardTitle>
            <CardDescription>Nodes with CLASSIFIED_AS edges vs unclassified, by label</CardDescription>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <div className="space-y-2">{[...Array(5)].map((_, i) => <Skeleton key={i} className="h-5 w-full" />)}</div>
            ) : !classStats || classStats.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">No classification data</p>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm font-medium">
                  <span>Total Classified: {totalClassified}</span>
                  {totalUnclassified > 0 && (
                    <a href="/graph-explorer?view=unclassified" className="text-amber-600 hover:underline flex items-center gap-1">
                      <AlertTriangle className="h-3.5 w-3.5" /> {totalUnclassified} unclassified
                    </a>
                  )}
                </div>
                <Separator />
                <ul className="space-y-2">
                  {classStats.map((row, i) => {
                    const total = (row.classified ?? 0) + (row.unclassified ?? 0);
                    const pct = total > 0 ? Math.round(((row.classified ?? 0) / total) * 100) : 0;
                    return (
                      <li key={i} className="space-y-1">
                        <div className="flex items-center justify-between text-sm">
                          <span className="font-medium">{row.label}</span>
                          <span className="text-muted-foreground">{row.classified}/{total} ({pct}%)</span>
                        </div>
                        <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                          <div className={`h-full rounded-full ${pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500'}`} style={{ width: `${pct}%` }} />
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {error && (
        <Alert variant="destructive"><AlertDescription>{String(error)}</AlertDescription></Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        {/* Ingested ontologies + class hierarchy */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm">Ingested Ontologies</CardTitle>
                <Select value={apFilter} onValueChange={setApFilter}>
                  <SelectTrigger className="w-28 h-7 text-xs">
                    <SelectValue placeholder="Filter…" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All</SelectItem>
                    <SelectItem value="AP239">AP239</SelectItem>
                    <SelectItem value="AP242">AP242</SelectItem>
                    <SelectItem value="AP243">AP243</SelectItem>
                    <SelectItem value="STEP">STEP</SelectItem>
                    <SelectItem value="PLCS">PLCS</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-2">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-5 w-full" />)}</div>
              ) : (filteredOntologies.length) === 0 ? (
                <p className="text-sm text-muted-foreground">No ontologies{apFilter !== 'all' ? ` matching "${apFilter}"` : ' ingested yet'}</p>
              ) : (
                <ul className="space-y-1.5">
                  {filteredOntologies.map((o, i) => (
                    <li key={i} className="flex items-center justify-between gap-2 text-sm">
                      <div className="flex items-center gap-2 min-w-0">
                        <FileCode2 className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                        <span className="truncate">{o.name ?? o.uri ?? `Ontology ${i + 1}`}</span>
                      </div>
                      <Badge variant="outline" className="text-xs shrink-0">
                        {o.class_count ?? 0} cls
                      </Badge>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card className="flex flex-col min-h-90">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Class Hierarchy</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 p-0">
              <ScrollArea className="h-80 px-4 pb-4">
                {(classHierarchy?.length ?? 0) === 0 ? (
                  <p className="text-sm text-muted-foreground p-4">No class data available</p>
                ) : (
                  <ClassTree classes={classHierarchy} onSelect={setSelectedClass} selectedId={selectedClass?.id ?? selectedClass?.uri} />
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </div>

        {/* Class detail */}
        <Card className="min-h-100">
          <CardHeader>
            <CardTitle className="text-base">{selectedClass ? selectedClass.name ?? selectedClass.label ?? selectedClass.id ?? selectedClass.uri : 'Class Detail'}</CardTitle>
            <CardDescription>{selectedClass ? 'Properties, description, and equivalent classes' : 'Select a class from the hierarchy to view details'}</CardDescription>
          </CardHeader>
          <CardContent>
            {!selectedClass ? (
              <p className="text-sm text-muted-foreground text-center py-12">Click a class in the hierarchy panel</p>
            ) : (
              <div className="space-y-4">
                {selectedClass.description && (
                  <div>
                    <h4 className="text-sm font-medium mb-1">Description</h4>
                    <p className="text-sm text-muted-foreground">{selectedClass.description}</p>
                  </div>
                )}

                <Separator />

                <div>
                  <h4 className="text-sm font-medium mb-2">Properties</h4>
                  {(selectedClass.properties ?? []).length === 0 ? (
                    <p className="text-xs text-muted-foreground">No properties</p>
                  ) : (
                    <ul className="space-y-1">
                      {selectedClass.properties.map((p, i) => (
                        <li key={i} className="flex items-center gap-2 text-sm">
                          <Badge variant="outline" className="text-xs">{p.type ?? 'property'}</Badge>
                          <span>{p.name ?? p.id}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <Separator />

                <div>
                  <h4 className="text-sm font-medium mb-2">Equivalent Classes</h4>
                  {(selectedClass.equivalentClasses ?? []).length === 0 ? (
                    <p className="text-xs text-muted-foreground">None</p>
                  ) : (
                    <div className="flex flex-wrap gap-1">
                      {selectedClass.equivalentClasses.map((ec, i) => (
                        <Badge key={i} variant="secondary">{ec}</Badge>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
