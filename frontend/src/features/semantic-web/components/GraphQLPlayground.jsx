import { useState, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@ui/card';
import { Button } from '@ui/button';
import { Badge } from '@ui/badge';
import { ScrollArea } from '@ui/scroll-area';
import { Alert, AlertDescription } from '@ui/alert';
import { Separator } from '@ui/separator';
import PageHeader from '@/components/PageHeader';
import { Play, Code2, Copy, Check } from 'lucide-react';
import { graphqlRequest } from '@/services/graphql';

const EXAMPLE_QUERIES = [
  {
    label: 'Statistics',
    query: `query {\n  statistics\n}`,
  },
  {
    label: 'Cypher Read',
    query: `query {\n  cypher_read(statement: "MATCH (n) RETURN labels(n) AS label, count(*) AS count ORDER BY count DESC LIMIT 10")\n}`,
  },
  {
    label: 'Node Types',
    query: `query {\n  statistics {\n    node_types\n  }\n}`,
  },
];

export default function GraphQLPlayground() {
  const [query, setQuery] = useState(EXAMPLE_QUERIES[0].query);
  const [variables, setVariables] = useState('{}');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleExecute = useCallback(async () => {
    setIsExecuting(true);
    setError(null);
    setResult(null);
    try {
      let vars;
      try {
        vars = JSON.parse(variables);
      } catch {
        vars = undefined;
      }
      const data = await graphqlRequest(query, vars);
      setResult(data);
    } catch (err) {
      setError(err?.message ?? String(err));
    } finally {
      setIsExecuting(false);
    }
  }, [query, variables]);

  const handleCopy = useCallback(() => {
    if (result) {
      navigator.clipboard.writeText(JSON.stringify(result, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [result]);

  return (
    <div className="container mx-auto p-6 space-y-6">
      <PageHeader
        title="GraphQL Playground"
        description="Execute GraphQL queries against the knowledge graph"
        icon={<Code2 className="h-6 w-6 text-primary" />}
      />

      {/* Example queries */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-sm text-muted-foreground">Examples:</span>
        {EXAMPLE_QUERIES.map((ex) => (
          <Button key={ex.label} variant="outline" size="sm" onClick={() => setQuery(ex.query)}>
            {ex.label}
          </Button>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Query + Variables */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Query</CardTitle>
            </CardHeader>
            <CardContent>
              <textarea
                className="w-full h-56 rounded-md border bg-zinc-950 text-green-400 px-3 py-2 text-sm font-mono resize-y focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                spellCheck={false}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground">Variables (JSON)</CardTitle>
            </CardHeader>
            <CardContent>
              <textarea
                className="w-full h-20 rounded-md border bg-zinc-950 text-green-400 px-3 py-2 text-sm font-mono resize-y focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                value={variables}
                onChange={(e) => setVariables(e.target.value)}
                spellCheck={false}
              />
            </CardContent>
          </Card>

          <Button onClick={handleExecute} disabled={isExecuting || !query.trim()} className="w-full">
            <Play className="h-4 w-4 mr-2" />
            {isExecuting ? 'Executing…' : 'Execute Query'}
          </Button>
        </div>

        {/* Results */}
        <Card className="min-h-96">
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-base">Results</CardTitle>
              <CardDescription>JSON response from the GraphQL API</CardDescription>
            </div>
            {result && (
              <Button variant="ghost" size="sm" onClick={handleCopy}>
                {copied ? <Check className="h-3 w-3 mr-1" /> : <Copy className="h-3 w-3 mr-1" />}
                {copied ? 'Copied' : 'Copy'}
              </Button>
            )}
          </CardHeader>
          <CardContent className="p-0">
            {error && (
              <Alert variant="destructive" className="m-4"><AlertDescription>{error}</AlertDescription></Alert>
            )}
            {!result && !error ? (
              <p className="text-sm text-muted-foreground text-center py-12">Execute a query to see results</p>
            ) : result ? (
              <ScrollArea className="h-96">
                <pre className="text-xs font-mono p-4 whitespace-pre-wrap break-words">
                  {JSON.stringify(result, null, 2)}
                </pre>
              </ScrollArea>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
