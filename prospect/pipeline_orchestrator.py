# prospect/pipeline_orchestrator.py

import asyncio
import traceback
import os
import time
from typing import Dict, Any, AsyncIterator
from datetime import datetime
import uuid

from loguru import logger

# Event Models
from event_models import (
    PipelineStartEvent,
    PipelineEndEvent,
    AgentStartEvent,
    AgentEndEvent,
    LeadGeneratedEvent,
    StatusUpdateEvent,
    PipelineErrorEvent,
    LeadEnrichmentStartEvent,
    LeadEnrichmentEndEvent,
)

# ADK Agents (Harvester)
from adk1.agent import (
    root_agent as harvester_query_refiner_agent,
    lead_search_and_qualify_agent as harvester_search_agent,
)

# Enhanced Processor Agents
from agents.lead_intake_agent import LeadIntakeAgent
from agents.lead_analysis_agent import LeadAnalysisAgent
from agents.enhanced_lead_processor import EnhancedLeadProcessor
from data_models.lead_structures import SiteData, GoogleSearchData
from core_logic.llm_client import LLMClientFactory

# ADK Runner
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Constants
ADK_APP_NAME = "prospecter_harvester"
ADK_USER_ID = "prospector_user_1"
ADK_SESSION_SERVICE = InMemorySessionService()


