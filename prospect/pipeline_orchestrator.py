# prospect/pipeline_orchestrator.py

import asyncio
import traceback
import os
import time
from typing import Dict, Any, AsyncIterator, List
from datetime import datetime
import uuid

from loguru import logger

# Event Models
from event_models import (
    PipelineStartEvent,
    PipelineEndEvent,
    AgentStartEvent,
    AgentEndEvent,
    LeadGeneratedEvent,
    StatusUpdateEvent,
    PipelineErrorEvent,
    LeadEnrichmentStartEvent,
    LeadEnrichmentEndEvent,
)

# ADK Agents (Harvester)
from adk1.agent import (
    lead_search_and_qualify_agent as harvester_search_agent,
)

# Enhanced Processor Agents
from agents.lead_intake_agent import LeadIntakeAgent
from agents.lead_analysis_agent import LeadAnalysisAgent
from agents.enhanced_lead_processor import EnhancedLeadProcessor
from data_models.lead_structures import SiteData, GoogleSearchData
from core_logic.llm_client import LLMClientFactory

# ADK Runner
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Constants
ADK_APP_NAME = "prospecter_harvester"
ADK_USER_ID = "prospector_user_1"
ADK_SESSION_SERVICE = InMemorySessionService()


class BusinessTypeClassifier:
    """
    Phase 3: Advanced business type classification for intelligent query selection
    """
    
    def __init__(self):
        self.business_categories = {
            'ai_technology': {
                'keywords': ['ai', 'artificial intelligence', 'machine learning', 'automation', 'inteligencia artificial'],
                'priority_strategies': ['problem_seeking', 'industry_growth', 'buying_intent'],
                'target_indicators': ['digital transformation', 'manual processes', 'modernization']
            },
            'software_development': {
                'keywords': ['software', 'development', 'programming', 'web', 'mobile', 'app'],
                'priority_strategies': ['problem_seeking', 'competitive_displacement', 'buying_intent'],
                'target_indicators': ['legacy systems', 'outdated technology', 'custom solutions']
            },
            'business_consulting': {
                'keywords': ['consulting', 'consultoria', 'advisory', 'strategy', 'business'],
                'priority_strategies': ['problem_seeking', 'industry_growth', 'buying_intent'],
                'target_indicators': ['growth challenges', 'strategic planning', 'operational issues']
            },
            'marketing_sales': {
                'keywords': ['marketing', 'sales', 'lead generation', 'customer acquisition', 'digital marketing'],
                'priority_strategies': ['problem_seeking', 'buying_intent', 'competitive_displacement'],
                'target_indicators': ['low sales', 'customer acquisition', 'marketing ROI']
            },
            'financial_services': {
                'keywords': ['finance', 'accounting', 'investment', 'fintech', 'banking'],
                'priority_strategies': ['industry_growth', 'competitive_displacement', 'buying_intent'],
                'target_indicators': ['financial planning', 'compliance', 'cost optimization']
            },
            'healthcare_tech': {
                'keywords': ['healthcare', 'medical', 'health tech', 'telemedicine', 'pharma'],
                'priority_strategies': ['problem_seeking', 'industry_growth', 'buying_intent'],
                'target_indicators': ['patient care', 'efficiency', 'digital health']
            }
        }
    
    def classify_business(self, business_context: Dict[str, Any]) -> Dict[str, Any]:
        """Classify business type and return optimization recommendations"""
        business_desc = business_context.get('business_description', '').lower()
        product_service = business_context.get('product_service_description', '').lower()
        combined_text = f"{business_desc} {product_service}"
        
        # Score each category
        category_scores = {}
        for category, config in self.business_categories.items():
            score = 0
            for keyword in config['keywords']:
                if keyword in combined_text:
                    score += 1
            category_scores[category] = score
        
        # Find best match
        primary_category = max(category_scores, key=category_scores.get) if category_scores else 'general'
        confidence = category_scores.get(primary_category, 0) / len(self.business_categories[primary_category]['keywords'])
        
        return {
            'primary_category': primary_category,
            'confidence': confidence,
            'priority_strategies': self.business_categories[primary_category]['priority_strategies'],
            'target_indicators': self.business_categories[primary_category]['target_indicators'],
            'all_scores': category_scores
        }


