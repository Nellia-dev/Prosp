import { useEffect, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useWebSocket } from '../contexts/WebSocketContext';
import { useToast } from './use-toast';
import { AgentStatus, LeadData, AgentMetrics, DashboardMetrics, ProcessingStage } from '../types/unified';
import { useAuth } from '../contexts/AuthContext';

// Import the new unified event types for perfect alignment
import {
  // Prospect pipeline events
  ProspectPipelineEvent,
  LeadGeneratedEvent,
  LeadEnrichmentStartEvent,
  LeadEnrichmentEndEvent,
  StatusUpdateEvent,
  PipelineEndEvent,
  PipelineErrorEvent,
  
  // WebSocket events
  QuotaUpdateEvent,
  JobProgressEvent,
  JobCompletedEvent,
  JobFailedEvent,
  LeadCreatedEvent,
  LeadEnrichedEvent,
  LeadEnrichmentFailedEvent,
  LeadStageUpdateEvent,
  LeadDeletedEvent,
  AgentStatusUpdateEvent,
  MetricsUpdateEvent,
  
  // Enrichment progress events
  EnrichmentProgressEvent,
  JobStatusUpdateEvent,
  
  // Union types
  WebSocketEvent,
  
  // Event name constants
  WebSocketEventNames,
  
  // Type guards
  isProspectPipelineEvent,
  isLeadGeneratedEvent,
  isLeadEnrichmentStartEvent,
  isLeadEnrichmentEndEvent,
  isPipelineEndEvent,
  isStatusUpdateEvent,
  isPipelineErrorEvent,
  isQuotaUpdateEvent,
  isJobCompletedEvent,
  isJobFailedEvent,
} from '../types/events';

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

    const handleLeadEnriched = (data: LeadEnrichedEvent) => {
      const updatedLead = data.lead;
      queryClient.setQueryData(['leads'], (oldData: { data?: LeadData[] } | undefined) => {
        if (!oldData?.data) return oldData;
        return {
          ...oldData,
          data: oldData.data.map(lead =>
            lead.id === updatedLead.id ? { ...lead, ...updatedLead } : lead
          ),
        };
      });
      queryClient.invalidateQueries({ queryKey: ['leads', updatedLead.id] });
      toast({
        title: "Lead Enriched",
        description: `Lead ${updatedLead.company_name} has been fully enriched.`,
      });
    };

    const handleLeadEnrichmentFailed = (data: LeadEnrichmentFailedEvent) => {
      queryClient.setQueryData(['leads'], (oldData: { data?: LeadData[] } | undefined) => {
        if (!oldData?.data) return oldData;
        return {
          ...oldData,
          data: oldData.data.map(lead =>
            lead.id === data.leadId ? { ...lead, processing_stage: 'failed' as ProcessingStage } : lead
          ),
        };
      });
      queryClient.invalidateQueries({ queryKey: ['leads', data.leadId] });
      toast({
        title: "Lead Enrichment Failed",
        description: data.error,
        variant: "destructive",
      });
    };

    const unsubEnriched = subscribe<LeadEnrichedEvent>('lead-enriched', handleLeadEnriched);
    const unsubFailed = subscribe<LeadEnrichmentFailedEvent>('lead_enrichment_failed', handleLeadEnrichmentFailed);

    return () => {
      unsubCreated();
      unsubStage();
      unsubDeleted();
      unsubEnriched();
      unsubFailed();
    };
  }, [subscribe, queryClient, toast]);

  // Handle Metrics Updates
  useEffect(() => {
    const handleMetricsUpdate = (data: DashboardMetrics) => {
      queryClient.setQueryData(['dashboard-metrics'], data);
    };
    const unsubscribe = subscribe<DashboardMetrics>('metrics-update', handleMetricsUpdate);
    return unsubscribe;
  }, [subscribe, queryClient]);

  // Handle Enrichment Updates (prospect pipeline events)
  useEffect(() => {
    const handleEnrichmentUpdate = (data: ProspectPipelineEvent) => {
      // Use type guards to safely handle different event types
      if (isProspectPipelineEvent(data)) {
        queryClient.setQueryData(['enrichment-status', data.job_id], (oldData: { events: ProspectPipelineEvent[] } | undefined) => {
          const newEvents = oldData ? [...oldData.events, data] : [data];
          return { events: newEvents, lastUpdate: new Date().toISOString() };
        });

        // Handle specific pipeline events
        if (isPipelineEndEvent(data)) {
          toast({
            title: "Enrichment Complete",
            description: `Lead enrichment finished for job ${data.job_id}`,
          });
          queryClient.invalidateQueries({ queryKey: ['leads'] });
        }

        if (isStatusUpdateEvent(data)) {
          // Handle status updates with progress information
          if (data.lead_id && data.progress_percentage !== undefined) {
            toast({
              title: "Enrichment Progress",
              description: `${data.status_message}: ${data.progress_percentage}%`,
              duration: 2000,
            });
          }
        }

        if (isPipelineErrorEvent(data)) {
          toast({
            title: "Enrichment Error",
            description: data.error_message,
            variant: "destructive",
          });
        }
      }
    };
    const unsubscribe = subscribe<ProspectPipelineEvent>('enrichment-update', handleEnrichmentUpdate);
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
export const useRealTimeEvent = <T extends WebSocketEvent = WebSocketEvent>(
  eventName: string,
  callback: (data: T) => void,
  dependencies: unknown[] = []
) => {
  const { subscribe } = useWebSocket();

  const wrappedCallback = useCallback((data: WebSocketEvent) => {
    callback(data as T);
  }, dependencies);

  useEffect(() => {
    const unsubscribe = subscribe(eventName, wrappedCallback);
    return unsubscribe;
  }, [eventName, wrappedCallback, subscribe]);
};
