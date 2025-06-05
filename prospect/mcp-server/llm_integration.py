"""
LLM Client Integration for MCP Server
Connects MCP server to prospect's LLM infrastructure and agent execution
"""

import os
import sys
import asyncio
from typing import Type, Optional, Any, Dict, List
from loguru import logger
import traceback

# Add prospect directory to path for imports
prospect_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if prospect_root not in sys.path:
    sys.path.insert(0, prospect_root)

from core_logic.llm_client import LLMClientBase, LLMClientFactory
from agents.base_agent import BaseAgent, AgentMetrics
from agent_registry import get_agent_registry, AgentRegistry, AgentInfo

class McpLlmService:
    """Service for integrating LLM client with MCP server agent execution"""
    
    def __init__(self):
        self.llm_client: Optional[LLMClientBase] = None
        self.agent_registry: AgentRegistry = get_agent_registry()
        self._initialized_agents: Dict[str, BaseAgent] = {}
        self._agent_instances: Dict[str, BaseAgent] = {}
        
        # Initialize LLM client
        self._initialize_llm_client()
        logger.info("MCP LLM Service initialized")
        
    def _initialize_llm_client(self) -> None:
        """Initialize the LLM client"""
        try:
            self.llm_client = LLMClientFactory.create_from_env()
            logger.info("LLM client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            raise
            
    def initialize_agent(self, agent_name: str, **kwargs) -> Optional[BaseAgent]:
        """Initialize an agent with LLM client and configuration"""
        try:
            # Check if agent is already initialized
            if agent_name in self._agent_instances:
                return self._agent_instances[agent_name]
                
            # Get agent class from registry
            agent_info = self.agent_registry.get_agent_by_name(agent_name)
            if not agent_info:
                logger.error(f"Agent {agent_name} not found in registry")
                return None
                
            agent_class = agent_info.class_ref
            
            # Initialize agent with LLM client
            agent_instance = self._create_agent_instance(agent_class, **kwargs)
            
            if agent_instance:
                self._agent_instances[agent_name] = agent_instance
                logger.debug(f"Initialized agent: {agent_name}")
                
            return agent_instance
            
        except Exception as e:
            logger.error(f"Failed to initialize agent {agent_name}: {e}")
            return None
            
    def _create_agent_instance(self, agent_class: Type[BaseAgent], **kwargs) -> Optional[BaseAgent]:
        """Create an instance of an agent with proper parameters"""
        try:
            # Get agent constructor parameters
            import inspect
            sig = inspect.signature(agent_class.__init__)
            
            # Build parameters for agent initialization
            init_params = {"llm_client": self.llm_client}
            
            # Add common parameters if present in constructor
            common_params = {
                "temperature": kwargs.get("temperature", 0.7),
                "product_service_context": kwargs.get("product_service_context", ""),
                "competitors_list": kwargs.get("competitors_list", ""),
                "tavily_api_key": kwargs.get("tavily_api_key") or os.getenv("TAVILY_API_KEY")
            }
            
            # Only add parameters that are accepted by the agent
            for param_name, param_value in common_params.items():
                if param_name in sig.parameters:
                    init_params[param_name] = param_value
                    
            # Add any additional kwargs that match constructor parameters
            for param_name, param_value in kwargs.items():
                if param_name in sig.parameters and param_name not in init_params:
                    init_params[param_name] = param_value
                    
            # Create agent instance
            return agent_class(**init_params)
            
        except Exception as e:
            logger.error(f"Failed to create agent instance for {agent_class.__name__}: {e}")
            return None
            
    def execute_agent(self, agent: BaseAgent, input_data: Any) -> Dict[str, Any]:
        """Execute an agent with proper error handling and metrics collection"""
        try:
            import time
            start_time = time.time()
            
            # Execute the agent
            result = agent.execute(input_data)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Get agent metrics if available
            metrics = self._get_agent_metrics(agent)
            
            return {
                "success": True,
                "result": result,
                "processing_time_seconds": processing_time,
                "metrics": metrics,
                "agent_name": agent.agent_name if hasattr(agent, 'agent_name') else agent.__class__.__name__,
                "error_message": None
            }
            
        except Exception as e:
            logger.error(f"Agent execution failed: {e}\n{traceback.format_exc()}")
            return {
                "success": False,
                "result": None,
                "processing_time_seconds": 0,
                "metrics": None,
                "agent_name": agent.__class__.__name__,
                "error_message": str(e)
            }
            
    def execute_agent_by_name(self, agent_name: str, input_data: Any, **kwargs) -> Dict[str, Any]:
        """Execute an agent by name with initialization if needed"""
        try:
            # Initialize agent if not already done
            agent = self.initialize_agent(agent_name, **kwargs)
            if not agent:
                return {
                    "success": False,
                    "result": None,
                    "processing_time_seconds": 0,
                    "metrics": None,
                    "agent_name": agent_name,
                    "error_message": f"Failed to initialize agent {agent_name}"
                }
                
            # Execute the agent
            return self.execute_agent(agent, input_data)
            
        except Exception as e:
            logger.error(f"Failed to execute agent {agent_name}: {e}")
            return {
                "success": False,
                "result": None,
                "processing_time_seconds": 0,
                "metrics": None,
                "agent_name": agent_name,
                "error_message": str(e)
            }
            
    async def execute_agent_pipeline(self, pipeline: List[str], initial_data: Any, **kwargs) -> Dict[str, Any]:
        """Execute a pipeline of agents sequentially"""
        try:
            # Validate pipeline
            is_valid, errors = self.agent_registry.validate_agent_pipeline(pipeline)
            if not is_valid:
                return {
                    "success": False,
                    "pipeline_results": [],
                    "final_result": None,
                    "total_processing_time": 0,
                    "error_message": f"Invalid pipeline: {'; '.join(errors)}"
                }
                
            pipeline_results = []
            current_data = initial_data
            total_time = 0
            
            for agent_name in pipeline:
                logger.info(f"Executing agent: {agent_name}")
                
                # Execute agent
                result = self.execute_agent_by_name(agent_name, current_data, **kwargs)
                pipeline_results.append({
                    "agent_name": agent_name,
                    "success": result["success"],
                    "processing_time": result["processing_time_seconds"],
                    "metrics": result["metrics"],
                    "error_message": result["error_message"]
                })
                
                total_time += result["processing_time_seconds"]
                
                # If agent failed, stop pipeline
                if not result["success"]:
                    return {
                        "success": False,
                        "pipeline_results": pipeline_results,
                        "final_result": None,
                        "total_processing_time": total_time,
                        "error_message": f"Pipeline failed at agent {agent_name}: {result['error_message']}"
                    }
                    
                # Use agent output as input for next agent
                current_data = result["result"]
                
            return {
                "success": True,
                "pipeline_results": pipeline_results,
                "final_result": current_data,
                "total_processing_time": total_time,
                "error_message": None
            }
            
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            return {
                "success": False,
                "pipeline_results": [],
                "final_result": None,
                "total_processing_time": 0,
                "error_message": str(e)
            }
            
    def execute_enhanced_lead_processing(self, analyzed_lead: Any, **kwargs) -> Dict[str, Any]:
        """Execute the enhanced lead processor specifically"""
        try:
            # Initialize enhanced lead processor
            agent = self.initialize_agent("enhanced_lead_processor", **kwargs)
            if not agent:
                return {
                    "success": False,
                    "result": None,
                    "processing_time_seconds": 0,
                    "error_message": "Failed to initialize enhanced_lead_processor"
                }
                
            # Execute enhanced processing
            return self.execute_agent(agent, analyzed_lead)
            
        except Exception as e:
            logger.error(f"Enhanced lead processing failed: {e}")
            return {
                "success": False,
                "result": None,
                "processing_time_seconds": 0,
                "error_message": str(e)
            }
            
    def _get_agent_metrics(self, agent: BaseAgent) -> Optional[Dict[str, Any]]:
        """Extract metrics from an agent if available"""
        try:
            if hasattr(agent, 'get_metrics'):
                metrics = agent.get_metrics()
                if isinstance(metrics, AgentMetrics):
                    return {
                        "processing_time_seconds": metrics.processing_time_seconds,
                        "llm_usage": {
                            "total_tokens": metrics.llm_usage.total_tokens if metrics.llm_usage else 0,
                            "prompt_tokens": metrics.llm_usage.prompt_tokens if metrics.llm_usage else 0,
                            "completion_tokens": metrics.llm_usage.completion_tokens if metrics.llm_usage else 0
                        } if metrics.llm_usage else None,
                        "success_rate": metrics.success_rate,
                        "error_count": metrics.error_count,
                        "retry_count": metrics.retry_count
                    }
                return metrics
            return None
        except Exception as e:
            logger.warning(f"Failed to get agent metrics: {e}")
            return None
            
    def get_agent_status(self, agent_name: str) -> Dict[str, Any]:
        """Get status of a specific agent"""
        try:
            agent_info = self.agent_registry.get_agent_by_name(agent_name)
            if not agent_info:
                return {
                    "agent_name": agent_name,
                    "status": "unknown",
                    "initialized": False,
                    "error": "Agent not found in registry"
                }
                
            is_initialized = agent_name in self._agent_instances
            agent_instance = self._agent_instances.get(agent_name)
            
            status = {
                "agent_name": agent_name,
                "category": agent_info.category.value,
                "status": "initialized" if is_initialized else "not_initialized",
                "initialized": is_initialized,
                "description": agent_info.description,
                "dependencies": agent_info.dependencies,
                "execution_order": agent_info.execution_order
            }
            
            # Add runtime status if agent is initialized
            if agent_instance:
                try:
                    # Check if agent has a health check method
                    if hasattr(agent_instance, 'health_check'):
                        health = agent_instance.health_check()
                        status["health"] = health
                    else:
                        status["health"] = "healthy"
                        
                    # Add recent metrics if available
                    metrics = self._get_agent_metrics(agent_instance)
                    if metrics:
                        status["recent_metrics"] = metrics
                        
                except Exception as e:
                    status["health"] = f"error: {str(e)}"
                    
            return status
            
        except Exception as e:
            logger.error(f"Failed to get agent status for {agent_name}: {e}")
            return {
                "agent_name": agent_name,
                "status": "error",
                "initialized": False,
                "error": str(e)
            }
            
    def get_all_agent_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all registered agents"""
        statuses = {}
        for agent_name in self.agent_registry.get_all_agents().keys():
            statuses[agent_name] = self.get_agent_status(agent_name)
        return statuses
        
    def shutdown_agent(self, agent_name: str) -> bool:
        """Shutdown and cleanup an agent"""
        try:
            if agent_name in self._agent_instances:
                agent = self._agent_instances[agent_name]
                
                # Call cleanup if available
                if hasattr(agent, 'cleanup'):
                    agent.cleanup()
                    
                del self._agent_instances[agent_name]
                logger.info(f"Agent {agent_name} shutdown successfully")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to shutdown agent {agent_name}: {e}")
            return False
            
    def shutdown_all_agents(self) -> None:
        """Shutdown all initialized agents"""
        agent_names = list(self._agent_instances.keys())
        for agent_name in agent_names:
            self.shutdown_agent(agent_name)
            
    def reinitialize_agent(self, agent_name: str, **kwargs) -> bool:
        """Reinitialize an agent with new parameters"""
        try:
            # Shutdown existing instance if present
            self.shutdown_agent(agent_name)
            
            # Reinitialize with new parameters
            agent = self.initialize_agent(agent_name, **kwargs)
            return agent is not None
        except Exception as e:
            logger.error(f"Failed to reinitialize agent {agent_name}: {e}")
            return False
            
    def get_service_status(self) -> Dict[str, Any]:
        """Get overall service status"""
        try:
            total_agents = len(self.agent_registry.get_all_agents())
            initialized_agents = len(self._agent_instances)
            
            return {
                "service_status": "healthy" if self.llm_client else "degraded",
                "llm_client_status": "connected" if self.llm_client else "disconnected",
                "total_registered_agents": total_agents,
                "initialized_agents": initialized_agents,
                "initialization_rate": (initialized_agents / total_agents * 100) if total_agents > 0 else 0,
                "available_categories": [cat.value for cat in self.agent_registry.categories.keys()],
                "agent_registry_status": "loaded"
            }
        except Exception as e:
            logger.error(f"Failed to get service status: {e}")
            return {
                "service_status": "error",
                "error": str(e)
            }

# Global service instance
_llm_service: Optional[McpLlmService] = None

def get_llm_service() -> McpLlmService:
    """Get the global LLM service instance"""
    global _llm_service
    if _llm_service is None:
        _llm_service = McpLlmService()
    return _llm_service

def reset_llm_service() -> None:
    """Reset the global LLM service (for testing)"""
    global _llm_service
    if _llm_service:
        _llm_service.shutdown_all_agents()
    _llm_service = None
