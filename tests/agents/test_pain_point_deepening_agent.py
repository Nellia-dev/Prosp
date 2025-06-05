import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import json

from agents.pain_point_deepening_agent import PainPointDeepeningAgent, PainPointDeepeningInput, PainPointDeepeningOutput, DetailedPainPoint
from core_logic.llm_client import LLMClientBase, LLMResponse
from mcp_server.data_models import AgentExecutionStatusEnum

class TestPainPointDeepeningAgent(unittest.IsolatedAsyncioTestCase): # Changed to IsolatedAsyncioTestCase

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.generate_llm_response = AsyncMock() # Mock async method
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0, "llm_calls": 0, "llm_usage": []}
        self.mock_llm_client.update_usage_stats = MagicMock()

        self.agent = PainPointDeepeningAgent(llm_client=self.mock_llm_client)

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_success(self, mock_report_event: MagicMock): # Made async, added mock_report_event
        mock_detailed_pain_point1 = DetailedPainPoint(
            pain_description="Lentidão na geração de relatórios financeiros.",
            business_impact="Atraso na tomada de decisões estratégicas e identificação de riscos.",
            solution_alignment="Nossa solução automatiza a coleta e processamento de dados, gerando relatórios em tempo real."
        )
        mock_detailed_pain_point2 = DetailedPainPoint(
            pain_description="Dificuldade em integrar dados de diferentes sistemas.",
            business_impact="Visão fragmentada do desempenho da empresa e retrabalho manual.",
            solution_alignment="Oferecemos conectores nativos para os principais ERPs e sistemas legados, consolidando informações."
        )

        mock_json_output_dict = {
            "primary_pain_category": "Eficiência Operacional",
            "detailed_pain_points": [
                mock_detailed_pain_point1.model_dump(),
                mock_detailed_pain_point2.model_dump()
            ],
            "urgency_level": "high",
            "investigative_questions": [
                "Quais são os principais gargalos que vocês identificam no fechamento mensal?",
                "Como a falta de integração de dados afeta a colaboração entre departamentos?"
            ]
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)

        self.mock_llm_client.generate_llm_response.return_value = mock_json_output_str # generate_llm_response returns string

        test_input = PainPointDeepeningInput(
            lead_analysis="Empresa X demonstra crescimento, mas mencionou desafios com sistemas legados.",
            persona_profile="Carlos, Diretor de TI, focado em modernização e eficiência.",
            product_service_offered="Solução de Business Intelligence",
            company_name="Empresa X"
        )

        result = await self.agent.execute(test_input, lead_id="test_lead_01", run_id="test_run_01") # await and pass ids

        self.assertIsInstance(result, PainPointDeepeningOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.primary_pain_category, "Eficiência Operacional")
        self.assertEqual(result.urgency_level, "high")

        self.assertEqual(len(result.detailed_pain_points), 2)
        self.assertEqual(result.detailed_pain_points[0].pain_description, mock_detailed_pain_point1.pain_description)
        self.assertEqual(result.detailed_pain_points[1].business_impact, mock_detailed_pain_point2.business_impact)

        self.assertListEqual(result.investigative_questions, [
            "Quais são os principais gargalos que vocês identificam no fechamento mensal?",
            "Como a falta de integração de dados afeta a colaboração entre departamentos?"
        ])

        self.mock_llm_client.generate_llm_response.assert_called_once()

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_01")
        self.assertEqual(args[1], self.agent.name)
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS)


    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_llm_returns_malformed_json(self, mock_report_event: MagicMock): # Made async
        malformed_json_str = '{ "primary_pain_category": "Eficiência Operacional", "detailed_pain_points": [ { "pain_description": "Incompleto..." '
        self.mock_llm_client.generate_llm_response.return_value = malformed_json_str

        test_input = PainPointDeepeningInput(
            lead_analysis="Análise qualquer.",
            persona_profile="Persona qualquer.",
            product_service_offered="Produto qualquer.",
            company_name="Empresa Malformada"
        )

        result = await self.agent.execute(test_input, lead_id="test_lead_02", run_id="test_run_02") # await and pass ids

        self.assertIsInstance(result, PainPointDeepeningOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to parse LLM response as JSON", result.error_message) # This error is set by agent's process

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_02")
        self.assertEqual(args[2], AgentExecutionStatusEnum.FAILED) # BaseAgent should report FAILED if agent output has error_message

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_llm_returns_empty_response(self, mock_report_event: MagicMock): # Made async
        self.mock_llm_client.generate_llm_response.return_value = ""

        test_input = PainPointDeepeningInput(
            lead_analysis="Análise.",
            persona_profile="Persona.",
            product_service_offered="Produto.",
            company_name="Empresa Vazia"
        )

        result = await self.agent.execute(test_input, lead_id="test_lead_03", run_id="test_run_03") # await and pass ids

        self.assertIsInstance(result, PainPointDeepeningOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("LLM call returned no response.", result.error_message) # This error is set by agent's process

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_03")
        self.assertEqual(args[2], AgentExecutionStatusEnum.FAILED)

if __name__ == '__main__':
    unittest.main()
