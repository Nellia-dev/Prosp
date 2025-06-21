from typing import Optional, List
from pydantic import BaseModel, Field

from .base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class ToTStrategyGenerationInput(BaseModel):
    current_lead_summary: str # Summary of analysis, pain points etc.
    persona_profile: Optional[str] = None # Detailed persona profile
    product_service_offered: str # What the user is selling

class ToTStrategyOptionModel(BaseModel):
    strategy_name: str = Field(..., description="Nome criativo, conciso e descritivo para a estratégia (ex: 'Conexão Direta via Desafio Compartilhado').")
    description: str = Field(..., description="Descrição detalhada da estratégia, explicando a lógica, os principais componentes e o fluxo de ações proposto.")
    initial_hook_or_angle: str = Field(..., description="O gancho ou ângulo inicial específico para esta estratégia, projetado para capturar o interesse do lead.")
    key_talking_points: List[str] = Field(default_factory=list, description="Principais pontos de discussão ou argumentos a serem usados nesta estratégia.")
    potential_benefits_for_lead: List[str] = Field(default_factory=list, description="Benefícios potenciais específicos que esta abordagem estratégica destacaria para o lead.")
    potential_challenges_or_risks: List[str] = Field(default_factory=list, description="Desafios ou riscos potenciais na execução desta estratégia ou objeções que o lead pode levantar.")
    primary_communication_channel_suggestion: str = Field(..., description="Principal canal de comunicação sugerido para iniciar esta estratégia (ex: Email, LinkedIn, WhatsApp, Evento).")
    tone_of_voice: str = Field(..., description="Tom de voz recomendado para esta estratégia (ex: Consultivo, Provocador, Educacional, Parceria).")
    opening_question: Optional[str] = Field(None, description="Uma pergunta de abertura impactante e relevante para esta estratégia, se aplicável.")

class ToTStrategyGenerationOutput(BaseModel):
    proposed_strategies: List[ToTStrategyOptionModel] = Field(default_factory=list)
    error_message: Optional[str] = None

