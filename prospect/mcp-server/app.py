"""
Refactored MCP Server for Agentic Harvester Integration
Implements the new agentic harvester endpoint with event streaming support.
"""

from flask import Flask, request, jsonify, Response
import json
import asyncio
import sys
import os
from typing import Dict, Any, AsyncIterator
from datetime import datetime
import traceback

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import the new agentic pipeline and the celery task
from run import execute_agentic_pipeline
from event_models import create_event_from_dict
from celery_app import run_agentic_harvester_task

# Import the enrichment pipeline
from agents.enhanced_lead_processor import EnhancedLeadProcessor
from data_models.lead_structures import AnalyzedLead
from core_logic.llm_client import LLMClientFactory

# Import existing MCP schemas and components
from mcp_schemas import (
    HarvesterJobData,
    EnrichmentJobData,
    AgenticHarvesterResponse,
    StreamingEventResponse,
    LeadProcessingStatusEnum,
    AgentExecutionStatusEnum
)

# Import existing enhanced MCP components (if available)
try:
    from agent_registry import get_agent_registry
    from llm_integration import get_llm_service
    from data_bridge import McpProspectDataManager
    ENHANCED_COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Enhanced MCP components not available: {e}")
    ENHANCED_COMPONENTS_AVAILABLE = False

app = Flask(__name__)

# Initialize enhanced components if available
if ENHANCED_COMPONENTS_AVAILABLE:
    try:
        agent_registry = get_agent_registry()
        llm_service = get_llm_service()
        data_manager = McpProspectDataManager()
        print("Enhanced MCP components initialized successfully")
    except Exception as e:
        print(f"Warning: Failed to initialize enhanced components: {e}")
        ENHANCED_COMPONENTS_AVAILABLE = False

# =============================================================================
# NEW AGENTIC HARVESTER ENDPOINTS
# =============================================================================

