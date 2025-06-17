import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, HttpUrl, validator

from .strategy import PersonaDetails, ApproachStrategy
from .message import PersonalizedMessage

class GoogleSearchData(BaseModel):
    """Google search result data for a lead"""
    title: str = Field(..., description="Page title from Google search")
    snippet: str = Field(..., description="Page snippet from Google search")

class SiteData(BaseModel):
    """Individual lead data from harvester"""
    url: HttpUrl = Field(..., description="Website URL")
    google_search_data: Optional[GoogleSearchData] = Field(None, description="Google search data")
    extracted_text_content: Optional[str] = Field(None, description="Extracted text content from the website")
    extraction_status_message: str = Field(..., description="Status message of extraction")
    screenshot_filepath: Optional[str] = Field(None, description="Path to screenshot if available")

    @validator('url', pre=True)
    def validate_url(cls, v):
        if isinstance(v, str) and not v.startswith(('http://', 'https://')):
            return f'https://{v}'
        return v

class LeadIntakeInput(BaseModel):
    """Input structure for the LeadIntakeAgent, combining SiteData with lead_id."""
    lead_id: str = Field(..., description="Unique identifier for the lead")
    company_name: str = Field(..., description="Company name for the lead")
    site_data: SiteData = Field(..., description="The actual site data to be processed")

class HarvesterOutput(BaseModel):
    """Complete output from the harvester service"""
    original_query: str = Field(..., description="Original search query")
    collection_timestamp: datetime = Field(..., description="When the data was collected")
    total_sites_targeted_for_processing: int = Field(..., description="Total sites targeted")
    total_sites_processed_in_extraction_phase: int = Field(..., description="Sites actually processed")
    sites_data: List[SiteData] = Field(..., description="List of processed site data")

class ValidatedLead(BaseModel):
    """Validated lead after intake processing"""
    lead_id: str = Field(..., description="Unique identifier for the lead")
    company_name: str = Field(..., description="Company name for the lead")
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

class LeadWithPersona(BaseModel):
    """Lead with persona information"""
    analyzed_lead: AnalyzedLead = Field(..., description="Analyzed lead data")
    persona: PersonaDetails = Field(..., description="Decision maker persona")
    persona_creation_timestamp: datetime = Field(default_factory=datetime.now)

class LeadWithStrategy(BaseModel):
    """Lead with complete approach strategy"""
    lead_with_persona: LeadWithPersona = Field(..., description="Lead with persona data")
    strategy: ApproachStrategy = Field(..., description="Approach strategy")
    strategy_timestamp: datetime = Field(default_factory=datetime.now)

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
