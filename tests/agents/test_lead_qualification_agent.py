import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import json

from agents.lead_qualification_agent import LeadQualificationAgent, LeadQualificationInput, LeadQualificationOutput
from core_logic.llm_client import LLMClientBase, LLMResponse
from mcp_server.data_models import AgentExecutionStatusEnum

class TestLeadQualificationAgent(unittest.IsolatedAsyncioTestCase): # Changed to IsolatedAsyncioTestCase

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.generate_llm_response = AsyncMock() # Mock async method
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0, "llm_calls": 0, "llm_usage": []}
        self.mock_llm_client.update_usage_stats = MagicMock()

        self.agent = LeadQualificationAgent(llm_client=self.mock_llm_client)

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_success_high_potential(self, mock_report_event: MagicMock): # Made async
        mock_json_output_dict = {
            "qualification_tier": "Alto Potencial",
            "justification": "O lead demonstra forte alinhamento com o produto, dores claras e urgência.",
            "confidence_score": 0.92
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)

        self.mock_llm_client.generate_llm_response.return_value = mock_json_output_str

        test_input = LeadQualificationInput(
            lead_analysis="Empresa Z demonstra crescimento rápido e investimento em tecnologia.",
            persona_profile="Mariana, CTO, buscando soluções inovadoras para escalar operações.",
            deepened_pain_points="Sistemas atuais não suportam a demanda, causando perda de oportunidades.",
            product_service_offered="Plataforma de escalabilidade XaaS"
        )

        result = await self.agent.execute(test_input, lead_id="test_lead_01", run_id="test_run_01")

        self.assertIsInstance(result, LeadQualificationOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.qualification_tier, "Alto Potencial")
        self.assertEqual(result.justification, "O lead demonstra forte alinhamento com o produto, dores claras e urgência.")
        self.assertEqual(result.confidence_score, 0.92)
        self.mock_llm_client.generate_llm_response.assert_called_once()

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_01")
        self.assertEqual(args[1], self.agent.name)
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS)

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_llm_returns_malformed_json(self, mock_report_event: MagicMock): # Made async
        malformed_json_str = '{ "qualification_tier": "Potencial Médio", "justification": "Algum alinhamento..." '
        self.mock_llm_client.generate_llm_response.return_value = malformed_json_str

        test_input = LeadQualificationInput(
            lead_analysis="Análise.",
            persona_profile="Persona.",
            deepened_pain_points="Dores.",
            product_service_offered="Produto."
        )

        result = await self.agent.execute(test_input, lead_id="test_lead_02", run_id="test_run_02")

        self.assertIsInstance(result, LeadQualificationOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to parse LLM response as JSON", result.error_message)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_02")
        self.assertEqual(args[2], AgentExecutionStatusEnum.FAILED)


    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_llm_returns_empty_response(self, mock_report_event: MagicMock): # Made async
        self.mock_llm_client.generate_llm_response.return_value = ""

        test_input = LeadQualificationInput(
            lead_analysis="Análise.",
            persona_profile="Persona.",
            deepened_pain_points="Dores.",
            product_service_offered="Produto."
        )

        result = await self.agent.execute(test_input, lead_id="test_lead_03", run_id="test_run_03")

        self.assertIsInstance(result, LeadQualificationOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("LLM call returned no response.", result.error_message)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_03")
        self.assertEqual(args[2], AgentExecutionStatusEnum.FAILED)


    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_llm_returns_json_with_unknown_tier(self, mock_report_event: MagicMock): # Made async
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
