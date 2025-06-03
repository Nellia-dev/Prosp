import unittest
from unittest.mock import MagicMock
import json

from agents.b2b_persona_creation_agent import B2BPersonaCreationAgent, B2BPersonaCreationInput, B2BPersonaCreationOutput
from core_logic.llm_client import LLMClientBase, LLMResponse

class TestB2BPersonaCreationAgent(unittest.TestCase):

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0}
        self.mock_llm_client.update_usage_stats = MagicMock()

        self.agent = B2BPersonaCreationAgent(llm_client=self.mock_llm_client)

    def test_process_success(self):
        mock_persona_text = (
            "Carlos Silva, Diretor de Marketing da TechSolutions Ltda. "
            "Responsável por estratégia de marketing digital e geração de leads. "
            "Busca soluções que otimizem o ROI de campanhas e melhorem a conversão. "
            "Prefere comunicação por email com dados e casos de sucesso. "
            "Nossa plataforma de Automação de Marketing pode ajudá-lo a segmentar audiências, "
            "automatizar funis e medir resultados com precisão."
        )
        # The agent's Pydantic output is B2BPersonaCreationOutput(persona_profile: str, error_message: Optional[str])
        # The LLM should be prompted to return JSON that contains this string.
        mock_json_output_dict = {
            "persona_profile": mock_persona_text
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)

        self.mock_llm_client.generate.return_value = LLMResponse(content=mock_json_output_str, provider_name="mock", model_name="mock_model", total_tokens=100, input_tokens=50, output_tokens=50)

        test_input = B2BPersonaCreationInput(
            lead_analysis="A TechSolutions Ltda é uma empresa de SaaS B2B em crescimento.",
            product_service_offered="Plataforma de Automação de Marketing",
            lead_url="http://techsolutions.example.com"
        )

        result = self.agent.execute(test_input)

        self.assertIsInstance(result, B2BPersonaCreationOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.persona_profile, mock_persona_text)
        self.mock_llm_client.generate.assert_called_once()

        called_prompt = self.mock_llm_client.generate.call_args[0][0]
        self.assertIn("Responda APENAS com um objeto JSON", called_prompt) # Check if prompt asks for JSON
        self.assertIn("persona_profile", called_prompt) # Check if the field name is in the prompt structure
        self.assertIn(test_input.product_service_offered, called_prompt)

    def test_process_llm_returns_malformed_json(self):
        malformed_json_str = '{ "persona_profile": "Perfil quebrado... ' # Malformed
        self.mock_llm_client.generate.return_value = LLMResponse(content=malformed_json_str, provider_name="mock", model_name="mock_model", total_tokens=10, input_tokens=5, output_tokens=5)

        test_input = B2BPersonaCreationInput(
            lead_analysis="Análise.", product_service_offered="Produto.", lead_url="url"
        )
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, B2BPersonaCreationOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to parse LLM response as JSON", result.error_message)
        self.assertEqual(result.persona_profile, "") # Should default to empty string

    def test_process_llm_returns_empty_response(self):
        self.mock_llm_client.generate.return_value = LLMResponse(content="", provider_name="mock", model_name="mock_model", total_tokens=2, input_tokens=1, output_tokens=1)

        test_input = B2BPersonaCreationInput(
            lead_analysis="Análise.", product_service_offered="Produto.", lead_url="url"
        )
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, B2BPersonaCreationOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("LLM response content is empty or not valid JSON", result.error_message)
        self.assertEqual(result.persona_profile, "")


if __name__ == '__main__':
    unittest.main()
