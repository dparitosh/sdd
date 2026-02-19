import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios';
import { toast } from 'sonner';
import logger from '../utils/logger';
import i18n from '../i18n';
import { API_CONFIG, STORAGE_KEYS } from '../constants';

// Use /api prefix for Vite proxy (vite.config.ts proxies /api to Flask)
const API_BASE_URL = API_CONFIG.BASE_URL;

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Add auth token if available from zustand store
        try {
          const authStorage = localStorage.getItem(STORAGE_KEYS.AUTH);
          if (authStorage) {
            const { state } = JSON.parse(authStorage);
            if (state?.token) {
              config.headers.Authorization = `Bearer ${state.token}`;
            }
          }
        } catch (error) {
          logger.error('Error reading auth token:', error);
        }
        
        // Add API key from environment variable (optional in dev)
        const apiKey = import.meta.env.VITE_API_KEY;
        if (apiKey) {
          config.headers['X-API-Key'] = apiKey;
        }
        
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<any>) => {
        if (error.response) {
          let message = 'An error occurred';
          let details: string | undefined;

          // Handle FastAPI 422 validation errors
          if (error.response.status === 422 && error.response.data?.detail) {
            const validationErrors = error.response.data.detail;
            if (Array.isArray(validationErrors)) {
              message = 'Validation Error';
              details = validationErrors.map((err: any) => 
                `${err.loc?.join('.') || 'field'}: ${err.msg}`
              ).join(', ');
            } else if (typeof validationErrors === 'string') {
              message = validationErrors;
            } else {
              message = 'Validation failed';
            }
          } else {
            // Extract error message - handle both string and object formats
            const errorData = error.response.data?.error;
            message = typeof errorData === 'string' 
              ? errorData 
              : errorData?.message || message;
            
            details = typeof errorData === 'object' 
              ? errorData?.details 
              : error.response.data?.details;
          }
          
          // If API key isn't configured client-side and the server requires it, surface that explicitly.
          if ((error.response.status === 401 || error.response.status === 403) && !import.meta.env.VITE_API_KEY) {
            toast.error(i18n.t('errors.apiKeyNotConfigured'));
            return Promise.reject(error);
          }

          // Handle 401 Unauthorized - redirect to login
          if (error.response.status === 401) {
            toast.error(i18n.t('errors.sessionExpired'), {
              description: i18n.t('auth.loginFailed'),
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
          
          // Show error toast with proper string values
          toast.error(String(message), {
            description: details ? String(details) : undefined,
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

/**
 * API Service Methods
 * Provides typed methods for all backend API endpoints
 */
export const apiService = {
  // Health & Statistics
  
  /**
   * Get API health status
   * @returns Health status and version information
   */
  getHealth: () => apiClient.get<{ status: string; version: string }>('/health'),
  
  /**
   * Get system statistics including node and relationship counts
   * @returns Statistics object with counts by type
   */
  getStatistics: () =>
    apiClient.get<{
      node_types: Record<string, number>;
      relationship_types: Record<string, number>;
      total_nodes: number;
      total_relationships: number;
    }>('/stats'),

  // Artifacts
  
  /**
   * Search for artifacts in the knowledge graph
   * @param params - Search parameters (type, name, comment, limit)
   * @returns Array of matching artifacts
   */
  searchArtifacts: (params: {
    type?: string;
    name?: string;
    comment?: string;
    limit?: number;
  }) => apiClient.get<any[]>('/artifacts', { params }),

  /**
   * Get a specific artifact by type and ID
   * @param type - Artifact type (e.g., 'package', 'class')
   * @param id - Artifact identifier
   * @returns Artifact details
   * @throws Error if type or id is missing
   */
  getArtifact: (type: string, id: string) => {
    // Validate parameters to prevent undefined URLs
    if (!type || !id) {
      logger.error(`Invalid parameters: type=${type}, id=${id}`);
      return Promise.reject(new Error('Type and ID are required'));
    }
    return apiClient.get<any>(`/artifacts/${type.toLowerCase()}/${encodeURIComponent(id)}`);
  },

  // Graph Visualization
  graph: {
    /**
     * Get graph data nodes and links
     * @param params - Optional filter parameters (node_types, limit, etc.)
     * @returns Graph data object
     */
    getData: (params?: { limit?: number; node_types?: string; ap_level?: string }) =>
      apiClient.get<any>('/graph/data', { params }),

    /**
     * Get list of node types
     * @returns List of node types with counts
     */
    getNodeTypes: () =>
      apiClient.get<any>('/graph/node-types'),

    /**
     * Get list of relationship types
     * @returns List of relationship types with counts
     */
    getRelationshipTypes: () =>
      apiClient.get<any>('/graph/relationship-types'),
  },

  // SMRL v1 API
  
  /**
   * SMRL (ISO 10303-4443) compliant API methods
   */
  smrl: {
    /**
     * Get a specific SMRL resource
     * @param type - Resource type (e.g., 'Requirement', 'Part')
     * @param uid - Unique identifier
     * @returns Resource data
     */
    getResource: (type: string, uid: string) =>
      apiClient.get<any>(`/v1/${type}/${encodeURIComponent(uid)}`),
    
    /**
     * List SMRL resources with pagination
     * @param type - Resource type
     * @param params - Optional pagination parameters
     * @returns Array of resources
     */
    listResources: (type: string, params?: { limit?: number; offset?: number }) =>
      apiClient.get<any>(`/v1/${type}`, { params }),
    
    /**
     * Create a new SMRL resource
     * @param type - Resource type
     * @param data - Resource data
     * @returns Created resource
     */
    createResource: (type: string, data: any) =>
      apiClient.post<any>(`/v1/${type}`, data),
    
    /**
     * Update an existing SMRL resource (full replacement)
     * @param type - Resource type
     * @param uid - Unique identifier
     * @param data - Complete resource data
     * @returns Updated resource
     */
    updateResource: (type: string, uid: string, data: any) =>
      apiClient.put<any>(`/v1/${type}/${encodeURIComponent(uid)}`, data),
    
    /**
     * Partially update an SMRL resource
     * @param type - Resource type
     * @param uid - Unique identifier
     * @param data - Partial resource data
     * @returns Updated resource
     */
    patchResource: (type: string, uid: string, data: any) =>
      apiClient.patch<any>(`/v1/${type}/${encodeURIComponent(uid)}`, data),
    
    /**
     * Delete an SMRL resource
     * @param type - Resource type
     * @param uid - Unique identifier
     * @returns Deletion confirmation
     */
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
    
    // Fixed: Use correct AP239 path for traceability
    getTraceability: (uid: string) =>
      apiClient.get<any>(`/ap239/requirements/${encodeURIComponent(uid)}/traceability`),
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
    // Bulk traceability endpoint - fixes N+1 query problem
    getBulkRequirementTraceability: (requirementIds: string[]) =>
      apiClient.post<{ count: number; results: any[] }>('/ap239/requirements/traceability/bulk', { requirement_ids: requirementIds }),
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

  // AP243 - Reference Data & Domain Model
  ap243: {
    getOverview: () =>
      apiClient.get<any>('/ap243/overview'),
    getDomainClasses: (params?: { search?: string; stereotype?: string; is_abstract?: boolean; package?: string; skip?: number; limit?: number }) =>
      apiClient.get<{ count: number; classes: any[] }>('/ap243/domain-classes', { params }),
    getDomainClassDetail: (name: string) =>
      apiClient.get<any>(`/ap243/domain-classes/${encodeURIComponent(name)}`),
    domainSearch: (params: { q: string; node_type?: string; skip?: number; limit?: number }) =>
      apiClient.get<{ count: number; results: any[] }>('/ap243/domain-search', { params }),
    getPackages: () =>
      apiClient.get<{ count: number; packages: any[] }>('/ap243/packages'),
    getStereotypes: () =>
      apiClient.get<{ count: number; stereotypes: any[] }>('/ap243/stereotypes'),
    getOntologies: (params?: { ontology?: string; search?: string }) =>
      apiClient.get<{ count: number; ontologies: any[] }>('/ap243/ontologies', { params }),
    getOntologyDetail: (name: string) =>
      apiClient.get<any>(`/ap243/ontologies/${encodeURIComponent(name)}`),
    getUnits: () =>
      apiClient.get<{ count: number; units: any[] }>('/ap243/units'),
    getUnit: (id: string) =>
      apiClient.get<any>(`/ap243/units/${encodeURIComponent(id)}`),
    getValueTypes: () =>
      apiClient.get<{ count: number; value_types: any[] }>('/ap243/value-types'),
    getClassifications: (params?: { system?: string }) =>
      apiClient.get<{ count: number; classifications: any[] }>('/ap243/classifications', { params }),
    getStatistics: () =>
      apiClient.get<any>('/ap243/statistics'),
  },

  // Hierarchy Navigation
  hierarchy: {
    search: (params: { q: string; levels?: string }) =>
      apiClient.get<any[]>('/hierarchy/search', { params }),
    getTraceabilityMatrix: () =>
      apiClient.get<{ count: number; matrix: any[] }>('/hierarchy/traceability-matrix'),
    navigate: (nodeType: string, nodeId: string, params?: { depth?: number; direction?: string }) =>
      apiClient.get<any>(`/hierarchy/navigate/${encodeURIComponent(nodeType)}/${encodeURIComponent(nodeId)}`, { params }),
    impact: (nodeType: string, nodeId: string) =>
      apiClient.get<any>(`/hierarchy/impact/${encodeURIComponent(nodeType)}/${encodeURIComponent(nodeId)}`),
  },

  // PLM Operations - Fixed paths to match backend implementation
  plm: {
    getBOM: (partId: string) => apiClient.get<any>(`/plm/composition/${encodeURIComponent(partId)}`),
    getChangeImpact: (partId: string) =>
      apiClient.get<any>(`/plm/impact/${encodeURIComponent(partId)}`),
    getTraceability: (params?: { source_type?: string; target_type?: string }) =>
      apiClient.get<any>('/plm/traceability', { params }),
  },

  // Simulation Operations - Updated to match actual backend implementation
  simulation: {
    getModels: (params?: { limit?: number }) =>
      apiClient.get<any>('/simulation/models', { params }),
    getResults: (params?: { limit?: number }) =>
      apiClient.get<any>('/simulation/results', { params }),
    getParameters: (params?: {
      class_name?: string;
      property_name?: string;
      data_type?: string;
      include_constraints?: boolean;
      limit?: number;
      // Back-compat: older caller names
      owner_type?: string;
    }) => {
      const normalizedParams = { ...params };
      if (!normalizedParams.class_name && normalizedParams.owner_type) {
        normalizedParams.class_name = normalizedParams.owner_type;
        delete (normalizedParams as any).owner_type;
      }
      return apiClient.get<any>('/simulation/parameters', { params: normalizedParams });
    },
    validateParameters: (parameters: Array<{ id: string; value: any }>) =>
      apiClient.post<any>('/simulation/validate', { parameters }),
    getUnits: () =>
      apiClient.get<any>('/simulation/units'),
  },

  // AI Agents & Orchestration
  agents: {
    runOrchestrator: (query: string, task_type: string = 'impact_analysis') =>
      apiClient.post<{ status: string; messages: any[]; final_state: any }>('/agents/orchestrator/run', {
        query,
        task_type
      }),
  },

  // OSLC TRS
  trs: {
    getTRS: () => apiClient.get<any>('/oslc/trs'),
    getBase: (page: number = 1) => apiClient.get<any>(`/oslc/trs/base?page=${page}`),
    getChangeLog: () => apiClient.get<any>('/oslc/trs/changelog'),
  },

  // OSLC Client (Consumer)
  oslcClient: {
    connect: (providerData: { root_url: string; auth_type?: string; username?: string; password?: string }) =>
      apiClient.post<any>('/oslc/client/connect', providerData),
    query: (params: { provider_url: string; resource_type?: string; query?: string }) =>
      apiClient.post<any>('/oslc/client/query', params),
  },

  // File Upload
  upload: {
    uploadFile: (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return apiClient.post<{ job_id: string; status: string }>('/upload/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
    getStatus: (jobId: string) =>
      apiClient.get<{ job_id: string; status: string; progress?: number; error?: string }>(`/upload/status/${encodeURIComponent(jobId)}`),
    getJobs: () =>
      apiClient.get<any[]>('/upload/jobs'),
  },

  // Cypher Query
  query: {
    executeCypher: (query: string, params?: Record<string, any>) =>
      apiClient.post<any>('/cypher', { query, params }),
  },
};

export default apiClient;
