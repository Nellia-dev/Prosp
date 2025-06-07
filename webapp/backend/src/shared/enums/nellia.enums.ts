export enum AgentName {
    LEAD_INTAKE_AGENT = 'lead_intake_agent',
    LEAD_ANALYSIS_AGENT = 'lead_analysis_agent',
    ENHANCED_LEAD_PROCESSOR = 'enhanced_lead_processor',
    TAVILY_ENRICHMENT_AGENT = 'tavily_enrichment_agent',
    CONTACT_EXTRACTION_AGENT = 'contact_extraction_agent',
    PAIN_POINT_DEEPENING_AGENT = 'pain_point_deepening_agent',
    LEAD_QUALIFICATION_AGENT = 'lead_qualification_agent',
    COMPETITOR_IDENTIFICATION_AGENT = 'competitor_identification_agent',
    STRATEGIC_QUESTION_GENERATION_AGENT = 'strategic_question_generation_agent',
    BUYING_TRIGGER_IDENTIFICATION_AGENT = 'buying_trigger_identification_agent',
    TOT_STRATEGY_GENERATION_AGENT = 'tot_strategy_generation_agent',
    TOT_STRATEGY_EVALUATION_AGENT = 'tot_strategy_evaluation_agent',
    TOT_ACTION_PLAN_SYNTHESIS_AGENT = 'tot_action_plan_synthesis_agent',
    DETAILED_APPROACH_PLAN_AGENT = 'detailed_approach_plan_agent',
    OBJECTION_HANDLING_AGENT = 'objection_handling_agent',
    VALUE_PROPOSITION_CUSTOMIZATION_AGENT = 'value_proposition_customization_agent',
    B2B_PERSONALIZED_MESSAGE_AGENT = 'b2b_personalized_message_agent',
    INTERNAL_BRIEFING_SUMMARY_AGENT = 'internal_briefing_summary_agent',
    APPROACH_STRATEGY_AGENT = 'approach_strategy_agent',
    B2B_PERSONA_CREATION_AGENT = 'b2b_persona_creation_agent',
    MESSAGE_CRAFTING_AGENT = 'message_crafting_agent',
    PERSONA_CREATION_AGENT = 'persona_creation_agent',
    LEAD_ANALYSIS_GENERATION_AGENT = 'lead_analysis_generation_agent',
}

export enum AgentStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  PROCESSING = 'processing',
  ERROR = 'error',
  COMPLETED = 'completed',
}

export enum AgentCategory {
    INITIAL_PROCESSING = 'initial_processing',
    ORCHESTRATOR = 'orchestrator',
    SPECIALIZED = 'specialized',
    ALTERNATIVE = 'alternative',
}
export enum QualificationTier {
  HIGH_POTENTIAL = 'High Potential',
  MEDIUM_POTENTIAL = 'Medium Potential',
  LOW_POTENTIAL = 'Low Potential',
}

export enum ProcessingStage {
    LEAD_QUALIFICATION = 'lead_qualification',
    ANALYZING_REFINING = 'analyzing_refining',
    POSSIBLY_QUALIFIED = 'possibly_qualified',
    PROSPECTING = 'prospecting',
    REVISANDO = 'revisando',
    PRIMEIRAS_MENSAGENS = 'primeiras_mensagens',
    NEGOCIANDO = 'negociando',
    DESQUALIFICADO = 'desqualificado',
    REUNIAO_AGENDADA = 'reuniao_agendada',
    // Additional stages that may be used
    INTAKE = 'intake',
    ANALYSIS = 'analysis',
    PERSONA = 'persona',
    STRATEGY = 'strategy',
    MESSAGE = 'message',
    COMPLETED = 'completed'
}

export enum LeadStatus {
  NEW = 'new',
  HARVESTED = 'harvested',
  PENDING_ENRICHMENT = 'pending_enrichment',
  ENRICHING = 'enriching',
  ENRICHED = 'enriched',
  ENRICHMENT_FAILED = 'enrichment_failed',
}
