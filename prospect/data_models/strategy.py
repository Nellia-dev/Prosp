from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from .enums import CommunicationChannel
from .intelligence import (
    LeadQualification, PurchaseTriggers, ExternalIntelligence, ContactInformation,
    PainPointAnalysis, CompetitorIntelligence, ToTStrategyOptionModel, EvaluatedStrategyModel, 
    ToTActionPlanSynthesisModel, ObjectionFramework, DetailedApproachPlanModel
)

class Persona(BaseModel):
    likely_role: str
    decision_maker_probability: float

class DetailedApproachStep(BaseModel):
    step_number: int
    channel: str
    objective: str
    cta: str = Field(..., alias='cta')

class DetailedApproachPlan(BaseModel):
    main_objective: str
    adapted_elevator_pitch: str
    contact_sequence: List[DetailedApproachStep]

class ValueProposition(BaseModel):
    title: str
    key_benefit: str

# EnhancedStrategy is now the main container for all intelligence pieces
class EnhancedStrategy(BaseModel):
    external_intelligence: Optional[ExternalIntelligence] = None
    contact_information: Optional[ContactInformation] = None
    pain_point_analysis: Optional[PainPointAnalysis] = None
    competitor_intelligence: Optional[CompetitorIntelligence] = None
    purchase_triggers: Optional[PurchaseTriggers] = None
    lead_qualification: Optional[LeadQualification] = None
    tot_generated_strategies: Optional[List[ToTStrategyOptionModel]] = None
    tot_evaluated_strategies: Optional[List[EvaluatedStrategyModel]] = None
    tot_synthesized_action_plan: Optional[ToTActionPlanSynthesisModel] = None
    detailed_approach_plan: Optional[DetailedApproachPlanModel] = None
    value_propositions: Optional[List[ValueProposition]] = None
    objection_framework: Optional[ObjectionFramework] = None
    strategic_questions: Optional[List[str]] = None

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
