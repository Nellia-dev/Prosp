import os
import json
import requests
import asyncio
from typing import Optional, List, Dict, Any

from loguru import logger
from pydantic import BaseModel, Field
from tavily import TavilyClient

from .base_agent import BaseAgent, TInput, TOutput
from core_logic.llm_client import LLMClientBase
from config import TavilyConfig


# Pydantic models for input and output
class TavilyEnrichmentInput(BaseModel):
    company_name: str
    initial_extracted_text: str
    product_service_description: str


class TavilyEnrichmentOutput(BaseModel):
    enrichment_summary: str
    tavily_api_called: bool = Field(default=False)
    error_message: Optional[str] = Field(default=None)


class TavilyEnrichmentAgent(BaseAgent[TavilyEnrichmentInput, TavilyEnrichmentOutput]):
    """Agent specialized in enriching lead information using the Tavily Search API."""

    def __init__(
        self,
        llm_client: LLMClientBase,
        name: str,
        description: str,
        event_queue: asyncio.Queue,
        user_id: str,
        tavily_api_key: Optional[str] = None,
    ):
        super().__init__(llm_client, name, description, event_queue, user_id)
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
        if not self.tavily_api_key:
            self.tavily_client = None
            logger.warning("Tavily API key not found. TavilyEnrichmentAgent will be skipped.")
        else:
            self.tavily_client = TavilyClient(api_key=self.tavily_api_key)

    async def _generate_search_queries(self, company_name: str, initial_text: str, product_service_desc: str) -> List[str]:
        """Generates search queries using an LLM."""
        prompt = f"""
        Based on the company '{company_name}' and its description: '{initial_text}', and considering they might be interested in '{product_service_desc}', generate {TavilyConfig.max_queries} distinct and concise search queries for the Tavily API to find recent news, financial reports, and strategic initiatives. Return a JSON list of strings.
        Example: [\"recent financial performance of {company_name}\", \"strategic partnerships of {company_name} 2024\"]
        """
        response_text = await self.llm_client.get_response(
            model="gemini-1.5-flash",
            temperature=0.2,
            system_message="You are an expert research assistant that returns only a JSON list of strings.",
            prompt=prompt,
        )
        try:
            queries = json.loads(response_text)
            if isinstance(queries, list):
                logger.info(f"Generated {len(queries)} search queries: {queries}")
                return queries
            logger.warning(f"LLM returned a non-list for search queries: {response_text}")
            return []
        except json.JSONDecodeError:
            logger.error(f"Failed to decode LLM response into a list of queries: {response_text}")
            return []

    async def _call_tavily_api(self, query: str) -> List[Dict[str, Any]]:
        """Calls the Tavily API asynchronously using a thread pool executor."""
        if not self.tavily_client:
            return []
        try:
            loop = asyncio.get_running_loop()
            # The TavilyClient is synchronous, so we run it in a thread pool.
            response = await loop.run_in_executor(
                None,  # Use the default executor
                lambda: self.tavily_client.search(query, search_depth="advanced", max_results=5)
            )
            results = response.get("results", [])
            logger.info(f"Tavily search for '{query}' returned {len(results)} results.")
            return results
        except Exception as e:
            logger.error(f"Tavily API call failed for query '{query}': {e}")
            return []

    async def _summarize_results(self, all_results: List[Dict], company_name: str) -> str:
        """Summarizes the collected search results using an LLM."""
        if not all_results:
            return "No new information found."

        context = "\n".join([f"- {res.get('title', '')}: {res.get('content', '')}" for res in all_results])
        prompt = f"""
        Summarize the following research findings about '{company_name}' into a concise paragraph. Focus on key insights relevant for sales prospecting.
        Context:\n{context}
        """
        summary = await self.llm_client.get_response(
            model="claude-3-haiku-20240307",
            temperature=0.3,
            system_message="You are an expert sales intelligence analyst.",
            prompt=prompt,
        )
        return summary

    async def process(self, lead_id: str, input_data: TavilyEnrichmentInput) -> TavilyEnrichmentOutput:
        """The main asynchronous processing method for the agent."""
        await self._emit_event("agent_start", {"agent_name": self.name, "lead_id": lead_id})
        logger.info(f"🔍 Starting Tavily enrichment for {input_data.company_name} (Lead ID: {lead_id})")

        if not self.tavily_client:
            output = TavilyEnrichmentOutput(
                tavily_api_called=False,
                enrichment_summary=input_data.initial_extracted_text,
                error_message="Tavily client not initialized.",
            )
            await self._emit_event("agent_end", {"agent_name": self.name, "lead_id": lead_id, "response": output.model_dump()})
            return output

        search_queries = await self._generate_search_queries(
            input_data.company_name, input_data.initial_extracted_text, input_data.product_service_description
        )

        if not search_queries:
            output = TavilyEnrichmentOutput(
                tavily_api_called=False,
                enrichment_summary=input_data.initial_extracted_text,
                error_message="Could not generate search queries.",
            )
            await self._emit_event("agent_end", {"agent_name": self.name, "lead_id": lead_id, "response": output.model_dump()})
            return output

        # Run searches in parallel
        search_tasks = [self._call_tavily_api(query) for query in search_queries]
        search_results_lists = await asyncio.gather(*search_tasks)
        all_results = [item for sublist in search_results_lists for item in sublist]  # Flatten the list of lists

        if not all_results:
            summary = "No new information found from web search."
        else:
            summary = await self._summarize_results(all_results, input_data.company_name)

        final_summary = f"{input_data.initial_extracted_text}\n\n**Enrichment Data:**\n{summary}"

        output = TavilyEnrichmentOutput(
            enrichment_summary=final_summary,
            tavily_api_called=True,
        )

        logger.info(f"✅ Finished Tavily enrichment for {input_data.company_name} (Lead ID: {lead_id})")
        await self._emit_event("agent_end", {"agent_name": self.name, "lead_id": lead_id, "response": output.model_dump()})
        return output

        # except Exception as e:
        #     self.logger.error(f"❌ An unexpected error occurred in {self.name} for {input_data.company_name}: {e}", exc_info=True)
        #     error_message = f"An unexpected error occurred: {str(e)}"

        # return TavilyEnrichmentOutput(
        #     enrichment_summary=input_data.initial_extracted_text,
        #     tavily_api_called=False,
        #     key_findings=key_findings,
        #     tavily_api_called=tavily_api_called,
        #     error_message=error_message.strip() if error_message else None
        # )

