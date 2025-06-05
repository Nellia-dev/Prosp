from flask import Flask, request, jsonify
from sqlalchemy.orm import Session
import datetime
import json # For final_package_summary and metrics_json, output_json
import traceback # For logging detailed errors
import asyncio
from typing import Dict, Any, List, Optional

# Import database and models from the same directory
import database
import models
# Import from local MCP schemas file
from .mcp_schemas import (
    LeadProcessingStateCreate, LeadProcessingState as LeadProcessingStatePydantic,
    AgentEventPayload, AgentExecutionRecordCreate, AgentExecutionRecord as AgentExecutionRecordPydantic,
    LeadProcessingStatusEnum, AgentExecutionStatusEnum
)
from pydantic import ValidationError
from sqlalchemy.orm import Session # Added for type hinting

# Import enhanced MCP components
from agent_registry import get_agent_registry, AgentRegistry
from llm_integration import get_llm_service, McpLlmService
from data_bridge import DataBridge, McpProspectDataManager

app = Flask(__name__)

# Initialize enhanced components
agent_registry = get_agent_registry()
llm_service = get_llm_service()
data_manager = McpProspectDataManager()

# Initialize DB - This should ideally be done via a CLI command
# For this exercise, we assume it's handled. If not, uncommenting the line below
# and running this file directly once might work, or use the separate init_mcp_db.py
# database.init_db()

# ===== ENHANCED ENDPOINTS =====

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

