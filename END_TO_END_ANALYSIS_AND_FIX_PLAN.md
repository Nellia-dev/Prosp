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

### Issue 2.1: Critical `SyntaxError` in Agent Orchestrator

*   **Symptom:** The application crashes at startup due to a `SyntaxError: 'return' with value in async generator` in `prospect/agents/enhanced_lead_processor.py`.
*   **Root Cause:** The `execute_enrichment_pipeline` function and its helper `run_sub_agent` are defined as `async` generators (using `yield`), but they incorrectly attempt to use a `return` statement with a value. Async generators can only stream data via `yield` and cannot return a final value in this manner. This indicates a fundamental design flaw in the orchestration logic, where streaming events and returning a final result are improperly mixed.
*   **Proposed Solution:**
    1.  Refactor the `execute_enrichment_pipeline` to correctly handle its dual responsibilities: yielding status events and producing a final result.
    2.  The chosen method will be to yield a specific `PipelineEndEvent` containing the final `ComprehensiveProspectPackage` as its payload. This maintains the streaming architecture while providing a clear, explicit signal for completion.
    3.  The calling context (likely in the MCP server's Celery task) will need to be updated to iterate through the generator and identify this final event to get the result.

### Issue 2.2: Fundamental Architectural Mismatch

*   **Symptom:** The backend is designed to call an MCP server that uses a legacy/alternative agent pipeline (`prospect/run.py`), but the container that is actually running is executing a different, more advanced pipeline (`prospect/enhanced_main.py`) which contains the `SyntaxError`.
*   **Root Cause:** There are two parallel, non-integrated Python applications within the `prospect` directory. The `docker-compose.yml` or `Dockerfile` for the `nellia-prospect-agents` container is likely configured to run `enhanced_main.py`, while the NestJS backend is making API calls to the Flask/Celery application (`prospect/mcp-server/app.py`) which is designed to execute `prospect/run.py`. The two systems are not designed to work together.
*   **Proposed Solution:**
    1.  **Unify the Python Application:** The two separate pipelines must be merged. The `enhanced_main.py` and its `EnhancedLeadProcessor` represent the intended, more feature-rich functionality. The MCP server (`app.py` and `celery_app.py`) must be refactored to call this `EnhancedLeadProcessor` instead of the legacy `execute_agentic_pipeline` from `run.py`.
    2.  **Align Backend and Python Service:** The API contract between the NestJS `McpService` and the Python `app.py` must be verified and aligned. The backend should send a request that the Python server can understand and use to trigger the correct, unified pipeline.
    3.  **Enable Real-Time Streaming:** The Celery task (`celery_app.py`) should be modified to leverage the streaming capabilities of the `EnhancedLeadProcessor`. Instead of collecting all events and sending a single webhook at the end, it should post each event to a real-time webhook as it is yielded. This will provide the intended live feedback to the frontend.

### Issue 2.3: Incorrect Container Orchestration

*   **Symptom:** The `docker-compose.yml` defines two separate Python services, `prospect-mcp-server` and `prospect-agents`, which creates unnecessary complexity and contributes to the architectural mismatch.
*   **Root Cause:** The system is designed as if the MCP server and the agents are two different applications, but they are fundamentally part of the same Python project. The `prospect-agents` container is redundant and its entrypoint (`enhanced_main.py`) is not designed to be called by the backend.
*   **Proposed Solution:**
    1.  **Consolidate into a Single Service:** The `prospect-mcp-server` and `prospect-agents` services in the `docker-compose.yml` should be merged into a single service.
    2.  **This service should be responsible for both running the Flask/Gunicorn web server and the Celery worker.** This can be achieved by using a supervisor process (like `supervisord`) or by running the Celery worker in the background.
    3.  **The `Dockerfile` should be simplified to have a single production target** that installs all necessary dependencies and configures the unified entry point.

### Issue 2.4: Incompatible Real-Time Feedback Loop

*   **Symptom:** The frontend is set up for real-time updates, but the backend's `McpWebhookService` is designed to handle only a single, final "job-complete" event from the Python application, not a continuous stream of events.
*   **Root Cause:** The `celery_app.py` is designed to collect all events from the pipeline and send them in one batch at the very end. The `McpWebhookService` is built to process this single batch. This completely defeats the purpose of the real-time streaming (`yield`) architecture in the Python agents and the WebSocket setup on the frontend.
*   **Proposed Solution:**
    1.  **Modify the Celery Task:** The `run_agentic_harvester_task` in `celery_app.py` must be changed. Instead of appending events to a list, it should immediately `POST` each event to a new, dedicated webhook endpoint as it is received from the agent generator.
    2.  **Create a New Webhook Endpoint:** A new endpoint (e.g., `/api/mcp/webhook/event-stream`) must be created in the backend. This endpoint will be responsible for receiving individual events.
    3.  **Update the Webhook Service:** The `McpWebhookService` will need a new method to handle these individual events. This method will parse the event type and payload, and then use the `WebSocketService` to broadcast the event to the appropriate room or client on the frontend.
    4.  **The existing `/job-complete` webhook can be kept** to handle the final `PipelineEndEvent`, which signifies that the job is truly finished and quotas can be updated.

---
*(This document will be updated as more issues are identified.)*