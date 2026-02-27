import { useState, useRef } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@ui/card';
import { Button } from '@ui/button';
import { Badge } from '@ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@ui/tabs';
import { ScrollArea } from '@ui/scroll-area';
import { Skeleton } from '@ui/skeleton';
import { Alert, AlertDescription } from '@ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@ui/select';
import { Separator } from '@ui/separator';
import PageHeader from '@/components/PageHeader';
import { Upload, FileCode, Search, Download, Layers } from 'lucide-react';
import { useMutation, useQuery } from '@tanstack/react-query';
import * as expressService from '@/services/express.service';

export default function ExpressExplorer() {
  const fileRef = useRef(null);
  const [parseResult, setParseResult] = useState(null);
  const [selectedEntity, setSelectedEntity] = useState(null);
  const [exportFormat, setExportFormat] = useState('json');

  const parseMutation = useMutation({
    mutationFn: (file) => expressService.parseExpress(file),
    onSuccess: (data) => {
      setParseResult(data);
      setSelectedEntity(null);
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: (schema) => expressService.analyzeExpress(schema),
  });

  const handleUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) parseMutation.mutate(file);
  };

  const entities = parseResult?.entities ?? [];
  const types = parseResult?.types ?? [];
  const rules = parseResult?.rules ?? [];
  const functions = parseResult?.functions ?? [];
  const schemaName = parseResult?.schema ?? parseResult?.name ?? 'Unknown';

  const handleAnalyze = () => {
    if (schemaName) analyzeMutation.mutate(schemaName);
  };

  const handleExport = async () => {
    if (!schemaName) return;
    try {
      const result = await expressService.exportExpress(schemaName, exportFormat);
      const blob = new Blob([typeof result === 'string' ? result : JSON.stringify(result, null, 2)], { type: 'application/octet-stream' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${schemaName}.${exportFormat === 'json' ? 'json' : exportFormat === 'plantuml' ? 'puml' : 'cypher'}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // silent fail — user can retry
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <PageHeader
        title="EXPRESS Explorer"
        description="Parse, browse, and analyze ISO 10303-11 EXPRESS schemas"
        icon={<FileCode className="h-6 w-6 text-primary" />}
      />

      {/* Upload + actions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Schema Input</CardTitle>
          <CardDescription>Upload an EXPRESS (.exp) file to parse</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-3">
          <input ref={fileRef} type="file" accept=".exp,.express" className="hidden" onChange={handleUpload} />
          <Button onClick={() => fileRef.current?.click()} disabled={parseMutation.isPending}>
            <Upload className="h-4 w-4 mr-2" />
            {parseMutation.isPending ? 'Parsing…' : 'Upload .exp File'}
          </Button>

          {parseResult && (
            <>
              <Button variant="outline" onClick={handleAnalyze} disabled={analyzeMutation.isPending}>
                <Search className="h-4 w-4 mr-2" />
                {analyzeMutation.isPending ? 'Analyzing…' : 'Analyze'}
              </Button>

              <div className="flex items-center gap-2">
                <Select value={exportFormat} onValueChange={setExportFormat}>
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="json">JSON</SelectItem>
                    <SelectItem value="neo4j">Neo4j Graph</SelectItem>
                    <SelectItem value="plantuml">PlantUML</SelectItem>
                  </SelectContent>
                </Select>
                <Button variant="outline" onClick={handleExport}>
                  <Download className="h-4 w-4 mr-2" /> Export
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {parseMutation.isError && (
        <Alert variant="destructive"><AlertDescription>{String(parseMutation.error)}</AlertDescription></Alert>
      )}

      {analyzeMutation.data && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Schema Analysis</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-xs font-mono whitespace-pre-wrap bg-muted p-3 rounded">
              {JSON.stringify(analyzeMutation.data, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}

      {/* Schema browser */}
      {parseResult && (
        <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
          {/* Left: categories */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Schema: {schemaName}</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Tabs defaultValue="entities" className="w-full">
                <TabsList className="w-full rounded-none border-b">
                  <TabsTrigger value="entities" className="flex-1">Entities ({entities.length})</TabsTrigger>
                  <TabsTrigger value="types" className="flex-1">Types ({types.length})</TabsTrigger>
                  <TabsTrigger value="rules" className="flex-1">Rules ({rules.length})</TabsTrigger>
                </TabsList>

                <TabsContent value="entities" className="m-0">
                  <ScrollArea className="h-72 px-3 pb-3">
                    {entities.length === 0 ? (
                      <p className="text-sm text-muted-foreground py-4">No entities</p>
                    ) : (
                      <ul className="space-y-0.5 pt-2">
                        {entities.map((e, i) => (
                          <li key={i}>
                            <button
                              type="button"
                              className={`w-full text-left text-sm px-2 py-1 rounded hover:bg-muted/50 truncate ${selectedEntity?.name === (e.name ?? e) ? 'bg-primary/10 font-medium' : ''}`}
                              onClick={() => setSelectedEntity(typeof e === 'string' ? { name: e } : e)}
                            >
                              {e.name ?? e}
                            </button>
                          </li>
                        ))}
                      </ul>
                    )}
                  </ScrollArea>
                </TabsContent>

                <TabsContent value="types" className="m-0">
                  <ScrollArea className="h-72 px-3 pb-3">
                    {types.length === 0 ? (
                      <p className="text-sm text-muted-foreground py-4">No types</p>
                    ) : (
                      <ul className="space-y-0.5 pt-2">
                        {types.map((t, i) => (
                          <li key={i} className="text-sm px-2 py-1">{t.name ?? t}</li>
                        ))}
                      </ul>
                    )}
                  </ScrollArea>
                </TabsContent>

                <TabsContent value="rules" className="m-0">
                  <ScrollArea className="h-72 px-3 pb-3">
                    {rules.length === 0 && functions.length === 0 ? (
                      <p className="text-sm text-muted-foreground py-4">No rules or functions</p>
                    ) : (
                      <ul className="space-y-0.5 pt-2">
                        {rules.map((r, i) => (
                          <li key={`r-${i}`} className="flex items-center gap-2 text-sm px-2 py-1">
                            <Badge variant="outline" className="text-xs">Rule</Badge>{r.name ?? r}
                          </li>
                        ))}
                        {functions.map((f, i) => (
                          <li key={`f-${i}`} className="flex items-center gap-2 text-sm px-2 py-1">
                            <Badge variant="secondary" className="text-xs">Fn</Badge>{f.name ?? f}
                          </li>
                        ))}
                      </ul>
                    )}
                  </ScrollArea>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          {/* Right: entity detail */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{selectedEntity ? selectedEntity.name : 'Entity Detail'}</CardTitle>
              <CardDescription>{selectedEntity ? 'Attributes, supertypes, and subtypes' : 'Select an entity from the left panel'}</CardDescription>
            </CardHeader>
            <CardContent>
              {!selectedEntity ? (
                <p className="text-sm text-muted-foreground text-center py-12">Click an entity to view details</p>
              ) : (
                <div className="space-y-4">
                  {/* Attributes */}
                  <div>
                    <h4 className="text-sm font-medium mb-2">Attributes</h4>
                    {(selectedEntity.attributes ?? []).length === 0 ? (
                      <p className="text-xs text-muted-foreground">No attributes defined</p>
                    ) : (
                      <ul className="space-y-1">
                        {selectedEntity.attributes.map((a, i) => (
                          <li key={i} className="flex items-center gap-2 text-sm">
                            <code className="bg-muted px-1.5 py-0.5 rounded text-xs">{a.name ?? a}</code>
                            {a.type && <span className="text-xs text-muted-foreground">: {a.type}</span>}
                            {a.optional && <Badge variant="outline" className="text-xs">optional</Badge>}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>

                  <Separator />

                  {/* Inverse attributes */}
                  {(selectedEntity.inverse_attributes ?? []).length > 0 && (
                    <>
                      <div>
                        <h4 className="text-sm font-medium mb-2">Inverse Attributes</h4>
                        <ul className="space-y-1">
                          {selectedEntity.inverse_attributes.map((a, i) => (
                            <li key={i} className="text-sm"><code className="bg-muted px-1.5 py-0.5 rounded text-xs">{a.name ?? a}</code></li>
                          ))}
                        </ul>
                      </div>
                      <Separator />
                    </>
                  )}

                  {/* Supertypes / subtypes */}
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <h4 className="text-sm font-medium mb-1">Supertypes</h4>
                      {(selectedEntity.supertypes ?? []).length === 0 ? (
                        <p className="text-xs text-muted-foreground">None</p>
                      ) : (
                        <div className="flex flex-wrap gap-1">
                          {selectedEntity.supertypes.map((s, i) => <Badge key={i} variant="secondary">{s}</Badge>)}
                        </div>
                      )}
                    </div>
                    <div>
                      <h4 className="text-sm font-medium mb-1">Subtypes</h4>
                      {(selectedEntity.subtypes ?? []).length === 0 ? (
                        <p className="text-xs text-muted-foreground">None</p>
                      ) : (
                        <div className="flex flex-wrap gap-1">
                          {selectedEntity.subtypes.map((s, i) => <Badge key={i} variant="outline">{s}</Badge>)}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
