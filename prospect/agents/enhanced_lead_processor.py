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
from event_models import AgentStartEvent, AgentEndEvent, StatusUpdateEvent, PipelineErrorEvent, PipelineEndEvent

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
        name: str,
        description: str,
        llm_client: LLMClientBase,
        product_service_context: str = "",
        competitors_list: str = "",
        tavily_api_key: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ):
        super().__init__(
            name=name,
            description=description,
            llm_client=llm_client,
            config={"temperature": temperature},
            **kwargs
        )
        
        self.product_service_context = product_service_context
        self.competitors_list = competitors_list
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")

        # Note: The sub-agent constructors will need to be updated to accept name and description
        self.tavily_enrichment_agent = TavilyEnrichmentAgent(llm_client=self.llm_client, name="TavilyEnrichmentAgent", description="Gathers external intelligence and news about the company using the Tavily web search API.", tavily_api_key=self.tavily_api_key)
        self.contact_extraction_agent = ContactExtractionAgent(llm_client=self.llm_client, name="ContactExtractionAgent", description="Extracts contact information from lead's data.")
        self.pain_point_deepening_agent = PainPointDeepeningAgent(llm_client=self.llm_client, name="PainPointDeepeningAgent", description="Further analyzes and details the lead's potential pain points.")
        self.lead_qualification_agent = LeadQualificationAgent(llm_client=self.llm_client, name="LeadQualificationAgent", description="Qualifies the lead by assigning a tier and provides a justification.")
        self.competitor_identification_agent = CompetitorIdentificationAgent(llm_client=self.llm_client, name="CompetitorIdentificationAgent", description="Identifies potential competitors of the lead company.")
        self.strategic_question_generation_agent = StrategicQuestionGenerationAgent(llm_client=self.llm_client, name="StrategicQuestionGenerationAgent", description="Generates additional strategic, open-ended questions.")
        self.buying_trigger_identification_agent = BuyingTriggerIdentificationAgent(llm_client=self.llm_client, name="BuyingTriggerIdentificationAgent", description="Identifies events or signals that might indicate the lead is actively looking for solutions.")
        self.tot_strategy_generation_agent = ToTStrategyGenerationAgent(llm_client=self.llm_client, name="ToTStrategyGenerationAgent", description="Generates multiple distinct strategic approach options for the lead.")
        self.tot_strategy_evaluation_agent = ToTStrategyEvaluationAgent(llm_client=self.llm_client, name="ToTStrategyEvaluationAgent", description="Evaluates the generated strategic options.")
        self.tot_action_plan_synthesis_agent = ToTActionPlanSynthesisAgent(llm_client=self.llm_client, name="ToTActionPlanSynthesisAgent", description="Synthesizes the evaluated strategies into a single, refined action plan.")
        self.detailed_approach_plan_agent = DetailedApproachPlanAgent(llm_client=self.llm_client, name="DetailedApproachPlanAgent", description="Develops a detailed, step-by-step approach plan.")
        self.objection_handling_agent = ObjectionHandlingAgent(llm_client=self.llm_client, name="ObjectionHandlingAgent", description="Anticipates potential objections the lead might have.")
        self.value_proposition_customization_agent = ValuePropositionCustomizationAgent(llm_client=self.llm_client, name="ValuePropositionCustomizationAgent", description="Crafts customized value propositions.")
        self.b2b_personalized_message_agent = B2BPersonalizedMessageAgent(llm_client=self.llm_client, name="B2BPersonalizedMessageAgent", description="Generates personalized outreach messages.")
        self.internal_briefing_summary_agent = InternalBriefingSummaryAgent(llm_client=self.llm_client, name="InternalBriefingSummaryAgent", description="Creates a comprehensive internal briefing document.")
        
    def _construct_persona_profile_string(self, analysis_obj: LeadAnalysis, company_name: str) -> str:
        """Helper to create a descriptive persona string from analysis."""
        persona_parts = [
            analysis_obj.general_diagnosis or "",
            f"Cultura da Empresa: {analysis_obj.company_culture_values or 'N/A'}",
            f"Tamanho da Empresa {company_name}: {analysis_obj.company_size_estimate or 'N/A'}"
        ]
        persona_profile_str = ". ".join(filter(None, persona_parts))
        return persona_profile_str if persona_profile_str else f"Perfil da persona para {company_name} não detalhado suficientemente na análise inicial."

    def _construct_lead_analysis_string(self, analysis_obj: LeadAnalysis, external_intel: Optional[ExternalIntelligence]) -> str:
        """Helper to create a lead analysis string."""
        return (
            f"Setor da Empresa: {analysis_obj.company_sector}\n"
            f"Principais Serviços: {', '.join(analysis_obj.main_services)}\n"
            f"Diagnóstico Geral: {analysis_obj.general_diagnosis}\n"
            f"Desafios Potenciais Identificados: {', '.join(analysis_obj.potential_challenges)}\n"
            f"Tamanho Estimado: {analysis_obj.company_size_estimate}\n"
            f"Cultura da Empresa: {analysis_obj.company_culture_values}\n"
            f"Diagnóstico Geral: {analysis_obj.general_diagnosis}\n"
            f"Inteligência Externa: {external_intel.tavily_enrichment if external_intel and external_intel.tavily_enrichment else 'N/A'}"
        )

    async def execute_enrichment_pipeline(
        self, analyzed_lead: AnalyzedLead, job_id: str, user_id: str
    ) -> AsyncIterator[Dict[str, Any]]:
        start_time = time.time()
        url = str(analyzed_lead.validated_lead.site_data.url)
        company_name = self._extract_company_name(analyzed_lead)
        
        pipeline_logger = self.logger.bind(job_id=job_id, user_id=user_id, company_url=url, company_name=company_name)
        pipeline_logger.info(f"🚀 ENRICHMENT PIPELINE STARTING for: {company_name}")
        pipeline_logger.info(f"📊 Pipeline input validation: URL={url}, extraction_successful={analyzed_lead.validated_lead.extraction_successful}")
        pipeline_logger.info(f"🔧 Configuration: product_context_length={len(self.product_service_context)}, tavily_enabled={bool(self.tavily_api_key)}")
        
        # Log input data quality
        text_content_length = len(analyzed_lead.validated_lead.cleaned_text_content or "")
        analysis_quality = {
            "sector": analyzed_lead.analysis.company_sector,
            "services_count": len(analyzed_lead.analysis.main_services),
            "challenges_count": len(analyzed_lead.analysis.potential_challenges),
            "relevance_score": analyzed_lead.analysis.relevance_score,
            "text_length": text_content_length
        }
        pipeline_logger.info(f"📈 Input analysis quality: {analysis_quality}")

        yield StatusUpdateEvent(
            event_type="status_update",
            timestamp=datetime.now().isoformat(),
            job_id=job_id,
            user_id=user_id,
            status_message=f"Starting enrichment for {company_name} - {len(analyzed_lead.analysis.main_services)} services identified."
        ).to_dict()

        try:
            async def run_and_log_agent(agent, input_data, agent_input_description):
                agent_logger = pipeline_logger.bind(agent_name=agent.name)
                agent_logger.info(f"🔄 AGENT STARTING: {agent.name}")
                agent_logger.info(f"📝 Agent description: {agent.description}")
                agent_logger.info(f"🔍 Input description: {agent_input_description}")
                
                # Log input data details
                input_data_info = {
                    "input_type": type(input_data).__name__,
                    "input_fields": list(input_data.__dict__.keys()) if hasattr(input_data, '__dict__') else "unknown"
                }
                agent_logger.debug(f"📊 Input data info: {input_data_info}")

                yield AgentStartEvent(
                    event_type="agent_start",
                    timestamp=datetime.now().isoformat(),
                    job_id=job_id,
                    user_id=user_id,
                    agent_name=agent.name,
                    agent_description=agent.description,
                    input_query=agent_input_description
                ).to_dict()
                
                output = None
                agent_start_time = time.time()
                try:
                    agent_logger.debug(f"⚡ Starting async execution for {agent.name}")
                    output = await agent.execute_async(input_data)
                    
                    # Detailed success analysis
                    error_msg = getattr(output, 'error_message', None)
                    success = not error_msg
                    
                    if success:
                        # Log output quality metrics
                        output_info = self._analyze_agent_output(agent.name, output)
                        agent_logger.info(f"✅ Agent {agent.name} completed successfully: {output_info}")
                    else:
                        agent_logger.warning(f"⚠️  Agent {agent.name} completed with error: {error_msg}")
                        
                except Exception as e:
                    agent_logger.error(f"❌ Sub-agent {agent.name} raised an exception: {e}")
                    agent_logger.error(f"🔍 Exception traceback: {traceback.format_exc()}")
                    success = False
                    # Try to create a default output object with an error message
                    try:
                        # This line seems wrong - agent.output_model doesn't exist
                        # We should create a proper default output based on the agent type
                        output = self._create_default_output_for_agent(agent.name, f"Agent execution failed: {e}")
                    except Exception as create_error:
                        agent_logger.error(f"🚨 Failed to create default output: {create_error}")
                        pass

                agent_end_time = time.time()
                execution_time = agent_end_time - agent_start_time
                
                agent_logger.info(f"⏱️  Agent {agent.name} execution time: {execution_time:.2f} seconds")
                
                yield AgentEndEvent(
                    event_type="agent_end",
                    timestamp=datetime.now().isoformat(),
                    job_id=job_id,
                    user_id=user_id,
                    agent_name=agent.name,
                    execution_time_seconds=execution_time,
                    success=success,
                    final_response=output.model_dump_json() if output else None,
                    error_message=getattr(output, 'error_message', "Agent execution failed with an exception.")
                ).to_dict()
                
                if not success:
                    agent_logger.error(f"🔴 Sub-agent {agent.name} FAILED: {getattr(output, 'error_message', 'Unknown error')}")
                else:
                    agent_logger.info(f"🟢 Sub-agent {agent.name} COMPLETED successfully")
                
                yield output

            async def get_agent_result(agent, input_data, description):
                result = None
                events = []
                try:
                    async for item in run_and_log_agent(agent, input_data, description):
                        if isinstance(item, dict) and 'event_type' in item:
                            events.append(item)
                        else:
                            result = item
                except Exception as e:
                    pipeline_logger.error(f"Error in get_agent_result for {agent.name}: {e}\n{traceback.format_exc()}")
                    # The original code returned None, so we'll create a default error object if possible
                    # or just let result be None.
                    pass
                return result, events

            analysis_obj = analyzed_lead.analysis
            persona_profile_str = self._construct_persona_profile_string(analysis_obj, company_name)

            # --- Execute Sub-Agents Sequentially ---
            pipeline_logger.info("🚀 PHASE 1: External Intelligence & Contact Extraction")
            
            # Step 1: Tavily Enrichment
            pipeline_logger.info("📡 Step 1/15: Tavily External Intelligence")
            tavily_output, events = await get_agent_result(self.tavily_enrichment_agent, TavilyEnrichmentInput(company_name=company_name, initial_extracted_text=analyzed_lead.validated_lead.site_data.extracted_text_content or ""), f"Enriching data for {company_name}")
            for event in events: yield event
            external_intel = ExternalIntelligence(tavily_enrichment=tavily_output.enriched_data if tavily_output else "")
            pipeline_logger.info(f"✅ Tavily enrichment completed: api_called={getattr(tavily_output, 'tavily_api_called', False)}, data_length={len(external_intel.tavily_enrichment)}")
            
            # Step 2: Contact Extraction
            pipeline_logger.info("📧 Step 2/15: Contact Information Extraction")
            contact_info, events = await get_agent_result(self.contact_extraction_agent, ContactExtractionInput(extracted_text=analyzed_lead.validated_lead.cleaned_text_content or "", company_name=company_name, product_service_offered=self.product_service_context), f"Extracting contacts for {company_name}")
            for event in events: yield event
            emails_found = len(getattr(contact_info, 'emails_found', [])) if contact_info else 0
            instagram_found = len(getattr(contact_info, 'instagram_profiles_found', [])) if contact_info else 0
            pipeline_logger.info(f"✅ Contact extraction completed: emails={emails_found}, instagram={instagram_found}")
            
            pipeline_logger.info("🚀 PHASE 2: Strategic Analysis & Qualification")
            
            # Prepare analysis string for subsequent agents
            lead_analysis_str_for_agents = self._construct_lead_analysis_string(analysis_obj, external_intel)
            pipeline_logger.debug(f"📊 Constructed lead analysis string, length: {len(lead_analysis_str_for_agents)}")
            
            # Step 3: Pain Point Deepening
            pipeline_logger.info("🎯 Step 3/15: Pain Point Analysis")
            pain_analysis_output, events = await get_agent_result(self.pain_point_deepening_agent, PainPointDeepeningInput(lead_analysis=lead_analysis_str_for_agents, persona_profile=persona_profile_str, product_service_offered=self.product_service_context, company_name=company_name), "Deepening pain points")
            for event in events: yield event
            deepened_pain_points_for_agents = json.dumps(pain_analysis_output.model_dump(), ensure_ascii=False) if pain_analysis_output and not getattr(pain_analysis_output, 'error_message', None) else "Análise de dores não disponível."
            pain_points_count = len(getattr(pain_analysis_output, 'detailed_pain_points', [])) if pain_analysis_output else 0
            pipeline_logger.info(f"✅ Pain point analysis completed: category={getattr(pain_analysis_output, 'primary_pain_category', 'N/A')}, points={pain_points_count}")

            # Step 4: Lead Qualification
            pipeline_logger.info("⚖️  Step 4/15: Lead Qualification")
            qualification_output, events = await get_agent_result(self.lead_qualification_agent, LeadQualificationInput(lead_analysis=lead_analysis_str_for_agents, persona_profile=persona_profile_str, deepened_pain_points=deepened_pain_points_for_agents, product_service_offered=self.product_service_context), "Qualifying lead")
            for event in events: yield event
            qual_tier = getattr(qualification_output, 'qualification_tier', 'N/A') if qualification_output else 'N/A'
            qual_confidence = getattr(qualification_output, 'confidence_score', 'N/A') if qualification_output else 'N/A'
            pipeline_logger.info(f"✅ Lead qualification completed: tier={qual_tier}, confidence={qual_confidence}")
            
            pipeline_logger.info("🚀 PHASE 3: Competitive Intelligence & Triggers")
            
            # Step 5: Competitor Intelligence
            pipeline_logger.info("🏢 Step 5/15: Competitor Analysis")
            competitor_intel_output, events = await get_agent_result(self.competitor_identification_agent, CompetitorIdentificationInput(initial_extracted_text=analyzed_lead.validated_lead.site_data.extracted_text_content or "", product_service_offered=", ".join(analysis_obj.main_services), known_competitors_list_str=self.competitors_list), "Identifying competitors")
            for event in events: yield event
            competitors_count = len(getattr(competitor_intel_output, 'identified_competitors', [])) if competitor_intel_output else 0
            pipeline_logger.info(f"✅ Competitor analysis completed: competitors_identified={competitors_count}")

            # Step 6: Purchase Triggers
            pipeline_logger.info("🔔 Step 6/15: Buying Trigger Identification")
            purchase_triggers_output, events = await get_agent_result(self.buying_trigger_identification_agent, BuyingTriggerIdentificationInput(lead_data_str=json.dumps(analyzed_lead.analysis.model_dump()), enriched_data=external_intel.tavily_enrichment if external_intel else "", product_service_offered=self.product_service_context), "Identifying buying triggers")
            for event in events: yield event
            triggers_count = len(getattr(purchase_triggers_output, 'identified_triggers', [])) if purchase_triggers_output else 0
            pipeline_logger.info(f"✅ Buying triggers completed: triggers_identified={triggers_count}")
            
            pipeline_logger.info("🚀 PHASE 4: Value Propositions & Strategic Planning")
            
            # Step 7: Value Propositions
            pipeline_logger.info("💎 Step 7/15: Value Proposition Customization")
            value_props_output, events = await get_agent_result(self.value_proposition_customization_agent, ValuePropositionCustomizationInput(lead_analysis=lead_analysis_str_for_agents, persona_profile=persona_profile_str, deepened_pain_points=deepened_pain_points_for_agents, buying_triggers_report=json.dumps([t.model_dump() for t in purchase_triggers_output.identified_triggers]) if purchase_triggers_output and purchase_triggers_output.identified_triggers else "[]", product_service_offered=self.product_service_context, company_name=company_name), "Customizing value propositions")
            for event in events: yield event
            value_props_count = len(getattr(value_props_output, 'custom_propositions', [])) if value_props_output else 0
            pipeline_logger.info(f"✅ Value propositions completed: propositions_created={value_props_count}")

            # Step 8: Strategic Questions
            pipeline_logger.info("❓ Step 8/15: Strategic Question Generation")
            strategic_questions_output, events = await get_agent_result(self.strategic_question_generation_agent, StrategicQuestionGenerationInput(lead_analysis=lead_analysis_str_for_agents, persona_profile=persona_profile_str, deepened_pain_points=deepened_pain_points_for_agents), "Generating strategic questions")
            for event in events: yield event
            questions_count = len(getattr(strategic_questions_output, 'generated_questions', [])) if strategic_questions_output else 0
            pipeline_logger.info(f"✅ Strategic questions completed: questions_generated={questions_count}")

            pipeline_logger.info("🚀 PHASE 5: Tree-of-Thought Strategy Development")
            
            # Prepare ToT summary
            current_lead_summary_for_tot = f"Empresa: {company_name} ({url})\nSetor: {analysis_obj.company_sector}\nPersona (Estimada): {persona_profile_str}\nDores: {pain_analysis_output.primary_pain_category if pain_analysis_output else 'N/A'}"
            pipeline_logger.debug(f"📋 ToT summary prepared, length: {len(current_lead_summary_for_tot)}")
            
            # Step 9: ToT Strategy Generation
            pipeline_logger.info("🌳 Step 9/15: Tree-of-Thought Strategy Generation")
            tot_generation_output, events = await get_agent_result(self.tot_strategy_generation_agent, ToTStrategyGenerationInput(current_lead_summary=current_lead_summary_for_tot, product_service_offered=self.product_service_context), "Generating ToT strategies")
            for event in events: yield event
            tot_strategies_count = len(getattr(tot_generation_output, 'proposed_strategies', [])) if tot_generation_output else 0
            pipeline_logger.info(f"✅ ToT strategy generation completed: strategies_proposed={tot_strategies_count}")

            # Step 10: ToT Strategy Evaluation
            pipeline_logger.info("🔍 Step 10/15: Tree-of-Thought Strategy Evaluation")
            tot_evaluation_output, events = await get_agent_result(self.tot_strategy_evaluation_agent, ToTStrategyEvaluationInput(proposed_strategies_text=json.dumps([s.model_dump() for s in tot_generation_output.proposed_strategies]) if tot_generation_output and tot_generation_output.proposed_strategies else "[]", current_lead_summary=current_lead_summary_for_tot), "Evaluating ToT strategies")
            for event in events: yield event
            tot_evaluated_count = len(getattr(tot_evaluation_output, 'evaluated_strategies', [])) if tot_evaluation_output else 0
            pipeline_logger.info(f"✅ ToT strategy evaluation completed: strategies_evaluated={tot_evaluated_count}")

            # Step 11: ToT Action Plan Synthesis
            pipeline_logger.info("🔧 Step 11/15: Tree-of-Thought Action Plan Synthesis")
            tot_synthesis_output, events = await get_agent_result(self.tot_action_plan_synthesis_agent, ToTActionPlanSynthesisInput(evaluated_strategies_text=json.dumps([e.model_dump() for e in tot_evaluation_output.evaluated_strategies]) if tot_evaluation_output and tot_evaluation_output.evaluated_strategies else "[]", proposed_strategies_text=json.dumps([s.model_dump() for s in tot_generation_output.proposed_strategies]) if tot_generation_output and tot_generation_output.proposed_strategies else "[]", current_lead_summary=current_lead_summary_for_tot), "Synthesizing ToT action plan")
            for event in events: yield event
            synthesis_success = tot_synthesis_output and not getattr(tot_synthesis_output, 'error_message', None)
            pipeline_logger.info(f"✅ ToT action plan synthesis completed: success={synthesis_success}")
            
            pipeline_logger.info("🚀 PHASE 6: Detailed Planning & Messaging")
            
            # Step 12: Detailed Approach Plan
            pipeline_logger.info("📋 Step 12/15: Detailed Approach Plan Development")
            detailed_approach_plan_output, events = await get_agent_result(self.detailed_approach_plan_agent, DetailedApproachPlanInput(lead_analysis=lead_analysis_str_for_agents, persona_profile=persona_profile_str, deepened_pain_points=deepened_pain_points_for_agents, final_action_plan_text=tot_synthesis_output.model_dump_json() if tot_synthesis_output else "{}", product_service_offered=self.product_service_context, lead_url=url), "Developing detailed approach plan")
            for event in events: yield event
            detailed_plan_success = detailed_approach_plan_output and not getattr(detailed_approach_plan_output, 'error_message', None)
            pipeline_logger.info(f"✅ Detailed approach plan completed: success={detailed_plan_success}")

            # Step 13: Objection Handling
            pipeline_logger.info("🛡️  Step 13/15: Objection Handling Preparation")
            objection_handling_output, events = await get_agent_result(self.objection_handling_agent, ObjectionHandlingInput(detailed_approach_plan_text=detailed_approach_plan_output.model_dump_json() if detailed_approach_plan_output else "{}", persona_profile=persona_profile_str, product_service_offered=self.product_service_context, company_name=company_name), "Preparing objection handling")
            for event in events: yield event
            objections_count = len(getattr(objection_handling_output, 'anticipated_objections', [])) if objection_handling_output else 0
            pipeline_logger.info(f"✅ Objection handling completed: objections_prepared={objections_count}")

            # Handle lead qualification mapping - rename confidence_score to qualification_score
            lead_qual_data = None
            if qualification_output:
                qual_dict = qualification_output.model_dump()
                # Map confidence_score to qualification_score if present
                if 'confidence_score' in qual_dict and qual_dict['confidence_score'] is not None:
                    qual_dict['qualification_score'] = qual_dict['confidence_score']
                else:
                    # Provide a default qualification_score based on tier
                    tier_map = {
                        'Alto Potencial': 0.9,
                        'Potencial Médio': 0.6,
                        'Baixo Potencial': 0.3,
                        'Não Qualificado': 0.1
                    }
                    qual_dict['qualification_score'] = tier_map.get(qual_dict.get('qualification_tier', ''), 0.5)
                lead_qual_data = qual_dict

            # Step 14: Personalized Message Generation
            pipeline_logger.info("💌 Step 14/15: Personalized Message Creation")
            personalized_message_output, events = await get_agent_result(self.b2b_personalized_message_agent, B2BPersonalizedMessageInput(final_action_plan_text=tot_synthesis_output.model_dump_json() if tot_synthesis_output else '{}', customized_value_propositions_text=json.dumps([p.model_dump() for p in value_props_output.custom_propositions]) if value_props_output and value_props_output.custom_propositions else '[]', contact_details=B2BContactDetailsInput(emails_found=contact_info.emails_found if contact_info else [], instagram_profiles_found=contact_info.instagram_profiles_found if contact_info else []), product_service_offered=self.product_service_context, lead_url=url, company_name=company_name, persona_fictional_name=persona_profile_str), "Crafting personalized message")
            for event in events: yield event
            message_channel = getattr(personalized_message_output, 'crafted_message_channel', 'N/A') if personalized_message_output else 'N/A'
            message_length = len(getattr(personalized_message_output, 'crafted_message_body', '')) if personalized_message_output else 0
            pipeline_logger.info(f"✅ Personalized message completed: channel={message_channel}, message_length={message_length}")
            
            # Construct enhanced strategy before final step
            pipeline_logger.info("🔧 Constructing enhanced strategy object")
            enhanced_strategy = EnhancedStrategy(
                external_intelligence=external_intel,
                contact_information=contact_info.model_dump() if contact_info else None,
                pain_point_analysis=pain_analysis_output.model_dump() if pain_analysis_output else None,
                competitor_intelligence=competitor_intel_output.model_dump() if competitor_intel_output else None,
                purchase_triggers=purchase_triggers_output.model_dump() if purchase_triggers_output else None,
                lead_qualification=lead_qual_data,
                tot_generated_strategies=[s.model_dump() for s in tot_generation_output.proposed_strategies] if tot_generation_output and tot_generation_output.proposed_strategies else [],
                tot_evaluated_strategies=[e.model_dump() for e in tot_evaluation_output.evaluated_strategies] if tot_evaluation_output and tot_evaluation_output.evaluated_strategies else [],
                tot_synthesized_action_plan=tot_synthesis_output.model_dump() if tot_synthesis_output else None,
                detailed_approach_plan=detailed_approach_plan_output.model_dump() if detailed_approach_plan_output else None,
                value_propositions=[p.model_dump() for p in value_props_output.custom_propositions] if value_props_output and value_props_output.custom_propositions else [],
                objection_framework=objection_handling_output.model_dump() if objection_handling_output else None,
                strategic_questions=strategic_questions_output.generated_questions if strategic_questions_output else []
            )
            
            # Step 15: Internal Briefing Summary
            pipeline_logger.info("📝 Step 15/15: Internal Briefing Summary")
            internal_briefing_output, events = await get_agent_result(self.internal_briefing_summary_agent, InternalBriefingSummaryInput(all_lead_data=enhanced_strategy.model_dump()), "Creating internal briefing")
            for event in events: yield event
            briefing_success = internal_briefing_output and not getattr(internal_briefing_output, 'error_message', None)
            pipeline_logger.info(f"✅ Internal briefing completed: success={briefing_success}")

            pipeline_logger.info("🚀 PHASE 7: Final Package Assembly")
            total_time = time.time() - start_time
            pipeline_logger.info(f"⏱️  Total pipeline execution time: {total_time:.2f} seconds")
            
            # Generate comprehensive pipeline summary
            pipeline_summary = {
                "tavily_enrichment": {"success": bool(tavily_output and not getattr(tavily_output, 'error_message', None)), "api_called": getattr(tavily_output, 'tavily_api_called', False)},
                "contact_extraction": {"success": bool(contact_info and not getattr(contact_info, 'error_message', None)), "emails": emails_found, "instagram": instagram_found},
                "pain_point_analysis": {"success": bool(pain_analysis_output and not getattr(pain_analysis_output, 'error_message', None)), "points_count": pain_points_count},
                "lead_qualification": {"success": bool(qualification_output and not getattr(qualification_output, 'error_message', None)), "tier": qual_tier, "confidence": qual_confidence},
                "competitor_analysis": {"success": bool(competitor_intel_output and not getattr(competitor_intel_output, 'error_message', None)), "competitors": competitors_count},
                "buying_triggers": {"success": bool(purchase_triggers_output and not getattr(purchase_triggers_output, 'error_message', None)), "triggers": triggers_count},
                "value_propositions": {"success": bool(value_props_output and not getattr(value_props_output, 'error_message', None)), "propositions": value_props_count},
                "strategic_questions": {"success": bool(strategic_questions_output and not getattr(strategic_questions_output, 'error_message', None)), "questions": questions_count},
                "tot_generation": {"success": bool(tot_generation_output and not getattr(tot_generation_output, 'error_message', None)), "strategies": tot_strategies_count},
                "tot_evaluation": {"success": bool(tot_evaluation_output and not getattr(tot_evaluation_output, 'error_message', None)), "evaluated": tot_evaluated_count},
                "tot_synthesis": {"success": synthesis_success},
                "detailed_plan": {"success": detailed_plan_success},
                "objection_handling": {"success": bool(objection_handling_output and not getattr(objection_handling_output, 'error_message', None)), "objections": objections_count},
                "personalized_message": {"success": bool(personalized_message_output and not getattr(personalized_message_output, 'error_message', None)), "channel": message_channel, "length": message_length},
                "internal_briefing": {"success": briefing_success}
            }
            
            # Calculate success metrics
            total_agents = len(pipeline_summary)
            successful_agents = sum(1 for agent_data in pipeline_summary.values() if agent_data["success"])
            success_rate = (successful_agents / total_agents) * 100
            
            pipeline_logger.info(f"📊 PIPELINE SUMMARY: {successful_agents}/{total_agents} agents successful ({success_rate:.1f}%)")
            pipeline_logger.info(f"🎯 Key metrics: contacts={emails_found + instagram_found}, pain_points={pain_points_count}, competitors={competitors_count}, triggers={triggers_count}")
            pipeline_logger.info(f"💎 Value outputs: propositions={value_props_count}, questions={questions_count}, strategies={tot_strategies_count}, objections={objections_count}")
            
            # Log any failed agents
            failed_agents = [name for name, data in pipeline_summary.items() if not data["success"]]
            if failed_agents:
                pipeline_logger.warning(f"⚠️  Failed agents: {', '.join(failed_agents)}")
            else:
                pipeline_logger.info("🎉 All agents completed successfully!")

            # Fix CommunicationChannel enum validation
            channel_value = personalized_message_output.crafted_message_channel.lower() if personalized_message_output and personalized_message_output.crafted_message_channel else "email"
            pipeline_logger.debug(f"📧 Channel validation: raw='{getattr(personalized_message_output, 'crafted_message_channel', 'N/A')}', normalized='{channel_value}'")
            
            # Validate and map channel to valid enum values
            if channel_value in ["n/a", "none", "", "unknown"]:
                channel_value = "email"  # Default fallback
                pipeline_logger.debug("📧 Using default email channel")
            elif channel_value not in ["email", "linkedin", "whatsapp", "phone"]:
                # Map common variations to valid channels
                if "linked" in channel_value or "linkedin" in channel_value:
                    channel_value = "linkedin"
                elif "whats" in channel_value or "zap" in channel_value:
                    channel_value = "whatsapp"
                elif "phone" in channel_value or "telefone" in channel_value or "tel" in channel_value:
                    channel_value = "phone"
                else:
                    channel_value = "email"  # Final fallback
                pipeline_logger.debug(f"📧 Mapped channel to: {channel_value}")
            
            pipeline_logger.info("📦 Assembling final comprehensive package")
            
            # Create personalization elements list
            personalization_elements = [
                f"Company: {company_name}",
                f"Channel: {channel_value}",
                f"Persona Context: {persona_profile_str[:100]}..." if persona_profile_str else "Generic approach",
                f"Pain Points: {pain_analysis_output.primary_pain_category}" if pain_analysis_output else "General business challenges",
                f"Value Props: {len(getattr(value_props_output, 'custom_propositions', []))} customized" if value_props_output else "Standard propositions"
            ]

            # Create primary message arguments
            primary_message_args = {
                "channel": CommunicationChannel(channel_value),
                "subject_line": personalized_message_output.crafted_message_subject if personalized_message_output else "Oportunidade de Parceria",
                "message_body": personalized_message_output.crafted_message_body if personalized_message_output else "Mensagem personalizada não disponível",
                "call_to_action": personalized_message_output.crafted_message_cta if hasattr(personalized_message_output, 'crafted_message_cta') and personalized_message_output and personalized_message_output.crafted_message_cta else "Entre em contato conosco",
                "personalization_elements": personalization_elements
            }
            
            primary_message = PersonalizedMessage(**primary_message_args)
            
            final_package = ComprehensiveProspectPackage(
                analyzed_lead=analyzed_lead,
                enhanced_strategy=enhanced_strategy,
                enhanced_personalized_message=EnhancedPersonalizedMessage(
                    primary_message=primary_message
                ),
                internal_briefing=internal_briefing_output,
                confidence_score=self._calculate_confidence_score(enhanced_strategy),
                roi_potential_score=self._calculate_roi_potential(enhanced_strategy),
                brazilian_market_fit=self._calculate_brazilian_fit(analyzed_lead),
                processing_metadata={"total_processing_time": total_time, "processing_mode": "enhanced", "tavily_enabled": bool(self.tavily_api_key), "company_name": company_name, "success_rate": success_rate, "pipeline_summary": pipeline_summary}
            )
            
            # Calculate final quality scores for logging
            final_confidence = self._calculate_confidence_score(enhanced_strategy)
            final_roi = self._calculate_roi_potential(enhanced_strategy)
            final_brazil_fit = self._calculate_brazilian_fit(analyzed_lead)
            
            pipeline_logger.info("🎉 ENRICHMENT PIPELINE COMPLETED SUCCESSFULLY!")
            pipeline_logger.info(f"📊 Final Quality Scores: confidence={final_confidence:.2f}, roi_potential={final_roi:.2f}, brazil_fit={final_brazil_fit:.2f}")
            pipeline_logger.info(f"⏱️  Total execution time: {total_time:.2f} seconds ({total_time/60:.1f} minutes)")
            pipeline_logger.info(f"📦 Final package size: {len(str(final_package.model_dump()))} characters")
            
            # Log detailed metrics summary
            pipeline_logger.info(f"🎯 ENRICHMENT RESULTS SUMMARY:")
            pipeline_logger.info(f"   • External Intelligence: {'✅' if external_intel.tavily_enrichment else '❌'} ({len(external_intel.tavily_enrichment)} chars)")
            pipeline_logger.info(f"   • Contact Information: {'✅' if emails_found + instagram_found > 0 else '❌'} ({emails_found + instagram_found} contacts)")
            pipeline_logger.info(f"   • Pain Point Analysis: {'✅' if pain_points_count > 0 else '❌'} ({pain_points_count} points, urgency: {getattr(pain_analysis_output, 'urgency_level', 'N/A')})")
            pipeline_logger.info(f"   • Lead Qualification: {'✅' if qual_tier != 'N/A' else '❌'} (tier: {qual_tier}, confidence: {qual_confidence})")
            pipeline_logger.info(f"   • Strategic Planning: {'✅' if synthesis_success else '❌'} ({tot_strategies_count} strategies → {tot_evaluated_count} evaluated)")
            pipeline_logger.info(f"   • Value Propositions: {'✅' if value_props_count > 0 else '❌'} ({value_props_count} propositions)")
            pipeline_logger.info(f"   • Personalized Message: {'✅' if message_length > 0 else '❌'} ({message_length} chars via {message_channel})")

            yield PipelineEndEvent(
                event_type="pipeline_end",
                timestamp=datetime.now().isoformat(),
                job_id=job_id,
                user_id=user_id,
                success=True,
                total_leads_generated=1,
                execution_time_seconds=total_time,
                data=final_package.model_dump()
            ).to_dict()

        except Exception as e:
            pipeline_logger.error(f"❌ ENRICHMENT PIPELINE FAILED: {e}")
            pipeline_logger.error(f"🔍 Exception details: {traceback.format_exc()}")
            pipeline_logger.error(f"⏱️  Failed after: {time.time() - start_time:.2f} seconds")
            
            yield PipelineErrorEvent(
                event_type="pipeline_error",
                timestamp=datetime.now().isoformat(),
                job_id=job_id,
                user_id=user_id,
                error_message=str(e),
                error_type=type(e).__name__
            ).to_dict()
            raise

    def process(self, analyzed_lead: AnalyzedLead) -> ComprehensiveProspectPackage:
        """
        DEPRECATED: Synchronous wrapper for the async pipeline.
        This method is not compatible with the new event-streaming architecture and will not return the final package.
        For streaming, call execute_enrichment_pipeline directly.
        """
        self.logger.warning("Executing enrichment pipeline synchronously. Event streaming is disabled.")
        
        async def run_sync():
            events = []
            final_result = None
            try:
                async for event in self.execute_enrichment_pipeline(analyzed_lead, "sync_job", "sync_user"):
                    if event.get("event_type") == "pipeline_end":
                        # Attempt to reconstruct the package from the final event
                        final_data = event.get("data", {})
                        return ComprehensiveProspectPackage(**final_data)
                    events.append(event)

                self.logger.warning("Synchronous execution finished, but no 'pipeline_end' event was found.")
                # Fallback for safety, though it shouldn't be reached in a successful run.
                return ComprehensiveProspectPackage(analyzed_lead=analyzed_lead)

            except Exception as e:
                self.logger.error(f"Synchronous execution failed: {e}")
                raise

        return asyncio.run(run_sync())
    
    # Helper methods
    
    def _analyze_agent_output(self, agent_name: str, output: Any) -> str:
        """Analyze agent output for logging purposes"""
        try:
            if not output:
                return "empty output"
            
            output_dict = output.model_dump() if hasattr(output, 'model_dump') else str(output)
            
            # Agent-specific analysis
            if agent_name == "TavilyEnrichmentAgent":
                tavily_called = getattr(output, 'tavily_api_called', False)
                data_length = len(getattr(output, 'enriched_data', ''))
                return f"tavily_called={tavily_called}, data_length={data_length}"
                
            elif agent_name == "ContactExtractionAgent":
                emails = len(getattr(output, 'emails_found', []))
                instagram = len(getattr(output, 'instagram_profiles_found', []))
                return f"emails={emails}, instagram={instagram}"
                
            elif agent_name == "PainPointDeepeningAgent":
                category = getattr(output, 'primary_pain_category', 'unknown')
                points_count = len(getattr(output, 'detailed_pain_points', []))
                urgency = getattr(output, 'urgency_level', 'unknown')
                return f"category={category}, points={points_count}, urgency={urgency}"
                
            elif agent_name == "LeadQualificationAgent":
                tier = getattr(output, 'qualification_tier', 'unknown')
                confidence = getattr(output, 'confidence_score', 'N/A')
                return f"tier={tier}, confidence={confidence}"
                
            elif agent_name == "ToTStrategyGenerationAgent":
                strategies_count = len(getattr(output, 'proposed_strategies', []))
                return f"strategies_generated={strategies_count}"
                
            elif agent_name == "ToTStrategyEvaluationAgent":
                evaluated_count = len(getattr(output, 'evaluated_strategies', []))
                return f"strategies_evaluated={evaluated_count}"
                
            elif agent_name == "ValuePropositionCustomizationAgent":
                props_count = len(getattr(output, 'custom_propositions', []))
                return f"value_propositions={props_count}"
                
            elif agent_name == "B2BPersonalizedMessageAgent":
                channel = getattr(output, 'crafted_message_channel', 'unknown')
                body_length = len(getattr(output, 'crafted_message_body', ''))
                return f"channel={channel}, message_length={body_length}"
                
            else:
                # Generic analysis
                field_count = len(output_dict) if isinstance(output_dict, dict) else 1
                return f"fields={field_count}"
                
        except Exception as e:
            return f"analysis_error={str(e)}"
    
    def _create_default_output_for_agent(self, agent_name: str, error_message: str) -> Any:
        """Create a default output object for failed agents"""
        try:
            # Import the output models
            if agent_name == "TavilyEnrichmentAgent":
                from .tavily_enrichment_agent import TavilyEnrichmentOutput
                return TavilyEnrichmentOutput(enriched_data="", tavily_api_called=False, error_message=error_message)
                
            elif agent_name == "ContactExtractionAgent":
                from .contact_extraction_agent import ContactExtractionOutput
                return ContactExtractionOutput(error_message=error_message)
                
            elif agent_name == "PainPointDeepeningAgent":
                from .pain_point_deepening_agent import PainPointDeepeningOutput
                return PainPointDeepeningOutput(error_message=error_message)
                
            elif agent_name == "LeadQualificationAgent":
                from .lead_qualification_agent import LeadQualificationOutput
                return LeadQualificationOutput(error_message=error_message)
                
            elif agent_name == "CompetitorIdentificationAgent":
                from .competitor_identification_agent import CompetitorIdentificationOutput
                return CompetitorIdentificationOutput(error_message=error_message)
                
            elif agent_name == "BuyingTriggerIdentificationAgent":
                from .buying_trigger_identification_agent import BuyingTriggerIdentificationOutput
                return BuyingTriggerIdentificationOutput(error_message=error_message)
                
            elif agent_name == "StrategicQuestionGenerationAgent":
                from .strategic_question_generation_agent import StrategicQuestionGenerationOutput
                return StrategicQuestionGenerationOutput(error_message=error_message)
                
            elif agent_name == "ToTStrategyGenerationAgent":
                from .tot_strategy_generation_agent import ToTStrategyGenerationOutput
                return ToTStrategyGenerationOutput(error_message=error_message)
                
            elif agent_name == "ToTStrategyEvaluationAgent":
                from .tot_strategy_evaluation_agent import ToTStrategyEvaluationOutput
                return ToTStrategyEvaluationOutput(error_message=error_message)
                
            elif agent_name == "ToTActionPlanSynthesisAgent":
                from .tot_action_plan_synthesis_agent import ToTActionPlanSynthesisOutput
                return ToTActionPlanSynthesisOutput(error_message=error_message)
                
            elif agent_name == "DetailedApproachPlanAgent":
                from .detailed_approach_plan_agent import DetailedApproachPlanOutput
                return DetailedApproachPlanOutput(error_message=error_message)
                
            elif agent_name == "ObjectionHandlingAgent":
                from .objection_handling_agent import ObjectionHandlingOutput
                return ObjectionHandlingOutput(error_message=error_message)
                
            elif agent_name == "ValuePropositionCustomizationAgent":
                from .value_proposition_customization_agent import ValuePropositionCustomizationOutput
                return ValuePropositionCustomizationOutput(error_message=error_message)
                
            elif agent_name == "B2BPersonalizedMessageAgent":
                from .b2b_personalized_message_agent import B2BPersonalizedMessageOutput
                return B2BPersonalizedMessageOutput(error_message=error_message)
                
            elif agent_name == "InternalBriefingSummaryAgent":
                from .internal_briefing_summary_agent import InternalBriefingSummaryOutput
                return InternalBriefingSummaryOutput(error_message=error_message)
                
            else:
                # Generic error object
                return {"error_message": error_message}
                
        except Exception as e:
            self.logger.error(f"Failed to create default output for {agent_name}: {e}")
            return {"error_message": f"Failed to create default output: {error_message}"}
    
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
