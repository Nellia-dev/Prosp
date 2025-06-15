from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import re # Ensure re is imported
import json # Ensure json is imported

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase
# Assuming ContactExtractionOutput might be used directly or its structure is known
# from agents.contact_extraction_agent import ContactExtractionOutput # Or define a simpler one if needed

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000 # Max length for combined inputs to LLM

class ContactDetailsInput(BaseModel): # Simplified for this agent, or use ContactExtractionOutput
    emails_found: List[str] = Field(default_factory=list)
    instagram_profiles_found: List[str] = Field(default_factory=list)
    # Add other fields if necessary, like LinkedIn, phone, etc.

class B2BPersonalizedMessageInput(BaseModel):
    final_action_plan_text: str
    customized_value_propositions_text: str
    contact_details: ContactDetailsInput
    product_service_offered: str
    lead_url: str
    company_name: str
    persona_fictional_name: str # Extracted from persona profile earlier
    # Adding tone_of_voice and opening_question if they come from final_action_plan_text parsing or specific fields
    # For now, assuming they are embedded within final_action_plan_text for the LLM to extract/use.

class B2BPersonalizedMessageOutput(BaseModel):
    crafted_message_channel: str = "N/A"
    crafted_message_subject: Optional[str] = None
    crafted_message_body: str = "Não foi possível gerar a mensagem."
    # Added for more structured output from LLM, if we go full JSON for all fields
    # opening_hook: Optional[str] = None
    # key_talking_points_covered: List[str] = Field(default_factory=list)
    # final_call_to_action_used: Optional[str] = None
    error_message: Optional[str] = None

