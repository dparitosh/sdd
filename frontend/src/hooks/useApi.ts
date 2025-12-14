/**
 * Custom React Hooks
 * Reusable hooks for common data fetching and state management patterns
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiService } from '@/services/api';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import { QUERY_CONFIG } from '@/constants';

/**
 * Hook for fetching system statistics
 * @returns Query result with stats data and loading state
 */
export function useStats() {
  const { t } = useTranslation();
  
  return useQuery({
    queryKey: ['stats'],
    queryFn: apiService.getStatistics,
    staleTime: QUERY_CONFIG.STALE_TIME,
    onError: () => {
      toast.error(t('errors.apiError', { message: 'Failed to load statistics' }));
    },
  });
}

/**
 * Hook for fetching requirements list
 * @param params - Optional query parameters
 * @returns Query result with requirements data
 */
export function useRequirements(params?: { limit?: number; offset?: number }) {
  const { t } = useTranslation();
  
  return useQuery({
    queryKey: ['requirements', params],
    queryFn: () => apiService.ap239.getRequirements(params),
    staleTime: QUERY_CONFIG.STALE_TIME,
    onError: () => {
      toast.error(t('errors.apiError', { message: 'Failed to load requirements' }));
    },
  });
}

/**
 * Hook for fetching a single requirement with traceability
 * @param uid - Requirement unique identifier
 * @returns Query result with requirement details
 */
export function useRequirement(uid: string | undefined) {
  const { t } = useTranslation();
  
  return useQuery({
    queryKey: ['requirement', uid],
    queryFn: () => uid ? apiService.ap239.getRequirement(uid) : Promise.reject(),
    enabled: !!uid,
    staleTime: QUERY_CONFIG.STALE_TIME,
    onError: () => {
      toast.error(t('errors.apiError', { message: 'Failed to load requirement' }));
    },
  });
}

/**
 * Hook for fetching requirement traceability
 * @param uid - Requirement unique identifier
 * @returns Query result with traceability data
 */
export function useRequirementTraceability(uid: string | undefined) {
  const { t } = useTranslation();
  
  return useQuery({
    queryKey: ['requirement-traceability', uid],
    queryFn: () => uid ? apiService.ap239.getRequirementTraceability(uid) : Promise.reject(),
    enabled: !!uid,
    staleTime: QUERY_CONFIG.STALE_TIME,
    onError: () => {
      toast.error(t('errors.apiError', { message: 'Failed to load traceability' }));
    },
  });
}

/**
 * Hook for fetching parts list
 * @param params - Optional query parameters
 * @returns Query result with parts data
 */
export function useParts(params?: { limit?: number; offset?: number }) {
  const { t } = useTranslation();
  
  return useQuery({
    queryKey: ['parts', params],
    queryFn: () => apiService.ap242.getParts(params),
    staleTime: QUERY_CONFIG.STALE_TIME,
    onError: () => {
      toast.error(t('errors.apiError', { message: 'Failed to load parts' }));
    },
  });
}

/**
 * Hook for fetching a single part
 * @param id - Part identifier
 * @returns Query result with part details
 */
export function usePart(id: string | undefined) {
  const { t } = useTranslation();
  
  return useQuery({
    queryKey: ['part', id],
    queryFn: () => id ? apiService.ap242.getPart(id) : Promise.reject(),
    enabled: !!id,
    staleTime: QUERY_CONFIG.STALE_TIME,
    onError: () => {
      toast.error(t('errors.apiError', { message: 'Failed to load part' }));
    },
  });
}

/**
 * Hook for fetching graph data
 * @param params - Graph query parameters
 * @returns Query result with graph nodes and edges
 */
export function useGraphData(params?: { limit?: number; type?: string }) {
  const { t } = useTranslation();
  
  return useQuery({
    queryKey: ['graph', params],
    queryFn: () => apiService.graph.getData(params),
    staleTime: QUERY_CONFIG.STALE_TIME,
    onError: () => {
      toast.error(t('errors.apiError', { message: 'Failed to load graph data' }));
    },
  });
}

