"""
Data models for the Nellia Prospector lead processing pipeline.
These models ensure type safety and data validation throughout the system.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl, validator
import uuid


class ExtractionStatus(str, Enum):
    """Status of website content extraction"""
    SUCCESS = "SUCESSO NA EXTRAÇÃO"
    SUCCESS_VIA_IMAGE = "SUCESSO NA EXTRAÇÃO (VIA ANÁLISE DE IMAGEM)"
    FAILED_TIMEOUT = "FALHA NA EXTRAÇÃO: TIMEOUT NA NAVEGAÇÃO"
    FAILED_STATUS = "FALHA NA EXTRAÇÃO: Página retornou status"
    FAILED_OTHER = "FALHA NA EXTRAÇÃO"


class GoogleSearchData(BaseModel):
    """Google search result data for a lead"""
    title: str = Field(..., description="Page title from Google search")
    snippet: str = Field(..., description="Page snippet from Google search")


class SiteData(BaseModel):
    """Individual lead data from harvester"""
    url: HttpUrl = Field(..., description="Website URL")
    google_search_data: Optional[GoogleSearchData] = Field(None, description="Google search data")
    extracted_text_content: Optional[str] = Field(None, description="Extracted text content from the website") # Made Optional
    extraction_status_message: str = Field(..., description="Status message of extraction")
    screenshot_filepath: Optional[str] = Field(None, description="Path to screenshot if available")
    
    @validator('url', pre=True)
    def validate_url(cls, v):
        if isinstance(v, str) and not v.startswith(('http://', 'https://')):
            return f'https://{v}'
        return v


class HarvesterOutput(BaseModel):
    """Complete output from the harvester service"""
    original_query: str = Field(..., description="Original search query")
    collection_timestamp: datetime = Field(..., description="When the data was collected")
    total_sites_targeted_for_processing: int = Field(..., description="Total sites targeted")
    total_sites_processed_in_extraction_phase: int = Field(..., description="Sites actually processed")
    sites_data: List[SiteData] = Field(..., description="List of processed site data")


class ValidatedLead(BaseModel):
    """Validated lead after intake processing"""
    site_data: SiteData = Field(..., description="Original site data")
    validation_timestamp: datetime = Field(default_factory=datetime.now)
    is_valid: bool = Field(..., description="Whether the lead passed validation")
    validation_errors: List[str] = Field(default_factory=list, description="List of validation errors")
    cleaned_text_content: Optional[str] = Field(None, description="Cleaned and normalized text content")
    extraction_successful: bool = Field(..., description="Whether extraction was successful")


class LeadAnalysis(BaseModel):
    """Analysis results for a lead"""
    company_sector: str = Field(..., description="Industry sector of the company")
    main_services: List[str] = Field(..., description="Main services/products offered")
    recent_activities: List[str] = Field(default_factory=list, description="Recent news or activities")
    potential_challenges: List[str] = Field(..., description="Identified challenges or pain points")
    company_size_estimate: Optional[str] = Field(None, description="Estimated company size")
    company_culture_values: Optional[str] = Field(None, description="Identified culture and values")
    relevance_score: float = Field(..., ge=0, le=1, description="Relevance score (0-1)")
    general_diagnosis: str = Field(..., description="General assessment of the company")
    opportunity_fit: str = Field(..., description="How our product/service could fit")


class AnalyzedLead(BaseModel):
    """Lead with complete analysis"""
    validated_lead: ValidatedLead = Field(..., description="Validated lead data")
    analysis: LeadAnalysis = Field(..., description="Lead analysis results")
    analysis_timestamp: datetime = Field(default_factory=datetime.now)
    product_service_context: str = Field(..., description="Product/service being offered")
    ai_intelligence: Optional[Dict[str, Any]] = Field(None, description="AI prospect intelligence profile from RAG")


class PersonaDetails(BaseModel):
    """Detailed persona information for a decision maker"""
    fictional_name: str = Field(..., description="Fictional name for the persona")
    likely_role: str = Field(..., description="Likely job title/role")
    key_responsibilities: List[str] = Field(..., description="Main professional responsibilities")
    professional_goals: List[str] = Field(..., description="Professional goals and objectives")
    main_challenges: List[str] = Field(..., description="Primary challenges faced")
    motivations: List[str] = Field(..., description="What motivates this persona")
    solution_seeking: str = Field(..., description="What they look for in solutions")
    communication_style: str = Field(..., description="Preferred communication style")
    decision_making_process: Optional[str] = Field(None, description="How they make decisions")


class LeadWithPersona(BaseModel):
    """Lead with persona information"""
    analyzed_lead: AnalyzedLead = Field(..., description="Analyzed lead data")
    persona: PersonaDetails = Field(..., description="Decision maker persona")
    persona_creation_timestamp: datetime = Field(default_factory=datetime.now)


class CommunicationChannel(str, Enum):
    """Preferred communication channels"""
    EMAIL = "email"
    LINKEDIN = "linkedin"
    WHATSAPP = "whatsapp"
    PHONE = "phone"


class ApproachStrategy(BaseModel):
    """Strategic approach plan for the lead"""
    primary_channel: CommunicationChannel = Field(..., description="Recommended primary channel")
    secondary_channel: Optional[CommunicationChannel] = Field(None, description="Backup channel")
    tone_of_voice: str = Field(..., description="Recommended tone and style")
    key_value_propositions: List[str] = Field(..., description="Main value props to highlight")
    talking_points: List[str] = Field(..., description="Key talking points")
    potential_objections: Dict[str, str] = Field(..., description="Objections and responses")
    opening_questions: List[str] = Field(..., description="Questions to spark interest")
    first_interaction_goal: str = Field(..., description="Goal for initial contact")
    follow_up_strategy: Optional[str] = Field(None, description="Follow-up approach if needed")


class LeadWithStrategy(BaseModel):
    """Lead with complete approach strategy"""
    lead_with_persona: LeadWithPersona = Field(..., description="Lead with persona data")
    strategy: ApproachStrategy = Field(..., description="Approach strategy")
    strategy_timestamp: datetime = Field(default_factory=datetime.now)


class PersonalizedMessage(BaseModel):
    """Personalized outreach message"""
    channel: CommunicationChannel = Field(..., description="Communication channel")
    subject_line: Optional[str] = Field(None, description="Subject line (for email)")
    message_body: str = Field(..., description="Main message content")
    call_to_action: str = Field(..., description="Clear CTA")
    personalization_elements: List[str] = Field(..., description="Personalized elements used")
    estimated_read_time: Optional[int] = Field(None, description="Estimated read time in seconds")
    ab_variant: Optional[str] = Field(None, description="A/B test variant identifier")


class FinalProspectPackage(BaseModel):
    """Complete processed lead package"""
    lead_with_strategy: LeadWithStrategy = Field(..., description="Lead with full strategy")
    personalized_message: PersonalizedMessage = Field(..., description="Ready-to-send message")
    processing_complete_timestamp: datetime = Field(default_factory=datetime.now)
    total_processing_time_seconds: Optional[float] = Field(None, description="Total processing time")
    
    # Metadata
    lead_id: Optional[str] = Field(None, description="Unique identifier for the lead")
    processing_version: str = Field(default="1.0", description="Version of processing pipeline")
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="Overall confidence in the output")
    
    def to_export_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary suitable for export"""
        return {
            "lead_url": str(self.lead_with_strategy.lead_with_persona.analyzed_lead.validated_lead.site_data.url),
            "company_name": self.lead_with_strategy.lead_with_persona.analyzed_lead.validated_lead.site_data.google_search_data.title if self.lead_with_strategy.lead_with_persona.analyzed_lead.validated_lead.site_data.google_search_data else "Unknown",
            "relevance_score": self.lead_with_strategy.lead_with_persona.analyzed_lead.analysis.relevance_score,
            "persona_role": self.lead_with_strategy.lead_with_persona.persona.likely_role,
            "recommended_channel": self.personalized_message.channel.value,
            "message_subject": self.personalized_message.subject_line,
            "message_preview": self.personalized_message.message_body[:200] + "...",
            "processing_timestamp": self.processing_complete_timestamp.isoformat(),
            "confidence_score": self.confidence_score
        }


