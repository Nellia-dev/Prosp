import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:3001/api',
  WS_URL: import.meta.env.VITE_WS_URL || 'ws://localhost:3001',
  TIMEOUT: 10000, // 10 seconds
  RETRY_ATTEMPTS: 3,
} as const;

// Enhanced axios client with authentication support
class ApiClient {
  private client: AxiosInstance;
  private authToken: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_CONFIG.BASE_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        if (this.authToken) {
          config.headers.Authorization = `Bearer ${this.authToken}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Token expired or invalid - will be handled by AuthContext
          this.authToken = null;
        }
        return Promise.reject(error);
      }
    );
  }

  // Set authentication token
  setAuthToken(token: string | null) {
    this.authToken = token;
  }

  // Get current token
  getAuthToken(): string | null {
    return this.authToken;
  }

  // HTTP methods
  async get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.client.get<T>(url, config);
  }

  async post<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.client.post<T>(url, data, config);
  }

  async put<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.client.put<T>(url, data, config);
  }

  async patch<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.client.patch<T>(url, data, config);
  }

  async delete<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.client.delete<T>(url, config);
  }
}

// Create and export singleton instance
export const apiClient = new ApiClient();

export const API_ENDPOINTS = {
  // Authentication
  AUTH: {
    LOGIN: '/auth/login',
    LOGOUT: '/auth/logout',
    REFRESH: '/auth/refresh',
    PROFILE: '/auth/profile',
  },
  
  // Agents
  AGENTS: {
    BASE: '/agents',
    BY_ID: (id: string) => `/agents/${id}`,
    START: (id: string) => `/agents/${id}/start`,
    STOP: (id: string) => `/agents/${id}/stop`,
    METRICS: (id: string) => `/agents/${id}/metrics`,
  },
  
  // Leads
  LEADS: {
    BASE: '/leads',
    BY_ID: (id: string) => `/leads/${id}`,
    BY_STAGE: '/leads/by-stage',
    BULK: '/leads/bulk',
    PROCESS: (id: string) => `/leads/${id}/process`,
    UPDATE_STAGE: (id: string) => `/leads/${id}/stage`,
    ANALYTICS: '/leads/analytics',
  },
  
  // Business Context
  BUSINESS_CONTEXT: {
    BASE: '/business-context',
    BY_ID: (id: string) => `/business-context/${id}`,
  },
  
  // Chat
  CHAT: {
    BASE: '/chat',
    MESSAGES: '/chat/messages',
    BY_AGENT: (agentId: string) => `/chat/agents/${agentId}/messages`,
  },
  
  // Metrics
  METRICS: {
    DASHBOARD: '/metrics/dashboard',
    PERFORMANCE: '/metrics/performance',
    AGENTS_PERFORMANCE: '/metrics/agents/performance',
    AGENT_METRICS: (agentId: string) => `/metrics/agents/${agentId}`,
    ALL_AGENTS: '/metrics/agents',
    LEADS_STATS: '/metrics/leads/stats-by-stage',
    SUMMARY: '/metrics/summary',
  },
} as const;
