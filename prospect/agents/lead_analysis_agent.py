"""
Lead Analysis Agent - Analyzes lead data to extract insights about the company.
"""

import json
import re
import asyncio
import time
import traceback
from typing import Optional, Dict, Any, List
from loguru import logger

from .base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase, LLMResponse
from data_models.lead_structures import (
    ValidatedLead,
    AnalyzedLead,
    LeadAnalysis,
    ExtractionStatus,
    SiteData,
    GoogleSearchData
)


class LeadAnalysisAgent(BaseAgent[ValidatedLead, AnalyzedLead]):
    """
    Agent responsible for analyzing lead data to extract:
    - Company sector and services
    - Recent activities and news
    - Potential challenges and pain points
    - Company size and culture
    - Relevance scoring
    - Opportunity fit assessment
    """

    def __init__(self, name: str, description: str, llm_client: Optional[LLMClientBase] = None, product_service_context: str = "", output_language: str = "en-US", **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)
        self.product_service_context = product_service_context
        self.output_language = output_language

    async def process(self, lead_id: str, job_id: str, input_data: ValidatedLead) -> AnalyzedLead:
        start_time = time.time()
        self.logger.info(f" LEAD ANALYSIS AGENT starting for lead {lead_id} in job {job_id}")
        await self._emit_event("agent_start", {
            "agent_name": self.name,
            "job_id": job_id,
            "lead_id": lead_id,
            "agent_description": self.description,
            "input_query": input_data.model_dump_json(indent=2)
        })

        try:
            input_data.lead_id = lead_id

            has_content = (
                input_data.extraction_successful and
                (input_data.cleaned_text_content or input_data.site_data.extracted_text_content)
            ) or (
                input_data.site_data.google_search_data and
                input_data.site_data.google_search_data.snippet
            )

            if not has_content:
                self.logger.warning(f"Lead {lead_id} has insufficient data for full analysis, generating limited analysis")
                analysis = self._generate_limited_analysis(input_data)
            else:
                self.logger.info(f"Lead {lead_id} has sufficient data for full analysis")
                analysis = await self._generate_full_analysis(input_data, lead_id=lead_id)

            if analysis and analysis.company_name:
                input_data.company_name = analysis.company_name

            final_output = AnalyzedLead(
                lead_id=lead_id,
                validated_lead=input_data,
                analysis=analysis,
                product_service_context=self.product_service_context
            )

            duration = time.time() - start_time
            await self._emit_event("agent_end", {
                "agent_name": self.name,
                "job_id": job_id,
                "lead_id": lead_id,
                "duration": duration,
                "output": final_output.model_dump()
            })
            return final_output

        except Exception as e:
            self.logger.error(f" Critical error in {self.name} for lead {lead_id}: {e}", exc_info=True)
            await self._emit_event("pipeline_error", {
                "agent_name": self.name,
                "job_id": job_id,
                "lead_id": lead_id,
                "error_message": str(e),
                "details": traceback.format_exc()
            })
            raise

    async def _generate_full_analysis(self, lead: ValidatedLead, lead_id: str) -> LeadAnalysis:
        """Generate comprehensive analysis for leads with successful extraction"""
        lead_data_for_prompt = {
            "url": str(lead.site_data.url),
            "google_search_snippet": lead.site_data.google_search_data.snippet if lead.site_data.google_search_data else None,
            "google_search_title": lead.site_data.google_search_data.title if lead.site_data.google_search_data else None,
            "extracted_web_content": lead.cleaned_text_content or lead.site_data.extracted_text_content,
            "extraction_status_message": lead.site_data.extraction_status_message,
            "extraction_successful": lead.extraction_successful
        }

        prompt = self._create_analysis_prompt(lead_data_for_prompt, self.output_language)

        try:
            response_obj = await asyncio.to_thread(
                self.generate_llm_response,
                prompt,
                output_language=self.output_language
            )
            response_text = response_obj.content if response_obj else None

            if not response_text:
                logger.warning(f"LLM call returned no response for lead ID {lead_id}")
                return self._generate_fallback_analysis(lead)

            analysis_dict = self.parse_llm_json_response(response_text, None)
            if analysis_dict is None:
                logger.warning("LLM response was not valid JSON. Falling back to text parsing.")
                analysis_dict = self._parse_text_analysis_to_dict(response_text)
            return self._create_lead_analysis_from_dict(analysis_dict)

        except Exception as e:
            logger.error(f"Error generating analysis for lead ID {lead_id} ({lead.site_data.url}): {e}", exc_info=True)
            return self._generate_fallback_analysis(lead)

    def _generate_limited_analysis(self, lead: ValidatedLead) -> LeadAnalysis:
        """Generate limited analysis based on Google search data only"""
        google_data = lead.site_data.google_search_data
        if not google_data:
            return self._generate_fallback_analysis(lead)

        title = google_data.title or ""
        snippet = google_data.snippet or ""
        sector = self._detect_sector_from_text(f"{title} {snippet}")

        return LeadAnalysis(
            company_name=title,
            company_sector=sector,
            main_services=["Not determined due to limited data"],
            recent_activities=[],
            potential_challenges=[
                "Digital presence may need improvement (website access issues)",
                "Possible need for technical website optimization"
            ],
            company_size_estimate="Not determined",
            company_culture_values="Not determined",
            relevance_score=0.3,
            general_diagnosis=f"Limited analysis due to extraction failure. Based only on: {title}",
            opportunity_fit=f"Evaluate with caution. If {self.product_service_context} solves digital presence or site data dependency issues, there might be an opportunity."
        )

    def _generate_fallback_analysis(self, lead: ValidatedLead) -> LeadAnalysis:
        """Generate fallback analysis when all else fails"""
        return LeadAnalysis(
            company_name=lead.site_data.google_search_data.title if lead.site_data.google_search_data else "Unknown",
            company_sector="Not Identified",
            main_services=["Not Identified"],
            recent_activities=[],
            potential_challenges=["Insufficient data for detailed analysis."],
            company_size_estimate="Not Determined",
            company_culture_values="Not Determined",
            relevance_score=0.1,
            general_diagnosis="Analysis could not be performed due to insufficient data or processing error.",
            opportunity_fit="Could not determine fit with product/service due to lack of data."
        )

    def _create_analysis_prompt(self, lead_data_for_prompt: Dict[str, Any], output_language: str) -> str:
        """
        Create the prompt for LLM analysis.
        Prompt is now in English and includes language localization instruction.
        """
        lead_data_json_str = json.dumps(lead_data_for_prompt, indent=2, ensure_ascii=False)

        return f"""You are a Senior Market Intelligence Analyst, specializing in evaluating B2B companies to identify potential customers.
Your primary task is to analyze the provided data about a lead and return a structured assessment in JSON format.

Our product/service is: "{self.product_service_context}"

Analyze the following lead data:
```json
{lead_data_json_str}
```

OUTPUT INSTRUCTIONS:
Respond EXCLUSIVELY with a valid JSON object, following the schema and field descriptions below.
DO NOT include ANY text, explanation, or markdown (like ```json) before or after the JSON object.
Your response must be only the JSON itself.

EXPECTED JSON SCHEMA AND FIELD DESCRIPTIONS:
{{
    "company_sector": "string | null - The company's main sector/industry (e.g., 'SaaS Technology', 'Fashion Retail', 'Financial Consulting'). If undetermined from text, use 'Not Specified'.",
    "main_services": ["string", ...] - List of main services or products offered by the company. Extract from text. If no clear information, use an empty list [].",
    "recent_activities": ["string", ...] - List of news, events, product launches, partnerships, or other recent important activities and milestones (ideally from the last 6-12 months) mentioned in the text. If none found, use an empty list [].",
    "potential_challenges": ["string", ...] - List of possible pains, challenges, or problems the company might be facing, inferred from the provided text. If none found, use an empty list [].",
    "company_size_estimate": "string | null - Estimated company size (e.g., 'Micro (1-9 employees)', 'Small (10-49 employees)', 'Medium (50-249 employees)', 'Large (250+ employees)'). Infer from clues in the text; if impossible, use 'Not Determined'.",
    "company_culture_values": "string | null - Insights into organizational culture, mission, vision, or values, if explicitly mentioned or strongly implied in the text. If not found, use 'Could not determine'.",
    "relevance_score": "float - A numeric score between 0.0 and 1.0 indicating how relevant this lead is for our product/service '{self.product_service_context}'. Consider 0.0 as totally irrelevant and 1.0 as perfectly aligned. Base this on the company's challenges, services, and sector. Be critical and objective.",
    "general_diagnosis": "string | null - A concise summary (2-3 sentences) of the company's current situation, its perceived strengths and weaknesses based on the data. If the 'extracted_web_content' field in the lead data mentions 'AI IMAGE ANALYSIS', incorporate relevant findings from that analysis here. If there isn't enough content for a diagnosis, use 'Limited diagnosis due to insufficient data.'.",
    "opportunity_fit": "string | null - Briefly explain (2-3 sentences) how our product/service '{self.product_service_context}' could specifically help this company, connecting with the identified 'potential_challenges' or needs. Justify the 'relevance_score'. If no clear fit, state so explicitly."
}}

ADDITIONAL IMPORTANT INSTRUCTIONS:
- FILL ALL JSON FIELDS according to the schema.
- For optional string fields (marked with `| null`), if information is not found, use the default string value indicated in the description (e.g., 'Not Specified', 'Not Determined') or, if you prefer and the schema implicitly allows `null` via the description, you can use `null`. However, for this exercise, prefer default strings like 'Not Specified'.
- For list fields (e.g., `main_services`), if no information is found, MANDATORILY return an empty list `[]`.
- Be objective and base your analysis STRICTLY on the information provided in the "Lead Data". DO NOT INVENT information not present in the text.
- Your final response must be ONLY the JSON object.

Important: Generate your entire response, including all textual content and string values within any JSON structure, strictly in the following language: {output_language}. Do not include any English text unless it is part of the original input data that should be preserved as is.
"""

    def _create_lead_analysis_from_dict(self, analysis_dict: Optional[Dict[str, Any]]) -> LeadAnalysis:
        """Create LeadAnalysis object from dictionary, handling potential None dictionary."""
        if analysis_dict is None:
            logger.warning("Received None for analysis_dict, creating a fallback LeadAnalysis.")
            return LeadAnalysis(
                company_sector="Not Identified (parsing error)",
                main_services=["Not Identified (parsing error)"],
                relevance_score=0.0,
                general_diagnosis="Failed to process LLM response or insufficient data.",
                opportunity_fit="Could not determine fit due to parsing error."
            )

        return LeadAnalysis(
            company_sector=analysis_dict.get("company_sector", "Not Specified"),
            main_services=analysis_dict.get("main_services", []),
            recent_activities=analysis_dict.get("recent_activities", []),
            potential_challenges=analysis_dict.get("potential_challenges", []),
            company_size_estimate=analysis_dict.get("company_size_estimate", "Not Determined"),
            company_culture_values=analysis_dict.get("company_culture_values", "Could not determine"),
            relevance_score=float(analysis_dict.get("relevance_score", 0.0)),
            general_diagnosis=analysis_dict.get("general_diagnosis", "Analysis not available"),
            opportunity_fit=analysis_dict.get("opportunity_fit", "Not determined")
        )

    def _parse_text_analysis_to_dict(self, response_text: str) -> Dict[str, Any]:
        """
        Rudimentary fallback to parse key information from text if JSON fails.
        This aims to populate a dictionary similar to what the JSON parser would.
        """
        logger.warning("Attempting rudimentary text parsing for analysis as JSON parsing failed.")
        analysis_dict = {}
        response_lower = response_text.lower()

        def extract_value(key_pattern: str, text: str, text_lower: str) -> Optional[str]:
            try:
                match = re.search(f"{key_pattern}:\s*(.+)", text, re.IGNORECASE)
                if match:
                    return match.group(1).strip().split('\n')[0]
            except Exception:
                pass
            return None

        analysis_dict["company_sector"] = extract_value("company_sector", response_text, response_lower) or "Not Specified (fallback)"
        analysis_dict["main_services"] = []
        analysis_dict["recent_activities"] = []
        analysis_dict["potential_challenges"] = []
        analysis_dict["company_size_estimate"] = extract_value("company_size_estimate", response_text, response_lower) or "Not Determined (fallback)"
        analysis_dict["company_culture_values"] = extract_value("company_culture_values", response_text, response_lower) or "Could not determine (fallback)"

        score_str = extract_value("relevance_score", response_text, response_lower)
        if score_str:
            try:
                analysis_dict["relevance_score"] = float(re.search(r"(\d\.?\d*)", score_str).group(1))
            except (ValueError, AttributeError):
                analysis_dict["relevance_score"] = 0.1
        else:
            analysis_dict["relevance_score"] = 0.1

        analysis_dict["general_diagnosis"] = extract_value("general_diagnosis", response_text, response_lower) or "Limited diagnosis (parsing fallback)"
        analysis_dict["opportunity_fit"] = extract_value("opportunity_fit", response_text, response_lower) or "Fit not determined (parsing fallback)"

        logger.debug(f"Rudimentary text parsing extracted: {analysis_dict}")
        return analysis_dict

    def _detect_sector_from_text(self, text: str) -> str:
        """Simple sector detection based on keywords (English keywords)"""
        text_lower = text.lower()
        sector_keywords = {
            "Technology": ["software", "technology", "tech", "it", "system", "app", "digital", "saas"],
            "Legal": ["legal", "lawyer", "attorney", "law firm", "advocacy"],
            "Healthcare": ["health", "medical", "hospital", "clinic", "pharmacy", "medicine"],
            "Education": ["education", "school", "university", "course", "teaching", "college"],
            "Retail": ["store", "retail", "commerce", "sale", "shop", "ecommerce"],
            "Manufacturing": ["industry", "factory", "manufacturing", "production", "industrial"],
            "Services": ["service", "consulting", "agency", "provider", "bpo"],
            "Food & Beverage": ["restaurant", "food", "beverage", "cafe", "catering"],
            "Construction": ["construction", "engineering", "building", "contractor"],
            "Real Estate": ["real estate", "property", "realty", "brokerage"]
        }

        for sector, keywords in sector_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return sector

        return "Others"

