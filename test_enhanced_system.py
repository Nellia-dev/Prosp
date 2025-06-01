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
        A Example Company é uma empresa brasileira especializada em soluções tecnológicas 
        para o mercado B2B. Oferecemos serviços de desenvolvimento de software, 
        consultoria em transformação digital e implementação de sistemas ERP.
        
        Nossos principais clientes são empresas de médio e grande porte que buscam 
        otimizar seus processos e aumentar sua competitividade no mercado.
        
        Contato: contato@example-company.com.br
        Telefone: (11) 99999-9999
        """,
        cleaned_text_content="""
        Example Company soluções tecnológicas mercado B2B desenvolvimento software 
        consultoria transformação digital implementação sistemas ERP clientes 
        médio grande porte otimizar processos competitividade
        """,
        text_analysis={
            "word_count": 45,
            "char_count": 280,
            "language": "pt"
        },
        extraction_status_message="Extraction successful"  # Added this line
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
            print(f"   - Qualification: {lead_result.get('qualification_tier', 'Unknown')}")
            print(f"   - Confidence: {lead_result.get('confidence_score', 0):.3f}")
            print(f"   - ROI Potential: {lead_result.get('roi_potential_score', 0):.3f}")
            print(f"   - Pain Category: {lead_result.get('primary_pain_category', 'Unknown')}")
            print(f"   - Urgency: {lead_result.get('urgency_level', 'Unknown')}")
            print(f"   - Strategy: {lead_result.get('selected_strategy', 'Unknown')}")
            print(f"   - Channel: {lead_result.get('primary_channel', 'Unknown')}")
            
            # Contact information
            contact_info = lead_result.get('contact_information', {})
            print(f"   - Emails found: {contact_info.get('emails_found', 0)}")
            print(f"   - Contact confidence: {contact_info.get('extraction_confidence', 0):.3f}")
            
            # Message details
            message_info = lead_result.get('personalized_message', {})
            print(f"   - Message channel: {message_info.get('channel', 'Unknown')}")
            print(f"   - Subject: {message_info.get('subject', 'N/A')[:50]}...")
            print(f"   - Personalization score: {message_info.get('personalization_score', 0):.3f}")
            print(f"   - Est. response rate: {message_info.get('estimated_response_rate', 0):.1%}")
        
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