@app.route('/api/agents/status', methods=['GET'])
def get_all_agent_statuses():
    """Get status of all registered agents"""
    try:
        statuses = llm_service.get_all_agent_statuses()
        return jsonify(statuses), 200
    except Exception as e:
        app.logger.error(f"Error getting all agent statuses: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/lead/<string:lead_id>/process/enhanced', methods=['POST'])
def process_lead_enhanced(lead_id: str):
    """Execute full enhanced lead processing pipeline"""
    db: Session = next(database.get_db())
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        # Convert input data to validated lead format
        validated_lead = DataBridge.convert_site_data_to_validated_lead(data)
        if not validated_lead:
            return jsonify({"error": "Failed to convert input data to ValidatedLead format"}), 400

        # Update lead state
        lead_state = db.query(models.LeadProcessingStateOrm).filter(
            models.LeadProcessingStateOrm.lead_id == lead_id
        ).first()
        
        if not lead_state:
            return jsonify({"error": "Lead not found"}), 404

        lead_state.status = LeadProcessingStatusEnum.ACTIVE
        lead_state.current_agent = "enhanced_lead_processor"
        lead_state.last_update_time = datetime.datetime.utcnow()

        # Execute enhanced processing
        processing_params = data.get('processing_params', {})
        result = llm_service.execute_enhanced_lead_processing(
            validated_lead, 
            **processing_params
        )

        if result['success']:
            # Store the comprehensive result
            prospect_data = result['result']
            storage_result = data_manager.store_prospect_result(lead_id, prospect_data)
            
            # Update lead state to completed
            lead_state.status = LeadProcessingStatusEnum.COMPLETED
            lead_state.end_time = datetime.datetime.utcnow()
            lead_state.final_package_summary = json.dumps(storage_result['summary_metrics'])
            
            db.commit()
            
            return jsonify({
                "success": True,
                "lead_id": lead_id,
                "processing_result": result,
                "storage_result": storage_result
            }), 200
        else:
            # Update lead state to failed
            lead_state.status = LeadProcessingStatusEnum.FAILED
            lead_state.error_message = result['error_message']
            lead_state.end_time = datetime.datetime.utcnow()
            
            db.commit()
            
            return jsonify({
                "success": False,
                "lead_id": lead_id,
                "error": result['error_message']
            }), 500

    except Exception as e:
        db.rollback()
        app.logger.error(f"Error in enhanced lead processing for {lead_id}: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@app.route('/api/lead/<string:lead_id>/agents/<string:agent_name>/execute', methods=['POST'])
def execute_specific_agent(lead_id: str, agent_name: str):
    """Execute specific agent in the pipeline"""
    db: Session = next(database.get_db())
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        input_data = data.get('input_data')
        agent_params = data.get('agent_params', {})

        # Update lead state
        lead_state = db.query(models.LeadProcessingStateOrm).filter(
            models.LeadProcessingStateOrm.lead_id == lead_id
        ).first()
        
        if not lead_state:
            return jsonify({"error": "Lead not found"}), 404

        lead_state.current_agent = agent_name
        lead_state.last_update_time = datetime.datetime.utcnow()

        # Execute the specific agent
        result = llm_service.execute_agent_by_name(agent_name, input_data, **agent_params)

        # Create agent execution record
        agent_summary = DataBridge.create_agent_execution_summary(agent_name, result)
        
        db_agent_record = models.AgentExecutionRecordOrm(
            lead_id=lead_id,
            agent_name=agent_name,
            status=AgentExecutionStatusEnum.SUCCEEDED if result['success'] else AgentExecutionStatusEnum.FAILED,
            start_time=datetime.datetime.utcnow(),
            end_time=datetime.datetime.utcnow(),
            processing_time_seconds=result.get('processing_time_seconds', 0),
            output_json=json.dumps(agent_summary.get('result_summary')),
            metrics_json=json.dumps(result.get('metrics')),
            error_message=result.get('error_message')
        )
        db.add(db_agent_record)
        
        if result['success']:
            lead_state.status = LeadProcessingStatusEnum.ACTIVE
        else:
            lead_state.status = LeadProcessingStatusEnum.FAILED
            lead_state.error_message = result['error_message']

        db.commit()
        db.refresh(db_agent_record)

        return jsonify({
            "success": result['success'],
            "agent_execution": AgentExecutionRecordPydantic.from_orm(db_agent_record).model_dump(),
            "result": result
        }), 200

    except Exception as e:
        db.rollback()
        app.logger.error(f"Error executing agent {agent_name} for lead {lead_id}: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@app.route('/api/lead/<string:lead_id>/pipeline/execute', methods=['POST'])
def execute_agent_pipeline(lead_id: str):
    """Execute a pipeline of agents sequentially"""
    db: Session = next(database.get_db())
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        pipeline = data.get('pipeline', [])
        initial_data = data.get('initial_data')
        pipeline_params = data.get('pipeline_params', {})

        if not pipeline:
            return jsonify({"error": "Pipeline cannot be empty"}), 400

        # Update lead state
        lead_state = db.query(models.LeadProcessingStateOrm).filter(
            models.LeadProcessingStateOrm.lead_id == lead_id
        ).first()
        
        if not lead_state:
            return jsonify({"error": "Lead not found"}), 404

        lead_state.status = LeadProcessingStatusEnum.ACTIVE
        lead_state.current_agent = f"Pipeline: {', '.join(pipeline)}"
        lead_state.last_update_time = datetime.datetime.utcnow()

        # Execute pipeline
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            llm_service.execute_agent_pipeline(pipeline, initial_data, **pipeline_params)
        )
        loop.close()

        # Create agent execution records for each step
        for step_result in result.get('pipeline_results', []):
            agent_summary = DataBridge.create_agent_execution_summary(
                step_result['agent_name'], 
                step_result
            )
            
            db_agent_record = models.AgentExecutionRecordOrm(
                lead_id=lead_id,
                agent_name=step_result['agent_name'],
                status=AgentExecutionStatusEnum.SUCCEEDED if step_result['success'] else AgentExecutionStatusEnum.FAILED,
                start_time=datetime.datetime.utcnow(),
                end_time=datetime.datetime.utcnow(),
                processing_time_seconds=step_result.get('processing_time', 0),
                output_json=json.dumps(agent_summary.get('result_summary')),
                metrics_json=json.dumps(step_result.get('metrics')),
                error_message=step_result.get('error_message')
            )
            db.add(db_agent_record)

        if result['success']:
            lead_state.status = LeadProcessingStatusEnum.COMPLETED
            lead_state.end_time = datetime.datetime.utcnow()
        else:
            lead_state.status = LeadProcessingStatusEnum.FAILED
            lead_state.error_message = result['error_message']
            lead_state.end_time = datetime.datetime.utcnow()

        db.commit()

        return jsonify({
            "success": result['success'],
            "pipeline_result": result,
            "lead_id": lead_id
        }), 200

    except Exception as e:
        db.rollback()
        app.logger.error(f"Error executing pipeline for lead {lead_id}: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@app.route('/api/pipeline/validate', methods=['POST'])
def validate_pipeline():
    """Validate an agent execution pipeline"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        pipeline = data.get('pipeline', [])
        if not pipeline:
            return jsonify({"error": "Pipeline cannot be empty"}), 400

        is_valid, errors = agent_registry.validate_agent_pipeline(pipeline)
        
        return jsonify({
            "valid": is_valid,
            "errors": errors,
            "pipeline": pipeline
        }), 200

    except Exception as e:
        app.logger.error(f"Error validating pipeline: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/service/status', methods=['GET'])
def get_service_status():
    """Get enhanced service status"""
    try:
        llm_status = llm_service.get_service_status()
        agent_summary = agent_registry.get_agent_summary()
        
        # Test database connection
        db: Session = next(database.get_db())
        db.execute("SELECT 1")
        db.close()
        database_status = "connected"
        
        return jsonify({
            "service_status": "healthy",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "database": database_status,
            "llm_service": llm_status,
            "agent_registry": agent_summary,
            "version": "2.0.0",
            "service": "enhanced-mcp-server"
        }), 200

    except Exception as e:
        app.logger.error(f"Error getting service status: {e}")
        return jsonify({
            "service_status": "error",
            "error": str(e),
            "timestamp": datetime.datetime.utcnow().isoformat()
        }), 500

# ===== ORIGINAL ENDPOINTS =====

@app.route('/api/lead/start', methods=['POST'])
def start_lead_processing():
    db: Session = next(database.get_db())
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        lead_data = LeadProcessingStateCreate(**data)

        existing_lead = db.query(models.LeadProcessingStateOrm).filter(models.LeadProcessingStateOrm.lead_id == lead_data.lead_id).first()
        if existing_lead:
            # Return current state if it exists, or error if it's being processed by a different run_id
            if existing_lead.run_id == lead_data.run_id:
                 return jsonify(LeadProcessingStatePydantic.from_orm(existing_lead).model_dump()), 200
            else: # lead_id exists but with a different run_id
                 return jsonify({"message": f"Lead {lead_data.lead_id} is already being processed or was processed under a different run_id {existing_lead.run_id}"}), 409

        db_lead = models.LeadProcessingStateOrm(
            lead_id=lead_data.lead_id,
            run_id=lead_data.run_id,
            url=str(lead_data.url) if lead_data.url else None, # Ensure URL is string
            status=LeadProcessingStatusEnum.ACTIVE, # Start as active
            current_agent=lead_data.current_agent or "LeadIntakeAgent",
            start_time=lead_data.start_time if lead_data.start_time else datetime.datetime.utcnow(),
            last_update_time=datetime.datetime.utcnow()
        )
        db.add(db_lead)
        db.commit()
        db.refresh(db_lead)
        return jsonify(LeadProcessingStatePydantic.from_orm(db_lead).model_dump()), 201
    except ValidationError as ve:
        return jsonify({"error": "Invalid input data", "details": ve.errors()}), 422
    except Exception as e:
        db.rollback()
        app.logger.error(f"Error in /api/lead/start: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@app.route('/api/lead/<string:lead_id>/event', methods=['POST'])
def record_agent_event(lead_id: str):
    db: Session = next(database.get_db())
    try:
        event_data_dict = request.json
        if not event_data_dict:
            return jsonify({"error": "Request body must be JSON"}), 400

        event_payload = AgentEventPayload(**event_data_dict)

        lead_state = db.query(models.LeadProcessingStateOrm).filter(models.LeadProcessingStateOrm.lead_id == lead_id).first()
        if not lead_state:
            return jsonify({"error": "Lead not found"}), 404

        # Create the agent execution record
        db_agent_record = models.AgentExecutionRecordOrm(
            lead_id=lead_id, # This comes from the path parameter
            agent_name=event_payload.agent_name,
            status=event_payload.status,
            start_time=event_payload.start_time,
            end_time=event_payload.end_time,
            processing_time_seconds=event_payload.processing_time_seconds,
            output_json=event_payload.output_json,
            metrics_json=event_payload.metrics_json,
            error_message=event_payload.error_message
        )
        db.add(db_agent_record)

        # Update lead state based on the event
        lead_state.last_update_time = datetime.datetime.utcnow()

        if event_payload.status == AgentExecutionStatusEnum.FAILED:
            lead_state.status = LeadProcessingStatusEnum.FAILED
            lead_state.error_message = event_payload.error_message or f"Agent {event_payload.agent_name} failed."
            lead_state.end_time = event_payload.end_time or datetime.datetime.utcnow()
            lead_state.current_agent = f"Failed: {event_payload.agent_name}"
        elif event_payload.status == AgentExecutionStatusEnum.SUCCEEDED: # Agent Succeeded
            lead_state.current_agent = f"Completed: {event_payload.agent_name}"
            # Determine if this is the last agent. This logic is simplified.
            # A more robust system might have a predefined workflow or check a specific "final_agent_name" list.
            # For now, let's assume "InternalBriefingSummaryAgent" is the typical last one for successful completion.
            if event_payload.agent_name == "InternalBriefingSummaryAgent": # This name should match the one used by the processor
                lead_state.status = LeadProcessingStatusEnum.COMPLETED
                lead_state.end_time = event_payload.end_time or datetime.datetime.utcnow()
                # Potentially summarize final output into lead_state.final_package_summary
                if event_payload.output_json:
                    try:
                        # Assuming output_json from InternalBriefingSummaryAgent is the full InternalBriefing Pydantic model
                        briefing_data = json.loads(event_payload.output_json)
                        lead_state.final_package_summary = json.dumps({
                            "executive_summary": briefing_data.get("executive_summary", "Summary not available."),
                            "recommended_next_step": briefing_data.get("recommended_next_step", "N/A")
                        })
                    except Exception as e_summary:
                        app.logger.error(f"Could not parse final_package_summary for lead {lead_id}: {e_summary}")
                        lead_state.final_package_summary = json.dumps({"error": "Failed to parse summary from agent output."})

            else: # Agent succeeded but not the final one, so lead is still active
                lead_state.status = LeadProcessingStatusEnum.ACTIVE
                # Update current_agent to reflect the next expected agent if known, or clear it
                # This part needs more sophisticated workflow management. For now, just note completion.
                lead_state.current_agent = f"Awaiting next agent after: {event_payload.agent_name}"

        db.commit()
        db.refresh(db_agent_record)
        db.refresh(lead_state) # Also refresh lead_state to get its updated fields for the response

        response_data = {
            "agent_event_recorded": AgentExecutionRecordPydantic.from_orm(db_agent_record).model_dump(),
            "current_lead_state": LeadProcessingStatePydantic.from_orm(lead_state).model_dump()
        }
        return jsonify(response_data), 201

    except ValidationError as ve:
        return jsonify({"error": "Invalid input data for event", "details": ve.errors()}), 422
    except Exception as e:
        db.rollback()
        app.logger.error(f"Error in /api/lead/{lead_id}/event: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@app.route('/api/lead/<string:lead_id>/status', methods=['GET'])
def get_lead_status(lead_id: str):
    db: Session = next(database.get_db())
    try:
        lead_state_orm = db.query(models.LeadProcessingStateOrm).filter(models.LeadProcessingStateOrm.lead_id == lead_id).first()

        if not lead_state_orm:
            return jsonify({"error": "Lead not found"}), 404

        agent_executions_orm = db.query(models.AgentExecutionRecordOrm).filter(models.AgentExecutionRecordOrm.lead_id == lead_id).order_by(models.AgentExecutionRecordOrm.start_time).all()

        lead_state_pydantic = LeadProcessingStatePydantic.from_orm(lead_state_orm)
        agent_executions_pydantic = [AgentExecutionRecordPydantic.from_orm(rec) for rec in agent_executions_orm]

        return jsonify({
            "lead_status": lead_state_pydantic.model_dump(mode='json'), # mode='json' for enums as strings
            "agent_executions": [rec.model_dump(mode='json') for rec in agent_executions_pydantic]
        }), 200

    except Exception as e:
        app.logger.error(f"Error in /api/lead/{lead_id}/status: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@app.route('/api/run/<string:run_id>/status', methods=['GET'])
def get_run_status(run_id: str):
    db: Session = next(database.get_db())
    try:
        lead_states_orm = db.query(models.LeadProcessingStateOrm).filter(models.LeadProcessingStateOrm.run_id == run_id).order_by(models.LeadProcessingStateOrm.start_time).all()

        if not lead_states_orm:
            return jsonify({"message": "No leads found for this run_id", "run_id": run_id, "leads": []}), 200 # Or 404 if preferred

        leads_pydantic = [LeadProcessingStatePydantic.from_orm(state).model_dump(mode='json') for state in lead_states_orm]

        return jsonify({
            "run_id": run_id,
            "leads": leads_pydantic
        }), 200

    except Exception as e:
        app.logger.error(f"Error in /api/run/{run_id}/status: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring."""
    try:
        # Test database connection
        db: Session = next(database.get_db())
        db.execute("SELECT 1")
        db.close()
        database_status = "connected"
    except Exception as e:
        database_status = f"error: {str(e)}"
    
    return jsonify({
        "status": "healthy" if database_status == "connected" else "unhealthy",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "database": database_status,
        "version": "2.0.0",
        "service": "enhanced-mcp-server"
    })

@app.route('/metrics', methods=['GET'])
def get_metrics():
    """Get system metrics for monitoring."""
    db: Session = next(database.get_db())
    try:
        total_leads = db.query(models.LeadProcessingStateOrm).count()
        active_leads = db.query(models.LeadProcessingStateOrm).filter(
            models.LeadProcessingStateOrm.status == LeadProcessingStatusEnum.ACTIVE
        ).count()
        completed_leads = db.query(models.LeadProcessingStateOrm).filter(
            models.LeadProcessingStateOrm.status == LeadProcessingStatusEnum.COMPLETED
        ).count()
        failed_leads = db.query(models.LeadProcessingStateOrm).filter(
            models.LeadProcessingStateOrm.status == LeadProcessingStatusEnum.FAILED
        ).count()
        
        # Get recent activity (last 24 hours)
        recent_cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        recent_leads = db.query(models.LeadProcessingStateOrm).filter(
            models.LeadProcessingStateOrm.start_time >= recent_cutoff
        ).count()
        
        # Enhanced metrics
        agent_summary = agent_registry.get_agent_summary()
        llm_status = llm_service.get_service_status()
        
        return jsonify({
            "total_leads": total_leads,
            "active_leads": active_leads,
            "completed_leads": completed_leads,
            "failed_leads": failed_leads,
            "recent_leads_24h": recent_leads,
            "success_rate": round((completed_leads / max(total_leads, 1)) * 100, 2),
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "enhanced_metrics": {
                "total_agents": agent_summary["total_agents"],
                "initialized_agents": llm_status["initialized_agents"],
                "agent_categories": agent_summary["categories"],
                "llm_client_status": llm_status["llm_client_status"]
            }
        })
    except Exception as e:
        app.logger.error(f"Error getting metrics: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

def run_dev_server():
    """Runs the Flask development server after ensuring DB is initialized."""
    print("Initializing database for development...")
    database.init_db()
    print("Database initialized.")
    print("Initializing enhanced MCP components...")
    
    try:
        # Initialize components
        print(f"Agent Registry: {len(agent_registry.get_all_agents())} agents registered")
        print(f"LLM Service: {llm_service.get_service_status()['service_status']}")
        print("Enhanced MCP Server ready!")
    except Exception as e:
        print(f"Warning: Some enhanced components failed to initialize: {e}")
        print("Running with basic functionality...")
    
    app.run(debug=True, port=5001, host="0.0.0.0")

if __name__ == '__main__':
    # This is for local dev. For prod, use Gunicorn or similar.
    run_dev_server()
