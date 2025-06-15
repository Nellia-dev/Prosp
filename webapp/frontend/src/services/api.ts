import { apiClient } from '../config/api';
import axios from 'axios';
import type {
  ApiResponse,
  PaginatedResponse,
  LoginRequest,
  LoginResponse,
  AgentResponse,
  StartAgentRequest,
  StopAgentRequest,
  LeadFilters,
  CreateLeadRequest,
  UpdateLeadRequest,
  UpdateLeadStageRequest,
  LeadResponse,
  LeadsByStageResponse,
  BulkLeadOperation,
  BusinessContextRequest,
  BusinessContextResponse,
  ChatMessageRequest,
  ChatMessageResponse,
  PerformanceMetricsResponse,
  AgentPerformanceResponse,
  LeadStatsResponse,
  MetricsSummaryResponse,
  UserPlanStatusResponse,
  ProspectJob,
} from '../types/api';

// Import dashboard metrics from unified types - perfect alignment with backend
import type { DashboardMetricsResponse } from '../types/api';

// Export the apiClient for use in other parts of the application
export { apiClient };

// Authentication API
export const authApi = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>('/auth/login', data);
    return response.data;
  },

  register: async (data: { email: string; password: string; firstName: string; lastName: string }): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>('/auth/register', data);
    return response.data;
  },

  logout: async (): Promise<void> => {
    await apiClient.post('/auth/logout');
  },

  getProfile: async (): Promise<LoginResponse['user']> => {
    const response = await apiClient.get<ApiResponse<LoginResponse['user']>>('/auth/profile');
    return response.data.data;
  },
};

// Agents API
export const agentsApi = {
  getAll: async (): Promise<AgentResponse[]> => {
    try {
      const response = await apiClient.get<ApiResponse<AgentResponse[]>>('/agents');
      if (response.data && response.data.data) {
        return response.data.data;
      }
      console.warn('agentsApi.getAll: response.data.data was null or undefined. Returning empty array.');
    } catch (error) {
      console.error('Error fetching all agents from API:', error);
      // Fallthrough to return empty array on error
    }
    return []; // Fallback default
  },

  getById: async (id: string): Promise<AgentResponse> => {
    const response = await apiClient.get<ApiResponse<AgentResponse>>(`/agents/${id}`);
    return response.data.data;
  },

  start: async (data: StartAgentRequest): Promise<void> => {
    await apiClient.post(`/agents/${data.agentId}/start`);
  },

  stop: async (data: StopAgentRequest): Promise<void> => {
    await apiClient.post(`/agents/${data.agentId}/stop`);
  },

  getStatus: async (id: string): Promise<AgentResponse> => {
    const response = await apiClient.get<ApiResponse<AgentResponse>>(`/agents/${id}/status`);
    return response.data.data;
  },
};

