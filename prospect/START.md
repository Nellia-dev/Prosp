# Getting Started with Enhanced Nellia Prospector

This guide provides instructions on how to set up and run the Enhanced Nellia Prospector application (`enhanced_main.py`).

## 1. Prerequisites

*   **Python:** Version 3.9 or higher is recommended.
*   **pip:** Python package installer (usually comes with Python).
*   **Git:** For cloning the repository.
*   **Virtual Environment (Recommended):** `venv` or `conda`.

## 2. Environment Setup

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Create and Activate a Virtual Environment (Recommended):**
    *   Using `venv`:
        ```bash
        python -m venv venv
        source venv/bin/activate  # On Windows: venv\Scripts\activate
        ```
    *   Using `conda`:
        ```bash
        conda create -n nellia_env python=3.9
        conda activate nellia_env
        ```

3.  **Install Dependencies:**
    Ensure all necessary dependencies are listed in `requirements.txt`. Then run:
    ```bash
    pip install -r requirements.txt
    ```
    *(If `requirements.txt` is missing or incomplete, it should be generated first based on project imports.)*

## 3. Environment Variables

The application requires certain API keys to be set as environment variables. You can set them directly in your shell, or create a `.env` file in the root of the project and load them using a library like `python-dotenv` (which should be added to `requirements.txt` if not already present).

Create a `.env` file (copy from `.env.example` if it exists):
```env
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
TAVILY_API_KEY="YOUR_TAVILY_API_KEY" 
# Add other necessary environment variables here
```

The application (`enhanced_main.py` and `cw.py`) uses `load_dotenv()` to load these variables.

## 4. Running the Application (`enhanced_main.py`)

The main script for running the enhanced prospector is `enhanced_main.py`.

**Command-Line Usage:**

```bash
python enhanced_main.py <harvester_file_path> --product "Your Product/Service Description" [options]
```

**Required Arguments:**

*   `<harvester_file_path>`: Path to the JSON file containing harvester output (e.g., `leads_example.json`).
*   `--product` or `-p`: A string describing the product or service you are offering, which the AI will use for context. Example: `"Nossa plataforma de IA para otimização de processos jurídicos"`.

**Common Options:**

*   `--mode` or `-m`: Processing mode. Choices:
    *   `standard`: Original 2-agent pipeline.
    *   `enhanced`: (Default) New comprehensive processing pipeline using all refactored agents.
    *   `hybrid`: Runs both standard and enhanced modes for a subset of leads for comparison.
*   `--competitors` or `-c`: A comma-separated string of known competitors. Example: `"HubSpot,Salesforce,RD Station"`.
*   `--limit` or `-n`: Limit the number of leads to process from the input file. Example: `--limit 10`.
*   `--output` or `-o`: Specify the output JSON file path. (Default: auto-generated filename like `enhanced_prospector_results_<mode>_<timestamp>.json`).
*   `--log-level` or `-l`: Set the logging level. Choices: `DEBUG`, `INFO`, `WARNING`, `ERROR`. (Default: `INFO`).

**Examples:**

1.  **Run in enhanced mode (default) for all leads:**
    ```bash
    python enhanced_main.py path/to/your/leads.json --product "Serviços de consultoria em nuvem AWS"
    ```

2.  **Run in standard mode, limiting to 5 leads:**
    ```bash
    python enhanced_main.py path/to/your/leads.json --product "Software de gestão financeira para PMEs" --mode standard --limit 5
    ```

3.  **Run in hybrid mode, specifying competitors and an output file:**
    ```bash
    python enhanced_main.py path/to/your/leads.json --product "Plataforma de marketing digital B2B" --mode hybrid --competitors "CompetitorX,CompetitorY" --output custom_results.json
    ```

## 5. Input File Format

The application expects an input JSON file (referred to as `harvester_file_path`) that conforms to the `HarvesterOutput` Pydantic model defined in `data_models/lead_structures.py`.

A typical structure might look like:
```json
{
  "original_query": "empresas de tecnologia em São Paulo",
  "collection_timestamp": "2023-10-26T10:00:00Z",
  "total_sites_targeted_for_processing": 1,
  "total_sites_processed_in_extraction_phase": 1,
  "sites_data": [
    {
      "url": "https://example-company.com.br",
      "google_search_data": {
        "title": "Example Company - Soluções em Tecnologia",
        "snippet": "Empresa brasileira especializada em soluções tecnológicas..."
      },
      "extracted_text_content": "Texto extraído do site da Example Company...",
      "extraction_status_message": "SUCESSO NA EXTRAÇÃO",
      "screenshot_filepath": null
    }
    // ... more sites_data items
  ]
}
```
*(Make sure your input JSON matches the structure defined in `data_models.lead_structures.HarvesterOutput` and `data_models.lead_structures.SiteData`)*

## 6. Output File

The application generates a JSON output file containing:
*   A summary of the processing run (mode, counts, time, metrics).
*   Configuration details used for the run.
*   A list of processed leads, with detailed analysis and structured data from the `ComprehensiveProspectPackage` for each lead.

The structure of this output is defined by the serialization of the `ProcessingResults` object in `enhanced_main.py`.

---

Happy Prospecting!
```
