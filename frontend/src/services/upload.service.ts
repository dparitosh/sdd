/** Upload service — file upload + job tracking */
import { apiClient } from './api';

export const uploadFile = (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  return apiClient.post<{ job_id: string; status: string }>(
    '/upload/',
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  );
};

export const getUploadStatus = (jobId: string) =>
  apiClient.get<{ job_id: string; status: string; progress?: number; error?: string }>(
    `/upload/status/${encodeURIComponent(jobId)}`
  );

export const getUploadJobs = () =>
  apiClient.get<any[]>('/upload/jobs');
