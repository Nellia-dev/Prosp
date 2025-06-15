from typing import Optional, List
from pydantic import BaseModel, Field
import json # For mock test

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class PainPointDeepeningInput(BaseModel):
    lead_analysis: str # Summary from LeadAnalysisAgent
    persona_profile: str # Summary from PersonaCreationAgent (or constructed)
    product_service_offered: str # User's product/service
    company_name: str

# Updated Pydantic Models
class DetailedPainPoint(BaseModel):
    pain_point_title: str = Field(default="Dor não especificada", description="Título curto e impactante da dor (ex: Baixa Eficiência Operacional, Dificuldade em Escalar Vendas).")
    detailed_description: str = Field(default="Descrição não fornecida.", description="Descrição elaborada da dor, suas causas e sintomas percebidos no contexto da empresa.")
    potential_business_impact: str = Field(default="Impacto não fornecido.", description="Impacto potencial ou real dessa dor no negócio do lead (ex: Perda de receita, Aumento de custos, Riscos de conformidade, Insatisfação de clientes).")
    how_our_solution_helps: str = Field(default="Alinhamento com solução não fornecido.", description="Como nosso produto/serviço especificamente aborda e resolve esta dor.")
    investigative_questions: List[str] = Field(default_factory=list, description="1-2 perguntas abertas para aprofundar o entendimento desta dor específica durante uma conversa.")

class PainPointDeepeningOutput(BaseModel):
    primary_pain_category: str = Field(default="Não especificado", description="Categoria principal que engloba as dores identificadas (ex: Eficiência Operacional, Crescimento de Receita, Gestão de Riscos, Custos Elevados).")
    detailed_pain_points: List[DetailedPainPoint] = Field(default_factory=list)
    urgency_level: str = Field(default="medium", description="Nível de urgência percebido para a resolução destas dores (Enum: 'low', 'medium', 'high', 'critical').")
    overall_pain_summary: Optional[str] = Field(default=None, description="Breve resumo geral (1-2 frases) sobre o cenário de dores do lead e sua aparente prontidão ou necessidade por soluções.")
    error_message: Optional[str] = None

