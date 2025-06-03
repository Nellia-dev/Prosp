from typing import Optional
from pydantic import BaseModel

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class ObjectionHandlingInput(BaseModel):
    detailed_approach_plan_text: str # Provides context on what is being proposed
    persona_profile: str
    product_service_offered: str
    company_name: str # Name of the lead's company

class ObjectionResponseModel(BaseModel):
    objection: str
    response_strategy: str
    suggested_response: str

class ObjectionHandlingOutput(BaseModel):
    anticipated_objections: List[ObjectionResponseModel] = Field(default_factory=list)
    error_message: Optional[str] = None

class ObjectionHandlingAgent(BaseAgent[ObjectionHandlingInput, ObjectionHandlingOutput]):
    def __init__(self, llm_client: LLMClientBase):
        super().__init__(llm_client)
        self.name = "ObjectionHandlingAgent"

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: ObjectionHandlingInput) -> ObjectionHandlingOutput:
        objection_responses_text = ""
        error_message = None

        try:
            # Truncate inputs
            tr_plan = self._truncate_text(input_data.detailed_approach_plan_text, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 3)
            tr_persona = self._truncate_text(input_data.persona_profile, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 3)

            prompt_template = """
                Você é um Especialista em Treinamento de Vendas, focado em preparação para objeções comuns no ciclo de vendas B2B.
                Seu objetivo é antecipar objeções que a persona ({persona_fictional_name} da {company_name}) possa ter em relação ao {product_service_offered} e ao plano de abordagem, e sugerir respostas eficazes.

                PLANO DE ABORDAGEM DETALHADO (para contextualizar a oferta e o momento):
                {detailed_approach_plan_text}

                PERFIL DA PERSONA (para entender suas prioridades e preocupações):
                {persona_profile}

                EMPRESA DO LEAD: {company_name}
                PRODUTO/SERVIÇO OFERECIDO: {product_service_offered}

                INSTRUÇÕES:
                1.  Com base no perfil da persona, no produto/serviço e no plano de abordagem, identifique de 3 a 5 objeções comuns que {persona_fictional_name} da {company_name} poderia ter.
                2.  Para cada objeção identificada, detalhe:
                    a.  **objection**: A declaração da objeção de forma clara.
                    b.  **response_strategy**: Uma estratégia de resposta sugerida (ex: Validar-Reformular-Responder, Usar Prova Social, Focar no ROI).
                    c.  **suggested_response**: Uma formulação de resposta específica e concisa (1-3 frases).

                Considere objeções relacionadas a Custo/Orçamento, Tempo/Urgência, Concorrência/Solução Atual, Complexidade/Implementação, e Necessidade/Valor.

                Responda APENAS com um objeto JSON com a seguinte estrutura:
                {{
                    "anticipated_objections": [
                        {{
                            "objection": "Declaração da objeção 1 (string)",
                            "response_strategy": "Estratégia de resposta para objeção 1 (string)",
                            "suggested_response": "Sugestão de resposta para objeção 1 (string)"
                        }},
                        {{
                            "objection": "Declaração da objeção 2 (string)",
                            "response_strategy": "Estratégia de resposta para objeção 2 (string)",
                            "suggested_response": "Sugestão de resposta para objeção 2 (string)"
                        }}
                        // ... mais objeções
                    ]
                }}
                Não inclua nenhuma explicação ou texto adicional fora do objeto JSON.
            """
            # Extract persona_fictional_name from persona_profile for the prompt
            persona_fictional_name = "a persona"
            try:
                match = re.search(r"([A-Za-zÀ-ÖØ-öø-ÿ\s]+),", input_data.persona_profile)
                if match:
                    persona_fictional_name = match.group(1).strip()
            except Exception:
                self.logger.warning("Could not parse persona_fictional_name from persona_profile string.")


            formatted_prompt = prompt_template.format(
                detailed_approach_plan_text=tr_plan,
                persona_profile=tr_persona,
                product_service_offered=input_data.product_service_offered,
                company_name=input_data.company_name,
                persona_fictional_name=persona_fictional_name
            )

            llm_response_str = self.generate_llm_response(formatted_prompt)

            if not llm_response_str:
                return ObjectionHandlingOutput(error_message="LLM call returned no response.")

            parsed_output = self.parse_llm_json_response(llm_response_str, ObjectionHandlingOutput)

            if parsed_output.error_message:
                 self.logger.warning(f"ObjectionHandlingAgent JSON parsing failed. Raw response: {llm_response_str[:500]}")

            return parsed_output

        except Exception as e:
            self.logger.error(f"An unexpected error occurred in {self.name}: {e}")
            import traceback
            import re # Ensure re is imported for the persona name extraction
            traceback.print_exc()
            return ObjectionHandlingOutput(error_message=f"An unexpected error occurred: {str(e)}")

