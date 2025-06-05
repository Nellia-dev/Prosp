import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import json

from agents.contact_extraction_agent import ContactExtractionAgent, ContactExtractionInput, ContactExtractionOutput
from core_logic.llm_client import LLMClientBase, LLMResponse
from mcp_server.data_models import AgentExecutionStatusEnum

class TestContactExtractionAgent(unittest.IsolatedAsyncioTestCase): # Changed to IsolatedAsyncioTestCase

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.generate_llm_response = AsyncMock() # For BaseAgent.generate_llm_response
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0, "llm_calls": 0, "llm_usage": []}
        self.mock_llm_client.update_usage_stats = MagicMock()

        self.agent = ContactExtractionAgent(llm_client=self.mock_llm_client)

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_success_finds_contacts(self, mock_report_event: MagicMock):
        mock_json_output = json.dumps({
            "emails_found": ["test@example.com", "sales@example.com"],
            "instagram_profiles_found": ["@example_insta"],
            "tavily_search_suggestion": "Search for Example Inc decision makers"
        })
        self.mock_llm_client.generate_llm_response.return_value = mock_json_output # generate_llm_response returns string

        test_input = ContactExtractionInput(
            extracted_text="Contact us at test@example.com or sales@example.com. Follow @example_insta.",
            company_name="Example Inc",
            product_service_offered="Test Services"
        )

        result = await self.agent.execute(test_input, lead_id="test_lead_01", run_id="test_run_01")

        self.assertIsInstance(result, ContactExtractionOutput)
        self.assertIsNone(result.error_message)
        self.assertIn("test@example.com", result.emails_found) # Order might change due to set operations
        self.assertIn("sales@example.com", result.emails_found)
        self.assertIn("example_insta", result.instagram_profiles_found) # Agent cleans to username
        self.assertEqual(result.tavily_search_suggestion, "Search for Example Inc decision makers")
        self.mock_llm_client.generate_llm_response.assert_called_once()

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_01")
        self.assertEqual(args[1], self.agent.name)
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS)


    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_success_no_contacts_found(self, mock_report_event: MagicMock):
        mock_json_output = json.dumps({
            "emails_found": [],
            "instagram_profiles_found": [],
            "tavily_search_suggestion": "Search for Example Inc news"
        })
        self.mock_llm_client.generate_llm_response.return_value = mock_json_output

        test_input = ContactExtractionInput(
            extracted_text="No contact info here.",
            company_name="Example Inc",
            product_service_offered="Test Services"
        )

        result = await self.agent.execute(test_input, lead_id="test_lead_02", run_id="test_run_02")

        self.assertIsInstance(result, ContactExtractionOutput)
        self.assertIsNone(result.error_message) # Agent considers this a success, just no data found by LLM
        self.assertListEqual(result.emails_found, [])
        self.assertListEqual(result.instagram_profiles_found, [])
        self.assertEqual(result.tavily_search_suggestion, "Search for Example Inc news")
        self.mock_llm_client.generate_llm_response.assert_called_once()

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_02")
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS)


    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_llm_returns_malformed_json_with_fallback(self, mock_report_event: MagicMock):
        malformed_response_str = "Found email: contact@fallback.com and insta: @fallback_insta. Suggest 'fallback company details'."
        self.mock_llm_client.generate_llm_response.return_value = malformed_response_str

        test_input = ContactExtractionInput(
            extracted_text="Some text leading to fallback: contact@fallback.com and @fallback_insta", # Ensure regex can find it
            company_name="Fallback Solutions",
            product_service_offered="Fallback Services"
        )

        result = await self.agent.execute(test_input, lead_id="test_lead_03", run_id="test_run_03")

        self.assertIsInstance(result, ContactExtractionOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to parse LLM JSON response", result.error_message)

        self.assertIn("contact@fallback.com", result.emails_found)
        self.assertIn("fallback_insta", result.instagram_profiles_found)
        self.assertTrue(result.tavily_search_suggestion.startswith("key decision makers at")) # Default fallback suggestion

        self.mock_llm_client.generate_llm_response.assert_called_once()
        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_03")
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS) # Agent's own error_message is set, but process itself might be success if fallback works


    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_llm_returns_empty_response(self, mock_report_event: MagicMock):
        self.mock_llm_client.generate_llm_response.return_value = "" # Empty content

        test_input = ContactExtractionInput(
            extracted_text="Some text.",
            company_name="Empty Response Co",
            product_service_offered="Services"
        )

        result = await self.agent.execute(test_input, lead_id="test_lead_04", run_id="test_run_id_04")

        self.assertIsInstance(result, ContactExtractionOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("LLM returned no response. Used regex fallback.", result.error_message)
        self.assertListEqual(result.emails_found, []) # Regex fallback on empty text yields empty
        self.assertListEqual(result.instagram_profiles_found, [])
        self.assertTrue(result.tavily_search_suggestion.startswith("key decision makers at"))

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_04")
        # The agent sets an error message, so BaseAgent should report FAILED
        self.assertEqual(args[2], AgentExecutionStatusEnum.FAILED)


    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_llm_returns_json_missing_fields(self, mock_report_event: MagicMock):
        mock_json_output = json.dumps({
            "emails_found": ["onlyemail@example.com"]
        })
        self.mock_llm_client.generate_llm_response.return_value = mock_json_output

        test_input = ContactExtractionInput(
            extracted_text="Text with only email: onlyemail@example.com.", # Added email for regex fallback to ensure it's combined
            company_name="Missing Fields Corp",
            product_service_offered="Partial Data"
        )

        result = await self.agent.execute(test_input, lead_id="test_lead_05", run_id="test_run_id_05")

        self.assertIsInstance(result, ContactExtractionOutput)
        self.assertIsNone(result.error_message) # Valid JSON, even if missing fields, Pydantic model should use defaults. Regex will augment.

        self.assertIn("onlyemail@example.com", result.emails_found)
        self.assertListEqual(result.instagram_profiles_found, [])
        self.assertTrue(result.tavily_search_suggestion.startswith("contact information for")) # Default from agent when LLM doesn't provide

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_05")
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS)

if __name__ == '__main__':
    unittest.main()
