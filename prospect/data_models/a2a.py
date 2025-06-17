import uuid
from datetime import datetime
from pydantic import BaseModel, Field

from .core import ValidatedLead, AnalyzedLead, LeadWithPersona, FinalProspectPackage

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
