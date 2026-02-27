import { useState, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@ui/card';
import { Button } from '@ui/button';
import { Badge } from '@ui/badge';
import { Label } from '@ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@ui/select';
import { Checkbox } from '@ui/checkbox';
import { ScrollArea } from '@ui/scroll-area';
import { Alert, AlertDescription } from '@ui/alert';
import PageHeader from '@/components/PageHeader';
import { Download, FileOutput, Loader2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { graphqlService } from '@/services/graphql';
import * as exportService from '@/services/export.service';

const FORMAT_OPTIONS = [
  { value: 'turtle', label: 'RDF/Turtle', ext: 'ttl' },
  { value: 'jsonld', label: 'JSON-LD', ext: 'jsonld' },
  { value: 'ntriples', label: 'N-Triples', ext: 'nt' },
];

export default function RDFExporter() {
  const [format, setFormat] = useState('turtle');
  const [selectedTypes, setSelectedTypes] = useState([]);
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState(null);
  const [lastExport, setLastExport] = useState(null);

  const { data: stats, isLoading } = useQuery({
    queryKey: ['statistics-export'],
    queryFn: graphqlService.getStatistics,
    staleTime: 60_000,
  });

  const nodeTypes = Object.entries(stats?.node_types ?? {}).sort(([, a], [, b]) => b - a);

  const toggleType = useCallback((type) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  }, []);

  const selectAll = useCallback(() => {
    setSelectedTypes(nodeTypes.map(([t]) => t));
  }, [nodeTypes]);

  const selectNone = useCallback(() => {
    setSelectedTypes([]);
  }, []);

  const handleExport = useCallback(async () => {
    setIsExporting(true);
    setExportError(null);
    setLastExport(null);
    try {
      let blob;
      if (format === 'jsonld') {
        const data = await exportService.exportJSONLD();
        blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/ld+json' });
      } else {
        const data = await exportService.exportRDF(format);
        blob = new Blob([typeof data === 'string' ? data : JSON.stringify(data)], { type: 'text/plain' });
      }

      const fmtInfo = FORMAT_OPTIONS.find((f) => f.value === format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `knowledge-graph.${fmtInfo?.ext ?? 'rdf'}`;
      a.click();
      URL.revokeObjectURL(url);
      setLastExport({ format: fmtInfo?.label ?? format, size: blob.size });
    } catch (err) {
      setExportError(err?.message ?? String(err));
    } finally {
      setIsExporting(false);
    }
  }, [format]);

  return (
    <div className="container mx-auto p-6 space-y-6">
      <PageHeader
        title="RDF Exporter"
        description="Export knowledge graph data in RDF serialization formats"
        icon={<FileOutput className="h-6 w-6 text-primary" />}
      />

      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        {/* Export config */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Export Format</CardTitle>
              <CardDescription>Choose the RDF serialization</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Select value={format} onValueChange={setFormat}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {FORMAT_OPTIONS.map((f) => (
                    <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Button onClick={handleExport} disabled={isExporting} className="w-full">
                {isExporting ? (
                  <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Exporting…</>
                ) : (
                  <><Download className="h-4 w-4 mr-2" /> Export</>
                )}
              </Button>

              {lastExport && (
                <Badge variant="outline" className="text-green-600">
                  Exported {lastExport.format} ({(lastExport.size / 1024).toFixed(1)} KB)
                </Badge>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Node type filter */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base">Node Type Filter</CardTitle>
                <CardDescription>Select which node labels to include in the export</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" onClick={selectAll}>All</Button>
                <Button variant="ghost" size="sm" onClick={selectNone}>None</Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="grid grid-cols-2 gap-2">{[...Array(6)].map((_, i) => <div key={i} className="h-6 bg-muted rounded animate-pulse" />)}</div>
            ) : nodeTypes.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">No node types found in graph</p>
            ) : (
              <ScrollArea className="h-80">
                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {nodeTypes.map(([type, count]) => (
                    <label key={type} className="flex items-center gap-2 rounded p-2 hover:bg-muted/50 cursor-pointer text-sm">
                      <Checkbox
                        checked={selectedTypes.includes(type)}
                        onCheckedChange={() => toggleType(type)}
                      />
                      <span className="truncate">{type}</span>
                      <Badge variant="secondary" className="ml-auto text-xs">{count}</Badge>
                    </label>
                  ))}
                </div>
              </ScrollArea>
            )}

            {exportError && (
              <Alert variant="destructive" className="mt-4">
                <AlertDescription>{exportError}</AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
