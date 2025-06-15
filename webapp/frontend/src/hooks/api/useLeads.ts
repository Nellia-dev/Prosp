import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { leadsApi } from '../../services/api';
import type {
  LeadFilters,
  CreateLeadRequest,
  UpdateLeadRequest,
  UpdateLeadStageRequest,
  LeadResponse,
  BulkLeadOperation,
} from '../../types/api';

// Query keys
export const leadKeys = {
  all: ['leads'] as const,
  lists: () => [...leadKeys.all, 'list'] as const,
  list: (filters: LeadFilters) => [...leadKeys.lists(), { filters }] as const,
  details: () => [...leadKeys.all, 'detail'] as const,
  detail: (id: string) => [...leadKeys.details(), id] as const,
  byStage: () => [...leadKeys.all, 'by-stage'] as const,
};

// Hooks
export const useLeads = (filters?: LeadFilters) => {
  return useQuery({
    queryKey: leadKeys.list(filters || {}),
    queryFn: () => leadsApi.getAll(filters),
    select: (data) => ({
      data: data?.data || [],
      total: data?.total || 0,
      page: data?.page || 1,
      limit: data?.limit || 10,
      totalPages: data?.totalPages || 0, // Assuming totalPages might be part of the response
    }),
    placeholderData: { data: [], total: 0, page: 1, limit: 10, totalPages: 0 }, // Changed to placeholderData
  });
};

export const useLead = (id: string) => {
  return useQuery({
    queryKey: leadKeys.detail(id),
    queryFn: () => leadsApi.getById(id),
    enabled: !!id,
  });
};

export const useLeadsByStage = () => {
  return useQuery({
    queryKey: leadKeys.byStage(),
    queryFn: leadsApi.getByStage,
  });
};

export const useCreateLead = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateLeadRequest) => leadsApi.create(data),
    onSuccess: () => {
      // Invalidate and refetch leads data
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
      queryClient.invalidateQueries({ queryKey: leadKeys.byStage() });
    },
  });
};

export const useUpdateLead = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateLeadRequest }) =>
      leadsApi.update(id, data),
    onSuccess: (data, variables) => {
      // Update the specific lead in cache
      queryClient.setQueryData(leadKeys.detail(variables.id), data);
      // Invalidate lists to ensure consistency
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
      queryClient.invalidateQueries({ queryKey: leadKeys.byStage() });
    },
  });
};

export const useDeleteLead = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => leadsApi.delete(id),
    onSuccess: (_, id) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: leadKeys.detail(id) });
      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
      queryClient.invalidateQueries({ queryKey: leadKeys.byStage() });
    },
  });
};

export const useUpdateLeadStage = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateLeadStageRequest }) =>
      leadsApi.updateStage(id, data),
    onSuccess: (data, variables) => {
      // Update the specific lead in cache
      queryClient.setQueryData(leadKeys.detail(variables.id), data);
      // Invalidate stage-based queries
      queryClient.invalidateQueries({ queryKey: leadKeys.byStage() });
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
    },
  });
};

export const useBulkLeadOperation = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: BulkLeadOperation) => leadsApi.bulkOperation(data),
    onSuccess: () => {
      // Invalidate all leads queries
      queryClient.invalidateQueries({ queryKey: leadKeys.all });
    },
  });
};

export const useProcessLead = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => leadsApi.process(id),
    onSuccess: (_, id) => {
      // Invalidate the specific lead and lists
      queryClient.invalidateQueries({ queryKey: leadKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
      queryClient.invalidateQueries({ queryKey: leadKeys.byStage() });
    },
  });
};
