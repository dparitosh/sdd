import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@ui/card';
import { Badge } from '@ui/badge';
import { Button } from '@ui/button';
import { Workflow, Play, Plus, GitBranch, CheckCircle2 } from 'lucide-react';
import PageHeader from '@/components/PageHeader';import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";

export default function WorkflowStudio() {
  const workflows = [
  {
    name: 'Standard Thermal Analysis',
    steps: 5,
    status: 'active',
    lastRun: '2 hours ago',
    runs: 45
  },
  {
    name: 'Multi-Physics Simulation',
    steps: 8,
    status: 'draft',
    lastRun: 'Never',
    runs: 0
  },
  {
    name: 'Structural Validation Suite',
    steps: 6,
    status: 'active',
    lastRun: '1 day ago',
    runs: 23
  }];


  return (/*#__PURE__*/
    _jsxs("div", { className: "container mx-auto p-6 space-y-6", children: [/*#__PURE__*/
      _jsx(PageHeader, {
        title: "Workflow Studio",
        description: "Design and execute automated simulation workflows",
        icon: /*#__PURE__*/_jsx(Workflow, { className: "h-8 w-8 text-primary" }),
        breadcrumbs: [
        { label: 'Simulation Engineering', href: '/simulation/models' },
        { label: 'Workflow Studio' }],

        actions: /*#__PURE__*/
        _jsxs(Button, { children: [/*#__PURE__*/
          _jsx(Plus, { className: "h-4 w-4 mr-2" }), "Create Workflow"] }

        ) }

      ), /*#__PURE__*/


      _jsx("div", { className: "space-y-4", children:
        workflows.map((workflow, idx) => /*#__PURE__*/
        _jsxs(Card, { className: "hover:shadow-md transition-shadow", children: [/*#__PURE__*/
          _jsx(CardHeader, { children: /*#__PURE__*/
            _jsxs("div", { className: "flex items-center justify-between", children: [/*#__PURE__*/
              _jsxs("div", { children: [/*#__PURE__*/
                _jsxs(CardTitle, { className: "flex items-center gap-3", children: [
                  workflow.name, /*#__PURE__*/
                  _jsx(Badge, { variant: workflow.status === 'active' ? 'default' : 'secondary', children:
                    workflow.status }
                  )] }
                ), /*#__PURE__*/
                _jsxs(CardDescription, { className: "mt-2", children: [
                  workflow.steps, " steps \xB7 ", workflow.runs, " total runs \xB7 Last run ", workflow.lastRun] }
                )] }
              ), /*#__PURE__*/
              _jsxs("div", { className: "flex gap-2", children: [/*#__PURE__*/
                _jsxs(Button, { variant: "outline", size: "sm", children: [/*#__PURE__*/
                  _jsx(GitBranch, { className: "h-4 w-4 mr-2" }), "Edit"] }

                ), /*#__PURE__*/
                _jsxs(Button, { size: "sm", children: [/*#__PURE__*/
                  _jsx(Play, { className: "h-4 w-4 mr-2" }), "Run"] }

                )] }
              )] }
            ) }
          ), /*#__PURE__*/
          _jsx(CardContent, { children: /*#__PURE__*/

            _jsx("div", { className: "flex items-center gap-2 overflow-x-auto pb-2", children:
              Array.from({ length: workflow.steps }).map((_, stepIdx) => /*#__PURE__*/
              _jsxs("div", { className: "flex items-center", children: [/*#__PURE__*/
                _jsx("div", { className: "flex items-center justify-center h-10 w-10 rounded-full bg-primary/10 text-primary font-medium text-sm flex-shrink-0", children:
                  stepIdx + 1 }
                ),
                stepIdx < workflow.steps - 1 && /*#__PURE__*/
                _jsx("div", { className: "h-0.5 w-8 bg-muted mx-1" })] }, stepIdx

              )
              ) }
            ) }
          )] }, idx
        )
        ) }
      ), /*#__PURE__*/


      _jsxs(Card, { className: "bg-gradient-to-br from-primary/5 to-primary/10", children: [/*#__PURE__*/
        _jsxs(CardHeader, { children: [/*#__PURE__*/
          _jsx(CardTitle, { children: "Visual Workflow Builder" }), /*#__PURE__*/
          _jsx(CardDescription, { children: "Drag-and-drop interface coming soon" })] }
        ), /*#__PURE__*/
        _jsx(CardContent, { children: /*#__PURE__*/
          _jsxs("div", { className: "grid grid-cols-1 md:grid-cols-3 gap-4", children: [/*#__PURE__*/
            _jsxs("div", { className: "p-4 border-2 border-dashed rounded-lg text-center", children: [/*#__PURE__*/
              _jsx(CheckCircle2, { className: "h-8 w-8 mx-auto mb-2 text-muted-foreground" }), /*#__PURE__*/
              _jsx("p", { className: "text-sm font-medium", children: "Input Configuration" }), /*#__PURE__*/
              _jsx("p", { className: "text-xs text-muted-foreground", children: "Define workflow inputs" })] }
            ), /*#__PURE__*/
            _jsxs("div", { className: "p-4 border-2 border-dashed rounded-lg text-center", children: [/*#__PURE__*/
              _jsx(Workflow, { className: "h-8 w-8 mx-auto mb-2 text-muted-foreground" }), /*#__PURE__*/
              _jsx("p", { className: "text-sm font-medium", children: "Processing Steps" }), /*#__PURE__*/
              _jsx("p", { className: "text-xs text-muted-foreground", children: "Chain simulation tasks" })] }
            ), /*#__PURE__*/
            _jsxs("div", { className: "p-4 border-2 border-dashed rounded-lg text-center", children: [/*#__PURE__*/
              _jsx(CheckCircle2, { className: "h-8 w-8 mx-auto mb-2 text-muted-foreground" }), /*#__PURE__*/
              _jsx("p", { className: "text-sm font-medium", children: "Output Collection" }), /*#__PURE__*/
              _jsx("p", { className: "text-xs text-muted-foreground", children: "Store and analyze results" })] }
            )] }
          ) }
        )] }
      ), /*#__PURE__*/


      _jsxs("div", { className: "grid grid-cols-1 md:grid-cols-4 gap-4", children: [/*#__PURE__*/
        _jsx(Card, { children: /*#__PURE__*/
          _jsxs(CardContent, { className: "pt-6", children: [/*#__PURE__*/
            _jsx("div", { className: "text-2xl font-bold", children: "8" }), /*#__PURE__*/
            _jsx("p", { className: "text-sm text-muted-foreground", children: "Active Workflows" })] }
          ) }
        ), /*#__PURE__*/
        _jsx(Card, { children: /*#__PURE__*/
          _jsxs(CardContent, { className: "pt-6", children: [/*#__PURE__*/
            _jsx("div", { className: "text-2xl font-bold text-green-500", children: "156" }), /*#__PURE__*/
            _jsx("p", { className: "text-sm text-muted-foreground", children: "Successful Runs" })] }
          ) }
        ), /*#__PURE__*/
        _jsx(Card, { children: /*#__PURE__*/
          _jsxs(CardContent, { className: "pt-6", children: [/*#__PURE__*/
            _jsx("div", { className: "text-2xl font-bold text-blue-500", children: "2.3h" }), /*#__PURE__*/
            _jsx("p", { className: "text-sm text-muted-foreground", children: "Avg Execution Time" })] }
          ) }
        ), /*#__PURE__*/
        _jsx(Card, { children: /*#__PURE__*/
          _jsxs(CardContent, { className: "pt-6", children: [/*#__PURE__*/
            _jsx("div", { className: "text-2xl font-bold text-amber-500", children: "3" }), /*#__PURE__*/
            _jsx("p", { className: "text-sm text-muted-foreground", children: "Queued Jobs" })] }
          ) }
        )] }
      )] }
    ));

}
