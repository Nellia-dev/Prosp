import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import json

from agents.detailed_approach_plan_agent import (
    DetailedApproachPlanAgent, DetailedApproachPlanInput, DetailedApproachPlanOutput, ContactStepDetail
)
from core_logic.llm_client import LLMClientBase, LLMResponse
from mcp_server.data_models import AgentExecutionStatusEnum

class TestDetailedApproachPlanAgent(unittest.IsolatedAsyncioTestCase): # Changed to IsolatedAsyncioTestCase

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.generate_llm_response = AsyncMock() # Mock async method
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0, "llm_calls": 0, "llm_usage": []}
        self.mock_llm_client.update_usage_stats = MagicMock()

        self.agent = DetailedApproachPlanAgent(llm_client=self.mock_llm_client)

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_success_generates_detailed_plan(self, mock_report_event: MagicMock): # Made async
        mock_contact_step1 = ContactStepDetail(
            step_number=1,
            channel="Email Personalizado",
            objective="Apresentar solução para dor X e agendar call.",
            key_topics_arguments=["Como a Solução Y resolve a dor X.", "Benefício quantificável Z.", "Case de sucesso similar."],
            key_questions=["Como a dor X tem impactado suas metas trimestrais?"],
            cta="Agendar conversa de 15 minutos.",
            supporting_materials="Link para o case de sucesso A."
        )
        mock_contact_step2 = ContactStepDetail(
            step_number=2,
            channel="LinkedIn (Follow-up)",
            objective="Reforçar valor e manter lead aquecido.",
            key_topics_arguments=["Insight sobre tendência do setor.", "Relevância da Solução Y para essa tendência."],
            key_questions=[], # Optional
            cta="Compartilhar um artigo e pedir opinião.",
            supporting_materials="Link para artigo B."
        )

        mock_json_output_dict = {
            "main_objective": "Converter o lead Empresa Alfa em cliente da Solução Y.",
            "adapted_elevator_pitch": "A Solução Y ajuda empresas como a Empresa Alfa a superar o desafio X, resultando em Y% de melhoria.",
            "contact_sequence": [
                mock_contact_step1.model_dump(),
                mock_contact_step2.model_dump()
            ],
            "engagement_indicators_to_monitor": ["Abertura de email", "Clique no link do case", "Resposta ao LinkedIn msg"],
            "potential_obstacles_attention_points": ["Lead pode estar ocupado", "Concorrência com Solução Z"],
            "suggested_next_steps_if_successful": ["Realizar demonstração personalizada", "Apresentar proposta comercial"]
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)

        self.mock_llm_client.generate_llm_response.return_value = mock_json_output_str

        test_input = DetailedApproachPlanInput(
            lead_analysis="Empresa Alfa, setor de Varejo. Desafio principal: gestão de inventário.",
            persona_profile="João, Gerente de Operações, busca eficiência e redução de custos.",
            deepened_pain_points="Perda de vendas por falta de produto; Custo alto de excesso de estoque.",
            final_action_plan_text="Estratégia: Foco na dor de gestão de inventário. Canal: Email e LinkedIn.",
            product_service_offered="Solução Y de Gestão de Inventário Inteligente",
            lead_url="http://empresaalfa.example.com"
        )

        result = await self.agent.execute(test_input, lead_id="test_lead_01", run_id="test_run_01")

        self.assertIsInstance(result, DetailedApproachPlanOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.main_objective, "Converter o lead Empresa Alfa em cliente da Solução Y.")
        self.assertEqual(len(result.contact_sequence), 2)
        self.assertEqual(result.contact_sequence[0].channel, "Email Personalizado")
        self.assertEqual(result.contact_sequence[1].objective, "Reforçar valor e manter lead aquecido.")
        self.assertIn("Abertura de email", result.engagement_indicators_to_monitor)

        self.mock_llm_client.generate_llm_response.assert_called_once()
        called_prompt = self.mock_llm_client.generate_llm_response.call_args[0][0]
        self.assertIn("Responda APENAS com um objeto JSON", called_prompt)
        self.assertIn("main_objective", called_prompt)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_01")
        self.assertEqual(args[1], self.agent.name)
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS)
        self.assertIsInstance(args[5], DetailedApproachPlanOutput)
        self.assertEqual(args[5].main_objective, "Converter o lead Empresa Alfa em cliente da Solução Y.")

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_llm_returns_malformed_json(self, mock_report_event: MagicMock): # Made async
        malformed_json_str = '{ "main_objective": "Plano quebrado..." '
        self.mock_llm_client.generate_llm_response.return_value = malformed_json_str

        test_input = DetailedApproachPlanInput(
            lead_analysis=".", persona_profile=".", deepened_pain_points=".",
            final_action_plan_text=".", product_service_offered=".", lead_url="http://a.com"
        )
        result = await self.agent.execute(test_input, lead_id="test_lead_02", run_id="test_run_02")

        self.assertIsInstance(result, DetailedApproachPlanOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to parse LLM response as JSON", result.error_message)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_02")
        self.assertEqual(args[2], AgentExecutionStatusEnum.FAILED)

if __name__ == '__main__':
    unittest.main()