class PipelineOrchestrator:
    """
    Orchestrates the entire lead generation and enrichment pipeline,
    from initial harvesting to deep enrichment, yielding real-time events.
    """

    def __init__(self, business_context: Dict[str, Any], user_id: str, job_id: str):
        self.business_context = business_context
        self.user_id = user_id
        self.job_id = job_id
        self.product_service_context = business_context.get("product_service_description", "")
        self.competitors_list = ", ".join(business_context.get("competitors", []))
        
        # Initialize a single LLM client to be shared by all agents
        self.llm_client = LLMClientFactory.create_from_env()
        
        # Initialize the Enhanced Processor agents here
        self.lead_intake_agent = LeadIntakeAgent(
            llm_client=self.llm_client,
            name="LeadIntakeAgent",
            description="Validates and prepares lead data for processing."
        )
        self.lead_analysis_agent = LeadAnalysisAgent(
            llm_client=self.llm_client,
            name="LeadAnalysisAgent",
            description="Analyzes validated lead data to extract key business insights.",
            product_service_context=self.product_service_context
        )
        self.enhanced_lead_processor = EnhancedLeadProcessor(
            llm_client=self.llm_client,
            name="EnhancedLeadProcessor",
            description="Orchestrates a series of specialized agents to generate a rich, multi-faceted prospect package.",
            product_service_context=self.product_service_context,
            competitors_list=self.competitors_list,
            tavily_api_key=os.getenv("TAVILY_API_KEY")
        )
        logger.info(f"PipelineOrchestrator initialized for job {self.job_id}")

    async def execute_streaming_pipeline(self) -> AsyncIterator[Dict[str, Any]]:
        """
        Main entry point to run the unified pipeline.
        It harvests leads and concurrently enriches them.
        """
        start_time = time.time()
        yield PipelineStartEvent(
            event_type="pipeline_start",
            timestamp=datetime.now().isoformat(),
            job_id=self.job_id,
            user_id=self.user_id,
            initial_query=self.business_context.get("business_description", "N/A"),
            max_leads_to_generate=self.business_context.get("max_leads_to_generate", 10)
        ).to_dict()

        enrichment_tasks = []
        try:
            # Start the harvester as the main task
            async for raw_lead_data in self._run_harvester():
                
                # For each lead found, yield the event and start enrichment
                lead_id = str(uuid.uuid4())
                
                yield LeadGeneratedEvent(
                    event_type="lead_generated",
                    timestamp=datetime.now().isoformat(),
                    job_id=self.job_id,
                    user_id=self.user_id,
                    lead_id=lead_id,
                    lead_data=raw_lead_data,
                    source_url=raw_lead_data.get("website", "N/A"),
                    agent_name=harvester_search_agent.name
                ).to_dict()

                # Create a concurrent task for enriching this lead
                async def _run_enrichment_and_collect_events(lead_data, lead_id):
                    events = []
                    async for event in self._enrich_lead(lead_data, lead_id):
                        events.append(event)
                    return events

                task = asyncio.create_task(_run_enrichment_and_collect_events(raw_lead_data, lead_id))
                enrichment_tasks.append(task)
                await asyncio.sleep(5) # Add a delay to avoid rate limiting

            # Wait for all enrichment tasks to complete
            yield StatusUpdateEvent(
                event_type="status_update",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                status_message="Harvester finished. Waiting for all enrichment tasks to complete..."
            ).to_dict()

            for task_future in asyncio.as_completed(enrichment_tasks):
                events = await task_future
                for event in events:
                    yield event

        except Exception as e:
            logger.error(f"Critical error in pipeline for job {self.job_id}: {e}")
            yield PipelineErrorEvent(
                event_type="pipeline_error",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                error_message=str(e),
                error_type=type(e).__name__
            ).to_dict()
        finally:
            total_time = time.time() - start_time
            yield PipelineEndEvent(
                event_type="pipeline_end",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                total_leads_generated=len(enrichment_tasks),
                execution_time_seconds=total_time,
                success=True # Assuming success if no critical error
            ).to_dict()

    async def _run_harvester(self) -> AsyncIterator[Dict[str, Any]]:
        """
        Runs the ADK-based harvester agent to find potential leads.
        """
        logger.info(f"[{self.job_id}] Starting harvester...")
        
        query_refiner_runner = Runner(
            app_name=ADK_APP_NAME,
            agent=harvester_query_refiner_agent,
            session_service=ADK_SESSION_SERVICE,
        )
        
        search_runner = Runner(
            app_name=ADK_APP_NAME,
            agent=harvester_search_agent,
            session_service=ADK_SESSION_SERVICE,
        )

        initial_query = self.business_context.get("business_description", "")
        if not initial_query:
            logger.warning("No business description found in context for harvester.")
            return

        try:
            session_id = str(uuid.uuid4())
            refined_query_response = None
            # Refine the query
            async for refined_query_response in query_refiner_runner.run_stream(
                user_id=self.user_id,
                session_id=session_id,
                new_message=initial_query,
            ):
                break
            
            if not refined_query_response:
                raise ValueError("Query refiner did not return a response.")

            search_query = refined_query_response.content

            yield StatusUpdateEvent(
                event_type="status_update",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                status_message=f"Harvester query refined to: {search_query}",
                agent_name=harvester_query_refiner_agent.name
            ).to_dict()

            # Search for leads
            max_leads = self.business_context.get("max_leads_to_generate", 10)
            lead_count = 0
            async for lead_chunk in search_runner.run_stream(
                user_id=self.user_id,
                session_id=session_id,
                new_message=search_query,
            ):
                if lead_chunk.content:
                    # Assuming lead_chunk.content is a list of lead dicts
                    for lead in lead_chunk.content:
                        if lead_count >= max_leads:
                            break
                        if "company_name" not in lead:
                            lead["company_name"] = lead.get("website", "Unknown")
                        yield lead
                        lead_count += 1
                if lead_count >= max_leads:
                    logger.info(f"[{self.job_id}] Harvester reached max leads ({max_leads}).")
                    break
        
        except Exception as e:
            logger.error(f"[{self.job_id}] Harvester failed: {e}\n{traceback.format_exc()}")
            yield PipelineErrorEvent(
                event_type="pipeline_error",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                error_message=f"Harvester failed: {e}",
                error_type=type(e).__name__,
                agent_name="Harvester"
            ).to_dict()
        finally:
            logger.info(f"[{self.job_id}] Harvester finished.")


    async def _enrich_lead(self, lead_data: Dict[str, Any], lead_id: str) -> AsyncIterator[Dict[str, Any]]:
        """
        Runs the full enhancement pipeline on a single lead.
        """
        yield LeadEnrichmentStartEvent(
            event_type="lead_enrichment_start",
            timestamp=datetime.now().isoformat(),
            job_id=self.job_id,
            user_id=self.user_id,
            lead_id=lead_id,
            company_name=lead_data.get("company_name", "N/A")
        ).to_dict()

        try:
            # 1. Intake
            site_data = SiteData(
                url=lead_data.get("website") or "http://example.com",
                extracted_text_content=lead_data.get("description"),
                google_search_data=GoogleSearchData(
                    title=lead_data.get("company_name") or lead_data.get("website", "Unknown"),
                    snippet=lead_data.get("description", "")
                ),
                extraction_status_message="SUCCESS"
            )
            validated_lead = self.lead_intake_agent.execute(site_data)
            if not validated_lead.is_valid:
                raise ValueError(f"Lead intake failed: {validated_lead.validation_errors}")

            # 2. Initial Analysis
            analyzed_lead = self.lead_analysis_agent.execute(validated_lead)

            # 3. Full Enrichment
            # The enhanced_processor itself yields events, so we can pass them through
            async for event in self.enhanced_lead_processor.execute_enrichment_pipeline(
                analyzed_lead=analyzed_lead,
                job_id=self.job_id,
                user_id=self.user_id
            ):
                # Add lead_id to every event for frontend tracking
                event["lead_id"] = lead_id
                yield event
            
            # The final event from the enrichment pipeline is PipelineEndEvent,
            # which contains the full package. We'll capture that here.
            final_package = event.get("data")

            yield LeadEnrichmentEndEvent(
                event_type="lead_enrichment_end",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                lead_id=lead_id,
                success=True,
                final_package=final_package
            ).to_dict()

        except Exception as e:
            logger.error(f"Enrichment failed for lead {lead_id}: {e}\n{traceback.format_exc()}")
            yield LeadEnrichmentEndEvent(
                event_type="lead_enrichment_end",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                lead_id=lead_id,
                success=False,
                error_message=str(e)
            ).to_dict()