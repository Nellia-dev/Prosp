# End-to-End Analysis and Fix Plan for the Nelia Prospector Pipeline

This document outlines a comprehensive analysis of the entire lead generation pipeline, from the frontend request to the final agent processing. It identifies existing issues and proposes a detailed plan to resolve them, ensuring a robust and fully functional workflow.

## 1. High-Level Flow Analysis

The system is designed to operate as follows:

1.  **Initiation (Frontend):** A user, having configured their business context, initiates a prospecting job from the web application.
2.  **Job Dispatch (Backend - NestJS):**
    *   The `ProspectController` receives the request.
    *   The `ProspectService` validates the user's business context and quota.
    *   A job is created and placed into a Bull queue (`prospect-processing`).
3.  **Queue Processing (Backend - NestJS):**
    *   The `ProspectProcessor` picks up the job.
    *   It calls the `McpService` to hand off the task to the Python environment.
4.  **Execution (Python - MCP Server):**
    *   The MCP Server receives the request from the backend.
    *   It executes the main prospecting script (`run.py` or similar).
    *   The `EnhancedLeadProcessor` orchestrates a series of specialized agents to enrich the lead data.
5.  **Real-time Feedback (Python -> Backend -> Frontend):**
    *   During execution, Python agents are intended to `yield` status update events.
    *   These events are sent back to the NestJS backend via an MCP webhook.
    *   The `McpWebhookService` receives these events and pushes them to the frontend via WebSockets.
6.  **Completion:** The final, enriched lead data is processed and stored.

## 2. Identified Issues & Proposed Solutions

This section will be populated as the analysis progresses.

### Issue 2.1: Critical `SyntaxError` in Agent Orchestrator (DONE)

*   **Symptom:** The application crashes at startup due to a `SyntaxError: 'return' with value in async generator` in `prospect/agents/enhanced_lead_processor.py`.
*   **Root Cause:** The `execute_enrichment_pipeline` function and its helper `run_sub_agent` are defined as `async` generators (using `yield`), but they incorrectly attempt to use a `return` statement with a value. Async generators can only stream data via `yield` and cannot return a final value in this manner. This indicates a fundamental design flaw in the orchestration logic, where streaming events and returning a final result are improperly mixed.
*   **Solution Implemented:**
    1.  Refactored the `execute_enrichment_pipeline` to correctly handle its dual responsibilities.
    2.  The pipeline now yields a specific `PipelineEndEvent` containing the final `ComprehensiveProspectPackage` as its payload.
    3.  The calling context in the Celery task was updated to iterate through the generator and handle this final event.

### Issue 2.2: Fundamental Architectural Mismatch (DONE)

*   **Symptom:** The backend is designed to call an MCP server that uses a legacy/alternative agent pipeline (`prospect/run.py`), but the container that is actually running is executing a different, more advanced pipeline (`prospect/enhanced_main.py`) which contains the `SyntaxError`.
*   **Root Cause:** There are two parallel, non-integrated Python applications within the `prospect` directory. The `docker-compose.yml` or `Dockerfile` for the `nellia-prospect-agents` container is likely configured to run `enhanced_main.py`, while the NestJS backend is making API calls to the Flask/Celery application (`prospect/mcp-server/app.py`) which is designed to execute `prospect/run.py`. The two systems are not designed to work together.
*   **Solution Implemented:**
    1.  **Unified the Python Application:** The `celery_app.py` was refactored to call the `EnhancedLeadProcessor` directly, unifying the two pipelines.
    2.  **Aligned Backend and Python Service:** The API contract was aligned by having the Celery task now handle the full, enhanced workflow.
    3.  **Enabled Real-Time Streaming:** The Celery task was modified to post each event to a real-time webhook as it is yielded.

### Issue 2.3: Incorrect Container Orchestration (DONE)

*   **Symptom:** The `docker-compose.yml` defines two separate Python services, `prospect-mcp-server` and `prospect-agents`, which creates unnecessary complexity and contributes to the architectural mismatch.
*   **Root Cause:** The system is designed as if the MCP server and the agents are two different applications, but they are fundamentally part of the same Python project. The `prospect-agents` container is redundant and its entrypoint (`enhanced_main.py`) is not designed to be called by the backend.
*   **Solution Implemented:**
    1.  **Consolidated into a Single Service:** The `prospect-mcp-server` and `prospect-agents` services in `docker-compose.yml` were merged into a single `prospect-service`.
    2.  This service now runs both the Gunicorn web server and the Celery worker.
    3.  The `Dockerfile` will now use a single production target for this unified service.

### Issue 2.4: Incompatible Real-Time Feedback Loop (DONE)

*   **Symptom:** The frontend is set up for real-time updates, but the backend's `McpWebhookService` is designed to handle only a single, final "job-complete" event from the Python application, not a continuous stream of events.
*   **Root Cause:** The `celery_app.py` is designed to collect all events from the pipeline and send them in one batch at the very end. The `McpWebhookService` is built to process this single batch. This completely defeats the purpose of the real-time streaming (`yield`) architecture in the Python agents and the WebSocket setup on the frontend.
*   **Solution Implemented:**
    1.  **Modified the Celery Task:** The `run_agentic_harvester_task` in `celery_app.py` now immediately `POST`s each event to a new, dedicated webhook endpoint.
    2.  **Created a New Webhook Endpoint:** A new endpoint (`/api/mcp/webhook/event-stream`) was created in the backend.
    3.  **Updated the Webhook Service:** The `McpWebhookService` was given a new method to handle these individual events and broadcast them via WebSockets.
    4.  The existing `/job-complete` webhook is preserved to handle the final `PipelineEndEvent`.

### Issue 2.5: Insufficient Logging for Debugging (DONE)

*   **Symptom:** When errors occur, the logs lack sufficient context (like `job_id` or `user_id`) to easily trace a single request through the entire pipeline, making debugging difficult.
*   **Root Cause:** The logging configuration is generic and does not consistently include critical context identifiers in log messages across the different Python modules.
*   **Solution Implemented:**
    1.  **Implemented Contextual Logging:** Used Loguru's `bind` feature in the Celery task to enrich log messages with `job_id` and `user_id`.
    2.  **Standardized Log Records:** Ensured that key identifiers are present in logs originating from the main pipeline task.
    3.  **Enhanced Agent Logging:** The refactored `run_and_log_agent` helper in `EnhancedLeadProcessor` now includes agent-specific context in its log messages.

---
All identified issues have been addressed and the corresponding solutions have been implemented.