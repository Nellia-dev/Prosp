import unittest
from unittest.mock import MagicMock
import json

from agents.contact_extraction_agent import ContactExtractionAgent, ContactExtractionInput, ContactExtractionOutput
from core_logic.llm_client import LLMClientBase, LLMResponse

class TestContactExtractionAgent(unittest.TestCase):

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0}
        self.mock_llm_client.update_usage_stats = MagicMock()
        
        self.agent = ContactExtractionAgent(llm_client=self.mock_llm_client)

    def test_process_success_finds_contacts(self):
        mock_json_output = json.dumps({
            "emails_found": ["test@example.com", "sales@example.com"],
            "instagram_profiles_found": ["@example_insta"],
            "tavily_search_suggestion": "Search for Example Inc decision makers"
        })
        self.mock_llm_client.generate.return_value = LLMResponse(content=mock_json_output, provider_name="mock", model_name="mock_model", total_tokens=30, input_tokens=15, output_tokens=15)

        test_input = ContactExtractionInput(
            extracted_text="Contact us at test@example.com or sales@example.com. Follow @example_insta.",
            company_name="Example Inc",
            product_service_offered="Test Services"
        )
        
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, ContactExtractionOutput)
        self.assertIsNone(result.error_message)
        self.assertListEqual(result.emails_found, ["test@example.com", "sales@example.com"])
        self.assertListEqual(result.instagram_profiles_found, ["@example_insta"])
        self.assertEqual(result.tavily_search_suggestion, "Search for Example Inc decision makers")
        self.mock_llm_client.generate.assert_called_once()
        # You can add more detailed prompt checking here if needed
        # self.mock_llm_client.generate.assert_called_with(expected_prompt_string)

    def test_process_success_no_contacts_found(self):
        mock_json_output = json.dumps({
            "emails_found": [],
            "instagram_profiles_found": [],
            "tavily_search_suggestion": "Search for Example Inc news"
        })
        self.mock_llm_client.generate.return_value = LLMResponse(content=mock_json_output, provider_name="mock", model_name="mock_model", total_tokens=20, input_tokens=10, output_tokens=10)

        test_input = ContactExtractionInput(
            extracted_text="No contact info here.",
            company_name="Example Inc",
            product_service_offered="Test Services"
        )
        
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, ContactExtractionOutput)
        self.assertIsNone(result.error_message)
        self.assertListEqual(result.emails_found, [])
        self.assertListEqual(result.instagram_profiles_found, [])
        self.assertEqual(result.tavily_search_suggestion, "Search for Example Inc news")
        self.mock_llm_client.generate.assert_called_once()

    def test_process_llm_returns_malformed_json_with_fallback(self):
        # Simulate LLM returning a string that is not valid JSON but contains extractable info
        malformed_response_str = "Found email: contact@fallback.com and insta: @fallback_insta. Suggest 'fallback company details'."
        self.mock_llm_client.generate.return_value = LLMResponse(content=malformed_response_str, provider_name="mock", model_name="mock_model", total_tokens=25, input_tokens=12, output_tokens=13)

        test_input = ContactExtractionInput(
            extracted_text="Some text leading to fallback.",
            company_name="Fallback Solutions",
            product_service_offered="Fallback Services"
        )
        
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, ContactExtractionOutput)
        self.assertIsNotNone(result.error_message) # Expecting an error message due to parsing failure
        self.assertIn("JSON parsing failed", result.error_message)
        
        # Check if regex fallback worked
        self.assertListEqual(result.emails_found, ["contact@fallback.com"])
        self.assertListEqual(result.instagram_profiles_found, ["@fallback_insta"])
        # Tavily suggestion would likely be empty or default from the model if JSON parsing failed for it
        self.assertEqual(result.tavily_search_suggestion, "") # Or whatever the default is in ContactExtractionOutput
        
        self.mock_llm_client.generate.assert_called_once()

    def test_process_llm_returns_empty_response(self):
        self.mock_llm_client.generate.return_value = LLMResponse(content="", provider_name="mock", model_name="mock_model", total_tokens=2, input_tokens=1, output_tokens=1) # Empty content

        test_input = ContactExtractionInput(
            extracted_text="Some text.",
            company_name="Empty Response Co",
            product_service_offered="Services"
        )
        
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, ContactExtractionOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("LLM call returned no response.", result.error_message)
        self.assertListEqual(result.emails_found, [])
        self.assertListEqual(result.instagram_profiles_found, [])
        self.assertEqual(result.tavily_search_suggestion, "")

    def test_process_llm_returns_json_missing_fields(self):
        # LLM returns valid JSON but misses some fields the Pydantic model expects (they should take defaults)
        mock_json_output = json.dumps({
            "emails_found": ["onlyemail@example.com"]
            # Missing "instagram_profiles_found" and "tavily_search_suggestion"
        })
        self.mock_llm_client.generate.return_value = LLMResponse(content=mock_json_output, provider_name="mock", model_name="mock_model", total_tokens=15, input_tokens=7, output_tokens=8)

        test_input = ContactExtractionInput(
            extracted_text="Text with only email.",
            company_name="Missing Fields Corp",
            product_service_offered="Partial Data"
        )
        
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, ContactExtractionOutput)
        # Depending on how parse_llm_json_response handles missing fields (and if there's a strict requirement for them beyond Pydantic defaults)
        # an error message might or might not be present. Given current BaseAgent, it should not set error if JSON is valid.
        # However, the agent's own logic checks if essential fields are missing after parsing.
        if not (result.emails_found or result.instagram_profiles_found or result.tavily_search_suggestion):
             self.assertIsNotNone(result.error_message) # This condition is from the agent's code
        else:
            self.assertIsNone(result.error_message) 


        self.assertListEqual(result.emails_found, ["onlyemail@example.com"])
        self.assertListEqual(result.instagram_profiles_found, []) # Should default to empty list
        self.assertEqual(result.tavily_search_suggestion, "")     # Should default to empty string

if __name__ == '__main__':
    unittest.main()
