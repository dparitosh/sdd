import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@ui/card';
import { Badge } from '@ui/badge';
import { Button } from '@ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@ui/tabs';
import { TrendingUp, Download, Share2, BarChart3, LineChart, PieChart } from 'lucide-react';
import PageHeader from '@/components/PageHeader';import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";

export default function ResultsAnalysis() {
  const results = [
  {
    name: 'Thermal Analysis - Run #45',
    timestamp: '2 hours ago',
    status: 'completed',
    metric: '342.5°C max temp'
  },
  {
    name: 'Structural FEA - Run #12',
    timestamp: '1 day ago',
    status: 'completed',
    metric: '125 MPa max stress'
  },
  {
    name: 'Propulsion Test - Run #8',
    timestamp: '3 days ago',
    status: 'completed',
    metric: '98.5% efficiency'
  }];


  return (/*#__PURE__*/
    _jsxs("div", { className: "container mx-auto p-6 space-y-6", children: [/*#__PURE__*/
      _jsx(PageHeader, {
        title: "Results Analysis",
        description: "Analyze and visualize simulation outputs",
        icon: /*#__PURE__*/_jsx(TrendingUp, { className: "h-8 w-8 text-primary" }),
        breadcrumbs: [
        { label: 'Simulation Engineering', href: '/simulation/models' },
        { label: 'Results Analysis' }],

        actions: /*#__PURE__*/
        _jsxs(_Fragment, { children: [/*#__PURE__*/
          _jsxs(Button, { variant: "outline", children: [/*#__PURE__*/
            _jsx(Download, { className: "h-4 w-4 mr-2" }), "Export"] }

          ), /*#__PURE__*/
          _jsxs(Button, { variant: "outline", children: [/*#__PURE__*/
            _jsx(Share2, { className: "h-4 w-4 mr-2" }), "Share"] }

          )] }
        ) }

      ), /*#__PURE__*/


      _jsxs(Card, { children: [/*#__PURE__*/
        _jsxs(CardHeader, { children: [/*#__PURE__*/
          _jsx(CardTitle, { children: "Recent Simulation Results" }), /*#__PURE__*/
          _jsx(CardDescription, { children: "Latest completed analysis runs" })] }
        ), /*#__PURE__*/
        _jsx(CardContent, { children: /*#__PURE__*/
          _jsx("div", { className: "space-y-3", children:
            results.map((result, idx) => /*#__PURE__*/
            _jsxs("div", { className: "flex items-center justify-between p-4 border rounded-lg hover:bg-accent/50 transition-colors", children: [/*#__PURE__*/
              _jsxs("div", { children: [/*#__PURE__*/
                _jsx("p", { className: "font-medium", children: result.name }), /*#__PURE__*/
                _jsx("p", { className: "text-sm text-muted-foreground", children: result.timestamp })] }
              ), /*#__PURE__*/
              _jsxs("div", { className: "flex items-center gap-3", children: [/*#__PURE__*/
                _jsx(Badge, { variant: "outline", children: result.metric }), /*#__PURE__*/
                _jsx(Badge, { className: "bg-green-500", children: result.status }), /*#__PURE__*/
                _jsx(Button, { variant: "ghost", size: "sm", children: "View Details" })] }
              )] }, idx
            )
            ) }
          ) }
        )] }
      ), /*#__PURE__*/


      _jsxs(Card, { children: [/*#__PURE__*/
        _jsxs(CardHeader, { children: [/*#__PURE__*/
          _jsx(CardTitle, { children: "Result Visualization" }), /*#__PURE__*/
          _jsx(CardDescription, { children: "Interactive charts and data exploration" })] }
        ), /*#__PURE__*/
        _jsx(CardContent, { children: /*#__PURE__*/
          _jsxs(Tabs, { defaultValue: "charts", className: "w-full", children: [/*#__PURE__*/
            _jsxs(TabsList, { className: "grid w-full grid-cols-3", children: [/*#__PURE__*/
              _jsxs(TabsTrigger, { value: "charts", children: [/*#__PURE__*/
                _jsx(BarChart3, { className: "h-4 w-4 mr-2" }), "Charts"] }

              ), /*#__PURE__*/
              _jsxs(TabsTrigger, { value: "trends", children: [/*#__PURE__*/
                _jsx(LineChart, { className: "h-4 w-4 mr-2" }), "Trends"] }

              ), /*#__PURE__*/
              _jsxs(TabsTrigger, { value: "comparison", children: [/*#__PURE__*/
                _jsx(PieChart, { className: "h-4 w-4 mr-2" }), "Comparison"] }

              )] }
            ), /*#__PURE__*/

            _jsx(TabsContent, { value: "charts", className: "space-y-4", children: /*#__PURE__*/
              _jsx("div", { className: "h-64 border-2 border-dashed rounded-lg flex items-center justify-center", children: /*#__PURE__*/
                _jsxs("div", { className: "text-center", children: [/*#__PURE__*/
                  _jsx(BarChart3, { className: "h-12 w-12 mx-auto mb-2 text-muted-foreground" }), /*#__PURE__*/
                  _jsx("p", { className: "text-sm text-muted-foreground", children: "Interactive charts will be displayed here" }), /*#__PURE__*/
                  _jsx("p", { className: "text-xs text-muted-foreground", children: "Select a result to visualize" })] }
                ) }
              ) }
            ), /*#__PURE__*/

            _jsx(TabsContent, { value: "trends", className: "space-y-4", children: /*#__PURE__*/
              _jsx("div", { className: "h-64 border-2 border-dashed rounded-lg flex items-center justify-center", children: /*#__PURE__*/
                _jsxs("div", { className: "text-center", children: [/*#__PURE__*/
                  _jsx(LineChart, { className: "h-12 w-12 mx-auto mb-2 text-muted-foreground" }), /*#__PURE__*/
                  _jsx("p", { className: "text-sm text-muted-foreground", children: "Trend analysis coming soon" }), /*#__PURE__*/
                  _jsx("p", { className: "text-xs text-muted-foreground", children: "Track metrics over time" })] }
                ) }
              ) }
            ), /*#__PURE__*/

            _jsx(TabsContent, { value: "comparison", className: "space-y-4", children: /*#__PURE__*/
              _jsx("div", { className: "h-64 border-2 border-dashed rounded-lg flex items-center justify-center", children: /*#__PURE__*/
                _jsxs("div", { className: "text-center", children: [/*#__PURE__*/
                  _jsx(PieChart, { className: "h-12 w-12 mx-auto mb-2 text-muted-foreground" }), /*#__PURE__*/
                  _jsx("p", { className: "text-sm text-muted-foreground", children: "Comparison view coming soon" }), /*#__PURE__*/
                  _jsx("p", { className: "text-xs text-muted-foreground", children: "Compare multiple results side-by-side" })] }
                ) }
              ) }
            )] }
          ) }
        )] }
      ), /*#__PURE__*/


      _jsxs("div", { className: "grid grid-cols-1 md:grid-cols-4 gap-4", children: [/*#__PURE__*/
        _jsx(Card, { children: /*#__PURE__*/
          _jsxs(CardContent, { className: "pt-6", children: [/*#__PURE__*/
            _jsx("div", { className: "text-2xl font-bold", children: "156" }), /*#__PURE__*/
            _jsx("p", { className: "text-sm text-muted-foreground", children: "Total Runs" })] }
          ) }
        ), /*#__PURE__*/
        _jsx(Card, { children: /*#__PURE__*/
          _jsxs(CardContent, { className: "pt-6", children: [/*#__PURE__*/
            _jsx("div", { className: "text-2xl font-bold text-green-500", children: "98.2%" }), /*#__PURE__*/
            _jsx("p", { className: "text-sm text-muted-foreground", children: "Success Rate" })] }
          ) }
        ), /*#__PURE__*/
        _jsx(Card, { children: /*#__PURE__*/
          _jsxs(CardContent, { className: "pt-6", children: [/*#__PURE__*/
            _jsx("div", { className: "text-2xl font-bold text-blue-500", children: "45.2 GB" }), /*#__PURE__*/
            _jsx("p", { className: "text-sm text-muted-foreground", children: "Data Stored" })] }
          ) }
        ), /*#__PURE__*/
        _jsx(Card, { children: /*#__PURE__*/
          _jsxs(CardContent, { className: "pt-6", children: [/*#__PURE__*/
            _jsx("div", { className: "text-2xl font-bold text-amber-500", children: "1.8h" }), /*#__PURE__*/
            _jsx("p", { className: "text-sm text-muted-foreground", children: "Avg Runtime" })] }
          ) }
        )] }
      )] }
    ));

}
