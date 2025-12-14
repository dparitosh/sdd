import { useQuery } from '@tanstack/react-query';
import { graphqlService } from '@/services/graphql';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@ui/card';
import { Skeleton } from '@ui/skeleton';
import { Alert, AlertDescription } from '@ui/alert';
import { Button } from '@ui/button';
import { Badge } from '@ui/badge';
import { Database, Activity, Search, Terminal, FileText, ArrowRight, Sparkles, LayoutDashboard } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import PageHeader from '@/components/PageHeader';import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";








export default function Dashboard() {
  const navigate = useNavigate();
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['statistics'],
    queryFn: graphqlService.getStatistics,
    retry: 1,
    staleTime: 30000
  });

  if (isLoading) {
    return (/*#__PURE__*/
      _jsxs("div", { className: "container mx-auto p-6 space-y-6", children: [/*#__PURE__*/
        _jsx(PageHeader, {
          title: "Dashboard",
          description: "Overview of your knowledge graph and system analytics",
          icon: /*#__PURE__*/_jsx(LayoutDashboard, { className: "h-6 w-6 text-primary" }) }
        ), /*#__PURE__*/
        _jsx("div", { className: "grid gap-4 md:grid-cols-2 lg:grid-cols-4", children:
          [...Array(4)].map((_, i) => /*#__PURE__*/
          _jsxs(Card, { children: [/*#__PURE__*/
            _jsx(CardHeader, { className: "pb-2", children: /*#__PURE__*/
              _jsx(Skeleton, { className: "h-4 w-24" }) }
            ), /*#__PURE__*/
            _jsx(CardContent, { children: /*#__PURE__*/
              _jsx(Skeleton, { className: "h-8 w-16" }) }
            )] }, i
          )
          ) }
        )] }
      ));

  }

  if (error) {
    return (/*#__PURE__*/
      _jsxs("div", { className: "container mx-auto p-6 space-y-6", children: [/*#__PURE__*/
        _jsx(PageHeader, {
          title: "Dashboard",
          description: "Overview of your knowledge graph and system analytics",
          icon: /*#__PURE__*/_jsx(LayoutDashboard, { className: "h-6 w-6 text-primary" }) }
        ), /*#__PURE__*/
        _jsx(Alert, { variant: "destructive", children: /*#__PURE__*/
          _jsx(AlertDescription, { children: "Failed to load statistics. Please check your connection and try again." }

          ) }
        )] }
      ));

  }

  // Prepare data grid items for periodic table layout
  const nodeTypes = Object.entries(stats?.node_types || {}).sort(([, a], [, b]) => b - a);
  const relationshipTypes = Object.entries(stats?.relationship_types || {}).sort(([, a], [, b]) => b - a);

  const gridItems = [
  { id: 'total-nodes', symbol: 'N', name: 'Total Nodes', value: stats?.total_nodes || 0, category: 'system', color: 'from-blue-500 to-blue-600' },
  { id: 'total-rels', symbol: 'R', name: 'Relationships', value: stats?.total_relationships || 0, category: 'system', color: 'from-cyan-500 to-cyan-600' },
  { id: 'node-types', symbol: 'NT', name: 'Node Types', value: nodeTypes.length, category: 'system', color: 'from-green-500 to-green-600' },
  { id: 'rel-types', symbol: 'RT', name: 'Relation Types', value: relationshipTypes.length, category: 'system', color: 'from-purple-500 to-purple-600' },
  ...nodeTypes.slice(0, 12).map(([type, count], idx) => ({
    id: `node-${type}`,
    symbol: type.substring(0, 2).toUpperCase(),
    name: type,
    value: count,
    category: 'node',
    color: `from-blue-${400 + idx % 3 * 100} to-blue-${500 + idx % 3 * 100}`
  })),
  ...relationshipTypes.slice(0, 8).map(([type, count], idx) => ({
    id: `rel-${type}`,
    symbol: type.substring(0, 3).toUpperCase(),
    name: type,
    value: count,
    category: 'relationship',
    color: `from-indigo-${400 + idx % 3 * 100} to-indigo-${500 + idx % 3 * 100}`
  }))];


  return (/*#__PURE__*/
    _jsxs("div", { className: "container mx-auto p-6 space-y-6", children: [/*#__PURE__*/
      _jsx(PageHeader, {
        title: "Dashboard",
        description: "Overview of your knowledge graph and system analytics",
        icon: /*#__PURE__*/_jsx(LayoutDashboard, { className: "h-6 w-6 text-primary" }) }
      ), /*#__PURE__*/


      _jsxs("div", { className: "relative overflow-hidden rounded-2xl bg-gradient-to-br from-primary/10 via-primary/5 to-background border-2 border-primary/20 shadow-lg p-8", children: [/*#__PURE__*/
        _jsx("div", { className: "absolute top-0 right-0 -mt-8 -mr-8 h-40 w-40 rounded-full bg-primary/10 blur-3xl" }), /*#__PURE__*/
        _jsx("div", { className: "absolute bottom-0 left-0 -mb-8 -ml-8 h-40 w-40 rounded-full bg-primary/10 blur-3xl" }), /*#__PURE__*/
        _jsx("div", { className: "relative", children: /*#__PURE__*/
          _jsxs("div", { className: "flex items-center gap-4 mb-4", children: [/*#__PURE__*/
            _jsx("div", { className: "h-16 w-16 rounded-2xl bg-gradient-to-br from-primary to-primary/80 flex items-center justify-center shadow-lg", children: /*#__PURE__*/
              _jsx(Database, { className: "h-8 w-8 text-primary-foreground" }) }
            ), /*#__PURE__*/
            _jsxs("div", { children: [/*#__PURE__*/
              _jsxs("div", { className: "flex items-center gap-3", children: [/*#__PURE__*/
                _jsx("h1", { className: "text-4xl font-bold tracking-tight", children: "Knowledge Graph Dashboard" }), /*#__PURE__*/
                _jsx(Badge, { className: "bg-green-500 text-white", children: "Online" })] }
              ), /*#__PURE__*/
              _jsx("p", { className: "text-lg text-muted-foreground", children: "Periodic table view of system components" })] }
            )] }
          ) }
        )] }
      ), /*#__PURE__*/


      _jsx("div", { className: "grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 xl:grid-cols-10 gap-2", children:
        gridItems.map((item, index) => /*#__PURE__*/
        _jsxs(Card, {

          className: "group relative overflow-hidden cursor-pointer transition-all duration-200 hover:scale-105 hover:shadow-lg hover:z-10",
          style: { animationDelay: `${index * 15}ms` }, children: [/*#__PURE__*/

          _jsx("div", { className: `absolute inset-0 bg-gradient-to-br ${item.color} opacity-8 group-hover:opacity-15 transition-opacity` }), /*#__PURE__*/
          _jsxs(CardContent, { className: "p-3 relative h-full flex flex-col items-center justify-center min-h-[85px]", children: [/*#__PURE__*/
            _jsx("div", { className: "text-xs text-muted-foreground mb-2 truncate w-full text-center leading-tight font-medium", children: item.name }), /*#__PURE__*/
            _jsx("div", { className: "text-2xl font-bold truncate w-full text-center", children: item.value.toLocaleString() }), /*#__PURE__*/
            _jsx(Badge, { variant: "outline", className: "text-[8px] px-1 py-0 mt-1.5 leading-none", children:
              item.category === 'system' ? 'SYS' : item.category === 'node' ? 'NOD' : 'REL' }
            )] }
          )] }, item.id
        )
        ) }
      ), /*#__PURE__*/


      _jsxs(Card, { children: [/*#__PURE__*/
        _jsx(CardHeader, { children: /*#__PURE__*/
          _jsxs(CardTitle, { className: "flex items-center gap-2", children: [/*#__PURE__*/
            _jsx(Activity, { className: "h-5 w-5 text-primary" }), "Quick Actions"] }

          ) }
        ), /*#__PURE__*/
        _jsx(CardContent, { children: /*#__PURE__*/
          _jsxs("div", { className: "grid grid-cols-2 md:grid-cols-4 gap-3", children: [/*#__PURE__*/
            _jsxs(Button, {
              variant: "outline",
              className: "h-20 flex flex-col gap-2 hover:bg-primary hover:text-primary-foreground transition-colors",
              onClick: () => navigate('/search'), children: [/*#__PURE__*/

              _jsx(Search, { className: "h-5 w-5" }), /*#__PURE__*/
              _jsx("span", { className: "text-sm font-medium", children: "Search" })] }
            ), /*#__PURE__*/
            _jsxs(Button, {
              variant: "outline",
              className: "h-20 flex flex-col gap-2 hover:bg-primary hover:text-primary-foreground transition-colors",
              onClick: () => navigate('/query-editor'), children: [/*#__PURE__*/

              _jsx(Terminal, { className: "h-5 w-5" }), /*#__PURE__*/
              _jsx("span", { className: "text-sm font-medium", children: "Query" })] }
            ), /*#__PURE__*/
            _jsxs(Button, {
              variant: "outline",
              className: "h-20 flex flex-col gap-2 hover:bg-primary hover:text-primary-foreground transition-colors",
              onClick: () => navigate('/requirements'), children: [/*#__PURE__*/

              _jsx(FileText, { className: "h-5 w-5" }), /*#__PURE__*/
              _jsx("span", { className: "text-sm font-medium", children: "Requirements" })] }
            ), /*#__PURE__*/
            _jsxs(Button, {
              variant: "outline",
              className: "h-20 flex flex-col gap-2 hover:bg-primary hover:text-primary-foreground transition-colors",
              onClick: () => navigate('/api-explorer'), children: [/*#__PURE__*/

              _jsx(Activity, { className: "h-5 w-5" }), /*#__PURE__*/
              _jsx("span", { className: "text-sm font-medium", children: "API" })] }
            )] }
          ) }
        )] }
      ), /*#__PURE__*/


      _jsxs(Card, { className: "border-2 border-primary/20 bg-gradient-to-br from-primary/5 to-background", children: [/*#__PURE__*/
        _jsxs(CardHeader, { children: [/*#__PURE__*/
          _jsxs(CardTitle, { className: "flex items-center gap-2", children: [/*#__PURE__*/
            _jsx(Sparkles, { className: "h-5 w-5 text-primary" }), "ISO 10303 Application Protocols"] }

          ), /*#__PURE__*/
          _jsx(CardDescription, { children: "Access standardized engineering data across the product lifecycle" }

          )] }
        ), /*#__PURE__*/
        _jsx(CardContent, { children: /*#__PURE__*/
          _jsxs("div", { className: "grid md:grid-cols-3 gap-4", children: [/*#__PURE__*/

            _jsxs(Card, { className: "cursor-pointer hover:shadow-lg transition-all hover:scale-105", onClick: () => navigate('/ap239/requirements'), children: [/*#__PURE__*/
              _jsx(CardHeader, { className: "pb-3", children: /*#__PURE__*/
                _jsxs("div", { className: "flex items-center justify-between", children: [/*#__PURE__*/
                  _jsx(Badge, { className: "bg-blue-500 text-white", children: "AP239" }), /*#__PURE__*/
                  _jsx(ArrowRight, { className: "h-4 w-4 text-muted-foreground" })] }
                ) }
              ), /*#__PURE__*/
              _jsxs(CardContent, { children: [/*#__PURE__*/
                _jsx("h3", { className: "font-semibold mb-1", children: "Requirements" }), /*#__PURE__*/
                _jsx("p", { className: "text-sm text-muted-foreground mb-3", children: "Product Life Cycle Support" }), /*#__PURE__*/
                _jsxs("div", { className: "text-xs text-muted-foreground space-y-1", children: [/*#__PURE__*/
                  _jsx("div", { children: "\u2022 Requirements Management" }), /*#__PURE__*/
                  _jsx("div", { children: "\u2022 Analysis & Specifications" }), /*#__PURE__*/
                  _jsx("div", { children: "\u2022 Change Control & Approvals" })] }
                )] }
              )] }
            ), /*#__PURE__*/


            _jsxs(Card, { className: "cursor-pointer hover:shadow-lg transition-all hover:scale-105", onClick: () => navigate('/ap242/parts'), children: [/*#__PURE__*/
              _jsx(CardHeader, { className: "pb-3", children: /*#__PURE__*/
                _jsxs("div", { className: "flex items-center justify-between", children: [/*#__PURE__*/
                  _jsx(Badge, { className: "bg-green-500 text-white", children: "AP242" }), /*#__PURE__*/
                  _jsx(ArrowRight, { className: "h-4 w-4 text-muted-foreground" })] }
                ) }
              ), /*#__PURE__*/
              _jsxs(CardContent, { children: [/*#__PURE__*/
                _jsx("h3", { className: "font-semibold mb-1", children: "Parts & Engineering" }), /*#__PURE__*/
                _jsx("p", { className: "text-sm text-muted-foreground mb-3", children: "3D Managed Product Data" }), /*#__PURE__*/
                _jsxs("div", { className: "text-xs text-muted-foreground space-y-1", children: [/*#__PURE__*/
                  _jsx("div", { children: "\u2022 Parts Catalog" }), /*#__PURE__*/
                  _jsx("div", { children: "\u2022 Materials & Properties" }), /*#__PURE__*/
                  _jsx("div", { children: "\u2022 CAD Geometry" })] }
                )] }
              )] }
            ), /*#__PURE__*/


            _jsxs(Card, { className: "cursor-pointer hover:shadow-lg transition-all hover:scale-105", onClick: () => navigate('/traceability'), children: [/*#__PURE__*/
              _jsx(CardHeader, { className: "pb-3", children: /*#__PURE__*/
                _jsxs("div", { className: "flex items-center justify-between", children: [/*#__PURE__*/
                  _jsx(Badge, { className: "bg-purple-500 text-white", children: "AP243" }), /*#__PURE__*/
                  _jsx(ArrowRight, { className: "h-4 w-4 text-muted-foreground" })] }
                ) }
              ), /*#__PURE__*/
              _jsxs(CardContent, { children: [/*#__PURE__*/
                _jsx("h3", { className: "font-semibold mb-1", children: "Reference Data" }), /*#__PURE__*/
                _jsx("p", { className: "text-sm text-muted-foreground mb-3", children: "Ontologies & Standards" }), /*#__PURE__*/
                _jsxs("div", { className: "text-xs text-muted-foreground space-y-1", children: [/*#__PURE__*/
                  _jsx("div", { children: "\u2022 Units & Measurements" }), /*#__PURE__*/
                  _jsx("div", { children: "\u2022 Classification Systems" }), /*#__PURE__*/
                  _jsx("div", { children: "\u2022 Cross-Schema Traceability" })] }
                )] }
              )] }
            )] }
          ) }
        )] }
      ), /*#__PURE__*/


      _jsxs(Card, { className: "border-dashed", children: [/*#__PURE__*/
        _jsx(CardHeader, { children: /*#__PURE__*/
          _jsxs(CardTitle, { className: "flex items-center gap-2", children: [/*#__PURE__*/
            _jsx(Database, { className: "h-5 w-5 text-green-500" }), "System Status"] }

          ) }
        ), /*#__PURE__*/
        _jsx(CardContent, { children: /*#__PURE__*/
          _jsxs("div", { className: "grid gap-4 md:grid-cols-4", children: [/*#__PURE__*/
            _jsxs("div", { className: "space-y-1", children: [/*#__PURE__*/
              _jsx("p", { className: "text-sm text-muted-foreground", children: "Platform" }), /*#__PURE__*/
              _jsxs("div", { className: "flex items-center gap-2", children: [/*#__PURE__*/
                _jsx("div", { className: "h-2 w-2 rounded-full bg-green-500 animate-pulse" }), /*#__PURE__*/
                _jsx("p", { className: "font-semibold", children: "Active" })] }
              )] }
            ), /*#__PURE__*/
            _jsxs("div", { className: "space-y-1", children: [/*#__PURE__*/
              _jsx("p", { className: "text-sm text-muted-foreground", children: "Database" }), /*#__PURE__*/
              _jsx("p", { className: "font-semibold", children: "Neo4j Aura" })] }
            ), /*#__PURE__*/
            _jsxs("div", { className: "space-y-1", children: [/*#__PURE__*/
              _jsx("p", { className: "text-sm text-muted-foreground", children: "Protocol" }), /*#__PURE__*/
              _jsx("p", { className: "font-semibold", children: "ISO 10303 SMRL" })] }
            ), /*#__PURE__*/
            _jsxs("div", { className: "space-y-1", children: [/*#__PURE__*/
              _jsx("p", { className: "text-sm text-muted-foreground", children: "Security" }), /*#__PURE__*/
              _jsx("p", { className: "font-semibold", children: "Enterprise" })] }
            )] }
          ) }
        )] }
      )] }
    ));

}
