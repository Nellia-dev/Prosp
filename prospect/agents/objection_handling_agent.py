import re
from typing import Optional, List
from pydantic import BaseModel, Field

from .base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase, LLMResponse

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class ObjectionHandlingInput(BaseModel):
    detailed_approach_plan_text: str # Provides context on what is being proposed
    persona_profile: str # Contains persona_fictional_name implicitly
    product_service_offered: str
    company_name: str # Name of the lead's company

# Updated Pydantic Models based on subtask's ideal JSON
class ObjectionResponse(BaseModel): # Renamed from ObjectionResponseModel for clarity
    objection_category: str = Field(default="Outro", description="Ex: Preço, Concorrência, Necessidade/Fit, Urgência/Timing, Confiança/Autoridade, Complexidade/Implementação, Outro")
    potential_objection_statement: str
    suggested_response_strategy: str # Renamed from response_strategy
    key_talking_points_for_response: List[str] = Field(default_factory=list)

class ObjectionHandlingOutput(BaseModel):
    anticipated_objections: List[ObjectionResponse] = Field(default_factory=list)
    general_advice_for_objection_handling: Optional[str] = None
    error_message: Optional[str] = None

class ObjectionHandlingAgent(BaseAgent[ObjectionHandlingInput, ObjectionHandlingOutput]):
    def __init__(self, llm_client: Optional[LLMClientBase] = None, **kwargs):
        super().__init__(
            name="ObjectionHandlingAgent",
            description="Anticipates and prepares responses for potential B2B sales objections.",
            llm_client=llm_client,
            **kwargs
        )

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: ObjectionHandlingInput) -> ObjectionHandlingOutput:
        error_message = None
        self.logger.info(f"🛡️ OBJECTION HANDLING AGENT STARTING for {input_data.company_name}")

        try:
            # Truncate inputs
            # Approximate character allocation
            prompt_fixed_overhead = 3500
            available_for_dynamic = GEMINI_TEXT_INPUT_TRUNCATE_CHARS - prompt_fixed_overhead
            
            tr_plan = self._truncate_text(input_data.detailed_approach_plan_text, int(available_for_dynamic * 0.4))
            tr_persona = self._truncate_text(input_data.persona_profile, int(available_for_dynamic * 0.4))
            # product_service_offered and company_name are usually short

            persona_fictional_name = "a persona"
            try:
                # Attempt to extract a name-like pattern from the beginning of the persona_profile
                # This assumes the name is somewhat at the beginning and might be followed by a comma or is the whole line.
                first_line_of_persona = input_data.persona_profile.splitlines()[0] if input_data.persona_profile else ""
                match = re.search(r"^([A-Za-zÀ-ÖØ-öø-ÿ\s]+)(?:,|$)", first_line_of_persona)
                if match:
                    extracted_name = match.group(1).strip()
                    # Basic check to avoid taking a whole sentence if no comma
                    if len(extracted_name.split()) <= 4 and extracted_name:
                        persona_fictional_name = extracted_name
            except Exception:
                self.logger.warning(f"Could not parse persona_fictional_name from persona_profile string for {input_data.company_name}. Using default.")

            # Refined prompt_template
            prompt_template = """
                Você é um Estrategista de Vendas B2B Sênior e Coach de Vendas, com vasta experiência em antecipar e superar objeções no mercado brasileiro.
                Sua tarefa é analisar o contexto do lead e do plano de abordagem para {persona_fictional_name} da empresa {company_name}, e preparar um framework de tratamento de objeções. O produto oferecido é: "{product_service_offered}".

                CONTEXTO PARA ANÁLISE DE OBJEÇÕES:

                1. PLANO DE ABORDAGEM DETALHADO (proposta de valor e como será o contato):
                   \"\"\"
                   {detailed_approach_plan_text}
                   \"\"\"

                2. PERFIL DA PERSONA (para entender suas prioridades, dores e estilo):
                   \"\"\"
                   {persona_profile}
                   \"\"\"
                
                EMPRESA DO LEAD: {company_name}
                NOSSO PRODUTO/SERVIÇO: {product_service_offered}

                INSTRUÇÕES PARA O FRAMEWORK DE OBJEÇÕES:
                1.  Com base em todo o contexto, antecipe de 3 a 5 objeções POTENCIAIS que {persona_fictional_name} da {company_name} poderia levantar.
                2.  Para cada objeção, forneça os seguintes detalhes:
                    a.  `objection_category`: Classifique a objeção (Exemplos: "Preço", "Concorrência", "Necessidade/Fit", "Urgência/Timing", "Confiança/Autoridade", "Complexidade/Implementação", "Outro").
                    b.  `potential_objection_statement`: Formule a objeção como {persona_fictional_name} poderia verbalizá-la.
                    c.  `suggested_response_strategy`: Descreva a estratégia geral para responder (Exemplos: "Validar e Reforçar Valor com ROI", "Comparar com Concorrente X focado em nosso diferencial Y", "Demonstrar Prova Social e Cases", "Simplificar a Percepção de Complexidade com plano de onboarding").
                    d.  `key_talking_points_for_response`: Liste 2-3 pontos chave ou perguntas para usar na resposta efetiva.
                3.  Forneça um `general_advice_for_objection_handling`: Um conselho geral ou tática proativa para a equipe de vendas ao lidar com objeções neste cenário específico, considerando o contexto brasileiro (Ex: "No Brasil, é crucial validar a preocupação do lead antes de apresentar soluções, focando na construção de confiança mútua.").

                FORMATO DA RESPOSTA:
                Responda EXCLUSIVAMENTE com um objeto JSON válido, seguindo o schema e as descrições de campo abaixo. Não inclua NENHUM texto, explicação, ou markdown (como ```json) antes ou depois do objeto JSON.

                SCHEMA JSON ESPERADO:
                {{
                  "anticipated_objections": [ // Lista de 3-5 objeções antecipadas.
                    {{
                      "objection_category": "string - Categoria da objeção (ex: 'Preço', 'Concorrência', 'Necessidade/Fit', 'Urgência/Timing', 'Confiança/Autoridade', 'Complexidade/Implementação', 'Outro').",
                      "potential_objection_statement": "string - A declaração da objeção como o lead poderia expressá-la.",
                      "suggested_response_strategy": "string - Estratégia concisa para abordar a objeção (ex: 'Empatizar, questionar para aprofundar, depois apresentar case de ROI').",
                      "key_talking_points_for_response": ["string", ...] // Lista de 2-3 pontos chave ou perguntas para a resposta. Lista vazia [] se a estratégia for autoexplicativa.
                    }}
                  ],
                  "general_advice_for_objection_handling": "string | null - Um conselho geral (1-2 frases) ou tática proativa para lidar com objeções neste cenário, considerando o mercado brasileiro. Use null se não houver conselho específico além das respostas."
                }}
            """

            formatted_prompt = prompt_template.format(
                detailed_approach_plan_text=tr_plan,
                persona_profile=tr_persona,
                product_service_offered=input_data.product_service_offered,
                company_name=input_data.company_name,
                persona_fictional_name=persona_fictional_name
            )
            self.logger.debug(f"Prompt for {self.name} (length: {len(formatted_prompt)}):\n{formatted_prompt[:600]}...")


            llm_response: Optional[LLMResponse] = self.generate_llm_response(formatted_prompt)

            if not llm_response or not llm_response.content:
                self.logger.error(f"❌ LLM call returned no response for {self.name} for company {input_data.company_name}")
                return ObjectionHandlingOutput(error_message="LLM call returned no response.")

            llm_response_str = llm_response.content
            self.logger.debug(f"LLM response received for {self.name} (length: {len(llm_response_str)}). Attempting to parse.")
            parsed_output = self.parse_llm_json_response(llm_response_str, ObjectionHandlingOutput)
            
            if parsed_output.error_message:
                 self.logger.warning(f"⚠️ {self.name} JSON parsing/validation failed for {input_data.company_name}. Error: {parsed_output.error_message}. Raw response snippet: {llm_response_str[:500]}")
                 return parsed_output

            self.logger.info(f"✅ Objection handling framework successfully processed for {input_data.company_name}. Objections anticipated: {len(parsed_output.anticipated_objections)}")
            return parsed_output

        except Exception as e:
            self.logger.error(f"❌ An unexpected error occurred in {self.name} for {input_data.company_name}: {e}", exc_info=True)
            return ObjectionHandlingOutput(error_message=f"An unexpected error occurred: {str(e)}")

