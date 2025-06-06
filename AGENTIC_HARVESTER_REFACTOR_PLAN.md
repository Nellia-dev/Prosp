# Plan: Refactor Lead Generation with New Agentic Harvester (`run.py`)

This plan outlines the steps to replace the old `prospect/harvester.py` with the new agentic harvester system based on `prospect/run.py` and `prospect/adk1/`. It also details the integration of real-time updates from this new agentic ecosystem into the web application via the MCP server.

## Phase 1: Adapt New Harvester (`prospect/run.py`) for Programmatic Use and Real-time Event Emission

**Goal:** Transform `prospect/run.py` from an interactive script into a callable Python module that can be invoked by the Python MCP server. This module will accept business context and other parameters, execute the agent pipeline, and `yield` structured events for real-time updates.

**To-Do List:**

- [x] **1.1. Refactor `prospect/run.py` for Programmatic Invocation:** ✅ **COMPLETED**
    -   ✅ Modified `prospect/run.py` to expose a primary asynchronous function:
        `async def execute_agentic_pipeline(initial_query: str, business_context: dict, user_id: str, max_leads_to_generate: int, config_overrides: dict) -> AsyncIterator[Dict[str, Any]]:`
    -   ✅ This function encapsulates the core logic from `main_loop` and `call_agent_and_run`.
    -   ✅ Accepts parameters: initial query, business context object, `user_id`, `max_leads_to_generate` (for quota management), and configurations (e.g., `max_sites_to_scrape`).
    -   ✅ Instead of printing events to `stdout`, this function `yields` structured event dictionaries.
    -   ✅ Preserved legacy functions for backward compatibility.
    -   **Files modified:** `prospect/run.py`.

- [x] **1.2. Define and Standardize Event Structure for Real-time Updates:** ✅ **COMPLETED**
    -   ✅ Defined clear, consistent Pydantic models for events in `prospect/event_models.py`.
    -   ✅ Implemented event types: `pipeline_start`, `agent_start`, `agent_end`, `tool_call_start`, `tool_call_output`, `tool_call_end`, `lead_generated`, `status_update`, `pipeline_error`, `pipeline_end`.
    -   ✅ Each event includes relevant data: `job_id`, `user_id`, agent name, tool name, arguments, output snippets, lead data, error messages, progress indicators.
    -   **Files created:** `prospect/event_models.py`.

- [x] **1.3. Integrate Business Context into Agent Pipeline:** ✅ **COMPLETED**
    -   ✅ The `execute_agentic_pipeline` function effectively utilizes the `business_context` input.
    -   ✅ Implemented preprocessing of `business_context` to formulate targeted queries via `_enhance_query_with_business_context()`.
    -   ✅ Added intelligent agent selection based on query intent via `_determine_agent_by_intent()`.
    -   ✅ Business context fields (industry, company_size, target_market, location) are integrated into query enhancement.
    -   **Files modified:** `prospect/run.py`.

- [x] **1.4. Ensure Configuration and Quota Adherence:** ✅ **COMPLETED**
    -   ✅ The `execute_agentic_pipeline` respects `max_leads_to_generate` and passes operational configurations to agents/tools.
    -   ✅ Implemented `max_leads_limit` parameter throughout the pipeline to respect quota limits.
    -   ✅ Added `max_sites_to_scrape` configuration support via `config_overrides`.
    -   ✅ Lead generation stops automatically when quota limits are reached.
    -   **Files modified:** `prospect/run.py`.

## Phase 2: Refactor Python MCP Server (`prospect/mcp-server/`)

**Goal:** Update the Python-based MCP server to utilize the new programmatic agentic harvester from Phase 1 and to stream its events back to the NestJS backend.

**To-Do List:**

- [x] **2.1. Define/Update MCP Tool for New Agentic Harvester:** ✅ **COMPLETED**
    -   ✅ Created new Python MCP server (`prospect/mcp-server/app.py`) with agentic harvester endpoints:
        - `/api/v2/run_agentic_harvester` (synchronous execution)
        - `/api/v2/stream_agentic_harvester` (Server-Sent Events streaming)
    -   ✅ Updated `mcp_schemas.py` with new data structures: `HarvesterJobData`, `AgenticHarvesterResponse`, `StreamingEventResponse`.
    -   ✅ Endpoints accept harvester job data from NestJS backend and call `execute_agentic_pipeline` from refactored `prospect/run.py`.
    -   **Files created/modified:** `prospect/mcp-server/app.py`, `prospect/mcp-server/mcp_schemas.py`.

- [x] **2.2. Implement Event Streaming from Python MCP Tool to NestJS Backend:** ✅ **COMPLETED**
    -   ✅ Implemented Server-Sent Events (SSE) streaming in `/api/v2/stream_agentic_harvester` endpoint.
    -   ✅ The endpoint handles asynchronous events yielded by `execute_agentic_pipeline` and streams them in real-time.
    -   ✅ Events are properly formatted as SSE with structured `StreamingEventResponse` format.
    -   ✅ Added comprehensive error handling and graceful stream termination.
    -   **Files modified:** `prospect/mcp-server/app.py`.

