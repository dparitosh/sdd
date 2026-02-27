import logger from '@/utils/logger';
import { useState, useCallback, useRef } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@ui/card';
import { Button } from '@ui/button';
import { Badge } from '@ui/badge';
import { Progress } from '@ui/progress';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@ui/table';
import { Upload, File, FileCode, FileSpreadsheet, FileJson, CheckCircle2, XCircle, Clock, Loader2, AlertCircle, Trash2, RefreshCw, Database, Download } from 'lucide-react';
import { toast } from 'sonner';
import { apiClient } from '@/services/api';
import PageHeader from '@/components/PageHeader';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { EXPORT_FORMATS } from '@/constants';

const FILE_TYPES = [{
  ext: '.xmi',
  name: 'XMI',
  icon: FileCode,
  color: 'text-blue-500',
  desc: 'UML/SysML Models'
}, {
  ext: '.xml',
  name: 'XML',
  icon: FileCode,
  color: 'text-purple-500',
  desc: 'XML Model Files'
}, {
  ext: '.csv',
  name: 'CSV',
  icon: FileSpreadsheet,
  color: 'text-green-500',
  desc: 'Tabular Data'
}, {
  ext: '.json',
  name: 'JSON',
  icon: FileJson,
  color: 'text-orange-500',
  desc: 'JSON Data'
}, {
  ext: '.exp',
  name: 'EXPRESS',
  icon: Database,
  color: 'text-cyan-500',
  desc: 'ISO 10303 Schemas'
}, {
  ext: '.xsd',
  name: 'XSD',
  icon: FileCode,
  color: 'text-red-500',
  desc: 'XML Schema Definition'
}, {
  ext: '.owl',
  name: 'Ontology',
  icon: FileCode,
  color: 'text-pink-500',
  desc: 'OWL/RDF/TTL Files'
}, {
  ext: '.stp',
  name: 'STEP',
  icon: Database,
  color: 'text-teal-500',
  desc: 'STEP AP242/AP243 (STP/STPX)'
}];
export default function DataImport() {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadedJobs, setUploadedJobs] = useState([]);
  const fileInputRef = useRef(null);
  const uploadMutation = useMutation({
    mutationFn: async file => {
      const formData = new FormData();
      formData.append('file', file);
      const response = await apiClient.post('/upload/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      return response;
    },
    onSuccess: (data, file) => {
      toast.success('File uploaded successfully', {
        description: `${file.name} is being processed`
      });
      if (data.job_id) {
        pollJobStatus(data.job_id);
      }
    },
    onError: error => {
      let errorMessage = 'Upload failed';
      let errorDetails = '';
      if (error.response?.status === 422 && error.response?.data?.detail) {
        const detail = error.response.data.detail;
        if (Array.isArray(detail)) {
          errorMessage = 'Validation Error';
          errorDetails = detail.map(err => `${err.loc?.join('.') || 'field'}: ${err.msg}`).join(', ');
        } else if (typeof detail === 'string') {
          errorDetails = detail;
        }
      } else {
        errorDetails = error.response?.data?.detail || error.message;
      }
      toast.error(errorMessage, {
        description: errorDetails || undefined
      });
    }
  });
  const pollJobStatus = async jobId => {
    const maxAttempts = 60;
    let attempts = 0;
    const poll = async () => {
      try {
        const status = await apiClient.get(`/upload/status/${jobId}`);
        setUploadedJobs(prev => {
          const existing = prev.findIndex(j => j.job_id === jobId);
          if (existing >= 0) {
            const updated = [...prev];
            updated[existing] = status;
            return updated;
          }
          return [...prev, status];
        });
        if (status.status === 'completed') {
          toast.success('Import completed', {
            description: status.message || 'File processed successfully'
          });
          return;
        }
        if (status.status === 'failed') {
          toast.error('Import failed', {
            description: status.error || 'Unknown error'
          });
          return;
        }
        if (attempts < maxAttempts && (status.status === 'pending' || status.status === 'processing')) {
          attempts++;
          setTimeout(poll, 5000);
        }
      } catch (error) {
        logger.error('Failed to poll status:', error);
      }
    };
    poll();
  };
  const {
    data: jobsData,
    refetch
  } = useQuery({
    queryKey: ['upload-jobs'],
    queryFn: () => apiClient.get('/upload/jobs'),
    refetchInterval: 10000
  });
  const handleDragOver = useCallback(e => {
    e.preventDefault();
    setIsDragging(true);
  }, []);
  const handleDragLeave = useCallback(e => {
    e.preventDefault();
    setIsDragging(false);
  }, []);
  const handleDrop = useCallback(e => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    files.forEach(file => uploadMutation.mutate(file));
  }, [uploadMutation]);
  const handleFileSelect = e => {
    const files = Array.from(e.target.files || []);
    files.forEach(file => uploadMutation.mutate(file));
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };
  const getStatusIcon = status => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'processing':
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
      default:
        return <Clock className="h-5 w-5 text-gray-500" />;
    }
  };
  const getStatusBadge = status => {
    const variants = {
      pending: 'secondary',
      processing: 'default',
      completed: 'outline',
      failed: 'destructive'
    };
    return <Badge variant={variants[status] || 'default'}>{status.toUpperCase()}</Badge>;
  };
  const allJobs = [...uploadedJobs, ...(jobsData?.jobs || [])].reduce((acc, job) => {
    const existing = acc.find(j => j.job_id === job.job_id);
    if (!existing) {
      acc.push(job);
    }
    return acc;
  }, []);

  const handleExport = async (format) => {
    try {
        const token = localStorage.getItem('mbse-auth-storage') 
        ? JSON.parse(localStorage.getItem('mbse-auth-storage')).state?.token 
        : null;

        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
        
        const response = await fetch(format.endpoint, { headers });
        
        if (!response.ok) throw new Error('Export failed');
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `export_${new Date().getTime()}${format.extension}`; // Basic naming
        
        // Try to get filename from header
        const disposition = response.headers.get('content-disposition');
        if (disposition && disposition.indexOf('attachment') !== -1) {
            var filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
            var matches = filenameRegex.exec(disposition);
            if (matches != null && matches[1]) { 
            a.download = matches[1].replace(/['"]/g, '');
            }
        }

        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        toast.success(`Exported as ${format.label}`);
    } catch (e) {
        toast.error(`Failed to export ${format.label}: ${e.message}`);
    }
  };

  const ImportSection = () => (
    <>
      <Card className="card-corporate border-2 shadow-lg"><CardHeader className="border-b bg-linear-to-r from-primary/5 to-primary/10"><CardTitle className="flex items-center gap-2"><Upload className="h-5 w-5 text-primary" />Upload Files</CardTitle><CardDescription>Drag and drop files or click to browse. Maximum file size: 100MB</CardDescription></CardHeader><CardContent className="pt-6"><div onDragOver={handleDragOver} onDragLeave={handleDragLeave} onDrop={handleDrop} onClick={() => fileInputRef.current?.click()} className={`
              relative border-2 border-dashed rounded-lg p-12 text-center cursor-pointer
              transition-all duration-200
              ${isDragging ? 'border-primary bg-primary/5 scale-[1.02]' : 'border-border hover:border-primary/50 hover:bg-accent/5'}
            `}><input ref={fileInputRef} type="file" multiple accept=".xmi,.xml,.csv,.json,.exp,.xsd,.owl,.rdf,.ttl,.nq,.stp,.step,.stpx" onChange={handleFileSelect} className="hidden" /><div className="space-y-4"><div className="flex justify-center"><div className={`
                  p-4 rounded-full bg-primary/10
                  ${isDragging ? 'scale-110' : 'scale-100'}
                  transition-transform duration-200
                `}><Upload className="h-12 w-12 text-primary" /></div></div><div><p className="text-lg font-semibold">{isDragging ? 'Drop files here' : 'Drag & drop files here'}</p><p className="text-sm text-muted-foreground mt-1">or click to browse your computer</p></div>{uploadMutation.isPending && <div className="flex items-center justify-center gap-2 text-primary"><Loader2 className="h-5 w-5 animate-spin" /><span>Uploading...</span></div>}</div></div><div className="mt-6 grid grid-cols-2 md:grid-cols-5 gap-4">{FILE_TYPES.map(type => {
            const Icon = type.icon;
            return <Card key={type.name} className="border"><CardContent className="p-4 text-center space-y-2"><Icon className={`h-8 w-8 mx-auto ${type.color}`} /><div><div className="font-semibold">{type.name}</div><div className="text-xs text-muted-foreground">{type.desc}</div></div></CardContent></Card>;
          })}</div></CardContent></Card>{allJobs.length > 0 && <Card className="card-corporate border-2"><CardHeader className="border-b bg-linear-to-r from-accent/10 to-accent/5"><div className="flex items-center justify-between"><CardTitle>Upload History</CardTitle><Button variant="outline" size="sm" onClick={() => refetch()}><RefreshCw className="h-4 w-4 mr-2" />Refresh</Button></div></CardHeader><CardContent className="pt-6"><div className="rounded-lg border-2 overflow-hidden"><Table><TableHeader className="bg-muted/50"><TableRow><TableHead>Status</TableHead><TableHead>Filename</TableHead><TableHead>Progress</TableHead><TableHead>Message</TableHead><TableHead className="w-25">Actions</TableHead></TableRow></TableHeader><TableBody>{allJobs.map(job => <TableRow key={job.job_id}><TableCell><div className="flex items-center gap-2">{getStatusIcon(job.status)}{getStatusBadge(job.status)}</div></TableCell><TableCell className="font-medium"><div className="flex items-center gap-2"><File className="h-4 w-4 text-muted-foreground" />{job.filename}</div></TableCell><TableCell><div className="space-y-2 min-w-50"><Progress value={job.progress} className="h-2" /><span className="text-xs text-muted-foreground">{job.progress}%</span></div></TableCell><TableCell className="max-w-md"><div className="space-y-1">{job.message && <p className="text-sm">{job.message}</p>}{job.error && <p className="text-sm text-red-500 flex items-center gap-1"><AlertCircle className="h-4 w-4" />{job.error}</p>}{job.stats && job.status === 'completed' && <div className="text-xs text-muted-foreground">{JSON.stringify(job.stats).slice(0, 100)}...</div>}</div></TableCell><TableCell><Button variant="ghost" size="sm" onClick={() => {
                    setUploadedJobs(prev => prev.filter(j => j.job_id !== job.job_id));
                  }}><Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" /></Button></TableCell></TableRow>)}</TableBody></Table></div></CardContent></Card>}
    </>
  );

  const ExportSection = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {EXPORT_FORMATS.map((format) => (
        <Card key={format.value} className="hover:shadow-md transition-shadow">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Download className="w-5 h-5 text-primary" />
              {format.label}
            </CardTitle>
            <CardDescription>{format.description}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button 
                className="w-full" 
                variant="outline"
                onClick={() => handleExport(format)}
            >
              Download {format.extension}
            </Button>
          </CardContent>
        </Card>
      ))}
    </div>
  );

  return <div className="container mx-auto p-6 space-y-6">
        <PageHeader title="Data Management" description="Import data into the Knowledge Graph or Export to various formats" icon={<Database className="h-6 w-6 text-primary" />} breadcrumbs={[{
      label: 'Data Management',
      href: '/import'
    }]} />
    
    <Tabs defaultValue="import" className="w-full">
        <TabsList className="grid w-full grid-cols-2 mb-8">
            <TabsTrigger value="import">Import Data</TabsTrigger>
            <TabsTrigger value="export">Export Data</TabsTrigger>
        </TabsList>
        <TabsContent value="import" className="space-y-4">
            <ImportSection />
        </TabsContent>
        <TabsContent value="export" className="space-y-4">
             <Card>
                <CardHeader>
                    <CardTitle>Export Data</CardTitle>
                    <CardDescription>Download the entire knowledge graph or specific subsets in standard formats.</CardDescription>
                </CardHeader>
                <CardContent>
                    <ExportSection />
                </CardContent>
             </Card>
        </TabsContent>
    </Tabs>
    </div>;
}
