import unittest
from unittest.mock import MagicMock
import json

from agents.internal_briefing_summary_agent import (
    InternalBriefingSummaryAgent, InternalBriefingSummaryInput,
    InternalBriefingSummaryOutput, InternalBriefingSection
)
from core_logic.llm_client import LLMClientBase, LLMResponse

class TestInternalBriefingSummaryAgent(unittest.TestCase):

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0}
        self.mock_llm_client.update_usage_stats = MagicMock()

        self.agent = InternalBriefingSummaryAgent(llm_client=self.mock_llm_client)

    def test_process_success_generates_briefing(self):
        mock_json_output_dict = {
            "executive_summary": "Lead TechGlobal: Alto potencial para Solução Z. Foco em otimizar P&D.",
            "lead_overview": {
                "title": "Visão Geral do Lead",
                "content": "TechGlobal (techglobal.com) - Inovação em IA. Oferecendo Solução Z."
            },
            "persona_profile_summary": {
                "title": "Perfil da Persona",
                "content": "Dr. Ana K., Diretora de P&D. Busca eficiência e tecnologias disruptivas."
            },
            "pain_points_and_needs": {
                "title": "Dores e Necessidades Principais",
                "content": "Ciclos longos de P&D. Solução Z pode acelerar X e Y."
            },
            "buying_triggers_opportunity": {
                "title": "Gatilhos de Compra e Oportunidade",
                "content": "Nova verba para P&D anunciada. Mercado competitivo exige inovação rápida."
            },
            "lead_qualification_summary": {
                "title": "Qualificação do Lead",
                "content": "Alto Potencial. Alinhamento estratégico e necessidade clara."
            },
            "approach_strategy_summary": {
                "title": "Estratégia de Abordagem Chave",
                "content": "Abordagem consultiva, foco no impacto da Solução Z em P&D. Email > Call."
            },
            "custom_value_proposition_summary": {
                "title": "Proposta de Valor Principal (Customizada)",
                "content": "Acelere o P&D da TechGlobal com a Solução Z, reduzindo o time-to-market em até N%."
            },
            "potential_objections_summary": {
                "title": "Objeções Potenciais e Respostas Chave",
                "content": "Custo? Focar no ROI e TCO. Integração? Demonstrar conectores."
            },
            "recommended_next_step": "Enviar email personalizado para Dr. Ana K. com case de P&D."
        }
        mock_json_output_str = json.dumps(mock_json_output_dict)

        self.mock_llm_client.generate.return_value = LLMResponse(content=mock_json_output_str, provider_name="mock", model_name="mock_model", total_tokens=300, input_tokens=150, output_tokens=150)

        test_input_data = {
            "company_name": "TechGlobal", "lead_url": "techglobal.com",
            "product_service_offered_by_us": "Solução Z",
            "lead_analysis_summary": {"company_sector": "IA", "main_services": ["P&D em IA"]},
            # ... (other summarized data points as expected by the agent's prompt formatting)
        }
        test_input = InternalBriefingSummaryInput(all_lead_data=test_input_data)

        result = self.agent.execute(test_input)

        self.assertIsInstance(result, InternalBriefingSummaryOutput)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.executive_summary, "Lead TechGlobal: Alto potencial para Solução Z. Foco em otimizar P&D.")
        self.assertEqual(result.lead_overview.title, "Visão Geral do Lead")
        self.assertIn("Dr. Ana K.", result.persona_profile_summary.content)
        self.assertEqual(result.recommended_next_step, "Enviar email personalizado para Dr. Ana K. com case de P&D.")

        self.mock_llm_client.generate.assert_called_once()
        called_prompt = self.mock_llm_client.generate.call_args[0][0]
        self.assertIn("Responda APENAS com um objeto JSON", called_prompt)
        self.assertIn("executive_summary", called_prompt) # Check a key field from the JSON structure

    def test_process_llm_returns_malformed_json(self):
        malformed_json_str = '{ "executive_summary": "Briefing quebrado..." '
        self.mock_llm_client.generate.return_value = LLMResponse(content=malformed_json_str, provider_name="mock", model_name="mock_model", total_tokens=10, input_tokens=5, output_tokens=5)

        test_input = InternalBriefingSummaryInput(all_lead_data={"company_name": "Test"})
        result = self.agent.execute(test_input)

        self.assertIsInstance(result, InternalBriefingSummaryOutput)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to parse LLM response as JSON", result.error_message)
        self.assertEqual(result.executive_summary, "Não especificado") # Default value

if __name__ == '__main__':
    unittest.main()
