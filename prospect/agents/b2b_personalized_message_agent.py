from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase
# Assuming ContactExtractionOutput might be used directly or its structure is known
# from agents.contact_extraction_agent import ContactExtractionOutput # Or define a simpler one if needed

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class ContactDetailsInput(BaseModel): # Simplified for this agent, or use ContactExtractionOutput
    emails_found: List[str] = Field(default_factory=list)
    instagram_profiles_found: List[str] = Field(default_factory=list)
    # Add other fields if necessary, like LinkedIn, phone, etc.

class B2BPersonalizedMessageInput(BaseModel):
    final_action_plan_text: str
    customized_value_propositions_text: str
    contact_details: ContactDetailsInput # Using the simplified structure
    product_service_offered: str
    lead_url: str
    company_name: str
    persona_fictional_name: str # Extracted from persona profile earlier

class B2BPersonalizedMessageOutput(BaseModel):
    crafted_message_channel: str = "N/A"
    crafted_message_subject: Optional[str] = None
    crafted_message_body: str = "Não foi possível gerar a mensagem."
    error_message: Optional[str] = None

class B2BPersonalizedMessageAgent(BaseAgent[B2BPersonalizedMessageInput, B2BPersonalizedMessageOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def _determine_channel_and_contact(self, contact_details: ContactDetailsInput) -> tuple[str, Optional[str]]:
        """Determines the best channel and contact point."""
        # Simplified logic from cw.py's criar_mensagem_personalizada
        if contact_details.emails_found:
            return "Email", contact_details.emails_found[0]
        if contact_details.instagram_profiles_found:
            # Assuming the first profile is the target. Might need more sophisticated selection.
            # The original cw.py uses the @handle directly.
            return "Instagram", contact_details.instagram_profiles_found[0]
        # Add more channels here if contact_details expands (e.g., LinkedIn, WhatsApp)
        return "N/A", None

    def process(self, input_data: B2BPersonalizedMessageInput) -> B2BPersonalizedMessageOutput:
        crafted_message_channel = "N/A"
        crafted_message_subject = None
        crafted_message_body = "Não foi possível gerar a mensagem."
        error_message = None

        try:
            channel, contact_info = self._determine_channel_and_contact(input_data.contact_details)
            crafted_message_channel = channel

            if channel == "N/A" or not contact_info:
                error_message = "Nenhum canal de contato adequado encontrado."
                return B2BPersonalizedMessageOutput(
                    crafted_message_channel=channel,
                    error_message=error_message
                )

            # Truncate inputs
            tr_action_plan = self._truncate_text(input_data.final_action_plan_text, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 3)
            tr_value_props = self._truncate_text(input_data.customized_value_propositions_text, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 3)

            channel_specific_instructions = ""
            if channel == "Email":
                channel_specific_instructions = (
                    "Formato para Email:\n"
                    "ASSUNTO: [Seu Assunto Conciso e Impactante Aqui]\n"
                    "CORPO:\n[Corpo do Email Personalizado Aqui]"
                )
            elif channel == "Instagram":
                channel_specific_instructions = (
                    "Formato para Instagram (Mensagem Direta):\n"
                    "CORPO:\n[Corpo da Mensagem Direta Personalizada Aqui]\n"
                    "(Lembre-se de ser mais informal e direto no Instagram, usando quebras de linha para facilitar a leitura. Emojis com moderação)."
                )
            # Add other channels as needed

            prompt_template = """
                Você é um Redator de Copy B2B Sênior, especialista em criar mensagens de primeiro contato altamente personalizadas e eficazes.
                Seu objetivo é redigir uma mensagem para {persona_fictional_name} da {company_name} através do canal {channel}, utilizando o contato {contact_info}.

                PLANO DE AÇÃO FINAL (contém a estratégia de abordagem, tom de voz, sequência de canais, pergunta de abertura):
                {final_action_plan_text}

                PROPOSTAS de VALOR PERSONALIZADAS (contém os ganchos e benefícios diretos para a persona):
                {customized_value_propositions_text}

                INFORMAÇÕES ADICIONAIS:
                Produto/Serviço Oferecido: {product_service_offered}
                URL do Lead: {lead_url}
                Empresa do Lead: {company_name}
                Nome da Persona: {persona_fictional_name}

                INSTRUÇÕES PARA CRIAÇÃO DA MENSAGEM:
                1.  Adapte o tom de voz e a pergunta de abertura do "Plano de Ação Final".
                2.  Incorpore elementos das "Propostas de Valor Personalizadas" para tornar a mensagem relevante e impactante.
                3.  Siga as diretrizes de formatação para o canal {channel} abaixo.
                4.  A mensagem deve ser concisa, clara e ter um Call to Action (CTA) de baixo atrito, conforme sugerido no plano de ação.
                5.  Personalize a saudação para {persona_fictional_name}.
                6.  Se for um email, crie um assunto atraente. Para Instagram DMs, não há assunto.

                {channel_specific_instructions}

                MENSAGEM GERADA:
            """

            formatted_prompt = prompt_template.format(
                persona_fictional_name=input_data.persona_fictional_name,
                company_name=input_data.company_name,
                channel=channel,
                contact_info=contact_info,
                final_action_plan_text=tr_action_plan,
                customized_value_propositions_text=tr_value_props,
                product_service_offered=input_data.product_service_offered,
                lead_url=input_data.lead_url,
                channel_specific_instructions=channel_specific_instructions
            )

            llm_response = self.generate_llm_response(formatted_prompt)

            if llm_response_str:
                parsed_output = self.parse_llm_json_response(llm_response_str, B2BPersonalizedMessageOutput)

                if parsed_output.error_message:
                    self.logger.warning(f"B2BPersonalizedMessageAgent JSON parsing failed for channel {channel}. Raw: {llm_response_str[:300]}. Error: {parsed_output.error_message}")
                    # Fallback to trying to extract from raw string if specific fields are missing and error occurred
                    # This is tricky because parse_llm_json_response might return a model with defaults.
                    # We assume if error_message is set by parse_llm_json_response, the primary fields might be unset or default.
                    
                    # Basic regex fallback (less critical if LLM is reliable with JSON)
                    temp_body = parsed_output.crafted_message_body
                    temp_subject = parsed_output.crafted_message_subject

                    if channel == "Email" and (not temp_body or temp_body == "Não foi possível gerar a mensagem."):
                        subject_match_re = re.search(r"ASSUNTO:\s*(.*)", llm_response_str, re.IGNORECASE)
                        body_match_re = re.search(r"CORPO:\s*((.|\n)*)", llm_response_str, re.IGNORECASE)
                        if subject_match_re:
                             temp_subject = subject_match_re.group(1).strip()
                        if body_match_re:
                             temp_body = body_match_re.group(1).strip()
                        
                    elif channel == "Instagram" and (not temp_body or temp_body == "Não foi possível gerar a mensagem."):
                        body_match_re = re.search(r"CORPO:\s*((.|\n)*)", llm_response_str, re.IGNORECASE)
                        if body_match_re:
                            temp_body = body_match_re.group(1).strip()
                    
                    # Only override if regex found something and original parsing didn't for that field
                    final_subject = temp_subject if temp_subject and temp_subject != parsed_output.crafted_message_subject else parsed_output.crafted_message_subject
                    final_body = temp_body if temp_body and temp_body != "Não foi possível gerar a mensagem." else parsed_output.crafted_message_body
                    
                    return B2BPersonalizedMessageOutput(
                        crafted_message_channel=channel, # channel is determined before LLM call
                        crafted_message_subject=final_subject,
                        crafted_message_body=final_body,
                        error_message=parsed_output.error_message or "JSON parsing failed, used regex fallback if possible."
                    )
                
                # Ensure channel from input is preserved if parsing is successful but channel field is not part of JSON
                parsed_output.crafted_message_channel = channel 
                return parsed_output
            else:
                error_message = "LLM call returned no response or an empty response."
                # Fall through to return default B2BPersonalizedMessageOutput with this error
        
        except Exception as e:
            self.logger.error(f"An unexpected error occurred in {self.name}: {e}")
            import traceback
            import re # Ensure re is imported
            traceback.print_exc()
            error_message = f"An unexpected error occurred: {str(e)}"

        # Default return if other paths didn't hit (e.g. empty llm_response_str)
        return B2BPersonalizedMessageOutput(
            crafted_message_channel=crafted_message_channel, # This will be "N/A" if channel determination failed early
            crafted_message_subject=None,
            crafted_message_body="Não foi possível gerar a mensagem.",
            error_message=error_message
        )

if __name__ == '__main__':
    import re # Ensure re is imported for the main block too
    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str) -> Optional[str]:
            if "MENSAGEM GERADA:" in prompt:
                if "Email" in prompt:
                    return (
                        "MENSAGEM GERADA:\n"
                        "ASSUNTO: Otimizando Operações na Empresa Exemplo Pós-Expansão\n"
                        "CORPO:\n"
                        "Olá Carlos Mendes,\n\n"
                        "Com a recente e empolgante expansão da Empresa Exemplo para o mercado LATAM, sei que escalar operações de forma eficiente é um grande foco. Muitas empresas de TI, nesse estágio, buscam otimizar processos internos para sustentar o crescimento sem sobrecarregar a equipe – algo que Nossas Soluções Incríveis de IA podem facilitar significativamente.\n\n"
                        "Nossa plataforma de IA não só automatiza tarefas repetitivas, mas aprende e se adapta aos fluxos de trabalho da Empresa Exemplo, garantindo que os desafios da expansão se transformem em vantagens competitivas.\n\n"
                        "Você teria 15 minutos na próxima semana para uma breve conversa sobre como podemos ajudar a Empresa Exemplo a navegar por esses desafios de crescimento com mais eficiência?\n\n"
                        "Atenciosamente,\n[Seu Nome/Empresa]"
                    )
                elif "Instagram" in prompt:
                    return (
                        "MENSAGEM GERADA:\n"
                        "CORPO:\n"
                        "Olá Carlos! 👋 Vi que a Empresa Exemplo está a todo vapor com a expansão para LATAM! 🚀\n\n"
                        "Muitas empresas de TI nesse pique buscam formas inteligentes de escalar as operações sem dor de cabeça. Nossa IA pode dar uma força nisso, automatizando processos e liberando sua equipe pra focar no que realmente importa.\n\n"
                        "Que tal um papo rápido de 10 min pra te mostrar como? 😉"
                    )
            return "Resposta padrão do mock."

    print("Running mock test for B2BPersonalizedMessageAgent (Email)...")
    mock_llm_email = MockLLMClient()
    agent_email = B2BPersonalizedMessageAgent(
        name="B2BPersonalizedMessageAgent",
        description="Generates personalized B2B messages.",
        llm_client=mock_llm_email
    )

    test_action_plan = "Plano: Email para Carlos com foco em eficiência na expansão. Pergunta: Como priorizam otimização?"
    test_value_props = "VP1: Escale com IA. VP2: Modernize com ROI."
    test_contacts_email = ContactDetailsInput(emails_found=["carlos.mendes@empresaexemplo.com"], instagram_profiles_found=[])
    test_product = "Nossas Soluções Incríveis de IA"
    test_url = "http://www.empresaexemplo.com"
    test_company = "Empresa Exemplo"
    test_persona_name = "Carlos Mendes"

    input_data_email = B2BPersonalizedMessageInput(
        final_action_plan_text=test_action_plan,
        customized_value_propositions_text=test_value_props,
        contact_details=test_contacts_email,
        product_service_offered=test_product,
        lead_url=test_url,
        company_name=test_company,
        persona_fictional_name=test_persona_name
    )
    output_email = agent_email.process(input_data_email)
    print(f"Channel: {output_email.crafted_message_channel}")
    print(f"Subject: {output_email.crafted_message_subject}")
    print(f"Body: \n{output_email.crafted_message_body}")
    if output_email.error_message:
        print(f"Error: {output_email.error_message}")
    assert output_email.crafted_message_channel == "Email"
    assert output_email.crafted_message_subject is not None
    assert "Carlos Mendes" in output_email.crafted_message_body
    assert "Empresa Exemplo" in output_email.crafted_message_body
    assert output_email.error_message is None

    print("\nRunning mock test for B2BPersonalizedMessageAgent (Instagram)...")
    mock_llm_insta = MockLLMClient() # Can reuse if prompt drives behavior
    agent_insta = B2BPersonalizedMessageAgent(
        name="B2BPersonalizedMessageAgent",
        description="Generates personalized B2B messages.",
        llm_client=mock_llm_insta
    )
    test_contacts_insta = ContactDetailsInput(emails_found=[], instagram_profiles_found=["@carlosmendes_exemploinsta"])
    
    input_data_insta = B2BPersonalizedMessageInput(
        final_action_plan_text=test_action_plan.replace("Email", "Instagram DM"), # Adjust plan for context
        customized_value_propositions_text=test_value_props,
        contact_details=test_contacts_insta,
        product_service_offered=test_product,
        lead_url=test_url,
        company_name=test_company,
        persona_fictional_name=test_persona_name
    )
    output_insta = agent_insta.process(input_data_insta)
    print(f"Channel: {output_insta.crafted_message_channel}")
    print(f"Subject: {output_insta.crafted_message_subject}") # Should be None
    print(f"Body: \n{output_insta.crafted_message_body}")
    if output_insta.error_message:
        print(f"Error: {output_insta.error_message}")
    assert output_insta.crafted_message_channel == "Instagram"
    assert output_insta.crafted_message_subject is None
    assert "Carlos!" in output_insta.crafted_message_body # More informal
    assert output_insta.error_message is None
    
    print("\nMock tests completed.")
