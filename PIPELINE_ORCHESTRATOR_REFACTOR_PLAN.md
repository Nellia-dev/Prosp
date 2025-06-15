# Pipeline Orchestrator Refactor Plan

> **Goal:** Replace the current hybrid enrichment approach with a single, fully-agentic pipeline orchestrated exclusively by `pipeline_orchestrator.py`.  
> The refactor will remove the `HybridPipelineOrchestrator`, eliminate the `use_hybrid` flag, and ensure that **all** agents located in `prospect/agents` are leveraged (directly or indirectly) to deliver a rich, end-to-end `ComprehensiveProspectPackage` for every lead.

---

## 1. Context

| File / Component | Current Role | Refactor Impact |
|------------------|-------------|-----------------|
| `prospect/pipeline_orchestrator.py` | Main end-to-end pipeline. Contains an optional hand-off to `HybridPipelineOrchestrator` inside `_enrich_lead`. | • Become the only orchestrator.  
• Remove **all** hybrid-related code paths.  
• Add direct calls to agents previously invoked only via `HybridPipelineOrchestrator`. |
| `prospect/hybrid_pipeline_orchestrator.py` | Houses selection logic that decides which processor (Enhanced vs. Persona-Driven) to run. | Will be **deleted** after its logic is merged. |
| `prospect/agents/enhanced_lead_processor.py` | Comprehensive processor that already chains >20 sub-agents. | Will remain the core enrichment engine, but now called directly by `PipelineOrchestrator`. |
| Other `prospect/agents/*.py` | Stand-alone agents used by EnhancedLeadProcessor **or** available for direct invocation (e.g. `LeadAnalysisGenerationAgent`, `B2BPersonaCreationAgent`). | Ensure they are instantiated in `PipelineOrchestrator.__init__` and integrated where they are not already covered by `EnhancedLeadProcessor`. |

---

## 2. High-Level Architecture After Refactor

```
PipelineOrchestrator
 ├── _search_leads                # unchanged (ADK1 → leads)
 └── _enrich_lead (rewritten)
      ├── LeadIntakeAgent
      ├── LeadAnalysisAgent
      ├── LeadAnalysisGenerationAgent      # NEW direct call
      ├── B2BPersonaCreationAgent          # NEW direct call
      ├── EnhancedLeadProcessor.execute_enrichment_pipeline
      └── ProspectProfiler (RAG intelligence)
```
All events (`LeadEnrichmentStartEvent`, status updates from sub-agents, and `LeadEnrichmentEndEvent`) flow from a **single generator** to the frontend.

---

## 3. Detailed Task Breakdown

### 3.1 Update `PipelineOrchestrator.__init__()`
1. **Delete arguments & fields**: `use_hybrid`, `self.use_hybrid`, and any reference to `HybridPipelineOrchestrator`.
2. **Instantiate missing agents** currently created only in hybrid:
   - `LeadAnalysisGenerationAgent`
   - `B2BPersonaCreationAgent`
3. **Verify** existing initialization of:
   - `LeadIntakeAgent`
   - `LeadAnalysisAgent`
   - `EnhancedLeadProcessor`
4. **Remove** import block for `HybridPipelineOrchestrator`.

### 3.2 Rewrite `_enrich_lead()`
1. **Event Start**: yield `LeadEnrichmentStartEvent` (already exists).
2. **Data Intake & Base Analysis**
   - Build `SiteData` (respecting ADK1 enrichment content).
   - `validated_lead = LeadIntakeAgent.execute(site_data)`
   - `analyzed_lead = LeadAnalysisAgent.execute(validated_lead)`
3. **Phase-2 Add-ons**  
   These enrich the analysis object before the heavy pipeline:
   - `analysis_report = LeadAnalysisGenerationAgent.execute(analyzed_lead)`
   - `persona_profile = B2BPersonaCreationAgent.execute(analyzed_lead)`
   - Attach results to `analyzed_lead` (e.g. `analyzed_lead.extended_report = analysis_report`).
4. **Comprehensive Enrichment**
   - `async for event in EnhancedLeadProcessor.execute_enrichment_pipeline(analyzed_lead, job_id, user_id): yield event` (propagate `lead_id`).
5. **RAG-based Profiling**
   - Use `prospect_profiler.create_advanced_prospect_profile()` to append `ai_intelligence`.
6. **Event End**: yield `LeadEnrichmentEndEvent` with the final `ComprehensiveProspectPackage`.

### 3.3 Delete `HybridPipelineOrchestrator`
- Remove file `prospect/hybrid_pipeline_orchestrator.py`.
- Search & remove all imports: `grep -R "HybridPipelineOrchestrator" prospect/`.

### 3.4 Clean-up & Tests
1. **Flag Removal**: Ensure no leftover `self.use_hybrid` or `use_hybrid` param in codebase.
2. **Unit Tests**: Update / create tests for `_enrich_lead` to mock all agents and assert event sequence.
3. **Docs & READMEs**: Update any documentation referring to hybrid orchestrator.

---

## 4. Rollout Plan

| Step | Action | Owner | Status |
|------|--------|-------|--------|
| 1 | Merge initialization changes | Dev | ☐ |
| 2 | Rewrite `_enrich_lead` | Dev | ☐ |
| 3 | Delete hybrid orchestrator & clean imports | DevOps | ☐ |
| 4 | Update tests & docs | QA | ☐ |
| 5 | Run end-to-end pipeline in staging | QA | ☐ |
| 6 | Deploy to production | DevOps | ☐ |

---

## 5. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| **Event Flooding**: More agents ⇒ more events; could overwhelm websocket clients. | Throttle non-critical status updates or batch them. |
| **Performance / Latency**: Full agent list increases latency. | Measure each agent; introduce async concurrency where safe; enable selective disable via env flags if needed. |
| **Backward Compatibility**: Consumers expecting hybrid flag. | Provide deprecation notice; keep stub env var but ignore internally. |

---

## 6. Acceptance Criteria

- [ ] `PipelineOrchestrator` has **no** reference to `HybridPipelineOrchestrator` or `use_hybrid`.
- [ ] `_enrich_lead` yields a coherent event stream covering all new agents.
- [ ] `EnhancedLeadProcessor` is invoked for every lead.
- [ ] All agents in `prospect/agents` are either invoked directly or via `EnhancedLeadProcessor`.
- [ ] A sample end-to-end run produces a `ComprehensiveProspectPackage` with extended fields (`ai_intelligence`, persona, analysis report, etc.).

---

## 7. Timeline Estimate

| Week | Milestone |
|------|-----------|
| 1 | Code refactor & compile fix |
| 2 | Unit tests updated; hybrid file removal |
| 3 | Staging validation & performance tuning |
| 4 | Production deployment |

---

*Last updated: 2025-06-15*
