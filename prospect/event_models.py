"""
Event models for the agentic harvester pipeline.
Defines structured event types that are yielded during the execution of the agentic pipeline.
"""

from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from datetime import datetime
from data_models.prospect import LeadData, ComprehensiveProspectPackage
from pydantic import HttpUrl
import json


@dataclass
class BaseEvent:
    """Base class for all pipeline events."""
    event_type: str
    timestamp: str
    # Non-default arguments must come before default arguments
    job_id: str
    user_id: str
    
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
    max_leads: int
    
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "initial_query": self.initial_query,
            "max_leads": self.max_leads
        })
        return data


@dataclass
class PipelineEndEvent(BaseEvent):
    """Event emitted when the agentic pipeline completes."""
    total_leads_generated: int
    execution_time: float
    success: bool
    error_message: Optional[str] = None
    
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "total_leads_generated": self.total_leads_generated,
            "execution_time": self.execution_time,
            "success": self.success,
            "error_message": self.error_message
        })
        return data


@dataclass
class AgentStartEvent(BaseEvent):
    """Event emitted when an agent starts execution."""
    agent_name: str
    input_query: str
    
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "agent_name": self.agent_name,
            "input_query": self.input_query
        })
        return data


@dataclass
class AgentEndEvent(BaseEvent):
    """Event emitted when an agent completes execution."""
    agent_name: str
    execution_time: float
    success: bool
    error_message: Optional[str] = None
    
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "agent_name": self.agent_name,
            "execution_time": self.execution_time,
            "success": self.success,
            "error_message": self.error_message
        })
        return data


@dataclass
class ToolCallStartEvent(BaseEvent):
    """Event emitted when a tool starts execution."""
    tool_name: str
    agent_name: str
    tool_args: Dict[str, Any]
    
    
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
    lead_data: LeadData  # Use the strongly-typed Pydantic model

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        # The lead_data is now a Pydantic model, so we dump it to a dict for serialization.
        # model_dump ensures that nested Pydantic models and enums are correctly converted.
        data.update({
            "lead_data": self.lead_data.model_dump(by_alias=True, exclude_none=True)
        })
        return data


@dataclass
class LeadEnrichmentStartEvent(BaseEvent):
    """Event emitted when the enrichment process starts for a specific lead."""
    lead_id: str
    company_name: str


    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "lead_id": self.lead_id,
            "company_name": self.company_name,
        })
        return data


@dataclass
class LeadEnrichmentEndEvent(BaseEvent):
    """Event emitted when the enrichment process for a lead completes."""
    lead_id: str
    success: bool
    final_package: Optional[ComprehensiveProspectPackage] = None  # Use the new model
    error_message: Optional[str] = None


    def _convert_value(self, value: Any) -> Any:
        """
        Recursively converts values for JSON serialization.
        - Converts HttpUrl to string.
        - Converts Pydantic models to dict using model_dump(mode='json').
        - Recursively processes lists and dicts.
        """
        if isinstance(value, HttpUrl):
            return str(value)
        if hasattr(value, 'model_dump'): # Check for Pydantic model
            return value.model_dump(mode='json')
        if isinstance(value, list):
            return [self._convert_value(item) for item in value]
        if isinstance(value, dict):
            return {k: self._convert_value(v) for k, v in value.items()}
        return value

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()

        def convert_special_types(item: Any) -> Any:
            if isinstance(item, HttpUrl):
                return str(item)
            if isinstance(item, datetime):
                return item.isoformat()
            if isinstance(item, dict):
                return {k: convert_special_types(v) for k, v in item.items()}
            if isinstance(item, list):
                return [convert_special_types(i) for i in item]
            return item

        processed_final_package = None
        # The final_package is now a Pydantic model. model_dump handles serialization.
        final_package_dict = self.final_package.model_dump(by_alias=True, exclude_none=True) if self.final_package else None

        data.update({
            "lead_id": self.lead_id,
            "success": self.success,
            "final_package": final_package_dict,
            "error_message": self.error_message,
        })
        return data


@dataclass
class StatusUpdateEvent(BaseEvent):
    """Event emitted for general status updates."""
    status_message: str
    agent_name: Optional[str] = None
    progress_percentage: Optional[float] = None
    
    
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
    "lead_enrichment_start": LeadEnrichmentStartEvent,
    "lead_enrichment_end": LeadEnrichmentEndEvent,
}


def create_event_from_dict(event_data: Dict[str, Any]) -> BaseEvent:
    """Create an event instance from a dictionary."""
    event_type = event_data.get("event_type")
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Unknown event type: {event_type}")
    
    event_class = EVENT_TYPES[event_type]
    return event_class(**event_data)
