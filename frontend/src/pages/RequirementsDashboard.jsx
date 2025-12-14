import logger from '@/utils/logger';
import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useDebounce } from 'use-debounce';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, CheckCircle2, Clock, FileText, GitBranch, Loader2, Search, TrendingUp } from 'lucide-react';

import ExportButton from '@/components/ExportButton';import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";

const RequirementsDashboard = () => {
  const [selectedReq, setSelectedReq] = useState(null);

  // Filters
  const [typeFilter, setTypeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Debounce search query to prevent excessive API calls
  const [debouncedSearchQuery] = useDebounce(searchQuery, 300);

  // Fetch requirements using React Query
  const { data: requirementsData, isLoading: loadingRequirements, error: requirementsError, refetch: refetchRequirements } = useQuery({
    queryKey: ['ap239-requirements', typeFilter, statusFilter, priorityFilter, debouncedSearchQuery],
    queryFn: () => {
      const params = {};
      if (typeFilter !== 'all') params.type = typeFilter;
      if (statusFilter !== 'all') params.status = statusFilter;
      if (priorityFilter !== 'all') params.priority = priorityFilter;
      if (debouncedSearchQuery) params.search = debouncedSearchQuery;
      return apiService.ap239.getRequirements(params);
    },
    refetchInterval: 30000 // Refresh every 30 seconds
  });

  // Fetch traceability matrix
  const { data: traceabilityData, isLoading: loadingTraceability } = useQuery({
    queryKey: ['traceability-matrix'],
    queryFn: () => apiService.hierarchy.getTraceabilityMatrix(),
    refetchInterval: 60000 // Refresh every minute
  });

  // Fetch statistics
  const { data: statisticsData, isLoading: loadingStatistics } = useQuery({
    queryKey: ['ap239-statistics'],
    queryFn: () => apiService.ap239.getStatistics(),
    refetchInterval: 60000
  });

  const requirements = requirementsData?.requirements || [];
  const traceability = traceabilityData?.matrix || [];
  const statistics = statisticsData?.statistics || null;

  const fetchRequirementDetail = async (reqId) => {
    try {
      const response = await apiService.ap239.getRequirement(reqId);
      setSelectedReq(response.requirement);
    } catch (error) {
      logger.error('Error fetching requirement detail:', error);
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority?.toLowerCase()) {
      case 'high':
        return 'destructive';
      case 'medium':
        return 'default';
      case 'low':
        return 'secondary';
      default:
        return 'outline';
    }
  };

  const getStatusIcon = (status) => {
    switch (status?.toLowerCase()) {
      case 'approved':
        return /*#__PURE__*/_jsx(CheckCircle2, { className: "h-4 w-4 text-green-500" });
      case 'draft':
        return /*#__PURE__*/_jsx(Clock, { className: "h-4 w-4 text-yellow-500" });
      case 'obsolete':
        return /*#__PURE__*/_jsx(AlertCircle, { className: "h-4 w-4 text-red-500" });
      default:
        return /*#__PURE__*/_jsx(FileText, { className: "h-4 w-4" });
    }
  };

  const isLoading = loadingRequirements || loadingTraceability || loadingStatistics;

  if (isLoading && !requirementsData) {
    return (/*#__PURE__*/
      _jsx("div", { className: "flex items-center justify-center h-screen", children: /*#__PURE__*/
        _jsx(Loader2, { className: "h-8 w-8 animate-spin" }) }
      ));

  }

  return (/*#__PURE__*/
    _jsxs("div", { className: "container mx-auto p-6 space-y-6", children: [/*#__PURE__*/

      _jsxs("div", { className: "flex justify-between items-center", children: [/*#__PURE__*/
        _jsxs("div", { children: [/*#__PURE__*/
          _jsx("h1", { className: "text-3xl font-bold", children: "Requirements Dashboard" }), /*#__PURE__*/
          _jsx("p", { className: "text-muted-foreground", children: "AP239 Product Life Cycle Support - Requirements Management" })] }
        ), /*#__PURE__*/
        _jsxs(Button, { variant: "outline", onClick: () => refetchRequirements(), disabled: isLoading, children: [
          isLoading ? /*#__PURE__*/_jsx(Loader2, { className: "h-4 w-4 animate-spin mr-2" }) : null, "Refresh"] }

        )] }
      ),


      requirementsError && /*#__PURE__*/
      _jsxs(Alert, { variant: "destructive", children: [/*#__PURE__*/
        _jsx(AlertCircle, { className: "h-4 w-4" }), /*#__PURE__*/
        _jsxs(AlertDescription, { children: ["Failed to load requirements: ",
          requirementsError instanceof Error ? requirementsError.message : 'Unknown error'] }
        )] }
      ),



      loadingStatistics ? /*#__PURE__*/
      _jsx("div", { className: "grid grid-cols-1 md:grid-cols-4 gap-4", children:
        [1, 2, 3, 4].map((i) => /*#__PURE__*/
        _jsxs(Card, { children: [/*#__PURE__*/
          _jsx(CardHeader, { className: "pb-2", children: /*#__PURE__*/
            _jsx(Skeleton, { className: "h-4 w-32" }) }
          ), /*#__PURE__*/
          _jsx(CardContent, { children: /*#__PURE__*/
            _jsx(Skeleton, { className: "h-8 w-16" }) }
          )] }, i
        )
        ) }
      ) :
      statistics ? /*#__PURE__*/
      _jsxs("div", { className: "grid grid-cols-1 md:grid-cols-4 gap-4", children: [/*#__PURE__*/
        _jsxs(Card, { children: [/*#__PURE__*/
          _jsxs(CardHeader, { className: "flex flex-row items-center justify-between space-y-0 pb-2", children: [/*#__PURE__*/
            _jsx(CardTitle, { className: "text-sm font-medium", children: "Total Requirements" }), /*#__PURE__*/
            _jsx(FileText, { className: "h-4 w-4 text-muted-foreground" })] }
          ), /*#__PURE__*/
          _jsx(CardContent, { children: /*#__PURE__*/
            _jsx("div", { className: "text-2xl font-bold", children:
              statistics.Requirement?.total || 0 }
            ) }
          )] }
        ), /*#__PURE__*/

        _jsxs(Card, { children: [/*#__PURE__*/
          _jsxs(CardHeader, { className: "flex flex-row items-center justify-between space-y-0 pb-2", children: [/*#__PURE__*/
            _jsx(CardTitle, { className: "text-sm font-medium", children: "Approved" }), /*#__PURE__*/
            _jsx(CheckCircle2, { className: "h-4 w-4 text-green-500" })] }
          ), /*#__PURE__*/
          _jsx(CardContent, { children: /*#__PURE__*/
            _jsx("div", { className: "text-2xl font-bold", children:
              statistics.Requirement?.by_status?.Approved || 0 }
            ) }
          )] }
        ), /*#__PURE__*/

        _jsxs(Card, { children: [/*#__PURE__*/
          _jsxs(CardHeader, { className: "flex flex-row items-center justify-between space-y-0 pb-2", children: [/*#__PURE__*/
            _jsx(CardTitle, { className: "text-sm font-medium", children: "Analyses" }), /*#__PURE__*/
            _jsx(TrendingUp, { className: "h-4 w-4 text-blue-500" })] }
          ), /*#__PURE__*/
          _jsx(CardContent, { children: /*#__PURE__*/
            _jsx("div", { className: "text-2xl font-bold", children:
              statistics.Analysis?.total || 0 }
            ) }
          )] }
        ), /*#__PURE__*/

        _jsxs(Card, { children: [/*#__PURE__*/
          _jsxs(CardHeader, { className: "flex flex-row items-center justify-between space-y-0 pb-2", children: [/*#__PURE__*/
            _jsx(CardTitle, { className: "text-sm font-medium", children: "Traceability Coverage" }), /*#__PURE__*/
            _jsx(GitBranch, { className: "h-4 w-4 text-purple-500" })] }
          ), /*#__PURE__*/
          _jsx(CardContent, { children: /*#__PURE__*/
            _jsxs("div", { className: "text-2xl font-bold", children: [
              traceability && traceability.length > 0 ?
              Math.round(traceability.filter((m) => m.traceability.length > 0).length / traceability.length * 100) :
              0, "%"] }
            ) }
          )] }
        )] }
      ) :
      null, /*#__PURE__*/


      _jsxs(Card, { children: [/*#__PURE__*/
        _jsxs(CardHeader, { className: "flex flex-row items-center justify-between", children: [/*#__PURE__*/
          _jsx(CardTitle, { children: "Filters" }), /*#__PURE__*/
          _jsx(ExportButton, {
            entityType: "requirements",
            filters: {
              type: typeFilter,
              status: statusFilter,
              priority: priorityFilter,
              search: debouncedSearchQuery
            } }
          )] }
        ), /*#__PURE__*/
        _jsx(CardContent, { children: /*#__PURE__*/
          _jsxs("div", { className: "grid grid-cols-1 md:grid-cols-4 gap-4", children: [/*#__PURE__*/
            _jsxs("div", { className: "relative", children: [/*#__PURE__*/
              _jsx(Search, { className: "absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" }), /*#__PURE__*/
              _jsx(Input, {
                placeholder: "Search requirements...",
                value: searchQuery,
                onChange: (e) => setSearchQuery(e.target.value),
                className: "pl-8" }
              )] }
            ), /*#__PURE__*/

            _jsxs(Select, { value: typeFilter, onValueChange: setTypeFilter, children: [/*#__PURE__*/
              _jsx(SelectTrigger, { children: /*#__PURE__*/
                _jsx(SelectValue, { placeholder: "Type" }) }
              ), /*#__PURE__*/
              _jsxs(SelectContent, { children: [/*#__PURE__*/
                _jsx(SelectItem, { value: "all", children: "All Types" }), /*#__PURE__*/
                _jsx(SelectItem, { value: "Performance", children: "Performance" }), /*#__PURE__*/
                _jsx(SelectItem, { value: "Functional", children: "Functional" }), /*#__PURE__*/
                _jsx(SelectItem, { value: "Safety", children: "Safety" }), /*#__PURE__*/
                _jsx(SelectItem, { value: "Interface", children: "Interface" })] }
              )] }
            ), /*#__PURE__*/

            _jsxs(Select, { value: statusFilter, onValueChange: setStatusFilter, children: [/*#__PURE__*/
              _jsx(SelectTrigger, { children: /*#__PURE__*/
                _jsx(SelectValue, { placeholder: "Status" }) }
              ), /*#__PURE__*/
              _jsxs(SelectContent, { children: [/*#__PURE__*/
                _jsx(SelectItem, { value: "all", children: "All Statuses" }), /*#__PURE__*/
                _jsx(SelectItem, { value: "Draft", children: "Draft" }), /*#__PURE__*/
                _jsx(SelectItem, { value: "Approved", children: "Approved" }), /*#__PURE__*/
                _jsx(SelectItem, { value: "Obsolete", children: "Obsolete" })] }
              )] }
            ), /*#__PURE__*/

            _jsxs(Select, { value: priorityFilter, onValueChange: setPriorityFilter, children: [/*#__PURE__*/
              _jsx(SelectTrigger, { children: /*#__PURE__*/
                _jsx(SelectValue, { placeholder: "Priority" }) }
              ), /*#__PURE__*/
              _jsxs(SelectContent, { children: [/*#__PURE__*/
                _jsx(SelectItem, { value: "all", children: "All Priorities" }), /*#__PURE__*/
                _jsx(SelectItem, { value: "High", children: "High" }), /*#__PURE__*/
                _jsx(SelectItem, { value: "Medium", children: "Medium" }), /*#__PURE__*/
                _jsx(SelectItem, { value: "Low", children: "Low" })] }
              )] }
            )] }
          ) }
        )] }
      ), /*#__PURE__*/


      _jsxs(Tabs, { defaultValue: "requirements", className: "w-full", children: [/*#__PURE__*/
        _jsxs(TabsList, { children: [/*#__PURE__*/
          _jsx(TabsTrigger, { value: "requirements", children: "Requirements List" }), /*#__PURE__*/
          _jsx(TabsTrigger, { value: "traceability", children: "Traceability Matrix" })] }
        ), /*#__PURE__*/

        _jsx(TabsContent, { value: "requirements", children: /*#__PURE__*/
          _jsxs(Card, { children: [/*#__PURE__*/
            _jsx(CardHeader, { children: /*#__PURE__*/
              _jsxs(CardTitle, { children: ["Requirements (", requirements.length, ")"] }) }
            ), /*#__PURE__*/
            _jsx(CardContent, { children:
              loadingRequirements ? /*#__PURE__*/
              _jsx("div", { className: "space-y-2", children:
                [1, 2, 3, 4, 5].map((i) => /*#__PURE__*/
                _jsx(Skeleton, { className: "h-12 w-full" }, i)
                ) }
              ) :
              requirements.length === 0 ? /*#__PURE__*/
              _jsx("div", { className: "text-center py-8 text-muted-foreground", children: "No requirements found. Try adjusting your filters." }

              ) : /*#__PURE__*/

              _jsxs(Table, { children: [/*#__PURE__*/
                _jsx(TableHeader, { children: /*#__PURE__*/
                  _jsxs(TableRow, { children: [/*#__PURE__*/
                    _jsx(TableHead, { children: "ID" }), /*#__PURE__*/
                    _jsx(TableHead, { children: "Name" }), /*#__PURE__*/
                    _jsx(TableHead, { children: "Type" }), /*#__PURE__*/
                    _jsx(TableHead, { children: "Priority" }), /*#__PURE__*/
                    _jsx(TableHead, { children: "Status" }), /*#__PURE__*/
                    _jsx(TableHead, { children: "Satisfied By" }), /*#__PURE__*/
                    _jsx(TableHead, { children: "Actions" })] }
                  ) }
                ), /*#__PURE__*/
                _jsx(TableBody, { children:
                  requirements.map((req) => /*#__PURE__*/
                  _jsxs(TableRow, { children: [/*#__PURE__*/
                    _jsx(TableCell, { className: "font-mono text-sm", children: req.name || req.id }), /*#__PURE__*/
                    _jsx(TableCell, { className: "font-medium", children: req.description || req.name }), /*#__PURE__*/
                    _jsx(TableCell, { children: /*#__PURE__*/
                      _jsx(Badge, { variant: "outline", children: req.type || 'N/A' }) }
                    ), /*#__PURE__*/
                    _jsx(TableCell, { children: /*#__PURE__*/
                      _jsx(Badge, { variant: getPriorityColor(req.priority), children:
                        req.priority || 'N/A' }
                      ) }
                    ), /*#__PURE__*/
                    _jsx(TableCell, { children: /*#__PURE__*/
                      _jsxs("div", { className: "flex items-center gap-2", children: [
                        getStatusIcon(req.status), /*#__PURE__*/
                        _jsx("span", { children: req.status || 'N/A' })] }
                      ) }
                    ), /*#__PURE__*/
                    _jsx(TableCell, { children: /*#__PURE__*/
                      _jsxs(Badge, { variant: "secondary", children: [
                        req.satisfied_by_parts?.length || 0, " parts"] }
                      ) }
                    ), /*#__PURE__*/
                    _jsx(TableCell, { children: /*#__PURE__*/
                      _jsx(Button, {
                        variant: "ghost",
                        size: "sm",
                        onClick: () => fetchRequirementDetail(req.name || req.id), children:
                        "View Details" }

                      ) }
                    )] }, req.name || req.id
                  )
                  ) }
                )] }
              ) }

            )] }
          ) }
        ), /*#__PURE__*/

        _jsx(TabsContent, { value: "traceability", children: /*#__PURE__*/
          _jsxs(Card, { children: [/*#__PURE__*/
            _jsxs(CardHeader, { children: [/*#__PURE__*/
              _jsx(CardTitle, { children: "Traceability Matrix" }), /*#__PURE__*/
              _jsx("p", { className: "text-sm text-muted-foreground", children: "Complete traceability from requirements through parts to ontologies" }

              )] }
            ), /*#__PURE__*/
            _jsx(CardContent, { children:
              loadingTraceability ? /*#__PURE__*/
              _jsx("div", { className: "space-y-4", children:
                [1, 2, 3].map((i) => /*#__PURE__*/
                _jsxs(Card, { children: [/*#__PURE__*/
                  _jsxs(CardHeader, { children: [/*#__PURE__*/
                    _jsx(Skeleton, { className: "h-6 w-64" }), /*#__PURE__*/
                    _jsx(Skeleton, { className: "h-4 w-32" })] }
                  ), /*#__PURE__*/
                  _jsx(CardContent, { children: /*#__PURE__*/
                    _jsx(Skeleton, { className: "h-20 w-full" }) }
                  )] }, i
                )
                ) }
              ) :
              traceability && traceability.length > 0 ? /*#__PURE__*/
              _jsx("div", { className: "space-y-4", children:
                traceability.map((entry, idx) => /*#__PURE__*/
                _jsxs(Card, { children: [/*#__PURE__*/
                  _jsx(CardHeader, { children: /*#__PURE__*/
                    _jsxs("div", { className: "flex items-center justify-between", children: [/*#__PURE__*/
                      _jsxs("div", { children: [/*#__PURE__*/
                        _jsx(CardTitle, { className: "text-base", children:
                          entry.requirement.name }
                        ), /*#__PURE__*/
                        _jsx("p", { className: "text-sm text-muted-foreground", children:
                          entry.requirement.id }
                        )] }
                      ), /*#__PURE__*/
                      _jsxs("div", { className: "flex gap-2", children: [/*#__PURE__*/
                        _jsx(Badge, { children: entry.requirement.type }), /*#__PURE__*/
                        _jsx(Badge, { variant: "outline", children: entry.requirement.status })] }
                      )] }
                    ) }
                  ), /*#__PURE__*/
                  _jsx(CardContent, { children:
                    entry.traceability.length > 0 ? /*#__PURE__*/
                    _jsx("div", { className: "space-y-2", children:
                      entry.traceability.map((trace, traceIdx) => /*#__PURE__*/
                      _jsxs("div", { className: "flex items-center gap-4 p-3 bg-muted rounded-lg", children: [/*#__PURE__*/
                        _jsx(GitBranch, { className: "h-4 w-4 text-muted-foreground" }), /*#__PURE__*/
                        _jsxs("div", { className: "flex-1", children: [/*#__PURE__*/
                          _jsx("div", { className: "font-medium", children: trace.part_name }),
                          trace.materials && trace.materials.length > 0 && /*#__PURE__*/
                          _jsxs("div", { className: "text-sm text-muted-foreground", children: ["Materials: ",
                            trace.materials.join(', ')] }
                          ),

                          trace.ontologies && trace.ontologies.length > 0 && /*#__PURE__*/
                          _jsxs("div", { className: "text-sm text-muted-foreground", children: ["Ontologies: ",
                            trace.ontologies.join(', ')] }
                          )] }

                        )] }, traceIdx
                      )
                      ) }
                    ) : /*#__PURE__*/

                    _jsx("div", { className: "text-center py-4 text-muted-foreground", children: "No traceability data available" }

                    ) }

                  )] }, idx
                )
                ) }
              ) : /*#__PURE__*/

              _jsx("div", { className: "text-center py-8 text-muted-foreground", children: "No traceability data available" }

              ) }

            )] }
          ) }
        )] }
      ),


      selectedReq && /*#__PURE__*/
      _jsxs(Card, { className: "fixed right-4 top-20 w-96 max-h-[80vh] overflow-y-auto shadow-lg z-50", children: [/*#__PURE__*/
        _jsx(CardHeader, { children: /*#__PURE__*/
          _jsxs("div", { className: "flex justify-between items-start", children: [/*#__PURE__*/
            _jsxs("div", { children: [/*#__PURE__*/
              _jsx(CardTitle, { children: selectedReq.name }), /*#__PURE__*/
              _jsx("p", { className: "text-sm text-muted-foreground", children: selectedReq.id })] }
            ), /*#__PURE__*/
            _jsx(Button, { variant: "ghost", size: "sm", onClick: () => setSelectedReq(null), children: "\u2715" }

            )] }
          ) }
        ), /*#__PURE__*/
        _jsxs(CardContent, { className: "space-y-4", children: [/*#__PURE__*/
          _jsxs("div", { children: [/*#__PURE__*/
            _jsx("h4", { className: "font-semibold mb-2", children: "Description" }), /*#__PURE__*/
            _jsx("p", { className: "text-sm text-muted-foreground", children:
              selectedReq.description || 'No description available' }
            )] }
          ),

          selectedReq.versions && selectedReq.versions.length > 0 && /*#__PURE__*/
          _jsxs("div", { children: [/*#__PURE__*/
            _jsx("h4", { className: "font-semibold mb-2", children: "Versions" }), /*#__PURE__*/
            _jsx("div", { className: "space-y-1", children:
              selectedReq.versions.map((v, idx) => /*#__PURE__*/
              _jsxs("div", { className: "text-sm", children: [
                v.version, " - ", v.name, " (", v.status, ")"] }, idx
              )
              ) }
            )] }
          ),


          selectedReq.analyses && selectedReq.analyses.length > 0 && /*#__PURE__*/
          _jsxs("div", { children: [/*#__PURE__*/
            _jsx("h4", { className: "font-semibold mb-2", children: "Analyses" }), /*#__PURE__*/
            _jsx("div", { className: "space-y-1", children:
              selectedReq.analyses.map((a, idx) => /*#__PURE__*/
              _jsx(Badge, { variant: "outline", className: "mr-1", children:
                a.name }, idx
              )
              ) }
            )] }
          ),


          selectedReq.approvals && selectedReq.approvals.length > 0 && /*#__PURE__*/
          _jsxs("div", { children: [/*#__PURE__*/
            _jsx("h4", { className: "font-semibold mb-2", children: "Approvals" }), /*#__PURE__*/
            _jsx("div", { className: "space-y-1", children:
              selectedReq.approvals.map((a, idx) => /*#__PURE__*/
              _jsxs("div", { className: "text-sm flex items-center gap-2", children: [
                getStatusIcon(a.status),
                a.name] }, idx
              )
              ) }
            )] }
          )] }

        )] }
      )] }

    ));

};

export default RequirementsDashboard;
