import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import json

from agents.objection_handling_agent import (
    ObjectionHandlingAgent, ObjectionHandlingInput, ObjectionHandlingOutput, ObjectionResponseModel
)
from core_logic.llm_client import LLMClientBase, LLMResponse
from mcp_server.data_models import AgentExecutionStatusEnum

class TestObjectionHandlingAgent(unittest.IsolatedAsyncioTestCase): # Changed to IsolatedAsyncioTestCase

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.generate_llm_response = AsyncMock() # Mock async method
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0, "llm_calls": 0, "llm_usage": []}
        self.mock_llm_client.update_usage_stats = MagicMock()

        self.agent = ObjectionHandlingAgent(llm_client=self.mock_llm_client)

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_success_anticipates_objections(self, mock_report_event: MagicMock): # Made async
        mock_objection1 = ObjectionResponseModel(
            objection="Nosso orçamento para novas ferramentas está congelado este ano.",
            response_strategy="Empatizar, focar no ROI e apresentar modelo de subscrição flexível.",
            suggested_response="Entendo que o orçamento é uma preocupação. Muitos de nossos clientes relatam um ROI de X% em Y meses. Além disso, temos opções de planos que podem se ajustar à sua realidade atual. Poderíamos explorar um piloto de baixo custo?"
        )
        mock_objection2 = ObjectionResponseModel(
            objection="Já utilizamos a Solução Z e estamos satisfeitos.",
            response_strategy="Reconhecer a Solução Z, destacar diferenciais chave para o cenário específico do lead, e propor análise comparativa focada nos ganhos não cobertos.",
            suggested_response="A Solução Z é uma boa ferramenta. O que nossos clientes que vieram da Z mais valorizam na nossa plataforma é [Diferencial A] e [Diferencial B], que são cruciais para [Problema Específico do Lead]. Que tal uma análise rápida focada nesses pontos?"
        )

        mock_json_output_dict = {
            "anticipated_objections": [
                mock_objection1.model_dump(),
                mock_objection2.model_dump()
            ]
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)

        self.mock_llm_client.generate_llm_response.return_value = mock_json_output_str

        test_input = ObjectionHandlingInput(
            detailed_approach_plan_text="Plano focado em email e LinkedIn, propondo a Solução X.",
            persona_profile="Maria, Diretora Financeira, cética quanto a novos custos.",
            product_service_offered="Solução X de Otimização Financeira",
            company_name="Financeira Eficiente S.A."
        )

        result = await self.agent.execute(test_input, lead_id="test_lead_01", run_id="test_run_01")

        self.assertIsInstance(result, ObjectionHandlingOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(len(result.anticipated_objections), 2)

        self.assertEqual(result.anticipated_objections[0].objection, mock_objection1.objection)
        self.assertEqual(result.anticipated_objections[1].response_strategy, mock_objection2.response_strategy)

        self.mock_llm_client.generate_llm_response.assert_called_once()
        called_prompt = self.mock_llm_client.generate_llm_response.call_args[0][0]
        self.assertIn("Responda APENAS com um objeto JSON", called_prompt)
        self.assertIn("anticipated_objections", called_prompt)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_01")
        self.assertEqual(args[1], self.agent.name)
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS)
        self.assertIsInstance(args[5], ObjectionHandlingOutput)
        self.assertEqual(len(args[5].anticipated_objections), 2)


    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_llm_returns_empty_list(self, mock_report_event: MagicMock): # Made async
        mock_json_output_dict = {"anticipated_objections": []}
        mock_json_output_str = json.dumps(mock_json_output_dict)
        self.mock_llm_client.generate_llm_response.return_value = mock_json_output_str

        test_input = ObjectionHandlingInput(
            detailed_approach_plan_text="Plano simples.",
            persona_profile="Persona sem grandes preocupações.",
            product_service_offered="Produto muito desejado.",
            company_name="Empresa Sem Objeções"
        )
        result = await self.agent.execute(test_input, lead_id="test_lead_02", run_id="test_run_02")

        self.assertIsInstance(result, ObjectionHandlingOutput)
        self.assertIsNone(result.error_message) # Empty list is valid
        self.assertEqual(len(result.anticipated_objections), 0)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_02")
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS)


    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_llm_returns_malformed_json(self, mock_report_event: MagicMock): # Made async
        malformed_json_str = '{ "anticipated_objections": [ {"objection": "Orçamento"} '
        self.mock_llm_client.generate_llm_response.return_value = malformed_json_str

        test_input = ObjectionHandlingInput(
            detailed_approach_plan_text=".", persona_profile=".", product_service_offered=".", company_name="."
        )
        result = await self.agent.execute(test_input, lead_id="test_lead_03", run_id="test_run_03")

        self.assertIsInstance(result, ObjectionHandlingOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to parse LLM response as JSON", result.error_message)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_03")
        self.assertEqual(args[2], AgentExecutionStatusEnum.FAILED)

if __name__ == '__main__':
    unittest.main()
