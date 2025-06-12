/**
 * Unified Event Types for Frontend
 * 
 * These types are perfectly aligned with:
 * - prospect/event_models.py (Python source of truth)
 * - webapp/backend/src/modules/websocket/dto/websocket.dto.ts (Backend DTOs)
 * 
 * ⚠️ CRITICAL: Any changes here must be synchronized across all three systems
 */

// ===================================
// Base Event Interface
// ===================================

export interface BaseEvent {
  event_type: string;
  timestamp: string;
  job_id: string;
  user_id: string;
}

// ===================================
// Pipeline Events (from prospect/event_models.py)
// ===================================

export interface PipelineStartEvent extends BaseEvent {
  event_type: 'pipeline_start';
  initial_query: string;
  max_leads_to_generate: number;
}

export interface PipelineEndEvent extends BaseEvent {
  event_type: 'pipeline_end';
  total_leads_generated: number;
  execution_time_seconds: number;
  success: boolean;
  error_message?: string;
}

export interface AgentStartEvent extends BaseEvent {
  event_type: 'agent_start';
  agent_name: string;
  agent_description: string;
  input_query: string;
}

export interface AgentEndEvent extends BaseEvent {
  event_type: 'agent_end';
  agent_name: string;
  execution_time_seconds: number;
  success: boolean;
  final_response?: string;
  error_message?: string;
}

export interface ToolCallStartEvent extends BaseEvent {
  event_type: 'tool_call_start';
  tool_name: string;
  agent_name: string;
  tool_args: Record<string, unknown>;
}

export interface ToolCallOutputEvent extends BaseEvent {
  event_type: 'tool_call_output';
  tool_name: string;
  agent_name: string;
  output_snippet: string;
  is_final: boolean;
}

export interface ToolCallEndEvent extends BaseEvent {
  event_type: 'tool_call_end';
  tool_name: string;
  agent_name: string;
  execution_time_seconds: number;
  success: boolean;
  error_message?: string;
}

export interface LeadGeneratedEvent extends BaseEvent {
  event_type: 'lead_generated';
  lead_id: string;
  lead_data: Record<string, unknown>; // This matches prospect CreateLeadDto
  source_url: string;
  agent_name: string;
}

export interface LeadEnrichmentStartEvent extends BaseEvent {
  event_type: 'lead_enrichment_start';
  lead_id: string;
  company_name: string;
}

export interface LeadEnrichmentEndEvent extends BaseEvent {
  event_type: 'lead_enrichment_end';
  lead_id: string;
  success: boolean;
  final_package?: Record<string, unknown>;
  error_message?: string;
}

export interface StatusUpdateEvent extends BaseEvent {
  event_type: 'status_update';
  status_message: string;
  agent_name?: string;
  progress_percentage?: number;
  lead_id?: string; // Added for lead-specific status updates
}

export interface PipelineErrorEvent extends BaseEvent {
  event_type: 'pipeline_error';
  error_message: string;
  error_type: string;
  agent_name?: string;
  tool_name?: string;
  lead_id?: string;
}

// ===================================
// Union Type for All Prospect Events
// ===================================

export type ProspectPipelineEvent = 
  | PipelineStartEvent
  | PipelineEndEvent
  | AgentStartEvent
  | AgentEndEvent
  | ToolCallStartEvent
  | ToolCallOutputEvent
  | ToolCallEndEvent
  | LeadGeneratedEvent
  | LeadEnrichmentStartEvent
  | LeadEnrichmentEndEvent
  | StatusUpdateEvent
  | PipelineErrorEvent;

// ===================================
// WebSocket Events (from backend DTOs)
// ===================================

