import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import json

from agents.b2b_persona_creation_agent import B2BPersonaCreationAgent, B2BPersonaCreationInput, B2BPersonaCreationOutput
from core_logic.llm_client import LLMClientBase, LLMResponse
from mcp_server.data_models import AgentExecutionStatusEnum

class TestB2BPersonaCreationAgent(unittest.IsolatedAsyncioTestCase): # Changed to IsolatedAsyncioTestCase

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.generate_llm_response = AsyncMock() # Mock async method
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0, "llm_calls": 0, "llm_usage": []}
        self.mock_llm_client.update_usage_stats = MagicMock()

        self.agent = B2BPersonaCreationAgent(llm_client=self.mock_llm_client)

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_success(self, mock_report_event: MagicMock): # Made async
        mock_persona_text = (
            "Carlos Silva, Diretor de Marketing da TechSolutions Ltda. "
            "Responsável por estratégia de marketing digital e geração de leads. "
            "Busca soluções que otimizem o ROI de campanhas e melhorem a conversão. "
            "Prefere comunicação por email com dados e casos de sucesso. "
            "Nossa plataforma de Automação de Marketing pode ajudá-lo a segmentar audiências, "
            "automatizar funis e medir resultados com precisão."
        )
        # The agent's Pydantic output is B2BPersonaCreationOutput(persona_profile: str, error_message: Optional[str])
        # The LLM should be prompted to return JSON that contains this string.
        mock_json_output_dict = {
            "persona_profile": mock_persona_text
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)

        self.mock_llm_client.generate_llm_response.return_value = mock_json_output_str

        test_input = B2BPersonaCreationInput(
            lead_analysis="A TechSolutions Ltda é uma empresa de SaaS B2B em crescimento.",
            product_service_offered="Plataforma de Automação de Marketing",
            lead_url="http://techsolutions.example.com"
        )

        result = await self.agent.execute(test_input, lead_id="test_lead_01", run_id="test_run_01")

        self.assertIsInstance(result, B2BPersonaCreationOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.persona_profile, mock_persona_text)
        self.mock_llm_client.generate_llm_response.assert_called_once()

        called_prompt = self.mock_llm_client.generate_llm_response.call_args[0][0]
        self.assertIn("Responda APENAS com um objeto JSON", called_prompt)
        self.assertIn("persona_profile", called_prompt)
        self.assertIn(test_input.product_service_offered, called_prompt)

        mock_report_event.assert_called_once()
        args, kwargs = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_01") # lead_id
        self.assertEqual(args[1], self.agent.name)   # agent_name
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS) # status
        self.assertIsInstance(args[5], B2BPersonaCreationOutput) # output_model_instance
        self.assertEqual(args[5].persona_profile, mock_persona_text)


    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_llm_returns_malformed_json(self, mock_report_event: MagicMock): # Made async
        malformed_json_str = '{ "persona_profile": "Perfil quebrado... ' # Malformed
        self.mock_llm_client.generate_llm_response.return_value = malformed_json_str

        test_input = B2BPersonaCreationInput(
            lead_analysis="Análise.", product_service_offered="Produto.", lead_url="url"
        )
        result = await self.agent.execute(test_input, lead_id="test_lead_02", run_id="test_run_02")

        self.assertIsInstance(result, B2BPersonaCreationOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to parse LLM response as JSON", result.error_message)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_02")
        self.assertEqual(args[2], AgentExecutionStatusEnum.FAILED)


    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_llm_returns_empty_response(self, mock_report_event: MagicMock): # Made async
        self.mock_llm_client.generate_llm_response.return_value = ""

        test_input = B2BPersonaCreationInput(
            lead_analysis="Análise.", product_service_offered="Produto.", lead_url="url"
        )
        result = await self.agent.execute(test_input, lead_id="test_lead_03", run_id="test_run_03")

        self.assertIsInstance(result, B2BPersonaCreationOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("LLM response content is empty or not valid JSON", result.error_message)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_03")
        self.assertEqual(args[2], AgentExecutionStatusEnum.FAILED)


if __name__ == '__main__':
    unittest.main()
