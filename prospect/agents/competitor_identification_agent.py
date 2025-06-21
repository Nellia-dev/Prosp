from typing import Optional, List
from pydantic import BaseModel, Field
import json # Ensure json is imported

from .base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class CompetitorIdentificationInput(BaseModel):
    initial_extracted_text: str # From website scraping or initial data
    product_service_offered: str # The user's product/service for context - CLARIFICATION: This is the LEAD's product/service
    known_competitors_list_str: str = "" # Optional, comma-separated string of USER's competitors

class CompetitorDetail(BaseModel):
    name: str = Field(..., description="Name of the identified competitor.")
    description: Optional[str] = Field(default=None, description="Brief description of why they are a competitor to the analyzed company.")
    perceived_strength: Optional[str] = Field(default=None, description="Perceived strength of the competitor (e.g., 'High market share', 'Strong brand recognition').")
    perceived_weakness: Optional[str] = Field(default=None, description="Perceived weakness of the competitor (e.g., 'Higher price point', 'Less flexible solution').")

class CompetitorIdentificationOutput(BaseModel):
    identified_competitors: List[CompetitorDetail] = Field(default_factory=list, description="List of identified competitors of the analyzed company.")
    other_notes: Optional[str] = Field(default=None, description="General observations about the competitive landscape of the analyzed company.")
    error_message: Optional[str] = Field(default=None)

