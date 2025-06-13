#!/usr/bin/env python3
"""
Test script to verify the pipeline orchestrator fixes
"""

import asyncio
import json
import sys
import os
from datetime import datetime

# Add the prospect directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline_orchestrator import PipelineOrchestrator
from loguru import logger

async def test_pipeline_execution():
    """Test the pipeline execution to see if the infinite loop is fixed"""
    
    # Test business context
    business_context = {
        "business_description": "AI-powered CRM software for small businesses",
        "product_service_description": "We provide intelligent customer relationship management solutions",
        "value_proposition": "Increase sales efficiency by 40% with AI automation",
        "ideal_customer": "Small to medium businesses with 10-100 employees",
        "industry_focus": ["Technology", "SaaS", "B2B"],
        "pain_points": ["Manual data entry", "Lead tracking", "Sales inefficiency"],
        "competitors": ["Salesforce", "HubSpot"],
        "max_leads_to_generate": 3  # Small number for testing
    }
    
    user_id = "test_user_123"
    job_id = f"test_job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    logger.info(f"🧪 Starting pipeline test with job_id: {job_id}")
    
    try:
        # Initialize the pipeline orchestrator
        logger.info("📝 Initializing PipelineOrchestrator...")
        orchestrator = PipelineOrchestrator(
            business_context=business_context,
            user_id=user_id,
            job_id=job_id,
            use_hybrid=False  # Disable hybrid for simpler testing
        )
        logger.info("✅ PipelineOrchestrator initialized successfully")
        
        # Execute the streaming pipeline
        logger.info("🚀 Starting execute_streaming_pipeline...")
        event_count = 0
        lead_count = 0
        
        async for event in orchestrator.execute_streaming_pipeline():
            event_count += 1
            event_type = event.get("event_type", "unknown")
            
            logger.info(f"📨 Event #{event_count}: {event_type}")
            
            if event_type == "lead_generated":
                lead_count += 1
                lead_data = event.get("lead_data", {})
                company_name = lead_data.get("company_name", "Unknown")
                logger.info(f"🎯 Lead #{lead_count} generated: {company_name}")
            
            elif event_type == "pipeline_end":
                total_leads = event.get("total_leads_generated", 0)
                execution_time = event.get("execution_time_seconds", 0)
                logger.info(f"🏁 Pipeline completed! Total leads: {total_leads}, Time: {execution_time:.2f}s")
                break
                
            elif event_type == "pipeline_error":
                error_msg = event.get("error_message", "Unknown error")
                logger.error(f"❌ Pipeline error: {error_msg}")
                break
                
            # Safety limit to avoid truly infinite loops during testing
            if event_count > 50:
                logger.warning("⚠️ Reached safety limit of 50 events, stopping test")
                break
        
        if event_count == 0:
            logger.error("❌ CRITICAL: Pipeline yielded NO events - infinite loop still present!")
            return False
        elif lead_count == 0:
            logger.error("❌ CRITICAL: Pipeline yielded events but NO leads were generated!")
            return False
        else:
            logger.success(f"✅ SUCCESS: Pipeline executed correctly! {event_count} events, {lead_count} leads")
            return True
            
    except Exception as e:
        logger.error(f"❌ Exception during pipeline execution: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    logger.info("🔧 Testing Pipeline Orchestrator Fixes")
    logger.info("=" * 50)
    
    success = await test_pipeline_execution()
    
    logger.info("=" * 50)
    if success:
        logger.success("🎉 TEST PASSED: Pipeline is working correctly!")
        return 0
    else:
        logger.error("💥 TEST FAILED: Pipeline still has issues!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)