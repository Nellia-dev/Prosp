"""
Agent Registry & Discovery System for MCP Server
Enables MCP server to discover, categorize, and manage all prospect agents
"""

import os
import sys
import importlib
import inspect
from typing import Dict, List, Type, Optional, Any
from enum import Enum
from dataclasses import dataclass
from loguru import logger

# Add prospect directory to path for imports
prospect_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if prospect_root not in sys.path:
    sys.path.insert(0, prospect_root)

from agents.base_agent import BaseAgent

class AgentCategory(str, Enum):
    """Agent categories for pipeline organization"""
    INITIAL_PROCESSING = "initial_processing"
    ORCHESTRATOR = "orchestrator"
    SPECIALIZED = "specialized"
    ALTERNATIVE = "alternative"

@dataclass
class AgentInfo:
    """Information about a registered agent"""
    name: str
    category: AgentCategory
    class_ref: Type[BaseAgent]
    module_path: str
    input_type: Type
    output_type: Type
    description: str
    dependencies: List[str]
    execution_order: int

class AgentRegistry:
    """Registry for discovering and managing prospect agents"""
    
    def __init__(self):
        self.agents: Dict[str, AgentInfo] = {}
        self.categories: Dict[AgentCategory, List[str]] = {
            category: [] for category in AgentCategory
        }
        self.pipeline_order: List[str] = []
        self._discover_agents()
        self._categorize_agents()
        self._build_pipeline_order()
        
        logger.info(f"Agent Registry initialized with {len(self.agents)} agents")
        
    def _discover_agents(self) -> None:
        """Discover all available agents in the prospect/agents directory"""
        agents_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agents')
        
        # Agent module mapping
        agent_modules = {
            # Initial Processing Agents
            'lead_intake_agent': 'agents.lead_intake_agent',
            'lead_analysis_agent': 'agents.lead_analysis_agent',
            
            # Main Orchestrator
            'enhanced_lead_processor': 'agents.enhanced_lead_processor',
            
            # Specialized Agents
            'tavily_enrichment_agent': 'agents.tavily_enrichment_agent',
            'contact_extraction_agent': 'agents.contact_extraction_agent',
            'pain_point_deepening_agent': 'agents.pain_point_deepening_agent',
            'lead_qualification_agent': 'agents.lead_qualification_agent',
            'competitor_identification_agent': 'agents.competitor_identification_agent',
            'strategic_question_generation_agent': 'agents.strategic_question_generation_agent',
            'buying_trigger_identification_agent': 'agents.buying_trigger_identification_agent',
            'tot_strategy_generation_agent': 'agents.tot_strategy_generation_agent',
            'tot_strategy_evaluation_agent': 'agents.tot_strategy_evaluation_agent',
            'tot_action_plan_synthesis_agent': 'agents.tot_action_plan_synthesis_agent',
            'detailed_approach_plan_agent': 'agents.detailed_approach_plan_agent',
            'objection_handling_agent': 'agents.objection_handling_agent',
            'value_proposition_customization_agent': 'agents.value_proposition_customization_agent',
            'b2b_personalized_message_agent': 'agents.b2b_personalized_message_agent',
            'internal_briefing_summary_agent': 'agents.internal_briefing_summary_agent',
            
            # Alternative/Modular Agents
            'approach_strategy_agent': 'agents.approach_strategy_agent',
            'b2b_persona_creation_agent': 'agents.b2b_persona_creation_agent',
            'message_crafting_agent': 'agents.message_crafting_agent',
            'persona_creation_agent': 'agents.persona_creation_agent',
            'lead_analysis_generation_agent': 'agents.lead_analysis_generation_agent'
        }
        
        for agent_name, module_path in agent_modules.items():
            try:
                self._register_agent_from_module(agent_name, module_path)
            except Exception as e:
                logger.warning(f"Failed to register agent {agent_name}: {e}")
                
    def _register_agent_from_module(self, agent_name: str, module_path: str) -> None:
        """Register an agent from its module"""
        try:
            module = importlib.import_module(module_path)
            
            # Find the agent class in the module
            agent_class = None
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BaseAgent) and 
                    obj != BaseAgent and
                    not obj.__name__ == 'BaseAgent'):
                    agent_class = obj
                    break
                    
            if not agent_class:
                logger.warning(f"No agent class found in module {module_path}")
                return
                
            # Extract input/output types from agent class
            input_type, output_type = self._extract_agent_types(agent_class)
            
            # Get agent description
            description = agent_class.__doc__ or f"Agent: {agent_class.__name__}"
            
            # Create agent info
            agent_info = AgentInfo(
                name=agent_name,
                category=self._determine_agent_category(agent_name),
                class_ref=agent_class,
                module_path=module_path,
                input_type=input_type,
                output_type=output_type,
                description=description.strip(),
                dependencies=self._determine_agent_dependencies(agent_name),
                execution_order=self._determine_execution_order(agent_name)
            )
            
            self.agents[agent_name] = agent_info
            logger.debug(f"Registered agent: {agent_name} ({agent_info.category})")
            
        except Exception as e:
            logger.error(f"Failed to register agent {agent_name} from {module_path}: {e}")
            raise
            
    def _extract_agent_types(self, agent_class: Type[BaseAgent]) -> tuple:
        """Extract input and output types from agent class"""
        try:
            # Get the generic types from BaseAgent inheritance
            if hasattr(agent_class, '__orig_bases__'):
                for base in agent_class.__orig_bases__:
                    if hasattr(base, '__args__') and len(base.__args__) == 2:
                        return base.__args__[0], base.__args__[1]
            
            # Fallback to Any if types can't be determined
            return Any, Any
            
        except Exception as e:
            logger.warning(f"Could not extract types for {agent_class.__name__}: {e}")
            return Any, Any
            
    def _determine_agent_category(self, agent_name: str) -> AgentCategory:
        """Determine the category of an agent based on its name"""
        if agent_name in ['lead_intake_agent', 'lead_analysis_agent']:
            return AgentCategory.INITIAL_PROCESSING
        elif agent_name == 'enhanced_lead_processor':
            return AgentCategory.ORCHESTRATOR
        elif agent_name in [
            'tavily_enrichment_agent', 'contact_extraction_agent', 'pain_point_deepening_agent',
            'lead_qualification_agent', 'competitor_identification_agent', 'strategic_question_generation_agent',
            'buying_trigger_identification_agent', 'tot_strategy_generation_agent', 'tot_strategy_evaluation_agent',
            'tot_action_plan_synthesis_agent', 'detailed_approach_plan_agent', 'objection_handling_agent',
            'value_proposition_customization_agent', 'b2b_personalized_message_agent', 'internal_briefing_summary_agent'
        ]:
            return AgentCategory.SPECIALIZED
        else:
            return AgentCategory.ALTERNATIVE
            
    def _determine_agent_dependencies(self, agent_name: str) -> List[str]:
        """Determine agent dependencies for pipeline execution"""
        dependencies_map = {
            # Initial processing has no dependencies
            'lead_intake_agent': [],
            'lead_analysis_agent': ['lead_intake_agent'],
            
            # Orchestrator depends on initial processing
            'enhanced_lead_processor': ['lead_analysis_agent'],
            
            # Specialized agents typically depend on analysis
            'tavily_enrichment_agent': ['lead_analysis_agent'],
            'contact_extraction_agent': ['lead_analysis_agent'],
            'pain_point_deepening_agent': ['lead_analysis_agent'],
            'lead_qualification_agent': ['pain_point_deepening_agent'],
            'competitor_identification_agent': ['lead_analysis_agent'],
            'strategic_question_generation_agent': ['pain_point_deepening_agent'],
            'buying_trigger_identification_agent': ['tavily_enrichment_agent'],
            'tot_strategy_generation_agent': ['lead_qualification_agent'],
            'tot_strategy_evaluation_agent': ['tot_strategy_generation_agent'],
            'tot_action_plan_synthesis_agent': ['tot_strategy_evaluation_agent'],
            'detailed_approach_plan_agent': ['tot_action_plan_synthesis_agent'],
            'objection_handling_agent': ['detailed_approach_plan_agent'],
            'value_proposition_customization_agent': ['buying_trigger_identification_agent'],
            'b2b_personalized_message_agent': ['value_proposition_customization_agent'],
            'internal_briefing_summary_agent': ['b2b_personalized_message_agent'],
            
            # Alternative agents
            'approach_strategy_agent': ['lead_analysis_agent'],
            'b2b_persona_creation_agent': ['lead_analysis_agent'],
            'message_crafting_agent': ['approach_strategy_agent'],
            'persona_creation_agent': ['lead_analysis_agent'],
            'lead_analysis_generation_agent': ['lead_intake_agent']
        }
        
        return dependencies_map.get(agent_name, [])
        
    def _determine_execution_order(self, agent_name: str) -> int:
        """Determine execution order for agent in pipeline"""
        order_map = {
            # Initial processing (0-10)
            'lead_intake_agent': 1,
            'lead_analysis_agent': 2,
            
            # Orchestrator (10-20)
            'enhanced_lead_processor': 15,
            
            # Specialized agents (20-100)
            'tavily_enrichment_agent': 21,
            'contact_extraction_agent': 22,
            'pain_point_deepening_agent': 25,
            'lead_qualification_agent': 30,
            'competitor_identification_agent': 26,
            'strategic_question_generation_agent': 31,
            'buying_trigger_identification_agent': 27,
            'tot_strategy_generation_agent': 35,
            'tot_strategy_evaluation_agent': 36,
            'tot_action_plan_synthesis_agent': 37,
            'detailed_approach_plan_agent': 40,
            'objection_handling_agent': 45,
            'value_proposition_customization_agent': 32,
            'b2b_personalized_message_agent': 50,
            'internal_briefing_summary_agent': 55,
            
            # Alternative agents (100+)
            'approach_strategy_agent': 101,
            'b2b_persona_creation_agent': 102,
            'message_crafting_agent': 103,
            'persona_creation_agent': 104,
            'lead_analysis_generation_agent': 105
        }
        
        return order_map.get(agent_name, 999)
        
    def _categorize_agents(self) -> None:
        """Categorize agents by their categories"""
        for agent_name, agent_info in self.agents.items():
            self.categories[agent_info.category].append(agent_name)
            
    def _build_pipeline_order(self) -> None:
        """Build optimal execution order for agent pipeline"""
        # Sort by execution order
        sorted_agents = sorted(
            self.agents.items(),
            key=lambda x: x[1].execution_order
        )
        self.pipeline_order = [agent_name for agent_name, _ in sorted_agents]
        
    # Public API Methods
    
    def get_agent_by_name(self, name: str) -> Optional[AgentInfo]:
        """Get agent information by name"""
        return self.agents.get(name)
        
    def get_agent_class(self, name: str) -> Optional[Type[BaseAgent]]:
        """Get agent class by name"""
        agent_info = self.get_agent_by_name(name)
        return agent_info.class_ref if agent_info else None
        
    def get_agents_by_category(self, category: AgentCategory) -> List[AgentInfo]:
        """Get agents by category"""
        agent_names = self.categories.get(category, [])
        return [self.agents[name] for name in agent_names if name in self.agents]
        
    def get_all_agents(self) -> Dict[str, AgentInfo]:
        """Get all registered agents"""
        return self.agents.copy()
        
    def get_pipeline_order(self) -> List[str]:
        """Get optimal agent execution order"""
        return self.pipeline_order.copy()
        
    def validate_agent_pipeline(self, pipeline: List[str]) -> tuple[bool, List[str]]:
        """Validate agent execution pipeline"""
        errors = []
        
        for agent_name in pipeline:
            if agent_name not in self.agents:
                errors.append(f"Unknown agent: {agent_name}")
                continue
                
            agent_info = self.agents[agent_name]
            for dependency in agent_info.dependencies:
                if dependency not in pipeline:
                    errors.append(f"Agent {agent_name} requires dependency {dependency}")
                elif pipeline.index(dependency) > pipeline.index(agent_name):
                    errors.append(f"Agent {agent_name} dependency {dependency} must execute before it")
                    
        return len(errors) == 0, errors
        
    def get_agent_dependencies(self, agent_name: str) -> List[str]:
        """Get dependencies for a specific agent"""
        agent_info = self.get_agent_by_name(agent_name)
        return agent_info.dependencies if agent_info else []
        
    def get_optimal_pipeline_for_goal(self, goal: str = "comprehensive") -> List[str]:
        """Get optimal pipeline for a specific processing goal"""
        if goal == "comprehensive":
            # Full enhanced processing pipeline
            return [
                'lead_intake_agent',
                'lead_analysis_agent',
                'enhanced_lead_processor'
            ]
        elif goal == "basic":
            # Basic processing only
            return [
                'lead_intake_agent',
                'lead_analysis_agent'
            ]
        elif goal == "specialized":
            # Specialized processing without orchestrator
            specialized_agents = self.get_agents_by_category(AgentCategory.SPECIALIZED)
            return [agent.name for agent in specialized_agents]
        else:
            return self.pipeline_order
            
    def get_agent_summary(self) -> Dict[str, Any]:
        """Get summary of all registered agents"""
        summary = {
            "total_agents": len(self.agents),
            "categories": {},
            "pipeline_length": len(self.pipeline_order),
            "agents_by_category": {}
        }
        
        for category in AgentCategory:
            agents_in_category = self.get_agents_by_category(category)
            summary["categories"][category.value] = len(agents_in_category)
            summary["agents_by_category"][category.value] = [
                {
                    "name": agent.name,
                    "description": agent.description,
                    "execution_order": agent.execution_order,
                    "dependencies": agent.dependencies
                }
                for agent in agents_in_category
            ]
            
        return summary

# Global registry instance
_agent_registry: Optional[AgentRegistry] = None

def get_agent_registry() -> AgentRegistry:
    """Get the global agent registry instance"""
    global _agent_registry
    if _agent_registry is None:
        _agent_registry = AgentRegistry()
    return _agent_registry

def reset_agent_registry() -> None:
    """Reset the global agent registry (for testing)"""
    global _agent_registry
    _agent_registry = None
