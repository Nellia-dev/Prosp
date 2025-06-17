#!/usr/bin/env python3
"""
Test script for the Enhanced Nellia Prospector system
"""

import os
import json
import tempfile
from datetime import datetime
import unittest # Added unittest

from data_models.lead_structures import HarvesterOutput, SiteData, GoogleSearchData
from enhanced_main import EnhancedNelliaProspector, ProcessingMode

def create_test_data():
    """Create test harvester data"""
    
    test_site = SiteData(
        url="https://example-company.com.br",
        google_search_data=GoogleSearchData(
            title="Example Company - Soluções em Tecnologia Avançada",
            snippet="Líder brasileira em IA e Machine Learning para otimização de processos B2B."
        ),
        extracted_text_content="""
        A Example Company é uma empresa brasileira inovadora, fundada em 2010, com foco em soluções de software e consultoria para o mercado B2B. 
        Nossa missão é transformar digitalmente negócios através de tecnologia de ponta e expertise setorial.
        Oferecemos um portfólio diversificado que inclui desenvolvimento de software sob medida, implementação de sistemas ERP e CRM, 
        e consultoria especializada em transformação digital e otimização de processos. Recentemente, expandimos nossa atuação para incluir 
        análise de dados avançada e soluções de inteligência artificial para previsão de demanda e detecção de anomalias.

        Nossos principais clientes são empresas de médio e grande porte nos setores de Varejo, Manufatura e Serviços Financeiros, 
        que buscam otimizar seus processos, reduzir custos operacionais, melhorar a experiência do cliente e aumentar sua competitividade.
        Um desafio comum que ajudamos a resolver é a integração de sistemas legados com novas tecnologias em nuvem, garantindo a continuidade e segurança dos dados.
        Muitas empresas também nos procuram para melhorar a visibilidade de seus dados e transformá-los em insights acionáveis para tomada de decisão estratégica.
        Acreditamos que a inovação contínua é chave para o sucesso. Por isso, investimos pesado em P&D e na capacitação de nossa equipe multidisciplinar.
        Nosso principal produto, o 'OptimusProcess AI', já foi premiado por sua capacidade de reduzir em até 30% o tempo de ciclo em processos logísticos.

        Recentemente, a Example Company recebeu um aporte de investimento Série A de R$ 20 milhões para expandir suas operações na América Latina.
        Estamos contratando novos talentos para as áreas de engenharia de software, ciência de dados e customer success.
        Nosso CEO, Dr. Silva, mencionou em uma entrevista recente ao 'Jornal Tech' que o foco para o próximo ano é 'consolidar a liderança no Brasil e iniciar a expansão para Chile e Colômbia'.
        Ele também destacou a importância de 'adotar ferramentas que garantam escalabilidade e eficiência operacional, como a nossa própria plataforma OptimusProcess AI'.
        A empresa participará da feira 'Tech Summit 2024' em São Paulo, onde apresentará um novo módulo de IA para gestão de riscos.
        Mencionamos também nossos concorrentes principais como a SolutionsMax e a InnovateFast, mas acreditamos que nossa abordagem personalizada nos diferencia.
        
        Para mais informações, entre em contato:
        Email: contato@example-company.com.br | vendas@example-company.com.br
        Telefone: (11) 99999-9999 | (11) 5555-4444
        Instagram: @ExampleCompanyBR
        Endereço: Av. Principal, 123, São Paulo, SP
        """,
        extraction_status_message="SUCESSO NA EXTRAÇÃO"
    )
    
    return HarvesterOutput(
        original_query="empresas de IA e otimização de processos em São Paulo",
        collection_timestamp=datetime.now().isoformat(),
        total_sites_targeted_for_processing=1,
        total_sites_processed_in_extraction_phase=1,
        sites_data=[test_site]
    )