if __name__ == '__main__':
    import sys

    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    class MockLLMClient(LLMClientBase):
        def generate_llm_response(self, prompt: str, output_language: str = "en-US") -> LLMResponse:
            logger.debug(f"MockLLMClient received prompt (lang: {output_language}):\n{prompt[:400]}...")
            mock_response = {
                "company_sector": "SaaS Technology",
                "main_services": ["AI-driven analytics", "Cloud data solutions"],
                "recent_activities": ["Launched new AI model in Q2", "Secured Series B funding"],
                "potential_challenges": ["High competition in AI space", "Need to scale infrastructure"],
                "company_size_estimate": "Medium (50-249 employees)",
                "company_culture_values": "Innovation, customer-centric, data-driven.",
                "relevance_score": 0.9,
                "general_diagnosis": "A fast-growing SaaS company with strong potential.",
                "opportunity_fit": "Our services can help them scale their infrastructure efficiently."
            }
            return LLMResponse(content=json.dumps(mock_response))

    async def main():
        logger.info("Running mock test for LeadAnalysisAgent...")
        mock_llm = MockLLMClient()
        agent = LeadAnalysisAgent(
            name="TestLeadAnalysisAgent",
            description="Test Agent for Lead Analysis",
            llm_client=mock_llm,
            product_service_context="Scalable cloud infrastructure solutions"
        )

        test_lead = ValidatedLead(
            lead_id="test_lead_123",
            company_name="InnovateAI",
            site_data=SiteData(
                url="http://innovateai.com",
                google_search_data=GoogleSearchData(title="InnovateAI", snippet="Leading provider of AI solutions."),
                extraction_status=ExtractionStatus.SUCCESS
            ),
            extraction_successful=True,
            cleaned_text_content="InnovateAI is a leader in AI-driven analytics..."
        )

        analyzed_lead = await agent.process(lead_id="test_lead_123", job_id="test_job_456", input_data=test_lead)

        if analyzed_lead and analyzed_lead.analysis and analyzed_lead.analysis.relevance_score > 0.5:
            logger.success("Agent processed successfully!")
            logger.info(f"Analysis Summary: {analyzed_lead.analysis.general_diagnosis}")
            logger.info(f"Relevance Score: {analyzed_lead.analysis.relevance_score}")
            assert analyzed_lead.analysis.company_sector == "SaaS Technology"
            assert len(analyzed_lead.analysis.main_services) > 0
        else:
            logger.error("Agent processing failed or resulted in low score.")

    asyncio.run(main())