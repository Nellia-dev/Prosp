import { AgentCategory, AgentName, ProcessingStage, QualificationTier } from '../enums/nellia.enums';

export interface AgentMetrics {
  processing_time_seconds: number;
  llm_usage: {
    total_tokens: number;
    prompt_tokens: number;
    completion_tokens: number;
  };
  success_rate: number;
  queue_depth: number;
  throughput_per_hour: number;
}

export interface AgentStatus {
  id: string;
  name: AgentName;
  status: 'active' | 'inactive' | 'processing' | 'error' | 'completed';
  metrics: AgentMetrics;
  last_updated: string;
  current_task?: string;
  description?: string;
  category?: AgentCategory;
}

export interface LeadData {
  id: string;
  company_name: string;
  website: string;
  relevance_score: number;
  roi_potential_score: number;
  brazilian_market_fit: number;
  qualification_tier: 'High Potential' | 'Medium Potential' | 'Low Potential';
  company_sector: string;
  persona?: {
    likely_role: string;
    decision_maker_probability: number;
  };
  pain_point_analysis?: string[];
  purchase_triggers?: string[];
  processing_stage: ProcessingStage;
  created_at: string;
  updated_at: string;
}

export interface BusinessContext {
  id?: string;
  business_description: string;
  target_market: string;
  value_proposition: string;
  ideal_customer?: string;
  pain_points: string[];
  industry_focus: string[];
  created_at?: string;
  updated_at?: string;
}

export interface ChatMessage {
  id: string;
  agent_id: string;
  content: string;
  timestamp: string;
  type: 'user' | 'agent';
  attachments?: string[]; // File paths for backend
}

export interface ProcessingProgress {
  lead_id: string;
  current_agent: string;
  progress_percentage: number;
  estimated_completion: string;
  current_step: string;
}

// Re-export types from enums for consistency
export { AgentName, AgentCategory, ProcessingStage, QualificationTier } from '../enums/nellia.enums';



export interface McpRequest {
  method: string;
  params?: any;
  id?: string;
}

export interface McpResponse {
  result?: any;
  error?: {
    code: number;
    message: string;
    data?: any;
  };
  id?: string;
}

// DTO Types for API operations
export interface CreateLeadDto {
  company_name: string;
  website?: string;
  company_sector?: string;
  description?: string;
  contact_email?: string;
  contact_phone?: string;
  contact_role?: string;
  market_region?: string;
  company_size?: string;
  annual_revenue?: number;
  userId?: string; // Associated user for multi-tenant support
}

export interface UpdateLeadDto {
  company_name?: string;
  website?: string;
  company_sector?: string;
  description?: string;
  contact_email?: string;
  contact_phone?: string;
  contact_role?: string;
  market_region?: string;
  company_size?: string;
  annual_revenue?: number;
  relevance_score?: number;
  roi_potential_score?: number;
  brazilian_market_fit?: number;
  qualification_tier?: QualificationTier;
  processing_stage?: ProcessingStage;
  persona_analysis?: string;
  pain_point_analysis?: string[];
  purchase_triggers?: string[];
  decision_maker_probability?: number;
}

export interface LeadFilters {
  search?: string;
  company_sector?: string;
  qualification_tier?: QualificationTier;
  processing_stage?: ProcessingStage;
  score_range?: {
    min: number;
    max: number;
  };
  sort_by?: 'company_name' | 'relevance_score' | 'roi_potential_score' | 'brazilian_market_fit' | 'created_at';
  sort_order?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
}

export interface CreateBusinessContextDto {
  business_description: string;
  target_market: string;
  value_proposition: string;
  ideal_customer?: string;
  pain_points: string[];
  industry_focus: string[];
}

export interface UpdateBusinessContextDto {
  business_description?: string;
  target_market?: string;
  value_proposition?: string;
  ideal_customer?: string;
  pain_points?: string[];
  industry_focus?: string[];
}

// Metrics-related types
export interface DashboardMetrics {
  totalLeads: number;
  completedLeads: number;
  averageProcessingTime: number;
  averageRoiPotential: number;
  successRate: number;
  agentMetrics: AgentMetrics[];
  lastUpdated: Date;
}

export interface AgentPerformanceData {
  agentName: string;
  success: number;
  errors: number;
  avgProcessingTime: number;
}

export interface PerformanceDataPoint {
  date: string;
  throughput: number;
  processingTime: number;
}

export type MetricsPeriod = '24h' | '7d' | '30d' | '90d';

// As per FRONTEND_EMPTY_STATE_FIX_PLAN.md for Metrics
export interface RecentActivityItem {
  id: string;
  type: 'lead_created' | 'agent_status_change' | 'prospect_job_started' | 'prospect_job_completed';
  description: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

export interface DashboardMetricsResponse {
  totalLeads: number;
  totalAgents: number;
  activeAgents: number;
  processingRate: number; // Placeholder, to be defined more clearly
  successRate: number;
  recentActivity: RecentActivityItem[];
  lastUpdated: Date; // Keeping this as it's generally useful
}

// Generic paginated response for API list endpoints
export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
}
