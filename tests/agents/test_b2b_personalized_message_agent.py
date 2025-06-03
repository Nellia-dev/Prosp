import unittest
from unittest.mock import MagicMock
import json

from agents.b2b_personalized_message_agent import (
    B2BPersonalizedMessageAgent, B2BPersonalizedMessageInput,
    B2BPersonalizedMessageOutput, ContactDetailsInput
)
from core_logic.llm_client import LLMClientBase, LLMResponse

class TestB2BPersonalizedMessageAgent(unittest.TestCase):

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0}
        self.mock_llm_client.update_usage_stats = MagicMock()

        self.agent = B2BPersonalizedMessageAgent(llm_client=self.mock_llm_client)

    def test_process_success_email(self):
        mock_json_output_dict = {
            "crafted_message_channel": "Email", # Agent determines this, but LLM confirms
            "crafted_message_subject": "Otimizando Processos na ExemploCorp com IA",
            "crafted_message_body": "Olá João,\n\nPercebi que a ExemploCorp busca otimizar X. Nossa solução Y pode ajudar com Z.\n\nGostaria de conversar?\n\nAtenciosamente,\n[Seu Nome]"
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)

        self.mock_llm_client.generate.return_value = LLMResponse(content=mock_json_output_str, provider_name="mock", model_name="mock_model", total_tokens=100, input_tokens=50, output_tokens=50)

        test_input = B2BPersonalizedMessageInput(
            final_action_plan_text="Plano de ação: Email para João sobre otimização.",
            customized_value_propositions_text="VP1: Otimização de X com Y.",
            contact_details=ContactDetailsInput(emails_found=["joao@exemplocorp.com"]),
            product_service_offered="Solução Y de IA",
            lead_url="http://exemplocorp.com",
            company_name="ExemploCorp",
            persona_fictional_name="João Silva"
        )

        result = self.agent.execute(test_input)

        self.assertIsInstance(result, B2BPersonalizedMessageOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.crafted_message_channel, "Email")
        self.assertEqual(result.crafted_message_subject, "Otimizando Processos na ExemploCorp com IA")
        self.assertIn("Olá João,", result.crafted_message_body)
        self.mock_llm_client.generate.assert_called_once()

    def test_process_success_instagram_dm(self):
        mock_json_output_dict = {
            "crafted_message_channel": "Instagram",
            "crafted_message_subject": None, # or ""
            "crafted_message_body": "Olá @JoaoExemplo! 👋 Vi que sua empresa ExemploCorp está focada em X. Nossa Solução Y pode ser um diferencial. Que tal um papo rápido?"
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)
        self.mock_llm_client.generate.return_value = LLMResponse(content=mock_json_output_str, provider_name="mock", model_name="mock_model", total_tokens=80, input_tokens=40, output_tokens=40)

        test_input = B2BPersonalizedMessageInput(
            final_action_plan_text="Plano de ação: DM no Instagram para @JoaoExemplo.",
            customized_value_propositions_text="VP1: X com Y.",
            contact_details=ContactDetailsInput(instagram_profiles_found=["@JoaoExemplo"]),
            product_service_offered="Solução Y",
            lead_url="http://exemplocorp.com",
            company_name="ExemploCorp",
            persona_fictional_name="João Exemplo"
        )
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, B2BPersonalizedMessageOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.crafted_message_channel, "Instagram")
        self.assertTrue(result.crafted_message_subject is None or result.crafted_message_subject == "")
        self.assertIn("Olá @JoaoExemplo!", result.crafted_message_body)

    def test_process_no_contact_details(self):
        test_input = B2BPersonalizedMessageInput(
            final_action_plan_text="Plano.",
            customized_value_propositions_text="VP.",
            contact_details=ContactDetailsInput(), # Empty contacts
            product_service_offered="Produto.",
            lead_url="url", company_name="Empresa", persona_fictional_name="Persona"
        )
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, B2BPersonalizedMessageOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Nenhum canal de contato adequado encontrado.", result.error_message)
        self.assertEqual(result.crafted_message_channel, "N/A")
        self.mock_llm_client.generate.assert_not_called() # LLM should not be called if no contact channel

    def test_process_llm_returns_malformed_json(self):
        malformed_json_str = '{ "crafted_message_subject": "Assunto quebrado..." '
        self.mock_llm_client.generate.return_value = LLMResponse(content=malformed_json_str, provider_name="mock", model_name="mock_model", total_tokens=10, input_tokens=5, output_tokens=5)

        test_input = B2BPersonalizedMessageInput(
            final_action_plan_text="Plano.", customized_value_propositions_text="VP.",
            contact_details=ContactDetailsInput(emails_found=["test@example.com"]),
            product_service_offered=".", lead_url=".", company_name=".", persona_fictional_name="."
        )
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, B2BPersonalizedMessageOutput)
        self.assertIsNotNone(result.error_message)
        # The error message might come from parse_llm_json_response or the agent's fallback logic
        self.assertTrue("JSON parsing failed" in result.error_message or "Failed to parse LLM response as JSON" in result.error_message)
        self.assertEqual(result.crafted_message_channel, "Email") # Channel determined before LLM call
        # Body might be empty or contain raw response depending on fallback
        # For this test, we mainly care that an error was flagged.

if __name__ == '__main__':
    unittest.main()
