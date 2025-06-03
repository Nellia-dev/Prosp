import unittest
from unittest.mock import MagicMock
import json

from agents.lead_analysis_generation_agent import LeadAnalysisGenerationAgent, LeadAnalysisGenerationInput, LeadAnalysisGenerationOutput
from core_logic.llm_client import LLMClientBase, LLMResponse

class TestLeadAnalysisGenerationAgent(unittest.TestCase):

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0}
        self.mock_llm_client.update_usage_stats = MagicMock()
        
        self.agent = LeadAnalysisGenerationAgent(llm_client=self.mock_llm_client)

    def test_process_success(self):
        # Note: LeadAnalysisGenerationOutput is currently defined as `analysis_report: str`.
        # The agent should still be prompted to return JSON for consistency with BaseAgent.parse_llm_json_response,
        # even if that JSON just wraps the string report.
        mock_report_text = (
            "A Empresa Exemplo atua no setor de Tecnologia da Informação, oferecendo principalmente soluções de software como serviço (SaaS). "
            "Com base nos dados, parece ser uma empresa de médio porte. "
            "Seus principais desafios podem incluir a necessidade de otimizar processos internos. "
            "Diagnóstico geral: Lead com bom potencial."
        )
        mock_json_output_dict = {
            "analysis_report": mock_report_text
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)
        
        self.mock_llm_client.generate.return_value = LLMResponse(content=mock_json_output_str, provider_name="mock", model_name="mock_model", total_tokens=100, input_tokens=50, output_tokens=50)

        test_input = LeadAnalysisGenerationInput(
            lead_data_str='{"company_name": "Empresa Exemplo", "url": "http://example.com", "description": "Líder em TI."}',
            enriched_data="Nenhuma informação adicional.",
            product_service_offered="Nossas Soluções Incríveis"
        )
        
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, LeadAnalysisGenerationOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.analysis_report, mock_report_text)
        self.mock_llm_client.generate.assert_called_once()
        
        # Check that the prompt requests JSON
        called_prompt = self.mock_llm_client.generate.call_args[0][0]
        self.assertIn("Responda APENAS com um objeto JSON", called_prompt)
        self.assertIn("analysis_report", called_prompt) # Check if the field name is in the prompt
        self.assertIn(test_input.product_service_offered, called_prompt)


    def test_process_llm_returns_malformed_json(self):
        malformed_json_str = '{ "analysis_report": "Relatório quebrado... ' # Malformed
        self.mock_llm_client.generate.return_value = LLMResponse(content=malformed_json_str, provider_name="mock", model_name="mock_model", total_tokens=10, input_tokens=5, output_tokens=5)

        test_input = LeadAnalysisGenerationInput(
            lead_data_str='{}', enriched_data="", product_service_offered="Test Product"
        )
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, LeadAnalysisGenerationOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to parse LLM response as JSON", result.error_message)
        self.assertEqual(result.analysis_report, "") # Should default to empty string

    def test_process_llm_returns_empty_response(self):
        self.mock_llm_client.generate.return_value = LLMResponse(content="", provider_name="mock", model_name="mock_model", total_tokens=2, input_tokens=1, output_tokens=1)
        
        test_input = LeadAnalysisGenerationInput(
            lead_data_str='{}', enriched_data="", product_service_offered="Test Product"
        )
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, LeadAnalysisGenerationOutput)
        self.assertIsNotNone(result.error_message)
        # This error comes from parse_llm_json_response when content is empty
        self.assertIn("LLM response content is empty or not valid JSON", result.error_message)


if __name__ == '__main__':
    unittest.main()
