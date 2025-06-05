import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import json

from agents.tot_strategy_generation_agent import ToTStrategyGenerationAgent, ToTStrategyGenerationInput, ToTStrategyGenerationOutput, ToTStrategyOptionModel
from core_logic.llm_client import LLMClientBase, LLMResponse
from mcp_server.data_models import AgentExecutionStatusEnum

class TestToTStrategyGenerationAgent(unittest.IsolatedAsyncioTestCase): # Changed to IsolatedAsyncioTestCase

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.generate_llm_response = AsyncMock() # Mock async method
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0, "llm_calls": 0, "llm_usage": []}
        self.mock_llm_client.update_usage_stats = MagicMock()

        self.agent = ToTStrategyGenerationAgent(llm_client=self.mock_llm_client)

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_success_generates_strategies(self, mock_report_event: MagicMock): # Made async
        mock_strategy1 = ToTStrategyOptionModel(
            strategy_name="Abordagem Consultiva Direta",
            angle_or_hook="Focar nos desafios de escalabilidade mencionados.",
            tone_of_voice="Consultivo e especialista",
            primary_channels=["Email", "LinkedIn"],
            key_points_or_arguments=["Como nossa solução X resolve o problema Y.", "Case de sucesso similar."],
            opening_question="Percebi que mencionaram desafios com escalabilidade; como isso impacta seus planos de crescimento para 2024?"
        )
        mock_strategy2 = ToTStrategyOptionModel(
            strategy_name="Networking via Evento do Setor",
            angle_or_hook="Conectar em um nível mais pessoal e contextual.",
            tone_of_voice="Cordial e informativo",
            primary_channels=["Evento Online", "LinkedIn (follow-up)"],
            key_points_or_arguments=["Benefício Z da nossa plataforma.", "Alinhamento com tendências do setor discutidas no evento."],
            opening_question="Ótima apresentação no evento X! Como você vê a aplicação da tendência Y na prática da Empresa Teste?"
        )

        mock_json_output_dict = {
            "proposed_strategies": [
                mock_strategy1.model_dump(),
                mock_strategy2.model_dump()
            ]
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)

        self.mock_llm_client.generate_llm_response.return_value = mock_json_output_str

        test_input = ToTStrategyGenerationInput(
            current_lead_summary="Empresa Teste, setor de SaaS, buscando escalar operações. Persona: Diretor de Ops.",
            product_service_offered="Plataforma de Otimização de Processos"
        )

        result = await self.agent.execute(test_input, lead_id="test_lead_01", run_id="test_run_01")

        self.assertIsInstance(result, ToTStrategyGenerationOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(len(result.proposed_strategies), 2)

        self.assertEqual(result.proposed_strategies[0].strategy_name, mock_strategy1.strategy_name)
        self.assertEqual(result.proposed_strategies[0].angle_or_hook, mock_strategy1.angle_or_hook)
        self.assertListEqual(result.proposed_strategies[1].primary_channels, mock_strategy2.primary_channels)

        self.mock_llm_client.generate_llm_response.assert_called_once()
        called_prompt = self.mock_llm_client.generate_llm_response.call_args[0][0]
        self.assertIn("Responda APENAS com um objeto JSON", called_prompt)
        self.assertIn("proposed_strategies", called_prompt)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_01")
        self.assertEqual(args[1], self.agent.name)
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS)
        self.assertIsInstance(args[5], ToTStrategyGenerationOutput)
        self.assertEqual(len(args[5].proposed_strategies), 2)


    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_llm_returns_empty_list(self, mock_report_event: MagicMock): # Made async
        mock_json_output_dict = {"proposed_strategies": []}
        mock_json_output_str = json.dumps(mock_json_output_dict)
        self.mock_llm_client.generate_llm_response.return_value = mock_json_output_str

        test_input = ToTStrategyGenerationInput(
            current_lead_summary="Lead com poucas informações.",
            product_service_offered="Produto genérico"
        )
        result = await self.agent.execute(test_input, lead_id="test_lead_02", run_id="test_run_02")

        self.assertIsInstance(result, ToTStrategyGenerationOutput)
        self.assertIsNone(result.error_message) # Empty list is valid JSON and expected by model
        self.assertEqual(len(result.proposed_strategies), 0)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_02")
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS)


    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_llm_returns_malformed_json(self, mock_report_event: MagicMock): # Made async
        malformed_json_str = '{ "proposed_strategies": [ {"strategy_name": "Quebrado"} '
        self.mock_llm_client.generate_llm_response.return_value = malformed_json_str

        test_input = ToTStrategyGenerationInput(
            current_lead_summary="Qualquer.", product_service_offered="Qualquer."
        )
        result = await self.agent.execute(test_input, lead_id="test_lead_03", run_id="test_run_03")

        self.assertIsInstance(result, ToTStrategyGenerationOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to parse LLM response as JSON", result.error_message)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_03")
        self.assertEqual(args[2], AgentExecutionStatusEnum.FAILED)

if __name__ == '__main__':
    unittest.main()
