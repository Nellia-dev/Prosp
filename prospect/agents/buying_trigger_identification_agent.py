from typing import Optional, List
from pydantic import BaseModel, Field
import json # Ensure json is imported for potential use in main block if needed

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000 # Max length for combined inputs to LLM

class BuyingTriggerIdentificationInput(BaseModel):
    lead_data_str: str # JSON string of lead data (e.g., from scraping, CRM)
    enriched_data: str # From Tavily or other enrichment sources
    product_service_offered: str # The user's product/service for context

class IdentifiedTrigger(BaseModel):
    trigger_description: str = Field(..., description="Clear and concise description of the identified buying trigger.")
    relevance_explanation: str = Field(..., description="Explanation of why this trigger is relevant for the offered product/service.")

class BuyingTriggerIdentificationOutput(BaseModel):
    identified_triggers: List[IdentifiedTrigger] = Field(default_factory=list, description="List of identified buying triggers.")
    other_observations: Optional[str] = Field(default=None, description="General pertinent observations about the company or market not qualifying as direct triggers.")
    error_message: Optional[str] = Field(default=None)

class BuyingTriggerIdentificationAgent(BaseAgent[BuyingTriggerIdentificationInput, BuyingTriggerIdentificationOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, output_language: str = "en-US", **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)
        self.output_language = output_language

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: BuyingTriggerIdentificationInput) -> BuyingTriggerIdentificationOutput:
        error_message = None

        try:
            # Truncate inputs
            # Approximate character allocation, leaving room for prompt overhead
            char_limit_lead_data = GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 3
            char_limit_enriched_data = GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 3

            truncated_lead_data = self._truncate_text(input_data.lead_data_str, char_limit_lead_data)
            truncated_enriched_data = self._truncate_text(input_data.enriched_data, char_limit_enriched_data)

            # Refined prompt_template, now in English
            prompt_template = """
                You are a Market Intelligence Analyst and B2B Sales Strategist, a corporate detective expert in identifying 'windows of opportunity' through buying signals.
                Your mission is to analyze the provided data about a lead and identify events or circumstances (buying triggers) that suggest the company might be receptive to or in need of solutions like ours: "{product_service_offered}".

                LEAD DATA (structured information about the company):
                ```json
                {lead_data_str}
                ```

                ENRICHED DATA (recent news, press releases, organizational changes, etc.):
                \"\"\"
                {enriched_data}
                \"\"\"

                OUR PRODUCT/SERVICE (for which we are seeking opportunities):
                "{product_service_offered}"

                DETAILED INSTRUCTIONS:
                1.  CAREFULLY analyze all information (Lead Data and Enriched Data).
                2.  Identify buying triggers. Triggers are events, changes, or statements indicating a potential need, problem to be solved, or a new initiative where our product/service would be relevant. Common examples include:
                    -   Recent changes in executive leadership (new C-levels, VPs, Directors in key areas).
                    -   Announcements of business expansion, new product/service launches, or entry into new geographic markets.
                    -   Significant investment rounds (Seed, Series A, B, C, etc.) or acquisitions.
                    -   Explicit mentions in the data of challenges, problems, or objectives that our "{product_service_offered}" can address (e.g., "seeking to optimize sales processes," "need to improve digital marketing team efficiency," "focus on digital transformation").
                    -   Significant increase in hiring in specific areas that would benefit from our product/service.
                    -   Mergers or acquisitions (of both the target company and its competitors).
                    -   Mentions of problems with current solutions, expiring contracts, or a clear desire for technological or procedural modernization.
                3.  For each identified trigger, provide a clear description and a concise explanation of its relevance. The `relevance_explanation` should succinctly connect the trigger to a possible need or problem that our "{product_service_offered}" can solve for this specific company.

                RESPONSE FORMAT:
                Respond EXCLUSIVELY with a valid JSON object, following the schema below. Do NOT include ANY text, explanation, or markdown (like ```json) before or after the JSON object.

                EXPECTED JSON SCHEMA:
                {{
                    "identified_triggers": [  // List of objects, one for each trigger. If no triggers are found, return an empty list [].
                        {{
                            "trigger_description": "string - Clear and concise description of the identified trigger (e.g., 'New Series B investment round announced on [date]', 'Hiring of new VP of Marketing focused on digital growth', 'Mention in annual report about focus on optimizing operational costs').",
                            "relevance_explanation": "string - Concise explanation (1-2 sentences) of why this specific trigger is relevant for our '{product_service_offered}', indicating a possible need or opportunity."
                        }}
                    ],
                    "other_observations": "string | null - General pertinent observations about the company or market that do not qualify as direct triggers but might be useful. If none, use null or a string like 'No additional relevant observations.'."
                }}
            """

            final_prompt = prompt_template.format(
                lead_data_str=truncated_lead_data,
                enriched_data=truncated_enriched_data,
                product_service_offered=input_data.product_service_offered
            ) + f"\n\nImportant: Generate your entire response, including all textual content and string values within any JSON structure, strictly in the following language: {self.output_language}. Do not include any English text unless it is part of the original input data that should be preserved as is."

            llm_response_str = self.generate_llm_response(final_prompt, output_language=self.output_language)

            if not llm_response_str: # Already in English
                return BuyingTriggerIdentificationOutput(error_message="LLM call returned no response.")

            # parse_llm_json_response should ideally handle Pydantic validation internally
            # or return a dict that can be validated by Pydantic model.
            parsed_output = self.parse_llm_json_response(llm_response_str, BuyingTriggerIdentificationOutput)
            
            if parsed_output.error_message:
                 self.logger.warning(f"{self.name} JSON parsing failed or model validation issue. Error: {parsed_output.error_message}. Raw response: {llm_response_str[:500]}")
                 # Return the output with the error message set by parse_llm_json_response
                 return parsed_output

            # Ensure identified_triggers is a list of IdentifiedTrigger objects if parsing was successful
            # This should be handled by Pydantic validation if parse_llm_json_response returns a dict
            # If parse_llm_json_response already returns a BuyingTriggerIdentificationOutput, this is fine.
            if not isinstance(parsed_output.identified_triggers, list) or \
               not all(isinstance(item, IdentifiedTrigger) for item in parsed_output.identified_triggers):
                # This case might indicate that parse_llm_json_response did not fully hydrate the model correctly
                # or the LLM returned an unexpected structure for identified_triggers.
                self.logger.warning(f"{self.name}: 'identified_triggers' is not a list of IdentifiedTrigger objects. LLM output might be malformed for this field.")
                # We might still return parsed_output as is, relying on the error_message if Pydantic validation failed,
                # or attempt a more specific error message here.
                # For now, we trust that parse_llm_json_response + Pydantic validation handles this.
                pass


            return parsed_output

        except Exception as e:
            self.logger.error(f"An unexpected error occurred in {self.name}: {e}", exc_info=True)
            # import traceback # Already imported if needed
            # traceback.print_exc() # Handled by logger's exc_info=True
            return BuyingTriggerIdentificationOutput(error_message=f"An unexpected error occurred: {str(e)}")

