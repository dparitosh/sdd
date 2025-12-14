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







import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger } from
'@/components/ui/accordion';
import { Play, Copy, ChevronRight, Terminal } from 'lucide-react';
import { apiClient } from '@/services/api';
import { toast } from 'sonner';import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";










const API_ENDPOINTS = [
// System
{
  method: 'GET',
  path: '/api/health',
  description: 'Health check with database connectivity',
  blueprint: 'System'
},
{
  method: 'GET',
  path: '/api/stats',
  description: 'Get graph statistics',
  blueprint: 'System'
},
{
  method: 'GET',
  path: '/info',
  description: 'API architecture and documentation',
  blueprint: 'System'
},

// Core API
{
  method: 'GET',
  path: '/api/search',
  description: 'Search across all node types',
  blueprint: 'Core',
  params: [
  { name: 'q', type: 'string', required: true, description: 'Search query' },
  { name: 'limit', type: 'number', required: false, description: 'Max results (default: 50)' }]

},
{
  method: 'GET',
  path: '/api/artifacts',
  description: 'List all artifacts',
  blueprint: 'Core',
  params: [
  { name: 'limit', type: 'number', required: false, description: 'Max results' }]

},
{
  method: 'GET',
  path: '/api/artifacts/{type}',
  description: 'List artifacts of a specific type',
  blueprint: 'Core',
  params: [
  { name: 'type', type: 'string', required: true, description: 'Artifact type (e.g., Class, Package)' },
  { name: 'limit', type: 'number', required: false, description: 'Max results' }]

},

// AP239 - Product Life Cycle Support (PLCS)
{
  method: 'GET',
  path: '/api/ap239/requirements',
  description: 'List all requirements',
  blueprint: 'AP239'
},
{
  method: 'GET',
  path: '/api/ap239/requirements/{id}',
  description: 'Get requirement details with versions and approvals',
  blueprint: 'AP239',
  params: [
  { name: 'id', type: 'string', required: true, description: 'Requirement ID' }]

},
{
  method: 'GET',
  path: '/api/ap239/approvals',
  description: 'List all approvals',
  blueprint: 'AP239'
},

// AP242 - 3D Engineering
{
  method: 'GET',
  path: '/api/ap242/parts',
  description: 'List all parts with materials and geometry',
  blueprint: 'AP242',
  params: [
  { name: 'search', type: 'string', required: false, description: 'Search by name' }]

},
{
  method: 'GET',
  path: '/api/ap242/parts/{id}',
  description: 'Get part details with BOM and materials',
  blueprint: 'AP242',
  params: [
  { name: 'id', type: 'string', required: true, description: 'Part ID' }]

},
{
  method: 'GET',
  path: '/api/ap242/materials',
  description: 'List all materials with properties',
  blueprint: 'AP242',
  params: [
  { name: 'search', type: 'string', required: false, description: 'Search by name or specification' }]

},

// AP243 - Reference Data
{
  method: 'GET',
  path: '/api/ap243/units',
  description: 'List all measurement units',
  blueprint: 'AP243'
},
{
  method: 'GET',
  path: '/api/ap243/units/{id}',
  description: 'Get unit details',
  blueprint: 'AP243',
  params: [
  { name: 'id', type: 'string', required: true, description: 'Unit ID' }]

},

// Hierarchy Navigation
{
  method: 'GET',
  path: '/api/hierarchy/search',
  description: 'Cross-schema search',
  blueprint: 'Hierarchy',
  params: [
  { name: 'query', type: 'string', required: true, description: 'Search query' },
  { name: 'level', type: 'number', required: false, description: 'AP level (239/242/243)' }]

},
{
  method: 'GET',
  path: '/api/hierarchy/traceability-matrix',
  description: 'Get full traceability matrix',
  blueprint: 'Hierarchy'
},
{
  method: 'GET',
  path: '/api/hierarchy/trace/{source_type}/{source_id}',
  description: 'Trace relationships from a source node',
  blueprint: 'Hierarchy',
  params: [
  { name: 'source_type', type: 'string', required: true, description: 'Source node type (e.g., Requirement, Part)' },
  { name: 'source_id', type: 'string', required: true, description: 'Source node ID' }]

},

// SMRL v1 API
{
  method: 'GET',
  path: '/api/v1/{type}',
  description: 'List SMRL resources of a specific type',
  blueprint: 'SMRL v1',
  params: [
  { name: 'type', type: 'string', required: true, description: 'Resource type (e.g., Requirement, Class)' },
  { name: 'limit', type: 'number', required: false, description: 'Max results' },
  { name: 'offset', type: 'number', required: false, description: 'Skip results' }]

},
{
  method: 'GET',
  path: '/api/v1/{type}/{uid}',
  description: 'Get a specific SMRL resource by UID',
  blueprint: 'SMRL v1',
  params: [
  { name: 'type', type: 'string', required: true, description: 'Resource type' },
  { name: 'uid', type: 'string', required: true, description: 'Resource UID' }]

},
{
  method: 'POST',
  path: '/api/v1/{type}',
  description: 'Create a new SMRL resource',
  blueprint: 'SMRL v1',
  params: [
  { name: 'type', type: 'string', required: true, description: 'Resource type' }],

  body: '{\n  "name": "New Resource",\n  "description": "Resource description"\n}'
},
{
  method: 'PUT',
  path: '/v1/{type}/{uid}',
  description: 'Update a resource',
  blueprint: 'SMRL v1',
  params: [
  { name: 'type', type: 'string', required: true, description: 'Resource type' },
  { name: 'uid', type: 'string', required: true, description: 'Resource UID' }],

  body: '{\n  "name": "Updated Name",\n  "description": "Updated description"\n}'
},
{
  method: 'DELETE',
  path: '/v1/{type}/{uid}',
  description: 'Delete a resource',
  blueprint: 'SMRL v1',
  params: [
  { name: 'type', type: 'string', required: true, description: 'Resource type' },
  { name: 'uid', type: 'string', required: true, description: 'Resource UID' }]

},

// Requirements (AP239)
{
  method: 'GET',
  path: '/ap239/requirements/{uid}/traceability',
  description: 'Get requirement traceability links',
  blueprint: 'AP239 Requirements',
  params: [
  { name: 'uid', type: 'string', required: true, description: 'Requirement UID' }]

},

// PLM Operations
{
  method: 'GET',
  path: '/plm/bom/{partId}',
  description: 'Get Bill of Materials for a part',
  blueprint: 'PLM',
  params: [
  { name: 'partId', type: 'string', required: true, description: 'Part ID' }]

},
{
  method: 'GET',
  path: '/plm/change-impact/{partId}',
  description: 'Analyze change impact for a part',
  blueprint: 'PLM',
  params: [
  { name: 'partId', type: 'string', required: true, description: 'Part ID' }]

},

// Simulation
{
  method: 'GET',
  path: '/simulation/models',
  description: 'List simulation models',
  blueprint: 'Simulation'
},
{
  method: 'GET',
  path: '/simulation/models/{id}',
  description: 'Get simulation model details',
  blueprint: 'Simulation',
  params: [
  { name: 'id', type: 'string', required: true, description: 'Model ID' }]

},
{
  method: 'POST',
  path: '/simulation/run',
  description: 'Run a simulation',
  blueprint: 'Simulation',
  body: '{\n  "modelId": "model-123",\n  "parameters": {\n    "param1": 100,\n    "param2": 200\n  }\n}'
},

// Query
{
  method: 'POST',
  path: '/cypher',
  description: 'Execute Cypher query',
  blueprint: 'Query',
  body: '{\n  "query": "MATCH (n) RETURN n LIMIT 10"\n}'
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
      return { data: result.data, time: endTime - startTime };
    },
    onSuccess: (result) => {
      setResponse(result.data);
      setResponseTime(result.time);
      setError(null);
      toast.success(`Request completed in ${result.time}ms`);
    },
    onError: (err) => {
      const errorMessage = err.response?.data?.message || err.message || (typeof err === 'string' ? err : 'Request failed');
      setError(errorMessage);
      setResponse(null);
      setResponseTime(null);
      toast.error('Request failed');
    }
  });

  const handleSelectEndpoint = (endpoint) => {
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

    // Build URL with path params
    let url = selectedEndpoint.path;
    Object.entries(pathParams).forEach(([key, value]) => {
      url = url.replace(`{${key}}`, encodeURIComponent(value));
    });

    // Add query params
    const params = new URLSearchParams();
    Object.entries(queryParams).forEach(([key, value]) => {
      if (value) params.append(key, value);
    });
    if (params.toString()) {
      url += '?' + params.toString();
    }

    // Parse body
    let body = undefined;
    if (requestBody && (selectedEndpoint.method === 'POST' || selectedEndpoint.method === 'PUT' || selectedEndpoint.method === 'PATCH')) {
      try {
        body = JSON.parse(requestBody);
      } catch (e) {
        toast.error('Invalid JSON in request body');
        return;
      }
    }

    executeMutation.mutate({ method: selectedEndpoint.method, url, body });
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

  const pathParamKeys = selectedEndpoint?.path.match(/\{([^}]+)\}/g)?.map((p) => p.slice(1, -1)) || [];
  const queryParamKeys = selectedEndpoint?.params?.filter((p) => p.name !== 'type' && p.name !== 'uid' && p.name !== 'id' && p.name !== 'partId') || [];

  return (/*#__PURE__*/
    _jsxs("div", { className: "space-y-6", children: [/*#__PURE__*/

      _jsxs("div", { className: "border-b pb-6", children: [/*#__PURE__*/
        _jsxs("div", { className: "flex items-center gap-4 mb-2", children: [/*#__PURE__*/
          _jsx("div", { className: "h-12 w-12 rounded-lg bg-gradient-primary flex items-center justify-center", children: /*#__PURE__*/
            _jsx(Terminal, { className: "h-6 w-6 text-white" }) }
          ), /*#__PURE__*/
          _jsxs("div", { children: [/*#__PURE__*/
            _jsx("h1", { className: "text-3xl font-bold tracking-tight", children: "REST API Documentation" }), /*#__PURE__*/
            _jsx("p", { className: "text-sm text-muted-foreground", children: "OpenAPI 3.0 Compatible Interface" })] }
          )] }
        ), /*#__PURE__*/
        _jsxs("div", { className: "flex gap-2 mt-4", children: [/*#__PURE__*/
          _jsx(Badge, { variant: "outline", className: "bg-blue-50 text-blue-700 border-blue-200", children: "API v1.0" }), /*#__PURE__*/
          _jsx(Badge, { variant: "outline", className: "bg-green-50 text-green-700 border-green-200", children: "ISO 10303 SMRL" }), /*#__PURE__*/
          _jsx(Badge, { variant: "outline", children: "Base: /api" })] }
        )] }
      ), /*#__PURE__*/

      _jsxs("div", { className: "grid grid-cols-1 gap-4", children: [/*#__PURE__*/

        _jsxs("div", { className: "space-y-2", children: [/*#__PURE__*/
          _jsxs("div", { className: "text-sm font-semibold text-muted-foreground mb-4", children: [
            API_ENDPOINTS.length, " Operations"] }
          ), /*#__PURE__*/
          _jsx(Accordion, { type: "single", collapsible: true, className: "w-full space-y-2", children:
            Object.entries(groupedEndpoints).map(([blueprint, endpoints]) => /*#__PURE__*/
            _jsxs(AccordionItem, { value: blueprint, className: "border rounded-lg", children: [/*#__PURE__*/
              _jsx(AccordionTrigger, { className: "px-4 hover:no-underline hover:bg-muted/50", children: /*#__PURE__*/
                _jsxs("div", { className: "flex items-center justify-between w-full", children: [/*#__PURE__*/
                  _jsx("span", { className: "font-semibold text-base", children: blueprint }), /*#__PURE__*/
                  _jsxs(Badge, { variant: "secondary", className: "ml-2", children: [
                    endpoints.length, " endpoints"] }
                  )] }
                ) }
              ), /*#__PURE__*/
              _jsx(AccordionContent, { className: "px-4 pb-4", children: /*#__PURE__*/
                _jsx("div", { className: "space-y-2 mt-2", children:
                  endpoints.map((endpoint, index) => /*#__PURE__*/
                  _jsx(Card, {

                    className: `cursor-pointer transition-all hover:shadow-md ${
                    selectedEndpoint === endpoint ? 'ring-2 ring-primary shadow-md' : ''}`,

                    onClick: () => handleSelectEndpoint(endpoint), children: /*#__PURE__*/

                    _jsx(CardContent, { className: "p-4", children: /*#__PURE__*/
                      _jsxs("div", { className: "flex items-start gap-3", children: [/*#__PURE__*/
                        _jsx(Badge, {
                          className: `${METHOD_COLORS[endpoint.method]} text-white text-xs font-bold shrink-0 mt-0.5`, children:

                          endpoint.method }
                        ), /*#__PURE__*/
                        _jsxs("div", { className: "flex-1 min-w-0", children: [/*#__PURE__*/
                          _jsx("code", { className: "text-sm font-mono font-semibold block mb-1", children: endpoint.path }), /*#__PURE__*/
                          _jsx("p", { className: "text-xs text-muted-foreground", children:
                            endpoint.description }
                          )] }
                        ), /*#__PURE__*/
                        _jsx(ChevronRight, { className: "h-4 w-4 text-muted-foreground shrink-0 mt-1" })] }
                      ) }
                    ) }, index
                  )
                  ) }
                ) }
              )] }, blueprint
            )
            ) }
          )] }
        ),


        selectedEndpoint && /*#__PURE__*/
        _jsxs(Card, { className: "border-2 border-primary/20 shadow-lg", children: [/*#__PURE__*/
          _jsx(CardHeader, { className: "border-b bg-muted/30", children: /*#__PURE__*/
            _jsxs("div", { className: "flex items-center justify-between", children: [/*#__PURE__*/
              _jsxs("div", { className: "flex items-center gap-3", children: [/*#__PURE__*/
                _jsx(Badge, { className: `${METHOD_COLORS[selectedEndpoint.method]} text-white font-bold px-3 py-1`, children:
                  selectedEndpoint.method }
                ), /*#__PURE__*/
                _jsxs("div", { children: [/*#__PURE__*/
                  _jsx("code", { className: "text-base font-mono font-semibold", children: selectedEndpoint.path }), /*#__PURE__*/
                  _jsx("p", { className: "text-sm text-muted-foreground mt-1", children: selectedEndpoint.description })] }
                )] }
              ), /*#__PURE__*/
              _jsx(Badge, { variant: "outline", className: "bg-blue-50 text-blue-700", children: "Try it out" })] }
            ) }
          ), /*#__PURE__*/
          _jsxs(CardContent, { className: "space-y-4", children: [

            pathParamKeys.length > 0 && /*#__PURE__*/
            _jsxs("div", { className: "space-y-2", children: [/*#__PURE__*/
              _jsx(Label, { className: "text-sm font-semibold", children: "Path Parameters" }),
              pathParamKeys.map((param) => /*#__PURE__*/
              _jsxs("div", { children: [/*#__PURE__*/
                _jsxs(Label, { htmlFor: param, className: "text-xs", children: [
                  param, " ", /*#__PURE__*/_jsx("span", { className: "text-destructive", children: "*" })] }
                ), /*#__PURE__*/
                _jsx(Input, {
                  id: param,
                  value: pathParams[param] || '',
                  onChange: (e) => setPathParams({ ...pathParams, [param]: e.target.value }),
                  placeholder: `Enter ${param}` }
                )] }, param
              )
              )] }
            ),



            queryParamKeys.length > 0 && /*#__PURE__*/
            _jsxs("div", { className: "space-y-2", children: [/*#__PURE__*/
              _jsx(Label, { className: "text-sm font-semibold", children: "Query Parameters" }),
              queryParamKeys.map((param) => /*#__PURE__*/
              _jsxs("div", { children: [/*#__PURE__*/
                _jsxs(Label, { htmlFor: param.name, className: "text-xs", children: [
                  param.name,
                  param.required && /*#__PURE__*/_jsx("span", { className: "text-destructive", children: " *" })] }
                ), /*#__PURE__*/
                _jsx(Input, {
                  id: param.name,
                  value: queryParams[param.name] || '',
                  onChange: (e) => setQueryParams({ ...queryParams, [param.name]: e.target.value }),
                  placeholder: param.description }
                )] }, param.name
              )
              )] }
            ),



            (selectedEndpoint.method === 'POST' || selectedEndpoint.method === 'PUT' || selectedEndpoint.method === 'PATCH') && /*#__PURE__*/
            _jsxs("div", { className: "space-y-2", children: [/*#__PURE__*/
              _jsx(Label, { className: "text-sm font-semibold", children: "Request Body (JSON)" }), /*#__PURE__*/
              _jsx(Textarea, {
                value: requestBody,
                onChange: (e) => setRequestBody(e.target.value),
                placeholder: "Enter JSON request body",
                rows: 8,
                className: "font-mono text-xs" }
              )] }
            ), /*#__PURE__*/



            _jsxs(Button, {
              onClick: handleExecute,
              disabled: executeMutation.isPending,
              className: "w-full", children: [/*#__PURE__*/

              _jsx(Play, { className: "h-4 w-4 mr-2" }),
              executeMutation.isPending ? 'Executing...' : 'Send Request'] }
            ),


            (response || error) && /*#__PURE__*/
            _jsxs(Tabs, { defaultValue: "response", className: "w-full", children: [/*#__PURE__*/
              _jsxs("div", { className: "flex items-center justify-between mb-2", children: [/*#__PURE__*/
                _jsxs(TabsList, { children: [/*#__PURE__*/
                  _jsx(TabsTrigger, { value: "response", children: "Response" }), /*#__PURE__*/
                  _jsx(TabsTrigger, { value: "headers", children: "Headers" })] }
                ), /*#__PURE__*/
                _jsxs("div", { className: "flex items-center gap-2", children: [
                  responseTime && /*#__PURE__*/
                  _jsxs(Badge, { variant: "outline", children: [responseTime, "ms"] }),

                  response && /*#__PURE__*/
                  _jsx(Button, { variant: "ghost", size: "sm", onClick: copyResponse, children: /*#__PURE__*/
                    _jsx(Copy, { className: "h-4 w-4" }) }
                  )] }

                )] }
              ), /*#__PURE__*/
              _jsx(TabsContent, { value: "response", className: "mt-0", children:
                error ? /*#__PURE__*/
                _jsx(Alert, { variant: "destructive", children: /*#__PURE__*/
                  _jsx(AlertDescription, { children: error }) }
                ) : /*#__PURE__*/

                _jsx("div", { className: "rounded-md border p-4 bg-muted/50 max-h-[400px] overflow-auto", children: /*#__PURE__*/
                  _jsx("pre", { className: "text-xs font-mono", children:
                    JSON.stringify(response, null, 2) }
                  ) }
                ) }

              ), /*#__PURE__*/
              _jsx(TabsContent, { value: "headers", className: "mt-0", children: /*#__PURE__*/
                _jsx("div", { className: "rounded-md border p-4 bg-muted/50", children: /*#__PURE__*/
                  _jsx("pre", { className: "text-xs font-mono", children:
                    JSON.stringify(
                      {
                        'Content-Type': 'application/json',
                        'X-Response-Time': `${responseTime}ms`
                      },
                      null,
                      2
                    ) }
                  ) }
                ) }
              )] }
            )] }

          )] }
        )] }

      )] }
    ));

}
