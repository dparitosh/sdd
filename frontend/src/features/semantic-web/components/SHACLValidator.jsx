import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@ui/card';
import { Button } from '@ui/button';
import { Badge } from '@ui/badge';
import { Label } from '@ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@ui/select';
import { ScrollArea } from '@ui/scroll-area';
import { Alert, AlertDescription } from '@ui/alert';
import { Separator } from '@ui/separator';
import PageHeader from '@/components/PageHeader';
import { ShieldCheck, CheckCircle2, XCircle, AlertTriangle } from 'lucide-react';
import { useSHACL } from '../hooks/useSHACL';

const SHAPE_OPTIONS = [
  { value: 'ap239_requirement', label: 'AP239 Requirement' },
  { value: 'ap242_part', label: 'AP242 Part' },
  { value: 'sdd_dossier', label: 'SDD Dossier' },
  { value: 'approval_record', label: 'Approval Record' },
];

export default function SHACLValidator() {
  const [shapeName, setShapeName] = useState('');
  const [rdfInput, setRdfInput] = useState('');
  const { validate, result, isValidating, error } = useSHACL();

  const handleValidate = () => {
    if (!rdfInput.trim()) return;
    validate(rdfInput.trim(), shapeName || undefined);
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <PageHeader
        title="SHACL Validator"
        description="Validate RDF data against SHACL shape definitions"
        icon={<ShieldCheck className="h-6 w-6 text-primary" />}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Input panel */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Input</CardTitle>
            <CardDescription>Paste or type RDF data (Turtle, JSON-LD, or N-Triples) and select a shape</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label>Shape Definition</Label>
              <Select value={shapeName} onValueChange={setShapeName}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a shape…" />
                </SelectTrigger>
                <SelectContent>
                  {SHAPE_OPTIONS.map((s) => (
                    <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label>RDF Data</Label>
              <textarea
                className="w-full h-64 rounded-md border bg-background px-3 py-2 text-sm font-mono resize-y focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                placeholder={'@prefix ex: <http://example.org/> .\n\nex:myResource a ex:Requirement ;\n  ex:name "Sample" .'}
                value={rdfInput}
                onChange={(e) => setRdfInput(e.target.value)}
              />
            </div>

            <Button onClick={handleValidate} disabled={isValidating || !rdfInput.trim()}>
              {isValidating ? 'Validating…' : 'Validate'}
            </Button>
          </CardContent>
        </Card>

        {/* Results panel */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Results</CardTitle>
            <CardDescription>Validation conformance and violation details</CardDescription>
          </CardHeader>
          <CardContent>
            {error && (
              <Alert variant="destructive" className="mb-4"><AlertDescription>{String(error)}</AlertDescription></Alert>
            )}

            {!result ? (
              <p className="text-sm text-muted-foreground text-center py-12">Run validation to see results</p>
            ) : (
              <div className="space-y-4">
                {/* Conformance badge */}
                <div className="flex items-center gap-3">
                  {result.conforms ? (
                    <Badge className="bg-green-500 text-white gap-1"><CheckCircle2 className="h-3 w-3" /> Conforms</Badge>
                  ) : (
                    <Badge variant="destructive" className="gap-1"><XCircle className="h-3 w-3" /> Does Not Conform</Badge>
                  )}
                  <span className="text-sm text-muted-foreground">
                    {(result.violations ?? []).length} violation{(result.violations ?? []).length !== 1 ? 's' : ''}
                  </span>
                </div>

                <Separator />

                {/* Violations list */}
                <ScrollArea className="h-72">
                  {(result.violations ?? []).length === 0 ? (
                    <p className="text-sm text-muted-foreground">No violations found</p>
                  ) : (
                    <ul className="space-y-3">
                      {result.violations.map((v, i) => (
                        <li key={i} className="rounded border p-3 space-y-1">
                          <div className="flex items-center gap-2">
                            <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />
                            <span className="text-sm font-medium">{v.message ?? 'Validation violation'}</span>
                          </div>
                          {v.path && <p className="text-xs text-muted-foreground ml-6">Path: <code className="bg-muted px-1 rounded">{v.path}</code></p>}
                          {v.focus_node && <p className="text-xs text-muted-foreground ml-6">Focus: {v.focus_node}</p>}
                          {v.severity && <Badge variant="outline" className="ml-6 text-xs">{v.severity}</Badge>}
                        </li>
                      ))}
                    </ul>
                  )}
                </ScrollArea>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
