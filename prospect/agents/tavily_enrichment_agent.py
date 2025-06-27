import os
import json
import requests
import asyncio
import time
import traceback
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
        super().__init__(name=name, description=description, llm_client=llm_client, event_queue=event_queue, user_id=user_id)
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
        llm_response = await asyncio.to_thread(
                self.llm_client.generate,
                prompt
            )
        response_text = llm_response.content
        # Clean the response: remove markdown and trim whitespace
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0]
        response_text = response_text.strip()
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
        llm_response = await asyncio.to_thread(self.llm_client.generate, prompt)
        summary = llm_response.content
        return summary

    async def process(self, lead_id: str, job_id: str, input_data: TavilyEnrichmentInput) -> TavilyEnrichmentOutput:
        """The main asynchronous processing method for the agent."""
        start_time = time.time()
        await self._emit_event("agent_start", {
            "agent_name": self.name,
            "job_id": job_id,
            "lead_id": lead_id,
            "agent_description": self.description,
            "input_query": input_data.model_dump_json(indent=2)
        })
        logger.info(f"🔍 Starting Tavily enrichment for {input_data.company_name} (Lead ID: {lead_id})")

        try:
            if not self.tavily_client:
                output = TavilyEnrichmentOutput(
                    tavily_api_called=False,
                    enrichment_summary=input_data.initial_extracted_text,
                    error_message="Tavily client not initialized.",
                )
                duration = time.time() - start_time
                await self._emit_event("agent_end", {
                    "agent_name": self.name,
                    "job_id": job_id,
                    "lead_id": lead_id,
                    "duration": duration,
                    "output": output.model_dump()
                })
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
                duration = time.time() - start_time
                await self._emit_event("agent_end", {
                    "agent_name": self.name,
                    "job_id": job_id,
                    "lead_id": lead_id,
                    "duration": duration,
                    "output": output.model_dump()
                })
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
            duration = time.time() - start_time
            await self._emit_event("agent_end", {
                "agent_name": self.name,
                "job_id": job_id,
                "lead_id": lead_id,
                "duration": duration,
                "output": output.model_dump()
            })
            return output

        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"❌ An unexpected error occurred in {self.name} for {input_data.company_name}: {e}", exc_info=True)
            await self._emit_event("pipeline_error", {
                "agent_name": self.name,
                "job_id": job_id,
                "lead_id": lead_id,
                "duration": duration,
                "error_message": str(e),
                "details": traceback.format_exc()
            })
            raise


if __name__ == '__main__':
    import sys
    from core_logic.llm_client import MockLLMResponse

    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key=api_key)

        def generate(self, prompt: str, temperature: float = 0.1) -> MockLLMResponse:
            logger.debug(f"MockLLMClient received prompt snippet:\n{prompt[:500]}...")
            if "generate search queries" in prompt:
                # Return a JSON list of strings for search queries
                queries = [
                    "latest news about Test Company Inc.",
                    "Test Company Inc. products and services overview",
                    "key contacts or decision makers at Test Company Inc."
                ]
                return MockLLMResponse(content=json.dumps(queries))
            elif "Summarize the following research findings" in prompt:
                # Return a summary string
                summary = "Test Company Inc. is a notable innovator in the testing solutions sector. Recent news includes a partnership with Beta Corp and the launch of their new 'TestMax' product line."
                return MockLLMResponse(content=summary)
            
            return MockLLMResponse(content="Default mock summary.")

    async def main():
        tavily_key = os.getenv("TAVILY_API_KEY")
        if not tavily_key:
            logger.warning("TAVILY_API_KEY not found. Actual API calls will be skipped.")

        mock_llm = MockLLMClient()
        event_queue = asyncio.Queue()

        agent = TavilyEnrichmentAgent(
            name="TestTavilyAgent",
            description="Test Tavily Agent",
            llm_client=mock_llm,
            event_queue=event_queue,
            user_id="test_user",
            tavily_api_key=tavily_key
        )

        test_input = TavilyEnrichmentInput(
            company_name="Test Company Inc.",
            initial_extracted_text="Test Company Inc. is a company that does testing.",
            product_service_description="testing solutions"
        )

        lead_id = "test_lead_123"
        job_id = "test_job_456"

        logger.info(f"Running test for TavilyEnrichmentAgent with Lead ID: {lead_id}")
        
        # In a real scenario, Tavily client would make a network request.
        # For this test, it will proceed if the key is present.
        output = await agent.process(lead_id, job_id, test_input)

        logger.info(f"\n--- Agent Output ---")
        logger.info(f"Tavily API Called: {output.tavily_api_called}")
        logger.info(f"Enrichment Summary:\n{output.enrichment_summary}")
        if output.error_message:
            logger.error(f"Error: {output.error_message}")
        logger.info(f"--------------------\n")

        assert output.tavily_api_called == bool(tavily_key)
        assert "Test Company Inc." in output.enrichment_summary
        if tavily_key:
            assert "TestMax" in output.enrichment_summary

        # Check events
        while not event_queue.empty():
            event = await event_queue.get()
            logger.info(f"Event received: {event['event_type']}")
            assert event['payload']['lead_id'] == lead_id

        logger.info("✅ Test for TavilyEnrichmentAgent completed successfully.")

    asyncio.run(main())
