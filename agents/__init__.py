# agents/__init__.py
from .base_agent import BaseAgent, AgentMetrics, LLMProvider
# Assuming no other agents currently exist based on the empty file,
# otherwise, other existing agent imports would be here.

from .content_marketing_agent import ContentMarketingAgent
from .campaign_content_optimizer_agent import CampaignContentOptimizerAgent # Added new agent

__all__ = [
    "BaseAgent",
    "AgentMetrics",
    "LLMProvider",
    # Assuming no other agents, otherwise, they would be listed here.
    "CampaignContentOptimizerAgent", # Added new agent
    "ContentMarketingAgent",
]
