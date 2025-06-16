from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import json # Ensure json is imported

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

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
            text = json.dumps(text, ensure_ascii=False) # Convert dicts/lists to JSON string if they appear
        return text[:max_chars]

    def _format_dict_for_prompt(self, data: Dict[str, Any], max_total_chars: int) -> str:
        """Formats the dictionary into a string, truncating individual long values."""
        formatted_parts = []

        # Prioritize certain keys for more characters if needed, or simply divide
        # For now, simple division, but a more sophisticated budgeting could be implemented
        num_items = len(data) if len(data) > 0 else 1
        # Give a bit more to complex fields if they exist by checking keys
        # This is a heuristic
        complex_field_keys = ['lead_analysis', 'persona_profile', 'deepened_pain_points',
                              'final_action_plan_text', 'detailed_approach_plan', 'customized_value_propositions_text']

        total_chars_used = 0

        # First pass for complex fields with potentially larger budget
        temp_complex_parts = {}
        for key, value in data.items():
            if key in complex_field_keys:
                str_value = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
                # Allocate more chars for these, e.g., 15% of total budget each if all present
                max_chars_per_item = int(max_total_chars * 0.15)
                truncated_value = self._truncate_text(str_value, max_chars_per_item)
                temp_complex_parts[key] = f"--- {key.replace('_', ' ').title()} ---\n{truncated_value}\n\n"
                total_chars_used += len(temp_complex_parts[key])

        remaining_chars = max_total_chars - total_chars_used
        non_complex_keys = [k for k in data.keys() if k not in complex_field_keys]
        num_non_complex_items = len(non_complex_keys) if non_complex_keys else 1
        max_chars_per_non_complex_item = remaining_chars // num_non_complex_items if remaining_chars > 0 else 50 # Small default

        for key in non_complex_keys:
            value = data[key]
            str_value = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
            truncated_value = self._truncate_text(str_value, max_chars_per_non_complex_item)
            formatted_parts.append(f"--- {key.replace('_', ' ').title()} ---\n{truncated_value}\n\n")

        # Add complex parts to the final list
        for key in complex_field_keys: # Maintain order if possible or define specific order
            if key in temp_complex_parts:
                formatted_parts.append(temp_complex_parts[key])

        return "".join(formatted_parts)


    def process(self, input_data: InternalBriefingSummaryInput) -> InternalBriefingSummaryOutput:
        error_message = None
        self.logger.info(f"📝 INTERNAL BRIEFING SUMMARY AGENT STARTING for lead data containing keys: {list(input_data.all_lead_data.keys())}")

        try:
            # Prepare the all_lead_data for the prompt by formatting and truncating
            # Reserve ample space for the prompt instructions and JSON structure definition
            prompt_instructions_overhead = 4000
            lead_data_for_prompt_str = self._format_dict_for_prompt(
                input_data.all_lead_data,
                GEMINI_TEXT_INPUT_TRUNCATE_CHARS - prompt_instructions_overhead
            )

            # Refined prompt_template based on the new Pydantic models, now in English
            prompt_template = """
                You are a Sales Enablement Manager and Senior Account Strategist, an expert in creating concise, strategic, and actionable internal briefings to prepare B2B sales executives for high-impact interactions, especially in the target market (e.g., Brazilian market).
                Your task is to analyze the extensive compiled data about a lead and synthesize it into a "Strategic Internal Briefing" in JSON format.

                COMPLETE LEAD DATA (organized by section, extracted from previous analyses):
                \"\"\"
                {all_lead_data_formatted_str}
                \"\"\"

                INSTRUCTIONS FOR BRIEFING CREATION:
                Based on ALL the data provided above, generate a briefing that equips the sales executive with essential knowledge and a clear plan.
                Be concise in each field, but ensure critical information is highlighted.
                Adapt language and suggestions for the business context of the target market (e.g., Brazil), if applicable based on the data.

                RESPONSE FORMAT:
                Respond EXCLUSIVELY with a valid JSON object, following the schema and field descriptions below. Do NOT include ANY text, explanation, or markdown (like ```json) before or after the JSON object.

                EXPECTED JSON SCHEMA:
                {{
                  "executive_summary": "string - An executive summary of the lead and opportunity in 2-3 impactful sentences, highlighting the main reason for engagement.",
                  "lead_profile_highlights": {{
                    "company_overview": "string - Brief overview of the lead's company (sector, approximate size, main business/product).",
                    "key_persona_traits": "string - Key characteristics of the target persona (likely role, key responsibilities, main motivations, preferred communication style).",
                    "critical_pain_points": ["string", ...] // List of 2-3 most critical pain points of the persona/company that our solution seems able to solve, based on analysis. Empty list [] if not clear.
                  }},
                  "strategic_approach_summary": {{
                    "main_objective": "string - The main and most strategic objective for this specific approach with the lead.",
                    "core_value_proposition": "string - The most resonant core value proposition for this lead, concisely connecting our solution to their pains/goals.",
                    "suggested_communication_channels": ["string", ...] // List of 1-2 most promising communication channels for this persona (e.g., 'Email', 'LinkedIn'). Empty list [] if not clear.
                  }},
                  "engagement_plan_overview": {{
                     "first_step_action": "string - Concrete action and description of the recommended first step in the contact plan (e.g., 'Send personalized email focusing on [pain X] with CTA for a 15-min call').",
                     "key_talking_points_initial": ["string", ...] // List of 2-3 key talking points for the initial interaction, derived from value proposition and pain points. Empty list [] if none.
                  }},
                  "potential_objections_and_responses": [ // List of 1-2 most likely objections and suggested responses. Empty list [] if no obvious objections.
                    {{
                      "objection": "string - Potential objection (e.g., 'We already have a similar solution', 'We don't have budget right now').",
                      "suggested_response": "string - Concise and strategic suggested response to the objection."
                    }}
                  ],
                  "key_discussion_points_for_sales_exec": ["string", ...], // List of 2-3 crucial questions or points the sales executive should address or investigate during conversations to deepen understanding. Empty list [] if none.
                  "suggested_next_steps_internal": ["string", ...], // List of 1-2 internal next steps for the sales team BEFORE contact or as PREPARATION (e.g., 'Research common connections with the decision-maker on LinkedIn', 'Review the Company Y success case'). Empty list [] if none.
                  "final_recommendation_notes": "string | null" // Any important final notes, additional strategic recommendations, or alerts for the sales team. Use null if none.
                }}
            """

            final_prompt = prompt_template.format(
                all_lead_data_formatted_str=lead_data_for_prompt_str
            ) + f"\n\nImportant: Generate your entire response, including all textual content and string values within any JSON structure, strictly in the following language: {self.output_language}. Do not include any English text unless it is part of the original input data that should be preserved as is."

            self.logger.debug(f"Prompt for {self.name} (length: {len(final_prompt)}):\n{final_prompt[:1000]}...")

            llm_response_str = self.generate_llm_response(final_prompt, output_language=self.output_language)

            if not llm_response_str: # Already in English
                self.logger.error(f"❌ LLM call returned no response for {self.name}")
                return InternalBriefingSummaryOutput(error_message="LLM call returned no response.")

            self.logger.debug(f"LLM response received for {self.name} (length: {len(llm_response_str)}). Attempting to parse.")
            parsed_output = self.parse_llm_json_response(llm_response_str, InternalBriefingSummaryOutput)
            
            if parsed_output.error_message:
                 self.logger.warning(f"⚠️ {self.name} JSON parsing failed or model validation issue. Error: {parsed_output.error_message}. Raw response snippet: {llm_response_str[:500]}")
                 return parsed_output
            
            self.logger.info(f"✅ Internal briefing summary successfully processed for lead data associated with: {input_data.all_lead_data.get('company_name', 'N/A')}")
            return parsed_output

        except Exception as e:
            self.logger.error(f"❌ An unexpected error occurred in {self.name}: {e}", exc_info=True)
            return InternalBriefingSummaryOutput(error_message=f"An unexpected error occurred: {str(e)}")

