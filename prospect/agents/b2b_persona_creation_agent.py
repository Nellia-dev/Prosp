from typing import Optional
from pydantic import BaseModel

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000 # Assuming this is a reasonable limit for the combined context

class B2BPersonaCreationInput(BaseModel):
    lead_analysis: str
    product_service_offered: str
    lead_url: str

class B2BPersonaCreationOutput(BaseModel):
    persona_profile: str
    error_message: Optional[str] = None

class B2BPersonaCreationAgent(BaseAgent[B2BPersonaCreationInput, B2BPersonaCreationOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, output_language: str = "en-US"):
        super().__init__(name=name, description=description, llm_client=llm_client)
        self.output_language = output_language

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: B2BPersonaCreationInput) -> B2BPersonaCreationOutput:
        persona_profile = ""
        error_message = None

        try:
            # Consider the total length of content being inserted into the prompt
            # For simplicity, truncating lead_analysis primarily.
            # A more sophisticated approach might budget characters for each section.
            truncated_analysis = self._truncate_text(input_data.lead_analysis, GEMINI_TEXT_INPUT_TRUNCATE_CHARS - 2000) # Reserve ~2k for rest of prompt
            
            # Refined prompt_template, now in English and with language instruction
            prompt_template = """
                You are a B2B Marketing and Persona Creation Specialist, with a focus on the target market (e.g., Brazilian market - adapt based on context). Your task is to create a detailed narrative persona profile for a key decision-maker, based on lead analysis, the product/service your company offers, and the lead's URL.

                LEAD ANALYSIS (provided by our intelligence team):
                \"\"\"
                {lead_analysis}
                \"\"\"

                OUR PRODUCT/SERVICE (that we want to present to this persona):
                "{product_service_offered}"

                LEAD URL (for your reference and additional context, if needed):
                {lead_url}

                INSTRUCTIONS FOR CREATING THE PERSONA PROFILE:
                Develop a cohesive and detailed narrative profile that brings this decision-maker to life. The profile should be written in the specified output language and specifically adapted to the relevant business context (e.g., Brazilian business context if output_language is 'pt-BR').

                The profile should cover, in an integrated and fluid manner, the following aspects:
                1.  **Fictional Name (appropriate for the target market) and Likely Role:** Assign a common name in the target market and the most probable job title for this decision-maker, based on the lead analysis.
                2.  **Key Responsibilities and Daily Challenges:** Describe their key functions and the obstacles they regularly face.
                3.  **Professional Goals and Motivations:** What they seek to achieve in their career and what drives them.
                4.  **B2B Search and Decision Behavior:** How this persona typically seeks solutions for their business challenges and what factors influence their purchasing decisions.
                5.  **Communication Style and Preferred Channels:** How they prefer to be approached and which professional communication channels they use most (e.g., LinkedIn, formal email, WhatsApp for close contacts).
                6.  **Specific Value Proposition:** How OUR PRODUCT/SERVICE ("{product_service_offered}") can specifically help this persona overcome their challenges and achieve their goals. Be clear and direct in this part.

                OUTPUT STYLE AND FORMAT:
                - The profile should be a **running text (narrative)**, descriptive and engaging.
                - **Do not use JSON format** or any other formal data structure.
                - Keep the text concise, ideally with a maximum of **350 words**, ensuring all 6 points above are covered.
                - The tone should be professional yet insightful, providing useful insights for a sales team.

                Start directly with the profile.

                PERSONA PROFILE:
            """

            # Add the language instruction
            language_instruction = f"\n\nImportant: Generate your entire response, including all textual content and string values within any JSON structure, strictly in the following language: {self.output_language}. Do not include any English text unless it is part of the original input data that should be preserved as is."
            final_prompt = prompt_template.format(
                lead_analysis=truncated_analysis,
                product_service_offered=input_data.product_service_offered,
                lead_url=input_data.lead_url
            ) + language_instruction

            llm_response = self.generate_llm_response(final_prompt, output_language=self.output_language)

            if llm_response:
                persona_profile = llm_response.strip()
            else:
                error_message = "LLM call returned no response or an empty response." # Already in English
                self.logger.warning(f"{self.name} received an empty response from LLM for URL: {input_data.lead_url}")
        
        except Exception as e:
            import traceback
            self.logger.error(f"An unexpected error occurred in {self.name} for URL {input_data.lead_url}: {str(e)}\n{traceback.format_exc()}")
            error_message = f"An unexpected error occurred in {self.name}: {str(e)}" # Already in English

        return B2BPersonaCreationOutput(
            persona_profile=persona_profile,
            error_message=error_message
        )

