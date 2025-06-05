"""
Enhanced Lead Processor Agent - Comprehensive lead intelligence and processing.
This version assumes BaseAgent.execute handles MCP reporting.
Helper methods are async and pass lead_id, run_id to specialized agent calls.
"""

import os
import json
import re
import traceback
from typing import Optional, List
from datetime import datetime

from loguru import logger
from pydantic import BaseModel # Though not directly used in this file after removing local MCP reporting

from data_models.lead_structures import (
    AnalyzedLead, ComprehensiveProspectPackage, ContactInformation, ExternalIntelligence,
    PainPointAnalysis, LeadQualification, CompetitorIntelligence, PurchaseTriggers,
    EnhancedStrategy, ValueProposition, ObjectionFramework, EnhancedPersonalizedMessage,
    PersonalizedMessage, InternalBriefing, CommunicationChannel, DetailedPainPointSchema,
    CompetitorDetailSchema, IdentifiedTriggerSchema, ToTStrategyOptionModel, EvaluatedStrategyModel,
    ActionPlanStepModel, ToTActionPlanSynthesisModel, ContactStepDetailSchema,
    DetailedApproachPlanModel, ObjectionResponseModelSchema, InternalBriefingSectionSchema
)
from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Import all specialized agent classes and their I/O models
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
        mcp_server_url: Optional[str] = None,
        enable_mcp_reporting: bool = False
    ):
        super().__init__(name="EnhancedLeadProcessor",
                         description="Orchestrates a comprehensive lead processing pipeline.",
                         llm_client=llm_client)
        
        self.product_service_context = product_service_context
        self.competitors_list = competitors_list
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")

        self.MCP_SERVER_URL = mcp_server_url or os.getenv("MCP_SERVER_URL", "http://127.0.0.1:5001")
        self.ENABLE_MCP_REPORTING = enable_mcp_reporting if enable_mcp_reporting is not None else os.getenv("ENABLE_MCP_REPORTING", "false").lower() == "true"

        if self.ENABLE_MCP_REPORTING:
            self.logger.info(f"MCP Reporting Enabled for EnhancedLeadProcessor, Server URL: {self.MCP_SERVER_URL}")

        # Instantiate all specialized agents
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

    def _construct_persona_profile_string(self, analysis_obj: Optional[LeadAnalysis], company_name: str) -> str:
        if not analysis_obj: return f"Perfil da persona para {company_name} não disponível (análise inicial ausente)."
        persona_parts = [
            analysis_obj.ideal_customer_profile or "",
            f"Cargo Estimado na {company_name}: {analysis_obj.company_culture_values.get('decision_maker_role_estimate', 'N/A') if isinstance(analysis_obj.company_culture_values, dict) else (str(analysis_obj.company_culture_values) or 'N/A')}",
            f"Tamanho da Empresa {company_name}: {analysis_obj.company_size_estimate or 'N/A'}"
        ]
        return ". ".join(filter(None, persona_parts)) or f"Perfil da persona para {company_name} não detalhado."

    def _construct_lead_analysis_string(self, analysis_obj: Optional[LeadAnalysis], external_intel: Optional[ExternalIntelligence]) -> str:
        if not analysis_obj: return "Análise inicial do lead não disponível."
        return (
            f"Setor da Empresa: {analysis_obj.company_sector}\n"
            f"Principais Serviços: {', '.join(analysis_obj.main_services or [])}\n"
            f"Descrição da Empresa: {analysis_obj.company_description or 'N/A'}\n"
            f"Desafios Potenciais Identificados: {', '.join(analysis_obj.potential_challenges or [])}\n"
            f"Inteligência Externa: {external_intel.tavily_enrichment if external_intel and external_intel.tavily_enrichment else 'N/A'}"
        )

    async def process(self, analyzed_lead: AnalyzedLead, lead_id: str, run_id: str) -> ComprehensiveProspectPackage:
        process_start_time_utc = datetime.utcnow()
        url = str(analyzed_lead.validated_lead.site_data.url)
        company_name = self._extract_company_name(analyzed_lead)
        self.logger.info(f"EnhancedLeadProcessor (Lead ID: {lead_id}, Run ID: {run_id}): Starting for {url}")

        analysis_obj = analyzed_lead.analysis
        persona_profile_str = self._construct_persona_profile_string(analysis_obj, company_name)

        # Initialize outputs
        ext_intel = await self._gather_external_intelligence(company_name, analyzed_lead, lead_id, run_id)
        contact_info = await self._extract_contact_information(analyzed_lead, lead_id, run_id)
        lead_analysis_str = self._construct_lead_analysis_string(analysis_obj, ext_intel)

        pain_output = await self._analyze_pain_points(lead_analysis_str, persona_profile_str, company_name, lead_id, run_id)
        pain_analysis = PainPointAnalysis(**pain_output.model_dump()) if not pain_output.error_message else PainPointAnalysis(error_message=pain_output.error_message, primary_pain_category="N/A")
        deepened_pain_str = pain_output.model_dump_json(indent=2) if not pain_output.error_message else "Erro na análise de dores."

        qual_output = await self._qualify_lead(lead_analysis_str, persona_profile_str, deepened_pain_str, lead_id, run_id)
        qualification = LeadQualification(**qual_output.model_dump()) if not qual_output.error_message else LeadQualification(error_message=qual_output.error_message)

        comp_output = await self._analyze_competitors(analyzed_lead, lead_id, run_id)
        competitor_intel = CompetitorIntelligence(**comp_output.model_dump()) if not comp_output.error_message else CompetitorIntelligence(error_message=comp_output.error_message)

        trigger_output = await self._identify_purchase_triggers(analyzed_lead, ext_intel, lead_id, run_id)
        purchase_triggers = PurchaseTriggers(**trigger_output.model_dump()) if not trigger_output.error_message else PurchaseTriggers(error_message=trigger_output.error_message)

        vp_output = await self._create_value_propositions(lead_analysis_str, persona_profile_str, deepened_pain_str, trigger_output, company_name, lead_id, run_id)
        value_props = [ValueProposition(**vp.model_dump()) for vp in vp_output.custom_propositions] if not vp_output.error_message else [ValueProposition(title="Error", error_message=vp_output.error_message)]

        sq_output = await self._generate_strategic_questions(lead_analysis_str, persona_profile_str, deepened_pain_str, lead_id, run_id)
        strategic_questions = sq_output.generated_questions if not sq_output.error_message else [f"Error: {sq_output.error_message}"]

        # ToT Strategy Flow
        current_summary = f"Empresa: {company_name}, Persona: {persona_profile_str[:100]}..., Dores: {deepened_pain_str[:100]}..."
        tot_gen_output = await self._generate_tot_strategies(current_summary, lead_id, run_id)
        tot_eval_output = await self._evaluate_tot_strategies(tot_gen_output, current_summary, lead_id, run_id)
        tot_synth_output = await self._synthesize_tot_action_plan(tot_eval_output, tot_gen_output, current_summary, lead_id, run_id)

        detailed_plan_output = await self._develop_detailed_approach_plan(lead_analysis_str, persona_profile_str, deepened_pain_str, tot_synth_output, url, lead_id, run_id)
        detailed_plan = DetailedApproachPlanModel(**detailed_plan_output.model_dump()) if not detailed_plan_output.error_message else DetailedApproachPlanModel(error_message=detailed_plan_output.error_message)

        obj_handling_plan_str = detailed_plan.model_dump_json(indent=2) if not detailed_plan.error_message else "Plano de abordagem não disponível."
        obj_output = await self._prepare_objection_handling(persona_profile_str, company_name, obj_handling_plan_str, lead_id, run_id)
        objection_framework = ObjectionFramework(**obj_output.model_dump()) if not obj_output.error_message else ObjectionFramework(error_message=obj_output.error_message)

        enhanced_strategy = EnhancedStrategy(
            external_intelligence=ext_intel, contact_information=contact_info, pain_point_analysis=pain_analysis,
            competitor_intelligence=competitor_intel, purchase_triggers=purchase_triggers, lead_qualification=qualification,
            tot_generated_strategies=tot_gen_output.proposed_strategies if not tot_gen_output.error_message else [],
            tot_evaluated_strategies=tot_eval_output.evaluated_strategies if not tot_eval_output.error_message else [],
            tot_synthesized_action_plan=tot_synth_output if not tot_synth_output.error_message else None,
            detailed_approach_plan=detailed_plan, value_propositions=value_props,
            objection_framework=objection_framework, strategic_questions=strategic_questions
        )

        msg_data = await self._create_personalized_message(analyzed_lead, enhanced_strategy, contact_info, persona_profile_str, lead_id, run_id)
        briefing_data = await self._create_internal_briefing(analyzed_lead, enhanced_strategy, lead_id, run_id)

        total_time = (datetime.utcnow() - process_start_time_utc).total_seconds()
        return ComprehensiveProspectPackage(
            analyzed_lead=analyzed_lead, enhanced_strategy=enhanced_strategy, enhanced_personalized_message=msg_data,
            internal_briefing=briefing_data, confidence_score=self._calculate_confidence_score(enhanced_strategy),
            roi_potential_score=self._calculate_roi_potential(enhanced_strategy), brazilian_market_fit=self._calculate_brazilian_fit(analyzed_lead),
            processing_metadata={"total_processing_time_seconds": total_time, "company_name": company_name, "lead_id": lead_id, "run_id": run_id}
        )

    async def _gather_external_intelligence(self, company_name: str, analyzed_lead: AnalyzedLead, lead_id: str, run_id: str) -> ExternalIntelligence:
        enrichment_input = TavilyEnrichmentInput(
            company_name=company_name,
            initial_extracted_text=analyzed_lead.validated_lead.site_data.extracted_text_content or "",
            product_service_offered=self.product_service_context # Added product_service_context
        )
        try:
            output = await self.tavily_enrichment_agent.execute(enrichment_input, lead_id=lead_id, run_id=run_id)
            if output.error_message:
                return ExternalIntelligence(error_message=output.error_message, tavily_enrichment=output.enriched_data or "Tavily agent failed.")
            return ExternalIntelligence(
                tavily_enrichment=output.enriched_data,
                sources_used=["Tavily API"] if output.tavily_api_called else [],
                enrichment_confidence=0.8 if output.tavily_api_called and output.enriched_data else 0.3
            )
        except Exception as e:
            self.logger.error(f"Exception in _gather_external_intelligence for {lead_id}: {e}\n{traceback.format_exc()}")
            return ExternalIntelligence(error_message=str(e))

    async def _extract_contact_information(self, analyzed_lead: AnalyzedLead, lead_id: str, run_id: str) -> ContactInformation:
        text_content = analyzed_lead.validated_lead.cleaned_text_content or analyzed_lead.validated_lead.site_data.extracted_text_content or ""
        extraction_input = ContactExtractionInput(extracted_text=text_content, company_name=self._extract_company_name(analyzed_lead), product_service_offered=self.product_service_context)
        try:
            output = await self.contact_extraction_agent.execute(extraction_input, lead_id=lead_id, run_id=run_id)
            if output.error_message:
                return ContactInformation(error_message=output.error_message)
            return ContactInformation(
                emails_found=output.emails_found,
                instagram_profiles=output.instagram_profiles_found,
                tavily_search_suggestions=[output.tavily_search_suggestion] if output.tavily_search_suggestion else [],
                extraction_confidence=0.75 if output.emails_found or output.instagram_profiles_found else 0.25
            )
        except Exception as e:
            self.logger.error(f"Exception in _extract_contact_information for {lead_id}: {e}\n{traceback.format_exc()}")
            return ContactInformation(error_message=str(e))

    async def _analyze_pain_points(self, lead_analysis_str: str, persona_profile_str: str, company_name: str, lead_id: str, run_id: str) -> PainPointDeepeningOutput:
        pain_input = PainPointDeepeningInput(lead_analysis=lead_analysis_str, persona_profile=persona_profile_str, product_service_offered=self.product_service_context, company_name=company_name)
        try:
            output = await self.pain_point_deepening_agent.execute(pain_input, lead_id=lead_id, run_id=run_id)
            if output.error_message: self.logger.warning(f"PainPointDeepeningAgent for {lead_id} reported: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _analyze_pain_points for {lead_id}: {e}\n{traceback.format_exc()}")
            return PainPointDeepeningOutput(error_message=str(e), deepened_pain_points=[])

    async def _qualify_lead(self, lead_analysis_str: str, persona_profile_str: str, deepened_pain_points_str: str, lead_id: str, run_id: str) -> LeadQualificationOutput:
        qualification_input = LeadQualificationInput(lead_analysis=lead_analysis_str, persona_profile=persona_profile_str, deepened_pain_points=deepened_pain_points_str, product_service_offered=self.product_service_context)
        try:
            output = await self.lead_qualification_agent.execute(qualification_input, lead_id=lead_id, run_id=run_id)
            if output.error_message: self.logger.warning(f"LeadQualificationAgent for {lead_id} reported: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _qualify_lead for {lead_id}: {e}\n{traceback.format_exc()}")
            return LeadQualificationOutput(error_message=str(e), qualification_tier="Error", confidence_score=0.0, justification="Exception during processing")

    async def _analyze_competitors(self, analyzed_lead: AnalyzedLead, lead_id: str, run_id: str) -> CompetitorIdentificationOutput:
        text_content = analyzed_lead.validated_lead.site_data.extracted_text_content or ""
        lead_product_service = ", ".join(analyzed_lead.analysis.main_services or [])
        competitor_input = CompetitorIdentificationInput(initial_extracted_text=text_content, product_service_offered=lead_product_service, known_competitors_list_str=self.competitors_list)
        try:
            output = await self.competitor_identification_agent.execute(competitor_input, lead_id=lead_id, run_id=run_id)
            if output.error_message: self.logger.warning(f"CompetitorIdentificationAgent for {lead_id} reported: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _analyze_competitors for {lead_id}: {e}\n{traceback.format_exc()}")
            return CompetitorIdentificationOutput(error_message=str(e), identified_competitors=[])

    async def _identify_purchase_triggers(self, analyzed_lead: AnalyzedLead, external_intel: ExternalIntelligence, lead_id: str, run_id: str) -> BuyingTriggerIdentificationOutput:
        lead_data_str = json.dumps({"company_name": self._extract_company_name(analyzed_lead), "description": analyzed_lead.analysis.company_description})
        enriched_data = external_intel.tavily_enrichment if external_intel and not external_intel.error_message else ""
        trigger_input = BuyingTriggerIdentificationInput(lead_data_str=lead_data_str, enriched_data=enriched_data, product_service_offered=self.product_service_context)
        try:
            output = await self.buying_trigger_identification_agent.execute(trigger_input, lead_id=lead_id, run_id=run_id)
            if output.error_message: self.logger.warning(f"BuyingTriggerIdentificationAgent for {lead_id} reported: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _identify_purchase_triggers for {lead_id}: {e}\n{traceback.format_exc()}")
            return BuyingTriggerIdentificationOutput(error_message=str(e), identified_triggers=[])

    async def _create_value_propositions(self, lead_analysis_str: str, persona_profile_str: str, deepened_pain_points_str: str, purchase_triggers_output: BuyingTriggerIdentificationOutput, company_name: str, lead_id: str, run_id: str) -> ValuePropositionCustomizationOutput:
        triggers_report = purchase_triggers_output.model_dump_json() if not purchase_triggers_output.error_message else "Trigger report not available."
        vp_input = ValuePropositionCustomizationInput(lead_analysis=lead_analysis_str, persona_profile=persona_profile_str, deepened_pain_points=deepened_pain_points_str, buying_triggers_report=triggers_report, product_service_offered=self.product_service_context, company_name=company_name)
        try:
            output = await self.value_proposition_customization_agent.execute(vp_input, lead_id=lead_id, run_id=run_id)
            if output.error_message: self.logger.warning(f"ValuePropositionCustomizationAgent for {lead_id} reported: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _create_value_propositions for {lead_id}: {e}\n{traceback.format_exc()}")
            return ValuePropositionCustomizationOutput(error_message=str(e), custom_propositions=[])

    async def _generate_strategic_questions(self, lead_analysis_str: str, persona_profile_str: str, deepened_pain_points_str: str, lead_id: str, run_id: str) -> StrategicQuestionGenerationOutput:
        sq_input = StrategicQuestionGenerationInput(lead_analysis=lead_analysis_str, persona_profile=persona_profile_str, deepened_pain_points=deepened_pain_points_str)
        try:
            output = await self.strategic_question_generation_agent.execute(sq_input, lead_id=lead_id, run_id=run_id)
            if output.error_message: self.logger.warning(f"StrategicQuestionGenerationAgent for {lead_id} reported: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _generate_strategic_questions for {lead_id}: {e}\n{traceback.format_exc()}")
            return StrategicQuestionGenerationOutput(error_message=str(e), generated_questions=[])

    async def _prepare_objection_handling(self, persona_profile_str: str, company_name: str, detailed_approach_plan_text: str, lead_id: str, run_id: str) -> ObjectionHandlingOutput:
        objection_input = ObjectionHandlingInput(detailed_approach_plan_text=detailed_approach_plan_text, persona_profile=persona_profile_str, product_service_offered=self.product_service_context, company_name=company_name)
        try:
            output = await self.objection_handling_agent.execute(objection_input, lead_id=lead_id, run_id=run_id)
            if output.error_message: self.logger.warning(f"ObjectionHandlingAgent for {lead_id} reported: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _prepare_objection_handling for {lead_id}: {e}\n{traceback.format_exc()}")
            return ObjectionHandlingOutput(error_message=str(e), common_objections_and_responses=[])
    
    async def _generate_tot_strategies(self, current_lead_summary: str, lead_id: str, run_id: str) -> ToTStrategyGenerationOutput:
        generation_input = ToTStrategyGenerationInput(current_lead_summary=current_lead_summary, product_service_offered=self.product_service_context)
        try:
            output = await self.tot_strategy_generation_agent.execute(generation_input, lead_id=lead_id, run_id=run_id)
            if output.error_message: self.logger.warning(f"ToTStrategyGenerationAgent for {lead_id} reported: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _generate_tot_strategies for {lead_id}: {e}\n{traceback.format_exc()}")
            return ToTStrategyGenerationOutput(error_message=str(e), proposed_strategies=[])

    async def _evaluate_tot_strategies(self, generated_strategies_output: ToTStrategyGenerationOutput, current_lead_summary: str, lead_id: str, run_id: str) -> ToTStrategyEvaluationOutput:
        proposed_strategies_text = generated_strategies_output.model_dump_json() if not generated_strategies_output.error_message else "Generated strategies not available."
        evaluation_input = ToTStrategyEvaluationInput(proposed_strategies_text=proposed_strategies_text, current_lead_summary=current_lead_summary)
        try:
            output = await self.tot_strategy_evaluation_agent.execute(evaluation_input, lead_id=lead_id, run_id=run_id)
            if output.error_message: self.logger.warning(f"ToTStrategyEvaluationAgent for {lead_id} reported: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _evaluate_tot_strategies for {lead_id}: {e}\n{traceback.format_exc()}")
            return ToTStrategyEvaluationOutput(error_message=str(e), evaluated_strategies=[])

    async def _synthesize_tot_action_plan(self, evaluated_strategies_output: ToTStrategyEvaluationOutput, generated_strategies_output: ToTStrategyGenerationOutput, current_lead_summary: str, lead_id: str, run_id: str) -> ToTActionPlanSynthesisOutput:
        evaluated_text = evaluated_strategies_output.model_dump_json() if not evaluated_strategies_output.error_message else "Evaluated strategies not available."
        proposed_text = generated_strategies_output.model_dump_json() if not generated_strategies_output.error_message else "Proposed strategies not available."
        synthesis_input = ToTActionPlanSynthesisInput(evaluated_strategies_text=evaluated_text, proposed_strategies_text=proposed_text, current_lead_summary=current_lead_summary)
        try:
            output = await self.tot_action_plan_synthesis_agent.execute(synthesis_input, lead_id=lead_id, run_id=run_id)
            if output.error_message: self.logger.warning(f"ToTActionPlanSynthesisAgent for {lead_id} reported: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _synthesize_tot_action_plan for {lead_id}: {e}\n{traceback.format_exc()}")
            return ToTActionPlanSynthesisOutput(error_message=str(e), recommended_strategy_name="Error", primary_angle_hook="", synthesized_action_plan_steps=[])

    async def _develop_detailed_approach_plan(self, lead_analysis_str: str, persona_profile_str: str, deepened_pain_points_str: str, tot_action_plan: ToTActionPlanSynthesisOutput, lead_url:str, lead_id: str, run_id: str) -> DetailedApproachPlanOutput:
        plan_text = tot_action_plan.model_dump_json() if not tot_action_plan.error_message else "ToT action plan not available."
        plan_input = DetailedApproachPlanInput(lead_analysis=lead_analysis_str, persona_profile=persona_profile_str, deepened_pain_points=deepened_pain_points_str, final_action_plan_text=plan_text, product_service_offered=self.product_service_context, lead_url=lead_url)
        try:
            output = await self.detailed_approach_plan_agent.execute(plan_input, lead_id=lead_id, run_id=run_id)
            if output.error_message: self.logger.warning(f"DetailedApproachPlanAgent for {lead_id} reported: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _develop_detailed_approach_plan for {lead_id}: {e}\n{traceback.format_exc()}")
            return DetailedApproachPlanOutput(error_message=str(e), detailed_plan_steps=[])
    
    async def _create_personalized_message(self, analyzed_lead: AnalyzedLead, enhanced_strategy: EnhancedStrategy, contact_info: ContactInformation, persona_profile_str: str, lead_id: str, run_id: str) -> EnhancedPersonalizedMessage:
        action_plan_text = enhanced_strategy.tot_synthesized_action_plan.model_dump_json() if enhanced_strategy.tot_synthesized_action_plan and not enhanced_strategy.tot_synthesized_action_plan.error_message else "Action plan not available."
        vps_text = json.dumps([vp.model_dump() for vp in enhanced_strategy.value_propositions if not vp.error_message]) if enhanced_strategy.value_propositions else "Value propositions not available."
        contact_details = B2BContactDetailsInput(emails_found=contact_info.emails_found or [], instagram_profiles_found=contact_info.instagram_profiles or [])

        message_input = B2BPersonalizedMessageInput(
            final_action_plan_text=action_plan_text, customized_value_propositions_text=vps_text,
            contact_details=contact_details, product_service_offered=self.product_service_context,
            lead_url=str(analyzed_lead.validated_lead.site_data.url), company_name=self._extract_company_name(analyzed_lead),
            persona_fictional_name=persona_profile_str
        )
        try:
            msg_output = await self.b2b_personalized_message_agent.execute(message_input, lead_id=lead_id, run_id=run_id)
            error_msg = msg_output.error_message
            if error_msg: self.logger.warning(f"B2BPersonalizedMessageAgent for {lead_id} reported: {error_msg}")

            channel = CommunicationChannel.EMAIL
            if msg_output.crafted_message_channel and msg_output.crafted_message_channel.upper() in CommunicationChannel.__members__:
                channel = CommunicationChannel[msg_output.crafted_message_channel.upper()]

            primary_message = PersonalizedMessage(
                channel=channel, subject_line=msg_output.crafted_message_subject, message_body=msg_output.crafted_message_body,
                call_to_action=msg_output.crafted_message_cta, error_message=error_msg
            )
            return EnhancedPersonalizedMessage(primary_message=primary_message, error_message=error_msg)
        except Exception as e:
            self.logger.error(f"Exception in _create_personalized_message for {lead_id}: {e}\n{traceback.format_exc()}")
            err_str = str(e)
            return EnhancedPersonalizedMessage(primary_message=PersonalizedMessage(channel=CommunicationChannel.EMAIL, message_body=f"Error: {err_str}"), error_message=err_str)

    async def _create_internal_briefing(self, analyzed_lead: AnalyzedLead, enhanced_strategy: EnhancedStrategy, lead_id: str, run_id: str) -> InternalBriefing:
        all_lead_data = {
            "company_name": self._extract_company_name(analyzed_lead), "lead_url": str(analyzed_lead.validated_lead.site_data.url),
            "product_service_offered_by_us": self.product_service_context,
            "initial_site_extracted_text_summary": self._truncate_text(analyzed_lead.validated_lead.site_data.extracted_text_content or "", 300),
            "lead_analysis_summary": analyzed_lead.analysis.model_dump(exclude_none=True) if analyzed_lead.analysis else {},
            "enhanced_strategy_summary": enhanced_strategy.model_dump(exclude_none=True) # Pass the whole strategy
        }
        briefing_input = InternalBriefingSummaryInput(all_lead_data=all_lead_data)
        try:
            output = await self.internal_briefing_summary_agent.execute(briefing_input, lead_id=lead_id, run_id=run_id)
            if output.error_message:
                self.logger.warning(f"InternalBriefingSummaryAgent for {lead_id} reported: {output.error_message}")
                return InternalBriefing(executive_summary=f"Falha: {output.error_message}", error_message=output.error_message)

            # Map fields from output.sections (assuming they exist) to InternalBriefing fields
            # This is a simplified mapping; a real one would iterate output.sections
            return InternalBriefing(
                executive_summary=output.executive_summary,
                lead_overview=output.lead_overview,
                persona_profile_summary=output.persona_profile_summary,
                pain_points_and_needs=output.pain_points_and_needs,
                buying_triggers_opportunity=output.buying_triggers_opportunity,
                lead_qualification_summary=output.lead_qualification_summary,
                approach_strategy_summary=output.approach_strategy_summary,
                custom_value_proposition_summary=output.custom_value_proposition_summary,
                potential_objections_summary=output.potential_objections_summary,
                recommended_next_step=output.recommended_next_step,
                error_message=output.error_message
            )
        except Exception as e:
            self.logger.error(f"Exception in _create_internal_briefing for {lead_id}: {e}\n{traceback.format_exc()}")
            return InternalBriefing(executive_summary=f"Exceção: {str(e)}", error_message=str(e))
    
    def _extract_company_name(self, analyzed_lead: AnalyzedLead) -> str:
        site_data = analyzed_lead.validated_lead.site_data
        if site_data.google_search_data and site_data.google_search_data.title:
            title = site_data.google_search_data.title
            company_name = title.split(" - ")[0].split(" | ")[0].split(": ")[0]
            company_name = re.sub(r'\s*\([^)]*\)', '', company_name)
            if len(company_name) > 5 and not any(char in company_name.lower() for char in ['http', 'www', '.com']):
                return company_name.strip()
        url = str(site_data.url)
        domain = url.replace('https://', '').replace('http://', '').split('/')[0]
        domain = domain.replace('www.', '')
        return domain.split('.')[0].title()
    
    def _truncate_text(self, text: Optional[str], max_length: int = 15000) -> str:
        if not text: return ""
        return text[:max_length] if len(text) > max_length else text
    
    def _calculate_confidence_score(self, enhanced_strategy: Optional[EnhancedStrategy]) -> float:
        if not enhanced_strategy: return 0.1
        base_score = 0.3
        qual_score = 0.0
        if enhanced_strategy.lead_qualification and not enhanced_strategy.lead_qualification.error_message:
            qual_score = (enhanced_strategy.lead_qualification.confidence_score or 0.5) * 0.2 # Use confidence_score

        pain_score = 0.0
        if enhanced_strategy.pain_point_analysis and not enhanced_strategy.pain_point_analysis.error_message and enhanced_strategy.pain_point_analysis.detailed_pain_points:
            pain_score = len(enhanced_strategy.pain_point_analysis.detailed_pain_points) * 0.05
            pain_score = min(pain_score, 0.15)

        contact_score = 0.0
        if enhanced_strategy.contact_information and not enhanced_strategy.contact_information.error_message:
            contact_score = (enhanced_strategy.contact_information.extraction_confidence or 0.3) * 0.1

        intel_score = 0.0
        if enhanced_strategy.external_intelligence and not enhanced_strategy.external_intelligence.error_message:
            intel_score = (enhanced_strategy.external_intelligence.enrichment_confidence or 0.3) * 0.1

        strategy_score = 0.15 if enhanced_strategy.tot_synthesized_action_plan and not enhanced_strategy.tot_synthesized_action_plan.error_message else 0.05
        
        total_score = base_score + qual_score + pain_score + contact_score + intel_score + strategy_score
        return min(total_score, 1.0)
    
    def _calculate_roi_potential(self, enhanced_strategy: Optional[EnhancedStrategy]) -> float:
        if not enhanced_strategy: return 0.0
        qual_weight = 0.0
        if enhanced_strategy.lead_qualification and not enhanced_strategy.lead_qualification.error_message:
            qual_weight = (enhanced_strategy.lead_qualification.confidence_score or 0.5) * 0.4

        urgency_weight = 0.0
        if enhanced_strategy.pain_point_analysis and not enhanced_strategy.pain_point_analysis.error_message and enhanced_strategy.pain_point_analysis.urgency_level:
            urgency_map = {"low": 0.1, "medium": 0.2, "high": 0.3, "critical": 0.4}
            urgency_weight = urgency_map.get(str(enhanced_strategy.pain_point_analysis.urgency_level).lower(), 0.1) * 0.25

        value_weight = 0.0
        if enhanced_strategy.value_propositions:
            valid_vps = [vp for vp in enhanced_strategy.value_propositions if not vp.error_message]
            value_weight = len(valid_vps) * 0.1
            value_weight = min(value_weight, 0.25)

        trigger_weight = 0.0
        if enhanced_strategy.purchase_triggers and not enhanced_strategy.purchase_triggers.error_message and enhanced_strategy.purchase_triggers.identified_triggers:
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
    
    def _build_prompt(self, input_data: AnalyzedLead) -> str: # Part of BaseAgent, not directly called by EnhancedLeadProcessor.process
        return f"Default prompt for {self.name} with input {str(input_data)[:100]}"
    
    def _parse_response(self, response: str) -> dict: # Part of BaseAgent, not directly called
        try:
            if "```json" in response: response = response.split("```json")[1].split("```")[0]
            elif "```" in response: response = response.split("```")[1].split("```")[0]
            return json.loads(response.strip())
        except Exception as e:
            self.logger.warning(f"EnhancedLeadProcessor._parse_response: JSON error - {e}. Resp: {response[:200]}")
            return {"error": "Failed to parse response", "raw_response": response}

from data_models.lead_structures import DetailedPainPointSchema, CompetitorDetailSchema, IdentifiedTriggerSchema, \
    ToTStrategyOptionModel, EvaluatedStrategyModel, ActionPlanStepModel, ToTActionPlanSynthesisModel, \
    ContactStepDetailSchema, DetailedApproachPlanModel, ObjectionResponseModelSchema, InternalBriefingSectionSchema

[end of agents/enhanced_lead_processor.py]
