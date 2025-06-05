import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import json

from agents.lead_analysis_generation_agent import LeadAnalysisGenerationAgent, LeadAnalysisGenerationInput, LeadAnalysisGenerationOutput
from core_logic.llm_client import LLMClientBase, LLMResponse
from mcp_server.data_models import AgentExecutionStatusEnum

class TestLeadAnalysisGenerationAgent(unittest.IsolatedAsyncioTestCase): # Changed to IsolatedAsyncioTestCase

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.generate_llm_response = AsyncMock() # Mock async method
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0, "llm_calls": 0, "llm_usage": []}
        self.mock_llm_client.update_usage_stats = MagicMock()

        self.agent = LeadAnalysisGenerationAgent(llm_client=self.mock_llm_client)

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_success(self, mock_report_event: MagicMock): # Made async
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

        self.mock_llm_client.generate_llm_response.return_value = mock_json_output_str

        test_input = LeadAnalysisGenerationInput(
            lead_data_str='{"company_name": "Empresa Exemplo", "url": "http://example.com", "description": "Líder em TI."}',
            enriched_data="Nenhuma informação adicional.",
            product_service_offered="Nossas Soluções Incríveis"
        )

        result = await self.agent.execute(test_input, lead_id="test_lead_01", run_id="test_run_01")

        self.assertIsInstance(result, LeadAnalysisGenerationOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.analysis_report, mock_report_text)
        self.mock_llm_client.generate_llm_response.assert_called_once()

        called_prompt = self.mock_llm_client.generate_llm_response.call_args[0][0]
        self.assertIn("Responda APENAS com um objeto JSON", called_prompt)
        self.assertIn("analysis_report", called_prompt)
        self.assertIn(test_input.product_service_offered, called_prompt)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_01")
        self.assertEqual(args[1], self.agent.name)
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS)


    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_llm_returns_malformed_json(self, mock_report_event: MagicMock): # Made async
        malformed_json_str = '{ "analysis_report": "Relatório quebrado... ' # Malformed
        self.mock_llm_client.generate_llm_response.return_value = malformed_json_str

        test_input = LeadAnalysisGenerationInput(
            lead_data_str='{}', enriched_data="", product_service_offered="Test Product"
        )
        result = await self.agent.execute(test_input, lead_id="test_lead_02", run_id="test_run_02")

        self.assertIsInstance(result, LeadAnalysisGenerationOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to parse LLM response as JSON", result.error_message)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_02")
        self.assertEqual(args[2], AgentExecutionStatusEnum.FAILED)

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_llm_returns_empty_response(self, mock_report_event: MagicMock): # Made async
        self.mock_llm_client.generate_llm_response.return_value = ""

        test_input = LeadAnalysisGenerationInput(
            lead_data_str='{}', enriched_data="", product_service_offered="Test Product"
        )
        result = await self.agent.execute(test_input, lead_id="test_lead_03", run_id="test_run_03")

        self.assertIsInstance(result, LeadAnalysisGenerationOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("LLM response content is empty or not valid JSON", result.error_message)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_03")
        self.assertEqual(args[2], AgentExecutionStatusEnum.FAILED)


if __name__ == '__main__':
    unittest.main()