class QueryPerformanceTracker:
    """
    Phase 3: Track query performance and learn from results
    """
    
    def __init__(self):
        self.query_metrics = {}
        self.strategy_performance = {
            'problem_seeking': {'leads_found': 0, 'quality_score': 0.0, 'conversion_rate': 0.0},
            'industry_growth': {'leads_found': 0, 'quality_score': 0.0, 'conversion_rate': 0.0},
            'buying_intent': {'leads_found': 0, 'quality_score': 0.0, 'conversion_rate': 0.0},
            'competitive_displacement': {'leads_found': 0, 'quality_score': 0.0, 'conversion_rate': 0.0}
        }
    
    def track_query_performance(self, query: str, strategy_type: str, leads_found: int, quality_metrics: Dict[str, float]):
        """Track performance of a specific query"""
        query_id = f"{strategy_type}_{hash(query)}"
        
        self.query_metrics[query_id] = {
            'query': query,
            'strategy_type': strategy_type,
            'leads_found': leads_found,
            'quality_score': quality_metrics.get('avg_quality', 0.0),
            'timestamp': datetime.now().isoformat(),
            'success_rate': quality_metrics.get('success_rate', 0.0)
        }
        
        # Update strategy performance
        if strategy_type in self.strategy_performance:
            current = self.strategy_performance[strategy_type]
            current['leads_found'] += leads_found
            current['quality_score'] = (current['quality_score'] + quality_metrics.get('avg_quality', 0.0)) / 2
            current['conversion_rate'] = (current['conversion_rate'] + quality_metrics.get('success_rate', 0.0)) / 2
    
    def get_best_strategy_for_business_type(self, business_category: str) -> str:
        """Return the best performing strategy for a business type"""
        # For now, return based on performance metrics
        # In a real implementation, this would be business_category specific
        best_strategy = max(self.strategy_performance.items(),
                          key=lambda x: x[1]['quality_score'] * x[1]['conversion_rate'])
        return best_strategy[0]
    
    def get_performance_analytics(self) -> Dict[str, Any]:
        """Return comprehensive performance analytics"""
        return {
            'strategy_performance': self.strategy_performance,
            'total_queries_tracked': len(self.query_metrics),
            'best_performing_strategy': self.get_best_strategy_for_business_type('general'),
            'avg_leads_per_query': sum(m['leads_found'] for m in self.query_metrics.values()) / max(len(self.query_metrics), 1)
        }


