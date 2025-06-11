"""
Hybrid Pipeline Orchestrator
Selects and executes different lead processing pipelines based on lead characteristics
or A/B testing strategies.
"""
import json
from typing import Any, AsyncIterator, Dict, Optional

from loguru import logger

from prospect.pipeline_orchestrator import PipelineOrchestrator
from prospect.agents.enhanced_lead_processor import EnhancedLeadProcessor
from prospect.agents.persona_driven_lead_processor import PersonaDrivenLeadProcessor
from prospect.data_models.lead_structures import AnalyzedLead, ComprehensiveProspectPackage, FinalProspectPackage
from prospect.core_logic.llm_client import LLMClientFactory, LLMProvider
from prospect.event_models import StatusUpdateEvent, PipelineErrorEvent, PipelineEndEvent, PipelineStartEvent, LeadGeneratedEvent # Assuming these are top-level importable

# Placeholder for lead characteristics model - to be defined based on actual needs
class LeadCharacteristics(Dict): # Using Dict as a placeholder
    pass


class AgentSelectionStrategy:
    """
    Determines which pipeline to use for a given lead.
    This is a conceptual class; its logic will be embedded or adapted
    within the HybridPipelineOrchestrator.
    """
    def select_pipeline_type(self, lead_characteristics: LeadCharacteristics) -> str:
        """
        Selects a pipeline type based on lead characteristics.

        Args:
            lead_characteristics: A dictionary or model containing features of the lead.

        Returns:
            A string identifier for the pipeline type (e.g., "enhanced", "persona_driven").
        """
        # Example logic (to be refined)
        complexity = lead_characteristics.get("complexity_score", 0.5) # 0.0 to 1.0
        persona_clarity = lead_characteristics.get("persona_clarity_score", 0.5) # 0.0 to 1.0
        data_quality = lead_characteristics.get("data_quality_score", 0.5) # 0.0 to 1.0

        if complexity > 0.7 and data_quality > 0.6:
            logger.info("Selecting 'enhanced_comprehensive' pipeline due to high complexity and good data quality.")
            return "enhanced_comprehensive"
        elif persona_clarity < 0.4 or data_quality < 0.4:
            logger.info("Selecting 'persona_driven' pipeline due to low persona clarity or data quality.")
            return "persona_driven"
        else:
            logger.info("Defaulting to 'enhanced_comprehensive' pipeline.")
            return "enhanced_comprehensive" # Default pipeline

