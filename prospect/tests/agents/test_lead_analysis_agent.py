import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

from agents.lead_analysis_agent import LeadAnalysisAgent
from data_models.lead_structures import ValidatedLead, SiteData, LeadAnalysis, ExtractionStatus

class TestLeadAnalysisAgent(unittest.TestCase):

    @patch.object(LeadAnalysisAgent, '_generate_limited_analysis')
    @patch.object(LeadAnalysisAgent, '_generate_full_analysis')
    def test_process_full_analysis_with_text_content_despite_extraction_failure(
        self, mock_full_analysis, mock_limited_analysis
    ):
        # 1. Setup Agent
        agent = LeadAnalysisAgent(
            name="TestLeadAnalysisAgent",
            description="Agent for testing lead analysis",
            product_service_context="Test Product/Service Context"
        )

        # 2. Prepare Input Data (ValidatedLead)
        test_text_content = "Empresa de teste especializada em desenvolvimento de software e consultoria estratégica."

        site_data = SiteData(
            url="http://exampletest.com",
            google_search_data=None, # Explicitly None
            screenshot_filepath=None, # Optional field
            extracted_text_content=test_text_content,
            extraction_status_message="Simulated extraction failure partway through",
            # ExtractionStatus is an enum, but message is just a string.
        )

        validated_lead_input = ValidatedLead(
            # lead_id is not a field in ValidatedLead as per data_models.lead_structures.py
            site_data=site_data,
            extraction_successful=False, # Key condition for this test
            cleaned_text_content=test_text_content, # Key content present
            is_valid=True, # Added missing mandatory field
            validation_errors=[], # Optional, default_factory
            validation_timestamp=datetime.now(), # Optional, default_factory
        )

        # 3. Configure Mock for _generate_full_analysis
        expected_analysis_output = LeadAnalysis(
            company_sector="Tecnologia da Informação",
            main_services=["Desenvolvimento de Software", "Consultoria Estratégica"],
            recent_activities=[], # Default
            potential_challenges=["Desafio Teste"], # Example challenge
            company_size_estimate="Pequena", # Optional
            company_culture_values="Inovadora", # Optional
            relevance_score=0.85,
            general_diagnosis="Lead promissor com base no texto fornecido.",
            opportunity_fit="Bom fit para Test Product/Service Context"
        )
        mock_full_analysis.return_value = expected_analysis_output

        # 4. (Mock for _generate_limited_analysis is already an argument)
        # No specific return value needed as we assert it's not called.

        # 5. Execute the process method
        analyzed_lead_result = agent.process(validated_lead_input)

        # 6. Assertions
        mock_full_analysis.assert_called_once_with(validated_lead_input)
        mock_limited_analysis.assert_not_called()

        # Assert that the analysis object within AnalyzedLead is the one we mocked
        self.assertEqual(analyzed_lead_result.analysis, expected_analysis_output)

        # Individual field checks (optional if the above object comparison is robust)
        self.assertEqual(analyzed_lead_result.analysis.company_sector, "Tecnologia da Informação")
        self.assertEqual(analyzed_lead_result.analysis.main_services, ["Desenvolvimento de Software", "Consultoria Estratégica"])
        self.assertEqual(analyzed_lead_result.analysis.relevance_score, 0.85)

        # Check that the validated_lead and product_service_context are correctly passed through
        self.assertEqual(analyzed_lead_result.validated_lead, validated_lead_input)
        self.assertEqual(analyzed_lead_result.product_service_context, "Test Product/Service Context")

if __name__ == '__main__':
    unittest.main()
