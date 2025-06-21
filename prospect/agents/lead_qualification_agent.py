from typing import Optional, List
from pydantic import BaseModel, Field

from .base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase
import json # For mock test

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class LeadQualificationInput(BaseModel):
    lead_analysis: str = Field(..., description="Summary from LeadAnalysisAgent.")
    persona_profile: str = Field(..., description="Summary from PersonaCreationAgent (or constructed).")
    deepened_pain_points: str = Field(..., description="JSON string from PainPointDeepeningAgent.")
    product_service_offered: str = Field(..., description="User's product/service being offered.")

# Updated Pydantic Output Model with English descriptions and defaults
class LeadQualificationOutput(BaseModel):
    qualification_tier: str = Field(default="Not Qualified", description="Enum: 'High Potential', 'Medium Potential', 'Low Potential', 'Not Qualified'")
    justification: str = Field(default="Justification not provided.", description="Detailed justification for the qualification tier, based on provided data.")
    key_positive_signals: List[str] = Field(default_factory=list, description="List of 2-3 main positive signals supporting the qualification.")
    key_negative_signals_or_risks: List[str] = Field(default_factory=list, description="List of 2-3 main negative signals or risks.")
    confidence_score: float = Field(default=0.5, description="Confidence in the qualification assessment (0.0 to 1.0).")
    suggested_next_steps_for_sales: List[str] = Field(default_factory=list, description="List of 1-2 practical next steps for the sales team.")
    error_message: Optional[str] = Field(default=None)