class B2BPersonalizedMessageAgent(BaseAgent[B2BPersonalizedMessageInput, B2BPersonalizedMessageOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def _determine_channel_and_contact(self, contact_details: ContactDetailsInput) -> tuple[str, Optional[str]]:
        """Determines the best channel and contact point."""
        if contact_details.emails_found:
            return "Email", contact_details.emails_found[0]
        if contact_details.instagram_profiles_found:
            return "Instagram DM", contact_details.instagram_profiles_found[0]
        # Add WhatsApp, LinkedIn, Phone logic here if contact_details expands
        return "N/A", None

    def process(self, input_data: B2BPersonalizedMessageInput) -> B2BPersonalizedMessageOutput:
        determined_channel, contact_target = self._determine_channel_and_contact(input_data.contact_details)

        llm_output_subject = None
        llm_output_body = "Não foi possível gerar a mensagem." # Default body
        error_message = None

        if determined_channel == "N/A" or not contact_target:
            error_message = "Nenhum canal de contato adequado encontrado ou informação de contato ausente."
            self.logger.warning(f"{self.name}: {error_message} for {input_data.company_name}")
            return B2BPersonalizedMessageOutput(
                crafted_message_channel=determined_channel,
                error_message=error_message
            )

        try:
            # Truncate inputs to avoid exceeding LLM token limits
            # Approximate character allocation
            char_limit_action_plan = GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 3
            char_limit_value_props = GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 3
            # Remaining for prompt structure, other fixed inputs, and response buffer

            tr_action_plan = self._truncate_text(input_data.final_action_plan_text, char_limit_action_plan)
            tr_value_props = self._truncate_text(input_data.customized_value_propositions_text, char_limit_value_props)

            # Refined prompt asking for JSON
            prompt_template = """
                Você é um Redator de Copy B2B Sênior e Estrategista de Engajamento, especialista em criar mensagens de primeiro contato altamente personalizadas e eficazes para o mercado brasileiro.
                Seu objetivo é redigir uma mensagem para {persona_fictional_name} da empresa {company_name}, a ser enviada através do canal '{channel}'.
                O contato alvo é: {contact_target}.

                Contexto Detalhado (Extraído de análises anteriores):
                1. PLANO DE AÇÃO FINAL (contém a estratégia de abordagem, tom de voz, sequência de canais, pergunta de abertura):
                   \"\"\"
                   {final_action_plan_text}
                   \"\"\"

                2. PROPOSTAS DE VALOR PERSONALIZADAS (contém os ganchos e benefícios diretos para a persona):
                   \"\"\"
                   {customized_value_propositions_text}
                   \"\"\"

                3. INFORMAÇÕES ADICIONAIS DO LEAD:
                   - Produto/Serviço Oferecido por nós: {product_service_offered}
                   - URL do Lead: {lead_url}
                   - Empresa do Lead: {company_name}
                   - Nome da Persona (para saudação): {persona_fictional_name}

                INSTRUÇÕES PARA CRIAÇÃO DA MENSAGEM (FORMATO JSON):
                Com base em TODO o contexto fornecido, sua tarefa é criar os componentes da mensagem.
                Adapte o tom de voz e a pergunta de abertura sugeridos no "PLANO DE AÇÃO FINAL".
                Incorpore elementos das "PROPOSTAS DE VALOR PERSONALIZADAS" para relevância.
                A mensagem deve ser concisa, clara, e ter um Call to Action (CTA) de baixo atrito, conforme o plano.
                Considere as nuances culturais do mercado brasileiro (ex: comunicação mais relacional).

                Responda EXCLUSIVAMENTE com um objeto JSON válido, contendo os seguintes campos:
                {{
                    "crafted_message_subject": "string | null (OBRIGATÓRIO: Se o canal for 'Email', crie um assunto conciso, atraente e personalizado, com no máximo 10-12 palavras. Se o canal não for 'Email', este campo DEVE ser null.)",
                    "crafted_message_body": "string (OBRIGATÓRIO: O corpo completo da mensagem. Personalize a saudação para {persona_fictional_name}. Adapte o conteúdo para o canal '{channel}'. Para 'Instagram DM' ou 'WhatsApp Message', use parágrafos curtos, quebras de linha para facilitar a leitura, e emojis com moderação se alinhado ao tom de voz. Para 'Email', mantenha um formato profissional.)"
                }}
                NÃO inclua explicações ou texto adicional fora do objeto JSON.
            """

            formatted_prompt = prompt_template.format(
                persona_fictional_name=input_data.persona_fictional_name,
                company_name=input_data.company_name,
                channel=determined_channel,
                contact_target=contact_target,
                final_action_plan_text=tr_action_plan,
                customized_value_propositions_text=tr_value_props,
                product_service_offered=input_data.product_service_offered,
                lead_url=input_data.lead_url
            )

            llm_response_str = self.generate_llm_response(formatted_prompt)

            if llm_response_str:
                # Primary parsing method is now JSON
                parsed_data = self.parse_llm_json_response(llm_response_str, B2BPersonalizedMessageOutput)

                if parsed_data and not parsed_data.error_message:
                    llm_output_subject = parsed_data.crafted_message_subject
                    llm_output_body = parsed_data.crafted_message_body
                    
                    # Validate channel-specific constraints
                    if determined_channel != "Email" and llm_output_subject is not None:
                        self.logger.warning(f"LLM provided subject for non-email channel ({determined_channel}). Setting subject to None.")
                        llm_output_subject = None
                    if determined_channel == "Email" and llm_output_subject is None :
                         self.logger.warning(f"LLM did not provide subject for Email channel. Defaulting or leaving as None.")
                         # Potentially add a default subject here if desired, or let it be None
                         # llm_output_subject = f"Oportunidade para {input_data.company_name}"


                else: # JSON parsing failed or returned model with error_message
                    error_message = parsed_data.error_message if parsed_data else "JSON parsing of LLM response failed."
                    self.logger.warning(f"{self.name}: {error_message}. Raw LLM response: {llm_response_str[:500]}")
                    # No regex fallback anymore, rely on prompt for JSON.
                    # If JSON fails, the default body "Não foi possível gerar a mensagem." will be used.
            else:
                error_message = "LLM call returned no response or an empty response."
                self.logger.warning(f"{self.name} received an empty response from LLM for URL: {input_data.lead_url}")
        
        except Exception as e:
            self.logger.error(f"An unexpected error occurred in {self.name} for {input_data.company_name}: {e}", exc_info=True)
            error_message = f"An unexpected error occurred: {str(e)}"

        return B2BPersonalizedMessageOutput(
            crafted_message_channel=determined_channel,
            crafted_message_subject=llm_output_subject,
            crafted_message_body=llm_output_body,
            error_message=error_message
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
            channel_match = re.search(r"canal '([^']*)'", prompt)
            channel = channel_match.group(1) if channel_match else "Email"

            if channel == "Email":
                return json.dumps({
                    "crafted_message_subject": "Otimizando Operações na Empresa Exemplo Pós-Expansão com IA",
                    "crafted_message_body": (
                        "Olá Carlos Mendes,\n\n"
                        "Com a recente e empolgante expansão da Empresa Exemplo para o mercado LATAM, sei que escalar operações de forma eficiente é um grande foco. Muitas empresas de TI, nesse estágio, buscam otimizar processos internos para sustentar o crescimento sem sobrecarregar a equipe – algo que Nossas Soluções Incríveis de IA podem facilitar significativamente.\n\n"
                        "Nossa plataforma de IA não só automatiza tarefas repetitivas, mas aprende e se adapta aos fluxos de trabalho da Empresa Exemplo, garantindo que os desafios da expansão se transformem em vantagens competitivas.\n\n"
                        "Você teria 15 minutos na próxima semana para uma breve conversa sobre como podemos ajudar a Empresa Exemplo a navegar por esses desafios de crescimento com mais eficiência?\n\n"
                        "Atenciosamente,\n[Seu Nome/Empresa]"
                    )
                })
            elif channel == "Instagram DM":
                return json.dumps({
                    "crafted_message_subject": None,
                    "crafted_message_body": (
                        "Olá Carlos! 👋 Vi que a Empresa Exemplo está a todo vapor com a expansão para LATAM! 🚀\n\n"
                        "Muitas empresas de TI nesse pique buscam formas inteligentes de escalar as operações sem dor de cabeça. Nossa IA pode dar uma força nisso, automatizando processos e liberando sua equipe pra focar no que realmente importa.\n\n"
                        "Que tal um papo rápido de 10 min pra te mostrar como? 😉"
                    )
                })
            return json.dumps({"crafted_message_subject": None, "crafted_message_body": "Mock response for other channels."})

    logger.info("Running mock test for B2BPersonalizedMessageAgent (Email)...")
    mock_llm_email = MockLLMClient()
    agent_email = B2BPersonalizedMessageAgent(
        name="B2BEmailMessageAgent",
        description="Generates personalized B2B email messages.",
        llm_client=mock_llm_email
    )

    test_action_plan = "Plano: Email para Carlos com foco em eficiência na expansão. Pergunta de abertura: Como priorizam otimização para escalar?"
    test_value_props = "[{\"proposition_title\":\"Escalabilidade Eficiente com IA\",\"detailed_explanation\":\"Nossa plataforma de IA permite que a Empresa Exemplo escale suas operações LATAM de forma ágil, automatizando X e Y, resultando em Z% de economia.\",\"evidence_or_example\":\"Case de Sucesso: Empresa GlobalTech similar à Empresa Exemplo...\"},{\"proposition_title\":\"Modernização com ROI Comprovado\",\"detailed_explanation\":\"Implementar Nossas Soluções Incríveis de IA representa um passo estratégico para modernizar processos, com um ROI médio de X% para clientes do setor de TI em 6 meses.\",\"evidence_or_example\":\"Relatório de ROI do Gartner para automação inteligente.\"}]"
    test_contacts_email = ContactDetailsInput(emails_found=["carlos.mendes@empresaexemplo.com"], instagram_profiles_found=[])
    test_product = "Nossas Soluções Incríveis de IA para automação de processos"
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
    logger.info(f"Channel: {output_email.crafted_message_channel}")
    logger.info(f"Subject: {output_email.crafted_message_subject}")
    logger.info(f"Body: \n{output_email.crafted_message_body}")
    if output_email.error_message:
        logger.error(f"Error: {output_email.error_message}")
    assert output_email.crafted_message_channel == "Email"
    assert output_email.crafted_message_subject is not None and "Empresa Exemplo" in output_email.crafted_message_subject
    assert "Carlos Mendes" in output_email.crafted_message_body
    assert "Empresa Exemplo" in output_email.crafted_message_body
    assert output_email.error_message is None

    logger.info("\nRunning mock test for B2BPersonalizedMessageAgent (Instagram DM)...")
    mock_llm_insta = MockLLMClient()
    agent_insta = B2BPersonalizedMessageAgent(
        name="B2BInstagramMessageAgent",
        description="Generates personalized B2B Instagram DMs.",
        llm_client=mock_llm_insta
    )
    test_contacts_insta = ContactDetailsInput(emails_found=[], instagram_profiles_found=["@carlosmendes_exemploinsta"])
    
    input_data_insta = B2BPersonalizedMessageInput(
        final_action_plan_text=test_action_plan.replace("Email", "Instagram DM"),
        customized_value_propositions_text=test_value_props,
        contact_details=test_contacts_insta,
        product_service_offered=test_product,
        lead_url=test_url,
        company_name=test_company,
        persona_fictional_name=test_persona_name
    )
    output_insta = agent_insta.process(input_data_insta)
    logger.info(f"Channel: {output_insta.crafted_message_channel}")
    logger.info(f"Subject: {output_insta.crafted_message_subject}")
    logger.info(f"Body: \n{output_insta.crafted_message_body}")
    if output_insta.error_message:
        logger.error(f"Error: {output_insta.error_message}")
    assert output_insta.crafted_message_channel == "Instagram DM"
    assert output_insta.crafted_message_subject is None
    assert "Carlos!" in output_insta.crafted_message_body
    assert output_insta.error_message is None
    
    logger.info("\nMock tests completed successfully.")

```
