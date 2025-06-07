/**
 * Enhanced API Hooks with Unified Agent Support
 * 
 * This file provides React Query hooks that:
 * - Use existing API types for compatibility 
 * - Add support for all agents from agent instructions
 * - Provide type adapters between frontend and backend models
 * - Implement optimistic updates and caching strategies
 * - Handle errors gracefully with retry logic
 */

import { 
  useQuery, 
  useMutation, 
  useQueryClient,
  UseQueryOptions,
  UseMutationOptions,
} from '@tanstack/react-query';

import { 
  authApi,
  agentsApi,
  leadsApi,
  businessContextApi,
  chatApi,
  metricsApi
} from '../../services/api';

// Import existing API types
import type {
  LoginRequest,
  LoginResponse,
  AgentResponse,
  StartAgentRequest,
  StopAgentRequest,
  LeadResponse,
  CreateLeadRequest,
  UpdateLeadRequest,
  UpdateLeadStageRequest,
  LeadFilters,
  BusinessContextResponse,
  BusinessContextRequest,
  ChatMessageResponse,
  ChatMessageRequest,
  DashboardMetricsResponse,
  PerformanceMetricsResponse,
  AgentPerformanceResponse,
  LeadStatsResponse,
  MetricsSummaryResponse,
  PaginatedResponse,
  BulkLeadOperation,
} from '../../types/api';

// Import unified types for extended agent support
import type {
  AgentName,
  ProcessingStage,
  QualificationTier,
} from '../../types/unified';

import {
  AGENT_NAMES,
  AGENT_DISPLAY_NAMES,
  STAGE_DISPLAY_NAMES,
} from '../../types/unified';

// ===================================
// Type Adapters & Extended Interfaces
// ===================================

// Extended Agent Response with unified agent names
export interface ExtendedAgentResponse extends Omit<AgentResponse, 'name'> {
  name: AgentName;
  displayName: string;
  category: 'initial_processing' | 'orchestrator' | 'specialized' | 'alternative';
}

// Agent categorization helper
export const getAgentCategory = (agentName: AgentName): ExtendedAgentResponse['category'] => {
  if (['lead_intake_agent', 'lead_analysis_agent'].includes(agentName)) {
    return 'initial_processing';
  }
  if (agentName === 'enhanced_lead_processor') {
    return 'orchestrator';
  }
  if ([
    'tavily_enrichment_agent',
    'contact_extraction_agent',
    'pain_point_deepening_agent',
    'lead_qualification_agent',
    'competitor_identification_agent',
    'strategic_question_generation_agent',
    'buying_trigger_identification_agent',
    'tot_strategy_generation_agent',
    'tot_strategy_evaluation_agent',
    'tot_action_plan_synthesis_agent',
    'detailed_approach_plan_agent',
    'objection_handling_agent',
    'value_proposition_customization_agent',
    'b2b_personalized_message_agent',
    'internal_briefing_summary_agent'
  ].includes(agentName)) {
    return 'specialized';
  }
  return 'alternative';
};

// Agent adapter function
export const adaptAgentResponse = (agent: AgentResponse): ExtendedAgentResponse => ({
  ...agent,
  name: agent.name as AgentName,
  displayName: AGENT_DISPLAY_NAMES[agent.name as AgentName] || agent.name,
  category: getAgentCategory(agent.name as AgentName),
});

// ===================================
// Query Keys Factory
// ===================================

export const queryKeys = {
  // Authentication
  auth: {
    profile: ['auth', 'profile'] as const,
  },

  // Agents
  agents: {
    all: ['agents'] as const,
    detail: (id: string) => ['agents', id] as const,
    status: (id: string) => ['agents', id, 'status'] as const,
    byCategory: (category: ExtendedAgentResponse['category']) => ['agents', 'category', category] as const,
  },

  // Leads
  leads: {
    all: ['leads'] as const,
    filtered: (filters: object) => ['leads', 'filtered', filters] as const,
    detail: (id: string) => ['leads', id] as const,
    byStage: ['leads', 'by-stage'] as const,
  },

  // Business Context
  businessContext: {
    current: ['business-context'] as const,
  },

  // Chat
  chat: {
    messages: (agentId: string) => ['chat', agentId, 'messages'] as const,
  },

  // Metrics
  metrics: {
    dashboard: ['metrics', 'dashboard'] as const,
    performance: (timeRange: string) => ['metrics', 'performance', timeRange] as const,
    agents: ['metrics', 'agents'] as const,
    leads: ['metrics', 'leads'] as const,
    summary: ['metrics', 'summary'] as const,
  },
} as const;

// ===================================
// Enhanced Agent Hooks
// ===================================

export const useAgents = (
  options?: UseQueryOptions<ExtendedAgentResponse[], Error>
) => {
  return useQuery({
    queryKey: queryKeys.agents.all,
    queryFn: async () => {
      const agents = await agentsApi.getAll();
      return agents.map(adaptAgentResponse);
    },
    staleTime: 1000 * 30, // 30 seconds
    refetchInterval: 1000 * 60, // 1 minute
    ...options,
  });
};