@app.route('/api/v2/run_agentic_harvester', methods=['POST'])
def run_agentic_harvester():
    """
    New endpoint to asynchronously execute the agentic harvester pipeline via Celery.
    Returns an immediate response with a job_id.
    """
    try:
        request_data = request.json
        if not request_data:
            return jsonify({"error": "Request body must be JSON"}), 400

        # Use a new job_id for every request to ensure unique tracking
        job_id = f"job_{request_data.get('user_id', 'unknown')}_{int(datetime.now().timestamp())}"
        request_data['job_id'] = job_id

        # Dispatch the task to the Celery worker
        run_agentic_harvester_task.delay(request_data)

        app.logger.info(f"Dispatched Celery task for job_id: {job_id}")

        # Return a 202 Accepted response immediately
        return jsonify({
            "status": "processing",
            "message": "Harvester job has been accepted and is processing.",
            "job_id": job_id,
            "user_id": request_data.get('user_id')
        }), 202

    except Exception as e:
        app.logger.error(f"Error in run_agentic_harvester: {e}\n{traceback.format_exc()}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/api/v2/stream_agentic_harvester', methods=['POST'])
def stream_agentic_harvester():
    """
    Endpoint to execute the agentic harvester pipeline with Server-Sent Events streaming.
    Returns real-time events as they occur during pipeline execution.
    """
    try:
        # Validate request data
        request_data = request.json
        if not request_data:
            return jsonify({"error": "Request body must be JSON"}), 400

        # Parse and validate harvester job data
        try:
            job_data = HarvesterJobData(**request_data)
        except Exception as e:
            return jsonify({"error": f"Invalid job data: {str(e)}"}), 400

        # Generate job_id if not provided
        if not job_data.job_id:
            job_data.job_id = f"job_{job_data.user_id}_{int(datetime.now().timestamp())}"

        def generate_events():
            """Generator function for Server-Sent Events"""
            try:
                # Create event loop for async execution
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Execute the agentic pipeline and stream events
                async def stream_pipeline():
                    async for event_dict in execute_agentic_pipeline(
                        initial_query=job_data.initial_query,
                        business_context=job_data.business_context,
                        user_id=job_data.user_id,
                        max_leads_to_generate=job_data.max_leads_to_generate,
                        config_overrides={"max_sites_to_scrape": job_data.max_sites_to_scrape}
                    ):
                        # Format event as Server-Sent Event
                        event_response = StreamingEventResponse(
                            event_type=event_dict.get('event_type', 'unknown'),
                            timestamp=event_dict.get('timestamp', datetime.now().isoformat()),
                            job_id=event_dict.get('job_id'),
                            user_id=event_dict.get('user_id'),
                            data=event_dict
                        )
                        
                        # Yield SSE formatted data
                        yield f"data: {event_response.model_dump_json()}\n\n"
                        
                        # End stream on pipeline completion
                        if event_dict.get('event_type') in ['pipeline_end', 'pipeline_error']:
                            break

                # Run the async pipeline
                loop.run_until_complete(stream_pipeline())
                loop.close()

            except Exception as e:
                # Send error event
                error_event = StreamingEventResponse(
                    event_type="pipeline_error",
                    timestamp=datetime.now().isoformat(),
                    job_id=job_data.job_id,
                    user_id=job_data.user_id,
                    data={
                        "error_message": str(e),
                        "error_type": type(e).__name__
                    }
                )
                yield f"data: {error_event.model_dump_json()}\n\n"

        # Return Server-Sent Events response
        return Response(
            generate_events(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        )

    except Exception as e:
        app.logger.error(f"Error in stream_agentic_harvester: {e}\n{traceback.format_exc()}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/api/v2/stream_enrichment_pipeline', methods=['POST'])
def stream_enrichment_pipeline():
    """
    Endpoint to execute the agentic enrichment pipeline with Server-Sent Events streaming.
    """
    try:
        request_data = request.json
        if not request_data:
            return jsonify({"error": "Request body must be JSON"}), 400

        try:
            job_data = EnrichmentJobData(**request_data)
        except Exception as e:
            return jsonify({"error": f"Invalid enrichment job data: {str(e)}"}), 400

        def generate_events():
            """Generator function for Server-Sent Events"""
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def stream_pipeline():
                    # Reconstruct the AnalyzedLead object
                    analyzed_lead = AnalyzedLead(**job_data.analyzed_lead_data)
                    
                    # Initialize LLM client and the processor
                    llm_client = LLMClientFactory.create_from_env()
                    processor = EnhancedLeadProcessor(
                        llm_client=llm_client,
                        product_service_context=job_data.product_service_context,
                        competitors_list=job_data.competitors_list or ""
                    )

                    async for event_dict in processor.execute_enrichment_pipeline(
                        analyzed_lead=analyzed_lead,
                        job_id=job_data.job_id,
                        user_id=job_data.user_id
                    ):
                        event_response = StreamingEventResponse(
                            event_type=event_dict.get('event_type', 'enrichment_status'),
                            timestamp=event_dict.get('timestamp', datetime.now().isoformat()),
                            job_id=event_dict.get('job_id'),
                            user_id=event_dict.get('user_id'),
                            data=event_dict
                        )
                        yield f"data: {event_response.model_dump_json()}\n\n"
                        
                        if event_dict.get('event_type') in ['pipeline_end', 'pipeline_error']:
                            break
                
                loop.run_until_complete(stream_pipeline())
                loop.close()

            except Exception as e:
                error_event = StreamingEventResponse(
                    event_type="pipeline_error",
                    timestamp=datetime.now().isoformat(),
                    job_id=job_data.job_id,
                    user_id=job_data.user_id,
                    data={"error_message": str(e), "error_type": type(e).__name__}
                )
                yield f"data: {error_event.model_dump_json()}\n\n"

        return Response(
            generate_events(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        )

    except Exception as e:
        app.logger.error(f"Error in stream_enrichment_pipeline: {e}\n{traceback.format_exc()}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

# =============================================================================
# ENHANCED MCP ENDPOINTS (Preserved if available)
# =============================================================================

if ENHANCED_COMPONENTS_AVAILABLE:
    @app.route('/api/agents/available', methods=['GET'])
    def get_available_agents():
        """List all available agents with metadata"""
        try:
            agent_summary = agent_registry.get_agent_summary()
            return jsonify(agent_summary), 200
        except Exception as e:
            app.logger.error(f"Error getting available agents: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/agents/<string:agent_name>/status', methods=['GET'])
    def get_agent_status(agent_name: str):
        """Get status of a specific agent"""
        try:
            status = llm_service.get_agent_status(agent_name)
            return jsonify(status), 200
        except Exception as e:
            app.logger.error(f"Error getting agent status for {agent_name}: {e}")
            return jsonify({"error": str(e)}), 500

# =============================================================================
# HEALTH AND STATUS ENDPOINTS
# =============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring."""
    try:
        # Basic health check
        status_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.1.0",
            "service": "agentic-mcp-server",
            "agentic_pipeline": "available"
        }
        
        # Add enhanced components status if available
        if ENHANCED_COMPONENTS_AVAILABLE:
            try:
                llm_status = llm_service.get_service_status()
                status_data["enhanced_components"] = {
                    "available": True,
                    "llm_service_status": llm_status.get('service_status', 'unknown')
                }
            except Exception as e:
                status_data["enhanced_components"] = {
                    "available": False,
                    "error": str(e)
                }
        else:
            status_data["enhanced_components"] = {"available": False}
            
        return jsonify(status_data), 200
        
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/service/status', methods=['GET'])
def get_service_status():
    """Get detailed service status including agentic pipeline capabilities."""
    try:
        status_data = {
            "service_status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.1.0",
            "service": "agentic-mcp-server",
            "capabilities": {
                "agentic_pipeline": True,
                "event_streaming": True,
                "business_context_integration": True,
                "quota_management": True
            },
            "endpoints": {
                "agentic_harvester": "/api/v2/run_agentic_harvester",
                "streaming_harvester": "/api/v2/stream_agentic_harvester"
            }
        }
        
        # Add enhanced components status if available
        if ENHANCED_COMPONENTS_AVAILABLE:
            try:
                agent_summary = agent_registry.get_agent_summary()
                llm_status = llm_service.get_service_status()
                
                status_data["enhanced_components"] = {
                    "available": True,
                    "agent_registry": agent_summary,
                    "llm_service": llm_status
                }
            except Exception as e:
                status_data["enhanced_components"] = {
                    "available": False,
                    "error": str(e)
                }
        else:
            status_data["enhanced_components"] = {"available": False}
            
        return jsonify(status_data), 200
        
    except Exception as e:
        app.logger.error(f"Error getting service status: {e}")
        return jsonify({
            "service_status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/metrics', methods=['GET'])
def get_metrics():
    """Get system metrics for monitoring."""
    try:
        metrics_data = {
            "timestamp": datetime.now().isoformat(),
            "service": "agentic-mcp-server",
            "version": "2.1.0",
            "agentic_pipeline_metrics": {
                "available": True,
                "event_types_supported": [
                    "pipeline_start", "pipeline_end", "agent_start", "agent_end",
                    "tool_call_start", "tool_call_output", "tool_call_end",
                    "lead_generated", "status_update", "pipeline_error"
                ]
            }
        }
        
        # Add enhanced metrics if available
        if ENHANCED_COMPONENTS_AVAILABLE:
            try:
                # This would include database metrics from the existing system
                # For now, we'll just indicate availability
                metrics_data["enhanced_metrics"] = {
                    "available": True,
                    "note": "Enhanced metrics integration pending"
                }
            except Exception as e:
                metrics_data["enhanced_metrics"] = {
                    "available": False,
                    "error": str(e)
                }
        
        return jsonify(metrics_data), 200
        
    except Exception as e:
        app.logger.error(f"Error getting metrics: {e}")
        return jsonify({"error": str(e)}), 500

# =============================================================================
# DEVELOPMENT SERVER
# =============================================================================

def run_dev_server():
    """Runs the Flask development server."""
    print("=" * 60)
    print("Starting Agentic MCP Server v2.1.0")
    print("=" * 60)
    
    # Check agentic pipeline availability
    try:
        from run import execute_agentic_pipeline
        print("✓ Agentic pipeline available")
    except ImportError as e:
        print(f"✗ Agentic pipeline not available: {e}")
        
    # Check enhanced components
    if ENHANCED_COMPONENTS_AVAILABLE:
        print("✓ Enhanced MCP components available")
        try:
            print(f"  - Agent Registry: {len(agent_registry.get_all_agents())} agents")
            print(f"  - LLM Service: {llm_service.get_service_status()['service_status']}")
        except Exception as e:
            print(f"  - Warning: Some enhanced components failed: {e}")
    else:
        print("○ Enhanced MCP components not available (running in basic mode)")
    
    print("\nAvailable endpoints:")
    print("  POST /api/v2/run_agentic_harvester - Execute agentic pipeline")
    print("  POST /api/v2/stream_agentic_harvester - Stream agentic pipeline events")
    print("  POST /api/v2/stream_enrichment_pipeline - Stream agentic enrichment events")
    print("  GET  /health - Health check")
    print("  GET  /api/service/status - Detailed service status")
    print("  GET  /metrics - System metrics")
    
    if ENHANCED_COMPONENTS_AVAILABLE:
        print("  GET  /api/agents/available - List available agents")
    
    print("\n" + "=" * 60)
    print("Server ready! Starting on http://0.0.0.0:5001")
    print("=" * 60)
    
    app.run(debug=True, port=5001, host="0.0.0.0")

if __name__ == '__main__':
    run_dev_server()
