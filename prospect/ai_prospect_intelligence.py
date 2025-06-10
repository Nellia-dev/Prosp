# ai_prospect_intelligence.py

"""
Phase 4: AI-Powered Prospect Intelligence Engine
Advanced predictive capabilities for prospect discovery and scoring
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
import math
from typing import Dict, Any, List, Optional, Tuple # Ensure Optional is imported

# Conceptual RAG Imports - these would be needed for a real implementation
# import numpy as np # For FAISS array operations and query_embedding_np
# from sentence_transformers import SentenceTransformer # For generating embeddings
# import google.generativeai as genai # For Google Gemini LLM
# import os # To access API keys from environment variables


class AdvancedProspectProfiler:
    """
    AI-powered prospect profiling with predictive capabilities
    """
    
    def __init__(self):
        # Ensure logger is available if this class is instantiated elsewhere independently
        # from loguru import logger # Already imported at module level

        # Conceptual: Actual initialization would download the model if not cached.
        # self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        # logger.info("Conceptual: SentenceTransformer model loaded in Profiler (placeholder).")
        self.embedding_model = None # Keep as None for now
        logger.info("Conceptual: Profiler.embedding_model placeholder for SentenceTransformer.")

        # Conceptual: Initialize LLM Client (e.g., Google Gemini)
        # try:
        #     gemini_api_key = os.getenv("GEMINI_API_KEY")
        #     if not gemini_api_key:
        #         logger.warning("GEMINI_API_KEY not found in environment variables. LLM will not be initialized.")
        #         self.llm_client = None
        #     else:
        #         genai.configure(api_key=gemini_api_key)
        #         self.llm_client = genai.GenerativeModel('gemini-pro') # Or other suitable Gemini model
        #         logger.info("Conceptual: Google Gemini LLM client initialized (placeholder).")
        # except Exception as e:
        #     logger.error(f"Error initializing Gemini LLM client: {e}")
        #     self.llm_client = None
        self.llm_client = None # Keep as None for now
        logger.info("Conceptual: Profiler.llm_client placeholder for Gemini.")
        logger.info("To use real LLM, uncomment Gemini initialization, set GEMINI_API_KEY, and ensure library is installed.")

        self.prospect_signals = {
            'high_intent': {
                'keywords': ['hiring', 'expanding', 'growing', 'funding', 'investment', 'acquisition'],
                'weight': 1.0,
                'urgency_multiplier': 2.0
            },
            'medium_intent': {
                'keywords': ['seeking', 'looking', 'need', 'require', 'searching', 'considering'],
                'weight': 0.7,
                'urgency_multiplier': 1.5
            },
            'pain_indicators': {
                'keywords': ['struggling', 'difficulty', 'challenge', 'problem', 'inefficient', 'manual'],
                'weight': 0.8,
                'urgency_multiplier': 1.8
            },
            'growth_signals': {
                'keywords': ['expansion', 'scale', 'growth', 'new', 'launch', 'opening'],
                'weight': 0.9,
                'urgency_multiplier': 1.6
            }
        }
        
        self.industry_urgency_factors = {
            'technology': 1.2,
            'healthcare': 1.1,
            'finance': 1.0,
            'manufacturing': 0.9,
            'retail': 1.1,
            'education': 0.8
        }
    
    def create_advanced_prospect_profile(self, lead_data: Dict[str, Any], enriched_context: Dict[str, Any], rag_vector_store: Optional[Dict] = None) -> Dict[str, Any]:
        """Create comprehensive AI-powered prospect profile"""
        
        # Extract text content for analysis
        text_content = self._extract_all_text(lead_data)
        
        # Analyze buying intent signals
        intent_score = self._analyze_buying_intent(text_content)
        
        # Analyze pain point alignment
        pain_alignment = self._analyze_pain_alignment(text_content, enriched_context)
        
        # Predict conversion probability
        conversion_probability = self._predict_conversion_probability(lead_data, enriched_context, intent_score, pain_alignment)
        
        # Calculate urgency score
        urgency_score = self._calculate_urgency_score(text_content, lead_data)
        
        # Determine optimal timing
        optimal_timing = self._predict_optimal_timing(lead_data, intent_score)
        
        # Generate engagement strategy
        engagement_strategy = self._generate_engagement_strategy(intent_score, pain_alignment, urgency_score)
        
        return {
            'prospect_score': self._calculate_overall_prospect_score(intent_score, pain_alignment, urgency_score),
            'buying_intent_score': intent_score,
            'pain_alignment_score': pain_alignment,
            'conversion_probability': conversion_probability,
            'urgency_score': urgency_score,
            'optimal_timing': optimal_timing,
            'engagement_strategy': engagement_strategy,
            'predictive_insights': self._generate_predictive_insights(lead_data, enriched_context, rag_vector_store),
            'competitive_analysis': self._analyze_competitive_landscape(text_content, enriched_context)
        }
    
    def _extract_all_text(self, lead_data: Dict[str, Any]) -> str:
        """Extract all available text from lead data"""
        text_parts = []
        
        # Common text fields
        for field in ['description', 'snippet', 'content', 'about', 'services', 'title', 'company_name']:
            if field in lead_data and lead_data[field]:
                text_parts.append(str(lead_data[field]))
        
        return ' '.join(text_parts).lower()
    
    def _analyze_buying_intent(self, text_content: str) -> float:
        """Analyze buying intent signals using AI-powered analysis"""
        intent_score = 0.0
        total_weight = 0.0
        
        for signal_type, config in self.prospect_signals.items():
            matches = sum(1 for keyword in config['keywords'] if keyword in text_content)
            if matches > 0:
                signal_strength = min(matches / len(config['keywords']), 1.0)
                weighted_score = signal_strength * config['weight']
                intent_score += weighted_score
                total_weight += config['weight']
        
        return min(intent_score / max(total_weight, 1.0), 1.0) if total_weight > 0 else 0.0
    
    def _analyze_pain_alignment(self, text_content: str, enriched_context: Dict[str, Any]) -> float:
        """Analyze how well prospect's pain points align with our solutions"""
        # Simplified RAG: Selectively using 'problems_we_solve' and 'value_proposition' from the broader enriched_context.
        lead_qualification_criteria = enriched_context.get('lead_qualification_criteria', {})
        business_offering = enriched_context.get('business_offering', {})

        problems_we_solve = lead_qualification_criteria.get('problems_we_solve', [])
        value_proposition = business_offering.get('value_proposition', '')

        our_solutions = problems_we_solve + ([value_proposition] if value_proposition else [])
        logger.info(f"Profiler: Analyzing pain alignment using {len(our_solutions)} solution points from loaded context.")

        solution_keywords = []
        for solution in our_solutions:
            if solution:
                solution_keywords.extend(str(solution).lower().split())
        
        if not solution_keywords:
            return 0.5  # Neutral if no solution info
        
        # Count alignment indicators
        alignment_count = 0
        for keyword in solution_keywords:
            if len(keyword) > 3 and keyword in text_content: # Basic check to avoid common short words
                alignment_count += 1
        
        return min(alignment_count / len(solution_keywords), 1.0) if solution_keywords else 0.5
    
    def _predict_conversion_probability(self, lead_data: Dict[str, Any], enriched_context: Dict[str, Any],
                                      intent_score: float, pain_alignment: float) -> float:
        """Predict probability of lead conversion using multiple factors"""
        
        # Base probability from intent and alignment
        base_probability = (intent_score * 0.6 + pain_alignment * 0.4)
        
        # Adjust for company size (if detectable)
        size_factor = self._estimate_company_size_factor(lead_data)
        
        # Adjust for industry alignment
        industry_factor = self._calculate_industry_alignment(lead_data, enriched_context)
        
        # Adjust for geographic alignment
        geo_factor = self._calculate_geographic_alignment(lead_data, enriched_context)
        
        # Combined probability with diminishing returns
        probability = base_probability * size_factor * industry_factor * geo_factor
        
        # Apply sigmoid function for realistic probability distribution
        return 1 / (1 + math.exp(-5 * (probability - 0.5)))
    
    def _calculate_urgency_score(self, text_content: str, lead_data: Dict[str, Any]) -> float:
        """Calculate urgency score based on various signals"""
        urgency_indicators = [
            'urgent', 'asap', 'immediately', 'quickly', 'deadline', 'soon',
            'critical', 'emergency', 'priority', 'fast', 'rapid'
        ]
        
        urgency_count = sum(1 for indicator in urgency_indicators if indicator in text_content)
        base_urgency = min(urgency_count / 3, 1.0)  # Normalize to 0-1
        
        # Apply urgency multipliers from prospect signals
        multiplier = 1.0
        for signal_type, config in self.prospect_signals.items():
            if any(keyword in text_content for keyword in config['keywords']):
                multiplier = max(multiplier, config['urgency_multiplier'])
        
        return min(base_urgency * multiplier, 1.0)
    
    def _predict_optimal_timing(self, lead_data: Dict[str, Any], intent_score: float) -> Dict[str, Any]:
        """Predict optimal timing for engagement"""
        
        # High intent = immediate contact
        if intent_score > 0.8:
            return {
                'recommendation': 'immediate',
                'timeframe': '0-24 hours',
                'reasoning': 'High buying intent detected'
            }
        elif intent_score > 0.6:
            return {
                'recommendation': 'urgent',
                'timeframe': '1-3 days',
                'reasoning': 'Strong interest signals present'
            }
        elif intent_score > 0.4:
            return {
                'recommendation': 'standard',
                'timeframe': '3-7 days',
                'reasoning': 'Moderate interest, follow-up needed'
            }
        else:
            return {
                'recommendation': 'nurture',
                'timeframe': '1-2 weeks',
                'reasoning': 'Early stage, requires nurturing'
            }
    
    def _generate_engagement_strategy(self, intent_score: float, pain_alignment: float, urgency_score: float) -> Dict[str, Any]:
        """Generate AI-powered engagement strategy"""
        
        # Determine primary approach
        if pain_alignment > 0.7:
            primary_approach = 'solution_focused'
            message = 'Lead with specific solutions to their identified pain points'
        elif intent_score > 0.7:
            primary_approach = 'opportunity_focused'
            message = 'Emphasize timing and opportunity advantages'
        elif urgency_score > 0.6:
            primary_approach = 'urgency_focused'
            message = 'Address immediate needs and quick implementation'
        else:
            primary_approach = 'relationship_focused'
            message = 'Build relationship and educate on value proposition'
        
        # Determine communication style
        if urgency_score > 0.7 or intent_score > 0.8:
            communication_style = 'direct_concise'
        elif pain_alignment > 0.6:
            communication_style = 'consultative_detailed'
        else:
            communication_style = 'educational_nurturing'
        
        return {
            'primary_approach': primary_approach,
            'communication_style': communication_style,
            'key_message': message,
            'recommended_channels': self._recommend_channels(intent_score, urgency_score),
            'follow_up_cadence': self._determine_follow_up_cadence(intent_score, urgency_score)
        }
    
    def _generate_predictive_insights(self, lead_data: Dict[str, Any], enriched_context: Dict[str, Any], rag_vector_store: Optional[Dict] = None) -> List[str]:
        """
        Generate AI-powered predictive insights using a RAG-simulated approach.
        Conceptual: This method now simulates a full RAG pipeline:
        1. Query Formulation from lead_data.
        2. Query Embedding (placeholder for SentenceTransformer).
        3. Vector Store Search (placeholder for FAISS, using the conceptual rag_vector_store).
        4. LLM Prompt Formulation with retrieved context.
        5. LLM Call and Response Processing (placeholder for Google Gemini).
        """
        lead_text_snippet = (self._extract_all_text(lead_data)[:1000]).lower() # Limit for query, already lowercased

        final_insights = ["Default insight: Further analysis pending full RAG implementation or component initialization."]

        if not rag_vector_store:
            logger.warning(f"Profiler: RAG vector store not available for lead {lead_data.get('company_name', 'N/A')}. Skipping RAG-based insights.")
            return final_insights

        # Conceptual: Check for actual model initialization if they were live
        # if not self.embedding_model or not self.llm_client:
        #     logger.warning(f"Profiler: Embedding model or LLM client not initialized. Skipping RAG-based insights for {lead_data.get('company_name', 'N/A')}.")
        #     return final_insights
        # For this blueprint, we proceed even if self.embedding_model/self.llm_client are None, as their calls are commented out.

        # 1. Formulate Query from lead_data
        query = f"Generate predictive sales insights for a company: {lead_data.get('company_name', 'N/A')}, described as: {lead_text_snippet}"
        logger.info(f"Profiler RAG Query: {query}")

        # 2. Embed Query (Conceptual: using SentenceTransformer example)
        query_embedding_np = None
        try:
            # This import would be at the top in a real file.
            import numpy as np
            # Actual call:
            # if self.embedding_model:
            #     query_embedding_np = self.embedding_model.encode([query])[0].astype(np.float32)
            #     logger.info("Query embedding generated using SentenceTransformer (conceptually).")
            # else:
            #     logger.warning("Profiler: Embedding model not available for query encoding. Using placeholder.")
            #     query_embedding_np = np.array([0.1] * rag_vector_store.get("embedding_dim", 384), dtype=np.float32)

            # Using placeholder for blueprint structure, ensure it matches expected dimension from vector store
            query_embedding_np = np.array([0.1] * rag_vector_store.get("embedding_dim", 384), dtype=np.float32)
            logger.info("Query embedding generated (placeholder numpy array).")
        except ImportError:
            logger.error("Profiler: Numpy import failed. Cannot create placeholder query embedding.")
            return final_insights # Cannot proceed without query embedding
        except Exception as e:
            logger.error(f"Profiler: Error during conceptual query embedding: {e}")
            return final_insights


        # 3. Search Vector Store (Conceptual: using FAISS example)
        retrieved_chunks_texts = []
        faiss_index_placeholder = rag_vector_store.get("index") # This is "placeholder_faiss_index_object"
        stored_chunks = rag_vector_store.get("chunks")

        if faiss_index_placeholder and stored_chunks and query_embedding_np is not None and query_embedding_np.size > 0:
            # try:
            #     # Actual FAISS search:
            #     # Ensure faiss_index is the actual FAISS index object, not the placeholder string.
            #     # For this to work, FAISS library must be imported and faiss_index must be a faiss.Index.
            #     # D, I = faiss_index.search(np.expand_dims(query_embedding_np, axis=0), k=min(3, len(stored_chunks)))
            #     # retrieved_chunks_texts = [stored_chunks[i] for i in I[0] if i < len(stored_chunks)]
            #     # logger.info(f"Retrieved {len(retrieved_chunks_texts)} chunks from FAISS.")
            # except Exception as e:
            #     logger.error(f"Error searching FAISS index: {e}")
            #     retrieved_chunks_texts = stored_chunks[:1] # Fallback to first chunk on error
            logger.info("Conceptual: FAISS search would happen here. Using first 2 stored chunks as placeholder for retrieved_chunks_texts.")
            retrieved_chunks_texts = stored_chunks[:2] # Placeholder retrieval
        else:
            logger.warning(f"Profiler: FAISS index placeholder, stored chunks not available, or query embedding failed for lead {lead_data.get('company_name', 'N/A')}. Using minimal context.")
        
        logger.info(f"Profiler: Retrieved {len(retrieved_chunks_texts)} context chunks (conceptually).")
        retrieved_context_str = "\n---\n".join(retrieved_chunks_texts) if retrieved_chunks_texts else "No specific context retrieved."

        # 4. Formulate LLM Prompt with Retrieved Context
        llm_prompt = f"""As an expert B2B sales analyst, provide 3-4 concise predictive insights for the following lead.
Lead Name: {lead_data.get('company_name', 'N/A')}
Lead Description (snippet): {lead_text_snippet}

Retrieved Context from our Business Strategy Document:
---
{retrieved_context_str}
---
Based ONLY on the lead data and the retrieved context above, what are the key predictive insights?
Insights:"""
        logger.info(f"Profiler RAG LLM Prompt for _generate_predictive_insights:\n{llm_prompt}")

        # 5. Call LLM (Conceptual: Google Gemini example) and Return Response
        # try:
        #     if self.llm_client:
        #         logger.info("Attempting to call Google Gemini LLM...")
        #         # The prompt sent to Gemini might need to be just the user query part,
        #         # and the "retrieved context" could be part of a specific structure if using multi-turn chat,
        #         # or simply prepended to the main query for simpler text generation models.
        #         # For gemini-pro (non-chat), the prompt is a direct string.
        #         response = self.llm_client.generate_content(llm_prompt) # llm_prompt is the full augmented prompt
        #         llm_output = response.text
        #         # Basic parsing of LLM output
        #         final_insights = [line.strip() for line in llm_output.split('\n') if line.strip() and not line.lower().startswith(("insights:", "predictive insights:"))]
        #         if not final_insights and llm_output: # Handle cases where output is single block
        #             final_insights.append(llm_output.strip())
        #         logger.info(f"Insights from Gemini LLM (conceptual): {final_insights}")
        #     else:
        #         logger.warning("LLM client (Gemini) not initialized. Using placeholder insights.")
        #         # Fallback to dynamic placeholders if LLM not available is handled below
        # except Exception as e:
        #     logger.error(f"Error calling Gemini LLM: {e}")
        #     final_insights = [f"Error generating insights from Gemini: {str(e)}"]

        # Current placeholder return, made more dynamic based on retrieved context
        # This block acts as a fallback if the try-except for LLM call is commented out or if self.llm_client is None.
        if not final_insights or final_insights[0].startswith("Default insight:") : # Check if not populated by conceptual LLM call
            logger.info("Conceptual: Google Gemini LLM call would happen here. Generating dynamic placeholder insights.")
            dynamic_placeholder1 = f"Lead '{lead_data.get('company_name', 'N/A')}' shows potential due to: '{retrieved_chunks_texts[0][:60]}...'." if retrieved_chunks_texts else "Generic insight: Lead data aligns with general business strategy."
            dynamic_placeholder2 = f"Consider their description '{lead_text_snippet[:60]}...' against our ICP and value proposition."
            dynamic_placeholder3 = f"Opportunity to leverage our competitive advantage regarding mentioned factors."
            final_insights = [dynamic_placeholder1, dynamic_placeholder2, dynamic_placeholder3]

        return final_insights[:3] # Ensure we return up to 3 insights

    def _analyze_competitive_landscape(self, text_content: str, enriched_context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze competitive landscape and positioning"""
        lead_qualification_criteria = enriched_context.get('lead_qualification_criteria', {})
        competitors = lead_qualification_criteria.get('avoid_competitors', [])
        competitive_mentions = []
        
        for competitor in competitors:
            if competitor and str(competitor).lower() in text_content: # Ensure competitor is string
                competitive_mentions.append(str(competitor))
        
        return {
            'competitor_mentions': competitive_mentions,
            'competitive_threat_level': 'high' if competitive_mentions else 'low',
            'differentiation_opportunities': self._identify_differentiation_opportunities(text_content, enriched_context),
            'positioning_strategy': 'competitive_displacement' if competitive_mentions else 'value_creation'
        }
    
    def _estimate_company_size_factor(self, lead_data: Dict[str, Any]) -> float:
        """Estimate company size compatibility factor"""
        text_content = self._extract_all_text(lead_data)
        
        # Size indicators
        if any(size in text_content for size in ['enterprise', 'large', 'corporation', 'global']):
            return 0.8  # Large companies may have longer sales cycles
        elif any(size in text_content for size in ['startup', 'small', 'boutique']):
            return 1.2  # Smaller companies may move faster
        else:
            return 1.0  # Medium/unknown size
    
    def _calculate_industry_alignment(self, lead_data: Dict[str, Any], enriched_context: Dict[str, Any]) -> float:
        """Calculate industry alignment factor"""
        prospect_targeting = enriched_context.get('prospect_targeting', {})
        target_industries = prospect_targeting.get('industry_focus', [])
        logger.info(f"Profiler: Calculating industry alignment with {len(target_industries)} target industries from loaded context.")

        if not target_industries:
            return 1.0
        
        text_content = self._extract_all_text(lead_data)
        
        for industry in target_industries:
            if str(industry).lower() in text_content: # Ensure industry is string
                return 1.2  # Boost for target industry match
        
        return 0.9  # Slight penalty for non-target industry
    
    def _calculate_geographic_alignment(self, lead_data: Dict[str, Any], enriched_context: Dict[str, Any]) -> float:
        """Calculate geographic alignment factor"""
        prospect_targeting = enriched_context.get('prospect_targeting', {})
        target_geos = prospect_targeting.get('geographic_focus', [])
        logger.info(f"Profiler: Calculating geographic alignment with {len(target_geos)} target geos from loaded context.")

        if not target_geos:
            return 1.0
        
        # Would need to implement geographic detection from lead data
        # For now, assume alignment if any target_geos are present but not specifically detected.
        # A more sophisticated approach would parse lead_data for location info.
        # If lead_data has location and it matches any in target_geos, return 1.2.
        # If lead_data has location and it does NOT match, return 0.8.
        # If lead_data has no location or target_geos is empty, return 1.0.
        return 1.0 # Placeholder for more advanced geo detection logic
    
    def _recommend_channels(self, intent_score: float, urgency_score: float) -> List[str]:
        """Recommend optimal communication channels"""
        if urgency_score > 0.7:
            return ['phone', 'email', 'linkedin']
        elif intent_score > 0.6:
            return ['email', 'linkedin', 'phone']
        else:
            return ['linkedin', 'email', 'content_marketing']
    
    def _determine_follow_up_cadence(self, intent_score: float, urgency_score: float) -> str:
        """Determine optimal follow-up frequency"""
        if urgency_score > 0.7 or intent_score > 0.8:
            return 'aggressive'  # Every 2-3 days
        elif intent_score > 0.5:
            return 'standard'   # Weekly
        else:
            return 'nurture'    # Bi-weekly/monthly
    
    def _identify_differentiation_opportunities(self, text_content: str, enriched_context: Dict[str, Any]) -> List[str]:
        """Identify opportunities for differentiation"""
        opportunities = []
        
        business_offering = enriched_context.get('business_offering', {})
        value_prop = business_offering.get('value_proposition', '').lower()
        competitive_advantage = business_offering.get('competitive_advantage', '').lower()
        logger.info("Profiler: Identifying differentiation opportunities using value prop and competitive advantage from loaded context.")

        # Look for pain points we can uniquely address
        if 'custom' in text_content and 'custom' in value_prop:
            opportunities.append("Emphasize customization capabilities")
        
        if 'support' in text_content and 'support' in competitive_advantage:
            opportunities.append("Highlight superior support offering")
        
        if 'price' in text_content or 'cost' in text_content: # Basic keyword check
            # More sophisticated logic might check if our value_prop or competitive_advantage addresses cost-effectiveness
            if "price" in value_prop or "cost" in value_prop or "affordable" in value_prop or \
               "price" in competitive_advantage or "cost" in competitive_advantage or "affordable" in competitive_advantage:
                opportunities.append("Present value-based pricing or cost-effectiveness proposition")
            else:
                opportunities.append("Acknowledge price/cost sensitivity if mentioned by prospect")

        return opportunities
    
    def _calculate_overall_prospect_score(self, intent_score: float, pain_alignment: float, urgency_score: float) -> float:
        """Calculate overall prospect score using weighted factors"""
        weights = {
            'intent': 0.4,
            'alignment': 0.35,
            'urgency': 0.25
        }
        
        overall_score = (
            intent_score * weights['intent'] +
            pain_alignment * weights['alignment'] +
            urgency_score * weights['urgency']
        )
        
        return round(overall_score, 3)


class BuyingSignalPredictor:
    """
    Advanced buying signal prediction using AI patterns
    """
    
    def __init__(self):
        self.signal_patterns = {
            'hiring_signals': {
                'patterns': [r'hiring.*(?:manager|director|cto|ceo)', r'job.*posting', r'we.*looking.*for'],
                'weight': 0.9,
                'timeframe': 'immediate'
            },
            'funding_signals': {
                'patterns': [r'funding.*round', r'investment.*received', r'series.*[abc]'],
                'weight': 0.8,
                'timeframe': '1-3 months'
            },
            'expansion_signals': {
                'patterns': [r'opening.*new', r'expanding.*to', r'new.*location'],
                'weight': 0.7,
                'timeframe': '3-6 months'
            },
            'technology_signals': {
                'patterns': [r'upgrading.*systems', r'new.*technology', r'digital.*transformation'],
                'weight': 0.6,
                'timeframe': '6-12 months'
            }
        }
    
    def predict_buying_signals(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict buying signals and timing"""
        text_content = ' '.join([str(v) for v in lead_data.values() if v]).lower()
        
        detected_signals = []
        confidence_scores = {}
        
        for signal_type, config in self.signal_patterns.items():
            matches = []
            for pattern in config['patterns']:
                matches.extend(re.findall(pattern, text_content))
            
            if matches:
                confidence = min(len(matches) / len(config['patterns']), 1.0) * config['weight']
                detected_signals.append({
                    'signal_type': signal_type,
                    'confidence': confidence,
                    'timeframe': config['timeframe'],
                    'evidence': matches[:3]  # Top 3 matches
                })
                confidence_scores[signal_type] = confidence
        
        return {
            'detected_signals': detected_signals,
            'overall_buying_probability': self._calculate_buying_probability(confidence_scores),
            'predicted_timeline': self._predict_purchase_timeline(detected_signals),
            'recommended_actions': self._recommend_actions(detected_signals)
        }
    
    def _calculate_buying_probability(self, confidence_scores: Dict[str, float]) -> float:
        """Calculate overall buying probability"""
        if not confidence_scores:
            return 0.1  # Base probability
        
        # Use geometric mean for conservative estimate
        product = 1.0
        for score in confidence_scores.values():
            product *= (1 - score)
        
        return 1 - product
    
    def _predict_purchase_timeline(self, detected_signals: List[Dict[str, Any]]) -> str:
        """Predict most likely purchase timeline"""
        if not detected_signals:
            return 'unknown'
        
        # Find most immediate signal
        timeframes = [signal['timeframe'] for signal in detected_signals]
        
        if 'immediate' in timeframes:
            return 'immediate'
        elif '1-3 months' in timeframes:
            return '1-3 months'
        elif '3-6 months' in timeframes:
            return '3-6 months'
        else:
            return '6-12 months'
    
    def _recommend_actions(self, detected_signals: List[Dict[str, Any]]) -> List[str]:
        """Recommend actions based on detected signals"""
        actions = []
        
        signal_types = [signal['signal_type'] for signal in detected_signals]
        
        if 'hiring_signals' in signal_types:
            actions.append("Immediate outreach - high buying intent detected")
        
        if 'funding_signals' in signal_types:
            actions.append("Emphasize growth and scalability benefits")
        
        if 'expansion_signals' in signal_types:
            actions.append("Position solutions for expansion support")
        
        if 'technology_signals' in signal_types:
            actions.append("Lead with technology modernization value")
        
        if not actions:
            actions.append("Standard nurturing approach - monitor for signals")
        
        return actions


class ProspectIntentScorer:
    """
    Advanced intent scoring engine using multiple AI algorithms
    """
    
    def __init__(self):
        # Ensure logger is available if this class is instantiated elsewhere independently
        # from loguru import logger # Already imported at module level

        self.intent_indicators = {
            'explicit_intent': {
                'keywords': ['looking for', 'need', 'require', 'seeking', 'want', 'searching'],
                'weight': 1.0
            },
            'research_intent': {
                'keywords': ['comparing', 'evaluating', 'considering', 'review', 'options'],
                'weight': 0.8
            },
            'problem_awareness': {
                'keywords': ['challenge', 'issue', 'problem', 'difficulty', 'struggle'],
                'weight': 0.7
            },
            'solution_awareness': {
                'keywords': ['solution', 'tool', 'platform', 'service', 'provider'],
                'weight': 0.6
            }
        }
    
    def calculate_intent_score(self, lead_data: Dict[str, Any], enriched_context: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive intent score"""
        
        text_content = self._extract_text_content(lead_data)
        
        # Calculate base intent score
        base_score = self._calculate_base_intent(text_content)
        
        # Apply contextual adjustments
        context_adjusted_score = self._apply_contextual_adjustments(base_score, text_content, enriched_context)
        
        # Calculate intent confidence
        confidence = self._calculate_confidence(text_content)
        
        # Determine intent stage
        intent_stage = self._determine_intent_stage(text_content, context_adjusted_score)
        
        return {
            'intent_score': round(context_adjusted_score, 3),
            'confidence': round(confidence, 3),
            'intent_stage': intent_stage,
            'intent_breakdown': self._breakdown_intent_components(text_content),
            'recommendations': self._generate_intent_recommendations(context_adjusted_score, intent_stage)
        }
    
    def _extract_text_content(self, lead_data: Dict[str, Any]) -> str:
        """Extract and clean text content for analysis"""
        text_fields = ['description', 'content', 'snippet', 'about', 'services']
        text_parts = []
        
        for field in text_fields:
            if field in lead_data and lead_data[field]:
                text_parts.append(str(lead_data[field]))
        
        return ' '.join(text_parts).lower()
    
    def _calculate_base_intent(self, text_content: str) -> float:
        """Calculate base intent score from text analysis"""
        total_score = 0.0
        total_weight = 0.0
        
        for intent_type, config in self.intent_indicators.items():
            matches = sum(1 for keyword in config['keywords'] if keyword in text_content)
            if matches > 0:
                normalized_score = min(matches / len(config['keywords']), 1.0)
                weighted_score = normalized_score * config['weight']
                total_score += weighted_score
                total_weight += config['weight']
        
        return total_score / max(total_weight, 1.0) if total_weight > 0 else 0.0
    
    def _apply_contextual_adjustments(self, base_score: float, text_content: str, enriched_context: Dict[str, Any]) -> float:
        """Apply contextual adjustments to base score"""
        # Simplified RAG: Selectively using 'industry_focus' and 'business_offering' details from the broader enriched_context.
        adjusted_score = base_score
        
        prospect_targeting = enriched_context.get('prospect_targeting', {})
        business_offering = enriched_context.get('business_offering', {})

        # Industry relevance adjustment
        target_industries = prospect_targeting.get('industry_focus', [])
        for industry in target_industries:
            if str(industry).lower() in text_content: # Ensure industry is string
                adjusted_score *= 1.2  # Boost for industry match
                break
        
        # Solution relevance adjustment
        our_keywords = []
        for field_key in ['description', 'product_service', 'value_proposition']: # Corrected keys for business_offering
            field_value = business_offering.get(field_key, '')
            if field_value:
                our_keywords.extend(str(field_value).lower().split())
        
        logger.info("Scorer: Applying contextual adjustments using industry focus and business offering from loaded context.")

        if our_keywords: # Ensure our_keywords is not empty before division
            relevant_keywords = sum(1 for keyword in our_keywords if len(keyword) > 3 and keyword in text_content)
            if relevant_keywords > 0:
                relevance_boost = min(relevant_keywords / len(our_keywords), 0.3) # Cap boost
                adjusted_score += relevance_boost
        
        return min(adjusted_score, 1.0) # Ensure score doesn't exceed 1.0
    
    def _calculate_confidence(self, text_content: str) -> float:
        """Calculate confidence in intent assessment"""
        # More text = higher confidence
        text_length_factor = min(len(text_content) / 1000, 1.0)
        
        # Specific indicators = higher confidence
        specific_indicators = ['exactly', 'specifically', 'precisely', 'particularly']
        specificity_factor = sum(1 for indicator in specific_indicators if indicator in text_content) / len(specific_indicators)
        
        return (text_length_factor * 0.6 + specificity_factor * 0.4)
    
    def _determine_intent_stage(self, text_content: str, intent_score: float) -> str:
        """Determine the prospect's intent stage"""
        if intent_score > 0.8:
            return 'high_intent'
        elif intent_score > 0.6:
            return 'medium_intent'
        elif intent_score > 0.3:
            return 'low_intent'
        else:
            return 'awareness'
    
    def _breakdown_intent_components(self, text_content: str) -> Dict[str, float]:
        """Break down intent into component scores"""
        breakdown = {}
        
        for intent_type, config in self.intent_indicators.items():
            matches = sum(1 for keyword in config['keywords'] if keyword in text_content)
            score = (matches / len(config['keywords'])) * config['weight'] if matches > 0 else 0.0
            breakdown[intent_type] = round(score, 3)
        
        return breakdown
    
    def _generate_intent_recommendations(self, intent_score: float, intent_stage: str) -> List[str]:
        """Generate recommendations based on intent analysis"""
        recommendations = []
        
        if intent_stage == 'high_intent':
            recommendations.extend([
                "Immediate follow-up required - high conversion probability",
                "Present specific solution proposal",
                "Schedule demo or consultation call"
            ])
        elif intent_stage == 'medium_intent':
            recommendations.extend([
                "Engage with targeted content and case studies",
                "Nurture with solution-specific information",
                "Follow up within 3-5 days"
            ])
        elif intent_stage == 'low_intent':
            recommendations.extend([
                "Add to nurture campaign",
                "Share educational content",
                "Monitor for intent signal changes"
            ])
        else:
            recommendations.extend([
                "Focus on awareness-building content",
                "Long-term nurturing strategy",
                "Educational approach recommended"
            ])
        
        return recommendations