import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Play, Copy, ChevronRight, Terminal } from 'lucide-react';
import { apiClient } from '@/services/api';
import { toast } from 'sonner';
const API_ENDPOINTS = [{
  method: 'GET',
  path: '/api/health',
  description: 'Health check with database connectivity',
  blueprint: 'System'
}, {
  method: 'GET',
  path: '/api/stats',
  description: 'Get graph statistics',
  blueprint: 'System'
}, {
  method: 'GET',
  path: '/info',
  description: 'API architecture and documentation',
  blueprint: 'System'
}, {
  method: 'GET',
  path: '/api/search',
  description: 'Search across all node types',
  blueprint: 'Core',
  params: [{
    name: 'q',
    type: 'string',
    required: true,
    description: 'Search query'
  }, {
    name: 'limit',
    type: 'number',
    required: false,
    description: 'Max results (default: 50)'
  }]
}, {
  method: 'GET',
  path: '/api/artifacts',
  description: 'List all artifacts',
  blueprint: 'Core',
  params: [{
    name: 'limit',
    type: 'number',
    required: false,
    description: 'Max results'
  }]
}, {
  method: 'GET',
  path: '/api/artifacts/{type}',
  description: 'List artifacts of a specific type',
  blueprint: 'Core',
  params: [{
    name: 'type',
    type: 'string',
    required: true,
    description: 'Artifact type (e.g., Class, Package)'
  }, {
    name: 'limit',
    type: 'number',
    required: false,
    description: 'Max results'
  }]
}, {
  method: 'GET',
  path: '/api/ap239/requirements',
  description: 'List all requirements',
  blueprint: 'AP239'
}, {
  method: 'GET',
  path: '/api/ap239/requirements/{id}',
  description: 'Get requirement details with versions and approvals',
  blueprint: 'AP239',
  params: [{
    name: 'id',
    type: 'string',
    required: true,
    description: 'Requirement ID'
  }]
}, {
  method: 'GET',
  path: '/api/ap239/approvals',
  description: 'List all approvals',
  blueprint: 'AP239'
}, {
  method: 'GET',
  path: '/api/ap242/parts',
  description: 'List all parts with materials and geometry',
  blueprint: 'AP242',
  params: [{
    name: 'search',
    type: 'string',
    required: false,
    description: 'Search by name'
  }]
}, {
  method: 'GET',
  path: '/api/ap242/parts/{id}',
  description: 'Get part details with BOM and materials',
  blueprint: 'AP242',
  params: [{
    name: 'id',
    type: 'string',
    required: true,
    description: 'Part ID'
  }]
}, {
  method: 'GET',
  path: '/api/ap242/materials',
  description: 'List all materials with properties',
  blueprint: 'AP242',
  params: [{
    name: 'search',
    type: 'string',
    required: false,
    description: 'Search by name or specification'
  }]
}, {
  method: 'GET',
  path: '/api/ap243/units',
  description: 'List all measurement units',
  blueprint: 'AP243'
}, {
  method: 'GET',
  path: '/api/ap243/units/{id}',
  description: 'Get unit details',
  blueprint: 'AP243',
  params: [{
    name: 'id',
    type: 'string',
    required: true,
    description: 'Unit ID'
  }]
}, {
  method: 'GET',
  path: '/api/hierarchy/search',
  description: 'Cross-schema search',
  blueprint: 'Hierarchy',
  params: [{
    name: 'query',
    type: 'string',
    required: true,
    description: 'Search query'
  }, {
    name: 'level',
    type: 'number',
    required: false,
    description: 'AP level (239/242/243)'
  }]
}, {
  method: 'GET',
  path: '/api/hierarchy/traceability-matrix',
  description: 'Get full traceability matrix',
  blueprint: 'Hierarchy'
}, {
  method: 'GET',
  path: '/api/hierarchy/trace/{source_type}/{source_id}',
  description: 'Trace relationships from a source node',
  blueprint: 'Hierarchy',
  params: [{
    name: 'source_type',
    type: 'string',
    required: true,
    description: 'Source node type (e.g., Requirement, Part)'
  }, {
    name: 'source_id',
    type: 'string',
    required: true,
    description: 'Source node ID'
  }]
}, {
  method: 'GET',
  path: '/api/v1/{type}',
  description: 'List SMRL resources of a specific type',
  blueprint: 'SMRL v1',
  params: [{
    name: 'type',
    type: 'string',
    required: true,
    description: 'Resource type (e.g., Requirement, Class)'
  }, {
    name: 'limit',
    type: 'number',
    required: false,
    description: 'Max results'
  }, {
    name: 'offset',
    type: 'number',
    required: false,
    description: 'Skip results'
  }]
}, {
  method: 'GET',
  path: '/api/v1/{type}/{uid}',
  description: 'Get a specific SMRL resource by UID',
  blueprint: 'SMRL v1',
  params: [{
    name: 'type',
    type: 'string',
    required: true,
    description: 'Resource type'
  }, {
    name: 'uid',
    type: 'string',
    required: true,
    description: 'Resource UID'
  }]
}, {
  method: 'POST',
  path: '/api/v1/{type}',
  description: 'Create a new SMRL resource',
  blueprint: 'SMRL v1',
  params: [{
    name: 'type',
    type: 'string',
    required: true,
    description: 'Resource type'
  }],
  body: '{\n  "name": "New Resource",\n  "description": "Resource description"\n}'
}, {
  method: 'PUT',
  path: '/api/v1/{type}/{uid}',
  description: 'Update a resource',
  blueprint: 'SMRL v1',
  params: [{
    name: 'type',
    type: 'string',
    required: true,
    description: 'Resource type'
  }, {
    name: 'uid',
    type: 'string',
    required: true,
    description: 'Resource UID'
  }],
  body: '{\n  "name": "Updated Name",\n  "description": "Updated description"\n}'
}, {
  method: 'DELETE',
  path: '/api/v1/{type}/{uid}',
  description: 'Delete a resource',
  blueprint: 'SMRL v1',
  params: [{
    name: 'type',
    type: 'string',
    required: true,
    description: 'Resource type'
  }, {
    name: 'uid',
    type: 'string',
    required: true,
    description: 'Resource UID'
  }]
}, {
  method: 'GET',
  path: '/api/ap239/requirements/{req_id}/traceability',
  description: 'Get requirement traceability links',
  blueprint: 'AP239 Requirements',
  params: [{
    name: 'req_id',
    type: 'string',
    required: true,
    description: 'Requirement ID'
  }]
}, {
  method: 'GET',
  path: '/api/plm/composition/{node_id}',
  description: 'Get Bill of Materials (composition) hierarchy for a node',
  blueprint: 'PLM',
  params: [{
    name: 'node_id',
    type: 'string',
    required: true,
    description: 'Node ID'
  }]
}, {
  method: 'GET',
  path: '/api/plm/impact/{node_id}',
  description: 'Analyze change impact for a node',
  blueprint: 'PLM',
  params: [{
    name: 'node_id',
    type: 'string',
    required: true,
    description: 'Node ID'
  }]
}, {
  method: 'GET',
  path: '/api/simulation/parameters',
  description: 'Extract simulation parameters with metadata (types, defaults, constraints)',
  blueprint: 'Simulation'
}, {
  method: 'GET',
  path: '/api/simulation/units',
  description: 'Get unit types and properties used for simulation integration',
  blueprint: 'Simulation'
}, {
  method: 'POST',
  path: '/api/simulation/validate',
  description: 'Validate parameter values against constraints',
  blueprint: 'Simulation',
  body: '{\n  "parameters": [\n    {\n      "id": "param-123",\n      "value": 100\n    }\n  ]\n}'
}, {
  method: 'POST',
  path: '/api/cypher',
  description: 'Execute Cypher query',
  blueprint: 'Query',
  body: '{\n  "query": "MATCH (n) RETURN n LIMIT 10"\n}'
}, {
  method: 'GET',
  path: '/api/export/schema',
  description: 'Export database schema and metadata',
  blueprint: 'Export'
}, {
  method: 'GET',
  path: '/api/export/graphml',
  description: 'Export graph as GraphML (XML)',
  blueprint: 'Export',
  params: [{
    name: 'node_types',
    type: 'string',
    required: false,
    description: 'Comma separated types'
  }, {
    name: 'limit',
    type: 'number',
    required: false,
    description: 'Max nodes (default 10000)'
  }]
}, {
  method: 'GET',
  path: '/api/export/jsonld',
  description: 'Export graph as JSON-LD (Semantic Linked Data)',
  blueprint: 'Export'
}, {
  method: 'GET',
  path: '/api/export/csv',
  description: 'Export nodes as CSV (ZIP archive)',
  blueprint: 'Export',
  params: [{
    name: 'node_type',
    type: 'string',
    required: false,
    description: 'Specific node type'
  }]
}, {
  method: 'GET',
  path: '/api/export/step',
  description: 'Export as STEP AP242 (CAD/PLM)',
  blueprint: 'Export'
}, {
  method: 'GET',
  path: '/api/export/rdf',
  description: 'Export as RDF/Turtle (Semantic Web)',
  blueprint: 'Export'
}, {
  method: 'GET',
  path: '/api/export/plantuml',
  description: 'Export as PlantUML Class Diagram',
  blueprint: 'Export',
  params: [{
    name: 'package',
    type: 'string',
    required: false,
    description: 'Filter by package name'
  }]
}];
const METHOD_COLORS = {
  GET: 'bg-blue-500',
  POST: 'bg-green-500',
  PUT: 'bg-yellow-500',
  PATCH: 'bg-orange-500',
  DELETE: 'bg-red-500'
};
export default function RestApiExplorer() {
  const [selectedEndpoint, setSelectedEndpoint] = useState(null);
  const [pathParams, setPathParams] = useState({});
  const [queryParams, setQueryParams] = useState({});
  const [requestBody, setRequestBody] = useState('');
  const [response, setResponse] = useState(null);
  const [responseTime, setResponseTime] = useState(null);
  const [error, setError] = useState(null);
  const executeMutation = useMutation({
    mutationFn: async ({
      method,
      url,
      body
    }) => {
      const startTime = Date.now();
      // apiClient is configured with baseURL='/api'. The endpoint catalog in this page
      // includes '/api/...' paths for readability, so strip that prefix to avoid '/api/api/...'.
      if (url?.startsWith('/api/')) {
        url = url.slice(4);
      } else if (url === '/api') {
        url = '/';
      }

      let result;
      switch (method) {
        case 'GET':
          result = await apiClient.get(url);
          break;
        case 'POST':
          result = await apiClient.post(url, body);
          break;
        case 'PUT':
          result = await apiClient.put(url, body);
          break;
        case 'PATCH':
          result = await apiClient.patch(url, body);
          break;
        case 'DELETE':
          result = await apiClient.delete(url);
          break;
        default:
          throw new Error(`Unsupported method: ${method}`);
      }
      const endTime = Date.now();
      return {
        data: result,
        time: endTime - startTime
      };
    },
    onSuccess: result => {
      setResponse(result.data);
      setResponseTime(result.time);
      setError(null);
      toast.success(`Request completed in ${result.time}ms`);
    },
    onError: err => {
      const errorMessage = err.response?.data?.message || err.message || (typeof err === 'string' ? err : 'Request failed');
      setError(errorMessage);
      setResponse(null);
      setResponseTime(null);
      toast.error('Request failed');
    }
  });
  const handleSelectEndpoint = endpoint => {
    setSelectedEndpoint(endpoint);
    setPathParams({});
    setQueryParams({});
    setRequestBody(endpoint.body || '');
    setResponse(null);
    setError(null);
    setResponseTime(null);
  };
  const handleExecute = () => {
    if (!selectedEndpoint) return;
    let url = selectedEndpoint.path;
    Object.entries(pathParams).forEach(([key, value]) => {
      url = url.replace(`{${key}}`, encodeURIComponent(value));
    });
    const params = new URLSearchParams();
    Object.entries(queryParams).forEach(([key, value]) => {
      if (value) params.append(key, value);
    });
    if (params.toString()) {
      url += '?' + params.toString();
    }
    let body = undefined;
    if (requestBody && (selectedEndpoint.method === 'POST' || selectedEndpoint.method === 'PUT' || selectedEndpoint.method === 'PATCH')) {
      try {
        body = JSON.parse(requestBody);
      } catch (e) {
        toast.error('Invalid JSON in request body');
        return;
      }
    }
    executeMutation.mutate({
      method: selectedEndpoint.method,
      url,
      body
    });
  };
  const copyResponse = () => {
    if (response) {
      navigator.clipboard.writeText(JSON.stringify(response, null, 2));
      toast.success('Response copied to clipboard');
    }
  };
  const groupedEndpoints = API_ENDPOINTS.reduce((acc, endpoint) => {
    if (!acc[endpoint.blueprint]) {
      acc[endpoint.blueprint] = [];
    }
    acc[endpoint.blueprint].push(endpoint);
    return acc;
  }, {});
  const pathParamKeys = selectedEndpoint?.path.match(/\{([^}]+)\}/g)?.map(p => p.slice(1, -1)) || [];
  const queryParamKeys = selectedEndpoint?.params?.filter(p => !pathParamKeys.includes(p.name) && p.name !== 'type' && p.name !== 'uid' && p.name !== 'id' && p.name !== 'partId' && p.name !== 'req_id' && p.name !== 'node_id') || [];
  return <div className="space-y-6"><div className="border-b pb-6"><div className="flex items-center gap-4 mb-2"><div className="h-12 w-12 rounded-lg bg-gradient-primary flex items-center justify-center"><Terminal className="h-6 w-6 text-white" /></div><div><h1 className="text-3xl font-bold tracking-tight">REST API Documentation</h1><p className="text-sm text-muted-foreground">OpenAPI 3.0 Compatible Interface</p></div></div><div className="flex gap-2 mt-4"><Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">API v1.0</Badge><Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">ISO 10303 SMRL</Badge><Badge variant="outline">Base: /api</Badge></div></div><div className="grid grid-cols-1 gap-4"><div className="space-y-2"><div className="text-sm font-semibold text-muted-foreground mb-4">{API_ENDPOINTS.length} Operations</div><Accordion type="single" collapsible className="w-full space-y-2">{Object.entries(groupedEndpoints).map(([blueprint, endpoints]) => <AccordionItem key={blueprint} value={blueprint} className="border rounded-lg"><AccordionTrigger className="px-4 hover:no-underline hover:bg-muted/50"><div className="flex items-center justify-between w-full"><span className="font-semibold text-base">{blueprint}</span><Badge variant="secondary" className="ml-2">{endpoints.length} endpoints</Badge></div></AccordionTrigger><AccordionContent className="px-4 pb-4"><div className="space-y-2 mt-2">{endpoints.map((endpoint, index) => <Card key={`${endpoint.method}:${endpoint.path}`} className={`cursor-pointer transition-all hover:shadow-md ${selectedEndpoint === endpoint ? 'ring-2 ring-primary shadow-md' : ''}`} onClick={() => handleSelectEndpoint(endpoint)}><CardContent className="p-4"><div className="flex items-start gap-3"><Badge className={`${METHOD_COLORS[endpoint.method]} text-white text-xs font-bold shrink-0 mt-0.5`}>{endpoint.method}</Badge><div className="flex-1 min-w-0"><code className="text-sm font-mono font-semibold block mb-1">{endpoint.path}</code><p className="text-xs text-muted-foreground">{endpoint.description}</p></div><ChevronRight className="h-4 w-4 text-muted-foreground shrink-0 mt-1" /></div></CardContent></Card>)}</div></AccordionContent></AccordionItem>)}</Accordion></div>{selectedEndpoint && <Card className="border-2 border-primary/20 shadow-lg"><CardHeader className="border-b bg-muted/30"><div className="flex items-center justify-between"><div className="flex items-center gap-3"><Badge className={`${METHOD_COLORS[selectedEndpoint.method]} text-white font-bold px-3 py-1`}>{selectedEndpoint.method}</Badge><div><code className="text-base font-mono font-semibold">{selectedEndpoint.path}</code><p className="text-sm text-muted-foreground mt-1">{selectedEndpoint.description}</p></div></div><Badge variant="outline" className="bg-blue-50 text-blue-700">Try it out</Badge></div></CardHeader><CardContent className="space-y-4">{pathParamKeys.length > 0 && <div className="space-y-2"><Label className="text-sm font-semibold">Path Parameters</Label>{pathParamKeys.map(param => <div key={param}><Label htmlFor={param} className="text-xs">{param} <span className="text-destructive">*</span></Label><Input id={param} value={pathParams[param] || ''} onChange={e => setPathParams({
                ...pathParams,
                [param]: e.target.value
              })} placeholder={`Enter ${param}`} /></div>)}</div>}{queryParamKeys.length > 0 && <div className="space-y-2"><Label className="text-sm font-semibold">Query Parameters</Label>{queryParamKeys.map(param => <div key={param.name}><Label htmlFor={param.name} className="text-xs">{param.name}{param.required && <span className="text-destructive"> *</span>}</Label><Input id={param.name} value={queryParams[param.name] || ''} onChange={e => setQueryParams({
                ...queryParams,
                [param.name]: e.target.value
              })} placeholder={param.description} /></div>)}</div>}{(selectedEndpoint.method === 'POST' || selectedEndpoint.method === 'PUT' || selectedEndpoint.method === 'PATCH') && <div className="space-y-2"><Label className="text-sm font-semibold">Request Body (JSON)</Label><Textarea value={requestBody} onChange={e => setRequestBody(e.target.value)} placeholder="Enter JSON request body" rows={8} className="font-mono text-xs" /></div>}<Button onClick={handleExecute} disabled={executeMutation.isPending} className="w-full"><Play className="h-4 w-4 mr-2" />{executeMutation.isPending ? 'Executing...' : 'Send Request'}</Button>{(response || error) && <Tabs defaultValue="response" className="w-full"><div className="flex items-center justify-between mb-2"><TabsList><TabsTrigger value="response">Response</TabsTrigger><TabsTrigger value="headers">Headers</TabsTrigger></TabsList><div className="flex items-center gap-2">{responseTime && <Badge variant="outline">{responseTime}ms</Badge>}{response && <Button variant="ghost" size="sm" onClick={copyResponse}><Copy className="h-4 w-4" /></Button>}</div></div><TabsContent value="response" className="mt-0">{error ? <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert> : <div className="rounded-md border p-4 bg-muted/50 max-h-[400px] overflow-auto"><pre className="text-xs font-mono">{JSON.stringify(response, null, 2)}</pre></div>}</TabsContent><TabsContent value="headers" className="mt-0"><div className="rounded-md border p-4 bg-muted/50"><pre className="text-xs font-mono">{JSON.stringify({
                    'Content-Type': 'application/json',
                    'X-Response-Time': `${responseTime}ms`
                  }, null, 2)}</pre></div></TabsContent></Tabs>}</CardContent></Card>}</div></div>;
}