class LeadQualificationAgent(BaseAgent[LeadQualificationInput, LeadQualificationOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, output_language: str = "en-US", **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)
        self.output_language = output_language

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: LeadQualificationInput) -> LeadQualificationOutput:
        error_message = None
        self.logger.info(f"⚖️ LEAD QUALIFICATION AGENT STARTING for product: {input_data.product_service_offered}")

        try:
            # Truncate inputs, giving more space to pain_points and lead_analysis
            prompt_fixed_overhead = 3000 # Estimate for fixed parts of the prompt
            available_for_dynamic = GEMINI_TEXT_INPUT_TRUNCATE_CHARS - prompt_fixed_overhead

            tr_lead_analysis = self._truncate_text(input_data.lead_analysis, int(available_for_dynamic * 0.30))
            tr_persona_profile = self._truncate_text(input_data.persona_profile, int(available_for_dynamic * 0.20))
            tr_deepened_pain_points = self._truncate_text(input_data.deepened_pain_points, int(available_for_dynamic * 0.30))
            # product_service_offered is usually short, direct use. Other 20% for safety/other small inputs.

            # Refined prompt_template, now in English
            prompt_template = """
                You are an experienced and discerning B2B Sales Director, specializing in qualifying leads in the target market (e.g., Brazilian market), focusing on optimizing the sales team's time.
                Your objective is to classify the lead's potential based on the provided strategic information, justify your assessment, and suggest concrete next steps.

                DATA FOR QUALIFICATION ANALYSIS:

                1. GENERAL LEAD ANALYSIS:
                   \"\"\"
                   {lead_analysis}
                   \"\"\"

                2. TARGET PERSONA PROFILE (Decision-Maker):
                   \"\"\"
                   {persona_profile}
                   \"\"\"

                3. DEEPENED PAIN POINTS AND INVESTIGATIVE QUESTIONS (Insights on needs):
                   \"\"\"
                   {deepened_pain_points}
                   \"\"\"

                4. PRODUCT/SERVICE WE ARE OFFERING:
                   "{product_service_offered}"

                QUALIFICATION INSTRUCTIONS:
                Based on ALL provided information, perform a complete lead assessment:
                1.  **Pain vs. Solution Alignment:** Evaluate how well the identified pain points align with the benefits of our "{product_service_offered}".
                2.  **Persona Fit:** Consider if the persona profile (role, responsibilities, motivations) represents an ideal customer and an accessible decision-maker.
                3.  **Urgency/Criticality:** Analyze the implicit urgency or criticality in the pain points. Is there an immediate or future need?
                4.  **Positive and Negative Signals:** Explicitly identify the main factors that make this lead promising and those that represent risks or misalignment.
                5.  **Lead Classification:** Classify the lead into ONE of the following categories:
                    -   "High Potential": Strong alignment with ICP, clear pains our solution resolves, apparent urgency, accessible persona. Immediate action recommended.
                    -   "Medium Potential": Good alignment, but may lack urgency, clarity on some points, or persona harder to access. Requires nurturing or further investigation.
                    -   "Low Potential": Weak alignment, unclear pains or not resolved by our solution, no urgency. Monitor from a distance or discard.
                    -   "Not Qualified": Clearly not a fit for our solution or market.
                6.  **Justification:** Provide a concise justification (2-3 sentences) for the classification, referencing the data.
                7.  **Confidence Score:** Assign a confidence score (float, 0.0 to 1.0) to your overall qualification assessment.
                8.  **Next Steps for Sales:** Suggest 1-2 actionable and specific next steps for the sales team based on your qualification.

                RESPONSE FORMAT:
                Respond EXCLUSIVELY with a valid JSON object, following the schema and field descriptions below. Do NOT include ANY text, explanation, or markdown (like ```json) before or after the JSON object.

                EXPECTED JSON SCHEMA:
                {{
                    "qualification_tier": "string", // Enum: "High Potential", "Medium Potential", "Low Potential", "Not Qualified"
                    "justification": "string - Detailed justification for the classification, based on provided data (max 3-4 sentences).",
                    "key_positive_signals": ["string", ...], // List of 2-3 main positive signals supporting the qualification (e.g., 'Clear alignment with ICP', 'Pain X directly solved by solution Y'). Empty list [] if no clear signals.
                    "key_negative_signals_or_risks": ["string", ...], // List of 2-3 main negative signals or risks (e.g., 'Budget might be a barrier', 'Persona difficult to contact', 'Competitor solution already in use'). Empty list [] if none.
                    "confidence_score": "float", // Your confidence in the qualification assessment (0.0 to 1.0). Must always be a float.
                    "suggested_next_steps_for_sales": ["string", ...] // List of 1-2 practical next steps for the sales team (e.g., 'Prioritize for immediate contact focusing on pain X', 'Include in nurturing flow focused on [theme Y]', 'Discard and focus on other leads'). Empty list [] if no clear suggestion.
                }}
            """

            final_prompt = prompt_template.format(
                lead_analysis=tr_lead_analysis,
                persona_profile=tr_persona_profile,
                deepened_pain_points=tr_deepened_pain_points,
                product_service_offered=input_data.product_service_offered
            ) + f"\n\nImportant: Generate your entire response, including all textual content and string values within any JSON structure, strictly in the following language: {self.output_language}. Do not include any English text unless it is part of the original input data that should be preserved as is."

            self.logger.debug(f"Prompt for {self.name} (length: {len(final_prompt)}):\n{final_prompt[:500]}...")

            llm_response_obj = self.generate_llm_response(final_prompt, output_language=self.output_language)

            if not llm_response_obj or not llm_response_obj.content:
                self.logger.error(f"❌ LLM call returned no response for {self.name}")
                return LeadQualificationOutput(error_message="LLM call returned no response.")

            llm_response_str = llm_response_obj.content
            self.logger.debug(f"LLM response received for {self.name} (length: {len(llm_response_str)}). Attempting to parse.")
            parsed_output = self.parse_llm_json_response(llm_response_str, LeadQualificationOutput)
            
            if parsed_output.error_message:
                self.logger.warning(f"⚠️ {self.name} JSON parsing/validation failed. Error: {parsed_output.error_message}. Raw response snippet: {llm_response_str[:500]}")
                # The error from parse_llm_json_response is already in parsed_output
                return parsed_output
            
            self.logger.info(f"✅ Lead qualification successful for product '{input_data.product_service_offered}'. Tier: {parsed_output.qualification_tier}, Confidence: {parsed_output.confidence_score}")
            return parsed_output

        except Exception as e:
            self.logger.error(f"❌ An unexpected error occurred in {self.name}: {e}", exc_info=True)
            return LeadQualificationOutput(error_message=f"An unexpected error occurred: {str(e)}")

