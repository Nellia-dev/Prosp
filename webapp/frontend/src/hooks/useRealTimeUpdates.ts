import { useEffect, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useWebSocket } from '../contexts/WebSocketContext';
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
  const { subscribe, isConnected } = useWebSocket();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  useEffect(() => {
    if (!isConnected) return;

    // Agent status updates
    const unsubscribeAgentStatus = subscribe('agent:status:updated', (data) => {
      const { agentId, status, metrics } = data as unknown as AgentStatusUpdateEvent;

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
    });

    // Agent metrics updates
    const unsubscribeAgentMetrics = subscribe('agent:metrics:updated', (data) => {
      const { agentId, metrics } = data as unknown as AgentMetricsUpdateEvent;

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
    });

    return () => {
      unsubscribeAgentStatus();
      unsubscribeAgentMetrics();
    };
  }, [isConnected, subscribe, queryClient, toast]);
};

export const useRealTimeLeadUpdates = () => {
  const { subscribe, isConnected } = useWebSocket();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  useEffect(() => {
    if (!isConnected) return;

    // Lead stage updates
    const unsubscribeLeadStage = subscribe('lead:stage:updated', (data) => {
      const { leadId, stage, updatedAt } = data as unknown as LeadStageUpdateEvent;

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
    });

    // Lead processing updates
    const unsubscribeLeadProcessing = subscribe('lead:processing:updated', (data) => {
      const { leadId, processingStatus, progress, results } = data as unknown as LeadProcessingUpdateEvent;

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
    });

    // Lead created
    const unsubscribeLeadCreated = subscribe('lead:created', (data) => {
      const newLead = data as unknown as LeadData;
      
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
    });

    // Lead deleted
    const unsubscribeLeadDeleted = subscribe('lead:deleted', (data) => {
      const { leadId } = data as unknown as LeadDeletedEvent;
      
      queryClient.setQueryData(['leads'], (oldData: { leads?: LeadData[]; total?: number } | undefined) => {
        if (!oldData?.leads) return oldData;
        
        return {
          ...oldData,
          leads: oldData.leads.filter((lead: LeadData) => lead.id !== leadId),
          total: Math.max(0, (oldData.total || 0) - 1),
        };
      });

      queryClient.removeQueries({ queryKey: ['leads', leadId] });
    });

    return () => {
      unsubscribeLeadStage();
      unsubscribeLeadProcessing();
      unsubscribeLeadCreated();
      unsubscribeLeadDeleted();
    };
  }, [isConnected, subscribe, queryClient, toast]);
};

export const useRealTimeMetricsUpdates = () => {
  const { subscribe, isConnected } = useWebSocket();
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!isConnected) return;

    // Dashboard metrics updates
    const unsubscribeMetrics = subscribe('metrics:dashboard:updated', (data) => {
      const metrics = data as unknown as Record<string, unknown>;
      
      queryClient.setQueryData(['metrics', 'dashboard'], metrics);
    });

    // Performance metrics updates
    const unsubscribePerformance = subscribe('metrics:performance:updated', (data) => {
      const performanceData = data as unknown as Record<string, unknown>;
      
      queryClient.setQueryData(['metrics', 'performance'], performanceData);
    });

    // Agent performance updates
    const unsubscribeAgentPerformance = subscribe('metrics:agent-performance:updated', (data) => {
      const agentPerformanceData = data as unknown as Record<string, unknown>;
      
      queryClient.setQueryData(['metrics', 'agent-performance'], agentPerformanceData);
    });

    return () => {
      unsubscribeMetrics();
      unsubscribePerformance();
      unsubscribeAgentPerformance();
    };
  }, [isConnected, subscribe, queryClient]);
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
  const { subscribe, isConnected } = useWebSocket();

  const wrappedCallback = useCallback((data: WebSocketEventData) => {
    callback(data as unknown as T);
  }, dependencies);

  useEffect(() => {
    if (!isConnected) return;

    const unsubscribe = subscribe(eventName, wrappedCallback);
    return unsubscribe;
  }, [isConnected, eventName, wrappedCallback, subscribe]);
};
