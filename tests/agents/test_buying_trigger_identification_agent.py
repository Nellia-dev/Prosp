import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import json

from agents.buying_trigger_identification_agent import BuyingTriggerIdentificationAgent, BuyingTriggerIdentificationInput, BuyingTriggerIdentificationOutput, IdentifiedTrigger
from core_logic.llm_client import LLMClientBase, LLMResponse
from mcp_server.data_models import AgentExecutionStatusEnum

class TestBuyingTriggerIdentificationAgent(unittest.IsolatedAsyncioTestCase): # Changed to IsolatedAsyncioTestCase

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.generate_llm_response = AsyncMock() # Mock async method
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0, "llm_calls": 0, "llm_usage": []}
        self.mock_llm_client.update_usage_stats = MagicMock()

        self.agent = BuyingTriggerIdentificationAgent(llm_client=self.mock_llm_client)

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_success_identifies_triggers(self, mock_report_event: MagicMock): # Made async
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

        self.mock_llm_client.generate_llm_response.return_value = mock_json_output_str

        test_input = BuyingTriggerIdentificationInput(
            lead_data_str='{"company_name": "InovaTech", "description": "Líder em IA."}',
            enriched_data="InovaTech anunciou hoje captação de $20M em Série B. João Novo foi contratado como VP de Engenharia.",
            product_service_offered="Plataforma de DevOps Avançada"
        )

        result = await self.agent.execute(test_input, lead_id="test_lead_01", run_id="test_run_01")

        self.assertIsInstance(result, BuyingTriggerIdentificationOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(len(result.identified_triggers), 2)

        self.assertEqual(result.identified_triggers[0].trigger_description, mock_trigger1.trigger_description)
        self.assertEqual(result.identified_triggers[1].relevance_explanation, mock_trigger2.relevance_explanation)

        self.assertEqual(result.other_observations, "A empresa parece estar em fase de crescimento acelerado.")
        self.mock_llm_client.generate_llm_response.assert_called_once()

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_01")
        self.assertEqual(args[1], self.agent.name)
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS)


    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_no_triggers_found(self, mock_report_event: MagicMock): # Made async
        mock_json_output_dict = {
            "identified_triggers": [],
            "other_observations": "Nenhum gatilho de compra óbvio identificado nos dados fornecidos."
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)
        self.mock_llm_client.generate_llm_response.return_value = mock_json_output_str

        test_input = BuyingTriggerIdentificationInput(
            lead_data_str='{"company_name": "Estável Ltda", "description": "Operações consistentes."}',
            enriched_data="Nenhuma notícia recente sobre Estável Ltda.",
            product_service_offered="Serviços de Consultoria"
        )
        result = await self.agent.execute(test_input, lead_id="test_lead_02", run_id="test_run_02")

        self.assertIsInstance(result, BuyingTriggerIdentificationOutput)
        self.assertIsNone(result.error_message) # Agent process succeeds, just no triggers found
        self.assertEqual(len(result.identified_triggers), 0)
        self.assertEqual(result.other_observations, "Nenhum gatilho de compra óbvio identificado nos dados fornecidos.")

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_02")
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS)


    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_llm_returns_malformed_json(self, mock_report_event: MagicMock): # Made async
        malformed_json_str = '{ "identified_triggers": [ {"trigger_description": "Incompleto..."} '
        self.mock_llm_client.generate_llm_response.return_value = malformed_json_str

        test_input = BuyingTriggerIdentificationInput(
            lead_data_str="{}", enriched_data="", product_service_offered=""
        )
        result = await self.agent.execute(test_input, lead_id="test_lead_03", run_id="test_run_03")

        self.assertIsInstance(result, BuyingTriggerIdentificationOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to parse LLM response as JSON", result.error_message)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_03")
        self.assertEqual(args[2], AgentExecutionStatusEnum.FAILED)

if __name__ == '__main__':
    unittest.main()
