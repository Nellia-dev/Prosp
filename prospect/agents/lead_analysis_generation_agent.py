from typing import Optional
from pydantic import BaseModel, Field
import json 
import asyncio
import time
import traceback
from textwrap import dedent
from loguru import logger

from .base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000  

class LeadAnalysisGenerationInput(BaseModel):
    lead_data_str: str = Field(..., description="JSON string representing structured lead data.")
    enriched_data: str = Field(..., description="Text string of enriched data from web searches, news, etc.")
    product_service_offered: str = Field(..., description="Description of the user's product/service for context.")


class LeadAnalysisGenerationOutput(BaseModel):
    analysis_report: str = Field(..., description="The generated textual analysis report for the lead.")


class LeadAnalysisGenerationAgent(BaseAgent[LeadAnalysisGenerationInput, LeadAnalysisGenerationOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, output_language: str = "en-US", **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)
        self.output_language = output_language

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    async def process(self, lead_id: str, job_id: str, input_data: LeadAnalysisGenerationInput) -> LeadAnalysisGenerationOutput:
        start_time = time.time()
        await self._emit_event("agent_start", {
            "agent_name": self.name,
            "job_id": job_id,
            "lead_id": lead_id,
            "agent_description": self.description,
            "input_data": input_data.model_dump()
        })
        logger.info(f"📊 Starting analysis generation for lead {lead_id}")

        try:
            prompt_fixed_overhead = 2000 
            available_for_dynamic = GEMINI_TEXT_INPUT_TRUNCATE_CHARS - prompt_fixed_overhead
            truncated_lead_data = self._truncate_text(input_data.lead_data_str, available_for_dynamic // 2)
            truncated_enriched_data = self._truncate_text(input_data.enriched_data, available_for_dynamic // 2)
            
            prompt_template = dedent("""
                You are a Senior Business Intelligence Analyst... Your task is to generate an insightful textual analysis of the lead, contextualized by our product/service: "{product_service_offered}".

                LEAD DATA (source: internally structured JSON):
                ---
                {lead_data_str}
                ---

                ENRICHED DATA (source: additional web research, news, etc.):
                ---
                {enriched_data}
                ---

                INSTRUCTIONS FOR THE ANALYSIS REPORT:
                Based on ALL provided data, draft a textual report covering:
                1.  **Company Overview:** Industry sector and main product/service.
                2.  **Estimated Size and Structure:** Company size and organizational structure.
                3.  **Key Challenges and Needs:** Challenges addressable by "{product_service_offered}".
                4.  **Culture and Values:** Any discernible cultural aspects.
                5.  **General Diagnosis and Conversion Potential:** Summarized diagnosis and conversion potential.

                GUIDELINES:
                - **Objectivity:** Base analysis on available information, noting any gaps.
                - **Format:** A well-articulated running text. DO NOT use JSON.
                - **Style:** Professional, analytical, and insightful.
                - **Length:** Max 300-350 words.
                - **Language:** Generate the entire response strictly in {output_language}.

                Begin the report directly with the analysis.
                LEAD ANALYSIS REPORT:
            """)
            
            final_prompt = prompt_template.format(
                product_service_offered=input_data.product_service_offered,
                lead_data_str=truncated_lead_data,
                enriched_data=truncated_enriched_data,
                output_language=self.output_language
            )

            logger.debug(f"Prompt for {self.name} (length: {len(final_prompt)}):\n{final_prompt[:500]}...")

            llm_response = await asyncio.to_thread(self.llm_client.generate, final_prompt)

            if not llm_response or not llm_response.content:
                raise ValueError("LLM call returned no response or an empty response.")

            analysis_report = llm_response.content.strip()
            logger.info(f"✅ Report generated for lead {lead_id}, length: {len(analysis_report)}")
            
            output = LeadAnalysisGenerationOutput(analysis_report=analysis_report)
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
            error_message = f"An unexpected error occurred in {self.name}: {e}"
            logger.error(error_message, exc_info=True)
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
    import json
    from core_logic.llm_client import MockLLMResponse

    logger.remove()
    logger.add(sys.stderr, level="INFO")

    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key=api_key)

        def generate(self, prompt: str, **kwargs) -> MockLLMResponse:
            logger.debug(f"MockLLMClient received prompt snippet...\n")
            report = "This is a mock analysis report for the test lead. It confirms the company is in the tech sector and has a high potential for conversion."
            return MockLLMResponse(content=report)

    async def main():
        mock_llm = MockLLMClient()
        event_queue = asyncio.Queue()

        agent = LeadAnalysisGenerationAgent(
            name="TestLeadAnalysisGenerator",
            description="Generates a textual analysis report for a lead.",
            llm_client=mock_llm,
            event_queue=event_queue,
            user_id="test_user",
            output_language="en-US"
        )

        test_input = LeadAnalysisGenerationInput(
            lead_data_str=json.dumps({"company_name": "TestCorp", "sector": "Technology"}),
            enriched_data="TestCorp was featured in a recent article about innovation.",
            product_service_offered="AI-powered sales automation"
        )

        lead_id = "lead_gen_123"
        job_id = "job_gen_456"

        logger.info(f"Running test for {agent.name} with Lead ID: {lead_id}")
        output = await agent.process(lead_id, job_id, test_input)

        logger.info(f"\n--- Agent Output ---")
        logger.info(f"Analysis Report:\n{output.analysis_report}")
        logger.info(f"--------------------\n")

        assert "mock analysis report" in output.analysis_report
        assert "high potential" in output.analysis_report

        # Check events
        event_count = 0
        while not event_queue.empty():
            event = await event_queue.get()
            logger.info(f"Event received: {event['event_type']}")
            assert event['payload']['lead_id'] == lead_id
            event_count += 1
        
        assert event_count == 2  # agent_start and agent_end

        logger.info(f"✅ Test for {agent.name} completed successfully.")

    asyncio.run(main())
