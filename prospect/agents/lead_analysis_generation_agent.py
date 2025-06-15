from typing import Optional
from pydantic import BaseModel
import json # Added for the mock test, if needed for complex lead_data_str

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
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, **kwargs): # Added **kwargs
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs) # Pass **kwargs


    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: LeadAnalysisGenerationInput) -> LeadAnalysisGenerationOutput:
        analysis_report = ""
        error_message = None

        self.logger.info(f"📊 LEAD ANALYSIS GENERATION AGENT STARTING for product/service: {input_data.product_service_offered}")

        try:
            # Approximate character allocation, leaving room for prompt overhead
            # Total GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000
            prompt_fixed_overhead = 2000 # Approx chars for fixed parts of prompt
            available_for_dynamic = GEMINI_TEXT_INPUT_TRUNCATE_CHARS - prompt_fixed_overhead

            # Distribute available characters: 50% for lead_data, 50% for enriched_data
            # (or adjust ratio if one is typically much larger)
            truncated_lead_data = self._truncate_text(input_data.lead_data_str, available_for_dynamic // 2)
            truncated_enriched_data = self._truncate_text(input_data.enriched_data, available_for_dynamic // 2)
            
            # Refined prompt_template
            prompt_template = """
                Você é um Analista de Inteligência de Negócios Sênior, especializado em destilar informações complexas de leads em relatórios executivos claros, concisos e acionáveis.
                Sua tarefa é gerar uma análise textual perspicaz do lead, contextualizada pelo nosso produto/serviço: "{product_service_offered}".

                DADOS DO LEAD (origem: JSON estruturado internamente):
                \"\"\"
                {lead_data_str}
                \"\"\"

                DADOS ENRIQUECIDOS (origem: pesquisa web adicional, notícias, etc.):
                \"\"\"
                {enriched_data}
                \"\"\"

                INSTRUÇÕES PARA O RELATÓRIO DE ANÁLISE:
                Com base em TODOS os dados fornecidos (Dados do Lead e Dados Enriquecidos), elabore um relatório textual que cubra os seguintes pontos de forma integrada e fluida:

                1.  **Visão Geral da Empresa:** Identifique claramente o setor de atuação da empresa e seu principal produto ou serviço.
                2.  **Porte e Estrutura Estimados:** Avalie o tamanho estimado da empresa (pequena, média, grande) e, se possível, infira aspectos de sua estrutura organizacional que possam ser relevantes.
                3.  **Desafios e Necessidades Chave:** Identifique os principais desafios e necessidades que a empresa parece enfrentar. Dê ênfase especial àqueles que podem ser diretamente endereçados ou aliviados pelo nosso produto/serviço: "{product_service_offered}".
                4.  **Cultura e Valores (se discernível):** Descreva brevemente quaisquer aspectos da cultura da empresa ou seus valores que se destacarem nas informações.
                5.  **Diagnóstico Geral e Potencial de Conversão:** Forneça um diagnóstico resumido da situação do lead e uma avaliação do seu potencial de conversão, considerando o fit com "{product_service_offered}".

                DIRETRIZES ADICIONAIS:
                - **Objetividade:** Baseie-se estritamente nas informações disponíveis. Se alguma informação crucial não estiver clara ou disponível, mencione isso de forma explícita (ex: "Não foi possível determinar o tamanho exato da empresa com os dados fornecidos.").
                - **Formato:** A análise deve ser um texto corrido e bem articulado. NÃO use formato JSON.
                - **Estilo:** Mantenha um tom profissional, analítico e perspicaz.
                - **Tamanho:** O relatório final deve ser conciso, idealmente com um máximo de 300-350 palavras.

                Comece o relatório diretamente com a análise.

                RELATÓRIO DE ANÁLISE DO LEAD:
            """
            
            formatted_prompt = prompt_template.format(
                product_service_offered=input_data.product_service_offered,
                lead_data_str=truncated_lead_data,
                enriched_data=truncated_enriched_data
            )
            self.logger.debug(f"Prompt for {self.name} (length: {len(formatted_prompt)}):\n{formatted_prompt[:500]}...")

            llm_response = self.generate_llm_response(formatted_prompt)

            if llm_response:
                analysis_report = llm_response.strip()
                self.logger.info(f"✅ Report generated by {self.name}, length: {len(analysis_report)}")
            else:
                error_message = "LLM call returned no response or an empty response."
                self.logger.warning(f"⚠️ {self.name} received empty response from LLM.")
                # analysis_report remains empty

        except Exception as e:
            self.logger.error(f"❌ An unexpected error occurred in {self.name}: {e}", exc_info=True)
            # import traceback # Handled by exc_info=True
            # traceback.print_exc()
            error_message = f"An unexpected error occurred in {self.name}: {str(e)}"
            # analysis_report remains empty

        return LeadAnalysisGenerationOutput(
            analysis_report=analysis_report,
            error_message=error_message
        )

if __name__ == '__main__':
    from loguru import logger # Ensure logger is available
    import sys
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str) -> Optional[str]:
            logger.debug(f"MockLLMClient received prompt snippet:\n{prompt[:600]}...")
            if "RELATÓRIO DE ANÁLISE DO LEAD:" in prompt: # Matches the end of the refined prompt
                # Simulate a more structured narrative based on the refined prompt's points
                return (
                    "A Empresa Exemplo opera predominantemente no setor de Tecnologia da Informação, com foco em soluções de software como serviço (SaaS) para gestão de projetos e colaboração.\n\n"
                    "Considerando os dados e a menção a 150 funcionários, a Empresa Exemplo classifica-se como de médio porte. Sua estrutura organizacional provavelmente inclui departamentos dedicados de TI, vendas, marketing e desenvolvimento de produto, típicos de uma empresa SaaS em crescimento.\n\n"
                    "Os principais desafios identificados, especialmente relevantes para Nossas Soluções Incríveis de Otimização de Vendas, incluem a necessidade de escalar suas operações de vendas de forma eficiente para suportar a expansão de mercado mencionada nos dados enriquecidos. A menção a 'modernizar sua pilha de tecnologia' também sugere uma abertura para novas ferramentas que possam otimizar o funil de vendas e a gestão de leads.\n\n"
                    "A cultura da empresa parece ser focada em inovação, evidenciado pelos prêmios recebidos em 2023. Isso sugere uma receptividade a soluções tecnológicas avançadas que demonstrem claro valor agregado.\n\n"
                    "Diagnóstico Geral: A Empresa Exemplo é um lead com bom potencial. A fase de expansão e a busca por modernização tecnológica criam uma janela de oportunidade para Nossas Soluções Incríveis, que podem auxiliar diretamente na otimização dos processos de vendas e gestão de clientes, cruciais para o sucesso da expansão. O potencial de conversão é moderado a alto, dependendo da urgência interna para resolver os desafios de escalabilidade de vendas."
                ).strip()
            return "Resposta padrão do mock para teste."

    logger.info("Running mock test for LeadAnalysisGenerationAgent...")
    mock_llm = MockLLMClient()
    # Provide name and description as required by BaseAgent
    agent = LeadAnalysisGenerationAgent(
        name="TestLeadAnalysisGenerationAgent",
        description="Test Agent for Lead Analysis Generation",
        llm_client=mock_llm
    )

    test_lead_data = json.dumps({ # Ensure lead_data_str is a JSON string
        "company_name": "Empresa Exemplo",
        "url": "http://www.empresaexemplo.com",
        "description": "Líder em soluções inovadoras de TI para gestão de projetos.",
        "employees": "150",
        "sector": "Tecnologia da Informação (SaaS)"
    })
    test_enriched_data = "A Empresa Exemplo ganhou prêmios de inovação em 2023. Artigos recentes mencionam expansão de mercado para LATAM e busca por modernizar sua pilha de tecnologia."
    test_product_service = "Nossas Soluções Incríveis de Otimização de Vendas"

    input_data = LeadAnalysisGenerationInput(
        lead_data_str=test_lead_data,
        enriched_data=test_enriched_data,
        product_service_offered=test_product_service
    )

    output = agent.process(input_data)

    logger.info(f"Analysis Report:\n{output.analysis_report}")
    if output.error_message:
        logger.error(f"Error: {output.error_message}")
    else:
        logger.success("Analysis report generated successfully.")


    assert "Empresa Exemplo" in output.analysis_report
    assert "Nossas Soluções Incríveis de Otimização de Vendas" in output.analysis_report
    assert "Tecnologia da Informação" in output.analysis_report
    assert "médio porte" in output.analysis_report
    assert "expansão de mercado" in output.analysis_report
    assert output.error_message is None
    logger.info("Mock test for LeadAnalysisGenerationAgent completed successfully.")

```
