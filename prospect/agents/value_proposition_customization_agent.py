import asyncio
import json
import re
import textwrap
from typing import List, Optional

from loguru import logger
from pydantic import BaseModel, Field

from .base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# --- Data Models ---

class ValuePropositionCustomizationInput(BaseModel):
    company_name: str
    product_service_description: str
    persona_profile: str # JSON string or dict
    pain_points_analysis: str # JSON string or dict

class ValueProposition(BaseModel):
    title: str = Field(description="A compelling, attention-grabbing headline for the value proposition.")
    proposition: str = Field(description="The detailed, customized value proposition statement, explaining the 'how'.")
    target_pain_point: str = Field(description="The specific pain point or business challenge this proposition directly addresses.")
    key_benefits: List[str] = Field(description="A bulleted list of 3-4 key benefits and outcomes for the customer.")
    evidence: str = Field(description="A suggestion for proof or evidence to support the claim (e.g., 'Cite case study X', 'Mention our 99.9% uptime').")

class ValuePropositionCustomizationOutput(BaseModel):
    customized_propositions: List[ValueProposition] = Field(default_factory=list)
    error_message: Optional[str] = None

# --- Agent Definition ---

class ValuePropositionCustomizationAgent(BaseAgent[ValuePropositionCustomizationInput, ValuePropositionCustomizationOutput]):
    """
    Agent specialized in customizing a B2B value proposition based on deep analysis of a lead's persona and pain points.
    """

    def __init__(
        self,
        llm_client: LLMClientBase,
        name: str = "Value Proposition Customization Agent",
        description: str = "Customizes the value proposition for a specific B2B buyer persona.",
        event_queue: Optional[asyncio.Queue] = None,
        user_id: Optional[str] = None,
    ):
        super().__init__(llm_client, name, description, event_queue, user_id)

    async def process(self, lead_id: str, input_data: ValuePropositionCustomizationInput) -> ValuePropositionCustomizationOutput:
        """
        Generates a customized value proposition by synthesizing lead data.
        """
        await self._emit_event("agent_start", {"agent_name": self.name, "lead_id": lead_id})
        logger.info(f"Starting Value Proposition Customization for {input_data.company_name} (Lead ID: {lead_id})")

        response_text = ""
        try:
            system_prompt = textwrap.dedent("""
                You are a world-class B2B Product Marketing expert. Your specialty is crafting highly specific and resonant value propositions that speak directly to a potential customer's diagnosed needs.

                You will be given comprehensive details about a target company, including a buyer persona profile and a detailed analysis of their pain points. You will also receive a description of the product/service being offered.

                Your task is to synthesize all this information to create 1-2 distinct, powerful value propositions. Each proposition must be tailored to the persona and directly address one of the identified pain points.

                Structure your response as a single, valid JSON object. The object should contain a single key, "customized_propositions", which is a list of value proposition objects.
                Each value proposition object in the list must contain the following keys:
                - "title": A compelling, attention-grabbing headline.
                - "proposition": The detailed, customized value proposition statement, explaining the 'how'.
                - "target_pain_point": The specific pain point or business challenge this proposition directly addresses.
                - "key_benefits": A list of 3-4 key benefits and outcomes for the customer.
                - "evidence": A suggestion for proof or evidence to support the claim (e.g., 'Cite case study X', 'Mention our 99.9% uptime').

                Do not include any text or explanations outside of the JSON object.
            """)

            user_prompt = textwrap.dedent(f"""
                **Target Company:** {input_data.company_name}

                **Our Product/Service Description:**
                ---
                {input_data.product_service_description}
                ---

                **Target Buyer Persona Profile:**
                ---
                {input_data.persona_profile}
                ---

                **Diagnosed Pain Points Analysis:**
                ---
                {input_data.pain_points_analysis}
                ---

                Based on all the information provided, please generate the customized value propositions in the specified JSON format.
            """)

            response_text = await self.llm_client.generate(system_prompt, user_prompt)

            # Clean and parse JSON response
            if response_text.strip().startswith("```json"):
                response_text = response_text.strip()[7:-3].strip()

            parsed_json = json.loads(response_text)
            propositions_data = parsed_json.get("customized_propositions", [])

            if not propositions_data:
                 raise ValueError("LLM did not return any value propositions.")

            validated_propositions = [ValueProposition(**p) for p in propositions_data]
            output = ValuePropositionCustomizationOutput(customized_propositions=validated_propositions)
            logger.success(f"Successfully generated {len(validated_propositions)} value propositions for Lead ID {lead_id}.")

        except (json.JSONDecodeError, TypeError, AttributeError, ValueError) as e:
            error_message = f"Failed to generate or parse value proposition: {e}"
            logger.error(f"{error_message} for Lead ID {lead_id}")
            logger.debug(f"LLM Response Text: {response_text}")
            output = ValuePropositionCustomizationOutput(customized_propositions=[], error_message=error_message)
        except Exception as e:
            error_message = f"An unexpected error occurred: {e}"
            logger.error(f"{error_message} for Lead ID {lead_id}", exc_info=True)
            output = ValuePropositionCustomizationOutput(customized_propositions=[], error_message=error_message)

        await self._emit_event("agent_end", {"agent_name": self.name, "lead_id": lead_id, "response": output.model_dump()})
        return output


if __name__ == "__main__":
    # Test code
    from core_logic.llm_client import LLMClientBase
    from pydantic import BaseModel
    
    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key)
            
        async def get_response(self, model: str, temperature: float, system_message: str, prompt: str) -> str:
            # Return a mock response for testing
            return """
            {
                "customized_propositions": [
                    {
                        "title": "Escale a Expansão da Empresa Exemplo com Eficiência Operacional via IA",
                        "proposition": "Para Carlos, da Empresa Exemplo, nossa solução de automação de processos com IA reduz em 40% o tempo gasto em tarefas manuais, permitindo que sua equipe foque em iniciativas estratégicas de expansão.",
                        "target_pain_point": "Dificuldade em escalar operações com a equipe atual",
                        "key_benefits": [
                            "Redução de 40% no tempo gasto em tarefas manuais",
                            "Maior precisão e consistência nos processos",
                            "Escalabilidade imediata sem necessidade de contratações adicionais"
                        ],
                        "evidence": "Mencionar nosso case de sucesso com a Empresa X que aumentou sua capacidade de processamento em 3x"
                    }
                ]
            }
            """
    
    # Create a test instance
    mock_llm = MockLLMClient()
    agent = ValuePropositionCustomizationAgent(llm_client=mock_llm)
    
    # Create test input
    input_data = ValuePropositionCustomizationInput(
        company_name="Empresa Exemplo",
        product_service_description="Solução de automação de processos com IA",
        persona_profile="Carlos, CTO com foco em eficiência operacional",
        pain_points_analysis="Dificuldade em escalar operações com a equipe atual"
    )
    
    # Run the test
    import asyncio
    output = asyncio.run(agent.process("test_lead_123", input_data))

    print("\n--- Agent Output ---")
    if output.error_message:
        print(f"Error: {output.error_message}")

    if output.customized_propositions:
        for i, vp in enumerate(output.customized_propositions):
            print(f"\n--- Value Proposition {i+1} ---")
            print(f"Title: {vp.title}")
            print(f"Proposition: {vp.proposition}")
            print(f"Target Pain Point: {vp.target_pain_point}")
            print(f"Key Benefits: {vp.key_benefits}")
            print(f"Evidence: {vp.evidence}")

    print("\nTest completed successfully.")
