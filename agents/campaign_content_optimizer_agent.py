from typing import List, Optional, Dict, Any
from loguru import logger
from pydantic import ValidationError

from agents.base_agent import BaseAgent, LLMProvider
from data_models.campaign_optimization_models import (
    CampaignContentInput,
    CampaignContentOutput,
    CampaignContentType, # Import Enum for type hinting if needed in logic
)

class CampaignContentOptimizerAgent(BaseAgent[CampaignContentInput, CampaignContentOutput]):
    """
    Agent for analyzing and suggesting improvements for campaign content.
    It takes original content, its type, target audience, and desired outcome
    to provide optimization suggestions and alternative versions.
    """

    DEFAULT_LLM_PROVIDER = LLMProvider.GEMINI # Or your preferred default

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            name="Campaign Content Optimizer Agent",
            description="Analyzes campaign content (like email subjects, ad headlines) and suggests improvements.",
            llm_provider=llm_provider or self.DEFAULT_LLM_PROVIDER,
            config=config,
        )

    def _build_llm_prompt(self, input_data: CampaignContentInput) -> str:
        prompt = f"""
You are an expert Campaign Content Optimization specialist. Your task is to analyze the provided campaign content and suggest concrete improvements to achieve the desired outcome for the target audience.

**Content Type:** {input_data.content_type.value}
**Original Content:**
---
{input_data.original_content}
---
**Target Audience Description:** {input_data.target_audience_description}
**Desired Outcome:** {input_data.desired_outcome}
**Additional Context:** {input_data.additional_context or "Not provided."}

Please provide your analysis and suggestions in a structured JSON format. The main keys should be "suggested_improvements", "optimized_versions", and "analysis_summary".

1.  **`suggested_improvements` (List[str]):**
    *   Provide at least 2-3 specific, actionable suggestions to improve the original content. Explain briefly why each suggestion would help achieve the desired outcome for the target audience.
    *   Focus on clarity, conciseness, persuasiveness, call-to-action (if applicable), tone, and relevance.

2.  **`optimized_versions` (List[str]):**
    *   Provide 1-2 alternative versions of the content with your suggested improvements applied. These should be ready-to-use.

3.  **`analysis_summary` (str):**
    *   Write a brief summary explaining the overall rationale behind your suggestions and optimized versions, highlighting how they better align with the desired outcome and target audience.

Example JSON structure:
{{
    "suggested_improvements": [
        "Suggestion 1: Make the headline more benefit-oriented by focusing on X.",
        "Suggestion 2: Shorten the call-to-action to be more direct.",
        "Suggestion 3: Add a sense of urgency if appropriate for the desired outcome."
    ],
    "optimized_versions": [
        "Optimized Version 1 incorporating suggestions...",
        "Optimized Version 2 presenting another angle..."
    ],
    "analysis_summary": "The original content was X, but it could be improved by Y and Z to better achieve the outcome of {input_data.desired_outcome} by appealing more directly to the {input_data.target_audience_description}."
}}

Ensure the output is a valid JSON object.
"""
        return prompt

    def process(self, input_data: CampaignContentInput) -> CampaignContentOutput:
        logger.info(
            f"[{self.name}] Starting content optimization for type: {input_data.content_type.value}"
        )
        logger.debug(f"[{self.name}] Input content: '{input_data.original_content[:100]}...'")

        prompt = self._build_llm_prompt(input_data)

        # Initialize output fields that are directly copied from input
        output_data_dict = {
            "original_content": input_data.original_content,
            "content_type": input_data.content_type,
            "target_audience_description": input_data.target_audience_description,
            "desired_outcome": input_data.desired_outcome,
            "suggested_improvements": [],
            "optimized_versions": [],
            "analysis_summary": "No analysis performed.",
            "confidence_score": None, # Default confidence
            "error_message": None
        }

        try:
            llm_response_str = self.generate_llm_response(prompt)
        except Exception as e:
            logger.error(f"[{self.name}] LLM generation failed: {e}")
            output_data_dict["error_message"] = f"LLM generation failed: {str(e)}"
            output_data_dict["analysis_summary"] = "Failed to generate analysis due to LLM error."
            return CampaignContentOutput(**output_data_dict)

        try:
            parsed_response = self.parse_llm_json_response(llm_response_str, dict)

            output_data_dict["suggested_improvements"] = parsed_response.get("suggested_improvements", [])
            output_data_dict["optimized_versions"] = parsed_response.get("optimized_versions", [])
            output_data_dict["analysis_summary"] = parsed_response.get("analysis_summary", "LLM response did not contain an analysis summary.")
            # You could add logic to derive a confidence_score here if the LLM provides it or based on response quality

            if not output_data_dict["suggested_improvements"] and not output_data_dict["optimized_versions"]:
                 output_data_dict["analysis_summary"] = "LLM response parsed, but no suggestions or optimized versions were found."
            elif not output_data_dict["error_message"]: # If no LLM error previously, set a success summary
                 output_data_dict["analysis_summary"] = parsed_response.get("analysis_summary", "Content optimization suggestions generated successfully.")


        except (ValueError, ValidationError) as e:
            logger.error(f"[{self.name}] Failed to parse or validate LLM JSON response: {e}")
            logger.debug(f"Problematic LLM response string: {llm_response_str[:1000]}...")
            output_data_dict["error_message"] = f"LLM response parsing failed: {str(e)}. Raw response snippet: {llm_response_str[:200]}..."
            output_data_dict["analysis_summary"] = "Failed to process LLM response."

        return CampaignContentOutput(**output_data_dict)

# Optional: if __name__ == "__main__": block for basic testing
if __name__ == "__main__":
    logger.remove()
    logger.add(lambda msg: print(msg), level="INFO")

    # Ensure API keys are set in environment (e.g., GEMINI_API_KEY)
    agent = CampaignContentOptimizerAgent()

    sample_input = CampaignContentInput(
        content_type=CampaignContentType.EMAIL_SUBJECT,
        original_content="Our new product is here, check it out now!",
        target_audience_description="Busy professionals who value efficiency and innovation.",
        desired_outcome="Maximize email open rates and convey excitement.",
        additional_context="Product is a time-saving software for project management."
    )

    logger.info(f"Testing agent with content type: {sample_input.content_type.value}")
    logger.info(f"Original content: '{sample_input.original_content}'")

    try:
        result = agent.execute(sample_input) # Use BaseAgent's execute method

        if result:
            logger.info("--- Campaign Content Optimizer Output ---")
            logger.info(f"Original Content: {result.original_content}")
            logger.info(f"Content Type: {result.content_type.value}")
            logger.info(f"Target Audience: {result.target_audience_description}")
            logger.info(f"Desired Outcome: {result.desired_outcome}")
            logger.info(f"Analysis Summary: {result.analysis_summary}")
            logger.info("Suggested Improvements:")
            for imp in result.suggested_improvements:
                logger.info(f"  - {imp}")
            logger.info("Optimized Versions:")
            for ver in result.optimized_versions:
                logger.info(f"  - {ver}")
            if result.confidence_score is not None:
                logger.info(f"Confidence Score: {result.confidence_score:.2f}")
            if result.error_message:
                logger.error(f"Error Message: {result.error_message}")
        else:
            logger.error("Agent execution returned no result.")

    except Exception as e:
        logger.error(f"Error during agent execution test: {e}", exc_info=True)
