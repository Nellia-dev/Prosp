import unittest
from unittest.mock import MagicMock, patch
import numpy as np
from datetime import datetime

# Adjust imports based on your project structure
from prospect.agents.lead_analysis_agent import LeadAnalysisAgent
from prospect.data_models.core import ValidatedLead, AnalyzedLead, LeadAnalysis, SiteData, GoogleSearchData
# Assuming generate_lead_vector will be mocked as it involves ML model loading
from prospect.data_models.enums import ExtractionStatus

class TestLeadAnalysisAgent(unittest.TestCase):

    def setUp(self):
        self.mock_llm_client = MagicMock()
        self.agent = LeadAnalysisAgent(
            name="TestLeadAnalysisAgent",
            description="Test Agent",
            llm_client=self.mock_llm_client,
            product_service_context="Test Product"
        )

        # Mock ValidatedLead input
        self.mock_site_data = SiteData(
            url="https://example.com", # type: ignore
            google_search_data=GoogleSearchData(title="Title", snippet="Snippet"),
            extracted_text_content="Sufficient extracted text for analysis.",
            extraction_status_message=ExtractionStatus.SUCCESS.value, # Use enum value
            screenshot_filepath=None
        )
        self.mock_validated_lead = ValidatedLead(
            lead_id="test_lead_123",
            company_name="Test Company",
            site_data=self.mock_site_data,
            validation_timestamp=datetime.now(),
            is_valid=True,
            validation_errors=[],
            cleaned_text_content="Sufficient cleaned text content for analysis.",
            extraction_successful=True
        )

        # Mock LLM Response for _generate_full_analysis
        self.mock_llm_response_dict = {
            "company_sector": "Tecnologia",
            "main_services": ["AI Solutions"],
            "recent_activities": ["New funding round"],
            "potential_challenges": ["Market competition"],
            "company_size_estimate": "Média",
            "company_culture_values": "Inovação",
            "relevance_score": 0.85,
            "general_diagnosis": "Promising lead",
            "opportunity_fit": "High potential for Test Product"
        }

    @patch('prospect.agents.lead_analysis_agent.generate_lead_vector') # Mock the imported function
    @patch.object(LeadAnalysisAgent, '_generate_full_analysis') # Mock the LLM call part
    def test_process_populates_lead_vector(self, mock_generate_full_analysis, mock_generate_lead_vector):
        # Setup mock for _generate_full_analysis
        mock_analysis_obj = LeadAnalysis(**self.mock_llm_response_dict)
        mock_generate_full_analysis.return_value = mock_analysis_obj

        # Setup mock for generate_lead_vector
        mock_vector = [0.1, 0.2, 0.3, 0.4, 0.5] # Example vector
        mock_generate_lead_vector.return_value = mock_vector

        # Process the lead
        analyzed_lead_result = self.agent.process(self.mock_validated_lead)

        self.assertIsNotNone(analyzed_lead_result)
        self.assertIsNotNone(analyzed_lead_result.lead_vector, "lead_vector should be populated")
        self.assertEqual(analyzed_lead_result.lead_vector, mock_vector)

        # Ensure generate_lead_vector was called with the intermediate AnalyzedLead instance
        mock_generate_lead_vector.assert_called_once()
        call_args = mock_generate_lead_vector.call_args[0][0]
        self.assertIsInstance(call_args, AnalyzedLead)
        self.assertEqual(call_args.validated_lead, self.mock_validated_lead)
        self.assertEqual(call_args.analysis, mock_analysis_obj)

    @patch('prospect.agents.lead_analysis_agent.generate_lead_vector')
    @patch.object(LeadAnalysisAgent, '_generate_full_analysis')
    def test_process_handles_vector_generation_failure(self, mock_generate_full_analysis, mock_generate_lead_vector):
        mock_analysis_obj = LeadAnalysis(**self.mock_llm_response_dict)
        mock_generate_full_analysis.return_value = mock_analysis_obj

        # Simulate generate_lead_vector returning None
        mock_generate_lead_vector.return_value = None

        analyzed_lead_result = self.agent.process(self.mock_validated_lead)

        self.assertIsNotNone(analyzed_lead_result)
        self.assertIsNone(analyzed_lead_result.lead_vector, "lead_vector should be None if generation returns None")
        mock_generate_lead_vector.assert_called_once()

        # Reset mock for next scenario (important if side_effect is sticky or want to check call_count per scenario)
        mock_generate_lead_vector.reset_mock()

        # Simulate generate_lead_vector raising an exception
        mock_generate_lead_vector.side_effect = Exception("Vectorization error")
        analyzed_lead_result = self.agent.process(self.mock_validated__lead) # Typo here, should be self.mock_validated_lead

        self.assertIsNotNone(analyzed_lead_result)
        self.assertIsNone(analyzed_lead_result.lead_vector, "lead_vector should be None if generation raises error")
        mock_generate_lead_vector.assert_called_once()


if __name__ == '__main__':
    unittest.main()
