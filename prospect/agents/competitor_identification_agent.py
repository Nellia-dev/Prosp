from typing import Optional, List
from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class CompetitorIdentificationInput(BaseModel):
    initial_extracted_text: str # From website scraping or initial data
    product_service_offered: str # The user's product/service for context
    known_competitors_list_str: str = "" # Optional, comma-separated string

class CompetitorDetail(BaseModel):
    name: str
    description: Optional[str] = None # Brief description of why they are a competitor
    perceived_strength: Optional[str] = None # e.g., "High", "Medium", "Low"
    perceived_weakness: Optional[str] = None

class CompetitorIdentificationOutput(BaseModel):
    identified_competitors: List[CompetitorDetail] = Field(default_factory=list)
    # current_solutions_in_use: List[str] = Field(default_factory=list) # Solutions the lead might be using
    other_notes: Optional[str] = None # For any general observations from the text
    error_message: Optional[str] = None

class CompetitorIdentificationAgent(BaseAgent[CompetitorIdentificationInput, CompetitorIdentificationOutput]):
    def __init__(self, llm_client: LLMClientBase):
        super().__init__(llm_client)
        self.name = "CompetitorIdentificationAgent"

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: CompetitorIdentificationInput) -> CompetitorIdentificationOutput:
        identified_competitors_report = ""
        error_message = None

        try:
            truncated_text = self._truncate_text(input_data.initial_extracted_text, GEMINI_TEXT_INPUT_TRUNCATE_CHARS - 500) # Reserve space for rest of prompt

            known_competitors_prompt_segment = ""
            if input_data.known_competitors_list_str and input_data.known_competitors_list_str.strip():
                known_competitors_prompt_segment = f"Considere também esta lista de concorrentes já conhecidos, se mencionados no texto: {input_data.known_competitors_list_str}."


            prompt_template = """
                Você é um Analista de Inteligência Competitiva. Sua tarefa é identificar concorrentes potenciais da empresa em análise, com base no texto extraído do site da empresa e no produto/serviço que ELA oferece.
                O objetivo é entender quem são os concorrentes diretos ou indiretos da EMPRESA ANALISADA, não da empresa que está usando este software.

                TEXTO EXTRAÍDO DO SITE DA EMPRESA ANALISADA:
                {initial_extracted_text}

                PRODUTO/SERVIÇO PRINCIPAL OFERECIDO PELA EMPRESA ANALISADA (inferido do texto ou fornecido):
                {product_service_offered_by_lead} 
                (Nota: Este é o produto/serviço da empresa que estamos analisando, não o produto da empresa que está usando esta ferramenta.)

                {known_competitors_prompt_segment}

                INSTRUÇÕES:
                1.  Analise o texto extraído para identificar quaisquer empresas ou produtos mencionados que possam ser considerados concorrentes da empresa analisada, com base no {product_service_offered_by_lead}.
                2.  Se o texto mencionar parceiros ou integrações, não os liste como concorrentes, a menos que também ofereçam soluções competitivas.
                3.  Para cada concorrente identificado, forneça seu nome e uma breve descrição do motivo pelo qual é considerado concorrente. Opcionalmente, adicione percepções sobre seus pontos fortes ou fracos se o texto fornecer pistas.
                4.  Se nenhum concorrente for explicitamente mencionado ou claramente identificável, retorne uma lista vazia para "identified_competitors".
                5.  Use o campo "other_notes" para quaisquer observações gerais sobre o cenário competitivo inferido do texto.

                Responda APENAS com um objeto JSON com a seguinte estrutura:
                {{
                    "identified_competitors": [
                        {{
                            "name": "Nome do Concorrente (string)",
                            "description": "Descrição do porquê é concorrente (string, opcional)",
                            "perceived_strength": "Ponto forte percebido (string, opcional)",
                            "perceived_weakness": "Ponto fraco percebido (string, opcional)"
                        }}
                    ],
                    "other_notes": "Observações gerais sobre o cenário competitivo (string, opcional)"
                }}
                Não inclua nenhuma explicação ou texto adicional fora do objeto JSON.
            """
            # Note: The prompt uses "product_service_offered_by_lead" to internally clarify.
            # The input "product_service_offered" is from the perspective of the lead being analyzed.
            
            formatted_prompt = prompt_template.format(
                initial_extracted_text=truncated_text,
                product_service_offered_by_lead=input_data.product_service_offered, # This is correct, it's the lead's offering
                known_competitors_prompt_segment=known_competitors_prompt_segment
            )

            llm_response_str = self.generate_llm_response(formatted_prompt)

            if not llm_response_str:
                return CompetitorIdentificationOutput(error_message="LLM call returned no response.")

            parsed_output = self.parse_llm_json_response(llm_response_str, CompetitorIdentificationOutput)
            
            if parsed_output.error_message:
                 self.logger.warning(f"CompetitorIdentificationAgent JSON parsing failed. Raw response: {llm_response_str[:500]}")
            # No specific regex fallback here. Error from parse_llm_json_response will be propagated.

            return parsed_output
        
        except Exception as e:
            self.logger.error(f"An unexpected error occurred in {self.name}: {e}")
            import traceback
            traceback.print_exc()
            return CompetitorIdentificationOutput(error_message=f"An unexpected error occurred: {str(e)}")

