import os
import sys
import asyncio
import json
import requests
from celery import Celery
from datetime import datetime
import time
from loguru import logger
from typing import List

# Add parent directory to allow imports from the 'prospect' module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- NEW IMPORTS for unified pipeline ---
from event_models import PipelineErrorEvent
from run import execute_agentic_pipeline # Import the real pipeline
# --- END NEW IMPORTS ---


# Get Webhook URLs from environment variables
NESTJS_WEBHOOK_URL = os.getenv('NESTJS_WEBHOOK_URL', 'http://backend:3001/api/v1/mcp/webhook/job-complete')
# New webhook for real-time event streaming
NESTJS_EVENT_WEBHOOK_URL = os.getenv('NESTJS_EVENT_WEBHOOK_URL', 'http://backend:3001/api/v1/mcp/webhook/event-stream')


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
    Celery task to orchestrate the agentic pipeline from 'run.py'.
    It generates an initial query and then calls the pipeline, streaming all
    events back to the NestJS backend via webhooks.
    """
    job_id = job_data.get('job_id')
    user_id = job_data.get('user_id')
    business_context = job_data.get('business_context', {})
    max_leads = job_data.get('max_leads_to_generate', 5) # Default to 5 leads

    task_logger = logger.bind(job_id=job_id, user_id=user_id)
    task_logger.info(f"CELERY_TASK_RECEIVED: Starting job with data: {job_data}")

    if not business_context:
        task_logger.error("Job failed: No business_context provided.")
        # Optionally send a failure event
        return

    # 1. Generate the initial search query from business context
    task_logger.info("Generating search query from business context...")
    initial_query = ""
    try:
        # This logic remains to create the initial seed query for the pipeline
        from adk1.agent import business_context_to_query_agent
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
        response = model.generate_content(
            f"{business_context_to_query_agent.instruction}\n\nContexto de Negócio:\n{json.dumps(business_context, indent=2)}"
        )
        initial_query = response.text.strip()
        task_logger.info(f"Generated initial query: '{initial_query}'")
    except Exception as e:
        task_logger.error(f"Failed to generate initial query: {e}")
        error_event = PipelineErrorEvent(
            timestamp=datetime.now().isoformat(),
            job_id=job_id,
            user_id=user_id,
            error_message=f"Failed to generate initial query: {e}",
            error_type="QueryGenerationError"
        ).to_dict()
        post_event_to_webhook(error_event)
        return

    # 2. Run the actual agentic pipeline and stream events
    task_logger.info("Starting agentic pipeline execution...")
    final_pipeline_results = {}
    try:
        # Use an async function to run the async generator
        final_pipeline_results = asyncio.run(
            _run_pipeline_and_stream_events(
                initial_query=initial_query,
                business_context=business_context,
                user_id=user_id,
                job_id=job_id,
                max_leads_to_generate=max_leads
            )
        )
        task_logger.info("Agentic pipeline execution finished.")
    except Exception as e:
        task_logger.error(f"An unexpected error occurred during pipeline execution: {e}")
        error_event = PipelineErrorEvent(
            timestamp=datetime.now().isoformat(),
            job_id=job_id,
            user_id=user_id,
            error_message=f"Top-level pipeline execution error: {e}",
            error_type=type(e).__name__
        ).to_dict()
        post_event_to_webhook(error_event)

    # 3. Send the final job completion webhook
    # The 'data' in this payload can be simplified, as detailed events were already sent.
    webhook_payload = {
        "job_id": job_id,
        "user_id": user_id,
        "status": "completed" if final_pipeline_results.get("success") else "failed",
        "data": final_pipeline_results
    }

    try:
        task_logger.info(f"Sending final 'job-complete' webhook to {NESTJS_WEBHOOK_URL}")
        response = requests.post(NESTJS_WEBHOOK_URL, json=webhook_payload, timeout=30)
        response.raise_for_status()
        task_logger.info(f"Final webhook sent successfully. Status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        task_logger.error(f"CRITICAL: Failed to send final webhook. Error: {e}")

    return webhook_payload


async def _run_pipeline_and_stream_events(**kwargs) -> dict:
    """
    Asynchronously runs the agentic pipeline and streams all events via webhook.
    """
    final_event_data = {}
    enriched_leads = []
    async for event in execute_agentic_pipeline(**kwargs):
        post_event_to_webhook(event)
        
        # Capture lead data as it is generated
        if event.get("event_type") == "lead_enriched":
            enriched_leads.append(event.get("lead_data"))

        # Capture the final 'pipeline_end' event to return summary data
        if event.get("event_type") == "pipeline_end":
            final_event_data = {
                "success": event.get("success", False),
                "total_leads_generated": event.get("total_leads_generated", 0),
                "execution_time_seconds": event.get("execution_time_seconds", 0),
                "error_message": event.get("error_message"),
                "leads": enriched_leads  # Include the aggregated leads
            }
    return final_event_data