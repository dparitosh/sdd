/** Validation service — SHACL shape validation */
import { apiClient } from './api';

export const validateSHACL = (data: any, shapeName?: string) =>
  apiClient.post<{ conforms: boolean; violations: any[] }>(
    '/validate/shacl',
    { data, shape_name: shapeName }
  );
