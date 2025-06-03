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
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger
import traceback

from pydantic import BaseModel # Added for _report_agent_event_to_mcp

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
from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase
from mcp_server.data_models import AgentEventPayload, AgentExecutionStatusEnum # Added for MCP reporting

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
        mcp_server_url: Optional[str] = None, # Added
        enable_mcp_reporting: bool = False, # Added
    ):
        super().__init__(llm_client=llm_client, name="EnhancedLeadProcessor", description="Orchestrates a comprehensive lead processing pipeline.")
        # self.logger is inherited from BaseAgent
        
        self.product_service_context = product_service_context
        self.competitors_list = competitors_list
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")

        # MCP Configuration
        self.MCP_SERVER_URL = mcp_server_url or os.getenv("MCP_SERVER_URL", "http://127.0.0.1:5001")
        self.ENABLE_MCP_REPORTING = enable_mcp_reporting if enable_mcp_reporting is not None else os.getenv("ENABLE_MCP_REPORTING", "false").lower() == "true"

        self.logger.info(f"MCP Reporting Enabled: {self.ENABLE_MCP_REPORTING}, Server URL: {self.MCP_SERVER_URL}")


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

    def _report_agent_event_to_mcp(self, lead_id: str, agent_name: str, status: str, start_time: datetime, end_time: datetime, output_model_instance: Optional[BaseModel], agent_error_message: Optional[str]) -> None:
        if not self.ENABLE_MCP_REPORTING:
            return

        processing_time_seconds = (end_time - start_time).total_seconds()

        output_data_json = None
        if output_model_instance and hasattr(output_model_instance, 'model_dump_json'):
            try:
                output_data_json = output_model_instance.model_dump_json()
            except Exception as e:
                self.logger.error(f"MCP Report: Error serializing output model for {agent_name}: {e}")
                output_data_json = json.dumps({"error": "Failed to serialize output model", "details": str(e)})

        metrics_json = None # For future use, as discussed

        event_status = AgentExecutionStatusEnum.SUCCESS if status.upper() == "SUCCESS" else AgentExecutionStatusEnum.FAILED

        payload = AgentEventPayload(
            agent_name=agent_name,
            status=event_status,
            start_time=start_time,
            end_time=end_time,
            processing_time_seconds=processing_time_seconds,
            error_message=agent_error_message,
            input_data_summary=None, # Not required by current subtask to capture input
            output_data_summary=output_data_json,
            metrics=metrics_json
        )

        try:
            response = requests.post(f"{self.MCP_SERVER_URL}/api/lead/{lead_id}/event", json=payload.model_dump(mode='json'), timeout=5)
            response.raise_for_status()
            self.logger.info(f"MCP Report: Successfully reported event for agent {agent_name} on lead {lead_id}. Status: {status}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"MCP Report: Failed to report event for agent {agent_name} on lead {lead_id}: {e}")
        except Exception as e_ser: # Catch potential serialization errors from payload.model_dump() itself
            self.logger.error(f"MCP Report: Failed to serialize payload for agent {agent_name} on lead {lead_id}: {e_ser}")


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

    async def process(self, analyzed_lead: AnalyzedLead, lead_id: str, run_id: str) -> ComprehensiveProspectPackage: # Added lead_id, run_id and async
        process_start_time_utc = datetime.utcnow() # For overall timing, can be part of metadata
        url = str(analyzed_lead.validated_lead.site_data.url)
        company_name = self._extract_company_name(analyzed_lead)

        self.logger.info(f"EnhancedLeadProcessor (Lead ID: {lead_id}, Run ID: {run_id}): Starting processing for URL: {url}")

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
            # Pass lead_id to helpers
            external_intel_data = await self._gather_external_intelligence(company_name, analyzed_lead, lead_id)
            contact_info_data = await self._extract_contact_information(analyzed_lead, lead_id)
            
            lead_analysis_str_for_agents = self._construct_lead_analysis_string(analysis_obj, external_intel_data)
            
            pain_agent_output = await self._analyze_pain_points(lead_analysis_str_for_agents, persona_profile_str, company_name, lead_id)
            pain_analysis_data = PainPointAnalysis(**pain_agent_output.model_dump()) if not pain_agent_output.error_message else PainPointAnalysis(error_message=pain_agent_output.error_message, primary_pain_category="N/A")

            deepened_pain_points_str = pain_agent_output.model_dump_json(indent=2) if not pain_agent_output.error_message else "Análise de dores não disponível ou com erro."

            qual_agent_output = await self._qualify_lead(lead_analysis_str_for_agents, persona_profile_str, deepened_pain_points_str, lead_id)
            qualification_data = LeadQualification(**qual_agent_output.model_dump()) if not qual_agent_output.error_message else LeadQualification(error_message=qual_agent_output.error_message)

            comp_agent_output = await self._analyze_competitors(analyzed_lead, lead_id)
            competitor_intel_data = CompetitorIntelligence(**comp_agent_output.model_dump()) if not comp_agent_output.error_message else CompetitorIntelligence(error_message=comp_agent_output.error_message)

            trigger_agent_output = await self._identify_purchase_triggers(analyzed_lead, external_intel_data, lead_id)
            purchase_triggers_data = PurchaseTriggers(**trigger_agent_output.model_dump()) if not trigger_agent_output.error_message else PurchaseTriggers(error_message=trigger_agent_output.error_message)
            
            vp_agent_output = await self._create_value_propositions(lead_analysis_str_for_agents, persona_profile_str, deepened_pain_points_str, trigger_agent_output, company_name, lead_id)
            value_props_data = [ValueProposition(**vp.model_dump()) for vp in vp_agent_output.custom_propositions] if not vp_agent_output.error_message else [ValueProposition(title="Error", connection_to_pain_or_trigger=vp_agent_output.error_message or "N/A", key_benefit="", differentiation_factor="", call_to_value="")]

            sq_agent_output = await self._generate_strategic_questions(lead_analysis_str_for_agents, persona_profile_str, deepened_pain_points_str, lead_id)
            strategic_questions_data = sq_agent_output.generated_questions if not sq_agent_output.error_message else [f"Error: {sq_agent_output.error_message or 'N/A'}"]

            current_lead_summary_for_tot = f"Empresa: {company_name}...\nPersona: {persona_profile_str}...\nDores: {deepened_pain_points_str[:200]}...\nQualificação: {qualification_data.qualification_tier if qualification_data else 'N/A'}"
            
            tot_generation_output = await self._generate_tot_strategies(current_lead_summary_for_tot, lead_id)
            tot_evaluation_output = await self._evaluate_tot_strategies(tot_generation_output, current_lead_summary_for_tot, lead_id)
            tot_synthesis_output = await self._synthesize_tot_action_plan(tot_evaluation_output, tot_generation_output, current_lead_summary_for_tot, lead_id)
            
            detailed_approach_plan_input_str = tot_synthesis_output.model_dump_json() if tot_synthesis_output and not tot_synthesis_output.error_message else "Plano ToT não disponível"
            detailed_plan_agent_output = await self._develop_detailed_approach_plan(lead_analysis_str_for_agents, persona_profile_str, deepened_pain_points_str, tot_synthesis_output, url, lead_id)
            detailed_approach_plan_data = DetailedApproachPlanModel(**detailed_plan_agent_output.model_dump()) if detailed_plan_agent_output and not detailed_plan_agent_output.error_message else DetailedApproachPlanModel(error_message=detailed_plan_agent_output.error_message if detailed_plan_agent_output else "Erro desconhecido")

            obj_handling_input_plan_str = detailed_approach_plan_data.model_dump_json() if detailed_approach_plan_data and not detailed_approach_plan_data.error_message else "Plano detalhado não disponível"
            obj_handling_agent_output = await self._prepare_objection_handling(persona_profile_str, company_name, obj_handling_input_plan_str, lead_id)
            objection_framework_data = ObjectionFramework(**obj_handling_agent_output.model_dump()) if not obj_handling_agent_output.error_message else ObjectionFramework(error_message=obj_handling_agent_output.error_message)

            enhanced_strategy = EnhancedStrategy(
                external_intelligence=external_intel_data,
                contact_information=contact_info_data,
                pain_point_analysis=pain_analysis_data,
                competitor_intelligence=competitor_intel_data,
                purchase_triggers=purchase_triggers_data,
                lead_qualification=qualification_data,
                tot_generated_strategies=tot_generation_output.proposed_strategies if tot_generation_output and not tot_generation_output.error_message else [],
                tot_evaluated_strategies=tot_evaluation_output.evaluated_strategies if tot_evaluation_output and not tot_evaluation_output.error_message else [],
                tot_synthesized_action_plan=tot_synthesis_output if tot_synthesis_output and not tot_synthesis_output.error_message else None,
                detailed_approach_plan=detailed_approach_plan_data,
                value_propositions=value_props_data,
                objection_framework=objection_framework_data,
                strategic_questions=strategic_questions_data
            )
            
            personalized_message_data = await self._create_personalized_message(analyzed_lead, enhanced_strategy, contact_info_data, persona_profile_str, lead_id)
            internal_briefing_data = await self._create_internal_briefing(analyzed_lead, enhanced_strategy, lead_id)
            
            total_processing_time_seconds = (datetime.utcnow() - process_start_time_utc).total_seconds()
            return ComprehensiveProspectPackage(
                analyzed_lead=analyzed_lead,
                enhanced_strategy=enhanced_strategy,
                enhanced_personalized_message=personalized_message_data,
                internal_briefing=internal_briefing_data,
                confidence_score=self._calculate_confidence_score(enhanced_strategy),
                roi_potential_score=self._calculate_roi_potential(enhanced_strategy),
                brazilian_market_fit=self._calculate_brazilian_fit(analyzed_lead),
                processing_metadata={"total_processing_time_seconds": total_processing_time_seconds, "company_name": company_name, "lead_id": lead_id, "run_id": run_id}
            )
        except Exception as e:
            self.logger.error(f"EnhancedLeadProcessor (Lead ID: {lead_id}): Critical error: {e}\n{traceback.format_exc()}")
            total_processing_time_seconds = (datetime.utcnow() - process_start_time_utc).total_seconds()
            return ComprehensiveProspectPackage(
                analyzed_lead=analyzed_lead,
                enhanced_strategy=EnhancedStrategy(error_message=f"Processing failed: {str(e)}"),
                enhanced_personalized_message=EnhancedPersonalizedMessage(primary_message=PersonalizedMessage(channel=CommunicationChannel.EMAIL,message_body="Error",call_to_action="N/A"), error_message=f"Processing failed: {str(e)}"),
                internal_briefing=InternalBriefing(executive_summary=f"Processing failed: {str(e)}"),
                confidence_score=0.1, roi_potential_score=0.0, brazilian_market_fit=0.0,
                processing_metadata={"total_processing_time_seconds": total_processing_time_seconds, "company_name": company_name, "lead_id": lead_id, "run_id": run_id, "error": str(e)}
            )

    async def _gather_external_intelligence(self, company_name: str, analyzed_lead: AnalyzedLead, lead_id: str) -> ExternalIntelligence:
        agent_name = TavilyEnrichmentAgent.__name__
        agent_start_time = datetime.utcnow()
        text_content = analyzed_lead.validated_lead.site_data.extracted_text_content or ""
        enrichment_input = TavilyEnrichmentInput(company_name=company_name, initial_extracted_text=text_content)
        output: Optional[TavilyEnrichmentOutput] = None
        error_msg_event = None
        status = "FAILED"
        try:
            # Agent .execute() methods are async due to BaseAgent.execute being async
            output = await self.tavily_enrichment_agent.execute(enrichment_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output and not output.error_message:
                return ExternalIntelligence(
                    tavily_enrichment=output.enriched_data,
                    market_research=f"Insights from Tavily enrichment for {company_name}.",
                    news_analysis=f"News from Tavily enrichment for {company_name}.",
                    sources_used=["Tavily API"] if output.tavily_api_called else [],
                    enrichment_confidence=0.8 if output.tavily_api_called and output.enriched_data else 0.3,
                    error_message=None # Error handled by event reporting
                )
            else: # Error in agent output
                 return ExternalIntelligence(error_message=error_msg_event or "Tavily agent failed without specific message.")

        except Exception as e:
            self.logger.error(f"Exception in _gather_external_intelligence (Lead ID: {lead_id}): {e}")
            error_msg_event = str(e)
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, error_msg_event)
            return ExternalIntelligence(error_message=error_msg_event)

    async def _extract_contact_information(self, analyzed_lead: AnalyzedLead, lead_id: str) -> ContactInformation:
        agent_name = ContactExtractionAgent.__name__
        agent_start_time = datetime.utcnow()
        text_content = analyzed_lead.validated_lead.cleaned_text_content or analyzed_lead.validated_lead.site_data.extracted_text_content or ""
        company_name = self._extract_company_name(analyzed_lead)
        extraction_input = ContactExtractionInput(extracted_text=text_content, company_name=company_name, product_service_offered=self.product_service_context)
        output: Optional[ContactExtractionOutput] = None
        error_msg_event = None
        status = "FAILED"
        try:
            output = await self.contact_extraction_agent.execute(extraction_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output and not output.error_message:
                return ContactInformation(
                    emails_found=output.emails_found,
                    instagram_profiles=output.instagram_profiles_found,
                    tavily_search_suggestions=[output.tavily_search_suggestion] if output.tavily_search_suggestion else [],
                    extraction_confidence=0.75 if output.emails_found or output.instagram_profiles_found else 0.25,
                    error_message=None
                )
            else:
                return ContactInformation(error_message=error_msg_event or "Contact extraction agent failed.")
        except Exception as e:
            self.logger.error(f"Exception in _extract_contact_information (Lead ID: {lead_id}): {e}")
            error_msg_event = str(e)
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, error_msg_event)
            return ContactInformation(error_message=error_msg_event)

    async def _analyze_pain_points(self, lead_analysis_str: str, persona_profile_str: str, company_name: str, lead_id: str) -> PainPointDeepeningOutput:
        agent_name = PainPointDeepeningAgent.__name__
        agent_start_time = datetime.utcnow()
        pain_input = PainPointDeepeningInput(
            lead_analysis=lead_analysis_str, persona_profile=persona_profile_str,
            product_service_offered=self.product_service_context, company_name=company_name
        )
        output: Optional[PainPointDeepeningOutput] = None
        error_msg_event = None
        status = "FAILED"
        try:
            output = await self.pain_point_deepening_agent.execute(pain_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output.error_message: self.logger.warning(f"PainPointDeepeningAgent (Lead ID: {lead_id}) returned: {output.error_message}")
            return output # Return agent's output directly, error or not
        except Exception as e:
            self.logger.error(f"Exception in _analyze_pain_points (Lead ID: {lead_id}): {e}")
            error_msg_event = str(e)
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, error_msg_event)
            return PainPointDeepeningOutput(error_message=error_msg_event, deepened_pain_points=[]) # Ensure correct model type

    async def _qualify_lead(self, lead_analysis_str: str, persona_profile_str: str, deepened_pain_points_str: str, lead_id: str) -> LeadQualificationOutput:
        agent_name = LeadQualificationAgent.__name__
        agent_start_time = datetime.utcnow()
        qualification_input = LeadQualificationInput(
            lead_analysis=lead_analysis_str, persona_profile=persona_profile_str,
            deepened_pain_points=deepened_pain_points_str, product_service_offered=self.product_service_context
        )
        output: Optional[LeadQualificationOutput] = None
        error_msg_event = None
        status = "FAILED"
        try:
            output = await self.lead_qualification_agent.execute(qualification_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output.error_message: self.logger.warning(f"LeadQualificationAgent (Lead ID: {lead_id}) returned: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _qualify_lead (Lead ID: {lead_id}): {e}")
            error_msg_event = str(e)
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, error_msg_event)
            return LeadQualificationOutput(error_message=error_msg_event, qualification_tier="Error", confidence_score=0.0, justification="Error in processing")

    async def _analyze_competitors(self, analyzed_lead: AnalyzedLead, lead_id: str) -> CompetitorIdentificationOutput:
        agent_name = CompetitorIdentificationAgent.__name__
        agent_start_time = datetime.utcnow()
        text_content = analyzed_lead.validated_lead.site_data.extracted_text_content or ""
        lead_product_service = ", ".join(analyzed_lead.analysis.main_services or []) or (analyzed_lead.analysis.company_description or "Serviços da empresa analisada")
        competitor_input = CompetitorIdentificationInput(
            initial_extracted_text=text_content, product_service_offered=lead_product_service,
            known_competitors_list_str=self.competitors_list
        )
        output: Optional[CompetitorIdentificationOutput] = None
        error_msg_event = None
        status = "FAILED"
        try:
            output = await self.competitor_identification_agent.execute(competitor_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output.error_message: self.logger.warning(f"CompetitorIdentificationAgent (Lead ID: {lead_id}) returned: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _analyze_competitors (Lead ID: {lead_id}): {e}")
            error_msg_event = str(e)
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, error_msg_event)
            return CompetitorIdentificationOutput(error_message=error_msg_event, identified_competitors_report="Error in processing", identified_competitors=[])

    async def _identify_purchase_triggers(self, analyzed_lead: AnalyzedLead, external_intel: Optional[ExternalIntelligence], lead_id: str) -> BuyingTriggerIdentificationOutput:
        agent_name = BuyingTriggerIdentificationAgent.__name__
        agent_start_time = datetime.utcnow()
        lead_data_dict = {
            "company_name": self._extract_company_name(analyzed_lead), "url": str(analyzed_lead.validated_lead.site_data.url),
            "description": analyzed_lead.analysis.company_description, "sector": analyzed_lead.analysis.company_sector,
            "main_services": analyzed_lead.analysis.main_services, "recent_activities_from_analysis": analyzed_lead.analysis.recent_activities,
            "extracted_text_summary": self._truncate_text(analyzed_lead.validated_lead.site_data.extracted_text_content or "", 500)
        }
        try: lead_data_str = json.dumps(lead_data_dict, ensure_ascii=False)
        except Exception as e_json:
            self.logger.warning(f"Could not serialize lead_data for BuyingTriggerIdentificationAgent (Lead ID: {lead_id}): {e_json}")
            lead_data_str = "{'error': 'Could not serialize lead data'}"

        enriched_data_str = external_intel.tavily_enrichment if external_intel and external_intel.tavily_enrichment else "Nenhuma informação de enriquecimento disponível."
        trigger_input = BuyingTriggerIdentificationInput(
            lead_data_str=lead_data_str, enriched_data=enriched_data_str, product_service_offered=self.product_service_context
        )
        output: Optional[BuyingTriggerIdentificationOutput] = None
        error_msg_event = None
        status = "FAILED"
        try:
            output = await self.buying_trigger_identification_agent.execute(trigger_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output.error_message: self.logger.warning(f"BuyingTriggerIdentificationAgent (Lead ID: {lead_id}) returned: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _identify_purchase_triggers (Lead ID: {lead_id}): {e}")
            error_msg_event = str(e)
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, error_msg_event)
            return BuyingTriggerIdentificationOutput(error_message=error_msg_event, identified_triggers_report="Error in processing", identified_triggers=[])

    async def _create_value_propositions(self, lead_analysis_str: str, persona_profile_str: str, deepened_pain_points_str: str, purchase_triggers_output: Optional[BuyingTriggerIdentificationOutput], company_name: str, lead_id: str) -> ValuePropositionCustomizationOutput:
        agent_name = ValuePropositionCustomizationAgent.__name__
        agent_start_time = datetime.utcnow()
        buying_triggers_report_str = purchase_triggers_output.model_dump_json(indent=2) if purchase_triggers_output and not purchase_triggers_output.error_message else "Relatório de gatilhos não disponível ou com erro."

        value_prop_input = ValuePropositionCustomizationInput(
            lead_analysis=lead_analysis_str, persona_profile=persona_profile_str,
            deepened_pain_points=deepened_pain_points_str, buying_triggers_report=buying_triggers_report_str,
            product_service_offered=self.product_service_context, company_name=company_name
        )
        output: Optional[ValuePropositionCustomizationOutput] = None
        error_msg_event = None
        status = "FAILED"
        try:
            output = await self.value_proposition_customization_agent.execute(value_prop_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output.error_message: self.logger.warning(f"ValuePropositionCustomizationAgent (Lead ID: {lead_id}) returned: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _create_value_propositions (Lead ID: {lead_id}): {e}")
            error_msg_event = str(e)
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, error_msg_event)
            return ValuePropositionCustomizationOutput(error_message=error_msg_event, custom_propositions=[])

    async def _generate_strategic_questions(self, lead_analysis_str: str, persona_profile_str: str, deepened_pain_points_str: str, lead_id: str) -> StrategicQuestionGenerationOutput:
        agent_name = StrategicQuestionGenerationAgent.__name__
        agent_start_time = datetime.utcnow()
        sq_input = StrategicQuestionGenerationInput(
            lead_analysis=lead_analysis_str, persona_profile=persona_profile_str, deepened_pain_points=deepened_pain_points_str
        )
        output: Optional[StrategicQuestionGenerationOutput] = None
        error_msg_event = None
        status = "FAILED"
        try:
            output = await self.strategic_question_generation_agent.execute(sq_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output.error_message: self.logger.warning(f"StrategicQuestionGenerationAgent (Lead ID: {lead_id}) returned: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _generate_strategic_questions (Lead ID: {lead_id}): {e}")
            error_msg_event = str(e)
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, error_msg_event)
            return StrategicQuestionGenerationOutput(error_message=error_msg_event, generated_questions=[])

    async def _prepare_objection_handling(self, persona_profile_str: str, company_name: str, detailed_approach_plan_text: str, lead_id: str) -> ObjectionHandlingOutput:
        agent_name = ObjectionHandlingAgent.__name__
        agent_start_time = datetime.utcnow()
        objection_input = ObjectionHandlingInput(
            detailed_approach_plan_text=detailed_approach_plan_text or "Plano de abordagem não disponível.",
            persona_profile=persona_profile_str, product_service_offered=self.product_service_context, company_name=company_name
        )
        output: Optional[ObjectionHandlingOutput] = None
        error_msg_event = None
        status = "FAILED"
        try:
            output = await self.objection_handling_agent.execute(objection_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output.error_message: self.logger.warning(f"ObjectionHandlingAgent (Lead ID: {lead_id}) returned: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _prepare_objection_handling (Lead ID: {lead_id}): {e}")
            error_msg_event = str(e)
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, error_msg_event)
            return ObjectionHandlingOutput(error_message=error_msg_event, common_objections_and_responses=[])

    async def _generate_tot_strategies(self, current_lead_summary: str, lead_id: str) -> ToTStrategyGenerationOutput:
        agent_name = ToTStrategyGenerationAgent.__name__
        agent_start_time = datetime.utcnow()
        generation_input = ToTStrategyGenerationInput(current_lead_summary=current_lead_summary, product_service_offered=self.product_service_context)
        output: Optional[ToTStrategyGenerationOutput] = None
        error_msg_event = None
        status = "FAILED"
        try:
            output = await self.tot_strategy_generation_agent.execute(generation_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output.error_message: self.logger.warning(f"ToTStrategyGenerationAgent (Lead ID: {lead_id}) failed: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in ToT strategy generation (Lead ID: {lead_id}): {e}")
            error_msg_event = str(e)
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, error_msg_event)
            return ToTStrategyGenerationOutput(error_message=error_msg_event, proposed_strategies=[])

    async def _evaluate_tot_strategies(self, generated_strategies_output: Optional[ToTStrategyGenerationOutput], current_lead_summary: str, lead_id: str) -> ToTStrategyEvaluationOutput:
        agent_name = ToTStrategyEvaluationAgent.__name__
        agent_start_time = datetime.utcnow()
        proposed_strategies_text_input = "Nenhuma estratégia proposta foi gerada."
        if generated_strategies_output and generated_strategies_output.proposed_strategies:
            proposed_strategies_text_input = ""
            for i, strat in enumerate(generated_strategies_output.proposed_strategies):
                proposed_strategies_text_input += f"Estratégia {i+1}: {strat.strategy_name}\n  Ângulo/Gancho: {strat.angle_or_hook}\n  Tom: {strat.tone_of_voice}\n  Canais: {', '.join(strat.primary_channels)}\n  Pontos Chave: {'; '.join(strat.key_points_or_arguments)}\n  Pergunta de Abertura: {strat.opening_question}\n\n"
        elif generated_strategies_output and generated_strategies_output.error_message:
             proposed_strategies_text_input = f"Erro na geração de estratégias: {generated_strategies_output.error_message}"

        evaluation_input = ToTStrategyEvaluationInput(proposed_strategies_text=proposed_strategies_text_input, current_lead_summary=current_lead_summary)
        output: Optional[ToTStrategyEvaluationOutput] = None
        error_msg_event = None
        status = "FAILED"
        try:
            output = await self.tot_strategy_evaluation_agent.execute(evaluation_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output.error_message: self.logger.warning(f"ToTStrategyEvaluationAgent (Lead ID: {lead_id}) failed: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in ToT strategy evaluation (Lead ID: {lead_id}): {e}")
            error_msg_event = str(e)
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, error_msg_event)
            return ToTStrategyEvaluationOutput(error_message=error_msg_event, evaluated_strategies=[])

    async def _synthesize_tot_action_plan(self, evaluated_strategies_output: Optional[ToTStrategyEvaluationOutput], generated_strategies_output: Optional[ToTStrategyGenerationOutput], current_lead_summary: str, lead_id: str) -> ToTActionPlanSynthesisOutput:
        agent_name = ToTActionPlanSynthesisAgent.__name__
        agent_start_time = datetime.utcnow()
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
        output: Optional[ToTActionPlanSynthesisOutput] = None
        error_msg_event = None
        status = "FAILED"
        try:
            output = await self.tot_action_plan_synthesis_agent.execute(synthesis_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output.error_message: self.logger.warning(f"ToTActionPlanSynthesisAgent (Lead ID: {lead_id}) failed: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in ToT action plan synthesis (Lead ID: {lead_id}): {e}")
            error_msg_event = str(e)
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, error_msg_event)
            return ToTActionPlanSynthesisOutput(error_message=error_msg_event, recommended_strategy_name="Error", primary_angle_hook="Error", synthesized_action_plan_steps=[])

    async def _develop_detailed_approach_plan(self, lead_analysis_str: str, persona_profile_str: str, deepened_pain_points_str: str, tot_action_plan: Optional[ToTActionPlanSynthesisOutput], lead_url:str, lead_id: str) -> DetailedApproachPlanOutput:
        agent_name = DetailedApproachPlanAgent.__name__
        agent_start_time = datetime.utcnow()
        final_action_plan_summary_for_detailed_plan = "Plano de Ação Sintetizado:\n"
        if tot_action_plan and not tot_action_plan.error_message:
            final_action_plan_summary_for_detailed_plan += f"- Estratégia Recomendada: {tot_action_plan.recommended_strategy_name}\n"
            final_action_plan_summary_for_detailed_plan += f"- Gancho Principal: {tot_action_plan.primary_angle_hook}\n"
            # ... (rest of summary for brevity, but should be more complete)
        elif tot_action_plan and tot_action_plan.error_message:
            final_action_plan_summary_for_detailed_plan = f"Erro no plano de ação sintetizado: {tot_action_plan.error_message}"
        else:
            final_action_plan_summary_for_detailed_plan = "Plano de ação sintetizado não disponível."

        plan_input = DetailedApproachPlanInput(
            lead_analysis=lead_analysis_str, persona_profile=persona_profile_str,
            deepened_pain_points=deepened_pain_points_str, final_action_plan_text=final_action_plan_summary_for_detailed_plan,
            product_service_offered=self.product_service_context, lead_url=lead_url
        )
        output: Optional[DetailedApproachPlanOutput] = None
        error_msg_event = None
        status = "FAILED"
        try:
            output = await self.detailed_approach_plan_agent.execute(plan_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output.error_message: self.logger.warning(f"DetailedApproachPlanAgent (Lead ID: {lead_id}) failed: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in detailed approach plan development (Lead ID: {lead_id}): {e}")
            error_msg_event = str(e)
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, error_msg_event)
            return DetailedApproachPlanOutput(error_message=error_msg_event, detailed_plan_steps=[])

    async def _create_personalized_message(self, analyzed_lead: AnalyzedLead, enhanced_strategy: EnhancedStrategy, contact_info: Optional[ContactInformation], persona_profile_str: str, lead_id: str) -> EnhancedPersonalizedMessage:
        agent_name = B2BPersonalizedMessageAgent.__name__
        agent_start_time = datetime.utcnow()
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
            persona_fictional_name=persona_profile_str # This should ideally be a specific name if available
        )
        output: Optional[B2BPersonalizedMessageOutput] = None
        error_msg_event = None
        status = "FAILED"
        primary_message_error_for_output = None
        try:
            output = await self.b2b_personalized_message_agent.execute(message_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            primary_message_error_for_output = error_msg_event
            if error_msg_event and not (output and output.crafted_message_body and output.crafted_message_body != "Não foi possível gerar a mensagem."):
                self.logger.warning(f"B2BPersonalizedMessageAgent (Lead ID: {lead_id}) failed: {error_msg_event}")

            channel = CommunicationChannel.EMAIL
            if output and output.crafted_message_channel and output.crafted_message_channel.upper() in CommunicationChannel.__members__:
                channel = CommunicationChannel[output.crafted_message_channel.upper()]
            elif output and output.crafted_message_channel and output.crafted_message_channel != "N/A":
                 self.logger.warning(f"Invalid channel '{output.crafted_message_channel}' from B2B agent (Lead ID: {lead_id}). Defaulting to EMAIL.")

            primary_message = PersonalizedMessage(
                channel=channel,
                subject_line=output.crafted_message_subject if output else "N/A",
                message_body=output.crafted_message_body if output else "Error",
                call_to_action=output.crafted_message_cta if output else "N/A",
                error_message=primary_message_error_for_output
            )
            return EnhancedPersonalizedMessage(primary_message=primary_message, error_message=primary_message_error_for_output)
        except Exception as e:
            self.logger.error(f"Exception in _create_personalized_message (Lead ID: {lead_id}): {e}")
            error_msg_event = str(e)
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, error_msg_event)
            primary_msg = PersonalizedMessage(channel=CommunicationChannel.EMAIL, message_body=f"Exceção: {error_msg_event}", call_to_action="N/A", error_message=error_msg_event)
            return EnhancedPersonalizedMessage(primary_message=primary_msg, error_message=error_msg_event)

    async def _create_internal_briefing(self, analyzed_lead: AnalyzedLead, enhanced_strategy: EnhancedStrategy, lead_id: str) -> InternalBriefing:
        agent_name = InternalBriefingSummaryAgent.__name__
        agent_start_time = datetime.utcnow()
        company_name = self._extract_company_name(analyzed_lead)
        analysis_obj = analyzed_lead.analysis
        # Consolidate all data for the briefing agent
        all_lead_data_dict = {
            "company_name": company_name, "lead_url": str(analyzed_lead.validated_lead.site_data.url),
            "product_service_offered_by_us": self.product_service_context,
            "initial_site_extracted_text_summary": self._truncate_text(analyzed_lead.validated_lead.site_data.extracted_text_content or "", 300),
            "lead_analysis_summary": analysis_obj.model_dump(exclude_none=True) if analysis_obj else {},
            "external_intelligence_summary": enhanced_strategy.external_intelligence.model_dump(exclude_none=True) if enhanced_strategy.external_intelligence and not enhanced_strategy.external_intelligence.error_message else {"error": enhanced_strategy.external_intelligence.error_message if enhanced_strategy.external_intelligence else "N/A"},
            "contact_information_summary": enhanced_strategy.contact_information.model_dump(exclude_none=True) if enhanced_strategy.contact_information and not enhanced_strategy.contact_information.error_message else {"error": enhanced_strategy.contact_information.error_message if enhanced_strategy.contact_information else "N/A"},
            "pain_point_analysis_summary": enhanced_strategy.pain_point_analysis.model_dump(exclude_none=True) if enhanced_strategy.pain_point_analysis and not enhanced_strategy.pain_point_analysis.error_message else {"error": enhanced_strategy.pain_point_analysis.error_message if enhanced_strategy.pain_point_analysis else "N/A"},
            "lead_qualification_summary": enhanced_strategy.lead_qualification.model_dump(exclude_none=True) if enhanced_strategy.lead_qualification and not enhanced_strategy.lead_qualification.error_message else {"error": enhanced_strategy.lead_qualification.error_message if enhanced_strategy.lead_qualification else "N/A"},
            "competitor_intelligence_summary": enhanced_strategy.competitor_intelligence.model_dump(exclude_none=True) if enhanced_strategy.competitor_intelligence and not enhanced_strategy.competitor_intelligence.error_message else {"error": enhanced_strategy.competitor_intelligence.error_message if enhanced_strategy.competitor_intelligence else "N/A"},
            "purchase_triggers_summary": enhanced_strategy.purchase_triggers.model_dump(exclude_none=True) if enhanced_strategy.purchase_triggers and not enhanced_strategy.purchase_triggers.error_message else {"error": enhanced_strategy.purchase_triggers.error_message if enhanced_strategy.purchase_triggers else "N/A"},
            "customized_value_propositions_summary": [vp.model_dump(exclude_none=True) for vp in enhanced_strategy.value_propositions or [] if not vp.error_message],
            "strategic_questions_generated": enhanced_strategy.strategic_questions or [],
            "objection_handling_summary": enhanced_strategy.objection_framework.model_dump(exclude_none=True) if enhanced_strategy.objection_framework and not enhanced_strategy.objection_framework.error_message else {"error": enhanced_strategy.objection_framework.error_message if enhanced_strategy.objection_framework else "N/A"},
            "tot_synthesized_action_plan_summary": enhanced_strategy.tot_synthesized_action_plan.model_dump(exclude_none=True) if enhanced_strategy.tot_synthesized_action_plan and not enhanced_strategy.tot_synthesized_action_plan.error_message else {"error": enhanced_strategy.tot_synthesized_action_plan.error_message if enhanced_strategy.tot_synthesized_action_plan else "N/A"},
            "detailed_approach_plan_summary": enhanced_strategy.detailed_approach_plan.model_dump(exclude_none=True) if enhanced_strategy.detailed_approach_plan and not enhanced_strategy.detailed_approach_plan.error_message else {"error": enhanced_strategy.detailed_approach_plan.error_message if enhanced_strategy.detailed_approach_plan else "N/A"},
        }
        briefing_input = InternalBriefingSummaryInput(all_lead_data=all_lead_data_dict)
        output: Optional[InternalBriefingSummaryOutput] = None
        error_msg_event = None
        status = "FAILED"
        try:
            output = await self.internal_briefing_summary_agent.execute(briefing_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output and not output.error_message:
                return InternalBriefing(
                    executive_summary=output.executive_summary,
                    lead_overview=InternalBriefingSectionSchema(**output.lead_overview.model_dump()) if output.lead_overview else None,
                    persona_profile_summary=InternalBriefingSectionSchema(**output.persona_profile_summary.model_dump()) if output.persona_profile_summary else None,
                    pain_points_and_needs=InternalBriefingSectionSchema(**output.pain_points_and_needs.model_dump()) if output.pain_points_and_needs else None,
                    buying_triggers_opportunity=InternalBriefingSectionSchema(**output.buying_triggers_opportunity.model_dump()) if output.buying_triggers_opportunity else None,
                    lead_qualification_summary=InternalBriefingSectionSchema(**output.lead_qualification_summary.model_dump()) if output.lead_qualification_summary else None,
                    approach_strategy_summary=InternalBriefingSectionSchema(**output.approach_strategy_summary.model_dump()) if output.approach_strategy_summary else None,
                    custom_value_proposition_summary=InternalBriefingSectionSchema(**output.custom_value_proposition_summary.model_dump()) if output.custom_value_proposition_summary else None,
                    potential_objections_summary=InternalBriefingSectionSchema(**output.potential_objections_summary.model_dump()) if output.potential_objections_summary else None,
                    recommended_next_step=output.recommended_next_step,
                    error_message=None
                )
            else: # Error in agent output
                err_msg = error_msg_event or "Internal briefing agent failed."
                self.logger.warning(f"InternalBriefingSummaryAgent (Lead ID: {lead_id}) returned an error: {err_msg}")
                return InternalBriefing(executive_summary=f"Falha: {err_msg}", error_message=err_msg)
        except Exception as e:
            self.logger.error(f"Exception in _create_internal_briefing (Lead ID: {lead_id}): {e}")
            error_msg_event = str(e)
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, error_msg_event)
            return InternalBriefing(executive_summary=f"Exceção: {error_msg_event}", error_message=error_msg_event)

    def _extract_company_name(self, analyzed_lead: AnalyzedLead) -> str:
        site_data = analyzed_lead.validated_lead.site_data
            # No specific error message for the final ExternalIntelligence object if agent error was already reported.
            # The error_message field in ExternalIntelligence can be used for issues *within* this helper,
            # not for propagating agent errors that are already sent to MCP.
            # However, for robustness, if the agent output itself has an error, we might want to reflect that
            # in the returned object if it influences further local processing.
            # For now, if agent had error, we return an ExternalIntelligence object with its own error_message.
            # This is a design choice: does the main `process` loop expect error info in these objects,
            # or only rely on what's sent to MCP? Assuming it needs some indication.
            # The `error_message=None` in the success case implies errors are exceptional.
            # If output has an error, the returned ExternalIntelligence should reflect that.
            # The `output.error_message` is already captured in `error_msg_event`.
            # So, the returned object can have `error_message=error_msg_event`.
            # This will be consistent.
            if output and not output.error_message:
                 return ExternalIntelligence(
                    tavily_enrichment=output.enriched_data,
                    market_research=f"Insights from Tavily enrichment for {company_name}.",
                    news_analysis=f"News from Tavily enrichment for {company_name}.",
                    sources_used=["Tavily API"] if output.tavily_api_called else [],
                    enrichment_confidence=0.8 if output.tavily_api_called and output.enriched_data else 0.3,
                    error_message=None # No error in this specific transformation
                )
            else: # Agent itself had an issue or returned an error
                return ExternalIntelligence(error_message=error_msg_event or "Tavily agent processing failed.") # Return with error message

        except Exception as e: # This is for exceptions during the _gather_external_intelligence helper itself
            self.logger.error(f"Exception in _gather_external_intelligence (Lead ID: {lead_id}): {e}\n{traceback.format_exc()}")
            # Report unexpected error in this helper
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, str(e))
            return ExternalIntelligence(error_message=str(e)) # Populate error message of the returned object

    async def _extract_contact_information(self, analyzed_lead: AnalyzedLead, lead_id: str) -> ContactInformation:
        agent_name = ContactExtractionAgent.__name__
        agent_start_time = datetime.utcnow()
        text_content = analyzed_lead.validated_lead.cleaned_text_content or analyzed_lead.validated_lead.site_data.extracted_text_content or ""
        company_name = self._extract_company_name(analyzed_lead)
        extraction_input = ContactExtractionInput(extracted_text=text_content, company_name=company_name, product_service_offered=self.product_service_context)
        output: Optional[ContactExtractionOutput] = None
        error_msg_event = None
        try:
            output = await self.contact_extraction_agent.execute(extraction_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output and not output.error_message:
                return ContactInformation(
                    emails_found=output.emails_found,
                    instagram_profiles=output.instagram_profiles_found,
                    tavily_search_suggestions=[output.tavily_search_suggestion] if output.tavily_search_suggestion else [],
                    extraction_confidence=0.75 if output.emails_found or output.instagram_profiles_found else 0.25,
                    error_message=None
                )
            else:
                return ContactInformation(error_message=error_msg_event or "Contact extraction agent failed.")
        except Exception as e:
            self.logger.error(f"Exception in _extract_contact_information (Lead ID: {lead_id}): {e}\n{traceback.format_exc()}")
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, str(e))
            return ContactInformation(error_message=str(e))

    async def _analyze_pain_points(self, lead_analysis_str: str, persona_profile_str: str, company_name: str, lead_id: str) -> PainPointDeepeningOutput:
        agent_name = PainPointDeepeningAgent.__name__
        agent_start_time = datetime.utcnow()
        pain_input = PainPointDeepeningInput(
            lead_analysis=lead_analysis_str, persona_profile=persona_profile_str,
            product_service_offered=self.product_service_context, company_name=company_name
        )
        output: Optional[PainPointDeepeningOutput] = None
        error_msg_event = None
        try:
            output = await self.pain_point_deepening_agent.execute(pain_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output.error_message: self.logger.warning(f"PainPointDeepeningAgent (Lead ID: {lead_id}) returned error: {output.error_message}")
            return output # Return agent's output directly
        except Exception as e:
            self.logger.error(f"Exception in _analyze_pain_points (Lead ID: {lead_id}): {e}\n{traceback.format_exc()}")
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, str(e))
            return PainPointDeepeningOutput(error_message=str(e), deepened_pain_points=[])

    async def _qualify_lead(self, lead_analysis_str: str, persona_profile_str: str, deepened_pain_points_str: str, lead_id: str) -> LeadQualificationOutput:
        agent_name = LeadQualificationAgent.__name__
        agent_start_time = datetime.utcnow()
        qualification_input = LeadQualificationInput(
            lead_analysis=lead_analysis_str, persona_profile=persona_profile_str,
            deepened_pain_points=deepened_pain_points_str, product_service_offered=self.product_service_context
        )
        output: Optional[LeadQualificationOutput] = None
        error_msg_event = None
        try:
            output = await self.lead_qualification_agent.execute(qualification_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output.error_message: self.logger.warning(f"LeadQualificationAgent (Lead ID: {lead_id}) returned error: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _qualify_lead (Lead ID: {lead_id}): {e}\n{traceback.format_exc()}")
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, str(e))
            return LeadQualificationOutput(error_message=str(e), qualification_tier="Error", confidence_score=0.0, justification="Error in processing")

    async def _analyze_competitors(self, analyzed_lead: AnalyzedLead, lead_id: str) -> CompetitorIdentificationOutput:
        agent_name = CompetitorIdentificationAgent.__name__
        agent_start_time = datetime.utcnow()
        text_content = analyzed_lead.validated_lead.site_data.extracted_text_content or ""
        lead_product_service = ", ".join(analyzed_lead.analysis.main_services or []) or (analyzed_lead.analysis.company_description or "Serviços da empresa analisada")
        competitor_input = CompetitorIdentificationInput(
            initial_extracted_text=text_content, product_service_offered=lead_product_service,
            known_competitors_list_str=self.competitors_list
        )
        output: Optional[CompetitorIdentificationOutput] = None
        error_msg_event = None
        try:
            output = await self.competitor_identification_agent.execute(competitor_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output.error_message: self.logger.warning(f"CompetitorIdentificationAgent (Lead ID: {lead_id}) returned error: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _analyze_competitors (Lead ID: {lead_id}): {e}\n{traceback.format_exc()}")
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, str(e))
            return CompetitorIdentificationOutput(error_message=str(e), identified_competitors_report="Error in processing", identified_competitors=[])

    async def _identify_purchase_triggers(self, analyzed_lead: AnalyzedLead, external_intel: Optional[ExternalIntelligence], lead_id: str) -> BuyingTriggerIdentificationOutput:
        agent_name = BuyingTriggerIdentificationAgent.__name__
        agent_start_time = datetime.utcnow()
        lead_data_dict = {
            "company_name": self._extract_company_name(analyzed_lead), "url": str(analyzed_lead.validated_lead.site_data.url),
            "description": analyzed_lead.analysis.company_description, "sector": analyzed_lead.analysis.company_sector,
            "main_services": analyzed_lead.analysis.main_services, "recent_activities_from_analysis": analyzed_lead.analysis.recent_activities,
            "extracted_text_summary": self._truncate_text(analyzed_lead.validated_lead.site_data.extracted_text_content or "", 500)
        }
        try: lead_data_str = json.dumps(lead_data_dict, ensure_ascii=False)
        except Exception as e_json:
            self.logger.warning(f"Could not serialize lead_data for BuyingTriggerIdentificationAgent (Lead ID: {lead_id}): {e_json}")
            lead_data_str = "{'error': 'Could not serialize lead data'}"

        enriched_data_str = external_intel.tavily_enrichment if external_intel and external_intel.tavily_enrichment else "Nenhuma informação de enriquecimento disponível."
        trigger_input = BuyingTriggerIdentificationInput(
            lead_data_str=lead_data_str, enriched_data=enriched_data_str, product_service_offered=self.product_service_context
        )
        output: Optional[BuyingTriggerIdentificationOutput] = None
        error_msg_event = None
        try:
            output = await self.buying_trigger_identification_agent.execute(trigger_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output.error_message: self.logger.warning(f"BuyingTriggerIdentificationAgent (Lead ID: {lead_id}) returned error: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _identify_purchase_triggers (Lead ID: {lead_id}): {e}\n{traceback.format_exc()}")
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, str(e))
            return BuyingTriggerIdentificationOutput(error_message=str(e), identified_triggers_report="Error in processing", identified_triggers=[])

    async def _create_value_propositions(self, lead_analysis_str: str, persona_profile_str: str, deepened_pain_points_str: str, purchase_triggers_output: Optional[BuyingTriggerIdentificationOutput], company_name: str, lead_id: str) -> ValuePropositionCustomizationOutput:
        agent_name = ValuePropositionCustomizationAgent.__name__
        agent_start_time = datetime.utcnow()
        buying_triggers_report_str = purchase_triggers_output.model_dump_json(indent=2) if purchase_triggers_output and not purchase_triggers_output.error_message else "Relatório de gatilhos não disponível ou com erro."

        value_prop_input = ValuePropositionCustomizationInput(
            lead_analysis=lead_analysis_str, persona_profile=persona_profile_str,
            deepened_pain_points=deepened_pain_points_str, buying_triggers_report=buying_triggers_report_str,
            product_service_offered=self.product_service_context, company_name=company_name
        )
        output: Optional[ValuePropositionCustomizationOutput] = None
        error_msg_event = None
        try:
            output = await self.value_proposition_customization_agent.execute(value_prop_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output.error_message: self.logger.warning(f"ValuePropositionCustomizationAgent (Lead ID: {lead_id}) returned error: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _create_value_propositions (Lead ID: {lead_id}): {e}\n{traceback.format_exc()}")
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, str(e))
            return ValuePropositionCustomizationOutput(error_message=str(e), custom_propositions=[])

    async def _generate_strategic_questions(self, lead_analysis_str: str, persona_profile_str: str, deepened_pain_points_str: str, lead_id: str) -> StrategicQuestionGenerationOutput:
        agent_name = StrategicQuestionGenerationAgent.__name__
        agent_start_time = datetime.utcnow()
        sq_input = StrategicQuestionGenerationInput(
            lead_analysis=lead_analysis_str, persona_profile=persona_profile_str, deepened_pain_points=deepened_pain_points_str
        )
        output: Optional[StrategicQuestionGenerationOutput] = None
        error_msg_event = None
        try:
            output = await self.strategic_question_generation_agent.execute(sq_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output.error_message: self.logger.warning(f"StrategicQuestionGenerationAgent (Lead ID: {lead_id}) returned error: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _generate_strategic_questions (Lead ID: {lead_id}): {e}\n{traceback.format_exc()}")
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, str(e))
            return StrategicQuestionGenerationOutput(error_message=str(e), generated_questions=[])

    async def _prepare_objection_handling(self, persona_profile_str: str, company_name: str, detailed_approach_plan_text: str, lead_id: str) -> ObjectionHandlingOutput:
        agent_name = ObjectionHandlingAgent.__name__
        agent_start_time = datetime.utcnow()
        objection_input = ObjectionHandlingInput(
            detailed_approach_plan_text=detailed_approach_plan_text or "Plano de abordagem não disponível.",
            persona_profile=persona_profile_str, product_service_offered=self.product_service_context, company_name=company_name
        )
        output: Optional[ObjectionHandlingOutput] = None
        error_msg_event = None
        try:
            output = await self.objection_handling_agent.execute(objection_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output.error_message: self.logger.warning(f"ObjectionHandlingAgent (Lead ID: {lead_id}) returned error: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _prepare_objection_handling (Lead ID: {lead_id}): {e}\n{traceback.format_exc()}")
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, str(e))
            return ObjectionHandlingOutput(error_message=str(e), common_objections_and_responses=[])
    
    async def _generate_tot_strategies(self, current_lead_summary: str, lead_id: str) -> ToTStrategyGenerationOutput:
        agent_name = ToTStrategyGenerationAgent.__name__
        agent_start_time = datetime.utcnow()
        generation_input = ToTStrategyGenerationInput(current_lead_summary=current_lead_summary, product_service_offered=self.product_service_context)
        output: Optional[ToTStrategyGenerationOutput] = None
        error_msg_event = None
        try:
            output = await self.tot_strategy_generation_agent.execute(generation_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output.error_message: self.logger.warning(f"ToTStrategyGenerationAgent (Lead ID: {lead_id}) failed: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in ToT strategy generation (Lead ID: {lead_id}): {e}\n{traceback.format_exc()}")
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, str(e))
            return ToTStrategyGenerationOutput(error_message=str(e), proposed_strategies=[])

    async def _evaluate_tot_strategies(self, generated_strategies_output: Optional[ToTStrategyGenerationOutput], current_lead_summary: str, lead_id: str) -> ToTStrategyEvaluationOutput:
        agent_name = ToTStrategyEvaluationAgent.__name__
        agent_start_time = datetime.utcnow()
        proposed_strategies_text_input = "Nenhuma estratégia proposta foi gerada."
        if generated_strategies_output and generated_strategies_output.proposed_strategies:
            proposed_strategies_text_input = ""
            for i, strat in enumerate(generated_strategies_output.proposed_strategies):
                proposed_strategies_text_input += f"Estratégia {i+1}: {strat.strategy_name}\n  Ângulo/Gancho: {strat.angle_or_hook}\n  Tom: {strat.tone_of_voice}\n  Canais: {', '.join(strat.primary_channels)}\n  Pontos Chave: {'; '.join(strat.key_points_or_arguments)}\n  Pergunta de Abertura: {strat.opening_question}\n\n"
        elif generated_strategies_output and generated_strategies_output.error_message:
             proposed_strategies_text_input = f"Erro na geração de estratégias: {generated_strategies_output.error_message}"

        evaluation_input = ToTStrategyEvaluationInput(proposed_strategies_text=proposed_strategies_text_input, current_lead_summary=current_lead_summary)
        output: Optional[ToTStrategyEvaluationOutput] = None
        error_msg_event = None
        try:
            output = await self.tot_strategy_evaluation_agent.execute(evaluation_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output.error_message: self.logger.warning(f"ToTStrategyEvaluationAgent (Lead ID: {lead_id}) failed: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in ToT strategy evaluation (Lead ID: {lead_id}): {e}\n{traceback.format_exc()}")
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, str(e))
            return ToTStrategyEvaluationOutput(error_message=str(e), evaluated_strategies=[])

    async def _synthesize_tot_action_plan(self, evaluated_strategies_output: Optional[ToTStrategyEvaluationOutput], generated_strategies_output: Optional[ToTStrategyGenerationOutput], current_lead_summary: str, lead_id: str) -> ToTActionPlanSynthesisOutput:
        agent_name = ToTActionPlanSynthesisAgent.__name__
        agent_start_time = datetime.utcnow()
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
        output: Optional[ToTActionPlanSynthesisOutput] = None
        error_msg_event = None
        try:
            output = await self.tot_action_plan_synthesis_agent.execute(synthesis_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output.error_message: self.logger.warning(f"ToTActionPlanSynthesisAgent (Lead ID: {lead_id}) failed: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in ToT action plan synthesis (Lead ID: {lead_id}): {e}\n{traceback.format_exc()}")
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, str(e))
            return ToTActionPlanSynthesisOutput(error_message=str(e), recommended_strategy_name="Error", primary_angle_hook="Error", synthesized_action_plan_steps=[])

    async def _develop_detailed_approach_plan(self, lead_analysis_str: str, persona_profile_str: str, deepened_pain_points_str: str, tot_action_plan: Optional[ToTActionPlanSynthesisOutput], lead_url:str, lead_id: str) -> DetailedApproachPlanOutput:
        agent_name = DetailedApproachPlanAgent.__name__
        agent_start_time = datetime.utcnow()
        final_action_plan_summary_for_detailed_plan = "Plano de Ação Sintetizado:\n"
        if tot_action_plan and not tot_action_plan.error_message:
            final_action_plan_summary_for_detailed_plan += f"- Estratégia Recomendada: {tot_action_plan.recommended_strategy_name}\n"
            final_action_plan_summary_for_detailed_plan += f"- Gancho Principal: {tot_action_plan.primary_angle_hook}\n"
        elif tot_action_plan and tot_action_plan.error_message:
            final_action_plan_summary_for_detailed_plan = f"Erro no plano de ação sintetizado: {tot_action_plan.error_message}"
        else:
            final_action_plan_summary_for_detailed_plan = "Plano de ação sintetizado não disponível."

        plan_input = DetailedApproachPlanInput(
            lead_analysis=lead_analysis_str, persona_profile=persona_profile_str,
            deepened_pain_points=deepened_pain_points_str, final_action_plan_text=final_action_plan_summary_for_detailed_plan,
            product_service_offered=self.product_service_context, lead_url=lead_url
        )
        output: Optional[DetailedApproachPlanOutput] = None
        error_msg_event = None
        try:
            output = await self.detailed_approach_plan_agent.execute(plan_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output.error_message: self.logger.warning(f"DetailedApproachPlanAgent (Lead ID: {lead_id}) failed: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in detailed approach plan development (Lead ID: {lead_id}): {e}\n{traceback.format_exc()}")
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, str(e))
            return DetailedApproachPlanOutput(error_message=str(e), detailed_plan_steps=[])
    
    async def _create_personalized_message(self, analyzed_lead: AnalyzedLead, enhanced_strategy: EnhancedStrategy, contact_info: Optional[ContactInformation], persona_profile_str: str, lead_id: str) -> EnhancedPersonalizedMessage:
        agent_name = B2BPersonalizedMessageAgent.__name__
        agent_start_time = datetime.utcnow()
        company_name = self._extract_company_name(analyzed_lead)
        final_action_plan_summary = "Plano de Ação Chave:\n"
        if enhanced_strategy.tot_synthesized_action_plan and not enhanced_strategy.tot_synthesized_action_plan.error_message:
            plan = enhanced_strategy.tot_synthesized_action_plan
            final_action_plan_summary += f"- Estratégia: {plan.recommended_strategy_name}\n"
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
        output: Optional[B2BPersonalizedMessageOutput] = None
        error_msg_event = None
        primary_message_error_for_output = None # Specific to this helper's return structure
        try:
            output = await self.b2b_personalized_message_agent.execute(message_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            primary_message_error_for_output = error_msg_event # Use the agent's error for the returned object
            if error_msg_event: self.logger.warning(f"B2BPersonalizedMessageAgent (Lead ID: {lead_id}) failed: {error_msg_event}")

            channel = CommunicationChannel.EMAIL
            if output and output.crafted_message_channel and output.crafted_message_channel.upper() in CommunicationChannel.__members__:
                channel = CommunicationChannel[output.crafted_message_channel.upper()]
            elif output and output.crafted_message_channel and output.crafted_message_channel != "N/A":
                 self.logger.warning(f"Invalid channel '{output.crafted_message_channel}' from B2B agent (Lead ID: {lead_id}). Defaulting to EMAIL.")

            primary_message = PersonalizedMessage(
                channel=channel,
                subject_line=output.crafted_message_subject if output else "N/A",
                message_body=output.crafted_message_body if output else "Error",
                call_to_action=output.crafted_message_cta if output else "N/A",
                error_message=primary_message_error_for_output # This reflects if the message crafting itself had an issue
            )
            return EnhancedPersonalizedMessage(primary_message=primary_message, error_message=primary_message_error_for_output) # Overall error for EnhancedPersonalizedMessage
        except Exception as e:
            self.logger.error(f"Exception in _create_personalized_message (Lead ID: {lead_id}): {e}\n{traceback.format_exc()}")
            error_msg_event = str(e)
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, error_msg_event)
            primary_msg = PersonalizedMessage(channel=CommunicationChannel.EMAIL, message_body=f"Exceção: {error_msg_event}", call_to_action="N/A", error_message=error_msg_event)
            return EnhancedPersonalizedMessage(primary_message=primary_msg, error_message=error_msg_event)

    async def _create_internal_briefing(self, analyzed_lead: AnalyzedLead, enhanced_strategy: EnhancedStrategy, lead_id: str) -> InternalBriefing:
        agent_name = InternalBriefingSummaryAgent.__name__
        agent_start_time = datetime.utcnow()
        company_name = self._extract_company_name(analyzed_lead)
        analysis_obj = analyzed_lead.analysis
        all_lead_data_dict = {
            "company_name": company_name, "lead_url": str(analyzed_lead.validated_lead.site_data.url),
            "product_service_offered_by_us": self.product_service_context,
            "initial_site_extracted_text_summary": self._truncate_text(analyzed_lead.validated_lead.site_data.extracted_text_content or "", 300),
            "lead_analysis_summary": analysis_obj.model_dump(exclude_none=True) if analysis_obj else {},
            "external_intelligence_summary": enhanced_strategy.external_intelligence.model_dump(exclude_none=True) if enhanced_strategy.external_intelligence and not enhanced_strategy.external_intelligence.error_message else {"error": enhanced_strategy.external_intelligence.error_message if enhanced_strategy.external_intelligence else "N/A"},
            "contact_information_summary": enhanced_strategy.contact_information.model_dump(exclude_none=True) if enhanced_strategy.contact_information and not enhanced_strategy.contact_information.error_message else {"error": enhanced_strategy.contact_information.error_message if enhanced_strategy.contact_information else "N/A"},
            "pain_point_analysis_summary": enhanced_strategy.pain_point_analysis.model_dump(exclude_none=True) if enhanced_strategy.pain_point_analysis and not enhanced_strategy.pain_point_analysis.error_message else {"error": enhanced_strategy.pain_point_analysis.error_message if enhanced_strategy.pain_point_analysis else "N/A"},
            "lead_qualification_summary": enhanced_strategy.lead_qualification.model_dump(exclude_none=True) if enhanced_strategy.lead_qualification and not enhanced_strategy.lead_qualification.error_message else {"error": enhanced_strategy.lead_qualification.error_message if enhanced_strategy.lead_qualification else "N/A"},
            "competitor_intelligence_summary": enhanced_strategy.competitor_intelligence.model_dump(exclude_none=True) if enhanced_strategy.competitor_intelligence and not enhanced_strategy.competitor_intelligence.error_message else {"error": enhanced_strategy.competitor_intelligence.error_message if enhanced_strategy.competitor_intelligence else "N/A"},
            "purchase_triggers_summary": enhanced_strategy.purchase_triggers.model_dump(exclude_none=True) if enhanced_strategy.purchase_triggers and not enhanced_strategy.purchase_triggers.error_message else {"error": enhanced_strategy.purchase_triggers.error_message if enhanced_strategy.purchase_triggers else "N/A"},
            "customized_value_propositions_summary": [vp.model_dump(exclude_none=True) for vp in enhanced_strategy.value_propositions or [] if not vp.error_message],
            "strategic_questions_generated": enhanced_strategy.strategic_questions or [],
            "objection_handling_summary": enhanced_strategy.objection_framework.model_dump(exclude_none=True) if enhanced_strategy.objection_framework and not enhanced_strategy.objection_framework.error_message else {"error": enhanced_strategy.objection_framework.error_message if enhanced_strategy.objection_framework else "N/A"},
            "tot_synthesized_action_plan_summary": enhanced_strategy.tot_synthesized_action_plan.model_dump(exclude_none=True) if enhanced_strategy.tot_synthesized_action_plan and not enhanced_strategy.tot_synthesized_action_plan.error_message else {"error": enhanced_strategy.tot_synthesized_action_plan.error_message if enhanced_strategy.tot_synthesized_action_plan else "N/A"},
            "detailed_approach_plan_summary": enhanced_strategy.detailed_approach_plan.model_dump(exclude_none=True) if enhanced_strategy.detailed_approach_plan and not enhanced_strategy.detailed_approach_plan.error_message else {"error": enhanced_strategy.detailed_approach_plan.error_message if enhanced_strategy.detailed_approach_plan else "N/A"},
        }
        briefing_input = InternalBriefingSummaryInput(all_lead_data=all_lead_data_dict)
        output: Optional[InternalBriefingSummaryOutput] = None
        error_msg_event = None
        try:
            output = await self.internal_briefing_summary_agent.execute(briefing_input)
            error_msg_event = output.error_message if output and output.error_message else None
            status = "FAILED" if error_msg_event else "SUCCESS"
            self._report_agent_event_to_mcp(lead_id, agent_name, status, agent_start_time, datetime.utcnow(), output, error_msg_event)

            if output and not output.error_message:
                # Map all sections carefully
                return InternalBriefing(
                    executive_summary=output.executive_summary,
                    lead_overview=InternalBriefingSectionSchema(**output.lead_overview.model_dump()) if output.lead_overview else None,
                    persona_profile_summary=InternalBriefingSectionSchema(**output.persona_profile_summary.model_dump()) if output.persona_profile_summary else None,
                    pain_points_and_needs=InternalBriefingSectionSchema(**output.pain_points_and_needs.model_dump()) if output.pain_points_and_needs else None,
                    buying_triggers_opportunity=InternalBriefingSectionSchema(**output.buying_triggers_opportunity.model_dump()) if output.buying_triggers_opportunity else None,
                    lead_qualification_summary=InternalBriefingSectionSchema(**output.lead_qualification_summary.model_dump()) if output.lead_qualification_summary else None,
                    approach_strategy_summary=InternalBriefingSectionSchema(**output.approach_strategy_summary.model_dump()) if output.approach_strategy_summary else None,
                    custom_value_proposition_summary=InternalBriefingSectionSchema(**output.custom_value_proposition_summary.model_dump()) if output.custom_value_proposition_summary else None,
                    potential_objections_summary=InternalBriefingSectionSchema(**output.potential_objections_summary.model_dump()) if output.potential_objections_summary else None,
                    recommended_next_step=output.recommended_next_step,
                    error_message=None
                )
            else:
                err_msg = error_msg_event or "Internal briefing agent failed."
                self.logger.warning(f"InternalBriefingSummaryAgent (Lead ID: {lead_id}) returned an error: {err_msg}")
                return InternalBriefing(executive_summary=f"Falha: {err_msg}", error_message=err_msg)
        except Exception as e:
            self.logger.error(f"Exception in _create_internal_briefing (Lead ID: {lead_id}): {e}\n{traceback.format_exc()}")
            error_msg_event = str(e)
            self._report_agent_event_to_mcp(lead_id, agent_name, "FAILED", agent_start_time, datetime.utcnow(), output, error_msg_event)
            return InternalBriefing(executive_summary=f"Exceção: {error_msg_event}", error_message=error_msg_event)
    
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
