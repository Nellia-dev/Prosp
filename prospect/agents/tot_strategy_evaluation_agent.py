from typing import Optional, List
from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class ToTStrategyEvaluationInput(BaseModel):
    proposed_strategies_text: str # Output from ToTStrategyGenerationAgent
    current_lead_summary: str   # Same summary used for generation, for context

class EvaluatedStrategyModel(BaseModel):
    strategy_name: str # Name of the strategy being evaluated
    suitability_assessment: str
    strengths: List[str]
    weaknesses_or_risks: List[str]
    suggested_improvements: List[str]
    confidence_score: str # e.g., "Baixa", "Média", "Alta"
    confidence_justification: str

class ToTStrategyEvaluationOutput(BaseModel):
    evaluated_strategies: List[EvaluatedStrategyModel] = Field(default_factory=list)
    error_message: Optional[str] = None

class ToTStrategyEvaluationAgent(BaseAgent[ToTStrategyEvaluationInput, ToTStrategyEvaluationOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: ToTStrategyEvaluationInput) -> ToTStrategyEvaluationOutput:
        evaluated_strategies_text = ""
        error_message = None

        try:
            truncated_strategies = self._truncate_text(input_data.proposed_strategies_text, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 2)
            truncated_summary = self._truncate_text(input_data.current_lead_summary, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 2)

            prompt_template = """
                Você é um Avaliador Crítico de Estratégias de Abordagem B2B. Seu papel é analisar as estratégias propostas, considerando o perfil do lead.

                ESTRATÉGIAS DE ABORDAGEM PROPOSTAS:
                {proposed_strategies_text}

                RESUMO ATUAL DO LEAD (para referência):
                {current_lead_summary}

                INSTRUÇÕES:
                Para cada estratégia proposta no texto fornecido (`proposed_strategies_text`):
                1.  **strategy_name**: Identifique e repita o nome da estratégia que está sendo avaliada.
                2.  **suitability_assessment**: Avalie a adequação da estratégia ao perfil do lead (persona, dores, gatilhos, setor).
                3.  **strengths**: Liste os pontos fortes da estratégia (como uma lista de strings).
                4.  **weaknesses_or_risks**: Liste os potenciais pontos fracos ou riscos (como uma lista de strings).
                5.  **suggested_improvements**: Sugira de 1 a 2 possíveis melhorias ou ajustes para a estratégia (como uma lista de strings).
                6.  **confidence_score**: Atribua uma pontuação de confiança (ex: "Baixa", "Média", "Alta") para o sucesso da estratégia.
                7.  **confidence_justification**: Forneça uma breve justificativa para a pontuação de confiança.

                Responda APENAS com um objeto JSON com a seguinte estrutura:
                {{
                    "evaluated_strategies": [
                        {{
                            "strategy_name": "Nome da Estratégia Avaliada 1",
                            "suitability_assessment": "Avaliação da adequação...",
                            "strengths": ["Ponto Forte 1.1", "Ponto Forte 1.2"],
                            "weaknesses_or_risks": ["Ponto Fraco 1.1", "Ponto Fraco 1.2"],
                            "suggested_improvements": ["Melhoria Sugerida 1.1", "Melhoria Sugerida 1.2"],
                            "confidence_score": "Alta",
                            "confidence_justification": "Justificativa para a confiança na Estratégia 1..."
                        }}
                        // ... mais avaliações de estratégias se houver múltiplas no texto de entrada
                    ]
                }}
                Não inclua nenhuma explicação ou texto adicional fora do objeto JSON.
            """

            formatted_prompt = prompt_template.format(
                proposed_strategies_text=truncated_strategies,
                current_lead_summary=truncated_summary
            )

            llm_response_str = self.generate_llm_response(formatted_prompt)

            if not llm_response_str:
                return ToTStrategyEvaluationOutput(error_message="LLM call returned no response.")

            parsed_output = self.parse_llm_json_response(llm_response_str, ToTStrategyEvaluationOutput)
            
            if parsed_output.error_message:
                 self.logger.warning(f"ToTStrategyEvaluationAgent JSON parsing failed. Raw response: {llm_response_str[:500]}")

            return parsed_output
        
        except Exception as e:
            self.logger.error(f"An unexpected error occurred in {self.name}: {e}")
            import traceback
            traceback.print_exc()
            return ToTStrategyEvaluationOutput(error_message=f"An unexpected error occurred: {str(e)}")

if __name__ == '__main__':
    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str) -> Optional[str]:
            if "AVALIAÇÃO DAS ESTRATÉGIAS DE ABORDAGEM:" in prompt:
                return (
                    "AVALIAÇÃO DAS ESTRATÉGIAS DE ABORDAGEM:\n\n"
                    "**Avaliação da Estratégia 1: O Desafio da Eficiência Oculta**\n"
                    "- Adequação: Alta. Alinha-se bem com o foco em eficiência do Diretor de Operações (Carlos Mendes) e a dor de processos manuais.\n"
                    "- Pontos Fortes: Abordagem analítica e consultiva, uso de email e LinkedIn é apropriado para o perfil.\n"
                    "- Pontos Fracos: Pode ser percebida como muito direta se o lead não estiver ciente dos 'custos ocultos'. O estudo de caso precisa ser muito relevante.\n"
                    "- Melhorias: \n"
                    "  1. Personalizar a pergunta de abertura com um dado específico da Empresa Exemplo, se possível.\n"
                    "  2. Oferecer uma ferramenta simples de auto-diagnóstico junto com o estudo de caso.\n"
                    "- Pontuação de Confiança: Alta. Justificativa: Aborda diretamente dores e o perfil da persona com uma solução lógica.\n\n"
                    "**Avaliação da Estratégia 2: Parceria para Inovação Contínua**\n"
                    "- Adequação: Média-Alta. O ângulo de inovação é bom para o setor de TI e para um Diretor de Operações, mas pode ser menos prioritário que a eficiência imediata.\n"
                    "- Pontos Fortes: Tom visionário pode ser atraente, webinar é um bom canal para educar.\n"
                    "- Pontos Fracos: 'Parceria para inovação' pode soar vago inicialmente. O gancho precisa ser rapidamente conectado a benefícios tangíveis.\n"
                    "- Melhorias:\n"
                    "  1. Conectar a 'inovação' com 'eficiência a longo prazo' ou 'preparação para crescimento devido à expansão'.\n"
                    "  2. Na pergunta de abertura, mencionar a recente expansão da Empresa Exemplo como um motivador para discutir inovação.\n"
                    "- Pontuação de Confiança: Média. Justificativa: Estratégia boa, mas precisa de conexão mais forte com as dores imediatas da persona para garantir tração inicial."
                )
            return "Resposta padrão do mock."

    print("Running mock test for ToTStrategyEvaluationAgent...")
    mock_llm = MockLLMClient()
    agent = ToTStrategyEvaluationAgent(
        name="ToTStrategyEvaluationAgent",
        description="Evaluates Tree-of-Thought strategies.",
        llm_client=mock_llm
    )

    test_proposed_strategies = (
        "**Estratégia 1: O Desafio da Eficiência Oculta**\n"
        "- Ângulo: Focar nos custos não óbvios...\n"
        "- Tom de Voz: Consultivo e Analítico...\n"
        "- Pergunta de Abertura: 'Muitas empresas no setor [setor do lead] não percebem...'\n\n"
        "**Estratégia 2: Parceria para Inovação Contínua**\n"
        "- Ângulo: Posicionar o produto como motor de inovação...\n"
        "- Tom de Voz: Visionário e de Parceria...\n"
        "- Pergunta de Abertura: 'Carlos, considerando a velocidade das mudanças...'"
    )
    test_lead_summary = (
        "Lead: Empresa Exemplo (Médio porte, TI). Persona: Carlos Mendes (Diretor de Operações), focado em eficiência, ROI. "
        "Dores: Otimização de processos manuais. Gatilhos: Expansão de mercado, busca por modernização."
    )

    input_data = ToTStrategyEvaluationInput(
        proposed_strategies_text=test_proposed_strategies,
        current_lead_summary=test_lead_summary
    )

    output = agent.process(input_data)

    print(f"Evaluated Strategies Text: \n{output.evaluated_strategies_text}")
    if output.error_message:
        print(f"Error: {output.error_message}")

    assert "Avaliação da Estratégia 1:" in output.evaluated_strategies_text
    assert "Avaliação da Estratégia 2:" in output.evaluated_strategies_text
    assert "Pontuação de Confiança: Alta" in output.evaluated_strategies_text
    assert output.error_message is None
    print("Mock test completed.")
