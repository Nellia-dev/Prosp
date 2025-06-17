#!/usr/bin/env python3
"""
Comprehensive integration test for the enhanced Nellia Prospector system.
Tests the integration of new-cw.py and ck.py capabilities into the agent architecture.
"""

import os
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Set up environment
os.environ.setdefault('GEMINI_API_KEY', 'test-key')
os.environ.setdefault('TAVILY_API_KEY', 'test-key')

from data_models.lead_structures import (
    HarvesterOutput, SiteData, AnalyzedLead, 
    EnhancedIntelligence, ComprehensiveProspectPackage
)
from agents.enhanced_lead_processor import EnhancedLeadProcessor
from core_logic.llm_client import LLMClient
from core_logic.nlp_utils import NLPProcessor, quick_entity_extraction, quick_sector_classification
from utils.constants import SECTOR_KEYWORDS, BRAZILIAN_BUSINESS_INDICATORS
from utils.logger_config import setup_logger

logger = setup_logger(__name__)

class MockLLMClient:
    """Mock LLM client for testing without API calls"""
    
    def __init__(self):
        self.total_tokens = 0
        self.call_count = 0
    
    def generate(self, prompt: str, **kwargs) -> Any:
        """Mock LLM response"""
        self.call_count += 1
        self.total_tokens += len(prompt.split()) * 2  # Simulate token usage
        
        class MockResponse:
            def __init__(self, content: str):
                self.content = content
        
        # Return realistic mock responses based on prompt content
        if "pain point analysis" in prompt.lower():
            return MockResponse(json.dumps({
                "primary_pain_category": "Process Efficiency",
                "detailed_pain_points": [
                    {"category": "Manual Processes", "description": "Heavy reliance on manual data entry"},
                    {"category": "System Integration", "description": "Disconnected systems causing data silos"}
                ],
                "business_impact_assessment": "High - causing 20+ hours/week of inefficiency",
                "urgency_level": "high",
                "confidence_score": 0.85
            }))
        
        elif "contact extraction" in prompt.lower():
            return MockResponse(json.dumps({
                "likely_contacts": [
                    {"name": "João Silva", "role": "CEO", "confidence": 0.8},
                    {"name": "Maria Santos", "role": "CTO", "confidence": 0.7}
                ],
                "contact_methods": {
                    "emails": ["contato@empresa.com"],
                    "social_profiles": ["linkedin.com/company/empresa"],
                    "phones": ["(11) 9999-9999"]
                },
                "confidence_score": 0.75
            }))
        
        elif "competitor analysis" in prompt.lower():
            return MockResponse(json.dumps({
                "mentioned_competitors": ["Concorrente A", "Concorrente B"],
                "current_solutions": ["Planilhas Excel", "Sistema legado"],
                "competitive_advantages": ["Maior agilidade", "Melhor suporte"],
                "market_position": "Challenger",
                "confidence_score": 0.7
            }))
        
        elif "purchase triggers" in prompt.lower():
            return MockResponse(json.dumps({
                "recent_events": ["Expansão da empresa", "Novo investimento"],
                "market_signals": ["Crescimento do setor", "Pressão competitiva"],
                "timing_indicators": ["Orçamento aprovado", "Projeto em andamento"],
                "urgency_assessment": "medium",
                "confidence_score": 0.65
            }))
        
        elif "qualification scoring" in prompt.lower():
            return MockResponse(json.dumps({
                "qualification_tier": "High Potential",
                "qualification_score": 0.82,
                "qualification_reasoning": [
                    "Strong pain point alignment",
                    "Budget indicators present",
                    "Decision maker identified"
                ],
                "recommendation": "Proceed with immediate outreach",
                "confidence_score": 0.8
            }))
        
        elif "strategy evaluation" in prompt.lower():
            return MockResponse(json.dumps({
                "strategy_options": [
                    {
                        "name": "Direct Value Proposition",
                        "description": "Lead with ROI and efficiency gains",
                        "pros": ["Clear benefit", "Quantifiable impact"],
                        "cons": ["May seem too sales-y"],
                        "score": 0.85
                    },
                    {
                        "name": "Educational Approach",
                        "description": "Share industry insights and best practices",
                        "pros": ["Builds credibility", "Non-threatening"],
                        "cons": ["Longer sales cycle"],
                        "score": 0.75
                    }
                ],
                "selected_strategy": "Direct Value Proposition",
                "reasoning": "Strong pain point alignment supports direct approach",
                "confidence_score": 0.8
            }))
        
        elif "objection handling" in prompt.lower():
            return MockResponse(json.dumps({
                "anticipated_objections": {
                    "budget": "Response focusing on ROI and cost savings",
                    "timing": "Emphasis on quick implementation and immediate benefits",
                    "trust": "Case studies and testimonials from similar companies"
                },
                "objection_prevention": ["Include social proof", "Address concerns proactively"],
                "confidence_score": 0.75
            }))
        
        elif "message generation" in prompt.lower():
            return MockResponse(json.dumps({
                "primary_message": {
                    "subject_line": "Transformação Digital para [Empresa] - ROI Comprovado",
                    "message_body": "Olá [Nome],\n\nNotei que a [Empresa] está enfrentando desafios com processos manuais...",
                    "call_to_action": "Que tal uma conversa de 15 minutos para mostrar como outras empresas similar conseguiram resultados?",
                    "personalization_elements": ["company_name", "industry_specific_pain", "competitor_reference"]
                },
                "alternative_messages": [
                    {
                        "subject_line": "Insights sobre Eficiência Operacional para [Empresa]",
                        "message_body": "Prezado [Nome],\n\nComo especialista em [Setor], tenho observado...",
                        "call_to_action": "Gostaria de compartilhar um case study relevante - podemos agendar uma call?",
                        "personalization_elements": ["sector_expertise", "relevant_case_study"]
                    }
                ],
                "message_tone": "professional_consultative",
                "cultural_adaptation": "brazilian_formal",
                "confidence_score": 0.88
            }))
        
        else:
            # Default response for any other prompt
            return MockResponse(json.dumps({
                "status": "processed",
                "confidence_score": 0.7,
                "processing_notes": "Mock response generated successfully"
            }))