class PainPointDeepeningAgent(BaseAgent[PainPointDeepeningInput, PainPointDeepeningOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: PainPointDeepeningInput) -> PainPointDeepeningOutput:
        error_message = None
        
        self.logger.info(f"🎯 PAIN POINT DEEPENING AGENT STARTING for company: {input_data.company_name}")
        self.logger.debug(f"📊 Input data: analysis_length={len(input_data.lead_analysis)}, persona_length={len(input_data.persona_profile)}, service='{input_data.product_service_offered}'")

        try:
            # Truncate inputs
            prompt_fixed_overhead = 4000 # Estimate for fixed parts of the prompt and JSON structure
            available_for_dynamic = GEMINI_TEXT_INPUT_TRUNCATE_CHARS - prompt_fixed_overhead
            
            tr_lead_analysis = self._truncate_text(input_data.lead_analysis, int(available_for_dynamic * 0.40))
            tr_persona_profile = self._truncate_text(input_data.persona_profile, int(available_for_dynamic * 0.40))
            # product_service_offered and company_name are typically short. Remaining 20% for them and buffer.
            
            self.logger.debug(f"✂️  Text truncation: analysis {len(input_data.lead_analysis)} -> {len(tr_lead_analysis)}, persona {len(input_data.persona_profile)} -> {len(tr_persona_profile)}")

            # Refined prompt_template
            prompt_template = """
                Você é um Consultor de Negócios B2B Sênior e Estrategista de Contas, com expertise em diagnosticar profundamente os pontos de dor de empresas e alinhar soluções de forma eficaz, especialmente no mercado brasileiro.
                Sua tarefa é analisar as informações da empresa '{company_name}' e da persona alvo, e detalhar os pontos de dor mais críticos, avaliando seu impacto e urgência, e formulando perguntas para aprofundamento.

                INFORMAÇÕES DISPONÍVEIS PARA ANÁLISE:

                1. ANÁLISE PRELIMINAR DO LEAD:
                   \"\"\"
                   {lead_analysis}
                   \"\"\"

                2. PERFIL DA PERSONA (Tomador de Decisão na {company_name}):
                   \"\"\"
                   {persona_profile}
                   \"\"\"

                3. NOSSO PRODUTO/SERVIÇO (que estamos oferecendo à {company_name}):
                   "{product_service_offered}"

                INSTRUÇÕES PARA O DIAGNÓSTICO DE PONTOS DE DOR:
                1.  **Identifique a Categoria Principal das Dores:** Determine uma categoria geral que englobe os principais desafios da empresa (ex: Eficiência Operacional, Crescimento de Receita, Gestão de Riscos, Custos Elevados, Inovação Tecnológica).
                2.  **Detalhe 2-3 Pontos de Dor Críticos:** Para cada ponto de dor identificado:
                    a.  `pain_point_title`: Crie um título curto e impactante para a dor.
                    b.  `detailed_description`: Descreva a dor de forma elaborada, incluindo suas possíveis causas e sintomas no contexto da '{company_name}'.
                    c.  `potential_business_impact`: Explique o impacto potencial ou real dessa dor nos negócios da '{company_name}' (ex: perda de receita, aumento de custos, riscos, insatisfação de clientes, perda de competitividade).
                    d.  `how_our_solution_helps`: Detalhe como o nosso "{product_service_offered}" especificamente aborda e ajuda a resolver esta dor.
                    e.  `investigative_questions`: Formule de 1 a 2 perguntas investigativas abertas e específicas para esta dor, destinadas a aprofundar a compreensão do problema e suas implicações durante uma conversa com a persona.
                3.  **Avalie o Nível de Urgência Geral:** Com base na sua análise, classifique o nível de urgência para a '{company_name}' resolver esses pontos de dor (opções: "low", "medium", "high", "critical").
                4.  **Crie um Resumo Geral das Dores:** Forneça um breve resumo (1-2 frases) sobre o cenário geral de dores do lead e sua aparente prontidão ou necessidade por soluções.
                5.  **Contexto Brasileiro:** Considere as nuances do mercado brasileiro ao avaliar os impactos e a urgência.

                FORMATO DA RESPOSTA:
                Responda EXCLUSIVAMENTE com um objeto JSON válido, seguindo o schema e as descrições de campo abaixo. Não inclua NENHUM texto, explicação, ou markdown (como ```json) antes ou depois do objeto JSON.

                SCHEMA JSON ESPERADO:
                {{
                    "primary_pain_category": "string - Categoria principal que engloba as dores identificadas (ex: Eficiência Operacional, Crescimento de Receita).",
                    "detailed_pain_points": [ // Lista de 2 a 3 objetos, um para cada dor detalhada.
                        {{
                            "pain_point_title": "string - Título curto e impactante da dor (ex: Baixa Eficiência em Processos Chave).",
                            "detailed_description": "string - Descrição elaborada da dor, suas causas e sintomas percebidos na empresa.",
                            "potential_business_impact": "string - Impacto potencial ou real dessa dor no negócio do lead (ex: Perda de receita devido a processos lentos).",
                            "how_our_solution_helps": "string - Como nosso produto/serviço '{product_service_offered}' especificamente aborda esta dor.",
                            "investigative_questions": ["string", ...] // Lista de 1-2 perguntas abertas para aprofundar esta dor específica. Lista vazia [] se não houver perguntas específicas.
                        }}
                    ],
                    "urgency_level": "string", // Enum: "low", "medium", "high", "critical" - Nível de urgência geral para resolver estas dores.
                    "overall_pain_summary": "string | null" // Breve resumo geral (1-2 frases) sobre o cenário de dores do lead. Use null se não houver um resumo conciso a adicionar.
                }}
            """

            formatted_prompt = prompt_template.format(
                lead_analysis=truncated_analysis,
                persona_profile=truncated_persona,
                product_service_offered=input_data.product_service_offered,
                company_name=input_data.company_name
            )
            self.logger.debug(f"Prompt for {self.name} (length: {len(formatted_prompt)}):\n{formatted_prompt[:600]}...")

            llm_response_str = self.generate_llm_response(formatted_prompt)

            if not llm_response_str:
                self.logger.error(f"❌ LLM call returned no response for {self.name} for company {input_data.company_name}")
                return PainPointDeepeningOutput(error_message="LLM call returned no response.")

            self.logger.debug(f"LLM response received for {self.name} (length: {len(llm_response_str)}). Attempting to parse.")
            
            parsed_output = self.parse_llm_json_response(llm_response_str, PainPointDeepeningOutput)
            
            if parsed_output.error_message:
                self.logger.warning(f"⚠️  {self.name} JSON parsing/validation failed for {input_data.company_name}. Error: {parsed_output.error_message}. Raw response snippet: {llm_response_str[:500]}")
                return parsed_output

            pain_points_count = len(parsed_output.detailed_pain_points)
            self.logger.info(f"✅ Pain point analysis successful for {input_data.company_name}: category='{parsed_output.primary_pain_category}', points_found={pain_points_count}, urgency='{parsed_output.urgency_level}'.")
            return parsed_output

        except Exception as e:
            self.logger.error(f"❌ An unexpected error occurred in {self.name} for {input_data.company_name}: {e}", exc_info=True)
            return PainPointDeepeningOutput(error_message=f"An unexpected error occurred: {str(e)}")

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
                "primary_pain_category": "Eficiência Operacional e Escalabilidade",
                "detailed_pain_points": [
                    {
                        "pain_point_title": "Otimização de Processos Manuais em Expansão",
                        "detailed_description": "A Empresa Exemplo, ao expandir para LATAM, enfrenta desafios com processos manuais que não escalam, especialmente em QA, gerando lentidão e potenciais erros.",
                        "potential_business_impact": "Atrasos em lançamentos de produtos/features, aumento de custos operacionais para manter a qualidade, dificuldade em atender a nova demanda do mercado LATAM.",
                        "how_our_solution_helps": "Nossas Soluções Incríveis de Automação com IA podem automatizar ciclos de QA repetitivos e complexos, liberando a equipe para focar em testes mais estratégicos e acelerando o time-to-market.",
                        "investigative_questions": [
                            "Como a expansão para LATAM está impactando especificamente os prazos de entrega de software?",
                            "Quais são os principais gargalos que vocês percebem nos processos de QA atualmente?"
                        ]
                    },
                    {
                        "pain_point_title": "Integração de Novas Tecnologias com Sistemas Legados",
                        "detailed_description": "A busca por modernização tecnológica mencionada pela Empresa Exemplo pode ser dificultada pela necessidade de integrar novas ferramentas com sistemas já existentes, um desafio comum para Diretores de Operações como Carlos Mendes.",
                        "potential_business_impact": "Aumento da complexidade técnica, custos de integração elevados, possível resistência da equipe a múltiplas ferramentas desconexas, tempo maior para obter valor das novas tecnologias.",
                        "how_our_solution_helps": "Nossas Soluções Incríveis de Automação com IA são projetadas com foco em integração facilitada (APIs robustas, conectores) e oferecem um dashboard unificado, simplificando a gestão.",
                        "investigative_questions": [
                            "Carlos, ao considerar novas tecnologias, qual é sua maior preocupação em relação à integração com o stack tecnológico atual da Empresa Exemplo?",
                            "Como a equipe técnica costuma lidar com a curva de aprendizado e adoção de novas plataformas?"
                        ]
                    }
                ],
                "urgency_level": "high",
                "overall_pain_summary": "A Empresa Exemplo possui dores significativas relacionadas à eficiência e escalabilidade de seus processos de TI, especialmente QA, impulsionadas pela expansão. Há uma necessidade clara de modernização e automação."
            })

    logger.info("Running mock test for PainPointDeepeningAgent...")
    mock_llm = MockLLMClient(api_key="mock_llm_key")
    agent = PainPointDeepeningAgent(
        name="TestPainPointDeepeningAgent",
        description="Test Agent for Pain Point Deepening",
        llm_client=mock_llm
    )

    test_lead_analysis = "A Empresa Exemplo (médio porte, setor de TI) enfrenta desafios na otimização de processos internos, muitos ainda manuais, para suportar sua recente expansão para o mercado LATAM. Ganhou prêmios de inovação e busca modernizar sua pilha de tecnologia."
    test_persona_profile = "Carlos Mendes é o Diretor de Operações da Empresa Exemplo. Suas principais responsabilidades incluem garantir a eficiência operacional e a implementação de novas tecnologias. Ele busca soluções com ROI claro e que sejam de fácil integração. É motivado por resultados mensuráveis e pelo reconhecimento de otimizar a operação da empresa. Seu estilo de comunicação é direto e formal."
    test_product_service = "Nossas Soluções Incríveis de Automação com IA para QA e DevOps"
    test_company_name = "Empresa Exemplo"

    input_data = PainPointDeepeningInput(
        lead_analysis=test_lead_analysis,
        persona_profile=test_persona_profile,
        product_service_offered=test_product_service,
        company_name=test_company_name
    )

    output = agent.process(input_data)

    if output.error_message:
        logger.error(f"Error: {output.error_message}")
    else:
        logger.success("PainPointDeepeningAgent processed successfully.")
        logger.info(f"Primary Pain Category: {output.primary_pain_category}")
        logger.info(f"Urgency Level: {output.urgency_level}")
        logger.info(f"Overall Pain Summary: {output.overall_pain_summary}")
        logger.info(f"Detailed Pain Points ({len(output.detailed_pain_points)}):")
        for i, dp_point in enumerate(output.detailed_pain_points):
            logger.info(f"  Pain Point {i+1}: {dp_point.pain_point_title}")
            logger.info(f"    Description: {dp_point.detailed_description}")
            logger.info(f"    Impact: {dp_point.potential_business_impact}")
            logger.info(f"    Solution Fit: {dp_point.how_our_solution_helps}")
            logger.info(f"    Investigative Questions: {dp_point.investigative_questions}")

    assert output.error_message is None
    assert output.primary_pain_category == "Eficiência Operacional e Escalabilidade"
    assert len(output.detailed_pain_points) == 2
    assert "expansão para LATAM" in output.detailed_pain_points[0].detailed_description
    assert len(output.detailed_pain_points[0].investigative_questions) > 0
    assert output.urgency_level == "high"
    assert output.overall_pain_summary is not None

    logger.info("\nMock test for PainPointDeepeningAgent completed successfully.")

```
