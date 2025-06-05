import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import json

from agents.b2b_personalized_message_agent import (
    B2BPersonalizedMessageAgent, B2BPersonalizedMessageInput,
    B2BPersonalizedMessageOutput, ContactDetailsInput
)
from core_logic.llm_client import LLMClientBase, LLMResponse
from mcp_server.data_models import AgentExecutionStatusEnum

class TestB2BPersonalizedMessageAgent(unittest.IsolatedAsyncioTestCase): # Changed to IsolatedAsyncioTestCase

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.generate_llm_response = AsyncMock() # Mock async method
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0, "llm_calls": 0, "llm_usage": []}
        self.mock_llm_client.update_usage_stats = MagicMock()

        self.agent = B2BPersonalizedMessageAgent(llm_client=self.mock_llm_client)

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_success_email(self, mock_report_event: MagicMock): # Made async
        mock_json_output_dict = {
            "crafted_message_channel": "Email", # Agent determines this, but LLM confirms
            "crafted_message_subject": "Otimizando Processos na ExemploCorp com IA",
            "crafted_message_body": "Olá João,\n\nPercebi que a ExemploCorp busca otimizar X. Nossa solução Y pode ajudar com Z.\n\nGostaria de conversar?\n\nAtenciosamente,\n[Seu Nome]"
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)

        self.mock_llm_client.generate_llm_response.return_value = mock_json_output_str

        test_input = B2BPersonalizedMessageInput(
            final_action_plan_text="Plano de ação: Email para João sobre otimização.",
            customized_value_propositions_text="VP1: Otimização de X com Y.",
            contact_details=ContactDetailsInput(emails_found=["joao@exemplocorp.com"]),
            product_service_offered="Solução Y de IA",
            lead_url="http://exemplocorp.com",
            company_name="ExemploCorp",
            persona_fictional_name="João Silva"
        )

        result = await self.agent.execute(test_input, lead_id="test_lead_01", run_id="test_run_01")

        self.assertIsInstance(result, B2BPersonalizedMessageOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.crafted_message_channel, "Email")
        self.assertEqual(result.crafted_message_subject, "Otimizando Processos na ExemploCorp com IA")
        self.assertIn("Olá João,", result.crafted_message_body)
        self.mock_llm_client.generate_llm_response.assert_called_once()

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_01")
        self.assertEqual(args[1], self.agent.name)
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS)
        self.assertIsInstance(args[5], B2BPersonalizedMessageOutput)
        self.assertEqual(args[5].crafted_message_subject, "Otimizando Processos na ExemploCorp com IA")

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_success_instagram_dm(self, mock_report_event: MagicMock): # Made async
        mock_json_output_dict = {
            "crafted_message_channel": "Instagram",
            "crafted_message_subject": None,
            "crafted_message_body": "Olá @JoaoExemplo! 👋 Vi que sua empresa ExemploCorp está focada em X. Nossa Solução Y pode ser um diferencial. Que tal um papo rápido?"
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)
        self.mock_llm_client.generate_llm_response.return_value = mock_json_output_str

        test_input = B2BPersonalizedMessageInput(
            final_action_plan_text="Plano de ação: DM no Instagram para @JoaoExemplo.",
            customized_value_propositions_text="VP1: X com Y.",
            contact_details=ContactDetailsInput(instagram_profiles_found=["@JoaoExemplo"]),
            product_service_offered="Solução Y",
            lead_url="http://exemplocorp.com",
            company_name="ExemploCorp",
            persona_fictional_name="João Exemplo"
        )
        result = await self.agent.execute(test_input, lead_id="test_lead_02", run_id="test_run_02")

        self.assertIsInstance(result, B2BPersonalizedMessageOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.crafted_message_channel, "Instagram")
        self.assertTrue(result.crafted_message_subject is None or result.crafted_message_subject == "")
        self.assertIn("Olá @JoaoExemplo!", result.crafted_message_body)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_02")
        self.assertEqual(args[2], AgentExecutionStatusEnum.SUCCESS)

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_no_contact_details(self, mock_report_event: MagicMock): # Made async
        test_input = B2BPersonalizedMessageInput(
            final_action_plan_text="Plano.",
            customized_value_propositions_text="VP.",
            contact_details=ContactDetailsInput(), # Empty contacts
            product_service_offered="Produto.",
            lead_url="url", company_name="Empresa", persona_fictional_name="Persona"
        )
        result = await self.agent.execute(test_input, lead_id="test_lead_03", run_id="test_run_03")

        self.assertIsInstance(result, B2BPersonalizedMessageOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Nenhum canal de contato adequado encontrado.", result.error_message)
        self.assertEqual(result.crafted_message_channel, "N/A")
        self.mock_llm_client.generate_llm_response.assert_not_called()

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_03")
        self.assertEqual(args[2], AgentExecutionStatusEnum.FAILED) # Agent's process sets error_message

    @patch('agents.base_agent.BaseAgent._report_event_to_mcp')
    async def test_process_llm_returns_malformed_json(self, mock_report_event: MagicMock): # Made async
        malformed_json_str = '{ "crafted_message_subject": "Assunto quebrado..." '
        self.mock_llm_client.generate_llm_response.return_value = malformed_json_str

        test_input = B2BPersonalizedMessageInput(
            final_action_plan_text="Plano.", customized_value_propositions_text="VP.",
            contact_details=ContactDetailsInput(emails_found=["test@example.com"]),
            product_service_offered=".", lead_url=".", company_name=".", persona_fictional_name="."
        )
        result = await self.agent.execute(test_input, lead_id="test_lead_04", run_id="test_run_04")

        self.assertIsInstance(result, B2BPersonalizedMessageOutput)
        self.assertIsNotNone(result.error_message)
        self.assertTrue("JSON parsing failed" in result.error_message or "Failed to parse LLM response as JSON" in result.error_message)

        mock_report_event.assert_called_once()
        args, _ = mock_report_event.call_args
        self.assertEqual(args[0], "test_lead_04")
        self.assertEqual(args[2], AgentExecutionStatusEnum.FAILED)

if __name__ == '__main__':
    unittest.main()