class HybridPipelineOrchestrator(PipelineOrchestrator):
    """
    An orchestrator that can choose between different processing pipelines
    (e.g., EnhancedLeadProcessor, PersonaDrivenLeadProcessor) based on
    lead characteristics or A/B testing flags.
    """
    def __init__(
        self,
        business_context: Dict[str, Any],
        user_id: str,
        job_id: str,
        # A/B testing or strategy selection parameters can be added here
        pipeline_selection_strategy: str = "default" # e.g., "default", "persona_focused_first", "enhanced_first"
    ):
        super().__init__(business_context, user_id, job_id)
        self.pipeline_selection_strategy_name = pipeline_selection_strategy
        self.selection_strategy = AgentSelectionStrategy() # Instantiate the strategy

        # Initialize all available processors
        # Ensure llm_client is available from super().__init__ or pass it explicitly
        llm_client = self.llm_client # LLMClientFactory.create_from_env(LLMProvider.GEMINI)

        self.enhanced_processor = EnhancedLeadProcessor(
            name="EnhancedLeadProcessor",
            description="Comprehensive lead processing with multiple specialized agents.",
            llm_client=llm_client,
            product_service_context=self.product_service_context,
            # competitors_list and tavily_api_key might be needed from business_context or config
            competitors_list=business_context.get("competitors_list_str", ""),
            tavily_api_key=business_context.get("tavily_api_key") # Assuming it's in business_context
        )
        self.persona_driven_processor = PersonaDrivenLeadProcessor(
            llm_client=llm_client,
            product_service_context=self.product_service_context
        )
        logger.info(f"HybridPipelineOrchestrator initialized with selection strategy: {self.pipeline_selection_strategy_name}")

    def _get_lead_characteristics(self, analyzed_lead: AnalyzedLead) -> LeadCharacteristics:
        """
        Analyzes an AnalyzedLead object to extract characteristics for pipeline selection.
        This is a placeholder and needs more sophisticated logic.
        """
        # Example: Simple scoring based on available data
        complexity_score = 0.5
        if analyzed_lead.analysis.potential_challenges and len(analyzed_lead.analysis.potential_challenges) > 2:
            complexity_score += 0.2
        if analyzed_lead.analysis.main_services and len(analyzed_lead.analysis.main_services) > 3:
            complexity_score += 0.2

        persona_clarity_score = 0.3 # Default low
        # If a persona was already somehow attached or hinted at in analysis
        if "persona" in (analyzed_lead.analysis.general_diagnosis or "").lower():
             persona_clarity_score = 0.7
        
        data_quality_score = 0.5
        if analyzed_lead.validated_lead.extraction_successful:
            data_quality_score += 0.3
        if analyzed_lead.validated_lead.cleaned_text_content and len(analyzed_lead.validated_lead.cleaned_text_content) > 500:
            data_quality_score += 0.2
            
        characteristics = LeadCharacteristics({
            "complexity_score": min(complexity_score, 1.0),
            "persona_clarity_score": min(persona_clarity_score, 1.0),
            "data_quality_score": min(data_quality_score, 1.0),
            "sector": analyzed_lead.analysis.company_sector
        })
        logger.info(f"Lead characteristics for pipeline selection: {characteristics}")
        return characteristics

    async def _enrich_lead(self, lead_data: Dict, lead_id: str) -> AsyncIterator[Dict]:
        """
        Overrides the parent _enrich_lead to select and use a specific processor.
        """
        # Standard initial intake and analysis
        site_data = SiteData(url=lead_data.get("website"), extracted_text_content=lead_data.get("description"))
        validated_lead = self.lead_intake_agent.execute(site_data) # Assuming lead_intake_agent is initialized in parent
        analyzed_lead_obj: AnalyzedLead = self.lead_analysis_agent.execute(validated_lead) # Assuming lead_analysis_agent is initialized

        # --- Pipeline Selection Logic ---
        lead_characteristics = self._get_lead_characteristics(analyzed_lead_obj)
        selected_pipeline_type = self.selection_strategy.select_pipeline_type(lead_characteristics)
        
        logger.info(f"[{self.job_id}-{lead_id}] Selected pipeline: '{selected_pipeline_type}' for lead {lead_data.get('company_name')}")
        yield StatusUpdateEvent(job_id=self.job_id, lead_id=lead_id, status_message=f"Selected pipeline: {selected_pipeline_type}").to_dict()

        processor_to_use = None
        if selected_pipeline_type == "persona_driven":
            processor_to_use = self.persona_driven_processor
        elif selected_pipeline_type == "enhanced_comprehensive":
            processor_to_use = self.enhanced_processor
        else: # Default to enhanced
            logger.warning(f"Unknown pipeline type '{selected_pipeline_type}', defaulting to 'enhanced_comprehensive'.")
            processor_to_use = self.enhanced_processor
        
        # --- Execute Selected Pipeline ---
        # The sub-processors (EnhancedLeadProcessor, PersonaDrivenLeadProcessor)
        # are expected to yield events themselves if they are designed for streaming.
        # If they return a single package, we adapt.

        final_package_data = None
        try:
            if hasattr(processor_to_use, 'execute_enrichment_pipeline'): # For EnhancedLeadProcessor style
                async for event_or_package in processor_to_use.execute_enrichment_pipeline(analyzed_lead_obj, self.job_id, self.user_id): # type: ignore
                    # Check if it's an event or the final package
                    if isinstance(event_or_package, dict) and "event_type" in event_or_package:
                        event_or_package["lead_id"] = lead_id # Ensure lead_id is in events
                        yield event_or_package
                    elif isinstance(event_or_package, ComprehensiveProspectPackage): # Assuming this is the final output type
                        final_package_data = event_or_package.model_dump()
                        # No yield here, final package handled after loop
                    else:
                        logger.warning(f"Unexpected item from {processor_to_use.name}: {type(event_or_package)}")

            elif hasattr(processor_to_use, 'execute_async'): # For PersonaDrivenLeadProcessor style
                # This processor returns a single FinalProspectPackage
                result_package: FinalProspectPackage = await processor_to_use.execute_async(analyzed_lead_obj) # type: ignore
                final_package_data = result_package.model_dump()
                # We might need to emit a summary event here if not done by the processor
                yield StatusUpdateEvent(job_id=self.job_id, lead_id=lead_id, status_message=f"{processor_to_use.name} completed.").to_dict()
            else:
                raise NotImplementedError(f"Processor {processor_to_use.name} does not have a recognized execution method.")

            # RAG Integration (if applicable, and if final_package_data is populated)
            if final_package_data and 'ai_intelligence' not in final_package_data.get('analyzed_lead', {}): # Check if AI profile already exists
                rag_store = self.job_vector_stores.get(self.job_id)
                context_dict = json.loads(self.rag_context_text) if hasattr(self, "rag_context_text") else {}
                
                ai_profile = self.prospect_profiler.create_advanced_prospect_profile(
                    lead_data=lead_data, # Original lead data
                    enriched_context=context_dict,
                    rag_vector_store=rag_store
                )
                # Merge AI profile into the final package
                # This part needs careful handling of the package structure
                if 'analyzed_lead' in final_package_data:
                    final_package_data['analyzed_lead']['ai_intelligence'] = ai_profile
                else: # If the structure is different (e.g. FinalProspectPackage)
                    # This assumes FinalProspectPackage might have a place for ai_intelligence or similar
                    # For now, let's assume it's part of analyzed_lead which is nested
                    logger.warning("Could not directly attach AI profile to final package structure.")


            yield LeadEnrichmentEndEvent(job_id=self.job_id, lead_id=lead_id, success=True, final_package=final_package_data).to_dict()

        except Exception as e:
            logger.error(f"[{self.job_id}-{lead_id}] Error during {processor_to_use.name} execution: {e}", exc_info=True)
            yield LeadEnrichmentEndEvent(job_id=self.job_id, lead_id=lead_id, success=False, error_message=str(e)).to_dict()

    # We inherit execute_streaming_pipeline, _search_leads, etc. from PipelineOrchestrator.
    # The key change is that _enrich_lead now has the selection logic.
    # _run_harvester is also inherited and should use the updated _search_leads.
