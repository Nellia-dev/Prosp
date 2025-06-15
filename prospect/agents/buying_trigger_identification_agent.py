from typing import Optional, List
from pydantic import BaseModel, Field
import json # Ensure json is imported for potential use in main block if needed

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000 # Max length for combined inputs to LLM

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
        error_message = None

        try:
            # Truncate inputs
            # Approximate character allocation, leaving room for prompt overhead
            char_limit_lead_data = GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 3
            char_limit_enriched_data = GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 3

            truncated_lead_data = self._truncate_text(input_data.lead_data_str, char_limit_lead_data)
            truncated_enriched_data = self._truncate_text(input_data.enriched_data, char_limit_enriched_data)

            # Refined prompt_template
            prompt_template = """
                Você é um Analista de Inteligência de Mercado e Estrategista de Vendas B2B, um detetive corporativo expert em identificar 'janelas de oportunidade' através de sinais de compra.
                Sua missão é analisar os dados fornecidos sobre um lead e identificar eventos ou circunstâncias (gatilhos de compra) que sugiram que a empresa possa estar receptiva ou necessitando de soluções como a nossa: "{product_service_offered}".

                DADOS DO LEAD (informações estruturadas sobre a empresa):
                ```json
                {lead_data_str}
                ```

                DADOS ENRIQUECIDOS (notícias recentes, comunicados de imprensa, mudanças organizacionais, etc.):
                \"\"\"
                {enriched_data}
                \"\"\"

                NOSSO PRODUTO/SERVIÇO (para o qual estamos buscando oportunidades):
                "{product_service_offered}"

                INSTRUÇÕES DETALHADAS:
                1.  Analise CUIDADOSAMENTE todas as informações (Dados do Lead e Dados Enriquecidos).
                2.  Identifique gatilhos de compra. Gatilhos são eventos, mudanças, ou declarações que indicam uma potencial necessidade, problema a ser resolvido, ou uma nova iniciativa onde nosso produto/serviço seria relevante. Exemplos comuns incluem:
                    -   Mudanças recentes na liderança executiva (novos C-levels, VPs, Diretores em áreas chave).
                    -   Anúncios de expansão de negócios, lançamento de novos produtos/serviços, ou entrada em novos mercados geográficos.
                    -   Rodadas de investimento significativas (Seed, Série A, B, C, etc.) ou aquisições.
                    -   Menções explícitas nos dados a desafios, problemas ou objetivos que nosso "{product_service_offered}" pode endereçar (ex: "buscando otimizar processos de vendas", "precisamos melhorar a eficiência da equipe de marketing digital", "foco em transformação digital").
                    -   Aumento significativo de contratações em áreas específicas que se beneficiariam do nosso produto/serviço.
                    -   Fusões ou aquisições (tanto da empresa alvo quanto de seus concorrentes).
                    -   Menções a problemas com soluções atuais, contratos expirando, ou um desejo claro de modernização tecnológica ou processual.
                3.  Para cada gatilho identificado, forneça uma descrição clara e uma explicação concisa de sua relevância. A `relevance_explanation` deve conectar sucintamente o gatilho a uma possível necessidade ou problema que nosso "{product_service_offered}" pode resolver para esta empresa específica.

                FORMATO DA RESPOSTA:
                Responda EXCLUSIVAMENTE com um objeto JSON válido, seguindo o schema abaixo. Não inclua NENHUM texto, explicação, ou markdown (como ```json) antes ou depois do objeto JSON.

                SCHEMA JSON ESPERADO:
                {{
                    "identified_triggers": [  // Lista de objetos, um para cada gatilho. Se nenhum gatilho for encontrado, retorne uma lista vazia [].
                        {{
                            "trigger_description": "string - Descrição clara e concisa do gatilho identificado (ex: 'Nova rodada de investimento Série B anunciada em [data]', 'Contratação de novo VP de Marketing com foco em crescimento digital', 'Menção no relatório anual sobre foco em otimização de custos operacionais').",
                            "relevance_explanation": "string - Explicação concisa (1-2 frases) de por que este gatilho específico é relevante para o nosso '{product_service_offered}', indicando uma possível necessidade ou oportunidade."
                        }}
                    ],
                    "other_observations": "string | null - Observações gerais pertinentes sobre a empresa ou o mercado que não se qualificam como gatilhos diretos, mas podem ser úteis. Se não houver, use null ou uma string como 'Nenhuma observação adicional relevante.'."
                }}
            """

            formatted_prompt = prompt_template.format(
                lead_data_str=truncated_lead_data,
                enriched_data=truncated_enriched_data,
                product_service_offered=input_data.product_service_offered
            )

            llm_response_str = self.generate_llm_response(formatted_prompt)

            if not llm_response_str:
                return BuyingTriggerIdentificationOutput(error_message="LLM call returned no response.")

            # parse_llm_json_response should ideally handle Pydantic validation internally
            # or return a dict that can be validated by Pydantic model.
            parsed_output = self.parse_llm_json_response(llm_response_str, BuyingTriggerIdentificationOutput)
            
            if parsed_output.error_message:
                 self.logger.warning(f"{self.name} JSON parsing failed or model validation issue. Error: {parsed_output.error_message}. Raw response: {llm_response_str[:500]}")
                 # Return the output with the error message set by parse_llm_json_response
                 return parsed_output

            # Ensure identified_triggers is a list of IdentifiedTrigger objects if parsing was successful
            # This should be handled by Pydantic validation if parse_llm_json_response returns a dict
            # If parse_llm_json_response already returns a BuyingTriggerIdentificationOutput, this is fine.
            if not isinstance(parsed_output.identified_triggers, list) or \
               not all(isinstance(item, IdentifiedTrigger) for item in parsed_output.identified_triggers):
                # This case might indicate that parse_llm_json_response did not fully hydrate the model correctly
                # or the LLM returned an unexpected structure for identified_triggers.
                self.logger.warning(f"{self.name}: 'identified_triggers' is not a list of IdentifiedTrigger objects. LLM output might be malformed for this field.")
                # We might still return parsed_output as is, relying on the error_message if Pydantic validation failed,
                # or attempt a more specific error message here.
                # For now, we trust that parse_llm_json_response + Pydantic validation handles this.
                pass


            return parsed_output

        except Exception as e:
            self.logger.error(f"An unexpected error occurred in {self.name}: {e}", exc_info=True)
            # import traceback # Already imported if needed
            # traceback.print_exc() # Handled by logger's exc_info=True
            return BuyingTriggerIdentificationOutput(error_message=f"An unexpected error occurred: {str(e)}")

