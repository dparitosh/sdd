import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios';
import { toast } from 'sonner';

// Use /api prefix for Vite proxy (vite.config.ts proxies /api to Flask)
const API_BASE_URL = '/api';

interface ApiErrorResponse {
  error: string;
  details?: string;
  status: number;
}

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 5000, // Reduced to 5 seconds to fail fast
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Add auth token if available from zustand store
        try {
          const authStorage = localStorage.getItem('mbse-auth-storage');
          if (authStorage) {
            const { state } = JSON.parse(authStorage);
            if (state?.token) {
              config.headers.Authorization = `Bearer ${state.token}`;
            }
          }
        } catch (error) {
          console.error('Error reading auth token:', error);
        }
        
        // Add API key from environment variable
        const apiKey = import.meta.env.VITE_API_KEY || 'mbse_dev_key_12345';
        config.headers['X-API-Key'] = apiKey;
        
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<ApiErrorResponse>) => {
        if (error.response) {
          const message = error.response.data?.error || 'An error occurred';
          
          // Handle 401 Unauthorized - redirect to login
          if (error.response.status === 401) {
            toast.error('Session expired', {
              description: 'Please log in again',
            });
            // Clear auth and redirect to login
            localStorage.removeItem('mbse-auth-storage');
            window.location.href = '/login';
            return Promise.reject(error);
          }
          
          // Handle 403 Forbidden
          if (error.response.status === 403) {
            toast.error('Access Denied', {
              description: 'You don\'t have permission to perform this action',
            });
            return Promise.reject(error);
          }
          
          toast.error(message, {
            description: error.response.data?.details,
          });
        } else if (error.request) {
          toast.error('Network Error', {
            description: 'Unable to connect to the server',
          });
        }
        return Promise.reject(error);
      }
    );
  }

  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, config);
    return response.data;
  }

  async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post<T>(url, data, config);
    return response.data;
  }

  async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.put<T>(url, data, config);
    return response.data;
  }

  async patch<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.patch<T>(url, data, config);
    return response.data;
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, config);
    return response.data;
  }
}

export const apiClient = new ApiClient();