class CompetitorIdentificationAgent(BaseAgent[CompetitorIdentificationInput, CompetitorIdentificationOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, output_language: str = "en-US", **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)
        self.output_language = output_language

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: CompetitorIdentificationInput) -> CompetitorIdentificationOutput:
        error_message = None

        try:
            # Reserve space for other prompt parts
            text_truncate_limit = GEMINI_TEXT_INPUT_TRUNCATE_CHARS - (
                len(input_data.product_service_offered) +
                len(input_data.known_competitors_list_str) +
                2000 # Approx length of fixed prompt parts
            )
            truncated_text = self._truncate_text(input_data.initial_extracted_text, text_truncate_limit)

            known_competitors_prompt_segment = ""
            if input_data.known_competitors_list_str and input_data.known_competitors_list_str.strip():
                known_competitors_prompt_segment = f"KNOWN COMPETITORS LIST (of our company, for contextual reference only):\n\"{input_data.known_competitors_list_str}\""

            # Refined prompt, now in English
            prompt_template = """
                You are a Senior Competitive Intelligence Analyst. Your task is to identify the competitors (direct and indirect) of THE ANALYZED COMPANY, based on its website content and the description of its products/services.
                The focus is exclusively on the competitors of THE ANALYZED COMPANY, not the competitors of the company using this tool.

                EXTRACTED TEXT FROM THE ANALYZED COMPANY'S WEBSITE:
                \"\"\"
                {initial_extracted_text}
                \"\"\"

                PRIMARY PRODUCT/SERVICE OFFERED BY THE ANALYZED COMPANY (to contextualize the identification of its competitors):
                "{product_service_offered_by_lead}"

                {known_competitors_prompt_segment}
                (The segment above, if present, lists competitors of OUR COMPANY. Only mention them as competitors of THE ANALYZED COMPANY if the "EXTRACTED TEXT" explicitly suggests this competition.)

                INSTRUCTIONS FOR COMPETITOR IDENTIFICATION:
                1.  Analyze the "EXTRACTED TEXT" to identify names of companies or products that offer solutions similar or alternative to THE ANALYZED COMPANY's "{product_service_offered_by_lead}".
                2.  Distinguish partners from competitors: if a company is mentioned as an integration partner, do not list it as a competitor unless the text also suggests it competes in other areas.
                3.  If the "{known_competitors_prompt_segment}" is provided, check if any of these names are mentioned in the "EXTRACTED TEXT" as a competitor of THE ANALYZED COMPANY. Do not assume they are competitors of THE ANALYZED COMPANY just because they are on this list.
                4.  If no competing companies are explicitly mentioned or clearly identifiable from the text, the "identified_competitors" field should be an empty list `[]`.

                RESPONSE FORMAT:
                Respond EXCLUSIVELY with a valid JSON object, following the schema and field descriptions below. Do NOT include ANY text, explanation, or markdown (like ```json) before or after the JSON object.

                EXPECTED JSON SCHEMA:
                {{
                    "identified_competitors": [ // List of objects, one for each identified competitor of THE ANALYZED COMPANY.
                        {{
                            "name": "string - The name of the identified competitor.",
                            "description": "string | null - Brief description (1-2 sentences) of why it is considered a competitor to THE ANALYZED COMPANY, based on the text. E.g., 'Offers similar product X', 'Focused on the same niche market Y'.",
                            "perceived_strength": "string | null - A perceived strength of the competitor, if mentioned or inferable from the text (e.g., 'Established market leader', 'Strong in technological innovation'). If not available, use null.",
                            "perceived_weakness": "string | null - A perceived weakness of the competitor, if mentioned or inferable from the text (e.g., 'Higher price point', 'Less customization flexibility'). If not available, use null."
                        }}
                    ],
                    "other_notes": "string | null - General observations about THE ANALYZED COMPANY's competitive landscape (e.g., 'Market seems fragmented with many niche players', 'Intense price competition', 'Text did not provide enough data for deep competitive analysis'). If none, use null."
                }}
            """
            
            final_prompt = prompt_template.format(
                initial_extracted_text=truncated_text,
                product_service_offered_by_lead=input_data.product_service_offered,
                known_competitors_prompt_segment=known_competitors_prompt_segment
            ) + f"\n\nImportant: Generate your entire response, including all textual content and string values within any JSON structure, strictly in the following language: {self.output_language}. Do not include any English text unless it is part of the original input data that should be preserved as is."

            llm_response_str = self.generate_llm_response(final_prompt, output_language=self.output_language)

            if not llm_response_str: # Already in English
                return CompetitorIdentificationOutput(error_message="LLM call returned no response.")

            parsed_output = self.parse_llm_json_response(llm_response_str, CompetitorIdentificationOutput)
            
            if parsed_output.error_message:
                 self.logger.warning(f"{self.name} JSON parsing failed or model validation issue. Error: {parsed_output.error_message}. Raw response: {llm_response_str[:500]}")

            return parsed_output
        
        except Exception as e:
            self.logger.error(f"An unexpected error occurred in {self.name}: {e}", exc_info=True)
            return CompetitorIdentificationOutput(error_message=f"An unexpected error occurred: {str(e)}")

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
            logger.debug(f"MockLLMClient received prompt (lang: {output_language}):\n{prompt[:700]}...")
            if f"strictly in the following language: {output_language}" not in prompt:
                 logger.error(f"Language instruction for '{output_language}' missing in prompt!")

            competitors = []
            # Example in English
            other_notes = "The market appears competitive with established players and new entrants."

            if "Alpha Solutions" in prompt:
                competitors.append({
                    "name": "Alpha Solutions",
                    "description": "Mentioned directly in the text as an alternative, indicating competition in the Custom Management Software area.",
                    "perceived_strength": "Established (implied by comparison)",
                    "perceived_weakness": "Less flexible than Example Inc. (stated in text)"
                })

            if "CompetiMaster" in prompt and "We evaluated CompetiMaster in the past" in prompt:
                 competitors.append({
                    "name": "CompetiMaster",
                    "description": "Considered in the past by Example Inc., suggesting it operates in the same Custom Management Software segment.",
                    "perceived_strength": None,
                    "perceived_weakness": None
                })

            if not competitors:
                other_notes = "No direct competitors clearly identified in the provided text. Beta Tools seems to be a partner."

            return json.dumps({
                "identified_competitors": competitors,
                "other_notes": other_notes
            })

    logger.info("Running mock test for CompetitorIdentificationAgent...")
    mock_llm = MockLLMClient()
    agent = CompetitorIdentificationAgent(
        name="CompetitorIdentificationAgent",
        description="Identifies competitors of the analyzed company.",
        llm_client=mock_llm,
        output_language="en-US" # Testing with English
    )

    # Test data in English
    test_extracted_text = (
        "Example Inc. is a leader in Custom Management Software. Our differentiators include X and Y. "
        "Alpha Solutions are good, but Example Inc. offers more flexibility. "
        "Our integration with Beta Tools is robust. We evaluated CompetiMaster in the past."
    )
    test_product_service_of_lead = "Custom Management Software"

    input_data_1 = CompetitorIdentificationInput(
        initial_extracted_text=test_extracted_text,
        product_service_offered=test_product_service_of_lead,
        known_competitors_list_str=""
    )
    output_1 = agent.process(input_data_1)
    logger.info("\nTest Case 1 (No known competitors list for user):") # Log in English
    if output_1.error_message:
        logger.error(f"Error: {output_1.error_message}")
    else:
        logger.info(f"Identified Competitors: {len(output_1.identified_competitors)}")
        for comp in output_1.identified_competitors: logger.info(f"  - {comp.name}: {comp.description}")
        logger.info(f"Other Notes: {output_1.other_notes}")

    assert output_1.error_message is None
    assert len(output_1.identified_competitors) >= 1
    assert any(c.name == "Alpha Solutions" for c in output_1.identified_competitors)

    input_data_2 = CompetitorIdentificationInput(
        initial_extracted_text=test_extracted_text,
        product_service_offered=test_product_service_of_lead,
        known_competitors_list_str="CompetiMaster, RivalTech"
    )
    output_2 = agent.process(input_data_2)
    logger.info("\nTest Case 2 (With known competitors list for user):") # Log in English
    if output_2.error_message:
        logger.error(f"Error: {output_2.error_message}")
    else:
        logger.info(f"Identified Competitors: {len(output_2.identified_competitors)}")
        for comp in output_2.identified_competitors: logger.info(f"  - {comp.name}: {comp.description}")
        logger.info(f"Other Notes: {output_2.other_notes}")

    assert output_2.error_message is None
    assert len(output_2.identified_competitors) >= 1
    assert any(c.name == "Alpha Solutions" for c in output_2.identified_competitors)
    assert any(c.name == "CompetiMaster" for c in output_2.identified_competitors)
    assert not any(c.name == "RivalTech" for c in output_2.identified_competitors)
    
    logger.info("\nMock tests completed successfully.")