# Google A2A Protocol Message Models (for future distributed agent implementation)
# These models would be used if implementing Google's Agent2Agent Protocol
# for distributed agent communication (https://github.com/google-a2a/A2A)
class A2AAgentMessage(BaseModel):
    """Base class for messages that would be sent between agents using Google's A2A Protocol"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_agent: str = Field(..., description="ID of the agent sending the message")
    target_agent: str = Field(..., description="ID of the agent receiving the message")
    protocol_version: str = Field(default="1.0", description="A2A protocol version")


class ProspectDataMessage(A2AAgentMessage):
    """Message containing validated lead data for A2A communication"""
    validated_lead: ValidatedLead


class AnalyzedProspectMessage(A2AAgentMessage):
    """Message containing analyzed lead data for A2A communication"""
    analyzed_lead: AnalyzedLead


class QualifiedProspectMessage(A2AAgentMessage):
    """Message containing lead with persona for A2A communication"""
    lead_with_persona: LeadWithPersona


class PersonalizedOutreachMessage(A2AAgentMessage):
    """Message containing final prospect package for A2A communication"""
    final_prospect: FinalProspectPackage


# Enhanced Intelligence and Processing Models for Integration with new-cw.py capabilities

class ContactInformation(BaseModel):
    """Contact information extracted from lead analysis"""
    emails_found: List[str] = Field(default_factory=list, description="Email addresses found")
    instagram_profiles: List[str] = Field(default_factory=list, description="Instagram profile URLs")
    linkedin_profiles: List[str] = Field(default_factory=list, description="LinkedIn profile URLs")
    phone_numbers: List[str] = Field(default_factory=list, description="Phone numbers found")
    extraction_confidence: float = Field(default=0.0, ge=0, le=1, description="Confidence in extraction accuracy")
    tavily_search_suggestions: List[str] = Field(default_factory=list, description="Suggested searches for additional contact info")

class PainPointAnalysis(BaseModel):
    """Deep analysis of company pain points and challenges"""
    primary_pain_category: str = Field(default="Não especificado", description="Main category of pain point") # Added default
    detailed_pain_points: List['DetailedPainPointSchema'] = Field(default_factory=list) # Uses new schema
    business_impact_assessment: Optional[str] = Field(None, description="Overall assessment of business impact from agent's raw text") # Made optional
    urgency_level: str = Field(default="medium", description="Urgency level: low, medium, high, critical")
    investigative_questions: List[str] = Field(
        default_factory=list, 
        description="Strategic questions to deepen understanding"
    )
    # potential_solutions_alignment: Dict[str, str] = Field( # This is now part of DetailedPainPointSchema
    #     default_factory=dict,
    #     description="How offered solution aligns with each pain point"
    # )
    raw_text_report: Optional[str] = Field(None, description="Raw text output from the agent, if parsing is partial")
    error_message: Optional[str] = None

class CompetitorIntelligence(BaseModel):
    """Competitive intelligence and market analysis"""
    identified_competitors: List['CompetitorDetailSchema'] = Field(default_factory=list) # Uses new schema
    other_notes: Optional[str] = Field(None, description="Other general notes on competitive landscape")
    raw_text_report: Optional[str] = Field(None, description="Raw text output from the agent, if parsing is partial")
    error_message: Optional[str] = None
    # Old fields removed: mentioned_competitors, current_solutions, competitive_advantages, 
    # market_positioning, switching_barriers, competitive_threats

class PurchaseTriggers(BaseModel):
    """Purchase triggers and timing indicators"""
    identified_triggers: List['IdentifiedTriggerSchema'] = Field(default_factory=list) # Uses new schema
    other_observations: Optional[str] = Field(None, description="Other general observations on triggers")
    raw_text_report: Optional[str] = Field(None, description="Raw text output from the agent, if parsing is partial")
    error_message: Optional[str] = None
    # Old fields removed: recent_events, market_signals, timing_indicators, 
    # growth_signals, urgency_drivers, budget_cycle_insights

class LeadQualification(BaseModel):
    """Lead qualification scoring and assessment"""
    qualification_tier: str = Field(..., description="High Potential, Medium, Low, Not Qualified")
    qualification_score: float = Field(..., ge=0, le=1, description="Numerical qualification score")
    qualification_reasoning: List[str] = Field(
        default_factory=list, 
        description="Reasons for qualification score"
    )
    fit_score: float = Field(default=0.0, ge=0, le=1, description="Product-market fit score")
    readiness_score: float = Field(default=0.0, ge=0, le=1, description="Purchase readiness score")
    authority_score: float = Field(default=0.0, ge=0, le=1, description="Decision-making authority score")
    budget_likelihood: str = Field(default="unknown", description="Budget availability likelihood")
    error_message: Optional[str] = None # Added for consistency

# --- Schemas mapping to Agent Outputs ---

class DetailedPainPointSchema(BaseModel): 
    """Maps to PainPointDeepeningOutput.DetailedPainPoint"""
    pain_description: str
    business_impact: str
    solution_alignment: str

class CompetitorDetailSchema(BaseModel):
    """Maps to CompetitorIdentificationOutput.CompetitorDetail"""
    name: str
    description: Optional[str] = None
    perceived_strength: Optional[str] = None
    perceived_weakness: Optional[str] = None

class IdentifiedTriggerSchema(BaseModel):
    """Maps to BuyingTriggerIdentificationOutput.IdentifiedTrigger"""
    trigger_description: str
    relevance_explanation: str

class ToTStrategyOptionModel(BaseModel): 
    """Maps to ToTStrategyGenerationOutput.ToTStrategyOptionModel - Aligns with existing ToTStrategyOption but for direct agent output mapping"""
    strategy_name: str
    angle_or_hook: str
    tone_of_voice: str
    primary_channels: List[str]
    key_points_or_arguments: List[str]
    opening_question: str

class EvaluatedStrategyModel(BaseModel): 
    """Maps to ToTStrategyEvaluationOutput.EvaluatedStrategyModel"""
    strategy_name: str
    suitability_assessment: str
    strengths: List[str]
    weaknesses_or_risks: List[str]
    suggested_improvements: List[str]
    confidence_score: str 
    confidence_justification: str

class ActionPlanStepModel(BaseModel): 
    """Maps to ToTActionPlanSynthesisOutput.ActionPlanStepModel"""
    step_number: int
    channel: str
    action_description: str
    key_message_or_argument: str
    cta: Optional[str] = None

class ToTActionPlanSynthesisModel(BaseModel): 
    """Maps to ToTActionPlanSynthesisOutput"""
    recommended_strategy_name: str = "Estratégia Combinada/Refinada"
    primary_angle_hook: str = "Não especificado"
    tone_of_voice: str = "Consultivo"
    action_sequence: List[ActionPlanStepModel] = Field(default_factory=list)
    key_talking_points: List[str] = Field(default_factory=list)
    main_opening_question: str = "Não especificado"
    success_metrics: List[str] = Field(default_factory=list)
    contingency_plan: Optional[str] = None
    error_message: Optional[str] = None

class ContactStepDetailSchema(BaseModel): 
    """Maps to DetailedApproachPlanOutput.ContactStepDetail"""
    step_number: int
    channel: str
    objective: str
    key_topics_arguments: List[str]
    key_questions: List[str] = Field(default_factory=list)
    cta: str
    supporting_materials: Optional[str] = None

class DetailedApproachPlanModel(BaseModel): 
    """Maps to DetailedApproachPlanOutput"""
    main_objective: str = "Não especificado"
    adapted_elevator_pitch: str = "Não especificado"
    contact_sequence: List[ContactStepDetailSchema] = Field(default_factory=list)
    engagement_indicators_to_monitor: List[str] = Field(default_factory=list)
    potential_obstacles_attention_points: List[str] = Field(default_factory=list)
    suggested_next_steps_if_successful: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None

class ObjectionResponseModelSchema(BaseModel): 
    """Maps to ObjectionHandlingOutput.ObjectionResponseModel"""
    objection: str
    response_strategy: str
    suggested_response: str

# ValueProposition is redefined later, so CustomValuePropModelSchema is implicitly handled by that.

class InternalBriefingSectionSchema(BaseModel):
    """Maps to InternalBriefingSummaryOutput.InternalBriefingSection"""
    title: str
    content: str
# --- End of Agent Output Schemas ---

class ExternalIntelligence(BaseModel):
    """External intelligence gathered from Tavily and other sources"""
    tavily_enrichment: str = Field(default="", description="Enriched data from Tavily API")
    market_research: str = Field(default="", description="Additional market research")
    news_analysis: str = Field(default="", description="Recent news and developments")
    social_signals: List[str] = Field(default_factory=list, description="Social media signals")
    enrichment_confidence: float = Field(default=0.0, ge=0, le=1, description="Confidence in enriched data")
    sources_used: List[str] = Field(default_factory=list, description="Data sources utilized")
    error_message: Optional[str] = None # Added for consistency


# ToTStrategyOption is effectively replaced by ToTStrategyOptionModel for agent output mapping
# class ToTStrategyOption(BaseModel):
#     """Tree of Thought strategy option"""
#     strategy_name: str = Field(..., description="Name of the strategy")
#     strategy_rationale: str = Field(..., description="Reasoning behind the strategy")
#     primary_channel: str = Field(..., description="Recommended communication channel") # To be primary_channels: List[str]
#     key_hook: str = Field(..., description="Main conversation starter")
#     success_probability: str = Field(..., description="Estimated success probability")
#     pros: List[str] = Field(default_factory=list, description="Advantages of this strategy")
#     cons: List[str] = Field(default_factory=list, description="Disadvantages and risks")

# ToTStrategyEvaluation is replaced by the new ToT models in EnhancedStrategy
# class ToTStrategyEvaluation(BaseModel):
#     """Tree of Thought strategy evaluation and selection"""
#     strategy_options: List[ToTStrategyOptionModel] = Field(default_factory=list, description="Strategy options considered, now using new model")
#     selected_strategy: ToTStrategyOptionModel = Field(..., description="Selected optimal strategy, now using new model")
    evaluation_criteria: List[str] = Field(default_factory=list, description="Criteria used for evaluation")
    contingency_plan: Optional[str] = Field(None, description="Backup approach if primary fails")

class ObjectionFramework(BaseModel):
    """Framework for handling objections"""
    anticipated_objections: List[ObjectionResponseModelSchema] = Field(default_factory=list)
    raw_text_report: Optional[str] = Field(None, description="Raw text output from the agent, if parsing is partial")
    error_message: Optional[str] = None
    # common_objections: Dict[str, str] = Field(
    #     default_factory=dict, 
    #     description="Common objections and responses"
    # )
    # objection_categories: List[str] = Field(default_factory=list, description="Categories of objections")
    # response_templates: Dict[str, str] = Field(
    #     default_factory=dict, 
    #     description="Template responses for objection types"
    # )
    # escalation_strategies: List[str] = Field(
    #     default_factory=list, 
    #     description="Strategies when objections persist"
    # )


# --- Value Proposition Models ---
# class CustomValuePropModelSchema(BaseModel): # Maps to CustomValuePropModel from agent
#     title: str
#     connection_to_pain_or_trigger: str
#     key_benefit: str
#     differentiation_factor: str
#     call_to_value: str

class ValueProposition(BaseModel): # Redefined to match CustomValuePropModel from agent
    """Customized value proposition, aligned with ValuePropositionCustomizationOutput"""
    title: str = Field(..., description="Title of the value proposition")
    connection_to_pain_or_trigger: str = Field(..., description="How it connects to lead's context")
    key_benefit: str = Field(..., description="Main benefit for the lead")
    differentiation_factor: str = Field(..., description="Unique selling point for this context")
    call_to_value: str = Field(..., description="Impactful phrase or call to reflection/action")
    error_message: Optional[str] = None # If a specific VP failed to generate
    # proposition_text: str (old field)
    # target_pain_points: List[str] (old field)
    # quantified_benefits: List[str] (old field)
    # proof_points: List[str] (old field)
    # differentiation_factors: List[str] (old field, now a single string)


class EnhancedStrategy(BaseModel):
    """Enhanced strategy combining multiple intelligence sources"""
    external_intelligence: Optional[ExternalIntelligence] = None # Made optional
    contact_information: Optional[ContactInformation] = None # Made optional
    pain_point_analysis: Optional[PainPointAnalysis] = None # Made optional
    competitor_intelligence: Optional[CompetitorIntelligence] = None # Made optional
    purchase_triggers: Optional[PurchaseTriggers] = None # Made optional
    lead_qualification: Optional[LeadQualification] = None # Made optional
    
    # ToT strategy outputs
    tot_generated_strategies: Optional[List[ToTStrategyOptionModel]] = None
    tot_evaluated_strategies: Optional[List[EvaluatedStrategyModel]] = None
    tot_synthesized_action_plan: Optional[ToTActionPlanSynthesisModel] = None # Replaces old tot_strategy_evaluation
    
    detailed_approach_plan: Optional[DetailedApproachPlanModel] = None # New field

    value_propositions: List[ValueProposition] = Field(default_factory=list) # Uses new ValueProposition structure
    objection_framework: Optional[ObjectionFramework] = None # Made optional
    strategic_questions: List[str] = Field(default_factory=list) # Already List[str], compatible
    
    # Removed fields that are now part of structured models or less relevant
    # final_action_plan: Optional[str] 
    # detailed_approach_plan_text: Optional[str]

class EnhancedPersonalizedMessage(BaseModel):
    """Enhanced personalized message with multiple variants"""
    primary_message: PersonalizedMessage = Field(..., description="Primary message variant")
    alternative_messages: List[PersonalizedMessage] = Field(
        default_factory=list, 
        description="Alternative message variants for A/B testing"
    )
    personalization_score: float = Field(default=0.0, ge=0, le=1, description="Level of personalization achieved") # Added default
    cultural_appropriateness_score: float = Field(
        default=0.0, ge=0, le=1, 
        description="Brazilian cultural appropriateness score"
    )
    estimated_response_rate: float = Field(
        default=0.0, ge=0, le=1, 
        description="Estimated response rate"
    )
    message_variants_rationale: str = Field(
        default="", 
        description="Explanation of why these variants were created"
    )
    error_message: Optional[str] = None # Added for consistency

# New InternalBriefing that matches the structure of InternalBriefingSummaryOutput from the agent
# class InternalBriefingSectionSchema(BaseModel): # Defined earlier
#     title: str
#     content: str

class InternalBriefing(BaseModel): # Replaces old InternalBriefing
    executive_summary: str = "Não especificado"
    lead_overview: Optional[InternalBriefingSectionSchema] = None 
    persona_profile_summary: Optional[InternalBriefingSectionSchema] = None
    pain_points_and_needs: Optional[InternalBriefingSectionSchema] = None
    buying_triggers_opportunity: Optional[InternalBriefingSectionSchema] = None
    lead_qualification_summary: Optional[InternalBriefingSectionSchema] = None
    approach_strategy_summary: Optional[InternalBriefingSectionSchema] = None
    custom_value_proposition_summary: Optional[InternalBriefingSectionSchema] = None
    potential_objections_summary: Optional[InternalBriefingSectionSchema] = None
    recommended_next_step: str = "Não especificado"
    error_message: Optional[str] = None 
    raw_text_report: Optional[str] = Field(None, description="Raw text output from the agent, if parsing is partial")
    # Removed old fields: key_talking_points, critical_objections, success_metrics, next_steps, decision_maker_profile, urgency_level
    # These are now expected to be part of the structured content within the sections or the executive_summary.

class ComprehensiveProspectPackage(BaseModel):
    """Complete enhanced prospect package with all intelligence"""
    analyzed_lead: AnalyzedLead = Field(..., description="Base analyzed lead data")
    enhanced_strategy: EnhancedStrategy = Field(..., description="Enhanced strategic analysis")
    enhanced_personalized_message: EnhancedPersonalizedMessage = Field(
        ..., description="Enhanced personalized messaging"
    )
    internal_briefing: InternalBriefing = Field(..., description="Internal sales briefing")
    processing_metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Processing metadata and metrics"
    )
    confidence_score: float = Field(..., ge=0, le=1, description="Overall confidence in analysis")
    roi_potential_score: float = Field(
        default=0.0, ge=0, le=1, 
        description="Estimated ROI potential (0-1 scale)"
    )
    brazilian_market_fit: float = Field(
        default=0.0, ge=0, le=1, 
        description="Brazilian market cultural fit score"
    )
    processing_timestamp: datetime = Field(default_factory=datetime.now)
    
    def to_enhanced_export_dict(self) -> Dict[str, Any]:
        """Convert to enhanced dictionary suitable for export"""
        base_dict = self.analyzed_lead.validated_lead.site_data
        return {
            "lead_url": str(base_dict.url),
            "company_name": base_dict.google_search_data.title if base_dict.google_search_data else "Unknown",
            "overall_confidence": self.confidence_score,
            "roi_potential": self.roi_potential_score,
            "qualification_tier": self.enhanced_strategy.lead_qualification.qualification_tier,
            "qualification_score": self.enhanced_strategy.lead_qualification.qualification_score,
            "primary_pain_category": self.enhanced_strategy.pain_point_analysis.primary_pain_category,
            "selected_strategy": self.enhanced_strategy.tot_strategy_evaluation.selected_strategy.strategy_name,
            "recommended_channel": self.enhanced_personalized_message.primary_message.channel.value,
            "personalization_score": self.enhanced_personalized_message.personalization_score,
            "contacts_found": len(self.enhanced_strategy.contact_information.emails_found),
            "purchase_triggers": len(self.enhanced_strategy.purchase_triggers.recent_events),
            "processing_timestamp": self.processing_timestamp.isoformat(),
            "executive_summary": self.internal_briefing.executive_summary[:200] + "..."
        }

# Additional A2A message types for future implementation
class InteractionLogMessage(A2AAgentMessage):
    """For logging interactions in a distributed system"""
    interaction_type: str
    interaction_data: dict

# Enhanced A2A messages for new capabilities
class EnhancedProspectMessage(A2AAgentMessage):
    """Message containing comprehensive prospect package for A2A communication"""
    comprehensive_prospect: ComprehensiveProspectPackage

class IntelligenceEnrichmentMessage(A2AAgentMessage):
    """Message for external intelligence enrichment requests"""
    company_name: str
    enrichment_requirements: List[str]
    tavily_queries: List[str]
