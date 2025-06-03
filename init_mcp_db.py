from mcp_server import database, models

def main():
    print("Initializing MCP Server database...")
    # This creates all tables based on models defined in mcp_server.models
    # It's safe to call multiple times - it won't recreate existing tables.
    database.init_db()
    print("Database tables created (if they didn't exist already).")
    print("If you made changes to mcp_server.models, you might need to manually manage migrations for an existing database.")

if __name__ == "__main__":
    main()
