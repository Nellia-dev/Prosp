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

from data_models.lead_structures import (
    AnalyzedLead,
    LeadAnalysis, # Added LeadAnalysis
    ComprehensiveProspectPackage,
    ContactInformation,
    ExternalIntelligence,
    PainPointAnalysis, # Expects DetailedPainPointSchema
    LeadQualification,
    CompetitorIntelligence, # Expects CompetitorDetailSchema
    PurchaseTriggers, # Expects IdentifiedTriggerSchema
    EnhancedStrategy,
    ValueProposition, # Redefined to match CustomValuePropModelSchema
    ObjectionFramework, # Expects ObjectionResponseModelSchema
    EnhancedPersonalizedMessage,
    PersonalizedMessage,
    InternalBriefing, # Redefined to use InternalBriefingSectionSchema
    CommunicationChannel,
    # --- Schemas from lead_structures.py that map to Agent Outputs ---
    DetailedPainPointSchema,
    CompetitorDetailSchema,
    IdentifiedTriggerSchema,
    ToTStrategyOptionModel, # Was ToTStrategyOption in lead_structures, but agent uses ToTStrategyOptionModel
    EvaluatedStrategyModel,
    ActionPlanStepModel,
    ToTActionPlanSynthesisModel,
    ContactStepDetailSchema, # Renamed from ContactStepDetail in agent for clarity
    DetailedApproachPlanModel, # Was DetailedApproachPlanOutput in agent, using Model for consistency
    ObjectionResponseModelSchema, # Was ObjectionResponseModel in agent
    InternalBriefingSectionSchema, # Was InternalBriefingSection in agent
)
from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# New Agent Imports
from .tavily_enrichment_agent import TavilyEnrichmentAgent, TavilyEnrichmentInput, TavilyEnrichmentOutput
from .contact_extraction_agent import ContactExtractionAgent, ContactExtractionInput, ContactExtractionOutput
from .pain_point_deepening_agent import PainPointDeepeningAgent, PainPointDeepeningInput, PainPointDeepeningOutput # Output has DetailedPainPoint
from .lead_qualification_agent import LeadQualificationAgent, LeadQualificationInput, LeadQualificationOutput
from .competitor_identification_agent import CompetitorIdentificationAgent, CompetitorIdentificationInput, CompetitorIdentificationOutput # Output has CompetitorDetail
from .strategic_question_generation_agent import StrategicQuestionGenerationAgent, StrategicQuestionGenerationInput, StrategicQuestionGenerationOutput
from .buying_trigger_identification_agent import BuyingTriggerIdentificationAgent, BuyingTriggerIdentificationInput, BuyingTriggerIdentificationOutput # Output has IdentifiedTrigger
from .tot_strategy_generation_agent import ToTStrategyGenerationAgent, ToTStrategyGenerationInput, ToTStrategyGenerationOutput # Output has ToTStrategyOptionModel
from .tot_strategy_evaluation_agent import ToTStrategyEvaluationAgent, ToTStrategyEvaluationInput, ToTStrategyEvaluationOutput # Output has EvaluatedStrategyModel
from .tot_action_plan_synthesis_agent import ToTActionPlanSynthesisAgent, ToTActionPlanSynthesisInput, ToTActionPlanSynthesisOutput # Output is ToTActionPlanSynthesisModel (structure)
from .detailed_approach_plan_agent import DetailedApproachPlanAgent, DetailedApproachPlanInput, DetailedApproachPlanOutput # Output is DetailedApproachPlanModel (structure)
from .objection_handling_agent import ObjectionHandlingAgent, ObjectionHandlingInput, ObjectionHandlingOutput # Output has ObjectionResponseModel
from .value_proposition_customization_agent import ValuePropositionCustomizationAgent, ValuePropositionCustomizationInput, ValuePropositionCustomizationOutput # Output has CustomValuePropModel
from .b2b_personalized_message_agent import B2BPersonalizedMessageAgent, B2BPersonalizedMessageInput, B2BPersonalizedMessageOutput, ContactDetailsInput as B2BContactDetailsInput
from .internal_briefing_summary_agent import InternalBriefingSummaryAgent, InternalBriefingSummaryInput, InternalBriefingSummaryOutput # Output has InternalBriefingSection

