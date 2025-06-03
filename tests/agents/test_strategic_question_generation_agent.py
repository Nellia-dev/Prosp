import unittest
from unittest.mock import MagicMock
import json

from agents.strategic_question_generation_agent import StrategicQuestionGenerationAgent, StrategicQuestionGenerationInput, StrategicQuestionGenerationOutput
from core_logic.llm_client import LLMClientBase, LLMResponse

class TestStrategicQuestionGenerationAgent(unittest.TestCase):

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0}
        self.mock_llm_client.update_usage_stats = MagicMock()

        self.agent = StrategicQuestionGenerationAgent(llm_client=self.mock_llm_client)

    def test_process_success_generates_questions(self):
        mock_json_output_dict = {
            "generated_questions": [
                "Considerando a expansão para o mercado X, como vocês planejam adaptar sua infraestrutura tecnológica atual?",
                "Quais seriam os principais indicadores de sucesso para a adoção de uma nova plataforma de gestão nos próximos 12 meses?",
                "De que forma a otimização de processos internos poderia liberar recursos para inovação em novos produtos?"
            ]
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)

        self.mock_llm_client.generate.return_value = LLMResponse(content=mock_json_output_str, provider_name="mock", model_name="mock_model", total_tokens=70, input_tokens=35, output_tokens=35)

        test_input = StrategicQuestionGenerationInput(
            lead_analysis="A Empresa Gama está crescendo rapidamente e planeja expansão internacional.",
            persona_profile="Roberto Silva, CEO, focado em crescimento sustentável e inovação.",
            deepened_pain_points="Sistemas atuais podem não escalar. Equipe sobrecarregada com tarefas manuais."
        )

        result = self.agent.execute(test_input)

        self.assertIsInstance(result, StrategicQuestionGenerationOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(len(result.generated_questions), 3)
        self.assertIn("Considerando a expansão para o mercado X", result.generated_questions[0])
        self.mock_llm_client.generate.assert_called_once()
        # call_args = self.mock_llm_client.generate.call_args[0][0]
        # self.assertIn(test_input.lead_analysis, call_args)


    def test_process_no_questions_generated_empty_list(self):
        mock_json_output_dict = {"generated_questions": []}
        mock_json_output_str = json.dumps(mock_json_output_dict)
        self.mock_llm_client.generate.return_value = LLMResponse(content=mock_json_output_str, provider_name="mock", model_name="mock_model", total_tokens=10, input_tokens=5, output_tokens=5)

        test_input = StrategicQuestionGenerationInput(
            lead_analysis="Empresa pequena, sem grandes desafios aparentes.",
            persona_profile="Dono único, satisfeito com o status quo.",
            deepened_pain_points="Nenhuma dor profunda identificada."
        )
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, StrategicQuestionGenerationOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(len(result.generated_questions), 0)

    def test_process_llm_returns_malformed_json(self):
        malformed_json_str = '{ "generated_questions": ["Pergunta 1", "Pergunta 2" ' # Malformed
        self.mock_llm_client.generate.return_value = LLMResponse(content=malformed_json_str, provider_name="mock", model_name="mock_model", total_tokens=10, input_tokens=5, output_tokens=5)

        test_input = StrategicQuestionGenerationInput(
            lead_analysis="Qualquer.", persona_profile="Qualquer.", deepened_pain_points="Qualquer."
        )
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, StrategicQuestionGenerationOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to parse LLM response as JSON", result.error_message)
        self.assertEqual(len(result.generated_questions), 0) # Should default to empty list

if __name__ == '__main__':
    unittest.main()
