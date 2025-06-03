from typing import Optional, List, Dict, Any
from datetime import datetime
import enum # Added import for enum
from pydantic import BaseModel, Field

class LeadProcessingStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class AgentExecutionStatusEnum(str, enum.Enum):
    SUCCESS = "SUCCESS"
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
