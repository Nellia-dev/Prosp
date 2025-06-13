"""
Test script for the HybridPipelineOrchestrator.
"""

import asyncio
import uuid
from typing import Dict, Any

from loguru import logger
from dotenv import load_dotenv
import os

# Adjust imports based on your project structure
from prospect.hybrid_pipeline_orchestrator import HybridPipelineOrchestrator
from prospect.data_models.lead_structures import (
    AnalyzedLead,
    ValidatedLead,
    SiteData,
    GoogleSearchData,
    LeadAnalysis,
    ExtractionStatus,
    ComprehensiveProspectPackage,
    FinalProspectPackage
)
from prospect.core_logic.llm_client import LLMClientFactory, LLMProvider

# --- Mock Data & Setup ---
# Use the same SAMPLE_BUSINESS_CONTEXT and SAMPLE_LEADS from test_rag_pipeline_integration.py
# For brevity, assuming they are accessible or redefined here.
SAMPLE_BUSINESS_CONTEXT = {
    "business_description": "Hybrid AI solutions for enterprise",
    "product_service_description": "Platform for deploying and managing hybrid AI models",
    "value_proposition": "Optimize AI workloads across cloud and on-premise",
    "ideal_customer": "Large enterprises with existing AI/ML infrastructure",
    "industry_focus": ["Finance", "Healthcare", "Manufacturing"],
    "pain_points": ["High cloud AI costs", "Data sovereignty issues", "Slow on-premise model deployment"],
    "competitors_list_str": "AWS Sagemaker, Azure ML, Google Vertex AI", # For EnhancedLeadProcessor
    "tavily_api_key": os.getenv("TAVILY_API_KEY"), # Ensure Tavily key is available
    "search_query": "hybrid AI platform for enterprise",
    "max_leads_to_generate": 1 # Keep low for testing
}

SAMPLE_LEAD_FOR_HYBRID_TEST = {
    "company_name": "Global Corp Solutions",
    "website": "https://globalcorp.example.com",
    "description": "Global Corp Solutions provides diverse enterprise services. We are exploring AI integration and have a dedicated AI research team. Our current infrastructure is a mix of cloud and on-premise servers. We are looking for cost-effective and secure AI deployment options."
}


def get_mock_analyzed_lead_for_hybrid(url: str, company_name: str, description: str, complexity: float = 0.5, persona_clarity: float = 0.5, data_quality: float = 0.5) -> AnalyzedLead:
    """Creates a mock AnalyzedLead with controllable characteristics for testing pipeline selection."""
    # This is a simplified mock. Real characteristic extraction would be more complex.
    # The scores here are just to influence the AgentSelectionStrategy's mock logic.
    
    # Simulate some analysis based on characteristics
    sector = "Diversified Enterprise"
    services = ["Enterprise Solutions", "AI Integration Consulting"]
    challenges = ["Integrating new AI tech", "Managing hybrid infrastructure"]
    if complexity > 0.7:
        challenges.append("Complex data pipelines")
        services.append("Advanced AI Model Deployment")
    
    general_diagnosis = f"{company_name} shows potential. "
    if persona_clarity < 0.4:
        general_diagnosis += "Decision-maker persona is unclear. "
    else:
        general_diagnosis += "Key decision-makers likely in IT/AI leadership. "
        
    if data_quality < 0.4:
        general_diagnosis += "Initial data quality is low, needs more enrichment."
    
    return AnalyzedLead(
        validated_lead=ValidatedLead(
            site_data=SiteData(
                url=url,
                google_search_data=GoogleSearchData(
                    title=f"{company_name} - Enterprise AI",
                    link=url,
                    snippet=description
                ),
                extracted_text_content=description,
                extraction_status_message=ExtractionStatus.SUCCESS.value if data_quality > 0.5 else ExtractionStatus.FAILED_OTHER.value
            ),
            is_valid=True,
            extraction_successful=data_quality > 0.5,
            cleaned_text_content=description
        ),
        analysis=LeadAnalysis(
            company_sector=sector,
            main_services=services,
            potential_challenges=challenges,
            company_size_estimate="Large",
            relevance_score= (complexity + persona_clarity + data_quality) / 3, # Simple average
            general_diagnosis=general_diagnosis,
            opportunity_fit="Varies based on pipeline outcome."
        ),
        product_service_context=SAMPLE_BUSINESS_CONTEXT["product_service_description"]
    )