if __name__ == '__main__':
    from loguru import logger
    import sys
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"): # api_key needed for base
            super().__init__(api_key)

        def generate_text_response(self, prompt: str) -> Optional[str]:
            logger.debug(f"MockLLMClient received prompt snippet:\n{prompt[:600]}...")
            if "consultas de pesquisa" in prompt: # Query generation prompt
                return json.dumps({
                    "search_queries": [
                        "latest news about Test Company Inc.",
                        "Test Company Inc. products and services overview",
                        "key contacts or decision makers at Test Company Inc."
                    ]
                })
            elif "Resumo Enriquecido" in prompt or "SCHEMA JSON ESPERADO" in prompt: # Summarization prompt (new)
                return json.dumps({
                    "enrichment_summary": "Test Company Inc. is a notable innovator in the testing solutions sector. Recent news includes a partnership with Beta Corp and the launch of their new 'TestMax' product line. They are actively hiring for sales roles, suggesting expansion.",
                    "key_findings": [
                        "Partnership with Beta Corp.",
                        "Launch of 'TestMax' product line.",
                        "Actively hiring for sales roles (indicates expansion)."
                    ]
                })
            return json.dumps({"enrichment_summary": "Default mock summary.", "key_findings": ["Default finding."]})

    tavily_key = os.getenv("TAVILY_API_KEY_TEST") # Use a specific test key if needed, or fallback to main
    if not tavily_key:
        tavily_key = os.getenv("TAVILY_API_KEY")

    if not tavily_key:
        logger.warning("TAVILY_API_KEY not found in environment variables. Mock tests requiring actual Tavily calls will be limited.")
        # Mock _search_with_tavily to prevent actual API calls if key is missing
        def mock_search_disabled(self, query: str, search_depth: str = "advanced", max_results: int = 5) -> List[dict]:
            logger.info(f"MOCK SEARCH (DISABLED): Would search for '{query}'")
            return [{"url": f"http://mock.tavily.com/{query.replace(' ', '-')}", "content": f"Mock content for query: {query}"}]
        TavilyEnrichmentAgent._search_with_tavily_original = TavilyEnrichmentAgent._search_with_tavily
        TavilyEnrichmentAgent._search_with_tavily = mock_search_disabled
        
    logger.info("Running mock test for TavilyEnrichmentAgent...")
    mock_llm = MockLLMClient(api_key="mock_llm_key")
    agent = TavilyEnrichmentAgent(
        name="TestTavilyAgent",
        description="Test Tavily Agent",
        llm_client=mock_llm,
        tavily_api_key=tavily_key # Pass key, even if it's None (agent handles it)
    )

    test_input = TavilyEnrichmentInput(
        company_name="Test Company Inc.",
        initial_extracted_text="Test Company Inc. is a company that does testing. Their website is testcompany.com."
    )

    output = agent.process(test_input)

    logger.info(f"Tavily API Called: {output.tavily_api_called}")
    logger.info(f"Enrichment Summary: {output.enrichment_summary}")
    logger.info(f"Key Findings: {output.key_findings}")
    if output.error_message:
        logger.error(f"Error: {output.error_message}")

    assert output.tavily_api_called if tavily_key else not output.tavily_api_called # API called only if key exists
    assert "Test Company Inc." in output.enrichment_summary
    if tavily_key: # Only expect key findings if Tavily was actually called and summarization worked
        assert len(output.key_findings) > 0
        assert "TestMax" in output.key_findings[1]

    # Restore original method if mocked
    if hasattr(TavilyEnrichmentAgent, '_search_with_tavily_original'):
        TavilyEnrichmentAgent._search_with_tavily = TavilyEnrichmentAgent._search_with_tavily_original
        del TavilyEnrichmentAgent._search_with_tavily_original

    logger.info("\nMock test for TavilyEnrichmentAgent completed.")
