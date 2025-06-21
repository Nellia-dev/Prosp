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
import asyncio
from typing import Optional, Dict, Any, List, AsyncIterator
from datetime import datetime
from loguru import logger

try:
    import numpy as np
    import faiss
    from sentence_transformers import SentenceTransformer
    RAG_LIBRARIES_AVAILABLE = True
except ImportError:
    np = None
    faiss = None
    SentenceTransformer = None
    RAG_LIBRARIES_AVAILABLE = False

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
from .base_agent import BaseAgent
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
        event_queue: Optional[asyncio.Queue] = None,
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
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        if (not self.tavily_api_key and not tavily_api_key):
            raise ValueError("Tavily API key is required for this agent. Please set the TAVILY_API_KEY environment variable or pass it as an argument.")
        self.event_queue = event_queue
        self.logger = logger.bind(agent_name=self.name, agent_description=self.description)
        self.logger.info(f"Initializing EnhancedLeadProcessor with Tavily API key: {'set' if self.tavily_api_key else 'not set'}")

        self.embedding_model = None
        if RAG_LIBRARIES_AVAILABLE:
            try:
                self.logger.info("Loading SentenceTransformer model for RAG...")
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                self.logger.success("SentenceTransformer model loaded successfully.")
            except Exception as e:
                self.logger.warning(f"Failed to load SentenceTransformer model: {e}. RAG features will be disabled.")
        else:
            self.logger.warning("RAG libraries (numpy, faiss, sentence-transformers) not found. RAG features will be disabled.")

        # Initialize sub-agents, passing the LLM client and other necessary configs
        self.tavily_enrichment_agent = TavilyEnrichmentAgent(llm_client=self.llm_client, name="TavilyEnrichmentAgent", description="Gathers external intelligence and news about the company using the Tavily web search API.", tavily_api_key=self.tavily_api_key, event_queue=self.event_queue, user_id=self.user_id)
        self.contact_extraction_agent = ContactExtractionAgent(llm_client=self.llm_client, name="ContactExtractionAgent", description="Extracts contact information from lead's data.", event_queue=self.event_queue, user_id=self.user_id)
        self.pain_point_deepening_agent = PainPointDeepeningAgent(llm_client=self.llm_client, name="PainPointDeepeningAgent", description="Further analyzes and details the lead's potential pain points.", event_queue=self.event_queue, user_id=self.user_id)
        self.lead_qualification_agent = LeadQualificationAgent(llm_client=self.llm_client, name="LeadQualificationAgent", description="Qualifies the lead by assigning a tier and provides a justification.", event_queue=self.event_queue, user_id=self.user_id)
        self.competitor_identification_agent = CompetitorIdentificationAgent(llm_client=self.llm_client, name="CompetitorIdentificationAgent", description="Identifies potential competitors of the lead company.", event_queue=self.event_queue, user_id=self.user_id)
        self.strategic_question_generation_agent = StrategicQuestionGenerationAgent(llm_client=self.llm_client, name="StrategicQuestionGenerationAgent", description="Generates additional strategic, open-ended questions.", event_queue=self.event_queue, user_id=self.user_id)
        self.buying_trigger_identification_agent = BuyingTriggerIdentificationAgent(llm_client=self.llm_client, name="BuyingTriggerIdentificationAgent", description="Identifies events or signals that might indicate the lead is actively looking for solutions.", event_queue=self.event_queue, user_id=self.user_id)
        self.b2b_persona_creation_agent = B2BPersonaCreationAgent(llm_client=self.llm_client, name="B2BPersonaCreationAgent", description="Creates B2B persona profiles from lead data.", event_queue=self.event_queue, user_id=self.user_id)
        self.tot_strategy_generation_agent = ToTStrategyGenerationAgent(llm_client=self.llm_client, name="ToTStrategyGenerationAgent", description="Generates multiple distinct strategic approach options for the lead.", event_queue=self.event_queue, user_id=self.user_id)
        self.tot_strategy_evaluation_agent = ToTStrategyEvaluationAgent(llm_client=self.llm_client, name="ToTStrategyEvaluationAgent", description="Evaluates the generated strategic options.", event_queue=self.event_queue, user_id=self.user_id)
        self.tot_action_plan_synthesis_agent = ToTActionPlanSynthesisAgent(llm_client=self.llm_client, name="ToTActionPlanSynthesisAgent", description="Synthesizes the evaluated strategies into a single, refined action plan.", event_queue=self.event_queue, user_id=self.user_id)
        self.detailed_approach_plan_agent = DetailedApproachPlanAgent(llm_client=self.llm_client, name="DetailedApproachPlanAgent", description="Develops a detailed, step-by-step approach plan.", event_queue=self.event_queue, user_id=self.user_id)
        self.objection_handling_agent = ObjectionHandlingAgent(llm_client=self.llm_client, name="ObjectionHandlingAgent", description="Anticipates potential objections the lead might have.", event_queue=self.event_queue, user_id=self.user_id)
        self.value_proposition_customization_agent = ValuePropositionCustomizationAgent(llm_client=self.llm_client, name="ValuePropositionCustomizationAgent", description="Crafts customized value propositions.", event_queue=self.event_queue, user_id=self.user_id)
        self.b2b_personalized_message_agent = B2BPersonalizedMessageAgent(llm_client=self.llm_client, name="B2BPersonalizedMessageAgent", description="Generates personalized outreach messages.", event_queue=self.event_queue, user_id=self.user_id)
        self.internal_briefing_summary_agent = InternalBriefingSummaryAgent(llm_client=self.llm_client, name="InternalBriefingSummaryAgent", description="Generates a concise internal briefing summary.", event_queue=self.event_queue, user_id=self.user_id)
        self.event_stream = asyncio.Queue() # Placeholder for event stream

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
        lead_id = analyzed_lead.validated_lead.lead_id
        await self._emit_event("enrichment_start", {"lead_id": lead_id, "job_id": job_id})
        
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
            async def get_agent_result(agent, input_data, description):
                start_time = time.time()
                agent_name = agent.name
                events = []
                
                self.logger.info(f"Executing Agent: {agent_name} - {description}")
                input_json = input_data.model_dump_json()
                self.logger.debug(f"Agent '{agent_name}' input: {input_json[:1000] + ('...' if len(input_json) > 1000 else '')}")

                await self.event_stream.emit(AgentStartEvent(job_id=job_id, user_id=user_id, agent_name=agent_name, timestamp=datetime.now().isoformat()))
                events.append(AgentStartEvent(job_id=job_id, user_id=user_id, agent_name=agent_name, timestamp=datetime.now().isoformat()))

                output = None
                try:
                    output = await agent.execute(input_data)
                    if hasattr(output, 'error_message') and output.error_message:
                        self.logger.warning(f"Agent '{agent_name}' returned an error in its output: {output.error_message}")
                        raise Exception(output.error_message)
                    
                    analysis = self._analyze_agent_output(agent_name, output)
                    self.logger.success(f"Agent '{agent_name}' executed successfully in {time.time() - start_time:.2f}s. Analysis: {analysis}")

                except Exception as e:
                    error_message = f"Agent '{agent_name}' failed: {e}"
                    self.logger.error(error_message)
                    self.logger.debug(traceback.format_exc())
                    await self.event_stream.emit(PipelineErrorEvent(job_id=job_id, user_id=user_id, agent_name=agent_name, error=str(e), timestamp=datetime.now().isoformat()))
                    events.append(PipelineErrorEvent(job_id=job_id, user_id=user_id, agent_name=agent_name, error=str(e), timestamp=datetime.now().isoformat()))
                    
                    output = self._create_default_output_for_agent(agent_name, str(e))

                end_time = time.time()
                duration = end_time - start_time
                output_dump = output.model_dump() if output else {}
                await self.event_stream.emit(AgentEndEvent(job_id=job_id, user_id=user_id, agent_name=agent_name, timestamp=datetime.now().isoformat(), duration=duration, output=output_dump))
                events.append(AgentEndEvent(job_id=job_id, user_id=user_id, agent_name=agent_name, timestamp=datetime.now().isoformat(), duration=duration, output=output_dump))

                return output, events  

            analysis_obj = analyzed_lead.analysis
            persona_profile_str = self._construct_persona_profile_string(analysis_obj, company_name)

            # --- Execute Sub-Agents Sequentially ---
            pipeline_logger.info("🚀 PHASE 1: External Intelligence & Contact Extraction")
            
            # Step 1: Tavily Enrichment
            pipeline_logger.info("📡 Step 1/15: Tavily External Intelligence")
            tavily_input = TavilyEnrichmentInput(
                company_name=analyzed_lead.validated_lead.company_name,
                initial_extracted_text=analyzed_lead.validated_lead.website_text,
                product_service_description=self.product_service_description,
            )
            tavily_output = await self.tavily_enrichment_agent.process(
                lead_id=analyzed_lead.validated_lead.lead_id, input_data=tavily_input
            )
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
            self.logger.info("Constructing lead analysis and persona profile strings for subsequent agents.")
            lead_analysis_str_for_agents = self._construct_lead_analysis_string(analysis_obj, external_intel)
            self.logger.debug(f"Constructed lead_analysis_str_for_agents (first 500 chars): {lead_analysis_str_for_agents[:500]}")
            persona_profile_str = self._construct_persona_profile_string(analyzed_lead.analysis, company_name)
            self.logger.debug(f"Constructed persona_profile_str (first 500 chars): {persona_profile_str[:500]}")
            
            # Step 3: Pain Point Deepening
            pipeline_logger.info("🎯 Step 3/15: Pain Point Analysis")
            pain_analysis_output, events = await get_agent_result(self.pain_point_deepening_agent, PainPointDeepeningInput(lead_analysis=lead_analysis_str_for_agents, persona_profile=persona_profile_str, product_service_offered=self.product_service_context, company_name=company_name), "Deepening pain points")
            for event in events: yield event
            deepened_pain_points_for_agents = json.dumps(pain_analysis_output.model_dump(), ensure_ascii=False) if pain_analysis_output and not getattr(pain_analysis_output, 'error_message', None) else "Análise de dores não disponível."
            pain_points_count = len(getattr(pain_analysis_output, 'detailed_pain_points', [])) if pain_analysis_output else 0
            pipeline_logger.info(f"✅ Pain point analysis completed: category={getattr(pain_analysis_output, 'primary_pain_category', 'N/A')}, points={pain_points_count}")

            # Step 3.5: AI Prospect Intelligence RAG Analysis
            pipeline_logger.info("🧠 Step 3.5/15: AI Prospect Intelligence RAG Analysis")
            try:
                from ai_prospect_intelligence import AdvancedProspectProfiler
                
                # Initialize the RAG profiler
                prospect_profiler = AdvancedProspectProfiler()
                
                # Prepare enriched context for RAG analysis
                enriched_context = {
                    'business_offering': {
                        'description': self.product_service_context
                    },
                    'prospect_targeting': {
                        'ideal_customer_profile': persona_profile_str
                    },
                    'lead_qualification_criteria': {
                        'problems_we_solve': getattr(pain_analysis_output, 'detailed_pain_points', []) if pain_analysis_output else []
                    }
                }
                
                # Create RAG vector store from enriched context
                rag_vector_store = self._create_rag_vector_store(enriched_context, external_intel)
                
                # Generate advanced prospect profile using RAG
                ai_prospect_profile = prospect_profiler.create_advanced_prospect_profile(
                    lead_data=analyzed_lead.analysis.model_dump(),
                    enriched_context=enriched_context,
                    rag_vector_store=rag_vector_store
                )
                
                pipeline_logger.info(f"🧠 AI Prospect Intelligence completed: prospect_score={ai_prospect_profile.get('prospect_score', 'N/A')}, insights={len(ai_prospect_profile.get('predictive_insights', []))}")
                
            except Exception as e:
                pipeline_logger.warning(f"⚠️  AI Prospect Intelligence failed: {e}")
                ai_prospect_profile = {
                    'prospect_score': 0.5,
                    'buying_intent_score': 0.5,
                    'pain_alignment_score': 0.5,
                    'urgency_score': 0.5,
                    'predictive_insights': ['Análise RAG não disponível devido a erro técnico'],
                    'context_usage_summary': {'error': str(e)}
                }

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
            
            # Step 7: Value Propositions (Enhanced with AI Prospect Intelligence)
            pipeline_logger.info("💎 Step 7/15: Value Proposition Customization (AI-Enhanced)")
            
            # Enhance value propositions with AI prospect insights
            enhanced_pain_points = deepened_pain_points_for_agents
            if ai_prospect_profile.get('predictive_insights'):
                ai_insights_str = "\n".join([f"• {insight}" for insight in ai_prospect_profile['predictive_insights']])
                enhanced_pain_points += f"\n\nAI PROSPECT INSIGHTS (Score: {ai_prospect_profile.get('prospect_score', 'N/A')}):\n{ai_insights_str}"
            
            value_props_output, events = await get_agent_result(self.value_proposition_customization_agent, ValuePropositionCustomizationInput(lead_analysis=lead_analysis_str_for_agents, persona_profile=persona_profile_str, deepened_pain_points=enhanced_pain_points, buying_triggers_report=json.dumps([t.model_dump() for t in purchase_triggers_output.identified_triggers]) if purchase_triggers_output and purchase_triggers_output.identified_triggers else "[]", product_service_offered=self.product_service_context, company_name=company_name), "Customizing value propositions with AI insights")
            for event in events: yield event
            value_props_count = len(getattr(value_props_output, 'custom_propositions', [])) if value_props_output else 0
            pipeline_logger.info(f"✅ Value propositions completed: propositions_created={value_props_count}, ai_enhanced=True")

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
            
            personalized_message_output = None
            messages_count = 0
            message_channel = "N/A"
            total_message_length = 0
            
            # Check if there are any contact channels to generate a message for
            if contact_info and (contact_info.emails_found or contact_info.instagram_profiles_found):
                pipeline_logger.info(f"Found contact channels: {len(contact_info.emails_found)} emails, {len(contact_info.instagram_profiles_found)} Instagram. Generating one personalized message.")
                
                # Prepare shared inputs for the message agent
                final_action_plan_str = tot_synthesis_output.model_dump_json() if tot_synthesis_output else "{}"
                value_props_str = json.dumps([p.model_dump() for p in value_props_output.custom_propositions], ensure_ascii=False) if value_props_output and value_props_output.custom_propositions else "[]"

                # The B2BPersonalizedMessageAgent is designed to take all found contacts and determine the best channel itself.
                # We create one input object with all the lists of contacts.
                message_input = B2BPersonalizedMessageInput(
                    final_action_plan_text=final_action_plan_str,
                    customized_value_propositions_text=value_props_str,
                    contact_details=B2BContactDetailsInput(
                        emails_found=contact_info.emails_found,
                        instagram_profiles_found=contact_info.instagram_profiles_found
                        # Note: The B2B agent currently only supports email and Instagram.
                        # Other contacts from ContactExtractionAgent (phone, linkedin) are not used here.
                    ),
                    product_service_offered=self.product_service_context,
                    lead_url=url,
                    company_name=company_name,
                    persona_fictional_name=persona_profile_str # The agent uses the fictional persona name for personalization
                )
                
                b2b_persona_output = await self.b2b_persona_creation_agent.process(
                lead_id=analyzed_lead.validated_lead.lead_id,
                input_data=message_input,
            )
                
                personalized_message_output, events = await get_agent_result(
                    self.b2b_personalized_message_agent,
                    message_input,
                    f"Crafting personalized message for {company_name}"
                )
                for event in events: yield event

                # Log the result of the single message generation
                if personalized_message_output and not personalized_message_output.error_message:
                    messages_count = 1
                    message_channel = personalized_message_output.crafted_message_channel
                    total_message_length = len(personalized_message_output.crafted_message_body)
                    pipeline_logger.info(f"✅ Personalized message completed: 1 message generated for channel '{message_channel}', length={total_message_length}")
                else:
                    error_msg = personalized_message_output.error_message if personalized_message_output else "Agent returned no output."
                    pipeline_logger.warning(f"⚠️ Personalized message generation failed: {error_msg}")
            
            else:
                pipeline_logger.warning("No suitable contacts (email or Instagram) found, skipping personalized message generation.")
            
            # Construct enhanced strategy before final step
            pipeline_logger.info("🔧 Constructing enhanced strategy object")
            enhanced_strategy = EnhancedStrategy(
                external_intelligence=external_intel,
                contact_information=contact_info.model_dump() if contact_info else None,
                pain_point_analysis=pain_analysis_output.model_dump() if pain_analysis_output else None,
                competitor_intelligence=competitor_intel_output.model_dump() if competitor_intel_output else None,
                purchase_triggers=purchase_triggers_output.model_dump() if purchase_triggers_output else None,
                lead_qualification=qualification_output.model_dump() if qualification_output else None,
                tot_generated_strategies=[s.model_dump() for s in tot_generation_output.proposed_strategies] if tot_generation_output and tot_generation_output.proposed_strategies else [],
                tot_evaluated_strategies=[e.model_dump() for e in tot_evaluation_output.evaluated_strategies] if tot_evaluation_output and tot_evaluation_output.evaluated_strategies else [],
                tot_synthesized_action_plan=tot_synthesis_output.model_dump() if tot_synthesis_output else None,
                detailed_approach_plan=detailed_approach_plan_output.model_dump() if detailed_approach_plan_output else None,
                value_propositions=[p.model_dump() for p in value_props_output.custom_propositions] if value_props_output and value_props_output.custom_propositions else [],
                objection_framework=objection_handling_output.model_dump() if objection_handling_output else None,
                strategic_questions=strategic_questions_output.generated_questions if strategic_questions_output else []
            )
            
            # Step 15: Internal Briefing Summary (Enhanced with AI Insights & Engagement Instructions)
            pipeline_logger.info("📝 Step 15/15: Internal Briefing Summary (AI-Enhanced)")
            
            # Prepare comprehensive lead data with AI insights for briefing
            comprehensive_lead_data = enhanced_strategy.model_dump()
            
            # Add AI Prospect Intelligence insights
            comprehensive_lead_data['ai_prospect_intelligence'] = {
                'prospect_score': ai_prospect_profile.get('prospect_score', 0.5),
                'buying_intent_score': ai_prospect_profile.get('buying_intent_score', 0.5),
                'pain_alignment_score': ai_prospect_profile.get('pain_alignment_score', 0.5),
                'urgency_score': ai_prospect_profile.get('urgency_score', 0.5),
                'predictive_insights': ai_prospect_profile.get('predictive_insights', []),
                'context_usage_summary': ai_prospect_profile.get('context_usage_summary', {})
            }
            
            # Add engagement readiness assessment
            engagement_readiness = self._calculate_engagement_readiness(ai_prospect_profile, enhanced_strategy)
            comprehensive_lead_data['engagement_readiness'] = engagement_readiness
            
            # Add recommended engagement strategy
            recommended_engagement = self._generate_engagement_instructions(
                ai_prospect_profile, enhanced_strategy, personalized_message_output, company_name
            )
            comprehensive_lead_data['recommended_engagement_strategy'] = recommended_engagement
            
            internal_briefing_output, events = await get_agent_result(self.internal_briefing_summary_agent, InternalBriefingSummaryInput(all_lead_data=comprehensive_lead_data), "Creating AI-enhanced internal briefing with engagement instructions")
            for event in events: yield event
            briefing_success = internal_briefing_output and not getattr(internal_briefing_output, 'error_message', None)
            pipeline_logger.info(f"✅ Internal briefing completed: success={briefing_success}, ai_enhanced=True, engagement_ready={engagement_readiness['ready']}")

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
                "personalized_message": {"success": messages_count > 0, "channel": message_channel, "messages_generated": messages_count, "total_length": total_message_length},
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
            
            # Create enhanced final package with AI insights
            final_package = ComprehensiveProspectPackage(
                analyzed_lead=analyzed_lead,
                enhanced_strategy=enhanced_strategy,
                enhanced_personalized_message=EnhancedPersonalizedMessage(
                    primary_message=primary_message
                ),
                internal_briefing=internal_briefing_output,
                confidence_score=self._calculate_confidence_score_with_ai(enhanced_strategy, ai_prospect_profile),
                roi_potential_score=self._calculate_roi_potential_with_ai(enhanced_strategy, ai_prospect_profile),
                processing_metadata={
                    "total_processing_time": total_time,
                    "processing_mode": "enhanced_with_ai_intelligence",
                    "tavily_enabled": bool(self.tavily_api_key),
                    "company_name": company_name,
                    "success_rate": success_rate,
                    "pipeline_summary": pipeline_summary,
                    "ai_prospect_intelligence": ai_prospect_profile,
                    "engagement_readiness": comprehensive_lead_data.get('engagement_readiness', {}),
                    "recommended_engagement": comprehensive_lead_data.get('recommended_engagement_strategy', {})
                }
            )
            
            # Calculate final quality scores for logging
            final_confidence = self._calculate_confidence_score(enhanced_strategy)
            final_roi = self._calculate_roi_potential(enhanced_strategy)
            
            pipeline_logger.info("🎉 ENRICHMENT PIPELINE COMPLETED SUCCESSFULLY!")
            pipeline_logger.info(f"📊 Final Quality Scores: confidence={final_confidence:.2f}, roi_potential={final_roi:.2f}")
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
            pipeline_logger.info(f"   • Personalized Message: {'✅' if total_message_length > 0 else '❌'} ({total_message_length} chars via {message_channel})")

            # Final event to signal completion
            final_event = {
                "event_type": "pipeline_end",
                "timestamp": datetime.now().isoformat(),
                "job_id": job_id,
                "user_id": user_id,
                "lead_id": analyzed_lead.validated_lead.lead_id,
                "data": final_package.model_dump(),
                "status": "completed"
            }
            await self._emit_event("enrichment_end", {"lead_id": lead_id, "job_id": job_id, "package": final_package.model_dump()})
            yield final_event

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
        It is maintained for compatibility with older parts of the system that may not be async yet.
        """
        self.logger.warning("Executing enrichment pipeline synchronously. Event streaming is disabled.")
        
        async def run_sync():
            final_package = None
            try:
                async for event in self.execute_enrichment_pipeline(analyzed_lead, "sync_job", "sync_user"):
                    if event.get("event_type") == "pipeline_end":
                        # Attempt to reconstruct the package from the final event
                        final_data = event.get("data", {})
                        if final_data:
                            final_package = ComprehensiveProspectPackage(**final_data)
                        break # Exit after getting the final package
            except Exception as e:
                self.logger.error(f"Synchronous execution failed: {e}")
                raise
            return final_package

        return asyncio.run(run_sync())

    def _extract_company_name(self, analyzed_lead: AnalyzedLead) -> str:
        # Simple implementation, can be made more robust
        if analyzed_lead.analysis and analyzed_lead.analysis.company_name:
            return analyzed_lead.analysis.company_name
        # Fallback logic if company_name is not in analysis
        # This could involve parsing the URL or other data
        if analyzed_lead.validated_lead and analyzed_lead.validated_lead.site_data and analyzed_lead.validated_lead.site_data.url:
            try:
                from urllib.parse import urlparse
                domain = urlparse(str(analyzed_lead.validated_lead.site_data.url)).netloc
                # simple domain to name logic
                company_name = domain.replace('www.', '').split('.')[0].capitalize()
                return company_name
            except Exception:
                return "Unknown Company"
        return "Unknown Company"

    def _create_rag_vector_store(self, enriched_context: Dict, external_intel: ExternalIntelligence) -> Dict:
        """Creates a RAG vector store from enriched context and external intelligence."""
        self.logger.info("Creating RAG vector store...")
        if not self.embedding_model or not RAG_LIBRARIES_AVAILABLE:
            self.logger.warning("RAG components not available. Skipping vector store creation.")
            return {}

        # 1. Flatten context into a list of text paragraphs
        paragraphs = []
        if self.product_service_context:
            paragraphs.append(f"Contexto do Produto/Serviço: {self.product_service_context}")
        
        if enriched_context:
            if enriched_context.get('prospect_targeting', {}).get('ideal_customer_profile'):
                paragraphs.append(f"Perfil do Cliente Ideal: {enriched_context['prospect_targeting']['ideal_customer_profile']}")
            
            pains = enriched_context.get('lead_qualification_criteria', {}).get('problems_we_solve', [])
            if pains:
                pain_text = ". ".join([p.get('pain_point', '') for p in pains if isinstance(p, dict) and p.get('pain_point')])
                if pain_text:
                    paragraphs.append(f"Dores que resolvemos: {pain_text}")

        if external_intel and external_intel.tavily_enrichment:
            paragraphs.append(f"Inteligência Externa (Tavily): {external_intel.tavily_enrichment}")

        if not paragraphs:
            self.logger.warning("No text content available to create RAG vector store.")
            return {}
        
        self.logger.info(f"Collected {len(paragraphs)} paragraphs for RAG context.")

        # 2. Chunk the text
        text_chunks = self._chunk_text(paragraphs)
        if not text_chunks:
            self.logger.warning("Text chunking resulted in no chunks.")
            return {}
        self.logger.info(f"Chunked text into {len(text_chunks)} chunks.")

        # 3. Generate embeddings
        embeddings = self.embedding_model.encode(text_chunks, show_progress_bar=False)
        if embeddings is None:
            self.logger.error("Failed to generate embeddings.")
            return {}
        
        # 4. Create FAISS index (if available)
        faiss_index = None
        if faiss:
            try:
                dimension = embeddings.shape[1]
                faiss_index = faiss.IndexFlatL2(dimension)
                faiss_index.add(np.array(embeddings, dtype=np.float32))
                self.logger.success(f"FAISS index created successfully with {faiss_index.ntotal} vectors.")
            except Exception as e:
                self.logger.error(f"Failed to create FAISS index: {e}", exc_info=True)
                faiss_index = None # Ensure it's None on failure

        vector_store = {
            "chunks": text_chunks,
            "embeddings": embeddings,
            "faiss_index": faiss_index
        }
        self.logger.success("RAG vector store created successfully.")
        return vector_store

    def _calculate_engagement_readiness(self, ai_profile: Dict, strategy: EnhancedStrategy) -> Dict:
        """
        Calculates engagement readiness based on AI profile and strategy quality.
        """
        readiness_score = 0.0
        reasons = []

        prospect_score = ai_profile.get('prospect_score', 0.5)
        urgency_score = ai_profile.get('urgency_score', 0.5)
        confidence = self._calculate_confidence_score_with_ai(strategy, ai_profile)

        # Weighted average
        readiness_score = (prospect_score * 0.4) + (urgency_score * 0.3) + (confidence * 0.3)
        
        if readiness_score > 0.75:
            reasons.append("High prospect score, urgency, and confidence in strategy.")
        elif readiness_score > 0.5:
            reasons.append("Moderate prospect score and/or urgency. Strategy is sound.")
        else:
            reasons.append("Low prospect score or urgency. Proceed with caution.")
            
        if not strategy.personalized_messages:
            reasons.append("Personalized messages are not yet generated.")
            readiness_score *= 0.8 # Penalize if messages are missing

        return {"ready": readiness_score > 0.6, "score": round(readiness_score, 2), "reason": " ".join(reasons)}

    def _generate_engagement_instructions(self, ai_profile: Dict, strategy: EnhancedStrategy, message_output: Any, company_name: str) -> Dict:
        """
        Generates next-step instructions for the sales team.
        """
        instructions = {
            "next_step": "Review the complete prospect package before taking action.",
            "talking_points": [],
            "suggested_channel": "Email",
            "key_insight": "N/A"
        }

        if strategy.detailed_approach_plan and strategy.detailed_approach_plan.contact_steps:
            first_step = strategy.detailed_approach_plan.contact_steps[0]
            instructions["next_step"] = f"Initiate Step 1: {first_step.step_title} via {first_step.channel}."
            instructions["suggested_channel"] = first_step.channel

        if ai_profile.get('predictive_insights'):
            instructions["key_insight"] = ai_profile['predictive_insights'][0]
        
        if strategy.value_propositions:
            for vp in strategy.value_propositions[:2]:
                instructions["talking_points"].append(f"VP: {vp.value_proposition_title}")

        if strategy.objection_handling and strategy.objection_handling.anticipated_objections:
            first_objection = strategy.objection_handling.anticipated_objections[0]
            instructions["talking_points"].append(f"Be prepared for objection: '{first_objection.objection}'")

        return instructions

    def _calculate_confidence_score_with_ai(self, strategy: EnhancedStrategy, ai_profile: Dict) -> float:
        """Calculates confidence score, boosted by AI prospect profile."""
        base_score = self._calculate_confidence_score(strategy)
        ai_prospect_score = ai_profile.get('prospect_score', 0.5)
        
        # AI score contributes up to 20% of the final score
        ai_boost = (ai_prospect_score - 0.5) * 0.4 # Scale to be between -0.2 and 0.2
        
        final_score = base_score + ai_boost
        return max(0.0, min(1.0, final_score))

    def _calculate_roi_potential_with_ai(self, strategy: EnhancedStrategy, ai_profile: Dict) -> float:
        """Calculates ROI potential, boosted by AI buying intent score."""
        base_roi = self._calculate_roi_potential(strategy)
        buying_intent_score = ai_profile.get('buying_intent_score', 0.5)
        
        # Buying intent contributes up to 30%
        ai_boost = (buying_intent_score - 0.5) * 0.6 # Scale to be between -0.3 and 0.3
        
        final_roi = base_roi + ai_boost
        return max(0.0, min(1.0, final_roi))

    def _calculate_confidence_score(self, strategy: EnhancedStrategy) -> float:
        """
        Calculates a base confidence score based on the completeness of the strategy.
        """
        if not strategy:
            return 0.1
        
        score = 0.5 # Base score
        if strategy.value_propositions:
            score += 0.15
        if strategy.objection_handling:
            score += 0.15
        if strategy.detailed_approach_plan:
            score += 0.2
            
        return min(1.0, score)

    def _calculate_roi_potential(self, strategy: EnhancedStrategy) -> float:
        """
        Calculates a base ROI potential score.
        A real implementation would be more sophisticated.
        """
        if not strategy:
            return 0.1
            
        # Simple logic: more detailed plans suggest higher potential
        score = 0.4
        if strategy.detailed_approach_plan and strategy.detailed_approach_plan.contact_steps:
            score += 0.1 * len(strategy.detailed_approach_plan.contact_steps)
        
        if strategy.value_propositions:
            score += 0.1 * len(strategy.value_propositions)
            
        return min(1.0, score)

    
    # Helper methods
    
    def _chunk_text(self, paragraphs: List[str], chunk_size: int = 500) -> List[str]:
        """Chunks text into smaller pieces."""
        chunks = []
        current_chunk = ""
        for p in paragraphs:
            if len(current_chunk) + len(p) + 2 > chunk_size and current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            current_chunk += ("\n\n" if current_chunk else "") + p
        if current_chunk:
            chunks.append(current_chunk)
        return chunks

    
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
    
    def _calculate_confidence_score_with_ai(self, enhanced_strategy: EnhancedStrategy, ai_prospect_profile: dict) -> float:
        """Calculate enhanced confidence score incorporating AI insights"""
        # Original confidence calculation
        base_confidence = self._calculate_confidence_score(enhanced_strategy)
        
        # AI prospect intelligence boost
        ai_prospect_score = ai_prospect_profile.get('prospect_score', 0.5)
        ai_pain_alignment = ai_prospect_profile.get('pain_alignment_score', 0.5)
        ai_buying_intent = ai_prospect_profile.get('buying_intent_score', 0.5)
        
        # Weight AI insights (30% of total score)
        ai_score = (ai_prospect_score + ai_pain_alignment + ai_buying_intent) / 3
        ai_weighted = ai_score * 0.3
        
        # Combine with traditional confidence (70% weight)
        traditional_weighted = base_confidence * 0.7
        
        # Bonus for having predictive insights
        insights_bonus = 0.05 if ai_prospect_profile.get('predictive_insights') else 0
        
        total_confidence = traditional_weighted + ai_weighted + insights_bonus
        return min(total_confidence, 1.0)

    def _calculate_confidence_score(self, enhanced_strategy: EnhancedStrategy) -> float:
        """Calculate overall confidence score (traditional method)"""
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
    
    def _calculate_roi_potential_with_ai(self, enhanced_strategy: EnhancedStrategy, ai_prospect_profile: dict) -> float:
        """Calculate enhanced ROI potential incorporating AI insights"""
        # Original ROI calculation
        base_roi = self._calculate_roi_potential(enhanced_strategy)
        
        # AI insights for ROI enhancement
        ai_buying_intent = ai_prospect_profile.get('buying_intent_score', 0.5)
        ai_urgency = ai_prospect_profile.get('urgency_score', 0.5)
        ai_pain_alignment = ai_prospect_profile.get('pain_alignment_score', 0.5)
        
        # Calculate AI ROI multiplier
        ai_roi_factors = (ai_buying_intent + ai_urgency + ai_pain_alignment) / 3
        
        # Higher AI scores suggest better ROI potential
        if ai_roi_factors >= 0.8:
            roi_multiplier = 1.2  # 20% boost for high AI scores
        elif ai_roi_factors >= 0.6:
            roi_multiplier = 1.1  # 10% boost for medium AI scores
        else:
            roi_multiplier = 1.0  # No change for low AI scores
        
        enhanced_roi = base_roi * roi_multiplier
        return min(enhanced_roi, 1.0)
    
    def _calculate_roi_potential(self, enhanced_strategy: EnhancedStrategy) -> float:
        """Calculate ROI potential score (traditional method)"""
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
    
    def _create_rag_vector_store(self, enriched_context: dict, external_intel: ExternalIntelligence) -> dict:
        """Create RAG vector store for AI Prospect Intelligence"""
        try:
            import numpy as np
            
            # Prepare text chunks for vector store
            chunks = []
            
            # Add business context chunks
            if enriched_context.get('business_offering', {}).get('description'):
                chunks.append(f"Business Offering: {enriched_context['business_offering']['description']}")
            
            if enriched_context.get('prospect_targeting', {}).get('ideal_customer_profile'):
                chunks.append(f"Target Customer Profile: {enriched_context['prospect_targeting']['ideal_customer_profile']}")
            
            # Add problem-solving context
            problems = enriched_context.get('lead_qualification_criteria', {}).get('problems_we_solve', [])
            if problems:
                for problem in problems:
                    if hasattr(problem, 'pain_description'):
                        chunks.append(f"Problem We Solve: {problem.pain_description}")
                    elif isinstance(problem, str):
                        chunks.append(f"Problem We Solve: {problem}")
            
            # Add external intelligence
            if external_intel and external_intel.tavily_enrichment:
                chunks.append(f"Market Intelligence: {external_intel.tavily_enrichment}")
            
            # Create simple vector store (basic implementation)
            try:
                from sentence_transformers import SentenceTransformer
                import faiss
                
                # Initialize embedding model
                model = SentenceTransformer('all-MiniLM-L6-v2')
                
                # Generate embeddings
                embeddings = model.encode(chunks)
                embeddings = embeddings.astype('float32')
                
                # Create FAISS index
                dimension = embeddings.shape[1]
                index = faiss.IndexFlatL2(dimension)
                index.add(embeddings)
                
                return {
                    "index": index,
                    "chunks": chunks,
                    "embeddings": embeddings
                }
                
            except ImportError:
                self.logger.warning("FAISS or SentenceTransformers not available, using simple text store")
                return {
                    "index": None,
                    "chunks": chunks,
                    "embeddings": None
                }
                
        except Exception as e:
            self.logger.error(f"Failed to create RAG vector store: {e}")
            return {"index": None, "chunks": [], "embeddings": None}

    def _calculate_engagement_readiness(self, ai_prospect_profile: dict, enhanced_strategy: EnhancedStrategy) -> dict:
        """Calculate engagement readiness based on AI insights and strategy completeness"""
        
        prospect_score = ai_prospect_profile.get('prospect_score', 0.5)
        buying_intent = ai_prospect_profile.get('buying_intent_score', 0.5)
        pain_alignment = ai_prospect_profile.get('pain_alignment_score', 0.5)
        urgency = ai_prospect_profile.get('urgency_score', 0.5)
        
        # Check strategy completeness
        has_contact_info = bool(enhanced_strategy.contact_information)
        has_value_props = bool(enhanced_strategy.value_propositions)
        has_strategy = bool(enhanced_strategy.tot_synthesized_action_plan)
        has_approach_plan = bool(enhanced_strategy.detailed_approach_plan)
        
        # Calculate readiness score
        ai_score = (prospect_score + buying_intent + pain_alignment + urgency) / 4
        strategy_score = sum([has_contact_info, has_value_props, has_strategy, has_approach_plan]) / 4
        
        overall_readiness = (ai_score * 0.7) + (strategy_score * 0.3)
        
        # Determine readiness level
        if overall_readiness >= 0.8:
            readiness_level = "HIGH"
            recommendation = "Proceed with immediate engagement"
        elif overall_readiness >= 0.6:
            readiness_level = "MEDIUM"
            recommendation = "Good prospect - proceed with engagement"
        elif overall_readiness >= 0.4:
            readiness_level = "LOW"
            recommendation = "Consider nurturing campaign first"
        else:
            readiness_level = "NOT_READY"
            recommendation = "Requires additional research and qualification"
        
        return {
            "ready": readiness_level in ["HIGH", "MEDIUM"],
            "readiness_level": readiness_level,
            "readiness_score": round(overall_readiness, 3),
            "ai_score": round(ai_score, 3),
            "strategy_completeness": round(strategy_score, 3),
            "recommendation": recommendation,
            "key_factors": {
                "prospect_score": prospect_score,
                "buying_intent": buying_intent,
                "pain_alignment": pain_alignment,
                "urgency": urgency,
                "has_contact_info": has_contact_info,
                "has_value_props": has_value_props,
                "has_strategy": has_strategy,
                "has_approach_plan": has_approach_plan
            }
        }

    def _generate_engagement_instructions(
        self,
        ai_prospect_profile: dict,
        enhanced_strategy: EnhancedStrategy,
        personalized_message_output: Any,
        company_name: str
    ) -> dict:
        """Generate clear engagement instructions based on AI insights and strategy"""
        
        # Extract key insights
        predictive_insights = ai_prospect_profile.get('predictive_insights', [])
        prospect_score = ai_prospect_profile.get('prospect_score', 0.5)
        urgency = ai_prospect_profile.get('urgency_score', 0.5)
        
        # Determine engagement priority
        if prospect_score >= 0.8 and urgency >= 0.7:
            priority = "URGENT"
            timing = "Within 24 hours"
        elif prospect_score >= 0.7:
            priority = "HIGH"
            timing = "Within 48 hours"
        elif prospect_score >= 0.5:
            priority = "MEDIUM"
            timing = "Within 1 week"
        else:
            priority = "LOW"
            timing = "When capacity allows"
        
        # Extract channel and message info
        channel = getattr(personalized_message_output, 'crafted_message_channel', 'Email')
        has_message = bool(getattr(personalized_message_output, 'crafted_message_body', ''))
        
        # Generate step-by-step instructions
        engagement_steps = []
        
        if has_message:
            engagement_steps.append({
                "step": 1,
                "action": f"Send personalized {channel.lower()} message",
                "details": f"Use the crafted {channel.lower()} message with personalized subject line",
                "timing": timing,
                "expected_outcome": "Initial response or engagement"
            })
        
        engagement_steps.append({
            "step": 2,
            "action": "Monitor engagement signals",
            "details": "Track email opens, link clicks, social media engagement",
            "timing": "Immediate after send",
            "expected_outcome": "Engagement metrics and response indicators"
        })
        
        engagement_steps.append({
            "step": 3,
            "action": "Follow-up sequence",
            "details": "Execute the detailed approach plan sequence (LinkedIn connection, content sharing, etc.)",
            "timing": "2-3 days after initial contact",
            "expected_outcome": "Continued engagement and conversation"
        })
        
        engagement_steps.append({
            "step": 4,
            "action": "Qualification call",
            "details": "Schedule discovery call to validate AI insights and explore specific needs",
            "timing": "After positive engagement",
            "expected_outcome": "Qualified opportunity or nurture decision"
        })
        
        # Generate talking points from AI insights
        talking_points = []
        for insight in predictive_insights[:3]:  # Top 3 insights
            talking_points.append(f"• {insight}")
        
        return {
            "priority": priority,
            "recommended_timing": timing,
            "primary_channel": channel,
            "engagement_steps": engagement_steps,
            "key_talking_points": talking_points,
            "success_metrics": [
                "Response rate to initial outreach",
                "Engagement with follow-up content",
                "Meeting/call acceptance rate",
                "Qualification score improvement"
            ],
            "risk_factors": [
                f"Urgency score is {'high' if urgency >= 0.7 else 'medium' if urgency >= 0.5 else 'low'}",
                f"Pain alignment is {'strong' if ai_prospect_profile.get('pain_alignment_score', 0) >= 0.7 else 'moderate'}"
            ],
            "next_review_date": "After initial engagement sequence completion",
            "backup_strategy": "If no response after 3 touchpoints, move to nurture campaign with educational content"
        }

    
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
