import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Download, FileJson, FileSpreadsheet, FileCode, GitGraph, FileText, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

interface ExportButtonProps {
  entityType: 'requirements' | 'parts' | 'graph';
  filters?: Record<string, any>;
  className?: string;
}

const ExportButton: React.FC<ExportButtonProps> = ({ entityType, filters = {}, className }) => {
  const [isExporting, setIsExporting] = useState(false);

  const exportFormats = [
    { id: 'json', name: 'JSON', icon: FileJson, endpoint: 'json' },
    { id: 'csv', name: 'CSV', icon: FileSpreadsheet, endpoint: 'csv' },
    { id: 'xml', name: 'XML', icon: FileCode, endpoint: 'xml' },
    { id: 'graphml', name: 'GraphML', icon: GitGraph, endpoint: 'graphml' },
    { id: 'rdf', name: 'RDF/Turtle', icon: FileText, endpoint: 'rdf' },
    { id: 'plantuml', name: 'PlantUML', icon: FileCode, endpoint: 'plantuml' },
  ];

  const handleExport = async (format: string, endpoint: string) => {
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
        description: `Downloaded ${filename}`,
      });
    } catch (error) {
      console.error('Export error:', error);
      toast.error('Export failed', {
        description: error instanceof Error ? error.message : 'An unknown error occurred',
      });
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button 
          variant="outline" 
          className={className}
          disabled={isExporting}
        >
          {isExporting ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Exporting...
            </>
          ) : (
            <>
              <Download className="mr-2 h-4 w-4" />
              Export
            </>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuLabel>Export Format</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {exportFormats.map((format) => {
          const Icon = format.icon;
          return (
            <DropdownMenuItem
              key={format.id}
              onClick={() => handleExport(format.id, format.endpoint)}
              disabled={isExporting}
              className="cursor-pointer"
            >
              <Icon className="mr-2 h-4 w-4" />
              {format.name}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default ExportButton;
