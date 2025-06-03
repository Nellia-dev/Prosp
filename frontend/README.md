# Frontend for Nellia Prospector MCP

This directory is reserved for the frontend application that will interact with the MCP (Mission Control Panel) server.

The frontend will be responsible for:

*   Displaying the status of lead processing runs.
*   Showing detailed progress for individual leads, including the outputs of each agent.
*   Providing an interface to view agent metrics and other relevant data from the MCP server.

Development of the frontend components will occur separately.

**MCP Server API Endpoints (for frontend consumption - see `MCP.md` for full details):**

*   `GET /api/lead/<lead_id>/status`: To get status and agent execution details for a specific lead.
*   `GET /api/run/<run_id>/status`: To get a list of leads and their overall status for a specific processing run.