if __name__ == '__main__':
    from loguru import logger # Ensure logger is available
    import sys
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str) -> Optional[str]:
            logger.debug(f"MockLLMClient received prompt snippet:\n{prompt[:500]}...")
            # Simulate LLM returning valid JSON based on the refined prompt
            return json.dumps({
                "identified_triggers": [
                    {
                        "trigger_description": "Anúncio de Expansão de Mercado para LATAM (Dados Enriquecidos)",
                        "relevance_explanation": "A expansão para novos mercados frequentemente requer otimização de processos e novas ferramentas para escalar operações, o que Nossas Soluções Incríveis podem fornecer."
                    },
                    {
                        "trigger_description": "Menção a 'otimizar processos internos' e 'modernizar sua pilha de tecnologia' (Dados do Lead e Enriquecidos)",
                        "relevance_explanation": "Esta é uma declaração direta de necessidade que se alinha perfeitamente com os benefícios de Nossas Soluções Incríveis."
                    },
                    {
                        "trigger_description": "Contratação de Novo COO, Carlos Mendes (Dados Enriquecidos)",
                        "relevance_explanation": "Novos líderes em operações frequentemente revisam sistemas e processos, abrindo oportunidades para Nossas Soluções Incríveis."
                    }
                ],
                "other_observations": "A empresa parece estar em um ciclo de crescimento e modernização, tornando-a um prospect interessante."
            })

    logger.info("Running mock test for BuyingTriggerIdentificationAgent...")
    mock_llm = MockLLMClient()
    agent = BuyingTriggerIdentificationAgent(
        name="BuyingTriggerIdentificationAgent",
        description="Identifies buying triggers from lead data.",
        llm_client=mock_llm
    )

    test_lead_data_str = """{
        "company_name": "Empresa Exemplo",
        "description": "Focada em crescimento e quer otimizar processos internos."
    }"""
    test_enriched_data = (
        "Empresa Exemplo anunciou expansão para o mercado LATAM. "
        "Recentemente nomeou um novo COO, Carlos Mendes, vindo da TechCorp. "
        "Artigo de notícias menciona que a Empresa Exemplo está buscando 'modernizar sua pilha de tecnologia'."
    )
    test_product_service = "Nossas Soluções Incríveis para Otimização de Processos"

    input_data = BuyingTriggerIdentificationInput(
        lead_data_str=test_lead_data_str,
        enriched_data=test_enriched_data,
        product_service_offered=test_product_service
    )

    output = agent.process(input_data)

    if output.error_message:
        logger.error(f"Error: {output.error_message}")
    else:
        logger.success("BuyingTriggerIdentificationAgent processed successfully.")
        logger.info(f"Identified Triggers: {len(output.identified_triggers)}")
        for i, trigger in enumerate(output.identified_triggers):
            logger.info(f"  Trigger {i+1}: {trigger.trigger_description}")
            logger.info(f"  Explanation: {trigger.relevance_explanation}")
        logger.info(f"Other Observations: {output.other_observations}")

    assert output.error_message is None
    assert len(output.identified_triggers) == 3
    assert "Anúncio de Expansão de Mercado para LATAM" in output.identified_triggers[0].trigger_description
    assert "Nossas Soluções Incríveis" in output.identified_triggers[0].relevance_explanation
    assert output.other_observations is not None

    logger.info("Mock test completed successfully.")

```
