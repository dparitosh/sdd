import { useState, useRef } from 'react';
import Editor from '@monaco-editor/react';
import { useMutation } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';

import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow } from
'@/components/ui/table';
import { Play, Download, History, Trash2, Copy } from 'lucide-react';
import { apiService } from '@/services/api';
import { toast } from 'sonner';import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";

















const SAMPLE_QUERIES = [
{
  name: 'List All Classes',
  query: 'MATCH (c:Class) RETURN c.name AS Name, c.uid AS UID LIMIT 20'
},
{
  name: 'Find Requirements',
  query: 'MATCH (r:Requirement) RETURN r.name AS Name, r.uid AS UID, r.description AS Description LIMIT 20'
},
{
  name: 'Traceability Links',
  query: 'MATCH (r:Requirement)-[rel]->(c:Class) RETURN r.name AS Requirement, type(rel) AS Relationship, c.name AS Class LIMIT 20'
},
{
  name: 'Package Hierarchy',
  query: 'MATCH (p:Package)-[:CONTAINS]->(c:Class) RETURN p.name AS Package, count(c) AS ClassCount ORDER BY ClassCount DESC LIMIT 10'
}];


export default function QueryEditor() {
  const [query, setQuery] = useState(SAMPLE_QUERIES[0].query);
  const [results, setResults] = useState(null);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState(() => {
    const saved = localStorage.getItem('queryHistory');
    return saved ? JSON.parse(saved) : [];
  });
  const editorRef = useRef(null);

  const executeMutation = useMutation({
    mutationFn: (cypherQuery) => apiService.executeCypher(cypherQuery),
    onSuccess: (response) => {
      const data = response.data;
      setResults(data.results || []);
      setSummary(data.summary || { executionTime: 0, resultCount: data.results?.length || 0 });
      setError(null);

      // Add to history
      const newHistory = {
        query,
        timestamp: new Date(),
        executionTime: data.summary?.executionTime,
        resultCount: data.results?.length || 0
      };
      const updatedHistory = [newHistory, ...history.slice(0, 19)]; // Keep last 20
      setHistory(updatedHistory);
      localStorage.setItem('queryHistory', JSON.stringify(updatedHistory));

      toast.success(`Query executed successfully (${data.results?.length || 0} results)`);
    },
    onError: (err) => {
      setError(err.message || 'Failed to execute query');
      setResults(null);
      setSummary(null);

      // Add error to history
      const newHistory = {
        query,
        timestamp: new Date(),
        error: err.message
      };
      const updatedHistory = [newHistory, ...history.slice(0, 19)];
      setHistory(updatedHistory);
      localStorage.setItem('queryHistory', JSON.stringify(updatedHistory));

      toast.error('Query execution failed');
    }
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
    ...results.map((row) =>
    keys.map((key) => {
      const value = row[key];
      if (value === null || value === undefined) return '';
      return `"${String(value).replace(/"/g, '""')}"`;
    }).join(',')
    )].
    join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `query_results_${new Date().toISOString()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Results exported to CSV');
  };

  const loadQuery = (queryText) => {
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

  const copyQuery = (queryText) => {
    navigator.clipboard.writeText(queryText);
    toast.success('Query copied to clipboard');
  };

  return (/*#__PURE__*/
    _jsxs("div", { className: "space-y-6", children: [/*#__PURE__*/

      _jsxs("div", { children: [/*#__PURE__*/
        _jsx("h1", { className: "text-3xl font-bold tracking-tight", children: "Query Editor" }), /*#__PURE__*/
        _jsx("p", { className: "text-muted-foreground", children: "Execute custom Cypher queries against the Neo4j database" }

        )] }
      ), /*#__PURE__*/


      _jsxs(Card, { children: [/*#__PURE__*/
        _jsx(CardHeader, { children: /*#__PURE__*/
          _jsx(CardTitle, { className: "text-sm font-medium", children: "Sample Queries" }) }
        ), /*#__PURE__*/
        _jsx(CardContent, { children: /*#__PURE__*/
          _jsx("div", { className: "flex flex-wrap gap-2", children:
            SAMPLE_QUERIES.map((sample, index) => /*#__PURE__*/
            _jsx(Button, {

              variant: "outline",
              size: "sm",
              onClick: () => loadQuery(sample.query), children:

              sample.name }, index
            )
            ) }
          ) }
        )] }
      ), /*#__PURE__*/


      _jsxs(Card, { children: [/*#__PURE__*/
        _jsxs(CardHeader, { className: "flex flex-row items-center justify-between", children: [/*#__PURE__*/
          _jsx(CardTitle, { children: "Cypher Query" }), /*#__PURE__*/
          _jsx("div", { className: "flex gap-2", children: /*#__PURE__*/
            _jsxs(Button, {
              onClick: handleExecute,
              disabled: executeMutation.isPending,
              size: "sm", children: [/*#__PURE__*/

              _jsx(Play, { className: "h-4 w-4 mr-2" }),
              executeMutation.isPending ? 'Executing...' : 'Execute'] }
            ) }
          )] }
        ), /*#__PURE__*/
        _jsx(CardContent, { children: /*#__PURE__*/
          _jsx("div", { className: "border rounded-md overflow-hidden", children: /*#__PURE__*/
            _jsx(Editor, {
              height: "300px",
              defaultLanguage: "cypher",
              defaultValue: query,
              onChange: (value) => setQuery(value || ''),
              onMount: (editor) => {
                editorRef.current = editor;
              },
              theme: "vs-dark",
              options: {
                minimap: { enabled: false },
                fontSize: 14,
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                automaticLayout: true
              } }
            ) }
          ) }
        )] }
      ),


      (results || error) && /*#__PURE__*/
      _jsxs(Card, { children: [/*#__PURE__*/
        _jsxs(CardHeader, { className: "flex flex-row items-center justify-between", children: [/*#__PURE__*/
          _jsxs("div", { children: [/*#__PURE__*/
            _jsx(CardTitle, { children: "Results" }),
            summary && /*#__PURE__*/
            _jsxs("div", { className: "flex gap-4 mt-2 text-sm text-muted-foreground", children: [/*#__PURE__*/
              _jsxs("span", { children: ["Execution Time: ", summary.executionTime, "ms"] }), /*#__PURE__*/
              _jsxs("span", { children: ["Results: ", summary.resultCount] })] }
            )] }

          ),
          results && results.length > 0 && /*#__PURE__*/
          _jsxs("div", { className: "flex gap-2", children: [/*#__PURE__*/
            _jsxs(Button, { variant: "outline", size: "sm", onClick: exportToJSON, children: [/*#__PURE__*/
              _jsx(Download, { className: "h-4 w-4 mr-2" }), "JSON"] }

            ), /*#__PURE__*/
            _jsxs(Button, { variant: "outline", size: "sm", onClick: exportToCSV, children: [/*#__PURE__*/
              _jsx(Download, { className: "h-4 w-4 mr-2" }), "CSV"] }

            )] }
          )] }

        ), /*#__PURE__*/
        _jsx(CardContent, { children:
          error ? /*#__PURE__*/
          _jsx(Alert, { variant: "destructive", children: /*#__PURE__*/
            _jsx(AlertDescription, { children: error }) }
          ) :
          results && results.length === 0 ? /*#__PURE__*/
          _jsx(Alert, { children: /*#__PURE__*/
            _jsx(AlertDescription, { children: "Query executed successfully but returned no results." }) }
          ) :
          results && /*#__PURE__*/
          _jsx("div", { className: "rounded-md border overflow-auto max-h-[500px]", children: /*#__PURE__*/
            _jsxs(Table, { children: [/*#__PURE__*/
              _jsx(TableHeader, { children: /*#__PURE__*/
                _jsx(TableRow, { children:
                  Object.keys(results[0]).map((key) => /*#__PURE__*/
                  _jsx(TableHead, { children: key }, key)
                  ) }
                ) }
              ), /*#__PURE__*/
              _jsx(TableBody, { children:
                results.map((row, index) => /*#__PURE__*/
                _jsx(TableRow, { children:
                  Object.values(row).map((value, i) => /*#__PURE__*/
                  _jsx(TableCell, { children:
                    typeof value === 'object' ?
                    JSON.stringify(value) :
                    String(value) }, i
                  )
                  ) }, index
                )
                ) }
              )] }
            ) }
          ) }

        )] }
      ), /*#__PURE__*/



      _jsxs(Card, { children: [/*#__PURE__*/
        _jsxs(CardHeader, { className: "flex flex-row items-center justify-between", children: [/*#__PURE__*/
          _jsxs(CardTitle, { className: "flex items-center gap-2", children: [/*#__PURE__*/
            _jsx(History, { className: "h-5 w-5" }), "Query History"] }

          ),
          history.length > 0 && /*#__PURE__*/
          _jsxs(Button, { variant: "outline", size: "sm", onClick: clearHistory, children: [/*#__PURE__*/
            _jsx(Trash2, { className: "h-4 w-4 mr-2" }), "Clear"] }

          )] }

        ), /*#__PURE__*/
        _jsx(CardContent, { children:
          history.length === 0 ? /*#__PURE__*/
          _jsx("p", { className: "text-sm text-muted-foreground text-center py-4", children: "No query history yet. Execute a query to see it here." }

          ) : /*#__PURE__*/

          _jsx("div", { className: "space-y-2 max-h-[400px] overflow-auto", children:
            history.map((item, index) => /*#__PURE__*/
            _jsxs("div", {

              className: "flex items-start justify-between gap-4 p-3 rounded-lg border hover:bg-muted/50 transition-colors", children: [/*#__PURE__*/

              _jsxs("div", { className: "flex-1 min-w-0", children: [/*#__PURE__*/
                _jsxs("div", { className: "flex items-center gap-2 mb-1", children: [/*#__PURE__*/
                  _jsx("span", { className: "text-xs text-muted-foreground", children:
                    new Date(item.timestamp).toLocaleString() }
                  ),
                  item.error ? /*#__PURE__*/
                  _jsx(Badge, { variant: "destructive", className: "text-xs", children: "Error" }) : /*#__PURE__*/

                  _jsxs(Badge, { variant: "outline", className: "text-xs", children: [
                    item.resultCount, " results \xB7 ", item.executionTime, "ms"] }
                  )] }

                ), /*#__PURE__*/
                _jsx("code", { className: "text-xs block truncate", children: item.query }),
                item.error && /*#__PURE__*/
                _jsx("p", { className: "text-xs text-destructive mt-1", children: item.error })] }

              ), /*#__PURE__*/
              _jsxs("div", { className: "flex gap-1", children: [/*#__PURE__*/
                _jsx(Button, {
                  variant: "ghost",
                  size: "sm",
                  onClick: () => copyQuery(item.query), children: /*#__PURE__*/

                  _jsx(Copy, { className: "h-3 w-3" }) }
                ), /*#__PURE__*/
                _jsx(Button, {
                  variant: "ghost",
                  size: "sm",
                  onClick: () => loadQuery(item.query), children: /*#__PURE__*/

                  _jsx(Play, { className: "h-3 w-3" }) }
                )] }
              )] }, index
            )
            ) }
          ) }

        )] }
      )] }
    ));

}
