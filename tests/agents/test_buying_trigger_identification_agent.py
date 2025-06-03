import unittest
from unittest.mock import MagicMock
import json

from agents.buying_trigger_identification_agent import BuyingTriggerIdentificationAgent, BuyingTriggerIdentificationInput, BuyingTriggerIdentificationOutput, IdentifiedTrigger
from core_logic.llm_client import LLMClientBase, LLMResponse

class TestBuyingTriggerIdentificationAgent(unittest.TestCase):

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0}
        self.mock_llm_client.update_usage_stats = MagicMock()
        
        self.agent = BuyingTriggerIdentificationAgent(llm_client=self.mock_llm_client)

    def test_process_success_identifies_triggers(self):
        mock_trigger1 = IdentifiedTrigger(
            trigger_description="Anúncio de nova rodada de investimento (Série B).",
            relevance_explanation="Indica capital para expansão e aquisição de novas tecnologias/soluções."
        )
        mock_trigger2 = IdentifiedTrigger(
            trigger_description="Contratação de novo VP de Engenharia.",
            relevance_explanation="Novos líderes frequentemente revisam e atualizam a stack tecnológica e processos."
        )
        
        mock_json_output_dict = {
            "identified_triggers": [
                mock_trigger1.model_dump(),
                mock_trigger2.model_dump()
            ],
            "other_observations": "A empresa parece estar em fase de crescimento acelerado."
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)
        
        self.mock_llm_client.generate.return_value = LLMResponse(content=mock_json_output_str, provider_name="mock", model_name="mock_model", total_tokens=80, input_tokens=40, output_tokens=40)

        test_input = BuyingTriggerIdentificationInput(
            lead_data_str='{"company_name": "InovaTech", "description": "Líder em IA."}',
            enriched_data="InovaTech anunciou hoje captação de $20M em Série B. João Novo foi contratado como VP de Engenharia.",
            product_service_offered="Plataforma de DevOps Avançada"
        )
        
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, BuyingTriggerIdentificationOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(len(result.identified_triggers), 2)
        
        self.assertEqual(result.identified_triggers[0].trigger_description, mock_trigger1.trigger_description)
        self.assertEqual(result.identified_triggers[1].relevance_explanation, mock_trigger2.relevance_explanation)
        
        self.assertEqual(result.other_observations, "A empresa parece estar em fase de crescimento acelerado.")
        self.mock_llm_client.generate.assert_called_once()
        # call_args = self.mock_llm_client.generate.call_args[0][0]
        # self.assertIn(test_input.enriched_data, call_args)

    def test_process_no_triggers_found(self):
        mock_json_output_dict = {
            "identified_triggers": [],
            "other_observations": "Nenhum gatilho de compra óbvio identificado nos dados fornecidos."
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)
        self.mock_llm_client.generate.return_value = LLMResponse(content=mock_json_output_str, provider_name="mock", model_name="mock_model", total_tokens=20, input_tokens=10, output_tokens=10)

        test_input = BuyingTriggerIdentificationInput(
            lead_data_str='{"company_name": "Estável Ltda", "description": "Operações consistentes."}',
            enriched_data="Nenhuma notícia recente sobre Estável Ltda.",
            product_service_offered="Serviços de Consultoria"
        )
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, BuyingTriggerIdentificationOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(len(result.identified_triggers), 0)
        self.assertEqual(result.other_observations, "Nenhum gatilho de compra óbvio identificado nos dados fornecidos.")

    def test_process_llm_returns_malformed_json(self):
        malformed_json_str = '{ "identified_triggers": [ {"trigger_description": "Incompleto..."} '
        self.mock_llm_client.generate.return_value = LLMResponse(content=malformed_json_str, provider_name="mock", model_name="mock_model", total_tokens=10, input_tokens=5, output_tokens=5)

        test_input = BuyingTriggerIdentificationInput(
            lead_data_str="{}", enriched_data="", product_service_offered=""
        )
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, BuyingTriggerIdentificationOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to parse LLM response as JSON", result.error_message)
        self.assertEqual(len(result.identified_triggers), 0) 
        self.assertIsNone(result.other_observations)

if __name__ == '__main__':
    unittest.main()
