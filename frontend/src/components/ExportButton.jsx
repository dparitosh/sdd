import logger from '@/utils/logger';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger } from
'@/components/ui/dropdown-menu';
import { Download, FileJson, FileSpreadsheet, FileCode, GitGraph, FileText, Loader2 } from 'lucide-react';
import { toast } from 'sonner';import { jsx as _jsx, Fragment as _Fragment, jsxs as _jsxs } from "react/jsx-runtime";







const ExportButton = ({ entityType, filters = {}, className }) => {
  const [isExporting, setIsExporting] = useState(false);

  const exportFormats = [
  { id: 'json', name: 'JSON', icon: FileJson, endpoint: 'json' },
  { id: 'csv', name: 'CSV', icon: FileSpreadsheet, endpoint: 'csv' },
  { id: 'xml', name: 'XML', icon: FileCode, endpoint: 'xml' },
  { id: 'graphml', name: 'GraphML', icon: GitGraph, endpoint: 'graphml' },
  { id: 'rdf', name: 'RDF/Turtle', icon: FileText, endpoint: 'rdf' },
  { id: 'plantuml', name: 'PlantUML', icon: FileCode, endpoint: 'plantuml' }];


  const handleExport = async (format, endpoint) => {
    setIsExporting(true);

    try {
      // Build query parameters
      const params = new URLSearchParams();

      // Add entity type filter
      if (entityType === 'requirements') {
        params.append('node_types', 'Requirement,RequirementVersion');
      } else if (entityType === 'parts') {
        params.append('node_types', 'Part,PartVersion,Material,Assembly');
      }

      // Add custom filters
      Object.entries(filters).forEach(([key, value]) => {
        if (value && value !== 'all') {
          params.append(key, String(value));
        }
      });

      // Set reasonable limit
      params.append('limit', '10000');
      params.append('include_properties', 'true');

      // Make export request
      const response = await fetch(`/api/v1/export/${endpoint}?${params.toString()}`);

      if (!response.ok) {
        throw new Error(`Export failed: ${response.statusText}`);
      }

      // Get filename from Content-Disposition header or generate one
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = `${entityType}_export.${format}`;

      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '');
        }
      }

      // Download file
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success(`Exported ${entityType} as ${format.toUpperCase()}`, {
        description: `Downloaded ${filename}`
      });
    } catch (error) {
      logger.error('Export error:', error);
      toast.error('Export failed', {
        description: error instanceof Error ? error.message : 'An unknown error occurred'
      });
    } finally {
      setIsExporting(false);
    }
  };

  return (/*#__PURE__*/
    _jsxs(DropdownMenu, { children: [/*#__PURE__*/
      _jsx(DropdownMenuTrigger, { asChild: true, children: /*#__PURE__*/
        _jsx(Button, {
          variant: "outline",
          className: className,
          disabled: isExporting, children:

          isExporting ? /*#__PURE__*/
          _jsxs(_Fragment, { children: [/*#__PURE__*/
            _jsx(Loader2, { className: "mr-2 h-4 w-4 animate-spin" }), "Exporting..."] }

          ) : /*#__PURE__*/

          _jsxs(_Fragment, { children: [/*#__PURE__*/
            _jsx(Download, { className: "mr-2 h-4 w-4" }), "Export"] }

          ) }

        ) }
      ), /*#__PURE__*/
      _jsxs(DropdownMenuContent, { align: "end", className: "w-48", children: [/*#__PURE__*/
        _jsx(DropdownMenuLabel, { children: "Export Format" }), /*#__PURE__*/
        _jsx(DropdownMenuSeparator, {}),
        exportFormats.map((format) => {
          const Icon = format.icon;
          return (/*#__PURE__*/
            _jsxs(DropdownMenuItem, {

              onClick: () => handleExport(format.id, format.endpoint),
              disabled: isExporting,
              className: "cursor-pointer", children: [/*#__PURE__*/

              _jsx(Icon, { className: "mr-2 h-4 w-4" }),
              format.name] }, format.id
            ));

        })] }
      )] }
    ));

};

export default ExportButton;