if __name__ == '__main__':
    from loguru import logger
    import sys
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    class MockLLMClient(LLMClientBase): # Assuming LLMClientBase is correctly imported/defined
        def __init__(self, api_key: str = "mock_key", **kwargs):
            # super().__init__(api_key) # Depends on LLMClientBase
            self.api_key = api_key

        def generate_text_response(self, prompt: str, output_language: str = "en-US") -> Optional[str]:
            logger.debug(f"MockLLMClient received prompt (lang: {output_language}):\n{prompt[:700]}...")
            if f"strictly in the following language: {output_language}" not in prompt:
                 logger.error(f"Language instruction for '{output_language}' missing in prompt!")

            # Example in English
            return json.dumps({
                "executive_summary": "Example Inc. (IT, Medium Size) shows high synergy with Our AI Solutions, especially due to its LATAM expansion and focus on optimizing operations. The COO, Carlos Mendes, is the key contact.",
                "lead_profile_highlights": {
                    "company_overview": "Example Inc. is a medium-sized IT company, focused on SaaS for project management, currently expanding to Latin America. Seeks to modernize its technology.",
                    "key_persona_traits": "Carlos Mendes (COO) values ROI, efficiency, and easy integration. Communicates formally via email/LinkedIn.",
                    "critical_pain_points": ["Scalability of manual QA processes during expansion.", "Need for technological modernization without disruption."]
                },
                "strategic_approach_summary": {
                    "main_objective": "Schedule a 20-minute exploratory call with Carlos Mendes to discuss QA and DevOps optimization with AI in the context of LATAM expansion.",
                    "core_value_proposition": "Our AI Solutions for QA and DevOps Automation can help Example Inc. scale its LATAM operations efficiently, ensuring quality and speed without overburdening the team.",
                    "suggested_communication_channels": ["Personalized Email", "LinkedIn"]
                },
                "engagement_plan_overview": {
                    "first_step_action": "Send a personalized email to Carlos Mendes focusing on expansion challenges and QA optimization, with a CTA for a 20-min call.",
                    "key_talking_points_initial": ["Impact of LATAM expansion on QA efficiency", "Benefits of QA automation with AI", "Similar success cases"]
                },
                "potential_objections_and_responses": [
                    {
                        "objection": "We already have a QA solution or are developing one internally.",
                        "suggested_response": "I understand. Many companies look to complement their current initiatives to accelerate results. Our AI can integrate or offer a new perspective on specific bottlenecks. Could we explore how?"
                    },
                    {
                        "objection": "We don't have a budget for new tools right now.",
                        "suggested_response": "Comprehensible, especially during an expansion. Our focus is precisely on optimizing costs and generating ROI. Could a quick conversation help us identify potential savings for Example Inc.?"
                    }
                ],
                "key_discussion_points_for_sales_exec": [
                    "What are the current biggest bottlenecks in Example Inc.'s QA cycles with the expansion?",
                    "How does Example Inc. measure the success of operational efficiency in DevOps?",
                    "What are Carlos Mendes's priorities for the next 6 months regarding technology and operations?"
                ],
                "suggested_next_steps_internal": [
                    "Research 2nd-degree connections with Carlos Mendes on LinkedIn.",
                    "Review the 'GlobalTech' success case, which had a similar expansion."
                ],
                "final_recommendation_notes": "Focus the approach on the impact of expansion and Carlos's experience with optimization. Be consultative and ROI-focused."
            })

    logger.info("Running mock test for InternalBriefingSummaryAgent...")
    mock_llm = MockLLMClient(api_key="mock_llm_key")
    agent = InternalBriefingSummaryAgent(
        name="TestInternalBriefingAgent",
        description="Test Agent for Internal Briefing Summary",
        llm_client=mock_llm,
        output_language="en-US" # Testing with English
    )

    # Test data in English
    test_all_lead_data = {
        "company_name": "Example Inc.",
        "lead_url": "http://www.exampleinc.com",
        "product_service_context": "Our AI Solutions for QA and DevOps Automation",
        "lead_analysis": {"company_sector": "IT", "company_size_estimate": "Medium Size", "main_services": ["SaaS for project management"], "potential_challenges": ["scalability", "technological modernization"], "general_diagnosis": "Company expanding into LATAM."},
        "persona_profile": {"fictional_name": "Carlos Mendes", "likely_role": "COO", "key_responsibilities": ["operational efficiency"], "motivations": ["clear ROI", "easy integration"]},
        "deepened_pain_points": {"primary_pain_category": "Operational Efficiency in Expansion", "detailed_pain_points": [{"pain": "Manual QA processes", "impact": "Delays"}]},
        "final_action_plan_text": {"recommended_strategy_name": "Consultative Efficiency", "main_call_to_action": "Schedule 20-min call"},
        "customized_value_propositions_text": [{"proposition_title": "Scalability with AI", "detailed_explanation": "Helps with LATAM expansion."}],
        "objection_handling_strategies": [{"objection": "Cost", "response_strategy": "Focus on ROI."}],
        "detailed_approach_plan": {"main_objective": "Schedule call", "contact_sequence": [{"step_number": 1, "channel": "Email", "objective": "Introduction"}]},
        "personalized_message_draft": {"crafted_message_channel": "Email", "crafted_message_subject": "Optimizing QA at Example Inc.", "crafted_message_body": "Hello Carlos..."},
    }

    input_data = InternalBriefingSummaryInput(all_lead_data=test_all_lead_data)
    output = agent.process(input_data)

    if output.error_message:
        logger.error(f"Error: {output.error_message}")
    else:
        logger.success("InternalBriefingSummaryAgent processed successfully.")
        logger.info(f"Executive Summary: {output.executive_summary}")
        logger.info(f"Lead Overview Title: {output.lead_profile_highlights.company_overview}")
        logger.info(f"Strategic Approach Objective: {output.strategic_approach_summary.main_objective}")
        assert "Example Inc." in output.executive_summary # English
        assert "Carlos Mendes" in output.lead_profile_highlights.key_persona_traits
        assert len(output.potential_objections_and_responses) > 0
        assert output.final_recommendation_notes is not None and "ROI-focused" in output.final_recommendation_notes

    assert output.error_message is None
    logger.info("\nMock test for InternalBriefingSummaryAgent completed successfully.")

```