class ToTStrategyGenerationAgent(BaseAgent[ToTStrategyGenerationInput, ToTStrategyGenerationOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: ToTStrategyGenerationInput) -> ToTStrategyGenerationOutput:
        proposed_strategies_text = ""
        error_message = None

        try:
            # Truncate inputs, giving appropriate space to each part
            total_chars_limit = GEMINI_TEXT_INPUT_TRUNCATE_CHARS
            # Approximate character count for the prompt structure itself
            prompt_overhead = 1000
            remaining_chars = total_chars_limit - prompt_overhead

            truncated_summary = self._truncate_text(input_data.current_lead_summary, remaining_chars // 3)
            truncated_persona = self._truncate_text(input_data.persona_profile or "Não fornecido.", remaining_chars // 3)
            truncated_product_service = self._truncate_text(input_data.product_service_offered, remaining_chars // 3)

            prompt_template = """
                Você é um Estrategista de Vendas B2B Criativo e Especialista em Ideação, com foco no desenvolvimento de abordagens de outreach inovadoras e diversificadas para o mercado brasileiro.

                Sua tarefa é gerar 3 a 4 OPÇÕES DE ESTRATÉGIAS DE ABORDAGEM distintas e bem descritas para um lead específico, com base nas informações fornecidas. As estratégias devem ser significativamente diferentes umas das outras para oferecer um leque variado de opções.

                INFORMAÇÕES DE CONTEXTO:

                1.  RESUMO DA INTELIGÊNCIA SOBRE O LEAD (dores, necessidades, gatilhos, etc.):
                    ```
                    {current_lead_summary}
                    ```

                2.  PERFIL DA PERSONA DO LEAD (detalhes sobre o decisor/influenciador):
                    ```
                    {persona_profile}
                    ```

                3.  PRODUTO/SERVIÇO QUE ESTAMOS OFERECENDO:
                    ```
                    {product_service_offered}
                    ```

                INSTRUÇÕES PARA GERAÇÃO DAS ESTRATÉGIAS:

                1.  **Diversidade**: Crie de 3 a 4 estratégias que sejam GENUINAMENTE DISTINTAS. Considere variar:
                    *   O ângulo principal (ex: focar na dor, no ganho, no medo de perder, na curiosidade).
                    *   A intensidade da abordagem (ex: mais sutil e educativa vs. mais direta e assertiva).
                    *   O canal primário sugerido.
                    *   A proposta de valor central enfatizada.
                2.  **Criatividade e Relevância**: As estratégias devem ser criativas, mas sempre relevantes para o contexto do lead, da persona e do produto/serviço. Pense "fora da caixa", mas com propósito.
                3.  **Contexto Brasileiro**: Assegure que as sugestões sejam culturalmente apropriadas e eficazes para o mercado brasileiro.
                4.  **Detalhes Claros**: Para cada estratégia, forneça todos os detalhes solicitados no formato JSON abaixo.

                Responda APENAS com um objeto JSON VÁLIDO seguindo RIGOROSAMENTE a estrutura abaixo. NÃO inclua NENHUM texto ou explicação adicional fora do objeto JSON.

                ```json
                {{
                    "proposed_strategies": [
                        {{
                            "strategy_name": "Nome Criativo e Descritivo da Estratégia (ex: 'Abordagem Consultiva Focada em ROI Imediato')",
                            "description": "Descrição detalhada da estratégia, explicando a lógica por trás dela, os principais componentes ou fases, e como ela se desenrolaria. (Seja específico, com 2-3 frases pelo menos).",
                            "initial_hook_or_angle": "O gancho ou ângulo inicial específico para esta estratégia, projetado para capturar o interesse do lead e iniciar a conversa (ex: 'Desafiar uma suposição comum do setor e oferecer uma nova perspectiva').",
                            "key_talking_points": [
                                "Ponto de conversa chave 1 relevante para esta estratégia (ex: 'Como nossa solução X resolve diretamente a dor Y mencionada pelo lead').",
                                "Ponto de conversa chave 2 (ex: 'Case de sucesso Z que demonstra o benefício W')."
                            ],
                            "potential_benefits_for_lead": [
                                "Benefício potencial específico para o lead se ele engajar com esta estratégia (ex: 'Identificar oportunidades de economia não percebidas').",
                                "Outro benefício (ex: 'Acesso a um framework exclusivo para resolver o problema A')."
                            ],
                            "potential_challenges_or_risks": [
                                "Desafio ou risco potencial na execução desta estratégia (ex: 'Pode exigir mais tempo de pesquisa inicial para personalizar o suficiente').",
                                "Objeção que o lead pode levantar especificamente para esta abordagem (ex: 'Já tentamos algo parecido e não funcionou')."
                            ],
                            "primary_communication_channel_suggestion": "Email | LinkedIn | WhatsApp | Phone | Evento | Outro (especificar)",
                            "tone_of_voice": "Tom de voz recomendado para esta estratégia (ex: 'Consultivo e especialista', 'Provocador e perspicaz', 'Educacional e prestativo', 'Parceria e colaborativo').",
                            "opening_question": "Uma pergunta de abertura impactante e relevante para esta estratégia, projetada para engajar e qualificar (ex: 'Carlos, percebi que empresas como a sua frequentemente enfrentam [desafio X]. Isso também é uma prioridade para você atualmente?')."
                        }}
                        // ... mais 2 ou 3 objetos de estratégia, cada um distinto do anterior
                    ]
                }}
                ```
            """

            formatted_prompt = prompt_template.format(
                current_lead_summary=truncated_summary,
                persona_profile=truncated_persona,
                product_service_offered=truncated_product_service
            )

            llm_response_str = self.generate_llm_response(formatted_prompt, use_gemini_pro_vision=False) # Assuming text-only

            if not llm_response_str:
                self.logger.error("LLM call returned no response.")
                return ToTStrategyGenerationOutput(error_message="LLM call returned no response.")

            parsed_output = self.parse_llm_json_response(llm_response_str, ToTStrategyGenerationOutput)
            
            if parsed_output.error_message:
                 self.logger.warning(f"ToTStrategyGenerationAgent JSON parsing failed. Raw response: {llm_response_str[:500]}")
                 # Return partially parsed strategies or an empty list with error
                 return ToTStrategyGenerationOutput(
                    proposed_strategies=parsed_output.proposed_strategies or [],
                    error_message=parsed_output.error_message
                )
            
            return parsed_output
        
        except Exception as e:
            self.logger.error(f"An unexpected error occurred in {self.name}: {e}", exc_info=True)
            return ToTStrategyGenerationOutput(error_message=f"An unexpected error occurred: {str(e)}")

if __name__ == '__main__':
    import json

    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str, use_gemini_pro_vision: bool = False) -> Optional[str]:
            # This mock will return a JSON string based on the new structure
            mock_json_response = {
                "proposed_strategies": [
                    {
                        "strategy_name": "Desafio da Eficiência Oculta com ROI Direto",
                        "description": "Esta estratégia foca em abordar o lead com uma análise preliminar (hipotética ou baseada em dados do setor) dos custos ocultos de seus processos atuais, e como a nossa solução pode gerar um ROI tangível rapidamente. A abordagem é consultiva, mas com um senso de urgência.",
                        "initial_hook_or_angle": "Apresentar um 'Diagnóstico Rápido de Eficiência' personalizado ou um dado estatístico impactante sobre perdas no setor do lead devido à ineficiência que nossa solução combate.",
                        "key_talking_points": [
                            "Quantificação dos custos de oportunidade de não otimizar processos X.",
                            "Demonstração clara do impacto da nossa solução na redução de Y horas/custos.",
                            "ROI esperado nos primeiros 6-12 meses e cases de sucesso com números."
                        ],
                        "potential_benefits_for_lead": [
                            "Identificar economias significativas não óbvias.",
                            "Obter um caminho claro para melhorar a eficiência com resultados mensuráveis.",
                            "Fortalecer sua posição como Diretor de Operações ao apresentar soluções de alto impacto."
                        ],
                        "potential_challenges_or_risks": [
                            "Lead pode ser cético em relação às estimativas sem um diagnóstico profundo.",
                            "Necessidade de dados concretos para suportar o 'diagnóstico rápido'."
                        ],
                        "primary_communication_channel_suggestion": "Email Personalizado com anexo (PDF do diagnóstico/estudo)",
                        "tone_of_voice": "Consultivo, analítico e focado em resultados",
                        "opening_question": "Carlos, com base em nossa experiência com empresas de TI em expansão, notamos que processos X frequentemente escondem oportunidades de economia de até Y%. Isso reflete os desafios que você enfrenta na Empresa Exemplo atualmente?"
                    },
                    {
                        "strategy_name": "Parceria Estratégica para Inovação e Crescimento Sustentado",
                        "description": "Posiciona nossa empresa não apenas como fornecedora, mas como uma parceira tecnológica estratégica que pode ajudar o lead a navegar a expansão e a incorporar inovações contínuas. O foco é no longo prazo e na co-criação de valor.",
                        "initial_hook_or_angle": "Convidar o lead para uma discussão de alto nível sobre tendências futuras do setor e como a IA está moldando empresas líderes, oferecendo um white paper ou participação em um grupo seleto.",
                        "key_talking_points": [
                            "Como nossa solução facilita a adaptação a novas demandas de mercado e escalabilidade.",
                            "Exemplos de co-criação de funcionalidades ou otimizações com clientes-chave.",
                            "Visão de futuro para nossa plataforma e como ela pode suportar a visão de longo prazo da Empresa Exemplo."
                        ],
                        "potential_benefits_for_lead": [
                            "Ganhar um parceiro que entende os desafios de crescimento e inovação no setor de TI.",
                            "Acesso a insights e tecnologias de ponta para se manter competitivo.",
                            "Possibilidade de influenciar o roadmap de uma solução chave para seu negócio."
                        ],
                        "potential_challenges_or_risks": [
                            "Pode parecer menos urgente se o lead estiver focado em problemas imediatos.",
                            "Proposta de 'parceria' pode soar como um compromisso maior do que o lead está pronto para considerar inicialmente."
                        ],
                        "primary_communication_channel_suggestion": "LinkedIn (artigo ou convite para evento online) seguido de email",
                        "tone_of_voice": "Visionário, colaborativo e de parceria estratégica",
                        "opening_question": "Carlos, com a recente expansão da Empresa Exemplo, como você vê o papel da inovação tecnológica e de parceiros estratégicos para garantir que esse crescimento seja não apenas rápido, mas também sustentável e à frente da concorrência?"
                    },
                    {
                        "strategy_name": "Workshop Exclusivo de Otimização de Processos Pós-Expansão",
                        "description": "Oferecer um workshop prático e exclusivo (online ou presencial) para a equipe do lead, focado em identificar gargalos de processos exacerbados pela expansão e como a IA pode ser aplicada taticamente. O objetivo é gerar valor imediato e demonstrar expertise.",
                        "initial_hook_or_angle": "Convite para um workshop gratuito e de alto valor, customizado para os desafios de empresas de TI em expansão, mencionando um benefício claro (ex: 'Saia com 3 táticas de otimização para implementar imediatamente').",
                        "key_talking_points": [
                            "Demonstração prática da nossa solução aplicada a um problema específico do lead (se possível obter essa info).",
                            "Metodologias de identificação de gargalos em processos de TI.",
                            "Como a IA pode automatizar tarefas X, Y, Z que são críticas durante a expansão."
                        ],
                        "potential_benefits_for_lead": [
                            "Capacitação da equipe com novas ideias e táticas de otimização.",
                            "Diagnóstico prático de alguns de seus desafios atuais.",
                            "Experiência direta com o potencial da nossa solução de forma interativa."
                        ],
                        "potential_challenges_or_risks": [
                            "Requer maior comprometimento de tempo do lead e sua equipe.",
                            "Logística para organizar o workshop (mesmo online) pode ser um desafio."
                        ],
                        "primary_communication_channel_suggestion": "Email (convite formal) + Reforço no LinkedIn",
                        "tone_of_voice": "Educacional, prático e colaborativo",
                        "opening_question": "Carlos, sabemos que a expansão traz desafios únicos para a otimização de processos. Estaríamos interessados em oferecer à sua equipe um workshop prático e gratuito sobre como a IA pode ajudar a superar esses obstáculos. Seria de interesse?"
                    }
                ]
            }
            return json.dumps(mock_json_response)

    print("Running mock test for ToTStrategyGenerationAgent...")
    mock_llm = MockLLMClient()
    agent = ToTStrategyGenerationAgent(
        name="ToTStrategyGenerationAgent",
        description="Generates diverse Tree-of-Thought B2B sales strategies.",
        llm_client=mock_llm,
        logger_name="TestLogger" # Optional: for quieter test output
    )

    test_lead_summary = (
        "Lead: Empresa Exemplo (Médio porte, setor de TI). Contato Principal: Carlos Mendes (Diretor de Operações).\n"
        "Foco da Persona: Eficiência operacional, ROI, otimização de processos, redução de custos, integração fácil de novas tecnologias.\n"
        "Dores Conhecidas: Processos manuais demorados que não escalam, dificuldade em integrar novas ferramentas com sistemas legados, pressão para modernizar a stack tecnológica para suportar a expansão.\n"
        "Gatilhos de Compra: Recente anúncio de expansão para duas novas regiões, feedback interno sobre a necessidade de automação."
    )
    test_persona_profile = (
        "Nome: Carlos Mendes\nCargo: Diretor de Operações (COO)\nEmpresa: Empresa Exemplo\nNível de Senioridade: Executivo C-Level, decisão final em compras de tecnologia para operações.\n"
        "Responsabilidades: Garantir a eficiência e escalabilidade das operações de TI, gerenciar o orçamento de tecnologia para operações, liderar projetos de transformação digital na área operacional.\n"
        "Principais Desafios: Reduzir custos operacionais enquanto aumenta a capacidade de entrega, garantir a integração suave de novas tecnologias com o ambiente existente, encontrar soluções que ofereçam ROI claro e rápido.\n"
        "Como se informa: White papers de consultorias (McKinsey, Gartner), webinars técnicos de fornecedores renomados, artigos em publicações como Forbes Tech e CIO Magazine, networking em eventos do setor.\n"
        "Tolerância a Riscos: Moderada. Aberto a inovações que demonstrem valor comprovado e um plano de implementação com riscos mitigados. Evita soluções experimentais sem cases robustos.\n"
        "Estilo de Comunicação Preferido: Email conciso e direto para introdução, seguido de reuniões com apresentações baseadas em dados. Valoriza clareza, objetividade e respostas rápidas."
    )
    test_product_service = (
        "Nossa solução é uma plataforma de Inteligência Artificial (IA) e Automação Inteligente de Processos (IPA) projetada especificamente para empresas de TI. "
        "Ela automatiza processos complexos de back-office, integra-se com sistemas legados através de APIs e conectores customizáveis, e fornece dashboards analíticos para otimização contínua. "
        "Benefícios Chave: Redução de custos operacionais em até 30% no primeiro ano, aumento da eficiência de processamento em até 50%, melhoria na conformidade e redução de erros humanos. "
        "Diferenciais: Implementação assistida em 4-6 semanas, suporte técnico premium 24/7 em português, e um modelo de precificação flexível baseado em volume de automação."
    )


    input_data = ToTStrategyGenerationInput(
        current_lead_summary=test_lead_summary,
        persona_profile=test_persona_profile,
        product_service_offered=test_product_service
    )

    output = agent.process(input_data)

    print("\n--- Agent Output ---")
    if output.error_message:
        print(f"Error: {output.error_message}")

    if output.proposed_strategies:
        for i, strat in enumerate(output.proposed_strategies):
            print(f"\n--- Proposed Strategy {i+1} ---")
            print(f"Name: {strat.strategy_name}")
            print(f"Description: {strat.description}")
            print(f"Hook/Angle: {strat.initial_hook_or_angle}")
            print(f"Talking Points: {strat.key_talking_points}")
            print(f"Benefits for Lead: {strat.potential_benefits_for_lead}")
            print(f"Challenges/Risks: {strat.potential_challenges_or_risks}")
            print(f"Channel Suggestion: {strat.primary_communication_channel_suggestion}")
            print(f"Tone: {strat.tone_of_voice}")
            print(f"Opening Question: {strat.opening_question}")

    assert output.error_message is None, f"Error message was: {output.error_message}"
    assert len(output.proposed_strategies) >= 2, "Should generate at least 2-3 strategies" # Mock returns 3
    assert output.proposed_strategies[0].strategy_name == "Desafio da Eficiência Oculta com ROI Direto"
    assert "Carlos Mendes" in input_data.persona_profile # Ensure context is passed
    assert "Nossa solução é uma plataforma de Inteligência Artificial" in input_data.product_service_offered

    print("\nMock test for ToTStrategyGenerationAgent completed successfully.")
