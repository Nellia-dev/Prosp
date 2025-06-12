import unittest
from unittest.mock import patch, MagicMock
import os
import json

# Adjust imports if necessary based on project structure
try:
    from data_models.campaign_optimization_models import (
        CampaignContentInput,
        CampaignContentOutput,
        CampaignContentType,
    )
    from agents.campaign_content_optimizer_agent import CampaignContentOptimizerAgent
    from core_logic.llm_client import LLMProvider
except ImportError:
    # Fallback for local testing if modules are not found
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
    from data_models.campaign_optimization_models import (
        CampaignContentInput,
        CampaignContentOutput,
        CampaignContentType,
    )
    from agents.campaign_content_optimizer_agent import CampaignContentOptimizerAgent
    from core_logic.llm_client import LLMProvider


class TestCampaignContentOptimizerAgent(unittest.TestCase):

    def setUp(self):
        # Mock LLMClient initialization if it requires API keys even for mocked calls
        # Based on previous experiences, setting a dummy key might be needed.
        # This setup assumes GEMINI is the default or an expected provider.
        os.environ["GEMINI_API_KEY"] = "dummy_test_key_for_optimizer_agent" # Ensure client can init
        self.agent = CampaignContentOptimizerAgent(llm_provider=LLMProvider.GEMINI) # Or your chosen provider

    @patch.object(CampaignContentOptimizerAgent, 'generate_llm_response')
    def test_process_valid_input_successful_llm_response(self, mock_generate_llm_response):
        mock_llm_output_dict = {
            "suggested_improvements": [
                "Make the call to action more prominent.",
                "Use stronger verbs to create excitement."
            ],
            "optimized_versions": [
                "Optimized Version 1: Experience the future of X!",
                "Optimized Version 2: Don't miss out on Y - Upgrade now!"
            ],
            "analysis_summary": "The original content was good, but these changes will boost CTR."
        }
        mock_generate_llm_response.return_value = json.dumps(mock_llm_output_dict)

        test_input = CampaignContentInput(
            content_type=CampaignContentType.AD_HEADLINE,
            original_content="New Product Available",
            target_audience_description="Tech enthusiasts looking for the latest gadgets.",
            desired_outcome="Increase click-through rates on ads.",
            additional_context="Product is a new smartwatch with innovative features."
        )

        result = self.agent.execute(test_input) # Using BaseAgent's execute

        self.assertIsInstance(result, CampaignContentOutput)
        self.assertEqual(result.original_content, test_input.original_content)
        self.assertEqual(result.content_type, test_input.content_type)
        self.assertEqual(result.target_audience_description, test_input.target_audience_description)
        self.assertEqual(result.desired_outcome, test_input.desired_outcome)

        self.assertEqual(len(result.suggested_improvements), 2)
        self.assertIn("Make the call to action more prominent.", result.suggested_improvements)

        self.assertEqual(len(result.optimized_versions), 2)
        self.assertIn("Optimized Version 1: Experience the future of X!", result.optimized_versions)

        # Check if the summary from LLM is used when no error and suggestions are present
        # The agent logic is: elif not output_data_dict["error_message"]: output_data_dict["analysis_summary"] = parsed_response.get("analysis_summary", "Content optimization suggestions generated successfully.")
        # So, if "analysis_summary" is in mock_llm_output_dict, it should be used.
        self.assertEqual(result.analysis_summary, "The original content was good, but these changes will boost CTR.")
        self.assertIsNone(result.error_message)

        mock_generate_llm_response.assert_called_once()

    @patch.object(CampaignContentOptimizerAgent, 'generate_llm_response')
    def test_process_llm_returns_error(self, mock_generate_llm_response):
        mock_generate_llm_response.side_effect = Exception("LLM API unavailable")

        test_input = CampaignContentInput(
            content_type=CampaignContentType.EMAIL_SUBJECT,
            original_content="A quick question",
            target_audience_description="Existing customers.",
            desired_outcome="Get feedback on recent purchase."
        )

        result = self.agent.execute(test_input)

        self.assertIsInstance(result, CampaignContentOutput)
        self.assertEqual(result.original_content, test_input.original_content) # Input data should still be there
        self.assertTrue("LLM generation failed: LLM API unavailable" in result.error_message)
        self.assertTrue("Failed to generate analysis due to LLM error." in result.analysis_summary)
        self.assertEqual(len(result.suggested_improvements), 0)
        self.assertEqual(len(result.optimized_versions), 0)

    @patch.object(CampaignContentOptimizerAgent, 'generate_llm_response')
    def test_process_llm_returns_malformed_json(self, mock_generate_llm_response):
        mock_generate_llm_response.return_value = "This is not valid JSON { definitely not"

        test_input = CampaignContentInput(
            content_type=CampaignContentType.SOCIAL_MEDIA_POST_TEXT,
            original_content="Check out our new blog post!",
            target_audience_description="Followers interested in industry news.",
            desired_outcome="Drive traffic to blog."
        )

        result = self.agent.execute(test_input)

        self.assertIsInstance(result, CampaignContentOutput)
        self.assertEqual(result.original_content, test_input.original_content)
        self.assertTrue("LLM response parsing failed" in result.error_message)
        self.assertTrue("Raw response snippet: This is not valid JSON { definitely not" in result.error_message)
        self.assertTrue("Failed to process LLM response." in result.analysis_summary)

    @patch.object(CampaignContentOptimizerAgent, 'generate_llm_response')
    def test_process_llm_returns_incomplete_data(self, mock_generate_llm_response):
        # LLM returns valid JSON, but misses some fields
        mock_llm_output_dict = {
            "analysis_summary": "Suggestions focused only on headlines today."
            # Missing "suggested_improvements" and "optimized_versions"
        }
        mock_generate_llm_response.return_value = json.dumps(mock_llm_output_dict)

        test_input = CampaignContentInput(
            content_type=CampaignContentType.AD_HEADLINE,
            original_content="Old Headline",
                target_audience_description="Everyone interested", # Changed to meet min_length=10
            desired_outcome="Get clicks"
        )

        result = self.agent.execute(test_input)

        self.assertIsInstance(result, CampaignContentOutput)
        self.assertEqual(result.original_content, test_input.original_content)
        self.assertEqual(len(result.suggested_improvements), 0) # Should default to empty list
        self.assertEqual(len(result.optimized_versions), 0)   # Should default to empty list
        # The logic in the agent is:
        # if not output_data_dict["suggested_improvements"] and not output_data_dict["optimized_versions"]:
        #    output_data_dict["analysis_summary"] = "LLM response parsed, but no suggestions or optimized versions were found."
        # This should be the summary in this case.
        self.assertEqual(result.analysis_summary, "LLM response parsed, but no suggestions or optimized versions were found.")
        self.assertIsNone(result.error_message)


if __name__ == '__main__':
    unittest.main()
