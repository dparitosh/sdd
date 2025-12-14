import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@ui/card';
import { Input } from '@ui/input';
import { Button } from '@ui/button';
import { Label } from '@ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue } from
'@ui/select';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger } from
'@ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow } from
'@ui/table';
import { Badge } from '@ui/badge';
import { Skeleton } from '@ui/skeleton';
import { Search, ExternalLink, List, Network, ChevronLeft, ChevronRight, Plus, X, ArrowUpDown, ArrowUp, ArrowDown, Loader2 } from 'lucide-react';
import PageHeader from '@/components/PageHeader';import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";


















const ARTIFACT_TYPES = [
'All',
'Class',
'Package',
'Property',
'Association',
'Requirement',
'Constraint',
'Enumeration',
'Port',
'Slot',
'InstanceSpecification'];


// Property definitions for each node type
const NODE_TYPE_PROPERTIES = {
  'All': ['name', 'comment', 'id'],
  'Class': ['name', 'comment', 'qualified_name', 'id', 'isAbstract', 'visibility'],
  'Package': ['name', 'comment', 'qualified_name', 'id', 'uri'],
  'Property': ['name', 'comment', 'qualified_name', 'id', 'aggregation', 'isDerived'],
  'Association': ['name', 'comment', 'qualified_name', 'id', 'isDerived'],
  'Requirement': ['name', 'comment', 'description', 'id', 'status', 'priority'],
  'Constraint': ['name', 'comment', 'specification', 'id'],
  'Enumeration': ['name', 'comment', 'qualified_name', 'id'],
  'Port': ['name', 'comment', 'id', 'direction'],
  'Slot': ['name', 'comment', 'id', 'value'],
  'InstanceSpecification': ['name', 'comment', 'id']
};

const SEARCH_OPERATORS = [
{ value: 'contains', label: 'Contains' },
{ value: 'equals', label: 'Equals' },
{ value: 'starts_with', label: 'Starts With' },
{ value: 'ends_with', label: 'Ends With' }];


const PAGE_SIZE = 25;

