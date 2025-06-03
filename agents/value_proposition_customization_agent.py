from typing import Optional
from pydantic import BaseModel

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class ValuePropositionCustomizationInput(BaseModel):
    lead_analysis: str
    persona_profile: str
    deepened_pain_points: str # Contains specific pains and investigative questions
    buying_triggers_report: str # Contains identified buying signals
    product_service_offered: str # The user's product/service
    company_name: str # Name of the lead's company

class CustomValuePropModel(BaseModel):
    title: str
    connection_to_pain_or_trigger: str
    key_benefit: str
    differentiation_factor: str
    call_to_value: str # Impactful phrase

class ValuePropositionCustomizationOutput(BaseModel):
    custom_propositions: List[CustomValuePropModel] = Field(default_factory=list)
    error_message: Optional[str] = None

class ValuePropositionCustomizationAgent(BaseAgent[ValuePropositionCustomizationInput, ValuePropositionCustomizationOutput]):
    def __init__(self, llm_client: LLMClientBase):
        super().__init__(llm_client)
        self.name = "ValuePropositionCustomizationAgent"

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: ValuePropositionCustomizationInput) -> ValuePropositionCustomizationOutput:
        customized_value_propositions_text = ""
        error_message = None

        try:
            # Truncate inputs, giving more space to pains and triggers
            tr_analysis = self._truncate_text(input_data.lead_analysis, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 5)
            tr_persona = self._truncate_text(input_data.persona_profile, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 5)
            tr_pains = self._truncate_text(input_data.deepened_pain_points, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 4)
            tr_triggers = self._truncate_text(input_data.buying_triggers_report, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 4)
            
            # Extract persona_fictional_name from persona_profile for the prompt
            persona_fictional_name = "a persona" 
            try:
                # A simple regex to find a name like pattern (e.g., "Carlos Mendes,")
                match = re.search(r"([A-Za-zÀ-ÖØ-öø-ÿ\s]+),", input_data.persona_profile)
                if match:
                    persona_fictional_name = match.group(1).strip()
            except Exception:
                pass # Stick to default if regex fails

            prompt_template = """
                Você é um Especialista em Marketing de Produto B2B, focado em adaptar propostas de valor para máxima ressonância com o cliente.
                Seu objetivo é criar 2-3 propostas de valor altamente personalizadas para {persona_fictional_name} da {company_name}, conectando o {product_service_offered} diretamente aos seus pontos de dor, gatilhos de compra e contexto da empresa.

                ANÁLISE DO LEAD:
                {lead_analysis}

                PERFIL DA PERSONA ({persona_fictional_name}):
                {persona_profile}

                PONTOS DE DOR APROFUNDADOS (incluindo perguntas investigativas):
                {deepened_pain_points}

                RELATÓRIO DE GATILHOS DE COMPRA IDENTIFICADOS:
                {buying_triggers_report}

                PRODUTO/SERVIÇO OFERECIDO: {product_service_offered}
                EMPRESA DO LEAD: {company_name}

                INSTRUÇÕES:
                Crie de 2 a 3 propostas de valor altamente personalizadas. Para cada proposta:
                1.  **title**: Um nome curto e impactante para a PV.
                2.  **connection_to_pain_or_trigger**: Explique como o {product_service_offered} aborda um ponto de dor específico de {persona_fictional_name} ou se alinha a um gatilho de compra identificado para a {company_name}. Use linguagem da persona e da empresa.
                3.  **key_benefit**: Destaque o resultado ou benefício mais importante que {persona_fictional_name} obterá. Seja específico e, se possível, quantificável (mesmo que estimado).
                4.  **differentiation_factor**: Mencione sutilmente um aspecto único do {product_service_offered} que o torna a melhor escolha para ESTE cenário.
                5.  **call_to_value**: Uma frase curta que resume o valor e convida à reflexão ou próxima etapa.

                Responda APENAS com um objeto JSON com a seguinte estrutura:
                {{
                    "custom_propositions": [
                        {{
                            "title": "Título da Proposta de Valor 1 (string)",
                            "connection_to_pain_or_trigger": "Conexão da PV1 com dor/gatilho (string)",
                            "key_benefit": "Benefício principal da PV1 (string)",
                            "differentiation_factor": "Diferencial chave da PV1 (string)",
                            "call_to_value": "Frase de impacto/Call to Value da PV1 (string)"
                        }}
                        // ... mais propostas de valor
                    ]
                }}
                Não inclua nenhuma explicação ou texto adicional fora do objeto JSON.
            """

            formatted_prompt = prompt_template.format(
                lead_analysis=tr_analysis,
                persona_profile=tr_persona,
                deepened_pain_points=tr_pains,
                buying_triggers_report=tr_triggers,
                product_service_offered=input_data.product_service_offered,
                company_name=input_data.company_name,
                persona_fictional_name=persona_fictional_name
            )

            llm_response_str = self.generate_llm_response(formatted_prompt)

            if not llm_response_str:
                return ValuePropositionCustomizationOutput(error_message="LLM call returned no response.")

            parsed_output = self.parse_llm_json_response(llm_response_str, ValuePropositionCustomizationOutput)
            
            if parsed_output.error_message:
                 self.logger.warning(f"ValuePropositionCustomizationAgent JSON parsing failed. Raw response: {llm_response_str[:500]}")

            return parsed_output

        except Exception as e:
            self.logger.error(f"An unexpected error occurred in {self.name}: {e}")
            import traceback
            import re # Ensure re is imported for the persona name extraction
            traceback.print_exc()
            return ValuePropositionCustomizationOutput(error_message=f"An unexpected error occurred: {str(e)}")

