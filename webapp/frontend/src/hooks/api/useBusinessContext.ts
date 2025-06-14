import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { businessContextApi } from '../../services/api';
import type { BusinessContextRequest, BusinessContextResponse } from '../../types/api';

// Query keys
export const businessContextKeys = {
  all: ['business-context'] as const,
  detail: () => [...businessContextKeys.all, 'detail'] as const,
};

// Hooks
export const useBusinessContext = () => {
  return useQuery<BusinessContextResponse | null>({
    queryKey: businessContextKeys.detail(),
    queryFn: () => businessContextApi.get(),
  });
};

export const useCreateBusinessContext = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: BusinessContextRequest) => businessContextApi.create(data),
    onSuccess: (data: BusinessContextResponse) => {
      // Update cache with new data
      queryClient.setQueryData(businessContextKeys.detail(), data);
    },
  });
};

export const useUpdateBusinessContext = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: BusinessContextRequest) => businessContextApi.update(data),
    onSuccess: (data: BusinessContextResponse) => {
      // Update cache with new data
      queryClient.setQueryData(businessContextKeys.detail(), data);
    },
  });
};
