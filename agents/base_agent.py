"""
Base agent class that provides common functionality for all agents in the pipeline.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TypeVar, Generic, List, get_args
from datetime import datetime
from loguru import logger
from pydantic import BaseModel, ValidationError, Field
import traceback
import json
import os
import requests

# MCP Server Imports
from mcp_server.data_models import AgentEventPayload, AgentExecutionStatusEnum

from core_logic.llm_client import LLMClientBase, LLMClientFactory, LLMProvider, LLMResponse


# Type variables for input and output types
TInput = TypeVar('TInput', bound=BaseModel)
TOutput = TypeVar('TOutput', bound=BaseModel)

# MCP Configuration (Module Level)
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:5001")
ENABLE_MCP_REPORTING = os.getenv("ENABLE_MCP_REPORTING", "false").lower() == "true"


class AgentMetrics(BaseModel):
    """Metrics for agent performance tracking"""
    agent_name: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    processing_time_seconds: Optional[float] = None
    success: bool = False
    error_message: Optional[str] = None
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    llm_usage: List[Dict[str, Any]] = Field(default_factory=list)


class BaseAgent(ABC, Generic[TInput, TOutput]):
    """
    Abstract base class for all agents in the Nellia Prospector pipeline.
    
    This class provides:
    - Common initialization and configuration
    - Error handling and logging
    - Performance tracking
    - LLM client management
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        llm_client: Optional[LLMClientBase] = None,
        llm_provider: Optional[LLMProvider] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the agent.
        
        Args:
            name: Agent name for logging and identification
            description: Agent description
            llm_client: Pre-configured LLM client (optional)
            llm_provider: LLM provider to use if client not provided
            config: Additional configuration dictionary
        """
        self.name = name or self.__class__.__name__ # Use class name if name not provided
        self.description = description or self.__doc__ or "N/A" # Use class docstring
        self.config = config or {} # Retaining config for now, though it was not used much
        
        # Initialize LLM client
        if llm_client:
            self.llm_client = llm_client
        elif llm_provider: # Ensure llm_provider is used if client is not passed
            self.llm_client = LLMClientFactory.create_from_env(llm_provider)
        else: # Fallback if neither is provided - might be an issue for agents needing LLM
            self.llm_client = LLMClientFactory.create_from_env()


        # Initialize metrics object for a single execution context
        self.metrics = AgentMetrics(agent_name=self.name)
        
        # MCP Server Reporting Configuration from module level constants
        self.mcp_server_url = MCP_SERVER_URL
        self.enable_mcp_reporting = ENABLE_MCP_REPORTING
        
        logger.info(f"Initialized agent: {self.name}")
        if self.enable_mcp_reporting:
            logger.info(f"MCP Reporting enabled for {self.name}, server: {self.mcp_server_url}")
    
    @abstractmethod
    def process(self, input_data: TInput) -> TOutput:
        """
        Process the input data and return the output.
        
        This is the main method that each agent must implement.
        
        Args:
            input_data: The input data for this agent
            
        Returns:
            The processed output data
        """
        pass

    def execute(self, input_data: TInput, lead_id: str, run_id: str) -> TOutput: # Changed lead_id, run_id to non-optional
        """
        Main execution method for the agent.
        Handles timing, error logging, LLM usage tracking, and MCP reporting.
        Calls the process method that should be implemented by subclasses.
        """
        self.metrics = AgentMetrics(agent_name=self.name, start_time=datetime.utcnow())
        
        output: Optional[TOutput] = None
        # lead_id and run_id are now guaranteed to be strings.

        try:
            self.logger.info(f"Agent {self.name} (Lead: {lead_id}, Run: {run_id}): Starting execution.")
            self.logger.debug(f"Agent {self.name} (Lead: {lead_id}): Input type: {type(input_data).__name__}, Input data: {input_data.model_dump_json(indent=2, exclude_none=True)[:500]}...")
            
            t_input_type_args = get_args(self.__orig_bases__[0]) if hasattr(self, "__orig_bases__") else None
            if t_input_type_args:
                t_input_type = t_input_type_args[0]
                if not isinstance(input_data, t_input_type):
                    self.logger.error(f"Agent {self.name} (Lead: {lead_id}): Input type {type(input_data)} does not match expected {t_input_type}")
                    raise ValueError(f"Input must be a Pydantic model of type {t_input_type.__name__}, got {type(input_data).__name__}")
            
            output = self.process(input_data) # Core agent logic
            
            if t_input_type_args:
                t_output_type = t_input_type_args[1]
                if not isinstance(output, t_output_type):
                     self.logger.error(f"Agent {self.name} (Lead: {lead_id}): Output type {type(output)} does not match expected {t_output_type}")
                     raise ValueError(f"Output must be a Pydantic model of type {t_output_type.__name__}, got {type(output).__name__}")

            # Check for error message in output model itself (common pattern)
            if hasattr(output, 'error_message') and getattr(output, 'error_message'):
                self.metrics.success = False
                self.metrics.error_message = getattr(output, 'error_message')
                self.logger.warning(f"Agent {self.name} (Lead: {lead_id}): Execution completed with error in output model: {self.metrics.error_message}")
            else:
                self.metrics.success = True
            self.logger.info(f"Agent {self.name} (Lead: {lead_id}): Execution completed. Success: {self.metrics.success}")

        except ValidationError as e_val:
            error_msg = f"Pydantic Validation error during agent {self.name} execution: {e_val}"
            self.logger.error(f"Agent {self.name} (Lead: {lead_id}): {error_msg}")
            self.metrics.success = False
            self.metrics.error_message = error_msg # Use the detailed validation error
            # Attempt to create a default error output object
            try:
                output_model_type = get_args(self.__orig_bases__[0])[1]
                if hasattr(output_model_type, "model_fields") and 'error_message' in output_model_type.model_fields:
                    output = output_model_type(error_message=self.metrics.error_message) # type: ignore
            except Exception as e_inner:
                self.logger.error(f"Agent {self.name} (Lead: {lead_id}): Could not form error output object after ValidationError: {e_inner}")
            raise # Re-raise ValidationError

        except Exception as e_gen:
            error_msg = f"Processing error in agent {self.name}: {str(e_gen)}\n{traceback.format_exc()}"
            self.logger.error(f"Agent {self.name} (Lead: {lead_id}): {error_msg}")
            self.metrics.success = False
            self.metrics.error_message = str(e_gen)
            try:
                output_model_type = get_args(self.__orig_bases__[0])[1]
                if hasattr(output_model_type, "model_fields") and 'error_message' in output_model_type.model_fields:
                    output = output_model_type(error_message=self.metrics.error_message) # type: ignore
            except Exception as e_inner:
                 self.logger.error(f"Agent {self.name} (Lead: {lead_id}): Could not form error output object after general exception: {e_inner}")
            raise # Re-raise general exception
            
        finally:
            self.metrics.end_time = datetime.utcnow()
            if self.metrics.start_time:
                self.metrics.processing_time_seconds = (self.metrics.end_time - self.metrics.start_time).total_seconds()
            
            # Consolidate LLM usage if client exists and has tracking
            if self.llm_client and hasattr(self.llm_client, 'get_usage_stats'):
                llm_stats = self.llm_client.get_usage_stats() # Assuming this returns a dict like {"total_tokens": ..., "input_tokens": ..., ...}
                self.metrics.llm_calls = llm_stats.get("llm_calls", self.metrics.llm_calls) # if get_usage_stats has #calls
                self.metrics.input_tokens = llm_stats.get("input_tokens", self.metrics.input_tokens)
                self.metrics.output_tokens = llm_stats.get("output_tokens", self.metrics.output_tokens)
                self.metrics.total_tokens = llm_stats.get("total_tokens", self.metrics.total_tokens)
                # self.metrics.llm_usage might be populated by individual LLM calls if needed, or get_usage_stats provides all

            mcp_status = AgentExecutionStatusEnum.SUCCESS if self.metrics.success else AgentExecutionStatusEnum.FAILED

            # metrics_dict for MCP: using the AgentMetrics model itself, or a subset
            metrics_for_mcp = self.metrics.model_dump(exclude={'start_time', 'end_time'}) # Exclude Nones, or specific fields

            self._report_event_to_mcp(
                lead_id=lead_id,
                agent_name=self.name,
                status=mcp_status,
                start_time=self.metrics.start_time,
                end_time=self.metrics.end_time,
                output_model_instance=output, # Pass the Pydantic model instance
                metrics_dict=metrics_for_mcp,
                error_message_str=self.metrics.error_message
            )

            self.logger.info(f"Agent {self.name} (Lead: {lead_id}, Run: {run_id}): Finished in {self.metrics.processing_time_seconds:.4f}s. Success: {self.metrics.success}. LLM Calls: {self.metrics.llm_calls}, Total Tokens: {self.metrics.total_tokens}")
            if self.metrics.error_message and not self.metrics.success:
                 self.logger.error(f"Agent {self.name} (Lead: {lead_id}, Run: {run_id}): Error: {self.metrics.error_message}")

        # This part is reached only if no exceptions were re-raised by the except blocks.
        if output is None:
             # This case should ideally be prevented by the except blocks creating a default error TOutput,
             # or by self.process() always returning a valid TOutput.
             self.logger.critical(f"Agent {self.name} (Lead: {lead_id}): Output is None at the end of execute and no exception was propagated. This is unexpected.")
             # Attempt to create a default error output if possible
             try:
                output_model_type = get_args(self.__orig_bases__[0])[1]
                err_msg = self.metrics.error_message or "Output was None and no prior error captured."
                if hasattr(output_model_type, "model_fields") and 'error_message' in output_model_type.model_fields:
                    return output_model_type(error_message=err_msg) # type: ignore
                else: # If TOutput can't represent an error, raise a generic critical error.
                    raise Exception(f"Critical: Agent {self.name} resulted in None output without error propagation, and TOutput cannot describe errors.")
             except Exception as e_final_create:
                 raise Exception(f"Critical: Agent {self.name} resulted in None output. Attempt to create error TOutput failed: {e_final_create}. Original error: {self.metrics.error_message}")

        return output # Return the Pydantic model instance

    def _report_event_to_mcp(
        self,
        lead_id: str,
        agent_name: str,
        status: AgentExecutionStatusEnum,
        start_time: Optional[datetime], # Make optional to handle cases where it might not be set
        end_time: Optional[datetime],   # Make optional
        output_model_instance: Optional[BaseModel],
        metrics_dict: Optional[Dict[str, Any]],
        error_message_str: Optional[str]
    ) -> None:
        if not self.enable_mcp_reporting: # Check instance variable, not global
            return

        processing_time_seconds = None
        if start_time and end_time: # Check if start_time and end_time are not None
            processing_time_seconds = (end_time - start_time).total_seconds()

        output_json_str = None
        if output_model_instance and hasattr(output_model_instance, 'model_dump_json'):
            try:
                output_json_str = output_model_instance.model_dump_json()
            except Exception as e:
                logger.error(f"[{self.name}] MCP Reporting: Error serializing output model for lead {lead_id}: {e}")
                output_json_str = json.dumps({"serialization_error": str(e)})
        elif isinstance(output_model_instance, dict):
            try:
                output_json_str = json.dumps(output_model_instance)
            except Exception as e:
                logger.error(f"[{self.name}] MCP Reporting: Error serializing dict output for lead {lead_id}: {e}")
                output_json_str = json.dumps({"serialization_error": str(e)})
        elif output_model_instance is None and status == AgentExecutionStatusEnum.FAILED:
             output_json_str = json.dumps({"error": "Agent execution failed before output could be generated."})


        metrics_json_str = None
        if metrics_dict:
            try:
                metrics_json_str = json.dumps(metrics_dict)
            except Exception as e:
                logger.error(f"[{self.name}] MCP Reporting: Error serializing metrics for lead {lead_id}: {e}")
                metrics_json_str = json.dumps({"serialization_error": str(e)})

        # Ensure start_time and end_time are valid for AgentEventPayload
        # If they were None, use current time as a fallback, though this indicates an issue.
        _start_time = start_time or datetime.utcnow()
        _end_time = end_time or datetime.utcnow()
        if not start_time: logger.warning(f"[{self.name}] MCP Reporting: start_time was None for agent {agent_name}, lead {lead_id}. Using current time.")
        if not end_time: logger.warning(f"[{self.name}] MCP Reporting: end_time was None for agent {agent_name}, lead {lead_id}. Using current time.")


        payload_data = AgentEventPayload(
            agent_name=agent_name,
            status=status,
            start_time=_start_time,
            end_time=_end_time,
            processing_time_seconds=processing_time_seconds,
            output_json=output_json_str,
            metrics_json=metrics_json_str,
            error_message=error_message_str
        )

        endpoint_url = f"{self.mcp_server_url}/api/lead/{lead_id}/event" # Use instance variable
        try:
            response = requests.post(endpoint_url, json=payload_data.model_dump(), timeout=5) # Use model_dump()
            response.raise_for_status()
            logger.info(f"[{self.name}] MCP Reporting: Successfully reported event for lead {lead_id} to {endpoint_url}")
        except requests.exceptions.RequestException as e:
            logger.error(f"[{self.name}] MCP Reporting: Failed to report event for lead {lead_id} to {endpoint_url}. Error: {e}")
        except Exception as e_unex:
            logger.error(f"[{self.name}] MCP Reporting: Unexpected error for lead {lead_id}. Error: {e_unex}")


    async def generate_llm_response(self, prompt: str, temperature: float = 0.7, max_tokens: int = 1000) -> LLMResponse: # Added temperature and max_tokens and return type
        """
        Generate a response from the LLM with error handling.
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            The LLM response content
            
        Raises:
            Exception: If LLM generation fails
        """
        try:
            response = self.llm_client.generate(prompt)
            return response.content
        except Exception as e:
            logger.error(f"[{self.name}] LLM generation failed: {e}")
            raise
    
    def parse_llm_json_response(self, response: str, expected_type: type) -> Any:
        """
        Parse JSON from LLM response with error handling.
        
        Args:
            response: The LLM response containing JSON
            expected_type: Expected type for validation (optional)
            
        Returns:
            Parsed JSON object
            
        Raises:
            ValueError: If JSON parsing fails
        """
        try:
            # Try to extract JSON from the response
            # LLMs often wrap JSON in markdown code blocks
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            else:
                json_str = response.strip()
            
            # Parse JSON
            data = json.loads(json_str)
            
            # Validate if expected type is provided
            if expected_type and hasattr(expected_type, 'parse_obj'):
                return expected_type.parse_obj(data)
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"[{self.name}] Failed to parse JSON from LLM response: {e}")
            logger.debug(f"Response: {response[:500]}...")
            raise ValueError(f"Invalid JSON in LLM response: {e}")
        except ValidationError as e:
            logger.error(f"[{self.name}] JSON validation failed: {e}")
            raise ValueError(f"JSON validation failed: {e}")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get a summary of agent metrics.
        
        Returns:
            Dictionary with metrics summary
        """
        if not self.metrics:
            return {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "average_processing_time": 0,
                "total_llm_tokens": 0
            }
        
        successful = [m for m in self.metrics if m.success]
        failed = [m for m in self.metrics if not m.success]
        
        total_time = sum(m.processing_time_seconds or 0 for m in successful)
        avg_time = total_time / len(successful) if successful else 0
        
        total_tokens = sum(
            m.llm_usage.get('total_tokens', 0) 
            for m in self.metrics 
            if m.llm_usage
        )
        
        return {
            "total_executions": len(self.metrics),
            "successful_executions": len(successful),
            "failed_executions": len(failed),
            "average_processing_time": avg_time,
            "total_processing_time": total_time,
            "total_llm_tokens": total_tokens,
            "last_execution": self.metrics[-1].dict() if self.metrics else None
        }
    
    def reset_metrics(self):
        """Reset agent metrics"""
        self.metrics = []
        if self.llm_client:
            self.llm_client.reset_usage_stats()
    
    def __str__(self):
        return f"{self.__class__.__name__}(name='{self.name}')"
    
    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"name='{self.name}', "
            f"description='{self.description}', "
            f"config={self.config})"
        ) 