// API Service Methods
export const apiService = {
  // Health & Statistics
  getHealth: () => apiClient.get<{ status: string; version: string }>('/health'),
  getStatistics: () =>
    apiClient.get<{
      node_types: Record<string, number>;
      relationship_types: Record<string, number>;
      total_nodes: number;
      total_relationships: number;
    }>('/stats'),

  // Artifacts
  searchArtifacts: (params: {
    type?: string;
    name?: string;
    comment?: string;
    limit?: number;
  }) => apiClient.get<any[]>('/artifacts', { params }),

  getArtifact: (type: string, id: string) =>
    apiClient.get<any>(`/${type.toLowerCase()}/${encodeURIComponent(id)}`),

  // SMRL v1 API
  smrl: {
    getResource: (type: string, uid: string) =>
      apiClient.get<any>(`/v1/${type}/${encodeURIComponent(uid)}`),
    
    listResources: (type: string, params?: { limit?: number; offset?: number }) =>
      apiClient.get<any>(`/v1/${type}`, { params }),
    
    createResource: (type: string, data: any) =>
      apiClient.post<any>(`/v1/${type}`, data),
    
    updateResource: (type: string, uid: string, data: any) =>
      apiClient.put<any>(`/v1/${type}/${encodeURIComponent(uid)}`, data),
    
    patchResource: (type: string, uid: string, data: any) =>
      apiClient.patch<any>(`/v1/${type}/${encodeURIComponent(uid)}`, data),
    
    deleteResource: (type: string, uid: string) =>
      apiClient.delete<any>(`/v1/${type}/${encodeURIComponent(uid)}`),
  },

  // Requirements
  requirements: {
    list: (params?: { limit?: number; offset?: number }) =>
      apiClient.get<any[]>('/v1/Requirement', { params }),
    
    get: (uid: string) =>
      apiClient.get<any>(`/v1/Requirement/${encodeURIComponent(uid)}`),
    
    create: (data: any) => apiClient.post<any>('/v1/Requirement', data),
    
    update: (uid: string, data: any) =>
      apiClient.put<any>(`/v1/Requirement/${encodeURIComponent(uid)}`, data),
    
    delete: (uid: string) =>
      apiClient.delete<any>(`/v1/Requirement/${encodeURIComponent(uid)}`),
    
    getTraceability: (uid: string) =>
      apiClient.get<any>(`/requirements/${encodeURIComponent(uid)}/traceability`),
  },

  // Query Editor
  executeCypher: (query: string) =>
    apiClient.post<{ results: any[]; summary: any }>('/cypher', { query }),

  // AP239 - Product Life Cycle Support (PLCS)
  ap239: {
    getRequirements: (params?: { type?: string; status?: string; priority?: string; search?: string }) =>
      apiClient.get<{ count: number; requirements: any[] }>('/ap239/requirements', { params }),
    getRequirement: (id: string) =>
      apiClient.get<any>(`/ap239/requirements/${encodeURIComponent(id)}`),
    getRequirementTraceability: (id: string) =>
      apiClient.get<any>(`/ap239/requirements/${encodeURIComponent(id)}/traceability`),
    getApprovals: () =>
      apiClient.get<{ count: number; approvals: any[] }>('/ap239/approvals'),
    getAnalyses: () =>
      apiClient.get<{ count: number; analyses: any[] }>('/ap239/analyses'),
    getDocuments: () =>
      apiClient.get<{ count: number; documents: any[] }>('/ap239/documents'),
    getStatistics: () =>
      apiClient.get<any>('/ap239/statistics'),
  },

  // AP242 - 3D Managed Product Data
  ap242: {
    getParts: (params?: { status?: string; search?: string }) =>
      apiClient.get<{ count: number; parts: any[] }>('/ap242/parts', { params }),
    getPart: (id: string) =>
      apiClient.get<any>(`/ap242/parts/${encodeURIComponent(id)}`),
    getPartBOM: (id: string) =>
      apiClient.get<any>(`/ap242/parts/${encodeURIComponent(id)}/bom`),
    getMaterials: (params?: { type?: string; search?: string }) =>
      apiClient.get<{ count: number; materials: any[] }>('/ap242/materials', { params }),
    getMaterial: (name: string) =>
      apiClient.get<any>(`/ap242/materials/${encodeURIComponent(name)}`),
    getAssemblies: () =>
      apiClient.get<{ count: number; assemblies: any[] }>('/ap242/assemblies'),
    getGeometry: () =>
      apiClient.get<{ count: number; geometries: any[] }>('/ap242/geometry'),
    getStatistics: () =>
      apiClient.get<any>('/ap242/statistics'),
  },

  // AP243 - Reference Data
  ap243: {
    getUnits: () =>
      apiClient.get<{ count: number; units: any[] }>('/ap243/units'),
    getUnit: (id: string) =>
      apiClient.get<any>(`/ap243/units/${encodeURIComponent(id)}`),
  },

  // Hierarchy Navigation
  hierarchy: {
    search: (params: { query: string; level?: number }) =>
      apiClient.get<any[]>('/hierarchy/search', { params }),
    getTraceabilityMatrix: () =>
      apiClient.get<{ count: number; matrix: any[] }>('/hierarchy/traceability-matrix'),
    trace: (sourceType: string, sourceId: string) =>
      apiClient.get<any>(`/hierarchy/trace/${encodeURIComponent(sourceType)}/${encodeURIComponent(sourceId)}`),
  },

  // PLM Operations
  plm: {
    getBOM: (partId: string) => apiClient.get<any>(`/plm/bom/${encodeURIComponent(partId)}`),
    getChangeImpact: (partId: string) =>
      apiClient.get<any>(`/plm/change-impact/${encodeURIComponent(partId)}`),
  },

  // Simulation Operations
  simulation: {
    listModels: () => apiClient.get<any[]>('/simulation/models'),
    getModel: (id: string) =>
      apiClient.get<any>(`/simulation/models/${encodeURIComponent(id)}`),
    runSimulation: (data: any) => apiClient.post<any>('/simulation/run', data),
  },
};
