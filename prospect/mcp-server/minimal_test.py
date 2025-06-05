#!/usr/bin/env python3
"""
Minimal MCP Server Test - Tests core functionality without agent loading
"""

import os
import sys
from loguru import logger

# Add prospect directory to path
prospect_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if prospect_root not in sys.path:
    sys.path.insert(0, prospect_root)

def test_basic_imports():
    """Test basic imports"""
    try:
        from flask import Flask
        from pydantic import BaseModel, Field
        from typing import List, Dict, Any, Optional
        print("✓ Basic imports successful")
        return True
    except Exception as e:
        print(f"✗ Basic imports failed: {e}")
        return False

def test_mcp_models():
    """Test MCP data models"""
    try:
        # Import from local MCP data_models file
        import data_models as mcp_data_models
        LeadProcessingState = mcp_data_models.LeadProcessingState
        AgentExecutionRecord = mcp_data_models.AgentExecutionRecord
        print("✓ MCP data models import successful")
        return True
    except Exception as e:
        print(f"✗ MCP data models failed: {e}")
        return False

def test_llm_client():
    """Test LLM client initialization"""
    try:
        from core_logic.llm_client import LLMClientFactory
        # Don't actually create client (requires API keys)
        print("✓ LLM client factory import successful")
        return True
    except Exception as e:
        print(f"✗ LLM client import failed: {e}")
        return False

def test_flask_app():
    """Test basic Flask app creation"""
    try:
        from flask import Flask
        app = Flask(__name__)
        
        @app.route('/test')
        def test_route():
            return {"status": "working", "message": "MCP server core is operational"}
            
        client = app.test_client()
        response = client.get('/test')
        
        if response.status_code == 200:
            print("✓ Flask app creation and test route successful")
            return True
        else:
            print(f"✗ Flask test route failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Flask app test failed: {e}")
        return False

def test_database_models():
    """Test database model creation"""
    try:
        from database import SessionLocal, get_database
        from models import Lead, AgentExecution
        print("✓ Database models import successful")
        return True
    except Exception as e:
        print(f"✗ Database models failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=== MCP Server Minimal Test Suite ===")
    
    tests = [
        ("Basic Imports", test_basic_imports),
        ("MCP Data Models", test_mcp_models),
        ("LLM Client", test_llm_client),
        ("Flask App", test_flask_app),
        ("Database Models", test_database_models)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- Testing {test_name} ---")
        if test_func():
            passed += 1
        else:
            logger.error(f"Test {test_name} failed")
    
    print(f"\n=== Results: {passed}/{total} tests passed ===")
    
    if passed == total:
        print("🎉 All core MCP server components are working!")
        return True
    else:
        print("⚠️  Some components need attention, but core functionality may still work")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
