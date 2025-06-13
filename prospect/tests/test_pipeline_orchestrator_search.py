import asyncio
import uuid
import os
from unittest import mock, IsolatedAsyncioTestCase # Using IsolatedAsyncioTestCase for async tests
from typing import Dict, Any

from dotenv import load_dotenv
from loguru import logger

# Adjust import to the correct PipelineOrchestrator
from prospect.pipeline_orchestrator import PipelineOrchestrator
from prospect import pipeline_orchestrator as pipeline_orchestrator_module # For direct patching
from prospect.event_models import PipelineStartEvent # To check event data

# Define a sample business context, similar to other test files
# Key 'tavily_api_key' might be needed if ADK1 agent uses it directly,
# though for this test, ADK1 calls are mocked.
SAMPLE_BUSINESS_CONTEXT_BASE: Dict[str, Any] = {
    "business_description": "Test Business Description for Search",
    "product_service_description": "Platform for testing search query propagation",
    "value_proposition": "Ensuring search queries reach ADK agents",
    "ideal_customer": "Developers writing tests",
    "industry_focus": ["Software Development", "Testing"],
    "pain_points": ["Incorrect query propagation", "Tests not specific enough"],
    "competitors_list_str": "None", # Simplified for this test
    "tavily_api_key": os.getenv("TAVILY_API_KEY", "dummy_tavily_key_if_not_set"), # Mocked anyway
    # search_query and max_leads_to_generate will be overridden per test
}

