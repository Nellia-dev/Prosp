from typing import Optional, List
from pydantic import BaseModel, Field
import json # Ensure json is imported

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class CompetitorIdentificationInput(BaseModel):
    initial_extracted_text: str # From website scraping or initial data
    product_service_offered: str # The user's product/service for context - CLARIFICATION: This is the LEAD's product/service
    known_competitors_list_str: str = "" # Optional, comma-separated string of USER's competitors

class CompetitorDetail(BaseModel):
    name: str
    description: Optional[str] = None # Brief description of why they are a competitor
    perceived_strength: Optional[str] = None # e.g., "High", "Medium", "Low"
    perceived_weakness: Optional[str] = None

class CompetitorIdentificationOutput(BaseModel):
    identified_competitors: List[CompetitorDetail] = Field(default_factory=list)
    other_notes: Optional[str] = None # For any general observations from the text
    error_message: Optional[str] = None

class CompetitorIdentificationAgent(BaseAgent[CompetitorIdentificationInput, CompetitorIdentificationOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: CompetitorIdentificationInput) -> CompetitorIdentificationOutput:
        error_message = None

        try:
            # Reserve space for other prompt parts
            text_truncate_limit = GEMINI_TEXT_INPUT_TRUNCATE_CHARS - (
                len(input_data.product_service_offered) +
                len(input_data.known_competitors_list_str) +
                2000 # Approx length of fixed prompt parts
            )
            truncated_text = self._truncate_text(input_data.initial_extracted_text, text_truncate_limit)

            known_competitors_prompt_segment = ""
            if input_data.known_competitors_list_str and input_data.known_competitors_list_str.strip():
                known_competitors_prompt_segment = f"LISTA DE CONCORRENTES CONHECIDOS (da nossa empresa, para referência contextual):\n\"{input_data.known_competitors_list_str}\""

            # Refined prompt
            prompt_template = """
                Você é um Analista de Inteligência Competitiva Sênior. Sua tarefa é identificar os concorrentes (diretos e indiretos) da EMPRESA ANALISADA, com base no conteúdo do site dela e na descrição de seus produtos/serviços.
                O foco é exclusivamente nos concorrentes da EMPRESA ANALISADA, não nos concorrentes da empresa que está utilizando esta ferramenta.

                TEXTO EXTRAÍDO DO SITE DA EMPRESA ANALISADA:
                \"\"\"
                {initial_extracted_text}
                \"\"\"

                PRODUTO/SERVIÇO PRINCIPAL OFERECIDO PELA EMPRESA ANALISADA (para contextualizar a identificação de seus concorrentes):
                "{product_service_offered_by_lead}"

                {known_competitors_prompt_segment}
                (O segmento acima, se presente, lista concorrentes da NOSSA EMPRESA. Apenas os mencione como concorrentes da EMPRESA ANALISADA se o "TEXTO EXTRAÍDO" sugerir explicitamente essa competição.)

                INSTRUÇÕES PARA IDENTIFICAÇÃO DE CONCORRENTES:
                1.  Analise o "TEXTO EXTRAÍDO" para identificar nomes de empresas ou produtos que ofereçam soluções similares ou alternativas ao "{product_service_offered_by_lead}" da EMPRESA ANALISADA.
                2.  Distinga parceiros de concorrentes: se uma empresa é mencionada como parceira de integração, não a liste como concorrente, a menos que o texto também sugira que ela compete em outras áreas.
                3.  Se o "{known_competitors_prompt_segment}" for fornecido, verifique se algum desses nomes é mencionado no "TEXTO EXTRAÍDO" como um competidor da EMPRESA ANALISADA. Não assuma que são concorrentes da EMPRESA ANALISADA apenas por estarem nessa lista.
                4.  Se nenhuma empresa concorrente for explicitamente mencionada ou claramente identificável a partir do texto, o campo "identified_competitors" deve ser uma lista vazia `[]`.

                FORMATO DA RESPOSTA:
                Responda EXCLUSIVAMENTE com um objeto JSON válido, seguindo o schema e as descrições de campo abaixo. Não inclua NENHUM texto, explicação, ou markdown (como ```json) antes ou depois do objeto JSON.

                SCHEMA JSON ESPERADO:
                {{
                    "identified_competitors": [ // Lista de objetos, um para cada concorrente identificado da EMPRESA ANALISADA.
                        {{
                            "name": "string - O nome do concorrente identificado.",
                            "description": "string | null - Breve descrição (1-2 frases) do porquê é considerado um concorrente da EMPRESA ANALISADA, com base no texto. Ex: 'Oferece produto X similar', 'Focado no mesmo nicho de mercado Y'.",
                            "perceived_strength": "string | null - Um ponto forte percebido do concorrente, se mencionado ou inferível do texto (ex: 'Líder de mercado estabelecido', 'Forte em inovação tecnológica'). Se não disponível, use null.",
                            "perceived_weakness": "string | null - Um ponto fraco percebido do concorrente, se mencionado ou inferível do texto (ex: 'Preço mais elevado', 'Menor flexibilidade de customização'). Se não disponível, use null."
                        }}
                    ],
                    "other_notes": "string | null - Observações gerais sobre o cenário competitivo da EMPRESA ANALISADA (ex: 'Mercado parece fragmentado com muitos players de nicho', 'Competição intensa em preço', 'Texto não forneceu dados suficientes para análise competitiva profunda'). Se não houver, use null."
                }}
            """
            
            formatted_prompt = prompt_template.format(
                initial_extracted_text=truncated_text,
                product_service_offered_by_lead=input_data.product_service_offered,
                known_competitors_prompt_segment=known_competitors_prompt_segment
            )

            llm_response_str = self.generate_llm_response(formatted_prompt)

            if not llm_response_str:
                return CompetitorIdentificationOutput(error_message="LLM call returned no response.")

            parsed_output = self.parse_llm_json_response(llm_response_str, CompetitorIdentificationOutput)
            
            if parsed_output.error_message:
                 self.logger.warning(f"{self.name} JSON parsing failed or model validation issue. Error: {parsed_output.error_message}. Raw response: {llm_response_str[:500]}")

            return parsed_output
        
        except Exception as e:
            self.logger.error(f"An unexpected error occurred in {self.name}: {e}", exc_info=True)
            return CompetitorIdentificationOutput(error_message=f"An unexpected error occurred: {str(e)}")

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

            competitors = []
            other_notes = "O mercado parece competitivo com players estabelecidos e novos entrantes."

            if "Soluções Alfa" in prompt: # Based on initial_extracted_text
                competitors.append({
                    "name": "Soluções Alfa",
                    "description": "Mencionada diretamente no texto como uma alternativa, indicando competição na área de Software de Gestão Personalizado.",
                    "perceived_strength": "Estabelecida (implícito pela comparação)",
                    "perceived_weakness": "Menos flexível que a Empresa Exemplo (declarado no texto)"
                })

            if "CompetiMaster" in prompt and "Avaliamos CompetiMaster no passado" in prompt: # Based on known_competitors and text
                 competitors.append({
                    "name": "CompetiMaster",
                    "description": "Considerado no passado pela Empresa Exemplo, sugerindo que atua no mesmo segmento de Software de Gestão Personalizado.",
                    "perceived_strength": None, # Não inferível do texto mock
                    "perceived_weakness": None
                })

            if not competitors:
                other_notes = "Nenhum concorrente direto claramente identificado no texto fornecido. Ferramentas Beta parece ser um parceiro."


            return json.dumps({
                "identified_competitors": competitors,
                "other_notes": other_notes
            })

    logger.info("Running mock test for CompetitorIdentificationAgent...")
    mock_llm = MockLLMClient()
    agent = CompetitorIdentificationAgent(
        name="CompetitorIdentificationAgent",
        description="Identifies competitors of the analyzed company.",
        llm_client=mock_llm
    )

    test_extracted_text = (
        "A Empresa Exemplo é líder em Software de Gestão Personalizado. Nossos diferenciais incluem X e Y. "
        "Soluções Alfa são boas, mas a Empresa Exemplo oferece mais flexibilidade. "
        "Nossa integração com Ferramentas Beta é robusta. Avaliamos CompetiMaster no passado."
    )
    test_product_service_of_lead = "Software de Gestão Personalizado"

    # Test Case 1: No known competitors list (for user's company)
    input_data_1 = CompetitorIdentificationInput(
        initial_extracted_text=test_extracted_text,
        product_service_offered=test_product_service_of_lead,
        known_competitors_list_str="" # Empty
    )
    output_1 = agent.process(input_data_1)
    logger.info("\nTest Case 1 (No known US-based competitors list for user):")
    if output_1.error_message:
        logger.error(f"Error: {output_1.error_message}")
    else:
        logger.info(f"Identified Competitors: {len(output_1.identified_competitors)}")
        for comp in output_1.identified_competitors: logger.info(f"  - {comp.name}: {comp.description}")
        logger.info(f"Other Notes: {output_1.other_notes}")

    assert output_1.error_message is None
    assert len(output_1.identified_competitors) >= 1 # Should find Soluções Alfa
    assert any(c.name == "Soluções Alfa" for c in output_1.identified_competitors)
    # CompetiMaster might be found if LLM infers from "Avaliamos CompetiMaster" even without it being in known_competitors_list_str
    # Depending on LLM strictness, this assertion might need adjustment or prompt refinement if we ONLY want it from known_competitors_list_str

    # Test Case 2: With known competitors list (for user's company)
    input_data_2 = CompetitorIdentificationInput(
        initial_extracted_text=test_extracted_text,
        product_service_offered=test_product_service_of_lead,
        known_competitors_list_str="CompetiMaster, RivalTech" # User's competitors
    )
    output_2 = agent.process(input_data_2)
    logger.info("\nTest Case 2 (With known US-based competitors list for user):")
    if output_2.error_message:
        logger.error(f"Error: {output_2.error_message}")
    else:
        logger.info(f"Identified Competitors: {len(output_2.identified_competitors)}")
        for comp in output_2.identified_competitors: logger.info(f"  - {comp.name}: {comp.description}")
        logger.info(f"Other Notes: {output_2.other_notes}")

    assert output_2.error_message is None
    assert len(output_2.identified_competitors) >= 1 # Soluções Alfa definitely
    assert any(c.name == "Soluções Alfa" for c in output_2.identified_competitors)
    assert any(c.name == "CompetiMaster" for c in output_2.identified_competitors) # Should be picked up due to text and list
    assert not any(c.name == "RivalTech" for c in output_2.identified_competitors) # Not in text
    
    logger.info("\nMock tests completed successfully.")

```