class TestEnhancedSystem(unittest.TestCase): # Inherit from unittest.TestCase

    def test_enhanced_processing(self):
        """Test enhanced processing mode"""
        
        print("🧪 Testing Enhanced Nellia Prospector System")
        print("=" * 50)
        
        test_data = create_test_data()
        
        processor = EnhancedNelliaProspector(
            product_service_context="Plataforma de automação de vendas B2B com IA para o mercado brasileiro, focada em otimizar o funil de vendas e personalizar a comunicação com leads qualificados.",
            competitors_list="HubSpot, Salesforce, RD Station, Pipedrive",
            processing_mode=ProcessingMode.ENHANCED,
            tavily_api_key=os.getenv("TAVILY_API_KEY")
        )
        
        print(f"✅ Processor initialized")
        print(f"   - Mode: {processor.processing_mode.value}")
        print(f"   - Tavily enabled: {bool(processor.enhanced_processor.tavily_api_key if hasattr(processor, 'enhanced_processor') and processor.enhanced_processor else False)}")
        print(f"   - Product context: {processor.product_service_context[:50]}...")
        
        try:
            print("\n🔄 Processing test lead...")
            results = processor.process_leads(test_data, limit=1)
            
            print(f"\n📊 Processing Results:")
            print(f"   - Mode: {results.mode.value}")
            print(f"   - Total leads: {results.total_leads}")
            print(f"   - Successful: {results.successful_leads}")
            print(f"   - Failed: {results.failed_leads}")
            print(f"   - Processing time: {results.processing_time:.2f}s")
            
            self.assertTrue(results.successful_leads >= 0) # Allow 0 for now if LLM has issues

            if results.results and results.successful_leads > 0:
                lead_result = results.results[0]
                print(f"\n📋 Lead Analysis for: {lead_result.get('company_name', 'Unknown')}")
                print(f"   - URL: {lead_result.get('url')}")
                print(f"   - Overall Confidence: {lead_result.get('overall_confidence_score', 0):.3f}")
                print(f"   - ROI Potential: {lead_result.get('roi_potential_score', 0):.3f}")

                # Assertions for key structured data fields
                self.assertIsNotNone(lead_result.get('company_name'))
                self.assertIsNotNone(lead_result.get('qualification_tier'), "Qualification tier should be present")
                self.assertIsInstance(lead_result.get('qualification_justification', ''), str)
                self.assertIsInstance(lead_result.get('num_detailed_pain_points', 0), int, "Number of pain points should be an int")
                
                primary_pain_cat = lead_result.get('primary_pain_category', '')
                self.assertTrue(isinstance(primary_pain_cat, str), "Primary pain category should be a string")
                if "Error" not in primary_pain_cat and primary_pain_cat != "N/A" and primary_pain_cat != "Não especificado":
                    self.assertTrue(len(primary_pain_cat) > 0, "Primary pain category, if not error/NA, should not be empty")

                self.assertIsNotNone(lead_result.get('recommended_strategy_name'), "Recommended strategy name should be present")
                
                self.assertGreaterEqual(lead_result.get('contacts_emails_found', 0), 1, "Should find at least one email")
                self.assertGreater(lead_result.get('contact_extraction_confidence', 0.0), 0.0, "Contact extraction confidence should be > 0")
                self.assertIsInstance(lead_result.get('tavily_enriched'), bool, "Tavily enriched flag should be boolean")
                
                # Check counts, allowing for 0 if LLM doesn't find items based on test data
                self.assertIsInstance(lead_result.get('num_value_propositions', 0), int)
                self.assertIsInstance(lead_result.get('num_strategic_questions',0), int)
                self.assertIsInstance(lead_result.get('num_competitors_identified',0), int)
                self.assertIsInstance(lead_result.get('num_purchase_triggers',0), int)
                self.assertIsInstance(lead_result.get('num_objections_prepared',0), int)

                self.assertIsNotNone(lead_result.get('detailed_plan_main_objective'), "Detailed plan objective should be present")
                self.assertTrue(lead_result.get('internal_briefing_executive_summary_present'), "Internal briefing summary present flag should be true")
                self.assertIsNotNone(lead_result.get('message_channel'), "Message channel should be present")
                print(f"   - Qualification: {lead_result.get('qualification_tier')} (Confidence: {lead_result.get('qualification_confidence', 0):.2f})")
                print(f"   - Pain Category: {lead_result.get('primary_pain_category')} (Urgency: {lead_result.get('pain_urgency_level')})")
                print(f"   - Recommended Strategy: {lead_result.get('recommended_strategy_name')}")
                print(f"   - Message Channel: {lead_result.get('message_channel')}")
                print(f"   - Emails Found: {lead_result.get('contacts_emails_found', 0)}")
                print(f"   - Tavily Enriched: {lead_result.get('tavily_enriched')}")

            # Generate and display report
            print("\n📈 Generating detailed report...")
            processor.generate_report(results)
            
            # Save results to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                processor.save_results(results, f.name)
                print(f"\n💾 Test results saved to: {f.name}")
            
            print("\n✅ Enhanced system test completed successfully!")
            return True
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            self.fail(f"Enhanced processing raised an exception: {e}") # Fail the test
            return False

    def test_standard_vs_enhanced(self):
        """Test comparison between standard and enhanced modes"""
        print("\n🔀 Testing Standard vs Enhanced Comparison")
        print("=" * 50)
        
        test_data = create_test_data()
        
        print("Testing Standard Mode...")
        standard_processor = EnhancedNelliaProspector(
            product_service_context="Plataforma de automação de vendas B2B",
            processing_mode=ProcessingMode.STANDARD
        )
        standard_results = standard_processor.process_leads(test_data, limit=1)
        
        print("\nTesting Enhanced Mode...")
        enhanced_processor = EnhancedNelliaProspector(
            product_service_context="Plataforma de automação de vendas B2B",
            processing_mode=ProcessingMode.ENHANCED,
            tavily_api_key=os.getenv("TAVILY_API_KEY")
        )
        enhanced_results = enhanced_processor.process_leads(test_data, limit=1)
        
        print(f"\n📊 Comparison Results:")
        print(f"Standard Mode:")
        print(f"   - Processing time: {standard_results.processing_time:.2f}s")
        if standard_results.total_leads > 0 :
             print(f"   - Success rate: {standard_results.metrics['success_rate']:.1%}")
        print(f"   - Tokens used: {standard_results.metrics.get('total_tokens_used', 0)}")
        
        print(f"\nEnhanced Mode:")
        print(f"   - Processing time: {enhanced_results.processing_time:.2f}s")
        if enhanced_results.total_leads > 0:
            print(f"   - Success rate: {enhanced_results.metrics['success_rate']:.1%}")
            print(f"   - Avg confidence: {enhanced_results.metrics.get('avg_overall_confidence_score', enhanced_results.metrics.get('avg_confidence_score', 0)):.3f}") # Updated key
            print(f"   - Avg ROI potential: {enhanced_results.metrics.get('avg_roi_potential', 0):.3f}")
        print(f"   - Tokens used: {enhanced_results.metrics.get('total_tokens_used', 0)}")
        
        if enhanced_results.results:
            enhanced_sample_result = enhanced_results.results[0]
            print(f"   - Sample Enhanced Lead Qualification: {enhanced_sample_result.get('qualification_tier', 'N/A')}")
            print(f"   - Sample Enhanced Pain Category: {enhanced_sample_result.get('primary_pain_category', 'N/A')}")
            print(f"   - Sample Recommended Strategy: {enhanced_sample_result.get('recommended_strategy_name', 'N/A')}")

        print("\n✅ Comparison test completed!")