export const useAgentsByCategory = (
  category: ExtendedAgentResponse['category'],
  options?: UseQueryOptions<ExtendedAgentResponse[], Error>
) => {
  return useQuery({
    queryKey: queryKeys.agents.byCategory(category),
    queryFn: async () => {
      const agents = await agentsApi.getAll();
      const extendedAgents = agents.map(adaptAgentResponse);
      return extendedAgents.filter(agent => agent.category === category);
    },
    staleTime: 1000 * 30,
    ...options,
  });
};

export const useAgent = (
  id: string,
  options?: UseQueryOptions<ExtendedAgentResponse, Error>
) => {
  return useQuery({
    queryKey: queryKeys.agents.detail(id),
    queryFn: async () => {
      const agent = await agentsApi.getById(id);
      return adaptAgentResponse(agent);
    },
    enabled: !!id,
    staleTime: 1000 * 30,
    ...options,
  });
};

export const useStartAgent = (
  options?: UseMutationOptions<void, Error, StartAgentRequest>
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: StartAgentRequest) => agentsApi.start(request),
    onSuccess: (_, variables) => {
      // Invalidate agent queries to get updated status
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.detail(variables.agentId) });
    },
    ...options,
  });
};

export const useStopAgent = (
  options?: UseMutationOptions<void, Error, StopAgentRequest>
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: StopAgentRequest) => agentsApi.stop(request),
    onSuccess: (_, variables) => {
      // Invalidate agent queries to get updated status
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.detail(variables.agentId) });
    },
    ...options,
  });
};

// ===================================
// Enhanced Lead Hooks
// ===================================

export const useLeads = (
  filters?: LeadFilters,
  options?: UseQueryOptions<PaginatedResponse<LeadResponse>, Error>
) => {
  return useQuery({
    queryKey: queryKeys.leads.filtered(filters || {}),
    queryFn: () => leadsApi.getAll(filters),
    staleTime: 1000 * 60 * 2, // 2 minutes
    ...options,
  });
};

export const useLead = (
  id: string,
  options?: UseQueryOptions<LeadResponse, Error>
) => {
  return useQuery({
    queryKey: queryKeys.leads.detail(id),
    queryFn: () => leadsApi.getById(id),
    enabled: !!id,
    staleTime: 1000 * 60, // 1 minute
    ...options,
  });
};

export const useCreateLead = (
  options?: UseMutationOptions<LeadResponse, Error, CreateLeadRequest>
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateLeadRequest) => leadsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.leads.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.leads.byStage });
    },
    ...options,
  });
};

export const useUpdateLead = (
  options?: UseMutationOptions<LeadResponse, Error, { id: string; data: UpdateLeadRequest }>
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateLeadRequest }) => 
      leadsApi.update(id, data),
    onSuccess: (updatedLead) => {
      // Update specific lead in cache
      queryClient.setQueryData(queryKeys.leads.detail(updatedLead.id), updatedLead);
      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: queryKeys.leads.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.leads.byStage });
    },
    ...options,
  });
};

export const useUpdateLeadStage = (
  options?: UseMutationOptions<LeadResponse, Error, { id: string; stage: string }>
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, stage }: { id: string; stage: string }) => 
      leadsApi.updateStage(id, { stage } as UpdateLeadStageRequest),
    onSuccess: (updatedLead) => {
      queryClient.setQueryData(queryKeys.leads.detail(updatedLead.id), updatedLead);
      queryClient.invalidateQueries({ queryKey: queryKeys.leads.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.leads.byStage });
    },
    ...options,
  });
};

export const useDeleteLead = (
  options?: UseMutationOptions<void, Error, string>
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => leadsApi.delete(id),
    onSuccess: (_, deletedId) => {
      queryClient.removeQueries({ queryKey: queryKeys.leads.detail(deletedId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.leads.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.leads.byStage });
    },
    ...options,
  });
};

export const useProcessLead = (
  options?: UseMutationOptions<void, Error, string>
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => leadsApi.process(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.leads.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.leads.byStage });
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.all });
    },
    ...options,
  });
};

// ===================================
// Business Context Hooks
// ===================================

export const useBusinessContext = (
  options?: UseQueryOptions<BusinessContextResponse | null, Error>
) => {
  return useQuery<BusinessContextResponse | null>({
    queryKey: queryKeys.businessContext.current,
    queryFn: () => businessContextApi.get(),
    staleTime: 1000 * 60 * 10, // 10 minutes
    ...options,
  });
};

export const useUpdateBusinessContext = (
  options?: UseMutationOptions<BusinessContextResponse, Error, BusinessContextRequest>
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: BusinessContextRequest) => businessContextApi.update(data),
    onSuccess: (updatedContext) => {
      queryClient.setQueryData(queryKeys.businessContext.current, updatedContext);
    },
    ...options,
  });
};

// ===================================
// Chat Hooks
// ===================================

