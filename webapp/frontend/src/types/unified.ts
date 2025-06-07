/**
 * Unified Type Definitions
 * 
 * This file contains unified type definitions that ensure consistency across:
 * - React Frontend (TypeScript)
 * - NestJS Backend (TypeScript)
 * - MCP Server (Python/Pydantic)
 * 
 * All types are aligned to match the database schema and API contracts.
 */

// ===================================
// Core Entity Types (Aligned with Database Schema)
// ===================================

export type ProcessingStage = 
  | 'lead_qualification'
  | 'analyzing_refining' 
  | 'possibly_qualified'
  | 'prospecting'
  | 'revisando'
  | 'primeiras_mensagens'
  | 'negociando'
  | 'desqualificado'
  | 'reuniao_agendada';

export type QualificationTier = 'High Potential' | 'Medium Potential' | 'Low Potential';

export type AgentName =
  // Initial Processing Agents
  | 'lead_intake_agent'
  | 'lead_analysis_agent'
  
  // Main Orchestrator
  | 'enhanced_lead_processor'
  
  // Specialized Sub-Agents (used by Enhanced Lead Processor)
  | 'tavily_enrichment_agent'
  | 'contact_extraction_agent'
  | 'pain_point_deepening_agent'
  | 'lead_qualification_agent'
  | 'competitor_identification_agent'
  | 'strategic_question_generation_agent'
  | 'buying_trigger_identification_agent'
  | 'tot_strategy_generation_agent'
  | 'tot_strategy_evaluation_agent'
  | 'tot_action_plan_synthesis_agent'
  | 'detailed_approach_plan_agent'
  | 'objection_handling_agent'
  | 'value_proposition_customization_agent'
  | 'b2b_personalized_message_agent'
  | 'internal_briefing_summary_agent'
  
  // Alternative/Modular Agents
  | 'approach_strategy_agent'
  | 'b2b_persona_creation_agent'
  | 'message_crafting_agent'
  | 'persona_creation_agent'
  | 'lead_analysis_generation_agent';

export type AgentStatusType = 'active' | 'inactive' | 'processing' | 'error' | 'completed';

export type UserRole = 'admin' | 'user';

// ===================================
// Agent Types
// ===================================

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
  status: AgentStatusType;
  metrics: AgentMetrics;
  last_updated: string;
  current_task?: string;
}

export type AgentCategory = 'initial_processing' | 'orchestrator' | 'specialized' | 'alternative';

export interface ExtendedAgentResponse extends AgentStatus {
  displayName: string;
  category: AgentCategory;
  description?: string;
}

// ===================================
// Lead Types (Aligned with Database Entity)
// ===================================

export interface LeadData {
  id: string;
  company_name: string;
  website: string;
  relevance_score: number;
  roi_potential_score: number;
  brazilian_market_fit: number;
  qualification_tier: QualificationTier;
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

// ===================================
// Business Context Types
// ===================================

export interface BusinessContext {
  id?: string;
  business_description: string;
  product_service_description: string;
  target_market: string;
  value_proposition: string;
  ideal_customer?: string;
  pain_points: string[];
  competitive_advantage?: string;
  competitors?: string[];
  industry_focus: string[];
  geographic_focus?: string[];
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

// ===================================
// Chat Types
// ===================================

export interface ChatMessage {
  id: string;
  agent_id: string;
  content: string;
  timestamp: string;
  type: 'user' | 'agent';
  attachments?: string[];
}

// ===================================
// User/Authentication Types
// ===================================

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  created_at: string;
  updated_at: string;
  last_login?: string;
}

// ===================================
// MCP Server Types (Aligned with Python data_models.py)
// ===================================

export type LeadProcessingStatus = 'PENDING' | 'ACTIVE' | 'COMPLETED' | 'FAILED';
export type AgentExecutionStatus = 'SUCCESS' | 'FAILED';

export interface LeadProcessingState {
  lead_id: string;
  run_id: string;
  url?: string;
  status: LeadProcessingStatus;
  current_agent?: string;
  start_time: string;
  last_update_time: string;
  end_time?: string;
  error_message?: string;
  final_package_summary?: Record<string, unknown>;
}

export interface AgentExecutionRecord {
  record_id: number;
  lead_id: string;
  agent_name: string;
  status: AgentExecutionStatus;
  start_time: string;
  end_time?: string;
  processing_time_seconds?: number;
  input_summary?: string;
  output_json?: string;
  metrics_json?: string;
  error_message?: string;
}

export interface ProcessingProgress {
  lead_id: string;
  current_agent: string;
  progress_percentage: number;
  estimated_completion: string;
  current_step: string;
}

// ===================================
// API Request/Response Types
// ===================================

export interface ApiResponse<T = unknown> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
}

