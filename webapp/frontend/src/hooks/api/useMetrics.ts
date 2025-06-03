import { useQuery } from '@tanstack/react-query';
import { metricsApi } from '../../services/api';

// Query keys
export const metricsKeys = {
  all: ['metrics'] as const,
  dashboard: () => [...metricsKeys.all, 'dashboard'] as const,
  performance: (timeRange: string) => [...metricsKeys.all, 'performance', timeRange] as const,
  agentPerformance: () => [...metricsKeys.all, 'agent-performance'] as const,
  leadStats: () => [...metricsKeys.all, 'lead-stats'] as const,
  summary: () => [...metricsKeys.all, 'summary'] as const,
};

// Hooks
export const useDashboardMetrics = () => {
  return useQuery({
    queryKey: metricsKeys.dashboard(),
    queryFn: metricsApi.getDashboard,
    refetchInterval: 30000, // Refetch every 30 seconds
  });
};

export const usePerformanceMetrics = (timeRange = '24h') => {
  return useQuery({
    queryKey: metricsKeys.performance(timeRange),
    queryFn: () => metricsApi.getPerformance(timeRange),
    refetchInterval: 60000, // Refetch every minute
  });
};

export const useAgentPerformanceMetrics = () => {
  return useQuery({
    queryKey: metricsKeys.agentPerformance(),
    queryFn: metricsApi.getAgentPerformance,
    refetchInterval: 30000, // Refetch every 30 seconds
  });
};

export const useLeadStatsMetrics = () => {
  return useQuery({
    queryKey: metricsKeys.leadStats(),
    queryFn: metricsApi.getLeadStats,
    refetchInterval: 60000, // Refetch every minute
  });
};

export const useMetricsSummary = () => {
  return useQuery({
    queryKey: metricsKeys.summary(),
    queryFn: metricsApi.getSummary,
    refetchInterval: 30000, // Refetch every 30 seconds
  });
};
