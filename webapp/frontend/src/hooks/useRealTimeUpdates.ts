import { useEffect, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useNelliaSocket } from './useSocketIO';
import { useToast } from './use-toast';
import { AgentStatus, LeadData, AgentMetrics } from '../types/nellia';
import { useAuth } from '../contexts/AuthContext';

// Define WebSocket event data types
interface WebSocketEventData {
  [key: string]: unknown;
}

type ProcessingStage = LeadData['processing_stage'];

interface AgentStatusUpdateEvent {
  agentId: string;
  status: AgentStatus['status'];
  metrics?: AgentMetrics;
}

interface AgentMetricsUpdateEvent {
  agentId: string;
  metrics: Partial<AgentMetrics>;
}

interface LeadStageUpdateEvent {
  leadId: string;
  stage: ProcessingStage;
  updatedAt: string;
}

interface LeadProcessingUpdateEvent {
  leadId: string;
  processingStatus: string;
  progress?: number;
  results?: Record<string, unknown>;
}

interface LeadDeletedEvent {
  leadId: string;
}

// New interfaces for quota and job updates
interface QuotaUpdateEvent {
  userId: string;
  planId: string;
  planName: string;
  quotaUsed: number;
  quotaTotal: number;
  quotaRemaining: number;
  quotaUsagePercentage: number;
  nextResetAt?: string;
  leadsGenerated?: number;
  timestamp: string;
}

interface JobProgressEvent {
  jobId: string;
  userId: string;
  status: string;
  progress: number;
  currentStep?: string;
  searchQuery?: string;
  timestamp: string;
}

interface JobCompletedEvent {
  jobId: string;
  userId: string;
  status: 'completed';
  leadsGenerated: number;
  searchQuery?: string;
  quotaUpdate?: QuotaUpdateEvent;
  startedAt: string;
  completedAt: string;
  timestamp: string;
}

interface JobFailedEvent {
  jobId: string;
  userId: string;
  status: 'failed';
  error: string;
  searchQuery?: string;
  startedAt: string;
  failedAt: string;
  timestamp: string;
}

export const useRealTimeAgentUpdates = () => {
  const socket = useNelliaSocket();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  useEffect(() => {
    if (!socket.isConnected) return;

    // Subscribe to agent updates
    socket.subscribe(['agents']);

    const handleAgentStatusUpdate = (data: unknown) => {
      const { agentId, status, metrics } = data as AgentStatusUpdateEvent;

      // Update agent in cache
      queryClient.setQueryData(['agents'], (oldData: { agents?: AgentStatus[] } | undefined) => {
        if (!oldData?.agents) return oldData;
        
        return {
          ...oldData,
          agents: oldData.agents.map((agent: AgentStatus) =>
            agent.id === agentId
              ? { ...agent, status, metrics: metrics || agent.metrics }
              : agent
          ),
        };
      });

      // Update specific agent query
      queryClient.invalidateQueries({ queryKey: ['agents', agentId] });
      
      // Show notification for status changes
      if (status === 'error') {
        toast({
          title: "Agent Error",
          description: `Agent ${agentId} encountered an error`,
          variant: "destructive",
        });
      }
    };

    const handleAgentMetricsUpdate = (data: unknown) => {
      const { agentId, metrics } = data as AgentMetricsUpdateEvent;

      queryClient.setQueryData(['agents'], (oldData: { agents?: AgentStatus[] } | undefined) => {
        if (!oldData?.agents) return oldData;
        
        return {
          ...oldData,
          agents: oldData.agents.map((agent: AgentStatus) =>
            agent.id === agentId
              ? { ...agent, metrics: { ...agent.metrics, ...metrics } }
              : agent
          ),
        };
      });

      // Invalidate metrics queries
      queryClient.invalidateQueries({ queryKey: ['metrics'] });
    };

    // Listen for Socket.IO events (these will be handled automatically by the useSocketIO hook)
    // The automatic query invalidation will handle most updates
    // We keep these handlers for specific UI notifications

    return () => {
      // Socket.IO disconnection is handled by useSocketIO hook
    };
  }, [socket.isConnected, socket, queryClient, toast]);
};

