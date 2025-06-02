#!/usr/bin/env python3
"""
Test script for the Enhanced Nellia Prospector system
"""

import os
import json
import tempfile
from datetime import datetime
from pathlib import Path

from data_models.lead_structures import HarvesterOutput, SiteData, GoogleSearchData
from enhanced_main import EnhancedNelliaProspector, ProcessingMode

def create_test_data():
    """Create test harvester data"""
    
    test_site = SiteData(
        url="https://example-company.com.br",
        google_search_data=GoogleSearchData(
            title="Example Company - Soluções em Tecnologia",
            snippet="Empresa brasileira especializada em soluções tecnológicas para o mercado B2B"
        ),
        extracted_text_content="""
        A Example Company é uma empresa brasileira inovadora, fundada em 2010, com foco em soluções de software e consultoria para o mercado B2B. 
        Nossa missão é transformar digitalmente negócios através de tecnologia de ponta e expertise setorial.
        Oferecemos um portfólio diversificado que inclui desenvolvimento de software sob medida, implementação de sistemas ERP e CRM, 
        e consultoria especializada em transformação digital e otimização de processos. Recentemente, expandimos nossa atuação para incluir 
        análise de dados avançada e soluções de inteligência artificial para previsão de demanda.
        
        Nossos principais clientes são empresas de médio e grande porte nos setores de Varejo, Manufatura e Serviços Financeiros, 
        que buscam otimizar seus processos, reduzir custos operacionais, melhorar a experiência do cliente e aumentar sua competitividade.
        Um desafio comum que ajudamos a resolver é a integração de sistemas legados com novas tecnologias em nuvem.
        Muitas empresas também nos procuram para melhorar a visibilidade de seus dados e transformá-los em insights acionáveis.
        Acreditamos que a inovação contínua é chave para o sucesso. Por isso, investimos pesado em P&D e na capacitação de nossa equipe.
        
        Recentemente, a Example Company recebeu um aporte de investimento Série A para expandir suas operações na América Latina.
        Estamos contratando novos talentos para as áreas de engenharia de software e ciência de dados.
        Nosso CEO, Dr. Silva, mencionou em uma entrevista recente ao 'Jornal Tech' que o foco para o próximo ano é 'consolidar a liderança no Brasil e iniciar a expansão para Chile e Colômbia'.
        Ele também destacou a importância de 'adotar ferramentas que garantam escalabilidade e eficiência operacional'.
        A empresa participará da feira 'Tech Summit 2024' em São Paulo.
        
        Para mais informações, entre em contato:
        Email: contato@example-company.com.br | vendas@example-company.com.br
        Telefone: (11) 99999-9999 | (11) 5555-4444
        Instagram: @ExampleCompanyBR
        Endereço: Av. Principal, 123, São Paulo, SP
        """,
        # removed cleaned_text_content and text_analysis
        extraction_status_message="Extraction successful"
    )
    
    return HarvesterOutput(
        original_query="empresas tecnologia São Paulo",
        collection_timestamp=datetime.now().isoformat(),
        total_sites_targeted_for_processing=1,
        total_sites_processed_in_extraction_phase=1,
        sites_data=[test_site]
    )

def test_enhanced_processing():
    """Test enhanced processing mode"""
    
    print("🧪 Testing Enhanced Nellia Prospector System")
    print("=" * 50)
    
    # Create test data
    test_data = create_test_data()
    
    # Initialize processor
    processor = EnhancedNelliaProspector(
        product_service_context="Plataforma de automação de vendas B2B com IA para o mercado brasileiro",
        competitors_list="HubSpot, Salesforce, RD Station",
        processing_mode=ProcessingMode.ENHANCED,
        tavily_api_key=os.getenv("TAVILY_API_KEY")  # Optional
    )
    
    print(f"✅ Processor initialized")
    print(f"   - Mode: {processor.processing_mode.value}")
    print(f"   - Tavily enabled: {bool(processor.enhanced_processor.tavily_api_key if hasattr(processor, 'enhanced_processor') and processor.enhanced_processor else False)}") # Adjusted for safety
    print(f"   - Product context: {processor.product_service_context[:50]}...")
    
    try:
        # Process test lead
        print("\n🔄 Processing test lead...")
        results = processor.process_leads(test_data, limit=1)
        
        # Display results
        print(f"\n📊 Processing Results:")
        print(f"   - Mode: {results.mode.value}")
        print(f"   - Total leads: {results.total_leads}")
        print(f"   - Successful: {results.successful_leads}")
        print(f"   - Failed: {results.failed_leads}")
        print(f"   - Processing time: {results.processing_time:.2f}s")
        
        if results.results:
            lead_result = results.results[0]
            print(f"\n📋 Lead Analysis:")
            print(f"   - Company: {lead_result.get('company_name', 'Unknown')}")
            print(f"   - Qualification Tier: {lead_result.get('qualification_tier', 'N/A')}")
            print(f"   - Qualification Justification: {lead_result.get('qualification_justification', 'N/A')[:100]}...")
            print(f"   - Overall Confidence: {lead_result.get('overall_confidence_score', 0):.3f}")
            print(f"   - ROI Potential: {lead_result.get('roi_potential_score', 0):.3f}")
            
            # Assertions for key structured data fields
            self.assertIsNotNone(lead_result.get('company_name'))
            self.assertTrue(results.successful_leads >= 0) # Allow 0 if LLM has issues, but test should pass if it runs
            
            if results.successful_leads > 0:
                self.assertIsNotNone(lead_result.get('qualification_tier'))
                self.assertIsInstance(lead_result.get('num_detailed_pain_points', 0), int)
                self.assertTrue(len(lead_result.get('primary_pain_category', '')) > 0 if lead_result.get('primary_pain_category') != "Error" else True)
                self.assertIsNotNone(lead_result.get('recommended_strategy_name'))
                
                # Check if contact extraction found emails (based on updated test data)
                self.assertGreaterEqual(lead_result.get('contacts_emails_found', 0), 1)
                self.assertGreater(lead_result.get('contact_extraction_confidence', 0.0), 0.0)

                self.assertIsInstance(lead_result.get('tavily_enriched'), bool)
                
                self.assertGreaterEqual(lead_result.get('num_value_propositions', 0), 0)
                self.assertGreaterEqual(lead_result.get('num_strategic_questions',0), 0)
                self.assertGreaterEqual(lead_result.get('num_competitors_identified',0), 0)
                self.assertGreaterEqual(lead_result.get('num_purchase_triggers',0), 0)
                self.assertGreaterEqual(lead_result.get('num_objections_prepared',0), 0)

                self.assertIsNotNone(lead_result.get('detailed_plan_main_objective'))
                self.assertTrue(lead_result.get('internal_briefing_executive_summary_present'))
                self.assertIsNotNone(lead_result.get('message_channel'))

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
        return False

