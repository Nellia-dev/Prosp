import { useQuery } from '@tanstack/react-query';
import { userApi } from '../../services/api';
import type { UserPlanStatusResponse } from '../../types/api';

/**
 * Hook to fetch and manage user plan status and quota information
 */
export const useUserPlanStatus = () => {
  return useQuery({
    queryKey: ['user', 'planStatus'],
    queryFn: () => userApi.getPlanStatus(),
    staleTime: 30 * 1000, // Consider data stale after 30 seconds
    refetchInterval: 60 * 1000, // Refetch every minute to keep quota info current
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
};

/**
 * Helper hook to get specific plan status information
 */
export const usePlanInfo = () => {
  const { data: planStatus, ...rest } = useUserPlanStatus();
  
  return {
    ...rest,
    planStatus,
    // Convenience getters
    plan: planStatus?.plan,
    quota: planStatus?.quota,
    canStartProspecting: planStatus?.canStartProspecting ?? false,
    hasActiveJob: planStatus?.hasActiveJob ?? false,
    activeJobId: planStatus?.activeJobId,
    // Calculated values
    quotaUsagePercentage: planStatus?.quota && planStatus.quota.total > 0
      ? Math.round((planStatus.quota.used / planStatus.quota.total) * 100)
      : 0,
    isQuotaExhausted: planStatus?.quota 
      ? planStatus.quota.remaining <= 0
      : false,
    // Formatted values
    quotaDisplay: planStatus?.quota 
      ? `${planStatus.quota.used}/${planStatus.quota.total === Infinity ? '∞' : planStatus.quota.total}`
      : '0/0',
    nextResetFormatted: planStatus?.quota?.nextResetAt
      ? new Date(planStatus.quota.nextResetAt).toLocaleDateString()
      : null,
  };
};