class TestPipelineOrchestratorSearch(IsolatedAsyncioTestCase):

    async def test_search_query_propagation_in_pipeline(self):
        logger.info("🚀 Starting test: test_search_query_propagation_in_pipeline (CORE_LIBRARIES_AVAILABLE directly patched)")

        original_core_libs_available = pipeline_orchestrator_module.CORE_LIBRARIES_AVAILABLE
        original_project_modules_available = pipeline_orchestrator_module.PROJECT_MODULES_AVAILABLE
        pipeline_orchestrator_module.CORE_LIBRARIES_AVAILABLE = True
        pipeline_orchestrator_module.PROJECT_MODULES_AVAILABLE = True # Patch this as well

        # For debugging
        logger.info(f"Value of CORE_LIBRARIES_AVAILABLE during test: {pipeline_orchestrator_module.CORE_LIBRARIES_AVAILABLE}")
        logger.info(f"Value of PROJECT_MODULES_AVAILABLE during test: {pipeline_orchestrator_module.PROJECT_MODULES_AVAILABLE}")
        self.assertTrue(pipeline_orchestrator_module.CORE_LIBRARIES_AVAILABLE, "CORE_LIBRARIES_AVAILABLE should be True")
        self.assertTrue(pipeline_orchestrator_module.PROJECT_MODULES_AVAILABLE, "PROJECT_MODULES_AVAILABLE should be True")

        try:
            with mock.patch('prospect.pipeline_orchestrator.SentenceTransformer', create=True) as MockSentenceTransformer, \
                 mock.patch('prospect.pipeline_orchestrator.AdvancedProspectProfiler', create=True) as MockAdvancedProspectProfiler, \
                 mock.patch('prospect.pipeline_orchestrator.faiss', create=True) as MockFaiss, \
                 mock.patch('prospect.pipeline_orchestrator.LLMClientFactory', create=True) as MockLLMClientFactory, \
                 mock.patch('prospect.pipeline_orchestrator.LeadIntakeAgent', create=True) as MockLeadIntakeAgent, \
                 mock.patch('prospect.pipeline_orchestrator.LeadAnalysisAgent', create=True) as MockLeadAnalysisAgent, \
                 mock.patch('prospect.pipeline_orchestrator.EnhancedLeadProcessor', create=True) as MockEnhancedLeadProcessor, \
                 mock.patch('prospect.pipeline_orchestrator.LeadAnalysisGenerationAgent', create=True) as MockLeadAnalysisGenerationAgent, \
                 mock.patch('prospect.pipeline_orchestrator.B2BPersonaCreationAgent', create=True) as MockB2BPersonaCreationAgent, \
                 mock.patch('prospect.pipeline_orchestrator.find_and_extract_structured_leads', create=True) as mock_find_extract, \
                 mock.patch('prospect.pipeline_orchestrator.search_and_qualify_leads', create=True) as mock_search_qualify:

                # Configure the mocks for classes instantiated in PipelineOrchestrator.__init__
                MockLLMClientFactory.create_from_env.return_value = mock.MagicMock()
                # For SentenceTransformer, the .encode().astype() chain is called.
                mock_encode_result = mock.MagicMock()
                mock_encode_result.astype.return_value = "dummy_embeddings" # Or whatever type is suitable
                MockSentenceTransformer.return_value.encode.return_value = mock_encode_result

                MockAdvancedProspectProfiler.return_value = mock.MagicMock() # Simple mock for now
                MockFaiss.IndexFlatL2.return_value = mock.MagicMock() # Mock the FAISS index part

                unique_search_query = f"ultra_specific_keyword_for_tavily_search_test_{uuid.uuid4()}"
                test_job_id = str(uuid.uuid4())
                test_user_id = "test_user_search_prop"

                test_business_context = {
                    **SAMPLE_BUSINESS_CONTEXT_BASE,
                    "search_query": unique_search_query,
                    "max_leads_to_generate": 1
                }

                captured_queries_find_extract = []
                captured_queries_search_qualify = []

                def side_effect_find_extract(query: str, max_leads: int):
                    logger.debug(f"Mock find_and_extract_structured_leads called with query: {query}, max_leads: {max_leads}")
                    captured_queries_find_extract.append(query)
                    # Return a valid structure that the orchestrator expects (list of dicts)
                    return [{"company_name": "Mock Lead from FindExtract", "website": "http://findextract.mock.com", "description": "Test"}]

                def side_effect_search_qualify(query: str, max_leads: int):
                    logger.debug(f"Mock search_and_qualify_leads called with query: {query}, max_leads: {max_leads}")
                    captured_queries_search_qualify.append(query)
                    return [{"company_name": "Mock Lead from SearchQualify", "website": "http://searchqualify.mock.com", "description": "Test"}]

                mock_find_extract.side_effect = side_effect_find_extract
                mock_search_qualify.side_effect = side_effect_search_qualify

                # Ensure mocks return something iterable, even if ADK1 fails and falls back
                mock_find_extract.return_value = [{"company_name": "Mock Lead FindExtract Default", "website": "http://findextract-default.mock.com"}]
                mock_search_qualify.return_value = [{"company_name": "Mock Lead SearchQualify Default", "website": "http://searchqualify-default.mock.com"}]


                orchestrator = PipelineOrchestrator(
                    business_context=test_business_context,
                    user_id=test_user_id,
                    job_id=test_job_id
                )

                pipeline_start_event_found = False
                events_processed_count = 0

                async for event_dict in orchestrator.execute_streaming_pipeline():
                    events_processed_count += 1
                    logger.debug(f"Received event: {event_dict.get('event_type')}")
                    if event_dict.get("event_type") == "pipeline_start": # Corrected event type check
                        pipeline_start_event_found = True
                        # Validate the initial query in PipelineStartEvent
                        self.assertEqual(event_dict.get("initial_query"), unique_search_query,
                                         "PipelineStartEvent did not contain the correct initial_query.")
                        logger.info(f"✅ PipelineStartEvent found with correct initial_query: {unique_search_query}")

                    # Limit processing for test speed, assuming relevant events occur early
                    if events_processed_count > 10 and pipeline_start_event_found and (mock_find_extract.called or mock_search_qualify.called):
                         logger.warning("Limiting event processing for test speed after key checks.")
                         break

                logger.info(f"🏁 Pipeline execution finished. Processed {events_processed_count} events.")
                self.assertTrue(pipeline_start_event_found, "PipelineStartEvent was not found.")

                # Check if at least one of the ADK1 search functions was called
                was_find_extract_called = mock_find_extract.called
                was_search_qualify_called = mock_search_qualify.called
                self.assertTrue(was_find_extract_called or was_search_qualify_called,
                                "Neither find_and_extract_structured_leads nor search_and_qualify_leads was called.")
                logger.info(f"📞 Mock call status: find_and_extract called: {was_find_extract_called}, search_and_qualify called: {was_search_qualify_called}")

                # Verify the query captured by the mocks
                if was_find_extract_called:
                    self.assertGreater(len(captured_queries_find_extract), 0, "find_and_extract_structured_leads was called but no query was captured.")
                    self.assertEqual(captured_queries_find_extract[0], unique_search_query,
                                     f"Captured query '{captured_queries_find_extract[0]}' in find_and_extract does not match expected '{unique_search_query}'.")
                    logger.info(f"✅ Query correctly captured by find_and_extract_structured_leads: {captured_queries_find_extract[0]}")

                # If find_and_extract fails (or returns empty), search_and_qualify might be called as fallback
                # The current logic in _search_with_adk1_agent tries find_and_extract first, then search_and_qualify on exception.
                # If find_and_extract returns an empty list but no exception, search_and_qualify might not be called.
                # For this test, we primarily care that the query reached the first attempted ADK1 call.
                # If you need to test fallback, you'd make mock_find_extract raise an exception.

                # For now, we just log if the fallback was hit with the query
                if was_search_qualify_called:
                    self.assertGreater(len(captured_queries_search_qualify), 0, "search_and_qualify_leads was called but no query was captured.")
                    self.assertEqual(captured_queries_search_qualify[0], unique_search_query,
                                     f"Captured query '{captured_queries_search_qualify[0]}' in search_and_qualify does not match expected '{unique_search_query}'.")
                    logger.info(f"✅ Query correctly captured by search_and_qualify_leads (fallback): {captured_queries_search_qualify[0]}")
        finally:
            # Restore the original values
            pipeline_orchestrator_module.CORE_LIBRARIES_AVAILABLE = original_core_libs_available
            pipeline_orchestrator_module.PROJECT_MODULES_AVAILABLE = original_project_modules_available
            logger.info(f"Restored CORE_LIBRARIES_AVAILABLE to: {original_core_libs_available}")
            logger.info(f"Restored PROJECT_MODULES_AVAILABLE to: {original_project_modules_available}")


