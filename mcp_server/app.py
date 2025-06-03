from flask import Flask, request, jsonify
from sqlalchemy.orm import Session
import datetime
import json # For final_package_summary and metrics_json, output_json
import traceback # For logging detailed errors

# Assuming .database and .models are in the same directory (mcp_server)
from . import database
from . import models
from .data_models import (
    LeadProcessingStateCreate, LeadProcessingState as LeadProcessingStatePydantic, # Alias to avoid name clash
    AgentEventPayload, AgentExecutionRecordCreate, AgentExecutionRecord as AgentExecutionRecordPydantic, # Alias
    LeadProcessingStatusEnum, AgentExecutionStatusEnum
)
from pydantic import ValidationError

app = Flask(__name__)

# Initialize DB - This should ideally be done via a CLI command
# For this exercise, we assume it's handled. If not, uncommenting the line below
# and running this file directly once might work, or use the separate init_mcp_db.py
# database.init_db()

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
        else: # Agent Succeeded
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

def run_dev_server():
    """Runs the Flask development server after ensuring DB is initialized."""
    print("Initializing database for development...")
    database.init_db()
    print("Database initialized.")
    app.run(debug=True, port=5001, host="0.0.0.0")

if __name__ == '__main__':
    # This is for local dev. For prod, use Gunicorn or similar.
    run_dev_server()
