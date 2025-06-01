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
    ToTStrategyOption,
    ToTStrategyEvaluation,
    EnhancedPersonalizedMessage,
    PersonalizedMessage,
    InternalBriefing,
    CommunicationChannel
)
from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

class EnhancedLeadProcessor(BaseAgent[AnalyzedLead, ComprehensiveProspectPackage]):
    """
    Enhanced lead processor that incorporates all advanced features:
    - Tavily API enrichment
    - Contact extraction
    - Deep pain point analysis
    - Tree-of-Thought strategy generation
    - Competitive intelligence
    - Purchase trigger identification
    """
    
    def __init__(
        self,
        llm_client: LLMClientBase,
        product_service_context: str = "",
        competitors_list: str = "",
        tavily_api_key: Optional[str] = None,
        temperature: float = 0.7
    ):
        super().__init__(llm_client, temperature)
        self.agent_name = "EnhancedLeadProcessor"
        self.logger = logger  # Initialize logger from loguru import
        
        self.product_service_context = product_service_context
        self.competitors_list = competitors_list
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
        
        # Processing configuration
        self.max_text_length = 15000
        self.tavily_max_results = 2
        self.tavily_max_queries = 3
        
    def process(self, analyzed_lead: AnalyzedLead) -> ComprehensiveProspectPackage:
        """
        Process analyzed lead through enhanced intelligence pipeline
        """
        start_time = time.time()
        url = str(analyzed_lead.validated_lead.site_data.url)
        company_name = self._extract_company_name(analyzed_lead)
        
        self.logger.info(f"Enhanced processing for: {url}")
        
        try:
            # Step 1: Gather external intelligence
            self.logger.info("Step 1: Gathering external intelligence")
            external_intel = self._gather_external_intelligence(company_name, analyzed_lead)
            
            # Step 2: Extract contact information
            self.logger.info("Step 2: Extracting contact information")
            contact_info = self._extract_contact_information(analyzed_lead)
            
            # Step 3: Deep pain point analysis
            self.logger.info("Step 3: Analyzing pain points")
            pain_analysis = self._analyze_pain_points(analyzed_lead, external_intel)
            
            # Step 4: Lead qualification
            self.logger.info("Step 4: Qualifying lead")
            qualification = self._qualify_lead(analyzed_lead, pain_analysis)
            
            # Step 5: Competitor intelligence
            self.logger.info("Step 5: Gathering competitor intelligence")
            competitor_intel = self._analyze_competitors(analyzed_lead)
            
            # Step 6: Purchase triggers
            self.logger.info("Step 6: Identifying purchase triggers")
            purchase_triggers = self._identify_purchase_triggers(analyzed_lead, external_intel)
            
            # Step 7: Custom value propositions
            self.logger.info("Step 7: Creating custom value propositions")
            value_props = self._create_value_propositions(analyzed_lead, pain_analysis)
            
            # Step 8: Strategic questions
            self.logger.info("Step 8: Generating strategic questions")
            strategic_questions = self._generate_strategic_questions(analyzed_lead, pain_analysis)
            
            # Step 9: Objection handling
            self.logger.info("Step 9: Preparing objection handling")
            objection_handling = self._prepare_objection_handling(analyzed_lead, competitor_intel)
            
            # Step 10: Tree-of-Thought strategy
            self.logger.info("Step 10: Tree-of-Thought strategy analysis")
            tot_strategy = self._generate_tot_strategy(analyzed_lead, value_props, pain_analysis)
            
            # Create enhanced strategy
            enhanced_strategy = EnhancedStrategy(
                external_intelligence=external_intel,
                contact_information=contact_info,
                pain_point_analysis=pain_analysis,
                competitor_intelligence=competitor_intel,
                purchase_triggers=purchase_triggers,
                lead_qualification=qualification,
                tot_strategy_evaluation=tot_strategy,
                value_propositions=value_props,
                objection_framework=objection_handling,
                strategic_questions=strategic_questions
            )
            
            # Step 11: Create personalized message
            self.logger.info("Step 11: Creating personalized message")
            personalized_message = self._create_personalized_message(analyzed_lead, enhanced_strategy)
            
            # Step 12: Internal briefing
            self.logger.info("Step 12: Creating internal briefing")
            internal_briefing = self._create_internal_briefing(analyzed_lead, enhanced_strategy)
            
            # Calculate processing metadata
            total_time = time.time() - start_time
            
            # Create final package
            final_package = ComprehensiveProspectPackage(
                analyzed_lead=analyzed_lead,
                enhanced_strategy=enhanced_strategy,
                enhanced_personalized_message=personalized_message,
                internal_briefing=internal_briefing,
                confidence_score=self._calculate_confidence_score(enhanced_strategy),
                roi_potential_score=self._calculate_roi_potential(enhanced_strategy),
                brazilian_market_fit=self._calculate_brazilian_fit(analyzed_lead),
                processing_metadata={
                    "total_processing_time": total_time,
                    "processing_mode": "enhanced",
                    "tavily_enabled": bool(self.tavily_api_key),
                    "company_name": company_name
                }
            )
            
            self.logger.info(f"Enhanced processing completed for {company_name} in {total_time:.2f}s")
            return final_package
            
        except Exception as e:
            self.logger.error(f"Enhanced processing failed for {url}: {e}")
            raise
    
    def _gather_external_intelligence(self, company_name: str, analyzed_lead: AnalyzedLead) -> ExternalIntelligence:
        """Gather external intelligence using Tavily API"""
        
        if not self.tavily_api_key:
            return ExternalIntelligence(
                tavily_enrichment="Tavily API key not configured",
                sources_used=["None - API key missing"]
            )
        
        # Check if enrichment is needed
        text_content = analyzed_lead.validated_lead.site_data.extracted_text_content or ""
        needs_enrichment = (
            len(text_content) < 700 or
            "FALHA NA EXTRAÇÃO" in text_content or
            not text_content.strip()
        )
        
        if not needs_enrichment:
            return ExternalIntelligence(
                tavily_enrichment="Enrichment not needed - sufficient original data",
                sources_used=["Original site content"]
            )
        
        try:
            # Generate search queries
            queries = [
                f"{company_name} recent news Brazil",
                f"{company_name} funding investment",
                f"{company_name} expansion hiring"
            ][:self.tavily_max_queries]
            
            all_results = []
            sources = []
            
            for query in queries:
                results = self._search_tavily(query)
                all_results.extend(results)
                sources.extend([r.get('url', 'Unknown') for r in results])
                time.sleep(0.5)  # Rate limiting
            
            if not all_results:
                return ExternalIntelligence(
                    tavily_enrichment="No results found from Tavily search",
                    sources_used=["Tavily API - no results"]
                )
            
            # Summarize findings with LLM
            enrichment_summary = self._summarize_tavily_results(company_name, all_results)
            
            return ExternalIntelligence(
                tavily_enrichment=enrichment_summary,
                market_research=f"External research for {company_name}",
                news_analysis=f"Recent developments for {company_name}",
                sources_used=list(set(sources)),
                enrichment_confidence=0.8 if all_results else 0.2
            )
            
        except Exception as e:
            self.logger.warning(f"Tavily enrichment failed: {e}")
            return ExternalIntelligence(
                tavily_enrichment=f"Enrichment failed: {str(e)}",
                sources_used=["Error"]
            )
    
    def _search_tavily(self, query: str) -> List[Dict[str, Any]]:
        """Search using Tavily API"""
        try:
            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.tavily_api_key,
                    "query": query,
                    "search_depth": "basic",
                    "include_answer": False,
                    "max_results": self.tavily_max_results
                },
                timeout=20
            )
            response.raise_for_status()
            return response.json().get("results", [])
        except Exception as e:
            self.logger.warning(f"Tavily search failed for '{query}': {e}")
            return []
    
    def _summarize_tavily_results(self, company_name: str, results: List[Dict[str, Any]]) -> str:
        """Summarize Tavily results using LLM"""
        
        content_parts = []
        for result in results:
            content = f"Source: {result.get('url', 'N/A')}\n"
            content += f"Title: {result.get('title', 'N/A')}\n"
            content += f"Content: {self._truncate_text(result.get('content', 'N/A'), 800)}\n"
            content_parts.append(content)
        
        combined_content = "\n\n---\n\n".join(content_parts)
        
        prompt = f"""Você é um Analista de Inteligência de Mercado.

Resuma os insights mais relevantes sobre "{company_name}" das seguintes fontes externas:

{self._truncate_text(combined_content, self.max_text_length - 1000)}

Foque em:
1. Notícias ou desenvolvimentos recentes
2. Financiamento, crescimento ou sinais de expansão
3. Atividade de contratação ou mudanças organizacionais
4. Iniciativas estratégicas ou desafios

Forneça um resumo conciso em português, destacando 2-3 insights-chave que seriam relevantes para abordagem de vendas B2B.
Se os dados não forem relevantes ou insuficientes, declare "Dados externos não forneceram insights adicionais significativos."
"""
        
        response = self.llm_client.generate(prompt)
        return response.content if response.content else "Failed to summarize external intelligence"
    
    def _extract_contact_information(self, analyzed_lead: AnalyzedLead) -> ContactInformation:
        """Extract contact information from site content"""
        
        text_content = analyzed_lead.validated_lead.cleaned_text_content or ""
        company_name = self._extract_company_name(analyzed_lead)
        
        prompt = f"""Você é um Especialista em Extração de Informações de Contato.

Analise o seguinte conteúdo do site para "{company_name}" e extraia informações de contato:

Conteúdo do texto (primeiros {self.max_text_length} chars):
{self._truncate_text(text_content, self.max_text_length)}

Extraia e retorne APENAS um objeto JSON válido com:
{{
    "emails_found": ["email1@domain.com", "email2@domain.com"],
    "instagram_profiles": ["https://instagram.com/profile"],
    "linkedin_profiles": ["https://linkedin.com/company/profile"],
    "phone_numbers": ["+55 11 99999-9999"],
    "tavily_search_suggestions": ["termo de busca 1", "termo de busca 2"],
    "extraction_confidence": 0.0-1.0
}}

Priorize emails comerciais (contato@, vendas@, comercial@) sobre pessoais.
Retorne arrays vazios se nenhum contato for encontrado.
"""
        
        try:
            response = self.llm_client.generate(prompt)
            contact_data = self._parse_response(response.content)
            
            return ContactInformation(
                emails_found=contact_data.get("emails_found", []),
                instagram_profiles=contact_data.get("instagram_profiles", []),
                linkedin_profiles=contact_data.get("linkedin_profiles", []),
                phone_numbers=contact_data.get("phone_numbers", []),
                tavily_search_suggestions=contact_data.get("tavily_search_suggestions", [f"Search for '{company_name} contato'"]),
                extraction_confidence=float(contact_data.get("extraction_confidence", 0.3))
            )
            
        except Exception as e:
            self.logger.warning(f"Contact extraction failed: {e}")
            return ContactInformation(
                tavily_search_suggestions=[f"Manual search recommended for '{company_name}' contacts"],
                extraction_confidence=0.0
            )
    
    def _analyze_pain_points(self, analyzed_lead: AnalyzedLead, external_intel: ExternalIntelligence) -> PainPointAnalysis:
        """Deep analysis of company pain points"""
        
        analysis = analyzed_lead.analysis
        company_name = self._extract_company_name(analyzed_lead)
        
        prompt = f"""Você é um Especialista em Análise de Pontos de Dor para vendas B2B.

Analise as seguintes informações da empresa para identificar pontos de dor detalhados:

Empresa: {company_name}
Setor: {analysis.company_sector}
Serviços: {', '.join(analysis.main_services)}
Desafios Atuais: {', '.join(analysis.potential_challenges)}
Inteligência Externa: {external_intel.tavily_enrichment}
Nosso Produto/Serviço: {self.product_service_context}

Para cada ponto de dor, forneça análise detalhada. Retorne JSON válido:
{{
    "primary_pain_category": "Categoria principal dos pontos de dor",
    "detailed_pain_points": [
        {{
            "pain_description": "Descrição específica da dor",
            "business_impact": "Como isso impacta operações/receita",
            "solution_alignment": "Como nossa solução aborda essa dor"
        }}
    ],
    "urgency_level": "low|medium|high|critical",
    "investigative_questions": ["Pergunta para confirmar essa dor", "Outra pergunta"],
    "potential_solutions_alignment": {{
        "pain1": "como nossa solução se alinha",
        "pain2": "outro alinhamento"
    }}
}}

Identifique 3-5 pontos de dor específicos que nossa solução possa abordar.
"""
        
        try:
            response = self.llm_client.generate(prompt)
            pain_data = self._parse_response(response.content)
            
            return PainPointAnalysis(
                primary_pain_category=pain_data.get("primary_pain_category", "Otimização de Processos"),
                detailed_pain_points=pain_data.get("detailed_pain_points", []),
                business_impact_assessment=f"Impact analysis for {company_name}",
                urgency_level=pain_data.get("urgency_level", "medium"),
                investigative_questions=pain_data.get("investigative_questions", []),
                potential_solutions_alignment=pain_data.get("potential_solutions_alignment", {})
            )
            
        except Exception as e:
            self.logger.warning(f"Pain point analysis failed: {e}")
            return PainPointAnalysis(
                primary_pain_category="Desafios Comerciais Genéricos",
                detailed_pain_points=[],
                business_impact_assessment="Standard business impact",
                urgency_level="medium"
            )
    
    def _qualify_lead(self, analyzed_lead: AnalyzedLead, pain_analysis: PainPointAnalysis) -> LeadQualification:
        """Qualify the lead based on all available information"""
        
        analysis = analyzed_lead.analysis
        
        # Calculate qualification score based on multiple factors
        relevance_weight = analysis.relevance_score * 0.4
        pain_weight = len(pain_analysis.detailed_pain_points) * 0.1
        urgency_weight = {"low": 0.1, "medium": 0.2, "high": 0.3, "critical": 0.4}.get(pain_analysis.urgency_level, 0.2)
        
        qualification_score = min(relevance_weight + pain_weight + urgency_weight, 1.0)
        
        # Determine tier based on score
        if qualification_score >= 0.8:
            tier = "High Potential"
        elif qualification_score >= 0.6:
            tier = "Medium Potential"
        elif qualification_score >= 0.4:
            tier = "Low Potential"
        else:
            tier = "Not Qualified"
        
        return LeadQualification(
            qualification_tier=tier,
            qualification_score=qualification_score,
            qualification_reasoning=[
                f"Relevance score: {analysis.relevance_score}",
                f"Pain points identified: {len(pain_analysis.detailed_pain_points)}",
                f"Urgency level: {pain_analysis.urgency_level}"
            ],
            fit_score=analysis.relevance_score,
            readiness_score=urgency_weight * 2.5,  # Convert to 0-1 scale
            authority_score=0.5,  # Default, would need more analysis
            budget_likelihood="unknown"
        )
    
    def _analyze_competitors(self, analyzed_lead: AnalyzedLead) -> CompetitorIntelligence:
        """Analyze competitor mentions and alternative solutions"""
        
        text_content = analyzed_lead.validated_lead.cleaned_text_content or ""
        
        prompt = f"""Você é um Analista de Inteligência Competitiva.

Analise o conteúdo do site em busca de menções de concorrentes ou soluções alternativas:

Nossa Solução: {self.product_service_context}
Concorrentes Conhecidos: {self.competitors_list or "Não especificado"}

Conteúdo do Site:
{self._truncate_text(text_content, self.max_text_length)}

Retorne JSON válido:
{{
    "mentioned_competitors": ["concorrente1", "concorrente2"],
    "current_solutions": ["solução1", "solução2"],
    "competitive_advantages": ["nossa vantagem 1", "nossa vantagem 2"],
    "market_positioning": "posição no mercado",
    "switching_barriers": ["barreira1", "barreira2"],
    "competitive_threats": ["ameaça1", "ameaça2"]
}}

Procure nomes diretos de concorrentes, parceiros tecnológicos ou soluções incumbentes.
"""
        
        try:
            response = self.llm_client.generate(prompt)
            comp_data = self._parse_response(response.content)
            
            return CompetitorIntelligence(
                mentioned_competitors=comp_data.get("mentioned_competitors", []),
                current_solutions=comp_data.get("current_solutions", []),
                competitive_advantages=comp_data.get("competitive_advantages", []),
                market_positioning=comp_data.get("market_positioning"),
                switching_barriers=comp_data.get("switching_barriers", []),
                competitive_threats=comp_data.get("competitive_threats", [])
            )
            
        except Exception as e:
            self.logger.warning(f"Competitor analysis failed: {e}")
            return CompetitorIntelligence()
    
    def _identify_purchase_triggers(self, analyzed_lead: AnalyzedLead, external_intel: ExternalIntelligence) -> PurchaseTriggers:
        """Identify purchase trigger events"""
        
        analysis = analyzed_lead.analysis
        
        prompt = f"""Você é um Especialista em Análise de Gatilhos de Compra.

Identifique eventos que poderiam desencadear decisões de compra:

Atividades Recentes: {', '.join(analysis.recent_activities)}
Inteligência Externa: {external_intel.tavily_enrichment}
Nossa Solução: {self.product_service_context}

Retorne JSON válido:
{{
    "recent_events": ["evento1", "evento2"],
    "market_signals": ["sinal1", "sinal2"],
    "timing_indicators": ["indicador1", "indicador2"],
    "growth_signals": ["crescimento1", "crescimento2"],
    "urgency_drivers": ["urgência1", "urgência2"],
    "budget_cycle_insights": "insights sobre ciclo orçamentário"
}}

Procure financiamento, expansão, contratações, mudanças tecnológicas, necessidades de compliance.
"""
        
        try:
            response = self.llm_client.generate(prompt)
            trigger_data = self._parse_response(response.content)
            
            return PurchaseTriggers(
                recent_events=trigger_data.get("recent_events", []),
                market_signals=trigger_data.get("market_signals", []),
                timing_indicators=trigger_data.get("timing_indicators", []),
                growth_signals=trigger_data.get("growth_signals", []),
                urgency_drivers=trigger_data.get("urgency_drivers", []),
                budget_cycle_insights=trigger_data.get("budget_cycle_insights")
            )
            
        except Exception as e:
            self.logger.warning(f"Purchase trigger analysis failed: {e}")
            return PurchaseTriggers()
    
    def _create_value_propositions(self, analyzed_lead: AnalyzedLead, pain_analysis: PainPointAnalysis) -> List[ValueProposition]:
        """Create custom value propositions"""
        
        company_name = self._extract_company_name(analyzed_lead)
        
        prompt = f"""Você é um Especialista em Proposições de Valor Customizadas.

Crie proposições de valor específicas para {company_name}:

Pontos de Dor Identificados: {pain_analysis.detailed_pain_points}
Nossa Solução: {self.product_service_context}
Categoria Principal de Dor: {pain_analysis.primary_pain_category}

Crie 2-3 proposições de valor customizadas. Retorne JSON válido:
{{
    "value_propositions": [
        {{
            "proposition_text": "Declaração da proposição de valor",
            "target_pain_points": ["dor1", "dor2"],
            "quantified_benefits": ["benefício mensurável 1", "benefício mensurável 2"],
            "proof_points": ["prova 1", "prova 2"],
            "differentiation_factors": ["diferencial 1", "diferencial 2"]
        }}
    ]
}}
"""
        
        try:
            response = self.llm_client.generate(prompt)
            value_data = self._parse_response(response.content)
            
            value_props = []
            for prop_data in value_data.get("value_propositions", []):
                value_props.append(ValueProposition(
                    proposition_text=prop_data.get("proposition_text", ""),
                    target_pain_points=prop_data.get("target_pain_points", []),
                    quantified_benefits=prop_data.get("quantified_benefits", []),
                    proof_points=prop_data.get("proof_points", []),
                    differentiation_factors=prop_data.get("differentiation_factors", [])
                ))
            
            return value_props
            
        except Exception as e:
            self.logger.warning(f"Value proposition creation failed: {e}")
            return [ValueProposition(
                proposition_text=f"Solução customizada para {company_name}",
                target_pain_points=[pain_analysis.primary_pain_category],
                quantified_benefits=["Aumento de eficiência"],
                proof_points=["Experiência comprovada"],
                differentiation_factors=["Foco no mercado brasileiro"]
            )]
    
    def _generate_strategic_questions(self, analyzed_lead: AnalyzedLead, pain_analysis: PainPointAnalysis) -> List[str]:
        """Generate strategic discovery questions"""
        
        base_questions = [
            f"Como vocês lidam atualmente com {pain_analysis.primary_pain_category.lower()}?",
            "Qual é o principal desafio que vocês enfrentam nesta área?",
            "Que impacto isso tem nos resultados da empresa?"
        ]
        
        # Add pain-specific questions
        for pain_point in pain_analysis.detailed_pain_points[:2]:
            if isinstance(pain_point, dict) and "pain_description" in pain_point:
                base_questions.append(f"Vocês já tentaram resolver {pain_point['pain_description'].lower()}?")
        
        return base_questions[:5]  # Limit to 5 questions
    
    def _prepare_objection_handling(self, analyzed_lead: AnalyzedLead, competitor_intel: CompetitorIntelligence) -> ObjectionFramework:
        """Prepare objection handling strategies"""
        
        common_objections = {
            "Custo muito alto": "Vamos analisar o ROI específico para sua situação",
            "Já temos uma solução": "Entendo. Como está funcionando a solução atual?",
            "Não é prioridade agora": "Compreendo. Quando seria um bom momento para revisitar isso?",
            "Preciso conversar com a equipe": "Perfeito. Que informações posso fornecer para facilitar essa conversa?"
        }
        
        return ObjectionFramework(
            common_objections=common_objections,
            objection_categories=["Orçamento", "Timing", "Autoridade", "Necessidade"],
            response_templates=common_objections,
            escalation_strategies=[
                "Agendar call com tomadores de decisão",
                "Fornecer case studies relevantes",
                "Propor piloto ou POC"
            ]
        )
    
    def _generate_tot_strategy(self, analyzed_lead: AnalyzedLead, value_props: List[ValueProposition], pain_analysis: PainPointAnalysis) -> ToTStrategyEvaluation:
        """Generate Tree-of-Thought strategy"""
        
        company_name = self._extract_company_name(analyzed_lead)
        
        # Create strategy options
        strategy_options = [
            ToTStrategyOption(
                strategy_name="Abordagem Consultiva",
                strategy_rationale="Foco em entender desafios específicos",
                primary_channel="email",
                key_hook="Insights sobre otimização para empresas do setor",
                success_probability="Alto - 70%",
                pros=["Baixa pressão", "Constrói relacionamento"],
                cons=["Processo mais longo", "Pode não criar urgência"]
            ),
            ToTStrategyOption(
                strategy_name="Demonstração de Valor",
                strategy_rationale="Mostrar benefícios específicos rapidamente",
                primary_channel="linkedin",
                key_hook="Case study relevante do setor",
                success_probability="Médio - 50%",
                pros=["Demonstra valor rapidamente", "Diferenciação clara"],
                cons=["Pode parecer muito vendedor", "Requer preparação"]
            )
        ]
        
        # Select best strategy based on pain urgency
        if pain_analysis.urgency_level in ["high", "critical"]:
            selected = strategy_options[1]  # Demonstration approach for urgent needs
        else:
            selected = strategy_options[0]  # Consultative for others
        
        return ToTStrategyEvaluation(
            strategy_options=strategy_options,
            selected_strategy=selected,
            evaluation_criteria=["Urgência da dor", "Complexidade da venda", "Canal preferido"],
            decision_rationale=f"Selecionado baseado no nível de urgência: {pain_analysis.urgency_level}",
            contingency_plan="Se abordagem principal falhar, tentar a alternativa após 1 semana"
        )
    
    def _create_personalized_message(self, analyzed_lead: AnalyzedLead, enhanced_strategy: EnhancedStrategy) -> EnhancedPersonalizedMessage:
        """Create personalized outreach message"""
        
        company_name = self._extract_company_name(analyzed_lead)
        selected_strategy = enhanced_strategy.tot_strategy_evaluation.selected_strategy
        
        # Determine channel
        channel_map = {
            "email": CommunicationChannel.EMAIL,
            "linkedin": CommunicationChannel.LINKEDIN,
            "whatsapp": CommunicationChannel.WHATSAPP,
            "phone": CommunicationChannel.PHONE
        }
        channel = channel_map.get(selected_strategy.primary_channel, CommunicationChannel.EMAIL)
        
        # Create primary message
        if channel == CommunicationChannel.EMAIL:
            subject = f"Insights para {company_name} - {enhanced_strategy.pain_point_analysis.primary_pain_category}"
            body = f"""Olá,

{selected_strategy.key_hook}

Notei que {company_name} atua no setor de {analyzed_lead.analysis.company_sector}. Temos ajudado empresas similares com {enhanced_strategy.pain_point_analysis.primary_pain_category.lower()}.

Gostaria de compartilhar algumas estratégias que podem ser relevantes para vocês.

Teria 15 minutos para uma conversa rápida esta semana?

Atenciosamente,
[Seu nome]"""
        else:
            subject = None
            body = f"Olá! Vi o trabalho de {company_name} e fiquei impressionado. Temos insights que podem ajudar com {enhanced_strategy.pain_point_analysis.primary_pain_category.lower()}. Podemos conversar?"
        
        # Identify personalization elements
        personalization_elements = [
            f"Nome da empresa: {company_name}",
            f"Setor específico: {analyzed_lead.analysis.company_sector}",
            f"Dor identificada: {enhanced_strategy.pain_point_analysis.primary_pain_category}"
        ]
        
        primary_message = PersonalizedMessage(
            channel=channel,
            subject_line=subject,
            message_body=body,
            call_to_action="Agendar conversa de 15 minutos",
            personalization_elements=personalization_elements
        )
        
        return EnhancedPersonalizedMessage(
            primary_message=primary_message,
            alternative_messages=[],  # Could add A/B variants here
            personalization_score=0.8,
            cultural_appropriateness_score=0.9,  # Brazilian Portuguese, formal tone
            estimated_response_rate=0.15,
            message_variants_rationale="Mensagem focada em value-add e baixa pressão"
        )
    
    def _create_internal_briefing(self, analyzed_lead: AnalyzedLead, enhanced_strategy: EnhancedStrategy) -> InternalBriefing:
        """Create internal sales briefing"""
        
        company_name = self._extract_company_name(analyzed_lead)
        
        return InternalBriefing(
            executive_summary=f"{company_name} - {enhanced_strategy.lead_qualification.qualification_tier}: {enhanced_strategy.pain_point_analysis.primary_pain_category} com urgência {enhanced_strategy.pain_point_analysis.urgency_level}",
            key_talking_points=[
                f"Empresa do setor {analyzed_lead.analysis.company_sector}",
                f"Principal dor: {enhanced_strategy.pain_point_analysis.primary_pain_category}",
                f"Estratégia: {enhanced_strategy.tot_strategy_evaluation.selected_strategy.strategy_name}"
            ],
            critical_objections=enhanced_strategy.objection_framework.common_objections,
            success_metrics=["Agendamento de reunião", "Identificação de decisor", "Qualificação de orçamento"],
            next_steps=[
                "Enviar mensagem inicial",
                "Follow-up em 3 dias se não houver resposta",
                "Preparar materiais de apoio"
            ],
            decision_maker_profile=f"Provavelmente {analyzed_lead.analysis.company_size_estimate or 'Pequena a Média'} empresa, decisor técnico/comercial",
            urgency_level=enhanced_strategy.pain_point_analysis.urgency_level
        )
    
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
    
    def _truncate_text(self, text: str, max_length: int = None) -> str:
        """Truncate text to maximum length"""
        if not text:
            return ""
        max_len = max_length or self.max_text_length
        return text[:max_len] if len(text) > max_len else text
    
    def _calculate_confidence_score(self, enhanced_strategy: EnhancedStrategy) -> float:
        """Calculate overall confidence score"""
        
        # Base relevance score
        base_score = 0.3
        
        # Add qualification score
        qual_score = enhanced_strategy.lead_qualification.qualification_score * 0.2
        
        # Add pain analysis score
        pain_score = len(enhanced_strategy.pain_point_analysis.detailed_pain_points) * 0.1
        
        # Add contact availability
        contact_score = enhanced_strategy.contact_information.extraction_confidence * 0.1
        
        # Add external intelligence
        intel_score = 0.1 if enhanced_strategy.external_intelligence.enrichment_confidence > 0.5 else 0.05
        
        # Add strategy completeness
        strategy_score = 0.15 if enhanced_strategy.tot_strategy_evaluation else 0.05
        
        total_score = base_score + qual_score + pain_score + contact_score + intel_score + strategy_score
        return min(total_score, 1.0)
    
    def _calculate_roi_potential(self, enhanced_strategy: EnhancedStrategy) -> float:
        """Calculate ROI potential score"""
        
        # Base on qualification and pain urgency
        qual_weight = enhanced_strategy.lead_qualification.qualification_score * 0.4
        
        urgency_weights = {"low": 0.1, "medium": 0.2, "high": 0.3, "critical": 0.4}
        urgency_weight = urgency_weights.get(enhanced_strategy.pain_point_analysis.urgency_level, 0.2)
        
        # Add value proposition strength
        value_weight = len(enhanced_strategy.value_propositions) * 0.1
        
        # Add purchase triggers
        trigger_weight = len(enhanced_strategy.purchase_triggers.recent_events) * 0.05
        
        return min(qual_weight + urgency_weight + value_weight + trigger_weight, 1.0)
    
    def _calculate_brazilian_fit(self, analyzed_lead: AnalyzedLead) -> float:
        """Calculate Brazilian market cultural fit"""
        
        # Base score for Portuguese content
        base_score = 0.7
        
        # Check for Brazilian indicators
        text_content = analyzed_lead.validated_lead.cleaned_text_content or ""
        brazilian_indicators = ["brasil", "brazilian", "são paulo", "rio de janeiro", "bh", "cnpj"]
        
        indicator_count = sum(1 for indicator in brazilian_indicators if indicator in text_content.lower())
        indicator_bonus = min(indicator_count * 0.1, 0.3)
        
        return min(base_score + indicator_bonus, 1.0)
    
    def _build_prompt(self, input_data: AnalyzedLead) -> str:
        """Build LLM prompt (required by BaseAgent)"""
        return f"Processing lead for {self._extract_company_name(input_data)}"
    
    def _parse_response(self, response: str) -> dict:
        """Parse LLM response to dict (required by BaseAgent)"""
        try:
            # Remove any markdown formatting
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            return json.loads(response.strip())
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse JSON response: {e}")
            return {"error": "Failed to parse response"}
        except Exception as e:
            self.logger.warning(f"Unexpected error parsing response: {e}")
            return {"error": str(e)}
