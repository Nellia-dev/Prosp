import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import json

from agents.strategic_question_generation_agent import StrategicQuestionGenerationAgent, StrategicQuestionGenerationInput, StrategicQuestionGenerationOutput
from core_logic.llm_client import LLMClientBase, LLMResponse
from mcp_server.data_models import AgentExecutionStatusEnum

class TestStrategicQuestionGenerationAgent(unittest.IsolatedAsyncioTestCase): # Changed to IsolatedAsyncioTestCase

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.generate_llm_response = AsyncMock() # Mock async method
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0, "llm_calls": 0, "llm_usage": []}
        self.mock_llm_client.update_usage_stats = MagicMock()

        self.agent = StrategicQuestionGenerationAgent(llm_client=self.mock_llm_client)

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_success_generates_questions(self, mock_report_event: MagicMock): # Made async
        mock_json_output_dict = {
            "generated_questions": [
                "Considerando a expansão para o mercado X, como vocês planejam adaptar sua infraestrutura tecnológica atual?",
                "Quais seriam os principais indicadores de sucesso para a adoção de uma nova plataforma de gestão nos próximos 12 meses?",
                "De que forma a otimização de processos internos poderia liberar recursos para inovação em novos produtos?"
            ]
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)

        self.mock_llm_client.generate_llm_response.return_value = mock_json_output_str

        test_input = StrategicQuestionGenerationInput(
            lead_analysis="A Empresa Gama está crescendo rapidamente e planeja expansão internacional.",
            persona_profile="Roberto Silva, CEO, focado em crescimento sustentável e inovação.",
            deepened_pain_points="Sistemas atuais podem não escalar. Equipe sobrecarregada com tarefas manuais."
        )

        result = await self.agent.execute(test_input, lead_id="test_lead_01", run_id="test_run_01")

        self.assertIsInstance(result, StrategicQuestionGenerationOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(len(result.generated_questions), 3)
        self.assertIn("Considerando a expansão para o mercado X", result.generated_questions[0])
        self.mock_llm_client.generate_llm_response.assert_called_once()

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_01")
        self.assertEqual(args[1], self.agent.name)
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS)


    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_no_questions_generated_empty_list(self, mock_report_event: MagicMock): # Made async
        mock_json_output_dict = {"generated_questions": []}
        mock_json_output_str = json.dumps(mock_json_output_dict)
        self.mock_llm_client.generate_llm_response.return_value = mock_json_output_str

        test_input = StrategicQuestionGenerationInput(
            lead_analysis="Empresa pequena, sem grandes desafios aparentes.",
            persona_profile="Dono único, satisfeito com o status quo.",
            deepened_pain_points="Nenhuma dor profunda identificada."
        )
        result = await self.agent.execute(test_input, lead_id="test_lead_02", run_id="test_run_02")

        self.assertIsInstance(result, StrategicQuestionGenerationOutput)
        self.assertIsNone(result.error_message) # Agent process itself succeeds even if no questions.
        self.assertEqual(len(result.generated_questions), 0)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_02")
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS)


    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_llm_returns_malformed_json(self, mock_report_event: MagicMock): # Made async
        malformed_json_str = '{ "generated_questions": ["Pergunta 1", "Pergunta 2" ' # Malformed
        self.mock_llm_client.generate_llm_response.return_value = malformed_json_str

        test_input = StrategicQuestionGenerationInput(
            lead_analysis="Qualquer.", persona_profile="Qualquer.", deepened_pain_points="Qualquer."
        )
        result = await self.agent.execute(test_input, lead_id="test_lead_03", run_id="test_run_03")

        self.assertIsInstance(result, StrategicQuestionGenerationOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to parse LLM response as JSON", result.error_message)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_03")
        self.assertEqual(args[2], AgentExecutionStatusEnum.FAILED)

if __name__ == '__main__':
    unittest.main()
