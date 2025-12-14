import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@ui/card';
import { Badge } from '@ui/badge';
import { Button } from '@ui/button';
import { Input } from '@ui/input';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '@ui/dialog';
import { Boxes, Search, Plus, FileCode, Clock, Eye, Pencil } from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import { toast } from 'sonner';import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";













export default function ModelRepository() {
  const [selectedModel, setSelectedModel] = useState(null);
  const [isViewOpen, setIsViewOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);

  const models = [
  {
    id: 1,
    name: 'Thermal Analysis v2.3',
    type: 'CFD',
    lastModified: '2 days ago',
    status: 'validated',
    description: 'Comprehensive thermal analysis model for propulsion systems',
    author: 'Engineering Team',
    version: '2.3.1',
    tags: ['thermal', 'cfd', 'propulsion']
  },
  {
    id: 2,
    name: 'Structural FEA Model',
    type: 'FEA',
    lastModified: '1 week ago',
    status: 'draft',
    description: 'Finite element analysis for structural integrity',
    author: 'Structures Team',
    version: '1.0.0',
    tags: ['structural', 'fea', 'analysis']
  },
  {
    id: 3,
    name: 'Propulsion Simulation',
    type: 'System',
    lastModified: '3 days ago',
    status: 'validated',
    description: 'End-to-end propulsion system simulation',
    author: 'Systems Team',
    version: '3.2.0',
    tags: ['propulsion', 'system', 'dynamics']
  },
  {
    id: 4,
    name: 'Aerodynamics Study',
    type: 'CFD',
    lastModified: '5 days ago',
    status: 'archived',
    description: 'Aerodynamic flow analysis and optimization',
    author: 'Aero Team',
    version: '1.5.2',
    tags: ['aerodynamics', 'cfd', 'flow']
  }];


  const getStatusColor = (status) => {
    switch (status) {
      case 'validated':return 'bg-green-500';
      case 'draft':return 'bg-amber-500';
      case 'archived':return 'bg-gray-500';
      default:return 'bg-blue-500';
    }
  };

  const handleView = (model) => {
    setSelectedModel(model);
    setIsViewOpen(true);
  };

  const handleEdit = (model) => {
    setSelectedModel(model);
    setIsEditOpen(true);
  };

  const handleAddNew = () => {
    toast.info('Add New Model', {
      description: 'Opening model creation wizard...'
    });
  };

  const handleSaveEdit = () => {
    toast.success('Model Updated', {
      description: `${selectedModel?.name} has been updated successfully.`
    });
    setIsEditOpen(false);
    setSelectedModel(null);
  };

  return (/*#__PURE__*/
    _jsxs("div", { className: "container mx-auto p-6 space-y-6", children: [/*#__PURE__*/
      _jsx(PageHeader, {
        title: "Model Repository",
        description: "Centralized library of simulation models and analysis templates",
        icon: /*#__PURE__*/_jsx(Boxes, { className: "h-8 w-8 text-primary" }),
        breadcrumbs: [
        { label: 'Simulation Engineering', href: '/simulation/models' },
        { label: 'Model Repository' }],

        actions: /*#__PURE__*/
        _jsxs(Button, { onClick: handleAddNew, children: [/*#__PURE__*/
          _jsx(Plus, { className: "h-4 w-4 mr-2" }), "Add New Model"] }

        ) }

      ), /*#__PURE__*/


      _jsx(Card, { children: /*#__PURE__*/
        _jsx(CardContent, { className: "pt-6", children: /*#__PURE__*/
          _jsxs("div", { className: "flex gap-4", children: [/*#__PURE__*/
            _jsxs("div", { className: "relative flex-1", children: [/*#__PURE__*/
              _jsx(Search, { className: "absolute left-3 top-3 h-4 w-4 text-muted-foreground" }), /*#__PURE__*/
              _jsx(Input, { placeholder: "Search models by name, type, or tags...", className: "pl-10" })] }
            ), /*#__PURE__*/
            _jsxs(Button, { variant: "outline", children: [/*#__PURE__*/
              _jsx(FileCode, { className: "h-4 w-4 mr-2" }), "Filter by Type"] }

            )] }
          ) }
        ) }
      ), /*#__PURE__*/


      _jsx("div", { className: "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6", children:
        models.map((model, idx) => /*#__PURE__*/
        _jsxs(Card, { className: "hover:shadow-lg transition-shadow", children: [/*#__PURE__*/
          _jsxs(CardHeader, { children: [/*#__PURE__*/
            _jsxs("div", { className: "flex items-start justify-between", children: [/*#__PURE__*/
              _jsx(CardTitle, { className: "text-lg", children: model.name }), /*#__PURE__*/
              _jsx("div", { className: `h-2 w-2 rounded-full ${getStatusColor(model.status)}` })] }
            ), /*#__PURE__*/
            _jsxs(CardDescription, { children: [model.type, " Model"] })] }
          ), /*#__PURE__*/
          _jsxs(CardContent, { className: "space-y-4", children: [/*#__PURE__*/
            _jsxs("div", { className: "flex items-center gap-2 text-sm text-muted-foreground", children: [/*#__PURE__*/
              _jsx(Clock, { className: "h-4 w-4" }), "Modified ",
              model.lastModified] }
            ), /*#__PURE__*/
            _jsxs("div", { className: "flex gap-2", children: [/*#__PURE__*/
              _jsx(Badge, { variant: "outline", className: "capitalize", children: model.status }), /*#__PURE__*/
              _jsx(Badge, { variant: "secondary", children: model.type })] }
            ), /*#__PURE__*/
            _jsxs("div", { className: "flex gap-2 pt-2", children: [/*#__PURE__*/
              _jsx(Button, {
                variant: "outline",
                size: "sm",
                className: "flex-1",
                onClick: () => handleView(model), children:
                "View" }

              ), /*#__PURE__*/
              _jsx(Button, {
                variant: "outline",
                size: "sm",
                className: "flex-1",
                onClick: () => handleEdit(model), children:
                "Edit" }

              )] }
            )] }
          )] }, idx
        )
        ) }
      ), /*#__PURE__*/


      _jsxs("div", { className: "grid grid-cols-1 md:grid-cols-4 gap-4", children: [/*#__PURE__*/
        _jsx(Card, { children: /*#__PURE__*/
          _jsxs(CardContent, { className: "pt-6", children: [/*#__PURE__*/
            _jsx("div", { className: "text-2xl font-bold", children: "24" }), /*#__PURE__*/
            _jsx("p", { className: "text-sm text-muted-foreground", children: "Total Models" })] }
          ) }
        ), /*#__PURE__*/
        _jsx(Card, { children: /*#__PURE__*/
          _jsxs(CardContent, { className: "pt-6", children: [/*#__PURE__*/
            _jsx("div", { className: "text-2xl font-bold text-green-500", children: "12" }), /*#__PURE__*/
            _jsx("p", { className: "text-sm text-muted-foreground", children: "Validated" })] }
          ) }
        ), /*#__PURE__*/
        _jsx(Card, { children: /*#__PURE__*/
          _jsxs(CardContent, { className: "pt-6", children: [/*#__PURE__*/
            _jsx("div", { className: "text-2xl font-bold text-amber-500", children: "8" }), /*#__PURE__*/
            _jsx("p", { className: "text-sm text-muted-foreground", children: "In Draft" })] }
          ) }
        ), /*#__PURE__*/
        _jsx(Card, { children: /*#__PURE__*/
          _jsxs(CardContent, { className: "pt-6", children: [/*#__PURE__*/
            _jsx("div", { className: "text-2xl font-bold text-blue-500", children: "156" }), /*#__PURE__*/
            _jsx("p", { className: "text-sm text-muted-foreground", children: "Total Runs" })] }
          ) }
        )] }
      ), /*#__PURE__*/


      _jsx(Dialog, { open: isViewOpen, onOpenChange: setIsViewOpen, children: /*#__PURE__*/
        _jsxs(DialogContent, { className: "max-w-2xl", children: [/*#__PURE__*/
          _jsxs(DialogHeader, { children: [/*#__PURE__*/
            _jsxs(DialogTitle, { className: "flex items-center gap-2", children: [/*#__PURE__*/
              _jsx(Eye, { className: "h-5 w-5 text-primary" }),
              selectedModel?.name] }
            ), /*#__PURE__*/
            _jsx(DialogDescription, { children: "Model Details and Information" }

            )] }
          ), /*#__PURE__*/
          _jsxs("div", { className: "space-y-4 py-4", children: [/*#__PURE__*/
            _jsxs("div", { className: "grid grid-cols-2 gap-4", children: [/*#__PURE__*/
              _jsxs("div", { children: [/*#__PURE__*/
                _jsx("label", { className: "text-sm font-medium text-muted-foreground", children: "Type" }), /*#__PURE__*/
                _jsx("p", { className: "text-sm mt-1", children: selectedModel?.type })] }
              ), /*#__PURE__*/
              _jsxs("div", { children: [/*#__PURE__*/
                _jsx("label", { className: "text-sm font-medium text-muted-foreground", children: "Status" }), /*#__PURE__*/
                _jsx("div", { className: "mt-1", children: /*#__PURE__*/
                  _jsx(Badge, { variant: "outline", className: "capitalize", children: selectedModel?.status }) }
                )] }
              ), /*#__PURE__*/
              _jsxs("div", { children: [/*#__PURE__*/
                _jsx("label", { className: "text-sm font-medium text-muted-foreground", children: "Version" }), /*#__PURE__*/
                _jsx("p", { className: "text-sm mt-1", children: selectedModel?.version })] }
              ), /*#__PURE__*/
              _jsxs("div", { children: [/*#__PURE__*/
                _jsx("label", { className: "text-sm font-medium text-muted-foreground", children: "Author" }), /*#__PURE__*/
                _jsx("p", { className: "text-sm mt-1", children: selectedModel?.author })] }
              )] }
            ), /*#__PURE__*/
            _jsxs("div", { children: [/*#__PURE__*/
              _jsx("label", { className: "text-sm font-medium text-muted-foreground", children: "Description" }), /*#__PURE__*/
              _jsx("p", { className: "text-sm mt-1", children: selectedModel?.description })] }
            ), /*#__PURE__*/
            _jsxs("div", { children: [/*#__PURE__*/
              _jsx("label", { className: "text-sm font-medium text-muted-foreground", children: "Tags" }), /*#__PURE__*/
              _jsx("div", { className: "flex gap-2 mt-2", children:
                selectedModel?.tags?.map((tag, idx) => /*#__PURE__*/
                _jsx(Badge, { variant: "secondary", children: tag }, idx)
                ) }
              )] }
            ), /*#__PURE__*/
            _jsxs("div", { children: [/*#__PURE__*/
              _jsx("label", { className: "text-sm font-medium text-muted-foreground", children: "Last Modified" }), /*#__PURE__*/
              _jsx("p", { className: "text-sm mt-1", children: selectedModel?.lastModified })] }
            )] }
          ), /*#__PURE__*/
          _jsxs(DialogFooter, { children: [/*#__PURE__*/
            _jsx(Button, { variant: "outline", onClick: () => setIsViewOpen(false), children: "Close" }

            ), /*#__PURE__*/
            _jsxs(Button, { onClick: () => {
                setIsViewOpen(false);
                setIsEditOpen(true);
              }, children: [/*#__PURE__*/
              _jsx(Pencil, { className: "h-4 w-4 mr-2" }), "Edit Model"] }

            )] }
          )] }
        ) }
      ), /*#__PURE__*/


      _jsx(Dialog, { open: isEditOpen, onOpenChange: setIsEditOpen, children: /*#__PURE__*/
        _jsxs(DialogContent, { className: "max-w-2xl", children: [/*#__PURE__*/
          _jsxs(DialogHeader, { children: [/*#__PURE__*/
            _jsxs(DialogTitle, { className: "flex items-center gap-2", children: [/*#__PURE__*/
              _jsx(Pencil, { className: "h-5 w-5 text-primary" }), "Edit Model"] }

            ), /*#__PURE__*/
            _jsx(DialogDescription, { children: "Update model information and metadata" }

            )] }
          ), /*#__PURE__*/
          _jsxs("div", { className: "space-y-4 py-4", children: [/*#__PURE__*/
            _jsxs("div", { children: [/*#__PURE__*/
              _jsx("label", { className: "text-sm font-medium", children: "Model Name" }), /*#__PURE__*/
              _jsx(Input, { defaultValue: selectedModel?.name, className: "mt-1" })] }
            ), /*#__PURE__*/
            _jsxs("div", { className: "grid grid-cols-2 gap-4", children: [/*#__PURE__*/
              _jsxs("div", { children: [/*#__PURE__*/
                _jsx("label", { className: "text-sm font-medium", children: "Type" }), /*#__PURE__*/
                _jsx(Input, { defaultValue: selectedModel?.type, className: "mt-1" })] }
              ), /*#__PURE__*/
              _jsxs("div", { children: [/*#__PURE__*/
                _jsx("label", { className: "text-sm font-medium", children: "Version" }), /*#__PURE__*/
                _jsx(Input, { defaultValue: selectedModel?.version, className: "mt-1" })] }
              )] }
            ), /*#__PURE__*/
            _jsxs("div", { children: [/*#__PURE__*/
              _jsx("label", { className: "text-sm font-medium", children: "Description" }), /*#__PURE__*/
              _jsx(Input, { defaultValue: selectedModel?.description, className: "mt-1" })] }
            ), /*#__PURE__*/
            _jsxs("div", { children: [/*#__PURE__*/
              _jsx("label", { className: "text-sm font-medium", children: "Status" }), /*#__PURE__*/
              _jsxs("div", { className: "flex gap-2 mt-1", children: [/*#__PURE__*/
                _jsx(Badge, {
                  variant: selectedModel?.status === 'validated' ? 'default' : 'outline',
                  className: "cursor-pointer", children:
                  "Validated" }

                ), /*#__PURE__*/
                _jsx(Badge, {
                  variant: selectedModel?.status === 'draft' ? 'default' : 'outline',
                  className: "cursor-pointer", children:
                  "Draft" }

                ), /*#__PURE__*/
                _jsx(Badge, {
                  variant: selectedModel?.status === 'archived' ? 'default' : 'outline',
                  className: "cursor-pointer", children:
                  "Archived" }

                )] }
              )] }
            )] }
          ), /*#__PURE__*/
          _jsxs(DialogFooter, { children: [/*#__PURE__*/
            _jsx(Button, { variant: "outline", onClick: () => setIsEditOpen(false), children: "Cancel" }

            ), /*#__PURE__*/
            _jsx(Button, { onClick: handleSaveEdit, children: "Save Changes" }

            )] }
          )] }
        ) }
      )] }
    ));

}
