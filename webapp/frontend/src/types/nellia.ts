
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

// Copied from unified.ts for alignment
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

// Copied from unified.ts for alignment
export type AgentCategory = 'initial_processing' | 'orchestrator' | 'specialized' | 'alternative';

export type AgentStatusType = 'active' | 'inactive' | 'processing' | 'error' | 'completed';

export interface AgentStatus {
  id: string;
  name: AgentName; // Use unified AgentName
  displayName: string; // Display name for the agent
  status: AgentStatusType;
  metrics: AgentMetrics;
  last_updated: string;
  current_task?: string;
  description?: string;
  category: AgentCategory; // Use unified AgentCategory
}

export interface DashboardMetricsData {
  totalLeads: number;
  completedLeads: number;
  averageProcessingTime: number;
  averageRoiPotential: number;
  successRate: number;
  agentMetrics: AgentStatus[]; // Assuming agentMetrics will be an array of AgentStatus
  lastUpdated: string;
}

export interface LeadData {
  id: string;
  company_name: string;
  website: string;
  relevance_score: number;
  roi_potential_score: number;
  qualification_tier: 'High Potential' | 'Medium Potential' | 'Low Potential';
  company_sector: string;
  persona?: {
    likely_role: string;
    decision_maker_probability: number;
  };
  pain_point_analysis?: string[];
  purchase_triggers?: string[];
  processing_stage: 'lead_qualification' | 'analyzing_refining' | 'possibly_qualified' | 'prospecting' | 'revisando' | 'primeiras_mensagens' | 'negociando' | 'desqualificado' | 'reuniao_agendada';
  created_at: string;
  updated_at: string;
  status: string;
  enrichment_data?: unknown;
}

export interface BusinessContext {
  business_description: string;
  target_market: string;
  value_proposition: string;
  ideal_customer: string;
  pain_points: string[];
  competitive_advantage: string;
  industry_focus: string[];
  geographic_focus: string[];
}

export interface ChatMessage {
  id: string;
  agent_id: string;
  content: string;
  timestamp: string;
  type: 'user' | 'agent';
  attachments?: File[];
}

export interface ProcessingProgress {
  lead_id: string;
  current_agent: string;
  progress_percentage: number;
  estimated_completion: string;
  current_step: string;
}

// Added from backend/src/shared/types/nellia.types.ts for alignment with API response
export interface RecentActivityItem {
  id: string;
  type: 'lead_created' | 'agent_status_change' | 'prospect_job_started' | 'prospect_job_completed';
  description: string;
  timestamp: string;
  metadata?: Record<string, unknown>; // Changed any to unknown
}

export interface DashboardMetricsResponse {
  totalLeads: number;
  totalAgents: number;
  activeAgents: number;
  processingRate: number;
  successRate: number;
  recentActivity: RecentActivityItem[];
  lastUpdated: string; // Frontend might prefer string, backend sends Date
}
