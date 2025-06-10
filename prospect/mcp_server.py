# prospect/mcp_server.py

import asyncio
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger
import uvicorn
import os
from dotenv import load_dotenv

# Add project root to path to allow imports
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline_orchestrator import PipelineOrchestrator

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
    try:
        payload = await request.json()
        business_context = payload.get("business_context")
        user_id = payload.get("user_id")
        job_id = payload.get("job_id")

        if not all([business_context, user_id, job_id]):
            raise HTTPException(status_code=400, detail="Missing required fields: business_context, user_id, job_id")

        logger.info(f"Received request to execute pipeline for job_id: {job_id}, user_id: {user_id}")

        orchestrator = PipelineOrchestrator(
            business_context=business_context,
            user_id=user_id,
            job_id=job_id
        )

        async def event_stream():
            """The async generator that yields events from the pipeline."""
            async for event in orchestrator.execute_streaming_pipeline():
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(0.01) # Small sleep to prevent blocking

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")
    except Exception as e:
        logger.error(f"Error processing streaming prospect request: {e}", traceback=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


if __name__ == "__main__":
    port = int(os.getenv("MCP_SERVER_PORT", 5001))
    uvicorn.run(app, host="0.0.0.0", port=port)