import { useEffect, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useWebSocket } from '../contexts/WebSocketContext';
import { useToast } from './use-toast';
import { AgentStatus, LeadData, AgentMetrics, DashboardMetricsResponse } from '../types/nellia';
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

interface LeadStageUpdateEvent {
  leadId: string;
  stage: ProcessingStage;
  updatedAt: string;
}

interface LeadCreatedEvent {
  lead: LeadData;
}

interface LeadDeletedEvent {
  leadId: string;
}

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

interface EnrichmentEvent {
  event_type: string;
  job_id: string;
  [key: string]: unknown;
}

// Combined hook for all real-time updates
export const useRealTimeUpdates = () => {
  const { isConnected, emit, subscribe } = useWebSocket();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { user } = useAuth();

  // Subscribe to rooms/entities
  useEffect(() => {
    if (isConnected) {
      emit('subscribe', { entities: ['agents', 'leads', 'metrics', 'enrichment'] });
      if (user?.id) {
        emit('join-user-room', { userId: user.id });
      }

      return () => {
        emit('unsubscribe', { entities: ['agents', 'leads', 'metrics', 'enrichment'] });
      };
    }
  }, [isConnected, emit, user?.id]);

  // Handle Agent Updates
  useEffect(() => {
    const handleAgentUpdate = (data: AgentStatus) => {
      queryClient.setQueryData(['agents'], (oldData: AgentStatus[] | undefined) => {
        if (!oldData) return [data];
        const existing = oldData.find(a => a.id === data.id);
        if (existing) {
          return oldData.map(a => a.id === data.id ? data : a);
        }
        return [...oldData, data];
      });
      queryClient.invalidateQueries({ queryKey: ['agents', data.id] });
    };

    const unsubscribe = subscribe<AgentStatus>('agent-update', handleAgentUpdate);
    return unsubscribe;
  }, [subscribe, queryClient]);

  // Handle Lead Updates
  useEffect(() => {
    const handleLeadCreated = (data: LeadCreatedEvent) => {
      const newLead = data.lead;
      queryClient.setQueryData(['leads'], (oldData: { data?: LeadData[] } | undefined) => {
        if (!oldData?.data) return { data: [newLead] };
        return { ...oldData, data: [newLead, ...oldData.data] };
      });
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      toast({
        title: "New Lead Generated",
        description: `Successfully generated lead: ${newLead.company_name}`,
      });
    };

    const handleLeadStageUpdate = (data: LeadStageUpdateEvent) => {
      queryClient.setQueryData(['leads'], (oldData: { data?: LeadData[] } | undefined) => {
        if (!oldData?.data) return oldData;
        return {
          ...oldData,
          data: oldData.data.map(lead =>
            lead.id === data.leadId ? { ...lead, processing_stage: data.stage, updated_at: data.updatedAt } : lead
          ),
        };
      });
      queryClient.invalidateQueries({ queryKey: ['leads', data.leadId] });
    };

    const handleLeadDeleted = (data: LeadDeletedEvent) => {
        queryClient.setQueryData(['leads'], (oldData: { data?: LeadData[] } | undefined) => {
            if (!oldData?.data) return oldData;
            return {
                ...oldData,
                data: oldData.data.filter(lead => lead.id !== data.leadId),
            };
        });
        queryClient.invalidateQueries({ queryKey: ['leads'] });
    };

    const unsubCreated = subscribe<LeadCreatedEvent>('lead-created', handleLeadCreated);
    const unsubStage = subscribe<LeadStageUpdateEvent>('lead-stage-update', handleLeadStageUpdate);
    const unsubDeleted = subscribe<LeadDeletedEvent>('lead-deleted', handleLeadDeleted);

    return () => {
      unsubCreated();
      unsubStage();
      unsubDeleted();
    };
  }, [subscribe, queryClient, toast]);

  // Handle Metrics Updates
  useEffect(() => {
    const handleMetricsUpdate = (data: DashboardMetricsResponse) => {
      queryClient.setQueryData(['dashboard-metrics'], data);
    };
    const unsubscribe = subscribe<DashboardMetricsResponse>('metrics-update', handleMetricsUpdate);
    return unsubscribe;
  }, [subscribe, queryClient]);

  // Handle Enrichment Updates
  useEffect(() => {
    const handleEnrichmentUpdate = (data: EnrichmentEvent) => {
      queryClient.setQueryData(['enrichment-status', data.job_id], (oldData: { events: EnrichmentEvent[] } | undefined) => {
        const newEvents = oldData ? [...oldData.events, data] : [data];
        return { events: newEvents, lastUpdate: new Date().toISOString() };
      });

      if (data.event_type === 'pipeline_end') {
        toast({
          title: "Enrichment Complete",
          description: `Lead enrichment finished for job ${data.job_id}`,
        });
        queryClient.invalidateQueries({ queryKey: ['leads'] });
      }
    };
    const unsubscribe = subscribe<EnrichmentEvent>('enrichment-update', handleEnrichmentUpdate);
    return unsubscribe;
  }, [subscribe, queryClient, toast]);

  // Handle Job and Quota Updates
  useEffect(() => {
    if (!user) return;

    const handleJobProgress = (data: JobProgressEvent) => {
      if (data.userId !== user.id) return;
      queryClient.setQueryData(['prospect-job-status'], data);
      toast({
        title: "Harvesting Progress",
        description: `${data.currentStep || 'Processing'}: ${data.progress}%`,
        duration: 2000,
      });
    };

    const handleJobCompleted = (data: JobCompletedEvent) => {
      if (data.userId !== user.id) return;
      queryClient.setQueryData(['prospect-job-status'], null);
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-metrics'] });
      toast({
        title: "Harvesting Complete",
        description: `Generated ${data.leadsGenerated} new leads.`,
      });
    };

    const handleJobFailed = (data: JobFailedEvent) => {
      if (data.userId !== user.id) return;
      queryClient.setQueryData(['prospect-job-status'], null);
      toast({
        title: "Harvesting Failed",
        description: data.error,
        variant: "destructive",
      });
    };

    const handleQuotaUpdate = (data: QuotaUpdateEvent) => {
      if (data.userId !== user.id) return;
      queryClient.setQueryData(['user-plan-status'], data);
      if (data.quotaUsagePercentage >= 90) {
        toast({
          title: "Quota Alert",
          description: `You have used ${data.quotaUsagePercentage.toFixed(0)}% of your quota.`,
          variant: "destructive",
        });
      }
    };

    const unsubProgress = subscribe<JobProgressEvent>('job-progress', handleJobProgress);
    const unsubCompleted = subscribe<JobCompletedEvent>('job-completed', handleJobCompleted);
    const unsubFailed = subscribe<JobFailedEvent>('job-failed', handleJobFailed);
    const unsubQuota = subscribe<QuotaUpdateEvent>('quota-update', handleQuotaUpdate);

    return () => {
      unsubProgress();
      unsubCompleted();
      unsubFailed();
      unsubQuota();
    };
  }, [subscribe, queryClient, toast, user]);
};

// Hook for subscribing to custom events (for components that need it)
export const useRealTimeEvent = <T extends WebSocketEventData = WebSocketEventData>(
  eventName: string,
  callback: (data: T) => void,
  dependencies: unknown[] = []
) => {
  const { subscribe } = useWebSocket();

  const wrappedCallback = useCallback((data: WebSocketEventData) => {
    callback(data as T);
  }, dependencies);

  useEffect(() => {
    const unsubscribe = subscribe(eventName, wrappedCallback);
    return unsubscribe;
  }, [eventName, wrappedCallback, subscribe]);
};
