# Plan: Real-Time CRM Board Updates

This document outlines a comprehensive plan to integrate real-time progress updates from the Python agent pipeline directly into the `CRMBoard.tsx` component. The goal is to visually represent the journey of a lead as it moves through the various stages of enrichment, providing a dynamic and informative user experience.

## 1. Desired User Experience

1.  A user initiates a prospecting job.
2.  As new leads are found and begin processing, their cards appear on the CRM board in the "Harvested" or "Intake" column.
3.  As the backend Python agents process a specific lead (e.g., qualifying it, analyzing pain points), the corresponding lead card will automatically move to the appropriate column on the board (e.g., from "Intake" to "Qualification").
4.  When the entire enrichment pipeline for a lead is complete, its card will be in the "Enriched" column.
5.  Clicking on a fully enriched lead card will open a modal (`LeadDetailsModal`) displaying all the detailed information gathered by the agents, such as identified pain points, competitors, strategic questions, and customized value propositions.

## 2. High-Level Technical Strategy

The implementation will be divided into three main areas:

1.  **Backend Enhancement:** Modify the backend services to translate low-level agent events into high-level "lead stage update" events that the frontend can easily consume.
2.  **Frontend State Management:** Update the `useRealTimeUpdates.ts` hook to listen for these new events and update the application's central state (the `react-query` cache) accordingly.
3.  **UI Component Enhancement:** Ensure the `LeadDetailsModal.tsx` is capable of displaying the full, rich data of a completed lead.

---

## 3. Detailed To-Do List

### Phase 1: Backend Enhancements

#### 3.1. Augment Python Events with Lead ID
*   **Task:** Modify the `_run_full_pipeline` function in `prospect/mcp-server/celery_app.py`.
*   **Details:** When iterating through the `analyzed_leads` and calling the `enrichment_processor.execute_enrichment_pipeline`, the events yielded by the processor are currently associated with the overall `job_id`. These events must be augmented to include the specific `lead_id` of the lead being processed. This is crucial for the backend to know which lead to update on the frontend.
*   **Action:** Pass the `lead_to_enrich.id` into the event-posting function (`post_event_to_webhook`) and include it in the payload.

#### 3.2. Create a Specific `lead-stage-update` WebSocket Event
*   **Task:** Modify the `processStreamedEvent` method in `webapp/backend/src/modules/mcp-webhook/mcp-webhook.service.ts`.
*   **Details:** Instead of emitting a generic `pipeline-event`, the service should inspect the `event_type` from the Python service. When it sees an `agent_start` event, it should map that agent's name to a corresponding `ProcessingStage` from the frontend's enum.
*   **Action:**
    1.  Create a mapping object (e.g., `AGENT_TO_STAGE_MAP`) that links agent names like `LeadQualificationAgent` to stages like `lead_qualification`.
    2.  When an `agent_start` event is received, use this map to determine the new stage.
    3.  Emit a new, specific WebSocket event: `this.webSocketService.emitToUser(user_id, 'lead-stage-update', { leadId: event.lead_id, newStage: mappedStage });`.

#### 3.3. Handle Final Enrichment Data
*   **Task:** Enhance the `processStreamedEvent` method in `webapp/backend/src/modules/mcp-webhook/mcp-webhook.service.ts`.
*   **Details:** When a `pipeline_end` event is received for a specific lead, it contains the full `ComprehensiveProspectPackage`. This data needs to be persisted and sent to the frontend.
*   **Action:**
    1.  When `event_type` is `pipeline_end` and `success` is true, call a new method in the `LeadsService` (e.g., `updateEnrichmentData(leadId, event.data)`).
    2.  Emit a `lead-enriched` event via WebSockets containing the lead ID and the full, updated lead data.

### Phase 2: Frontend State Management

#### 3.4. Handle Lead Stage Updates
*   **Task:** Modify the `useRealTimeUpdates.ts` hook.
*   **Details:** Add a new `useEffect` block to subscribe to the `lead-stage-update` event from the WebSocket.
*   **Action:**
    1.  The event handler will receive `{ leadId, newStage }`.
    2.  It will use `queryClient.setQueryData(['leads'], (oldData) => ...)` to find the lead with the matching `leadId` in the cache and update its `processing_stage` property to `newStage`. This will automatically trigger a re-render of the `CRMBoard`, visually moving the card.

#### 3.5. Handle Final Enrichment Data
*   **Task:** Modify the `useRealTimeUpdates.ts` hook.
*   **Details:** Add a handler for the `lead-enriched` event.
*   **Action:**
    1.  The handler will receive the fully updated lead object.
    2.  It will use `queryClient.setQueryData(['leads'], ...)` to replace the old lead data in the cache with the new, fully enriched data.

### Phase 3: UI Component Enhancements

#### 3.6. Update Data Types
*   **Task:** Modify `webapp/frontend/src/types/unified.ts` (or a similar types file).
*   **Details:** The `LeadData` type definition must be expanded to include all the fields from the `ComprehensiveProspectPackage` (e.g., `pain_point_analysis`, `competitor_intelligence`, `value_propositions`, etc.). This will ensure type safety when accessing the new data.

#### 3.7. Enhance the Lead Details Modal
*   **Task:** Modify the `webapp/frontend/src/components/LeadDetailsModal.tsx` component.
*   **Details:** The modal currently displays basic lead information. It needs to be significantly enhanced to render the rich data from the enrichment process.
*   **Action:**
    1.  Add new sections to the modal for each key piece of enriched data.
    2.  Use accordions, tabs, or cards to neatly display:
        *   **Pain Points:** List the identified pain points and their urgency.
        *   **Competitors:** Display a list of identified competitors.
        *   **Buying Triggers:** Show the signals that indicate the lead might be ready to buy.
        *   **Value Propositions:** List the customized value propositions generated by the agent.
        *   **Strategic Questions:** Display the questions designed to engage the lead.
        *   **Objection Handling:** Show the prepared responses to potential objections.
        *   **Contact Information:** Display any extracted emails or social media profiles.

This plan provides a clear, step-by-step path to implementing the desired real-time functionality on the CRM board.