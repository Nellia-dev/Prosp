"""
Enhanced Lead Processor Agent - Comprehensive lead intelligence and processing
Incorporates features from new-cw.py and ck.py including Tavily enrichment, 
Tree-of-Thought strategy, and advanced intelligence gathering.
"""

import os
import json
import re
import time
import requests # Keep for TavilyEnrichmentAgent if it makes direct calls (though it shouldn't if using self._search_with_tavily)
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger
import traceback # Added for better error logging

from data_models.lead_structures import (
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
    # Schemas that are now part of lead_structures and used by EnhancedStrategy
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
from agents.base_agent import BaseAgent # BaseAgent.execute will be called
from core_logic.llm_client import LLMClientBase

# Import all agent classes and their I/O models
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
        # temperature removed as it's part of BaseAgent constructor now
    ):
        # Pass llm_client to BaseAgent constructor. Name and description are optional in BaseAgent.
        super().__init__(llm_client=llm_client, name="EnhancedLeadProcessor", description="Orchestrates a comprehensive lead processing pipeline.")
        self.logger = logger # Already available from BaseAgent if not set explicitly
        
        self.product_service_context = product_service_context
        self.competitors_list = competitors_list
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")

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
        persona_profile_str = ". ".join(filter(None, persona_parts))
        return persona_profile_str if persona_profile_str.strip() else f"Perfil da persona para {company_name} não detalhado suficientemente na análise inicial."

    def _construct_lead_analysis_string(self, analysis_obj: Optional[LeadAnalysis], external_intel: Optional[ExternalIntelligence]) -> str:
        if not analysis_obj: return "Análise inicial do lead não disponível."
        return (
            f"Setor da Empresa: {analysis_obj.company_sector}\n"
            f"Principais Serviços: {', '.join(analysis_obj.main_services or [])}\n"
            f"Descrição da Empresa: {analysis_obj.company_description or 'N/A'}\n"
            f"Desafios Potenciais Identificados: {', '.join(analysis_obj.potential_challenges or [])}\n"
            f"Tamanho Estimado: {analysis_obj.company_size_estimate or 'N/A'}\n"
            f"Cultura da Empresa: {str(analysis_obj.company_culture_values) if analysis_obj.company_culture_values else 'N/A'}\n"
            f"Diagnóstico Geral: {analysis_obj.general_diagnosis or 'N/A'}\n"
            f"Inteligência Externa: {external_intel.tavily_enrichment if external_intel and external_intel.tavily_enrichment else 'N/A'}"
        )

    # process method signature does NOT change for this workaround
    def process(self, analyzed_lead: AnalyzedLead) -> ComprehensiveProspectPackage:
        start_time = time.time()
        url = str(analyzed_lead.validated_lead.site_data.url)
        company_name = self._extract_company_name(analyzed_lead)
        # lead_id and run_id would be passed here if BaseAgent.execute was successfully modified

        self.logger.info(f"EnhancedLeadProcessor: Starting processing for URL: {url}")

        analysis_obj = analyzed_lead.analysis
        persona_profile_str = self._construct_persona_profile_string(analysis_obj, company_name)

        # Initialize Pydantic model outputs with defaults or error states
        external_intel_data = ExternalIntelligence(error_message="Not processed")
        contact_info_data = ContactInformation(error_message="Not processed")
        pain_analysis_data = PainPointAnalysis(error_message="Not processed", primary_pain_category="N/A")
        qualification_data = LeadQualification(error_message="Not processed")
        competitor_intel_data = CompetitorIntelligence(error_message="Not processed")
        purchase_triggers_data = PurchaseTriggers(error_message="Not processed")
        value_props_data = [ValueProposition(title="Error", connection_to_pain_or_trigger="Not processed", key_benefit="", differentiation_factor="", call_to_value="")]
        strategic_questions_data = ["Strategic questions not generated"]
        objection_framework_data = ObjectionFramework(error_message="Not processed")
        tot_generation_output = ToTStrategyGenerationOutput(error_message="Not processed")
        tot_evaluation_output = ToTStrategyEvaluationOutput(error_message="Not processed")
        tot_synthesis_output = ToTActionPlanSynthesisOutput(error_message="Not processed")
        detailed_approach_plan_data = DetailedApproachPlanModel(error_message="Not processed") # Use the schema from lead_structures
        personalized_message_data = EnhancedPersonalizedMessage(primary_message=PersonalizedMessage(channel=CommunicationChannel.EMAIL, message_body="Error", call_to_action="N/A"), error_message="Not processed")
        internal_briefing_data = InternalBriefing(executive_summary="Error generating briefing")

        try:
            external_intel_data = self._gather_external_intelligence(company_name, analyzed_lead)
            contact_info_data = self._extract_contact_information(analyzed_lead)
            
            lead_analysis_str_for_agents = self._construct_lead_analysis_string(analysis_obj, external_intel_data)
            
            # Execute agents - calls to execute() will not pass lead_id, run_id due to BaseAgent modification failure
            pain_agent_output = self.pain_point_deepening_agent.execute(PainPointDeepeningInput(lead_analysis=lead_analysis_str_for_agents, persona_profile=persona_profile_str, product_service_offered=self.product_service_context, company_name=company_name))
            pain_analysis_data = PainPointAnalysis(**pain_agent_output.model_dump()) # Map from agent's output model

            deepened_pain_points_str = pain_agent_output.model_dump_json(indent=2) if not pain_agent_output.error_message else "Análise de dores não disponível ou com erro."

            qual_agent_output = self.lead_qualification_agent.execute(LeadQualificationInput(lead_analysis=lead_analysis_str_for_agents, persona_profile=persona_profile_str, deepened_pain_points=deepened_pain_points_str, product_service_offered=self.product_service_context))
            qualification_data = LeadQualification(**qual_agent_output.model_dump())

            comp_agent_output = self.competitor_identification_agent.execute(CompetitorIdentificationInput(initial_extracted_text=analyzed_lead.validated_lead.site_data.extracted_text_content or "", product_service_offered= ", ".join(analysis_obj.main_services or []), known_competitors_list_str=self.competitors_list))
            competitor_intel_data = CompetitorIntelligence(**comp_agent_output.model_dump())

            trigger_agent_output = self.buying_trigger_identification_agent.execute(BuyingTriggerIdentificationInput(lead_data_str=json.dumps({"company_name": company_name, "description": analysis_obj.company_description}), enriched_data=external_intel_data.tavily_enrichment, product_service_offered=self.product_service_context))
            purchase_triggers_data = PurchaseTriggers(**trigger_agent_output.model_dump())
            
            vp_agent_output = self._create_value_propositions(lead_analysis_str_for_agents, persona_profile_str, deepened_pain_points_str, trigger_agent_output, company_name) # This helper now returns the agent's output model
            value_props_data = [ValueProposition(**vp.model_dump()) for vp in vp_agent_output.custom_propositions] if not vp_agent_output.error_message else [ValueProposition(title="Error", connection_to_pain_or_trigger=vp_agent_output.error_message, key_benefit="", differentiation_factor="", call_to_value="")]

            sq_agent_output = self._generate_strategic_questions(lead_analysis_str_for_agents, persona_profile_str, deepened_pain_points_str)
            strategic_questions_data = sq_agent_output.generated_questions if not sq_agent_output.error_message else [f"Error: {sq_agent_output.error_message}"]

            current_lead_summary_for_tot = f"Empresa: {company_name}...\nPersona: {persona_profile_str}...\nDores: {deepened_pain_points_str[:200]}...\nQualificação: {qualification_data.qualification_tier}"
            
            tot_generation_output = self._generate_tot_strategies(current_lead_summary_for_tot)
            tot_evaluation_output = self._evaluate_tot_strategies(tot_generation_output, current_lead_summary_for_tot)
            tot_synthesis_output = self._synthesize_tot_action_plan(tot_evaluation_output, tot_generation_output, current_lead_summary_for_tot)
            
            detailed_approach_plan_input_str = tot_synthesis_output.model_dump_json() if tot_synthesis_output and not tot_synthesis_output.error_message else "Plano ToT não disponível"
            detailed_plan_agent_output = self._develop_detailed_approach_plan(lead_analysis_str_for_agents, persona_profile_str, deepened_pain_points_str, tot_synthesis_output, url)
            detailed_approach_plan_data = DetailedApproachPlanModel(**detailed_plan_agent_output.model_dump()) if detailed_plan_agent_output and not detailed_plan_agent_output.error_message else DetailedApproachPlanModel(error_message=detailed_plan_agent_output.error_message if detailed_plan_agent_output else "Erro desconhecido")


            obj_handling_input_plan_str = detailed_approach_plan_data.model_dump_json() if detailed_approach_plan_data and not detailed_approach_plan_data.error_message else "Plano detalhado não disponível"
            obj_handling_agent_output = self._prepare_objection_handling(persona_profile_str, company_name, obj_handling_input_plan_str)
            objection_framework_data = ObjectionFramework(**obj_handling_agent_output.model_dump())

            enhanced_strategy = EnhancedStrategy(
                external_intelligence=external_intel_data, contact_information=contact_info_data,
                pain_point_analysis=pain_analysis_data, competitor_intelligence=competitor_intel_data,
                purchase_triggers=purchase_triggers_data, lead_qualification=qualification_data,
                tot_generated_strategies=tot_generation_output.proposed_strategies if tot_generation_output and not tot_generation_output.error_message else [],
                tot_evaluated_strategies=tot_evaluation_output.evaluated_strategies if tot_evaluation_output and not tot_evaluation_output.error_message else [],
                tot_synthesized_action_plan=tot_synthesis_output if tot_synthesis_output and not tot_synthesis_output.error_message else None,
                detailed_approach_plan=detailed_approach_plan_data,
                value_propositions=value_props_data, objection_framework=objection_framework_data,
                strategic_questions=strategic_questions_data
            )
            
            personalized_message_data = self._create_personalized_message(analyzed_lead, enhanced_strategy, contact_info_data, persona_profile_str)
            internal_briefing_data = self._create_internal_briefing(analyzed_lead, enhanced_strategy)
            
            total_processing_time = time.time() - start_time
            return ComprehensiveProspectPackage(
                analyzed_lead=analyzed_lead, enhanced_strategy=enhanced_strategy,
                enhanced_personalized_message=personalized_message_data,
                internal_briefing=internal_briefing_data,
                confidence_score=self._calculate_confidence_score(enhanced_strategy),
                roi_potential_score=self._calculate_roi_potential(enhanced_strategy),
                brazilian_market_fit=self._calculate_brazilian_fit(analyzed_lead),
                processing_metadata={"total_processing_time": total_processing_time, "company_name": company_name}
            )
        except Exception as e:
            self.logger.error(f"EnhancedLeadProcessor: Critical error during processing for {url}: {e}\n{traceback.format_exc()}")
            # Return a package with error information
            return ComprehensiveProspectPackage(
                analyzed_lead=analyzed_lead,
                enhanced_strategy=EnhancedStrategy(error_message=f"Processing failed: {str(e)}"), # Add error_message to EnhancedStrategy if not present
                enhanced_personalized_message=EnhancedPersonalizedMessage(primary_message=PersonalizedMessage(channel=CommunicationChannel.EMAIL,message_body="Error",call_to_action="N/A"), error_message=f"Processing failed: {str(e)}"),
                internal_briefing=InternalBriefing(executive_summary=f"Processing failed: {str(e)}"),
                confidence_score=0.1, roi_potential_score=0.0, brazilian_market_fit=0.0, # Default scores
                processing_metadata={"total_processing_time": time.time() - start_time, "company_name": company_name, "error": str(e)}
            )

    def _gather_external_intelligence(self, company_name: str, analyzed_lead: AnalyzedLead) -> ExternalIntelligence:
        text_content = analyzed_lead.validated_lead.site_data.extracted_text_content or ""
        enrichment_input = TavilyEnrichmentInput(company_name=company_name, initial_extracted_text=text_content)
        try:
            output: TavilyEnrichmentOutput = self.tavily_enrichment_agent.execute(enrichment_input) # No lead_id, run_id
            return ExternalIntelligence(
                tavily_enrichment=output.enriched_data,
                market_research=f"Insights from Tavily enrichment for {company_name}.",
                news_analysis=f"News from Tavily enrichment for {company_name}.",
                sources_used=["Tavily API"] if output.tavily_api_called else [],
                enrichment_confidence=0.8 if output.tavily_api_called and output.enriched_data else 0.3,
                error_message=output.error_message
            )
        except Exception as e:
            self.logger.error(f"Exception in _gather_external_intelligence: {e}")
            return ExternalIntelligence(error_message=str(e))

    def _extract_contact_information(self, analyzed_lead: AnalyzedLead) -> ContactInformation:
        text_content = analyzed_lead.validated_lead.cleaned_text_content or analyzed_lead.validated_lead.site_data.extracted_text_content or ""
        company_name = self._extract_company_name(analyzed_lead)
        extraction_input = ContactExtractionInput(extracted_text=text_content, company_name=company_name, product_service_offered=self.product_service_context)
        try:
            output: ContactExtractionOutput = self.contact_extraction_agent.execute(extraction_input) # No lead_id, run_id
            return ContactInformation(
                emails_found=output.emails_found,
                instagram_profiles=output.instagram_profiles_found,
                tavily_search_suggestions=[output.tavily_search_suggestion] if output.tavily_search_suggestion else [],
                extraction_confidence=0.75 if output.emails_found or output.instagram_profiles_found else 0.25,
                error_message=output.error_message
            )
        except Exception as e:
            self.logger.error(f"Exception in _extract_contact_information: {e}")
            return ContactInformation(error_message=str(e))

    def _analyze_pain_points(self, lead_analysis_str: str, persona_profile_str: str, company_name: str) -> PainPointDeepeningOutput:
        pain_input = PainPointDeepeningInput(
            lead_analysis=lead_analysis_str, persona_profile=persona_profile_str,
            product_service_offered=self.product_service_context, company_name=company_name
        )
        try:
            output: PainPointDeepeningOutput = self.pain_point_deepening_agent.execute(pain_input) # No lead_id, run_id
            if output.error_message: self.logger.warning(f"PainPointDeepeningAgent returned: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _analyze_pain_points: {e}")
            return PainPointDeepeningOutput(error_message=str(e))

    def _qualify_lead(self, lead_analysis_str: str, persona_profile_str: str, deepened_pain_points_str: str) -> LeadQualificationOutput:
        qualification_input = LeadQualificationInput(
            lead_analysis=lead_analysis_str, persona_profile=persona_profile_str,
            deepened_pain_points=deepened_pain_points_str, product_service_offered=self.product_service_context
        )
        try:
            output: LeadQualificationOutput = self.lead_qualification_agent.execute(qualification_input) # No lead_id, run_id
            if output.error_message: self.logger.warning(f"LeadQualificationAgent returned: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _qualify_lead: {e}")
            return LeadQualificationOutput(error_message=str(e))

    def _analyze_competitors(self, analyzed_lead: AnalyzedLead) -> CompetitorIdentificationOutput:
        text_content = analyzed_lead.validated_lead.site_data.extracted_text_content or ""
        lead_product_service = ", ".join(analyzed_lead.analysis.main_services or []) or (analyzed_lead.analysis.company_description or "Serviços da empresa analisada")
        competitor_input = CompetitorIdentificationInput(
            initial_extracted_text=text_content, product_service_offered=lead_product_service,
            known_competitors_list_str=self.competitors_list
        )
        try:
            output: CompetitorIdentificationOutput = self.competitor_identification_agent.execute(competitor_input) # No lead_id, run_id
            if output.error_message: self.logger.warning(f"CompetitorIdentificationAgent returned: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _analyze_competitors: {e}")
            return CompetitorIdentificationOutput(error_message=str(e))

    def _identify_purchase_triggers(self, analyzed_lead: AnalyzedLead, external_intel: Optional[ExternalIntelligence]) -> BuyingTriggerIdentificationOutput:
        lead_data_dict = {
            "company_name": self._extract_company_name(analyzed_lead), "url": str(analyzed_lead.validated_lead.site_data.url),
            "description": analyzed_lead.analysis.company_description, "sector": analyzed_lead.analysis.company_sector,
            "main_services": analyzed_lead.analysis.main_services, "recent_activities_from_analysis": analyzed_lead.analysis.recent_activities,
            "extracted_text_summary": self._truncate_text(analyzed_lead.validated_lead.site_data.extracted_text_content or "", 500)
        }
        try: lead_data_str = json.dumps(lead_data_dict, ensure_ascii=False)
        except Exception as e_json:
            self.logger.warning(f"Could not serialize lead_data for BuyingTriggerIdentificationAgent: {e_json}")
            lead_data_str = "{'error': 'Could not serialize lead data'}"
        enriched_data_str = external_intel.tavily_enrichment if external_intel and external_intel.tavily_enrichment else "Nenhuma informação de enriquecimento disponível."
        trigger_input = BuyingTriggerIdentificationInput(
            lead_data_str=lead_data_str, enriched_data=enriched_data_str, product_service_offered=self.product_service_context
        )
        try:
            output: BuyingTriggerIdentificationOutput = self.buying_trigger_identification_agent.execute(trigger_input) # No lead_id, run_id
            if output.error_message: self.logger.warning(f"BuyingTriggerIdentificationAgent returned: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _identify_purchase_triggers: {e}")
            return BuyingTriggerIdentificationOutput(error_message=str(e))

    def _create_value_propositions(self, lead_analysis_str: str, persona_profile_str: str, deepened_pain_points_str: str, purchase_triggers_output: Optional[BuyingTriggerIdentificationOutput], company_name: str) -> ValuePropositionCustomizationOutput:
        buying_triggers_report_str = purchase_triggers_output.model_dump_json(indent=2) if purchase_triggers_output and not purchase_triggers_output.error_message else "Relatório de gatilhos não disponível ou com erro."

        value_prop_input = ValuePropositionCustomizationInput(
            lead_analysis=lead_analysis_str, persona_profile=persona_profile_str,
            deepened_pain_points=deepened_pain_points_str, buying_triggers_report=buying_triggers_report_str,
            product_service_offered=self.product_service_context, company_name=company_name
        )
        try:
            output: ValuePropositionCustomizationOutput = self.value_proposition_customization_agent.execute(value_prop_input) # No lead_id, run_id
            if output.error_message: self.logger.warning(f"ValuePropositionCustomizationAgent returned: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _create_value_propositions: {e}")
            return ValuePropositionCustomizationOutput(error_message=str(e))

    def _generate_strategic_questions(self, lead_analysis_str: str, persona_profile_str: str, deepened_pain_points_str: str) -> StrategicQuestionGenerationOutput:
        sq_input = StrategicQuestionGenerationInput(
            lead_analysis=lead_analysis_str, persona_profile=persona_profile_str, deepened_pain_points=deepened_pain_points_str
        )
        try:
            output: StrategicQuestionGenerationOutput = self.strategic_question_generation_agent.execute(sq_input) # No lead_id, run_id
            if output.error_message: self.logger.warning(f"StrategicQuestionGenerationAgent returned: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _generate_strategic_questions: {e}")
            return StrategicQuestionGenerationOutput(error_message=str(e))

    def _prepare_objection_handling(self, persona_profile_str: str, company_name: str, detailed_approach_plan_text: str) -> ObjectionHandlingOutput:
        objection_input = ObjectionHandlingInput(
            detailed_approach_plan_text=detailed_approach_plan_text or "Plano de abordagem não disponível.",
            persona_profile=persona_profile_str, product_service_offered=self.product_service_context, company_name=company_name
        )
        try:
            output: ObjectionHandlingOutput = self.objection_handling_agent.execute(objection_input) # No lead_id, run_id
            if output.error_message: self.logger.warning(f"ObjectionHandlingAgent returned: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _prepare_objection_handling: {e}")
            return ObjectionHandlingOutput(error_message=str(e))
    
    def _generate_tot_strategies(self, current_lead_summary: str) -> ToTStrategyGenerationOutput:
        generation_input = ToTStrategyGenerationInput(current_lead_summary=current_lead_summary, product_service_offered=self.product_service_context)
        try:
            output: ToTStrategyGenerationOutput = self.tot_strategy_generation_agent.execute(generation_input) # No lead_id, run_id
            if output.error_message: self.logger.warning(f"ToTStrategyGenerationAgent failed: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in ToT strategy generation: {e}")
            return ToTStrategyGenerationOutput(error_message=f"Exceção ao gerar estratégias: {str(e)}")

    def _evaluate_tot_strategies(self, generated_strategies_output: Optional[ToTStrategyGenerationOutput], current_lead_summary: str) -> ToTStrategyEvaluationOutput:
        proposed_strategies_text_input = "Nenhuma estratégia proposta foi gerada."
        if generated_strategies_output and generated_strategies_output.proposed_strategies:
            proposed_strategies_text_input = ""
            for i, strat in enumerate(generated_strategies_output.proposed_strategies):
                proposed_strategies_text_input += f"Estratégia {i+1}: {strat.strategy_name}\n  Ângulo/Gancho: {strat.angle_or_hook}\n  Tom: {strat.tone_of_voice}\n  Canais: {', '.join(strat.primary_channels)}\n  Pontos Chave: {'; '.join(strat.key_points_or_arguments)}\n  Pergunta de Abertura: {strat.opening_question}\n\n"
        elif generated_strategies_output and generated_strategies_output.error_message:
             proposed_strategies_text_input = f"Erro na geração de estratégias: {generated_strategies_output.error_message}"

        evaluation_input = ToTStrategyEvaluationInput(proposed_strategies_text=proposed_strategies_text_input, current_lead_summary=current_lead_summary)
        try:
            output: ToTStrategyEvaluationOutput = self.tot_strategy_evaluation_agent.execute(evaluation_input) # No lead_id, run_id
            if output.error_message: self.logger.warning(f"ToTStrategyEvaluationAgent failed: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in ToT strategy evaluation: {e}")
            return ToTStrategyEvaluationOutput(error_message=f"Exceção ao avaliar estratégias: {str(e)}")

    def _synthesize_tot_action_plan(self, evaluated_strategies_output: Optional[ToTStrategyEvaluationOutput], generated_strategies_output: Optional[ToTStrategyGenerationOutput], current_lead_summary: str) -> ToTActionPlanSynthesisOutput:
        evaluated_strategies_text_input = "Nenhuma estratégia avaliada."
        if evaluated_strategies_output and evaluated_strategies_output.evaluated_strategies:
            evaluated_strategies_text_input = ""
            for i, strat_eval in enumerate(evaluated_strategies_output.evaluated_strategies):
                evaluated_strategies_text_input += f"Avaliação da Estratégia: {strat_eval.strategy_name}\n  Adequação: {strat_eval.suitability_assessment}\n  Pontos Fortes: {'; '.join(strat_eval.strengths)}\n  Fraquezas/Riscos: {'; '.join(strat_eval.weaknesses_or_risks)}\n  Melhorias: {'; '.join(strat_eval.suggested_improvements)}\n  Confiança: {strat_eval.confidence_score} - {strat_eval.confidence_justification}\n\n"
        elif evaluated_strategies_output and evaluated_strategies_output.error_message:
            evaluated_strategies_text_input = f"Erro na avaliação de estratégias: {evaluated_strategies_output.error_message}"

        proposed_strategies_text_input = "Nenhuma estratégia original proposta."
        if generated_strategies_output and generated_strategies_output.proposed_strategies:
            proposed_strategies_text_input = ""
            for i, strat in enumerate(generated_strategies_output.proposed_strategies):
                proposed_strategies_text_input += f"Estratégia Original {i+1}: {strat.strategy_name}\n  Detalhes: {strat.angle_or_hook}\n\n"

        synthesis_input = ToTActionPlanSynthesisInput(
            evaluated_strategies_text=evaluated_strategies_text_input,
            proposed_strategies_text=proposed_strategies_text_input,
            current_lead_summary=current_lead_summary
        )
        try:
            output: ToTActionPlanSynthesisOutput = self.tot_action_plan_synthesis_agent.execute(synthesis_input) # No lead_id, run_id
            if output.error_message: self.logger.warning(f"ToTActionPlanSynthesisAgent failed: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in ToT action plan synthesis: {e}")
            return ToTActionPlanSynthesisOutput(error_message=f"Exceção ao sintetizar plano de ação: {str(e)}")

    def _develop_detailed_approach_plan(self, lead_analysis_str: str, persona_profile_str: str, deepened_pain_points_str: str, tot_action_plan: Optional[ToTActionPlanSynthesisOutput], lead_url:str) -> DetailedApproachPlanOutput:
        final_action_plan_summary_for_detailed_plan = "Plano de Ação Sintetizado:\n"
        if tot_action_plan and not tot_action_plan.error_message:
            final_action_plan_summary_for_detailed_plan += f"- Estratégia Recomendada: {tot_action_plan.recommended_strategy_name}\n"
            final_action_plan_summary_for_detailed_plan += f"- Gancho Principal: {tot_action_plan.primary_angle_hook}\n" # ... (rest of summary)
        elif tot_action_plan and tot_action_plan.error_message:
            final_action_plan_summary_for_detailed_plan = f"Erro no plano de ação sintetizado: {tot_action_plan.error_message}"
        else:
            final_action_plan_summary_for_detailed_plan = "Plano de ação sintetizado não disponível."

        plan_input = DetailedApproachPlanInput(
            lead_analysis=lead_analysis_str, persona_profile=persona_profile_str,
            deepened_pain_points=deepened_pain_points_str, final_action_plan_text=final_action_plan_summary_for_detailed_plan,
            product_service_offered=self.product_service_context, lead_url=lead_url
        )
        try:
            output: DetailedApproachPlanOutput = self.detailed_approach_plan_agent.execute(plan_input) # No lead_id, run_id
            if output.error_message: self.logger.warning(f"DetailedApproachPlanAgent failed: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in detailed approach plan development: {e}")
            return DetailedApproachPlanOutput(error_message=str(e))
    
    def _create_personalized_message(self, analyzed_lead: AnalyzedLead, enhanced_strategy: EnhancedStrategy, contact_info: Optional[ContactInformation], persona_profile_str: str) -> EnhancedPersonalizedMessage:
        company_name = self._extract_company_name(analyzed_lead)
        final_action_plan_summary = "Plano de Ação Chave:\n"
        if enhanced_strategy.tot_synthesized_action_plan and not enhanced_strategy.tot_synthesized_action_plan.error_message:
            plan = enhanced_strategy.tot_synthesized_action_plan
            final_action_plan_summary += f"- Estratégia: {plan.recommended_strategy_name}\n" #... (rest of summary)
        else: final_action_plan_summary = enhanced_strategy.tot_synthesized_action_plan.error_message if enhanced_strategy.tot_synthesized_action_plan else "Plano ToT não disponível."

        value_props_text = "\n".join([f"VP{i+1}({vp.title}): {vp.key_benefit}" for i, vp in enumerate(enhanced_strategy.value_propositions or []) if not vp.error_message]) or "Propostas de valor não disponíveis."

        b2b_contact_details = B2BContactDetailsInput(
            emails_found=contact_info.emails_found if contact_info else [],
            instagram_profiles_found=contact_info.instagram_profiles if contact_info else []
        )
        message_input = B2BPersonalizedMessageInput(
            final_action_plan_text=final_action_plan_summary, customized_value_propositions_text=value_props_text,
            contact_details=b2b_contact_details, product_service_offered=self.product_service_context,
            lead_url=str(analyzed_lead.validated_lead.site_data.url), company_name=company_name,
            persona_fictional_name=persona_profile_str
        )
        try:
            msg_output: B2BPersonalizedMessageOutput = self.b2b_personalized_message_agent.execute(message_input) # No lead_id, run_id
            primary_msg_error = msg_output.error_message
            if msg_output.error_message and not (msg_output.crafted_message_body and msg_output.crafted_message_body != "Não foi possível gerar a mensagem."):
                self.logger.warning(f"B2BPersonalizedMessageAgent failed: {msg_output.error_message}")
                primary_msg_error = msg_output.error_message

            channel = CommunicationChannel.EMAIL
            if msg_output.crafted_message_channel and msg_output.crafted_message_channel.upper() in CommunicationChannel.__members__:
                channel = CommunicationChannel[msg_output.crafted_message_channel.upper()]
            elif msg_output.crafted_message_channel and msg_output.crafted_message_channel != "N/A":
                 self.logger.warning(f"Invalid channel '{msg_output.crafted_message_channel}' from B2B agent. Defaulting to EMAIL.")

            primary_message = PersonalizedMessage(
                channel=channel, subject_line=msg_output.crafted_message_subject, message_body=msg_output.crafted_message_body,
                call_to_action="Verificar corpo da mensagem para CTA.",
                error_message=primary_msg_error
            )
            return EnhancedPersonalizedMessage(primary_message=primary_message, error_message=primary_msg_error)
        except Exception as e:
            self.logger.error(f"Exception in _create_personalized_message: {e}")
            primary_msg = PersonalizedMessage(channel=CommunicationChannel.EMAIL, message_body=f"Exceção: {str(e)}", call_to_action="N/A", error_message=str(e))
            return EnhancedPersonalizedMessage(primary_message=primary_msg, error_message=str(e))

    def _create_internal_briefing(self, analyzed_lead: AnalyzedLead, enhanced_strategy: EnhancedStrategy) -> InternalBriefing:
        company_name = self._extract_company_name(analyzed_lead)
        analysis_obj = analyzed_lead.analysis
        all_lead_data = {
            "company_name": company_name, "lead_url": str(analyzed_lead.validated_lead.site_data.url),
            "product_service_offered_by_us": self.product_service_context,
            "initial_site_extracted_text_summary": self._truncate_text(analyzed_lead.validated_lead.site_data.extracted_text_content or "", 300),
            "lead_analysis_summary": analysis_obj.model_dump(exclude_none=True) if analysis_obj else {},
            "external_intelligence_summary": enhanced_strategy.external_intelligence.model_dump(exclude_none=True) if enhanced_strategy.external_intelligence else {},
            "contact_information_summary": enhanced_strategy.contact_information.model_dump(exclude_none=True) if enhanced_strategy.contact_information else {},
            "pain_point_analysis_summary": enhanced_strategy.pain_point_analysis.model_dump(exclude_none=True) if enhanced_strategy.pain_point_analysis else {},
            "lead_qualification_summary": enhanced_strategy.lead_qualification.model_dump(exclude_none=True) if enhanced_strategy.lead_qualification else {},
            "competitor_intelligence_summary": enhanced_strategy.competitor_intelligence.model_dump(exclude_none=True) if enhanced_strategy.competitor_intelligence else {},
            "purchase_triggers_summary": enhanced_strategy.purchase_triggers.model_dump(exclude_none=True) if enhanced_strategy.purchase_triggers else {},
            "customized_value_propositions_summary": [vp.model_dump(exclude_none=True) for vp in enhanced_strategy.value_propositions or []],
            "strategic_questions_generated": enhanced_strategy.strategic_questions or [],
            "objection_handling_summary": enhanced_strategy.objection_framework.model_dump(exclude_none=True) if enhanced_strategy.objection_framework else {},
            "tot_synthesized_action_plan_summary": enhanced_strategy.tot_synthesized_action_plan.model_dump(exclude_none=True) if enhanced_strategy.tot_synthesized_action_plan else {},
            "detailed_approach_plan_summary": enhanced_strategy.detailed_approach_plan.model_dump(exclude_none=True) if enhanced_strategy.detailed_approach_plan else {},
        }
        briefing_input = InternalBriefingSummaryInput(all_lead_data=all_lead_data)
        try:
            output: InternalBriefingSummaryOutput = self.internal_briefing_summary_agent.execute(briefing_input) # No lead_id, run_id
            if output.error_message:
                self.logger.warning(f"InternalBriefingSummaryAgent returned an error: {output.error_message}")
                return InternalBriefing(executive_summary=f"Falha: {output.error_message}", error_message=output.error_message)

            return InternalBriefing( # Mapping from agent's output model
                executive_summary=output.executive_summary,
                lead_overview=InternalBriefingSectionSchema(**output.lead_overview.model_dump()) if output.lead_overview else None,
                persona_profile_summary=InternalBriefingSectionSchema(**output.persona_profile_summary.model_dump()) if output.persona_profile_summary else None,
                # ... (map all other sections similarly) ...
                pain_points_and_needs=InternalBriefingSectionSchema(**output.pain_points_and_needs.model_dump()) if output.pain_points_and_needs else None,
                buying_triggers_opportunity=InternalBriefingSectionSchema(**output.buying_triggers_opportunity.model_dump()) if output.buying_triggers_opportunity else None,
                lead_qualification_summary=InternalBriefingSectionSchema(**output.lead_qualification_summary.model_dump()) if output.lead_qualification_summary else None,
                approach_strategy_summary=InternalBriefingSectionSchema(**output.approach_strategy_summary.model_dump()) if output.approach_strategy_summary else None,
                custom_value_proposition_summary=InternalBriefingSectionSchema(**output.custom_value_proposition_summary.model_dump()) if output.custom_value_proposition_summary else None,
                potential_objections_summary=InternalBriefingSectionSchema(**output.potential_objections_summary.model_dump()) if output.potential_objections_summary else None,
                recommended_next_step=output.recommended_next_step,
                error_message=output.error_message
            )
        except Exception as e:
            self.logger.error(f"Exception in _create_internal_briefing: {e}")
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
        if enhanced_strategy.lead_qualification:
            if enhanced_strategy.lead_qualification.confidence_score is not None:
                qual_score = enhanced_strategy.lead_qualification.confidence_score * 0.2
            # Fallback to older qualification_score if confidence_score is not there
            elif hasattr(enhanced_strategy.lead_qualification, 'qualification_score') and enhanced_strategy.lead_qualification.qualification_score is not None:
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
    
    def _calculate_roi_potential(self, enhanced_strategy: Optional[EnhancedStrategy]) -> float:
        if not enhanced_strategy: return 0.0
        qual_weight = 0.0
        if enhanced_strategy.lead_qualification:
            if enhanced_strategy.lead_qualification.confidence_score is not None:
                qual_weight = enhanced_strategy.lead_qualification.confidence_score * 0.4
            elif hasattr(enhanced_strategy.lead_qualification, 'qualification_score') and enhanced_strategy.lead_qualification.qualification_score is not None: # Fallback
                 qual_weight = enhanced_strategy.lead_qualification.qualification_score * 0.4

        urgency_weight = 0.0
        if enhanced_strategy.pain_point_analysis and enhanced_strategy.pain_point_analysis.urgency_level:
            urgency_map = {"low": 0.1, "medium": 0.2, "high": 0.3, "critical": 0.4}
            urgency_weight = urgency_map.get(str(enhanced_strategy.pain_point_analysis.urgency_level).lower(), 0.1) * 0.25

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