class PipelineOrchestrator:
    """
    Orchestrates the entire lead generation and enrichment pipeline,
    from initial harvesting to deep enrichment, yielding real-time events.
    """

    def __init__(self, business_context: Dict[str, Any], user_id: str, job_id: str):
        self.business_context = business_context
        self.user_id = user_id
        self.job_id = job_id
        self.product_service_context = business_context.get("product_service_description", "")
        self.competitors_list = ", ".join(business_context.get("competitors", []))
        
        # Initialize a single LLM client to be shared by all agents
        self.llm_client = LLMClientFactory.create_from_env()
        
        # Initialize the Enhanced Processor agents here
        self.lead_intake_agent = LeadIntakeAgent(
            llm_client=self.llm_client,
            name="LeadIntakeAgent",
            description="Validates and prepares lead data for processing."
        )
        self.lead_analysis_agent = LeadAnalysisAgent(
            llm_client=self.llm_client,
            name="LeadAnalysisAgent",
            description="Analyzes validated lead data to extract key business insights.",
            product_service_context=self.product_service_context
        )
        self.enhanced_lead_processor = EnhancedLeadProcessor(
            llm_client=self.llm_client,
            name="EnhancedLeadProcessor",
            description="Orchestrates a series of specialized agents to generate a rich, multi-faceted prospect package.",
            product_service_context=self.product_service_context,
            competitors_list=self.competitors_list,
            tavily_api_key=os.getenv("TAVILY_API_KEY")
        )
        logger.info(f"PipelineOrchestrator initialized for job {self.job_id}")
        
        # Phase 3: Query performance tracking and business classification
        self.query_performance_tracker = QueryPerformanceTracker()
        self.business_classifier = BusinessTypeClassifier()
        
        # Phase 4: AI-Powered Prospect Intelligence
        try:
            from ai_prospect_intelligence import (
                AdvancedProspectProfiler,
                BuyingSignalPredictor,
                ProspectIntentScorer
            )
            self.prospect_profiler = AdvancedProspectProfiler()
            self.signal_predictor = BuyingSignalPredictor()
            self.intent_scorer = ProspectIntentScorer()
            self.ai_intelligence_enabled = True
            logger.info(f"[{self.job_id}] AI-Powered Prospect Intelligence enabled")
        except ImportError as e:
            logger.warning(f"[{self.job_id}] AI Intelligence module not available: {e}")
            self.ai_intelligence_enabled = False

    def _generate_multiple_prospect_queries(self, business_context: Dict[str, Any]) -> List[str]:
        """
        PHASE 2: Generate multiple prospect-focused queries using different strategies.
        Returns 3-5 different query approaches to maximize prospect discovery.
        """
        logger.info(f"[{self.job_id}] Generating MULTI-STRATEGY prospect queries...")
        
        location = business_context.get('geographic_focus', ['Brazil'])[0]
        
        # Strategy 1: Problem-Seeking Queries
        problem_queries = self._generate_problem_seeking_queries(business_context, location)
        
        # Strategy 2: Industry + Growth Signal Queries
        growth_queries = self._generate_industry_growth_queries(business_context, location)
        
        # Strategy 3: Buying Intent Signal Queries
        intent_queries = self._generate_buying_intent_queries(business_context, location)
        
        # Strategy 4: Competitive Displacement Queries
        displacement_queries = self._generate_competitive_displacement_queries(business_context, location)
        
        # Combine all strategies
        all_queries = problem_queries + growth_queries + intent_queries + displacement_queries
        
        # Remove duplicates while preserving order
        unique_queries = []
        for query in all_queries:
            if query not in unique_queries:
                unique_queries.append(query)
        
        # Limit to top 5 most diverse queries
        selected_queries = unique_queries[:5]
        
        logger.info(f"[{self.job_id}] Generated {len(selected_queries)} multi-strategy queries:")
        for i, query in enumerate(selected_queries, 1):
            logger.info(f"[{self.job_id}] Strategy {i}: '{query}'")
            
        return selected_queries
    
    def _generate_problem_seeking_queries(self, business_context: Dict[str, Any], location: str) -> List[str]:
        """Strategy 1: Find companies with problems we solve"""
        business_desc = business_context.get('business_description', '').lower()
        pain_points = business_context.get('pain_points', [])
        queries = []
        
        # Map business offerings to customer problems
        if any(term in business_desc for term in ['ai', 'artificial intelligence']):
            queries.extend([
                f"companies struggling manual processes {location}",
                f"businesses needing automation {location}",
                f"traditional companies digital transformation {location}"
            ])
        
        if any(term in business_desc for term in ['software', 'technology']):
            queries.extend([
                f"companies outdated systems {location}",
                f"businesses inefficient workflows {location}",
                f"organizations legacy software {location}"
            ])
        
        if any(term in business_desc for term in ['consulting', 'advisory']):
            queries.extend([
                f"companies strategic challenges {location}",
                f"businesses growth problems {location}",
                f"organizations operational issues {location}"
            ])
        
        if any(term in business_desc for term in ['marketing', 'sales']):
            queries.extend([
                f"companies low customer acquisition {location}",
                f"businesses poor sales performance {location}",
                f"organizations marketing struggles {location}"
            ])
        
        # Add pain-point specific queries
        for pain in pain_points:
            pain_str = str(pain).lower()
            if 'manual' in pain_str:
                queries.append(f"companies manual operations {location}")
            if 'efficiency' in pain_str or 'inefficient' in pain_str:
                queries.append(f"businesses operational inefficiency {location}")
            if 'growth' in pain_str:
                queries.append(f"companies scaling difficulties {location}")
                
        return queries[:3]  # Return top 3 problem-seeking queries
    
    def _generate_industry_growth_queries(self, business_context: Dict[str, Any], location: str) -> List[str]:
        """Strategy 2: Find companies in target industries showing growth signals"""
        industry_focus = business_context.get('industry_focus', [])
        target_market = business_context.get('target_market', '').lower()
        queries = []
        
        # Industry + growth combinations
        for industry in industry_focus:
            industry_str = str(industry).lower()
            if industry_str not in ['small', 'medium', 'large']:
                queries.extend([
                    f"{industry_str} companies expanding {location}",
                    f"{industry_str} businesses hiring {location}",
                    f"{industry_str} organizations growing {location}"
                ])
        
        # Size-based targeting
        if 'small' in target_market or any('small' in str(ind).lower() for ind in industry_focus):
            queries.extend([
                f"small companies rapid growth {location}",
                f"startups scaling operations {location}",
                f"small businesses expanding {location}"
            ])
        
        if 'medium' in target_market or any('medium' in str(ind).lower() for ind in industry_focus):
            queries.extend([
                f"medium enterprises expansion {location}",
                f"mid-size companies growth {location}",
                f"medium businesses scaling {location}"
            ])
        
        return queries[:2]  # Return top 2 industry-growth queries
    
    def _generate_buying_intent_queries(self, business_context: Dict[str, Any], location: str) -> List[str]:
        """Strategy 3: Find companies showing buying intent signals"""
        business_desc = business_context.get('business_description', '').lower()
        queries = []
        
        # Hiring-based intent signals
        if any(term in business_desc for term in ['ai', 'technology', 'software']):
            queries.extend([
                f"companies hiring CTO {location}",
                f"businesses recruiting technology roles {location}",
                f"organizations hiring IT director {location}"
            ])
        
        if any(term in business_desc for term in ['consulting', 'strategy']):
            queries.extend([
                f"companies hiring consultants {location}",
                f"businesses seeking strategic advisors {location}",
                f"organizations hiring business development {location}"
            ])
        
        if any(term in business_desc for term in ['marketing', 'sales']):
            queries.extend([
                f"companies hiring marketing director {location}",
                f"businesses recruiting sales manager {location}",
                f"organizations hiring growth roles {location}"
            ])
        
        # Investment/funding intent signals
        queries.extend([
            f"companies recent funding {location}",
            f"businesses announcing expansion {location}",
            f"organizations new investment {location}"
        ])
        
        return queries[:2]  # Return top 2 buying intent queries
    
    def _generate_competitive_displacement_queries(self, business_context: Dict[str, Any], location: str) -> List[str]:
        """Strategy 4: Find companies potentially switching from competitors"""
        competitors = business_context.get('competitors', [])
        business_desc = business_context.get('business_description', '').lower()
        queries = []
        
        # Generic displacement opportunities
        if any(term in business_desc for term in ['software', 'technology']):
            queries.extend([
                f"companies replacing software {location}",
                f"businesses switching systems {location}",
                f"organizations upgrading technology {location}"
            ])
        
        if any(term in business_desc for term in ['consulting', 'services']):
            queries.extend([
                f"companies changing consultants {location}",
                f"businesses seeking new advisors {location}",
                f"organizations switching service providers {location}"
            ])
        
        # Competitor-specific displacement (if competitors are known)
        for competitor in competitors[:2]:  # Limit to top 2 competitors
            if competitor:
                competitor_str = str(competitor)
                queries.append(f"companies alternatives to {competitor_str} {location}")
        
        return queries[:1]  # Return top 1 displacement query
    
    def _generate_search_query_from_business_context(self, business_context: Dict[str, Any]) -> str:
        """
        PHASE 2: Multi-strategy prospect query generation.
        Generates multiple queries and selects the best one using intelligent selection.
        """
        # Generate multiple query strategies
        query_options = self._generate_multiple_prospect_queries(business_context)
        
        if not query_options:
            # Fallback to Phase 1 logic
            return self._generate_fallback_prospect_query(business_context)
        
        # Select the best query using intelligent selection
        selected_query = self._select_optimal_query(query_options, business_context)
        
        logger.info(f"[{self.job_id}] FINAL SELECTED QUERY: '{selected_query}'")
        return selected_query
    
    def _select_optimal_query(self, query_options: List[str], business_context: Dict[str, Any]) -> str:
        """
        Phase 3: Advanced intelligent query selection using business classification and performance data
        """
        if not query_options:
            return self._generate_fallback_prospect_query(business_context)
        
        # Step 1: Classify the business
        business_classification = self.business_classifier.classify_business(business_context)
        logger.info(f"[{self.job_id}] Business classified as: {business_classification['primary_category']} (confidence: {business_classification['confidence']:.2f})")
        
        # Step 2: Get performance-based recommendations
        best_strategy = self.query_performance_tracker.get_best_strategy_for_business_type(business_classification['primary_category'])
        
        # Step 3: Map query options to strategies
        query_strategy_mapping = self._map_queries_to_strategies(query_options)
        
        # Step 4: Prioritize based on business type and performance
        priority_strategies = business_classification['priority_strategies']
        target_indicators = business_classification['target_indicators']
        
        # Try to find query matching best performing strategy
        if best_strategy in query_strategy_mapping:
            selected_query = query_strategy_mapping[best_strategy][0]
            logger.info(f"[{self.job_id}] Selected query based on best performing strategy '{best_strategy}': '{selected_query}'")
            return selected_query
        
        # Fallback to priority strategies for this business type
        for strategy in priority_strategies:
            if strategy in query_strategy_mapping:
                selected_query = query_strategy_mapping[strategy][0]
                logger.info(f"[{self.job_id}] Selected query based on priority strategy '{strategy}': '{selected_query}'")
                return selected_query
        
        # Fallback to queries containing target indicators
        for query in query_options:
            if any(indicator in query.lower() for indicator in target_indicators):
                logger.info(f"[{self.job_id}] Selected query based on target indicators: '{query}'")
                return query
        
        # Final fallback
        selected_query = query_options[0]
        logger.info(f"[{self.job_id}] Selected first available query: '{selected_query}'")
        return selected_query
    
    def _map_queries_to_strategies(self, query_options: List[str]) -> Dict[str, List[str]]:
        """Map queries to their corresponding strategies based on keywords"""
        strategy_mapping = {
            'problem_seeking': [],
            'industry_growth': [],
            'buying_intent': [],
            'competitive_displacement': []
        }
        
        for query in query_options:
            query_lower = query.lower()
            
            # Problem-seeking indicators
            if any(word in query_lower for word in ['struggling', 'challenges', 'problems', 'issues', 'manual', 'inefficient']):
                strategy_mapping['problem_seeking'].append(query)
            
            # Industry growth indicators
            elif any(word in query_lower for word in ['expanding', 'growing', 'growth', 'scaling', 'hiring']):
                strategy_mapping['industry_growth'].append(query)
            
            # Buying intent indicators
            elif any(word in query_lower for word in ['hiring', 'seeking', 'recruiting', 'investment', 'funding']):
                strategy_mapping['buying_intent'].append(query)
            
            # Competitive displacement indicators
            elif any(word in query_lower for word in ['replacing', 'switching', 'alternatives', 'changing']):
                strategy_mapping['competitive_displacement'].append(query)
            
            # Default to problem_seeking if no clear match
            else:
                strategy_mapping['problem_seeking'].append(query)
        
        return strategy_mapping
    
    def _generate_fallback_prospect_query(self, business_context: Dict[str, Any]) -> str:
        """Fallback prospect-focused query if all else fails"""
        location = business_context.get('geographic_focus', ['Brazil'])[0]
        return f"growing companies seeking solutions {location}"

    def _create_enriched_search_context(self, business_context: Dict[str, Any], search_query: str) -> Dict[str, Any]:
        """
        Create enriched PROSPECT-FOCUSED context for the harvester.
        Emphasizes finding companies that NEED our solutions, not competitors.
        """
        return {
            "search_query": search_query,
            "search_intent": "FIND_PROSPECTS_NOT_COMPETITORS",
            "business_offering": {
                "description": business_context.get('business_description', ''),
                "product_service": business_context.get('product_service_description', ''),
                "value_proposition": business_context.get('value_proposition', ''),
                "competitive_advantage": business_context.get('competitive_advantage', '')
            },
            "prospect_targeting": {
                "ideal_customer_profile": business_context.get('ideal_customer', ''),
                "target_market": business_context.get('target_market', ''),
                "geographic_focus": business_context.get('geographic_focus', []),
                "industry_focus": business_context.get('industry_focus', []),
                "company_size_preference": self._extract_size_preference(business_context),
                "growth_stage_indicators": ["expanding", "hiring", "growing", "investing", "scaling"]
            },
            "lead_qualification_criteria": {
                "problems_we_solve": business_context.get('pain_points', []),
                "avoid_competitors": business_context.get('competitors', []),
                "buying_signals": [
                    "companies hiring new roles",
                    "businesses announcing expansion",
                    "organizations seeking solutions",
                    "companies with growth challenges",
                    "businesses undergoing transformation"
                ],
                "must_have_characteristics": [
                    f"Located in {', '.join(business_context.get('geographic_focus', ['Brazil']))}",
                    f"Target industries: {', '.join(business_context.get('industry_focus', ['any industry']))}",
                    f"Customer profile: {business_context.get('ideal_customer', 'growing businesses')}"
                ],
                "exclusion_criteria": [
                    "Avoid companies that offer similar services",
                    "Skip obvious competitors",
                    "Focus on potential customers, not service providers"
                ]
            }
        }
    
    def _extract_size_preference(self, business_context: Dict[str, Any]) -> str:
        """Extract company size preference from business context"""
        ideal_customer = business_context.get('ideal_customer', '').lower()
        industry_focus = business_context.get('industry_focus', [])
        
        # Check for size indicators
        if any(size in ideal_customer for size in ['small', 'pequenas', 'startup']):
            return "small_companies"
        elif any(size in ideal_customer for size in ['medium', 'médias', 'mid-size']):
            return "medium_companies"
        elif any(size in ideal_customer for size in ['large', 'enterprise', 'grandes']):
            return "large_companies"
            
        # Check industry focus for size indicators
        for industry in industry_focus:
            industry_str = str(industry).lower()
            if 'small' in industry_str or 'pequenas' in industry_str:
                return "small_companies"
            elif 'medium' in industry_str or 'médias' in industry_str:
                return "medium_companies"
                
        return "all_sizes"

    async def execute_streaming_pipeline(self) -> AsyncIterator[Dict[str, Any]]:
        """
        Main entry point to run the unified pipeline.
        It harvests leads and concurrently enriches them.
        """
        start_time = time.time()
        yield PipelineStartEvent(
            event_type="pipeline_start",
            timestamp=datetime.now().isoformat(),
            job_id=self.job_id,
            user_id=self.user_id,
            initial_query=self.business_context.get("business_description", "N/A"),
            max_leads_to_generate=self.business_context.get("max_leads_to_generate", 10)
        ).to_dict()

        enrichment_tasks = []
        leads_found = 0
        try:
            # Start the harvester as the main task
            async for raw_lead_data in self._run_harvester():
                
                # Skip example.com or invalid leads
                website_url = raw_lead_data.get("website", "")
                if "example.com" in website_url or not website_url or website_url == "N/A":
                    logger.warning(f"[{self.job_id}] Skipping invalid lead: {website_url}")
                    continue
                
                # For each lead found, yield the event and start enrichment
                lead_id = str(uuid.uuid4())
                leads_found += 1
                
                yield LeadGeneratedEvent(
                    event_type="lead_generated",
                    timestamp=datetime.now().isoformat(),
                    job_id=self.job_id,
                    user_id=self.user_id,
                    lead_id=lead_id,
                    lead_data=raw_lead_data,
                    source_url=raw_lead_data.get("website", "N/A"),
                    agent_name=harvester_search_agent.name
                ).to_dict()

                # Create a concurrent task for enriching this lead
                async def _run_enrichment_and_collect_events(lead_data, lead_id):
                    events = []
                    async for event in self._enrich_lead(lead_data, lead_id):
                        events.append(event)
                    return events

                task = asyncio.create_task(_run_enrichment_and_collect_events(raw_lead_data, lead_id))
                enrichment_tasks.append(task)
                await asyncio.sleep(5) # Add a delay to avoid rate limiting

            # Wait for all enrichment tasks to complete
            if leads_found == 0:
                yield StatusUpdateEvent(
                    event_type="status_update",
                    timestamp=datetime.now().isoformat(),
                    job_id=self.job_id,
                    user_id=self.user_id,
                    status_message="No valid leads were found by the harvester. Please check your business description and try refining your search criteria."
                ).to_dict()
            else:
                yield StatusUpdateEvent(
                    event_type="status_update",
                    timestamp=datetime.now().isoformat(),
                    job_id=self.job_id,
                    user_id=self.user_id,
                    status_message=f"Harvester finished. Found {leads_found} leads. Waiting for all enrichment tasks to complete..."
                ).to_dict()

            for task_future in asyncio.as_completed(enrichment_tasks):
                events = await task_future
                for event in events:
                    yield event

        except Exception as e:
            logger.error(f"Critical error in pipeline for job {self.job_id}: {e}")
            yield PipelineErrorEvent(
                event_type="pipeline_error",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                error_message=str(e),
                error_type=type(e).__name__
            ).to_dict()
        finally:
            total_time = time.time() - start_time
            yield PipelineEndEvent(
                event_type="pipeline_end",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                total_leads_generated=len(enrichment_tasks),
                execution_time_seconds=total_time,
                success=True # Assuming success if no critical error
            ).to_dict()

    async def _run_harvester(self) -> AsyncIterator[Dict[str, Any]]:
        """
        Run the harvester to find and qualify leads using direct query generation.
        Bypasses the problematic ADK query refiner agent.
        """
        logger.info(f"[{self.job_id}] Starting harvester...")
        
        # Generate search query directly from business context
        search_query = self._generate_search_query_from_business_context(self.business_context)
        logger.info(f"[{self.job_id}] Generated search query: {search_query}")
        
        # Phase 3: Track query selection for performance analysis
        query_start_time = time.time()
        leads_found_count = 0
        
        # Create enriched context for better lead qualification
        enriched_context = self._create_enriched_search_context(self.business_context, search_query)
        logger.debug(f"[{self.job_id}] Enriched search context created")
        
        # Initialize the search agent runner
        search_runner = Runner(
            app_name=ADK_APP_NAME,
            agent=harvester_search_agent,
            session_service=ADK_SESSION_SERVICE,
        )

        try:
            session_id = str(uuid.uuid4())
            logger.debug(f"[{self.job_id}] Creating ADK session with ID: {session_id}")
            
            await ADK_SESSION_SERVICE.create_session(
                session_id=session_id, app_name=ADK_APP_NAME, user_id=self.user_id
            )
            logger.debug(f"[{self.job_id}] ADK session created successfully")
            
            yield StatusUpdateEvent(
                event_type="status_update",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                status_message=f"Harvester using search query: {search_query}",
                agent_name="DirectQueryGenerator"
            ).to_dict()

            # Search for leads
            max_leads = self.business_context.get("max_leads_to_generate", 10)
            lead_count = 0
            search_content = types.Content(parts=[types.Part(text=search_query)])
            
            logger.info(f"[{self.job_id}] Starting lead search with query: {search_query}")
            
            async for lead_chunk in search_runner.run_async(
                user_id=self.user_id,
                session_id=session_id,
                new_message=search_content,
            ):
                logger.debug(f"[{self.job_id}] Received lead_chunk: {type(lead_chunk)}")
                
                if hasattr(lead_chunk, 'content'):
                    content = lead_chunk.content
                    logger.debug(f"[{self.job_id}] Lead chunk content type: {type(content)}")
                    logger.debug(f"[{self.job_id}] Lead chunk content: {str(content)[:500]}...")
                    
                    # Handle different content types
                    leads_data = None
                    if isinstance(content, list):
                        leads_data = content
                    elif isinstance(content, str):
                        try:
                            # Try to parse as JSON if it's a string
                            import json
                            leads_data = json.loads(content)
                            if not isinstance(leads_data, list):
                                leads_data = [leads_data] if leads_data else []
                        except json.JSONDecodeError:
                            logger.warning(f"[{self.job_id}] Could not parse lead content as JSON: {content[:200]}...")
                            continue
                    elif hasattr(content, 'parts') and content.parts:
                        # Handle different types of parts
                        for part in content.parts:
                            if hasattr(part, 'function_response') and part.function_response:
                                # Extract data from function response
                                func_response = part.function_response
                                if hasattr(func_response, 'response') and func_response.response:
                                    response_data = func_response.response
                                    if isinstance(response_data, dict) and 'result' in response_data:
                                        result = response_data['result']
                                        if isinstance(result, list):
                                            leads_data = result
                                            logger.info(f"[{self.job_id}] Extracted {len(leads_data)} leads from function response")
                                            break
                            elif hasattr(part, 'text') and part.text:
                                # Try to parse text content as JSON
                                text_content = part.text
                                try:
                                    import json
                                    leads_data = json.loads(text_content)
                                    if not isinstance(leads_data, list):
                                        leads_data = [leads_data] if leads_data else []
                                except json.JSONDecodeError:
                                    logger.warning(f"[{self.job_id}] Could not parse part text as JSON: {text_content[:200]}...")
                                    continue
                    
                    if leads_data:
                        logger.info(f"[{self.job_id}] Processing {len(leads_data)} leads from chunk")
                        for lead in leads_data:
                            if lead_count >= max_leads:
                                break
                            
                            logger.debug(f"[{self.job_id}] Processing lead: {lead}")
                            
                            # Ensure lead has required fields and extract from various formats
                            if isinstance(lead, dict):
                                # Extract and normalize fields
                                company_name = (
                                    lead.get("company_name") or
                                    lead.get("title") or
                                    lead.get("name") or
                                    "Unknown"
                                )
                                
                                website_url = (
                                    lead.get("website") or
                                    lead.get("url") or
                                    lead.get("source_url") or
                                    ""
                                )
                                
                                description = (
                                    lead.get("description") or
                                    lead.get("snippet") or
                                    lead.get("qualification_summary") or
                                    lead.get("full_content") or
                                    ""
                                )
                                
                                # Only process leads with valid websites
                                if website_url and not any(invalid in website_url.lower() for invalid in ["example.com", "localhost", "127.0.0.1"]):
                                    normalized_lead = {
                                        "company_name": company_name,
                                        "website": website_url,
                                        "description": description,
                                        "snippet": description[:200] if description else "",
                                        "source_url": website_url
                                    }
                                    
                                    # Phase 4: Apply AI-powered prospect intelligence
                                    if self.ai_intelligence_enabled:
                                        try:
                                            # AI Prospect Analysis
                                            ai_profile = self.prospect_profiler.create_advanced_prospect_profile(
                                                normalized_lead, self.business_context
                                            )
                                            
                                            # AI Buying Signal Prediction
                                            buying_signals = self.signal_predictor.predict_buying_signals(normalized_lead)
                                            
                                            # AI Intent Scoring
                                            intent_analysis = self.intent_scorer.calculate_intent_score(
                                                normalized_lead, self.business_context
                                            )
                                            
                                            # Add AI intelligence to lead data
                                            normalized_lead["ai_intelligence"] = {
                                                "prospect_score": ai_profile["prospect_score"],
                                                "conversion_probability": ai_profile["conversion_probability"],
                                                "buying_intent_score": ai_profile["buying_intent_score"],
                                                "urgency_score": ai_profile["urgency_score"],
                                                "intent_stage": intent_analysis["intent_stage"],
                                                "optimal_timing": ai_profile["optimal_timing"],
                                                "engagement_strategy": ai_profile["engagement_strategy"],
                                                "buying_signals": buying_signals["detected_signals"],
                                                "predictive_insights": ai_profile["predictive_insights"],
                                                "overall_buying_probability": buying_signals["overall_buying_probability"]
                                            }
                                            
                                            # Log AI analysis results
                                            logger.info(f"[{self.job_id}] AI Analysis - {company_name}: Prospect Score {ai_profile['prospect_score']:.3f}, Intent Stage: {intent_analysis['intent_stage']}, Conversion Probability: {ai_profile['conversion_probability']:.3f}")
                                            
                                        except Exception as ai_error:
                                            logger.warning(f"[{self.job_id}] AI intelligence failed for {company_name}: {ai_error}")
                                            # Continue without AI intelligence if it fails
                                    
                                    logger.info(f"[{self.job_id}] Yielding lead: {company_name} - {website_url}")
                                    yield normalized_lead
                                    lead_count += 1
                                    leads_found_count += 1
                                else:
                                    logger.warning(f"[{self.job_id}] Skipping lead with invalid/missing website: {website_url}")
                            else:
                                logger.warning(f"[{self.job_id}] Skipping non-dict lead: {type(lead)}")
                    else:
                        logger.warning(f"[{self.job_id}] No valid leads data found in chunk")
                else:
                    logger.warning(f"[{self.job_id}] Lead chunk has no content attribute")
                
                if lead_count >= max_leads:
                    logger.info(f"[{self.job_id}] Harvester reached max leads ({max_leads}).")
                    break
            
            if lead_count == 0:
                logger.warning(f"[{self.job_id}] No leads were generated by the harvester")
                # Don't yield any leads if none were found - let the pipeline handle this gracefully
                return
        
        except Exception as e:
            logger.error(f"[{self.job_id}] Harvester failed: {e}\n{traceback.format_exc()}")
            yield PipelineErrorEvent(
                event_type="pipeline_error",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                error_message=f"Harvester failed: {e}",
                error_type=type(e).__name__,
                agent_name="Harvester"
            ).to_dict()
        finally:
            # Phase 3: Record query performance
            query_duration = time.time() - query_start_time
            
            # Calculate quality metrics
            quality_metrics = {
                'avg_quality': 0.7 if leads_found_count > 0 else 0.0,  # Placeholder - would be calculated from actual lead quality
                'success_rate': 1.0 if leads_found_count > 0 else 0.0,
                'leads_per_second': leads_found_count / max(query_duration, 1)
            }
            
            # Determine strategy type used
            strategy_type = self._determine_strategy_type(search_query)
            
            # Track performance
            self.query_performance_tracker.track_query_performance(
                query=search_query,
                strategy_type=strategy_type,
                leads_found=leads_found_count,
                quality_metrics=quality_metrics
            )
            
            logger.info(f"[{self.job_id}] Harvester finished. Performance tracked: {leads_found_count} leads found using {strategy_type} strategy")
    
    def _determine_strategy_type(self, query: str) -> str:
        """Determine which strategy type was used based on query content"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['struggling', 'challenges', 'problems', 'manual', 'inefficient']):
            return 'problem_seeking'
        elif any(word in query_lower for word in ['expanding', 'growing', 'hiring', 'scaling']):
            return 'industry_growth'
        elif any(word in query_lower for word in ['seeking', 'recruiting', 'investment', 'funding']):
            return 'buying_intent'
        elif any(word in query_lower for word in ['replacing', 'switching', 'alternatives']):
            return 'competitive_displacement'
        else:
            return 'general'


    async def _enrich_lead(self, lead_data: Dict[str, Any], lead_id: str) -> AsyncIterator[Dict[str, Any]]:
        """
        Runs the full enhancement pipeline on a single lead.
        """
        yield LeadEnrichmentStartEvent(
            event_type="lead_enrichment_start",
            timestamp=datetime.now().isoformat(),
            job_id=self.job_id,
            user_id=self.user_id,
            lead_id=lead_id,
            company_name=lead_data.get("company_name", "N/A")
        ).to_dict()

        try:
            # 1. Intake - Extract proper URL and data
            website_url = (
                lead_data.get("website") or
                lead_data.get("url") or
                lead_data.get("source_url") or
                "http://example.com"
            )
            
            company_name = (
                lead_data.get("company_name") or
                lead_data.get("title") or
                website_url.replace("http://", "").replace("https://", "").split("/")[0]
            )
            
            description = (
                lead_data.get("description") or
                lead_data.get("snippet") or
                lead_data.get("search_snippet") or
                lead_data.get("full_content") or
                ""
            )
            
            logger.info(f"[{self.job_id}] Enriching lead: {company_name} at {website_url}")
            
            site_data = SiteData(
                url=website_url,
                extracted_text_content=description,
                google_search_data=GoogleSearchData(
                    title=company_name,
                    snippet=description[:500] if description else ""
                ),
                extraction_status_message="SUCCESS"
            )
            validated_lead = self.lead_intake_agent.execute(site_data)
            if not validated_lead.is_valid:
                raise ValueError(f"Lead intake failed: {validated_lead.validation_errors}")

            # 2. Initial Analysis
            analyzed_lead = self.lead_analysis_agent.execute(validated_lead)

            # 3. Full Enrichment
            # The enhanced_processor itself yields events, so we can pass them through
            async for event in self.enhanced_lead_processor.execute_enrichment_pipeline(
                analyzed_lead=analyzed_lead,
                job_id=self.job_id,
                user_id=self.user_id
            ):
                # Add lead_id to every event for frontend tracking
                event["lead_id"] = lead_id
                yield event
            
            # The final event from the enrichment pipeline is PipelineEndEvent,
            # which contains the full package. We'll capture that here.
            final_package = event.get("data")

            yield LeadEnrichmentEndEvent(
                event_type="lead_enrichment_end",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                lead_id=lead_id,
                success=True,
                final_package=final_package
            ).to_dict()

        except Exception as e:
            logger.error(f"Enrichment failed for lead {lead_id}: {e}\n{traceback.format_exc()}")
            yield LeadEnrichmentEndEvent(
                event_type="lead_enrichment_end",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                lead_id=lead_id,
                success=False,
                error_message=str(e)
            ).to_dict()