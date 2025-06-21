import asyncio
import json
import textwrap
from typing import List, Optional

from loguru import logger
from pydantic import BaseModel, Field

from .base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase
from data_models.lead_structures import ExternalIntelligence

# Input and Output Models
class B2BPersonaCreationInput(BaseModel):
    company_name: str
    company_description: str
    product_service_description: str
    external_intelligence: ExternalIntelligence

class Persona(BaseModel):
    name: str = Field(description="A fictional name and title for the persona.")
    title: str = Field(description="The job title for the persona.")
    description: str = Field(description="A detailed description of the persona, including responsibilities, challenges, and how the product can help.")

class B2BPersonaCreationOutput(BaseModel):
    personas: List[Persona] = Field(default_factory=list, description="A list of generated B2B personas.")
    error_message: Optional[str] = Field(default=None)

# Agent Definition
class B2BPersonaCreationAgent(BaseAgent[B2BPersonaCreationInput, B2BPersonaCreationOutput]):
    """
    Agent specialized in creating B2B buyer personas using LLM.
    """

    def __init__(
        self,
        llm_client: LLMClientBase,
        name: str = "B2B Persona Creation Agent",
        description: str = "Generates detailed B2B buyer personas based on company data and external intelligence.",
        event_queue: Optional[asyncio.Queue] = None,
        user_id: Optional[str] = None,
    ):
        super().__init__(llm_client, name, description, event_queue, user_id)

    async def process(self, lead_id: str, input_data: B2BPersonaCreationInput) -> B2BPersonaCreationOutput:
        """
        Generates B2B personas based on company information and external intelligence.
        """
        await self._emit_event("agent_start", {"agent_name": self.name, "lead_id": lead_id})
        logger.info(f"Starting B2B Persona Creation for {input_data.company_name} (Lead ID: {lead_id})")

        system_prompt = textwrap.dedent(
            """
            You are an expert in B2B marketing and sales strategy. Your task is to create detailed buyer personas for a given company based on its description, product/service, and external intelligence.

            Generate 3 detailed B2B buyer personas.

            For each persona, provide:
            - A name and title.
            - A detailed description including their key responsibilities, objectives, main challenges, pain points, how the company's product/service can help them, and the best channels to reach them.

            Output the result as a JSON array of objects, where each object represents a persona and has the keys "name", "title", and "description".
            Do not include any other text or explanations outside of the JSON array.
            """
        )

        user_prompt = textwrap.dedent(
            f"""
            Company Name: {input_data.company_name}
            Company Description: {input_data.company_description}
            Product/Service Description: {input_data.product_service_description}

            External Intelligence:
            {input_data.external_intelligence.tavily_enrichment}

            Based on this information, generate 3 detailed B2B buyer personas in the specified JSON format.
            """
        )

        response_text = await self.llm_client.generate(system_prompt, user_prompt)

        personas = []
        error_message = None
        try:
            # The LLM might return a markdown code block ```json ... ```, so we strip it.
            if response_text.strip().startswith("```json"):
                response_text = response_text.strip()[7:-3].strip()

            personas_data = json.loads(response_text)
            personas = [Persona(**p) for p in personas_data]
            logger.info(f"Successfully parsed {len(personas)} personas for Lead ID {lead_id}.")
        except (json.JSONDecodeError, TypeError, AttributeError) as e:
            error_message = f"Failed to parse B2B Personas from LLM response: {e}"
            logger.error(f"{error_message} for Lead ID {lead_id}")
            logger.debug(f"LLM Response Text: {response_text}")
            # We will return an empty list of personas, which the downstream agents should handle.

        output = B2BPersonaCreationOutput(personas=personas, error_message=error_message)

        logger.info(f"Finished B2B Persona Creation for {input_data.company_name} (Lead ID: {lead_id})")
        await self._emit_event("agent_end", {"agent_name": self.name, "lead_id": lead_id, "response": output.model_dump()})

        return output
