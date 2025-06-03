import unittest
from unittest.mock import MagicMock
import json

from agents.tot_strategy_evaluation_agent import ToTStrategyEvaluationAgent, ToTStrategyEvaluationInput, ToTStrategyEvaluationOutput, EvaluatedStrategyModel
from core_logic.llm_client import LLMClientBase, LLMResponse

class TestToTStrategyEvaluationAgent(unittest.TestCase):

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0}
        self.mock_llm_client.update_usage_stats = MagicMock()

        self.agent = ToTStrategyEvaluationAgent(llm_client=self.mock_llm_client)

    def test_process_success_evaluates_strategies(self):
        mock_eval_strategy1 = EvaluatedStrategyModel(
            strategy_name="Abordagem Consultiva Direta",
            suitability_assessment="Alta adequação ao perfil do lead que busca expertise.",
            strengths=["Constrói confiança", "Permite aprofundar dores"],
            weaknesses_or_risks=["Pode ser demorada", "Requer alta habilidade consultiva"],
            suggested_improvements=["Incluir um case de sucesso conciso no primeiro contato."],
            confidence_score="Alta",
            confidence_justification="Alinhamento forte com as necessidades percebidas."
        )
        mock_eval_strategy2 = EvaluatedStrategyModel(
            strategy_name="Networking via Evento do Setor",
            suitability_assessment="Média adequação; depende da participação do lead no evento.",
            strengths=["Contato mais natural", "Possibilidade de encontrar outros contatos"],
            weaknesses_or_risks=["Baixa previsibilidade de encontro", "Pode ser superficial"],
            suggested_improvements=["Pesquisar antecipadamente se o lead confirmou presença."],
            confidence_score="Média",
            confidence_justification="Potencial existe, mas com incertezas."
        )

        mock_json_output_dict = {
            "evaluated_strategies": [
                mock_eval_strategy1.model_dump(),
                mock_eval_strategy2.model_dump()
            ]
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)

        self.mock_llm_client.generate.return_value = LLMResponse(content=mock_json_output_str, provider_name="mock", model_name="mock_model", total_tokens=200, input_tokens=100, output_tokens=100)

        test_input = ToTStrategyEvaluationInput(
            proposed_strategies_text="Estratégia 1: Abordagem Consultiva Direta...\nEstratégia 2: Networking via Evento do Setor...",
            current_lead_summary="Empresa Teste, Diretor de Ops focado em eficiência."
        )

        result = self.agent.execute(test_input)

        self.assertIsInstance(result, ToTStrategyEvaluationOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(len(result.evaluated_strategies), 2)

        self.assertEqual(result.evaluated_strategies[0].strategy_name, mock_eval_strategy1.strategy_name)
        self.assertEqual(result.evaluated_strategies[0].suitability_assessment, mock_eval_strategy1.suitability_assessment)
        self.assertListEqual(result.evaluated_strategies[1].strengths, mock_eval_strategy2.strengths)

        self.mock_llm_client.generate.assert_called_once()
        called_prompt = self.mock_llm_client.generate.call_args[0][0]
        self.assertIn("Responda APENAS com um objeto JSON", called_prompt)
        self.assertIn("evaluated_strategies", called_prompt)


    def test_process_llm_returns_empty_list(self):
        mock_json_output_dict = {"evaluated_strategies": []}
        mock_json_output_str = json.dumps(mock_json_output_dict)
        self.mock_llm_client.generate.return_value = LLMResponse(content=mock_json_output_str, provider_name="mock", model_name="mock_model", total_tokens=10, input_tokens=5, output_tokens=5)

        test_input = ToTStrategyEvaluationInput(
            proposed_strategies_text="Nenhuma estratégia proposta.",
            current_lead_summary="Lead com poucas informações."
        )
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, ToTStrategyEvaluationOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(len(result.evaluated_strategies), 0)

    def test_process_llm_returns_malformed_json(self):
        malformed_json_str = '{ "evaluated_strategies": [ {"strategy_name": "Quebrado"} '
        self.mock_llm_client.generate.return_value = LLMResponse(content=malformed_json_str, provider_name="mock", model_name="mock_model", total_tokens=10, input_tokens=5, output_tokens=5)

        test_input = ToTStrategyEvaluationInput(
            proposed_strategies_text="Qualquer.", current_lead_summary="Qualquer."
        )
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, ToTStrategyEvaluationOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to parse LLM response as JSON", result.error_message)
        self.assertEqual(len(result.evaluated_strategies), 0)

if __name__ == '__main__':
    unittest.main()
