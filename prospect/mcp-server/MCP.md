# Nellia Prospector - Mission Control Panel (MCP) Server

This document describes the architecture and API of the MCP Server, a Flask-based application designed to track the real-time progress and results of leads processed by the Enhanced Nellia Prospector pipeline.

## 1. Purpose

The MCP Server provides:
- A persistent store for the status of each lead being processed.
- A detailed record of each agent's execution for a given lead, including its JSON output and metrics.
- API endpoints for the main processing pipeline to report events.
- API endpoints for a frontend application or other services (like CRON jobs) to query lead status and results.

## 2. Technology Stack

- **Backend Framework:** Flask
- **Database:** SQLite (using SQLAlchemy ORM)
- **Data Validation & Serialization:** Pydantic

## 3. Core Data Models

The MCP server uses Pydantic models for API interaction and SQLAlchemy models for database persistence. The primary concepts are:

### 3.1. `LeadProcessingState`
Tracks the overall status of a single lead throughout its lifecycle in the processing pipeline.
*(Refer to `mcp_server.data_models.LeadProcessingState` for detailed Pydantic field definitions, including `lead_id`, `run_id`, `url`, `status`, `current_agent`, `start_time`, `last_update_time`, `end_time`, `error_message`, `final_package_summary`)*

### 3.2. `AgentExecutionRecord`
Records the execution details for each agent that processes a specific lead.
*(Refer to `mcp_server.data_models.AgentExecutionRecord` for detailed Pydantic field definitions, including `record_id`, `lead_id`, `agent_name`, `status`, `start_time`, `end_time`, `processing_time_seconds`, `output_json`, `metrics_json`, `error_message`)*

### 3.3. Enums
- `LeadProcessingStatusEnum`: Defines possible statuses for a lead (e.g., PENDING, ACTIVE, COMPLETED, FAILED).
- `AgentExecutionStatusEnum`: Defines possible statuses for an agent execution (e.g., SUCCESS, FAILED).

## 4. Database Schema

The data is stored in a SQLite database (`mcp_server_data.db`) with the following main tables:

### 4.1. `leads_processing_state`
- `lead_id TEXT PRIMARY KEY`: Unique ID for the lead.
- `run_id TEXT NOT NULL`: ID for the processing run.
- `url TEXT`: URL of the lead.
- `status TEXT NOT NULL` (Uses `LeadProcessingStatusEnum`).
- `current_agent TEXT`: Name of the agent currently processing or last processed.
- `start_time TIMESTAMP NOT NULL`: When processing for this lead started.
- `last_update_time TIMESTAMP NOT NULL`: Last time this lead's record was updated.
- `end_time TIMESTAMP`: When processing for this lead concluded.
- `error_message TEXT`: If the overall lead processing failed.
- `final_package_summary TEXT`: JSON string summarizing the final output.

### 4.2. `agent_execution_records`
- `record_id INTEGER PRIMARY KEY AUTOINCREMENT`: Unique ID for the agent execution event.
- `lead_id TEXT NOT NULL`: Foreign key to `leads_processing_state.lead_id`.
- `agent_name TEXT NOT NULL`: Name of the agent that executed.
- `status TEXT NOT NULL` (Uses `AgentExecutionStatusEnum`).
- `start_time TIMESTAMP NOT NULL`: When this agent started processing.
- `end_time TIMESTAMP NOT NULL`: When this agent finished.
- `processing_time_seconds REAL`: Duration of agent execution.
- `input_summary TEXT`: Optional summary of input to the agent.
- `output_json TEXT`: JSON string of the agent's Pydantic output model.
- `metrics_json TEXT`: JSON string of the agent's `BaseAgent` metrics.
- `error_message TEXT`: If this specific agent execution failed.

*(SQLAlchemy ORM models `LeadProcessingStateOrm` and `AgentExecutionRecordOrm` in `mcp_server/models.py` map to these tables.)*

## 5. API Endpoints

The MCP server exposes the following RESTful API endpoints:

### 5.1. Start Lead Processing
- **Endpoint:** `POST /api/lead/start`
- **Purpose:** Registers a new lead when its processing is about to begin.
- **Request Body:** JSON object conforming to `mcp_server.data_models.LeadProcessingStateCreate`.
  ```json
  {
    "lead_id": "unique_lead_identifier",
    "run_id": "unique_run_identifier",
    "url": "http://example.com",
    "start_time": "YYYY-MM-DDTHH:MM:SS.ffffffZ", // ISO 8601 UTC
    "current_agent": "InitialAgentName" // Optional
  }
  ```
