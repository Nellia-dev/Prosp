import os
import sys
import asyncio
import requests
from celery import Celery
from datetime import datetime

# Add parent directory to allow imports from the 'prospect' module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run import execute_agentic_pipeline

# Get Webhook URL from environment variable, with a default for local development
NESTJS_WEBHOOK_URL = os.getenv('NESTJS_WEBHOOK_URL', 'http://localhost:3000/api/mcp/webhook/job-complete')

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

@celery_app.task(name='mcp.tasks.run_agentic_harvester_task')
def run_agentic_harvester_task(job_data: dict):
    """
    Celery task to run the agentic harvester pipeline asynchronously.
    """
    job_id = job_data.get('job_id')
    user_id = job_data.get('user_id')
    
    print(f"[{datetime.now()}] Celery task started for job_id: {job_id}")
    
    loop = asyncio.get_event_loop()
    events = []
    leads_data = []
    final_result = {}

    try:
        # Define an async function to collect results from the pipeline
        async def collect_pipeline_results():
            async for event in execute_agentic_pipeline(
                initial_query=job_data['initial_query'],
                business_context=job_data['business_context'],
                user_id=job_data['user_id'],
                max_leads_to_generate=job_data['max_leads_to_generate'],
                config_overrides={"max_sites_to_scrape": job_data['max_sites_to_scrape']}
            ):
                events.append(event)
                if event.get('event_type') == 'lead_generated':
                    leads_data.append(event.get('lead_data'))
                elif event.get('event_type') == 'pipeline_end':
                    return {
                        "success": event.get('success', True),
                        "total_leads_generated": event.get('total_leads_generated', 0),
                        "execution_time_seconds": event.get('execution_time_seconds', 0),
                        "error_message": event.get('error_message'),
                        "leads_data": leads_data
                    }
            # Fallback if pipeline_end is not reached
            return {
                "success": False,
                "error_message": "Pipeline did not complete as expected.",
                "leads_data": leads_data
            }

        # Run the async function and get the final result
        final_result = loop.run_until_complete(collect_pipeline_results())
        print(f"[{datetime.now()}] Pipeline execution finished for job_id: {job_id}. Success: {final_result.get('success')}")

    except Exception as e:
        print(f"[{datetime.now()}] An exception occurred during pipeline execution for job_id: {job_id}. Error: {e}")
        final_result = {
            "success": False,
            "error_message": str(e),
            "leads_data": leads_data
        }

    # Construct the webhook payload
    webhook_payload = {
        "job_id": job_id,
        "user_id": user_id,
        "status": "completed" if final_result.get("success") else "failed",
        "data": final_result
    }

    # Send the results back to the NestJS backend via webhook
    try:
        print(f"[{datetime.now()}] Sending webhook for job_id: {job_id} to {NESTJS_WEBHOOK_URL}")
        response = requests.post(NESTJS_WEBHOOK_URL, json=webhook_payload, timeout=30)
        response.raise_for_status()
        print(f"[{datetime.now()}] Webhook sent successfully for job_id: {job_id}. Status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now()}] CRITICAL: Failed to send webhook for job_id: {job_id}. Error: {e}")
        # In a production system, this should trigger a retry mechanism
    
    return webhook_payload