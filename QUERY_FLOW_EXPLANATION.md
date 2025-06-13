# Explaining the `search_query` Flow in the Nellia Prospector Pipeline

This document clarifies how a custom `search_query` provided by a user via an API request is intended to flow through the `mcp_server` to the `PipelineOrchestrator` and ultimately be used by the lead harvesting agents (e.g., ADK1).

## Intended Flow of `search_query`

The system is designed to allow users to specify a custom `search_query` for the lead harvesting process. Here's how it works:

1.  **API Request to `mcp_server.py`:**
    *   The user makes a POST request to the `/api/v2/execute_streaming_prospect` endpoint.
    *   This request must contain a JSON payload.

2.  **Structuring the Payload:**
    *   To use a custom `search_query`, it **must** be included within the `business_context` object in the JSON payload, under the key `"search_query"`.
    *   **Correct Payload Structure Example:**
        ```json
        {
          "user_id": "your_user_id",
          "job_id": "your_job_id",
          "business_context": {
            "search_query": "custom search terms for technology companies in Brazil",
            "product_service_description": "Description of your product/service...",
            "ideal_customer": "Details about your ideal customer...",
            "business_description": "Your business description...",
            "value_proposition": "Your value proposition...",
            "industry_focus": ["technology", "saas"],
            "pain_points": ["difficulty scaling", "manual processes"],
            "competitors": ["competitor A", "competitor B"]
            // ... other relevant business_context fields ...
          }
        }
        ```

3.  **Processing in `mcp_server.py`:**
    *   The `mcp_server.py` extracts the entire `business_context` object (the dictionary) from the request payload.
    *   It then passes this complete `business_context` object directly to the `PipelineOrchestrator` when it's initialized.

4.  **Usage in `PipelineOrchestrator.py`:**
    *   The `PipelineOrchestrator` stores the received `business_context`.
    *   In its `execute_streaming_pipeline` method, it specifically attempts to retrieve the search query using:
        ```python
        search_query = self.business_context.get("search_query", "empresas de tecnologia")
        ```
    *   This line of code means:
        *   If a key named `"search_query"` exists within the `self.business_context` object, its value will be used as the `search_query`.
        *   If the key `"search_query"` is **not found** in `self.business_context`, the `search_query` will default to `"empresas de tecnologia"`.
    *   This `search_query` is then passed to the lead harvesting agents (e.g., ADK1 agent via the `_search_leads` method).

## Verification and Conclusion

A thorough review of the `mcp_server.py` and `pipeline_orchestrator.py` code confirms that the system **correctly attempts to extract and use the `search_query` from the provided `business_context` object.**

If you observe that your custom `search_query` is not being used and the system is defaulting to `"empresas de tecnologia"`, it is almost certainly due to one of the following reasons related to the API request payload:

*   The `search_query` field is missing entirely from the `business_context` object.
*   The `search_query` field is present but is misspelled (e.g., `Search_Query`, `searchquery`). Remember that JSON keys are case-sensitive.
*   The `search_query` field is present but is not nested directly under the `business_context` object. For instance, it might be incorrectly placed at the top level of the payload alongside `business_context`.

**No code changes were required to "fix" the usage of `search_query`**, as the existing implementation correctly adheres to the logic of retrieving it from `business_context.search_query`.

## How to Ensure Your `search_query` is Used

To ensure your custom `search_query` is used by the pipeline:

1.  **Verify your API request payload structure.**
2.  Make sure the `search_query` key-value pair is directly inside the `business_context` dictionary.
3.  Ensure the key is exactly `search_query` (all lowercase).

By following the payload structure shown in the example above, your custom search query will be correctly passed to and utilized by the lead harvesting agents.
