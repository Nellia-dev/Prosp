import { useQuery } from '@tanstack/react-query';
import { metricsApi } from '../../services/api';
import type { DashboardMetricsResponse, RecentActivityItem } from '../../types/nellia'; // Added import

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
// Helper function to provide default metrics structure, matching DashboardMetricsResponse
const getDefaultMetrics = () => ({
  totalLeads: 0,
  totalAgents: 0,
  activeAgents: 0,
  processingRate: 0,
  successRate: 0,
  recentActivity: [],
  lastUpdated: new Date().toISOString(), // Ensure lastUpdated is a string for consistency if used directly
});

export const useDashboardMetrics = () => {
  return useQuery({
    queryKey: metricsKeys.dashboard(),
    queryFn: metricsApi.getDashboard, // This now returns Promise<DashboardMetricsResponse>
    select: (apiData: DashboardMetricsResponse | undefined) => { // Explicitly type apiData
      const defaults = getDefaultMetrics(); // This is DashboardMetricsResponse
      if (!apiData) { // If apiData is undefined
        return defaults;
      }
      // apiData is DashboardMetricsResponse here
      return {
        totalLeads: apiData.totalLeads ?? defaults.totalLeads,
        totalAgents: apiData.totalAgents ?? defaults.totalAgents,
        activeAgents: apiData.activeAgents ?? defaults.activeAgents,
        processingRate: apiData.processingRate ?? defaults.processingRate,
        successRate: apiData.successRate ?? defaults.successRate,
        recentActivity: apiData.recentActivity || defaults.recentActivity, // Ensure array
        lastUpdated: apiData.lastUpdated
          ? (typeof apiData.lastUpdated === 'string' ? apiData.lastUpdated : new Date(apiData.lastUpdated).toISOString())
          : defaults.lastUpdated,
      };
    },
    placeholderData: getDefaultMetrics(), // Call the function to provide the object
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
