# prospect/mcp_server.py

import asyncio
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger
import uvicorn
import os
from dotenv import load_dotenv
import httpx
from typing import Dict, Any

# Add project root to path to allow imports
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline_orchestrator import PipelineOrchestrator

class WebhookEventSender:
    """Sends pipeline events to the webapp webhook endpoint"""
    
    def __init__(self, webhook_url: str, enabled: bool = True):
        self.webhook_url = webhook_url
        self.enabled = enabled
        self.client = httpx.AsyncClient(timeout=30.0) if enabled else None
        logger.info(f"WebhookEventSender initialized - URL: {webhook_url}, Enabled: {enabled}")
    
    async def send_event(self, event: Dict[str, Any]):
        """Send pipeline event to webapp webhook"""
        if not self.enabled or not self.client:
            return
            
        try:
            response = await self.client.post(
                f"{self.webhook_url}/queue/mcp/event-stream",
                json=event,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.debug(f"Webhook event sent successfully: {event.get('event_type', 'unknown')}")
            else:
                logger.warning(f"Webhook failed with status {response.status_code}: {response.text}")
                
        except httpx.TimeoutException:
            logger.warning(f"Webhook timeout for event: {event.get('event_type', 'unknown')}")
        except Exception as e:
            logger.error(f"Webhook error for event {event.get('event_type', 'unknown')}: {e}")
    
    async def close(self):
        """Close the HTTP client"""
        if self.client:
            await self.client.aclose()

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Nellia Prospector MCP Server",
    description="Provides endpoints to run the unified prospecting and enrichment pipeline.",
    version="2.0.0"
)

@app.on_event("startup")
async def startup_event():
    logger.add(sys.stderr, level="INFO", format="{time} {level} {message}")
    logger.info("MCP Server starting up...")
    # You can add any other startup logic here, like checking API keys
    if not os.getenv("GEMINI_API_KEY"):
        logger.warning("GEMINI_API_KEY is not set in the environment.")
    if not os.getenv("TAVILY_API_KEY"):
        logger.warning("TAVILY_API_KEY is not set in the environment.")


@app.get("/health", tags=["System"])
async def health_check():
    """Check if the server is running."""
    return {"status": "ok"}


@app.post("/api/v2/execute_streaming_prospect", tags=["Pipeline"])
async def execute_streaming_prospect(request: Request):
    """
    Executes the unified harvesting and enrichment pipeline, streaming events back.
    """
    webhook_sender = None
    try:
        payload = await request.json()
        business_context = payload.get("business_context")
        user_id = payload.get("user_id")
        job_id = payload.get("job_id")

        if not all([business_context, user_id, job_id]):
            raise HTTPException(status_code=400, detail="Missing required fields: business_context, user_id, job_id")

        logger.info(f"Received request to execute pipeline for job_id: {job_id}, user_id: {user_id}")

        # Initialize webhook sender - now uses queue endpoint
        webapp_webhook_url = os.getenv("WEBAPP_WEBHOOK_URL", "http://webapp-backend:3001")
        webhook_enabled = os.getenv("WEBAPP_WEBHOOK_ENABLED", "true").lower() == "true"
        webhook_sender = WebhookEventSender(webapp_webhook_url, webhook_enabled)

        logger.info("[PIPELINE_STEP] Initializing PipelineOrchestrator")
        orchestrator = PipelineOrchestrator(
            business_context=business_context,
            user_id=user_id,
            job_id=job_id,
            use_hybrid= True,  # Use hybrid mode for both Gemini and TAVILY
        )

        async def event_stream():
            """The async generator that yields events from the pipeline."""
            try:
                logger.info(f"Starting pipeline execution for job_id: {job_id}")
                # This is the key fix - actually call the main pipeline method
                async for event in orchestrator.execute_streaming_pipeline():
                    # Ensure user_id and job_id are in every event
                    event["user_id"] = user_id
                    event["job_id"] = job_id
                    
                    logger.debug(f"Pipeline event: {event.get('event_type', 'unknown')}")
                    
                    # Send to webapp webhook
                    await webhook_sender.send_event(event)
                    
                    # Stream to client
                    yield f"data: {json.dumps(event)}\n\n"
                    await asyncio.sleep(0.01) # Small sleep to prevent blocking
                    
                logger.info(f"Pipeline execution completed for job_id: {job_id}")
                    
            except Exception as e:
                logger.error(f"Error in pipeline execution for job_id {job_id}: {e}")
                error_event = {
                    "event_type": "pipeline_error",
                    "job_id": job_id,
                    "user_id": user_id,
                    "error_message": str(e),
                    "timestamp": json.dumps({"timestamp": "now"})  # Will be replaced by proper timestamp
                }
                await webhook_sender.send_event(error_event)
                yield f"data: {json.dumps(error_event)}\n\n"
            finally:
                # Cleanup webhook sender
                if webhook_sender:
                    await webhook_sender.close()

        logger.info("[PIPELINE_STEP] Returning StreamingResponse")
        return StreamingResponse(event_stream(), media_type="text/event-stream")

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")
    except Exception as e:
        logger.error(f"Error processing streaming prospect request: {e}")
        # Cleanup webhook sender on error
        if webhook_sender:
            try:
                await webhook_sender.close()
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


if __name__ == "__main__":
    port = int(os.getenv("MCP_SERVER_PORT", 5001))
    uvicorn.run(app, host="0.0.0.0", port=port)