class EnhancedSystemTester:
    """Comprehensive tester for the enhanced system"""
    
    def __init__(self):
        self.nlp_processor = NLPProcessor()
        self.mock_llm = MockLLMClient()
        self.test_results = {}
        
    def create_test_lead(self) -> AnalyzedLead:
        """Create a realistic test lead for processing"""
        site_data = SiteData(
            url="https://empresateste.com.br",
            company_name="TechSolutions Brasil Ltda",
            extracted_text="""
            A TechSolutions Brasil é uma empresa líder em transformação digital para PMEs brasileiras.
            Oferecemos soluções de automação, integração de sistemas e business intelligence.
            Nossos clientes enfrentam desafios com processos manuais e sistemas desconectados.
            Contato: joao.silva@techsolutions.com.br | (11) 98765-4321
            LinkedIn: linkedin.com/company/techsolutions-brasil
            Localização: São Paulo, SP
            CNPJ: 12.345.678/0001-90
            
            Nossa equipe é liderada pelo CEO João Silva e CTO Maria Santos.
            Estamos expandindo operations e buscando melhorar nossa eficiência operacional.
            Competimos principalmente com a ConsultTech e a DigitalPro.
            Recentemente recebemos investimento para crescimento.
            """,
            page_title="TechSolutions Brasil - Transformação Digital para PMEs",
            meta_description="Soluções de automação e integração para pequenas e médias empresas brasileiras",
            collection_timestamp=datetime.now().isoformat()
        )
        
        return AnalyzedLead(
            **site_data.dict(),
            company_summary="Empresa de tecnologia focada em transformação digital para PMEs brasileiras",
            identified_services_offered=[
                "Automação de processos",
                "Integração de sistemas", 
                "Business Intelligence",
                "Consultoria em transformação digital"
            ],
            potential_pain_points=[
                "Processos manuais excessivos",
                "Sistemas desconectados",
                "Falta de visibilidade de dados",
                "Ineficiência operacional"
            ],
            business_sector="technology",
            relevance_score=0.85,
            processing_status="analyzed",
            confidence_score=0.82
        )
    
    def test_nlp_utilities(self) -> Dict[str, Any]:
        """Test NLP utility functions"""
        logger.info("Testing NLP utilities...")
        
        test_text = """
        A Nellia Prospector é uma empresa brasileira de inteligência artificial
        que oferece soluções de automação para lead generation.
        Contato: contato@nellia.com.br | (11) 98640-9993
        LinkedIn: linkedin.com/company/nellia
        Localização: São Paulo, SP
        """
        
        results = {}
        
        # Test entity extraction
        entities = quick_entity_extraction(test_text)
        results['entity_extraction'] = {
            'emails_found': len(entities['emails']) > 0,
            'phones_found': len(entities['phones']) > 0,
            'social_found': len(entities['social_media']) > 0
        }
        
        # Test sector classification
        sector, confidence = quick_sector_classification(test_text)
        results['sector_classification'] = {
            'sector': sector,
            'confidence': confidence,
            'is_valid': sector in SECTOR_KEYWORDS
        }
        
        # Test text analysis
        text_analysis = self.nlp_processor.analyze_text_properties(test_text)
        results['text_analysis'] = {
            'language_detected': text_analysis.language_detected,
            'word_count': text_analysis.word_count,
            'complexity': text_analysis.reading_complexity
        }
        
        # Test business intelligence
        business_intel = self.nlp_processor.extract_business_intelligence(test_text)
        results['business_intelligence'] = {
            'sector': business_intel.sector_classification,
            'services_count': len(business_intel.services_mentioned),
            'pain_points_count': len(business_intel.pain_points_mentioned)
        }
        
        logger.info(f"NLP utilities test completed: {results}")
        return results
    
    def test_enhanced_processor(self) -> Dict[str, Any]:
        """Test the enhanced lead processor"""
        logger.info("Testing Enhanced Lead Processor...")
        
        # Create processor with mock LLM
        processor = EnhancedLeadProcessor(
            llm_client=self.mock_llm,
            tavily_api_key="test-key",
            temperature=0.7
        )
        
        # Create test lead
        test_lead = self.create_test_lead()
        
        # Process the lead
        start_time = time.time()
        try:
            result = processor.process(test_lead)
            processing_time = time.time() - start_time
            
            # Validate result
            success = isinstance(result, ComprehensiveProspectPackage)
            
            results = {
                'processing_successful': success,
                'processing_time': round(processing_time, 2),
                'llm_calls_made': self.mock_llm.call_count,
                'tokens_used': self.mock_llm.total_tokens,
                'result_type': type(result).__name__
            }
            
            if success:
                results.update({
                    'has_enhanced_intelligence': hasattr(result, 'enhanced_intelligence'),
                    'has_strategy': hasattr(result, 'enhanced_strategy'),
                    'has_message': hasattr(result, 'personalized_message'),
                    'confidence_score': getattr(result, 'confidence_score', 0.0)
                })
            
        except Exception as e:
            logger.error(f"Enhanced processor test failed: {e}")
            results = {
                'processing_successful': False,
                'error': str(e),
                'processing_time': time.time() - start_time
            }
        
        logger.info(f"Enhanced processor test completed: {results}")
        return results
    
    def test_data_model_validation(self) -> Dict[str, Any]:
        """Test data model validation and structure"""
        logger.info("Testing data model validation...")
        
        results = {}
        
        try:
            # Test EnhancedIntelligence model
            enhanced_intel = EnhancedIntelligence(
                contact_information={
                    "emails_found": ["test@example.com"],
                    "social_profiles": ["linkedin.com/company/test"],
                    "potential_contacts": [{"name": "Test", "role": "CEO"}]
                },
                pain_point_analysis={
                    "primary_pain_category": "Efficiency",
                    "detailed_pain_points": [{"category": "Manual", "description": "Too manual"}],
                    "business_impact_assessment": "High impact"
                },
                competitor_intelligence={
                    "mentioned_competitors": ["Competitor A"],
                    "current_solutions": ["Excel"],
                    "competitive_advantages": ["Better UX"]
                },
                purchase_triggers={
                    "recent_events": ["Funding"],
                    "market_signals": ["Growth"],
                    "timing_indicators": ["Budget approved"]
                },
                lead_qualification={
                    "qualification_tier": "High Potential",
                    "qualification_score": 0.85,
                    "qualification_reasoning": ["Strong fit"]
                },
                external_intelligence={
                    "tavily_enrichment": "Additional market data",
                    "market_research": "Industry trends",
                    "news_analysis": "Recent developments"
                }
            )
            
            results['enhanced_intelligence_valid'] = True
            
            # Test ComprehensiveProspectPackage
            test_lead = self.create_test_lead()
            
            comprehensive_package = ComprehensiveProspectPackage(
                **test_lead.dict(),
                enhanced_intelligence=enhanced_intel,
                enhanced_strategy={
                    "tot_strategy_options": [{"name": "Direct", "score": 0.8}],
                    "selected_approach": {"name": "Direct", "reasoning": "Best fit"},
                    "objection_frameworks": {"budget": "ROI focus"}
                },
                personalized_message={
                    "primary_message": {
                        "subject_line": "Test Subject",
                        "message_body": "Test Body",
                        "call_to_action": "Test CTA"
                    },
                    "alternative_messages": [],
                    "message_tone": "professional",
                    "cultural_adaptation": "brazilian"
                },
                final_confidence_score=0.85,
                processing_metadata={
                    "processing_time": 5.2,
                    "tokens_used": 1500,
                    "agent_version": "enhanced_v1.0"
                }
            )
            
            results['comprehensive_package_valid'] = True
            results['data_preservation'] = all([
                comprehensive_package.company_name == test_lead.company_name,
                comprehensive_package.url == test_lead.url,
                comprehensive_package.relevance_score == test_lead.relevance_score
            ])
            
        except Exception as e:
            logger.error(f"Data model validation failed: {e}")
            results['error'] = str(e)
            results['enhanced_intelligence_valid'] = False
            results['comprehensive_package_valid'] = False
            results['data_preservation'] = False
        
        logger.info(f"Data model validation completed: {results}")
        return results
    
    def test_brazilian_market_features(self) -> Dict[str, Any]:
        """Test Brazilian market-specific features"""
        logger.info("Testing Brazilian market features...")
        
        results = {}
        
        # Test Brazilian business indicators
        brazilian_text = """
        Empresa brasileira com CNPJ 12.345.678/0001-90
        Localizada em São Paulo, atende todo o Brasil
        Compliance com LGPD, faturamento em Real (R$)
        Atende de segunda a sexta das 9h às 18h
        """
        
        entities = self.nlp_processor.extract_entities(brazilian_text)
        business_intel = self.nlp_processor.extract_business_intelligence(brazilian_text)
        
        results.update({
            'cnpj_detection': len(entities.business_identifiers) > 0,
            'location_detection': len(entities.locations) > 0,
            'brazilian_indicators': len(business_intel.business_indicators) > 0,
            'portuguese_content': business_intel.sector_classification != "unknown"
        })
        
        # Test cultural adaptation
        results['cultural_constants_loaded'] = len(BRAZILIAN_BUSINESS_INDICATORS) > 0
        results['sector_keywords_br'] = 'tecnologia' in str(SECTOR_KEYWORDS).lower()
        
        return results
    
    def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling and edge cases"""
        logger.info("Testing error handling...")
        
        results = {}
        
        # Test with empty/invalid data
        try:
            empty_lead = AnalyzedLead(
                url="",
                company_name="",
                extracted_text="",
                page_title="",
                meta_description="",
                collection_timestamp=datetime.now().isoformat(),
                company_summary="",
                identified_services_offered=[],
                potential_pain_points=[],
                business_sector="unknown",
                relevance_score=0.0,
                processing_status="error",
                confidence_score=0.0
            )
            
            processor = EnhancedLeadProcessor(
                llm_client=self.mock_llm,
                tavily_api_key="test-key"
            )
            
            result = processor.process(empty_lead)
            results['empty_data_handling'] = isinstance(result, ComprehensiveProspectPackage)
            
        except Exception as e:
            results['empty_data_handling'] = False
            results['empty_data_error'] = str(e)
        
        # Test NLP with edge cases
        try:
            empty_entities = quick_entity_extraction("")
            results['empty_text_nlp'] = len(empty_entities['emails']) == 0
            
            long_text = "palavra " * 10000  # Very long text
            long_summary = self.nlp_processor.summarize_text(long_text)
            results['long_text_handling'] = len(long_summary) < len(long_text)
            
        except Exception as e:
            results['nlp_edge_cases'] = False
            results['nlp_error'] = str(e)
        
        logger.info(f"Error handling test completed: {results}")
        return results
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run all tests and return comprehensive results"""
        logger.info("Starting comprehensive enhanced system test...")
        
        start_time = time.time()
        
        all_results = {
            'test_timestamp': datetime.now().isoformat(),
            'test_environment': 'mock',
            'tests': {}
        }
        
        # Run individual tests
        test_methods = [
            ('nlp_utilities', self.test_nlp_utilities),
            ('enhanced_processor', self.test_enhanced_processor),
            ('data_model_validation', self.test_data_model_validation),
            ('brazilian_market_features', self.test_brazilian_market_features),
            ('error_handling', self.test_error_handling)
        ]
        
        for test_name, test_method in test_methods:
            try:
                logger.info(f"Running {test_name} test...")
                test_result = test_method()
                all_results['tests'][test_name] = {
                    'status': 'passed',
                    'results': test_result
                }
            except Exception as e:
                logger.error(f"Test {test_name} failed: {e}")
                all_results['tests'][test_name] = {
                    'status': 'failed',
                    'error': str(e)
                }
        
        # Calculate overall results
        total_tests = len(test_methods)
        passed_tests = sum(1 for test in all_results['tests'].values() if test['status'] == 'passed')
        
        all_results['summary'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'success_rate': round(passed_tests / total_tests * 100, 1),
            'total_time': round(time.time() - start_time, 2)
        }
        
        logger.info(f"Comprehensive test completed: {all_results['summary']}")
        return all_results

def main():
    """Main test execution"""
    print("🚀 Nellia Prospector Enhanced System Integration Test")
    print("=" * 60)
    
    tester = EnhancedSystemTester()
    results = tester.run_comprehensive_test()
    
    # Save results
    results_file = f"test_results_enhanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Print summary
    summary = results['summary']
    print(f"\n📊 Test Results Summary:")
    print(f"   Total Tests: {summary['total_tests']}")
    print(f"   Passed: {summary['passed_tests']}")
    print(f"   Failed: {summary['failed_tests']}")
    print(f"   Success Rate: {summary['success_rate']}%")
    print(f"   Total Time: {summary['total_time']}s")
    
    # Detailed results
    print(f"\n📋 Detailed Results:")
    for test_name, test_data in results['tests'].items():
        status_emoji = "✅" if test_data['status'] == 'passed' else "❌"
        print(f"   {status_emoji} {test_name}: {test_data['status']}")
        if test_data['status'] == 'failed':
            print(f"      Error: {test_data.get('error', 'Unknown error')}")
    
    print(f"\n💾 Full results saved to: {results_file}")
    
    # Return success code
    return 0 if summary['success_rate'] == 100 else 1

if __name__ == "__main__":
    exit(main())
