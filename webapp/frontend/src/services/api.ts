import { apiClient } from '../config/api';
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
  DashboardMetricsResponse,
  PerformanceMetricsResponse,
  AgentPerformanceResponse,
  LeadStatsResponse,
  MetricsSummaryResponse,
} from '../types/api';

// Export the apiClient for use in other parts of the application
export { apiClient };

// Authentication API
export const authApi = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const response = await apiClient.post<ApiResponse<LoginResponse>>('/auth/login', data);
    return response.data.data;
  },

  register: async (data: { email: string; password: string; name: string }): Promise<LoginResponse> => {
    const response = await apiClient.post<ApiResponse<LoginResponse>>('/auth/register', data);
    return response.data.data;
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
    const response = await apiClient.get<ApiResponse<AgentResponse[]>>('/agents');
    return response.data.data;
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
    const response = await apiClient.get<ApiResponse<PaginatedResponse<LeadResponse>>>(
      `/leads?${params.toString()}`
    );
    return response.data.data;
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
  get: async (): Promise<BusinessContextResponse> => {
    const response = await apiClient.get<ApiResponse<BusinessContextResponse>>('/business-context');
    return response.data.data;
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

// Metrics API
export const metricsApi = {
  getDashboard: async (): Promise<DashboardMetricsResponse> => {
    const response = await apiClient.get<ApiResponse<DashboardMetricsResponse>>('/metrics/dashboard');
    return response.data.data;
  },

  getPerformance: async (timeRange = '24h'): Promise<PerformanceMetricsResponse> => {
    const response = await apiClient.get<ApiResponse<PerformanceMetricsResponse>>(
      `/metrics/performance?timeRange=${timeRange}`
    );
    return response.data.data;
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
