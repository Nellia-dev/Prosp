from typing import Optional, List
from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase
import json # For mock test

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class LeadQualificationInput(BaseModel):
    lead_analysis: str # Summary from LeadAnalysisAgent
    persona_profile: str # Summary from PersonaCreationAgent (or constructed)
    deepened_pain_points: str # JSON string from PainPointDeepeningAgent
    product_service_offered: str # User's product/service

# Updated Pydantic Output Model
class LeadQualificationOutput(BaseModel):
    qualification_tier: str = Field(default="Não Qualificado", description="Enum: 'Alto Potencial', 'Potencial Médio', 'Baixo Potencial', 'Não Qualificado'")
    justification: str = "Justificativa não fornecida."
    key_positive_signals: List[str] = Field(default_factory=list)
    key_negative_signals_or_risks: List[str] = Field(default_factory=list)
    confidence_score: float = 0.5 # Made non-optional, default to 0.5
    suggested_next_steps_for_sales: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None

class LeadQualificationAgent(BaseAgent[LeadQualificationInput, LeadQualificationOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: LeadQualificationInput) -> LeadQualificationOutput:
        error_message = None
        self.logger.info(f"⚖️ LEAD QUALIFICATION AGENT STARTING for product: {input_data.product_service_offered}")

        try:
            # Truncate inputs, giving more space to pain_points and lead_analysis
            prompt_fixed_overhead = 3000 # Estimate for fixed parts of the prompt
            available_for_dynamic = GEMINI_TEXT_INPUT_TRUNCATE_CHARS - prompt_fixed_overhead

            tr_lead_analysis = self._truncate_text(input_data.lead_analysis, int(available_for_dynamic * 0.30))
            tr_persona_profile = self._truncate_text(input_data.persona_profile, int(available_for_dynamic * 0.20))
            tr_deepened_pain_points = self._truncate_text(input_data.deepened_pain_points, int(available_for_dynamic * 0.30))
            # product_service_offered is usually short, direct use. Other 20% for safety/other small inputs.

            # Refined prompt_template
            prompt_template = """
                Você é um Diretor de Vendas B2B experiente e criterioso, com especialização em qualificar leads no mercado brasileiro, focando em otimizar o tempo da equipe de vendas.
                Seu objetivo é classificar o potencial do lead com base nas informações estratégicas fornecidas, justificar sua avaliação e sugerir próximos passos concretos.

                DADOS PARA ANÁLISE DE QUALIFICAÇÃO:

                1. ANÁLISE GERAL DO LEAD:
                   \"\"\"
                   {lead_analysis}
                   \"\"\"

                2. PERFIL DA PERSONA (Tomador de Decisão Alvo):
                   \"\"\"
                   {persona_profile}
                   \"\"\"

                3. PONTOS DE DOR APROFUNDADOS E PERGUNTAS INVESTIGATIVAS (Insights sobre necessidades):
                   \"\"\"
                   {deepened_pain_points}
                   \"\"\"

                4. PRODUTO/SERVIÇO QUE ESTAMOS OFERECENDO:
                   "{product_service_offered}"

                INSTRUÇÕES PARA QUALIFICAÇÃO:
                Com base em TODAS as informações fornecidas, realize uma avaliação completa do lead:
                1.  **Alinhamento de Dor vs. Solução:** Avalie o quão bem os pontos de dor identificados se alinham com os benefícios do nosso "{product_service_offered}".
                2.  **Adequação da Persona:** Considere se o perfil da persona (cargo, responsabilidades, motivações) representa um cliente ideal e um tomador de decisão acessível.
                3.  **Urgência/Criticidade:** Analise a urgência ou criticidade implícita nos pontos de dor. Existe uma necessidade imediata ou futura?
                4.  **Sinais Positivos e Negativos:** Identifique explicitamente os principais fatores que tornam este lead promissor e os que representam riscos ou desalinhamento.
                5.  **Classificação do Lead:** Classifique o lead em UMA das seguintes categorias:
                    -   "Alto Potencial": Forte alinhamento com o ICP, dores claras que nossa solução resolve, urgência aparente, persona acessível. Ação imediata recomendada.
                    -   "Potencial Médio": Bom alinhamento, mas pode faltar urgência, clareza em alguns pontos, ou persona mais difícil de acessar. Requer nutrição ou mais investigação.
                    -   "Baixo Potencial": Alinhamento fraco, dores não claras ou não resolvidas pela nossa solução, sem urgência. Acompanhar de longe ou descartar.
                    -   "Desqualificado": Claramente não é um fit para nossa solução ou mercado.
                6.  **Justificativa:** Forneça uma justificativa concisa (2-3 frases) para a classificação, referenciando os dados.
                7.  **Score de Confiança:** Atribua um score de confiança (float, 0.0 a 1.0) à sua avaliação geral de qualificação.
                8.  **Próximos Passos para Vendas:** Sugira 1-2 próximos passos acionáveis e específicos para a equipe de vendas com base na sua qualificação.

                FORMATO DA RESPOSTA:
                Responda EXCLUSIVAMENTE com um objeto JSON válido, seguindo o schema e as descrições de campo abaixo. Não inclua NENHUM texto, explicação, ou markdown (como ```json) antes ou depois do objeto JSON.

                SCHEMA JSON ESPERADO:
                {{
                    "qualification_tier": "string", // Enum: "Alto Potencial", "Potencial Médio", "Baixo Potencial", "Desqualificado"
                    "justification": "string - Justificativa detalhada para a classificação, baseada nos dados fornecidos (máx. 3-4 frases).",
                    "key_positive_signals": ["string", ...], // Lista de 2-3 principais sinais positivos que suportam a qualificação (ex: 'Alinhamento claro com ICP', 'Dor X diretamente resolvida pela solução Y'). Lista vazia [] se não houver sinais claros.
                    "key_negative_signals_or_risks": ["string", ...], // Lista de 2-3 principais sinais negativos ou riscos (ex: 'Orçamento pode ser uma barreira', 'Persona difícil de contatar', 'Solução concorrente já em uso'). Lista vazia [] se não houver.
                    "confidence_score": "float", // Sua confiança na avaliação de qualificação (0.0 a 1.0). Deve ser sempre um float.
                    "suggested_next_steps_for_sales": ["string", ...] // Lista de 1-2 próximos passos práticos para a equipe de vendas (ex: 'Priorizar para contato imediato com foco na dor X', 'Incluir em fluxo de nutrição focado em [tema Y]', 'Descartar e focar em outros leads'). Lista vazia [] se não houver sugestão clara.
                }}
            """

            formatted_prompt = prompt_template.format(
                lead_analysis=tr_lead_analysis,
                persona_profile=tr_persona_profile,
                deepened_pain_points=tr_deepened_pain_points,
                product_service_offered=input_data.product_service_offered
            )
            self.logger.debug(f"Prompt for {self.name} (length: {len(formatted_prompt)}):\n{formatted_prompt[:500]}...")

            llm_response_str = self.generate_llm_response(formatted_prompt)

            if not llm_response_str:
                self.logger.error(f"❌ LLM call returned no response for {self.name}")
                return LeadQualificationOutput(error_message="LLM call returned no response.")

            self.logger.debug(f"LLM response received for {self.name} (length: {len(llm_response_str)}). Attempting to parse.")
            parsed_output = self.parse_llm_json_response(llm_response_str, LeadQualificationOutput)
            
            if parsed_output.error_message:
                self.logger.warning(f"⚠️ {self.name} JSON parsing/validation failed. Error: {parsed_output.error_message}. Raw response snippet: {llm_response_str[:500]}")
                # The error from parse_llm_json_response is already in parsed_output
                return parsed_output
            
            self.logger.info(f"✅ Lead qualification successful for product '{input_data.product_service_offered}'. Tier: {parsed_output.qualification_tier}, Confidence: {parsed_output.confidence_score}")
            return parsed_output

        except Exception as e:
            self.logger.error(f"❌ An unexpected error occurred in {self.name}: {e}", exc_info=True)
            return LeadQualificationOutput(error_message=f"An unexpected error occurred: {str(e)}")

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
                "qualification_tier": "Alto Potencial",
                "justification": "A Empresa Exemplo demonstra forte alinhamento com Nossas Soluções Incríveis devido à sua recente expansão e necessidade declarada de otimizar processos internos, onde nossa IA se destaca. O Diretor de Operações, Carlos Mendes, focado em ROI e eficiência, é a persona ideal.",
                "key_positive_signals": [
                    "Expansão recente para LATAM (indicando necessidade de escalar).",
                    "Menção explícita à 'otimização de processos internos'.",
                    "Persona (Diretor de Operações) com foco em ROI e eficiência."
                ],
                "key_negative_signals_or_risks": [
                    "Pode já estar avaliando outras soluções devido à urgência da expansão.",
                    "Resistência à mudança se a equipe estiver sobrecarregada com a expansão."
                ],
                "confidence_score": 0.85,
                "suggested_next_steps_for_sales": [
                    "Priorizar para contato imediato, focando em como a IA pode suportar a expansão LATAM de forma eficiente.",
                    "Preparar um case de estudo de empresa similar que escalou com nossa solução."
                ]
            })

    logger.info("Running mock test for LeadQualificationAgent...")
    mock_llm = MockLLMClient(api_key="mock_llm_key")
    agent = LeadQualificationAgent(
        name="TestLeadQualificationAgent",
        description="Test Agent for Lead Qualification",
        llm_client=mock_llm
    )

    test_lead_analysis = "A Empresa Exemplo (médio porte, setor de TI) enfrenta desafios na otimização de processos internos, especialmente após anúncio de expansão para o mercado LATAM."
    test_persona_profile = "Carlos Mendes, Diretor de Operações. Busca ROI claro, eficiência e soluções que se integrem facilmente. Motivado por resultados mensuráveis e reconhecimento."
    test_deepened_pain_points = json.dumps({
        "primary_pain_category": "Eficiência Operacional e Escalabilidade",
        "detailed_pain_points": [
            {"pain": "Otimização de Processos Manuais durante expansão", "impact": "Atrasos, aumento de custos, dificuldade em manter qualidade.", "urgency": "Alta"},
            {"pain": "Integração de Novas Tecnologias com sistemas legados", "impact": "Complexidade, tempo de implementação, resistência da equipe.", "urgency": "Média"}
        ],
        "investigative_questions_answered": [
            {"question": "Como a expansão impactou a capacidade de entrega?", "answer": "Ainda não totalmente claro, mas há preocupação."},
        ]
    })
    test_product_service = "Nossas Soluções Incríveis de Automação com IA"

    input_data = LeadQualificationInput(
        lead_analysis=test_lead_analysis,
        persona_profile=test_persona_profile,
        deepened_pain_points=test_deepened_pain_points,
        product_service_offered=test_product_service
    )

    output = agent.process(input_data)

    if output.error_message:
        logger.error(f"Error: {output.error_message}")
    else:
        logger.success("LeadQualificationAgent processed successfully.")
        logger.info(f"Qualification Tier: {output.qualification_tier}")
        logger.info(f"Justification: {output.justification}")
        logger.info(f"Confidence Score: {output.confidence_score}")
        logger.info(f"Positive Signals: {output.key_positive_signals}")
        logger.info(f"Negative Signals/Risks: {output.key_negative_signals_or_risks}")
        logger.info(f"Suggested Next Steps: {output.suggested_next_steps_for_sales}")

    assert output.error_message is None
    assert output.qualification_tier == "Alto Potencial"
    assert "Empresa Exemplo" in output.justification
    assert "Nossas Soluções Incríveis" in output.justification
    assert len(output.key_positive_signals) > 0
    assert output.confidence_score == 0.85
    assert len(output.suggested_next_steps_for_sales) > 0

    logger.info("\nMock test for LeadQualificationAgent completed successfully.")

```
