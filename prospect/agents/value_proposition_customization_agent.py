import re # Moved import re to top
from typing import Optional, List
from pydantic import BaseModel, Field

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

class ValuePropositionModel(BaseModel): # Renamed from CustomValuePropModel and updated
    value_proposition_title: str = Field(..., description="Título curto, impactante e direto ao ponto para a proposta de valor.")
    detailed_proposition: str = Field(..., description="Descrição detalhada da proposta de valor, explicando claramente como a solução aborda uma dor/necessidade específica do lead e entrega valor. Deve ser personalizada.")
    key_benefits_highlighted: List[str] = Field(default_factory=list, description="Lista de 2-3 benefícios chave mais relevantes para o lead, idealmente quantificáveis ou de alto impacto (ex: 'Redução de custos operacionais em até 15%', 'Aumento da eficiência da equipe em X horas/semana').")
    target_pain_point_or_trigger: str = Field(..., description="O ponto de dor principal ou gatilho de compra específico do lead que esta proposta de valor visa diretamente endereçar.")
    evidence_or_proof_suggestion: str = Field(..., description="Sugestão de como esta proposta de valor pode ser comprovada ou demonstrada ao lead (ex: 'Apresentar case de estudo da Empresa Y no mesmo setor', 'Oferecer uma demonstração focada na funcionalidade Z', 'Compartilhar um relatório de benchmark da indústria').")

class ValuePropositionCustomizationOutput(BaseModel):
    customized_value_propositions: List[ValuePropositionModel] = Field(default_factory=list) # Renamed field
    error_message: Optional[str] = None