export interface QuotaUpdateEvent {
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

export interface JobProgressEvent {
  jobId: string;
  userId: string;
  status: string;
  progress: number;
  currentStep?: string;
  searchQuery?: string;
  timestamp: string;
}

export interface JobCompletedEvent {
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

export interface JobFailedEvent {
  jobId: string;
  userId: string;
  status: 'failed';
  error: string;
  searchQuery?: string;
  startedAt: string;
  failedAt: string;
  timestamp: string;
}

// ===================================
// Lead WebSocket Events (aligned with backend)
// ===================================

// Import LeadData type from unified types for perfect alignment
import type { LeadData } from '../types/unified';

export interface LeadCreatedEvent {
  lead: LeadData & { userId: string }; // Backend adds userId for WebSocket routing
}

export interface LeadEnrichedEvent {
  lead: LeadData & { userId: string }; // Backend adds userId for WebSocket routing
}

export interface LeadEnrichmentFailedEvent {
  leadId: string;
  error: string;
}

export interface LeadStageUpdateEvent {
  leadId: string;
  stage: string;
  updatedAt: string;
}

export interface LeadDeletedEvent {
  leadId: string;
}

// ===================================
// Agent and Metrics Events
// ===================================

export interface AgentStatusUpdateEvent {
  id: string;
  name: string;
  status: string;
  metrics?: Record<string, unknown>;
  last_updated: string;
  current_task?: string;
}

export interface MetricsUpdateEvent {
  totalLeads: number;
  completedLeads: number;
  averageProcessingTime: number;
  averageRoiPotential: number;
  successRate: number;
  activeAgents: number;
  lastUpdated: string;
}

// ===================================
// Enrichment Progress Events (special handling)
// ===================================

export interface EnrichmentProgressEvent {
  event_type: 'enrichment_progress';
  job_id: string;
  lead_id: string;
  current_agent: string;
  status_message: string;
  progress_percentage: number;
  timestamp: string;
}

export interface JobStatusUpdateEvent {
  event_type: 'job_status_update';
  job_id: string;
  status_message: string;
  timestamp: string;
}

// ===================================
// Union Types for Event Handling
// ===================================

export type WebSocketEvent = 
  | ProspectPipelineEvent
  | QuotaUpdateEvent
  | JobProgressEvent
  | JobCompletedEvent
  | JobFailedEvent
  | LeadCreatedEvent
  | LeadEnrichedEvent
  | LeadEnrichmentFailedEvent
  | LeadStageUpdateEvent
  | LeadDeletedEvent
  | AgentStatusUpdateEvent
  | MetricsUpdateEvent
  | EnrichmentProgressEvent
  | JobStatusUpdateEvent;

// ===================================
// Event Type Guards
// ===================================

// Helper type for type guards
type EventObject = Record<string, unknown>;

const isEventObject = (event: unknown): event is EventObject => {
  return event !== null && typeof event === 'object';
};

export const isProspectPipelineEvent = (event: unknown): event is ProspectPipelineEvent => {
  if (!isEventObject(event)) return false;
  return typeof event.event_type === 'string' && 
         typeof event.job_id === 'string' && 
         typeof event.user_id === 'string' &&
         typeof event.timestamp === 'string';
};

export const isLeadGeneratedEvent = (event: unknown): event is LeadGeneratedEvent => {
  return isEventObject(event) && event.event_type === 'lead_generated';
};

export const isLeadEnrichmentStartEvent = (event: unknown): event is LeadEnrichmentStartEvent => {
  return isEventObject(event) && event.event_type === 'lead_enrichment_start';
};

export const isLeadEnrichmentEndEvent = (event: unknown): event is LeadEnrichmentEndEvent => {
  return isEventObject(event) && event.event_type === 'lead_enrichment_end';
};

export const isPipelineEndEvent = (event: unknown): event is PipelineEndEvent => {
  return isEventObject(event) && event.event_type === 'pipeline_end';
};

export const isStatusUpdateEvent = (event: unknown): event is StatusUpdateEvent => {
  return isEventObject(event) && event.event_type === 'status_update';
};

export const isPipelineErrorEvent = (event: unknown): event is PipelineErrorEvent => {
  return isEventObject(event) && event.event_type === 'pipeline_error';
};

export const isQuotaUpdateEvent = (event: unknown): event is QuotaUpdateEvent => {
  return isEventObject(event) && 
         typeof event.userId === 'string' && 
         typeof event.quotaUsed === 'number';
};

export const isJobCompletedEvent = (event: unknown): event is JobCompletedEvent => {
  return isEventObject(event) && 
         event.status === 'completed' && 
         typeof event.leadsGenerated === 'number';
};

export const isJobFailedEvent = (event: unknown): event is JobFailedEvent => {
  return isEventObject(event) && 
         event.status === 'failed' && 
         typeof event.error === 'string';
};

// ===================================
// Event Name Constants (for subscription)
// ===================================

export const WebSocketEventNames = {
  // Prospect pipeline events
  PIPELINE_START: 'pipeline_start',
  PIPELINE_END: 'pipeline_end',
  AGENT_START: 'agent_start',
  AGENT_END: 'agent_end',
  TOOL_CALL_START: 'tool_call_start',
  TOOL_CALL_OUTPUT: 'tool_call_output',
  TOOL_CALL_END: 'tool_call_end',
  LEAD_GENERATED: 'lead_generated',
  LEAD_ENRICHMENT_START: 'lead_enrichment_start',
  LEAD_ENRICHMENT_END: 'lead_enrichment_end',
  STATUS_UPDATE: 'status_update',
  PIPELINE_ERROR: 'pipeline_error',
  
  // WebSocket-specific events
  LEAD_CREATED: 'lead-created',
  LEAD_ENRICHED: 'lead-enriched',
  LEAD_ENRICHMENT_FAILED: 'lead_enrichment_failed',
  LEAD_STAGE_UPDATE: 'lead-stage-update',
  LEAD_DELETED: 'lead-deleted',
  AGENT_UPDATE: 'agent-update',
  METRICS_UPDATE: 'metrics-update',
  QUOTA_UPDATE: 'quota-update',
  JOB_PROGRESS: 'job-progress',
  JOB_COMPLETED: 'job-completed',
  JOB_FAILED: 'job-failed',
  ENRICHMENT_UPDATE: 'enrichment-update',
  
  // Special enrichment events
  ENRICHMENT_PROGRESS: 'enrichment_progress',
  JOB_STATUS_UPDATE: 'job_status_update',
  UNHANDLED_PIPELINE_EVENT: 'unhandled-pipeline-event',
} as const;

export type WebSocketEventName = typeof WebSocketEventNames[keyof typeof WebSocketEventNames];
