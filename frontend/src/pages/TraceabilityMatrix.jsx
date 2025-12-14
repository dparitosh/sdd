import logger from '@/utils/logger';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue } from
'@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Download, RefreshCw, Search, CheckCircle2, AlertCircle, XCircle, GitBranch } from 'lucide-react';
import { apiService } from '@/services/api';
import { toast } from 'sonner';
import PageHeader from '@/components/PageHeader';import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
















const TRACE_STATUS_COLORS = {
  satisfied: 'bg-green-100 text-green-800 hover:bg-green-200',
  partial: 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200',
  missing: 'bg-red-100 text-red-800 hover:bg-red-200',
  unknown: 'bg-gray-100 text-gray-800 hover:bg-gray-200'
};

const TRACE_STATUS_ICONS = {
  satisfied: CheckCircle2,
  partial: AlertCircle,
  missing: XCircle,
  unknown: AlertCircle
};

export default function TraceabilityMatrix() {
  const [filter, setFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  // Fetch requirements
  const { data: requirements = [], isLoading: reqLoading } = useQuery({
    queryKey: ['requirements-traceability'],
    queryFn: async () => {
      const response = await apiService.requirements.list({ limit: 1000 });
      return response.data || [];
    }
  });

  // Fetch traceability data for all requirements
  const { data: traceabilityData = [], isLoading: traceLoading, refetch } = useQuery({
    queryKey: ['traceability-all', requirements],
    queryFn: async () => {
      const traces = [];

      for (const req of requirements.slice(0, 50)) {// Limit to first 50 for performance
        try {
          const response = await apiService.requirements.getTraceability(req.uid);
          const links = response.data || [];

          links.forEach((link) => {
            traces.push({
              requirement: {
                uid: req.uid,
                name: req.name,
                status: req.status
              },
              target: {
                uid: link.target?.uid || link.uid,
                name: link.target?.name || link.name,
                type: link.target?.type || link.type || 'Unknown'
              },
              relationship: link.relationship || 'traces',
              satisfied: link.satisfied !== false
            });
          });
        } catch (error) {
          logger.error(`Failed to fetch traceability for ${req.uid}:`, error);
        }
      }

      return traces;
    },
    enabled: requirements.length > 0
  });

  const isLoading = reqLoading || traceLoading;

  // Filter data
  const filteredData = traceabilityData.filter((link) => {
    const matchesFilter =
    filter === '' ||
    link.requirement.name.toLowerCase().includes(filter.toLowerCase()) ||
    link.target.name.toLowerCase().includes(filter.toLowerCase());

    const matchesStatus =
    statusFilter === 'all' ||
    statusFilter === 'satisfied' && link.satisfied ||
    statusFilter === 'missing' && !link.satisfied;

    return matchesFilter && matchesStatus;
  });

  // Group by requirement
  const groupedData = filteredData.reduce((acc, link) => {
    if (!acc[link.requirement.uid]) {
      acc[link.requirement.uid] = {
        requirement: link.requirement,
        targets: []
      };
    }
    acc[link.requirement.uid].targets.push(link);
    return acc;
  }, {});

  // Statistics
  const totalRequirements = Object.keys(groupedData).length;
  const totalLinks = filteredData.length;
  const satisfiedLinks = filteredData.filter((l) => l.satisfied).length;
  const missingLinks = filteredData.filter((l) => !l.satisfied).length;
  const coverage = totalLinks > 0 ? (satisfiedLinks / totalLinks * 100).toFixed(1) : '0';

  const exportToCSV = () => {
    const headers = ['Requirement UID', 'Requirement Name', 'Target Type', 'Target UID', 'Target Name', 'Relationship', 'Status'];
    const rows = filteredData.map((link) => [
    link.requirement.uid,
    link.requirement.name,
    link.target.type,
    link.target.uid,
    link.target.name,
    link.relationship,
    link.satisfied ? 'Satisfied' : 'Missing']
    );

    const csv = [headers, ...rows].map((row) => row.map((cell) => `"${cell}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `traceability_matrix_${new Date().toISOString()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Traceability matrix exported to CSV');
  };

  return (/*#__PURE__*/
    _jsxs("div", { className: "container mx-auto p-6 space-y-6", children: [/*#__PURE__*/
      _jsx(PageHeader, {
        title: "Traceability Matrix",
        description: "Visualize and analyze requirement traceability relationships",
        icon: /*#__PURE__*/_jsx(GitBranch, { className: "h-6 w-6 text-primary" }),
        breadcrumbs: [
        { label: 'Knowledge Graph', href: '/graph' },
        { label: 'Traceability Matrix' }],

        actions: /*#__PURE__*/
        _jsxs("div", { className: "flex gap-2", children: [/*#__PURE__*/
          _jsxs(Button, { variant: "outline", onClick: () => refetch(), children: [/*#__PURE__*/
            _jsx(RefreshCw, { className: "h-4 w-4 mr-2" }), "Refresh"] }

          ), /*#__PURE__*/
          _jsxs(Button, { variant: "outline", onClick: exportToCSV, disabled: filteredData.length === 0, children: [/*#__PURE__*/
            _jsx(Download, { className: "h-4 w-4 mr-2" }), "Export CSV"] }

          )] }
        ) }

      ), /*#__PURE__*/


      _jsxs("div", { className: "grid grid-cols-1 md:grid-cols-4 gap-4", children: [/*#__PURE__*/
        _jsxs(Card, { children: [/*#__PURE__*/
          _jsx(CardHeader, { className: "pb-2", children: /*#__PURE__*/
            _jsx(CardTitle, { className: "text-sm font-medium text-muted-foreground", children: "Total Requirements" }

            ) }
          ), /*#__PURE__*/
          _jsx(CardContent, { children: /*#__PURE__*/
            _jsx("div", { className: "text-2xl font-bold", children: totalRequirements }) }
          )] }
        ), /*#__PURE__*/
        _jsxs(Card, { children: [/*#__PURE__*/
          _jsx(CardHeader, { className: "pb-2", children: /*#__PURE__*/
            _jsx(CardTitle, { className: "text-sm font-medium text-muted-foreground", children: "Total Links" }

            ) }
          ), /*#__PURE__*/
          _jsx(CardContent, { children: /*#__PURE__*/
            _jsx("div", { className: "text-2xl font-bold", children: totalLinks }) }
          )] }
        ), /*#__PURE__*/
        _jsxs(Card, { children: [/*#__PURE__*/
          _jsx(CardHeader, { className: "pb-2", children: /*#__PURE__*/
            _jsx(CardTitle, { className: "text-sm font-medium text-muted-foreground", children: "Satisfied Links" }

            ) }
          ), /*#__PURE__*/
          _jsx(CardContent, { children: /*#__PURE__*/
            _jsx("div", { className: "text-2xl font-bold text-green-600", children: satisfiedLinks }) }
          )] }
        ), /*#__PURE__*/
        _jsxs(Card, { children: [/*#__PURE__*/
          _jsx(CardHeader, { className: "pb-2", children: /*#__PURE__*/
            _jsx(CardTitle, { className: "text-sm font-medium text-muted-foreground", children: "Coverage" }

            ) }
          ), /*#__PURE__*/
          _jsx(CardContent, { children: /*#__PURE__*/
            _jsxs("div", { className: "text-2xl font-bold", children: [coverage, "%"] }) }
          )] }
        )] }
      ), /*#__PURE__*/


      _jsxs(Card, { children: [/*#__PURE__*/
        _jsx(CardHeader, { children: /*#__PURE__*/
          _jsx(CardTitle, { children: "Filters" }) }
        ), /*#__PURE__*/
        _jsx(CardContent, { children: /*#__PURE__*/
          _jsxs("div", { className: "grid grid-cols-1 md:grid-cols-2 gap-4", children: [/*#__PURE__*/
            _jsxs("div", { children: [/*#__PURE__*/
              _jsx(Label, { htmlFor: "search", children: "Search" }), /*#__PURE__*/
              _jsxs("div", { className: "relative", children: [/*#__PURE__*/
                _jsx(Search, { className: "absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" }), /*#__PURE__*/
                _jsx(Input, {
                  id: "search",
                  placeholder: "Search requirements or targets...",
                  value: filter,
                  onChange: (e) => setFilter(e.target.value),
                  className: "pl-10" }
                )] }
              )] }
            ), /*#__PURE__*/
            _jsxs("div", { children: [/*#__PURE__*/
              _jsx(Label, { htmlFor: "status-filter", children: "Status Filter" }), /*#__PURE__*/
              _jsxs(Select, { value: statusFilter, onValueChange: setStatusFilter, children: [/*#__PURE__*/
                _jsx(SelectTrigger, { id: "status-filter", children: /*#__PURE__*/
                  _jsx(SelectValue, {}) }
                ), /*#__PURE__*/
                _jsxs(SelectContent, { children: [/*#__PURE__*/
                  _jsx(SelectItem, { value: "all", children: "All Status" }), /*#__PURE__*/
                  _jsx(SelectItem, { value: "satisfied", children: "Satisfied Only" }), /*#__PURE__*/
                  _jsx(SelectItem, { value: "missing", children: "Missing Only" })] }
                )] }
              )] }
            )] }
          ) }
        )] }
      ), /*#__PURE__*/


      _jsxs(Card, { children: [/*#__PURE__*/
        _jsxs(CardHeader, { children: [/*#__PURE__*/
          _jsx(CardTitle, { children: "Traceability Links" }), /*#__PURE__*/
          _jsxs(CardDescription, { children: ["Showing ",
            filteredData.length, " traceability links"] }
          )] }
        ), /*#__PURE__*/
        _jsx(CardContent, { children:
          isLoading ? /*#__PURE__*/
          _jsx("div", { className: "space-y-4", children:
            Array.from({ length: 5 }).map((_, i) => /*#__PURE__*/
            _jsx(Skeleton, { className: "h-24 w-full" }, i)
            ) }
          ) :
          Object.keys(groupedData).length === 0 ? /*#__PURE__*/
          _jsx(Alert, { children: /*#__PURE__*/
            _jsx(AlertDescription, { children: "No traceability data found. Make sure requirements have relationships defined in the database." }

            ) }
          ) : /*#__PURE__*/

          _jsx("div", { className: "space-y-4 max-h-[600px] overflow-auto", children:
            Object.values(groupedData).map(({ requirement, targets }) => /*#__PURE__*/
            _jsxs("div", {

              className: "border rounded-lg p-4 hover:bg-muted/50 transition-colors", children: [/*#__PURE__*/

              _jsxs("div", { className: "flex items-start justify-between mb-3", children: [/*#__PURE__*/
                _jsxs("div", { children: [/*#__PURE__*/
                  _jsx("div", { className: "font-semibold text-sm", children: requirement.name }), /*#__PURE__*/
                  _jsx("div", { className: "text-xs text-muted-foreground font-mono mt-1", children:
                    requirement.uid }
                  )] }
                ),
                requirement.status && /*#__PURE__*/
                _jsx(Badge, { variant: "outline", children: requirement.status })] }

              ), /*#__PURE__*/

              _jsx("div", { className: "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2", children:
                targets.map((link, index) => {
                  const status = link.satisfied ? 'satisfied' : 'missing';
                  const StatusIcon = TRACE_STATUS_ICONS[status];

                  return (/*#__PURE__*/
                    _jsxs("div", {

                      className: `flex items-center gap-2 p-2 rounded-md text-xs ${TRACE_STATUS_COLORS[status]}`, children: [/*#__PURE__*/

                      _jsx(StatusIcon, { className: "h-3 w-3 flex-shrink-0" }), /*#__PURE__*/
                      _jsxs("div", { className: "flex-1 min-w-0", children: [/*#__PURE__*/
                        _jsx("div", { className: "font-medium truncate", children: link.target.name }), /*#__PURE__*/
                        _jsxs("div", { className: "text-xs opacity-75", children: [
                          link.target.type, " \xB7 ", link.relationship] }
                        )] }
                      )] }, index
                    ));

                }) }
              )] }, requirement.uid
            )
            ) }
          ) }

        )] }
      )] }
    ));

}
