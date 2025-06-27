import json
import re
from typing import Optional, List
import asyncio
import time
import traceback

from pydantic import BaseModel, Field

from .base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class ContactExtractionInput(BaseModel):
    extracted_text: str
    company_name: str
    product_service_offered: str # Context of what the lead offers, to understand roles

class ContactExtractionOutput(BaseModel):
    emails_found: List[str] = Field(default_factory=list, description="List of email addresses found.")
    instagram_profiles_found: List[str] = Field(default_factory=list, description="List of Instagram profile handles (e.g., @username).")
    phone_numbers_found: List[str] = Field(default_factory=list, description="List of phone numbers found.")
    linkedin_profiles_found: List[str] = Field(default_factory=list, description="List of LinkedIn profile URLs.")
    facebook_profiles_found: List[str] = Field(default_factory=list, description="List of Facebook profile URLs.")
    twitter_x_profiles_found: List[str] = Field(default_factory=list, description="List of Twitter/X handles (e.g., @username).")
    suggested_search_queries: List[str] = Field(default_factory=list, description="List of suggested search queries to find more contact details or decision-makers.")
    confidence_score: Optional[float] = Field(default=None, description="Confidence score (0.0 to 1.0) in the quantity and quality of contact information extracted directly from the text.")
    extraction_summary: Optional[str] = Field(default=None, description="Brief summary of the extraction process, noting ease of finding information and any difficulties.")
    error_message: Optional[str] = Field(default=None)

