/** EXPRESS service — ISO 10303-11 EXPRESS schema endpoints */
import { apiClient } from './api';

export const parseExpress = (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  return apiClient.post<any>('/express/parse/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const queryExpress = (schemaData: Record<string, any>, entityName?: string, supertype?: string) =>
  apiClient.post<any>('/express/query/entities', {
    schema_data: schemaData,
    entity_name: entityName ?? null,
    supertype: supertype ?? null,
    include_abstract: true,
  });

export const analyzeExpress = (schemaData: Record<string, any>) =>
  apiClient.post<any>('/express/analyze/statistics', schemaData);

export const exportExpress = (schemaData: Record<string, any>, format: 'json' | 'markdown' | 'graphml' = 'json') =>
  apiClient.post<any>(`/express/export/${format}`, schemaData);
