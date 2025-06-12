from typing import Optional, List
from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class StrategicQuestionGenerationInput(BaseModel):
    lead_analysis: str
    persona_profile: str
    deepened_pain_points: str # This contains investigative questions already

class StrategicQuestionGenerationOutput(BaseModel):
    generated_questions: List[str] = Field(default_factory=list) # 2-3 additional open-ended strategic questions
    error_message: Optional[str] = None

class StrategicQuestionGenerationAgent(BaseAgent[StrategicQuestionGenerationInput, StrategicQuestionGenerationOutput]):
    def __init__(self, llm_client: LLMClientBase):
        super().__init__(
            name="Strategic Question Generation Agent",
            description="Generates additional strategic, open-ended questions based on lead analysis and pain points.",
            llm_client=llm_client
        )
        # self.name = "StrategicQuestionGenerationAgent" # Redundant

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: StrategicQuestionGenerationInput) -> StrategicQuestionGenerationOutput:
        strategic_questions = ""
        error_message = None

        try:
            # Truncate inputs
            truncated_analysis = self._truncate_text(input_data.lead_analysis, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 4)
            truncated_persona = self._truncate_text(input_data.persona_profile, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 4)
            truncated_pain_points = self._truncate_text(input_data.deepened_pain_points, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 3) # Give more space to this

            prompt_template = """
                Você é um Coach de Vendas Estratégicas, mestre em formular perguntas que abrem conversas e revelam necessidades mais profundas.
                Seu objetivo é gerar 2-3 perguntas estratégicas adicionais, abertas, que vão além das perguntas investigativas já formuladas nos "Pontos de Dor Aprofundados".
                Essas novas perguntas devem incentivar a persona a pensar sobre o futuro, os impactos mais amplos dos seus desafios e as oportunidades de crescimento.

                ANÁLISE DO LEAD:
                {lead_analysis}

                PERFIL DA PERSONA (Tomador de Decisão):
                {persona_profile}

                PONTOS DE DOR APROFUNDADOS (contém perguntas investigativas já formuladas):
                {deepened_pain_points}

                INSTRUÇÕES:
                1.  Revise todas as informações fornecidas para entender o contexto.
                2.  Não repita as perguntas investigativas já presentes nos "Pontos de Dor Aprofundados".
                3.  Formule de 2 a 3 novas perguntas estratégicas, abertas, que:
                    a.  Incentivem a persona a refletir sobre a visão de longo prazo da empresa.
                    b.  Explorem as implicações mais amplas dos desafios atuais (além do impacto imediato).
                    c.  Descubram objetivos ou aspirações ainda não mencionados.
                    d.  Sejam neutras e não sugiram uma solução específica.
                4.  As perguntas devem ser concisas e diretas.
                
                Responda APENAS com um objeto JSON com a seguinte estrutura:
                {{
                    "generated_questions": [
                        "Primeira pergunta estratégica (string)",
                        "Segunda pergunta estratégica (string)",
                        "Terceira pergunta estratégica (string, se aplicável)"
                    ]
                }}
                Não inclua nenhuma numeração, explicação ou texto adicional fora do objeto JSON.
            """

            formatted_prompt = prompt_template.format(
                lead_analysis=truncated_analysis,
                persona_profile=truncated_persona,
                deepened_pain_points=truncated_pain_points
            )

            llm_response_str = self.generate_llm_response(formatted_prompt)

            if not llm_response_str:
                return StrategicQuestionGenerationOutput(error_message="LLM call returned no response.")

            parsed_output = self.parse_llm_json_response(llm_response_str, StrategicQuestionGenerationOutput)
            
            if parsed_output.error_message:
                 self.logger.warning(f"StrategicQuestionGenerationAgent JSON parsing failed. Raw response: {llm_response_str[:500]}")
            # No specific regex fallback here. Error from parse_llm_json_response will be propagated.
            # Or, if the list is empty but there was no error message, it means LLM returned empty list.

            return parsed_output

        except Exception as e:
            self.logger.error(f"An unexpected error occurred in {self.name}: {e}")
            import traceback
            traceback.print_exc()
            return StrategicQuestionGenerationOutput(error_message=f"An unexpected error occurred: {str(e)}")

if __name__ == '__main__':
    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str) -> Optional[str]:
            if "NOVAS PERGUNTAS ESTRATÉGICAS:" in prompt:
                return (
                    "1. Pensando daqui a 3-5 anos, como a evolução da otimização de processos na Empresa Exemplo poderia impactar a sua capacidade de inovar e competir no mercado?\n"
                    "2. Além dos desafios operacionais diários, quais são as maiores oportunidades que você enxerga para o crescimento da Empresa Exemplo que talvez não estejam sendo totalmente exploradas atualmente?\n"
                    "3. Se você pudesse eliminar completamente um obstáculo que impede sua equipe de alcançar seu pleno potencial, qual seria e por quê?"
                )
            return "Resposta padrão do mock."

    print("Running mock test for StrategicQuestionGenerationAgent...")
    mock_llm = MockLLMClient()
    agent = StrategicQuestionGenerationAgent(llm_client=mock_llm)

    test_lead_analysis = "A Empresa Exemplo (médio porte, TI) foca em otimização."
    test_persona_profile = "Carlos Mendes, Diretor de Operações, focado em eficiência e ROI."
    test_deepened_pain_points = (
        "Ponto de Dor 1: Otimização de Processos Manuais.\n"
        "   - Pergunta Investigativa: Carlos, como os processos manuais atuais impactam o tempo?\n"
        "   - Pergunta Investigativa: Quais são os custos dos processos manuais?\n"
        "Ponto de Dor 2: Integração de Novas Tecnologias.\n"
        "   - Pergunta Investigativa: Quais são suas maiores preocupações com integração?\n"
    )

    input_data = StrategicQuestionGenerationInput(
        lead_analysis=test_lead_analysis,
        persona_profile=test_persona_profile,
        deepened_pain_points=test_deepened_pain_points
    )

    output = agent.process(input_data)

    print(f"Strategic Questions: \n{output.strategic_questions}")
    if output.error_message:
        print(f"Error: {output.error_message}")

    assert "1." in output.strategic_questions
    assert "2." in output.strategic_questions
    assert "impactar a sua capacidade de inovar" in output.strategic_questions # Check some specific phrase
    assert output.error_message is None
    print("Mock test completed.")
