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

export default apiClient;