- [x] **2.3. Review and Update Supporting MCP Server Modules:** ✅ **COMPLETED**
    -   ✅ Enhanced MCP server with backward compatibility for existing enhanced components.
    -   ✅ Preserved `agent_registry.py` and `llm_integration.py` functionality with graceful fallback.
    -   ✅ New agentic server runs independently but can coexist with existing enhanced MCP components.
    -   ✅ Added comprehensive health checks and service status endpoints.
    -   **Files preserved:** `prospect/mcp-server/agent_registry.py`, `prospect/mcp-server/llm_integration.py`.

- [x] **2.4. Add MCP Endpoint for Agentic Enrichment Pipeline:** ✅ **COMPLETED**
    -   ✅ Created a new streaming endpoint in `prospect/mcp-server/app.py`: `/api/v2/stream_enrichment_pipeline`.
    -   ✅ This endpoint accepts harvested lead data via the `EnrichmentJobData` schema.
    -   ✅ It invokes the `EnhancedLeadProcessor` from `prospect/agents/enhanced_lead_processor.py`.
    -   ✅ The `EnhancedLeadProcessor` was refactored into an `async` generator that `yields` events for each sub-agent's execution.
    -   ✅ The endpoint streams these granular enrichment events back to the NestJS backend in real-time.
    -   **Files modified:** `prospect/mcp-server/app.py`, `prospect/agents/enhanced_lead_processor.py`, `prospect/agents/base_agent.py`, `prospect/mcp-server/mcp_schemas.py`.

## Phase 3: Update NestJS Backend (`webapp/backend/`)

**Goal:** Modify the NestJS backend to invoke the refactored Python MCP server, correctly process the streamed agent events, and relay these granular updates to the frontend via WebSockets.

**To-Do List:**

- [x] **3.1. Update `McpService` in NestJS for Event Streaming:** ✅ **COMPLETED**
    -   ✅ Updated `webapp/backend/src/modules/mcp/mcp.service.ts` method `runHarvester` to call the new `/api/v2/run_agentic_harvester` endpoint.
    -   ✅ The service now calls the agentic harvester endpoint with proper payload structure (`user_id`, `initial_query`, `business_context`, `max_leads_to_generate`, `max_sites_to_scrape`).
    -   ✅ Implemented automatic fallback to legacy harvester if agentic harvester fails, ensuring reliability.
    -   ✅ Enhanced logging and error handling for the new agentic pipeline integration.
    -   **Files modified:** `webapp/backend/src/modules/mcp/mcp.service.ts`.

- [x] **3.2. Adapt NestJS Queue Processors for Two-Stage Pipeline (Harvesting & Enrichment):** ✅ **COMPLETED**
    -   ✅ The queue system has been split into two stages.
    -   ✅ **Stage 1: Harvesting (`prospect.processor.ts`)**
        -   The `prospect.processor.ts` now saves harvested leads with a `HARVESTED` status.
        -   It dispatches a new `enrich-lead` job to the `enrichment-processing` queue.
    -   ✅ **Stage 2: Enrichment (`enrichment.processor.ts`)**
        -   A new processor, `enrichment.processor.ts`, has been created.
        -   It calls the `/api/v2/stream_enrichment_pipeline` endpoint.
        -   It updates the lead with the final `ComprehensiveProspectPackage` and sets its status to `ENRICHED`.
    -   **Files modified:** `webapp/backend/src/modules/queue/processors/prospect.processor.ts`, `webapp/backend/src/modules/queue/queue.module.ts`.
    -   **Files created:** `webapp/backend/src/modules/queue/processors/enrichment.processor.ts`.

- [x] **3.3. Enhance `WebSocketGateway` for Full Pipeline Visibility:** ✅ **COMPLETED**
    -   ✅ The `WebSocketService` and `websocket.dto.ts` have been updated.
    -   ✅ New methods (`emitLeadUpdate`, `emitEnrichmentUpdate`) and event types (`ENRICHMENT_UPDATE`) have been added.
    -   ✅ The system can now broadcast granular updates for both harvesting and enrichment pipelines.
    -   **Files modified:** `webapp/backend/src/modules/websocket/websocket.service.ts`, `webapp/backend/src/modules/websocket/dto/websocket.dto.ts`.

- [x] **3.4. Update DTOs and Database for `ComprehensiveProspectPackage`:** ✅ **COMPLETED**
    -   ✅ The `LeadStatus` enum and `CreateLeadDto` have been updated in `nellia.types.ts`.
    -   ✅ The `LeadEntity` in `webapp/backend/src/database/entities/lead.entity.ts` has been expanded with `status` and `enrichment_data` columns.
    -   ✅ The `LeadsService` has been updated with `findById`, `updateStatus`, and `updateEnrichmentData` methods.
    -   **Files modified:** `webapp/backend/src/shared/types/nellia.types.ts`, `webapp/backend/src/database/entities/lead.entity.ts`, `webapp/backend/src/modules/leads/leads.service.ts`.

