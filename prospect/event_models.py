"""
Event models for the agentic harvester pipeline.
Defines structured event types that are yielded during the execution of the agentic pipeline.
"""

from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class BaseEvent:
    """Base class for all pipeline events."""
    event_type: str
    timestamp: str
    job_id: Optional[str] = None
    user_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization."""
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "job_id": self.job_id,
            "user_id": self.user_id
        }


@dataclass
class PipelineStartEvent(BaseEvent):
    """Event emitted when the agentic pipeline starts."""
    initial_query: str
    max_leads_to_generate: int
    
    def __post_init__(self):
        self.event_type = "pipeline_start"
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "initial_query": self.initial_query,
            "max_leads_to_generate": self.max_leads_to_generate
        })
        return data


@dataclass
class PipelineEndEvent(BaseEvent):
    """Event emitted when the agentic pipeline completes."""
    total_leads_generated: int
    execution_time_seconds: float
    success: bool
    error_message: Optional[str] = None
    
    def __post_init__(self):
        self.event_type = "pipeline_end"
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "total_leads_generated": self.total_leads_generated,
            "execution_time_seconds": self.execution_time_seconds,
            "success": self.success,
            "error_message": self.error_message
        })
        return data


@dataclass
class AgentStartEvent(BaseEvent):
    """Event emitted when an agent starts execution."""
    agent_name: str
    agent_description: str
    input_query: str
    
    def __post_init__(self):
        self.event_type = "agent_start"
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "agent_name": self.agent_name,
            "agent_description": self.agent_description,
            "input_query": self.input_query
        })
        return data


@dataclass
class AgentEndEvent(BaseEvent):
    """Event emitted when an agent completes execution."""
    agent_name: str
    execution_time_seconds: float
    success: bool
    final_response: Optional[str] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        self.event_type = "agent_end"
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "agent_name": self.agent_name,
            "execution_time_seconds": self.execution_time_seconds,
            "success": self.success,
            "final_response": self.final_response,
            "error_message": self.error_message
        })
        return data


@dataclass
class ToolCallStartEvent(BaseEvent):
    """Event emitted when a tool starts execution."""
    tool_name: str
    agent_name: str
    tool_args: Dict[str, Any]
    
    def __post_init__(self):
        self.event_type = "tool_call_start"
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "tool_name": self.tool_name,
            "agent_name": self.agent_name,
            "tool_args": self.tool_args
        })
        return data


@dataclass
class ToolCallOutputEvent(BaseEvent):
    """Event emitted when a tool produces output."""
    tool_name: str
    agent_name: str
    output_snippet: str  # Potentially chunked output
    is_final: bool = False
    
    def __post_init__(self):
        self.event_type = "tool_call_output"
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "tool_name": self.tool_name,
            "agent_name": self.agent_name,
            "output_snippet": self.output_snippet,
            "is_final": self.is_final
        })
        return data


@dataclass
class ToolCallEndEvent(BaseEvent):
    """Event emitted when a tool completes execution."""
    tool_name: str
    agent_name: str
    execution_time_seconds: float
    success: bool
    error_message: Optional[str] = None
    
    def __post_init__(self):
        self.event_type = "tool_call_end"
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "tool_name": self.tool_name,
            "agent_name": self.agent_name,
            "execution_time_seconds": self.execution_time_seconds,
            "success": self.success,
            "error_message": self.error_message
        })
        return data


@dataclass
class LeadGeneratedEvent(BaseEvent):
    """Event emitted when a lead is successfully generated."""
    lead_data: Dict[str, Any]
    source_url: str
    agent_name: str
    
    def __post_init__(self):
        self.event_type = "lead_generated"
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "lead_data": self.lead_data,
            "source_url": self.source_url,
            "agent_name": self.agent_name
        })
        return data


@dataclass
class StatusUpdateEvent(BaseEvent):
    """Event emitted for general status updates."""
    status_message: str
    agent_name: Optional[str] = None
    progress_percentage: Optional[float] = None
    
    def __post_init__(self):
        self.event_type = "status_update"
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "status_message": self.status_message,
            "agent_name": self.agent_name,
            "progress_percentage": self.progress_percentage
        })
        return data


@dataclass
class PipelineErrorEvent(BaseEvent):
    """Event emitted when a critical error occurs in the pipeline."""
    error_message: str
    error_type: str
    agent_name: Optional[str] = None
    tool_name: Optional[str] = None
    
    def __post_init__(self):
        self.event_type = "pipeline_error"
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "error_message": self.error_message,
            "error_type": self.error_type,
            "agent_name": self.agent_name,
            "tool_name": self.tool_name
        })
        return data


# Event type mapping for easy instantiation
EVENT_TYPES = {
    "pipeline_start": PipelineStartEvent,
    "pipeline_end": PipelineEndEvent,
    "agent_start": AgentStartEvent,
    "agent_end": AgentEndEvent,
    "tool_call_start": ToolCallStartEvent,
    "tool_call_output": ToolCallOutputEvent,
    "tool_call_end": ToolCallEndEvent,
    "lead_generated": LeadGeneratedEvent,
    "status_update": StatusUpdateEvent,
    "pipeline_error": PipelineErrorEvent,
}


def create_event_from_dict(event_data: Dict[str, Any]) -> BaseEvent:
    """Create an event instance from a dictionary."""
    event_type = event_data.get("event_type")
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Unknown event type: {event_type}")
    
    event_class = EVENT_TYPES[event_type]
    return event_class(**event_data)
