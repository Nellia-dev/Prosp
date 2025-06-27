from typing import Optional, List
import asyncio
import time
import traceback
import json
from pydantic import BaseModel, Field, field_validator

from .base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase, LLMResponse

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class DetailedApproachPlanInput(BaseModel):
    lead_analysis: str # Summary of company, sector, challenges etc.
    persona_profile: str # Detailed description of the target persona
    deepened_pain_points: str # JSON string of PainPointAnalysisOutput (includes investigative questions)
    final_action_plan_text: str # JSON string of ToTActionPlanSynthesisOutput (Synthesized plan from ToT agents)
    product_service_offered: str # User's product/service
    lead_url: str # Lead's website URL

# Sub-models for structured output
class ContactStepDetail(BaseModel):
    step_number: int = Field(..., description="The step number in the sequence (1, 2, 3, ...).")
    channel: str = Field(..., description="Contact channel for this step (e.g., 'Personalized Email', 'LinkedIn (Connection Note)', 'Brief Follow-up Phone Call').")
    objective: str = Field(..., description="Specific and measurable objective for this step.")
    key_topics_arguments: List[str] = Field(default_factory=list, description="List of 2-3 key topics or arguments to address in this step.")
    key_questions: List[str] = Field(default_factory=list, description="Optional list of 1-2 key questions to ask in this step.")
    cta: str = Field(..., description="Specific and clear Call to Action for this step.")
    supporting_materials: Optional[str] = Field(default=None, description="Optional: Supporting resource/material to use or mention (e.g., link to case study, article).")
    
    @field_validator('key_questions', 'key_topics_arguments', mode='before')
    def ensure_list_of_strings(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            # Handles single line string or multiline string from LLM
            return [s.strip() for s in v.splitlines() if s.strip()]
        if isinstance(v, list):
            # Filter list to only include non-empty strings, converting all items to str just in case
            return [str(item).strip() for item in v if str(item).strip()]
        return [] # Return empty list for other unexpected types

class DetailedApproachPlanOutput(BaseModel):
    main_objective: str = Field(default="Main objective of the approach not specified.", description="The primary strategic objective of this comprehensive approach plan.")
    adapted_elevator_pitch: str = Field(default="Adapted elevator pitch not specified.", description="A 2-3 sentence elevator pitch, highly personalized for THIS lead and persona.")
    contact_sequence: List[ContactStepDetail] = Field(default_factory=list, description="List detailing the first 3-4 steps of the contact sequence.")
    engagement_indicators_to_monitor: List[str] = Field(default_factory=list, description="List of 2-3 key indicators to monitor lead engagement.")
    potential_obstacles_attention_points: List[str] = Field(default_factory=list, description="List of 2-3 potential obstacles or attention points for the sales team.")
    suggested_next_steps_if_successful: List[str] = Field(default_factory=list, description="List of 1-2 suggested next steps if the initial contact sequence is successful.")
    error_message: Optional[str] = Field(default=None)

    @field_validator('contact_sequence', mode='before')
    def ensure_contact_sequence_is_list(cls, v):
        if v is None:
            return []
        return v if isinstance(v, list) else []

    @field_validator('engagement_indicators_to_monitor', 'potential_obstacles_attention_points', 'suggested_next_steps_if_successful', mode='before')
    def ensure_string_list_fields(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [s.strip() for s in v.splitlines() if s.strip()]
        if isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        return []


class DetailedApproachPlanAgent(BaseAgent[DetailedApproachPlanInput, DetailedApproachPlanOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, output_language: str = "en-US", **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)
        self.output_language = output_language
        # Logger is already initialized in BaseAgent as self.logger

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    async def process(self, lead_id: str, job_id: str, input_data: DetailedApproachPlanInput) -> DetailedApproachPlanOutput:
        start_time = time.time()
        self.logger.info(f"🚀 DETAILED APPROACH PLAN AGENT starting for lead {lead_id} in job {job_id}")
        await self._emit_event("agent_start", {
            "agent_name": self.name,
            "job_id": job_id,
            "lead_id": lead_id,
            "agent_description": self.description,
            "input_query": input_data.model_dump_json(indent=2)
        })

        try:
            base_prompt_overhead = 3000
            available_chars_for_inputs = GEMINI_TEXT_INPUT_TRUNCATE_CHARS - base_prompt_overhead
            tr_final_action_plan = self._truncate_text(input_data.final_action_plan_text, int(available_chars_for_inputs * 0.35))
            tr_deepened_pain_points = self._truncate_text(input_data.deepened_pain_points, int(available_chars_for_inputs * 0.25))
            tr_lead_analysis = self._truncate_text(input_data.lead_analysis, int(available_chars_for_inputs * 0.20))
            tr_persona_profile = self._truncate_text(input_data.persona_profile, int(available_chars_for_inputs * 0.20))

            prompt_template = """
                You are a Senior Account Strategist and B2B Sales Coach, specializing in creating actionable and effective multi-step engagement plans, with a focus on the target market (e.g., Brazilian market).
                Your task is to expand the provided "Synthesized Final Action Plan" into a "Detailed Approach Plan" that a sales team can execute.

                SYNTHESIZED FINAL ACTION PLAN (High-Level Strategy):
                \"\"\"
                {final_action_plan_text}
                \"\"\"

                ADDITIONAL CONTEXTUAL INFORMATION ABOUT THE LEAD:
                - Lead Analysis: {lead_analysis}
                - Target Persona Profile: {persona_profile}
                - Deepened Pain Points (including investigative questions): {deepened_pain_points}
                - Product/Service we are offering: {product_service_offered}
                - Lead URL (for reference): {lead_url}

                INSTRUCTIONS FOR THE DETAILED PLAN:
                Based on the "Synthesized Final Action Plan" and ALL contextual information, detail the following aspects.
                The plan must be practical, with clear steps, and adapted to communication and business nuances of the target market (e.g., Brazil).
                Create an initial contact sequence of 3 to 4 steps.

                RESPONSE FORMAT:
                Respond EXCLUSIVELY with a valid JSON object, following the schema and field descriptions below. Do NOT include ANY text, explanation, or markdown (like ```json) before or after the JSON object.

                EXPECTED JSON SCHEMA:
                {{
                    "main_objective": "string - Reaffirm or refine the main strategic objective of this complete approach, derived from the Final Action Plan.",
                    "adapted_elevator_pitch": "string - Create a 2-3 sentence 'core message' or 'elevator pitch', highly personalized for THIS lead and persona, highlighting the most crucial benefit of '{product_service_offered}'.",
                    "contact_sequence": [ 
                        {{
                            "step_number": "integer - The step number in the sequence (1, 2, 3, ...).",
                            "channel": "string - Contact channel for this step (e.g., 'Personalized Email', 'LinkedIn (Connection Note)', 'Brief Follow-up Phone Call', 'Short WhatsApp Message').",
                            "objective": "string - Specific and measurable objective for this step (e.g., 'Get a response to the initial email and validate interest', 'Schedule a 15-minute discovery call', 'Confirm persona's main challenge X').",
                            "key_topics_arguments": ["string", ...], 
                            "key_questions": ["string", ...], 
                            "cta": "string - Specific and clear Call to Action for this step (e.g., 'Propose a time for a brief 15-min conversation', 'Ask to connect on LinkedIn', 'Ask for the best time for a quick follow-up').",
                            "supporting_materials": "string | null"
                        }}
                    ],
                    "engagement_indicators_to_monitor": ["string", ...], 
                    "potential_obstacles_attention_points": ["string", ...], 
                    "suggested_next_steps_if_successful": ["string", ...]
                }}
            """

            final_prompt = prompt_template.format(
                final_action_plan_text=tr_final_action_plan,
                lead_analysis=tr_lead_analysis,
                persona_profile=tr_persona_profile,
                deepened_pain_points=tr_deepened_pain_points,
                product_service_offered=input_data.product_service_offered,
                lead_url=input_data.lead_url
            ) + f"\n\nImportant: Generate your entire response, including all textual content and string values within any JSON structure, strictly in the following language: {self.output_language}."

            response_obj = await asyncio.to_thread(
                self.generate_llm_response,
                final_prompt,
                output_language=self.output_language
            )
            llm_response_str = response_obj.content if response_obj else None

            if not llm_response_str:
                self.logger.error(f"LLM call returned no response for {self.name} on lead {lead_id}")
                output = DetailedApproachPlanOutput(error_message="LLM call returned no response.")
                duration = time.time() - start_time
                await self._emit_event("agent_end", {"agent_name": self.name, "job_id": job_id, "lead_id": lead_id, "duration": duration, "output": output.model_dump()})
                return output

            parsed_output = self.parse_llm_json_response(llm_response_str, DetailedApproachPlanOutput)
            
            if parsed_output.error_message:
                 self.logger.warning(f"{self.name} JSON parsing/validation failed for lead {lead_id}. Error: {parsed_output.error_message}")
                 duration = time.time() - start_time
                 await self._emit_event("agent_end", {"agent_name": self.name, "job_id": job_id, "lead_id": lead_id, "duration": duration, "output": parsed_output.model_dump()})
                 return parsed_output
            
            self.logger.info(f"✅ Successfully processed detailed approach plan for lead {lead_id}.")
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
            self.logger.error(f"❌ Critical error in {self.name} for lead {lead_id}: {e}", exc_info=True)
            await self._emit_event("pipeline_error", {
                "agent_name": self.name,
                "job_id": job_id,
                "lead_id": lead_id,
                "error_message": str(e),
                "details": traceback.format_exc()
            })
            raise

if __name__ == '__main__':
    from loguru import logger
    import sys
    import asyncio

    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key", **kwargs):
            self.api_key = api_key

        def generate_llm_response(self, prompt: str, output_language: str = "en-US") -> Optional[LLMResponse]:
            logger.debug(f"MockLLMClient received prompt (lang: {output_language}):\n{prompt[:700]}...")
            content = json.dumps({
                "main_objective": "Initiate a consultative dialogue with Carlos Mendes about optimizing efficiency in Example Inc.'s expansion, aiming to schedule a 20-minute exploratory call.",
                "adapted_elevator_pitch": "With Example Inc.'s expansion, scaling operations efficiently is vital. Our Incredible AI Solutions help IT companies like yours automate key processes and optimize resources, ensuring growth without operational bottlenecks and freeing up your team for innovation.",
                "contact_sequence": [
                    {
                        "step_number": 1,
                        "channel": "Personalized Initial Email",
                        "objective": "Get an initial response and demonstrate understanding of Example Inc.'s challenges.",
                        "key_topics_arguments": [
                            "Acknowledge the company's expansion and its scalability challenges.",
                            "Connect expansion with operational scalability challenges.",
                            "Mention how AI can optimize processes (e.g., automate X, Y, Z)."
                        ],
                        "key_questions": [
                            "As you expand, how are you ensuring your operational processes scale effectively?",
                            "What is the primary obstacle you foresee in maintaining service quality during this growth phase?"
                        ],
                        "cta": "Would you be open to a brief 20-minute call next week to explore how our AI-driven automation could support Example Inc.'s successful expansion?",
                        "supporting_materials": "Link to our case study: 'How Company B Scaled 3x with AI Automation'"
                    }
                ],
                "engagement_indicators_to_monitor": ["Email open/click rates", "LinkedIn connection acceptance", "Response to email/InMail"],
                "potential_obstacles_attention_points": [
                    "Carlos Mendes may be extremely busy due to the expansion.",
                    "Possible skepticism regarding the actual ROI of AI or concerns about implementation complexity.",
                    "The company might already have an in-house solution or a preferred vendor."
                ],
                "suggested_next_steps_if_successful": [
                    "Schedule the confirmed exploratory call (15-20 minutes).",
                    "Prepare specific questions for the call based on persona pains and profile.",
                    "Send a brief diagnostic questionnaire (1-3 questions) before the call to optimize time."
                ]
            })
            return LLMResponse(content=content)

    async def main():
        logger.info("Running mock test for DetailedApproachPlanAgent...")
        mock_llm = MockLLMClient(api_key="mock_llm_key")
        agent = DetailedApproachPlanAgent(
            name="TestDetailedApproachPlanAgent",
            description="Test Agent for Detailed Approach Plan",
            llm_client=mock_llm,
            output_language="en-US"
        )

        input_data = DetailedApproachPlanInput(
            lead_analysis="Example Inc. is a mid-sized IT services company currently undergoing a significant expansion. They are focused on cloud solutions and cybersecurity.",
            persona_profile="Carlos Mendes, Head of IT Operations. Experienced, pragmatic, and focused on operational efficiency and ROI. Skeptical of buzzwords, values proven solutions.",
            deepened_pain_points=json.dumps({"pain_points": [{"point": "Scalability issues", "questions": ["How do you manage workload spikes?"]}]}),
            final_action_plan_text="Focus on efficiency gains and risk mitigation. Propose AI automation as a solution to scale operations without increasing headcount.",
            product_service_offered="Incredible AI Solutions",
            lead_url="http://example.com"
        )

        output = await agent.process(lead_id="test_lead_123", job_id="test_job_456", input_data=input_data)

        logger.info("\nTest Case 1 (Valid Input):")
        if output.error_message:
            logger.error(f"  Error: {output.error_message}")
        else:
            logger.info(f"  Output: {output.model_dump_json(indent=2)}")
        
        assert output.error_message is None
        assert len(output.contact_sequence) > 0
        assert output.contact_sequence[0].step_number == 1
        assert "Carlos Mendes" in output.main_objective

        logger.info("\n✅ Mock test completed successfully!")

    asyncio.run(main())
