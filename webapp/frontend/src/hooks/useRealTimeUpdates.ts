import { useEffect, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useNelliaSocket } from './useSocketIO';
import { useToast } from './use-toast';
import { AgentStatus, LeadData, AgentMetrics } from '../types/nellia';

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

// Combined hook for all real-time updates
export const useRealTimeUpdates = () => {
  useRealTimeAgentUpdates();
  useRealTimeLeadUpdates();
  useRealTimeMetricsUpdates();
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
