from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class ContactInformation(BaseModel):
    """Contact information extracted from lead analysis"""
    emails_found: List[str] = Field(default_factory=list, description="Email addresses found")
    instagram_profiles: List[str] = Field(default_factory=list, description="Instagram profile URLs")
    linkedin_profiles: List[str] = Field(default_factory=list, description="LinkedIn profile URLs")
    phone_numbers: List[str] = Field(default_factory=list, description="Phone numbers found")
    extraction_confidence: float = Field(default=0.0, ge=0, le=1, description="Confidence in extraction accuracy")
    tavily_search_suggestions: List[str] = Field(default_factory=list, description="Suggested searches for additional contact info")

class DetailedPainPointSchema(BaseModel): 
    """Maps to PainPointDeepeningOutput.DetailedPainPoint"""
    pain_description: str
    business_impact: str
    solution_alignment: str

class PainPointAnalysis(BaseModel):
    """Deep analysis of company pain points and challenges"""
    primary_pain_category: str = Field(default="Não especificado", description="Main category of pain point")
    detailed_pain_points: List[DetailedPainPointSchema] = Field(default_factory=list)
    business_impact_assessment: Optional[str] = Field(None, description="Overall assessment of business impact from agent's raw text")
    urgency_level: str = Field(default="medium", description="Urgency level: low, medium, high, critical")
    investigative_questions: List[str] = Field(default_factory=list, description="Strategic questions to deepen understanding")
    raw_text_report: Optional[str] = Field(None, description="Raw text output from the agent, if parsing is partial")
    error_message: Optional[str] = None

class CompetitorDetailSchema(BaseModel):
    """Maps to CompetitorIdentificationOutput.CompetitorDetail"""
    name: str
    description: Optional[str] = None
    perceived_strength: Optional[str] = None
    perceived_weakness: Optional[str] = None

class CompetitorIntelligence(BaseModel):
    """Competitive intelligence and market analysis"""
    identified_competitors: List[CompetitorDetailSchema] = Field(default_factory=list)
    other_notes: Optional[str] = Field(None, description="Other general notes on competitive landscape")
    raw_text_report: Optional[str] = Field(None, description="Raw text output from the agent, if parsing is partial")
    error_message: Optional[str] = None

class IdentifiedTriggerSchema(BaseModel):
    """Maps to BuyingTriggerIdentificationOutput.IdentifiedTrigger"""
    trigger_description: str
    relevance_explanation: str

class PurchaseTriggers(BaseModel):
    """Purchase triggers and timing indicators"""
    identified_triggers: List[IdentifiedTriggerSchema] = Field(default_factory=list)
    other_observations: Optional[str] = Field(None, description="Other general observations on triggers")
    raw_text_report: Optional[str] = Field(None, description="Raw text output from the agent, if parsing is partial")
    error_message: Optional[str] = None

class LeadQualification(BaseModel):
    """Lead qualification scoring and assessment"""
    qualification_tier: str = Field(..., description="High Potential, Medium, Low, Not Qualified")
    qualification_score: float = Field(..., ge=0, le=1, description="Numerical qualification score")
    qualification_reasoning: List[str] = Field(default_factory=list, description="Reasons for qualification score")
    fit_score: float = Field(default=0.0, ge=0, le=1, description="Product-market fit score")
    readiness_score: float = Field(default=0.0, ge=0, le=1, description="Purchase readiness score")
    authority_score: float = Field(default=0.0, ge=0, le=1, description="Decision-making authority score")
    budget_likelihood: str = Field(default="unknown", description="Budget availability likelihood")
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="Confidence score of the qualification analysis")
    error_message: Optional[str] = None

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

class InternalBriefingSection(BaseModel):
    title: str
    content: str

class InternalBriefing(BaseModel):
    executive_summary: str = "Não especificado"
    lead_overview: InternalBriefingSection = Field(default_factory=lambda: InternalBriefingSection(title="Visão Geral do Lead", content=""))
    persona_profile_summary: InternalBriefingSection = Field(default_factory=lambda: InternalBriefingSection(title="Perfil da Persona", content=""))
    pain_points_and_needs: InternalBriefingSection = Field(default_factory=lambda: InternalBriefingSection(title="Dores e Necessidades", content=""))
    buying_triggers_opportunity: InternalBriefingSection = Field(default_factory=lambda: InternalBriefingSection(title="Gatilhos de Compra e Oportunidade", content=""))
    lead_qualification_summary: InternalBriefingSection = Field(default_factory=lambda: InternalBriefingSection(title="Qualificação do Lead", content=""))
    approach_strategy_summary: InternalBriefingSection = Field(default_factory=lambda: InternalBriefingSection(title="Estratégia de Abordagem", content=""))
    custom_value_proposition_summary: InternalBriefingSection = Field(default_factory=lambda: InternalBriefingSection(title="Proposta de Valor Customizada", content=""))
    potential_objections_summary: InternalBriefingSection = Field(default_factory=lambda: InternalBriefingSection(title="Objeções Potenciais", content=""))
    recommended_next_step: str = "Não especificado"
    error_message: Optional[str] = None

class PersonaProfile(BaseModel):
    persona_title: str
    decision_maker_likelihood: float

class ExternalIntelligence(BaseModel):
    """External intelligence gathered from Tavily and other sources"""
    tavily_enrichment: str = Field(default="", description="Enriched data from Tavily API")
    market_research: str = Field(default="", description="Additional market research")
    news_analysis: str = Field(default="", description="Recent news and developments")
    social_signals: List[str] = Field(default_factory=list, description="Social media signals")
    enrichment_confidence: float = Field(default=0.0, ge=0, le=1, description="Confidence in enriched data")
    sources_used: List[str] = Field(default_factory=list, description="Data sources utilized")
    error_message: Optional[str] = None

class ObjectionFramework(BaseModel):
    """Framework for handling objections"""
    anticipated_objections: List[ObjectionResponseModelSchema] = Field(default_factory=list)
    raw_text_report: Optional[str] = Field(None, description="Raw text output from the agent, if parsing is partial")
    error_message: Optional[str] = None