class ValuePropositionCustomizationAgent(BaseAgent[ValuePropositionCustomizationInput, ValuePropositionCustomizationOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)

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
            tr_pains = self._truncate_text(input_data.deepened_pain_points, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 3) # Adjusted allocation
            tr_triggers = self._truncate_text(input_data.buying_triggers_report, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 4) # Adjusted allocation
            tr_product_service = self._truncate_text(input_data.product_service_offered, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 5)
            
            persona_fictional_name = "o(a) decisor(a)" # Default
            try:
                match = re.search(r"Nome:\s*([A-Za-zÀ-ÖØ-öø-ÿ\s]+)(?:,|$|\n)", input_data.persona_profile, re.IGNORECASE)
                if not match: # Try matching "([A-Za-zÀ-ÖØ-öø-ÿ\s]+)," as a fallback
                    match = re.search(r"([A-Za-zÀ-ÖØ-öø-ÿ\s]+),", input_data.persona_profile)
                if match:
                    persona_fictional_name = match.group(1).strip()
            except Exception:
                self.logger.warning("Regex for persona name extraction failed or persona_profile is not as expected.")


            prompt_template = """
                Você é um Estrategista de Marketing B2B especialista em criar propostas de valor (VPs) altamente personalizadas e atraentes para o mercado brasileiro.
                Sua tarefa é gerar 2-3 propostas de valor distintas e customizadas para {persona_fictional_name} da empresa {company_name}, utilizando as informações fornecidas. Cada VP deve ser única e focar em diferentes ângulos ou benefícios, sempre conectando o produto/serviço {product_service_offered} às necessidades específicas do lead.

                INFORMAÇÕES DE CONTEXTO:

                1.  ANÁLISE DO LEAD E EMPRESA ({company_name}):
                    ```
                    {lead_analysis}
                    ```

                2.  PERFIL DA PERSONA ({persona_fictional_name}):
                    ```
                    {persona_profile}
                    ```

                3.  PONTOS DE DOR APROFUNDADOS DO LEAD:
                    ```
                    {deepened_pain_points}
                    ```

                4.  RELATÓRIO DE GATILHOS DE COMPRA IDENTIFICADOS:
                    ```
                    {buying_triggers_report}
                    ```

                5.  NOSSO PRODUTO/SERVIÇO OFERECIDO:
                    ```
                    {product_service_offered}
                    ```

                INSTRUÇÕES PARA CRIAÇÃO DAS PROPOSTAS DE VALOR:

                1.  **Personalização Extrema**: Cada VP deve ser meticulosamente adaptada para {persona_fictional_name} e {company_name}. Use o nome da persona e da empresa na descrição da VP quando apropriado para aumentar a personalização.
                2.  **Conexão Clara**: Conecte explicitamente os benefícios da solução ({product_service_offered}) a um `target_pain_point_or_trigger` relevante.
                3.  **Benefícios Quantificáveis**: Sempre que possível, os `key_benefits_highlighted` devem ser quantificáveis (ex: "redução de X%", "aumento de Y horas/semana") ou de alto impacto percebido.
                4.  **Distinção entre VPs**: Crie 2 a 3 VPs que sejam significativamente diferentes em seu ângulo principal, nos benefícios destacados ou no ponto de dor que abordam.
                5.  **Ressonância com Mercado Brasileiro**: Formule as VPs de maneira que ressoem com a cultura de negócios brasileira (ex: foco em parceria, resultados tangíveis, inovação com pragmatismo).
                6.  **Sugestão de Evidência**: Para cada VP, sugira uma forma prática e relevante de comprovar o valor prometido.

                Responda APENAS com um objeto JSON VÁLIDO seguindo RIGOROSAMENTE a estrutura abaixo. NÃO inclua NENHUM texto ou explicação adicional fora do objeto JSON.

                ```json
                {{
                    "customized_value_propositions": [
                        {{
                            "value_proposition_title": "Título Curto e Impactante da Proposta de Valor (ex: Otimize X em Y% para {company_name})",
                            "detailed_proposition": "Descrição detalhada e personalizada da proposta de valor, explicando como {product_service_offered} resolve a dor Z de {persona_fictional_name} na {company_name}, e como isso se traduz em valor real. (Use 2-3 frases).",
                            "key_benefits_highlighted": [
                                "Benefício chave 1 (ex: Aumento de X% na eficiência operacional)",
                                "Benefício chave 2 (ex: Redução de custos com Y em Z%)",
                                "Benefício chave 3 (ex: Melhoria na tomada de decisão através de insights acionáveis)"
                            ],
                            "target_pain_point_or_trigger": "Ponto de dor específico ou gatilho de compra que esta VP aborda (ex: 'Processos manuais que não escalam com a expansão da {company_name}', 'Necessidade de modernizar a pilha tecnológica para suportar o crescimento').",
                            "evidence_or_proof_suggestion": "Sugestão de como comprovar esta VP (ex: 'Apresentar case de estudo da Empresa Alfa no mesmo setor demonstrando redução de custos', 'Oferecer uma demonstração personalizada focada na automação do processo X para {persona_fictional_name}', 'Compartilhar um white paper sobre como a IA otimiza Y para empresas como a {company_name}')."
                        }}
                        // ... mais 1 ou 2 propostas de valor distintas, se aplicável
                    ]
                }}
                ```
            """

            formatted_prompt = prompt_template.format(
                lead_analysis=tr_analysis,
                persona_profile=tr_persona,
                deepened_pain_points=tr_pains,
                buying_triggers_report=tr_triggers,
                product_service_offered=tr_product_service, # Use truncated version
                company_name=input_data.company_name,
                persona_fictional_name=persona_fictional_name
            )

            llm_response_str = self.generate_llm_response(formatted_prompt, use_gemini_pro_vision=False) # Assuming text-only

            if not llm_response_str:
                self.logger.error("LLM call returned no response.")
                return ValuePropositionCustomizationOutput(error_message="LLM call returned no response.")

            parsed_output = self.parse_llm_json_response(llm_response_str, ValuePropositionCustomizationOutput)
            
            if parsed_output.error_message:
                 self.logger.warning(f"ValuePropositionCustomizationAgent JSON parsing failed. Raw response: {llm_response_str[:500]}")
                 return ValuePropositionCustomizationOutput(
                     customized_value_propositions=parsed_output.customized_value_propositions or [],
                     error_message=parsed_output.error_message
                 )

            return parsed_output

        except Exception as e:
            self.logger.error(f"An unexpected error occurred in {self.name}: {e}", exc_info=True)
            return ValuePropositionCustomizationOutput(error_message=f"An unexpected error occurred: {str(e)}")

if __name__ == '__main__':
    import json

    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str, use_gemini_pro_vision: bool = False) -> Optional[str]:
            # This mock will return a JSON string based on the new structure
            mock_json_response = {
                "customized_value_propositions": [
                    {
                        "value_proposition_title": "Escale a Expansão da Empresa Exemplo com Eficiência Operacional via IA",
                        "detailed_proposition": "Carlos, com a recente expansão da Empresa Exemplo para o mercado LATAM e seu foco em otimizar processos, nossa plataforma de IA foi projetada para garantir que suas operações escalem de forma suave e eficaz, eliminando os gargalos que frequentemente acompanham o crescimento acelerado. Entendemos que, para você na Empresa Exemplo, manter a eficiência durante a expansão é crucial.",
                        "key_benefits_highlighted": [
                            "Automatize até 35% dos processos operacionais repetitivos, liberando sua equipe na Empresa Exemplo para focar em inovação.",
                            "Reduza custos relacionados a erros manuais em até 20% no primeiro ano.",
                            "Melhore o tempo de resposta e processamento em até 40% durante este período crítico de expansão."
                        ],
                        "target_pain_point_or_trigger": "Expansão para LATAM e a necessidade de otimizar processos manuais que não escalam.",
                        "evidence_or_proof_suggestion": "Apresentar um case de estudo da 'Empresa Beta', também do setor de TI, que expandiu suas operações em 50% enquanto reduziu custos operacionais em 15% após implementar nossa IA. Oferecer demo focado em automação de processos de back-office."
                    },
                    {
                        "value_proposition_title": "Modernize as Operações da Empresa Exemplo: IA com ROI Rápido e Integração Simplificada",
                        "detailed_proposition": "Carlos, como Diretor de Operações da Empresa Exemplo, sabemos que você valoriza ROI claro e integração tecnológica sem transtornos, especialmente ao modernizar a stack para suportar o crescimento. Nossa solução de IA foi desenvolvida para entregar exatamente isso, aliviando a preocupação com a complexidade de novas ferramentas.",
                        "key_benefits_highlighted": [
                            "Implementação completa em 4-6 semanas, minimizando a disrupção nas operações da Empresa Exemplo.",
                            "Retorno sobre o investimento projetado em menos de 6 meses através da otimização de recursos e redução de erros.",
                            "Capacite sua equipe na Empresa Exemplo com uma interface intuitiva que não exige conhecimento técnico especializado em IA."
                        ],
                        "target_pain_point_or_trigger": "Preocupação com a complexidade de novas ferramentas e a necessidade de ROI claro ao modernizar a pilha tecnológica.",
                        "evidence_or_proof_suggestion": "Compartilhar um white paper técnico sobre nossa arquitetura de integração flexível e APIs. Agendar uma sessão de Q&A com nosso especialista em integração para discutir o ambiente específico da Empresa Exemplo."
                    }
                ]
            }
            return json.dumps(mock_json_response)

    print("Running mock test for ValuePropositionCustomizationAgent...")
    mock_llm = MockLLMClient()
    agent = ValuePropositionCustomizationAgent(
        name="ValuePropositionCustomizationAgent",
        description="Customizes value propositions for leads based on deep analysis.",
        llm_client=mock_llm,
        logger_name="TestLogger"
    )

    test_lead_analysis = "A Empresa Exemplo é uma empresa de TI de médio porte em franca expansão, tendo recentemente anunciado entrada no mercado LATAM. O foco interno é otimizar processos para suportar esse crescimento."
    test_persona_profile = ("Nome: Carlos Mendes\nCargo: Diretor de Operações (COO)\nEmpresa: Empresa Exemplo\n"
                           "Foco: Eficiência operacional, ROI, resultados mensuráveis, integração fácil de novas tecnologias, modernização da stack tecnológica.\n"
                           "Dores: Processos manuais atuais não são escaláveis para a expansão; preocupação com a complexidade e o tempo de implementação de novas ferramentas; pressão para demonstrar ROI rapidamente.")
    test_deepened_pain_points = ("- Processos manuais demorados que não escalam com a expansão (ex: onboarding de novos clientes, gestão de projetos internacionais).\n"
                                 "- Dificuldade em obter uma visão consolidada dos dados operacionais devido a sistemas legados e desconectados.\n"
                                 "- Preocupação com a curva de aprendizado da equipe ao adotar novas tecnologias complexas.")
    test_buying_triggers = ("- Anúncio público de Expansão para o mercado LATAM (gatilho de crescimento).\n"
                            "- Contratação recente de Carlos Mendes como novo COO, com mandato para modernizar operações (gatilho de mudança de liderança).\n"
                            "- Feedback interno crescente sobre a necessidade de automação para reduzir a carga de trabalho manual (gatilho de dor interna).")
    test_product_service = ("Nossa Solução de IA para Otimização de Operações: Uma plataforma inteligente que automatiza processos de back-office, integra-se com sistemas existentes via APIs, "
                           "e fornece analytics preditivos para melhoria contínua. Diferenciais: implementação rápida (4-6 semanas), suporte local no Brasil, ROI médio de 250% em 12 meses para clientes do setor de TI.")
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

    print("\n--- Agent Output ---")
    if output.error_message:
        print(f"Error: {output.error_message}")

    if output.customized_value_propositions:
        for i, vp in enumerate(output.customized_value_propositions):
            print(f"\n--- Value Proposition {i+1} ---")
            print(f"Title: {vp.value_proposition_title}")
            print(f"Detailed Proposition: {vp.detailed_proposition}")
            print(f"Key Benefits: {vp.key_benefits_highlighted}")
            print(f"Target Pain/Trigger: {vp.target_pain_point_or_trigger}")
            print(f"Evidence Suggestion: {vp.evidence_or_proof_suggestion}")

    assert output.error_message is None, f"Error message was: {output.error_message}"
    assert len(output.customized_value_propositions) == 2
    assert output.customized_value_propositions[0].value_proposition_title == "Escale a Expansão da Empresa Exemplo com Eficiência Operacional via IA"
    assert "Carlos" in output.customized_value_propositions[0].detailed_proposition
    assert "Empresa Exemplo" in output.customized_value_propositions[0].detailed_proposition
    assert len(output.customized_value_propositions[0].key_benefits_highlighted) == 3
    assert output.customized_value_propositions[1].target_pain_point_or_trigger == "Preocupação com a complexidade de novas ferramentas e a necessidade de ROI claro ao modernizar a pilha tecnológica."

    print("\nMock test for ValuePropositionCustomizationAgent completed successfully.")
