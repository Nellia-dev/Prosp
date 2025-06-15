#!/usr/bin/env python3
"""
Production Pipeline Test Script
Tests the complete workflow: RAG query generation -> ADK1 search -> Lead enrichment -> Event streaming
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any

# Add the prospect directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline_orchestrator import PipelineOrchestrator
from loguru import logger

async def test_production_pipeline():
    """Test the complete production pipeline workflow"""
    
    # Comprehensive business context for testing
    business_context = {
        "business_description": "We provide AI-powered CRM solutions for small and medium businesses",
        "product_service_description": "Intelligent customer relationship management software with automated lead scoring, sales pipeline optimization, and predictive analytics",
        "value_proposition": "Increase sales efficiency by 40% and reduce manual data entry by 80% with our AI automation",
        "ideal_customer": "Small to medium businesses with 10-100 employees in technology, consulting, or professional services sectors",
        "industry_focus": ["Technology", "SaaS", "Consulting", "Professional Services"],
        "pain_points": [
            "Manual data entry consuming too much time",
            "Difficulty tracking leads through sales pipeline", 
            "Poor sales forecasting accuracy",
            "Lost leads due to poor follow-up"
        ],
        "competitors": ["Salesforce", "HubSpot", "Pipedrive"],
        "target_market": "SMB market in North America and Europe",
        "location": "United States, Canada, United Kingdom",
        "max_leads_to_generate": 3,
        "user_search_query": "companies looking for CRM software automation"  # User input
    }
    
    user_id = "test_user_production"
    job_id = f"prod_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    logger.info("🚀 Starting Production Pipeline Test")
    logger.info("=" * 60)
    logger.info(f"📋 Job ID: {job_id}")
    logger.info(f"👤 User ID: {user_id}")
    logger.info(f"🎯 Business: {business_context['business_description']}")
    logger.info(f"🔍 User Query: {business_context['user_search_query']}")
    logger.info("=" * 60)
    
    try:
        # Initialize the pipeline orchestrator
        logger.info("🔧 Initializing Production Pipeline...")
        orchestrator = PipelineOrchestrator(
            business_context=business_context,
            user_id=user_id,
            job_id=job_id
        )
        logger.success("✅ Pipeline initialized successfully")
        
        # Track pipeline execution
        event_count = 0
        lead_count = 0
        query_generated = False
        search_executed = False
        enrichment_completed = False
        
        start_time = datetime.now()
        
        logger.info("🚀 Starting streaming pipeline execution...")
        
        async for event in orchestrator.execute_streaming_pipeline():
            event_count += 1
            event_type = event.get("event_type", "unknown")
            timestamp = event.get("timestamp", "")
            
            logger.info(f"📨 Event #{event_count}: {event_type} @ {timestamp}")
            
            if event_type == "pipeline_start":
                initial_query = event.get("initial_query", "")
                max_leads = event.get("max_leads_to_generate", 0)
                logger.info(f"🎯 Pipeline started with query: '{initial_query}' (max leads: {max_leads})")
                query_generated = True
                
            elif event_type == "lead_generated":
                lead_count += 1
                lead_data = event.get("lead_data", {})
                company_name = lead_data.get("company_name", "Unknown")
                website = lead_data.get("website", "No website")
                description = lead_data.get("description", "No description")[:100]
                
                logger.info(f"🎯 Lead #{lead_count} Generated:")
                logger.info(f"   🏢 Company: {company_name}")
                logger.info(f"   🌐 Website: {website}")
                logger.info(f"   📝 Description: {description}...")
                
                search_executed = True
                
            elif event_type == "lead_enrichment_start":
                company_name = event.get("company_name", "Unknown")
                lead_id = event.get("lead_id", "Unknown")
                logger.info(f"🔍 Starting enrichment for {company_name} (ID: {lead_id})")
                
            elif event_type == "lead_enrichment_end":
                lead_id = event.get("lead_id", "Unknown")
                success = event.get("success", False)
                error_message = event.get("error_message", "")
                
                if success:
                    logger.success(f"✅ Enrichment completed for lead {lead_id}")
                    enrichment_completed = True
                else:
                    logger.error(f"❌ Enrichment failed for lead {lead_id}: {error_message}")
                    
            elif event_type == "status_update":
                status_message = event.get("status_message", "")
                logger.info(f"📊 Status: {status_message}")
                
            elif event_type == "pipeline_end":
                total_leads = event.get("total_leads_generated", 0)
                execution_time = event.get("execution_time_seconds", 0)
                success = event.get("success", False)
                
                logger.info("🏁 Pipeline Completed!")
                logger.info(f"   📊 Total leads: {total_leads}")
                logger.info(f"   ⏱️  Execution time: {execution_time:.2f}s")
                logger.info(f"   ✅ Success: {success}")
                break
                
            elif event_type == "pipeline_error":
                error_msg = event.get("error_message", "Unknown error")
                logger.error(f"❌ Pipeline Error: {error_msg}")
                break
                
            # Safety limit
            if event_count > 100:
                logger.warning("⚠️ Reached safety limit, stopping test")
                break
        
        # Final validation
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        logger.info("\n" + "=" * 60)
        logger.info("📋 PRODUCTION TEST RESULTS")
        logger.info("=" * 60)
        
        results = {
            "query_generation": "✅ PASS" if query_generated else "❌ FAIL",
            "lead_search": "✅ PASS" if search_executed else "❌ FAIL", 
            "lead_enrichment": "✅ PASS" if enrichment_completed else "❌ FAIL",
            "event_streaming": "✅ PASS" if event_count > 0 else "❌ FAIL",
            "total_events": event_count,
            "total_leads": lead_count,
            "execution_time": f"{total_time:.2f}s"
        }
        
        for test, result in results.items():
            logger.info(f"{test.replace('_', ' ').title()}: {result}")
        
        # Overall assessment
        all_passed = all("✅" in str(v) for k, v in results.items() if k not in ["total_events", "total_leads", "execution_time"])
        
        if all_passed and event_count > 0 and lead_count > 0:
            logger.success("\n🎉 PRODUCTION TEST PASSED! All systems working correctly.")
            return True
        else:
            logger.error(f"\n💥 PRODUCTION TEST FAILED! Issues detected.")
            return False
            
    except Exception as e:
        logger.error(f"❌ Critical error during production test: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test runner"""
    logger.info("🧪 Production Pipeline Test Suite")
    logger.info("Testing: RAG Query Generation + ADK1 Search + Lead Enrichment + Event Streaming")
    logger.info("=" * 80)
    
    success = await test_production_pipeline()
    
    logger.info("=" * 80)
    if success:
        logger.success("🎉 ALL TESTS PASSED - Pipeline is production ready!")
        return 0
    else:
        logger.error("💥 TESTS FAILED - Pipeline needs fixes before production")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)