- **Response (201 Created):** JSON object of the created `LeadProcessingState`.
- **Response (409 Conflict):** If lead with the same `lead_id` already exists.
- **Response (400 Bad Request):** For invalid request data.

### 5.2. Record Agent Event
- **Endpoint:** `POST /api/lead/<lead_id>/event`
- **Purpose:** Records an event from an agent after it has finished processing for a given lead. Updates the lead's overall status.
- **Path Parameter:** `lead_id` - The ID of the lead being processed.
- **Request Body:** JSON object conforming to `mcp_server.data_models.AgentEventPayload`.
  ```json
  {
    "agent_name": "SpecificAgentName",
    "status": "SUCCESS", // or "FAILED"
    "start_time": "YYYY-MM-DDTHH:MM:SS.ffffffZ",
    "end_time": "YYYY-MM-DDTHH:MM:SS.ffffffZ",
    "processing_time_seconds": 10.5,
    "output_json": "{\"key\": \"value\", ...}", // Stringified JSON output of the agent
    "metrics_json": "{\"llm_calls\": 1, ...}", // Stringified JSON of BaseAgent metrics
    "error_message": null // or "Error details if status is FAILED"
  }
  ```
- **Response (201 Created):** JSON object of the created `AgentExecutionRecord`.
- **Response (404 Not Found):** If the specified `lead_id` does not exist.
- **Response (400 Bad Request):** For invalid request data.

### 5.3. Get Lead Status
- **Endpoint:** `GET /api/lead/<lead_id>/status`
- **Purpose:** Retrieves the current overall status and all agent execution records for a specific lead.
- **Path Parameter:** `lead_id` - The ID of the lead.
- **Response (200 OK):** JSON object containing:
  ```json
  {
    "lead_status": { ... LeadProcessingState data ... },
    "agent_executions": [
      { ... AgentExecutionRecord data ... },
      ...
    ]
  }
  ```
- **Response (404 Not Found):** If the `lead_id` does not exist.

### 5.4. Get Run Status
- **Endpoint:** `GET /api/run/<run_id>/status`
- **Purpose:** Retrieves the status for all leads associated with a specific processing run.
- **Path Parameter:** `run_id` - The ID of the processing run.
- **Response (200 OK):** JSON object containing:
  ```json
  {
    "run_id": "the_run_id",
    "leads": [
      { ... LeadProcessingState data for lead 1 ... },
      { ... LeadProcessingState data for lead 2 ... },
      ...
    ]
  }
  ```
  (Returns an empty list for "leads" if no leads are found for the `run_id`).

## 6. How the Pipeline Interacts with MCP

1.  **`EnhancedNelliaProspector` (`enhanced_main.py`):**
    -   Generates a unique `run_id` for each overall execution.
    -   For each lead, generates a unique `lead_id`.
    -   Calls `POST /api/lead/start` on the MCP server before processing the lead.
    -   Passes `lead_id` and `run_id` to `EnhancedLeadProcessor`.

2.  **`EnhancedLeadProcessor` (`agents/enhanced_lead_processor.py`):**
    -   Receives `lead_id` and `run_id` from `EnhancedNelliaProspector`.
    -   For each specialized agent it calls (e.g., `TavilyEnrichmentAgent`):
        -   It records the start time.
        -   Executes the specialized agent.
        -   Records the end time and status (SUCCESS/FAILED).
        -   Sends the agent's name, status, timings, JSON output, and basic metrics as an `AgentEventPayload` to `POST /api/lead/<lead_id>/event` on the MCP server.

## 7. Running the MCP Server

1.  **Initialize Database (One-time):**
    Ensure the SQLite database `mcp_server_data.db` is created and has the correct schema.
    You can use the `init_mcp_db.py` script (if provided) or initialize via Python:
    ```bash
    python -c "from mcp_server.database import init_db; init_db()"
    ```
    *(Ensure your current directory is the project root when running this, so `mcp_server` is importable).*

2.  **Start the Flask Server:**
    The `mcp_server/app.py` file contains a simple development server runner.
    ```bash
    python mcp_server/app.py
    ```
    This will typically start the server on `http://127.0.0.1:5001`.

3.  **Enable Reporting from Pipeline:**
    Ensure the Nellia Prospector pipeline (`enhanced_main.py`) is configured to report to the MCP server by setting the following environment variables:
    ```env
    ENABLE_MCP_REPORTING="true"
    MCP_SERVER_URL="http://127.0.0.1:5001"
    ```

## 8. Future Considerations (A2A Protocol)

Flask was chosen with the potential future integration of the Agent-to-Agent (A2A) communication protocol in mind. The current REST API can serve as a precursor, and parts of the A2A protocol could be implemented on top of or alongside these HTTP endpoints if needed.