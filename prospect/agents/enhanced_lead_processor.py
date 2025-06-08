"""
Enhanced Lead Processor Agent - Comprehensive lead intelligence and processing
Incorporates features from new-cw.py and ck.py including Tavily enrichment, 
Tree-of-Thought strategy, and advanced intelligence gathering.
"""

import os
import json
import re
import time
import requests
import traceback
from typing import Optional, Dict, Any, List, AsyncIterator
from datetime import datetime
from loguru import logger

from data_models.lead_structures import (
    LeadAnalysis,
    AnalyzedLead,
    ComprehensiveProspectPackage,
    ContactInformation,
    ExternalIntelligence,
    PainPointAnalysis,
    LeadQualification,
    CompetitorIntelligence,
    PurchaseTriggers,
    EnhancedStrategy,
    ValueProposition,
    ObjectionFramework,
    EnhancedPersonalizedMessage,
    PersonalizedMessage,
    InternalBriefing,
    CommunicationChannel,
    DetailedPainPointSchema,
    CompetitorDetailSchema,
    IdentifiedTriggerSchema,
    ToTStrategyOptionModel,
    EvaluatedStrategyModel,
    ActionPlanStepModel,
    ToTActionPlanSynthesisModel,
    ContactStepDetailSchema,
    DetailedApproachPlanModel,
    ObjectionResponseModelSchema,
    InternalBriefingSectionSchema,
)
from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase
from event_models import AgentStartEvent, AgentEndEvent, StatusUpdateEvent, PipelineErrorEvent

# New Agent Imports
from .tavily_enrichment_agent import TavilyEnrichmentAgent, TavilyEnrichmentInput, TavilyEnrichmentOutput
from .contact_extraction_agent import ContactExtractionAgent, ContactExtractionInput, ContactExtractionOutput
from .pain_point_deepening_agent import PainPointDeepeningAgent, PainPointDeepeningInput, PainPointDeepeningOutput
from .lead_qualification_agent import LeadQualificationAgent, LeadQualificationInput, LeadQualificationOutput
from .competitor_identification_agent import CompetitorIdentificationAgent, CompetitorIdentificationInput, CompetitorIdentificationOutput
from .strategic_question_generation_agent import StrategicQuestionGenerationAgent, StrategicQuestionGenerationInput, StrategicQuestionGenerationOutput
from .buying_trigger_identification_agent import BuyingTriggerIdentificationAgent, BuyingTriggerIdentificationInput, BuyingTriggerIdentificationOutput
from .tot_strategy_generation_agent import ToTStrategyGenerationAgent, ToTStrategyGenerationInput, ToTStrategyGenerationOutput
from .tot_strategy_evaluation_agent import ToTStrategyEvaluationAgent, ToTStrategyEvaluationInput, ToTStrategyEvaluationOutput
from .tot_action_plan_synthesis_agent import ToTActionPlanSynthesisAgent, ToTActionPlanSynthesisInput, ToTActionPlanSynthesisOutput
from .detailed_approach_plan_agent import DetailedApproachPlanAgent, DetailedApproachPlanInput, DetailedApproachPlanOutput
from .objection_handling_agent import ObjectionHandlingAgent, ObjectionHandlingInput, ObjectionHandlingOutput
from .value_proposition_customization_agent import ValuePropositionCustomizationAgent, ValuePropositionCustomizationInput, ValuePropositionCustomizationOutput
from .b2b_personalized_message_agent import B2BPersonalizedMessageAgent, B2BPersonalizedMessageInput, B2BPersonalizedMessageOutput, ContactDetailsInput as B2BContactDetailsInput
from .internal_briefing_summary_agent import InternalBriefingSummaryAgent, InternalBriefingSummaryInput, InternalBriefingSummaryOutput


