import unittest
from unittest.mock import MagicMock
import json

from agents.pain_point_deepening_agent import PainPointDeepeningAgent, PainPointDeepeningInput, PainPointDeepeningOutput, DetailedPainPoint
from core_logic.llm_client import LLMClientBase, LLMResponse

class TestPainPointDeepeningAgent(unittest.TestCase):

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0}
        self.mock_llm_client.update_usage_stats = MagicMock()

        self.agent = PainPointDeepeningAgent(llm_client=self.mock_llm_client)

    def test_process_success(self):
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

        self.mock_llm_client.generate.return_value = LLMResponse(content=mock_json_output_str, provider_name="mock", model_name="mock_model", total_tokens=50, input_tokens=25, output_tokens=25)

        test_input = PainPointDeepeningInput(
            lead_analysis="Empresa X demonstra crescimento, mas mencionou desafios com sistemas legados.",
            persona_profile="Carlos, Diretor de TI, focado em modernização e eficiência.",
            product_service_offered="Solução de Business Intelligence",
            company_name="Empresa X"
        )

        result = self.agent.execute(test_input)

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

        self.mock_llm_client.generate.assert_called_once()
        # More detailed prompt content check can be added here
        # call_args = self.mock_llm_client.generate.call_args
        # called_prompt = call_args[0][0] # First positional argument
        # self.assertIn("Retorne APENAS um objeto JSON", called_prompt)
        # self.assertIn(test_input.company_name, called_prompt)


    def test_process_llm_returns_malformed_json(self):
        malformed_json_str = '{ "primary_pain_category": "Eficiência Operacional", "detailed_pain_points": [ { "pain_description": "Incompleto..." '
        self.mock_llm_client.generate.return_value = LLMResponse(content=malformed_json_str, provider_name="mock", model_name="mock_model", total_tokens=10, input_tokens=5, output_tokens=5)

        test_input = PainPointDeepeningInput(
            lead_analysis="Análise qualquer.",
            persona_profile="Persona qualquer.",
            product_service_offered="Produto qualquer.",
            company_name="Empresa Malformada"
        )

        result = self.agent.execute(test_input)

        self.assertIsInstance(result, PainPointDeepeningOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to parse LLM response as JSON", result.error_message)
        # Check that default values are present for main fields
        self.assertEqual(result.primary_pain_category, "Não especificado")
        self.assertEqual(len(result.detailed_pain_points), 0)
        self.assertEqual(result.urgency_level, "medium")

    def test_process_llm_returns_empty_response(self):
        self.mock_llm_client.generate.return_value = LLMResponse(content="", provider_name="mock", model_name="mock_model", total_tokens=2, input_tokens=1, output_tokens=1)

        test_input = PainPointDeepeningInput(
            lead_analysis="Análise.",
            persona_profile="Persona.",
            product_service_offered="Produto.",
            company_name="Empresa Vazia"
        )

        result = self.agent.execute(test_input)

        self.assertIsInstance(result, PainPointDeepeningOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("LLM call returned no response.", result.error_message)

if __name__ == '__main__':
    unittest.main()
