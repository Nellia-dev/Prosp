from typing import Optional
from pydantic import BaseModel

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000  # Max input tokens for Gemini Flash is 128k


class LeadAnalysisGenerationInput(BaseModel):
    lead_data_str: str  # JSON string of lead data
    enriched_data: str
    product_service_offered: str


class LeadAnalysisGenerationOutput(BaseModel):
    analysis_report: str
    error_message: Optional[str] = None


class LeadAnalysisGenerationAgent(BaseAgent[LeadAnalysisGenerationInput, LeadAnalysisGenerationOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase):
        super().__init__(name=name, description=description, llm_client=llm_client)
        # self.name is already set by super().__init__

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: LeadAnalysisGenerationInput) -> LeadAnalysisGenerationOutput:
        analysis_report = ""
        error_message = None

        try:
            # Truncate inputs to avoid exceeding LLM context window
            truncated_lead_data = self._truncate_text(input_data.lead_data_str, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 3)
            truncated_enriched_data = self._truncate_text(input_data.enriched_data, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 3)
            
            prompt_template = """
                Você é um Analista de Negócios B2B experiente. Sua tarefa é gerar uma análise concisa e perspicaz de um lead para {product_service_offered}.

                DADOS DO LEAD (JSON):
                {lead_data_str}

                DADOS ENRIQUECIDOS (Resultados de pesquisa na web, etc.):
                {enriched_data}

                INSTRUÇÕES:
                Com base nos dados do lead e nos dados enriquecidos fornecidos:
                1.  Identifique o setor da empresa e seu principal produto/serviço.
                2.  Avalie o tamanho estimado da empresa (pequena, média, grande) e sua possível estrutura organizacional.
                3.  Identifique os principais desafios e necessidades que a empresa pode estar enfrentando, especialmente aqueles que podem ser resolvidos por {product_service_offered}.
                4.  Descreva brevemente a cultura da empresa e seus valores, se identificáveis.
                5.  Forneça um diagnóstico geral do lead e seu potencial de conversão.

                Seja objetivo e use as informações disponíveis. Se alguma informação não estiver clara, indique isso.
                A análise deve ser um texto corrido, não um JSON.
                Máximo de 300 palavras.

                ANÁLISE DO LEAD:
            """
            
            formatted_prompt = prompt_template.format(
                product_service_offered=input_data.product_service_offered,
                lead_data_str=truncated_lead_data,
                enriched_data=truncated_enriched_data
            )

            llm_response = self.generate_llm_response(formatted_prompt)

            if llm_response:
                analysis_report = llm_response
            else:
                error_message = "LLM call returned no response or an empty response."
                # analysis_report remains empty

        except Exception as e:
            import traceback
            traceback.print_exc()
            error_message = f"An unexpected error occurred in {self.name}: {str(e)}"
            # analysis_report remains empty

        return LeadAnalysisGenerationOutput(
            analysis_report=analysis_report,
            error_message=error_message
        )

if __name__ == '__main__':
    # This is a placeholder for testing
    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str) -> Optional[str]:
            if "ANÁLISE DO LEAD:" in prompt:
                return (
                    "A Empresa Exemplo atua no setor de Tecnologia da Informação, oferecendo principalmente soluções de software como serviço (SaaS). "
                    "Com base nos dados, parece ser uma empresa de médio porte, com uma estrutura organizacional que provavelmente inclui departamentos de TI, vendas e marketing. "
                    "Seus principais desafios podem incluir a necessidade de otimizar processos internos e melhorar a experiência do cliente, áreas onde Nossas Soluções Incríveis podem agregar valor. "
                    "A cultura da empresa parece ser focada em inovação (com base em 'dados enriquecidos sobre prêmios de inovação'). "
                    "Diagnóstico geral: Lead com bom potencial, especialmente se estiver buscando modernizar suas ferramentas de gestão."
                )
            return "Resposta padrão do mock."

    print("Running mock test for LeadAnalysisGenerationAgent...")
    mock_llm = MockLLMClient()
    agent = LeadAnalysisGenerationAgent(llm_client=mock_llm)

    test_lead_data = """{
        "company_name": "Empresa Exemplo",
        "url": "http://www.empresaexemplo.com",
        "description": "Líder em soluções inovadoras de TI.",
        "employees": "150"
    }"""
    test_enriched_data = "A Empresa Exemplo ganhou prêmios de inovação em 2023. Artigos recentes mencionam expansão de mercado."
    test_product_service = "Nossas Soluções Incríveis"

    input_data = LeadAnalysisGenerationInput(
        lead_data_str=test_lead_data,
        enriched_data=test_enriched_data,
        product_service_offered=test_product_service
    )

    output = agent.process(input_data)

    print(f"Analysis Report: {output.analysis_report}")
    if output.error_message:
        print(f"Error: {output.error_message}")

    assert "Empresa Exemplo" in output.analysis_report
    assert "Nossas Soluções Incríveis" in output.analysis_report # Check if product/service was in the context for the LLM
    assert output.error_message is None
    print("Mock test completed.")