/**
 * Hook for creating a new SMRL resource
 * @param type - Resource type (e.g., 'Requirement', 'Part')
 * @returns Mutation function and state
 */
export function useCreateResource(type: string) {
  const queryClient = useQueryClient();
  const { t } = useTranslation();
  
  return useMutation({
    mutationFn: (data: any) => apiService.smrl.createResource(type, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [type.toLowerCase() + 's'] });
      toast.success(t('common.success'), {
        description: `${type} created successfully`,
      });
    },
    onError: (error: any) => {
      toast.error(t('errors.apiError', { 
        message: error.message || 'Failed to create resource' 
      }));
    },
  });
}

/**
 * Hook for updating an SMRL resource
 * @param type - Resource type
 * @returns Mutation function and state
 */
export function useUpdateResource(type: string) {
  const queryClient = useQueryClient();
  const { t } = useTranslation();
  
  return useMutation({
    mutationFn: ({ uid, data }: { uid: string; data: any }) =>
      apiService.smrl.updateResource(type, uid, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [type.toLowerCase(), variables.uid] });
      queryClient.invalidateQueries({ queryKey: [type.toLowerCase() + 's'] });
      toast.success(t('common.success'), {
        description: `${type} updated successfully`,
      });
    },
    onError: (error: any) => {
      toast.error(t('errors.apiError', { 
        message: error.message || 'Failed to update resource' 
      }));
    },
  });
}

/**
 * Hook for deleting an SMRL resource
 * @param type - Resource type
 * @returns Mutation function and state
 */
export function useDeleteResource(type: string) {
  const queryClient = useQueryClient();
  const { t } = useTranslation();
  
  return useMutation({
    mutationFn: (uid: string) => apiService.smrl.deleteResource(type, uid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [type.toLowerCase() + 's'] });
      toast.success(t('common.success'), {
        description: `${type} deleted successfully`,
      });
    },
    onError: (error: any) => {
      toast.error(t('errors.apiError', { 
        message: error.message || 'Failed to delete resource' 
      }));
    },
  });
}

/**
 * Hook for uploading files
 * @returns Mutation function for file upload
 */
export function useFileUpload() {
  const { t } = useTranslation();
  
  return useMutation({
    mutationFn: (file: File) => apiService.upload.uploadFile(file),
    onSuccess: (data) => {
      toast.success(t('upload.uploading'), {
        description: `Job ID: ${data.job_id}`,
      });
    },
    onError: (error: any) => {
      toast.error(t('errors.apiError', { 
        message: error.message || 'Upload failed' 
      }));
    },
  });
}

/**
 * Hook for polling upload status
 * @param jobId - Upload job identifier
 * @param enabled - Whether to enable polling
 * @returns Query result with job status
 */
export function useUploadStatus(jobId: string | undefined, enabled = true) {
  const { t } = useTranslation();
  
  return useQuery({
    queryKey: ['upload-status', jobId],
    queryFn: () => jobId ? apiService.upload.getStatus(jobId) : Promise.reject(),
    enabled: enabled && !!jobId,
    refetchInterval: (data) => {
      // Stop polling if completed or failed
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false;
      }
      return 1000; // Poll every second
    },
    onError: () => {
      toast.error(t('errors.apiError', { message: 'Failed to get upload status' }));
    },
  });
}

/**
 * Hook for executing Cypher queries
 * @returns Mutation function for query execution
 */
export function useCypherQuery() {
  const { t } = useTranslation();
  
  return useMutation({
    mutationFn: (query: string) => apiService.query.executeCypher(query),
    onError: (error: any) => {
      toast.error(t('errors.apiError', { 
        message: error.message || 'Query execution failed' 
      }));
    },
  });
}