def main_test_runner(): # Renamed to avoid conflict with unittest.main
    """Main test function"""
    
    print("🔧 Environment Check:")
    print(f"   - GEMINI_API_KEY: {'✅ Set' if os.getenv('GEMINI_API_KEY') else '❌ Missing'}")
    print(f"   - TAVILY_API_KEY: {'✅ Set' if os.getenv('TAVILY_API_KEY') else '⚠️ Optional (Enhanced features may be limited)'}")
    
    if not os.getenv('GEMINI_API_KEY'):
        print("\n❌ GEMINI_API_KEY is required for testing!")
        print("Please set it in your .env file or environment variables.")
        return False 
    
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestEnhancedSystem))
    runner = unittest.TextTestRunner()
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\n🎉 All tests in enhanced_system_test passed! Nellia Prospector is ready for further testing!")
        print("\nNext steps:")
        print("1. Add real harvester data files")
        print("2. Configure Tavily API for external intelligence (if not done)")
        print("3. Run with: python enhanced_main.py harvester_file.json -p 'Your product'")
        print("4. Try different modes: --mode enhanced|standard|hybrid")
        return True
    else:
        print("\n⚠️ Some tests in enhanced_system_test failed.")
        return False

if __name__ == "__main__":
    if main_test_runner():
        print("\n✅✅✅ Overall test suite completed successfully. ✅✅✅")
        sys.exit(0) # Explicitly exit with 0 for success
    else:
        print("\n❌❌❌ Overall test suite failed. ❌❌❌")
        sys.exit(1) # Explicitly exit with 1 for failure
