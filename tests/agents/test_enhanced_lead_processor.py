import unittest
from unittest.mock import MagicMock, patch, AsyncMock # Added AsyncMock
import json
from datetime import datetime

# Agent being tested
from agents.enhanced_lead_processor import EnhancedLeadProcessor

# Data models from lead_structures
from data_models.lead_structures import (
    AnalyzedLead, ValidatedLead, SiteData, LeadAnalysis, GoogleSearchData,
    ComprehensiveProspectPackage, EnhancedStrategy,
    ExternalIntelligence, ContactInformation, PainPointAnalysis, LeadQualification,
    CompetitorIntelligence, PurchaseTriggers, ValueProposition, ObjectionFramework,
    PersonalizedMessage, EnhancedPersonalizedMessage, InternalBriefing, CommunicationChannel,
    # Schemas that are now part of lead_structures and used by EnhancedStrategy
    DetailedPainPointSchema, CompetitorDetailSchema, IdentifiedTriggerSchema,
    ToTStrategyOptionModel, EvaluatedStrategyModel, ActionPlanStepModel, ToTActionPlanSynthesisModel,
    ContactStepDetailSchema, DetailedApproachPlanModel, ObjectionResponseModelSchema, InternalBriefingSectionSchema
)

# LLM Client base
from core_logic.llm_client import LLMClientBase, LLMResponse

# Input/Output models for ALL internal agents
from agents.tavily_enrichment_agent import TavilyEnrichmentAgent, TavilyEnrichmentInput, TavilyEnrichmentOutput
from agents.contact_extraction_agent import ContactExtractionAgent, ContactExtractionInput, ContactExtractionOutput
from agents.pain_point_deepening_agent import PainPointDeepeningAgent, PainPointDeepeningInput, PainPointDeepeningOutput, DetailedPainPoint
from agents.lead_qualification_agent import LeadQualificationAgent, LeadQualificationInput, LeadQualificationOutput
from agents.competitor_identification_agent import CompetitorIdentificationAgent, CompetitorIdentificationInput, CompetitorIdentificationOutput, CompetitorDetail
from agents.strategic_question_generation_agent import StrategicQuestionGenerationAgent, StrategicQuestionGenerationInput, StrategicQuestionGenerationOutput
from agents.buying_trigger_identification_agent import BuyingTriggerIdentificationAgent, BuyingTriggerIdentificationInput, BuyingTriggerIdentificationOutput, IdentifiedTrigger
from agents.tot_strategy_generation_agent import ToTStrategyGenerationAgent, ToTStrategyGenerationInput, ToTStrategyGenerationOutput # ToTStrategyOptionModel is defined here too
from agents.tot_strategy_evaluation_agent import ToTStrategyEvaluationAgent, ToTStrategyEvaluationInput, ToTStrategyEvaluationOutput # EvaluatedStrategyModel is here
from agents.tot_action_plan_synthesis_agent import ToTActionPlanSynthesisAgent, ToTActionPlanSynthesisInput, ToTActionPlanSynthesisOutput # ActionPlanStepModel is here
from agents.detailed_approach_plan_agent import DetailedApproachPlanAgent, DetailedApproachPlanInput, DetailedApproachPlanOutput # ContactStepDetail is here
from agents.objection_handling_agent import ObjectionHandlingAgent, ObjectionHandlingInput, ObjectionHandlingOutput # ObjectionResponseModel is here
from agents.value_proposition_customization_agent import ValuePropositionCustomizationAgent, ValuePropositionCustomizationInput, ValuePropositionCustomizationOutput # CustomValuePropModel is here
from agents.b2b_personalized_message_agent import B2BPersonalizedMessageAgent, B2BPersonalizedMessageInput, B2BPersonalizedMessageOutput, ContactDetailsInput as B2BContactDetailsInput
from agents.internal_briefing_summary_agent import InternalBriefingSummaryAgent, InternalBriefingSummaryInput, InternalBriefingSummaryOutput


