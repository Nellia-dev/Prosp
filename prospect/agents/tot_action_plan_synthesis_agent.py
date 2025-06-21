from typing import Optional, List
from pydantic import BaseModel, Field

from .base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase, LLMResponse

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class ToTActionPlanSynthesisInput(BaseModel):
    evaluated_strategies_text: str # Output from ToTStrategyEvaluationAgent
    proposed_strategies_text: str  # Output from ToTStrategyGenerationAgent (for reference)
    current_lead_summary: str    # Original lead summary (for context)
    product_service_info: Optional[str] = None # Added for better context

class ToTActionPlanSynthesisOutput(BaseModel):
    synthesized_action_plan_name: str = Field(
        ...,
        description="Nome conciso e descritivo para o plano de ação sintetizado (ex: Abordagem Consultiva Direta)"
    )
    action_plan_summary: str = Field(
        ...,
        description="Resumo do plano de ação sintetizado, explicando a lógica da combinação ou seleção das estratégias."
    )
    key_steps: List[str] = Field(
        default_factory=list,
        description="Lista de passos chave do plano sintetizado (2-4 passos)."
    )
    primary_communication_channel: str = Field(
        ...,
        description="Principal canal de comunicação para o início da abordagem (Email | LinkedIn | WhatsApp | Phone | Other)."
    )
    recommended_tone_of_voice: str = Field(
        ...,
        description="Tom de voz recomendado (ex: Consultivo e prestativo, Direto e focado em resultados)."
    )
    main_value_proposition_to_highlight: str = Field(
        ...,
        description="Principal proposta de valor a ser destacada neste plano, conectada ao produto/serviço e dores do lead."
    )
    confidence_score: float = Field(
        ...,
        description="Pontuação de confiança (0.0 a 1.0) na eficácia deste plano sintetizado."
    )
    estimated_impact: str = Field(
        ...,
        description="Impacto estimado do plano (Alto | Médio | Baixo)."
    )
    justification_for_synthesis: str = Field(
        ...,
        description="Breve justificativa de por que este plano sintetizado é o ideal, considerando as avaliações das estratégias originais e o perfil do lead."
    )
    error_message: Optional[str] = Field(default=None, description="Mensagem de erro, se houver.")

