from typing import Optional
from pydantic import BaseModel
import json # Added for the mock test, if needed for complex lead_data_str

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000  # Max input tokens for Gemini Flash is 128k


class LeadAnalysisGenerationInput(BaseModel):
    lead_data_str: str = Field(..., description="JSON string representing structured lead data.")
    enriched_data: str = Field(..., description="Text string of enriched data from web searches, news, etc.")
    product_service_offered: str = Field(..., description="Description of the user's product/service for context.")


class LeadAnalysisGenerationOutput(BaseModel):
    analysis_report: str = Field(..., description="The generated textual analysis report for the lead.")
    error_message: Optional[str] = Field(default=None, description="Error message if the process failed.")


class LeadAnalysisGenerationAgent(BaseAgent[LeadAnalysisGenerationInput, LeadAnalysisGenerationOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, output_language: str = "en-US", **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)
        self.output_language = output_language


    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: LeadAnalysisGenerationInput) -> LeadAnalysisGenerationOutput:
        analysis_report = ""
        error_message = None

        self.logger.info(f"📊 LEAD ANALYSIS GENERATION AGENT STARTING for product/service: {input_data.product_service_offered}")

        try:
            # Approximate character allocation, leaving room for prompt overhead
            # Total GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000
            prompt_fixed_overhead = 2000 # Approx chars for fixed parts of prompt
            available_for_dynamic = GEMINI_TEXT_INPUT_TRUNCATE_CHARS - prompt_fixed_overhead

            # Distribute available characters: 50% for lead_data, 50% for enriched_data
            # (or adjust ratio if one is typically much larger)
            truncated_lead_data = self._truncate_text(input_data.lead_data_str, available_for_dynamic // 2)
            truncated_enriched_data = self._truncate_text(input_data.enriched_data, available_for_dynamic // 2)
            
            # Refined prompt_template, now in English
            prompt_template = """
                You are a Senior Business Intelligence Analyst, specializing in distilling complex lead information into clear, concise, and actionable executive reports.
                Your task is to generate an insightful textual analysis of the lead, contextualized by our product/service: "{product_service_offered}".

                LEAD DATA (source: internally structured JSON):
                \"\"\"
                {lead_data_str}
                \"\"\"

                ENRICHED DATA (source: additional web research, news, etc.):
                \"\"\"
                {enriched_data}
                \"\"\"

                INSTRUCTIONS FOR THE ANALYSIS REPORT:
                Based on ALL provided data (Lead Data and Enriched Data), draft a textual report covering the following points in an integrated and fluid manner:

                1.  **Company Overview:** Clearly identify the company's industry sector and its main product or service.
                2.  **Estimated Size and Structure:** Assess the estimated company size (small, medium, large) and, if possible, infer relevant aspects of its organizational structure.
                3.  **Key Challenges and Needs:** Identify the main challenges and needs the company appears to face. Place special emphasis on those that can be directly addressed or alleviated by our product/service: "{product_service_offered}".
                4.  **Culture and Values (if discernible):** Briefly describe any aspects of the company's culture or values that stand out from the information.
                5.  **General Diagnosis and Conversion Potential:** Provide a summarized diagnosis of the lead's situation and an assessment of its conversion potential, considering the fit with "{product_service_offered}".

                ADDITIONAL GUIDELINES:
                - **Objectivity:** Base your analysis strictly on the available information. If crucial information is unclear or unavailable, mention this explicitly (e.g., "The exact company size could not be determined from the provided data.").
                - **Format:** The analysis should be a well-articulated running text. DO NOT use JSON format.
                - **Style:** Maintain a professional, analytical, and insightful tone.
                - **Length:** The final report should be concise, ideally with a maximum of 300-350 words.

                Begin the report directly with the analysis.

                LEAD ANALYSIS REPORT:
            """
            
            final_prompt = prompt_template.format(
                product_service_offered=input_data.product_service_offered,
                lead_data_str=truncated_lead_data,
                enriched_data=truncated_enriched_data
            ) + f"\n\nImportant: Generate your entire response, including all textual content and string values within any JSON structure, strictly in the following language: {self.output_language}. Do not include any English text unless it is part of the original input data that should be preserved as is."

            self.logger.debug(f"Prompt for {self.name} (length: {len(final_prompt)}):\n{final_prompt[:500]}...")

            llm_response = self.generate_llm_response(final_prompt, output_language=self.output_language)

            if llm_response:
                analysis_report = llm_response.strip()
                self.logger.info(f"✅ Report generated by {self.name}, length: {len(analysis_report)}")
            else:
                error_message = "LLM call returned no response or an empty response." # Already English
                self.logger.warning(f"⚠️ {self.name} received empty response from LLM.")
                # analysis_report remains empty

        except Exception as e:
            self.logger.error(f"❌ An unexpected error occurred in {self.name}: {e}", exc_info=True)
            error_message = f"An unexpected error occurred in {self.name}: {str(e)}" # Already English
            # analysis_report remains empty

        return LeadAnalysisGenerationOutput(
            analysis_report=analysis_report,
            error_message=error_message
        )

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

            if "LEAD ANALYSIS REPORT:" in prompt:
                # Example in English
                return (
                    "Example Inc. primarily operates in the Information Technology sector, focusing on Software as a Service (SaaS) solutions for project management and collaboration.\n\n"
                    "Considering the data and mention of 150 employees, Example Inc. is classified as a medium-sized enterprise. Its organizational structure likely includes dedicated IT, sales, marketing, and product development departments, typical of a growing SaaS company.\n\n"
                    "Key challenges identified, particularly relevant for Our Incredible Sales Optimization Solutions, include the need to efficiently scale its sales operations to support the mentioned market expansion. The mention of 'modernizing its technology stack' also suggests an openness to new tools that can optimize the sales funnel and lead management.\n\n"
                    "The company culture appears to be innovation-focused, evidenced by awards received in 2023. This suggests receptiveness to advanced technological solutions that demonstrate clear added value.\n\n"
                    "General Diagnosis: Example Inc. is a lead with good potential. The expansion phase and the quest for technological modernization create a window of opportunity for Our Incredible Solutions, which can directly assist in optimizing sales processes and customer management, crucial for successful expansion. Conversion potential is moderate to high, depending on the internal urgency to address sales scalability challenges."
                ).strip()
            return "Default mock response for testing."

    logger.info("Running mock test for LeadAnalysisGenerationAgent...")
    mock_llm = MockLLMClient()
    agent = LeadAnalysisGenerationAgent(
        name="TestLeadAnalysisGenerationAgent",
        description="Test Agent for Lead Analysis Generation",
        llm_client=mock_llm,
        output_language="en-US" # Testing with English
    )

    # Test data in English
    test_lead_data = json.dumps({
        "company_name": "Example Inc.",
        "url": "http://www.exampleinc.com",
        "description": "Leader in innovative IT solutions for project management.",
        "employees": "150",
        "sector": "Information Technology (SaaS)"
    })
    test_enriched_data = "Example Inc. won innovation awards in 2023. Recent articles mention market expansion to LATAM and a quest to modernize its technology stack."
    test_product_service = "Our Incredible Sales Optimization Solutions"

    input_data = LeadAnalysisGenerationInput(
        lead_data_str=test_lead_data,
        enriched_data=test_enriched_data,
        product_service_offered=test_product_service
    )

    output = agent.process(input_data)

    logger.info(f"Analysis Report:\n{output.analysis_report}")
    if output.error_message:
        logger.error(f"Error: {output.error_message}")
    else:
        logger.success("Analysis report generated successfully.")


    assert "Example Inc." in output.analysis_report # English
    assert "Our Incredible Sales Optimization Solutions" in output.analysis_report
    assert "Information Technology" in output.analysis_report # English
    assert "medium-sized enterprise" in output.analysis_report # English
    assert "market expansion" in output.analysis_report # English
    assert output.error_message is None
    logger.info("Mock test for LeadAnalysisGenerationAgent completed successfully.")

```
