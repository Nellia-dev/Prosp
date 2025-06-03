import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { agentsApi } from '../../services/api';
import type { AgentResponse, StartAgentRequest, StopAgentRequest } from '../../types/api';

// Query keys
export const agentKeys = {
  all: ['agents'] as const,
  lists: () => [...agentKeys.all, 'list'] as const,
  list: (filters: string) => [...agentKeys.lists(), { filters }] as const,
  details: () => [...agentKeys.all, 'detail'] as const,
  detail: (id: string) => [...agentKeys.details(), id] as const,
  status: (id: string) => [...agentKeys.detail(id), 'status'] as const,
};

// Hooks
export const useAgents = () => {
  return useQuery({
    queryKey: agentKeys.lists(),
    queryFn: agentsApi.getAll,
  });
};

export const useAgent = (id: string) => {
  return useQuery({
    queryKey: agentKeys.detail(id),
    queryFn: () => agentsApi.getById(id),
    enabled: !!id,
  });
};

export const useAgentStatus = (id: string, enabled = true) => {
  return useQuery({
    queryKey: agentKeys.status(id),
    queryFn: () => agentsApi.getStatus(id),
    enabled: !!id && enabled,
    refetchInterval: 5000, // Refresh every 5 seconds
  });
};

export const useStartAgent = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: StartAgentRequest) => agentsApi.start(data),
    onSuccess: (_, variables) => {
      // Invalidate and refetch agent data
      queryClient.invalidateQueries({ queryKey: agentKeys.detail(variables.agentId) });
      queryClient.invalidateQueries({ queryKey: agentKeys.lists() });
    },
  });
};

export const useStopAgent = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: StopAgentRequest) => agentsApi.stop(data),
    onSuccess: (_, variables) => {
      // Invalidate and refetch agent data
      queryClient.invalidateQueries({ queryKey: agentKeys.detail(variables.agentId) });
      queryClient.invalidateQueries({ queryKey: agentKeys.lists() });
    },
  });
};
