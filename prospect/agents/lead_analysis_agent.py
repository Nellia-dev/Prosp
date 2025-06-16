"""
Lead Analysis Agent - Analyzes lead data to extract insights about the company.
"""

import json
from typing import Optional, Dict, Any, List
from loguru import logger

from agents.base_agent import BaseAgent
from data_models.lead_structures import (
    ValidatedLead, 
    AnalyzedLead, 
    LeadAnalysis,
    ExtractionStatus
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
    
    def __init__(self, name: str, description: str, llm_client: Optional[object] = None, product_service_context: str = "", output_language: str = "en-US", **kwargs):
        """
        Initialize the Lead Analysis Agent.
        
        Args:
            name: The name of the agent.
            description: A description of the agent.
            llm_client: An optional LLM client.
            product_service_context: Description of the product/service being offered
            output_language: The desired language for the LLM response (e.g., "en-US", "pt-BR").
            **kwargs: Additional arguments for BaseAgent
        """
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)
        self.product_service_context = product_service_context
        self.output_language = output_language
    
    def process(self, input_data: ValidatedLead) -> AnalyzedLead:
        """
        Process validated lead data to generate analysis.
        
        Args:
            input_data: ValidatedLead object
            
        Returns:
            AnalyzedLead object with complete analysis
        """
        logger.info(f"Analyzing lead: {input_data.site_data.url}")
        
        # Check if we have sufficient content for full analysis
        has_content = (
            input_data.extraction_successful and
            (input_data.cleaned_text_content or input_data.site_data.extracted_text_content)
        ) or (
            input_data.site_data.google_search_data and
            input_data.site_data.google_search_data.snippet
        )
        
        if not has_content:
            logger.warning(f"Lead has insufficient data for full analysis, generating limited analysis")
            analysis = self._generate_limited_analysis(input_data)
        else:
            logger.info(f"Lead has sufficient data for full analysis")
            # Generate full analysis using LLM
            analysis = self._generate_full_analysis(input_data)
        
        # Create and return analyzed lead
        return AnalyzedLead(
            validated_lead=input_data,
            analysis=analysis,
            product_service_context=self.product_service_context
        )
    
    def _generate_full_analysis(self, lead: ValidatedLead) -> LeadAnalysis:
        """Generate comprehensive analysis for leads with successful extraction"""
        
        # Prepare data for LLM
        lead_data_for_prompt = {
            "url": str(lead.site_data.url),
            "google_search_snippet": lead.site_data.google_search_data.snippet if lead.site_data.google_search_data else None,
            "google_search_title": lead.site_data.google_search_data.title if lead.site_data.google_search_data else None,
            "extracted_web_content": lead.cleaned_text_content or lead.site_data.extracted_text_content, # Prioritize cleaned text
            "extraction_status_message": lead.site_data.extraction_status_message,
            "extraction_successful": lead.extraction_successful
        }
        
        prompt = self._create_analysis_prompt(lead_data_for_prompt, self.output_language)
        
        try:
            # Generate analysis using LLM
            response_text = self.generate_llm_response(prompt, output_language=self.output_language)
            
            # Try to parse as JSON first
            try:
                # The parse_llm_json_response method should handle potential markdown ```json ... ```
                analysis_dict = self.parse_llm_json_response(response_text, None)
                if analysis_dict is None: # If parse_llm_json_response returns None due to parsing issue
                    logger.warning("LLM response was not valid JSON after attempting to parse. Falling back to text parsing.")
                    analysis_dict = self._parse_text_analysis_to_dict(response_text) # Try text parsing to dict
                return self._create_lead_analysis_from_dict(analysis_dict)
            except ValueError as ve: # Catch explicit JSON parsing errors if parse_llm_json_response raises it
                logger.warning(f"JSON parsing failed with ValueError: {ve}. Falling back to text parsing.")
                analysis_dict = self._parse_text_analysis_to_dict(response_text) # Try text parsing to dict
                return self._create_lead_analysis_from_dict(analysis_dict)
                
        except Exception as e:
            logger.error(f"Error generating analysis for {lead.site_data.url}: {e}", exc_info=True)
            # Return a basic analysis on error
            return self._generate_fallback_analysis(lead)
    
    def _generate_limited_analysis(self, lead: ValidatedLead) -> LeadAnalysis:
        """Generate limited analysis based on Google search data only"""
        
        google_data = lead.site_data.google_search_data
        
        if not google_data:
            return self._generate_fallback_analysis(lead)
        
        # Try to extract basic information from title and snippet
        title = google_data.title or ""
        snippet = google_data.snippet or ""
        
        # Simple sector detection based on keywords
        sector = self._detect_sector_from_text(f"{title} {snippet}")
        
        return LeadAnalysis(
            company_sector=sector,
            main_services=["Information not available - extraction failed"],
            recent_activities=[],
            potential_challenges=[
                "Digital presence may need improvement (website access issues)",
                "Possible need for technical website optimization"
            ],
            company_size_estimate="Not determined",
            company_culture_values="Not determined",
            relevance_score=0.3,  # Lower score due to limited data
            general_diagnosis=f"Limited analysis due to extraction failure. Based only on: {title}",
            opportunity_fit=f"Evaluate with caution. If {self.product_service_context} solves digital presence or site data dependency issues, there might be an opportunity."
        )
    
    def _generate_fallback_analysis(self, lead: ValidatedLead) -> LeadAnalysis:
        """Generate fallback analysis when all else fails"""
        return LeadAnalysis(
            company_sector="Not Identified",
            main_services=["Not Identified"],
            recent_activities=[],
            potential_challenges=["Insufficient data for detailed analysis."],
            company_size_estimate="Not Determined",
            company_culture_values="Not Determined",
            relevance_score=0.1, # Minimal score for fallback
            general_diagnosis="Analysis could not be performed due to insufficient data or processing error.",
            opportunity_fit="Could not determine fit with product/service due to lack of data."
        )
    
    def _create_analysis_prompt(self, lead_data_for_prompt: Dict[str, Any], output_language: str) -> str:
        """
        Create the prompt for LLM analysis.
        Prompt is now in English and includes language localization instruction.
        """
        # Prepare lead_data JSON string for embedding in the prompt
        # Ensure ensure_ascii=False for proper handling of non-ASCII characters
        lead_data_json_str = json.dumps(lead_data_for_prompt, indent=2, ensure_ascii=False)

        return f"""
You are a Senior Market Intelligence Analyst, specializing in evaluating B2B companies to identify potential customers.
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
            # Create a LeadAnalysis that indicates failure or insufficient data.
            return LeadAnalysis( # Fallback strings now in English
                company_sector="Not Identified (parsing error)",
                main_services=["Not Identified (parsing error)"],
                relevance_score=0.0,
                general_diagnosis="Failed to process LLM response or insufficient data.",
                opportunity_fit="Could not determine fit due to parsing error."
            )

        return LeadAnalysis( # Default strings now in English
            company_sector=analysis_dict.get("company_sector", "Not Specified"),
            main_services=analysis_dict.get("main_services") if isinstance(analysis_dict.get("main_services"), list) else ["Not Identified"],
            recent_activities=analysis_dict.get("recent_activities") if isinstance(analysis_dict.get("recent_activities"), list) else [],
            potential_challenges=analysis_dict.get("potential_challenges") if isinstance(analysis_dict.get("potential_challenges"), list) else [],
            company_size_estimate=analysis_dict.get("company_size_estimate", "Not Determined"),
            company_culture_values=analysis_dict.get("company_culture_values", "Could not determine"),
            relevance_score=float(analysis_dict.get("relevance_score", 0.0)), # Ensure float
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

        # Simplified extraction - this is very basic and error-prone
        # It's better to improve the prompt to ensure JSON output

        def extract_value(key_pattern: str, text: str, text_lower: str) -> Optional[str]:
            try:
                match = re.search(f"{key_pattern}\\s*:\\s*(.+)", text, re.IGNORECASE)
                if match:
                    return match.group(1).strip().split('\n')[0] # Take first line after key
            except Exception:
                pass # Ignore regex errors
            return None

        analysis_dict["company_sector"] = extract_value("company_sector", response_text, response_lower) or \
                                          extract_value("sector", response_text, response_lower) or \
                                          "Not Specified (fallback)"
        
        # For lists, this is even harder with simple regex from unstructured text
        analysis_dict["main_services"] = [] # Default to empty list
        analysis_dict["recent_activities"] = []
        analysis_dict["potential_challenges"] = []

        analysis_dict["company_size_estimate"] = extract_value("company_size_estimate", response_text, response_lower) or \
                                                 extract_value("company size", response_text, response_lower) or \
                                                 "Not Determined (fallback)"
        
        analysis_dict["company_culture_values"] = extract_value("company_culture_values", response_text, response_lower) or \
                                                  extract_value("culture and values", response_text, response_lower) or \
                                                  "Could not determine (fallback)"
        
        score_str = extract_value("relevance_score", response_text, response_lower)
        if score_str:
            try:
                analysis_dict["relevance_score"] = float(re.search(r"(\d\.?\d*)", score_str).group(1))
            except: # pylint: disable=bare-except
                analysis_dict["relevance_score"] = 0.1 # Fallback score
        else:
            analysis_dict["relevance_score"] = 0.1

        analysis_dict["general_diagnosis"] = extract_value("general_diagnosis", response_text, response_lower) or \
                                             "Limited diagnosis (parsing fallback)"
        
        analysis_dict["opportunity_fit"] = extract_value("opportunity_fit", response_text, response_lower) or \
                                           "Fit not determined (parsing fallback)"
        
        logger.debug(f"Rudimentary text parsing extracted: {analysis_dict}")
        return analysis_dict

    # This method is kept as it's used by _generate_limited_analysis
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