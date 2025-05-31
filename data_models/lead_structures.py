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
    extracted_text_content: str = Field(..., description="Extracted text content from the website")
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


# Additional A2A message types for future implementation
class InteractionLogMessage(A2AAgentMessage):
    """For logging interactions in a distributed system"""
    interaction_type: str
    interaction_data: dict 