if __name__ == '__main__':
    import re # Ensure re is imported for the main block too
    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str) -> Optional[str]:
            if "PROPOSTAS DE VALOR PERSONALIZADAS PARA" in prompt:
                return (
                    "PROPOSTAS DE VALOR PERSONALIZADAS PARA Empresa Exemplo:\n\n"
                    "**Proposta de Valor 1: Escale a Expansão da Empresa Exemplo com Eficiência Impulsionada por IA**\n"
                    "- **Conexão Direta:** Carlos, com a recente expansão da Empresa Exemplo para o mercado LATAM (gatilho identificado) e seu foco em otimizar processos (dor da persona), Nossas Soluções Incríveis de IA são projetadas para garantir que suas operações escalem suavemente, sem os gargalos que frequentemente acompanham o crescimento rápido.\n"
                    "- **Benefício Principal:** Permita que sua equipe na Empresa Exemplo se concentre na inovação e no atendimento ao cliente, enquanto nossa IA automatiza até X% dos processos operacionais repetitivos, reduzindo custos em Y% e melhorando o tempo de resposta em Z% durante este período crítico de expansão.\n"
                    "- **Diferencial Chave:** Nossa plataforma de IA não só automatiza, mas aprende e se adapta continuamente aos fluxos de trabalho da Empresa Exemplo, garantindo otimizações crescentes e insights preditivos que outras ferramentas genéricas não oferecem.\n"
                    "- **Frase de Impacto (Call to Value):** 'Carlos, vamos transformar os desafios da expansão da Empresa Exemplo em uma vantagem competitiva com operações mais inteligentes?'\n\n"
                    "**Proposta de Valor 2: Modernize as Operações da Empresa Exemplo com IA de Fácil Integração e ROI Comprovado**\n"
                    "- **Conexão Direta:** Sabemos que, como Diretor de Operações (perfil da persona), você valoriza ROI claro e integração fácil, especialmente ao considerar a modernização da pilha tecnológica da Empresa Exemplo (gatilho e dor identificados). Nossas Soluções Incríveis de IA foram desenvolvidas pensando nisso.\n"
                    "- **Benefício Principal:** Implemente Nossas Soluções Incríveis de IA em semanas, não meses, e comece a ver um retorno sobre o investimento em menos de [tempo específico, ex: 6 meses] através da redução de erros manuais, otimização do uso de recursos e melhor tomada de decisão baseada em dados precisos para a Empresa Exemplo.\n"
                    "- **Diferencial Chave:** Ao contrário de soluções complexas, nossa IA oferece uma interface intuitiva e dashboards personalizados para a Empresa Exemplo, permitindo que sua equipe aproveite o poder da IA sem a necessidade de conhecimento técnico especializado, com suporte dedicado para garantir uma transição suave.\n"
                    "- **Frase de Impacto (Call to Value):** 'Pronto para modernizar as operações da Empresa Exemplo com uma solução de IA que entrega resultados rápidos e se integra perfeitamente ao seu ecossistema, Carlos?'"
                )
            return "Resposta padrão do mock."

    print("Running mock test for ValuePropositionCustomizationAgent...")
    mock_llm = MockLLMClient()
    agent = ValuePropositionCustomizationAgent(llm_client=mock_llm)

    test_lead_analysis = "Empresa Exemplo (TI, Médio Porte). Foco em otimizar processos. Expansão recente."
    test_persona_profile = "Carlos Mendes, Diretor de Operações da Empresa Exemplo. Busca eficiência, ROI, integração fácil."
    test_deepened_pain_points = "Dor: Processos manuais que não escalam com a expansão. Dor: Preocupação com complexidade de novas ferramentas."
    test_buying_triggers = "Gatilho: Anúncio de Expansão para LATAM. Gatilho: Busca por modernizar pilha tecnológica. Gatilho: Novo COO (Carlos Mendes) nomeado."
    test_product_service = "Nossas Soluções Incríveis de IA"
    test_company_name = "Empresa Exemplo"

    input_data = ValuePropositionCustomizationInput(
        lead_analysis=test_lead_analysis,
        persona_profile=test_persona_profile,
        deepened_pain_points=test_deepened_pain_points,
        buying_triggers_report=test_buying_triggers,
        product_service_offered=test_product_service,
        company_name=test_company_name
    )

    output = agent.process(input_data)

    print(f"Customized Value Propositions Text: \n{output.customized_value_propositions_text}")
    if output.error_message:
        print(f"Error: {output.error_message}")

    assert "PROPOSTAS DE VALOR PERSONALIZADAS PARA Empresa Exemplo:" in output.customized_value_propositions_text
    assert "Carlos" in output.customized_value_propositions_text # Persona name
    assert "Empresa Exemplo" in output.customized_value_propositions_text # Company name
    assert "Nossas Soluções Incríveis de IA" in output.customized_value_propositions_text
    assert "Proposta de Valor 1:" in output.customized_value_propositions_text
    assert "Proposta de Valor 2:" in output.customized_value_propositions_text
    assert output.error_message is None
    print("Mock test completed.")
