import { useState, useRef } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@ui/card';
import { Button } from '@ui/button';
import { Badge } from '@ui/badge';
import { ScrollArea } from '@ui/scroll-area';
import { Skeleton } from '@ui/skeleton';
import { Alert, AlertDescription } from '@ui/alert';
import { Separator } from '@ui/separator';
import PageHeader from '@/components/PageHeader';
import { Upload, ChevronRight, ChevronDown, FileCode2, Layers } from 'lucide-react';
import { useOntology } from '../hooks/useOntology';

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
  const { ontologies, classHierarchy, ingest, isIngesting, ingestResult, isLoading, error } = useOntology();

  const handleUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) ingest(file);
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <PageHeader
        title="Ontology Manager"
        description="Upload OWL/RDF ontologies and browse class hierarchies"
        icon={<Layers className="h-6 w-6 text-primary" />}
      />

      {/* Upload */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Ingest Ontology</CardTitle>
          <CardDescription>Upload an OWL or RDF file to ingest into the knowledge graph</CardDescription>
        </CardHeader>
        <CardContent className="flex items-center gap-4">
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
        </CardContent>
      </Card>

      {error && (
        <Alert variant="destructive"><AlertDescription>{String(error)}</AlertDescription></Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        {/* Ingested ontologies + class hierarchy */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Ingested Ontologies</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-2">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-5 w-full" />)}</div>
              ) : (ontologies?.length ?? 0) === 0 ? (
                <p className="text-sm text-muted-foreground">No ontologies ingested yet</p>
              ) : (
                <ul className="space-y-1">
                  {ontologies.map((o, i) => (
                    <li key={i} className="flex items-center gap-2 text-sm">
                      <FileCode2 className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="truncate">{o.name ?? o.uri ?? `Ontology ${i + 1}`}</span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card className="flex flex-col min-h-[360px]">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Class Hierarchy</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 p-0">
              <ScrollArea className="h-[320px] px-4 pb-4">
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
        <Card className="min-h-[400px]">
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
