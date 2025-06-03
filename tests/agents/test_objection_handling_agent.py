import unittest
from unittest.mock import MagicMock
import json

from agents.objection_handling_agent import (
    ObjectionHandlingAgent, ObjectionHandlingInput, ObjectionHandlingOutput, ObjectionResponseModel
)
from core_logic.llm_client import LLMClientBase, LLMResponse

class TestObjectionHandlingAgent(unittest.TestCase):

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0}
        self.mock_llm_client.update_usage_stats = MagicMock()

        self.agent = ObjectionHandlingAgent(llm_client=self.mock_llm_client)

    def test_process_success_anticipates_objections(self):
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

        self.mock_llm_client.generate.return_value = LLMResponse(content=mock_json_output_str, provider_name="mock", model_name="mock_model", total_tokens=200, input_tokens=100, output_tokens=100)

        test_input = ObjectionHandlingInput(
            detailed_approach_plan_text="Plano focado em email e LinkedIn, propondo a Solução X.",
            persona_profile="Maria, Diretora Financeira, cética quanto a novos custos.",
            product_service_offered="Solução X de Otimização Financeira",
            company_name="Financeira Eficiente S.A."
        )

        result = self.agent.execute(test_input)

        self.assertIsInstance(result, ObjectionHandlingOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(len(result.anticipated_objections), 2)

        self.assertEqual(result.anticipated_objections[0].objection, mock_objection1.objection)
        self.assertEqual(result.anticipated_objections[1].response_strategy, mock_objection2.response_strategy)

        self.mock_llm_client.generate.assert_called_once()
        called_prompt = self.mock_llm_client.generate.call_args[0][0]
        self.assertIn("Responda APENAS com um objeto JSON", called_prompt)
        self.assertIn("anticipated_objections", called_prompt)

    def test_process_llm_returns_empty_list(self):
        mock_json_output_dict = {"anticipated_objections": []}
        mock_json_output_str = json.dumps(mock_json_output_dict)
        self.mock_llm_client.generate.return_value = LLMResponse(content=mock_json_output_str, provider_name="mock", model_name="mock_model", total_tokens=10, input_tokens=5, output_tokens=5)

        test_input = ObjectionHandlingInput(
            detailed_approach_plan_text="Plano simples.",
            persona_profile="Persona sem grandes preocupações.",
            product_service_offered="Produto muito desejado.",
            company_name="Empresa Sem Objeções"
        )
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, ObjectionHandlingOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(len(result.anticipated_objections), 0)

    def test_process_llm_returns_malformed_json(self):
        malformed_json_str = '{ "anticipated_objections": [ {"objection": "Orçamento"} '
        self.mock_llm_client.generate.return_value = LLMResponse(content=malformed_json_str, provider_name="mock", model_name="mock_model", total_tokens=10, input_tokens=5, output_tokens=5)

        test_input = ObjectionHandlingInput(
            detailed_approach_plan_text=".", persona_profile=".", product_service_offered=".", company_name="."
        )
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, ObjectionHandlingOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to parse LLM response as JSON", result.error_message)
        self.assertEqual(len(result.anticipated_objections), 0)

if __name__ == '__main__':
    unittest.main()
