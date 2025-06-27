from typing import Optional, Dict, Any, List
import asyncio
import time
import traceback
import json
from pydantic import BaseModel, Field

from .base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase, LLMResponse

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class InternalBriefingSummaryInput(BaseModel):
    all_lead_data: Dict[str, Any] # Dictionary holding all previously generated data

# --- Updated Pydantic Output Models (Translated) ---
class LeadProfileHighlights(BaseModel):
    company_overview: str = Field(default="Company overview not provided.", description="Brief overview of the lead's company (sector, approximate size, main business/product).")
    key_persona_traits: str = Field(default="Key persona traits not provided.", description="Key characteristics of the target persona (likely role, key responsibilities, main motivations, preferred communication style).")
    critical_pain_points: List[str] = Field(default_factory=list, description="List of 2-3 most critical pain points of the persona/company that our solution can address.")

class StrategicApproachSummary(BaseModel):
    main_objective: str = Field(default="Main objective not provided.", description="The primary strategic objective for this specific approach with the lead.")
    core_value_proposition: str = Field(default="Core value proposition not provided.", description="The most resonant core value proposition for this lead, concisely connecting our solution to their pains/goals.")
    suggested_communication_channels: List[str] = Field(default_factory=list, description="List of 1-2 most promising communication channels for this persona (e.g., 'Email', 'LinkedIn').")

class EngagementPlanOverview(BaseModel):
    first_step_action: str = Field(default="First step not provided.", description="Concrete action and description of the recommended first step in the contact plan.")
    key_talking_points_initial: List[str] = Field(default_factory=list, description="List of 2-3 key talking points for the initial interaction, derived from value proposition and pain points.")

class ObjectionResponsePair(BaseModel):
    objection: str = Field(default="Objection not specified.", description="Potential objection (e.g., 'We already have a similar solution', 'We don't have budget right now').")
    suggested_response: str = Field(default="Response not suggested.", description="Concise and strategic suggested response to the objection.")

class InternalBriefingSummaryOutput(BaseModel):
    executive_summary: str = Field(default="Executive summary not provided.", description="An impactful 2-3 sentence executive summary of the lead and opportunity, highlighting the main reason for engagement.")
    lead_profile_highlights: LeadProfileHighlights = Field(default_factory=LeadProfileHighlights, description="Highlights of the lead's profile.")
    strategic_approach_summary: StrategicApproachSummary = Field(default_factory=StrategicApproachSummary, description="Summary of the strategic approach.")
    engagement_plan_overview: EngagementPlanOverview = Field(default_factory=EngagementPlanOverview, description="Overview of the engagement plan.")
    potential_objections_and_responses: List[ObjectionResponsePair] = Field(default_factory=list, description="List of 1-2 most likely objections and suggested responses.")
    key_discussion_points_for_sales_exec: List[str] = Field(default_factory=list, description="List of 2-3 crucial questions or points the sales executive should address or investigate during conversations.")
    suggested_next_steps_internal: List[str] = Field(default_factory=list, description="List of 1-2 internal next steps for the sales team BEFORE contact or as PREPARATION.")
    final_recommendation_notes: Optional[str] = Field(default="No specific final notes.", description="Any important final notes, additional strategic recommendations, or alerts for the sales team.")
    error_message: Optional[str] = Field(default=None)
# --- End of Updated Pydantic Output Models ---

