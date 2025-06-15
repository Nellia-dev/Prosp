import re
from typing import Optional, List
from pydantic import BaseModel, Field
import json # For mock test

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

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
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)

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


            llm_response_str = self.generate_llm_response(formatted_prompt)

            if not llm_response_str:
                self.logger.error(f"❌ LLM call returned no response for {self.name} for company {input_data.company_name}")
                return ObjectionHandlingOutput(error_message="LLM call returned no response.")

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

if __name__ == '__main__':
    from loguru import logger
    import sys
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str) -> Optional[str]:
            logger.debug(f"MockLLMClient received prompt snippet:\n{prompt[:600]}...")
            # Simulate LLM returning valid JSON based on the refined prompt and new model
            return json.dumps({
                "anticipated_objections": [
                    {
                        "objection_category": "Custo/Orçamento",
                        "potential_objection_statement": "Não temos orçamento para Nossas Soluções Incríveis de IA este trimestre, especialmente com os investimentos da expansão.",
                        "suggested_response_strategy": "Validar a preocupação, focar no ROI e na economia a médio prazo, oferecer opções flexíveis se possível.",
                        "key_talking_points_for_response": [
                            "Entendo a questão orçamentária, Carlos, especialmente em expansão.",
                            "Nossa solução é projetada para gerar economias X e Y em Z meses, otimizando custos que aumentam com a expansão.",
                            "Poderíamos explorar um piloto ou fase inicial para demonstrar o valor rapidamente?"
                        ]
                    },
                    {
                        "objection_category": "Tempo/Urgência",
                        "potential_objection_statement": "Estamos completamente focados em estabilizar as operações da expansão agora. Não temos tempo para um novo projeto como este.",
                        "suggested_response_strategy": "Empatizar, posicionar a solução como um facilitador para os desafios atuais, sugerir início faseado.",
                        "key_talking_points_for_response": [
                            "Compreendo a carga de trabalho atual com a expansão.",
                            "Nossa IA pode aliviar parte dessa pressão operacional, automatizando X e Y.",
                            "Podemos iniciar com um escopo reduzido para demonstrar valor sem sobrecarregar sua equipe?"
                        ]
                    },
                     {
                        "objection_category": "Complexidade/Implementação",
                        "potential_objection_statement": "Isso parece muito complexo de implementar no meio de tudo o que está acontecendo na Empresa Exemplo.",
                        "suggested_response_strategy": "Reforçar facilidade de integração, apresentar casos de implementação rápida, oferecer suporte dedicado.",
                        "key_talking_points_for_response": [
                            "Nossa solução foi projetada para integração ágil, Carlos.",
                            "Muitos clientes veem resultados em poucas semanas.",
                            "Oferecemos um gerente de projeto para garantir uma transição suave."
                        ]
                    }
                ],
                "general_advice_for_objection_handling": "No Brasil, sempre valide a preocupação do lead antes de responder. Construir confiança é chave. Use exemplos e cases de sucesso locais, se possível, para aumentar a credibilidade."
            })

    logger.info("Running mock test for ObjectionHandlingAgent...")
    mock_llm = MockLLMClient(api_key="mock_llm_key")
    agent = ObjectionHandlingAgent(
        name="TestObjectionHandlingAgent",
        description="Test Agent for Objection Handling",
        llm_client=mock_llm
    )

    test_detailed_plan = "Plano focado em email para Carlos Mendes sobre eficiência com IA na Empresa Exemplo, devido à expansão. CTA: call de 15 min."
    test_persona_profile = "Carlos Mendes, Diretor de Operações da Empresa Exemplo. Busca eficiência, ROI, integração fácil. Preocupado com complexidade. Comunicação direta."
    test_product_service = "Nossas Soluções Incríveis de IA para Automação"
    test_company_name = "Empresa Exemplo"

    input_data = ObjectionHandlingInput(
        detailed_approach_plan_text=test_detailed_plan,
        persona_profile=test_persona_profile,
        product_service_offered=test_product_service,
        company_name=test_company_name
    )

    output = agent.process(input_data)

    if output.error_message:
        logger.error(f"Error: {output.error_message}")
    else:
        logger.success("ObjectionHandlingAgent processed successfully.")
        logger.info(f"Anticipated Objections: {len(output.anticipated_objections)}")
        for i, obj_resp in enumerate(output.anticipated_objections):
            logger.info(f"  Objection {i+1}: [{obj_resp.objection_category}] {obj_resp.potential_objection_statement}")
            logger.info(f"    Strategy: {obj_resp.suggested_response_strategy}")
            logger.info(f"    Talking Points: {obj_resp.key_talking_points_for_response}")
        logger.info(f"General Advice: {output.general_advice_for_objection_handling}")


    assert output.error_message is None
    assert len(output.anticipated_objections) == 3
    assert output.anticipated_objections[0].objection_category == "Custo/Orçamento"
    assert "Carlos" in output.anticipated_objections[0].potential_objection_statement
    assert len(output.anticipated_objections[0].key_talking_points_for_response) > 0
    assert output.general_advice_for_objection_handling is not None and "Brasil" in output.general_advice_for_objection_handling

    logger.info("\nMock test for ObjectionHandlingAgent completed successfully.")

```
