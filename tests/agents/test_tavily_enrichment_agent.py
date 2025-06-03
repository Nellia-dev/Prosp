import unittest
from unittest.mock import MagicMock, patch
import json

from agents.tavily_enrichment_agent import TavilyEnrichmentAgent, TavilyEnrichmentInput, TavilyEnrichmentOutput
from core_logic.llm_client import LLMClientBase, LLMResponse

class TestTavilyEnrichmentAgent(unittest.TestCase):

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        # Mock methods called by BaseAgent.execute (which calls agent.process)
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0} # Ensure all keys are present
        self.mock_llm_client.update_usage_stats = MagicMock()

        self.agent = TavilyEnrichmentAgent(
            llm_client=self.mock_llm_client,
            tavily_api_key="test_tavily_key"
        )

    @patch('agents.tavily_enrichment_agent.TavilyEnrichmentAgent._search_with_tavily')
    def test_process_with_tavily_search_and_summarization(self, mock_search_with_tavily):
        # Mocking the LLM response for generating search queries
        mock_query_generation_response = json.dumps([
            "pesquisa sobre Empresa Teste",
            "notícias recentes Empresa Teste"
        ])
        # Mocking the LLM response for summarizing Tavily results
        mock_summarization_response = "A Empresa Teste é líder em testes e recentemente lançou um novo produto."

        # Configure side_effect for multiple calls to generate
        self.mock_llm_client.generate.side_effect = [
            LLMResponse(content=mock_query_generation_response, provider_name="mock", model_name="mock_model", total_tokens=10, input_tokens=5, output_tokens=5),
            LLMResponse(content=mock_summarization_response, provider_name="mock", model_name="mock_model", total_tokens=20, input_tokens=10, output_tokens=10)
        ]

        # Mocking Tavily search results
        mock_search_with_tavily.return_value = [
            {"url": "http://example.com/news1", "content": "Notícia 1 sobre Empresa Teste."},
            {"url": "http://example.com/news2", "content": "Notícia 2 sobre Empresa Teste."}
        ]

        test_input = TavilyEnrichmentInput(
            company_name="Empresa Teste",
            initial_extracted_text="Texto inicial sobre a Empresa Teste."
        )

        result = self.agent.execute(test_input)

        self.assertIsInstance(result, TavilyEnrichmentOutput)
        self.assertTrue(result.tavily_api_called)
        self.assertEqual(result.enriched_data, mock_summarization_response)
        self.assertIsNone(result.error_message)

        self.assertEqual(self.mock_llm_client.generate.call_count, 2) # One for queries, one for summary
        mock_search_with_tavily.assert_called() # Check that Tavily search was attempted

    @patch('agents.tavily_enrichment_agent.TavilyEnrichmentAgent._search_with_tavily')
    def test_process_tavily_search_returns_no_results(self, mock_search_with_tavily):
        mock_query_generation_response = json.dumps(["pesquisa Empresa Teste"])
        # LLM for summarization won't be called if no Tavily results
        self.mock_llm_client.generate.return_value = LLMResponse(content=mock_query_generation_response, provider_name="mock", model_name="mock_model", total_tokens=10, input_tokens=5, output_tokens=5)

        mock_search_with_tavily.return_value = [] # No results from Tavily

        test_input = TavilyEnrichmentInput(
            company_name="Empresa Teste",
            initial_extracted_text="Texto inicial."
        )
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, TavilyEnrichmentOutput)
        self.assertTrue(result.tavily_api_called)
        # enriched_data should be the initial_extracted_text as no summarization happens
        self.assertEqual(result.enriched_data, test_input.initial_extracted_text)
        self.assertIn("Tavily API was called but returned no results", result.error_message if result.error_message else "")

        self.mock_llm_client.generate.assert_called_once() # Only for query generation
        mock_search_with_tavily.assert_called_once()

    def test_process_llm_fails_query_generation(self):
        # Simulate LLM failing to generate search queries (e.g., returns empty or invalid JSON)
        self.mock_llm_client.generate.return_value = LLMResponse(content="não é json", provider_name="mock", model_name="mock_model", total_tokens=5, input_tokens=2, output_tokens=3)

        # We still need to mock _search_with_tavily because the fallback query will call it
        with patch('agents.tavily_enrichment_agent.TavilyEnrichmentAgent._search_with_tavily') as mock_search:
            mock_search.return_value = [{"url": "http://example.com/fallback", "content": "Fallback content."}]
            # Second LLM call for summarization
            mock_summarization_response = "Resumo do fallback."
            # Need to ensure the generate mock can be called again for summarization
            # If generate is already configured with a single return_value, this might not work as expected without side_effect

            # Reconfigure generate for this specific test case for multiple calls
            self.mock_llm_client.generate.side_effect = [
                LLMResponse(content="não é json", provider_name="mock", model_name="mock_model", total_tokens=5, input_tokens=2, output_tokens=3), # For query gen
                LLMResponse(content=mock_summarization_response, provider_name="mock", model_name="mock_model", total_tokens=10, input_tokens=5, output_tokens=5) # For summary
            ]

            test_input = TavilyEnrichmentInput(
                company_name="Empresa Teste",
                initial_extracted_text="Texto inicial."
            )
            result = self.agent.execute(test_input)

            self.assertIsInstance(result, TavilyEnrichmentOutput)
            self.assertTrue(result.tavily_api_called) # Fallback query is made
            self.assertIn("Error decoding LLM response for search queries", result.error_message if result.error_message else "")
            self.assertEqual(result.enriched_data, mock_summarization_response) # Summarization of fallback search

            self.assertEqual(self.mock_llm_client.generate.call_count, 2)
            mock_search.assert_called_once()


    @patch('agents.tavily_enrichment_agent.requests.post') # Mock the actual requests.post call
    def test_search_with_tavily_api_failure(self, mock_requests_post):
        # Simulate Tavily API returning an error
        mock_requests_post.side_effect = requests.exceptions.RequestException("API Error")

        # LLM for query generation
        mock_query_generation_response = json.dumps(["pesquisa Empresa Teste"])
        self.mock_llm_client.generate.return_value = LLMResponse(content=mock_query_generation_response, provider_name="mock", model_name="mock_model", total_tokens=10, input_tokens=5, output_tokens=5)

        test_input = TavilyEnrichmentInput(
            company_name="Empresa Teste",
            initial_extracted_text="Texto inicial."
        )
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, TavilyEnrichmentOutput)
        self.assertTrue(result.tavily_api_called)
        self.assertEqual(result.enriched_data, test_input.initial_extracted_text) # No enrichment data
        self.assertIn("Tavily API was called but returned no results", result.error_message if result.error_message else "") # Error from _search_with_tavily is generic "no results"

        self.mock_llm_client.generate.assert_called_once()
        mock_requests_post.assert_called_once()


if __name__ == '__main__':
    unittest.main()