if __name__ == '__main__':
    # Ensure logger is available for __main__ block or use print
    from loguru import logger
    import sys
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    class MockLLMClient(LLMClientBase): # Assuming LLMClientBase is correctly imported or defined
        def __init__(self, api_key: str = "mock_key", **kwargs): # Added **kwargs to match potential BaseAgent changes
            # super().__init__(api_key) # This would depend on LLMClientBase's __init__
            self.api_key = api_key


        # Updated signature to include output_language
        def generate_text_response(self, prompt: str, output_language: str = "en-US") -> Optional[str]:
            logger.debug(f"MockLLMClient received prompt (lang: {output_language}):\n{prompt[:600]}...") # Log snippet
            # Simple check if the language instruction is in the prompt
            if f"strictly in the following language: {output_language}" not in prompt:
                 logger.error("Language instruction missing or incorrect in prompt!")

            if "PERSONA PROFILE:" in prompt: # English keyword from the new prompt
                # Example persona in English, as if generated for en-US
                return (
                    "Carlos Mendes, Operations Director at ExampleTech, based in Campinas, SP, constantly faces the challenge of optimizing processes and reducing operational costs in a competitive tech market. "
                    "His responsibilities include ensuring software production efficiency and the rapid implementation of new technologies to keep the company ahead. "
                    "Carlos seeks solutions that demonstrate clear ROI and are easy to integrate with legacy systems, minimizing disruption. He is motivated by professional recognition and delivering measurable results that positively impact the bottom line. "
                    "To stay updated, Carlos participates in technical webinars and reads articles on specialized IT sector portals. He values direct, data-driven communication and prefers formal emails or concise LinkedIn presentations for initial contact. "
                    "Our Incredible Solutions for intelligent automation can help him automate manual development and QA tasks, providing real-time data for more assertive and faster decisions, aligning with his goal of modernization and efficiency. This would free up his team to focus on innovation, a crucial point for ExampleTech."
                ).strip()
            return "Default mock response."

    logger.info("Running mock test for B2BPersonaCreationAgent...")
    mock_llm = MockLLMClient()
    # Providing name and description as per BaseAgent's __init__ and the new output_language
    agent = B2BPersonaCreationAgent(
        name="TestB2BPersonaAgent",
        description="Test Agent for B2B Persona Creation",
        llm_client=mock_llm,
        output_language="en-US" # Testing with English
    )

    test_lead_analysis = (
        "ExampleTech, located in Campinas, São Paulo, operates in the Information Technology sector, primarily offering Software as a Service (SaaS) solutions for project management. "
        "It is a medium-sized company with about 150 employees and recently announced an investment round to expand its operations in Latin America. "
        "Its main disclosed challenges include the need to scale its software development operations efficiently and optimize internal processes to support accelerated growth. "
        "They constantly seek innovation to remain competitive."
    )
    test_product_service = "Our Incredible Solutions for intelligent automation for DEVs and QA"
    test_lead_url = "http://www.exampletech.com.br" # Corrected URL for mock

    input_data = B2BPersonaCreationInput(
        lead_analysis=test_lead_analysis,
        product_service_offered=test_product_service,
        lead_url=test_lead_url
    )

    output = agent.process(input_data)

    logger.info(f"Persona Profile:\n{output.persona_profile}")
    if output.error_message:
        logger.error(f"Error: {output.error_message}")
    else:
        logger.success("Persona profile generated successfully.")

    assert "Carlos Mendes" in output.persona_profile # Mock data example
    assert "Our Incredible Solutions" in output.persona_profile # Check product mention
    assert "Campinas" in output.persona_profile # Check context use
    assert output.error_message is None
    logger.info("Mock test for B2BPersonaCreationAgent completed successfully.")
```
