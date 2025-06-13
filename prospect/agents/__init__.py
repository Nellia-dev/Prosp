"""
Agents for the Prospecting Pipeline
"""

# Base agent
from .base_agent import BaseAgent, AgentMetrics

# Core processing agents
from .lead_intake_agent import LeadIntakeAgent
from .lead_analysis_agent import LeadAnalysisAgent
from .enhanced_lead_processor import EnhancedLeadProcessor

# Specialized agents (used by EnhancedLeadProcessor or for specific tasks)
from .tavily_enrichment_agent import TavilyEnrichmentAgent
from .contact_extraction_agent import ContactExtractionAgent
from .pain_point_deepening_agent import PainPointDeepeningAgent
from .lead_qualification_agent import LeadQualificationAgent
from .competitor_identification_agent import CompetitorIdentificationAgent
from .strategic_question_generation_agent import StrategicQuestionGenerationAgent
from .buying_trigger_identification_agent import BuyingTriggerIdentificationAgent
from .tot_strategy_generation_agent import ToTStrategyGenerationAgent
from .tot_strategy_evaluation_agent import ToTStrategyEvaluationAgent
from .tot_action_plan_synthesis_agent import ToTActionPlanSynthesisAgent
from .detailed_approach_plan_agent import DetailedApproachPlanAgent
from .objection_handling_agent import ObjectionHandlingAgent
from .value_proposition_customization_agent import ValuePropositionCustomizationAgent
from .b2b_personalized_message_agent import B2BPersonalizedMessageAgent
from .internal_briefing_summary_agent import InternalBriefingSummaryAgent

# Alternative workflow agents (Phase 1 Integration)
from .persona_creation_agent import PersonaCreationAgent
from .approach_strategy_agent import ApproachStrategyAgent
from .message_crafting_agent import MessageCraftingAgent
from .persona_driven_lead_processor import PersonaDrivenLeadProcessor

# Other specialized agents (for future integration phases)
from .b2b_persona_creation_agent import B2BPersonaCreationAgent
from .lead_analysis_generation_agent import LeadAnalysisGenerationAgent

# Hybrid Orchestrator (Phase 3 Integration)
# Note: This might logically sit outside 'agents' but is related to their orchestration.
# For now, placing it here for discoverability as per the plan.
# Consider moving to a higher-level 'orchestrators' module if structure evolves.
# from prospect.hybrid_pipeline_orchestrator import HybridPipelineOrchestrator # Path needs to be correct


__all__ = [
    "BaseAgent",
    "AgentMetrics",
    "LeadIntakeAgent",
    "LeadAnalysisAgent",
    "EnhancedLeadProcessor",
    "TavilyEnrichmentAgent",
    "ContactExtractionAgent",
    "PainPointDeepeningAgent",
    "LeadQualificationAgent",
    "CompetitorIdentificationAgent",
    "StrategicQuestionGenerationAgent",
    "BuyingTriggerIdentificationAgent",
    "ToTStrategyGenerationAgent",
    "ToTStrategyEvaluationAgent",
    "ToTActionPlanSynthesisAgent",
    "DetailedApproachPlanAgent",
    "ObjectionHandlingAgent",
    "ValuePropositionCustomizationAgent",
    "B2BPersonalizedMessageAgent",
    "InternalBriefingSummaryAgent",
    "PersonaCreationAgent",
    "ApproachStrategyAgent",
    "MessageCraftingAgent",
    "PersonaDrivenLeadProcessor",
    "B2BPersonaCreationAgent",
    "LeadAnalysisGenerationAgent",
    # "HybridPipelineOrchestrator", # Add when its import path is finalized
]
