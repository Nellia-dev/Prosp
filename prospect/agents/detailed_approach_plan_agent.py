from typing import Optional, List
from pydantic import BaseModel, Field, validator

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class DetailedApproachPlanInput(BaseModel):
    lead_analysis: str
    persona_profile: str
    deepened_pain_points: str # Includes investigative questions
    final_action_plan_text: str # Synthesized plan from ToT agents
    product_service_offered: str
    lead_url: str

# Sub-models for structured output
class ContactStepDetail(BaseModel):
    step_number: int
    channel: str
    objective: str
    key_topics_arguments: List[str] = Field(default_factory=list)
    key_questions: List[str] = Field(default_factory=list)
    cta: str
    supporting_materials: Optional[str] = None
    
    @validator('key_questions', pre=True)
    def validate_key_questions(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        return v if isinstance(v, list) else []
    
    @validator('key_topics_arguments', pre=True)
    def validate_key_topics_arguments(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        return v if isinstance(v, list) else []

class DetailedApproachPlanOutput(BaseModel):
    main_objective: str = "Não especificado"
    adapted_elevator_pitch: str = "Não especificado"
    contact_sequence: List[ContactStepDetail] = Field(default_factory=list)
    engagement_indicators_to_monitor: List[str] = Field(default_factory=list)
    potential_obstacles_attention_points: List[str] = Field(default_factory=list)
    suggested_next_steps_if_successful: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None

class DetailedApproachPlanAgent(BaseAgent[DetailedApproachPlanInput, DetailedApproachPlanOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)
        from loguru import logger
        self.logger = logger

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: DetailedApproachPlanInput) -> DetailedApproachPlanOutput:
        detailed_approach_plan_text = ""
        error_message = None

        try:
            # Truncate inputs, final_action_plan_text is key
            tr_lead_analysis = self._truncate_text(input_data.lead_analysis, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 5)
            tr_persona_profile = self._truncate_text(input_data.persona_profile, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 5)
            tr_deepened_pain_points = self._truncate_text(input_data.deepened_pain_points, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 5)
            tr_final_action_plan = self._truncate_text(input_data.final_action_plan_text, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 3)


            prompt_template = """
                Você é um Estrategista de Contas Sênior. Sua tarefa é expandir o "Plano de Ação Final Sintetizado" em um "Plano de Abordagem Detalhado".
                Este plano deve ser prático e acionável para a equipe de vendas.

                PLANO DE AÇÃO FINAL SINTETIZADO:
                {final_action_plan_text}

                INFORMAÇÕES DE CONTEXTO ADICIONAIS:
                Análise do Lead: {lead_analysis}
                Perfil da Persona: {persona_profile}
                Pontos de Dor Aprofundados (com perguntas investigativas): {deepened_pain_points}
                Produto/Serviço Oferecido: {product_service_offered}
                URL do Lead: {lead_url}

                INSTRUÇÕES:
                Com base no "Plano de Ação Final Sintetizado" e nas informações de contexto, detalhe os seguintes aspectos em formato JSON:

                Responda APENAS com um objeto JSON com a seguinte estrutura:
                {{
                    "main_objective": "Objetivo Principal da Abordagem (string, reafirme ou refine o objetivo do plano de ação)",
                    "adapted_elevator_pitch": "Mensagem Central - Elevator Pitch Adaptado para ESTE lead (string, 2-3 frases concisas)",
                    "contact_sequence": [
                        {{
                            "step_number": 1,
                            "channel": "Canal de contato (string, ex: Email, LinkedIn, Telefone)",
                            "objective": "Objetivo específico deste contato (string, ex: Obter resposta, Agendar call)",
                            "key_topics_arguments": ["Tópico/Argumento chave 1 (string)", "Tópico/Argumento 2 (string)"],
                            "key_questions": ["Pergunta chave 1 a ser feita (string, opcional)", "Pergunta chave 2 (string, opcional)"],
                            "cta": "Call to Action específico para este passo (string)",
                            "supporting_materials": "Recursos/Materiais de apoio (string, opcional, ex: Link para estudo de caso)"
                        }}
                        // ... Detalhe os primeiros 3-5 passos da sequência de contato
                    ],
                    "engagement_indicators_to_monitor": ["Indicador de engajamento 1 (string, ex: Abertura de email)", "Indicador 2 (string)"],
                    "potential_obstacles_attention_points": ["Ponto de atenção/obstáculo 1 (string, ex: Lead pode estar ocupado)", "Obstáculo 2 (string)"],
                    "suggested_next_steps_if_successful": ["Próximo passo sugerido 1 (string)", "Próximo passo 2 (string)"]
                }}
                Não inclua nenhuma explicação ou texto adicional fora do objeto JSON.
            """

            formatted_prompt = prompt_template.format(
                final_action_plan_text=tr_final_action_plan,
                lead_analysis=tr_lead_analysis,
                persona_profile=tr_persona_profile,
                deepened_pain_points=tr_deepened_pain_points,
                product_service_offered=input_data.product_service_offered,
                lead_url=input_data.lead_url
            )

            llm_response_str = self.generate_llm_response(formatted_prompt)

            if not llm_response_str:
                return DetailedApproachPlanOutput(error_message="LLM call returned no response.")

            parsed_output = self.parse_llm_json_response(llm_response_str, DetailedApproachPlanOutput)
            
            if parsed_output.error_message:
                 self.logger.warning(f"DetailedApproachPlanAgent JSON parsing failed. Raw response: {llm_response_str[:500]}")
            
            return parsed_output

        except Exception as e:
            self.logger.error(f"An unexpected error occurred in {self.name}: {e}")
            import traceback
            traceback.print_exc()
            return DetailedApproachPlanOutput(error_message=f"An unexpected error occurred: {str(e)}")

if __name__ == '__main__':
    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str) -> Optional[str]:
            if "PLANO DE ABORDAGEM DETALHADO:" in prompt:
                return (
                    "PLANO DE ABORDAGEM DETALHADO:\n\n"
                    "**1. Objetivo Principal da Abordagem:**\n"
                    "Iniciar um diálogo consultivo com Carlos Mendes (Diretor de Operações da Empresa Exemplo) sobre como Nossas Soluções Incríveis de IA podem mitigar os desafios de eficiência operacional, especialmente no contexto da recente expansão da empresa, visando agendar uma call exploratória.\n\n"
                    "**2. Mensagem Central (Elevator Pitch Adaptado):**\n"
                    "Com a expansão da Empresa Exemplo, garantir que as operações escalem de forma eficiente é crucial. Nossas Soluções Incríveis de IA ajudam empresas de TI como a sua a automatizar processos chave e otimizar recursos, assegurando que o crescimento não seja prejudicado por gargalos operacionais, e liberando sua equipe para focar em inovação.\n\n"
                    "**3. Detalhamento da Sequência de Contato (Primeiros 3 passos):**\n\n"
                    "   **Passo 1:**\n"
                    "   - **Canal:** Email Personalizado Inicial\n"
                    "   - **Objetivo Específico:** Obter uma resposta inicial e demonstrar entendimento dos desafios da Empresa Exemplo.\n"
                    "   - **Principais Tópicos/Argumentos:** Reconhecer a expansão da empresa; conectar expansão com desafios de escalabilidade operacional; mencionar como a IA pode otimizar processos (ex: automatizar X, Y, Z).\n"
                    "   - **Pergunta(s) Chave:** 'Carlos, com a recente e empolgante expansão da Empresa Exemplo, muitas empresas de TI enfrentam o desafio de escalar suas operações de forma eficiente. Como vocês estão priorizando a otimização de processos internos para sustentar esse crescimento?' (Pergunta do Plano de Ação)\n"
                    "   - **Call to Action (CTA):** 'Você teria 15 minutos na próxima semana para uma breve conversa sobre como podemos ajudar a Empresa Exemplo a navegar por esses desafios de crescimento com mais eficiência?'\n"
                    "   - **Recursos/Materiais de Apoio:** Link para um estudo de caso conciso ou infográfico sobre IA para otimização em empresas de TI em expansão.\n\n"
                    "   **Passo 2:**\n"
                    "   - **Canal:** Conexão no LinkedIn (2 dias após email)\n"
                    "   - **Objetivo Específico:** Estabelecer conexão e reforçar a mensagem inicial de forma mais informal.\n"
                    "   - **Principais Tópicos/Argumentos:** Referência ao email enviado; breve insight sobre desafios de escalar operações.\n"
                    "   - **Pergunta(s) Chave (na nota de convite):** 'Carlos, vi que a Empresa Exemplo está expandindo - parabéns! Muitas empresas nesse estágio encontram desafios em [mencionar um desafio específico de otimização]. Curioso para saber como vocês estão lidando com isso. Enviei um email com algumas ideias, adoraria conectar por aqui também.'\n"
                    "   - **Call to Action (CTA):** Aceitar o convite de conexão.\n"
                    "   - **Recursos/Materiais de Apoio:** Nenhum neste passo.\n\n"
                    "   **Passo 3:**\n"
                    "   - **Canal:** Follow-up no LinkedIn (3 dias após conexão, se aceita e sem resposta ao email)\n"
                    "   - **Objetivo Específico:** Gerar engajamento e oferecer mais valor.\n"
                    "   - **Principais Tópicos/Argumentos:** Compartilhar artigo/insight relevante sobre otimização para empresas em expansão; reiterar a proposta de valor de forma sutil.\n"
                    "   - **Pergunta(s) Chave:** 'Este artigo sobre [tópico relevante] pode ser útil. Que tipo de estratégias de otimização vocês têm achado mais eficazes durante a expansão?'\n"
                    "   - **Call to Action (CTA):** 'Se estiver aberto a uma conversa rápida sobre como Nossas Soluções Incríveis de IA podem endereçar alguns desses pontos, me avise.'\n"
                    "   - **Recursos/Materiais de Apoio:** Link para o artigo ou insight compartilhado.\n\n"
                    "**4. Indicadores de Engajamento a Monitorar:**\n"
                    "- Abertura do email inicial e cliques no link do estudo de caso.\n"
                    "- Aceitação do convite de conexão no LinkedIn.\n"
                    "- Respostas às mensagens (email ou LinkedIn).\n"
                    "- Visitas ao site da nossa empresa (se o tráfego puder ser rastreado).\n"
                    "- Perguntas sobre o estudo de caso ou os insights compartilhados.\n\n"
                    "**5. Pontos de Atenção/Possíveis Obstáculos:**\n"
                    "- Carlos Mendes pode estar extremamente ocupado devido à expansão.\n"
                    "- Pode haver ceticismo em relação ao ROI real da IA ou preocupações com a complexidade da implementação (lembrar que ele valoriza 'integração fácil').\n"
                    "- A empresa pode já ter uma solução interna ou um fornecedor preferido.\n"
                    "- Resistência geral à mudança ou a novas ferramentas se a equipe estiver sobrecarregada.\n\n"
                    "**6. Próximos Passos Sugeridos (se o contato inicial for bem-sucedido):**\n"
                    "- Agendar a call exploratória (15-20 minutos).\n"
                    "- Preparar perguntas específicas para a call com base nas dores e no perfil da persona para aprofundar o diagnóstico.\n"
                    "- Se possível, antes da call, enviar um breve questionário de diagnóstico (1-3 perguntas) para otimizar o tempo da conversa."
                )
            return "Resposta padrão do mock."

    print("Running mock test for DetailedApproachPlanAgent...")
    mock_llm = MockLLMClient()
    agent = DetailedApproachPlanAgent(
        name="DetailedApproachPlanAgent",
        description="Creates a detailed approach plan.",
        llm_client=mock_llm
    )

    test_lead_analysis = "Empresa Exemplo (TI, Médio Porte). Foco em otimizar processos."
    test_persona_profile = "Carlos Mendes, Diretor de Operações. Busca eficiência, ROI, integração fácil."
    test_deepened_pain_points = "Dor: Processos manuais. Pergunta: Como impacta o tempo? Dor: Integração. Pergunta: Preocupações?"
    test_final_action_plan = (
        "**Nome da Estratégia Final:** Eficiência Consultiva com Foco no Impacto da Expansão\n"
        "**Principal Ângulo/Gancho:** Ajudar Carlos Mendes com desafios de eficiência na expansão.\n"
        "**Sequência de Canais e Ações:** 1. Email personalizado. 2. Conexão LinkedIn. 3. Follow-up LinkedIn.\n"
        "**Pergunta de Abertura Principal:** 'Carlos, com a expansão, como priorizam otimização?'"
    )
    test_product_service = "Nossas Soluções Incríveis de IA"
    test_lead_url = "http://www.empresaexemplo.com"

    input_data = DetailedApproachPlanInput(
        lead_analysis=test_lead_analysis,
        persona_profile=test_persona_profile,
        deepened_pain_points=test_deepened_pain_points,
        final_action_plan_text=test_final_action_plan,
        product_service_offered=test_product_service,
        lead_url=test_lead_url
    )

    output = agent.process(input_data)

    print(f"Detailed Approach Plan Text: \n{output.detailed_approach_plan_text}")
    if output.error_message:
        print(f"Error: {output.error_message}")

    assert "PLANO DE ABORDAGEM DETALHADO:" in output.detailed_approach_plan_text
    assert "Carlos Mendes" in output.detailed_approach_plan_text
    assert "Nossas Soluções Incríveis de IA" in output.detailed_approach_plan_text
    assert "Passo 1:" in output.detailed_approach_plan_text
    assert "Passo 2:" in output.detailed_approach_plan_text
    assert output.error_message is None
    print("Mock test completed.")
