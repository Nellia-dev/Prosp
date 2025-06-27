import asyncio
import json
import time
import traceback
from textwrap import dedent
from typing import List

from loguru import logger
from pydantic import BaseModel, Field

from .base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000


class LeadQualificationInput(BaseModel):
    lead_analysis: str = Field(..., description="Summary from LeadAnalysisAgent.")
    persona_profile: str = Field(..., description="Summary from PersonaCreationAgent (or constructed).")
    deepened_pain_points: str = Field(..., description="JSON string from PainPointDeepeningAgent.")
    product_service_offered: str = Field(..., description="User's product/service being offered.")


class LeadQualificationOutput(BaseModel):
    qualification_tier: str = Field(default="Not Qualified", description="Enum: 'High Potential', 'Medium Potential', 'Low Potential', 'Not Qualified'")
    justification: str = Field(default="Justification not provided.", description="Detailed justification for the qualification tier.")
    key_positive_signals: List[str] = Field(default_factory=list, description="List of main positive signals.")
    key_negative_signals_or_risks: List[str] = Field(default_factory=list, description="List of main negative signals or risks.")
    confidence_score: float = Field(default=0.5, description="Confidence in the assessment (0.0 to 1.0).")
    suggested_next_steps_for_sales: List[str] = Field(default_factory=list, description="List of practical next steps for the sales team.")


