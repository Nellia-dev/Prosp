import unittest
from unittest.mock import MagicMock
import json

from agents.competitor_identification_agent import CompetitorIdentificationAgent, CompetitorIdentificationInput, CompetitorIdentificationOutput, CompetitorDetail
from core_logic.llm_client import LLMClientBase, LLMResponse

class TestCompetitorIdentificationAgent(unittest.TestCase):

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0}
        self.mock_llm_client.update_usage_stats = MagicMock()
        
        self.agent = CompetitorIdentificationAgent(llm_client=self.mock_llm_client)

    def test_process_success_finds_competitors(self):
        mock_competitor1 = CompetitorDetail(
            name="Soluções Alfa",
            description="Concorrente direto que oferece produtos similares.",
            perceived_strength="Marca estabelecida.",
            perceived_weakness="Menos flexível."
        )
        mock_competitor2 = CompetitorDetail(
            name="Tech Inovadora Ltda",
            description="Startup com soluções de nicho que se sobrepõem parcialmente.",
            perceived_strength="Ágil e inovadora.",
            perceived_weakness="Menor base de clientes."
        )
        
        mock_json_output_dict = {
            "identified_competitors": [
                mock_competitor1.model_dump(),
                mock_competitor2.model_dump()
            ],
            "other_notes": "O mercado parece ter alguns players consolidados e novas startups."
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)
        
        self.mock_llm_client.generate.return_value = LLMResponse(content=mock_json_output_str, provider_name="mock", model_name="mock_model", total_tokens=60, input_tokens=30, output_tokens=30)

        test_input = CompetitorIdentificationInput(
            initial_extracted_text="Nossa empresa, Exemplo Corp, se destaca pela flexibilidade, ao contrário de Soluções Alfa. Também observamos a Tech Inovadora Ltda.",
            product_service_offered="Software de Gestão Personalizado",
            known_competitors_list_str="Soluções Beta, Rival X" # Known but not in text
        )
        
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, CompetitorIdentificationOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(len(result.identified_competitors), 2)
        
        self.assertEqual(result.identified_competitors[0].name, mock_competitor1.name)
        self.assertEqual(result.identified_competitors[0].description, mock_competitor1.description)
        self.assertEqual(result.identified_competitors[1].name, mock_competitor2.name)
        
        self.assertEqual(result.other_notes, "O mercado parece ter alguns players consolidados e novas startups.")
        self.mock_llm_client.generate.assert_called_once()
        # call_args = self.mock_llm_client.generate.call_args[0][0]
        # self.assertIn(test_input.known_competitors_list_str, call_args)


    def test_process_no_competitors_found(self):
        mock_json_output_dict = {
            "identified_competitors": [],
            "other_notes": "Nenhuma menção clara a concorrentes diretos no texto fornecido."
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)
        self.mock_llm_client.generate.return_value = LLMResponse(content=mock_json_output_str, provider_name="mock", model_name="mock_model", total_tokens=20, input_tokens=10, output_tokens=10)

        test_input = CompetitorIdentificationInput(
            initial_extracted_text="Somos uma empresa única em um novo mercado.",
            product_service_offered="Solução Pioneira Delta"
        )
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, CompetitorIdentificationOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(len(result.identified_competitors), 0)
        self.assertEqual(result.other_notes, "Nenhuma menção clara a concorrentes diretos no texto fornecido.")

    def test_process_llm_returns_malformed_json(self):
        malformed_json_str = '{ "identified_competitors": [ {"name": "Concorrente Quebrado"} ' # Malformed
        self.mock_llm_client.generate.return_value = LLMResponse(content=malformed_json_str, provider_name="mock", model_name="mock_model", total_tokens=10, input_tokens=5, output_tokens=5)

        test_input = CompetitorIdentificationInput(
            initial_extracted_text="Texto qualquer.",
            product_service_offered="Produto qualquer."
        )
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, CompetitorIdentificationOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to parse LLM response as JSON", result.error_message)
        self.assertEqual(len(result.identified_competitors), 0) # Should default to empty list
        self.assertIsNone(result.other_notes) # Should default to None

if __name__ == '__main__':
    unittest.main()