from .content_marketing_agent import ContentMarketingAgent, ContentMarketingInput
from data_models.content_marketing_models import ContentMarketingOutput as ContentMarketingOutputModel


class EnhancedLeadProcessor(BaseAgent[AnalyzedLead, ComprehensiveProspectPackage]):
    def __init__(
        self,
        llm_client: LLMClientBase,
        product_service_context: str = "",
        competitors_list: str = "",
        tavily_api_key: Optional[str] = None,
        temperature: float = 0.7 # Keep temperature here for config
    ):
        config = {}
        if temperature is not None: # Ensure temperature is explicitly passed before adding to config
            config["temperature"] = temperature

        super().__init__(
            name="Enhanced Lead Processor",
            description="Orchestrates a comprehensive lead processing pipeline involving multiple specialized agents.",
            llm_client=llm_client,
            config=config if config else None # Pass config only if it has entries
        )
        # self.agent_name = "EnhancedLeadProcessor" # BaseAgent will set self.name
        self.logger = logger # logger is imported from loguru
        
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
        self.content_marketing_agent = ContentMarketingAgent(llm_client=self.llm_client)
        
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

    def process(self, analyzed_lead: AnalyzedLead) -> ComprehensiveProspectPackage:
        start_time = time.time()
        url = str(analyzed_lead.validated_lead.site_data.url)
        company_name = self._extract_company_name(analyzed_lead)
        self.logger.info(f"Enhanced processing for: {url}")

        # Prepare common inputs
        analysis_obj = analyzed_lead.analysis
        persona_profile_str = self._construct_persona_profile_string(analysis_obj, company_name)

        try:
            external_intel = self._gather_external_intelligence(company_name, analyzed_lead)
            contact_info = self._extract_contact_information(analyzed_lead)
            
            lead_analysis_str_for_agents = self._construct_lead_analysis_string(analysis_obj, external_intel)
            
            pain_analysis_output = self._analyze_pain_points(lead_analysis_str_for_agents, persona_profile_str, company_name)
            
            # Use the structured pain_analysis_output for deepened_pain_points_str
            deepened_pain_points_for_agents = json.dumps(pain_analysis_output.model_dump(), ensure_ascii=False) if pain_analysis_output and not pain_analysis_output.error_message else "Análise de dores não disponível ou com erro."

            qualification_output = self._qualify_lead(lead_analysis_str_for_agents, persona_profile_str, deepened_pain_points_for_agents)
            competitor_intel_output = self._analyze_competitors(analyzed_lead)
            purchase_triggers_output = self._identify_purchase_triggers(analyzed_lead, external_intel)
            
            value_props_list = self._create_value_propositions(
                lead_analysis_str_for_agents, 
                persona_profile_str, 
                deepened_pain_points_for_agents, 
                purchase_triggers_output, # Pass the object
                company_name
            )
            strategic_questions_list = self._generate_strategic_questions(lead_analysis_str_for_agents, persona_profile_str, deepened_pain_points_for_agents)

            current_lead_summary_for_tot = (
                f"Empresa: {company_name} ({url})\nSetor: {analysis_obj.company_sector}\n"
                f"Serviços Principais: {', '.join(analysis_obj.main_services)}\n"
                f"Persona (Estimada): {persona_profile_str}\n"
                f"Dores Primárias (Resumo): {pain_analysis_output.primary_pain_category if pain_analysis_output else 'N/A'}\n"
                f"Qualificação: {qualification_output.qualification_tier if qualification_output else 'N/A'}\n"
                f"Produto/Serviço Nosso: {self.product_service_context}"
            )
            
            tot_generation_output = self._generate_tot_strategies(current_lead_summary_for_tot)
            tot_evaluation_output = self._evaluate_tot_strategies(tot_generation_output, current_lead_summary_for_tot)
            tot_synthesis_output = self._synthesize_tot_action_plan(tot_evaluation_output, tot_generation_output, current_lead_summary_for_tot)
            
            detailed_approach_plan_output = self._develop_detailed_approach_plan(
                lead_analysis_str_for_agents, persona_profile_str, deepened_pain_points_for_agents, tot_synthesis_output, str(url)
            )

            objection_handling_output = self._prepare_objection_handling(
                persona_profile_str, 
                company_name,
                detailed_approach_plan_output.model_dump_json(indent=2) if detailed_approach_plan_output and not detailed_approach_plan_output.error_message else "Plano detalhado não disponível"
            )

            # Corrected assignments for value_propositions and strategic_questions
            current_value_propositions = value_props_list.custom_value_propositions if value_props_list and hasattr(value_props_list, 'custom_value_propositions') and not value_props_list.error_message else []
            current_strategic_questions = strategic_questions_list.strategic_questions if strategic_questions_list and hasattr(strategic_questions_list, 'strategic_questions') and not strategic_questions_list.error_message else []

            enhanced_strategy = EnhancedStrategy(
                external_intelligence=external_intel,
                contact_information=contact_info,
                pain_point_analysis=pain_analysis_output,
                competitor_intelligence=competitor_intel_output,
                purchase_triggers=purchase_triggers_output,
                lead_qualification=qualification_output,
                tot_generated_strategies=tot_generation_output.proposed_strategies if tot_generation_output else None,
                tot_evaluated_strategies=tot_evaluation_output.evaluated_strategies if tot_evaluation_output else None,
                tot_synthesized_action_plan=tot_synthesis_output if tot_synthesis_output else None,
                detailed_approach_plan=detailed_approach_plan_output if detailed_approach_plan_output else None,
                value_propositions=current_value_propositions,
                objection_framework=objection_handling_output,
                strategic_questions=current_strategic_questions
            )

            # New call for content marketing ideas
            content_marketing_output = self._generate_content_marketing_ideas(
                analyzed_lead,
                persona_profile_str,
                enhanced_strategy # Pass the current state of enhanced_strategy
            )
            enhanced_strategy.content_marketing_ideas = content_marketing_output # Assign to the field
            
            personalized_message = self._create_personalized_message(analyzed_lead, enhanced_strategy, contact_info, persona_profile_str)
            internal_briefing = self._create_internal_briefing(analyzed_lead, enhanced_strategy)
            
            total_time = time.time() - start_time
            return ComprehensiveProspectPackage(
                analyzed_lead=analyzed_lead,
                enhanced_strategy=enhanced_strategy,
                enhanced_personalized_message=personalized_message,
                internal_briefing=internal_briefing,
                confidence_score=self._calculate_confidence_score(enhanced_strategy),
                roi_potential_score=self._calculate_roi_potential(enhanced_strategy),
                brazilian_market_fit=self._calculate_brazilian_fit(analyzed_lead),
                processing_metadata={"total_processing_time": total_time, "processing_mode": "enhanced", "tavily_enabled": bool(self.tavily_api_key), "company_name": company_name}
            )
        except Exception as e:
            self.logger.error(f"Enhanced processing failed for {url}: {e}\n{traceback.format_exc()}")
            raise

    def _gather_external_intelligence(self, company_name: str, analyzed_lead: AnalyzedLead) -> ExternalIntelligence:
        text_content = analyzed_lead.validated_lead.site_data.extracted_text_content or ""
        enrichment_input = TavilyEnrichmentInput(company_name=company_name, initial_extracted_text=text_content)
        try:
            output: TavilyEnrichmentOutput = self.tavily_enrichment_agent.execute(enrichment_input)
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
            output: ContactExtractionOutput = self.contact_extraction_agent.execute(extraction_input)
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

    def _analyze_pain_points(self, lead_analysis_str: str, persona_profile_str: str, company_name: str) -> PainPointDeepeningOutput: # Changed return type
        pain_input = PainPointDeepeningInput(
            lead_analysis=lead_analysis_str,
            persona_profile=persona_profile_str,
            product_service_offered=self.product_service_context,
            company_name=company_name
        )
        try:
            output: PainPointDeepeningOutput = self.pain_point_deepening_agent.execute(pain_input)
            if output.error_message:
                self.logger.warning(f"PainPointDeepeningAgent returned an error: {output.error_message}")
            return output # Return the agent's Pydantic output directly
        except Exception as e:
            self.logger.error(f"Exception in _analyze_pain_points: {e}")
            return PainPointDeepeningOutput(error_message=str(e))

    def _qualify_lead(self, lead_analysis_str: str, persona_profile_str: str, deepened_pain_points_str: str) -> LeadQualificationOutput: # Changed return type
        qualification_input = LeadQualificationInput(
            lead_analysis=lead_analysis_str,
            persona_profile=persona_profile_str,
            deepened_pain_points=deepened_pain_points_str,
            product_service_offered=self.product_service_context
        )
        try:
            output: LeadQualificationOutput = self.lead_qualification_agent.execute(qualification_input)
            if output.error_message:
                self.logger.warning(f"LeadQualificationAgent returned an error: {output.error_message}")
            return output # Return the agent's Pydantic output directly
        except Exception as e:
            self.logger.error(f"Exception in _qualify_lead: {e}")
            return LeadQualificationOutput(error_message=str(e))

    def _analyze_competitors(self, analyzed_lead: AnalyzedLead) -> CompetitorIdentificationOutput: # Changed return type
        text_content = analyzed_lead.validated_lead.site_data.extracted_text_content or ""
        lead_product_service = ", ".join(analyzed_lead.analysis.main_services) if analyzed_lead.analysis.main_services else \
                               (analyzed_lead.analysis.company_description or "Serviços da empresa analisada")
        competitor_input = CompetitorIdentificationInput(
            initial_extracted_text=text_content,
            product_service_offered=lead_product_service,
            known_competitors_list_str=self.competitors_list
        )
        try:
            output: CompetitorIdentificationOutput = self.competitor_identification_agent.execute(competitor_input)
            if output.error_message:
                 self.logger.warning(f"CompetitorIdentificationAgent returned an error: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _analyze_competitors: {e}")
            return CompetitorIdentificationOutput(error_message=str(e))

    def _identify_purchase_triggers(self, analyzed_lead: AnalyzedLead, external_intel: Optional[ExternalIntelligence]) -> BuyingTriggerIdentificationOutput: # Changed return type
        lead_data_dict = {
            "company_name": self._extract_company_name(analyzed_lead), "url": str(analyzed_lead.validated_lead.site_data.url),
            "description": analyzed_lead.analysis.company_description, "sector": analyzed_lead.analysis.company_sector,
            "main_services": analyzed_lead.analysis.main_services, "recent_activities_from_analysis": analyzed_lead.analysis.recent_activities,
            "extracted_text_summary": self._truncate_text(analyzed_lead.validated_lead.site_data.extracted_text_content or "", 500)
        }
        try:
            lead_data_str = json.dumps(lead_data_dict, ensure_ascii=False)
        except Exception as e_json:
            self.logger.warning(f"Could not serialize lead_data for BuyingTriggerIdentificationAgent: {e_json}")
            lead_data_str = "{'error': 'Could not serialize lead data'}"
        enriched_data_str = external_intel.tavily_enrichment if external_intel and external_intel.tavily_enrichment else "Nenhuma informação de enriquecimento disponível."
        trigger_input = BuyingTriggerIdentificationInput(
            lead_data_str=lead_data_str, enriched_data=enriched_data_str, product_service_offered=self.product_service_context
        )
        try:
            output: BuyingTriggerIdentificationOutput = self.buying_trigger_identification_agent.execute(trigger_input)
            if output.error_message:
                self.logger.warning(f"BuyingTriggerIdentificationAgent returned an error: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _identify_purchase_triggers: {e}")
            return BuyingTriggerIdentificationOutput(error_message=str(e))

    def _create_value_propositions(self, lead_analysis_str: str, persona_profile_str: str, deepened_pain_points_str: str, purchase_triggers_output: Optional[BuyingTriggerIdentificationOutput], company_name: str) -> ValuePropositionCustomizationOutput: # Changed return type
        buying_triggers_report_str = json.dumps([t.model_dump() for t in purchase_triggers_output.identified_triggers]) if purchase_triggers_output and purchase_triggers_output.identified_triggers else "Relatório de gatilhos não disponível ou com erro."
        value_prop_input = ValuePropositionCustomizationInput(
            lead_analysis=lead_analysis_str, persona_profile=persona_profile_str,
            deepened_pain_points=deepened_pain_points_str, buying_triggers_report=buying_triggers_report_str,
            product_service_offered=self.product_service_context, company_name=company_name
        )
        try:
            output: ValuePropositionCustomizationOutput = self.value_proposition_customization_agent.execute(value_prop_input)
            if output.error_message:
                self.logger.warning(f"ValuePropositionCustomizationAgent returned an error: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _create_value_propositions: {e}")
            return ValuePropositionCustomizationOutput(error_message=str(e))

    def _generate_strategic_questions(self, lead_analysis_str: str, persona_profile_str: str, deepened_pain_points_str: str) -> StrategicQuestionGenerationOutput: # Changed return type
        sq_input = StrategicQuestionGenerationInput(
            lead_analysis=lead_analysis_str, persona_profile=persona_profile_str, deepened_pain_points=deepened_pain_points_str
        )
        try:
            output: StrategicQuestionGenerationOutput = self.strategic_question_generation_agent.execute(sq_input)
            if output.error_message:
                self.logger.warning(f"StrategicQuestionGenerationAgent returned an error: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _generate_strategic_questions: {e}")
            return StrategicQuestionGenerationOutput(error_message=str(e))

    def _generate_content_marketing_ideas(
        self,
        analyzed_lead: AnalyzedLead,
        persona_profile_str: str,
        enhanced_strategy_data: EnhancedStrategy # Pass currently built strategy data for context
    ) -> Optional[ContentMarketingOutputModel]: # Use the aliased model if defined, or direct import
        self.logger.info(f"[{self.agent_name}] Generating content marketing ideas for {self._extract_company_name(analyzed_lead)}...")

        topic_parts = []
        # Accessing company_description from analysis object
        if analyzed_lead.analysis.company_description: # company_description is part of LeadAnalysis
            topic_parts.append(f"Company Focus: {analyzed_lead.analysis.company_description}")
        if analyzed_lead.analysis.main_services:
            topic_parts.append(f"Main Services: {', '.join(analyzed_lead.analysis.main_services)}")

        # Safely access pain points from enhanced_strategy_data
        if enhanced_strategy_data.pain_point_analysis and \
           not enhanced_strategy_data.pain_point_analysis.error_message and \
           hasattr(enhanced_strategy_data.pain_point_analysis, 'detailed_pain_points') and \
           enhanced_strategy_data.pain_point_analysis.detailed_pain_points:
             topic_parts.append(f"Key Pain Points: {', '.join([dp.pain_description for dp in enhanced_strategy_data.pain_point_analysis.detailed_pain_points[:2]])}")

        topic = ". ".join(topic_parts) if topic_parts else f"General business solutions for {self._extract_company_name(analyzed_lead)}"
        topic = self._truncate_text(topic, 500) # Ensure topic is not excessively long

        content_goals = [
            "increase brand awareness",
            "educate the target audience",
            "drive engagement",
            "position the company as a thought leader"
        ]

        market_input = ContentMarketingInput(
            topic=topic,
            target_audience=persona_profile_str if persona_profile_str else "General business professionals",
            content_goals=content_goals
        )

        try:
            content_ideas_output: ContentMarketingOutputModel = self.content_marketing_agent.execute(market_input)
            if content_ideas_output.generation_summary and "error" in content_ideas_output.generation_summary.lower():
                self.logger.warning(f"[{self.agent_name}] ContentMarketingAgent generated an output with error summary: {content_ideas_output.generation_summary}")
            return content_ideas_output
        except Exception as e:
            self.logger.error(f"[{self.agent_name}] Failed to generate content marketing ideas: {e}")
            return ContentMarketingOutputModel(
                input_topic=topic,
                generation_summary=f"Error generating content marketing ideas: {str(e)}"
            )

    def _prepare_objection_handling(self, persona_profile_str: str, company_name: str, detailed_approach_plan_text: str) -> ObjectionHandlingOutput: # Changed signature & return type
        objection_input = ObjectionHandlingInput(
            detailed_approach_plan_text=detailed_approach_plan_text or "Plano de abordagem não disponível.",
            persona_profile=persona_profile_str, product_service_offered=self.product_service_context, company_name=company_name
        )
        try:
            output: ObjectionHandlingOutput = self.objection_handling_agent.execute(objection_input)
            if output.error_message:
                self.logger.warning(f"ObjectionHandlingAgent returned an error: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in _prepare_objection_handling: {e}")
            return ObjectionHandlingOutput(error_message=str(e))
    
    def _generate_tot_strategies(self, current_lead_summary: str) -> ToTStrategyGenerationOutput:
        self.logger.info("ToT Sub-step 1: Generating strategy options")
        generation_input = ToTStrategyGenerationInput(current_lead_summary=current_lead_summary, product_service_offered=self.product_service_context)
        try:
            output: ToTStrategyGenerationOutput = self.tot_strategy_generation_agent.execute(generation_input)
            if output.error_message:
                self.logger.warning(f"ToTStrategyGenerationAgent failed: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in ToT strategy generation: {e}")
            return ToTStrategyGenerationOutput(error_message=f"Exceção ao gerar estratégias: {str(e)}")

    def _evaluate_tot_strategies(self, generated_strategies_output: Optional[ToTStrategyGenerationOutput], current_lead_summary: str) -> ToTStrategyEvaluationOutput:
        self.logger.info("ToT Sub-step 2: Evaluating strategy options")
        proposed_strategies_text_input = "Nenhuma estratégia proposta foi gerada."
        if generated_strategies_output and generated_strategies_output.proposed_strategies:
            proposed_strategies_text_input = ""
            for i, strat in enumerate(generated_strategies_output.proposed_strategies):
                proposed_strategies_text_input += f"Estratégia {i+1}: {strat.strategy_name}\n  Ângulo/Gancho: {strat.angle_or_hook}\n  Tom: {strat.tone_of_voice}\n  Canais: {', '.join(strat.primary_channels)}\n  Pontos Chave: {'; '.join(strat.key_points_or_arguments)}\n  Pergunta de Abertura: {strat.opening_question}\n\n"
        elif generated_strategies_output and generated_strategies_output.error_message:
             proposed_strategies_text_input = f"Erro na geração de estratégias: {generated_strategies_output.error_message}"
        
        evaluation_input = ToTStrategyEvaluationInput(proposed_strategies_text=proposed_strategies_text_input, current_lead_summary=current_lead_summary)
        try:
            output: ToTStrategyEvaluationOutput = self.tot_strategy_evaluation_agent.execute(evaluation_input)
            if output.error_message:
                self.logger.warning(f"ToTStrategyEvaluationAgent failed: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in ToT strategy evaluation: {e}")
            return ToTStrategyEvaluationOutput(error_message=f"Exceção ao avaliar estratégias: {str(e)}")

    def _synthesize_tot_action_plan(self, evaluated_strategies_output: Optional[ToTStrategyEvaluationOutput], generated_strategies_output: Optional[ToTStrategyGenerationOutput], current_lead_summary: str) -> ToTActionPlanSynthesisOutput:
        self.logger.info("ToT Sub-step 3: Synthesizing final action plan")
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
            output: ToTActionPlanSynthesisOutput = self.tot_action_plan_synthesis_agent.execute(synthesis_input)
            if output.error_message:
                self.logger.warning(f"ToTActionPlanSynthesisAgent failed: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in ToT action plan synthesis: {e}")
            return ToTActionPlanSynthesisOutput(error_message=f"Exceção ao sintetizar plano de ação: {str(e)}")

    def _develop_detailed_approach_plan(self, lead_analysis_str: str, persona_profile_str: str, deepened_pain_points_str: str, tot_action_plan: Optional[ToTActionPlanSynthesisOutput], lead_url:str) -> DetailedApproachPlanOutput: # Changed return type
        self.logger.info("Developing detailed approach plan...")
        final_action_plan_summary_for_detailed_plan = "Plano de Ação Sintetizado:\n"
        if tot_action_plan and not tot_action_plan.error_message:
            final_action_plan_summary_for_detailed_plan += f"- Estratégia Recomendada: {tot_action_plan.recommended_strategy_name}\n"
            final_action_plan_summary_for_detailed_plan += f"- Gancho Principal: {tot_action_plan.primary_angle_hook}\n"
            final_action_plan_summary_for_detailed_plan += f"- Tom de Voz: {tot_action_plan.tone_of_voice}\n"
            for step in tot_action_plan.action_sequence:
                final_action_plan_summary_for_detailed_plan += f"  - Passo {step.step_number} ({step.channel}): {step.action_description} (CTA: {step.cta or 'N/A'})\n"
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
            output: DetailedApproachPlanOutput = self.detailed_approach_plan_agent.execute(plan_input)
            if output.error_message:
                self.logger.warning(f"DetailedApproachPlanAgent failed: {output.error_message}")
            return output
        except Exception as e:
            self.logger.error(f"Exception in detailed approach plan development: {e}")
            return DetailedApproachPlanOutput(error_message=str(e))

    # Removed old _generate_tot_strategy method as it's replaced by the three new ones.
    
    def _create_personalized_message(self, analyzed_lead: AnalyzedLead, enhanced_strategy: EnhancedStrategy, contact_info: Optional[ContactInformation], persona_profile_str: str) -> EnhancedPersonalizedMessage:
        company_name = self._extract_company_name(analyzed_lead)
        
        final_action_plan_summary = "Plano de Ação Chave:\n"
        if enhanced_strategy.tot_synthesized_action_plan and not enhanced_strategy.tot_synthesized_action_plan.error_message:
            plan = enhanced_strategy.tot_synthesized_action_plan
            final_action_plan_summary += f"- Estratégia: {plan.recommended_strategy_name}\n"
            final_action_plan_summary += f"- Gancho: {plan.primary_angle_hook}\n"
            final_action_plan_summary += f"- Pergunta Abertura: {plan.main_opening_question}\n"
        elif enhanced_strategy.tot_synthesized_action_plan and enhanced_strategy.tot_synthesized_action_plan.error_message:
            final_action_plan_summary = f"Erro no plano de ação: {enhanced_strategy.tot_synthesized_action_plan.error_message}"
        else: # Fallback if tot_synthesized_action_plan is None
            final_action_plan_summary = "Plano de ação não disponível."
            
        value_props_str_list = []
        if enhanced_strategy.value_propositions:
            for i, vp in enumerate(enhanced_strategy.value_propositions):
                if not vp.error_message:
                    value_props_str_list.append(f"Proposta {i+1} ({vp.title}): {vp.key_benefit}. Conexão: {vp.connection_to_pain_or_trigger}. Diferencial: {vp.differentiation_factor}. Chamada: {vp.call_to_value}")
        value_props_text = "\n".join(value_props_str_list) if value_props_str_list else "Propostas de valor não disponíveis."

        b2b_contact_details = B2BContactDetailsInput(
            emails_found=contact_info.emails_found if contact_info else [],
            instagram_profiles_found=contact_info.instagram_profiles if contact_info else []
        )

        message_input = B2BPersonalizedMessageInput(
            final_action_plan_text=final_action_plan_summary,
            customized_value_propositions_text=value_props_text,
            contact_details=b2b_contact_details,
            product_service_offered=self.product_service_context,
            lead_url=str(analyzed_lead.validated_lead.site_data.url),
            company_name=company_name,
            persona_fictional_name=persona_profile_str # Using the constructed persona string
        )
        try:
            msg_output: B2BPersonalizedMessageOutput = self.b2b_personalized_message_agent.execute(message_input)
            if msg_output.error_message and not (msg_output.crafted_message_body and msg_output.crafted_message_body != "Não foi possível gerar a mensagem."):
                self.logger.warning(f"B2BPersonalizedMessageAgent failed: {msg_output.error_message}")
                primary_msg = PersonalizedMessage(channel=CommunicationChannel.EMAIL, message_body=f"Erro: {msg_output.error_message}", call_to_action="N/A", error_message=msg_output.error_message)
                return EnhancedPersonalizedMessage(primary_message=primary_msg, error_message=msg_output.error_message)

            channel = CommunicationChannel.EMAIL
            if msg_output.crafted_message_channel and msg_output.crafted_message_channel != "N/A": # Check for "N/A"
                try:
                    channel = CommunicationChannel(msg_output.crafted_message_channel.lower())
                except ValueError:
                    self.logger.warning(f"Invalid channel '{msg_output.crafted_message_channel}' from B2B agent. Defaulting to EMAIL.")
            
            primary_message = PersonalizedMessage(
                channel=channel, subject_line=msg_output.crafted_message_subject, message_body=msg_output.crafted_message_body,
                call_to_action="Verificar corpo da mensagem para CTA.", 
                error_message=msg_output.error_message if (msg_output.error_message and msg_output.error_message not in msg_output.crafted_message_body) else None
            )
            return EnhancedPersonalizedMessage(primary_message=primary_message, error_message=primary_message.error_message)
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
            "lead_analysis_summary": {
                "company_sector": analysis_obj.company_sector, "main_services": analysis_obj.main_services,
                "company_description": self._truncate_text(analysis_obj.company_description or "", 300),
                "ideal_customer_profile_estimate": self._construct_persona_profile_string(analysis_obj, company_name),
                "potential_challenges": analysis_obj.potential_challenges, "general_diagnosis": analysis_obj.general_diagnosis
            },
            "external_intelligence_summary": self._truncate_text(enhanced_strategy.external_intelligence.tavily_enrichment if enhanced_strategy.external_intelligence else "N/A", 300),
            "contact_information_summary": safe_dump_or_error(enhanced_strategy.contact_information, "contact_information"),
            "pain_point_analysis_summary": safe_dump_or_error(enhanced_strategy.pain_point_analysis, "pain_point_analysis"),
            "lead_qualification_summary": safe_dump_or_error(enhanced_strategy.lead_qualification, "lead_qualification"),
            "competitor_intelligence_summary": safe_dump_or_error(enhanced_strategy.competitor_intelligence, "competitor_intelligence"),
            "purchase_triggers_summary": safe_dump_or_error(enhanced_strategy.purchase_triggers, "purchase_triggers"),
            "customized_value_propositions_summary": [safe_dump_or_error(vp, f"value_proposition_{i}") for i, vp in enumerate(enhanced_strategy.value_propositions)] if enhanced_strategy.value_propositions else [],
            "strategic_questions_generated": enhanced_strategy.strategic_questions if enhanced_strategy.strategic_questions else [],
            "objection_handling_summary": safe_dump_or_error(enhanced_strategy.objection_framework, "objection_framework"),
            "tot_synthesized_action_plan_summary": safe_dump_or_error(enhanced_strategy.tot_synthesized_action_plan, "tot_synthesized_action_plan"),
            "detailed_approach_plan_summary": safe_dump_or_error(enhanced_strategy.detailed_approach_plan, "detailed_approach_plan"),
             # Added Content Marketing Ideas Summary
            "content_marketing_ideas_summary": safe_dump_or_error(enhanced_strategy.content_marketing_ideas, "content_marketing_ideas"),
        }
        briefing_input = InternalBriefingSummaryInput(all_lead_data=all_lead_data)
        try:
            output: InternalBriefingSummaryOutput = self.internal_briefing_summary_agent.execute(briefing_input)
            if output.error_message:
                self.logger.warning(f"InternalBriefingSummaryAgent returned an error: {output.error_message}")
                return InternalBriefing(executive_summary=f"Falha ao gerar briefing: {output.error_message}", error_message=output.error_message)
            
            # Map InternalBriefingSummaryOutput (agent's Pydantic) to InternalBriefing (lead_structures Pydantic)
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
                error_message=output.error_message
            )
        except Exception as e:
            self.logger.error(f"Exception in _create_internal_briefing: {e}")
            return InternalBriefing(executive_summary=f"Exceção ao gerar briefing: {str(e)}", error_message=str(e))
    
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
        # max_len = max_length or self.max_text_length # self.max_text_length no longer exists
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
        # This method might not be directly used if all LLM calls are delegated to sub-agents
        # that use their own BaseAgent.parse_llm_json_response.
        # However, keeping it for potential direct calls or as a utility.
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response: # Handle cases where ``` is present without json specifier
                response = response.split("```")[1].split("```")[0]
            return json.loads(response.strip())
        except json.JSONDecodeError as e:
            self.logger.warning(f"EnhancedLeadProcessor._parse_response: JSONDecodeError - {e}. Response: {response[:200]}")
            return {"error": "Failed to parse JSON response", "raw_response": response}
        except Exception as e: # Catch broader errors during parsing
            self.logger.warning(f"EnhancedLeadProcessor._parse_response: Unexpected error - {e}. Response: {response[:200]}")
            return {"error": str(e), "raw_response": response}

# Ensure data_models from lead_structures are correctly referenced for Pydantic types
from data_models.lead_structures import DetailedPainPointSchema, CompetitorDetailSchema, IdentifiedTriggerSchema, \
    ToTStrategyOptionModel, EvaluatedStrategyModel, ActionPlanStepModel, ToTActionPlanSynthesisModel, \
    ContactStepDetailSchema, DetailedApproachPlanModel, ObjectionResponseModelSchema, InternalBriefingSectionSchema
