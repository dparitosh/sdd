import logger from '@/utils/logger';
import { useState, useCallback, useRef } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@ui/card';
import { Button } from '@ui/button';
import { Badge } from '@ui/badge';
import { Progress } from '@ui/progress';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow } from
'@ui/table';
import {
  Upload,
  File,
  FileCode,
  FileSpreadsheet,
  FileJson,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  AlertCircle,
  Trash2,
  RefreshCw } from
'lucide-react';
import { toast } from 'sonner';
import { apiClient } from '@/services/api';
import PageHeader from '@/components/PageHeader';import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";











const FILE_TYPES = [
{ ext: '.xmi', name: 'XMI', icon: FileCode, color: 'text-blue-500', desc: 'UML/SysML Models' },
{ ext: '.xml', name: 'XML', icon: FileCode, color: 'text-purple-500', desc: 'XML Model Files' },
{ ext: '.csv', name: 'CSV', icon: FileSpreadsheet, color: 'text-green-500', desc: 'Tabular Data' },
{ ext: '.json', name: 'JSON', icon: FileJson, color: 'text-orange-500', desc: 'JSON Data' }];


export default function DataImport() {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadedJobs, setUploadedJobs] = useState([]);
  const fileInputRef = useRef(null);

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: async (file) => {
      const formData = new FormData();
      formData.append('file', file);

      // Remove Content-Type header to let browser set multipart boundary
      const response = await apiClient.post('/upload/', formData, {
        headers: { 'Content-Type': undefined }
      });

      return response;
    },
    onSuccess: (data, file) => {
      toast.success('File uploaded successfully', {
        description: `${file.name} is being processed`
      });

      // Start polling for status
      if (data.job_id) {
        pollJobStatus(data.job_id);
      }
    },
    onError: (error) => {
      let errorMessage = 'Upload failed';
      let errorDetails = '';

      // Handle FastAPI validation errors
      if (error.response?.status === 422 && error.response?.data?.detail) {
        const detail = error.response.data.detail;
        if (Array.isArray(detail)) {
          errorMessage = 'Validation Error';
          errorDetails = detail.map((err) =>
          `${err.loc?.join('.') || 'field'}: ${err.msg}`
          ).join(', ');
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

  // Poll job status
  const pollJobStatus = async (jobId) => {
    const maxAttempts = 60; // Poll for 5 minutes
    let attempts = 0;

    const poll = async () => {
      try {
        const status = await apiClient.get(`/upload/status/${jobId}`);

        setUploadedJobs((prev) => {
          const existing = prev.findIndex((j) => j.job_id === jobId);
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

        // Continue polling
        if (attempts < maxAttempts && (status.status === 'pending' || status.status === 'processing')) {
          attempts++;
          setTimeout(poll, 5000); // Poll every 5 seconds
        }
      } catch (error) {
        logger.error('Failed to poll status:', error);
      }
    };

    poll();
  };

  // Query for existing jobs
  const { data: jobsData, refetch } = useQuery({
    queryKey: ['upload-jobs'],
    queryFn: () => apiClient.get('/upload/jobs'),
    refetchInterval: 10000 // Refetch every 10 seconds
  });

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    files.forEach((file) => uploadMutation.mutate(file));
  }, [uploadMutation]);

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files || []);
    files.forEach((file) => uploadMutation.mutate(file));

    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return /*#__PURE__*/_jsx(CheckCircle2, { className: "h-5 w-5 text-green-500" });
      case 'failed':
        return /*#__PURE__*/_jsx(XCircle, { className: "h-5 w-5 text-red-500" });
      case 'processing':
        return /*#__PURE__*/_jsx(Loader2, { className: "h-5 w-5 text-blue-500 animate-spin" });
      default:
        return /*#__PURE__*/_jsx(Clock, { className: "h-5 w-5 text-gray-500" });
    }
  };

  const getStatusBadge = (status) => {
    const variants = {
      pending: 'secondary',
      processing: 'default',
      completed: 'outline',
      failed: 'destructive'
    };

    return (/*#__PURE__*/
      _jsx(Badge, { variant: variants[status] || 'default', children:
        status.toUpperCase() }
      ));

  };

  const allJobs = [...uploadedJobs, ...(jobsData?.jobs || [])].reduce((acc, job) => {
    const existing = acc.find((j) => j.job_id === job.job_id);
    if (!existing) {
      acc.push(job);
    }
    return acc;
  }, []);

  return (/*#__PURE__*/
    _jsxs("div", { className: "container mx-auto p-6 space-y-6", children: [/*#__PURE__*/
      _jsx(PageHeader, {
        title: "Data Import",
        description: "Upload XMI, XML, CSV, or JSON files to import into the knowledge graph",
        icon: /*#__PURE__*/_jsx(Upload, { className: "h-6 w-6 text-primary" }),
        breadcrumbs: [
        { label: 'Data Management', href: '/import' },
        { label: 'Data Import' }] }

      ), /*#__PURE__*/


      _jsxs(Card, { className: "card-corporate border-2 shadow-lg", children: [/*#__PURE__*/
        _jsxs(CardHeader, { className: "border-b bg-gradient-to-r from-primary/5 to-primary/10", children: [/*#__PURE__*/
          _jsxs(CardTitle, { className: "flex items-center gap-2", children: [/*#__PURE__*/
            _jsx(Upload, { className: "h-5 w-5 text-primary" }), "Upload Files"] }

          ), /*#__PURE__*/
          _jsx(CardDescription, { children: "Drag and drop files or click to browse. Maximum file size: 100MB" }

          )] }
        ), /*#__PURE__*/
        _jsxs(CardContent, { className: "pt-6", children: [/*#__PURE__*/

          _jsxs("div", {
            onDragOver: handleDragOver,
            onDragLeave: handleDragLeave,
            onDrop: handleDrop,
            onClick: () => fileInputRef.current?.click(),
            className: `
              relative border-2 border-dashed rounded-lg p-12 text-center cursor-pointer
              transition-all duration-200
              ${isDragging ?
            'border-primary bg-primary/5 scale-[1.02]' :
            'border-border hover:border-primary/50 hover:bg-accent/5'}
            `, children: [/*#__PURE__*/


            _jsx("input", {
              ref: fileInputRef,
              type: "file",
              multiple: true,
              accept: ".xmi,.xml,.csv,.json",
              onChange: handleFileSelect,
              className: "hidden" }
            ), /*#__PURE__*/

            _jsxs("div", { className: "space-y-4", children: [/*#__PURE__*/
              _jsx("div", { className: "flex justify-center", children: /*#__PURE__*/
                _jsx("div", { className: `
                  p-4 rounded-full bg-primary/10
                  ${isDragging ? 'scale-110' : 'scale-100'}
                  transition-transform duration-200
                `, children: /*#__PURE__*/
                  _jsx(Upload, { className: "h-12 w-12 text-primary" }) }
                ) }
              ), /*#__PURE__*/

              _jsxs("div", { children: [/*#__PURE__*/
                _jsx("p", { className: "text-lg font-semibold", children:
                  isDragging ? 'Drop files here' : 'Drag & drop files here' }
                ), /*#__PURE__*/
                _jsx("p", { className: "text-sm text-muted-foreground mt-1", children: "or click to browse your computer" }

                )] }
              ),

              uploadMutation.isPending && /*#__PURE__*/
              _jsxs("div", { className: "flex items-center justify-center gap-2 text-primary", children: [/*#__PURE__*/
                _jsx(Loader2, { className: "h-5 w-5 animate-spin" }), /*#__PURE__*/
                _jsx("span", { children: "Uploading..." })] }
              )] }

            )] }
          ), /*#__PURE__*/


          _jsx("div", { className: "mt-6 grid grid-cols-2 md:grid-cols-4 gap-4", children:
            FILE_TYPES.map((type) => {
              const Icon = type.icon;
              return (/*#__PURE__*/
                _jsx(Card, { className: "border", children: /*#__PURE__*/
                  _jsxs(CardContent, { className: "p-4 text-center space-y-2", children: [/*#__PURE__*/
                    _jsx(Icon, { className: `h-8 w-8 mx-auto ${type.color}` }), /*#__PURE__*/
                    _jsxs("div", { children: [/*#__PURE__*/
                      _jsx("div", { className: "font-semibold", children: type.name }), /*#__PURE__*/
                      _jsx("div", { className: "text-xs text-muted-foreground", children: type.desc })] }
                    )] }
                  ) }, type.ext
                ));

            }) }
          )] }
        )] }
      ),


      allJobs.length > 0 && /*#__PURE__*/
      _jsxs(Card, { className: "card-corporate border-2", children: [/*#__PURE__*/
        _jsx(CardHeader, { className: "border-b bg-gradient-to-r from-accent/10 to-accent/5", children: /*#__PURE__*/
          _jsxs("div", { className: "flex items-center justify-between", children: [/*#__PURE__*/
            _jsx(CardTitle, { children: "Upload History" }), /*#__PURE__*/
            _jsxs(Button, {
              variant: "outline",
              size: "sm",
              onClick: () => refetch(), children: [/*#__PURE__*/

              _jsx(RefreshCw, { className: "h-4 w-4 mr-2" }), "Refresh"] }

            )] }
          ) }
        ), /*#__PURE__*/
        _jsx(CardContent, { className: "pt-6", children: /*#__PURE__*/
          _jsx("div", { className: "rounded-lg border-2 overflow-hidden", children: /*#__PURE__*/
            _jsxs(Table, { children: [/*#__PURE__*/
              _jsx(TableHeader, { className: "bg-muted/50", children: /*#__PURE__*/
                _jsxs(TableRow, { children: [/*#__PURE__*/
                  _jsx(TableHead, { children: "Status" }), /*#__PURE__*/
                  _jsx(TableHead, { children: "Filename" }), /*#__PURE__*/
                  _jsx(TableHead, { children: "Progress" }), /*#__PURE__*/
                  _jsx(TableHead, { children: "Message" }), /*#__PURE__*/
                  _jsx(TableHead, { className: "w-[100px]", children: "Actions" })] }
                ) }
              ), /*#__PURE__*/
              _jsx(TableBody, { children:
                allJobs.map((job) => /*#__PURE__*/
                _jsxs(TableRow, { children: [/*#__PURE__*/
                  _jsx(TableCell, { children: /*#__PURE__*/
                    _jsxs("div", { className: "flex items-center gap-2", children: [
                      getStatusIcon(job.status),
                      getStatusBadge(job.status)] }
                    ) }
                  ), /*#__PURE__*/
                  _jsx(TableCell, { className: "font-medium", children: /*#__PURE__*/
                    _jsxs("div", { className: "flex items-center gap-2", children: [/*#__PURE__*/
                      _jsx(File, { className: "h-4 w-4 text-muted-foreground" }),
                      job.filename] }
                    ) }
                  ), /*#__PURE__*/
                  _jsx(TableCell, { children: /*#__PURE__*/
                    _jsxs("div", { className: "space-y-2 min-w-[200px]", children: [/*#__PURE__*/
                      _jsx(Progress, { value: job.progress, className: "h-2" }), /*#__PURE__*/
                      _jsxs("span", { className: "text-xs text-muted-foreground", children: [
                        job.progress, "%"] }
                      )] }
                    ) }
                  ), /*#__PURE__*/
                  _jsx(TableCell, { className: "max-w-md", children: /*#__PURE__*/
                    _jsxs("div", { className: "space-y-1", children: [
                      job.message && /*#__PURE__*/
                      _jsx("p", { className: "text-sm", children: job.message }),

                      job.error && /*#__PURE__*/
                      _jsxs("p", { className: "text-sm text-red-500 flex items-center gap-1", children: [/*#__PURE__*/
                        _jsx(AlertCircle, { className: "h-4 w-4" }),
                        job.error] }
                      ),

                      job.stats && job.status === 'completed' && /*#__PURE__*/
                      _jsxs("div", { className: "text-xs text-muted-foreground", children: [
                        JSON.stringify(job.stats).slice(0, 100), "..."] }
                      )] }

                    ) }
                  ), /*#__PURE__*/
                  _jsx(TableCell, { children: /*#__PURE__*/
                    _jsx(Button, {
                      variant: "ghost",
                      size: "sm",
                      onClick: () => {
                        setUploadedJobs((prev) => prev.filter((j) => j.job_id !== job.job_id));
                      }, children: /*#__PURE__*/

                      _jsx(Trash2, { className: "h-4 w-4 text-muted-foreground hover:text-destructive" }) }
                    ) }
                  )] }, job.job_id
                )
                ) }
              )] }
            ) }
          ) }
        )] }
      )] }

    ));

}
