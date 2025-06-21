import asyncio
import json
import re
import textwrap
from typing import List, Optional

from loguru import logger
from pydantic import Field, BaseModel

from .base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# --- Data Models ---

class ContactDetailsInput(BaseModel):
    emails_found: List[str] = Field(default_factory=list)
    instagram_profiles_found: List[str] = Field(default_factory=list)

class B2BPersonalizedMessageInput(BaseModel):
    final_action_plan_text: str
    customized_value_propositions_text: str
    contact_details: ContactDetailsInput
    product_service_offered: str
    lead_url: str
    company_name: str
    persona_fictional_name: str

class B2BPersonalizedMessageOutput(BaseModel):
    crafted_message_channel: str = "N/A"
    crafted_message_subject: Optional[str] = None
    crafted_message_body: str = "Message could not be generated."
    error_message: Optional[str] = None

# --- Agent Definition ---

class B2BPersonalizedMessageAgent(BaseAgent[B2BPersonalizedMessageInput, B2BPersonalizedMessageOutput]):
    def __init__(
        self,
        llm_client: LLMClientBase,
        name: str = "B2B Personalized Message Agent",
        description: str = "Crafts personalized B2B messages based on a detailed action plan and value proposition.",
        output_language: str = "en-US",
        event_queue: Optional[asyncio.Queue] = None,
        user_id: Optional[str] = None,
    ):
        super().__init__(llm_client, name, description, event_queue, user_id)
        self.output_language = output_language

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def _determine_channel_and_contact(self, contact_details: ContactDetailsInput) -> tuple[str, Optional[str]]:
        """Determines the best channel and contact point."""
        if contact_details.emails_found:
            return "Email", contact_details.emails_found[0]
        if contact_details.instagram_profiles_found:
            return "Instagram DM", contact_details.instagram_profiles_found[0]
        return "N/A", None

    async def process(self, lead_id: str, input_data: B2BPersonalizedMessageInput) -> B2BPersonalizedMessageOutput:
        await self._emit_event("agent_start", {"agent_name": self.name, "lead_id": lead_id})
        logger.info(f"Starting message generation for {input_data.company_name} (Lead ID: {lead_id})")

        determined_channel, contact_target = self._determine_channel_and_contact(input_data.contact_details)
        output: B2BPersonalizedMessageOutput

        if determined_channel == "N/A":
            logger.warning(f"No contact channel found for {input_data.company_name} (Lead ID: {lead_id}).")
            output = B2BPersonalizedMessageOutput(error_message="No suitable contact channel found.")
            await self._emit_event("agent_end", {"agent_name": self.name, "lead_id": lead_id, "response": output.model_dump()})
            return output

        response_text = ""
        try:
            logger.info(f"Crafting message for {input_data.company_name} via {determined_channel} (Lead ID: {lead_id}).")

            truncated_action_plan = self._truncate_text(input_data.final_action_plan_text, 8000)
            truncated_value_props = self._truncate_text(input_data.customized_value_propositions_text, 8000)

            prompt_template = textwrap.dedent(f"""
                You are an expert B2B sales strategist and copywriter. Your task is to craft a highly personalized outreach message using the provided strategic inputs. You must follow all instructions precisely.

                **1. Strategic Context & Inputs:**
                - **Company to Contact:** {input_data.company_name}
                - **Persona Name (Fictional):** {input_data.persona_fictional_name}
                - **Our Product/Service:** {input_data.product_service_offered}
                - **Final Action Plan (Key Insights & Strategy):**
                {truncated_action_plan}
                - **Customized Value Propositions:**
                {truncated_value_props}
                - **Contact Channel:** {determined_channel}
                - **Contact Target:** {contact_target}

                **2. Your Task: Craft the Message**
                Based *only* on the information provided above, create a complete and ready-to-send message.

                **3. Output Format: JSON**
                You MUST provide your response as a single, valid JSON object. Do not add any text or explanations before or after the JSON object. The JSON object must have the following structure:
                {{{{
                    "subject": "<A compelling, personalized subject line for the email. If the channel is not email, this can be null.>",
                    "body": "<The full, ready-to-send message body as a single string. Use \\n for newlines.>"
                }}}}

                **4. Language Instruction:**
                Important: Generate the message body and subject line strictly in the following language: **{self.output_language}**.
            """)

            response_text = await self.llm_client.generate(system_prompt="", user_prompt=prompt_template)

            if not response_text:
                raise ValueError("LLM returned an empty response.")

            # Clean and parse JSON response
            if response_text.strip().startswith("```json"):
                response_text = response_text.strip()[7:-3].strip()
            
            message_data = json.loads(response_text)

            output = B2BPersonalizedMessageOutput(
                crafted_message_channel=determined_channel,
                crafted_message_subject=message_data.get("subject"),
                crafted_message_body=message_data.get("body", "Message body could not be extracted.")
            )
            logger.success(f"Successfully generated message for {input_data.company_name} (Lead ID: {lead_id})")

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            error_message = f"Failed to parse LLM response for {input_data.company_name}: {e}"
            logger.error(f"{error_message} (Lead ID: {lead_id})")
            logger.debug(f"LLM Response Text: {response_text}")
            output = B2BPersonalizedMessageOutput(
                crafted_message_channel=determined_channel,
                error_message=error_message
            )
        except Exception as e:
            error_message = f"An unexpected error occurred in {self.name} for {input_data.company_name}: {e}"
            logger.error(f"{error_message} (Lead ID: {lead_id})", exc_info=True)
            output = B2BPersonalizedMessageOutput(
                crafted_message_channel=determined_channel,
                error_message=error_message
            )
        
        await self._emit_event("agent_end", {"agent_name": self.name, "lead_id": lead_id, "response": output.model_dump()})
        return output

