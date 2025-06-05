import { Injectable, Logger } from '@nestjs/common';
import { WebSocketService } from './websocket.service';
import { RealTimeEntity, RealTimeAction } from './dto/websocket.dto';

@Injectable()
export class WebSocketEventsService {
  private readonly logger = new Logger(WebSocketEventsService.name);

  constructor(private readonly webSocketService: WebSocketService) {}

  // Agent-related events
  emitAgentStatusChange(agentData: {
    id: string;
    name: string;
    status: string;
    current_task?: string;
    metrics?: any;
  }) {
    this.webSocketService.broadcastAgentStatusUpdate({
      ...agentData,
      last_updated: new Date().toISOString(),
    });

    this.webSocketService.broadcastRealTimeUpdate({
      entity: RealTimeEntity.AGENT,
      action: RealTimeAction.UPDATE,
      data: agentData,
      timestamp: new Date().toISOString(),
    });
  }

  emitAgentStarted(agentData: { id: string; name: string }) {
    this.webSocketService.broadcastRealTimeUpdate({
      entity: RealTimeEntity.AGENT,
      action: RealTimeAction.UPDATE,
      data: { ...agentData, status: 'active' },
      timestamp: new Date().toISOString(),
    });
  }

  emitAgentStopped(agentData: { id: string; name: string }) {
    this.webSocketService.broadcastRealTimeUpdate({
      entity: RealTimeEntity.AGENT,
      action: RealTimeAction.UPDATE,
      data: { ...agentData, status: 'inactive' },
      timestamp: new Date().toISOString(),
    });
  }

  // Lead-related events
  emitLeadCreated(leadData: any) {
    this.webSocketService.broadcastLeadUpdate(leadData);

    this.webSocketService.broadcastRealTimeUpdate({
      entity: RealTimeEntity.LEAD,
      action: RealTimeAction.CREATE,
      data: leadData,
      timestamp: new Date().toISOString(),
    });
  }

  emitLeadUpdated(leadData: any) {
    this.webSocketService.broadcastLeadUpdate(leadData);

    this.webSocketService.broadcastRealTimeUpdate({
      entity: RealTimeEntity.LEAD,
      action: RealTimeAction.UPDATE,
      data: leadData,
      timestamp: new Date().toISOString(),
    });
  }

  emitLeadStageChanged(leadData: {
    id: string;
    company_name: string;
    previous_stage: string;
    new_stage: string;
    agent_id?: string;
  }) {
    this.webSocketService.broadcastRealTimeUpdate({
      entity: RealTimeEntity.LEAD,
      action: RealTimeAction.UPDATE,
      data: {
        type: 'stage_change',
        ...leadData,
      },
      timestamp: new Date().toISOString(),
    });
  }

  emitProcessingProgress(progressData: {
    lead_id: string;
    current_agent: string;
    progress_percentage: number;
    current_step: string;
    estimated_completion?: string;
  }) {
    this.webSocketService.broadcastProcessingProgress({
      ...progressData,
      estimated_completion: progressData.estimated_completion || 
        new Date(Date.now() + 30000).toISOString(),
    });
  }

  // Metrics-related events
  emitMetricsUpdate(metricsData: {
    totalLeads?: number;
    completedLeads?: number;
    averageProcessingTime?: number;
    successRate?: number;
    activeAgents?: number;
  }) {
    this.webSocketService.broadcastMetricsUpdate({
      ...metricsData,
      lastUpdated: new Date().toISOString(),
    });

    this.webSocketService.broadcastRealTimeUpdate({
      entity: RealTimeEntity.METRICS,
      action: RealTimeAction.UPDATE,
      data: metricsData,
      timestamp: new Date().toISOString(),
    });
  }

  // Batch operations
  emitBatchOperationStarted(operationData: {
    operation_type: string;
    total_items: number;
    estimated_duration?: number;
  }) {
    this.webSocketService.broadcastRealTimeUpdate({
      entity: RealTimeEntity.METRICS,
      action: RealTimeAction.PROCESS,
      data: {
        type: 'batch_operation_started',
        ...operationData,
      },
      timestamp: new Date().toISOString(),
    });
  }

  emitBatchOperationProgress(progressData: {
    operation_type: string;
    completed_items: number;
    total_items: number;
    current_item?: string;
  }) {
    const progress_percentage = (progressData.completed_items / progressData.total_items) * 100;

    this.webSocketService.broadcastRealTimeUpdate({
      entity: RealTimeEntity.METRICS,
      action: RealTimeAction.PROCESS,
      data: {
        type: 'batch_operation_progress',
        ...progressData,
        progress_percentage,
      },
      timestamp: new Date().toISOString(),
    });
  }

  emitBatchOperationCompleted(resultData: {
    operation_type: string;
    total_items: number;
    successful_items: number;
    failed_items: number;
    duration: number;
  }) {
    this.webSocketService.broadcastRealTimeUpdate({
      entity: RealTimeEntity.METRICS,
      action: RealTimeAction.PROCESS,
      data: {
        type: 'batch_operation_completed',
        ...resultData,
      },
      timestamp: new Date().toISOString(),
    });
  }

  // System-level events
  emitSystemAlert(alertData: {
    level: 'info' | 'warning' | 'error';
    message: string;
    details?: any;
  }) {
    this.webSocketService.broadcastRealTimeUpdate({
      entity: RealTimeEntity.METRICS,
      action: RealTimeAction.UPDATE,
      data: {
        type: 'system_alert',
        ...alertData,
      },
      timestamp: new Date().toISOString(),
    });
  }

  // Connection and health events
  emitHealthStatusUpdate(healthData: {
    component: string;
    status: 'healthy' | 'degraded' | 'unhealthy';
    details?: any;
  }) {
    this.webSocketService.broadcastRealTimeUpdate({
      entity: RealTimeEntity.METRICS,
      action: RealTimeAction.UPDATE,
      data: {
        type: 'health_status_update',
        ...healthData,
      },
      timestamp: new Date().toISOString(),
    });
  }
}