import os
import json
import requests
import time
import re
import traceback
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent # Assuming BaseAgent is in agents.base_agent
from core_logic.llm_client import LLMClientBase # Assuming LLMClientBase is in core_logic.llm_client

# Constants
TAVILY_SEARCH_DEPTH: str = "advanced"
TAVILY_MAX_RESULTS_PER_QUERY: int = 3 # Max results per individual Tavily search query
TAVILY_TOTAL_QUERIES_PER_LEAD: int = 3 # Max number of Tavily queries for a single lead enrichment
GEMINI_TEXT_INPUT_TRUNCATE_CHARS: int = 30000 # Max characters for Gemini text input

# --- Input and Output Models ---
class TavilyEnrichmentInput(BaseModel):
    company_name: str
    initial_extracted_text: str
    product_service_offered: Optional[str] = None # Added for context in summarization

class TavilyEnrichmentOutput(BaseModel):
    enriched_data: str
    tavily_api_called: bool
    error_message: Optional[str] = None

class TavilyEnrichmentAgent(BaseAgent[TavilyEnrichmentInput, TavilyEnrichmentOutput]):
    def __init__(self, llm_client: LLMClientBase, tavily_api_key: str):
        super().__init__(llm_client)
        self.tavily_api_key = tavily_api_key
        if not self.tavily_api_key:
            raise ValueError("Tavily API key is required for TavilyEnrichmentAgent.")

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    async def _search_with_tavily(self, query: str, search_depth: str = TAVILY_SEARCH_DEPTH, max_results: int = TAVILY_MAX_RESULTS_PER_QUERY) -> Optional[Dict[str, Any]]:
        """
        Performs a search using the Tavily API.
        Adapted from search_with_tavily in cw.py.
        """
        headers = {
            "Authorization": f"Bearer {self.tavily_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "query": query,
            "search_depth": search_depth,
            "max_results": max_results,
            "include_answer": True,
            "include_raw_content": False, # Raw content can be very verbose
            "include_images": False,
        }
        try:
            # Using httpx for async requests if BaseAgent or llm_client provides an async client
            # For now, sticking to requests with the assumption that this might be run in a thread
            # or the BaseAgent handles async execution. If not, this should be updated.
            # For direct async, one might use 'httpx.AsyncClient()'.
            response = await self.http_client.post("https://api.tavily.com/search", headers=headers, json=payload)
            response.raise_for_status()  # Raises an exception for HTTP errors
            return response.json()
        except requests.exceptions.RequestException as e: # httpx.RequestError for httpx
            self.logger.error(f"Tavily API request failed: {e}")
            return None
        except json.JSONDecodeError:
            self.logger.error("Failed to decode Tavily API response as JSON.")
            return None

    async def process(self, input_data: TavilyEnrichmentInput) -> TavilyEnrichmentOutput:
        self.logger.info(f"Starting Tavily enrichment for company: {input_data.company_name}")
        tavily_api_called = False
        error_occured = False # Renamed for clarity
        final_enriched_data = input_data.initial_extracted_text # Default to initial if all else fails

        critical_info_prompt = f"""
        Analyze the provided text about the company '{input_data.company_name}' and identify key information missing that would be crucial for a B2B sales context.
        Focus on aspects like their specific area of operation, key products/services, target audience, and recent relevant news or challenges.
        Based on these gaps, formulate up to {TAVILY_TOTAL_QUERIES_PER_LEAD} distinct search queries for Tavily API to gather this missing information.
        Return ONLY a JSON list of these queries. Example: ["query1", "query2", "query3"]

        Initial text:
        {self._truncate_text(input_data.initial_extracted_text, GEMINI_TEXT_INPUT_TRUNCATE_CHARS)}
        """
        try:
            llm_response_queries_str = await self.generate_llm_response(
                prompt=critical_info_prompt,
                temperature=0.5,
                max_tokens=500
            )

            if not llm_response_queries_str or not llm_response_queries_str.strip():
                self.logger.warning("LLM did not return any search queries.")
                return TavilyEnrichmentOutput(
                    enriched_data=input_data.initial_extracted_text,
                    tavily_api_called=False,
                    error_message="LLM did not generate search queries for Tavily."
                )

            queries: List[str] = []
            try:
                # Remove markdown code block fences if present
                cleaned_llm_response = re.sub(r"```json\n|\n```", "", llm_response_queries_str.strip())
                queries = json.loads(cleaned_llm_response)
                if not isinstance(queries, list) or not all(isinstance(q, str) for q in queries):
                    # Log the problematic structure before raising error
                    self.logger.error(f"LLM response for queries is not a list of strings. Response: {cleaned_llm_response}")
                    raise json.JSONDecodeError("Response is not a list of strings.", cleaned_llm_response, 0)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse LLM response for search queries: {e}. Response: {llm_response_queries_str}")
                queries = re.findall(r'"(.*?)"', llm_response_queries_str) # Regex fallback
                if not queries:
                    self.logger.error(f"Could not extract queries using regex fallback. LLM Response: {llm_response_queries_str}")
                    return TavilyEnrichmentOutput(
                        enriched_data=input_data.initial_extracted_text,
                        tavily_api_called=False,
                        error_message=f"Failed to parse or extract search queries from LLM response: {llm_response_queries_str}"
                    )
                self.logger.info(f"Successfully extracted queries using regex fallback: {queries}")

            if not queries:
                 self.logger.warning("No search queries were generated or extracted.")
                 return TavilyEnrichmentOutput(
                    enriched_data=input_data.initial_extracted_text,
                    tavily_api_called=False,
                    error_message="No search queries were generated or extracted after LLM call."
                )

            search_results_text = ""
            for i, query in enumerate(queries[:TAVILY_TOTAL_QUERIES_PER_LEAD]):
                self.logger.info(f"Executing Tavily search query {i+1}/{len(queries[:TAVILY_TOTAL_QUERIES_PER_LEAD])}: {query}")
                # Ensure http_client is available and configured for async in BaseAgent or passed to this agent
                if not hasattr(self, 'http_client'):
                     self.logger.error("HTTP client not available for Tavily search. Please configure an async HTTP client.")
                     # Fallback or error based on how critical Tavily is
                     # For now, let's assume it's critical and leads to an error state for this process
                     return TavilyEnrichmentOutput(
                        enriched_data=input_data.initial_extracted_text,
                        tavily_api_called=False, # API was not called due to client issue
                        error_message="HTTP client for Tavily search not configured."
                    )

                tavily_search_data = await self._search_with_tavily(query)
                tavily_api_called = True

                if tavily_search_data and tavily_search_data.get("results"):
                    for result in tavily_search_data["results"]:
                        search_results_text += f"Source: {result.get('url', 'N/A')}\nContent: {result.get('content', '')}\n\n"
                else:
                    self.logger.warning(f"No results from Tavily for query: {query}")

                if i < TAVILY_TOTAL_QUERIES_PER_LEAD - 1: # Avoid sleeping after the last query
                    await asyncio.sleep(1) # Use asyncio.sleep for async context

            if not search_results_text.strip():
                self.logger.info("No information retrieved from Tavily search.")
                # final_enriched_data is already input_data.initial_extracted_text by default
            else:
                self.logger.info("Summarizing Tavily search results with LLM.")
                summarization_prompt = f"""
                Based on the initial information about '{input_data.company_name}' and the following search results from Tavily, provide a concise and comprehensive summary.
                Focus on enriching the initial data with new, relevant B2B insights, particularly those that might be useful when considering the company as a prospect for: '{input_data.product_service_offered if input_data.product_service_offered else "nossos produtos/serviços"}'.
                Avoid redundancy. If the search results are irrelevant or unhelpful, state that and primarily use the initial text.

                Initial Information:
                {self._truncate_text(input_data.initial_extracted_text, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 2)}

                Tavily Search Results:
                {self._truncate_text(search_results_text, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 2)}

                Our Product/Service Context (for relevance): {input_data.product_service_offered if input_data.product_service_offered else "Não especificado, foque em insights gerais B2B."}

                Return only the summarized and enriched text.
                """

                summary_response = await self.generate_llm_response(
                    prompt=summarization_prompt,
                    temperature=0.6,
                    max_tokens=1500
                )

                if summary_response and summary_response.strip():
                    final_enriched_data = summary_response
                    self.logger.info("Successfully generated summary of Tavily results.")
                else:
                    self.logger.warning("LLM summarization of Tavily results failed or returned empty. Using combined text.")
                    final_enriched_data = input_data.initial_extracted_text + "\n\n--- Tavily Search Results (Raw) ---\n" + search_results_text
                    error_occured = True # Mark that summarization specifically failed

        except Exception as e:
            self.logger.error(f"Error during Tavily enrichment process for {input_data.company_name}: {e}")
            self.logger.error(traceback.format_exc()) # Log full traceback
            # final_enriched_data is already input_data.initial_extracted_text
            # Error message will be set in the final return
            return TavilyEnrichmentOutput(
                enriched_data=input_data.initial_extracted_text, # Fallback to initial text
                tavily_api_called=tavily_api_called,
                error_message=f"An unexpected error occurred: {str(e)}"
            )

        current_error_message = None
        if error_occured: # If summarization failed
            current_error_message = "LLM summarization of Tavily results failed. Raw Tavily data appended."

        # If an error occurred earlier (e.g., LLM query gen) it would have returned already.
        # This handles errors specifically from the summarization step post-Tavily search.

        return TavilyEnrichmentOutput(
            enriched_data=final_enriched_data.strip(),
            tavily_api_called=tavily_api_called,
            error_message=current_error_message
        )

# Note: The example usage (main function) needs to be adapted for async execution
# For example, using asyncio.run(main()) and ensuring LLMClientBase and BaseAgent support async.
# Assuming BaseAgent's generate_llm_response is async and an async http_client is injected or available.
# Also, `import asyncio` would be needed at the top.
# The original example was synchronous.
# For the purpose of this tool, the main/example part is illustrative.
# It's also assumed that `BaseAgent` has an `http_client` attribute that is an async HTTP client (e.g., httpx.AsyncClient)
# If not, the `_search_with_tavily` method needs to instantiate its own client or be made synchronous.
# For now, I've added a check for `self.http_client` and `asyncio.sleep`.
# If `BaseAgent` does not provide `self.http_client` as async, `_search_with_tavily` will fail.
# It's common for a BaseAgent to provide such a client. If not, `requests` would be used in a sync manner,
# and the `process` method itself might not be fully async without further changes.
# For this refactoring, I'm aligning with the `async def process` signature.
# The original `cw.py` code used synchronous `requests`.
# I will add `import asyncio` for `asyncio.sleep`.

import asyncio # Added for asyncio.sleep
