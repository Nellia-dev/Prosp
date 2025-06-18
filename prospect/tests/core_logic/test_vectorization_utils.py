import unittest
from unittest.mock import patch, MagicMock
import numpy as np

# Adjust imports based on your project structure
from prospect.data_models.core import AnalyzedLead, ValidatedLead, LeadAnalysis
from prospect.core_logic.vectorization_utils import generate_lead_vector, model as sentence_transformer_model

class TestVectorizationUtils(unittest.TestCase):

    def setUp(self):
        # Mock data for AnalyzedLead
        self.mock_validated_lead_full = ValidatedLead(
            lead_id="test_id_full",
            company_name="Test Company Full",
            site_data=MagicMock(), # Assume SiteData is complex or not needed for vectorization logic itself
            cleaned_text_content="Este é um texto de exemplo para testes.",
            extraction_successful=True,
            # Add other required fields for ValidatedLead if any, with default/mock values
            validation_timestamp=MagicMock(),
            is_valid=True,
            validation_errors=[]
        )
        self.mock_analysis_full = LeadAnalysis(
            company_sector="Tecnologia",
            main_services=["Software"],
            potential_challenges=["Desafio 1"],
            relevance_score=0.9,
            general_diagnosis="Diagnóstico completo",
            opportunity_fit="Bom fit"
            # Add other required fields for LeadAnalysis if any
        )
        self.analyzed_lead_full = AnalyzedLead(
            validated_lead=self.mock_validated_lead_full,
            analysis=self.mock_analysis_full,
            product_service_context="Produto Teste"
            # Add other required fields for AnalyzedLead if any
        )

        self.mock_validated_lead_no_text = ValidatedLead(
            lead_id="test_id_no_text",
            company_name="Test Company No Text",
            site_data=MagicMock(),
            cleaned_text_content="", # No text
            extraction_successful=True,
            validation_timestamp=MagicMock(),
            is_valid=True,
            validation_errors=[]
        )
        self.analyzed_lead_no_text = AnalyzedLead(
            validated_lead=self.mock_validated_lead_no_text,
            analysis=self.mock_analysis_full, # Keep analysis part
            product_service_context="Produto Teste"
        )

        self.mock_validated_lead_short_text = ValidatedLead(
            lead_id="test_id_short_text",
            company_name="Test Company Short Text",
            site_data=MagicMock(),
            cleaned_text_content="curto", # Short text
            extraction_successful=True,
            validation_timestamp=MagicMock(),
            is_valid=True,
            validation_errors=[]
        )
        self.analyzed_lead_short_text = AnalyzedLead(
            validated_lead=self.mock_validated_lead_short_text,
            analysis=self.mock_analysis_full,
            product_service_context="Produto Teste"
        )

        self.mock_analysis_minimal = LeadAnalysis(
            company_sector=None, # No sector
            main_services=[],
            potential_challenges=[],
            relevance_score=0.1, # Minimal score
            general_diagnosis="Diagnóstico mínimo",
            opportunity_fit="Fit baixo"
        )
        self.analyzed_lead_no_analysis_details = AnalyzedLead(
            validated_lead=self.mock_validated_lead_full, # Full text
            analysis=self.mock_analysis_minimal, # Minimal analysis
            product_service_context="Produto Teste"
        )

        _mock_site_data_empty = MagicMock()
        # Ensure SiteData mock has necessary attributes if accessed by AnalyzedLead/ValidatedLead
        _mock_site_data_empty.url = "http://empty.com"
        _mock_site_data_empty.google_search_data = None
        _mock_site_data_empty.extracted_text_content = None
        _mock_site_data_empty.extraction_status_message = ""
        _mock_site_data_empty.screenshot_filepath = None


        self.analyzed_lead_empty = AnalyzedLead(
            validated_lead=ValidatedLead(
                lead_id="empty", company_name="Empty",
                site_data=_mock_site_data_empty, # Use properly mocked SiteData
                cleaned_text_content=None, extraction_successful=False,
                validation_timestamp=MagicMock(), is_valid=False, validation_errors=["empty"]
            ),
            analysis=LeadAnalysis(
                company_sector=None, main_services=[], potential_challenges=[],
                relevance_score=0.0, general_diagnosis="", opportunity_fit=""
            ),
            product_service_context=""
        )

    @patch('prospect.core_logic.vectorization_utils.model.encode')
    def test_generate_lead_vector_full_data(self, mock_encode):
        mock_text_embedding = np.random.rand(384).astype(np.float32) # all-MiniLM-L6-v2 dimension
        mock_encode.return_value = mock_text_embedding

        vector = generate_lead_vector(self.analyzed_lead_full)

        self.assertIsNotNone(vector)
        self.assertIsInstance(vector, list)
        # Expected length: text_embedding_dim + 3 structured features
        self.assertEqual(len(vector), 384 + 3)
        mock_encode.assert_called_once_with(self.mock_validated_lead_full.cleaned_text_content, convert_to_tensor=False)

    @patch('prospect.core_logic.vectorization_utils.model.encode')
    def test_generate_lead_vector_no_text(self, mock_encode):
        vector = generate_lead_vector(self.analyzed_lead_no_text)

        self.assertIsNotNone(vector)
        self.assertIsInstance(vector, list)
        # Expected length: 0 for text + 3 structured features
        self.assertEqual(len(vector), 3)
        mock_encode.assert_not_called()

    @patch('prospect.core_logic.vectorization_utils.model.encode')
    def test_generate_lead_vector_short_text_is_skipped(self, mock_encode):
        # Text is "curto", which is < 10 chars, so should be skipped by the current logic
        vector = generate_lead_vector(self.analyzed_lead_short_text)
        self.assertIsNotNone(vector)
        self.assertIsInstance(vector, list)
        self.assertEqual(len(vector), 3) # Only structured features
        mock_encode.assert_not_called()


    @patch('prospect.core_logic.vectorization_utils.model.encode')
    def test_generate_lead_vector_no_analysis_details(self, mock_encode):
        mock_text_embedding = np.random.rand(384).astype(np.float32)
        mock_encode.return_value = mock_text_embedding

        vector = generate_lead_vector(self.analyzed_lead_no_analysis_details)

        self.assertIsNotNone(vector)
        self.assertIsInstance(vector, list)
        # Expected length: text_embedding_dim + 3 structured features (0.1, 0.0 for sector, 0.0 for challenges)
        self.assertEqual(len(vector), 384 + 3)
        # Check structured part
        self.assertAlmostEqual(vector[384], 0.1) # relevance_score
        self.assertEqual(vector[385], 0.0)      # company_sector (not present)
        self.assertEqual(vector[386], 0.0)      # potential_challenges (not present)
        mock_encode.assert_called_once_with(self.mock_validated_lead_full.cleaned_text_content, convert_to_tensor=False)

    def test_generate_lead_vector_empty_input(self):
        # Test with completely empty/None AnalyzedLead or its sub-fields if function expects it
        # Current generate_lead_vector checks for analyzed_lead itself
        self.assertIsNone(generate_lead_vector(None))

        # Test with an AnalyzedLead that has None for validated_lead.cleaned_text_content
        # and minimal analysis, effectively leading to no vector parts.
        vector = generate_lead_vector(self.analyzed_lead_empty)
        self.assertIsNone(vector) # Should return None as no text and minimal structured data might lead to empty list

    @patch('prospect.core_logic.vectorization_utils.model.encode')
    def test_vector_concatenation_order_and_values(self, mock_encode):
        mock_text_embedding = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        mock_encode.return_value = mock_text_embedding

        # Customize lead to have predictable structured features
        custom_validated_lead = ValidatedLead(
            lead_id="custom", company_name="Custom",
            site_data=MagicMock(), cleaned_text_content="Custom text.", extraction_successful=True,
            validation_timestamp=MagicMock(), is_valid=True, validation_errors=[]
        )
        custom_analysis = LeadAnalysis(
            company_sector="Financeiro", main_services=[], potential_challenges=["C1"],
            relevance_score=0.75, general_diagnosis="", opportunity_fit=""
        )
        custom_lead = AnalyzedLead(
            validated_lead=custom_validated_lead, analysis=custom_analysis, product_service_context=""
        )

        vector = generate_lead_vector(custom_lead)

        self.assertIsNotNone(vector)
        expected_vector = [0.1, 0.2, 0.3, 0.75, 1.0, 1.0] # text_emb, relevance, sector_present, challenge_present
        self.assertEqual(len(vector), len(expected_vector))
        for i in range(len(vector)):
            self.assertAlmostEqual(vector[i], expected_vector[i], places=4)

if __name__ == '__main__':
    unittest.main()