if __name__ == '__main__':
    from loguru import logger # Ensure logger is available
    import sys
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    class MockLLMClient(LLMClientBase): # Assuming LLMClientBase is correctly imported/defined
        def __init__(self, api_key: str = "mock_key", **kwargs):
            # super().__init__(api_key) # Depends on LLMClientBase
            self.api_key = api_key


        def generate_text_response(self, prompt: str, output_language: str = "en-US") -> Optional[str]:
            logger.debug(f"MockLLMClient received prompt (lang: {output_language}):\n{prompt[:600]}...")
            if f"strictly in the following language: {output_language}" not in prompt:
                 logger.error(f"Language instruction for '{output_language}' missing in prompt!")

            # Simulate LLM returning valid JSON based on the refined prompt (English example)
            return json.dumps({
                "identified_triggers": [
                    {
                        "trigger_description": "Market Expansion Announcement to LATAM (Enriched Data)",
                        "relevance_explanation": "Expansion into new markets often requires process optimization and new tools to scale operations, which Our Incredible Solutions can provide."
                    },
                    {
                        "trigger_description": "Mention of 'optimizing internal processes' and 'modernizing technology stack' (Lead and Enriched Data)",
                        "relevance_explanation": "This is a direct statement of need that aligns perfectly with the benefits of Our Incredible Solutions."
                    },
                    {
                        "trigger_description": "Hiring of New COO, Carlos Mendes (Enriched Data)",
                        "relevance_explanation": "New leaders in operations often review systems and processes, opening opportunities for Our Incredible Solutions."
                    }
                ],
                "other_observations": "The company appears to be in a growth and modernization cycle, making it an interesting prospect."
            })

    logger.info("Running mock test for BuyingTriggerIdentificationAgent...")
    mock_llm = MockLLMClient()
    agent = BuyingTriggerIdentificationAgent(
        name="BuyingTriggerIdentificationAgent",
        description="Identifies buying triggers from lead data.",
        llm_client=mock_llm,
        output_language="en-US" # Testing with English
    )

    # Test data in English
    test_lead_data_str = """{
        "company_name": "Example Inc.",
        "description": "Focused on growth and wants to optimize internal processes."
    }"""
    test_enriched_data = (
        "Example Inc. announced expansion into the LATAM market. "
        "Recently appointed a new COO, Carlos Mendes, from TechCorp. "
        "News article mentions Example Inc. is looking to 'modernize its technology stack'."
    )
    test_product_service = "Our Incredible Solutions for Process Optimization"

    input_data = BuyingTriggerIdentificationInput(
        lead_data_str=test_lead_data_str,
        enriched_data=test_enriched_data,
        product_service_offered=test_product_service
    )

    output = agent.process(input_data)

    if output.error_message:
        logger.error(f"Error: {output.error_message}")
    else:
        logger.success("BuyingTriggerIdentificationAgent processed successfully.")
        logger.info(f"Identified Triggers: {len(output.identified_triggers)}")
        for i, trigger in enumerate(output.identified_triggers):
            logger.info(f"  Trigger {i+1}: {trigger.trigger_description}")
            logger.info(f"  Explanation: {trigger.relevance_explanation}")
        logger.info(f"Other Observations: {output.other_observations}")

    assert output.error_message is None
    assert len(output.identified_triggers) == 3
    assert "Market Expansion Announcement to LATAM" in output.identified_triggers[0].trigger_description
    assert "Our Incredible Solutions" in output.identified_triggers[0].relevance_explanation
    assert output.other_observations is not None

    logger.info("Mock test completed successfully.")

```
