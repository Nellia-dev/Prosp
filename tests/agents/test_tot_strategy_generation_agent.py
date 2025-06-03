import unittest
from unittest.mock import MagicMock
import json

from agents.tot_strategy_generation_agent import ToTStrategyGenerationAgent, ToTStrategyGenerationInput, ToTStrategyGenerationOutput, ToTStrategyOptionModel
from core_logic.llm_client import LLMClientBase, LLMResponse

class TestToTStrategyGenerationAgent(unittest.TestCase):

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0}
        self.mock_llm_client.update_usage_stats = MagicMock()

        self.agent = ToTStrategyGenerationAgent(llm_client=self.mock_llm_client)

    def test_process_success_generates_strategies(self):
        mock_strategy1 = ToTStrategyOptionModel(
            strategy_name="Abordagem Consultiva Direta",
            angle_or_hook="Focar nos desafios de escalabilidade mencionados.",
            tone_of_voice="Consultivo e especialista",
            primary_channels=["Email", "LinkedIn"],
            key_points_or_arguments=["Como nossa solução X resolve o problema Y.", "Case de sucesso similar."],
            opening_question="Percebi que mencionaram desafios com escalabilidade; como isso impacta seus planos de crescimento para 2024?"
        )
        mock_strategy2 = ToTStrategyOptionModel(
            strategy_name="Networking via Evento do Setor",
            angle_or_hook="Conectar em um nível mais pessoal e contextual.",
            tone_of_voice="Cordial e informativo",
            primary_channels=["Evento Online", "LinkedIn (follow-up)"],
            key_points_or_arguments=["Benefício Z da nossa plataforma.", "Alinhamento com tendências do setor discutidas no evento."],
            opening_question="Ótima apresentação no evento X! Como você vê a aplicação da tendência Y na prática da Empresa Teste?"
        )

        mock_json_output_dict = {
            "proposed_strategies": [
                mock_strategy1.model_dump(),
                mock_strategy2.model_dump()
            ]
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)

        self.mock_llm_client.generate.return_value = LLMResponse(content=mock_json_output_str, provider_name="mock", model_name="mock_model", total_tokens=150, input_tokens=75, output_tokens=75)

        test_input = ToTStrategyGenerationInput(
            current_lead_summary="Empresa Teste, setor de SaaS, buscando escalar operações. Persona: Diretor de Ops.",
            product_service_offered="Plataforma de Otimização de Processos"
        )

        result = self.agent.execute(test_input)

        self.assertIsInstance(result, ToTStrategyGenerationOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(len(result.proposed_strategies), 2)

        self.assertEqual(result.proposed_strategies[0].strategy_name, mock_strategy1.strategy_name)
        self.assertEqual(result.proposed_strategies[0].angle_or_hook, mock_strategy1.angle_or_hook)
        self.assertListEqual(result.proposed_strategies[1].primary_channels, mock_strategy2.primary_channels)

        self.mock_llm_client.generate.assert_called_once()
        called_prompt = self.mock_llm_client.generate.call_args[0][0]
        self.assertIn("Responda APENAS com um objeto JSON", called_prompt)
        self.assertIn("proposed_strategies", called_prompt)


    def test_process_llm_returns_empty_list(self):
        mock_json_output_dict = {"proposed_strategies": []}
        mock_json_output_str = json.dumps(mock_json_output_dict)
        self.mock_llm_client.generate.return_value = LLMResponse(content=mock_json_output_str, provider_name="mock", model_name="mock_model", total_tokens=10, input_tokens=5, output_tokens=5)

        test_input = ToTStrategyGenerationInput(
            current_lead_summary="Lead com poucas informações.",
            product_service_offered="Produto genérico"
        )
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, ToTStrategyGenerationOutput)
        self.assertIsNone(result.error_message) # Empty list is valid JSON
        self.assertEqual(len(result.proposed_strategies), 0)

    def test_process_llm_returns_malformed_json(self):
        malformed_json_str = '{ "proposed_strategies": [ {"strategy_name": "Quebrado"} '
        self.mock_llm_client.generate.return_value = LLMResponse(content=malformed_json_str, provider_name="mock", model_name="mock_model", total_tokens=10, input_tokens=5, output_tokens=5)

        test_input = ToTStrategyGenerationInput(
            current_lead_summary="Qualquer.", product_service_offered="Qualquer."
        )
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, ToTStrategyGenerationOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to parse LLM response as JSON", result.error_message)
        self.assertEqual(len(result.proposed_strategies), 0)

if __name__ == '__main__':
    unittest.main()