if __name__ == '__main__':
    import re # Ensure re is imported for the main block too
    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str) -> Optional[str]:
            if "PREPARAÇÃO PARA OBJEÇÕES COMUNS:" in prompt:
                return (
                    "PREPARAÇÃO PARA OBJEÇÕES COMUNS:\n\n"
                    "**1. Objeção: Custo / Orçamento**\n"
                    "   - **Declaração:** \"Não temos orçamento para Nossas Soluções Incríveis de IA este trimestre, especialmente com os investimentos da expansão.\"\n"
                    "   - **Estratégia de Resposta:** Validar a preocupação, focar no ROI e na economia a médio prazo, e oferecer opções flexíveis se possível.\n"
                    "   - **Sugestão de Resposta:** \"Entendo perfeitamente, Carlos. Muitas empresas que expandem, como a Empresa Exemplo, ficam de olho no orçamento. Poderíamos explorar como o investimento em Nossas Soluções Incríveis de IA pode, na verdade, gerar economias mensuráveis em X e Y meses, otimizando justamente os custos que tendem a aumentar com a expansão?\"\n\n"
                    "**2. Objeção: Tempo / Urgência (Foco em outras prioridades devido à expansão)**\n"
                    "   - **Declaração:** \"Estamos completamente focados em estabilizar as operações da expansão agora. Não temos tempo para um novo projeto como este.\"\n"
                    "   - **Estratégia de Resposta:** Empatizar com a carga de trabalho, posicionar a solução como um facilitador para os desafios atuais, e sugerir um início faseado ou de baixo impacto.\n"
                    "   - **Sugestão de Resposta:** \"Compreendo que a expansão é a prioridade total. Nossa intenção com Nossas Soluções Incríveis de IA é justamente aliviar parte dessa pressão operacional que a expansão traz, automatizando processos X e Y. Podemos começar com um piloto pequeno em uma área específica para demonstrar valor rapidamente sem sobrecarregar sua equipe?\"\n\n"
                    "**3. Objeção: Complexidade / Implementação (Preocupação da persona com 'integração fácil')**\n"
                    "   - **Declaração:** \"Isso parece muito complexo de implementar no meio de tudo o que está acontecendo na Empresa Exemplo.\"\n"
                    "   - **Estratégia de Resposta:** Reforçar a facilidade de integração (ponto chave da persona), apresentar casos de implementação rápida, e oferecer suporte dedicado.\n"
                    "   - **Sugestão de Resposta:** \"Uma das grandes vantagens de Nossas Soluções Incríveis de IA é a rapidez e facilidade de integração, Carlos. Pensamos nisso justamente para cenários como o da Empresa Exemplo. Muitos de nossos clientes ficam surpresos ao ver os primeiros resultados em poucas semanas, e oferecemos um gerente de projeto dedicado para garantir que tudo corra sem percalços.\"\n\n"
                    "**4. Objeção: Solução Atual / Concorrência**\n"
                    "   - **Declaração:** \"Já temos uma ferramenta que faz algo parecido / Estamos avaliando a Solução Z.\"\n"
                    "   - **Estratégia de Resposta:** Não criticar, mas diferenciar com base nos pontos fortes únicos e no alinhamento com as dores específicas da persona/empresa (eficiência, escalabilidade para expansão).\n"
                    "   - **Sugestão de Resposta:** \"É ótimo que vocês já estejam buscando otimizar! O que clientes como a Empresa Exemplo normalmente descobrem é que Nossas Soluções Incríveis de IA se destacam em [diferencial 1, ex: escalabilidade para expansão] e [diferencial 2, ex: insights preditivos para eficiência], que são particularmente relevantes no seu cenário atual. Poderíamos explorar essas diferenças?\""
                )
            return "Resposta padrão do mock."

    print("Running mock test for ObjectionHandlingAgent...")
    mock_llm = MockLLMClient()
    agent = ObjectionHandlingAgent(llm_client=mock_llm)

    test_detailed_plan = "Plano focado em email para Carlos Mendes sobre eficiência com IA na Empresa Exemplo, devido à expansão."
    test_persona_profile = "Carlos Mendes, Diretor de Operações da Empresa Exemplo. Busca eficiência, ROI, integração fácil. Preocupado com complexidade."
    test_product_service = "Nossas Soluções Incríveis de IA"
    test_company_name = "Empresa Exemplo"

    input_data = ObjectionHandlingInput(
        detailed_approach_plan_text=test_detailed_plan,
        persona_profile=test_persona_profile,
        product_service_offered=test_product_service,
        company_name=test_company_name
    )

    output = agent.process(input_data)

    print(f"Objection Responses Text: \n{output.objection_responses_text}")
    if output.error_message:
        print(f"Error: {output.error_message}")

    assert "PREPARAÇÃO PARA OBJEÇÕES COMUNS:" in output.objection_responses_text
    assert "Carlos" in output.objection_responses_text # Check persona name used
    assert "Empresa Exemplo" in output.objection_responses_text # Check company name used
    assert "Nossas Soluções Incríveis de IA" in output.objection_responses_text
    assert "Custo / Orçamento" in output.objection_responses_text
    assert "Complexidade / Implementação" in output.objection_responses_text
    assert output.error_message is None
    print("Mock test completed.")
