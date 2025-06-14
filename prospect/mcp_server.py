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
                f"{self.webhook_url},
                json=event,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code in [200, 201]:
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
    logger.info("🚀 MCP Server starting up...")
    
    # Check API keys - ADK1 uses GOOGLE_API_KEY, not GEMINI_API_KEY
    google_api_key = os.getenv("GOOGLE_API_KEY")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    
    if not google_api_key and not gemini_api_key:
        logger.error("❌ Neither GOOGLE_API_KEY nor GEMINI_API_KEY is set in the environment.")
        logger.error("   ADK1 agent requires GOOGLE_API_KEY to function properly.")
    elif google_api_key:
        logger.info("✅ GOOGLE_API_KEY found (required for ADK1)")
    elif gemini_api_key:
        logger.warning("⚠️ Only GEMINI_API_KEY found. ADK1 requires GOOGLE_API_KEY.")
        # Set GOOGLE_API_KEY from GEMINI_API_KEY if available
        os.environ["GOOGLE_API_KEY"] = gemini_api_key
        logger.info("🔄 Set GOOGLE_API_KEY from GEMINI_API_KEY for ADK1 compatibility")
    
    if not tavily_api_key:
        logger.error("❌ TAVILY_API_KEY is not set in the environment.")
        logger.error("   ADK1 agent requires TAVILY_API_KEY for web search functionality.")
    else:
        logger.info("✅ TAVILY_API_KEY found")
    
    # Test PipelineOrchestrator import
    try:
        logger.info("🧪 Testing PipelineOrchestrator import...")
        from pipeline_orchestrator import PipelineOrchestrator
        logger.info("✅ PipelineOrchestrator imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import PipelineOrchestrator: {e}")
        import traceback
        traceback.print_exc()


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
        user_search_query = payload.get("user_search_query", "")  # Optional user input for search

        if not all([business_context, user_id, job_id]):
            raise HTTPException(status_code=400, detail="Missing required fields: business_context, user_id, job_id")

        # Add user search query to business context if provided
        if user_search_query.strip():
            business_context["user_search_query"] = user_search_query.strip()
            logger.info(f"User provided additional search query: '{user_search_query}'")

        logger.info(f"Received request to execute pipeline for job_id: {job_id}, user_id: {user_id}")

        # Initialize webhook sender with better error handling
        webapp_webhook_url = os.getenv("NESTJS_EVENT_WEBHOOK_URL", "http://backend:3001")
        webhook_enabled = os.getenv("WEBAPP_WEBHOOK_ENABLED", "true").lower() == "true"
        
        # Test webhook connectivity and disable if unreachable
        if webhook_enabled:
            try:
                # Quick connectivity test
                import socket
                hostname = webapp_webhook_url.replace("http://", "").replace("https://", "").split(":")[0]
                socket.gethostbyname(hostname)
                logger.info(f"Webhook hostname {hostname} is resolvable, webhooks enabled")
            except socket.gaierror:
                logger.warning(f"Webhook hostname {hostname} is not resolvable, disabling webhooks for this run")
                webhook_enabled = False
        
        webhook_sender = WebhookEventSender(webapp_webhook_url, webhook_enabled)

        logger.info(f"[PIPELINE_STEP] Initializing PipelineOrchestrator for job {job_id}")
        
        try:
            orchestrator = PipelineOrchestrator(
                business_context=business_context,
                user_id=user_id,
                job_id=job_id,
                use_hybrid=True,  # Use hybrid mode for both Gemini and TAVILY
            )
            logger.info(f"✅ PipelineOrchestrator initialized successfully for job {job_id}")
        except Exception as init_error:
            logger.error(f"❌ Failed to initialize PipelineOrchestrator for job {job_id}: {init_error}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Failed to initialize pipeline: {str(init_error)}")

        async def event_stream():
            """The async generator that yields events from the pipeline."""
            try:
                logger.info(f"🚀 Starting pipeline execution for job_id: {job_id}")
                event_count = 0
                
                # This is the key fix - actually call the main pipeline method
                async for event in orchestrator.execute_streaming_pipeline():
                    event_count += 1
                    
                    # Ensure user_id and job_id are in every event
                    event["user_id"] = user_id
                    event["job_id"] = job_id
                    
                    event_type = event.get('event_type', 'unknown')
                    logger.info(f"📨 Pipeline event #{event_count}: {event_type}")
                    
                    # Send to webapp webhook
                    await webhook_sender.send_event(event)
                    
                    # Stream to client
                    yield f"data: {json.dumps(event)}\n\n"
                    await asyncio.sleep(0.01) # Small sleep to prevent blocking
                    
                logger.info(f"✅ Pipeline execution completed for job_id: {job_id} - Total events: {event_count}")
                
                if event_count == 0:
                    logger.error(f"❌ CRITICAL: Pipeline yielded NO events for job {job_id} - this indicates the infinite loop issue!")
                    error_event = {
                        "event_type": "pipeline_error",
                        "job_id": job_id,
                        "user_id": user_id,
                        "error_message": "Pipeline yielded no events - possible infinite loop or initialization failure",
                        "timestamp": "now"
                    }
                    await webhook_sender.send_event(error_event)
                    yield f"data: {json.dumps(error_event)}\n\n"
                    
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
