"""
Hybrid Pipeline Orchestrator
Selects and executes different lead processing pipelines based on lead characteristics
or A/B testing strategies.
"""
import json
from datetime import datetime
from typing import Any, AsyncIterator, Dict, Optional

from loguru import logger

from pipeline_orchestrator import PipelineOrchestrator
from agents.enhanced_lead_processor import EnhancedLeadProcessor
from agents.persona_driven_lead_processor import PersonaDrivenLeadProcessor
from data_models.lead_structures import AnalyzedLead, ComprehensiveProspectPackage, FinalProspectPackage, SiteData
from core_logic.llm_client import LLMClientFactory, LLMProvider
from event_models import StatusUpdateEvent, PipelineErrorEvent, PipelineEndEvent, PipelineStartEvent, LeadGeneratedEvent, LeadEnrichmentEndEvent, LeadEnrichmentStartEvent

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
        super().__init__(business_context, user_id, job_id, use_hybrid=False)
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
            # tavily_api_key=business_context.get("tavily_api_key", "") # Assuming it's in business_context
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
        NOTE: The main pipeline_orchestrator already emits LeadEnrichmentStartEvent,
        so we don't emit it here to avoid duplication.
        """
        try:
            logger.info(f"[{self.job_id}-{lead_id}] Starting hybrid enrichment for {lead_data.get('company_name', 'Unknown')}")
            
            # Standard initial intake and analysis - fix SiteData construction
            # Check if we have enriched content from ADK1
            extracted_content = lead_data.get("description", "")
            adk1_enrichment = lead_data.get("adk1_enrichment", {})
            
            # Use full_content from ADK1 if available, otherwise use description
            if adk1_enrichment.get("full_content"):
                extracted_content = adk1_enrichment["full_content"]
            elif not extracted_content and adk1_enrichment.get("qualification_summary"):
                extracted_content = adk1_enrichment["qualification_summary"]
            
            # Set appropriate extraction status message based on content availability
            if extracted_content and len(extracted_content.strip()) > 50:
                extraction_status = "Extração bem-sucedida via ADK1 harvester"
            else:
                extraction_status = "Extração limitada - usando dados básicos do ADK1"
            
            site_data = SiteData(
                url=lead_data.get("website", "http://example.com/unknown"),
                extracted_text_content=extracted_content,
                extraction_status_message=extraction_status
            )
            
            # Check if agents are properly initialized
            if not hasattr(self, 'lead_intake_agent') or self.lead_intake_agent is None:
                logger.error(f"[{self.job_id}-{lead_id}] lead_intake_agent is not initialized")
                raise Exception("lead_intake_agent is not properly initialized")
                
            if not hasattr(self, 'lead_analysis_agent') or self.lead_analysis_agent is None:
                logger.error(f"[{self.job_id}-{lead_id}] lead_analysis_agent is not initialized")
                raise Exception("lead_analysis_agent is not properly initialized")
            
            logger.info(f"[{self.job_id}-{lead_id}] Starting lead intake and analysis for {lead_data.get('company_name', 'Unknown')}")
            
            validated_lead = self.lead_intake_agent.execute(site_data)
            analyzed_lead_obj: AnalyzedLead = self.lead_analysis_agent.execute(validated_lead)

            # --- Pipeline Selection Logic ---
            lead_characteristics = self._get_lead_characteristics(analyzed_lead_obj)
            selected_pipeline_type = self.selection_strategy.select_pipeline_type(lead_characteristics)
            
            logger.info(f"[{self.job_id}-{lead_id}] Selected pipeline: '{selected_pipeline_type}' for lead {lead_data.get('company_name')}")
            
            # Emit status update about pipeline selection
            status_event = StatusUpdateEvent(
                event_type="status_update",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                status_message=f"Selected pipeline: {selected_pipeline_type}"
            ).to_dict()
            # Add lead_id manually since StatusUpdateEvent doesn't accept it as parameter
            status_event["lead_id"] = lead_id
            yield status_event

            processor_to_use = None
            if selected_pipeline_type == "persona_driven":
                processor_to_use = self.persona_driven_processor
            elif selected_pipeline_type == "enhanced_comprehensive":
                processor_to_use = self.enhanced_processor
            else: # Default to enhanced
                logger.warning(f"Unknown pipeline type '{selected_pipeline_type}', defaulting to 'enhanced_comprehensive'.")
                processor_to_use = self.enhanced_processor
            
            # --- Execute Selected Pipeline ---
            final_package_data = None
            
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
                status_event = StatusUpdateEvent(
                    event_type="status_update",
                    timestamp=datetime.now().isoformat(),
                    job_id=self.job_id,
                    user_id=self.user_id,
                    status_message=f"{processor_to_use.name} completed."
                ).to_dict()
                # Add lead_id manually since StatusUpdateEvent doesn't accept it as parameter
                status_event["lead_id"] = lead_id
                yield status_event
            else:
                raise NotImplementedError(f"Processor {processor_to_use.name} does not have a recognized execution method.")

            # RAG Integration - Apply AI intelligence to the analyzed lead
            logger.info(f"[{self.job_id}-{lead_id}] Applying RAG intelligence to analyzed lead")
            
            # Get RAG store and context
            rag_store = self.job_vector_stores.get(self.job_id) if hasattr(self, 'job_vector_stores') else None
            context_dict = json.loads(self.rag_context_text) if hasattr(self, "rag_context_text") else {}
            
            logger.info(f"[{self.job_id}-{lead_id}] RAG context available: {bool(context_dict)}, Vector store available: {bool(rag_store)}")
            
            # Apply AI prospect intelligence using RAG
            if hasattr(self, 'prospect_profiler') and self.prospect_profiler:
                try:
                    ai_profile = self.prospect_profiler.create_advanced_prospect_profile(
                        lead_data=lead_data,
                        enriched_context=context_dict,
                        rag_vector_store=rag_store
                    )
                    
                    # Apply AI intelligence to the analyzed lead object
                    analyzed_lead_obj.ai_intelligence = ai_profile
                    logger.success(f"[{self.job_id}-{lead_id}] AI intelligence profile applied to analyzed lead")
                    
                    # Update final package if it contains analyzed_lead
                    if final_package_data:
                        if 'analyzed_lead' in final_package_data:
                            final_package_data['analyzed_lead']['ai_intelligence'] = ai_profile
                        elif hasattr(final_package_data, 'get') and final_package_data.get('analyzed_lead'):
                            final_package_data['analyzed_lead']['ai_intelligence'] = ai_profile
                        else:
                            # Add AI profile to final package root if structure is different
                            final_package_data['ai_intelligence'] = ai_profile
                            
                except Exception as e:
                    logger.error(f"[{self.job_id}-{lead_id}] Failed to apply AI intelligence: {e}")
            else:
                logger.warning(f"[{self.job_id}-{lead_id}] Prospect profiler not available for RAG integration")

            # Ensure final package has proper structure
            if not final_package_data:
                # Create a basic final package from the analyzed lead
                final_package_data = {
                    "analyzed_lead": analyzed_lead_obj.model_dump() if hasattr(analyzed_lead_obj, 'model_dump') else analyzed_lead_obj.__dict__,
                    "enrichment_completed": True,
                    "pipeline_used": selected_pipeline_type
                }
                logger.info(f"[{self.job_id}-{lead_id}] Created basic final package from analyzed lead")
            
            # Log final package structure for debugging
            logger.info(f"[{self.job_id}-{lead_id}] Final package keys: {list(final_package_data.keys()) if isinstance(final_package_data, dict) else 'Not a dict'}")
            
            yield LeadEnrichmentEndEvent(
                event_type="lead_enrichment_end",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                lead_id=lead_id,
                success=True,
                final_package=final_package_data
            ).to_dict()

        except Exception as e:
            logger.error(f"[{self.job_id}-{lead_id}] Error during hybrid enrichment: {e}", exc_info=True)
            yield LeadEnrichmentEndEvent(
                event_type="lead_enrichment_end",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                lead_id=lead_id,
                success=False,
                error_message=str(e)
            ).to_dict()

    # We inherit execute_streaming_pipeline, _search_leads, etc. from PipelineOrchestrator.
    # The key change is that _enrich_lead now has the selection logic.
    # _run_harvester is also inherited and should use the updated _search_leads.