export const useRealTimeLeadUpdates = () => {
  const socket = useNelliaSocket();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  useEffect(() => {
    if (!socket.isConnected) return;

    // Subscribe to lead updates
    socket.subscribe(['leads']);

    const handleLeadStageUpdate = (data: unknown) => {
      const { leadId, stage, updatedAt } = data as LeadStageUpdateEvent;

      // Update lead in cache
      queryClient.setQueryData(['leads'], (oldData: { leads?: LeadData[] } | undefined) => {
        if (!oldData?.leads) return oldData;
        
        return {
          ...oldData,
          leads: oldData.leads.map((lead: LeadData) =>
            lead.id === leadId
              ? { ...lead, processing_stage: stage, updated_at: updatedAt }
              : lead
          ),
        };
      });

      // Update specific lead query
      queryClient.setQueryData(['leads', leadId], (oldData: LeadData | undefined) => {
        if (!oldData) return oldData;
        return { ...oldData, processing_stage: stage, updated_at: updatedAt };
      });

      // Invalidate stage-based queries
      queryClient.invalidateQueries({ queryKey: ['leads', 'by-stage'] });
    };

    const handleLeadProcessingUpdate = (data: unknown) => {
      const { leadId, processingStatus, progress, results } = data as LeadProcessingUpdateEvent;

      queryClient.setQueryData(['leads', leadId], (oldData: LeadData | undefined) => {
        if (!oldData) return oldData;
        return {
          ...oldData,
          // Note: These fields might need to be added to LeadData interface
          // processingStatus,
          // processingProgress: progress,
          // processingResults: results,
        };
      });

      // Show progress notification
      if (progress !== undefined) {
        toast({
          title: "Processing Lead",
          description: `Lead processing ${progress}% complete`,
          duration: 2000,
        });
      }
    };

    const handleLeadCreated = (data: unknown) => {
      const newLead = data as LeadData;
      
      queryClient.setQueryData(['leads'], (oldData: { leads?: LeadData[]; total?: number } | undefined) => {
        if (!oldData?.leads) return { leads: [newLead], total: 1 };
        
        return {
          ...oldData,
          leads: [newLead, ...oldData.leads],
          total: (oldData.total || 0) + 1,
        };
      });

      toast({
        title: "New Lead",
        description: `New lead: ${newLead.company_name}`,
        duration: 3000,
      });
    };

    const handleLeadDeleted = (data: unknown) => {
      const { leadId } = data as LeadDeletedEvent;
      
      queryClient.setQueryData(['leads'], (oldData: { leads?: LeadData[]; total?: number } | undefined) => {
        if (!oldData?.leads) return oldData;
        
        return {
          ...oldData,
          leads: oldData.leads.filter((lead: LeadData) => lead.id !== leadId),
          total: Math.max(0, (oldData.total || 0) - 1),
        };
      });

      queryClient.removeQueries({ queryKey: ['leads', leadId] });
    };

    return () => {
      // Socket.IO disconnection is handled by useSocketIO hook
    };
  }, [socket.isConnected, socket, queryClient, toast]);
};

export const useRealTimeMetricsUpdates = () => {
  const socket = useNelliaSocket();
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!socket.isConnected) return;

    // Subscribe to metrics updates
    socket.subscribe(['metrics']);

    const handleMetricsUpdate = (data: unknown) => {
      const metrics = data as Record<string, unknown>;
      
      queryClient.setQueryData(['metrics', 'dashboard'], metrics);
    };

    const handlePerformanceUpdate = (data: unknown) => {
      const performanceData = data as Record<string, unknown>;
      
      queryClient.setQueryData(['metrics', 'performance'], performanceData);
    };

    const handleAgentPerformanceUpdate = (data: unknown) => {
      const agentPerformanceData = data as Record<string, unknown>;
      
      queryClient.setQueryData(['metrics', 'agent-performance'], agentPerformanceData);
    };

    return () => {
      // Socket.IO disconnection is handled by useSocketIO hook
    };
  }, [socket.isConnected, socket, queryClient]);
};

// New hooks for quota and job updates
export const useRealTimeQuotaUpdates = () => {
  const socket = useNelliaSocket();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { user } = useAuth();

  useEffect(() => {
    if (!socket.isConnected || !user) return;

    // Join user-specific room for quota updates
    socket.emit('join-user-room', { userId: user.id });

    // Listen for quota updates through lastMessage
    if (socket.lastMessage?.type === 'quota-updated') {
      const quotaData = socket.lastMessage.data as QuotaUpdateEvent;
      
      // Only process updates for the current user
      if (quotaData.userId !== user.id) return;

      // Update user plan status cache
      queryClient.setQueryData(['user-plan-status'], (oldData: Record<string, unknown> | undefined) => {
        if (!oldData) return oldData;
        
        return {
          ...oldData,
          quotaUsed: quotaData.quotaUsed,
          quotaTotal: quotaData.quotaTotal,
          quotaRemaining: quotaData.quotaRemaining,
          quotaUsagePercentage: quotaData.quotaUsagePercentage,
          lastUpdated: quotaData.timestamp,
        };
      });

      // Show notification for quota updates
      if (quotaData.leadsGenerated && quotaData.leadsGenerated > 0) {
        toast({
          title: "Quota Updated",
          description: `Generated ${quotaData.leadsGenerated} new leads. ${quotaData.quotaRemaining} leads remaining.`,
          duration: 5000,
        });
      }

      // Warning for low quota
      if (quotaData.quotaUsagePercentage >= 90) {
        toast({
          title: "Quota Nearly Exhausted",
          description: `You've used ${quotaData.quotaUsagePercentage}% of your quota. Consider upgrading your plan.`,
          variant: "destructive",
          duration: 8000,
        });
      }
    }
  }, [socket.lastMessage, socket.isConnected, queryClient, toast, user]);
};

