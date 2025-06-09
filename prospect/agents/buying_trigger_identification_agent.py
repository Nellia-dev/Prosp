from typing import Optional, List
from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class BuyingTriggerIdentificationInput(BaseModel):
    lead_data_str: str # JSON string of lead data (e.g., from scraping, CRM)
    enriched_data: str # From Tavily or other enrichment sources
    product_service_offered: str # The user's product/service for context

class IdentifiedTrigger(BaseModel):
    trigger_description: str
    relevance_explanation: str # Why it's a trigger for the product/service

class BuyingTriggerIdentificationOutput(BaseModel):
    identified_triggers: List[IdentifiedTrigger] = Field(default_factory=list)
    other_observations: Optional[str] = None # For any general observations from the text
    error_message: Optional[str] = None

class BuyingTriggerIdentificationAgent(BaseAgent[BuyingTriggerIdentificationInput, BuyingTriggerIdentificationOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: BuyingTriggerIdentificationInput) -> BuyingTriggerIdentificationOutput:
        identified_triggers_report = ""
        error_message = None

        try:
            # Truncate inputs
            truncated_lead_data = self._truncate_text(input_data.lead_data_str, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 3)
            truncated_enriched_data = self._truncate_text(input_data.enriched_data, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 3)

            prompt_template = """
                Você é um Analista de Sinais de Compra B2B. Sua tarefa é identificar potenciais gatilhos de compra com base nos dados do lead e informações enriquecidas.
                Gatilhos de compra são eventos ou circunstâncias que indicam que uma empresa pode estar ativamente procurando soluções como {product_service_offered}.

                DADOS DO LEAD (JSON):
                {lead_data_str}

                DADOS ENRIQUECIDOS (Notícias, comunicados de imprensa, mudanças na empresa, etc.):
                {enriched_data}

                PRODUTO/SERVIÇO OFERECIDO (pela sua empresa, para contextualizar a busca por gatilhos):
                {product_service_offered}

                INSTRUÇÕES:
                Analise todas as informações fornecidas para identificar sinais que possam indicar uma necessidade ou oportunidade para {product_service_offered}.
                Procure por gatilhos como (mas não limitado a):
                -   Mudanças recentes na liderança (novos C-levels, diretores).
                -   Anúncios de expansão, novos produtos ou entrada em novos mercados.
                -   Rodadas de investimento recentes.
                -   Menções a desafios específicos que seu {product_service_offered} resolve (ex: "buscando otimizar X", "precisamos melhorar Y").
                -   Contratação para novas funções relacionadas à área que seu produto/serviço atende.
                -   Fusões ou aquisições.
                -   Menções a problemas com soluções atuais ou desejo de modernização.

                Para cada gatilho identificado:
                1.  Descreva o gatilho.
                2.  Explique brevemente por que ele pode ser um indicador de oportunidade para {product_service_offered}.
                
                Se nenhum gatilho claro for identificado, retorne uma lista vazia para "identified_triggers".
                Use o campo "other_observations" para quaisquer notas gerais.

                Responda APENAS com um objeto JSON com a seguinte estrutura:
                {{
                    "identified_triggers": [
                        {{
                            "trigger_description": "Descrição do gatilho (string)",
                            "relevance_explanation": "Explicação da relevância para {product_service_offered} (string)"
                        }}
                    ],
                    "other_observations": "Observações gerais (string, opcional)"
                }}
                Não inclua nenhuma explicação ou texto adicional fora do objeto JSON.
            """

            formatted_prompt = prompt_template.format(
                lead_data_str=truncated_lead_data,
                enriched_data=truncated_enriched_data,
                product_service_offered=input_data.product_service_offered
            )

            llm_response_str = self.generate_llm_response(formatted_prompt)

            if not llm_response_str:
                return BuyingTriggerIdentificationOutput(error_message="LLM call returned no response.")

            parsed_output = self.parse_llm_json_response(llm_response_str, BuyingTriggerIdentificationOutput)
            
            if parsed_output.error_message:
                 self.logger.warning(f"BuyingTriggerIdentificationAgent JSON parsing failed. Raw response: {llm_response_str[:500]}")
            # No specific regex fallback here. Error from parse_llm_json_response will be propagated.

            return parsed_output

        except Exception as e:
            self.logger.error(f"An unexpected error occurred in {self.name}: {e}")
            import traceback
            traceback.print_exc()
            return BuyingTriggerIdentificationOutput(error_message=f"An unexpected error occurred: {str(e)}")

if __name__ == '__main__':
    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str) -> Optional[str]:
            if "RELATÓRIO DE GATILHOS DE COMPRA IDENTIFICADOS:" in prompt:
                return (
                    "RELATÓRIO DE GATILHOS DE COMPRA IDENTIFICADOS:\n\n"
                    "Com base nas informações fornecidas:\n\n"
                    "1.  **Gatilho: Anúncio de Expansão de Mercado (Dados Enriquecidos).\n"
                    "    **Por quê:** A expansão para novos mercados frequentemente requer otimização de processos e novas ferramentas para escalar operações, o que Nossas Soluções Incríveis podem fornecer.\n\n"
                    "2.  **Gatilho: Menção a 'otimizar processos internos' (Dados do Lead).\n"
                    "    **Por quê:** Esta é uma declaração direta de necessidade que se alinha perfeitamente com os benefícios de Nossas Soluções Incríveis, que são projetadas para otimizar processos.\n\n"
                    "3.  **Gatilho: Contratação de Novo Diretor de Operações (Dados Enriquecidos - 'recentemente nomeou um novo COO').\n"
                    "    **Por quê:** Novos líderes, especialmente em operações, muitas vezes revisam sistemas e processos existentes e estão abertos a novas soluções para marcar sua gestão, como Nossas Soluções Incríveis."
                )
            return "Resposta padrão do mock."

    print("Running mock test for BuyingTriggerIdentificationAgent...")
    mock_llm = MockLLMClient()
    agent = BuyingTriggerIdentificationAgent(
        name="BuyingTriggerIdentificationAgent",
        description="Identifies buying triggers from lead data.",
        llm_client=mock_llm
    )

    test_lead_data_str = """{
        "company_name": "Empresa Exemplo",
        "description": "Focada em crescimento e otimizar processos internos."
    }"""
    test_enriched_data = (
        "Empresa Exemplo anunciou expansão para o mercado LATAM. "
        "Recentemente nomeou um novo COO, Carlos Mendes, vindo da TechCorp. "
        "Artigo de notícias menciona que a Empresa Exemplo está buscando 'modernizar sua pilha de tecnologia'."
    )
    test_product_service = "Nossas Soluções Incríveis"

    input_data = BuyingTriggerIdentificationInput(
        lead_data_str=test_lead_data_str,
        enriched_data=test_enriched_data,
        product_service_offered=test_product_service
    )

    output = agent.process(input_data)

    print(f"Identified Triggers Report: \n{output.identified_triggers_report}")
    if output.error_message:
        print(f"Error: {output.error_message}")

    assert "Anúncio de Expansão de Mercado" in output.identified_triggers_report
    assert "otimizar processos internos" in output.identified_triggers_report
    assert "Novo Diretor de Operações" in output.identified_triggers_report
    assert "Nossas Soluções Incríveis" in output.identified_triggers_report # Check product was in context
    assert output.error_message is None
    print("Mock test completed.")
