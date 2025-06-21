"""
Base agent class that provides common functionality for all agents in the pipeline.
"""

from abc import ABC, abstractmethod
import asyncio
from typing import Any, Dict, Optional, TypeVar, Generic
from datetime import datetime
from loguru import logger
from pydantic import BaseModel, ValidationError
import traceback
import json

from core_logic.llm_client import LLMClientBase, LLMClientFactory, LLMProvider


# Type variables for input and output types
TInput = TypeVar('TInput', bound=BaseModel)
TOutput = TypeVar('TOutput', bound=BaseModel)


class AgentMetrics(BaseModel):
    """Metrics for agent performance tracking"""
    start_time: datetime
    end_time: Optional[datetime] = None
    processing_time_seconds: Optional[float] = None
    success: bool = False
    error_message: Optional[str] = None
    llm_usage: Optional[Dict[str, int]] = None


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
        event_queue: Optional[asyncio.Queue] = None,
        user_id: Optional[str] = None,
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
        self.name = name
        self.description = description
        self.config = config or {}
        self.event_queue = event_queue
        self.user_id = user_id
        
        # Initialize logger instance for agent use
        self.logger = logger.bind(agent=name)
        
        # Initialize LLM client
        if llm_client:
            self.llm_client = llm_client
        else:
            self.llm_client = LLMClientFactory.create_from_env(llm_provider)
        
        # Initialize metrics
        self.metrics = []
        
        self.logger.info(f"Initialized agent: {self.name}")
    
    async def _emit_event(self, event_type: str, payload: dict):
        """Emit an event to the event queue if it exists."""
        if self.event_queue:
            event = {
                "event_type": event_type,
                "agent_name": self.name,
                "user_id": self.user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "payload": payload
            }
            await self.event_queue.put(event)

    @abstractmethod
    async def process(self, input_data: TInput) -> TOutput:
        """
        Process the input data and return the output.
        
        This is the main method that each agent must implement.
        
        Args:
            input_data: The input data for this agent
            
        Returns:
            The processed output data
        """
        pass

    async def process_async(self, input_data: TInput) -> TOutput:
        """
        Asynchronous version of the process method.
        Default implementation calls the synchronous version.
        Agents that need true async processing should override this.
        """
        return self.process(input_data)

    def execute(self, input_data: TInput) -> TOutput:
        """
        Execute the agent with error handling and metrics tracking.
        
        Args:
            input_data: The input data for this agent
            
        Returns:
            The processed output data
            
        Raises:
            Exception: If processing fails after error handling
        """
        metrics = AgentMetrics(start_time=datetime.now())
        
        try:
            logger.info(f"[{self.name}] Starting processing")
            logger.debug(f"[{self.name}] Input type: {type(input_data).__name__}")
            
            # Validate input
            if not isinstance(input_data, BaseModel):
                raise ValueError(f"Input must be a Pydantic model, got {type(input_data)}")
            
            # Process the data
            output = self.process(input_data)
            
            # Validate output
            if not isinstance(output, BaseModel):
                raise ValueError(f"Output must be a Pydantic model, got {type(output)}")
            
            # Update metrics
            metrics.end_time = datetime.now()
            metrics.processing_time_seconds = (metrics.end_time - metrics.start_time).total_seconds()
            metrics.success = True
            
            if self.llm_client:
                metrics.llm_usage = self.llm_client.get_usage_stats()
            
            logger.info(
                f"[{self.name}] Processing completed successfully in "
                f"{metrics.processing_time_seconds:.2f} seconds"
            )
            
            return output
            
        except ValidationError as e:
            error_msg = f"Validation error: {e}"
            logger.error(f"[{self.name}] {error_msg}")
            metrics.success = False
            metrics.error_message = error_msg
            raise
            
        except Exception as e:
            error_msg = f"Processing error: {str(e)}\n{traceback.format_exc()}"
            logger.error(f"[{self.name}] {error_msg}")
            metrics.success = False
            metrics.error_message = str(e)
            raise
            
        finally:
            if not metrics.end_time:
                metrics.end_time = datetime.now()
                metrics.processing_time_seconds = (metrics.end_time - metrics.start_time).total_seconds()
            
            self.metrics.append(metrics)

    async def execute_async(self, input_data: TInput) -> TOutput:
        """
        Asynchronously execute the agent with error handling and metrics tracking.
        """
        metrics = AgentMetrics(start_time=datetime.now())
        
        try:
            logger.info(f"[{self.name}] Starting async processing")
            logger.debug(f"[{self.name}] Input type: {type(input_data).__name__}")

            if not isinstance(input_data, BaseModel):
                raise ValueError(f"Input must be a Pydantic model, got {type(input_data)}")

            # Await the async process method
            output = await self.process_async(input_data)

            if not isinstance(output, BaseModel):
                raise ValueError(f"Output must be a Pydantic model, got {type(output)}")

            metrics.end_time = datetime.now()
            metrics.processing_time_seconds = (metrics.end_time - metrics.start_time).total_seconds()
            metrics.success = True

            if self.llm_client:
                metrics.llm_usage = self.llm_client.get_usage_stats()

            logger.info(
                f"[{self.name}] Async processing completed successfully in "
                f"{metrics.processing_time_seconds:.2f} seconds"
            )
            
            return output

        except ValidationError as e:
            error_msg = f"Validation error during async execution: {e}"
            logger.error(f"[{self.name}] {error_msg}")
            metrics.success = False
            metrics.error_message = error_msg
            raise

        except Exception as e:
            error_msg = f"Async processing error: {str(e)}\n{traceback.format_exc()}"
            logger.error(f"[{self.name}] {error_msg}")
            metrics.success = False
            metrics.error_message = str(e)
            raise

        finally:
            if not metrics.end_time:
                metrics.end_time = datetime.now()
                metrics.processing_time_seconds = (metrics.end_time - metrics.start_time).total_seconds()
            
            self.metrics.append(metrics)
    
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
        logger.debug(f"[{self.name}] Starting LLM generation with prompt length: {len(prompt)} chars")
        
        try:
            # Log prompt stats for debugging
            logger.debug(f"[{self.name}] LLM prompt preview: {prompt[:200]}...")
            
            response = self.llm_client.generate(prompt)
            
            # Log response stats
            response_length = len(response.content) if response.content else 0
            logger.info(f"[{self.name}] LLM generation successful - response length: {response_length} chars")
            logger.debug(f"[{self.name}] LLM response preview: {response.content[:200] if response.content else 'Empty response'}...")
            
            if not response.content:
                logger.warning(f"[{self.name}] LLM returned empty response")
                
            return response.content
        except Exception as e:
            logger.error(f"[{self.name}] LLM generation failed: {e}")
            logger.error(f"[{self.name}] Failed prompt length: {len(prompt)} chars")
            logger.debug(f"[{self.name}] Failed prompt preview: {prompt[:200]}...")
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
        logger.debug(f"[{self.name}] Starting JSON parsing for response length: {len(response)} chars")
        
        try:
            # Try to extract JSON from the response
            # LLMs often wrap JSON in markdown code blocks
            json_str = ""
            extraction_method = ""
            
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
                extraction_method = "markdown_json_block"
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
                extraction_method = "markdown_code_block"
            else:
                json_str = response.strip()
                extraction_method = "raw_response"
            
            logger.debug(f"[{self.name}] JSON extraction method: {extraction_method}, extracted length: {len(json_str)} chars")
            logger.debug(f"[{self.name}] Extracted JSON preview: {json_str[:200]}...")
            
            # Parse JSON
            data = json.loads(json_str)
            logger.info(f"[{self.name}] JSON parsing successful - parsed object type: {type(data)}")
            
            # Validate if expected type is provided
            if expected_type and hasattr(expected_type, 'model_validate'):
                logger.debug(f"[{self.name}] Validating against expected type: {expected_type.__name__}")
                validated_data = expected_type.model_validate(data)
                logger.info(f"[{self.name}] JSON validation successful")
                return validated_data
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"[{self.name}] Failed to parse JSON from LLM response: {e}")
            logger.error(f"[{self.name}] Extraction method used: {extraction_method}")
            logger.error(f"[{self.name}] JSON string that failed: {json_str[:500] if json_str else 'Empty'}...")
            logger.debug(f"[{self.name}] Full response: {response[:1000]}...")
            raise ValueError(f"Invalid JSON in LLM response: {e}")
        except ValidationError as e:
            logger.error(f"[{self.name}] JSON validation failed: {e}")
            logger.error(f"[{self.name}] Parsed data: {data}")
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