if __name__ == '__main__':
    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str) -> Optional[str]:
            if "RELATÓRIO DE CONCORRENTES IDENTIFICADOS" in prompt:
                response_text = (
                    "RELATÓRIO DE CONCORRENTES IDENTIFICADOS PARA A EMPRESA ANALISADA:\n\n"
                    "Com base no texto fornecido, que menciona 'Soluções Alfa são boas, mas a Empresa Exemplo oferece mais flexibilidade', e 'nossa integração com Ferramentas Beta é robusta', os seguintes concorrentes podem ser inferidos:\n\n"
                    "1.  **Soluções Alfa:**\n"
                    "    Considerado um concorrente porque o texto os compara diretamente com a Empresa Exemplo, sugerindo que oferecem produtos/serviços na mesma categoria de 'Software de Gestão Personalizado'.\n\n"
                )
                if "CompetiMaster" in prompt: # Checking if known_competitors_list_str was used
                    response_text += (
                        "2.  **CompetiMaster (da lista de conhecidos):**\n"
                        "    Embora não explicitamente detalhado no texto do site, se 'CompetiMaster' foi mencionado em algum lugar (como 'avaliamos CompetiMaster'), seria um concorrente no setor de 'Software de Gestão Personalizado'.\n\n"
                    )
                response_text += "Nenhum outro concorrente direto foi claramente identificado apenas no texto fornecido. Ferramentas Beta parece ser um parceiro de integração."
                return response_text
            return "Resposta padrão do mock."

    print("Running mock test for CompetitorIdentificationAgent...")
    mock_llm = MockLLMClient()
    agent = CompetitorIdentificationAgent(llm_client=mock_llm)

    test_extracted_text = (
        "A Empresa Exemplo é líder em Software de Gestão Personalizado. Nossos diferenciais incluem X e Y. "
        "Soluções Alfa são boas, mas a Empresa Exemplo oferece mais flexibilidade. "
        "Nossa integração com Ferramentas Beta é robusta. Avaliamos CompetiMaster no passado."
    )
    test_product_service_of_lead = "Software de Gestão Personalizado" # Product of the company being analyzed

    # Test Case 1: No known competitors list
    input_data_1 = CompetitorIdentificationInput(
        initial_extracted_text=test_extracted_text,
        product_service_offered=test_product_service_of_lead
    )
    output_1 = agent.process(input_data_1)
    print("\nTest Case 1 (No known competitors list):")
    print(f"Report: {output_1.identified_competitors_report}")
    if output_1.error_message:
        print(f"Error: {output_1.error_message}")
    assert "Soluções Alfa" in output_1.identified_competitors_report
    assert "CompetiMaster" not in output_1.identified_competitors_report # because it wasn't in known_competitors_list_str for this test
    assert output_1.error_message is None

    # Test Case 2: With known competitors list
    input_data_2 = CompetitorIdentificationInput(
        initial_extracted_text=test_extracted_text,
        product_service_offered=test_product_service_of_lead,
        known_competitors_list_str="CompetiMaster, RivalTech"
    )
    output_2 = agent.process(input_data_2)
    print("\nTest Case 2 (With known competitors list):")
    print(f"Report: {output_2.identified_competitors_report}")
    if output_2.error_message:
        print(f"Error: {output_2.error_message}")
    assert "Soluções Alfa" in output_2.identified_competitors_report
    assert "CompetiMaster" in output_2.identified_competitors_report # Should be picked up now
    assert "RivalTech" not in output_2.identified_competitors_report # Not mentioned in text, so LLM might not include it unless text implies it
    assert output_2.error_message is None
    
    print("\nMock tests completed.")
