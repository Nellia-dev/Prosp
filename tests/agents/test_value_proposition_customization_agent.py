import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import json

from agents.value_proposition_customization_agent import (
    ValuePropositionCustomizationAgent, ValuePropositionCustomizationInput,
    ValuePropositionCustomizationOutput, CustomValuePropModel
)
from core_logic.llm_client import LLMClientBase, LLMResponse
from mcp_server.data_models import AgentExecutionStatusEnum

class TestValuePropositionCustomizationAgent(unittest.IsolatedAsyncioTestCase): # Changed to IsolatedAsyncioTestCase

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.generate_llm_response = AsyncMock() # Mock async method
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0, "llm_calls": 0, "llm_usage": []}
        self.mock_llm_client.update_usage_stats = MagicMock()

        self.agent = ValuePropositionCustomizationAgent(llm_client=self.mock_llm_client)

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_success_customizes_propositions(self, mock_report_event: MagicMock): # Made async
        mock_vp1 = CustomValuePropModel(
            title="Otimização de Processos para Crescimento Acelerado na TechCorp",
            connection_to_pain_or_trigger="Identificamos que a TechCorp está expandindo rapidamente (gatilho) e enfrenta desafios em escalar seus processos manuais (dor).",
            key_benefit="Nossa plataforma X automatiza até 70% dos fluxos de trabalho de back-office, permitindo que sua equipe foque em inovação e atendimento ao cliente durante a expansão.",
            differentiation_factor="Integração nativa com seus sistemas legados Y e Z, minimizando a disrupção e acelerando o time-to-value.",
            call_to_value="Vamos transformar os desafios de crescimento da TechCorp em uma vantagem competitiva?"
        )
        mock_vp2 = CustomValuePropModel(
            title="Capacite o CFO da TechCorp com Visibilidade Financeira em Tempo Real",
            connection_to_pain_or_trigger="Para o CFO (persona) da TechCorp, que busca ROI claro e previsibilidade, a falta de dados consolidados (dor) é um obstáculo.",
            key_benefit="A plataforma X oferece dashboards financeiros unificados e relatórios personalizáveis em tempo real, melhorando a tomada de decisão e o planejamento estratégico.",
            differentiation_factor="Nossa análise preditiva de fluxo de caixa é um diferencial que outras ferramentas não possuem, antecipando necessidades futuras.",
            call_to_value="Pronto para dar ao seu time financeiro o poder da informação instantânea e precisa?"
        )

        mock_json_output_dict = {
            "custom_propositions": [
                mock_vp1.model_dump(),
                mock_vp2.model_dump()
            ]
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)

        self.mock_llm_client.generate_llm_response.return_value = mock_json_output_str

        test_input = ValuePropositionCustomizationInput(
            lead_analysis="TechCorp, SaaS, expansão rápida. Desafios: processos manuais, sistemas legados.",
            persona_profile="CFO, busca ROI e previsibilidade. Preocupado com falta de dados consolidados.",
            deepened_pain_points="Processos manuais não escalam; falta de visibilidade financeira.",
            buying_triggers_report="Anúncio de expansão; Contratação de novo CFO.",
            product_service_offered="Plataforma X de Automação e BI Financeiro",
            company_name="TechCorp"
        )

        result = await self.agent.execute(test_input, lead_id="test_lead_01", run_id="test_run_01")

        self.assertIsInstance(result, ValuePropositionCustomizationOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(len(result.custom_propositions), 2)

        self.assertEqual(result.custom_propositions[0].title, mock_vp1.title)
        self.assertEqual(result.custom_propositions[1].key_benefit, mock_vp2.key_benefit)

        self.mock_llm_client.generate_llm_response.assert_called_once()
        called_prompt = self.mock_llm_client.generate_llm_response.call_args[0][0]
        self.assertIn("Responda APENAS com um objeto JSON", called_prompt)
        self.assertIn("custom_propositions", called_prompt)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_01")
        self.assertEqual(args[1], self.agent.name)
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS)
        self.assertIsInstance(args[5], ValuePropositionCustomizationOutput)
        self.assertEqual(len(args[5].custom_propositions), 2)

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_llm_returns_malformed_json(self, mock_report_event: MagicMock): # Made async
        malformed_json_str = '{ "custom_propositions": [ {"title": "VP Quebrada"} '
        self.mock_llm_client.generate_llm_response.return_value = malformed_json_str

        test_input = ValuePropositionCustomizationInput(
            lead_analysis=".", persona_profile=".", deepened_pain_points=".",
            buying_triggers_report=".", product_service_offered=".", company_name="."
        )
        result = await self.agent.execute(test_input, lead_id="test_lead_02", run_id="test_run_02")

        self.assertIsInstance(result, ValuePropositionCustomizationOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to parse LLM response as JSON", result.error_message)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_02")
        self.assertEqual(args[2], AgentExecutionStatusEnum.FAILED)

if __name__ == '__main__':
    unittest.main()