## Phase 4: Business Context Integration and User-Specific Adjustments

**Goal:** Ensure the user's business context is correctly fetched, passed to, and utilized by the new harvester, and that business context storage is user-specific.

**To-Do List:**

- [x] **4.1. Make Business Context User-Specific (If Not Already):** ✅ **COMPLETED**
    -   ✅ The `BusinessContextEntity` is now user-specific with a `userId` foreign key.
    -   ✅ The `BusinessContextService` has been updated to manage contexts on a per-user basis.
    -   ✅ The `BusinessContextController` now exposes user-specific endpoints.
    -   ✅ DTOs in `nellia.types.ts` have been updated to support the new fields.
    -   **Files modified:** `webapp/backend/src/database/entities/business-context.entity.ts`, `webapp/backend/src/modules/business-context/business-context.service.ts`, `webapp/backend/src/modules/business-context/business-context.controller.ts`, `webapp/backend/src/shared/types/nellia.types.ts`.

- [x] **4.2. Adapt `ProspectService.startProspectingProcess` for Business Context Input:** ✅ **COMPLETED**
    -   ✅ The `startProspectingProcess` method in `prospect.service.ts` now fetches the user-specific business context.
    -   ✅ It prepares and includes the full `business_context` object in the `HarvesterJobData` sent to the queue.
    -   **Files modified:** `webapp/backend/src/modules/prospect/prospect.service.ts`.

## Phase 5: Frontend Considerations (Informational for UI/UX Team)

**Goal:** Highlight necessary frontend adjustments to fully leverage the new backend capabilities.

**To-Do List (Guidance for Frontend Development):**

- [x] **5.1. Enhanced WebSocket Event Handling:** ✅ **COMPLETED**
    -   ✅ The `useSocketIO` hook has been updated to listen for new `enrichment-update` and `lead-update` events.
    -   ✅ The `useRealTimeUpdates` hook now handles these events, updating the React Query cache to ensure the UI reflects the latest data.
    -   **Files modified:** `webapp/frontend/src/hooks/useSocketIO.ts`, `webapp/frontend/src/hooks/useRealTimeUpdates.ts`.
- [x] **5.2. Richer Real-time Progress Display:** ✅ **COMPLETED**
    -   ✅ The `ProspectDashboard.tsx` component has been updated to listen for and display real-time enrichment events.
    -   ✅ The `ActiveJobsDisplay` sub-component now shows the current enrichment agent and a progress bar based on the number of events received.
    -   **Files modified:** `webapp/frontend/src/components/ProspectDashboard.tsx`.
- [ ] **5.3. Business Context as Primary Input:**
    -   The UI for initiating prospecting should emphasize the use of the user's saved business context. The "search query" might become a way to provide a specific focus or keyword refinement on top of the broader business context.

## Phase 6: Testing and Deployment Strategy

**Goal:** Ensure the refactored lead generation system is robust, reliable, and functions as expected.

**To-Do List:**

- [ ] **6.1. Unit Testing:**
    -   Write unit tests for the refactored `prospect/run.py` (programmatic invocation and event generation).
    -   Test the new Python MCP server endpoint and its event streaming logic.
    -   Test updated NestJS services (`McpService` for SSE handling, `ProspectProcessor` for event-driven lead saving, `WebSocketGateway` for new event types).
- [ ] **6.2. Integration Testing:**
    -   Test the full communication flow: NestJS Backend (`ProspectService` -> `ProspectProcessor` -> `McpService`) -> Python MCP Server -> `run.py` agentic pipeline -> Event streaming back to NestJS `McpService` -> `WebSocketGateway`.
    -   Verify correct passing and utilization of user-specific business context.
    -   Validate that real-time agent updates are correctly propagated to a mock WebSocket client, including `jobId` and `userId`.
- [ ] **6.3. End-to-End (E2E) Testing:**
    -   With the frontend, conduct E2E tests:
        -   User sets up/updates their business context.
        -   User initiates prospecting.
        -   Verify that the correct business context is used.
        -   Observe real-time, granular agent progress updates on the dashboard.
        -   Confirm leads are generated, saved correctly, and associated with the user.
        -   Test quota consumption and concurrent job prevention.
- [ ] **6.4. Deployment Considerations:**
    -   Review and update `prospect/Dockerfile` and `docker-compose.yml` if the new Python system (`run.py` and its ADK dependencies) has different setup or runtime requirements than `harvester.py`.
    -   Ensure all necessary environment variables (API keys for Gemini, Tavily) are correctly configured for the Python environment.

---
This plan provides a structured approach to integrate the new agentic harvester. The emphasis on programmatic invocation, standardized event streaming, and user-specific business context integration are key to achieving the desired outcome.