async def run_hybrid_pipeline_test_case(lead_characteristics_scores: Dict[str, float], expected_pipeline_type: str):
    """Helper to run a test case for the hybrid orchestrator."""
    company_name = f"TestCompany_{expected_pipeline_type.replace('_','').title()}"
    lead_url = f"http://{company_name.lower()}.example.com"
    
    logger.info(f"🧪 Testing Hybrid Orchestrator with characteristics: {lead_characteristics_scores} -> expecting '{expected_pipeline_type}' pipeline")

    # Create mock AnalyzedLead based on desired characteristics for selection
    # This is a bit indirect; ideally, _get_lead_characteristics would be mocked or made more deterministic for testing.
    # For now, we craft an AnalyzedLead that *should* trigger the desired scores.
    mock_lead_input = get_mock_analyzed_lead_for_hybrid(
        url=lead_url,
        company_name=company_name,
        description=f"This is a test lead for {company_name}, designed to trigger {expected_pipeline_type} pipeline. Complexity: {lead_characteristics_scores.get('complexity_score',0.5)}, Persona Clarity: {lead_characteristics_scores.get('persona_clarity_score',0.5)}, Data Quality: {lead_characteristics_scores.get('data_quality_score',0.5)}",
        **lead_characteristics_scores # Pass scores to influence mock AnalyzedLead creation
    )

    job_id = str(uuid.uuid4())
    hybrid_orchestrator = HybridPipelineOrchestrator(
        business_context=SAMPLE_BUSINESS_CONTEXT,
        user_id="hybrid_test_user",
        job_id=job_id
    )
    
    # We need to simulate the main execution flow that calls _enrich_lead
    # For this test, we'll directly call a simplified version of what execute_streaming_pipeline does
    
    events_generated = []
    final_package_from_event = None

    # Simulate the part of execute_streaming_pipeline that calls _enrich_lead
    # This is a targeted test of the _enrich_lead's selection logic
    async for event in hybrid_orchestrator._enrich_lead(
        lead_data={"website": lead_url, "description": mock_lead_input.validated_lead.cleaned_text_content, "company_name": company_name}, # Simplified lead_data
        lead_id="test_lead_001"
    ):
        events_generated.append(event)
        if event.get("event_type") == "lead_enrichment_end" and event.get("success"):
            final_package_from_event = event.get("final_package")

    assert final_package_from_event is not None, "Lead enrichment should produce a final package."
    
    # Check if the correct pipeline was logged as selected
    pipeline_selection_logged = False
    selected_pipeline_in_log = "unknown"
    for event in events_generated:
        if event.get("event_type") == "status_update" and "Selected pipeline:" in event.get("status_message", ""):
            pipeline_selection_logged = True
            selected_pipeline_in_log = event.get("status_message").split(": ")[1]
            logger.info(f"🔍 Logged pipeline selection: {selected_pipeline_in_log}")
            break
            
    assert pipeline_selection_logged, "Pipeline selection should be logged in a StatusUpdateEvent"
    # Note: The AgentSelectionStrategy is simple. This tests if the orchestrator calls it.
    # More robust testing would mock AgentSelectionStrategy.select_pipeline_type
    # For now, we check if the logged selection contains the *expected* part of the name.
    assert expected_pipeline_type in selected_pipeline_in_log, f"Expected pipeline '{expected_pipeline_type}' but log shows '{selected_pipeline_in_log}'"

    logger.success(f"✅ Hybrid pipeline test case for '{expected_pipeline_type}' PASSED.")


async def main_hybrid_tests():
    # Test case 1: Should select 'enhanced_comprehensive'
    await run_hybrid_pipeline_test_case(
        {"complexity_score": 0.8, "persona_clarity_score": 0.7, "data_quality_score": 0.7},
        "enhanced_comprehensive"
    )
    
    # Test case 2: Should select 'persona_driven'
    await run_hybrid_pipeline_test_case(
        {"complexity_score": 0.5, "persona_clarity_score": 0.3, "data_quality_score": 0.6},
        "persona_driven"
    )

    # Test case 3: Should default to 'enhanced_comprehensive'
    await run_hybrid_pipeline_test_case(
        {"complexity_score": 0.5, "persona_clarity_score": 0.6, "data_quality_score": 0.5},
        "enhanced_comprehensive" # Default
    )

if __name__ == "__main__":
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(dotenv_path):
        logger.info(f"🔑 Loading .env file from: {dotenv_path}")
        load_dotenv(dotenv_path)
    else:
        logger.warning(f"⚠️  .env file not found at {dotenv_path}. Real LLM calls might fail if keys not in environment.")
    
    # Ensure API keys are loaded for sub-agents if real LLM calls are made
    if not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
        logger.error("❌ GEMINI_API_KEY or GOOGLE_API_KEY not set. Tests requiring LLM will likely fail or use mocks if available.")

    asyncio.run(main_hybrid_tests())
