from typing import Optional, List, Dict, Any
from datetime import datetime
import enum # Added import for enum
from pydantic import BaseModel, Field

# =============================================================================
# NEW SCHEMAS FOR AGENTIC HARVESTER
# =============================================================================

class HarvesterJobData(BaseModel):
    """Schema for harvester job data sent from NestJS backend"""
    user_id: str = Field(description="ID of the user who initiated the job")
    initial_query: str = Field(description="User's initial search query")
    business_context: Dict[str, Any] = Field(description="User's business context")
    max_leads_to_generate: int = Field(description="Maximum number of leads to generate")
    max_sites_to_scrape: Optional[int] = Field(default=3, description="Maximum sites to scrape")
    job_id: Optional[str] = Field(None, description="Job identifier for tracking")
    timestamp: str = Field(description="Timestamp when job was initiated")

class AgenticHarvesterResponse(BaseModel):
    """Response schema for agentic harvester execution"""
    success: bool
    job_id: str
    user_id: str
    total_leads_generated: int
    execution_time_seconds: float
    error_message: Optional[str] = None
    leads_data: Optional[List[Dict[str, Any]]] = None

class StreamingEventResponse(BaseModel):
    """Schema for streaming event responses"""
    event_type: str
    timestamp: str
    job_id: Optional[str] = None
    user_id: Optional[str] = None
    data: Dict[str, Any]

class EnrichmentJobData(BaseModel):
    """Schema for enrichment job data sent from NestJS backend"""
    user_id: str = Field(description="ID of the user who initiated the job")
    job_id: str = Field(description="Job identifier for tracking")
    # The entire AnalyzedLead object will be sent as a dict
    analyzed_lead_data: Dict[str, Any] = Field(description="The analyzed lead data to be enriched")
    product_service_context: str = Field(description="The user's product/service context")
    competitors_list: Optional[str] = Field(None, description="A string of known competitors")
    timestamp: str = Field(description="Timestamp when job was initiated")

class LeadProcessingStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class AgentExecutionStatusEnum(str, enum.Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"

class LeadProcessingStateBase(BaseModel):
    lead_id: str = Field(description="Unique identifier for the lead, e.g., a UUID or hash of the URL.")
    run_id: str = Field(description="Identifier for the execution run, grouping multiple leads.")
    url: Optional[str] = Field(None, description="The actual URL of the lead.")
    status: LeadProcessingStatusEnum = Field(default=LeadProcessingStatusEnum.PENDING, description="Current processing status of the lead.")
    current_agent: Optional[str] = Field(None, description="Name of the agent currently processing this lead, if active.")
    start_time: datetime = Field(default_factory=datetime.utcnow)
    last_update_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    error_message: Optional[str] = Field(None, description="Error message if the overall lead processing failed.")
    # Using Dict for summary; can be stringified JSON if stored directly in DB text field
    final_package_summary: Optional[Dict[str, Any]] = Field(None, description="A brief summary of the final output or key error information.")

class LeadProcessingStateCreate(LeadProcessingStateBase):
    pass

class LeadProcessingState(LeadProcessingStateBase):
    class Config:
        from_attributes = True # For Pydantic v2 (orm_mode is deprecated)

class AgentExecutionRecordBase(BaseModel):
    lead_id: str = Field(description="Foreign key linking to the LeadProcessingState.")
    agent_name: str
    status: AgentExecutionStatusEnum
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None # Should be set on completion
    processing_time_seconds: Optional[float] = None
    input_summary: Optional[str] = Field(None, description="Optional: a brief summary or hash of the input to the agent.")
    output_json: Optional[str] = Field(None, description="The full JSON output from the agent as a string.")
    metrics_json: Optional[str] = Field(None, description="JSON string of AgentMetrics from BaseAgent.")
    error_message: Optional[str] = Field(None, description="Error message if this specific agent execution failed.")

class AgentExecutionRecordCreate(AgentExecutionRecordBase):
    pass

class AgentExecutionRecord(AgentExecutionRecordBase):
    record_id: int = Field(description="Unique auto-incrementing ID for the record.")

    class Config:
        from_attributes = True # For Pydantic v2 (orm_mode is deprecated)

# Example of how the event payload from processor to MCP might look
class AgentEventPayload(BaseModel):
    agent_name: str
    status: AgentExecutionStatusEnum
    start_time: datetime
    end_time: datetime
    processing_time_seconds: Optional[float] = None
    output_json: Optional[str] = None # Output from the agent
    metrics_json: Optional[str] = None # Metrics from BaseAgent
    error_message: Optional[str] = None