export interface ApiError {
  message: string;
  statusCode: number;
  error?: string;
  timestamp: string;
  path: string;
}

// ===================================
// DTO Types for API Operations
// ===================================

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
  competitive_advantage?: string;
  competitors?: string[];
  industry_focus: string[];
  geographic_focus?: string[];
}

export interface UpdateBusinessContextDto {
  business_description?: string;
  product_service_description?: string;
  target_market?: string;
  value_proposition?: string;
  ideal_customer?: string;
  pain_points?: string[];
  competitive_advantage?: string;
  competitors?: string[];
  industry_focus?: string[];
  geographic_focus?: string[];
}

// ===================================
// Authentication Types
// ===================================

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

export interface LoginResponse {
  access_token: string;
  user: User;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

// ===================================
// Agent Control Types
// ===================================

export interface StartAgentRequest {
  agentId: string;
}

export interface StopAgentRequest {
  agentId: string;
}

// ===================================
// Chat Types
// ===================================

export interface ChatMessageRequest {
  agent_id: string;
  content: string;
  attachments?: string[];
}

export interface ChatMessageResponse extends ChatMessage {
  id: string; // Ensuring ID is always present in responses
}

// ===================================
// Metrics Types
// ===================================

export interface DashboardMetrics {
  totalLeads: number;
  completedLeads: number;
  averageProcessingTime: number;
  averageRoiPotential: number;
  successRate: number;
  activeAgents: number;
  lastUpdated: string;
}

export interface PerformanceDataPoint {
  timestamp: string;
  throughput: number;
  processingTime: number;
}

export interface PerformanceMetrics {
  timeRange: string;
  throughputData: PerformanceDataPoint[];
  processingTimeData: PerformanceDataPoint[];
}

export interface AgentPerformanceData {
  agentId: string;
  agentName: string;
  successCount: number;
  errorCount: number;
  averageProcessingTime: number;
  throughput: number;
}

export interface LeadStatsData {
  stage: ProcessingStage;
  count: number;
  averageROI: number;
  highPotentialCount: number;
}

export interface MetricsSummary {
  overview: DashboardMetrics;
  performance: PerformanceMetrics;
  agentPerformance: AgentPerformanceData[];
  leadStats: LeadStatsData[];
}

export type MetricsPeriod = '24h' | '7d' | '30d' | '90d';

// ===================================
// Bulk Operations
// ===================================

export interface BulkLeadOperation {
  operation: 'create' | 'update' | 'delete' | 'process';
  leads: (CreateLeadDto | UpdateLeadDto)[];
}

// ===================================
// WebSocket Types (Real-time Updates)
// ===================================

export interface WebSocketMessage {
  type: 'agent_status_update' | 'lead_update' | 'metrics_update' | 'processing_progress';
  data: AgentStatus | LeadData | DashboardMetrics | ProcessingProgress;
  timestamp: string;
}

export interface RealTimeUpdate {
  entity: 'agent' | 'lead' | 'metrics';
  action: 'create' | 'update' | 'delete' | 'process';
  data: AgentStatus | LeadData | DashboardMetrics;
  timestamp: string;
}

// ===================================
// Error Handling Types
// ===================================

export interface ValidationError {
  field: string;
  message: string;
  value?: string | number | boolean;
}

export interface BusinessError extends Error {
  code: string;
  details?: Record<string, unknown>;
}

// ===================================
// Type Guards and Utilities
// ===================================

export const isProcessingStage = (value: string): value is ProcessingStage => {
  return [
    'lead_qualification',
    'analyzing_refining', 
    'possibly_qualified',
    'prospecting',
    'revisando',
    'primeiras_mensagens',
    'negociando',
    'desqualificado',
    'reuniao_agendada'
  ].includes(value as ProcessingStage);
};

export const isQualificationTier = (value: string): value is QualificationTier => {
  return ['High Potential', 'Medium Potential', 'Low Potential'].includes(value as QualificationTier);
};

export const isAgentName = (value: string): value is AgentName => {
  return ['lead_intake', 'analysis', 'persona_creation', 'approach_strategy', 'message_crafting'].includes(value as AgentName);
};

export const isUserRole = (value: string): value is UserRole => {
  return ['admin', 'user'].includes(value as UserRole);
};

// ===================================
// Constants
// ===================================

export const PROCESSING_STAGES: ProcessingStage[] = [
  'lead_qualification',
  'analyzing_refining', 
  'possibly_qualified',
  'prospecting',
  'revisando',
  'primeiras_mensagens',
  'negociando',
  'desqualificado',
  'reuniao_agendada'
];

export const QUALIFICATION_TIERS: QualificationTier[] = [
  'High Potential',
  'Medium Potential', 
  'Low Potential'
];

export const AGENT_NAMES: AgentName[] = [
  // Initial Processing Agents
  'lead_intake_agent',
  'lead_analysis_agent',
  
  // Main Orchestrator
  'enhanced_lead_processor',
  
  // Specialized Sub-Agents (used by Enhanced Lead Processor)
  'tavily_enrichment_agent',
  'contact_extraction_agent',
  'pain_point_deepening_agent',
  'lead_qualification_agent',
  'competitor_identification_agent',
  'strategic_question_generation_agent',
  'buying_trigger_identification_agent',
  'tot_strategy_generation_agent',
  'tot_strategy_evaluation_agent',
  'tot_action_plan_synthesis_agent',
  'detailed_approach_plan_agent',
  'objection_handling_agent',
  'value_proposition_customization_agent',
  'b2b_personalized_message_agent',
  'internal_briefing_summary_agent',
  
  // Alternative/Modular Agents
  'approach_strategy_agent',
  'b2b_persona_creation_agent',
  'message_crafting_agent',
  'persona_creation_agent',
  'lead_analysis_generation_agent'
];

export const USER_ROLES: UserRole[] = ['admin', 'user'];

// ===================================
// Stage Display Names and Colors
// ===================================

export const AGENT_DISPLAY_NAMES: Record<AgentName, string> = {
  // Initial Processing Agents
  'lead_intake_agent': 'Lead Intake Agent',
  'lead_analysis_agent': 'Lead Analysis Agent',
  
  // Main Orchestrator
  'enhanced_lead_processor': 'Enhanced Lead Processor',
  
  // Specialized Sub-Agents
  'tavily_enrichment_agent': 'Web Research Agent',
  'contact_extraction_agent': 'Contact Extraction Agent',
  'pain_point_deepening_agent': 'Pain Point Analysis Agent',
  'lead_qualification_agent': 'Lead Qualification Agent',
  'competitor_identification_agent': 'Competitor Analysis Agent',
  'strategic_question_generation_agent': 'Strategic Questions Agent',
  'buying_trigger_identification_agent': 'Buying Triggers Agent',
  'tot_strategy_generation_agent': 'Strategy Generation Agent',
  'tot_strategy_evaluation_agent': 'Strategy Evaluation Agent',
  'tot_action_plan_synthesis_agent': 'Action Plan Synthesis Agent',
  'detailed_approach_plan_agent': 'Approach Planning Agent',
  'objection_handling_agent': 'Objection Handling Agent',
  'value_proposition_customization_agent': 'Value Proposition Agent',
  'b2b_personalized_message_agent': 'Message Personalization Agent',
  'internal_briefing_summary_agent': 'Internal Briefing Agent',
  
  // Alternative/Modular Agents
  'approach_strategy_agent': 'Approach Strategy Agent',
  'b2b_persona_creation_agent': 'B2B Persona Agent',
  'message_crafting_agent': 'Message Crafting Agent',
  'persona_creation_agent': 'Persona Creation Agent',
  'lead_analysis_generation_agent': 'Analysis Generation Agent'
};

export const STAGE_DISPLAY_NAMES: Record<ProcessingStage, string> = {
  'lead_qualification': 'Lead Qualification',
  'analyzing_refining': 'Analyzing & Refining',
  'possibly_qualified': 'Possibly Qualified',
  'prospecting': 'Prospecting',
  'revisando': 'Under Review',
  'primeiras_mensagens': 'First Messages',
  'negociando': 'Negotiating',
  'desqualificado': 'Disqualified',
  'reuniao_agendada': 'Meeting Scheduled'
};

export const STAGE_COLORS: Record<ProcessingStage, string> = {
  'lead_qualification': '#6366f1',
  'analyzing_refining': '#8b5cf6',
  'possibly_qualified': '#06b6d4',
  'prospecting': '#10b981',
  'revisando': '#f59e0b',
  'primeiras_mensagens': '#3b82f6',
  'negociando': '#8b5cf6',
  'desqualificado': '#ef4444',
  'reuniao_agendada': '#22c55e'
};