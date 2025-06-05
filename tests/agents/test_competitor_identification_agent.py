import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import json

from agents.competitor_identification_agent import CompetitorIdentificationAgent, CompetitorIdentificationInput, CompetitorIdentificationOutput, CompetitorDetail
from core_logic.llm_client import LLMClientBase, LLMResponse
from mcp_server.data_models import AgentExecutionStatusEnum

class TestCompetitorIdentificationAgent(unittest.IsolatedAsyncioTestCase): # Changed to IsolatedAsyncioTestCase

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.generate_llm_response = AsyncMock() # Mock async method
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0, "llm_calls": 0, "llm_usage": []}
        self.mock_llm_client.update_usage_stats = MagicMock()

        self.agent = CompetitorIdentificationAgent(llm_client=self.mock_llm_client)

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_success_finds_competitors(self, mock_report_event: MagicMock): # Made async
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

        self.mock_llm_client.generate_llm_response.return_value = mock_json_output_str

        test_input = CompetitorIdentificationInput(
            initial_extracted_text="Nossa empresa, Exemplo Corp, se destaca pela flexibilidade, ao contrário de Soluções Alfa. Também observamos a Tech Inovadora Ltda.",
            product_service_offered="Software de Gestão Personalizado",
            known_competitors_list_str="Soluções Beta, Rival X" # Known but not in text
        )

        result = await self.agent.execute(test_input, lead_id="test_lead_01", run_id="test_run_01")

        self.assertIsInstance(result, CompetitorIdentificationOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(len(result.identified_competitors), 2)

        self.assertEqual(result.identified_competitors[0].name, mock_competitor1.name)
        self.assertEqual(result.identified_competitors[0].description, mock_competitor1.description)
        self.assertEqual(result.identified_competitors[1].name, mock_competitor2.name)

        self.assertEqual(result.other_notes, "O mercado parece ter alguns players consolidados e novas startups.")
        self.mock_llm_client.generate_llm_response.assert_called_once()

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_01")
        self.assertEqual(args[1], self.agent.name)
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS)


    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_no_competitors_found(self, mock_report_event: MagicMock): # Made async
        mock_json_output_dict = {
            "identified_competitors": [],
            "other_notes": "Nenhuma menção clara a concorrentes diretos no texto fornecido."
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)
        self.mock_llm_client.generate_llm_response.return_value = mock_json_output_str

        test_input = CompetitorIdentificationInput(
            initial_extracted_text="Somos uma empresa única em um novo mercado.",
            product_service_offered="Solução Pioneira Delta"
        )
        result = await self.agent.execute(test_input, lead_id="test_lead_02", run_id="test_run_02")

        self.assertIsInstance(result, CompetitorIdentificationOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(len(result.identified_competitors), 0)
        self.assertEqual(result.other_notes, "Nenhuma menção clara a concorrentes diretos no texto fornecido.")

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_02")
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS)

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_llm_returns_malformed_json(self, mock_report_event: MagicMock): # Made async
        malformed_json_str = '{ "identified_competitors": [ {"name": "Concorrente Quebrado"} ' # Malformed
        self.mock_llm_client.generate_llm_response.return_value = malformed_json_str

        test_input = CompetitorIdentificationInput(
            initial_extracted_text="Texto qualquer.",
            product_service_offered="Produto qualquer."
        )
        result = await self.agent.execute(test_input, lead_id="test_lead_03", run_id="test_run_03")

        self.assertIsInstance(result, CompetitorIdentificationOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to parse LLM response as JSON", result.error_message)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_03")
        self.assertEqual(args[2], AgentExecutionStatusEnum.FAILED)

if __name__ == '__main__':
    unittest.main()
