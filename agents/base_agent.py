"""
Base agent class that provides common functionality for all agents in the pipeline.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TypeVar, Generic, List, get_args # Added List, get_args
from datetime import datetime
from loguru import logger
from pydantic import BaseModel, ValidationError, Field # Added Field
import traceback
import json
import os # Added for MCP config
import requests # Added for MCP reporting

from core_logic.llm_client import LLMClientBase, LLMClientFactory, LLMProvider, LLMResponse # Added LLMResponse


# Type variables for input and output types
TInput = TypeVar('TInput', bound=BaseModel)
TOutput = TypeVar('TOutput', bound=BaseModel)


class AgentMetrics(BaseModel):
    """Metrics for agent performance tracking"""
    agent_name: str # Added agent_name for clarity in metrics object
    start_time: Optional[datetime] = None # Made optional, set at start of execute
    end_time: Optional[datetime] = None
    processing_time_seconds: Optional[float] = None
    success: bool = False
    error_message: Optional[str] = None
    llm_calls: int = 0 # Added
    input_tokens: int = 0 # Added
    output_tokens: int = 0 # Added
    total_tokens: int = 0 # Added
    llm_usage: List[Dict[str, Any]] = Field(default_factory=list) # Store individual call usage, changed from Optional[Dict]


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
        self.metrics = AgentMetrics(agent_name=self.name) # metrics is now a single object, not a list
        
        # MCP Server Reporting Configuration
        self.mcp_server_url = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:5001")
        self.enable_mcp_reporting = os.getenv("ENABLE_MCP_REPORTING", "false").lower() == "true"
        
        logger.info(f"Initialized agent: {self.name}")
    
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
    
    def execute(self, input_data: TInput, lead_id: Optional[str] = None, run_id: Optional[str] = None) -> TOutput:
        """
        Main execution method for the agent.
        Handles timing, error logging, LLM usage tracking, and MCP reporting.
        Calls the process method that should be implemented by subclasses.
        """
        self.metrics = AgentMetrics(agent_name=self.name, start_time=datetime.utcnow()) # Reset metrics
        
        output: Optional[TOutput] = None
        effective_lead_id = lead_id or "unknown_lead"
        effective_run_id = run_id or "unknown_run"
        output_json_str: Optional[str] = None

        try:
            self.logger.info(f"Agent {self.name} (Lead: {effective_lead_id}, Run: {effective_run_id}): Starting execution.")
            self.logger.debug(f"Agent {self.name} (Lead: {effective_lead_id}): Input type: {type(input_data).__name__}, Input data: {input_data.model_dump_json(indent=2, exclude_none=True)[:500]}...")
            
            t_input_type_args = get_args(self.__orig_bases__[0]) if hasattr(self, "__orig_bases__") else None
            if t_input_type_args:
                t_input_type = t_input_type_args[0]
                if not isinstance(input_data, t_input_type):
                    self.logger.error(f"Input type {type(input_data)} does not match expected {t_input_type}")
                    raise ValueError(f"Input must be a Pydantic model of type {t_input_type.__name__}, got {type(input_data).__name__}")
            
            output = self.process(input_data)
            
            if t_input_type_args:
                t_output_type = t_input_type_args[1]
                if not isinstance(output, t_output_type):
                     self.logger.error(f"Output type {type(output)} does not match expected {t_output_type}")
                     raise ValueError(f"Output must be a Pydantic model of type {t_output_type.__name__}, got {type(output).__name__}")

            if hasattr(output, 'error_message') and getattr(output, 'error_message'):
                self.metrics.success = False
                self.metrics.error_message = getattr(output, 'error_message')
                self.logger.warning(f"Agent {self.name} (Lead: {effective_lead_id}): Execution completed with error in output: {self.metrics.error_message}")
            else:
                self.metrics.success = True
            self.logger.info(f"Agent {self.name} (Lead: {effective_lead_id}): Execution completed. Success: {self.metrics.success}")

        except ValidationError as e:
            error_msg = f"Pydantic Validation error during agent {self.name} execution: {e}"
            self.logger.error(f"Agent {self.name} (Lead: {effective_lead_id}): {error_msg}")
            self.metrics.success = False
            self.metrics.error_message = error_msg
            try:
                output_model_type = get_args(self.__orig_bases__[0])[1]
                if hasattr(output_model_type, "model_fields") and 'error_message' in output_model_type.model_fields:
                    output = output_model_type(error_message=error_msg)
                elif hasattr(output_model_type, "__fields__") and 'error_message' in output_model_type.__fields__:
                    output = output_model_type(error_message=error_msg) # type: ignore
            except Exception as e_inner:
                self.logger.error(f"Agent {self.name} (Lead: {effective_lead_id}): Could not form error output object: {e_inner}")

        except Exception as e:
            error_msg = f"Processing error in agent {self.name}: {str(e)}\n{traceback.format_exc()}"
            self.logger.error(f"Agent {self.name} (Lead: {effective_lead_id}): {error_msg}")
            self.metrics.success = False
            self.metrics.error_message = str(e)
            try:
                output_model_type = get_args(self.__orig_bases__[0])[1]
                if hasattr(output_model_type, "model_fields") and 'error_message' in output_model_type.model_fields:
                    output = output_model_type(error_message=str(e))
                elif hasattr(output_model_type, "__fields__") and 'error_message' in output_model_type.__fields__:
                    output = output_model_type(error_message=str(e)) # type: ignore
            except Exception as e_inner:
                 self.logger.error(f"Agent {self.name} (Lead: {effective_lead_id}): Could not form error output object after general exception: {e_inner}")
            
        finally:
            self.metrics.end_time = datetime.utcnow()
            if self.metrics.start_time:
                self.metrics.processing_time_seconds = (self.metrics.end_time - self.metrics.start_time).total_seconds()
            
            if output is not None:
                try:
                    output_json_str = output.model_dump_json(exclude_none=True) if hasattr(output, "model_dump_json") else json.dumps(str(output))
                except Exception as e_json:
                    self.logger.error(f"Agent {self.name} (Lead: {effective_lead_id}): Failed to serialize output to JSON for MCP: {e_json}")
                    try:
                        output_dict = output.model_dump() if hasattr(output, "model_dump") else dict(output) if hasattr(output, "__dict__") else {"raw_output": str(output)}
                        output_json_str = json.dumps({"error": "Failed to serialize output with model_dump_json for MCP", "detail": str(e_json), "fallback_output": output_dict})
                    except Exception as e_dict_json:
                         output_json_str = json.dumps({"error": "Failed to serialize output completely for MCP", "detail": str(e_dict_json)})
            else:
                output_json_str = json.dumps({"error": "Agent output was None.", "agent_error_message": self.metrics.error_message})

            if self.enable_mcp_reporting and lead_id and run_id:
                self._report_event_to_mcp(effective_lead_id, effective_run_id, output_json_str)

            self.logger.info(f"Agent {self.name} (Lead: {effective_lead_id}, Run: {effective_run_id}): Finished in {self.metrics.processing_time_seconds:.4f}s. Success: {self.metrics.success}. LLM Calls: {self.metrics.llm_calls}, Total Tokens: {self.metrics.total_tokens}")
            if self.metrics.error_message and not self.metrics.success:
                 self.logger.error(f"Agent {self.name} (Lead: {effective_lead_id}, Run: {effective_run_id}): Error: {self.metrics.error_message}")

        if output is None:
             self.logger.critical(f"Agent {self.name} (Lead: {effective_lead_id}): Output is None at the end of execute. This indicates a logic flaw or TOutput cannot represent error state adequately.")
             try:
                output_model_type = get_args(self.__orig_bases__[0])[1]
                error_msg_content = self.metrics.error_message or "Unknown error: Output was None and no specific error message in metrics."
                if hasattr(output_model_type, "model_fields") and 'error_message' in output_model_type.model_fields:
                    output = output_model_type(error_message=error_msg_content)
                elif hasattr(output_model_type, "__fields__") and 'error_message' in output_model_type.__fields__:
                    output = output_model_type(error_message=error_msg_content) # type: ignore
                else:
                    raise ValueError(f"Agent {self.name}: Output is None and TOutput type ({output_model_type}) has no 'error_message' field. Cannot create default error response.")
             except Exception as e_final:
                 self.logger.error(f"Agent {self.name} (Lead: {effective_lead_id}): Truly failed to create any TOutput: {e_final}")
                 raise ValueError(f"Agent {self.name}: Critical error - output is None and cannot form error response. Original error: {self.metrics.error_message or 'Unknown'}")
        return output

    def _report_event_to_mcp(self, lead_id: str, run_id: str, output_json_str: Optional[str]):
        """Helper method to report agent execution event to MCP server."""
        if not self.enable_mcp_reporting:
            return

        metrics_payload_dict = {
            "llm_calls": self.metrics.llm_calls,
            "total_tokens": self.metrics.total_tokens,
            "input_tokens": self.metrics.input_tokens,
            "output_tokens": self.metrics.output_tokens,
            "llm_usage_details": self.metrics.llm_usage
        }
        try:
            metrics_json_str = json.dumps(metrics_payload_dict)
        except Exception as e_metrics_json:
            self.logger.error(f"Agent {self.name} (Lead: {lead_id}): Failed to serialize metrics to JSON: {e_metrics_json}")
            metrics_json_str = json.dumps({"error": "Failed to serialize metrics", "detail": str(e_metrics_json)})

        event_payload = {
            "agent_name": self.name,
            "status": "SUCCESS" if self.metrics.success else "FAILED",
            "start_time": self.metrics.start_time.isoformat() if self.metrics.start_time else datetime.utcnow().isoformat(),
            "end_time": self.metrics.end_time.isoformat() if self.metrics.end_time else datetime.utcnow().isoformat(),
            "processing_time_seconds": self.metrics.processing_time_seconds,
            "output_json": output_json_str,
            "metrics_json": metrics_json_str,
            "error_message": self.metrics.error_message
        }

        endpoint_url = f"{self.mcp_server_url}/api/lead/{lead_id}/event"
        try:
            self.logger.debug(f"Agent {self.name} (Lead: {lead_id}): Reporting event to MCP: {endpoint_url} with payload keys: {list(event_payload.keys())}")
            response = requests.post(endpoint_url, json=event_payload, timeout=10)
            response.raise_for_status()
            self.logger.info(f"Agent {self.name} (Lead: {lead_id}): Successfully reported event to MCP server (status {response.status_code}).")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Agent {self.name} (Lead: {lead_id}): Failed to report event to MCP server at {endpoint_url}. Error: {e}")
        except Exception as e_unexpected:
            self.logger.error(f"Agent {self.name} (Lead: {lead_id}): Unexpected error while reporting to MCP: {e_unexpected}")


    def generate_llm_response(self, prompt: str) -> str:
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