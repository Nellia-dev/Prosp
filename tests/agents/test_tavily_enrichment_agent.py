import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import json
import requests # For mocking requests.exceptions.RequestException

from agents.tavily_enrichment_agent import TavilyEnrichmentAgent, TavilyEnrichmentInput, TavilyEnrichmentOutput
from core_logic.llm_client import LLMClientBase, LLMResponse
from mcp_server.data_models import AgentExecutionStatusEnum # For asserting status

class TestTavilyEnrichmentAgent(unittest.IsolatedAsyncioTestCase): # Changed to IsolatedAsyncioTestCase

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        # BaseAgent.generate_llm_response is async, so mock it as AsyncMock
        self.mock_llm_client.generate_llm_response = AsyncMock()
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0, "llm_calls": 0, "llm_usage": []}
        self.mock_llm_client.update_usage_stats = MagicMock()


        self.agent = TavilyEnrichmentAgent(
            llm_client=self.mock_llm_client,
            tavily_api_key="test_tavily_key"
        )
        # Mock the internal _search_with_tavily as it's async and makes http calls
        self.agent._search_with_tavily = AsyncMock()


    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_with_tavily_search_and_summarization(self, mock_report_event: MagicMock):
        mock_query_generation_response = json.dumps([
            "pesquisa sobre Empresa Teste",
            "notícias recentes Empresa Teste"
        ])
        mock_summarization_response = "A Empresa Teste é líder em testes e recentemente lançou um novo produto."

        self.mock_llm_client.generate_llm_response.side_effect = [
            mock_query_generation_response, # For query generation
            mock_summarization_response    # For summarization
        ]

        self.agent._search_with_tavily.return_value = { # Simulate Tavily API's JSON structure
            "results": [
                {"url": "http://example.com/news1", "content": "Notícia 1 sobre Empresa Teste."},
                {"url": "http://example.com/news2", "content": "Notícia 2 sobre Empresa Teste."}
            ]
        }

        test_input = TavilyEnrichmentInput(
            company_name="Empresa Teste",
            initial_extracted_text="Texto inicial sobre a Empresa Teste.",
            product_service_offered="Nosso Produto Teste" # Added
        )

        result = await self.agent.execute(test_input, lead_id="test_lead_id_01", run_id="test_run_id_01")

        self.assertIsInstance(result, TavilyEnrichmentOutput)
        self.assertTrue(result.tavily_api_called)
        self.assertEqual(result.enriched_data, mock_summarization_response)
        self.assertIsNone(result.error_message)

        self.assertEqual(self.mock_llm_client.generate_llm_response.call_count, 2)
        self.agent._search_with_tavily.assert_called()

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_id_01") # lead_id
        self.assertEqual(args[1], self.agent.name)   # agent_name
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS) # status

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_tavily_search_returns_no_results(self, mock_report_event: MagicMock):
        mock_query_generation_response = json.dumps(["pesquisa Empresa Teste"])
        self.mock_llm_client.generate_llm_response.return_value = mock_query_generation_response

        self.agent._search_with_tavily.return_value = {"results": []} # No results from Tavily

        test_input = TavilyEnrichmentInput(
            company_name="Empresa Teste",
            initial_extracted_text="Texto inicial.",
            product_service_offered="Nosso Produto Teste" # Added
        )
        result = await self.agent.execute(test_input, lead_id="test_lead_id_02", run_id="test_run_id_02")

        self.assertIsInstance(result, TavilyEnrichmentOutput)
        self.assertTrue(result.tavily_api_called)
        # When no Tavily results and no summarization, enriched_data should be initial_extracted_text
        self.assertEqual(result.enriched_data, test_input.initial_extracted_text)
        # The error_message might be set by the agent if it considers "no results" an error for enrichment.
        # Based on current TavilyEnrichmentAgent, it logs a warning but doesn't set error_message for no results,
        # but rather uses initial text. If summarization fails (which it would if no new data), that might set an error.
        # Let's assume for now it's not a hard error in the output model, but BaseAgent might report it.
        # The agent's process method does: `self.logger.info("No information retrieved from Tavily search.")`
        # and `final_enriched_data` remains `input_data.initial_extracted_text`.
        # The `error_occured` flag is not set here. So `error_message` in output model should be None.
        self.assertIsNone(result.error_message)

        self.mock_llm_client.generate_llm_response.assert_called_once()
        self.agent._search_with_tavily.assert_called()

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_id_02")
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS) # Still success as per agent logic, just no new data.

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_llm_fails_query_generation(self, mock_report_event: MagicMock):
        self.mock_llm_client.generate_llm_response.return_value = "não é json" # Invalid JSON for query gen

        # Fallback Tavily search
        self.agent._search_with_tavily.return_value = {"results": [{"url": "http://example.com/fallback", "content": "Fallback content."}]}

        # Mock the second LLM call for summarization (if the first fails, it tries regex then this summary)
        mock_summarization_response = "Resumo do fallback."
        # Need to configure side_effect for the generate_llm_response
        self.mock_llm_client.generate_llm_response.side_effect = [
            "não é json", # For query gen
            mock_summarization_response # For summary of fallback
        ]

        test_input = TavilyEnrichmentInput(
            company_name="Empresa Teste",
            initial_extracted_text="Texto inicial.",
            product_service_offered="Nosso Produto Teste" # Added
        )
        result = await self.agent.execute(test_input, lead_id="test_lead_id_03", run_id="test_run_id_03")

        self.assertIsInstance(result, TavilyEnrichmentOutput)
        self.assertTrue(result.tavily_api_called)
        self.assertIn("Failed to parse or extract search queries", result.error_message if result.error_message else "")
        # Even if query gen fails, if fallback Tavily search + summarization works, enriched_data is updated.
        # Current agent logic: if query parsing fails but regex fallback finds queries, it proceeds.
        # If regex also fails, it returns with error. Let's assume regex also fails for this test of error_message.
        # Re-checking agent: if json.loads fails for queries, and regex fails, it returns an error output.

        # To test the specific error message from query parsing failure leading to agent's error_message:
        self.mock_llm_client.generate_llm_response.side_effect = ["{invalid_json_for_queries", "summarized_fallback_if_any"]
        self.agent._search_with_tavily.return_value = {"results": []} # Ensure no actual search happens if queries fail badly

        result_error_case = await self.agent.execute(test_input, lead_id="test_lead_id_03b", run_id="test_run_id_03b")
        self.assertIn("Failed to parse or extract search queries", result_error_case.error_message if result_error_case.error_message else "")
        self.assertEqual(result_error_case.enriched_data, test_input.initial_extracted_text) # Should fallback to initial

        mock_report_event.assert_called() # Called for test_lead_id_03b
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_id_03b")
        self.assertEqual(args[2], AgentExecutionStatusEnum.FAILED) # Agent process sets error message

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_search_with_tavily_api_failure(self, mock_report_event: MagicMock):
        self.mock_llm_client.generate_llm_response.return_value = json.dumps(["pesquisa Empresa Teste"])
        self.agent._search_with_tavily.side_effect = requests.exceptions.RequestException("API Error")

        test_input = TavilyEnrichmentInput(
            company_name="Empresa Teste",
            initial_extracted_text="Texto inicial.",
            product_service_offered="Nosso Produto Teste" # Added
        )
        result = await self.agent.execute(test_input, lead_id="test_lead_id_04", run_id="test_run_id_04")

        self.assertIsInstance(result, TavilyEnrichmentOutput)
        # tavily_api_called might be true if the call was attempted.
        # The error_message should reflect the Tavily API failure.
        self.assertTrue(result.tavily_api_called) # Call was attempted
        self.assertIn("An unexpected error occurred: API Error", result.error_message if result.error_message else "")
        self.assertEqual(result.enriched_data, test_input.initial_extracted_text)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_id_04")
        self.assertEqual(args[2], AgentExecutionStatusEnum.FAILED)


if __name__ == '__main__':
    unittest.main()