class LeadQualificationAgent(BaseAgent[LeadQualificationInput, LeadQualificationOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, output_language: str = "en-US", **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)
        self.output_language = output_language

    def _truncate_text(self, text: str, max_chars: int) -> str:
        return text[:max_chars]

    async def process(self, lead_id: str, job_id: str, input_data: LeadQualificationInput) -> LeadQualificationOutput:
        start_time = time.time()
        await self._emit_event("agent_start", {
            "agent_name": self.name,
            "job_id": job_id,
            "lead_id": lead_id,
            "agent_description": self.description,
            "input_data": input_data.model_dump()
        })
        logger.info(f"⚖️ Qualifying lead {lead_id} for product: {input_data.product_service_offered}")

        try:
            prompt_fixed_overhead = 3000
            available_for_dynamic = GEMINI_TEXT_INPUT_TRUNCATE_CHARS - prompt_fixed_overhead
            tr_lead_analysis = self._truncate_text(input_data.lead_analysis, int(available_for_dynamic * 0.4))
            tr_persona_profile = self._truncate_text(input_data.persona_profile, int(available_for_dynamic * 0.2))
            tr_deepened_pain_points = self._truncate_text(input_data.deepened_pain_points, int(available_for_dynamic * 0.4))

            prompt_template = dedent("""
                You are an experienced B2B Sales Director, specializing in qualifying leads. Your objective is to classify the lead's potential based on the provided strategic information, justify your assessment, and suggest concrete next steps.

                DATA FOR QUALIFICATION ANALYSIS:
                1. GENERAL LEAD ANALYSIS:
                ---
                {lead_analysis}
                ---
                2. TARGET PERSONA PROFILE (Decision-Maker):
                ---
                {persona_profile}
                ---
                3. DEEPENED PAIN POINTS:
                ---
                {deepened_pain_points}
                ---
                4. PRODUCT/SERVICE WE ARE OFFERING: "{product_service_offered}"

                INSTRUCTIONS:
                Perform a complete lead assessment based on all data. Classify the lead, justify it, identify signals, and suggest next steps.

                RESPONSE FORMAT:
                Respond EXCLUSIVELY with a valid JSON object following the schema. Do NOT include any text before or after the JSON object.

                EXPECTED JSON SCHEMA:
                {{
                    "qualification_tier": "string",
                    "justification": "string",
                    "key_positive_signals": ["string"],
                    "key_negative_signals_or_risks": ["string"],
                    "confidence_score": float,
                    "suggested_next_steps_for_sales": ["string"]
                }}
            """)

            final_prompt = prompt_template.format(
                lead_analysis=tr_lead_analysis,
                persona_profile=tr_persona_profile,
                deepened_pain_points=tr_deepened_pain_points,
                product_service_offered=input_data.product_service_offered
            ) + f"\n\nImportant: Generate your response in {self.output_language}."

            logger.debug(f"Prompt for {self.name} (length: {len(final_prompt)}):\n{final_prompt[:500]}...")

            llm_response = await asyncio.to_thread(self.llm_client.generate, final_prompt)

            if not llm_response or not llm_response.content:
                raise ValueError("LLM call returned no response or empty content.")

            parsed_output = self.parse_llm_json_response(llm_response.content, LeadQualificationOutput)

            if parsed_output.error_message:
                raise ValueError(f"Failed to parse LLM response: {parsed_output.error_message}")

            logger.info(f"✅ Lead {lead_id} qualified. Tier: {parsed_output.qualification_tier}")
            
            duration = time.time() - start_time
            await self._emit_event("agent_end", {
                "agent_name": self.name,
                "job_id": job_id,
                "lead_id": lead_id,
                "duration": duration,
                "output": parsed_output.model_dump()
            })
            return parsed_output

        except Exception as e:
            duration = time.time() - start_time
            error_message = f"An unexpected error occurred in {self.name}: {e}"
            logger.error(error_message, exc_info=True)
            await self._emit_event("pipeline_error", {
                "agent_name": self.name,
                "job_id": job_id,
                "lead_id": lead_id,
                "duration": duration,
                "error_message": str(e),
                "details": traceback.format_exc()
            })
            raise


if __name__ == '__main__':
    import sys
    from core_logic.llm_client import MockLLMResponse

    logger.remove()
    logger.add(sys.stderr, level="INFO")

    class MockLLMClient(LLMClientBase):
        def generate(self, prompt: str, **kwargs) -> MockLLMResponse:
            logger.info("MockLLMClient generating response...")
            mock_json_response = json.dumps({
                "qualification_tier": "High Potential",
                "justification": "The lead shows strong alignment with our ICP and has clear pain points that our solution addresses directly.",
                "key_positive_signals": ["High-growth company in target sector", "Decision-maker persona matches"],
                "key_negative_signals_or_risks": ["May have an existing solution in place"],
                "confidence_score": 0.85,
                "suggested_next_steps_for_sales": ["Prioritize for immediate outreach", "Focus on competitive differentiators"]
            })
            return MockLLMResponse(content=mock_json_response)

    async def main():
        mock_llm = MockLLMClient()
        event_queue = asyncio.Queue()
        agent = LeadQualificationAgent(
            name="TestLeadQualifier",
            description="Qualifies leads based on analysis data.",
            llm_client=mock_llm,
            event_queue=event_queue,
            user_id="test_user"
        )

        test_input = LeadQualificationInput(
            lead_analysis="Company is a fast-growing SaaS startup.",
            persona_profile="CTO, focused on innovation and budget efficiency.",
            deepened_pain_points=json.dumps([{"pain": "Scalability issues"}]),
            product_service_offered="Cloud-native scaling solution"
        )

        lead_id = "lead_qual_123"
        job_id = "job_qual_456"

        logger.info(f"--- Running Test for {agent.name} ---")
        output = await agent.process(lead_id, job_id, test_input)

        logger.info(f"\n--- Agent Output ---")
        logger.info(json.dumps(output.model_dump(), indent=2))
        assert output.qualification_tier == "High Potential"
        assert output.confidence_score == 0.85

        logger.info("\n--- Verifying Emitted Events ---")
        event_count = 0
        while not event_queue.empty():
            event = await event_queue.get()
            logger.info(f"Event received: {event['event_type']} for lead {event['payload']['lead_id']}")
            event_count += 1
        assert event_count == 2

        logger.info(f"\n✅ Test for {agent.name} completed successfully.")

    asyncio.run(main())

