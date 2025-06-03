import json
import re
import traceback
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent # Assuming BaseAgent is in agents.base_agent
from core_logic.llm_client import LLMClientBase # Assuming LLMClientBase is in core_logic.llm_client

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS: int = 30000 # Max characters for Gemini text input (shared with other agents)

# --- Input and Output Models ---
class ContactExtractionInput(BaseModel):
    extracted_text: str
    company_name: str
    product_service_offered: str

class ContactExtractionOutput(BaseModel):
    emails_found: List[str] = Field(default_factory=list)
    instagram_profiles_found: List[str] = Field(default_factory=list)
    tavily_search_suggestion: str = ""
    error_message: Optional[str] = None

class ContactExtractionAgent(BaseAgent[ContactExtractionInput, ContactExtractionOutput]):
    def __init__(self, llm_client: LLMClientBase):
        super().__init__(llm_client)

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def _extract_with_regex(self, text: str) -> tuple[List[str], List[str]]:
        """
        Extracts emails and Instagram profiles using regex as a fallback.
        """
        # Improved email regex to be a bit more robust but still simple
        emails = list(set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?<!\.png|\.jpg|\.jpeg|\.gif)", text)))

        # Regex for Instagram profiles: instagram.com/username or @username
        # It captures the username part.
        ig_pattern1 = r"instagram\.com/([a-zA-Z0-9._]+)"
        ig_pattern2 = r"(?<!\w)@([a-zA-Z0-9._]{3,30})(?!\.\w)" # @username, not part of an email, min 3 max 30 chars for username

        profiles_p1 = re.findall(ig_pattern1, text)
        profiles_p2 = re.findall(ig_pattern2, text)

        raw_instagram_profiles = list(set(profiles_p1 + profiles_p2))

        cleaned_profiles = []
        for profile in raw_instagram_profiles:
            # Remove any leading/trailing slashes or query params if full URL matched for username part
            username = profile.split('/')[0]
            # Filter out common non-profile paths that might be caught if regex is too broad
            if username.lower() not in ["p", "reel", "stories", "explore", "accounts", "tags", "static", "web"] and "." not in username.split('.')[-1][-2:]: # Avoid things like .png
                 if 3 <= len(username) <= 30: # Instagram username length constraints
                    cleaned_profiles.append(username)

        final_ig_profiles = list(set(cleaned_profiles)) # Ensure uniqueness after cleaning

        self.logger.info(f"Regex fallback extracted emails: {emails}")
        self.logger.info(f"Regex fallback extracted Instagram profiles: {final_ig_profiles}")
        return emails, final_ig_profiles

    async def process(self, input_data: ContactExtractionInput) -> ContactExtractionOutput:
        self.logger.info(f"Starting contact extraction for company: {input_data.company_name}")

        truncated_text = self._truncate_text(input_data.extracted_text, GEMINI_TEXT_INPUT_TRUNCATE_CHARS)

        prompt = f"""
        Analyze the following text, which is data extracted from the website of the company '{input_data.company_name}'.
        The company offers: '{input_data.product_service_offered}'.

        Your tasks are:
        1. Identify and extract all email addresses. Prioritize generic company emails (e.g., contact@, sales@, info@) and emails of potential decision-makers or relevant departments.
        2. Identify and extract all Instagram profile usernames. For example, if you find "instagram.com/username123", extract "username123". If you find "@anotheruser", extract "anotheruser".
        3. Based on the text and the company's offerings, suggest ONE concise Tavily search query (max 10-15 words) to find more information about potential contacts or decision-makers if the current text is insufficient. This query should be specific and actionable. For example: "key marketing contacts at [Company Name]" or "CXOs at [Company Name] LinkedIn".

        Return the information as a JSON object with the following exact keys:
        "emails_found": ["email1@example.com", "email2@example.com"],
        "instagram_profiles_found": ["username1", "username2"],
        "tavily_search_suggestion": "Your concise Tavily search query here"

        If no emails are found, return an empty list for "emails_found".
        If no Instagram profiles are found, return an empty list for "instagram_profiles_found".
        If the text provides enough contact information, "tavily_search_suggestion" can be an empty string or a very generic suggestion like "General information about {input_data.company_name}".

        Extracted text:
        ---
        {truncated_text}
        ---

        Ensure the output is ONLY the JSON object, without any markdown formatting like ```json ... ```.
        """

        try:
            llm_response_str = await self.generate_llm_response(
                prompt=prompt,
                temperature=0.1, # Very low temperature for precise extraction
                max_tokens=1000
            )

            if not llm_response_str:
                self.logger.warning("LLM returned no response for contact extraction.")
                emails, ig_profiles = self._extract_with_regex(truncated_text)
                return ContactExtractionOutput(
                    emails_found=emails,
                    instagram_profiles_found=ig_profiles,
                    tavily_search_suggestion=f"key decision makers at {input_data.company_name}",
                    error_message="LLM returned no response. Used regex fallback."
                )

            # Attempt to parse the LLM response as JSON
            # parse_llm_json_response is expected to handle basic cleaning (like ```json ... ```)
            # but the prompt now explicitly asks LLM to avoid it.
            parsed_output = await self.parse_llm_json_response(llm_response_str, ContactExtractionOutput)

            final_emails = []
            final_ig_profiles = []
            final_suggestion = f"contact information for {input_data.company_name}" # Default suggestion
            error_msg = None

            if parsed_output and not parsed_output.error_message : # Successfully parsed by BaseAgent method
                final_emails = parsed_output.emails_found if parsed_output.emails_found is not None else []
                raw_ig_profiles = parsed_output.instagram_profiles_found if parsed_output.instagram_profiles_found is not None else []

                # Clean IG profiles from LLM: ensure they are just usernames
                for profile in raw_ig_profiles:
                    username = profile.split("instagram.com/")[-1].split("/")[0]
                    if username.startswith('@'): # Remove leading @ if present
                        username = username[1:]
                    if 3 <= len(username) <= 30 and username.lower() not in ["p", "reel", "stories", "explore", "accounts", "tags"]:
                        final_ig_profiles.append(username)
                final_ig_profiles = list(set(final_ig_profiles)) # Deduplicate

                final_suggestion = parsed_output.tavily_search_suggestion or final_suggestion
                self.logger.info(f"Successfully parsed LLM JSON response. Emails: {len(final_emails)}, IG: {len(final_ig_profiles)}")

            else: # JSON parsing failed or BaseAgent indicated an error
                error_msg = parsed_output.error_message if parsed_output else "LLM response was not valid JSON."
                self.logger.warning(f"Failed to parse LLM JSON response for contact extraction: {error_msg}. Raw response: '{llm_response_str[:200]}'. Using regex fallback.")
                # Fallback to regex for emails and IG. Suggestion might be lost or use default.
                regex_emails, regex_ig_profiles = self._extract_with_regex(truncated_text)
                final_emails.extend(regex_emails)
                final_ig_profiles.extend(regex_ig_profiles)
                error_msg = f"{error_msg} Used regex fallback."


            # Augment with regex scan of the original text in case LLM missed some,
            # especially if LLM parsing failed.
            regex_emails_orig, regex_ig_profiles_orig = self._extract_with_regex(truncated_text)

            combined_emails = list(set(final_emails + regex_emails_orig))
            combined_ig_profiles = list(set(final_ig_profiles + regex_ig_profiles_orig))

            # Final cleaning for IG profiles to ensure they are just usernames
            cleaned_ig_profiles_final = []
            for p_ig in combined_ig_profiles:
                username = p_ig.split("instagram.com/")[-1].split("/")[0]
                if username.startswith('@'):
                    username = username[1:]
                if 3 <= len(username) <= 30 and username.lower() not in ["p", "reel", "stories", "explore", "accounts", "tags"]:
                     cleaned_ig_profiles_final.append(username)

            return ContactExtractionOutput(
                emails_found=list(set(combined_emails)),
                instagram_profiles_found=list(set(cleaned_ig_profiles_final)),
                tavily_search_suggestion=final_suggestion, # Suggestion from LLM if parsed, else default
                error_message=error_msg
            )

        except Exception as e:
            self.logger.error(f"Critical error during contact extraction for {input_data.company_name}: {e}")
            self.logger.error(traceback.format_exc())
            emails_fallback, ig_profiles_fallback = self._extract_with_regex(truncated_text) # Fallback to regex
            return ContactExtractionOutput(
                emails_found=emails_fallback,
                instagram_profiles_found=ig_profiles_fallback,
                tavily_search_suggestion=f"key decision makers at {input_data.company_name}",
                error_message=f"An unexpected critical error occurred: {str(e)}. Used regex fallback."
            )

