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
    crafted_message_body: str = "Message could not be generated." # Translated default
    # Added for more structured output from LLM, if we go full JSON for all fields
    # opening_hook: Optional[str] = None
    # key_talking_points_covered: List[str] = Field(default_factory=list)
    # final_call_to_action_used: Optional[str] = None
    error_message: Optional[str] = None

class B2BPersonalizedMessageAgent(BaseAgent[B2BPersonalizedMessageInput, B2BPersonalizedMessageOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, output_language: str = "en-US", **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)
        self.output_language = output_language

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
        llm_output_body = "Message could not be generated." # Default body, translated
        error_message = None

        if determined_channel == "N/A" or not contact_target:
            error_message = "No suitable contact channel found or contact information missing." # Translated
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

            # Refined prompt asking for JSON, now in English
            prompt_template = """
                You are a Senior B2B Copywriter and Engagement Strategist, specializing in crafting highly personalized and effective first-contact messages for the target market (e.g., Brazilian market - adapt as needed).
                Your objective is to draft a message for {persona_fictional_name} at {company_name}, to be sent via the '{channel}' channel.
                The target contact is: {contact_target}.

                Detailed Context (Extracted from previous analyses):
                1. FINAL ACTION PLAN (contains approach strategy, tone of voice, channel sequence, opening question):
                   \"\"\"
                   {final_action_plan_text}
                   \"\"\"

                2. CUSTOMIZED VALUE PROPOSITIONS (contains hooks and direct benefits for the persona):
                   \"\"\"
                   {customized_value_propositions_text}
                   \"\"\"

                3. ADDITIONAL LEAD INFORMATION:
                   - Product/Service We Offer: {product_service_offered}
                   - Lead URL: {lead_url}
                   - Lead Company: {company_name}
                   - Persona Name (for salutation): {persona_fictional_name}

                INSTRUCTIONS FOR MESSAGE CREATION (JSON FORMAT):
                Based on ALL provided context, your task is to create the message components.
                Adapt the tone of voice and opening question suggested in the "FINAL ACTION PLAN".
                Incorporate elements from the "CUSTOMIZED VALUE PROPOSITIONS" for relevance.
                The message should be concise, clear, and have a low-friction Call to Action (CTA), as per the plan.
                Consider cultural nuances of the target market (e.g., more relational communication for Brazil).

                Respond EXCLUSIVELY with a valid JSON object, containing the following fields:
                {{
                    "crafted_message_subject": "string | null (REQUIRED: If the channel is 'Email', create a concise, engaging, and personalized subject line, max 10-12 words. If the channel is not 'Email', this field MUST be null.)",
                    "crafted_message_body": "string (REQUIRED: The full body of the message. Personalize the greeting for {persona_fictional_name}. Adapt content for the '{channel}' channel. For 'Instagram DM' or 'WhatsApp Message', use short paragraphs, line breaks for readability, and emojis sparingly if aligned with the tone. For 'Email', maintain a professional format.)"
                }}
                DO NOT include explanations or additional text outside the JSON object.
            """

            language_instruction = f"\n\nImportant: Generate your entire response, including all textual content and string values within any JSON structure, strictly in the following language: {self.output_language}. Do not include any English text unless it is part of the original input data that should be preserved as is."

            final_prompt = prompt_template.format(
                persona_fictional_name=input_data.persona_fictional_name,
                company_name=input_data.company_name,
                channel=determined_channel,
                contact_target=contact_target,
                final_action_plan_text=tr_action_plan,
                customized_value_propositions_text=tr_value_props,
                product_service_offered=input_data.product_service_offered,
                lead_url=input_data.lead_url
            ) + language_instruction

            llm_response_str = self.generate_llm_response(final_prompt, output_language=self.output_language)

            if llm_response_str:
                parsed_data = self.parse_llm_json_response(llm_response_str, B2BPersonalizedMessageOutput)

                if parsed_data and not parsed_data.error_message:
                    llm_output_subject = parsed_data.crafted_message_subject
                    llm_output_body = parsed_data.crafted_message_body
                    
                    if determined_channel != "Email" and llm_output_subject is not None:
                        self.logger.warning(f"LLM provided subject for non-email channel ({determined_channel}). Setting subject to None.")
                        llm_output_subject = None
                    if determined_channel == "Email" and llm_output_subject is None :
                         self.logger.warning(f"LLM did not provide subject for Email channel. Defaulting or leaving as None.")
                         # llm_output_subject = f"Opportunity for {input_data.company_name}" # Example default

                else:
                    error_message = parsed_data.error_message if parsed_data else "JSON parsing of LLM response failed." # Already English
                    self.logger.warning(f"{self.name}: {error_message}. Raw LLM response: {llm_response_str[:500]}")
            else:
                error_message = "LLM call returned no response or an empty response." # Already English
                self.logger.warning(f"{self.name} received an empty response from LLM for URL: {input_data.lead_url}")
        
        except Exception as e:
            self.logger.error(f"An unexpected error occurred in {self.name} for {input_data.company_name}: {e}", exc_info=True)
            error_message = f"An unexpected error occurred: {str(e)}" # Already English

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

    class MockLLMClient(LLMClientBase): # Assuming LLMClientBase is correctly imported/defined
        def __init__(self, api_key: str = "mock_key", **kwargs ):
            # super().__init__(api_key) # Depends on LLMClientBase
            self.api_key = api_key


        def generate_text_response(self, prompt: str, output_language: str = "en-US") -> Optional[str]:
            logger.debug(f"MockLLMClient received prompt (lang: {output_language}):\n{prompt[:700]}...")
            channel_match = re.search(r"channel '{channel}'.*?\n\n                The target contact is: {contact_target}.*?\n\n                Detailed Context".replace("{channel}", "([^']*)").replace("{contact_target}", "([^']*)"), prompt, re.DOTALL) # More robust extraction for channel

            channel = "Email" # Default
            if channel_match and channel_match.group(1):
                channel = channel_match.group(1)
            else: # Fallback if the more specific regex above fails
                 channel_match_simple = re.search(r"through the '([^']*)' channel", prompt)
                 if channel_match_simple:
                     channel = channel_match_simple.group(1)

            logger.debug(f"MockLLM determined channel: {channel}")

            # Check if language instruction is present
            if f"strictly in the following language: {output_language}" not in prompt:
                logger.error(f"Language instruction for '{output_language}' missing in prompt!")

            if channel == "Email":
                # Example in English
                return json.dumps({
                    "crafted_message_subject": f"Optimizing Operations at {input_data_email.company_name} Post-Expansion with AI",
                    "crafted_message_body": (
                        f"Hello {input_data_email.persona_fictional_name},\n\n"
                        f"With {input_data_email.company_name}'s recent and exciting expansion into the LATAM market, I know that scaling operations efficiently is a major focus. Many IT companies at this stage look to optimize internal processes to sustain growth without overburdening the team – something Our Incredible AI Solutions can significantly facilitate.\n\n"
                        f"Our AI platform not only automates repetitive tasks but also learns and adapts to {input_data_email.company_name}'s workflows, ensuring that expansion challenges turn into competitive advantages.\n\n"
                        f"Would you have 15 minutes next week for a brief conversation about how we can help {input_data_email.company_name} navigate these growth challenges more efficiently?\n\n"
                        "Sincerely,\n[Your Name/Company]"
                    )
                })
            elif channel == "Instagram DM":
                 # Example in English
                return json.dumps({
                    "crafted_message_subject": None,
                    "crafted_message_body": (
                        f"Hi {input_data_insta.persona_fictional_name}! 👋 Saw {input_data_insta.company_name} is making big moves with the LATAM expansion! 🚀\n\n"
                        "Many IT companies in this phase are looking for smart ways to scale operations smoothly. Our AI can help with that, automating processes and freeing up your team to focus on what really matters.\n\n"
                        "How about a quick 10-min chat to show you how? 😉"
                    )
                })
            return json.dumps({"crafted_message_subject": None, "crafted_message_body": "Mock response for other channels."})

    logger.info("Running mock test for B2BPersonalizedMessageAgent (Email)...")
    mock_llm_email = MockLLMClient()
    agent_email = B2BPersonalizedMessageAgent(
        name="B2BEmailMessageAgent",
        description="Generates personalized B2B email messages.",
        llm_client=mock_llm_email,
        output_language="en-US" # Testing with English
    )

    # Test data in English
    test_action_plan = "Plan: Email Carlos focusing on efficiency in expansion. Opening question: How do you prioritize optimization to scale?"
    test_value_props = "[{\"proposition_title\":\"Efficient Scalability with AI\",\"detailed_explanation\":\"Our AI platform allows Example Inc. to scale its LATAM operations agilely, automating X and Y, resulting in Z% savings.\",\"evidence_or_example\":\"Success Story: GlobalTech similar to Example Inc....\"},{\"proposition_title\":\"Modernization with Proven ROI\",\"detailed_explanation\":\"Implementing Our Incredible AI Solutions represents a strategic step to modernize processes, with an average ROI of X% for IT sector clients in 6 months.\",\"evidence_or_example\":\"Gartner ROI report for intelligent automation.\"}]"
    test_contacts_email = ContactDetailsInput(emails_found=["carlos.mendes@exampleinc.com"], instagram_profiles_found=[])
    test_product = "Our Incredible AI Solutions for process automation"
    test_url = "http://www.exampleinc.com"
    test_company = "Example Inc." # Changed to English for consistency
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
    assert output_email.crafted_message_subject is not None and "Example Inc." in output_email.crafted_message_subject
    assert "Carlos Mendes" in output_email.crafted_message_body
    assert "Example Inc." in output_email.crafted_message_body
    assert output_email.error_message is None

    logger.info("\nRunning mock test for B2BPersonalizedMessageAgent (Instagram DM)...")
    mock_llm_insta = MockLLMClient()
    agent_insta = B2BPersonalizedMessageAgent(
        name="B2BInstagramMessageAgent",
        description="Generates personalized B2B Instagram DMs.",
        llm_client=mock_llm_insta,
        output_language="en-US" # Testing with English
    )
    test_contacts_insta = ContactDetailsInput(emails_found=[], instagram_profiles_found=["@carlosmendes_exampleinsta"])
    
    input_data_insta = B2BPersonalizedMessageInput(
        final_action_plan_text=test_action_plan.replace("Email", "Instagram DM"), # Adjust action plan for channel
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