class ContactExtractionAgent(BaseAgent[ContactExtractionInput, ContactExtractionOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, output_language: str = "en-US", **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)
        self.output_language = output_language

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    async def process(self, lead_id: str, job_id: str, input_data: ContactExtractionInput) -> ContactExtractionOutput:
        start_time = time.time()
        self.logger.info(f"📧 CONTACT EXTRACTION STARTING for lead {lead_id} in job {job_id}")
        await self._emit_event("agent_start", {
            "agent_name": self.name,
            "job_id": job_id,
            "lead_id": lead_id,
            "agent_description": self.description,
            "input_query": input_data.model_dump_json(indent=2)
        })

        try:
            char_limit_extracted_text = GEMINI_TEXT_INPUT_TRUNCATE_CHARS - 2500
            truncated_text = self._truncate_text(input_data.extracted_text, char_limit_extracted_text)

            prompt_template = """
                You are a Data Mining and OSINT (Open Source Intelligence) Specialist, highly skilled in extracting B2B contact information from web content and unstructured texts.
                Your task is to analyze the provided content about the company '{company_name}' (which offers '{product_service_offered}') and extract a variety of contact information, as well as suggest search queries to find more details.

                PROVIDED CONTENT (website, news, etc.):
                \"\"\"
                {extracted_text}
                \"\"\"

                DETAILED EXTRACTION INSTRUCTIONS:
                1.  **Emails:** Identify and list all valid email addresses. Prioritize generic emails (e.g., contact@, sales@) and, if possible, emails that seem to belong to departments or individuals (e.g., name.surname@).
                2.  **Phones:** Identify and list all phone numbers. Try to standardize to a format that includes country and area codes when inferable (e.g., "+1 415 555-XXXX").
                3.  **LinkedIn Profiles:** Identify LinkedIn profile URLs, both for the company page and for individuals who appear to be key employees or decision-makers.
                4.  **Instagram Profiles:** Identify Instagram usernames/profiles (e.g., @company_name).
                5.  **Facebook Profiles:** Identify Facebook page URLs associated with the company.
                6.  **Twitter/X Profiles:** Identify Twitter/X handles (e.g., @companyX).
                7.  **Additional Search Suggestions:** Based on the text and company profile, formulate up to 3 optimized search strings (for Google or Tavily API). The goal of these future searches will be to find:
                    a.  Contacts of specific key decision-makers (e.g., CEOs, Marketing/Sales Directors, etc.) at '{company_name}'.
                    b.  More direct contact information or specific department contacts if the current text is limited.
                    Example suggestions: "Sales contact {company_name}", "VP Sales {company_name} LinkedIn", "Phone {company_name} [city] branch".
                8.  **Confidence Score:** Provide a numeric score (float between 0.0 and 1.0) representing your confidence in the quantity and quality of contact information extracted directly from the text. 0.0 for no information found, 1.0 for abundant and clear information.
                9.  **Extraction Summary:** A brief summary (1-2 sentences) of the extraction process, mentioning which types of information were easiest to find and any difficulties or observations (e.g., "Many generic emails found, but few individual contacts. Company LinkedIn URL clear. Search suggestions focused on decision-makers.").

                RESPONSE FORMAT:
                Respond EXCLUSIVELY with a valid JSON object, following the schema and field descriptions below. Do NOT include ANY text, explanation, or markdown (like ```json) before or after the JSON object.

                EXPECTED JSON SCHEMA:
                {{
                    "emails_found": ["string", ...], // List of email addresses. Empty list [] if none found.
                    "phone_numbers_found": ["string", ...], // List of phone numbers. Empty list [] if none found.
                    "linkedin_profiles_found": ["string", ...], // List of LinkedIn profile URLs. Empty list [] if none found.
                    "instagram_profiles_found": ["string", ...], // List of Instagram profiles (e.g., "@username"). Empty list [] if none found.
                    "facebook_profiles_found": ["string", ...], // List of Facebook profile URLs. Empty list [] if none found.
                    "twitter_x_profiles_found": ["string", ...], // List of Twitter/X handles (e.g., "@username"). Empty list [] if none found.
                    "suggested_search_queries": ["string", ...], // List of up to 3 search suggestions. Empty list [] if no clear suggestions.
                    "confidence_score": "float | null", // Confidence score (0.0 to 1.0) or null if not applicable.
                    "extraction_summary": "string | null" // Summary of the extraction process or null.
                }}
            """

            final_prompt = prompt_template.format(
                company_name=input_data.company_name,
                product_service_offered=input_data.product_service_offered,
                extracted_text=truncated_text
            ) + f"\n\nImportant: Generate your entire response, including all textual content and string values within any JSON structure, strictly in the following language: {self.output_language}. Do not include any English text unless it is part of the original input data that should be preserved as is."

            response_obj = await asyncio.to_thread(
                self.generate_llm_response,
                final_prompt,
                output_language=self.output_language
            )
            llm_response_str = response_obj.content if response_obj else None

            if not llm_response_str:
                self.logger.error(f"❌ LLM call returned no response for contact extraction for {input_data.company_name}")
                output = ContactExtractionOutput(error_message="LLM call returned no response.")
                duration = time.time() - start_time
                await self._emit_event("agent_end", {"agent_name": self.name, "job_id": job_id, "lead_id": lead_id, "duration": duration, "output": output.model_dump()})
                return output

            self.logger.debug(f"✅ LLM returned response for {input_data.company_name}, length: {len(llm_response_str)}")
            parsed_output = self.parse_llm_json_response(llm_response_str, ContactExtractionOutput)

            if parsed_output.error_message:
                 self.logger.warning(f"⚠️ {self.name} JSON parsing failed for {input_data.company_name}. Error: {parsed_output.error_message}. Raw response: {llm_response_str[:500]}")
                 duration = time.time() - start_time
                 await self._emit_event("agent_end", {"agent_name": self.name, "job_id": job_id, "lead_id": lead_id, "duration": duration, "output": parsed_output.model_dump()})
                 return parsed_output

            self.logger.info(f"✅ Contact extraction successful for {input_data.company_name}")
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

    class MockLLMClient(LLMClientBase): # Assuming LLMClientBase is correctly imported/defined
        def __init__(self, api_key: str = "mock_key", **kwargs):
            # super().__init__(api_key) # Depends on LLMClientBase
            self.api_key = api_key

        def generate_text_response(self, prompt: str, output_language: str = "en-US") -> Optional[str]:
            logger.debug(f"MockLLMClient received prompt (lang: {output_language}):\n{prompt[:700]}...")
            if f"strictly in the following language: {output_language}" not in prompt:
                 logger.error(f"Language instruction for '{output_language}' missing in prompt!")

            if "Test Company Alpha" in prompt:
                # Example response in English
                return json.dumps({
                    "emails_found": ["contact@alpha.com", "sales@alpha.com"],
                    "phone_numbers_found": ["+1 415 555-0100"],
                    "linkedin_profiles_found": ["linkedin.com/company/alpha-inc", "linkedin.com/in/ceoalpha"],
                    "instagram_profiles_found": ["@alpha_inc_official"],
                    "facebook_profiles_found": ["facebook.com/alphainc"],
                    "twitter_x_profiles_found": ["@AlphaIncGlobal"],
                    "suggested_search_queries": ["Contact Sales Director Test Company Alpha", "Test Company Alpha marketing team jobs"],
                    "confidence_score": 0.9,
                    "extraction_summary": "Successful extraction. Found multiple contacts and social profiles. Clear text."
                })
            elif "Test Company Beta" in prompt:
                return '{"emails_found": ["info@beta.com"], "instagram_profiles_found": ["@beta_co"], "confidence_score": 0.5, "extraction_summary": "Partial.", "suggested_search_queries": []}' # Malformed on purpose (missing quote before suggested)
            elif "Test Company Gamma" in prompt:
                return json.dumps({
                    "emails_found": [],
                    "phone_numbers_found": [],
                    "linkedin_profiles_found": [],
                    "instagram_profiles_found": [],
                    "facebook_profiles_found": [],
                    "twitter_x_profiles_found": [],
                    "suggested_search_queries": ["Investment Test Company Gamma", "News Test Company Gamma"],
                    "confidence_score": 0.2,
                    "extraction_summary": "No direct contacts found in text. Search suggestions for further investigation."
                })
            return json.dumps({
                    "emails_found": [], "phone_numbers_found": [], "linkedin_profiles_found": [],
                    "instagram_profiles_found": [], "facebook_profiles_found": [], "twitter_x_profiles_found": [],
                    "suggested_search_queries": ["Contact {company_name}"], "confidence_score": 0.1, "extraction_summary": "Very limited information."
            })
    
    logger.info("Running mock tests for ContactExtractionAgent...")
    mock_llm = MockLLMClient(api_key="mock_llm_key")
    agent = ContactExtractionAgent(
        name="TestContactExtractionAgent",
        description="Test Agent for Contact Extraction",
        llm_client=mock_llm,
        output_language="en-US" # Testing with English
        )

    # Test Case 1: Valid JSON response
    input_alpha = ContactExtractionInput(
        extracted_text="Test Company Alpha is a leader in AI. Contact us at contact@alpha.com or sales@alpha.com. Call +1 (415) 555-0100. Follow us on Instagram @alpha_inc_official, LinkedIn /company/alpha-inc and /in/ceoalpha, FB facebook.com/alphainc, X @AlphaIncGlobal.",
        company_name="Test Company Alpha",
        product_service_offered="AI Solutions for B2B" # English
    )
    output_alpha = agent.process(input_alpha)
    logger.info(f"\nTest Case 1 (Alpha - Valid JSON):")
    logger.info(f"  Output: {output_alpha.model_dump_json(indent=2)}")
    assert output_alpha.error_message is None
    assert output_alpha.emails_found == ["contact@alpha.com", "sales@alpha.com"]
    assert output_alpha.instagram_profiles_found == ["@alpha_inc_official"]
    assert output_alpha.linkedin_profiles_found == ["linkedin.com/company/alpha-inc", "linkedin.com/in/ceoalpha"]
    assert output_alpha.confidence_score == 0.9
    assert "Successful extraction" in output_alpha.extraction_summary

    # Test Case 2: Malformed JSON response
    input_beta = ContactExtractionInput(
        extracted_text="Info at info@beta.com, Insta @beta_co. Test Company Beta focuses on cloud services.",
        company_name="Test Company Beta",
        product_service_offered="Cloud Services for SMBs" # English
    )
    output_beta = agent.process(input_beta)
    logger.info(f"\nTest Case 2 (Beta - Malformed JSON):")
    logger.info(f"  Output: {output_beta.model_dump_json(indent=2)}")
    assert output_beta.error_message is not None
    assert "JSON parsing failed" in output_beta.error_message or "LLM response was not valid JSON" in output_beta.error_message

    # Test Case 3: Valid JSON, no contacts found
    input_gamma = ContactExtractionInput(
        extracted_text="Test Company Gamma makes widgets. No contact info here.",
        company_name="Test Company Gamma",
        product_service_offered="High-Quality Widgets" # English
    )
    output_gamma = agent.process(input_gamma)
    logger.info(f"\nTest Case 3 (Gamma - No Contacts):")
    logger.info(f"  Output: {output_gamma.model_dump_json(indent=2)}")
    assert output_gamma.error_message is None
    assert output_gamma.emails_found == []
    assert output_gamma.instagram_profiles_found == []
    assert output_gamma.confidence_score == 0.2
    assert len(output_gamma.suggested_search_queries) > 0
    assert "No direct contacts found" in output_gamma.extraction_summary
    
    logger.info("\nAll mock tests for ContactExtractionAgent completed.")
