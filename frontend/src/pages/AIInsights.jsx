import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@ui/card';
import { Badge } from '@ui/badge';
import { Button } from '@ui/button';
import { Lightbulb, TrendingUp, AlertCircle, Sparkles } from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import { toast } from 'sonner';import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";

export default function AIInsights() {
  const handleGenerateInsights = () => {
    toast.success('Generating AI Insights', {
      description: 'Analyzing knowledge graph for new recommendations...'
    });
  };

  const handleViewDetails = (type) => {
    toast.info(`Opening ${type} Details`, {
      description: 'Loading detailed analysis and recommendations...'
    });
  };

  return (/*#__PURE__*/
    _jsxs("div", { className: "container mx-auto p-6 space-y-6", children: [/*#__PURE__*/
      _jsx(PageHeader, {
        title: "AI Insights",
        description: "Intelligent recommendations and insights from your knowledge graph",
        icon: /*#__PURE__*/_jsx(Lightbulb, { className: "h-8 w-8 text-primary" }),
        badge: "AI-Powered",
        breadcrumbs: [
        { label: 'GenAI Studio', href: '/ai/insights' },
        { label: 'AI Insights' }],

        actions: /*#__PURE__*/
        _jsxs(Button, { onClick: handleGenerateInsights, children: [/*#__PURE__*/
          _jsx(Sparkles, { className: "h-4 w-4 mr-2" }), "Generate Insights"] }

        ) }

      ), /*#__PURE__*/


      _jsxs("div", { className: "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6", children: [/*#__PURE__*/
        _jsxs(Card, { className: "border-l-4 border-l-blue-500", children: [/*#__PURE__*/
          _jsxs(CardHeader, { children: [/*#__PURE__*/
            _jsxs(CardTitle, { className: "flex items-center gap-2", children: [/*#__PURE__*/
              _jsx(TrendingUp, { className: "h-5 w-5 text-blue-500" }), "Requirements Impact"] }

            ), /*#__PURE__*/
            _jsx(CardDescription, { children: "High Priority" })] }
          ), /*#__PURE__*/
          _jsxs(CardContent, { children: [/*#__PURE__*/
            _jsx("p", { className: "text-sm", children: "23 requirements may be affected by recent design changes in the propulsion system." }

            ), /*#__PURE__*/
            _jsx(Button, { variant: "link", className: "mt-2 p-0", onClick: () => handleViewDetails('Requirements Impact'), children: "View Details \u2192" })] }
          )] }
        ), /*#__PURE__*/

        _jsxs(Card, { className: "border-l-4 border-l-amber-500", children: [/*#__PURE__*/
          _jsxs(CardHeader, { children: [/*#__PURE__*/
            _jsxs(CardTitle, { className: "flex items-center gap-2", children: [/*#__PURE__*/
              _jsx(AlertCircle, { className: "h-5 w-5 text-amber-500" }), "Missing Traceability"] }

            ), /*#__PURE__*/
            _jsx(CardDescription, { children: "Attention Needed" })] }
          ), /*#__PURE__*/
          _jsxs(CardContent, { children: [/*#__PURE__*/
            _jsx("p", { className: "text-sm", children: "15 components lack traceability links to requirements. AI suggests likely connections." }

            ), /*#__PURE__*/
            _jsx(Button, { variant: "link", className: "mt-2 p-0", onClick: () => handleViewDetails('Traceability Suggestions'), children: "Review Suggestions \u2192" })] }
          )] }
        ), /*#__PURE__*/

        _jsxs(Card, { className: "border-l-4 border-l-green-500", children: [/*#__PURE__*/
          _jsxs(CardHeader, { children: [/*#__PURE__*/
            _jsxs(CardTitle, { className: "flex items-center gap-2", children: [/*#__PURE__*/
              _jsx(Sparkles, { className: "h-5 w-5 text-green-500" }), "Optimization Opportunity"] }

            ), /*#__PURE__*/
            _jsx(CardDescription, { children: "Recommended" })] }
          ), /*#__PURE__*/
          _jsxs(CardContent, { children: [/*#__PURE__*/
            _jsx("p", { className: "text-sm", children: "Similar patterns detected in 3 simulation models. Consider creating reusable template." }

            ), /*#__PURE__*/
            _jsx(Button, { variant: "link", className: "mt-2 p-0", onClick: () => handleViewDetails('Optimization Patterns'), children: "Explore \u2192" })] }
          )] }
        )] }
      ), /*#__PURE__*/


      _jsxs(Card, { className: "bg-gradient-to-br from-primary/5 to-primary/10", children: [/*#__PURE__*/
        _jsxs(CardHeader, { children: [/*#__PURE__*/
          _jsx(CardTitle, { children: "More AI Features Coming Soon" }), /*#__PURE__*/
          _jsx(CardDescription, { children: "We're continuously adding new AI capabilities" })] }
        ), /*#__PURE__*/
        _jsxs(CardContent, { className: "space-y-2", children: [/*#__PURE__*/
          _jsxs("div", { className: "flex items-center gap-2", children: [/*#__PURE__*/
            _jsx(Badge, { variant: "outline", children: "Coming Soon" }), /*#__PURE__*/
            _jsx("span", { className: "text-sm", children: "Automated risk assessment" })] }
          ), /*#__PURE__*/
          _jsxs("div", { className: "flex items-center gap-2", children: [/*#__PURE__*/
            _jsx(Badge, { variant: "outline", children: "Coming Soon" }), /*#__PURE__*/
            _jsx("span", { className: "text-sm", children: "Predictive maintenance suggestions" })] }
          ), /*#__PURE__*/
          _jsxs("div", { className: "flex items-center gap-2", children: [/*#__PURE__*/
            _jsx(Badge, { variant: "outline", children: "Coming Soon" }), /*#__PURE__*/
            _jsx("span", { className: "text-sm", children: "Smart documentation generation" })] }
          )] }
        )] }
      )] }
    ));

}
