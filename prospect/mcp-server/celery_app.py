import os
import sys
import asyncio
import requests
from celery import Celery
from datetime import datetime
import time
from loguru import logger
from typing import List

# Add parent directory to allow imports from the 'prospect' module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- NEW IMPORTS for unified pipeline ---
from core_logic.llm_client import LLMClientFactory
from data_models.lead_structures import HarvesterOutput, SiteData, GoogleSearchData, AnalyzedLead
from agents.lead_intake_agent import LeadIntakeAgent
from agents.lead_analysis_agent import LeadAnalysisAgent
from agents.enhanced_lead_processor import EnhancedLeadProcessor
from event_models import PipelineErrorEvent
# --- END NEW IMPORTS ---


# Get Webhook URLs from environment variables
NESTJS_WEBHOOK_URL = os.getenv('NESTJS_WEBHOOK_URL', 'http://localhost:3000/api/mcp/webhook/job-complete')
# New webhook for real-time event streaming
NESTJS_EVENT_WEBHOOK_URL = os.getenv('NESTJS_EVENT_WEBHOOK_URL', 'http://localhost:3000/api/mcp/webhook/event-stream')


# Configure Celery
celery_app = Celery(
    'mcp_tasks',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# --- NEW HELPER FUNCTION ---
def post_event_to_webhook(event_data: dict):
    """Posts a single event to the real-time event webhook."""
    try:
        # Use a session for connection pooling
        with requests.Session() as s:
            response = s.post(NESTJS_EVENT_WEBHOOK_URL, json=event_data, timeout=10)
            response.raise_for_status()
            logger.info(f"Successfully posted event '{event_data.get('event_type')}' to webhook.")
    except requests.exceptions.RequestException as e:
        logger.error(f"CRITICAL: Failed to send event webhook for job_id: {event_data.get('job_id')}. Error: {e}")
        # In a production system, this might need a retry mechanism or dead-letter queue.

# --- REWRITTEN CELERY TASK ---
@celery_app.task(name='mcp.tasks.run_agentic_harvester_task')
def run_agentic_harvester_task(job_data: dict):
    """
    Celery task to run the FULL unified pipeline: Harvester -> Intake -> Analysis -> Enrichment.
    This task now streams events in real-time to the backend.
    """
    job_id = job_data.get('job_id')
    user_id = job_data.get('user_id')
    
    # Configure logger for this task run
    task_logger = logger.bind(job_id=job_id, user_id=user_id)
    task_logger.info("Unified Celery task started.")

    # This is a placeholder for the actual harvester logic.
    # In a real scenario, a harvester would run here and produce SiteData objects.
    # For this refactoring, we simulate its output based on the initial query.
    # We assume the harvester found one "lead" which is the company from the query.
    harvester_output = HarvesterOutput(
        sites_data=[
            SiteData(
                url=f"http://www.{job_data['initial_query'].replace(' ', '').lower()}.com",
                extracted_text_content=f"Information about {job_data['initial_query']}",
                google_search_data=GoogleSearchData(
                    title=f"{job_data['initial_query']} - Official Site",
                    link=f"http://www.{job_data['initial_query'].replace(' ', '').lower()}.com",
                    snippet=f"The official website for {job_data['initial_query']}"
                )
            )
        ]
    )
    
    # Initialize the core components needed for the pipeline
    llm_client = LLMClientFactory.create_from_env()
    business_context = job_data.get('business_context', {})
    product_service_context = business_context.get('product_service_description', '')
    competitors_list = ", ".join(business_context.get('competitors', []))

    lead_intake_agent = LeadIntakeAgent(llm_client=llm_client)
    lead_analysis_agent = LeadAnalysisAgent(llm_client=llm_client, product_service_context=product_service_context)
    enhanced_processor = EnhancedLeadProcessor(
        llm_client=llm_client,
        product_service_context=product_service_context,
        competitors_list=competitors_list
    )

    # Run the pipeline asynchronously
    loop = asyncio.get_event_loop()
    final_results = loop.run_until_complete(
        _run_full_pipeline(
            harvester_output,
            lead_intake_agent,
            lead_analysis_agent,
            enhanced_processor,
            job_id,
            user_id,
            task_logger
        )
    )

    # Send the final job completion webhook
    webhook_payload = {
        "job_id": job_id,
        "user_id": user_id,
        "status": "completed" if final_results.get("success") else "failed",
        "data": final_results
    }

    try:
        task_logger.info(f"Sending final 'job-complete' webhook to {NESTJS_WEBHOOK_URL}")
        response = requests.post(NESTJS_WEBHOOK_URL, json=webhook_payload, timeout=30)
        response.raise_for_status()
        task_logger.info(f"Final webhook sent successfully. Status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        task_logger.error(f"CRITICAL: Failed to send final webhook. Error: {e}")

    return webhook_payload


async def _run_full_pipeline(
    harvester_output: HarvesterOutput,
    intake_agent: LeadIntakeAgent,
    analysis_agent: LeadAnalysisAgent,
    enrichment_processor: EnhancedLeadProcessor,
    job_id: str,
    user_id: str,
    task_logger
) -> dict:
    """
    The main async pipeline logic.
    """
    total_leads_processed = 0
    total_leads_succeeded = 0
    all_enriched_packages = []
    start_time = time.time()

    # 1. Intake and Analysis Stage
    task_logger.info(f"Starting Intake and Analysis for {len(harvester_output.sites_data)} sites.")
    analyzed_leads: List[AnalyzedLead] = []
    for site_data in harvester_output.sites_data:
        try:
            validated_lead = await intake_agent.execute(site_data)
            if not validated_lead.is_valid:
                task_logger.warning(f"Skipping invalid lead: {site_data.url}")
                continue
            
            analyzed_lead = await analysis_agent.execute(validated_lead)
            if analyzed_lead.analysis.relevance_score < 0.1: # Basic relevance filter
                task_logger.warning(f"Skipping irrelevant lead: {site_data.url} (Score: {analyzed_lead.analysis.relevance_score})")
                continue
            
            analyzed_leads.append(analyzed_lead)
        except Exception as e:
            task_logger.error(f"Failed during intake/analysis for {site_data.url}: {e}")

    task_logger.info(f"Intake/Analysis complete. {len(analyzed_leads)} leads are qualified for enrichment.")

    # 2. Enrichment Stage
    for lead_to_enrich in analyzed_leads:
        total_leads_processed += 1
        task_logger.info(f"Starting enrichment for lead: {lead_to_enrich.validated_lead.site_data.url}")
        try:
            async for event in enrichment_processor.execute_enrichment_pipeline(
                analyzed_lead=lead_to_enrich,
                job_id=job_id,
                user_id=user_id
            ):
                # Stream every event immediately
                post_event_to_webhook(event)
                
                # If this is the final event for this lead, capture the data
                if event.get("event_type") == "pipeline_end" and event.get("success"):
                    all_enriched_packages.append(event.get("data"))
                    total_leads_succeeded += 1

        except Exception as e:
            task_logger.error(f"Enrichment failed for lead {lead_to_enrich.validated_lead.site_data.url}: {e}")
            # Post a failure event for this specific lead
            error_event = PipelineErrorEvent(
                timestamp=datetime.now().isoformat(),
                job_id=job_id,
                user_id=user_id,
                error_message=str(e),
                error_type=type(e).__name__
            ).to_dict()
            post_event_to_webhook(error_event)

    execution_time = time.time() - start_time
    task_logger.info(f"Full pipeline processing finished in {execution_time:.2f}s.")

    return {
        "success": total_leads_succeeded > 0,
        "total_leads_generated": total_leads_succeeded,
        "total_leads_processed": total_leads_processed,
        "execution_time_seconds": execution_time,
        "leads_data": all_enriched_packages # This now contains the full ComprehensiveProspectPackage
    }