export default function AdvancedSearch() {
  const [searchParams, setSearchParams] = useState({
    type: 'All',
    name: '',
    comment: ''
  });
  const [viewMode, setViewMode] = useState('table');
  const [currentPage, setCurrentPage] = useState(1);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [sortField, setSortField] = useState('name');
  const [sortOrder, setSortOrder] = useState('asc');
  const [searchCriteria, setSearchCriteria] = useState([
  { id: 1, property: 'name', operator: 'contains', value: '', logicOperator: 'AND' }]
  );

  // Get available properties for selected type
  const availableProperties = NODE_TYPE_PROPERTIES[searchParams.type] || NODE_TYPE_PROPERTIES['All'];

  // Add new search criterion
  const addCriterion = () => {
    const newId = Math.max(...searchCriteria.map((c) => c.id), 0) + 1;
    setSearchCriteria([
    ...searchCriteria,
    { id: newId, property: availableProperties[0], operator: 'contains', value: '', logicOperator: 'AND' }]
    );
  };

  // Remove criterion
  const removeCriterion = (id) => {
    if (searchCriteria.length > 1) {
      setSearchCriteria(searchCriteria.filter((c) => c.id !== id));
    }
  };

  // Update criterion
  const updateCriterion = (id, field, value) => {
    setSearchCriteria(searchCriteria.map((c) =>
    c.id === id ? { ...c, [field]: value } : c
    ));
  };

  const { data: results, isLoading, refetch } = useQuery({
    queryKey: ['artifacts', searchParams],
    queryFn: () =>
    apiService.searchArtifacts({
      type: searchParams.type !== 'All' ? searchParams.type : undefined,
      name: searchParams.name || undefined,
      comment: searchParams.comment || undefined,
      limit: 100
    }),
    enabled: false // Only search when user clicks button
  });

  const handleSearch = () => {
    setCurrentPage(1); // Reset to first page on new search
    refetch();
  };

  const handleReset = () => {
    setSearchParams({ type: 'All', name: '', comment: '' });
    setCurrentPage(1);
    setSearchCriteria([
    { id: 1, property: 'name', operator: 'contains', value: '', logicOperator: 'AND' }]
    );
  };

  // Pagination logic
  const totalPages = results ? Math.ceil(results.length / PAGE_SIZE) : 0;

  // Sort results
  const sortedResults = results ? [...results].sort((a, b) => {
    let aVal = a[sortField] || '';
    let bVal = b[sortField] || '';

    // Convert to string for comparison
    aVal = String(aVal).toLowerCase();
    bVal = String(bVal).toLowerCase();

    if (sortOrder === 'asc') {
      return aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
    } else {
      return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
    }
  }) : [];

  const paginatedResults = sortedResults ?
  sortedResults.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE) :
  [];

  const handleSort = (field) => {
    if (sortField === field) {
      // Toggle sort order if clicking same field
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      // Set new field and default to ascending
      setSortField(field);
      setSortOrder('asc');
    }
    setCurrentPage(1); // Reset to first page when sorting
  };

  const SortIcon = ({ field }) => {
    if (sortField !== field) {
      return /*#__PURE__*/_jsx(ArrowUpDown, { className: "h-4 w-4 ml-1 opacity-40" });
    }
    return sortOrder === 'asc' ? /*#__PURE__*/
    _jsx(ArrowUp, { className: "h-4 w-4 ml-1 text-primary" }) : /*#__PURE__*/
    _jsx(ArrowDown, { className: "h-4 w-4 ml-1 text-primary" });
  };

  const goToPage = (page) => {
    setCurrentPage(Math.max(1, Math.min(page, totalPages)));
  };

  // Reusable Pagination Component
  const PaginationControls = () =>
  results && sortedResults.length > PAGE_SIZE ? /*#__PURE__*/
  _jsxs("div", { className: "flex items-center justify-between py-3 px-4 bg-gradient-to-r from-muted/30 to-transparent rounded-lg border", children: [/*#__PURE__*/
    _jsxs("div", { className: "text-sm text-muted-foreground font-medium", children: ["Showing ",
      (currentPage - 1) * PAGE_SIZE + 1, " to ", Math.min(currentPage * PAGE_SIZE, sortedResults.length), " of ", sortedResults.length, " results"] }
    ), /*#__PURE__*/
    _jsxs("div", { className: "flex items-center gap-2", children: [/*#__PURE__*/
      _jsxs(Button, {
        variant: "outline",
        size: "sm",
        onClick: () => goToPage(currentPage - 1),
        disabled: currentPage === 1,
        className: "h-9", children: [/*#__PURE__*/

        _jsx(ChevronLeft, { className: "h-4 w-4 mr-1" }), "Previous"] }

      ), /*#__PURE__*/
      _jsxs("div", { className: "flex items-center gap-1", children: [
        Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
          let pageNum;
          if (totalPages <= 5) {
            pageNum = i + 1;
          } else if (currentPage <= 3) {
            pageNum = i + 1;
          } else if (currentPage >= totalPages - 2) {
            pageNum = totalPages - 4 + i;
          } else {
            pageNum = currentPage - 2 + i;
          }

          return (/*#__PURE__*/
            _jsx(Button, {

              variant: currentPage === pageNum ? "default" : "outline",
              size: "sm",
              className: "w-9 h-9",
              onClick: () => goToPage(pageNum), children:

              pageNum }, pageNum
            ));

        }),
        totalPages > 5 && currentPage < totalPages - 2 && /*#__PURE__*/
        _jsxs(_Fragment, { children: [/*#__PURE__*/
          _jsx("span", { className: "text-muted-foreground px-1", children: "..." }), /*#__PURE__*/
          _jsx(Button, {
            variant: "outline",
            size: "sm",
            className: "w-9 h-9",
            onClick: () => goToPage(totalPages), children:

            totalPages }
          )] }
        )] }

      ), /*#__PURE__*/
      _jsxs(Button, {
        variant: "outline",
        size: "sm",
        onClick: () => goToPage(currentPage + 1),
        disabled: currentPage === totalPages,
        className: "h-9", children: [
        "Next", /*#__PURE__*/

        _jsx(ChevronRight, { className: "h-4 w-4 ml-1" })] }
      )] }
    )] }
  ) :
  null;


  return (/*#__PURE__*/
    _jsxs("div", { className: "container mx-auto p-6 space-y-6", children: [/*#__PURE__*/
      _jsx(PageHeader, {
        title: "Advanced Search",
        description: "Search for SysML/UML artifacts in the knowledge graph with advanced filtering",
        icon: /*#__PURE__*/_jsx(Search, { className: "h-6 w-6 text-primary" }),
        breadcrumbs: [
        { label: 'Knowledge Graph', href: '/graph' },
        { label: 'Advanced Search' }],

        actions:
        results && /*#__PURE__*/
        _jsxs(Badge, { variant: "outline", children: [
          results.length, " ", results.length === 1 ? 'result' : 'results'] }
        ) }


      ), /*#__PURE__*/


      _jsxs(Card, { className: "card-corporate border-2 shadow-lg", children: [/*#__PURE__*/
        _jsx(CardHeader, { className: "border-b bg-gradient-to-r from-primary/5 to-primary/10 pb-4", children: /*#__PURE__*/
          _jsxs("div", { className: "flex items-center justify-between", children: [/*#__PURE__*/
            _jsxs(CardTitle, { className: "flex items-center gap-2", children: [/*#__PURE__*/
              _jsx(Search, { className: "h-5 w-5 text-primary" }), "Search Criteria"] }

            ),
            isLoading && /*#__PURE__*/
            _jsxs(Badge, { variant: "outline", className: "text-xs", children: [/*#__PURE__*/
              _jsx(Loader2, { className: "h-3 w-3 mr-1 animate-spin" }), "Searching..."] }

            )] }

          ) }
        ), /*#__PURE__*/
        _jsxs(CardContent, { className: "pt-6", children: [/*#__PURE__*/
          _jsxs("div", { className: "space-y-6", children: [/*#__PURE__*/

            _jsx("div", { className: "grid gap-4 md:grid-cols-2 lg:grid-cols-3", children: /*#__PURE__*/
              _jsxs("div", { className: "space-y-2", children: [/*#__PURE__*/
                _jsx(Label, { htmlFor: "type", className: "text-sm font-semibold", children: "Artifact Type *" }), /*#__PURE__*/
                _jsxs(Select, {
                  value: searchParams.type,
                  onValueChange: (value) => {
                    setSearchParams({ ...searchParams, type: value });
                    // Reset criteria when type changes to use appropriate properties
                    setSearchCriteria([
                    { id: 1, property: NODE_TYPE_PROPERTIES[value]?.[0] || 'name', operator: 'contains', value: '', logicOperator: 'AND' }]
                    );
                  }, children: [/*#__PURE__*/

                  _jsx(SelectTrigger, { id: "type", children: /*#__PURE__*/
                    _jsx(SelectValue, {}) }
                  ), /*#__PURE__*/
                  _jsx(SelectContent, { children:
                    ARTIFACT_TYPES.map((type) => /*#__PURE__*/
                    _jsx(SelectItem, { value: type, children:
                      type }, type
                    )
                    ) }
                  )] }
                )] }
              ) }
            ), /*#__PURE__*/


            _jsxs("div", { className: "space-y-4 mt-6 pt-6 border-t-2", children: [/*#__PURE__*/
              _jsxs("div", { className: "flex items-center justify-between mb-4", children: [/*#__PURE__*/
                _jsx(Label, { className: "text-base font-semibold", children: "Search Criteria" }), /*#__PURE__*/
                _jsxs(Button, {
                  variant: "outline",
                  size: "sm",
                  onClick: addCriterion,
                  className: "flex gap-1", children: [/*#__PURE__*/

                  _jsx(Plus, { className: "h-4 w-4" }), "Add Criterion"] }

                )] }
              ),

              searchCriteria.map((criterion, index) => /*#__PURE__*/
              _jsxs("div", { className: "space-y-3", children: [

                index > 0 && /*#__PURE__*/
                _jsxs("div", { className: "flex items-center gap-2 mb-2", children: [/*#__PURE__*/
                  _jsxs(Select, {
                    value: criterion.logicOperator,
                    onValueChange: (value) => updateCriterion(criterion.id, 'logicOperator', value), children: [/*#__PURE__*/

                    _jsx(SelectTrigger, { className: "w-24 h-8 bg-primary/10 border-primary/30", children: /*#__PURE__*/
                      _jsx(SelectValue, {}) }
                    ), /*#__PURE__*/
                    _jsxs(SelectContent, { children: [/*#__PURE__*/
                      _jsx(SelectItem, { value: "AND", children: "AND" }), /*#__PURE__*/
                      _jsx(SelectItem, { value: "OR", children: "OR" })] }
                    )] }
                  ), /*#__PURE__*/
                  _jsx("div", { className: "h-px flex-1 bg-border" })] }
                ), /*#__PURE__*/


                _jsxs("div", { className: "grid gap-3 md:grid-cols-12 items-end bg-muted/30 p-4 rounded-lg border-2", children: [/*#__PURE__*/

                  _jsxs("div", { className: "md:col-span-3 space-y-2", children: [/*#__PURE__*/
                    _jsx(Label, { className: "text-xs", children: "Property" }), /*#__PURE__*/
                    _jsxs(Select, {
                      value: criterion.property,
                      onValueChange: (value) => updateCriterion(criterion.id, 'property', value), children: [/*#__PURE__*/

                      _jsx(SelectTrigger, { children: /*#__PURE__*/
                        _jsx(SelectValue, {}) }
                      ), /*#__PURE__*/
                      _jsx(SelectContent, { children:
                        availableProperties.map((prop) => /*#__PURE__*/
                        _jsx(SelectItem, { value: prop, children:
                          prop.charAt(0).toUpperCase() + prop.slice(1).replace('_', ' ') }, prop
                        )
                        ) }
                      )] }
                    )] }
                  ), /*#__PURE__*/


                  _jsxs("div", { className: "md:col-span-3 space-y-2", children: [/*#__PURE__*/
                    _jsx(Label, { className: "text-xs", children: "Operator" }), /*#__PURE__*/
                    _jsxs(Select, {
                      value: criterion.operator,
                      onValueChange: (value) => updateCriterion(criterion.id, 'operator', value), children: [/*#__PURE__*/

                      _jsx(SelectTrigger, { children: /*#__PURE__*/
                        _jsx(SelectValue, {}) }
                      ), /*#__PURE__*/
                      _jsx(SelectContent, { children:
                        SEARCH_OPERATORS.map((op) => /*#__PURE__*/
                        _jsx(SelectItem, { value: op.value, children:
                          op.label }, op.value
                        )
                        ) }
                      )] }
                    )] }
                  ), /*#__PURE__*/


                  _jsxs("div", { className: "md:col-span-5 space-y-2", children: [/*#__PURE__*/
                    _jsx(Label, { className: "text-xs", children: "Value" }), /*#__PURE__*/
                    _jsx(Input, {
                      placeholder: "Enter search value...",
                      value: criterion.value,
                      onChange: (e) => updateCriterion(criterion.id, 'value', e.target.value),
                      onKeyDown: (e) => e.key === 'Enter' && handleSearch() }
                    )] }
                  ), /*#__PURE__*/


                  _jsx("div", { className: "md:col-span-1 flex items-end", children: /*#__PURE__*/
                    _jsx(Button, {
                      variant: "ghost",
                      size: "sm",
                      onClick: () => removeCriterion(criterion.id),
                      disabled: searchCriteria.length === 1,
                      className: "h-10 w-full text-destructive hover:text-destructive hover:bg-destructive/10", children: /*#__PURE__*/

                      _jsx(X, { className: "h-4 w-4" }) }
                    ) }
                  )] }
                )] }, criterion.id
              )
              )] }
            )] }
          ), /*#__PURE__*/



          _jsxs("div", { className: "flex items-center justify-between mt-6 pt-6 border-t-2", children: [/*#__PURE__*/
            _jsxs("div", { className: "flex gap-3", children: [/*#__PURE__*/
              _jsxs(Button, {
                onClick: handleSearch,
                className: "flex gap-2 shadow-md hover:shadow-lg transition-all min-w-[140px]",
                size: "lg", children: [/*#__PURE__*/

                _jsx(Search, { className: "h-4 w-4" }), "Search Now"] }

              ), /*#__PURE__*/
              _jsx(Button, {
                variant: "outline",
                onClick: handleReset,
                size: "lg",
                className: "border-2 min-w-[140px]", children:
                "Clear All" }

              )] }
            ),
            results && /*#__PURE__*/
            _jsxs("div", { className: "text-sm text-muted-foreground", children: [/*#__PURE__*/
              _jsx("span", { className: "font-semibold text-foreground", children: results.length }), " artifacts match your criteria"] }
            )] }

          )] }
        )] }
      ), /*#__PURE__*/


      _jsxs(Card, { className: "card-corporate border-2", children: [/*#__PURE__*/
        _jsx(CardHeader, { className: "border-b bg-gradient-to-r from-accent/10 to-accent/5", children: /*#__PURE__*/
          _jsxs("div", { className: "flex items-center justify-between", children: [/*#__PURE__*/
            _jsxs(CardTitle, { children: ["Search Results",

              results && /*#__PURE__*/
              _jsxs("span", { className: "ml-2 text-sm font-normal text-muted-foreground", children: ["(",
                results.length, " found", results.length > PAGE_SIZE ? `, showing ${paginatedResults.length}` : '', ")"] }
              )] }

            ), /*#__PURE__*/
            _jsx(Tabs, { value: viewMode, onValueChange: (v) => setViewMode(v), children: /*#__PURE__*/
              _jsxs(TabsList, { children: [/*#__PURE__*/
                _jsxs(TabsTrigger, { value: "table", className: "flex items-center gap-1", children: [/*#__PURE__*/
                  _jsx(List, { className: "h-4 w-4" }), "Table"] }

                ), /*#__PURE__*/
                _jsxs(TabsTrigger, { value: "graph", className: "flex items-center gap-1", children: [/*#__PURE__*/
                  _jsx(Network, { className: "h-4 w-4" }), "Graph"] }

                )] }
              ) }
            )] }
          ) }
        ), /*#__PURE__*/
        _jsxs(CardContent, { children: [

          !isLoading && /*#__PURE__*/_jsx(PaginationControls, {}),

          isLoading ? /*#__PURE__*/
          _jsx("div", { className: "space-y-2 mt-4", children:
            [...Array(5)].map((_, i) => /*#__PURE__*/
            _jsx(Skeleton, { className: "h-12 w-full" }, i)
            ) }
          ) :
          results && results.length > 0 ? /*#__PURE__*/
          _jsxs(_Fragment, { children: [/*#__PURE__*/
            _jsxs(Tabs, { value: viewMode, children: [/*#__PURE__*/
              _jsx(TabsContent, { value: "table", className: "mt-0", children: /*#__PURE__*/
                _jsx("div", { className: "rounded-lg border-2 shadow-sm overflow-hidden", children: /*#__PURE__*/
                  _jsxs(Table, { children: [/*#__PURE__*/
                    _jsx(TableHeader, { className: "bg-muted/50", children: /*#__PURE__*/
                      _jsxs(TableRow, { className: "hover:bg-muted/50", children: [/*#__PURE__*/
                        _jsx(TableHead, {
                          className: "cursor-pointer select-none hover:bg-muted transition-colors",
                          onClick: () => handleSort('type'), children: /*#__PURE__*/

                          _jsxs("div", { className: "flex items-center font-semibold", children: ["Type", /*#__PURE__*/

                            _jsx(SortIcon, { field: "type" })] }
                          ) }
                        ), /*#__PURE__*/
                        _jsx(TableHead, {
                          className: "cursor-pointer select-none hover:bg-muted transition-colors",
                          onClick: () => handleSort('name'), children: /*#__PURE__*/

                          _jsxs("div", { className: "flex items-center font-semibold", children: ["Name", /*#__PURE__*/

                            _jsx(SortIcon, { field: "name" })] }
                          ) }
                        ), /*#__PURE__*/
                        _jsx(TableHead, {
                          className: "cursor-pointer select-none hover:bg-muted transition-colors",
                          onClick: () => handleSort('id'), children: /*#__PURE__*/

                          _jsxs("div", { className: "flex items-center font-semibold", children: ["UID", /*#__PURE__*/

                            _jsx(SortIcon, { field: "id" })] }
                          ) }
                        ), /*#__PURE__*/
                        _jsx(TableHead, {
                          className: "cursor-pointer select-none hover:bg-muted transition-colors",
                          onClick: () => handleSort('comment'), children: /*#__PURE__*/

                          _jsxs("div", { className: "flex items-center font-semibold", children: ["Comment", /*#__PURE__*/

                            _jsx(SortIcon, { field: "comment" })] }
                          ) }
                        ), /*#__PURE__*/
                        _jsx(TableHead, { className: "w-[100px]", children: /*#__PURE__*/
                          _jsx("div", { className: "font-semibold", children: "Actions" }) }
                        )] }
                      ) }
                    ), /*#__PURE__*/
                    _jsx(TableBody, { children:
                      paginatedResults.map((artifact, index) => /*#__PURE__*/
                      _jsxs(TableRow, { children: [/*#__PURE__*/
                        _jsx(TableCell, { children: /*#__PURE__*/
                          _jsx(Badge, { variant: "outline", children: artifact.type }) }
                        ), /*#__PURE__*/
                        _jsx(TableCell, { className: "font-medium", children:
                          artifact.name || '(unnamed)' }
                        ), /*#__PURE__*/
                        _jsx(TableCell, { children: /*#__PURE__*/
                          _jsx("code", { className: "text-xs", children: artifact.id || artifact.uid }) }
                        ), /*#__PURE__*/
                        _jsx(TableCell, { className: "max-w-md truncate", children:
                          artifact.comment || '-' }
                        ), /*#__PURE__*/
                        _jsx(TableCell, { children: /*#__PURE__*/
                          _jsx(Button, {
                            variant: "ghost",
                            size: "sm",
                            disabled: !artifact.id && !artifact.uid,
                            onClick: () => {
                              const artifactId = artifact.id || artifact.uid;
                              const artifactType = artifact.type.toLowerCase();
                              if (artifactId) {
                                // Only open link for types that have detail endpoints
                                // Class and Package have /api/{type}/{id} endpoints
                                if (['class', 'package'].includes(artifactType)) {
                                  window.open(
                                    `/api/${artifactType}/${encodeURIComponent(artifactId)}`,
                                    '_blank'
                                  );
                                } else {
                                  // For other types, show in REST API Explorer or show message
                                  window.alert(`View ${artifact.type} "${artifact.name}" in Graph Browser or use the REST API Explorer to query by ID: ${artifactId}`);
                                }
                              }
                            }, children: /*#__PURE__*/

                            _jsx(ExternalLink, { className: "h-4 w-4" }) }
                          ) }
                        )] }, artifact.id || artifact.uid || index
                      )
                      ) }
                    )] }
                  ) }
                ) }
              ), /*#__PURE__*/
              _jsx(TabsContent, { value: "graph", className: "mt-0", children: /*#__PURE__*/
                _jsx("div", { className: "border rounded-lg p-8 bg-muted/20 min-h-[400px]", children: /*#__PURE__*/
                  _jsxs("div", { className: "flex flex-col items-center justify-center h-full text-center", children: [/*#__PURE__*/
                    _jsx(Network, { className: "h-16 w-16 text-muted-foreground mb-4" }), /*#__PURE__*/
                    _jsx("h3", { className: "text-lg font-semibold mb-2", children: "Graph Visualization" }), /*#__PURE__*/
                    _jsxs("p", { className: "text-sm text-muted-foreground max-w-md", children: ["Interactive graph view showing relationships between nodes.",

                      results.length, " nodes ready to visualize."] }
                    ), /*#__PURE__*/
                    _jsx("div", { className: "mt-6 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3", children:
                      paginatedResults.slice(0, 12).map((artifact, index) => /*#__PURE__*/
                      _jsx(Card, { className: "card-corporate", children: /*#__PURE__*/
                        _jsxs(CardContent, { className: "p-4 text-center", children: [/*#__PURE__*/
                          _jsx(Badge, { variant: "outline", className: "mb-2", children: artifact.type }), /*#__PURE__*/
                          _jsx("div", { className: "text-sm font-medium truncate", children: artifact.name || '(unnamed)' })] }
                        ) }, index
                      )
                      ) }
                    ), /*#__PURE__*/
                    _jsx("p", { className: "text-xs text-muted-foreground mt-4", children: "Full graph visualization with D3.js coming soon" }

                    )] }
                  ) }
                ) }
              )] }
            ), /*#__PURE__*/


            _jsx("div", { className: "mt-6 pt-4 border-t-2", children: /*#__PURE__*/
              _jsx(PaginationControls, {}) }
            )] }
          ) : /*#__PURE__*/

          _jsx("div", { className: "flex h-32 items-center justify-center text-muted-foreground", children:
            results ? 'No results found' : 'Enter search criteria and click Search' }
          )] }

        )] }
      )] }
    ));

}