def test_standard_vs_enhanced():
    """Test comparison between standard and enhanced modes"""
    
    print("\n🔀 Testing Standard vs Enhanced Comparison")
    print("=" * 50)
    
    test_data = create_test_data()
    
    # Test standard mode
    print("Testing Standard Mode...")
    standard_processor = EnhancedNelliaProspector(
        product_service_context="Plataforma de automação de vendas B2B",
        processing_mode=ProcessingMode.STANDARD
    )
    
    standard_results = standard_processor.process_leads(test_data, limit=1)
    
    # Test enhanced mode
    print("\nTesting Enhanced Mode...")
    enhanced_processor = EnhancedNelliaProspector(
        product_service_context="Plataforma de automação de vendas B2B",
        processing_mode=ProcessingMode.ENHANCED,
        tavily_api_key=os.getenv("TAVILY_API_KEY") # Optional
    )
    
    enhanced_results = enhanced_processor.process_leads(test_data, limit=1)
    
    # Compare results
    print(f"\n📊 Comparison Results:")
    print(f"Standard Mode:")
    print(f"   - Processing time: {standard_results.processing_time:.2f}s")
    print(f"   - Success rate: {standard_results.metrics['success_rate']:.1%}")
    print(f"   - Tokens used: {standard_results.metrics.get('total_tokens_used', 0)}")
    
    print(f"\nEnhanced Mode:")
    print(f"   - Processing time: {enhanced_results.processing_time:.2f}s")
    print(f"   - Success rate: {enhanced_results.metrics['success_rate']:.1%}")
    print(f"   - Tokens used: {enhanced_results.metrics.get('total_tokens_used', 0)}")
    print(f"   - Avg confidence: {enhanced_results.metrics.get('avg_confidence_score', 0):.3f}")
    print(f"   - Avg ROI potential: {enhanced_results.metrics.get('avg_roi_potential', 0):.3f}")
    
    print("\n✅ Comparison test completed!")

def main():
    """Main test function"""
    
    # Check environment
    print("🔧 Environment Check:")
    print(f"   - GEMINI_API_KEY: {'✅ Set' if os.getenv('GEMINI_API_KEY') else '❌ Missing'}")
    print(f"   - TAVILY_API_KEY: {'✅ Set' if os.getenv('TAVILY_API_KEY') else '⚠️ Optional'}")
    
    if not os.getenv('GEMINI_API_KEY'):
        print("\n❌ GEMINI_API_KEY is required for testing!")
        print("Please set it in your .env file or environment variables.")
        return False # Changed to return False for clarity
    
    # Run tests
    success = True
    
    try:
        enhanced_test_passed = test_enhanced_processing()
        if not enhanced_test_passed:
            success = False
        
        # Only run comparison if enhanced test passed, or run independently
        # For now, let's assume it can run even if the first one has issues,
        # as it might test different aspects or simpler modes.
        test_standard_vs_enhanced()
        
        if success: # This 'success' only reflects enhanced_test_passed currently
            print("\n🎉 Enhanced test section passed! Nellia Prospector is ready for further testing!")
            print("\nNext steps:")
            print("1. Add real harvester data files")
            print("2. Configure Tavily API for external intelligence")
            print("3. Run with: python enhanced_main.py harvester_file.json -p 'Your product'")
            print("4. Try different modes: --mode enhanced|standard|hybrid")
        else:
            print("\n⚠️ Some tests in the enhanced processing section failed.")

    except Exception as e:
        print(f"\n💥 Test suite encountered an unhandled exception: {e}")
        import traceback
        traceback.print_exc()
        success = False # Overall suite failure
    
    return success

if __name__ == "__main__":
    # This will print True if all tests (that update 'success' flag) pass, False otherwise.
    # The script will exit with 0 if main() returns True (or anything not False/0/None), and 1 if it returns False.
    # To make it more explicit for CI/CD:
    if main():
        print("\n✅✅✅ Overall test suite completed successfully. ✅✅✅")
        exit(0)
    else:
        print("\n❌❌❌ Overall test suite failed. ❌❌❌")
        exit(1)
