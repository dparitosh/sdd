import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@ui/card';
import { Badge } from '@ui/badge';
import { Button } from '@ui/button';
import { Brain, Network, Activity, Play } from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import { toast } from 'sonner';import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";

export default function SmartAnalysis() {
  const handleRunAnalysis = () => {
    toast.success('Starting Analysis', {
      description: 'Running AI-powered analysis on your knowledge graph...'
    });
  };

  const handleStartImpactAnalysis = () => {
    toast.info('Impact Analysis', {
      description: 'Identifying affected components and requirements...'
    });
  };

  const handleAnalyzePropagation = () => {
    toast.info('Change Propagation', {
      description: 'Tracing change ripple effects through the system...'
    });
  };

  const handleViewResults = (analysisName) => {
    toast.info(`${analysisName} Results`, {
      description: 'Loading analysis results and recommendations...'
    });
  };

  return (/*#__PURE__*/
    _jsxs("div", { className: "container mx-auto p-6 space-y-6", children: [/*#__PURE__*/
      _jsx(PageHeader, {
        title: "Smart Analysis",
        description: "Automated impact analysis and change propagation",
        icon: /*#__PURE__*/_jsx(Brain, { className: "h-8 w-8 text-primary" }),
        badge: "AI-Powered",
        breadcrumbs: [
        { label: 'GenAI Studio', href: '/ai/insights' },
        { label: 'Smart Analysis' }],

        actions: /*#__PURE__*/
        _jsxs(Button, { onClick: handleRunAnalysis, children: [/*#__PURE__*/
          _jsx(Play, { className: "h-4 w-4 mr-2" }), "Run Analysis"] }

        ) }

      ), /*#__PURE__*/


      _jsxs("div", { className: "grid grid-cols-1 md:grid-cols-2 gap-6", children: [/*#__PURE__*/
        _jsxs(Card, { className: "hover:shadow-lg transition-shadow", children: [/*#__PURE__*/
          _jsxs(CardHeader, { children: [/*#__PURE__*/
            _jsxs(CardTitle, { className: "flex items-center gap-2", children: [/*#__PURE__*/
              _jsx(Network, { className: "h-5 w-5 text-primary" }), "Impact Analysis"] }

            ), /*#__PURE__*/
            _jsx(CardDescription, { children: "Understand downstream effects of changes" })] }
          ), /*#__PURE__*/
          _jsxs(CardContent, { children: [/*#__PURE__*/
            _jsx("p", { className: "text-sm mb-4", children: "AI-powered analysis to identify all components, requirements, and simulations affected by proposed changes." }

            ), /*#__PURE__*/
            _jsx(Button, { variant: "outline", className: "w-full", onClick: handleStartImpactAnalysis, children: "Start Impact Analysis" })] }
          )] }
        ), /*#__PURE__*/

        _jsxs(Card, { className: "hover:shadow-lg transition-shadow", children: [/*#__PURE__*/
          _jsxs(CardHeader, { children: [/*#__PURE__*/
            _jsxs(CardTitle, { className: "flex items-center gap-2", children: [/*#__PURE__*/
              _jsx(Activity, { className: "h-5 w-5 text-primary" }), "Change Propagation"] }

            ), /*#__PURE__*/
            _jsx(CardDescription, { children: "Trace change ripple effects" })] }
          ), /*#__PURE__*/
          _jsxs(CardContent, { children: [/*#__PURE__*/
            _jsx("p", { className: "text-sm mb-4", children: "Automatically propagate design changes through the knowledge graph and identify required updates." }

            ), /*#__PURE__*/
            _jsx(Button, { variant: "outline", className: "w-full", onClick: handleAnalyzePropagation, children: "Analyze Propagation" })] }
          )] }
        )] }
      ), /*#__PURE__*/


      _jsxs(Card, { children: [/*#__PURE__*/
        _jsxs(CardHeader, { children: [/*#__PURE__*/
          _jsx(CardTitle, { children: "Recent Analyses" }), /*#__PURE__*/
          _jsx(CardDescription, { children: "Previously run impact and change analyses" })] }
        ), /*#__PURE__*/
        _jsx(CardContent, { children: /*#__PURE__*/
          _jsxs("div", { className: "space-y-4", children: [/*#__PURE__*/
            _jsxs("div", { className: "flex items-center justify-between p-4 border rounded-lg", children: [/*#__PURE__*/
              _jsxs("div", { children: [/*#__PURE__*/
                _jsx("p", { className: "font-medium", children: "Propulsion System Update" }), /*#__PURE__*/
                _jsx("p", { className: "text-sm text-muted-foreground", children: "Analyzed 2 hours ago" })] }
              ), /*#__PURE__*/
              _jsxs("div", { className: "flex items-center gap-2", children: [/*#__PURE__*/
                _jsx(Badge, { variant: "outline", children: "45 impacts found" }), /*#__PURE__*/
                _jsx(Button, { variant: "ghost", size: "sm", onClick: () => handleViewResults('Propulsion System Update'), children: "View Results" })] }
              )] }
            ), /*#__PURE__*/
            _jsxs("div", { className: "flex items-center justify-between p-4 border rounded-lg", children: [/*#__PURE__*/
              _jsxs("div", { children: [/*#__PURE__*/
                _jsx("p", { className: "font-medium", children: "Thermal Analysis Changes" }), /*#__PURE__*/
                _jsx("p", { className: "text-sm text-muted-foreground", children: "Analyzed yesterday" })] }
              ), /*#__PURE__*/
              _jsxs("div", { className: "flex items-center gap-2", children: [/*#__PURE__*/
                _jsx(Badge, { variant: "outline", children: "12 impacts found" }), /*#__PURE__*/
                _jsx(Button, { variant: "ghost", size: "sm", onClick: () => handleViewResults('Thermal Analysis Changes'), children: "View Results" })] }
              )] }
            )] }
          ) }
        )] }
      )] }
    ));

}
