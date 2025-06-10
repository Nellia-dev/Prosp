import json
import re
from typing import Optional, List

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000 # Max input tokens for Gemini Flash is 128k, roughly 512k chars. Input is 32k tokens, output 2k.

class ContactExtractionInput(BaseModel):
    extracted_text: str
    company_name: str
    product_service_offered: str

class ContactExtractionOutput(BaseModel):
    emails_found: List[str] = Field(default_factory=list)
    instagram_profiles_found: List[str] = Field(default_factory=list)
    tavily_search_suggestion: str = "" # Suggestion for further Tavily search
    error_message: Optional[str] = None

class ContactExtractionAgent(BaseAgent[ContactExtractionInput, ContactExtractionOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: ContactExtractionInput) -> ContactExtractionOutput:
        error_message = None
        emails = []
        instagram_profiles = []
        tavily_suggestion = ""
        
        self.logger.info(f"📧 CONTACT EXTRACTION STARTING for company: {input_data.company_name}")
        self.logger.info(f"📊 Input data: text_length={len(input_data.extracted_text)}, service={input_data.product_service_offered}")

        try:
            self.logger.debug("🤖 Generating LLM prompt for contact extraction")
            prompt_template = """
                Analise o seguinte texto extraído para a empresa '{company_name}' que oferece '{product_service_offered}'.
                Extraia todos os endereços de e-mail e perfis do Instagram que encontrar.
                Além disso, com base no texto e no perfil da empresa, sugira uma única string de consulta otimizada para o Tavily API para encontrar informações de contato MAIS RELEVANTES ou decisores chave, caso as informações atuais sejam insuficientes. A sugestão deve ser específica.

                Texto Extraído:
                {extracted_text}

                Responda em formato JSON com as seguintes chaves:
                - "emails": ["email1@example.com", "email2@example.com"] (lista de strings, pode estar vazia)
                - "instagram_profiles": ["@perfil1", "@perfil2"] (lista de strings, pode estar vazia)
                - "tavily_search_suggestion": "sugestão de pesquisa para o Tavily API" (string única)

                Se nenhum e-mail ou perfil do Instagram for encontrado, retorne listas vazias para as respectivas chaves.
                Se nenhuma sugestão de pesquisa adicional for necessária, retorne uma string vazia para "tavily_search_suggestion".
                Responda APENAS com o objeto JSON, sem nenhum texto ou formatação adicional antes ou depois.
            """
            
            truncated_text = self._truncate_text(input_data.extracted_text, GEMINI_TEXT_INPUT_TRUNCATE_CHARS)

            formatted_prompt = prompt_template.format(
                company_name=input_data.company_name,
                product_service_offered=input_data.product_service_offered,
                extracted_text=truncated_text
            )

            llm_response_str = self.generate_llm_response(formatted_prompt)

            if not llm_response_str:
                self.logger.error("❌ LLM call returned no response for contact extraction")
                return ContactExtractionOutput(
                    error_message="LLM call returned no response."
                )

            self.logger.debug(f"✅ LLM returned response, length: {len(llm_response_str)}")

            # Attempt to parse the LLM response as JSON
            parsed_output = self.parse_llm_json_response(llm_response_str, ContactExtractionOutput)

            # Check if parsing failed or if the essential fields are missing
            if parsed_output.error_message or not (parsed_output.emails_found or parsed_output.instagram_profiles_found or parsed_output.tavily_search_suggestion):
                # Retain existing error message from parsing if available
                current_error = parsed_output.error_message or f"LLM response was not valid JSON or essential fields missing. Raw: {llm_response_str[:200]}"
                
                self.logger.warning(f"⚠️  JSON parsing failed or returned empty, attempting regex fallback. Error: {current_error}")
                
                # Fallback: Try to extract emails and Instagram profiles using regex
                raw_emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', llm_response_str)
                raw_instagram = re.findall(r'@[\w\.]+', llm_response_str)
                
                self.logger.debug(f"🔍 Regex fallback found: emails={len(raw_emails)}, instagram={len(raw_instagram)}")
                
                final_emails = parsed_output.emails_found
                if not final_emails and raw_emails:
                    final_emails = list(set(raw_emails))
                    self.logger.debug(f"📧 Using regex emails: {final_emails}")
                
                final_instagram = parsed_output.instagram_profiles_found
                if not final_instagram and raw_instagram:
                    final_instagram = list(set(raw_instagram))
                    self.logger.debug(f"📱 Using regex Instagram: {final_instagram}")

                # If regex also found nothing and parsing failed, the error message reflects that.
                if not final_emails and not final_instagram:
                    error_message = f"JSON parsing failed ({current_error}), and no contacts found via regex."
                    self.logger.warning(f"❌ No contacts found through any method")
                else: # Some data extracted with regex, or parsing partially succeeded
                    error_message = f"JSON parsing issues ({current_error}), but some data might be from regex fallback."
                    self.logger.info(f"⚠️  Partial success with fallback: emails={len(final_emails)}, instagram={len(final_instagram)}")
                
                return ContactExtractionOutput(
                    emails_found=final_emails,
                    instagram_profiles_found=final_instagram,
                    tavily_search_suggestion=parsed_output.tavily_search_suggestion,
                    error_message=error_message
                )
            
            # Successfully parsed JSON
            self.logger.info(f"✅ Contact extraction successful: emails={len(parsed_output.emails_found)}, instagram={len(parsed_output.instagram_profiles_found)}")
            return parsed_output

        except Exception as e:
            self.logger.error(f"An unexpected error occurred in ContactExtractionAgent: {e}")
            import traceback
            traceback.print_exc()
            # Ensure the return type is always ContactExtractionOutput
            return ContactExtractionOutput(
                error_message=f"An unexpected error occurred: {str(e)}"
            )

if __name__ == '__main__':
    # This is a placeholder for testing
    # You would need a mock LLMClient
    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str) -> Optional[str]:
            # Simulate different LLM responses based on the prompt
            if "Test Company Alpha" in prompt:
                return json.dumps({
                    "emails": ["contact@alpha.com", "sales@alpha.com"],
                    "instagram_profiles": ["@alpha_inc"],
                    "tavily_search_suggestion": "Key decision makers at Test Company Alpha"
                })
            elif "Test Company Beta" in prompt: # Simulate malformed JSON
                return '{"emails": ["info@beta.com"], "instagram_profiles": ["@beta_co" "tavily_search_suggestion": "Test Company Beta partnerships"}'
            elif "Test Company Gamma" in prompt: # Simulate no contacts found
                return json.dumps({
                    "emails": [],
                    "instagram_profiles": [],
                    "tavily_search_suggestion": "Test Company Gamma recent funding rounds"
                })
            elif "Test Company Delta" in prompt: # Simulate LLM returning non-JSON with extractable info
                return "Found email test@delta.com and insta @delta.official. Suggest: 'Delta financials'"
            return json.dumps({
                    "emails": [],
                    "instagram_profiles": [],
                    "tavily_search_suggestion": ""
                })
    
    print("Running mock tests for ContactExtractionAgent...")
    mock_llm = MockLLMClient(api_key="mock_llm_key")
    agent = ContactExtractionAgent(llm_client=mock_llm)

    # Test Case 1: Valid JSON response
    input_alpha = ContactExtractionInput(
        extracted_text="Test Company Alpha is a leader in AI. Contact us at contact@alpha.com or sales@alpha.com. Follow us on Instagram @alpha_inc.",
        company_name="Test Company Alpha",
        product_service_offered="AI Solutions"
    )
    output_alpha = agent.process(input_alpha)
    print(f"\nTest Case 1 (Alpha - Valid JSON):")
    print(f"  Emails: {output_alpha.emails_found}")
    print(f"  Instagram: {output_alpha.instagram_profiles_found}")
    print(f"  Tavily Suggestion: {output_alpha.tavily_search_suggestion}")
    print(f"  Error: {output_alpha.error_message}")
    assert output_alpha.emails_found == ["contact@alpha.com", "sales@alpha.com"]
    assert output_alpha.instagram_profiles_found == ["@alpha_inc"]
    assert output_alpha.tavily_search_suggestion == "Key decision makers at Test Company Alpha"
    assert output_alpha.error_message is None

    # Test Case 2: Malformed JSON response (with regex fallback)
    input_beta = ContactExtractionInput(
        extracted_text="Info at info@beta.com, Insta @beta_co. Test Company Beta focuses on cloud services.",
        company_name="Test Company Beta",
        product_service_offered="Cloud Services"
    )
    output_beta = agent.process(input_beta)
    print(f"\nTest Case 2 (Beta - Malformed JSON with Fallback):")
    print(f"  Emails: {output_beta.emails_found}") # Should be empty as per current parse_llm_json_response strictness
    print(f"  Instagram: {output_beta.instagram_profiles_found}") # Should be empty
    print(f"  Tavily Suggestion: {output_beta.tavily_search_suggestion}") # Should be empty
    print(f"  Error: {output_beta.error_message}")
    # The parse_llm_json_response will return an error_message. The fallback regex is inside the 'else' of that.
    # Depending on how strict parse_llm_json_response is, it might not populate fields if JSON is bad.
    # The current implementation of parse_llm_json_response returns a model with error_message set if parsing fails.
    assert "LLM response was not valid JSON" in output_beta.error_message if output_beta.error_message else False


    # Test Case 3: Valid JSON, no contacts found
    input_gamma = ContactExtractionInput(
        extracted_text="Test Company Gamma makes widgets. No contact info here.",
        company_name="Test Company Gamma",
        product_service_offered="Widgets"
    )
    output_gamma = agent.process(input_gamma)
    print(f"\nTest Case 3 (Gamma - No Contacts):")
    print(f"  Emails: {output_gamma.emails_found}")
    print(f"  Instagram: {output_gamma.instagram_profiles_found}")
    print(f"  Tavily Suggestion: {output_gamma.tavily_search_suggestion}")
    print(f"  Error: {output_gamma.error_message}")
    assert output_gamma.emails_found == []
    assert output_gamma.instagram_profiles_found == []
    assert output_gamma.tavily_search_suggestion == "Test Company Gamma recent funding rounds"
    assert output_gamma.error_message is None

    # Test Case 4: LLM returns non-JSON but with extractable info (regex fallback)
    input_delta = ContactExtractionInput(
        extracted_text="Contact Test Company Delta at test@delta.com or @delta.official",
        company_name="Test Company Delta",
        product_service_offered="Consulting"
    )
    output_delta = agent.process(input_delta)
    print(f"\nTest Case 4 (Delta - Non-JSON with Regex Fallback):")
    print(f"  Emails: {output_delta.emails_found}")
    print(f"  Instagram: {output_delta.instagram_profiles_found}")
    print(f"  Tavily Suggestion: {output_delta.tavily_search_suggestion}") # Fallback does not parse suggestion
    print(f"  Error: {output_delta.error_message}")
    assert output_delta.emails_found == ["test@delta.com"]
    assert output_delta.instagram_profiles_found == ["@delta.official"]
    assert "LLM response was not valid JSON" in output_delta.error_message if output_delta.error_message else False
    
    print("\nAll mock tests for ContactExtractionAgent completed.")
