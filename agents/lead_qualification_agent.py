from typing import Optional
from pydantic import BaseModel

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class LeadQualificationInput(BaseModel):
    lead_analysis: str
    persona_profile: str
    deepened_pain_points: str # Contains investigative questions and context
    product_service_offered: str

class LeadQualificationOutput(BaseModel):
    qualification_tier: str = "Não Qualificado" # e.g., "Alto Potencial", "Potencial Médio", "Baixo Potencial", "Não Qualificado"
    justification: str = "Não foi possível determinar a qualificação."
    confidence_score: Optional[float] = None # Optional: LLM could provide a confidence score
    error_message: Optional[str] = None

class LeadQualificationAgent(BaseAgent[LeadQualificationInput, LeadQualificationOutput]):
    def __init__(self, llm_client: LLMClientBase):
        super().__init__(
            name="Lead Qualification Agent",
            description="Qualifies leads based on strategic information, classifying them into potential tiers.",
            llm_client=llm_client
        )
        # self.name = "LeadQualificationAgent" # This would be redundant if BaseAgent sets it.

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: LeadQualificationInput) -> LeadQualificationOutput:
        qualification_assessment = ""
        error_message = None

        try:
            # Truncate inputs to avoid exceeding LLM context window
            truncated_analysis = self._truncate_text(input_data.lead_analysis, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 4)
            truncated_persona = self._truncate_text(input_data.persona_profile, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 4)
            truncated_pain_points = self._truncate_text(input_data.deepened_pain_points, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 4)

            prompt_template = """
                Você é um Diretor de Vendas experiente, especializado em qualificar leads B2B com base em informações estratégicas.
                Seu objetivo é classificar o potencial do lead e fornecer uma justificativa clara.

                ANÁLISE DO LEAD:
                {lead_analysis}

                PERFIL DA PERSONA (Tomador de Decisão):
                {persona_profile}

                PONTOS DE DOR APROFUNDADOS E PERGUNTAS INVESTIGATIVAS:
                {deepened_pain_points}

                PRODUTO/SERVIÇO OFERECIDO:
                {product_service_offered}

                INSTRUÇÕES:
                Com base em todas as informações fornecidas:
                1.  Avalie o alinhamento entre os pontos de dor identificados e o {product_service_offered}.
                2.  Considere a adequação do perfil da persona (cargo, responsabilidades, motivações) como um cliente ideal.
                3.  Analise a urgência ou criticidade implícita nos pontos de dor e nas perguntas investigativas.
                4.  Classifique o lead em uma das seguintes categorias: "Alto Potencial", "Potencial Médio", "Baixo Potencial", "Não Qualificado".
                5.  Forneça uma justificativa concisa para sua classificação, destacando os principais fatores.
                6.  Opcionalmente, forneça uma pontuação de confiança (0.0 a 1.0) para sua avaliação.

                Responda APENAS com um objeto JSON com a seguinte estrutura:
                {{
                    "qualification_tier": "Alto Potencial | Potencial Médio | Baixo Potencial | Não Qualificado (string)",
                    "justification": "Justificativa detalhada para a classificação (string, máximo 200 palavras)",
                    "confidence_score": "(Opcional) Pontuação de confiança da avaliação (float, 0.0 a 1.0)"
                }}
                Não inclua nenhuma explicação ou texto adicional fora do objeto JSON.
            """

            formatted_prompt = prompt_template.format(
                lead_analysis=truncated_analysis,
                persona_profile=truncated_persona,
                deepened_pain_points=truncated_pain_points,
                product_service_offered=input_data.product_service_offered
            )

            llm_response_str = self.generate_llm_response(formatted_prompt)

            if not llm_response_str:
                return LeadQualificationOutput(error_message="LLM call returned no response.")

            parsed_output = self.parse_llm_json_response(llm_response_str, LeadQualificationOutput)
            
            if parsed_output.error_message:
                self.logger.warning(f"LeadQualificationAgent JSON parsing failed. Raw response: {llm_response_str[:500]}")
            # No specific regex fallback here, error from parse_llm_json_response will be propagated.
            
            return parsed_output

        except Exception as e:
            self.logger.error(f"An unexpected error occurred in {self.name}: {e}")
            import traceback
            traceback.print_exc()
            return LeadQualificationOutput(error_message=f"An unexpected error occurred: {str(e)}")

if __name__ == '__main__':
    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str) -> Optional[str]:
            if "AVALIAÇÃO DE QUALIFICAÇÃO DO LEAD:" in prompt:
                return (
                    "CLASSIFICAÇÃO: Alto Potencial\n"
                    "JUSTIFICATIVA: A análise do lead (Empresa Exemplo, médio porte, TI) e o perfil da persona (Carlos Mendes, Diretor de Operações) indicam forte alinhamento com Nossas Soluções Incríveis. Os pontos de dor aprofundados sobre otimização de processos manuais e integração de tecnologia são diretamente abordados pela nossa oferta. A urgência é sugerida pela busca da persona por ROI claro e eficiência."
                )
            return "Resposta padrão do mock."

    print("Running mock test for LeadQualificationAgent...")
    mock_llm = MockLLMClient()
    agent = LeadQualificationAgent(llm_client=mock_llm)

    test_lead_analysis = "A Empresa Exemplo (médio porte, setor de TI) enfrenta desafios na otimização de processos internos."
    test_persona_profile = "Carlos Mendes, Diretor de Operações, busca ROI claro e eficiência."
    test_deepened_pain_points = (
        "Ponto de Dor 1: Otimização de Processos Manuais. Perguntas sobre impacto e custos.\n"
        "Ponto de Dor 2: Integração de Novas Tecnologias. Perguntas sobre preocupações e aprendizado."
    )
    test_product_service = "Nossas Soluções Incríveis"

    input_data = LeadQualificationInput(
        lead_analysis=test_lead_analysis,
        persona_profile=test_persona_profile,
        deepened_pain_points=test_deepened_pain_points,
        product_service_offered=test_product_service
    )

    output = agent.process(input_data)

    print(f"Qualification Assessment: {output.qualification_assessment}")
    if output.error_message:
        print(f"Error: {output.error_message}")

    assert "CLASSIFICAÇÃO: Alto Potencial" in output.qualification_assessment
    assert "JUSTIFICATIVA:" in output.qualification_assessment
    assert "Nossas Soluções Incríveis" in output.qualification_assessment # Check product mentioned in prompt was used
    assert output.error_message is None
    print("Mock test completed.")
