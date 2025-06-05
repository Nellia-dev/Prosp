import { IsString, IsObject, IsEnum, IsDateString, IsOptional } from 'class-validator';

export enum WebSocketMessageType {
  AGENT_STATUS_UPDATE = 'agent_status_update',
  LEAD_UPDATE = 'lead_update',
  METRICS_UPDATE = 'metrics_update',
  PROCESSING_PROGRESS = 'processing_progress',
}

export enum RealTimeAction {
  CREATE = 'create',
  UPDATE = 'update',
  DELETE = 'delete',
  PROCESS = 'process',
}

export enum RealTimeEntity {
  AGENT = 'agent',
  LEAD = 'lead',
  METRICS = 'metrics',
}

export class WebSocketMessage {
  @IsEnum(WebSocketMessageType)
  type: WebSocketMessageType;

  @IsObject()
  data: any;

  @IsDateString()
  timestamp: string;
}

export class RealTimeUpdate {
  @IsEnum(RealTimeEntity)
  entity: RealTimeEntity;

  @IsEnum(RealTimeAction)
  action: RealTimeAction;

  @IsObject()
  data: any;

  @IsDateString()
  timestamp: string;

  @IsString()
  @IsOptional()
  userId?: string;
}

export class ConnectionStats {
  @IsString()
  totalConnections: number;

  @IsString({ each: true })
  clientIds: string[];

  @IsDateString()
  timestamp: string;
}

export class ProcessingProgressData {
  @IsString()
  lead_id: string;

  @IsString()
  current_agent: string;

  @IsString()
  progress_percentage: number;

  @IsDateString()
  estimated_completion: string;

  @IsString()
  current_step: string;
}

export class AgentStatusUpdateData {
  @IsString()
  id: string;

  @IsString()
  name: string;

  @IsString()
  status: string;

  @IsObject()
  @IsOptional()
  metrics?: any;

  @IsDateString()
  last_updated: string;

  @IsString()
  @IsOptional()
  current_task?: string;
}

export class LeadUpdateData {
  @IsString()
  id: string;

  @IsString()
  company_name: string;

  @IsString()
  @IsOptional()
  website?: string;

  @IsString()
  processing_stage: string;

  @IsString()
  qualification_tier: string;

  @IsString()
  relevance_score: number;

  @IsString()
  roi_potential_score: number;

  @IsDateString()
  updated_at: string;
}

export class MetricsUpdateData {
  @IsString()
  totalLeads: number;

  @IsString()
  completedLeads: number;

  @IsString()
  averageProcessingTime: number;

  @IsString()
  averageRoiPotential: number;

  @IsString()
  successRate: number;

  @IsString()
  activeAgents: number;

  @IsDateString()
  lastUpdated: string;
}

// Client-to-server message types
export class PingMessage {
  @IsString()
  type: 'ping';

  @IsDateString()
  @IsOptional()
  timestamp?: string;
}

export class SubscribeToUpdatesMessage {
  @IsString()
  type: 'subscribe';

  @IsEnum(RealTimeEntity, { each: true })
  entities: RealTimeEntity[];

  @IsString()
  @IsOptional()
  userId?: string;
}

export class UnsubscribeFromUpdatesMessage {
  @IsString()
  type: 'unsubscribe';

  @IsEnum(RealTimeEntity, { each: true })
  entities: RealTimeEntity[];
}