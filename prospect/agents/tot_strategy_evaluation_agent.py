from typing import Optional, List
from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class ToTStrategyEvaluationInput(BaseModel):
    proposed_strategies_text: str # Output from ToTStrategyGenerationAgent
    current_lead_summary: str   # Original lead summary
    persona_profile: Optional[str] = None # Detailed persona profile
    product_service_info: Optional[str] = None # Info about user's product/service

class EvaluatedStrategyModel(BaseModel):
    strategy_name: str = Field(..., description="Nome da Estratégia Avaliada (deve corresponder a um nome da entrada).")
    evaluation_summary: str = Field(..., description="Resumo da avaliação da estratégia, incluindo uma visão geral de sua adequação e potencial.")
    strengths: List[str] = Field(default_factory=list, description="Principais pontos fortes identificados para esta estratégia.")
    weaknesses: List[str] = Field(default_factory=list, description="Principais pontos fracos ou riscos associados a esta estratégia.")
    suggested_improvements: List[str] = Field(default_factory=list, description="Sugestões de melhorias para otimizar a estratégia.")
    relevance_to_persona_score: float = Field(..., ge=0.0, le=1.0, description="Pontuação (0.0 a 1.0) da relevância da estratégia para o perfil da persona do lead.")
    potential_effectiveness_score: float = Field(..., ge=0.0, le=1.0, description="Pontuação (0.0 a 1.0) da eficácia potencial da estratégia em alcançar os objetivos de engajamento/conversão.")
    alignment_with_solution_score: float = Field(..., ge=0.0, le=1.0, description="Pontuação (0.0 a 1.0) do alinhamento da estratégia com a solução/produto/serviço oferecido.")
    estimated_risk_level: str = Field(..., description="Nível de risco estimado da estratégia (Baixo | Médio | Alto).") # Could use an Enum later
    overall_recommendation_score: float = Field(..., ge=0.0, le=1.0, description="Pontuação geral de recomendação da estratégia (0.0 a 1.0), considerando todos os fatores.")

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
            # Truncate inputs, giving appropriate space to each part
            total_chars_limit = GEMINI_TEXT_INPUT_TRUNCATE_CHARS
            truncated_strategies = self._truncate_text(input_data.proposed_strategies_text, total_chars_limit // 2)
            truncated_summary = self._truncate_text(input_data.current_lead_summary, total_chars_limit // 4)
            truncated_persona = self._truncate_text(input_data.persona_profile or "Não fornecido.", total_chars_limit // 4)
            truncated_product_info = self._truncate_text(input_data.product_service_info or "Não fornecido.", total_chars_limit // 4)


            prompt_template = """
                Você é um Estrategista de Vendas B2B Crítico e Analista, especialista em avaliar diversas abordagens estratégicas para o mercado brasileiro.

                Sua tarefa é AVALIAR CRITICAMENTE cada uma das 'ESTRATÉGIAS DE ABORDAGEM PROPOSTAS' fornecidas, usando o 'RESUMO ATUAL DO LEAD', o 'PERFIL DA PERSONA DO LEAD' e as 'INFORMAÇÕES DO PRODUTO/SERVIÇO' como base para sua avaliação.

                CONTEXTO PARA AVALIAÇÃO:

                1.  RESUMO ATUAL DO LEAD:
                    ```
                    {current_lead_summary}
                    ```

                2.  PERFIL DA PERSONA DO LEAD (detalhes sobre o decisor/influenciador):
                    ```
                    {persona_profile}
                    ```

                3.  INFORMAÇÕES DO PRODUTO/SERVIÇO (que estamos oferecendo):
                    ```
                    {product_service_info}
                    ```

                ESTRATÉGIAS DE ABORDAGEM PROPOSTAS (geradas anteriormente):
                ```json
                {proposed_strategies_text}
                ```
                // Nota: O input acima (`proposed_strategies_text`) geralmente é um JSON string representando uma lista de estratégias.
                // Você deve iterar sobre cada estratégia dentro dessa lista para avaliação.

                INSTRUÇÕES DE AVALIAÇÃO PARA CADA ESTRATÉGIA:
                Para cada estratégia proposta, forneça uma avaliação detalhada seguindo a estrutura JSON abaixo. Seja específico e justifique suas pontuações.

                Responda APENAS com um objeto JSON contendo uma lista de avaliações. A estrutura deve ser:
                ```json
                {{
                    "evaluated_strategies": [
                        {{
                            "strategy_name": "Nome da Estratégia Avaliada (exatamente como fornecido na entrada)",
                            "evaluation_summary": "Resumo conciso da sua avaliação geral da estratégia, destacando sua aplicabilidade e potencial geral para este lead e produto.",
                            "strengths": [
                                "Ponto forte principal identificado (ex: 'Alinhamento direto com a dor X da persona').",
                                "Outro ponto forte (ex: 'Canal de comunicação sugerido é o preferido pela persona')."
                            ],
                            "weaknesses": [
                                "Ponto fraco principal identificado (ex: 'Tom de voz pode ser inadequado para o nível sênior da persona').",
                                "Outro ponto fraco ou risco (ex: 'Proposta de valor não clara o suficiente na abordagem inicial')."
                            ],
                            "suggested_improvements": [
                                "Sugestão de melhoria 1 (ex: 'Refinar a mensagem de abertura para incluir um dado estatístico relevante').",
                                "Sugestão de melhoria 2 (ex: 'Considerar um canal alternativo como LinkedIn para o primeiro contato')."
                            ],
                            "relevance_to_persona_score": 0.0, // Pontuação de 0.0 a 1.0 indicando quão relevante a estratégia é para o perfil da persona (dores, motivações, cargo).
                            "potential_effectiveness_score": 0.0, // Pontuação de 0.0 a 1.0 para a eficácia potencial da estratégia em engajar o lead e avançar a conversa.
                            "alignment_with_solution_score": 0.0, // Pontuação de 0.0 a 1.0 indicando o quão bem a estratégia posiciona ou utiliza a nossa solução/produto/serviço.
                            "estimated_risk_level": "Baixo | Médio | Alto", // Nível de risco percebido (ex: risco de alienar o lead, ser ignorado, parecer genérico).
                            "overall_recommendation_score": 0.0 // Pontuação de 0.0 a 1.0 representando sua recomendação geral para esta estratégia (pode ser uma média ponderada ou avaliação holística).
                        }}
                        // ... mais objetos de avaliação, um para cada estratégia proposta na entrada
                    ]
                }}
                ```
                Certifique-se de que o campo `strategy_name` em sua saída corresponda exatamente ao nome da estratégia fornecida na entrada `proposed_strategies_text`.
                Não inclua nenhuma explicação ou texto adicional fora do objeto JSON principal.
            """

            formatted_prompt = prompt_template.format(
                proposed_strategies_text=truncated_strategies,
                current_lead_summary=truncated_summary,
                persona_profile=truncated_persona,
                product_service_info=truncated_product_info
            )

            llm_response_str = self.generate_llm_response(formatted_prompt, use_gemini_pro_vision=False) # Assuming text-only

            if not llm_response_str:
                self.logger.error("LLM call returned no response.")
                return ToTStrategyEvaluationOutput(error_message="LLM call returned no response.")

            parsed_output = self.parse_llm_json_response(llm_response_str, ToTStrategyEvaluationOutput)
            
            if parsed_output.error_message:
                 self.logger.warning(f"ToTStrategyEvaluationAgent JSON parsing failed. Raw response: {llm_response_str[:500]}")
                 # Attempt to return partially parsed strategies if possible, or an empty list with error
                 return ToTStrategyEvaluationOutput(
                     evaluated_strategies=parsed_output.evaluated_strategies or [], # Ensure it's a list
                     error_message=parsed_output.error_message
                 )

            return parsed_output
        
        except Exception as e:
            self.logger.error(f"An unexpected error occurred in {self.name}: {e}", exc_info=True)
            return ToTStrategyEvaluationOutput(error_message=f"An unexpected error occurred: {str(e)}")

if __name__ == '__main__':
    import json

    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str, use_gemini_pro_vision: bool = False) -> Optional[str]:
            # This mock will return a JSON string based on the new structure
            mock_json_response = {
                "evaluated_strategies": [
                    {
                        "strategy_name": "Estratégia 1: O Desafio da Eficiência Oculta",
                        "evaluation_summary": "Estratégia promissora, bem alinhada com o perfil focado em eficiência do lead (Carlos Mendes) e as dores de otimização. A solução de IA é diretamente aplicável.",
                        "strengths": [
                            "Abordagem consultiva e analítica ressoa com diretores de operações.",
                            "Foco em ROI e eficiência é um gatilho forte para a persona.",
                            "Uso de email e LinkedIn é apropriado para o contato inicial."
                        ],
                        "weaknesses": [
                            "Pode ser percebida como muito direta se o lead não estiver ativamente buscando soluções.",
                            "O estudo de caso precisa ser extremamente relevante e conciso para prender a atenção."
                        ],
                        "suggested_improvements": [
                            "Personalizar a pergunta de abertura com um dado específico ou desafio recente da Empresa Exemplo.",
                            "Oferecer uma ferramenta de auto-diagnóstico ou um checklist rápido junto ao estudo de caso para aumentar o engajamento."
                        ],
                        "relevance_to_persona_score": 0.9,
                        "potential_effectiveness_score": 0.8,
                        "alignment_with_solution_score": 0.95,
                        "estimated_risk_level": "Baixo",
                        "overall_recommendation_score": 0.88
                    },
                    {
                        "strategy_name": "Estratégia 2: Parceria para Inovação Contínua",
                        "evaluation_summary": "Estratégia com bom potencial, mas precisa conectar 'inovação' de forma mais clara aos benefícios tangíveis de eficiência e ROI para o lead. Menos direta que a Estratégia 1 para as dores imediatas.",
                        "strengths": [
                            "Tom visionário pode ser atraente para um líder em uma empresa de TI em expansão.",
                            "Webinar é um bom formato para educar e demonstrar expertise em inovação."
                        ],
                        "weaknesses": [
                            "'Parceria para inovação' pode soar vago e menos urgente que otimização de custos/processos.",
                            "Requer que o lead invista mais tempo (webinar) comparado a um email/estudo de caso."
                        ],
                        "suggested_improvements": [
                            "Conectar explicitamente 'inovação contínua' com 'eficiência operacional a longo prazo' e 'sustentabilidade do crescimento da expansão'.",
                            "Na mensagem de abertura, mencionar a recente expansão da Empresa Exemplo como um gancho para discutir como a inovação suporta tal crescimento."
                        ],
                        "relevance_to_persona_score": 0.7,
                        "potential_effectiveness_score": 0.65,
                        "alignment_with_solution_score": 0.8,
                        "estimated_risk_level": "Médio",
                        "overall_recommendation_score": 0.72
                    }
                ]
            }
            return json.dumps(mock_json_response)

    print("Running mock test for ToTStrategyEvaluationAgent...")
    mock_llm = MockLLMClient()
    agent = ToTStrategyEvaluationAgent(
        name="ToTStrategyEvaluationAgent",
        description="Evaluates Tree-of-Thought strategies critically.",
        llm_client=mock_llm,
        logger_name="TestLogger" # Optional: for quieter test output
    )

    # Example of what proposed_strategies_text might look like (as a JSON string)
    # This would typically come from the ToTStrategyGenerationAgent
    proposed_strategies_list = [
        {
            "strategy_name": "Estratégia 1: O Desafio da Eficiência Oculta",
            "angle_hook": "Focar nos custos não óbvios de processos manuais e como a IA pode revelar economias significativas.",
            "tone_of_voice": "Consultivo e Analítico",
            "communication_channels": ["Email Personalizado", "LinkedIn Message"],
            "key_talking_points": ["ROI da automação", "Riscos da ineficiência manual", "Cases de sucesso similares"],
            "main_call_to_action": "Agendar uma breve análise de diagnóstico de eficiência.",
            "opening_question": "Carlos, muitas empresas no setor de TI não percebem o quanto processos manuais podem estar limitando a escalabilidade, especialmente durante expansões. Você já quantificou o impacto disso na Empresa Exemplo?"
        },
        {
            "strategy_name": "Estratégia 2: Parceria para Inovação Contínua",
            "angle_hook": "Posicionar nossa solução como um motor de inovação contínua, ajudando a Empresa Exemplo a se manter à frente no mercado.",
            "tone_of_voice": "Visionário e de Parceria",
            "communication_channels": ["Convite para Webinar Exclusivo", "Artigo no LinkedIn Pulse"],
            "key_talking_points": ["IA como vantagem competitiva", "Futuro do setor de TI", "Inovação incremental vs. disruptiva"],
            "main_call_to_action": "Participar de um webinar sobre o futuro da IA no setor de TI.",
            "opening_question": "Carlos, considerando a velocidade das mudanças tecnológicas e a recente expansão da Empresa Exemplo, como vocês estão estruturando a inovação contínua para garantir a liderança de mercado?"
        }
    ]
    test_proposed_strategies_json_string = json.dumps({"proposed_strategies": proposed_strategies_list})


    test_lead_summary = (
        "Lead: Empresa Exemplo (Médio porte, setor de TI). Contato Principal: Carlos Mendes (Diretor de Operações). "
        "Foco da Persona: Eficiência operacional, ROI, otimização de processos, redução de custos. "
        "Dores Conhecidas: Processos manuais demorados, dificuldade em escalar operações, busca por modernização tecnológica. "
        "Gatilhos de Compra: Recente expansão de mercado anunciada pela empresa, busca por soluções que suportem o crescimento."
    )
    test_persona_profile = (
        "Nome: Carlos Mendes\nCargo: Diretor de Operações\nEmpresa: Empresa Exemplo\nNível de Senioridade: Alto (poder de decisão)\n"
        "Responsabilidades: Eficiência das operações, otimização de custos, implementação de novas tecnologias que melhorem processos.\n"
        "Principais Desafios: Garantir que a infraestrutura e os processos suportem a expansão da empresa sem perda de qualidade ou aumento excessivo de custos.\n"
        "Como se informa: Relatórios da indústria, webinars técnicos, artigos de liderança de pensamento, networking com pares.\n"
        "Tolerância a Riscos: Moderada - aberto a inovações, mas precisa ver ROI claro e cases de sucesso antes de grandes investimentos.\n"
        "Estilo de Comunicação Preferido: Direto, baseado em dados, focado em soluções e resultados."
    )
    test_product_info = (
        "Nossa solução é uma plataforma de Inteligência Artificial (IA) que automatiza processos de back-office e otimiza a alocação de recursos para empresas de TI. "
        "Benefícios Chave: Redução de custos operacionais em até 25%, aumento da eficiência em até 40%, melhoria na tomada de decisão com base em dados. "
        "Diferenciais: Implementação rápida (2-4 semanas), interface intuitiva, suporte técnico especializado no Brasil."
    )


    input_data = ToTStrategyEvaluationInput(
        proposed_strategies_text=test_proposed_strategies_json_string,
        current_lead_summary=test_lead_summary,
        persona_profile=test_persona_profile,
        product_service_info=test_product_info
    )

    output = agent.process(input_data)

    print("\n--- Agent Output ---")
    if output.error_message:
        print(f"Error: {output.error_message}")

    if output.evaluated_strategies:
        for i, eval_strat in enumerate(output.evaluated_strategies):
            print(f"\n--- Evaluated Strategy {i+1} ---")
            print(f"Name: {eval_strat.strategy_name}")
            print(f"Summary: {eval_strat.evaluation_summary}")
            print(f"Strengths: {eval_strat.strengths}")
            print(f"Weaknesses: {eval_strat.weaknesses}")
            print(f"Improvements: {eval_strat.suggested_improvements}")
            print(f"Persona Score: {eval_strat.relevance_to_persona_score}")
            print(f"Effectiveness Score: {eval_strat.potential_effectiveness_score}")
            print(f"Solution Alignment: {eval_strat.alignment_with_solution_score}")
            print(f"Risk: {eval_strat.estimated_risk_level}")
            print(f"Overall Score: {eval_strat.overall_recommendation_score}")

    assert output.error_message is None, f"Error message was: {output.error_message}"
    assert len(output.evaluated_strategies) == 2
    assert output.evaluated_strategies[0].strategy_name == "Estratégia 1: O Desafio da Eficiência Oculta"
    assert output.evaluated_strategies[0].overall_recommendation_score > 0.8
    assert output.evaluated_strategies[1].estimated_risk_level == "Médio"

    print("\nMock test for ToTStrategyEvaluationAgent completed successfully.")
