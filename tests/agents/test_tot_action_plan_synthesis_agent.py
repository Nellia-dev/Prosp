import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import json

from agents.tot_action_plan_synthesis_agent import (
    ToTActionPlanSynthesisAgent, ToTActionPlanSynthesisInput, ToTActionPlanSynthesisOutput, ActionPlanStepModel
)
from core_logic.llm_client import LLMClientBase, LLMResponse
from mcp_server.data_models import AgentExecutionStatusEnum

class TestToTActionPlanSynthesisAgent(unittest.IsolatedAsyncioTestCase): # Changed to IsolatedAsyncioTestCase

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.generate_llm_response = AsyncMock() # Mock async method
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0, "llm_calls": 0, "llm_usage": []}
        self.mock_llm_client.update_usage_stats = MagicMock()

        self.agent = ToTActionPlanSynthesisAgent(llm_client=self.mock_llm_client)

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_success_synthesizes_plan(self, mock_report_event: MagicMock): # Made async
        mock_action_step1 = ActionPlanStepModel(
            step_number=1,
            channel="Email",
            action_description="Enviar email introdutório personalizado.",
            key_message_or_argument="Focar na dor X e como a Solução Y pode aliviar.",
            cta="Agendar uma breve chamada de 15 minutos."
        )
        mock_action_step2 = ActionPlanStepModel(
            step_number=2,
            channel="LinkedIn",
            action_description="Conectar e enviar mensagem de follow-up com insight.",
            key_message_or_argument="Compartilhar artigo relevante sobre o setor e mencionar a Solução Y.",
            cta="Perguntar opinião sobre o artigo."
        )

        mock_json_output_dict = {
            "recommended_strategy_name": "Abordagem Consultiva Refinada",
            "primary_angle_hook": "Resolver o desafio de escalabilidade com foco em ROI rápido.",
            "tone_of_voice": "Consultivo e orientado a resultados",
            "action_sequence": [
                mock_action_step1.model_dump(),
                mock_action_step2.model_dump()
            ],
            "key_talking_points": ["ROI em 6 meses", "Facilidade de integração", "Suporte dedicado"],
            "main_opening_question": "Considerando seus planos de expansão, como a atual infraestrutura suportará o aumento de demanda de forma eficiente?",
            "success_metrics": ["Taxa de resposta ao email > 20%", "Agendamento de 5 calls/semana"],
            "contingency_plan": "Se não houver resposta, tentar contato via parceiro em comum após 7 dias."
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)

        self.mock_llm_client.generate_llm_response.return_value = mock_json_output_str

        test_input = ToTActionPlanSynthesisInput(
            evaluated_strategies_text="Avaliação Estratégia 1 (Confiança Alta): ... Melhorias: ...\nAvaliação Estratégia 2 (Confiança Média): ...",
            proposed_strategies_text="Estratégia Original 1: ...\nEstratégia Original 2: ...",
            current_lead_summary="Empresa ABC, buscando escalar. CEO focado em ROI."
        )

        result = await self.agent.execute(test_input, lead_id="test_lead_01", run_id="test_run_01")

        self.assertIsInstance(result, ToTActionPlanSynthesisOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.recommended_strategy_name, "Abordagem Consultiva Refinada")
        self.assertEqual(result.primary_angle_hook, "Resolver o desafio de escalabilidade com foco em ROI rápido.")
        self.assertEqual(len(result.action_sequence), 2)
        self.assertEqual(result.action_sequence[0].channel, "Email")
        self.assertListEqual(result.success_metrics, ["Taxa de resposta ao email > 20%", "Agendamento de 5 calls/semana"])

        self.mock_llm_client.generate_llm_response.assert_called_once()
        called_prompt = self.mock_llm_client.generate_llm_response.call_args[0][0]
        self.assertIn("Responda APENAS com um objeto JSON", called_prompt)
        self.assertIn("recommended_strategy_name", called_prompt)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_01")
        self.assertEqual(args[1], self.agent.name)
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS)
        self.assertIsInstance(args[5], ToTActionPlanSynthesisOutput)
        self.assertEqual(args[5].recommended_strategy_name, "Abordagem Consultiva Refinada")


    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_llm_returns_malformed_json(self, mock_report_event: MagicMock): # Made async
        malformed_json_str = '{ "recommended_strategy_name": "Plano Quebrado", "action_sequence": [ {"step_number": 1} '
        self.mock_llm_client.generate_llm_response.return_value = malformed_json_str

        test_input = ToTActionPlanSynthesisInput(
            evaluated_strategies_text="Qualquer", proposed_strategies_text="Qualquer", current_lead_summary="Qualquer"
        )
        result = await self.agent.execute(test_input, lead_id="test_lead_02", run_id="test_run_02")

        self.assertIsInstance(result, ToTActionPlanSynthesisOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to parse LLM response as JSON", result.error_message)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_02")
        self.assertEqual(args[2], AgentExecutionStatusEnum.FAILED)

if __name__ == '__main__':
    unittest.main()