class TestEnhancedLeadProcessor(unittest.IsolatedAsyncioTestCase): # Changed to IsolatedAsyncioTestCase

    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClientBase)
        self.mock_llm_client.get_usage_stats.return_value = {"total_tokens": 0, "input_tokens":0, "output_tokens":0}
        self.mock_llm_client.update_usage_stats = MagicMock()

        self.processor = EnhancedLeadProcessor(
            llm_client=self.mock_llm_client,
            product_service_context="Nosso Produto Incrível de Teste",
            competitors_list="Concorrente A, Concorrente B",
            tavily_api_key="test_tavily_key",
            mcp_server_url="http://mock-mcp-server.com",
            enable_mcp_reporting=True
        )
        # self.processor._report_agent_event_to_mcp = MagicMock() # Removed: Method no longer exists in EnhancedLeadProcessor

        # Mock all internal agents - now using AsyncMock for their execute methods
        self.processor.tavily_enrichment_agent = MagicMock(spec=TavilyEnrichmentAgent)
        self.processor.tavily_enrichment_agent.execute = AsyncMock()
        self.processor.contact_extraction_agent = MagicMock(spec=ContactExtractionAgent)
        self.processor.contact_extraction_agent.execute = AsyncMock()
        self.processor.pain_point_deepening_agent = MagicMock(spec=PainPointDeepeningAgent)
        self.processor.pain_point_deepening_agent.execute = AsyncMock()
        self.processor.lead_qualification_agent = MagicMock(spec=LeadQualificationAgent)
        self.processor.lead_qualification_agent.execute = AsyncMock()
        self.processor.competitor_identification_agent = MagicMock(spec=CompetitorIdentificationAgent)
        self.processor.competitor_identification_agent.execute = AsyncMock()
        self.processor.strategic_question_generation_agent = MagicMock(spec=StrategicQuestionGenerationAgent)
        self.processor.strategic_question_generation_agent.execute = AsyncMock()
        self.processor.buying_trigger_identification_agent = MagicMock(spec=BuyingTriggerIdentificationAgent)
        self.processor.buying_trigger_identification_agent.execute = AsyncMock()
        self.processor.tot_strategy_generation_agent = MagicMock(spec=ToTStrategyGenerationAgent)
        self.processor.tot_strategy_generation_agent.execute = AsyncMock()
        self.processor.tot_strategy_evaluation_agent = MagicMock(spec=ToTStrategyEvaluationAgent)
        self.processor.tot_strategy_evaluation_agent.execute = AsyncMock()
        self.processor.tot_action_plan_synthesis_agent = MagicMock(spec=ToTActionPlanSynthesisAgent)
        self.processor.tot_action_plan_synthesis_agent.execute = AsyncMock()
        self.processor.detailed_approach_plan_agent = MagicMock(spec=DetailedApproachPlanAgent)
        self.processor.detailed_approach_plan_agent.execute = AsyncMock()
        self.processor.objection_handling_agent = MagicMock(spec=ObjectionHandlingAgent)
        self.processor.objection_handling_agent.execute = AsyncMock()
        self.processor.value_proposition_customization_agent = MagicMock(spec=ValuePropositionCustomizationAgent)
        self.processor.value_proposition_customization_agent.execute = AsyncMock()
        self.processor.b2b_personalized_message_agent = MagicMock(spec=B2BPersonalizedMessageAgent)
        self.processor.b2b_personalized_message_agent.execute = AsyncMock()
        self.processor.internal_briefing_summary_agent = MagicMock(spec=InternalBriefingSummaryAgent)
        self.processor.internal_briefing_summary_agent.execute = AsyncMock()

    async def test_process_successful_orchestration(self):
        # 1. Prepare Input AnalyzedLead
        mock_site_data = SiteData(
            url="http://example.com",
            google_search_data=GoogleSearchData(title="Example Corp - Soluções Inovadoras", snippet="Líder em inovação."),
            extracted_text_content="Texto extraído do site da Example Corp sobre seus serviços e história.",
            extraction_status_message="SUCESSO NA EXTRAÇÃO",
            screenshot_filepath=None
        )
        mock_validated_lead = ValidatedLead(
            site_data=mock_site_data,
            is_valid=True,
            cleaned_text_content="Texto limpo do site da Example Corp.",
            extraction_successful=True
        )
        mock_lead_analysis = LeadAnalysis(
            company_sector="Tecnologia",
            main_services=["SaaS", "Consultoria em IA"],
            recent_activities=["Lançamento de novo produto"],
            potential_challenges=["Escalabilidade", "Concorrência acirrada"],
            company_size_estimate="Média",
            company_culture_values="Inovação, Foco no Cliente",
            relevance_score=0.85,
            general_diagnosis="Empresa promissora com desafios de crescimento.",
            opportunity_fit="Nossa solução de otimização pode ajudar a escalar.",
            ideal_customer_profile="Diretor de TI buscando eficiência e inovação."
        )
        analyzed_lead_input = AnalyzedLead(
            validated_lead=mock_validated_lead,
            analysis=mock_lead_analysis,
            product_service_context="Nosso Produto Incrível de Teste"
        )

        # 2. Configure Mock Agent Return Values (Pydantic Output Models)
        #    Using AsyncMock's return_value for agents that are awaited
        tavily_output = TavilyEnrichmentOutput(
            enriched_data="Dados enriquecidos da Example Corp via Tavily.", tavily_api_called=True
        )
        self.processor.tavily_enrichment_agent.execute.return_value = tavily_output

        contact_output = ContactExtractionOutput(
            emails_found=["contato@example.com"], instagram_profiles_found=["@examplecorp"], tavily_search_suggestion="Buscar decisores na Example Corp"
        )
        self.processor.contact_extraction_agent.execute.return_value = contact_output

        pain_output = PainPointDeepeningOutput(
            primary_pain_category="Escalabilidade de TI",
            detailed_pain_points=[DetailedPainPoint(pain_description="Infraestrutura atual não suporta crescimento.", business_impact="Perda de novos clientes.", solution_alignment="Nossa solução oferece auto-scaling.")],
            urgency_level="high",
            investigative_questions=["Como a falta de escalabilidade impactou seus SLAs?"]
        )
        self.processor.pain_point_deepening_agent.execute.return_value = pain_output

        qualification_output = LeadQualificationOutput(
            qualification_tier="Alto Potencial", justification="Forte alinhamento de dores e perfil.", confidence_score=0.9
        )
        self.processor.lead_qualification_agent.execute.return_value = qualification_output

        competitor_output = CompetitorIdentificationOutput(
            identified_competitors=[CompetitorDetail(name="CompInc", description="Principal concorrente.")], other_notes="Mercado competitivo."
        )
        self.processor.competitor_identification_agent.execute.return_value = competitor_output

        trigger_output = BuyingTriggerIdentificationOutput(
            identified_triggers=[IdentifiedTrigger(trigger_description="Anunciaram nova rodada de investimento.", relevance_explanation="Capital para novas soluções.")],
            other_observations="Parecem estar em fase de expansão."
        )
        self.processor.buying_trigger_identification_agent.execute.return_value = trigger_output

        value_prop_output = ValuePropositionCustomizationOutput(
            custom_propositions=[ValueProposition(title="Escale com Confiança", connection_to_pain_or_trigger="Para desafios de escalabilidade...", key_benefit="Reduza custos de infra em X%", differentiation_factor="Nossa IA proprietária.", call_to_value="Pronto para escalar?")]
        )
        self.processor.value_proposition_customization_agent.execute.return_value = value_prop_output

        strategic_q_output = StrategicQuestionGenerationOutput(
            generated_questions=["Como a Example Corp planeja lidar com o crescimento X nos próximos Y meses?"]
        )
        self.processor.strategic_question_generation_agent.execute.return_value = strategic_q_output

        mock_tot_generation_output = ToTStrategyGenerationOutput(
            proposed_strategies=[ToTStrategyOptionModel(strategy_name="Estratégia A", angle_or_hook="Foco na dor X", tone_of_voice="Consultivo", primary_channels=["Email"], key_points_or_arguments=["Ponto 1"], opening_question="Pergunta A?")]
        )
        self.processor.tot_strategy_generation_agent.execute.return_value = mock_tot_generation_output

        mock_tot_evaluation_output = ToTStrategyEvaluationOutput(
            evaluated_strategies=[EvaluatedStrategyModel(strategy_name="Estratégia A", suitability_assessment="Boa", strengths=["Forte"], weaknesses_or_risks=["Nenhum"], suggested_improvements=["Nenhuma"], confidence_score="Alta", confidence_justification="Faz sentido.")]
        )
        self.processor.tot_strategy_evaluation_agent.execute.return_value = mock_tot_evaluation_output

        mock_tot_synthesis_output = ToTActionPlanSynthesisOutput(
            recommended_strategy_name="Estratégia A (Refinada)", primary_angle_hook="Resolver dor X com Y", tone_of_voice="Consultivo",
            action_sequence=[ActionPlanStepModel(step_number=1, channel="Email", action_description="Enviar email focado.", key_message_or_argument="Benefício Z", cta="Call 15min")],
            key_talking_points=["ROI", "Facilidade"], main_opening_question="Como a dor X afeta Z?", success_metrics=["Resposta ao email"]
        )
        self.processor.tot_action_plan_synthesis_agent.execute.return_value = mock_tot_synthesis_output

        mock_detailed_plan_output = DetailedApproachPlanOutput(
            main_objective="Agendar reunião", adapted_elevator_pitch="Nós ajudamos com X, Y, Z.",
            contact_sequence=[ContactStepDetailSchema(step_number=1, channel="Email", objective="Introdução", key_topics_arguments=["Dor X"], key_questions=["Pergunta sobre X?"], cta="Call", supporting_materials="Case study A")]
        )
        self.processor.detailed_approach_plan_agent.execute.return_value = mock_detailed_plan_output

        objection_output = ObjectionHandlingOutput(
            anticipated_objections=[ObjectionResponseModelSchema(objection="Custo?", response_strategy="Foco no ROI", suggested_response="Retorno em X meses.")]
        )
        self.processor.objection_handling_agent.execute.return_value = objection_output

        message_output = B2BPersonalizedMessageOutput(
            crafted_message_channel="Email", crafted_message_subject="Oportunidade para Example Corp", crafted_message_body="Olá [Nome]..."
        )
        self.processor.b2b_personalized_message_agent.execute.return_value = message_output

        briefing_output = InternalBriefingSummaryOutput(
            executive_summary="Resumo: Lead Example Corp é promissor.",
            lead_overview=InternalBriefingSectionSchema(title="Visão Geral", content="..."), # Mock other sections as needed
            persona_profile_summary=InternalBriefingSectionSchema(title="Persona", content="..."),
            pain_points_and_needs=InternalBriefingSectionSchema(title="Dores", content="..."),
            buying_triggers_opportunity=InternalBriefingSectionSchema(title="Gatilhos", content="..."),
            lead_qualification_summary=InternalBriefingSectionSchema(title="Qualificação", content="..."),
            approach_strategy_summary=InternalBriefingSectionSchema(title="Estratégia", content="..."),
            custom_value_proposition_summary=InternalBriefingSectionSchema(title="VPs", content="..."),
            potential_objections_summary=InternalBriefingSectionSchema(title="Objeções", content="..."),
            recommended_next_step="Enviar email."
        )
        self.processor.internal_briefing_summary_agent.execute.return_value = briefing_output

        # 3. Execute EnhancedLeadProcessor.process
        package_output = await self.processor.process(
            analyzed_lead_input,
            lead_id="test_lead_id_123",
            run_id="test_run_id_456"
        )

        # 4. Assert Orchestration
        self.processor.tavily_enrichment_agent.execute.assert_called_once()
        self.processor.contact_extraction_agent.execute.assert_called_once()
        self.processor.pain_point_deepening_agent.execute.assert_called_once()
        # ... (assert_called_once for all other agents)
        self.processor.lead_qualification_agent.execute.assert_called_once()
        self.processor.competitor_identification_agent.execute.assert_called_once()
        self.processor.buying_trigger_identification_agent.execute.assert_called_once()
        self.processor.value_proposition_customization_agent.execute.assert_called_once()
        self.processor.strategic_question_generation_agent.execute.assert_called_once()
        self.processor.tot_strategy_generation_agent.execute.assert_called_once()
        self.processor.tot_strategy_evaluation_agent.execute.assert_called_once()
        self.processor.tot_action_plan_synthesis_agent.execute.assert_called_once()
        self.processor.detailed_approach_plan_agent.execute.assert_called_once()
        self.processor.objection_handling_agent.execute.assert_called_once()
        self.processor.b2b_personalized_message_agent.execute.assert_called_once()
        self.processor.internal_briefing_summary_agent.execute.assert_called_once()

        # Assertions for self.processor._report_agent_event_to_mcp removed, as this is now handled by BaseAgent.execute

        # 5. Assert Output ComprehensiveProspectPackage (selected fields)
        self.assertIsInstance(package_output, ComprehensiveProspectPackage)
        self.assertIsNotNone(package_output.enhanced_strategy)
        es = package_output.enhanced_strategy

        self.assertEqual(es.external_intelligence.tavily_enrichment, "Dados enriquecidos da Example Corp via Tavily.")
        self.assertIn("contato@example.com", es.contact_information.emails_found)
        self.assertEqual(es.pain_point_analysis.primary_pain_category, "Escalabilidade de TI")
        self.assertEqual(es.lead_qualification.qualification_tier, "Alto Potencial")

        self.assertIsNotNone(es.tot_synthesized_action_plan)
        self.assertEqual(es.tot_synthesized_action_plan.recommended_strategy_name, "Estratégia A (Refinada)")

        self.assertIsNotNone(package_output.enhanced_personalized_message)
        self.assertEqual(package_output.enhanced_personalized_message.primary_message.subject_line, "Oportunidade para Example Corp")

        self.assertIsNotNone(package_output.internal_briefing)
        self.assertEqual(package_output.internal_briefing.executive_summary, "Resumo: Lead Example Corp é promissor.")

        self.assertGreater(package_output.confidence_score, 0)
        self.assertGreater(package_output.roi_potential_score, 0)


if __name__ == '__main__':
    unittest.main()
