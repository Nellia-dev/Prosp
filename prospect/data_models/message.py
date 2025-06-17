from typing import Optional, List
from pydantic import BaseModel, Field
from .enums import CommunicationChannel

class PrimaryMessage(BaseModel):
    subject_line: str
    message_body: str

class EnhancedPersonalizedMessage(BaseModel):
    primary_message: Optional[PrimaryMessage] = None

class PersonalizedMessage(BaseModel):
    """Personalized outreach message"""
    channel: CommunicationChannel = Field(..., description="Communication channel")
    subject_line: Optional[str] = Field(None, description="Subject line (for email)")
    message_body: str = Field(..., description="Main message content")
    call_to_action: str = Field(..., description="Clear CTA")
    personalization_elements: List[str] = Field(..., description="Personalized elements used")
    estimated_read_time: Optional[int] = Field(None, description="Estimated read time in seconds")
    ab_variant: Optional[str] = Field(None, description="A/B test variant identifier")
