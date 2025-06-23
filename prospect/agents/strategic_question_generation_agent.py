from typing import Optional, List, Dict
from pydantic import BaseModel, Field

from .base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase, LLMResponse

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class StrategicQuestionGenerationInput(BaseModel):
    lead_analysis: str
    persona_profile: str
    deepened_pain_points: str # JSON string from PainPointDeepeningAgent
    # product_service_info: Optional[str] = None # Not currently used in prompt
    # value_propositions: Optional[List[str]] = Field(default_factory=list) # Not currently used in prompt


# Updated Pydantic Output Model
class StrategicQuestionGenerationOutput(BaseModel):
    generated_questions: List[str] = Field(default_factory=list, description="Lista de 3-5 perguntas estratégicas, abertas.")
    question_category_map: Dict[str, str] = Field(default_factory=dict,
                                                  description="Mapeia cada pergunta gerada à sua categoria estratégica (ex: 'Desafio Principal', 'Visão de Futuro').")
    overall_questioning_strategy_summary: Optional[str] = Field(default=None,
                                                               description="Breve resumo da lógica ou objetivo estratégico por trás do conjunto de perguntas formuladas.")
    error_message: Optional[str] = None

class StrategicQuestionGenerationAgent(BaseAgent[StrategicQuestionGenerationInput, StrategicQuestionGenerationOutput]):
    def __init__(self, name: str, description: str, llm_client: Optional[LLMClientBase] = None, **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: StrategicQuestionGenerationInput) -> StrategicQuestionGenerationOutput:
        error_message = None
        self.logger.info(f"❓ STRATEGIC QUESTION GENERATION AGENT STARTING...")
        self.logger.debug(f"📊 Input data: analysis_len={len(input_data.lead_analysis)}, persona_len={len(input_data.persona_profile)}, pain_points_len={len(input_data.deepened_pain_points)}")

        try:
            # Truncate inputs
            prompt_fixed_overhead = 4000 # Estimate for fixed parts of the prompt and JSON structure
            available_for_dynamic = GEMINI_TEXT_INPUT_TRUNCATE_CHARS - prompt_fixed_overhead

            tr_lead_analysis = self._truncate_text(input_data.lead_analysis, int(available_for_dynamic * 0.30))
            tr_persona_profile = self._truncate_text(input_data.persona_profile, int(available_for_dynamic * 0.30))
            # Ensure deepened_pain_points (JSON string) is also truncated if very long
            tr_deepened_pain_points = self._truncate_text(input_data.deepened_pain_points, int(available_for_dynamic * 0.40))

            # Refined prompt_template
            prompt_template = """
                Você é um Coach de Vendas Estratégicas e Especialista em Discovery Calls, com profundo conhecimento do mercado B2B brasileiro.
                Sua missão é formular de 3 a 5 perguntas estratégicas, abertas e instigantes, que vão ALÉM das perguntas investigativas já contidas nos "PONTOS DE DOR JÁ MAPEADOS".
                Estas novas perguntas devem ajudar um vendedor a:
                -   Validar e aprofundar a compreensão das necessidades e desafios da persona.
                -   Incentivar a persona a refletir sobre a visão de longo prazo da empresa.
                -   Explorar as implicações mais amplas dos desafios atuais (além do impacto imediato).
                -   Descobrir objetivos, aspirações ou preocupações ainda não explicitamente mencionadas.
                -   Preparar o terreno para apresentar soluções de forma consultiva.
                -   Serem formuladas considerando as nuances da comunicação empresarial no Brasil (ex: respeito, busca por clareza, construção de relacionamento).

                CONTEXTO DISPONÍVEL:

                1. ANÁLISE DO LEAD:
                   \"\"\"
                   {lead_analysis}
                   \"\"\"

                2. PERFIL DA PERSONA (Tomador de Decisão):
                   \"\"\"
                   {persona_profile}
                   \"\"\"

                3. PONTOS DE DOR JÁ MAPEADOS (E PERGUNTAS INVESTIGATIVAS INICIAIS ASSOCIADAS A ELES):
                   \"\"\"
                   {deepened_pain_points}
                   \"\"\"

                INSTRUÇÕES PARA AS PERGUNTAS ESTRATÉGICAS:
                1.  Revise TODO o contexto para identificar lacunas de informação ou áreas para exploração mais profunda.
                2.  NÃO REPITA ou reformule superficialmente as perguntas já existentes nos "PONTOS DE DOR JÁ MAPEADOS". Crie perguntas genuinamente NOVAS e mais ESTRATÉGICAS.
                3.  As perguntas devem ser ABERTAS (incentivando respostas elaboradas, não "sim/não"). Use preferencialmente "Como...", "Quais são os impactos de...", "De que forma...", "Qual sua visão sobre...". Evite perguntas que comecem com "Você acha que..." ou que sugiram a resposta.
                4.  As perguntas devem ser NEUTRAS, focadas no cliente, e não devem vender explicitamente nenhuma solução neste momento.
                5.  Para cada pergunta em `generated_questions`, atribua uma categoria correspondente em `question_category_map` que justifique seu propósito. Exemplos de Categorias: "Desafio Principal e Impacto", "Processo de Decisão e Influenciadores", "Visão de Futuro e Metas de Longo Prazo", "Critérios para Solução Ideal", "Riscos e Preocupações Atuais", "Ambiente Competitivo e Diferenciais", "Critérios de Sucesso e Métricas".
                6.  Forneça um breve resumo da estratégia geral por trás do conjunto de perguntas que você formulou no campo `overall_questioning_strategy_summary`.

                FORMATO DA RESPOSTA:
                Responda EXCLUSIVAMENTE com um objeto JSON válido, seguindo o schema e as descrições de campo abaixo. Não inclua NENHUM texto, explicação, ou markdown (como ```json) antes ou depois do objeto JSON.

                SCHEMA JSON ESPERADO:
                {{
                  "generated_questions": [
                    "string - Primeira pergunta estratégica aberta e concisa.",
                    "string - Segunda pergunta estratégica aberta e concisa."
                    // Inclua de 3 a 5 perguntas no total.
                  ],
                  "question_category_map": {{ // Dicionário mapeando CADA pergunta em "generated_questions" à sua categoria. A chave deve ser a pergunta EXATA.
                    "Primeira pergunta estratégica aberta e concisa.": "string - Categoria da Pergunta (ex: Desafio Principal e Impacto, Visão de Futuro e Metas de Longo Prazo)",
                    "Segunda pergunta estratégica aberta e concisa.": "string - Categoria da Pergunta"
                    // ... e assim por diante para cada pergunta em "generated_questions".
                  }},
                  "overall_questioning_strategy_summary": "string | null - Breve resumo (1-2 frases) da lógica ou objetivo estratégico por trás do conjunto de perguntas formuladas (o que se espera descobrir ou validar com elas). Use null se não houver um resumo específico ou se for autoexplicativo."
                }}
            """

            formatted_prompt = prompt_template.format(
                lead_analysis=tr_lead_analysis,
                persona_profile=tr_persona_profile,
                deepened_pain_points=tr_deepened_pain_points
            )
            self.logger.debug(f"Prompt for {self.name} (length: {len(formatted_prompt)}):\n{formatted_prompt[:600]}...")

            llm_response: Optional[LLMResponse] = self.generate_llm_response(formatted_prompt)

            if not llm_response or not llm_response.content:
                self.logger.error(f"❌ LLM call returned no response for {self.name}")
                return StrategicQuestionGenerationOutput(error_message="LLM call returned no response.")

            llm_response_str = llm_response.content
            self.logger.debug(f"LLM response received for {self.name} (length: {len(llm_response_str)}). Attempting to parse.")
            parsed_output = self.parse_llm_json_response(llm_response_str, StrategicQuestionGenerationOutput)
            
            if parsed_output.error_message:
                 self.logger.warning(f"⚠️ {self.name} JSON parsing/validation failed. Error: {parsed_output.error_message}. Raw response snippet: {llm_response_str[:500]}")
                 return parsed_output # Return object with error message set

            # Additional validation for question_category_map consistency
            if parsed_output.generated_questions and not parsed_output.question_category_map:
                self.logger.warning(f"⚠️ {self.name}: LLM generated questions but question_category_map is empty. Questions might lack categorization.")
            elif parsed_output.generated_questions and (len(parsed_output.question_category_map) != len(parsed_output.generated_questions) or \
                 not all(q in parsed_output.question_category_map for q in parsed_output.generated_questions)):
                 self.logger.warning(f"⚠️ {self.name}: Mismatch or inconsistency between generated_questions and question_category_map keys. LLM output may need review.")
                 # Potentially set an error or try to reconcile, but for now, just log.

            self.logger.info(f"✅ Strategic questions generated by {self.name}: {len(parsed_output.generated_questions)} questions.")
            return parsed_output

        except Exception as e:
            self.logger.error(f"❌ An unexpected error occurred in {self.name}: {e}", exc_info=True)
            return StrategicQuestionGenerationOutput(error_message=f"An unexpected error occurred: {str(e)}")

