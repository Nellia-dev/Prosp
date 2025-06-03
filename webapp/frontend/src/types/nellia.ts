
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
  name: string;
  status: 'active' | 'inactive' | 'processing' | 'error' | 'completed';
  metrics: AgentMetrics;
  last_updated: string;
  current_task?: string;
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
  processing_stage: 'lead_qualification' | 'analyzing_refining' | 'possibly_qualified' | 'prospecting' | 'revisando' | 'primeiras_mensagens' | 'negociando' | 'desqualificado' | 'reuniao_agendada';
  created_at: string;
  updated_at: string;
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
