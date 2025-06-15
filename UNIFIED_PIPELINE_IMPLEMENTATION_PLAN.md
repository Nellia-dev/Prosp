# Plan: Unified Streaming Prospecting Pipeline

**Document Version:** 1.0
**Date:** 2025-06-09

## 1. Analysis: The Core Problem

The current system is split into two disconnected pipelines:

1.  **A "Harvester" Pipeline (`run.py`):** A simple, legacy pipeline that finds basic leads. This is the *only* pipeline the web application currently uses.
2.  **An "Enhanced" Pipeline (`enhanced_main.py`):** The powerful, multi-agent pipeline that performs deep enrichment and strategic analysis. This pipeline is currently **inactive** and inaccessible from the web app.

This disconnect means the application's core value—delivering highly-refined, actionable leads—is not being realized.

## 2. The New Vision: A Unified, Real-Time Pipeline

The goal is to refactor the system into a **single, continuous pipeline** that seamlessly moves from lead discovery to full enrichment, streaming live updates to the user throughout the entire process.

### New Architecture Diagram

```mermaid
graph TD
    subgraph User
        A[Start Prospecting]
    end

    subgraph "NestJS Backend"
        B[Controller] --> C[Service]
        C --> D[Queue]
        E[Processor] --> F[Call Unified Pipeline]
    end

    subgraph "Python MCP Server (Unified Pipeline)"
        G[API Endpoint: /execute_streaming_prospect]
        F --> G
        G --> H{Orchestrator}
        H -- starts --> I[ADK Harvester]
        I -- finds lead 1 --> H
        H -- streams --> J[Event: lead_generated (lead 1)]
        H -- starts async task --> K[Enhanced Processor (for lead 1)]
        I -- continues searching --> L[...]
        K -- streams progress --> M[Events: enrichment_update (lead 1)]
        L -- finds lead 2 --> H
        H -- streams --> N[Event: lead_generated (lead 2)]
        H -- starts async task --> O[Enhanced Processor (for lead 2)]
    end

    subgraph "NestJS Backend"
        J --> P[WebSocket Service]
        M --> P
        N --> P
    end

    subgraph "Frontend"
        Q[UI]
        P --> Q
    end

    A --> B

    style K fill:#bbf,stroke:#333,stroke-width:2px
    style O fill:#bbf,stroke:#333,stroke-width:2px
    style M fill:#bbf,stroke:#333,stroke-width:2px
```

## 3. Implementation To-Do List

### Phase 1: Python - The Unified Pipeline Orchestrator
- [x] **Create `pipeline_orchestrator.py`:**
    - [x] Define a primary async generator function `execute_streaming_pipeline(business_context, user_id)`.
    - [x] Inside, initialize and run the `adk1` harvester agent.
    - [x] As the harvester yields raw leads, the orchestrator should:
        - [x] `yield` a `lead_generated` event.
        - [x] `asyncio.create_task` to run the full `EnhancedLeadProcessor` on the new lead.
    - [x] The enrichment task itself must `yield` all intermediate `agent_start`, `status_update`, and `agent_end` events.
    - [x] `yield` a final `lead_enriched` event upon successful completion of the enrichment task.

- [x] **Refactor `mcp_server.py`:**
    - [x] Create a new `POST` endpoint: `/api/v2/execute_streaming_prospect`.
    - [x] This endpoint should call the `execute_streaming_pipeline` from the new orchestrator.
    - [x] It must return a `StreamingResponse` that passes through the events yielded by the orchestrator.
    - [x] Remove the old `/api/v2/run_agentic_harvester` endpoint to prevent its use.

### Phase 2: Backend - Simplify and Relay Events
- [x] **Update `prospect.processor.ts`:**
    - [x] Modify the `handleHarvesterProcess` to call a new `mcp.service.ts` method (`executeUnifiedPipeline`).
    - [x] This method should iterate over the streaming response from the Python server.
    - [x] For each event received, it should call the `mcp-webhook.service.ts` to process it.

- [x] **Update `mcp.service.ts`:**
    - [x] Create the new `executeUnifiedPipeline` method to call the new `/api/v2/execute_streaming_prospect` endpoint.
    - [x] Ensure this method correctly handles a streaming HTTP response.

- [x] **Update `mcp-webhook.service.ts`:**
    - [x] Refactor `processStreamedEvent` to be the primary handler for all events from the unified pipeline.
    - [x] Add logic for the `lead_generated` event: Create a new lead in the DB with `HARVESTED` status and notify the frontend.
    - [x] Add logic for the `enrichment-update` event: Relay the event to the frontend via `websocket.service.ts`.
    - [x] Add logic for the `lead_enriched` event: Find the corresponding lead, update it with the full `ComprehensiveProspectPackage`, set its status to `ENRICHED`, and notify the frontend.

### Phase 3: Frontend - Visualize the Live Process
- [x] **Update `ProspectDashboard.tsx`:**
    - [x] On a `lead_generated` event, dynamically add a new lead card to the UI in an "Enriching" state.
    - [x] The new card should display a progress indicator or status text.

- [x] **Update Lead Card Component (`CompactLeadCard.tsx`):**
    - [x] Listen for `enrichment-update` events for the specific lead ID.
    - [x] Display the `status_message` from the event on the card (e.g., "Analyzing competitors...").

- [x] **Update `LeadDetailsModal.tsx`:**
    - [x] When a `lead_enriched` event is received, update the lead card to show completion.
    - [x] The modal should now fetch and display the full, rich data from the `comprehensive_prospect_package`.
    - [x] Design and add UI elements (Tabs, Accordions) to cleanly present:
        - [x] Strategic Approach Plan
        - [x] Crafted Outreach Message & Value Propositions
        - [x] Pain Points & Buying Triggers
        - [x] Competitor Intelligence