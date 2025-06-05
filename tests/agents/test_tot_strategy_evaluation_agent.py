import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import json

from agents.tot_strategy_evaluation_agent import ToTStrategyEvaluationAgent, ToTStrategyEvaluationInput, ToTStrategyEvaluationOutput, EvaluatedStrategyModel
from core_logic.llm_client import LLMClientBase, LLMResponse
from mcp_server.data_models import AgentExecutionStatusEnum

class TestToTStrategyEvaluationAgent(unittest.IsolatedAsyncioTestCase): # Changed to IsolatedAsyncioTestCase

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.generate_llm_response = AsyncMock() # Mock async method
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0, "llm_calls": 0, "llm_usage": []}
        self.mock_llm_client.update_usage_stats = MagicMock()

        self.agent = ToTStrategyEvaluationAgent(llm_client=self.mock_llm_client)

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_success_evaluates_strategies(self, mock_report_event: MagicMock): # Made async
        mock_eval_strategy1 = EvaluatedStrategyModel(
            strategy_name="Abordagem Consultiva Direta",
            suitability_assessment="Alta adequação ao perfil do lead que busca expertise.",
            strengths=["Constrói confiança", "Permite aprofundar dores"],
            weaknesses_or_risks=["Pode ser demorada", "Requer alta habilidade consultiva"],
            suggested_improvements=["Incluir um case de sucesso conciso no primeiro contato."],
            confidence_score="Alta",
            confidence_justification="Alinhamento forte com as necessidades percebidas."
        )
        mock_eval_strategy2 = EvaluatedStrategyModel(
            strategy_name="Networking via Evento do Setor",
            suitability_assessment="Média adequação; depende da participação do lead no evento.",
            strengths=["Contato mais natural", "Possibilidade de encontrar outros contatos"],
            weaknesses_or_risks=["Baixa previsibilidade de encontro", "Pode ser superficial"],
            suggested_improvements=["Pesquisar antecipadamente se o lead confirmou presença."],
            confidence_score="Média",
            confidence_justification="Potencial existe, mas com incertezas."
        )

        mock_json_output_dict = {
            "evaluated_strategies": [
                mock_eval_strategy1.model_dump(),
                mock_eval_strategy2.model_dump()
            ]
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)

        self.mock_llm_client.generate_llm_response.return_value = mock_json_output_str

        test_input = ToTStrategyEvaluationInput(
            proposed_strategies_text="Estratégia 1: Abordagem Consultiva Direta...\nEstratégia 2: Networking via Evento do Setor...",
            current_lead_summary="Empresa Teste, Diretor de Ops focado em eficiência."
        )

        result = await self.agent.execute(test_input, lead_id="test_lead_01", run_id="test_run_01")

        self.assertIsInstance(result, ToTStrategyEvaluationOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(len(result.evaluated_strategies), 2)

        self.assertEqual(result.evaluated_strategies[0].strategy_name, mock_eval_strategy1.strategy_name)
        self.assertEqual(result.evaluated_strategies[0].suitability_assessment, mock_eval_strategy1.suitability_assessment)
        self.assertListEqual(result.evaluated_strategies[1].strengths, mock_eval_strategy2.strengths)

        self.mock_llm_client.generate_llm_response.assert_called_once()
        called_prompt = self.mock_llm_client.generate_llm_response.call_args[0][0]
        self.assertIn("Responda APENAS com um objeto JSON", called_prompt)
        self.assertIn("evaluated_strategies", called_prompt)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_01")
        self.assertEqual(args[1], self.agent.name)
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS)
        self.assertIsInstance(args[5], ToTStrategyEvaluationOutput)
        self.assertEqual(len(args[5].evaluated_strategies), 2)


    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_llm_returns_empty_list(self, mock_report_event: MagicMock): # Made async
        mock_json_output_dict = {"evaluated_strategies": []}
        mock_json_output_str = json.dumps(mock_json_output_dict)
        self.mock_llm_client.generate_llm_response.return_value = mock_json_output_str

        test_input = ToTStrategyEvaluationInput(
            proposed_strategies_text="Nenhuma estratégia proposta.",
            current_lead_summary="Lead com poucas informações."
        )
        result = await self.agent.execute(test_input, lead_id="test_lead_02", run_id="test_run_02")

        self.assertIsInstance(result, ToTStrategyEvaluationOutput)
        self.assertIsNone(result.error_message) # Empty list is valid
        self.assertEqual(len(result.evaluated_strategies), 0)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_02")
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS)

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_llm_returns_malformed_json(self, mock_report_event: MagicMock): # Made async
        malformed_json_str = '{ "evaluated_strategies": [ {"strategy_name": "Quebrado"} '
        self.mock_llm_client.generate_llm_response.return_value = malformed_json_str

        test_input = ToTStrategyEvaluationInput(
            proposed_strategies_text="Qualquer.", current_lead_summary="Qualquer."
        )
        result = await self.agent.execute(test_input, lead_id="test_lead_03", run_id="test_run_03")

        self.assertIsInstance(result, ToTStrategyEvaluationOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to parse LLM response as JSON", result.error_message)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_03")
        self.assertEqual(args[2], AgentExecutionStatusEnum.FAILED)

if __name__ == '__main__':
    unittest.main()
