from typing import Optional, List
from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class PainPointDeepeningInput(BaseModel):
    lead_analysis: str
    persona_profile: str
    product_service_offered: str
    company_name: str # Added company_name for more context

class DetailedPainPoint(BaseModel):
    pain_description: str
    business_impact: str
    solution_alignment: str # How the user's product/service aligns

class PainPointDeepeningOutput(BaseModel):
    primary_pain_category: str = "Não especificado"
    detailed_pain_points: List[DetailedPainPoint] = Field(default_factory=list)
    urgency_level: str = "medium" # e.g., low, medium, high, critical
    investigative_questions: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None

class PainPointDeepeningAgent(BaseAgent[PainPointDeepeningInput, PainPointDeepeningOutput]):
    def __init__(self, llm_client: LLMClientBase):
        super().__init__(
            name="Pain Point Deepening Agent",
            description="Analyzes lead data and persona to identify and elaborate on specific pain points.",
            llm_client=llm_client
        )
        # self.name = "PainPointDeepeningAgent" # Redundant

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: PainPointDeepeningInput) -> PainPointDeepeningOutput:
        deepened_pain_points = ""
        error_message = None

        try:
            # Truncate inputs
            truncated_analysis = self._truncate_text(input_data.lead_analysis, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 4)
            truncated_persona = self._truncate_text(input_data.persona_profile, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 4)
            
            prompt_template = """
                Você é um Consultor de Vendas Estratégicas especializado em identificar e aprofundar os pontos de dor de clientes B2B.
                Seu objetivo é ajudar a equipe de vendas a entender melhor as necessidades implícitas e explícitas da persona na empresa '{company_name}'.

                ANÁLISE DO LEAD:
                {lead_analysis}

                PERFIL DA PERSONA (Tomador de Decisão na {company_name}):
                {persona_profile}

                PRODUTO/SERVIÇO QUE VOCÊ OFERECE:
                {product_service_offered}

                INSTRUÇÕES:
                Com base nas informações fornecidas:
                1.  Identifique a categoria principal dos pontos de dor.
                2.  Liste de 2 a 3 pontos de dor detalhados que a persona provavelmente enfrenta, considerando o contexto da empresa '{company_name}' e a análise do lead. Para cada um:
                    a.  Descreva a dor específica.
                    b.  Explique o impacto de negócio dessa dor (operações, receita, etc.).
                    c.  Indique como o {product_service_offered} se alinha para resolver essa dor.
                3.  Avalie o nível de urgência geral para resolver esses pontos de dor (low, medium, high, critical).
                4.  Formule de 2 a 4 perguntas investigativas abertas e específicas para aprofundar a compreensão dos problemas e suas implicações.
                
                Retorne APENAS um objeto JSON com a seguinte estrutura:
                {{
                    "primary_pain_category": "Categoria principal dos pontos de dor (string)",
                    "detailed_pain_points": [
                        {{
                            "pain_description": "Descrição específica da dor (string)",
                            "business_impact": "Como isso impacta operações/receita (string)",
                            "solution_alignment": "Como nossa solução {product_service_offered} aborda essa dor (string)"
                        }}
                    ],
                    "urgency_level": "low|medium|high|critical (string)",
                    "investigative_questions": ["Pergunta investigativa 1 (string)", "Pergunta investigativa 2 (string)"]
                }}
                Não inclua explicações adicionais fora do JSON.
            """

            formatted_prompt = prompt_template.format(
                lead_analysis=truncated_analysis,
                persona_profile=truncated_persona,
                product_service_offered=input_data.product_service_offered,
                company_name=input_data.company_name
            )

            llm_response_str = self.generate_llm_response(formatted_prompt)

            if not llm_response_str:
                return PainPointDeepeningOutput(error_message="LLM call returned no response.")

            parsed_output = self.parse_llm_json_response(llm_response_str, PainPointDeepeningOutput)
            
            # If parsing failed, parse_llm_json_response might set parsed_output.error_message
            # or return a default model with an error message.
            if parsed_output.error_message:
                 self.logger.warning(f"PainPointDeepeningAgent JSON parsing failed. Raw response: {llm_response_str[:500]}")
            # No specific regex fallback here as the structure is complex.
            # The error from parse_llm_json_response will be propagated.

            return parsed_output

        except Exception as e:
            self.logger.error(f"An unexpected error occurred in {self.name}: {e}")
            import traceback
            traceback.print_exc()
            return PainPointDeepeningOutput(error_message=f"An unexpected error occurred: {str(e)}")

if __name__ == '__main__':
    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str) -> Optional[str]:
            if "PONTOS DE DOR APROFUNDADOS E PERGUNTAS INVESTIGATIVAS" in prompt:
                return (
                    "Para a Empresa Exemplo:\n\n"
                    "Ponto de Dor 1: Otimização de Processos Manuais Identificada na Análise.\n"
                    "   - Pergunta Investigativa: Carlos, você mencionou a busca por eficiência. Poderia descrever como os processos manuais atuais impactam o tempo de resposta da sua equipe?\n"
                    "   - Pergunta Investigativa: Quais são os custos (diretos e indiretos) que você associa à manutenção desses processos manuais?\n"
                    "   - Observação: Soluções como Nossas Soluções Incríveis frequentemente ajudam a automatizar tais processos, liberando tempo da equipe para tarefas mais estratégicas.\n\n"
                    "Ponto de Dor 2: Integração de Novas Tecnologias (mencionado no perfil da persona).\n"
                    "   - Pergunta Investigativa: Ao considerar novas tecnologias, quais são suas maiores preocupações em termos de integração com os sistemas existentes na Empresa Exemplo?\n"
                    "   - Pergunta Investigativa: Como a equipe normalmente lida com a curva de aprendizado de novas ferramentas?\n"
                    "   - Observação: A facilidade de integração e o suporte robusto são aspectos que Nossas Soluções Incríveis priorizam para mitigar esses desafios."
                )
            return "Resposta padrão do mock."

    print("Running mock test for PainPointDeepeningAgent...")
    mock_llm = MockLLMClient()
    agent = PainPointDeepeningAgent(llm_client=mock_llm)

    test_lead_analysis = "A Empresa Exemplo (médio porte, setor de TI) enfrenta desafios na otimização de processos internos, muitos ainda manuais."
    test_persona_profile = (
        "Carlos Mendes, Diretor de Operações da Empresa Exemplo. Responsável por eficiência e implementação de novas tecnologias. "
        "Busca ROI claro e integração fácil. Comunicação direta."
    )
    test_product_service = "Nossas Soluções Incríveis"
    test_company_name = "Empresa Exemplo"

    input_data = PainPointDeepeningInput(
        lead_analysis=test_lead_analysis,
        persona_profile=test_persona_profile,
        product_service_offered=test_product_service,
        company_name=test_company_name
    )

    output = agent.process(input_data)

    print(f"Deepened Pain Points: {output.deepened_pain_points}")
    if output.error_message:
        print(f"Error: {output.error_message}")

    assert "Empresa Exemplo" in output.deepened_pain_points
    assert "Carlos" in output.deepened_pain_points # Check if persona context was used
    assert "Nossas Soluções Incríveis" in output.deepened_pain_points
    assert "Pergunta Investigativa:" in output.deepened_pain_points
    assert output.error_message is None
    print("Mock test completed.")
