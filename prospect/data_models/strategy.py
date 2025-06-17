from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from .enums import CommunicationChannel

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

class CompetitorInfo(BaseModel):
    name: str
    description: str

class CompetitorIntelligence(BaseModel):
    identified_competitors: List[CompetitorInfo]

class EnhancedStrategy(BaseModel):
    detailed_approach_plan: Optional[DetailedApproachPlan] = None
    value_propositions: Optional[List[ValueProposition]] = None
    competitor_intelligence: Optional[CompetitorIntelligence] = None

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
