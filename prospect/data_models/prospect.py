from typing import List, Optional
from pydantic import BaseModel

from .enums import ProcessingStage, LeadStatus, QualificationTier
from .strategy import Persona, EnhancedStrategy
from .message import EnhancedPersonalizedMessage

from .core import AnalyzedLead
from .intelligence import InternalBriefing, PersonaProfile

class ComprehensiveProspectPackage(BaseModel):
    """A Pydantic model that mirrors the TypeScript ComprehensiveProspectPackage interface."""
    analyzed_lead: AnalyzedLead
    enhanced_strategy: Optional[EnhancedStrategy] = None
    enhanced_personalized_message: Optional[EnhancedPersonalizedMessage] = None
    internal_briefing: Optional[InternalBriefing] = None
    persona_profile: Optional[PersonaProfile] = None
    relevance_score: float
    roi_potential_score: float
    processing_metadata: Dict[str, Any]

class LeadData(BaseModel):
    """Pydantic model for a lead, aligned with the frontend's LeadData type."""
    id: str
    company_name: str
    website: str
    relevance_score: float
    roi_potential_score: float
    qualification_tier: QualificationTier
    company_sector: str
    persona: Optional[Persona] = None
    pain_point_analysis: Optional[List[str]] = None
    purchase_triggers: Optional[List[str]] = None
    processing_stage: ProcessingStage
    status: LeadStatus
    enrichment_data: Optional[ComprehensiveProspectPackage] = None
    created_at: str
    updated_at: str