// Leads API
export const leadsApi = {
  getAll: async (filters?: LeadFilters): Promise<PaginatedResponse<LeadResponse>> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined) {
          params.append(key, String(value));
        }
      });
    }
    try {
      const response = await apiClient.get<ApiResponse<PaginatedResponse<LeadResponse>>>(
        `/leads?${params.toString()}`
      );
      if (response.data && response.data.data) {
        // Ensure data array exists, even if empty, and pagination fields have defaults
        return {
          data: response.data.data.data || [],
          total: response.data.data.total || 0,
          page: response.data.data.page || 1,
          limit: response.data.data.limit || 10,
          totalPages: response.data.data.totalPages || 0,
        };
      }
      console.warn('leadsApi.getAll: response.data.data was null or undefined. Returning default paginated response.');
    } catch (error) {
      console.error('Error fetching all leads from API:', error);
      // Fallthrough to return default paginated response on error
    }
    return { data: [], total: 0, page: 1, limit: 10, totalPages: 0 }; // Fallback default
  },

  getById: async (id: string): Promise<LeadResponse> => {
    const response = await apiClient.get<ApiResponse<LeadResponse>>(`/leads/${id}`);
    return response.data.data;
  },

  create: async (data: CreateLeadRequest): Promise<LeadResponse> => {
    const response = await apiClient.post<ApiResponse<LeadResponse>>('/leads', data);
    return response.data.data;
  },

  update: async (id: string, data: UpdateLeadRequest): Promise<LeadResponse> => {
    const response = await apiClient.put<ApiResponse<LeadResponse>>(`/leads/${id}`, data);
    return response.data.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/leads/${id}`);
  },

  updateStage: async (id: string, data: UpdateLeadStageRequest): Promise<LeadResponse> => {
    const response = await apiClient.patch<ApiResponse<LeadResponse>>(`/leads/${id}/stage`, data);
    return response.data.data;
  },

  getByStage: async (): Promise<LeadsByStageResponse> => {
    const response = await apiClient.get<ApiResponse<LeadsByStageResponse>>('/leads/by-stage');
    return response.data.data;
  },

  bulkOperation: async (data: BulkLeadOperation): Promise<void> => {
    await apiClient.post('/leads/bulk', data);
  },

  process: async (id: string): Promise<void> => {
    await apiClient.post(`/leads/${id}/process`);
  },
};

// Business Context API
export const businessContextApi = {
  get: async (): Promise<BusinessContextResponse | null> => {
    try {
      const response = await apiClient.get<BusinessContextResponse | null>('/business-context');
      // The backend returns the business context object directly, or a 200 with null.
      // We return the data, or null if it's falsy.
      return response.data || null;
    } catch (error) {
      // A 404 Not Found error also indicates that the context doesn't exist.
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        return null;
      }
      // For any other errors, we re-throw them to be handled by react-query's error state.
      throw error;
    }
  },

  create: async (data: BusinessContextRequest): Promise<BusinessContextResponse> => {
    const response = await apiClient.post<ApiResponse<BusinessContextResponse>>('/business-context', data);
    return response.data.data;
  },

  update: async (data: BusinessContextRequest): Promise<BusinessContextResponse> => {
    const response = await apiClient.put<ApiResponse<BusinessContextResponse>>('/business-context', data);
    return response.data.data;
  },
};

// Chat API
export const chatApi = {
  getMessages: async (agentId: string): Promise<ChatMessageResponse[]> => {
    const response = await apiClient.get<ApiResponse<ChatMessageResponse[]>>(`/chat/${agentId}/messages`);
    return response.data.data;
  },

  sendMessage: async (data: ChatMessageRequest): Promise<ChatMessageResponse> => {
    const response = await apiClient.post<ApiResponse<ChatMessageResponse>>('/chat/messages', data);
    return response.data.data;
  },
};

// Metrics API - using unified types for perfect alignment
export const metricsApi = {
  getDashboard: async (): Promise<DashboardMetricsResponse> => {
    try {
      const response = await apiClient.get<ApiResponse<DashboardMetricsResponse>>('/metrics/dashboard');
      if (response.data && response.data.data) {
        // Ensure lastUpdated is a string, as expected by DashboardMetricsResponse
        const metrics = response.data.data;
        if (metrics.lastUpdated && typeof metrics.lastUpdated !== 'string') {
          metrics.lastUpdated = new Date(metrics.lastUpdated).toISOString();
        }
        return metrics;
      }
      console.warn('metricsApi.getDashboard: response.data.data was null or undefined. Returning default metrics.');
    } catch (error) {
      console.error('Error fetching dashboard metrics from API:', error);
      // Fallthrough to return default metrics on error
    }
    // Fallback default if API call fails or data is malformed - aligned with DashboardMetricsResponse
    return {
      totalLeads: 0,
      totalAgents: 0,
      activeAgents: 0,
      processingRate: 0,
      successRate: 0,
      recentActivity: [],
      lastUpdated: new Date().toISOString(),
    };
  },

  getPerformance: async (timeRange = '24h'): Promise<PerformanceMetricsResponse> => {
    const response = await apiClient.get<ApiResponse<PerformanceMetricsResponse>>(
      `/metrics/performance?timeRange=${timeRange}`
    );
    return response.data.data || { timeRange, throughputData: [], processingTimeData: [] };
  },

  getAgentPerformance: async (): Promise<AgentPerformanceResponse[]> => {
    const response = await apiClient.get<ApiResponse<AgentPerformanceResponse[]>>('/metrics/agents');
    return response.data.data;
  },

  getLeadStats: async (): Promise<LeadStatsResponse[]> => {
    const response = await apiClient.get<ApiResponse<LeadStatsResponse[]>>('/metrics/leads');
    return response.data.data;
  },

  getSummary: async (): Promise<MetricsSummaryResponse> => {
    const response = await apiClient.get<ApiResponse<MetricsSummaryResponse>>('/metrics/summary');
    return response.data.data;
  },
};

// Prospect API - using unified types for perfect alignment with backend and hooks
export const prospectApi = {
  startProspectingJob: async (businessContext: BusinessContextRequest): Promise<{ jobId: string | number; status: string }> => {
    const response = await apiClient.post<{ jobId: string | number; status: string }>('/prospect/start', businessContext);
    return response.data;
  },
  
  getJobs: async (): Promise<ProspectJob[]> => {
    const response = await apiClient.get<ApiResponse<ProspectJob[]>>('/prospect/jobs');
    return response.data.data || [];
  },
  
  getJobStatus: async (jobId: string): Promise<ProspectJob> => {
    // Backend /prospect/status/:jobId returns ProspectJobStatus which aligns with ProspectJob type
    const response = await apiClient.get<ApiResponse<ProspectJob>>(`/prospect/status/${jobId}`);
    return response.data.data;
  },
};


// User API
export const userApi = {
  getPlanStatus: async (): Promise<UserPlanStatusResponse> => {
    try {
      const response = await apiClient.get<ApiResponse<UserPlanStatusResponse>>('/users/me/plan-status');
      if (response.data && response.data.data) {
        return response.data.data;
      }
      console.warn('userApi.getPlanStatus: response.data.data was null or undefined. Returning default plan status.');
    } catch (error) {
      console.error('Error fetching user plan status from API:', error);
      // Fallthrough to return default plan status on error
    }
    // Fallback default if API call fails or data is malformed
    return {
      plan: {
        id: 'free',
        name: 'Free',
        quota: 10,
        period: 'week',
        price: 0,
      },
      quota: {
        total: 10,
        used: 0,
        remaining: 10,
        nextResetAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(), // 1 week from now
      },
      canStartProspecting: true,
      hasActiveJob: false,
      activeJobId: null,
    };
  },
};
