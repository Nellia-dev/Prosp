"""
Persona Driven Lead Processor Agent
Orchestrates a pipeline focused on deep persona creation and tailored strategy.
"""

from typing import Optional

from agents.base_agent import BaseAgent
from data_models.lead_structures import (
    AnalyzedLead,
    FinalProspectPackage,
    LeadWithPersona,
    LeadWithStrategy
)
from core_logic.llm_client import LLMClientBase

# Import the agents to be orchestrated
from .persona_creation_agent import PersonaCreationAgent
from .approach_strategy_agent import ApproachStrategyAgent
from .message_crafting_agent import MessageCraftingAgent


class PersonaDrivenLeadProcessor(BaseAgent[AnalyzedLead, FinalProspectPackage]):
    """
    Orchestrates a lead processing pipeline that prioritizes deep persona
    creation to drive strategy and messaging.
    """
    def __init__(
        self,
        name: str = "PersonaDrivenLeadProcessor",
        description: str = "Processes leads with a persona-first approach.",
        llm_client: Optional[LLMClientBase] = None,
        product_service_context: str = "",
        **kwargs
    ):
        super().__init__(
            name=name,
            description=description,
            llm_client=llm_client,
            config={"product_service_context": product_service_context},
            **kwargs
        )
        self.product_service_context = product_service_context

        # Initialize the orchestrated agents
        # Ensure these agents are correctly initialized with necessary parameters
        self.persona_creation_agent = PersonaCreationAgent(
            llm_client=self.llm_client
        )
        self.approach_strategy_agent = ApproachStrategyAgent(
            llm_client=self.llm_client,
            product_service_context=self.product_service_context
        )
        self.message_crafting_agent = MessageCraftingAgent(
            llm_client=self.llm_client
        )
        self.logger.info(f"Initialized {self.name} with product context: '{product_service_context[:50]}...'")

    async def process_async(self, analyzed_lead: AnalyzedLead) -> FinalProspectPackage:
        """
        Asynchronously processes the lead through a persona-driven pipeline.
        """
        self.logger.info(f"[{self.name}] Starting persona-driven processing for lead: {analyzed_lead.validated_lead.site_data.url}")

        # Step 1: Create structured persona
        self.logger.info(f"[{self.name}] Step 1: Creating persona...")
        lead_with_persona: LeadWithPersona = await self.persona_creation_agent.execute_async(analyzed_lead)
        self.logger.info(f"[{self.name}] Persona created: {lead_with_persona.persona.fictional_name if lead_with_persona.persona else 'N/A'}")

        # Step 2: Generate strategy based on persona
        self.logger.info(f"[{self.name}] Step 2: Generating approach strategy...")
        lead_with_strategy: LeadWithStrategy = await self.approach_strategy_agent.execute_async(lead_with_persona)
        self.logger.info(f"[{self.name}] Strategy generated: Primary channel {lead_with_strategy.strategy.primary_channel.value if lead_with_strategy.strategy else 'N/A'}")

        # Step 3: Craft personalized message
        self.logger.info(f"[{self.name}] Step 3: Crafting personalized message...")
        final_package: FinalProspectPackage = await self.message_crafting_agent.execute_async(lead_with_strategy)
        self.logger.info(f"[{self.name}] Message crafted for channel: {final_package.personalized_message.channel.value if final_package.personalized_message else 'N/A'}")

        self.logger.info(f"[{self.name}] Persona-driven processing completed for lead: {analyzed_lead.validated_lead.site_data.url}")
        return final_package

    def process(self, input_data: AnalyzedLead) -> FinalProspectPackage:
        """
        Synchronous wrapper for the async process method.
        Consider using asyncio.run() if calling from a sync context.
        """
        self.logger.warning(f"[{self.name}] process() called synchronously. Consider using execute_async for non-blocking operations.")
        import asyncio
        return asyncio.run(self.process_async(input_data))
