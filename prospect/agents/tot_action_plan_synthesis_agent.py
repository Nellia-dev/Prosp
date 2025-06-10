from typing import Optional, List
from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class ToTActionPlanSynthesisInput(BaseModel):
    evaluated_strategies_text: str # Output from ToTStrategyEvaluationAgent
    proposed_strategies_text: str  # Output from ToTStrategyGenerationAgent (for reference)
    current_lead_summary: str    # Original lead summary (for context)

class ActionPlanStepModel(BaseModel):
    step_number: int
    channel: str
    action_description: str
    key_message_or_argument: str
    cta: Optional[str] = None

class ToTActionPlanSynthesisOutput(BaseModel):
    recommended_strategy_name: str = "Estratégia Combinada/Refinada"
    primary_angle_hook: str = "Não especificado"
    tone_of_voice: str = "Consultivo"
    action_sequence: List[ActionPlanStepModel] = Field(default_factory=list)
    key_talking_points: List[str] = Field(default_factory=list) # Overall talking points
    main_opening_question: str = "Não especificado"
    success_metrics: List[str] = Field(default_factory=list) # e.g., "Taxa de resposta ao email"
    contingency_plan: Optional[str] = None
    error_message: Optional[str] = None

class ToTActionPlanSynthesisAgent(BaseAgent[ToTActionPlanSynthesisInput, ToTActionPlanSynthesisOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: ToTActionPlanSynthesisInput) -> ToTActionPlanSynthesisOutput:
        final_action_plan_text = ""
        error_message = None

        try:
            # Truncate inputs, giving more space to evaluated strategies
            truncated_eval_strategies = self._truncate_text(input_data.evaluated_strategies_text, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 2)
            truncated_prop_strategies = self._truncate_text(input_data.proposed_strategies_text, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 4)
            truncated_summary = self._truncate_text(input_data.current_lead_summary, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 4)

            prompt_template = """
                Você é um Sintetizador de Planos de Ação B2B. Sua tarefa é criar um ÚNICO plano de ação coeso e final, com base na avaliação das estratégias propostas e no perfil do lead.

                AVALIAÇÃO DAS ESTRATÉGIAS DE ABORDAGEM (inclui pontos fortes, fracos, melhorias e pontuação de confiança):
                {evaluated_strategies_text}

                ESTRATÉGIAS PROPOSTAS ORIGINAIS (para referência, caso precise resgatar alguma ideia original):
                {proposed_strategies_text}

                RESUMO ATUAL DO LEAD (para referência contextual):
                {current_lead_summary}

                INSTRUÇÕES:
                1.  Revise a avaliação de cada estratégia (`evaluated_strategies_text`), focando naquela(s) com maior "Pontuação de Confiança" e melhor alinhamento com o lead. Considere as "Melhorias Sugeridas".
                2.  Sintetize UM ÚNICO plano de ação final. Este plano deve ser o melhor caminho a seguir.
                3.  Detalhe o plano de ação final nos campos JSON especificados abaixo.

                Responda APENAS com um objeto JSON com a seguinte estrutura:
                {{
                    "recommended_strategy_name": "Nome da Estratégia Final (string, ex: Eficiência Consultiva com Prova Social)",
                    "primary_angle_hook": "A mensagem central da abordagem (string)",
                    "tone_of_voice": "Tom de voz principal (string, ex: Consultivo, Direto, Educacional)",
                    "action_sequence": [
                        {{
                            "step_number": 1,
                            "channel": "Canal de contato (string, ex: Email, LinkedIn)",
                            "action_description": "Descrição da ação a ser tomada (string)",
                            "key_message_or_argument": "Mensagem ou argumento chave para este passo (string)",
                            "cta": "Call to action específico para este passo (string, opcional)"
                        }}
                        // ... mais passos na sequência (2-3 passos iniciais)
                    ],
                    "key_talking_points": ["Ponto de discussão geral 1 (string)", "Ponto de discussão geral 2 (string)"],
                    "main_opening_question": "A pergunta principal para iniciar o primeiro contato (string)",
                    "success_metrics": ["Métrica de sucesso inicial 1 (string, ex: Taxa de resposta ao email)", "Métrica 2 (string)"],
                    "contingency_plan": "Plano de contingência breve se a abordagem inicial não funcionar (string, opcional)"
                }}
                Não inclua nenhuma explicação ou texto adicional fora do objeto JSON.
            """

            formatted_prompt = prompt_template.format(
                evaluated_strategies_text=truncated_eval_strategies,
                proposed_strategies_text=truncated_prop_strategies, # For LLM to reference original ideas if needed
                current_lead_summary=truncated_summary
            )

            llm_response_str = self.generate_llm_response(formatted_prompt)

            if not llm_response_str:
                return ToTActionPlanSynthesisOutput(error_message="LLM call returned no response.")

            parsed_output = self.parse_llm_json_response(llm_response_str, ToTActionPlanSynthesisOutput)
            
            if parsed_output.error_message:
                 self.logger.warning(f"ToTActionPlanSynthesisAgent JSON parsing failed. Raw response: {llm_response_str[:500]}")
            
            return parsed_output
        
        except Exception as e:
            self.logger.error(f"An unexpected error occurred in {self.name}: {e}")
            import traceback
            traceback.print_exc()
            return ToTActionPlanSynthesisOutput(error_message=f"An unexpected error occurred: {str(e)}")

if __name__ == '__main__':
    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str) -> Optional[str]:
            if "PLANO DE AÇÃO FINAL SINTETIZADO:" in prompt:
                return (
                    "PLANO DE AÇÃO FINAL SINTETIZADO:\n\n"
                    "**Nome da Estratégia Final:** Eficiência Consultiva com Foco no Impacto da Expansão\n\n"
                    "**Principal Ângulo/Gancho:** Ajudar Carlos Mendes (Diretor de Operações da Empresa Exemplo) a quantificar e mitigar os desafios de eficiência operacional que podem ser exacerbados pela recente expansão da empresa, utilizando Nossas Soluções Incríveis de IA.\n\n"
                    "**Tom de Voz:** Consultivo, Analítico e Orientado a Soluções.\n\n"
                    "**Sequência de Canais e Ações:**\n"
                    "1.  **Email Personalizado Inicial:** Enviar um email focado nos desafios de eficiência no contexto da expansão. Anexar um estudo de caso conciso ou um infográfico sobre como a IA pode otimizar operações em empresas de TI em crescimento.\n"
                    "2.  **Conexão no LinkedIn (2 dias após email):** Enviar um convite de conexão para Carlos Mendes, mencionando o email enviado e um insight rápido sobre os desafios de escalar operações (ex: 'Vi que a Empresa Exemplo está expandindo. Muitas empresas nesse estágio encontram desafios em X. Curioso para saber como vocês estão lidando com isso.').\n"
                    "3.  **Follow-up no LinkedIn (3 dias após conexão, se aceita):** Compartilhar um artigo relevante ou um segundo breve insight sobre otimização de processos para empresas em expansão. Oferecer uma ferramenta simples de auto-diagnóstico (se disponível) ou um breve call to action para uma conversa exploratória.\n"
                    "4.  **Call Exploratória (se houver engajamento):** Focar em entender os desafios específicos da Empresa Exemplo no contexto da expansão e como Nossas Soluções Incríveis de IA podem ajudar.\n\n"
                    "**Principais Pontos de Discussão/Argumentos:**\n"
                    "1.  Os riscos de ineficiência aumentam significativamente durante e após a expansão de mercado.\n"
                    "2.  Nossas Soluções Incríveis de IA podem automatizar X, Y, Z, liberando recursos valiosos.\n"
                    "3.  Quantificação do ROI esperado pela otimização de processos (com base em dados de mercado ou do estudo de caso).\n"
                    "4.  Facilidade de integração da nossa solução, minimizando disrupções (abordando dor da persona).\n"
                    "5.  Suporte e parceria para garantir a adoção bem-sucedida da tecnologia.\n\n"
                    "**Pergunta de Abertura Principal (para o email):**\n"
                    "'Carlos, com a recente e empolgante expansão da Empresa Exemplo, muitas empresas de TI enfrentam o desafio de escalar suas operações de forma eficiente. Como vocês estão priorizando a otimização de processos internos para sustentar esse crescimento?'\n\n"
                    "**Métricas de Sucesso Iniciais:**\n"
                    "- Taxa de abertura e cliques do email inicial.\n"
                    "- Taxa de aceitação do convite de conexão no LinkedIn.\n"
                    "- Respostas e engajamento nas mensagens do LinkedIn.\n"
                    "- Agendamento de calls exploratórias."
                )
            return "Resposta padrão do mock."

    print("Running mock test for ToTActionPlanSynthesisAgent...")
    mock_llm = MockLLMClient()
    agent = ToTActionPlanSynthesisAgent(
        name="ToTActionPlanSynthesisAgent",
        description="Synthesizes a final action plan from evaluated strategies.",
        llm_client=mock_llm
    )

    test_eval_strategies = (
        "**Avaliação da Estratégia 1: O Desafio da Eficiência Oculta**\n"
        "- Adequação: Alta. Pontuação de Confiança: Alta.\n"
        "- Melhorias: Personalizar pergunta com dado específico. Oferecer ferramenta de auto-diagnóstico.\n\n"
        "**Avaliação da Estratégia 2: Parceria para Inovação Contínua**\n"
        "- Adequação: Média-Alta. Pontuação de Confiança: Média.\n"
        "- Melhorias: Conectar inovação com eficiência a longo prazo e expansão."
    )
    test_prop_strategies = (
        "**Estratégia 1: O Desafio da Eficiência Oculta** (detalhes...)\n"
        "**Estratégia 2: Parceria para Inovação Contínua** (detalhes...)"
    )
    test_lead_summary = (
        "Lead: Empresa Exemplo (Médio porte, TI). Persona: Carlos Mendes (Diretor de Operações), focado em eficiência, ROI. "
        "Dores: Otimização de processos manuais. Gatilhos: Expansão de mercado, busca por modernização. Produto nosso: Nossas Soluções Incríveis de IA."
    )

    input_data = ToTActionPlanSynthesisInput(
        evaluated_strategies_text=test_eval_strategies,
        proposed_strategies_text=test_prop_strategies,
        current_lead_summary=test_lead_summary
    )

    output = agent.process(input_data)

    print(f"Final Action Plan Text: \n{output.final_action_plan_text}")
    if output.error_message:
        print(f"Error: {output.error_message}")

    assert "PLANO DE AÇÃO FINAL SINTETIZADO:" in output.final_action_plan_text
    assert "Eficiência Consultiva com Foco no Impacto da Expansão" in output.final_action_plan_text
    assert "Carlos Mendes" in output.final_action_plan_text
    assert "Nossas Soluções Incríveis de IA" in output.final_action_plan_text
    assert output.error_message is None
    print("Mock test completed.")
