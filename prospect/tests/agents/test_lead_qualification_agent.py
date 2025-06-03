import unittest
from unittest.mock import MagicMock
import json

from agents.lead_qualification_agent import LeadQualificationAgent, LeadQualificationInput, LeadQualificationOutput
from core_logic.llm_client import LLMClientBase, LLMResponse

class TestLeadQualificationAgent(unittest.TestCase):

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0}
        self.mock_llm_client.update_usage_stats = MagicMock()
        
        self.agent = LeadQualificationAgent(llm_client=self.mock_llm_client)

    def test_process_success_high_potential(self):
        mock_json_output_dict = {
            "qualification_tier": "Alto Potencial",
            "justification": "O lead demonstra forte alinhamento com o produto, dores claras e urgência.",
            "confidence_score": 0.92
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)
        
        self.mock_llm_client.generate.return_value = LLMResponse(content=mock_json_output_str, provider_name="mock", model_name="mock_model", total_tokens=40, input_tokens=20, output_tokens=20)

        test_input = LeadQualificationInput(
            lead_analysis="Empresa Z demonstra crescimento rápido e investimento em tecnologia.",
            persona_profile="Mariana, CTO, buscando soluções inovadoras para escalar operações.",
            deepened_pain_points="Sistemas atuais não suportam a demanda, causando perda de oportunidades.",
            product_service_offered="Plataforma de escalabilidade XaaS"
        )
        
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, LeadQualificationOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.qualification_tier, "Alto Potencial")
        self.assertEqual(result.justification, "O lead demonstra forte alinhamento com o produto, dores claras e urgência.")
        self.assertEqual(result.confidence_score, 0.92)
        self.mock_llm_client.generate.assert_called_once()
        # call_args = self.mock_llm_client.generate.call_args
        # called_prompt = call_args[0][0] 
        # self.assertIn(test_input.product_service_offered, called_prompt)

    def test_process_llm_returns_malformed_json(self):
        malformed_json_str = '{ "qualification_tier": "Potencial Médio", "justification": "Algum alinhamento..." ' # Missing closing brace and confidence
        self.mock_llm_client.generate.return_value = LLMResponse(content=malformed_json_str, provider_name="mock", model_name="mock_model", total_tokens=10, input_tokens=5, output_tokens=5)

        test_input = LeadQualificationInput(
            lead_analysis="Análise.",
            persona_profile="Persona.",
            deepened_pain_points="Dores.",
            product_service_offered="Produto."
        )
        
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, LeadQualificationOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to parse LLM response as JSON", result.error_message)
        self.assertEqual(result.qualification_tier, "Não Qualificado") # Default value
        self.assertEqual(result.justification, "Não foi possível determinar a qualificação.") # Default
        self.assertIsNone(result.confidence_score) # Default

    def test_process_llm_returns_empty_response(self):
        self.mock_llm_client.generate.return_value = LLMResponse(content="", provider_name="mock", model_name="mock_model", total_tokens=2, input_tokens=1, output_tokens=1)

        test_input = LeadQualificationInput(
            lead_analysis="Análise.",
            persona_profile="Persona.",
            deepened_pain_points="Dores.",
            product_service_offered="Produto."
        )
        
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, LeadQualificationOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("LLM call returned no response.", result.error_message)
        self.assertEqual(result.qualification_tier, "Não Qualificado") # Default


    def test_process_llm_returns_json_with_unknown_tier(self):
        # Test if the model handles unexpected enum values gracefully if not strictly parsed by Pydantic
        # Pydantic will likely raise an error if "Tier Desconhecido" is not in an Enum for qualification_tier.
        # However, our current LeadQualificationOutput.qualification_tier is just a string, so this will pass.
        # If it were an Enum, parse_llm_json_response would set an error.
        mock_json_output_dict = {
            "qualification_tier": "Tier Desconhecido", 
            "justification": "LLM retornou um tier não esperado.",
            "confidence_score": 0.5
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)
        self.mock_llm_client.generate.return_value = LLMResponse(content=mock_json_output_str, provider_name="mock", model_name="mock_model", total_tokens=20, input_tokens=10, output_tokens=10)
        
        test_input = LeadQualificationInput(
            lead_analysis="Análise.",
            persona_profile="Persona.",
            deepened_pain_points="Dores.",
            product_service_offered="Produto."
        )
        result = self.agent.execute(test_input)
        
        self.assertIsInstance(result, LeadQualificationOutput)
        self.assertIsNone(result.error_message) # Pydantic will accept any string for qualification_tier
        self.assertEqual(result.qualification_tier, "Tier Desconhecido")
        self.assertEqual(result.justification, "LLM retornou um tier não esperado.")

if __name__ == '__main__':
    unittest.main()