class ToTActionPlanSynthesisAgent(BaseAgent[ToTActionPlanSynthesisInput, ToTActionPlanSynthesisOutput]):
    def __init__(self, llm_client: Optional[LLMClientBase] = None, **kwargs):
        super().__init__(
            name="ToTActionPlanSynthesisAgent",
            description="Synthesizes a final action plan from evaluated strategies.",
            llm_client=llm_client,
            **kwargs
        )

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
            truncated_summary = self._truncate_text(input_data.current_lead_summary, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 5)
            truncated_product_info = self._truncate_text(input_data.product_service_info or "N/A", GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 5)


            prompt_template = """
                Você é um Estrategista de Vendas B2B Sênior e Sintetizador de Decisões, especialista em consolidar múltiplas opções estratégicas em um único plano de ação ótimo e acionável, com foco no mercado brasileiro.

                Sua tarefa é analisar as estratégias de abordagem avaliadas, o perfil do lead e as informações do produto/serviço para SINTETIZAR O MELHOR PLANO DE AÇÃO ÚNICO.

                INFORMAÇÕES DISPONÍVEIS:

                1.  AVALIAÇÃO DETALHADA DAS ESTRATÉGIAS DE ABORDAGEM (inclui pontos fortes, fracos, melhorias sugeridas e pontuações de confiança):
                    ```json
                    {evaluated_strategies_text}
                    ```

                2.  ESTRATÉGIAS PROPOSTAS ORIGINAIS (para referência, caso precise resgatar alguma ideia original não totalmente refletida na avaliação):
                    ```json
                    {proposed_strategies_text}
                    ```

                3.  RESUMO DO LEAD (perfil do cliente em potencial, dores, necessidades, contexto):
                    ```
                    {current_lead_summary}
                    ```

                4. INFORMAÇÕES SOBRE O PRODUTO/SERVIÇO QUE ESTAMOS OFERECENDO:
                    ```
                    {product_service_info}
                    ```

                INSTRUÇÕES PARA SÍNTESE E FORMATAÇÃO DA SAÍDA:

                1.  **Análise Crítica:** Revise cuidadosamente a `AVALIAÇÃO DETALHADA DAS ESTRATÉGIAS`. Considere os pontos fortes, fracos e, crucialmente, as `melhorias sugeridas` e as `pontuações de confiança` de cada estratégia avaliada.
                2.  **Decisão de Síntese:**
                    *   **Opção A (Melhor Estratégia Refinada):** Se uma estratégia se destaca claramente como superior (alta confiança, bom alinhamento), utilize-a como base, incorporando as `melhorias sugeridas`.
                    *   **Opção B (Combinação Inteligente):** Se múltiplas estratégias têm pontos fortes complementares, combine os melhores elementos delas em um novo plano coeso.
                    *   **Opção C (Nova Abordagem Inspirada):** Em casos raros, se as avaliações indicarem falhas significativas em todas, você pode propor uma variação inspirada nas ideias originais, mas corrigindo as falhas.
                3.  **Foco no Lead e Produto:** O plano sintetizado DEVE ser altamente relevante para o `RESUMO DO LEAD` e destacar como o `INFORMAÇÕES SOBRE O PRODUTO/SERVIÇO` resolve as dores ou atinge os objetivos do lead.
                4.  **Plano Acionável:** Detalhe o plano de ação final nos campos JSON especificados abaixo. Os `key_steps` devem ser concretos e sequenciais.
                5.  **Justificativa Clara:** A `justification_for_synthesis` deve explicar por que o plano escolhido é o melhor, referenciando as avaliações.

                Responda APENAS com um objeto JSON VÁLIDO seguindo RIGOROSAMENTE a estrutura abaixo. NÃO inclua NENHUM texto ou explicação adicional fora do objeto JSON.

                ```json
                {{
                  "synthesized_action_plan_name": "Nome conciso e descritivo para o plano de ação sintetizado (ex: Abordagem Consultiva Direta com Foco em ROI)",
                  "action_plan_summary": "Resumo do plano de ação sintetizado, explicando a lógica da combinação ou seleção das estratégias e como ele se conecta ao lead e produto/serviço.",
                  "key_steps": [
                    "Passo chave 1: Descrição concisa da primeira ação principal (ex: Enviar email personalizado inicial focando na dor X e apresentando brevemente a solução Y).",
                    "Passo chave 2: Descrição concisa da segunda ação principal (ex: Follow-up via LinkedIn após 2 dias, compartilhando um case de sucesso relevante).",
                    "Passo chave 3: Descrição concisa da terceira ação principal (ex: Propor uma chamada rápida de 15 minutos para diagnóstico inicial)."
                  ],
                  "primary_communication_channel": "Email | LinkedIn | WhatsApp | Phone | Other (especificar)",
                  "recommended_tone_of_voice": "Tom de voz recomendado para a comunicação (ex: Consultivo e prestativo, Entusiasmado e inovador, Direto e focado em resultados)",
                  "main_value_proposition_to_highlight": "Principal proposta de valor do nosso produto/serviço a ser destacada neste plano, diretamente ligada às necessidades do lead (ex: Redução de custos operacionais em X% através da automação inteligente).",
                  "confidence_score": 0.0, // Sua estimativa de confiança (0.0 a 1.0) na eficácia deste plano sintetizado
                  "estimated_impact": "Alto | Médio | Baixo", // Impacto potencial esperado no avanço da oportunidade com o lead
                  "justification_for_synthesis": "Justificativa concisa para a escolha desta síntese, referenciando as avaliações das estratégias (ex: 'Este plano combina a alta confiança da Estratégia A com as melhorias sugeridas para o canal da Estratégia B, resultando em uma abordagem mais robusta e direta para o perfil do lead, que valoriza ROI.')"
                }}
                ```
            """

            formatted_prompt = prompt_template.format(
                evaluated_strategies_text=truncated_eval_strategies,
                proposed_strategies_text=truncated_prop_strategies,
                current_lead_summary=truncated_summary,
                product_service_info=truncated_product_info
            )

            llm_response: Optional[LLMResponse] = self.generate_llm_response(formatted_prompt)

            if not llm_response or not llm_response.content:
                self.logger.error("LLM call returned no response.")
                return ToTActionPlanSynthesisOutput(
                    synthesized_action_plan_name="Error",
                    action_plan_summary="LLM did not return a response.",
                    key_steps=[],
                    primary_communication_channel="N/A",
                    recommended_tone_of_voice="N/A",
                    main_value_proposition_to_highlight="N/A",
                    confidence_score=0.0,
                    estimated_impact="Low",
                    justification_for_synthesis="Error in LLM call.",
                    error_message="LLM call returned no response."
                )

            llm_response_str = llm_response.content
            parsed_output = self.parse_llm_json_response(llm_response_str, ToTActionPlanSynthesisOutput)
            
            if parsed_output.error_message:
                self.logger.warning(f"ToTActionPlanSynthesisAgent JSON parsing failed. Raw response: {llm_response_str[:500]}")
                # Return a default error object, as Pydantic v2 won't allow partials
                return ToTActionPlanSynthesisOutput(
                    synthesized_action_plan_name="Parsing Error",
                    action_plan_summary="Failed to parse the action plan summary.",
                    key_steps=[],
                    primary_communication_channel="N/A",
                    recommended_tone_of_voice="N/A",
                    main_value_proposition_to_highlight="N/A",
                    confidence_score=0.0,
                    estimated_impact="Low",
                    justification_for_synthesis="Failed to parse the justification.",
                    error_message=parsed_output.error_message
                )
            
            return parsed_output
        
        except Exception as e:
            self.logger.error(f"An unexpected error occurred in {self.name}: {e}", exc_info=True)
            return ToTActionPlanSynthesisOutput(
                synthesized_action_plan_name="Unexpected Error",
                action_plan_summary=f"An unexpected error occurred: {str(e)}",
                key_steps=[],
                primary_communication_channel="N/A",
                recommended_tone_of_voice="N/A",
                main_value_proposition_to_highlight="N/A",
                confidence_score=0.0,
                estimated_impact="Low",
                justification_for_synthesis="Unexpected error during processing.",
                error_message=f"An unexpected error occurred: {str(e)}"
            )