if __name__ == "__main__":
    # Setup environment for testing (e.g., loading .env)
    # This path assumes the test is run from the project root or 'prospect/tests/' directory
    # Adjust if your execution context is different.
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env') # From prospect/tests/ to project root
    if not os.path.exists(dotenv_path):
         # Try path assuming execution from project root where 'prospect' is a subdir
        dotenv_path_alt = os.path.join(os.path.dirname(__file__), '..', '.env') # From prospect/tests to prospect/
        if os.path.exists(dotenv_path_alt):
            dotenv_path = dotenv_path_alt
        else:
            # Try path assuming execution from project root where '.env' is
            dotenv_path_project_root = os.path.join(os.path.dirname(__file__), '.env')
            if os.path.exists(dotenv_path_project_root):
                 dotenv_path = dotenv_path_project_root
            else:
                dotenv_path = None


    if dotenv_path and os.path.exists(dotenv_path):
        logger.info(f"🔑 Loading .env file from: {os.path.abspath(dotenv_path)}")
        load_dotenv(dotenv_path)
    else:
        logger.warning(f"⚠️ .env file not found at various attempted paths including '{os.path.abspath(dotenv_path)}' (if resolved) or other default locations. Real LLM calls might fail if keys not in environment.")

    # Ensure API keys are loaded for sub-agents if real LLM calls are made by non-mocked parts
    if not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
        logger.warning("GEMINI_API_KEY or GOOGLE_API_KEY not set. This is fine if all LLM calls are mocked.")
    if not os.getenv("TAVILY_API_KEY"):
        logger.warning("TAVILY_API_KEY not set. This is fine as ADK1 calls are mocked for this test.")

    # Standard unittest execution
    asyncio.run(unittest.main())