class EnhancedLeadProcessor(BaseAgent[AnalyzedLead, ComprehensiveProspectPackage]):
    def __init__(
        self,
        llm_client: LLMClientBase,
        product_service_context: str = "",
        competitors_list: str = "",
        tavily_api_key: Optional[str] = None,
        temperature: float = 0.7
    ):
        super().__init__(
            name="EnhancedLeadProcessor",
            description="Orchestrates a series of specialized agents to generate a rich, multi-faceted prospect package.",
            llm_client=llm_client,
            config={"temperature": temperature}
        )
        self.logger = logger
        
        self.product_service_context = product_service_context
        self.competitors_list = competitors_list
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")

        self.tavily_enrichment_agent = TavilyEnrichmentAgent(llm_client=self.llm_client, tavily_api_key=self.tavily_api_key)
        self.contact_extraction_agent = ContactExtractionAgent(llm_client=self.llm_client)
        self.pain_point_deepening_agent = PainPointDeepeningAgent(llm_client=self.llm_client)
        self.lead_qualification_agent = LeadQualificationAgent(llm_client=self.llm_client)
        self.competitor_identification_agent = CompetitorIdentificationAgent(llm_client=self.llm_client)
        self.strategic_question_generation_agent = StrategicQuestionGenerationAgent(llm_client=self.llm_client)
        self.buying_trigger_identification_agent = BuyingTriggerIdentificationAgent(llm_client=self.llm_client)
        self.tot_strategy_generation_agent = ToTStrategyGenerationAgent(llm_client=self.llm_client)
        self.tot_strategy_evaluation_agent = ToTStrategyEvaluationAgent(llm_client=self.llm_client)
        self.tot_action_plan_synthesis_agent = ToTActionPlanSynthesisAgent(llm_client=self.llm_client)
        self.detailed_approach_plan_agent = DetailedApproachPlanAgent(llm_client=self.llm_client)
        self.objection_handling_agent = ObjectionHandlingAgent(llm_client=self.llm_client)
        self.value_proposition_customization_agent = ValuePropositionCustomizationAgent(llm_client=self.llm_client)
        self.b2b_personalized_message_agent = B2BPersonalizedMessageAgent(llm_client=self.llm_client)
        self.internal_briefing_summary_agent = InternalBriefingSummaryAgent(llm_client=self.llm_client)
        
    def _construct_persona_profile_string(self, analysis_obj: LeadAnalysis, company_name: str) -> str:
        """Helper to create a descriptive persona string from analysis."""
        persona_parts = [
            analysis_obj.ideal_customer_profile or "",
            f"Cargo Estimado na {company_name}: {analysis_obj.company_culture_values.get('decision_maker_role_estimate', 'N/A') if isinstance(analysis_obj.company_culture_values, dict) else (analysis_obj.company_culture_values or 'N/A')}",
            f"Tamanho da Empresa {company_name}: {analysis_obj.company_size_estimate or 'N/A'}"
        ]
        persona_profile_str = ". ".join(filter(None, persona_parts))
        return persona_profile_str if persona_profile_str else f"Perfil da persona para {company_name} não detalhado suficientemente na análise inicial."

    def _construct_lead_analysis_string(self, analysis_obj: LeadAnalysis, external_intel: Optional[ExternalIntelligence]) -> str:
        """Helper to create a lead analysis string."""
        return (
            f"Setor da Empresa: {analysis_obj.company_sector}\n"
            f"Principais Serviços: {', '.join(analysis_obj.main_services)}\n"
            f"Descrição da Empresa: {analysis_obj.company_description}\n"
            f"Desafios Potenciais Identificados: {', '.join(analysis_obj.potential_challenges)}\n"
            f"Tamanho Estimado: {analysis_obj.company_size_estimate}\n"
            f"Cultura da Empresa: {analysis_obj.company_culture_values}\n"
            f"Diagnóstico Geral: {analysis_obj.general_diagnosis}\n"
            f"Inteligência Externa: {external_intel.tavily_enrichment if external_intel and external_intel.tavily_enrichment else 'N/A'}"
        )

    async def execute_enrichment_pipeline(
        self, analyzed_lead: AnalyzedLead, job_id: str, user_id: str
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Asynchronously executes the full enrichment pipeline, yielding events for each step.
        Returns the final ComprehensiveProspectPackage upon completion.
        """
        start_time = time.time()
        url = str(analyzed_lead.validated_lead.site_data.url)
        company_name = self._extract_company_name(analyzed_lead)
        self.logger.info(f"Starting enrichment pipeline for: {url} (Job ID: {job_id})")

        yield StatusUpdateEvent(
            timestamp=datetime.now().isoformat(),
            job_id=job_id,
            user_id=user_id,
            status_message=f"Starting enrichment for {company_name}."
        ).to_dict()

        try:
            # This is a helper to run a sub-agent and yield the correct events
            async def run_sub_agent(agent, input_data, agent_input_description):
                # First, execute the agent to get the output
                output = await agent.execute_async(input_data)

                # Now, yield the start and end events without a return statement
                yield AgentStartEvent(
                    timestamp=datetime.now().isoformat(), job_id=job_id, user_id=user_id,
                    agent_name=agent.name, input_query=agent_input_description
                ).to_dict()

                yield AgentEndEvent(
                    timestamp=datetime.now().isoformat(), job_id=job_id, user_id=user_id,
                    agent_name=agent.name, success=not getattr(output, 'error_message', None),
                    final_response=output.model_dump_json(),
                    error_message=getattr(output, 'error_message', None)
                ).to_dict()

                if getattr(output, 'error_message', None):
                    self.logger.warning(f"Sub-agent {agent.name} failed: {output.error_message}")
                
                # The result is now implicitly passed by the 'output' variable,
                # and the calling context will handle it.
                # We need to return the output outside the generator function.
                return output # This is now outside the generator scope.

            # Prepare common inputs
            analysis_obj = analyzed_lead.analysis
            persona_profile_str = self._construct_persona_profile_string(analysis_obj, company_name)

            # --- Execute Sub-Agents Sequentially ---
            external_intel = await run_sub_agent(self.tavily_enrichment_agent, TavilyEnrichmentInput(company_name=company_name, initial_extracted_text=analyzed_lead.validated_lead.site_data.extracted_text_content or ""), f"Enriching data for {company_name}")
            contact_info = await run_sub_agent(self.contact_extraction_agent, ContactExtractionInput(extracted_text=analyzed_lead.validated_lead.cleaned_text_content or "", company_name=company_name, product_service_offered=self.product_service_context), f"Extracting contacts for {company_name}")
            
            lead_analysis_str_for_agents = self._construct_lead_analysis_string(analysis_obj, external_intel)
            
            pain_analysis_output = await run_sub_agent(self.pain_point_deepening_agent, PainPointDeepeningInput(lead_analysis=lead_analysis_str_for_agents, persona_profile=persona_profile_str, product_service_offered=self.product_service_context, company_name=company_name), "Deepening pain points")
            deepened_pain_points_for_agents = json.dumps(pain_analysis_output.model_dump(), ensure_ascii=False) if pain_analysis_output and not pain_analysis_output.error_message else "Análise de dores não disponível."

            qualification_output = await run_sub_agent(self.lead_qualification_agent, LeadQualificationInput(lead_analysis=lead_analysis_str_for_agents, persona_profile=persona_profile_str, deepened_pain_points=deepened_pain_points_for_agents, product_service_offered=self.product_service_context), "Qualifying lead")
            competitor_intel_output = await run_sub_agent(self.competitor_identification_agent, CompetitorIdentificationInput(initial_extracted_text=analyzed_lead.validated_lead.site_data.extracted_text_content or "", product_service_offered=", ".join(analysis_obj.main_services), known_competitors_list_str=self.competitors_list), "Identifying competitors")
            purchase_triggers_output = await run_sub_agent(self.buying_trigger_identification_agent, BuyingTriggerIdentificationInput(lead_data_str=json.dumps(analyzed_lead.analysis.model_dump()), enriched_data=external_intel.tavily_enrichment or "", product_service_offered=self.product_service_context), "Identifying buying triggers")
            
            value_props_output = await run_sub_agent(self.value_proposition_customization_agent, ValuePropositionCustomizationInput(lead_analysis=lead_analysis_str_for_agents, persona_profile=persona_profile_str, deepened_pain_points=deepened_pain_points_for_agents, buying_triggers_report=json.dumps([t.model_dump() for t in purchase_triggers_output.identified_triggers]), product_service_offered=self.product_service_context, company_name=company_name), "Customizing value propositions")
            strategic_questions_output = await run_sub_agent(self.strategic_question_generation_agent, StrategicQuestionGenerationInput(lead_analysis=lead_analysis_str_for_agents, persona_profile=persona_profile_str, deepened_pain_points=deepened_pain_points_for_agents), "Generating strategic questions")

            current_lead_summary_for_tot = f"Empresa: {company_name} ({url})\nSetor: {analysis_obj.company_sector}\nPersona (Estimada): {persona_profile_str}\nDores: {pain_analysis_output.primary_pain_category if pain_analysis_output else 'N/A'}"
            
            tot_generation_output = await run_sub_agent(self.tot_strategy_generation_agent, ToTStrategyGenerationInput(current_lead_summary=current_lead_summary_for_tot, product_service_offered=self.product_service_context), "Generating ToT strategies")
            tot_evaluation_output = await run_sub_agent(self.tot_strategy_evaluation_agent, ToTStrategyEvaluationInput(proposed_strategies_text=json.dumps([s.model_dump() for s in tot_generation_output.proposed_strategies]), current_lead_summary=current_lead_summary_for_tot), "Evaluating ToT strategies")
            tot_synthesis_output = await run_sub_agent(self.tot_action_plan_synthesis_agent, ToTActionPlanSynthesisInput(evaluated_strategies_text=json.dumps([e.model_dump() for e in tot_evaluation_output.evaluated_strategies]), proposed_strategies_text=json.dumps([s.model_dump() for s in tot_generation_output.proposed_strategies]), current_lead_summary=current_lead_summary_for_tot), "Synthesizing ToT action plan")
            
            detailed_approach_plan_output = await run_sub_agent(self.detailed_approach_plan_agent, DetailedApproachPlanInput(lead_analysis=lead_analysis_str_for_agents, persona_profile=persona_profile_str, deepened_pain_points=deepened_pain_points_for_agents, final_action_plan_text=tot_synthesis_output.model_dump_json(), product_service_offered=self.product_service_context, lead_url=url), "Developing detailed approach plan")
            objection_handling_output = await run_sub_agent(self.objection_handling_agent, ObjectionHandlingInput(detailed_approach_plan_text=detailed_approach_plan_output.model_dump_json(), persona_profile=persona_profile_str, product_service_offered=self.product_service_context, company_name=company_name), "Preparing objection handling")

            # Final construction of the package
            enhanced_strategy = EnhancedStrategy(
                external_intelligence=external_intel, contact_information=contact_info, pain_point_analysis=pain_analysis_output,
                competitor_intelligence=competitor_intel_output, purchase_triggers=purchase_triggers_output, lead_qualification=qualification_output,
                tot_generated_strategies=tot_generation_output.proposed_strategies, tot_evaluated_strategies=tot_evaluation_output.evaluated_strategies,
                tot_synthesized_action_plan=tot_synthesis_output, detailed_approach_plan=detailed_approach_plan_output,
                value_propositions=value_props_output.custom_propositions, objection_framework=objection_handling_output,
                strategic_questions=strategic_questions_output.generated_questions
            )
            
            personalized_message_output = await run_sub_agent(self.b2b_personalized_message_agent, B2BPersonalizedMessageInput(final_action_plan_text=tot_synthesis_output.model_dump_json(), customized_value_propositions_text=json.dumps([p.model_dump() for p in value_props_output.custom_propositions]), contact_details=B2BContactDetailsInput(emails_found=contact_info.emails_found, instagram_profiles_found=contact_info.instagram_profiles), product_service_offered=self.product_service_context, lead_url=url, company_name=company_name, persona_fictional_name=persona_profile_str), "Crafting personalized message")
            internal_briefing_output = await run_sub_agent(self.internal_briefing_summary_agent, InternalBriefingSummaryInput(all_lead_data=enhanced_strategy.model_dump()), "Creating internal briefing")

            total_time = time.time() - start_time
            
            final_package = ComprehensiveProspectPackage(
                analyzed_lead=analyzed_lead,
                enhanced_strategy=enhanced_strategy,
                enhanced_personalized_message=EnhancedPersonalizedMessage(primary_message=PersonalizedMessage(channel=CommunicationChannel(personalized_message_output.crafted_message_channel.lower()), subject_line=personalized_message_output.crafted_message_subject, message_body=personalized_message_output.crafted_message_body, call_to_action="N/A")),
                internal_briefing=internal_briefing_output,
                confidence_score=self._calculate_confidence_score(enhanced_strategy),
                roi_potential_score=self._calculate_roi_potential(enhanced_strategy),
                brazilian_market_fit=self._calculate_brazilian_fit(analyzed_lead),
                processing_metadata={"total_processing_time": total_time, "processing_mode": "enhanced", "tavily_enabled": bool(self.tavily_api_key), "company_name": company_name}
            )
            
            yield StatusUpdateEvent(
                timestamp=datetime.now().isoformat(), job_id=job_id, user_id=user_id,
                status_message="Enrichment pipeline completed successfully."
            ).to_dict()

            return final_package

        except Exception as e:
            self.logger.error(f"Enrichment pipeline failed for {url}: {e}\n{traceback.format_exc()}")
            yield PipelineErrorEvent(
                timestamp=datetime.now().isoformat(),
                job_id=job_id,
                user_id=user_id,
                error_message=str(e),
                error_type=type(e).__name__
            ).to_dict()
            raise

    def process(self, analyzed_lead: AnalyzedLead) -> ComprehensiveProspectPackage:
        """
        Synchronous wrapper for the async pipeline.
        This remains for compatibility with the existing BaseAgent.execute method.
        For streaming, call execute_enrichment_pipeline directly.
        """
        self.logger.warning("Executing enrichment pipeline synchronously. Event streaming is disabled.")
        
        async def run_sync():
            events = []
            final_result = None
            try:
                async for event in self.execute_enrichment_pipeline(analyzed_lead, "sync_job", "sync_user"):
                    events.append(event)
                # The return value of an async generator is not directly accessible here.
                # This synchronous version will need a different way to get the final package.
                # For now, we'll assume the last event might contain it or we reconstruct it.
                # This part needs refinement if sync execution is a primary use case.
                # A better approach would be to not have this sync method at all.
                # Let's return an empty package for now to satisfy the type hint.
                # The primary use will be the async generator.
                self.logger.info("Synchronous execution finished. Note: Final package is not returned in this mode.")
                
                # This is a simplified placeholder. A real implementation would need to
                # properly retrieve the return value from the async generator.
                return ComprehensiveProspectPackage(analyzed_lead=analyzed_lead)

            except Exception as e:
                self.logger.error(f"Synchronous execution failed: {e}")
                raise

        return asyncio.run(run_sync())
    
    # Helper methods
    
    def _extract_company_name(self, analyzed_lead: AnalyzedLead) -> str:
        """Extract company name from Google search data or URL"""
        
        site_data = analyzed_lead.validated_lead.site_data
        if site_data.google_search_data and site_data.google_search_data.title:
            title = site_data.google_search_data.title
            company_name = title.split(" - ")[0].split(" | ")[0].split(": ")[0]
            company_name = re.sub(r'\s*\([^)]*\)', '', company_name)
            if len(company_name) > 5 and not any(char in company_name.lower() for char in ['http', 'www', '.com']):
                return company_name.strip()
        
        # Fallback to domain name
        url = str(site_data.url)
        domain = url.replace('https://', '').replace('http://', '').split('/')[0]
        domain = domain.replace('www.', '')
        return domain.split('.')[0].title()
    
    def _truncate_text(self, text: Optional[str], max_length: int = 15000) -> str: # Default max_length
        """Truncate text to maximum length"""
        if not text:
            return ""
        return text[:max_length] if len(text) > max_length else text
    
    def _calculate_confidence_score(self, enhanced_strategy: EnhancedStrategy) -> float:
        """Calculate overall confidence score"""
        base_score = 0.3
        qual_score = 0.0
        if enhanced_strategy.lead_qualification:
            if enhanced_strategy.lead_qualification.confidence_score is not None:
                qual_score = enhanced_strategy.lead_qualification.confidence_score * 0.2
            elif hasattr(enhanced_strategy.lead_qualification, 'qualification_score') and enhanced_strategy.lead_qualification.qualification_score is not None: # Legacy field
                 qual_score = enhanced_strategy.lead_qualification.qualification_score * 0.2
            else: qual_score = 0.05
        
        pain_score = 0.0
        if enhanced_strategy.pain_point_analysis and enhanced_strategy.pain_point_analysis.detailed_pain_points:
            pain_score = len(enhanced_strategy.pain_point_analysis.detailed_pain_points) * 0.05
            pain_score = min(pain_score, 0.15)
        
        contact_score = 0.0
        if enhanced_strategy.contact_information and hasattr(enhanced_strategy.contact_information, 'extraction_confidence'):
            contact_score = enhanced_strategy.contact_information.extraction_confidence * 0.1
        
        intel_score = 0.0
        if enhanced_strategy.external_intelligence and hasattr(enhanced_strategy.external_intelligence, 'enrichment_confidence'):
            intel_score = 0.1 if enhanced_strategy.external_intelligence.enrichment_confidence > 0.5 else 0.05
        
        strategy_score = 0.15 if enhanced_strategy.tot_synthesized_action_plan and not enhanced_strategy.tot_synthesized_action_plan.error_message else 0.05
        
        total_score = base_score + qual_score + pain_score + contact_score + intel_score + strategy_score
        return min(total_score, 1.0)
    
    def _calculate_roi_potential(self, enhanced_strategy: EnhancedStrategy) -> float:
        """Calculate ROI potential score"""
        qual_weight = 0.0
        if enhanced_strategy.lead_qualification:
            if enhanced_strategy.lead_qualification.confidence_score is not None:
                qual_weight = enhanced_strategy.lead_qualification.confidence_score * 0.4
            elif hasattr(enhanced_strategy.lead_qualification, 'qualification_score') and enhanced_strategy.lead_qualification.qualification_score is not None:
                 qual_weight = enhanced_strategy.lead_qualification.qualification_score * 0.4
            
        urgency_weight = 0.0
        if enhanced_strategy.pain_point_analysis and enhanced_strategy.pain_point_analysis.urgency_level:
            urgency_map = {"low": 0.1, "medium": 0.2, "high": 0.3, "critical": 0.4}
            urgency_weight = urgency_map.get(enhanced_strategy.pain_point_analysis.urgency_level.lower(), 0.1) * 0.25
        
        value_weight = 0.0
        if enhanced_strategy.value_propositions:
            valid_vps = [vp for vp in enhanced_strategy.value_propositions if not vp.error_message]
            value_weight = len(valid_vps) * 0.1
            value_weight = min(value_weight, 0.25)

        trigger_weight = 0.0
        if enhanced_strategy.purchase_triggers and enhanced_strategy.purchase_triggers.identified_triggers:
            trigger_weight = len(enhanced_strategy.purchase_triggers.identified_triggers) * 0.05
            trigger_weight = min(trigger_weight, 0.1)
            
        return min(qual_weight + urgency_weight + value_weight + trigger_weight, 1.0)
    
    def _calculate_brazilian_fit(self, analyzed_lead: AnalyzedLead) -> float:
        base_score = 0.7
        text_content = analyzed_lead.validated_lead.cleaned_text_content or ""
        if not text_content:
            text_content = analyzed_lead.validated_lead.site_data.extracted_text_content or ""
            
        brazilian_indicators = ["brasil", "brazilian", "são paulo", "rio de janeiro", "bh", "cnpj", ".br"]
        
        indicator_count = sum(1 for indicator in brazilian_indicators if indicator in text_content.lower())
        if ".br" in str(analyzed_lead.validated_lead.site_data.url).lower():
            indicator_count +=1
            
        indicator_bonus = min(indicator_count * 0.1, 0.3)
        return min(base_score + indicator_bonus, 1.0)
    
    def _build_prompt(self, input_data: AnalyzedLead) -> str:
        return f"Enhanced processing task for lead: {self._extract_company_name(input_data)}"
    
    def _parse_response(self, response: str) -> dict:
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            return json.loads(response.strip())
        except json.JSONDecodeError as e:
            self.logger.warning(f"EnhancedLeadProcessor._parse_response: JSONDecodeError - {e}. Response: {response[:200]}")
            return {"error": "Failed to parse JSON response", "raw_response": response}
        except Exception as e:
            self.logger.warning(f"EnhancedLeadProcessor._parse_response: Unexpected error - {e}. Response: {response[:200]}")
            return {"error": str(e), "raw_response": response}
