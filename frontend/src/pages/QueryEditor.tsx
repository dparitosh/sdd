import { useState, useRef } from 'react';
import Editor from '@monaco-editor/react';
import { useMutation } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { 
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Play, Download, History, Trash2, Copy } from 'lucide-react';
import { apiService } from '@/services/api';
import { toast } from 'sonner';

interface QueryResult {
  results: any[];
  summary: {
    executionTime: number;
    resultCount: number;
  };
}

interface QueryHistory {
  query: string;
  timestamp: Date;
  executionTime?: number;
  resultCount?: number;
  error?: string;
}

const SAMPLE_QUERIES = [
  {
    name: 'List All Classes',
    query: 'MATCH (c:Class) RETURN c.name AS Name, c.uid AS UID LIMIT 20',
  },
  {
    name: 'Find Requirements',
    query: 'MATCH (r:Requirement) RETURN r.name AS Name, r.uid AS UID, r.description AS Description LIMIT 20',
  },
  {
    name: 'Traceability Links',
    query: 'MATCH (r:Requirement)-[rel]->(c:Class) RETURN r.name AS Requirement, type(rel) AS Relationship, c.name AS Class LIMIT 20',
  },
  {
    name: 'Package Hierarchy',
    query: 'MATCH (p:Package)-[:CONTAINS]->(c:Class) RETURN p.name AS Package, count(c) AS ClassCount ORDER BY ClassCount DESC LIMIT 10',
  },
];