class InternalBriefingSummaryAgent(BaseAgent[InternalBriefingSummaryInput, InternalBriefingSummaryOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, output_language: str = "en-US", **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)
        self.output_language = output_language

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        if not isinstance(text, str):
            text = json.dumps(text, ensure_ascii=False)
        return text[:max_chars]

    def _format_dict_for_prompt(self, data: Dict[str, Any], max_total_chars: int) -> str:
        """Formats the dictionary into a string, truncating individual long values."""
        formatted_parts = []
        complex_field_keys = ['lead_analysis', 'persona_profile', 'deepened_pain_points',
                              'final_action_plan_text', 'detailed_approach_plan', 'customized_value_propositions_text']
        total_chars_used = 0
        temp_complex_parts = {}
        for key, value in data.items():
            if key in complex_field_keys:
                str_value = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
                max_chars_per_item = int(max_total_chars * 0.15)
                truncated_value = self._truncate_text(str_value, max_chars_per_item)
                temp_complex_parts[key] = f"--- {key.replace('_', ' ').title()} ---\n{truncated_value}\n\n"
                total_chars_used += len(temp_complex_parts[key])

        remaining_chars = max_total_chars - total_chars_used
        non_complex_keys = [k for k in data.keys() if k not in complex_field_keys]
        num_non_complex_items = len(non_complex_keys) if non_complex_keys else 1
        max_chars_per_non_complex_item = remaining_chars // num_non_complex_items if remaining_chars > 0 else 50

        for key in non_complex_keys:
            value = data[key]
            str_value = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
            truncated_value = self._truncate_text(str_value, max_chars_per_non_complex_item)
            formatted_parts.append(f"--- {key.replace('_', ' ').title()} ---\n{truncated_value}\n\n")

        for key in complex_field_keys:
            if key in temp_complex_parts:
                formatted_parts.append(temp_complex_parts[key])

        return "".join(formatted_parts)

    async def process(self, lead_id: str, job_id: str, input_data: InternalBriefingSummaryInput) -> InternalBriefingSummaryOutput:
        start_time = time.time()
        self.logger.info(f"🚀 INTERNAL BRIEFING SUMMARY AGENT starting for lead {lead_id} in job {job_id}")
        await self._emit_event("agent_start", {
            "agent_name": self.name,
            "job_id": job_id,
            "lead_id": lead_id,
            "agent_description": self.description,
            "input_query": json.dumps(input_data.all_lead_data, indent=2)
        })

        try:
            prompt_instructions_overhead = 4000
            lead_data_for_prompt_str = self._format_dict_for_prompt(
                input_data.all_lead_data,
                GEMINI_TEXT_INPUT_TRUNCATE_CHARS - prompt_instructions_overhead
            )

            prompt_template = """...""" # Prompt is large, keeping it collapsed for brevity

            final_prompt = prompt_template.format(
                all_lead_data_formatted_str=lead_data_for_prompt_str
            ) + f"\n\nImportant: Generate your entire response... in {self.output_language}."

            response_obj = await asyncio.to_thread(
                self.generate_llm_response,
                final_prompt,
                output_language=self.output_language
            )
            llm_response_str = response_obj.content if response_obj else None

            if not llm_response_str:
                self.logger.error(f"LLM call returned no response for {self.name} on lead {lead_id}")
                output = InternalBriefingSummaryOutput(error_message="LLM call returned no response.")
                duration = time.time() - start_time
                await self._emit_event("agent_end", {"agent_name": self.name, "job_id": job_id, "lead_id": lead_id, "duration": duration, "output": output.model_dump()})
                return output

            parsed_output = self.parse_llm_json_response(llm_response_str, InternalBriefingSummaryOutput)
            
            if parsed_output.error_message:
                 self.logger.warning(f"{self.name} JSON parsing/validation failed for lead {lead_id}. Error: {parsed_output.error_message}")
                 duration = time.time() - start_time
                 await self._emit_event("agent_end", {"agent_name": self.name, "job_id": job_id, "lead_id": lead_id, "duration": duration, "output": parsed_output.model_dump()})
                 return parsed_output
            
            self.logger.info(f"✅ Successfully processed internal briefing summary for lead {lead_id}.")
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

    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key", **kwargs):
            self.api_key = api_key

        def generate_llm_response(self, prompt: str, output_language: str = "en-US") -> Optional[LLMResponse]:
            logger.debug(f"MockLLMClient received prompt (lang: {output_language}):\n{prompt[:500]}...")
            mock_response = {
                "executive_summary": "Opportunity with TechCorp, a mid-size SaaS firm, to address critical scalability issues in their backend services. The persona, Jane Doe (CTO), is focused on technical excellence and future-proofing their infrastructure.",
                "lead_profile_highlights": {
                    "company_overview": "TechCorp: Mid-size B2B SaaS company specializing in project management tools.",
                    "key_persona_traits": "Jane Doe, CTO. Technical, data-driven, avoids sales fluff. Prefers email.",
                    "critical_pain_points": ["Service timeouts during peak usage", "High infrastructure costs", "Slow deployment cycles"]
                },
                "strategic_approach_summary": {
                    "main_objective": "Position our AI-driven infrastructure optimization as the key to solving TechCorp's scalability and cost issues.",
                    "core_value_proposition": "We help SaaS companies like TechCorp scale efficiently, cutting infrastructure costs by up to 30% while improving service reliability.",
                    "suggested_communication_channels": ["Email", "LinkedIn"]
                },
                "engagement_plan_overview": {
                    "first_step_action": "Send a personalized email to Jane Doe, referencing a recent blog post of hers on scalability and connecting it to our solution.",
                    "key_talking_points_initial": ["The challenge of scaling SaaS infrastructure", "AI-driven cost optimization", "Improving deployment velocity"]
                },
                "potential_objections_and_responses": [
                    {
                        "objection": "We have an in-house DevOps team handling this.",
                        "suggested_response": "That's great. We complement in-house teams by automating the routine optimization tasks, freeing them to focus on strategic initiatives."
                    }
                ],
                "key_discussion_points_for_sales_exec": ["What are your current cloud infrastructure costs?", "How do you currently monitor for performance bottlenecks?"],
                "suggested_next_steps_internal": ["Review Jane Doe's LinkedIn profile for recent activity", "Prepare a one-page summary of a relevant case study."],
                "final_recommendation_notes": "Jane is highly technical. Ensure the sales exec is prepared for in-depth questions."
            }
            return LLMResponse(content=json.dumps(mock_response))

    async def main():
        logger.info("Running mock test for InternalBriefingSummaryAgent...")
        mock_llm = MockLLMClient(api_key="mock_llm_key")
        agent = InternalBriefingSummaryAgent(
            name="TestInternalBriefingSummaryAgent",
            description="Test Agent for Internal Briefing Summary",
            llm_client=mock_llm
        )

        test_input = InternalBriefingSummaryInput(
            all_lead_data={
                "company_name": "TechCorp",
                "lead_analysis": {"summary": "SaaS company facing scalability issues."},
                "persona_profile": {"name": "Jane Doe", "role": "CTO"}
            }
        )

        output = await agent.process(lead_id="lead_abc", job_id="job_123", input_data=test_input)

        if output.error_message:
            logger.error(f"Agent returned an error: {output.error_message}")
        else:
            logger.success("Agent processed successfully!")
            logger.info(f"Executive Summary: {output.executive_summary}")
            assert "TechCorp" in output.executive_summary
            assert len(output.potential_objections_and_responses) > 0

    asyncio.run(main())
