from typing import Optional, List
from pydantic import BaseModel, Field

from .base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase, LLMResponse

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
    def __init__(self, llm_client: Optional[LLMClientBase] = None, **kwargs):
        super().__init__(
            name="ToTStrategyEvaluationAgent",
            description="Evaluates Tree-of-Thought strategies critically.",
            llm_client=llm_client,
            **kwargs
        )

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

            llm_response: Optional[LLMResponse] = self.generate_llm_response(formatted_prompt)

            if not llm_response or not llm_response.content:
                self.logger.error("LLM call returned no response.")
                return ToTStrategyEvaluationOutput(evaluated_strategies=[], error_message="LLM call returned no response.")

            llm_response_str = llm_response.content
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
            return ToTStrategyEvaluationOutput(evaluated_strategies=[], error_message=f"An unexpected error occurred: {str(e)}")