export const useRealTimeJobUpdates = () => {
  const socket = useNelliaSocket();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { user } = useAuth();

  useEffect(() => {
    if (!socket.isConnected || !user) return;

    // Join user-specific room for job updates
    socket.emit('join-user-room', { userId: user.id });

    // Listen for job updates through lastMessage
    if (socket.lastMessage?.type === 'job-progress') {
      const jobData = socket.lastMessage.data as JobProgressEvent;
      
      // Only process updates for the current user
      if (jobData.userId !== user.id) return;

      // Update prospect job status cache
      queryClient.setQueryData(['prospect-job-status'], (oldData: Record<string, unknown> | undefined) => {
        return {
          ...oldData,
          jobId: jobData.jobId,
          status: jobData.status,
          progress: jobData.progress,
          currentStep: jobData.currentStep,
          searchQuery: jobData.searchQuery,
          lastUpdated: jobData.timestamp,
        };
      });

      // Show progress notification
      toast({
        title: "Job Progress",
        description: `${jobData.currentStep || 'Processing'}: ${jobData.progress}% complete`,
        duration: 3000,
      });
    }

    if (socket.lastMessage?.type === 'job-completed') {
      const jobData = socket.lastMessage.data as JobCompletedEvent;
      
      // Only process updates for the current user
      if (jobData.userId !== user.id) return;

      // Clear job status
      queryClient.setQueryData(['prospect-job-status'], null);

      // Invalidate related queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      queryClient.invalidateQueries({ queryKey: ['metrics'] });
      queryClient.invalidateQueries({ queryKey: ['user-plan-status'] });

      // Show success notification
      toast({
        title: "Job Completed Successfully",
        description: `Generated ${jobData.leadsGenerated} new leads for "${jobData.searchQuery}"`,
        duration: 6000,
      });

      // Handle quota update if included
      if (jobData.quotaUpdate) {
        queryClient.setQueryData(['user-plan-status'], (oldData: Record<string, unknown> | undefined) => {
          if (!oldData) return oldData;
          
          return {
            ...oldData,
            quotaUsed: jobData.quotaUpdate!.quotaUsed,
            quotaTotal: jobData.quotaUpdate!.quotaTotal,
            quotaRemaining: jobData.quotaUpdate!.quotaRemaining,
            quotaUsagePercentage: jobData.quotaUpdate!.quotaUsagePercentage,
            lastUpdated: jobData.quotaUpdate!.timestamp,
          };
        });
      }
    }

    if (socket.lastMessage?.type === 'job-failed') {
      const jobData = socket.lastMessage.data as JobFailedEvent;
      
      // Only process updates for the current user
      if (jobData.userId !== user.id) return;

      // Clear job status
      queryClient.setQueryData(['prospect-job-status'], null);

      // Show error notification
      toast({
        title: "Job Failed",
        description: `Failed to process "${jobData.searchQuery}": ${jobData.error}`,
        variant: "destructive",
        duration: 8000,
      });
    }
  }, [socket.lastMessage, socket.isConnected, queryClient, toast, user]);
};

// Combined hook for all real-time updates
export const useRealTimeUpdates = () => {
  useRealTimeAgentUpdates();
  useRealTimeLeadUpdates();
  useRealTimeMetricsUpdates();
  useRealTimeQuotaUpdates();
  useRealTimeJobUpdates();
};

// Hook for subscribing to custom events
export const useRealTimeEvent = <T extends WebSocketEventData = WebSocketEventData>(
  eventName: string,
  callback: (data: T) => void,
  dependencies: unknown[] = []
) => {
  const socket = useNelliaSocket();

  const wrappedCallback = useCallback((data: WebSocketEventData) => {
    callback(data as T);
  }, dependencies);

  useEffect(() => {
    if (!socket.isConnected) return;

    // For Socket.IO, we can't directly subscribe to custom events like the old WebSocket context
    // Instead, the events are automatically handled by the useSocketIO hook
    // This hook is kept for compatibility but events are handled in useSocketIO

    return () => {
      // Cleanup is handled by useSocketIO hook
    };
  }, [socket.isConnected, eventName, wrappedCallback, socket]);
};