# Example Usage (Illustrative - requires async execution context)
# async def main():
#     from core_logic.llm_clients.gemini_client import GeminiClient # Example LLM Client
#     gemini_api_key = os.getenv("GEMINI_API_KEY") # Ensure this is set in your environment
#     import os # ensure os is imported if you run this example

#     if not gemini_api_key:
#         print("Please set GEMINI_API_KEY environment variable to run the example.")
#         return

#     llm_client = GeminiClient(api_key=gemini_api_key)
#     extraction_agent = ContactExtractionAgent(llm_client=llm_client)

#     test_input_text = """
#     Welcome to Global Innovations Ltd. We are pioneers in sustainable tech.
#     For inquiries, please email info@globalinnovations.com or our sales team at sales.department@globalinnovations.com.
#     Follow our journey on Instagram: instagram.com/GlobalInnovationsOfficial and also @GI_Labs for our research updates.
#     You can also reach out to project_manager@globalinnovations.com.
#     Our website is globalinnovations.com. Check our careers page. No phone numbers please.
#     Sometimes people mention @badprofile or instagram.com/p/postid or test@test.png.
#     """

#     test_input = ContactExtractionInput(
#         company_name="Global Innovations Ltd.",
#         product_service_offered="Sustainable Technology",
#         extracted_text=test_input_text
#     )
#     output = await extraction_agent.process(test_input)
#     print("--- Contact Extraction Output ---")
#     if output.error_message:
#         print(f"Error: {output.error_message}")
#     print(f"Emails: {output.emails_found}")
#     print(f"Instagram Profiles: {output.instagram_profiles_found}")
#     print(f"Tavily Suggestion: {output.tavily_search_suggestion}")

# if __name__ == "__main__":
#     import asyncio
#     # asyncio.run(main()) # This would run the example if uncommented and GEMINI_API_KEY is set
#     print("ContactExtractionAgent defined. Example main() is commented out.")
# Pass # Placeholder for actual main execution
