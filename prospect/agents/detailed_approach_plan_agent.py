from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import json # Ensure json is imported

from .base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class DetailedApproachPlanInput(BaseModel):
    lead_analysis: str # Summary of company, sector, challenges etc.
    persona_profile: str # Detailed description of the target persona
    deepened_pain_points: str # JSON string of PainPointAnalysisOutput (includes investigative questions)
    final_action_plan_text: str # JSON string of ToTActionPlanSynthesisOutput (Synthesized plan from ToT agents)
    product_service_offered: str # User's product/service
    lead_url: str # Lead's website URL

# Sub-models for structured output
class ContactStepDetail(BaseModel):
    step_number: int = Field(..., description="The step number in the sequence (1, 2, 3, ...).")
    channel: str = Field(..., description="Contact channel for this step (e.g., 'Personalized Email', 'LinkedIn (Connection Note)', 'Brief Follow-up Phone Call').")
    objective: str = Field(..., description="Specific and measurable objective for this step.")
    key_topics_arguments: List[str] = Field(default_factory=list, description="List of 2-3 key topics or arguments to address in this step.")
    key_questions: List[str] = Field(default_factory=list, description="Optional list of 1-2 key questions to ask in this step.")
    cta: str = Field(..., description="Specific and clear Call to Action for this step.")
    supporting_materials: Optional[str] = Field(default=None, description="Optional: Supporting resource/material to use or mention (e.g., link to case study, article).")
    
    @field_validator('key_questions', 'key_topics_arguments', mode='before')
    def ensure_list_of_strings(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            # Handles single line string or multiline string from LLM
            return [s.strip() for s in v.splitlines() if s.strip()]
        if isinstance(v, list):
            # Filter list to only include non-empty strings, converting all items to str just in case
            return [str(item).strip() for item in v if str(item).strip()]
        return [] # Return empty list for other unexpected types

class DetailedApproachPlanOutput(BaseModel):
    main_objective: str = Field(default="Main objective of the approach not specified.", description="The primary strategic objective of this comprehensive approach plan.")
    adapted_elevator_pitch: str = Field(default="Adapted elevator pitch not specified.", description="A 2-3 sentence elevator pitch, highly personalized for THIS lead and persona.")
    contact_sequence: List[ContactStepDetail] = Field(default_factory=list, description="List detailing the first 3-4 steps of the contact sequence.")
    engagement_indicators_to_monitor: List[str] = Field(default_factory=list, description="List of 2-3 key indicators to monitor lead engagement.")
    potential_obstacles_attention_points: List[str] = Field(default_factory=list, description="List of 2-3 potential obstacles or attention points for the sales team.")
    suggested_next_steps_if_successful: List[str] = Field(default_factory=list, description="List of 1-2 suggested next steps if the initial contact sequence is successful.")
    error_message: Optional[str] = Field(default=None)

    @field_validator('contact_sequence', mode='before')
    def ensure_contact_sequence_is_list(cls, v):
        if v is None:
            return []
        return v if isinstance(v, list) else []

    @field_validator('engagement_indicators_to_monitor', 'potential_obstacles_attention_points', 'suggested_next_steps_if_successful', mode='before')
    def ensure_string_list_fields(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [s.strip() for s in v.splitlines() if s.strip()]
        if isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        return []


class DetailedApproachPlanAgent(BaseAgent[DetailedApproachPlanInput, DetailedApproachPlanOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, output_language: str = "en-US", **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)
        self.output_language = output_language
        # Logger is already initialized in BaseAgent as self.logger

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: DetailedApproachPlanInput) -> DetailedApproachPlanOutput:
        error_message = None

        try:
            # Approximate character allocation, leaving room for prompt overhead (approx 2.5k for fixed parts)
            # Total GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000
            base_prompt_overhead = 3000
            available_chars_for_inputs = GEMINI_TEXT_INPUT_TRUNCATE_CHARS - base_prompt_overhead

            # Distribute remaining characters among dynamic inputs
            # Prioritize final_action_plan_text and deepened_pain_points
            tr_final_action_plan = self._truncate_text(input_data.final_action_plan_text, int(available_chars_for_inputs * 0.35))
            tr_deepened_pain_points = self._truncate_text(input_data.deepened_pain_points, int(available_chars_for_inputs * 0.25))
            tr_lead_analysis = self._truncate_text(input_data.lead_analysis, int(available_chars_for_inputs * 0.20))
            tr_persona_profile = self._truncate_text(input_data.persona_profile, int(available_chars_for_inputs * 0.20))

            # Refined prompt, now in English
            prompt_template = """
                You are a Senior Account Strategist and B2B Sales Coach, specializing in creating actionable and effective multi-step engagement plans, with a focus on the target market (e.g., Brazilian market).
                Your task is to expand the provided "Synthesized Final Action Plan" into a "Detailed Approach Plan" that a sales team can execute.

                SYNTHESIZED FINAL ACTION PLAN (High-Level Strategy):
                \"\"\"
                {final_action_plan_text}
                \"\"\"

                ADDITIONAL CONTEXTUAL INFORMATION ABOUT THE LEAD:
                - Lead Analysis: {lead_analysis}
                - Target Persona Profile: {persona_profile}
                - Deepened Pain Points (including investigative questions): {deepened_pain_points}
                - Product/Service we are offering: {product_service_offered}
                - Lead URL (for reference): {lead_url}

                INSTRUCTIONS FOR THE DETAILED PLAN:
                Based on the "Synthesized Final Action Plan" and ALL contextual information, detail the following aspects.
                The plan must be practical, with clear steps, and adapted to communication and business nuances of the target market (e.g., Brazil).
                Create an initial contact sequence of 3 to 4 steps.

                RESPONSE FORMAT:
                Respond EXCLUSIVELY with a valid JSON object, following the schema and field descriptions below. Do NOT include ANY text, explanation, or markdown (like ```json) before or after the JSON object.

                EXPECTED JSON SCHEMA:
                {{
                    "main_objective": "string - Reaffirm or refine the main strategic objective of this complete approach, derived from the Final Action Plan.",
                    "adapted_elevator_pitch": "string - Create a 2-3 sentence 'core message' or 'elevator pitch', highly personalized for THIS lead and persona, highlighting the most crucial benefit of '{product_service_offered}'.",
                    "contact_sequence": [ // List detailing the first 3-4 steps of the contact sequence.
                        {{
                            "step_number": "integer - The step number in the sequence (1, 2, 3, ...).",
                            "channel": "string - Contact channel for this step (e.g., 'Personalized Email', 'LinkedIn (Connection Note)', 'Brief Follow-up Phone Call', 'Short WhatsApp Message').",
                            "objective": "string - Specific and measurable objective for this step (e.g., 'Get a response to the initial email and validate interest', 'Schedule a 15-minute discovery call', 'Confirm persona's main challenge X').",
                            "key_topics_arguments": ["string", ...], // List of 2-3 key topics or arguments to be addressed in this step, aligned with the elevator pitch and persona's pains. Empty list [] if no specific topics beyond the main message.
                            "key_questions": ["string", ...], // Optional list of 1-2 key questions to ask in this step to engage, qualify, or discover information. Empty list [] if not applicable.
                            "cta": "string - Specific and clear Call to Action for this step (e.g., 'Propose a time for a brief 15-min conversation', 'Ask to connect on LinkedIn', 'Ask for the best time for a quick follow-up').",
                            "supporting_materials": "string | null" // Optional: Supporting resource/material to use or mentioned in this step (e.g., 'Link to case study on [similar problem]', 'Blog article on [persona's topic of interest]', 'Short demo video'). Use null if none.
                        }}
                    ],
                    "engagement_indicators_to_monitor": ["string", ...], // List of 2-3 key indicators to monitor lead engagement throughout the sequence (e.g., 'Email open and click-through rates', 'LinkedIn connection acceptance', 'Responses to direct messages', 'Website visits from sent links'). Empty list [] if no specific indicators beyond direct responses.
                    "potential_obstacles_attention_points": ["string", ...], // List of 2-3 potential obstacles, challenges, or attention points the sales team should consider when executing this plan (e.g., 'Lead might be extremely busy due to [recent event]', 'Possible initial skepticism about [aspect of the solution]', 'Need to bypass gatekeeper for first contact'). Empty list [] if no specific points.
                    "suggested_next_steps_if_successful": ["string", ...] // List of 1-2 suggested next steps if the initial contact sequence is successful and the main objective is achieved (e.g., 'Schedule detailed product demo', 'Prepare personalized proposal based on discovery call', 'Introduce technical specialist from our team'). Empty list [] if the plan already covers this."
                }}
            """

            final_prompt = prompt_template.format(
                final_action_plan_text=tr_final_action_plan,
                lead_analysis=tr_lead_analysis,
                persona_profile=tr_persona_profile,
                deepened_pain_points=tr_deepened_pain_points,
                product_service_offered=input_data.product_service_offered,
                lead_url=input_data.lead_url
            ) + f"\n\nImportant: Generate your entire response, including all textual content and string values within any JSON structure, strictly in the following language: {self.output_language}. Do not include any English text unless it is part of the original input data that should be preserved as is."

            self.logger.debug(f"Prompt for {self.name} (length: {len(final_prompt)}):\n{final_prompt[:1000]}...")

            llm_response_str = self.generate_llm_response(final_prompt, output_language=self.output_language)

            if not llm_response_str: # Already in English
                self.logger.error(f"LLM call returned no response for {self.name} on lead {input_data.lead_url}")
                return DetailedApproachPlanOutput(error_message="LLM call returned no response.")

            self.logger.debug(f"LLM response received for {self.name} (length: {len(llm_response_str)}). Attempting to parse.")
            parsed_output = self.parse_llm_json_response(llm_response_str, DetailedApproachPlanOutput)
            
            if parsed_output.error_message:
                 self.logger.warning(f"{self.name} JSON parsing/validation failed for lead {input_data.lead_url}. Error: {parsed_output.error_message}. Raw response snippet: {llm_response_str[:500]}")
                 # The error message from parsing is already in parsed_output
                 return parsed_output
            
            self.logger.info(f"Successfully processed detailed approach plan for lead {input_data.lead_url}.")
            return parsed_output

        except Exception as e:
            self.logger.error(f"An unexpected error occurred in {self.name} for lead {input_data.lead_url}: {e}", exc_info=True)
            return DetailedApproachPlanOutput(error_message=f"An unexpected error occurred: {str(e)}")

if __name__ == '__main__':
    from loguru import logger # Ensure logger is available
    import sys
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    class MockLLMClient(LLMClientBase): # Assuming LLMClientBase is correctly imported/defined
        def __init__(self, api_key: str = "mock_key", **kwargs):
            # super().__init__(api_key) # Depends on LLMClientBase
            self.api_key = api_key

        def generate_text_response(self, prompt: str, output_language: str = "en-US") -> Optional[str]:
            logger.debug(f"MockLLMClient received prompt (lang: {output_language}):\n{prompt[:700]}...")
            if f"strictly in the following language: {output_language}" not in prompt:
                 logger.error(f"Language instruction for '{output_language}' missing in prompt!")

            # Example in English
            return json.dumps({
                "main_objective": "Initiate a consultative dialogue with Carlos Mendes about optimizing efficiency in Example Inc.'s expansion, aiming to schedule a 20-minute exploratory call.",
                "adapted_elevator_pitch": "With Example Inc.'s expansion, scaling operations efficiently is vital. Our Incredible AI Solutions help IT companies like yours automate key processes and optimize resources, ensuring growth without operational bottlenecks and freeing up your team for innovation.",
                "contact_sequence": [
                    {
                        "step_number": 1,
                        "channel": "Personalized Initial Email",
                        "objective": "Get an initial response and demonstrate understanding of Example Inc.'s challenges.",
                        "key_topics_arguments": [
                            "Acknowledge the company's expansion and its scalability challenges.",
                            "Connect expansion with operational scalability challenges.",
                            "Mention how AI can optimize processes (e.g., automate X, Y, Z)."
                        ],
                        "key_questions": [
                            "Carlos, with the recent expansion, how are you prioritizing internal process optimization to sustain this growth?"
                        ],
                        "cta": "Would you have 15-20 minutes next week for a brief conversation about how we can help Example Inc. navigate these growth challenges more efficiently?",
                        "supporting_materials": "Link to a concise case study on AI for optimization in expanding IT companies."
                    },
                    {
                        "step_number": 2,
                        "channel": "LinkedIn (Connection Note)",
                        "objective": "Establish connection and reinforce the initial message more informally.",
                        "key_topics_arguments": [
                            "Reference the email sent.",
                            "Brief insight into challenges of scaling operations."
                        ],
                        "key_questions": [
                            "Carlos, I saw Example Inc. is expanding - congratulations! Many companies at this stage face challenges in [mention a specific optimization challenge]. Curious to know how you're handling this. I sent an email with some ideas, would love to connect here too."
                        ],
                        "cta": "Accept the connection request.",
                        "supporting_materials": None
                    },
                    {
                        "step_number": 3,
                        "channel": "LinkedIn (Follow-up Message)",
                        "objective": "Generate engagement and offer more value if no response to email/invitation.",
                        "key_topics_arguments": [
                            "Share relevant article/insight on optimization for expanding companies.",
                            "Subtly reiterate the value proposition in a consultative manner."
                        ],
                        "key_questions": [],
                        "cta": "If you're open to a quick chat about how Our Incredible AI Solutions can address some of these points, let me know when would be a good time.",
                        "supporting_materials": "Link to relevant article or insight."
                    }
                ],
                "engagement_indicators_to_monitor": [
                    "Initial email open and click-through rates on case study link.",
                    "LinkedIn connection acceptance rate.",
                    "Responses to direct messages (email or LinkedIn).",
                    "Visits to our company website (if trackable)."
                ],
                "potential_obstacles_attention_points": [
                    "Carlos Mendes might be extremely busy due to the expansion.",
                    "Possible skepticism regarding the actual ROI of AI or concerns about implementation complexity.",
                    "The company might already have an in-house solution or a preferred vendor."
                ],
                "suggested_next_steps_if_successful": [
                    "Schedule the confirmed exploratory call (15-20 minutes).",
                    "Prepare specific questions for the call based on persona pains and profile.",
                    "Send a brief diagnostic questionnaire (1-3 questions) before the call to optimize time."
                ]
            })

    logger.info("Running mock test for DetailedApproachPlanAgent...")
    mock_llm = MockLLMClient(api_key="mock_llm_key")
    agent = DetailedApproachPlanAgent(
        name="TestDetailedApproachPlanAgent",
        description="Test Agent for Detailed Approach Plan",
        llm_client=mock_llm,
        output_language="en-US" # Testing with English
    )

    # Test data in English
    test_lead_analysis = "Example Inc. (IT, Medium Size). Focus on optimizing development and QA processes to support LATAM expansion. Recently received Series B funding."
    test_persona_profile = "Carlos Mendes, COO. Responsible for operational efficiency and adoption of new technologies. Seeks clear ROI and easy integration. Preferred communication: formal email, LinkedIn for networking."
    test_deepened_pain_points = json.dumps({
        "primary_pain_category": "Operational Efficiency",
        "detailed_pain_points": [{"pain": "Manual QA processes", "impact": "Release delays"}],
        "urgency_level": "High"
    })
    test_final_action_plan = json.dumps({
        "recommended_strategy_name": "Consultative Efficiency with Focus on LATAM Expansion Impact",
        "primary_angle_hook": "Help Carlos Mendes ensure Example Inc.'s LATAM expansion is supported by highly efficient and scalable development and QA operations using AI.",
        "key_talking_points": ["QA optimization with AI", "ROI of development automation", "Support for LATAM expansion"],
        "communication_channel_sequence": ["Personalized Email", "LinkedIn Connection Note", "LinkedIn Follow-up Message"],
        "tone_of_voice": "Consultative, focused on results and efficiency, respectful of executive's time.",
        "main_call_to_action": "Schedule a 20-minute exploratory call to discuss QA and DevOps optimization with AI.",
        "opening_question_suggestion": "Carlos, with the recent LATAM expansion, how is Example Inc. adapting its QA and development cycles to ensure speed and quality?"
    })
    test_product_service = "Our Incredible AI Solutions for QA and DevOps Automation"
    test_lead_url = "http://www.exampleinc.com" # English example URL

    input_data = DetailedApproachPlanInput(
        lead_analysis=test_lead_analysis,
        persona_profile=test_persona_profile,
        deepened_pain_points=test_deepened_pain_points,
        final_action_plan_text=test_final_action_plan,
        product_service_offered=test_product_service,
        lead_url=test_lead_url
    )

    output = agent.process(input_data)

    if output.error_message:
        logger.error(f"Error: {output.error_message}")
    else:
        logger.success("DetailedApproachPlanAgent processed successfully.")
        logger.info(f"Main Objective: {output.main_objective}")
        logger.info(f"Adapted Elevator Pitch: {output.adapted_elevator_pitch}")
        logger.info(f"Contact Sequence Steps: {len(output.contact_sequence)}")
        if output.contact_sequence:
            for i, step in enumerate(output.contact_sequence):
                logger.info(f"  Step {step.step_number}: Channel: {step.channel}, Objective: {step.objective}, CTA: {step.cta}")
                logger.info(f"    Topics: {step.key_topics_arguments}")
                logger.info(f"    Questions: {step.key_questions}")
                logger.info(f"    Materials: {step.supporting_materials}")
        logger.info(f"Engagement Indicators: {output.engagement_indicators_to_monitor}")
        logger.info(f"Potential Obstacles: {output.potential_obstacles_attention_points}")
        logger.info(f"Next Steps if Successful: {output.suggested_next_steps_if_successful}")


    assert output.error_message is None
    assert "Carlos Mendes" in output.main_objective or "Example Inc." in output.main_objective
    assert len(output.contact_sequence) > 0 and output.contact_sequence[0].step_number == 1
    assert "Our Incredible AI Solutions" in output.adapted_elevator_pitch
    assert len(output.engagement_indicators_to_monitor) > 0
    assert len(output.potential_obstacles_attention_points) > 0

    logger.info("\nMock test for DetailedApproachPlanAgent completed successfully.")