export default function QueryEditor() {
  const [query, setQuery] = useState(SAMPLE_QUERIES[0].query);
  const [results, setResults] = useState<any[] | null>(null);
  const [summary, setSummary] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<QueryHistory[]>(() => {
    const saved = localStorage.getItem('queryHistory');
    return saved ? JSON.parse(saved) : [];
  });
  const editorRef = useRef<any>(null);

  const executeMutation = useMutation({
    mutationFn: (cypherQuery: string) => apiService.executeCypher(cypherQuery),
    onSuccess: (response) => {
      const data = response.data;
      setResults(data.results || []);
      setSummary(data.summary || { executionTime: 0, resultCount: data.results?.length || 0 });
      setError(null);
      
      // Add to history
      const newHistory: QueryHistory = {
        query,
        timestamp: new Date(),
        executionTime: data.summary?.executionTime,
        resultCount: data.results?.length || 0,
      };
      const updatedHistory = [newHistory, ...history.slice(0, 19)]; // Keep last 20
      setHistory(updatedHistory);
      localStorage.setItem('queryHistory', JSON.stringify(updatedHistory));
      
      toast.success(`Query executed successfully (${data.results?.length || 0} results)`);
    },
    onError: (err: any) => {
      setError(err.message || 'Failed to execute query');
      setResults(null);
      setSummary(null);
      
      // Add error to history
      const newHistory: QueryHistory = {
        query,
        timestamp: new Date(),
        error: err.message,
      };
      const updatedHistory = [newHistory, ...history.slice(0, 19)];
      setHistory(updatedHistory);
      localStorage.setItem('queryHistory', JSON.stringify(updatedHistory));
      
      toast.error('Query execution failed');
    },
  });

  const handleExecute = () => {
    if (!query.trim()) {
      toast.error('Please enter a query');
      return;
    }
    executeMutation.mutate(query);
  };

  const exportToJSON = () => {
    if (!results) return;
    
    const json = JSON.stringify(results, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `query_results_${new Date().toISOString()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Results exported to JSON');
  };

  const exportToCSV = () => {
    if (!results || results.length === 0) return;
    
    const keys = Object.keys(results[0]);
    const csv = [
      keys.join(','),
      ...results.map(row => 
        keys.map(key => {
          const value = row[key];
          if (value === null || value === undefined) return '';
          return `"${String(value).replace(/"/g, '""')}"`;
        }).join(',')
      )
    ].join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `query_results_${new Date().toISOString()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Results exported to CSV');
  };

  const loadQuery = (queryText: string) => {
    setQuery(queryText);
    if (editorRef.current) {
      editorRef.current.setValue(queryText);
    }
  };

  const clearHistory = () => {
    if (confirm('Are you sure you want to clear query history?')) {
      setHistory([]);
      localStorage.removeItem('queryHistory');
      toast.success('Query history cleared');
    }
  };

  const copyQuery = (queryText: string) => {
    navigator.clipboard.writeText(queryText);
    toast.success('Query copied to clipboard');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Query Editor</h1>
        <p className="text-muted-foreground">
          Execute custom Cypher queries against the Neo4j database
        </p>
      </div>

      {/* Sample Queries */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Sample Queries</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {SAMPLE_QUERIES.map((sample, index) => (
              <Button
                key={index}
                variant="outline"
                size="sm"
                onClick={() => loadQuery(sample.query)}
              >
                {sample.name}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Editor */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Cypher Query</CardTitle>
          <div className="flex gap-2">
            <Button
              onClick={handleExecute}
              disabled={executeMutation.isPending}
              size="sm"
            >
              <Play className="h-4 w-4 mr-2" />
              {executeMutation.isPending ? 'Executing...' : 'Execute'}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="border rounded-md overflow-hidden">
            <Editor
              height="300px"
              defaultLanguage="cypher"
              defaultValue={query}
              onChange={(value) => setQuery(value || '')}
              onMount={(editor) => {
                editorRef.current = editor;
              }}
              theme="vs-dark"
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                automaticLayout: true,
              }}
            />
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {(results || error) && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Results</CardTitle>
              {summary && (
                <div className="flex gap-4 mt-2 text-sm text-muted-foreground">
                  <span>Execution Time: {summary.executionTime}ms</span>
                  <span>Results: {summary.resultCount}</span>
                </div>
              )}
            </div>
            {results && results.length > 0 && (
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={exportToJSON}>
                  <Download className="h-4 w-4 mr-2" />
                  JSON
                </Button>
                <Button variant="outline" size="sm" onClick={exportToCSV}>
                  <Download className="h-4 w-4 mr-2" />
                  CSV
                </Button>
              </div>
            )}
          </CardHeader>
          <CardContent>
            {error ? (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            ) : results && results.length === 0 ? (
              <Alert>
                <AlertDescription>Query executed successfully but returned no results.</AlertDescription>
              </Alert>
            ) : results && (
              <div className="rounded-md border overflow-auto max-h-[500px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      {Object.keys(results[0]).map((key) => (
                        <TableHead key={key}>{key}</TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {results.map((row, index) => (
                      <TableRow key={index}>
                        {Object.values(row).map((value: any, i) => (
                          <TableCell key={i}>
                            {typeof value === 'object' 
                              ? JSON.stringify(value) 
                              : String(value)}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* History */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <History className="h-5 w-5" />
            Query History
          </CardTitle>
          {history.length > 0 && (
            <Button variant="outline" size="sm" onClick={clearHistory}>
              <Trash2 className="h-4 w-4 mr-2" />
              Clear
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {history.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              No query history yet. Execute a query to see it here.
            </p>
          ) : (
            <div className="space-y-2 max-h-[400px] overflow-auto">
              {history.map((item, index) => (
                <div
                  key={index}
                  className="flex items-start justify-between gap-4 p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs text-muted-foreground">
                        {new Date(item.timestamp).toLocaleString()}
                      </span>
                      {item.error ? (
                        <Badge variant="destructive" className="text-xs">Error</Badge>
                      ) : (
                        <Badge variant="outline" className="text-xs">
                          {item.resultCount} results · {item.executionTime}ms
                        </Badge>
                      )}
                    </div>
                    <code className="text-xs block truncate">{item.query}</code>
                    {item.error && (
                      <p className="text-xs text-destructive mt-1">{item.error}</p>
                    )}
                  </div>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => copyQuery(item.query)}
                    >
                      <Copy className="h-3 w-3" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => loadQuery(item.query)}
                    >
                      <Play className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