export const useChatMessages = (
  agentId: string,
  options?: UseQueryOptions<ChatMessageResponse[], Error>
) => {
  return useQuery({
    queryKey: queryKeys.chat.messages(agentId),
    queryFn: () => chatApi.getMessages(agentId),
    enabled: !!agentId,
    staleTime: 1000 * 30, // 30 seconds
    ...options,
  });
};

export const useSendMessage = (
  options?: UseMutationOptions<ChatMessageResponse, Error, ChatMessageRequest>
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (message: ChatMessageRequest) => chatApi.sendMessage(message),
    onSuccess: (newMessage) => {
      // Add new message to cache
      queryClient.setQueryData(
        queryKeys.chat.messages(newMessage.agentId),
        (old: ChatMessageResponse[] | undefined) => [...(old || []), newMessage]
      );
    },
    ...options,
  });
};

// ===================================
// Metrics Hooks
// ===================================

export const useDashboardMetrics = (
  options?: UseQueryOptions<DashboardMetricsResponse, Error>
) => {
  return useQuery({
    queryKey: queryKeys.metrics.dashboard,
    queryFn: () => metricsApi.getDashboard(),
    staleTime: 1000 * 60, // 1 minute
    refetchInterval: 1000 * 60 * 2, // 2 minutes
    ...options,
  });
};

export const usePerformanceMetrics = (
  timeRange = '24h',
  options?: UseQueryOptions<PerformanceMetricsResponse, Error>
) => {
  return useQuery({
    queryKey: queryKeys.metrics.performance(timeRange),
    queryFn: () => metricsApi.getPerformance(timeRange),
    staleTime: 1000 * 60 * 2, // 2 minutes
    ...options,
  });
};

export const useAgentPerformanceData = (
  options?: UseQueryOptions<AgentPerformanceResponse[], Error>
) => {
  return useQuery({
    queryKey: queryKeys.metrics.agents,
    queryFn: () => metricsApi.getAgentPerformance(),
    staleTime: 1000 * 60, // 1 minute
    ...options,
  });
};

export const useLeadStatsData = (
  options?: UseQueryOptions<LeadStatsResponse[], Error>
) => {
  return useQuery({
    queryKey: queryKeys.metrics.leads,
    queryFn: () => metricsApi.getLeadStats(),
    staleTime: 1000 * 60, // 1 minute
    ...options,
  });
};

export const useMetricsSummary = (
  options?: UseQueryOptions<MetricsSummaryResponse, Error>
) => {
  return useQuery({
    queryKey: queryKeys.metrics.summary,
    queryFn: () => metricsApi.getSummary(),
    staleTime: 1000 * 60, // 1 minute
    ...options,
  });
};

// ===================================
// Authentication Hooks
// ===================================

export const useLogin = (
  options?: UseMutationOptions<LoginResponse, Error, LoginRequest>
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (credentials: LoginRequest) => authApi.login(credentials),
    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.auth.profile, data.user);
      queryClient.invalidateQueries();
    },
    ...options,
  });
};

export const useLogout = (
  options?: UseMutationOptions<void, Error, void>
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => authApi.logout(),
    onSuccess: () => {
      queryClient.clear();
    },
    ...options,
  });
};

export const useProfile = (
  options?: UseQueryOptions<LoginResponse['user'], Error>
) => {
  return useQuery({
    queryKey: queryKeys.auth.profile,
    queryFn: () => authApi.getProfile(),
    staleTime: 1000 * 60 * 5, // 5 minutes
    ...options,
  });
};

// ===================================
// Utility Hooks and Helpers
// ===================================

export const useInvalidateQueries = () => {
  const queryClient = useQueryClient();

  return {
    invalidateAgents: () => queryClient.invalidateQueries({ queryKey: queryKeys.agents.all }),
    invalidateLeads: () => queryClient.invalidateQueries({ queryKey: queryKeys.leads.all }),
    invalidateMetrics: () => queryClient.invalidateQueries({ queryKey: ['metrics'] }),
    invalidateAll: () => queryClient.invalidateQueries(),
  };
};

// Helper to get agent display information
export const useAgentDisplayInfo = () => {
  return {
    getAgentDisplayName: (agentName: AgentName) => AGENT_DISPLAY_NAMES[agentName] || agentName,
    getStageDisplayName: (stage: ProcessingStage) => STAGE_DISPLAY_NAMES[stage] || stage,
    getAgentCategory,
    getAllAgentNames: () => AGENT_NAMES,
    getAgentsByCategory: (category: ExtendedAgentResponse['category']) => 
      AGENT_NAMES.filter(name => getAgentCategory(name) === category),
  };
};

// Pipeline status helper
export const usePipelineStatus = () => {
  const { data: agents } = useAgents();
  const { data: metrics } = useDashboardMetrics();

  return {
    isProcessing: agents?.some(agent => agent.status === 'processing') || false,
    activeAgentCount: agents?.filter(agent => agent.status === 'active').length || 0,
    totalLeads: metrics?.totalLeads || 0,
    processingRate: metrics?.processingRate || 0,
  };
};