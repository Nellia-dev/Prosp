import json
import re
from typing import Optional, List

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class ContactExtractionInput(BaseModel):
    extracted_text: str
    company_name: str
    product_service_offered: str # Context of what the lead offers, to understand roles

class ContactExtractionOutput(BaseModel):
    emails_found: List[str] = Field(default_factory=list)
    instagram_profiles_found: List[str] = Field(default_factory=list)
    # Added for consistency with subtask example, though prompt needs to request them.
    # These fields are from the subtask's ideal output, not originally in this agent's output model.
    # For this refinement, I will focus the prompt on existing fields first.
    # If these were to be added, the Pydantic model would be the source of truth for the prompt.
    phone_numbers_found: List[str] = Field(default_factory=list)
    linkedin_profiles_found: List[str] = Field(default_factory=list)
    facebook_profiles_found: List[str] = Field(default_factory=list)
    twitter_x_profiles_found: List[str] = Field(default_factory=list)
    suggested_search_queries: List[str] = Field(default_factory=list) # Changed from tavily_search_suggestion for multiple queries
    confidence_score: Optional[float] = None
    extraction_summary: Optional[str] = None
    error_message: Optional[str] = None

class ContactExtractionAgent(BaseAgent[ContactExtractionInput, ContactExtractionOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: ContactExtractionInput) -> ContactExtractionOutput:
        error_message = None
        
        self.logger.info(f"📧 CONTACT EXTRACTION STARTING for company: {input_data.company_name}")
        self.logger.info(f"📊 Input data: text_length={len(input_data.extracted_text)}, service_context_for_lead='{input_data.product_service_offered}'")

        try:
            # Reserve characters for the rest of the prompt
            char_limit_extracted_text = GEMINI_TEXT_INPUT_TRUNCATE_CHARS - 2500
            truncated_text = self._truncate_text(input_data.extracted_text, char_limit_extracted_text)

            # Refined prompt to match the extended ContactExtractionOutput model
            prompt_template = """
                Você é um Especialista em Mineração de Dados e OSINT (Open Source Intelligence), altamente qualificado em extrair informações de contato B2B de conteúdo web e textos não estruturados.
                Sua tarefa é analisar o conteúdo fornecido sobre a empresa '{company_name}' (que oferece '{product_service_offered}') e extrair uma variedade de informações de contato, além de sugerir consultas de busca para encontrar mais detalhes.

                CONTEÚDO FORNECIDO (website, notícias, etc.):
                \"\"\"
                {extracted_text}
                \"\"\"

                INSTRUÇÕES DETALHADAS PARA EXTRAÇÃO:
                1.  **E-mails:** Identifique e liste todos os endereços de e-mail válidos. Priorize e-mails genéricos (ex: contato@, vendas@) e, se possível, e-mails que pareçam pertencer a departamentos ou indivíduos (ex: nome.sobrenome@).
                2.  **Telefones:** Identifique e liste todos os números de telefone. Tente padronizar para um formato que inclua DDI e DDD quando inferível (ex: "+55 11 9XXXX-XXXX").
                3.  **Perfis do LinkedIn:** Identifique URLs de perfis do LinkedIn, tanto da página da empresa quanto de indivíduos que pareçam ser funcionários ou decisores chave.
                4.  **Perfis do Instagram:** Identifique nomes de usuário/perfis do Instagram (ex: @nome_da_empresa).
                5.  **Perfis do Facebook:** Identifique URLs de páginas do Facebook associadas à empresa.
                6.  **Perfis do Twitter/X:** Identifique handles do Twitter/X (ex: @empresaX).
                7.  **Sugestões de Busca Adicional:** Com base no texto e no perfil da empresa, formule até 3 strings de busca otimizadas (para Google ou Tavily API). O objetivo destas buscas futuras será encontrar:
                    a.  Contatos de decisores chave específicos (ex: CEOs, Diretores de Marketing/Vendas, etc.) na '{company_name}'.
                    b.  Informações de contato mais diretas ou de departamentos específicos, caso o texto atual seja limitado.
                    Exemplos de sugestões: "Contato comercial {company_name}", "Diretor de Vendas {company_name} LinkedIn", "Telefone {company_name} filial [cidade]".
                8.  **Score de Confiança:** Forneça um score numérico (float entre 0.0 e 1.0) que represente sua confiança na quantidade e qualidade das informações de contato extraídas diretamente do texto. 0.0 para nenhuma informação encontrada, 1.0 para informações abundantes e claras.
                9.  **Resumo da Extração:** Um breve resumo (1-2 frases) do processo de extração, mencionando quais tipos de informação foram mais fáceis de encontrar e quaisquer dificuldades ou observações (ex: "Muitos emails genéricos encontrados, mas poucos contatos individuais. URL do LinkedIn da empresa clara. Sugestões de busca focadas em decisores.").

                FORMATO DA RESPOSTA:
                Responda EXCLUSIVAMENTE com um objeto JSON válido, seguindo o schema e as descrições de campo abaixo. Não inclua NENHUM texto, explicação, ou markdown (como ```json) antes ou depois do objeto JSON.

                SCHEMA JSON ESPERADO:
                {{
                    "emails_found": ["string", ...], // Lista de endereços de e-mail. Lista vazia [] se nenhum encontrado.
                    "phone_numbers_found": ["string", ...], // Lista de números de telefone. Lista vazia [] se nenhum encontrado.
                    "linkedin_profiles_found": ["string", ...], // Lista de URLs de perfis do LinkedIn. Lista vazia [] se nenhum encontrado.
                    "instagram_profiles_found": ["string", ...], // Lista de perfis do Instagram (ex: "@username"). Lista vazia [] se nenhum encontrado.
                    "facebook_profiles_found": ["string", ...], // Lista de URLs de perfis do Facebook. Lista vazia [] se nenhum encontrado.
                    "twitter_x_profiles_found": ["string", ...], // Lista de handles do Twitter/X (ex: "@username"). Lista vazia [] se nenhum encontrado.
                    "suggested_search_queries": ["string", ...], // Lista de até 3 sugestões de busca. Lista vazia [] se nenhuma sugestão clara.
                    "confidence_score": "float | null", // Score de confiança (0.0 a 1.0) ou null se não aplicável.
                    "extraction_summary": "string | null" // Resumo do processo de extração ou null.
                }}
            """
            
            formatted_prompt = prompt_template.format(
                company_name=input_data.company_name,
                product_service_offered=input_data.product_service_offered, # Context about what the lead company does
                extracted_text=truncated_text
            )

            llm_response_str = self.generate_llm_response(formatted_prompt)

            if not llm_response_str:
                self.logger.error(f"❌ LLM call returned no response for contact extraction for {input_data.company_name}")
                return ContactExtractionOutput(
                    error_message="LLM call returned no response."
                )

            self.logger.debug(f"✅ LLM returned response for {input_data.company_name}, length: {len(llm_response_str)}")
            parsed_output = self.parse_llm_json_response(llm_response_str, ContactExtractionOutput)
            
            if parsed_output.error_message:
                 self.logger.warning(f"⚠️ {self.name} JSON parsing failed or model validation issue for {input_data.company_name}. Error: {parsed_output.error_message}. Raw response: {llm_response_str[:500]}")
                 # Even if parsing has an error, it returns a default model with the error message set.
                 # We don't need a separate regex fallback if the prompt is strong for JSON.
                 return parsed_output # Return the output object which contains the error message

            self.logger.info(f"✅ Contact extraction successful for {input_data.company_name}: "
                             f"Emails: {len(parsed_output.emails_found)}, "
                             f"Phones: {len(parsed_output.phone_numbers_found)}, "
                             f"LinkedIn: {len(parsed_output.linkedin_profiles_found)}, "
                             f"Instagram: {len(parsed_output.instagram_profiles_found)}, "
                             f"Facebook: {len(parsed_output.facebook_profiles_found)}, "
                             f"Twitter/X: {len(parsed_output.twitter_x_profiles_found)}, "
                             f"Search Queries: {len(parsed_output.suggested_search_queries)}, "
                             f"Confidence: {parsed_output.confidence_score}")
            return parsed_output

        except Exception as e:
            self.logger.error(f"❌ An unexpected error occurred in {self.name} for {input_data.company_name}: {e}", exc_info=True)
            return ContactExtractionOutput(
                error_message=f"An unexpected error occurred: {str(e)}"
            )

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
            if "Test Company Alpha" in prompt:
                return json.dumps({
                    "emails_found": ["contact@alpha.com", "sales@alpha.com"],
                    "phone_numbers_found": ["+55 11 2345-6789"],
                    "linkedin_profiles_found": ["linkedin.com/company/alpha-inc", "linkedin.com/in/ceoalpha"],
                    "instagram_profiles_found": ["@alpha_inc_official"],
                    "facebook_profiles_found": ["facebook.com/alphainc"],
                    "twitter_x_profiles_found": ["@AlphaIncGlobal"],
                    "suggested_search_queries": ["Contato Diretor Vendas Test Company Alpha", "Test Company Alpha vagas marketing"],
                    "confidence_score": 0.9,
                    "extraction_summary": "Extração bem-sucedida. Encontrados múltiplos contatos e perfis sociais. Texto claro."
                })
            elif "Test Company Beta" in prompt: # Simulate malformed JSON (missing quote)
                return '{"emails_found": ["info@beta.com"], "instagram_profiles_found": ["@beta_co"], "confidence_score": 0.5, "extraction_summary": "Parcial." "suggested_search_queries": []}'
            elif "Test Company Gamma" in prompt: # Simulate no contacts found
                return json.dumps({
                    "emails_found": [],
                    "phone_numbers_found": [],
                    "linkedin_profiles_found": [],
                    "instagram_profiles_found": [],
                    "facebook_profiles_found": [],
                    "twitter_x_profiles_found": [],
                    "suggested_search_queries": ["Investimento Test Company Gamma", "Notícias Test Company Gamma"],
                    "confidence_score": 0.2,
                    "extraction_summary": "Nenhum contato direto encontrado no texto. Sugestões de busca para aprofundar."
                })
            return json.dumps({
                    "emails_found": [], "phone_numbers_found": [], "linkedin_profiles_found": [],
                    "instagram_profiles_found": [], "facebook_profiles_found": [], "twitter_x_profiles_found": [],
                    "suggested_search_queries": ["Contato {company_name}"], "confidence_score": 0.1, "extraction_summary": "Informação muito limitada."
            })
    
    logger.info("Running mock tests for ContactExtractionAgent...")
    mock_llm = MockLLMClient(api_key="mock_llm_key")
    # Provide name and description as required by BaseAgent
    agent = ContactExtractionAgent(name="TestContactExtractionAgent", description="Test Agent", llm_client=mock_llm)

    # Test Case 1: Valid JSON response
    input_alpha = ContactExtractionInput(
        extracted_text="Test Company Alpha is a leader in AI. Contact us at contact@alpha.com or sales@alpha.com. Call +551123456789. Follow us on Instagram @alpha_inc_official, LinkedIn /company/alpha-inc and /in/ceoalpha, FB facebook.com/alphainc, X @AlphaIncGlobal.",
        company_name="Test Company Alpha",
        product_service_offered="AI Solutions for B2B"
    )
    output_alpha = agent.process(input_alpha)
    logger.info(f"\nTest Case 1 (Alpha - Valid JSON):")
    logger.info(f"  Output: {output_alpha.model_dump_json(indent=2)}")
    assert output_alpha.error_message is None
    assert output_alpha.emails_found == ["contact@alpha.com", "sales@alpha.com"]
    assert output_alpha.instagram_profiles_found == ["@alpha_inc_official"]
    assert output_alpha.linkedin_profiles_found == ["linkedin.com/company/alpha-inc", "linkedin.com/in/ceoalpha"]
    assert output_alpha.confidence_score == 0.9

    # Test Case 2: Malformed JSON response
    input_beta = ContactExtractionInput(
        extracted_text="Info at info@beta.com, Insta @beta_co. Test Company Beta focuses on cloud services.",
        company_name="Test Company Beta",
        product_service_offered="Cloud Services for SMBs"
    )
    output_beta = agent.process(input_beta)
    logger.info(f"\nTest Case 2 (Beta - Malformed JSON):")
    logger.info(f"  Output: {output_beta.model_dump_json(indent=2)}")
    assert output_beta.error_message is not None
    assert "JSON parsing failed" in output_beta.error_message or "LLM response was not valid JSON" in output_beta.error_message # Check for parsing error

    # Test Case 3: Valid JSON, no contacts found
    input_gamma = ContactExtractionInput(
        extracted_text="Test Company Gamma makes widgets. No contact info here.",
        company_name="Test Company Gamma",
        product_service_offered="High-Quality Widgets"
    )
    output_gamma = agent.process(input_gamma)
    logger.info(f"\nTest Case 3 (Gamma - No Contacts):")
    logger.info(f"  Output: {output_gamma.model_dump_json(indent=2)}")
    assert output_gamma.error_message is None
    assert output_gamma.emails_found == []
    assert output_gamma.instagram_profiles_found == []
    assert output_gamma.confidence_score == 0.2
    assert len(output_gamma.suggested_search_queries) > 0
    
    logger.info("\nAll mock tests for ContactExtractionAgent completed.")

```
