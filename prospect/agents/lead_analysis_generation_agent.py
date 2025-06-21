from typing import Optional
from pydantic import BaseModel, Field
import json # Added for the mock test, if needed for complex lead_data_str

from .base_agent import BaseAgent
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

            llm_response_obj = self.generate_llm_response(final_prompt, output_language=self.output_language)

            if llm_response_obj and llm_response_obj.content:
                analysis_report = llm_response_obj.content.strip()
                self.logger.info(f"✅ Report generated by {self.name}, length: {len(analysis_report)}")
            else:
                error_message = "LLM call returned no response or an empty response."
                self.logger.warning(f"⚠️ {self.name} received empty response from LLM.")

        except Exception as e:
            self.logger.error(f"❌ An unexpected error occurred in {self.name}: {e}", exc_info=True)
            error_message = f"An unexpected error occurred in {self.name}: {str(e)}" # Already English
            # analysis_report remains empty

        return LeadAnalysisGenerationOutput(
            analysis_report=analysis_report,
            error_message=error_message
        )

