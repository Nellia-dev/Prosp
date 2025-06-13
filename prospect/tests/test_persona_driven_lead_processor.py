"""
Test script for the PersonaDrivenLeadProcessor.
"""

import asyncio
import uuid
from typing import Dict, Any

from loguru import logger

# Assuming necessary imports from your project structure
from prospect.agents.persona_driven_lead_processor import PersonaDrivenLeadProcessor
from prospect.data_models.lead_structures import (
    AnalyzedLead,
    ValidatedLead,
    SiteData,
    GoogleSearchData,
    LeadAnalysis,
    ExtractionStatus,
    FinalProspectPackage
)
from prospect.core_logic.llm_client import LLMClientFactory, LLMProvider


# --- Mock Data ---
def get_mock_analyzed_lead(url: str = "http://example.com", company_name: str = "Example Corp") -> AnalyzedLead:
    """Creates a mock AnalyzedLead object for testing."""
    return AnalyzedLead(
        validated_lead=ValidatedLead(
            site_data=SiteData(
                url=url,
                google_search_data=GoogleSearchData(
                    title=f"{company_name} - Innovative Solutions",
                    link=url,
                    snippet=f"{company_name} offers cutting-edge solutions for modern businesses."
                ),
                extracted_text_content=f"Welcome to {company_name}. We are leaders in innovation. Our services include X, Y, Z. We solve problems like A, B, C.",
                extraction_status_message=ExtractionStatus.SUCCESS.value
            ),
            is_valid=True,
            extraction_successful=True,
            cleaned_text_content=f"Welcome to {company_name}. We are leaders in innovation. Our services include X, Y, Z. We solve problems like A, B, C."
        ),
        analysis=LeadAnalysis(
            company_sector="Technology",
            main_services=["X", "Y", "Z"],
            potential_challenges=["A", "B", "C"],
            company_size_estimate="Medium",
            relevance_score=0.8,
            general_diagnosis=f"{company_name} is a promising lead in the tech sector.",
            opportunity_fit="High potential for our services."
        ),
        product_service_context="AI-powered sales automation"
    )

async def test_persona_driven_pipeline():
    """
    Tests the full pipeline of PersonaDrivenLeadProcessor.
    """
    logger.info("🧪 Starting test for PersonaDrivenLeadProcessor...")

    # Initialize LLM Client (using a mock or a real one if configured)
    # For a real test, ensure GEMINI_API_KEY is set in your .env
    try:
        llm_client = LLMClientFactory.create_from_env(LLMProvider.GEMINI)
        logger.info("🤖 Using real Gemini LLM Client for test.")
    except ValueError:
        logger.warning("⚠️  GEMINI_API_KEY not found. LLM calls will not be real. Using a placeholder.")
        # You might want to implement a mock LLM client here for offline tests
        # For now, this will likely fail if the key isn't set, as agents expect a client.
        # This test is more of an integration test.
        llm_client = None # Or a mock client
        if not llm_client:
            logger.error("❌ Mock LLM client not implemented, and real client failed. Test cannot proceed meaningfully.")
            return


    # Initialize the processor
    processor = PersonaDrivenLeadProcessor(
        llm_client=llm_client,
        product_service_context="AI-driven B2B sales automation and lead generation"
    )
    logger.info(f"✅ {processor.name} initialized.")

    # Create mock input
    mock_lead_input = get_mock_analyzed_lead(
        url="http://techinnovators.com",
        company_name="Tech Innovators Inc."
    )
    logger.info(f"📊 Mock input created for: {mock_lead_input.validated_lead.site_data.url}")

    # Execute the pipeline
    try:
        logger.info("🚀 Executing persona-driven pipeline...")
        final_package: FinalProspectPackage = await processor.execute_async(mock_lead_input)
        logger.success(f"🎉 Pipeline execution completed for {mock_lead_input.validated_lead.site_data.url}!")

        # --- Assertions and Checks ---
        assert final_package is not None, "Final package should not be None"
        assert isinstance(final_package, FinalProspectPackage), "Output should be FinalProspectPackage"

        # Check Persona
        persona = final_package.lead_with_strategy.lead_with_persona.persona
        assert persona is not None, "Persona should be generated"
        assert persona.fictional_name != "João Silva", "Persona name should be more specific than default" # Default fallback check
        logger.info(f"👤 Persona: {persona.fictional_name} ({persona.likely_role})")

        # Check Strategy
        strategy = final_package.lead_with_strategy.strategy
        assert strategy is not None, "Strategy should be generated"
        assert strategy.primary_channel is not None, "Strategy primary channel should be set"
        logger.info(f"📈 Strategy: Primary Channel - {strategy.primary_channel.value}, Goal - {strategy.first_interaction_goal}")

        # Check Message
        message = final_package.personalized_message
        assert message is not None, "Personalized message should be crafted"
        assert len(message.message_body) > 20, "Message body should have content"
        logger.info(f"✉️ Message: Channel - {message.channel.value}, Subject - '{message.subject_line}', CTA - '{message.call_to_action}'")
        
        logger.info(f"✅ All assertions passed for {processor.name}!")

    except Exception as e:
        logger.error(f"❌ Test failed during pipeline execution: {e}")
        logger.error(traceback.format_exc())
        assert False, f"Pipeline execution error: {e}"

if __name__ == "__main__":
    # Setup for running the async test
    # Load .env file from prospect directory if it exists, to get API keys
    from dotenv import load_dotenv
    import os
    # Go up one level from prospect/tests to prospect/
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(dotenv_path):
        logger.info(f"🔑 Loading .env file from: {dotenv_path}")
        load_dotenv(dotenv_path)
    else:
        logger.warning(f"⚠️  .env file not found at {dotenv_path}. Real LLM calls might fail if keys not in environment.")

    asyncio.run(test_persona_driven_pipeline())
