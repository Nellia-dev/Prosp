#!/usr/bin/env python3
"""
Database initialization script for MCP Server.
Run this to create the database tables.
"""

import sys
import os

# Add the mcp-server directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now import the modules
import database
import models

if __name__ == "__main__":
    print("Initializing MCP Server database...")
    try:
        database.init_db()
        print("✅ Database initialized successfully!")
        print("📋 Created tables:")
        print("   - leads_processing_state")
        print("   - agent_execution_records")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)
