# Nellia Prospector - AI-Powered B2B Lead Processing System

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/AI-Powered-green.svg" alt="AI">
  <img src="https://img.shields.io/badge/B2B-Lead_Generation-orange.svg" alt="B2B">
</div>

## 🚀 Overview

Nellia Prospector is a sophisticated multi-agent system that transforms raw lead data into actionable, high-quality engagement opportunities. The system processes potential leads provided by an external "Harvester" service, analyzes each lead, creates personas, develops tailored approach plans, and crafts personalized messages for initial outreach.

**Key Features:**
- 🤖 Multi-agent architecture for specialized processing
- 📊 Intelligent lead analysis and scoring
- 👤 Automated persona creation
- 📝 Personalized message generation
- 🔍 LGPD compliant data processing
- 📈 527% average ROI (as per website claims)

## 📋 Table of Contents

- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Agent Pipeline](#agent-pipeline)
- [Development](#development)
- [API Reference](#api-reference)
- [Contributing](#contributing)

## 🏗️ Architecture

The system is built with a modular, multi-agent architecture:

```
Input (Harvester JSON) → Lead Intake & Validation → Lead Analysis → 
Persona Creation → Approach Strategy → Message Crafting → Output
```

### Project Structure

```
nellia_prospector/
├── main.py                    # Main orchestrator
├── agents/                    # Agent implementations
│   ├── base_agent.py         # Abstract base agent
│   ├── lead_intake_agent.py  # Validation agent
│   ├── lead_analysis_agent.py # Analysis agent
│   └── ...                   # Other agents (coming soon)
├── core_logic/               # Core business logic
│   ├── llm_client.py        # LLM abstraction layer
│   └── nlp_utils.py         # NLP utilities
├── data_models/              # Pydantic data models
│   └── lead_structures.py   # Lead data structures
├── harvester_output/         # Example harvester outputs
└── utils/                    # Utility functions
```

## 🛠️ Installation

### Prerequisites

- Python 3.8 or higher
- Virtual environment (recommended)
- Playwright (for harvester)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/nellia/nellia-prospector.git
   cd nellia-prospector
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers** (if using harvester)
   ```bash
   playwright install
   ```

5. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# LLM API Keys (at least one required)
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here  # Optional

# Agent Configuration
AGENT_TEMPERATURE=0.7
AGENT_MAX_TOKENS=8192
AGENT_MAX_RETRIES=3
AGENT_RETRY_DELAY=5

# Pipeline Configuration
PIPELINE_BATCH_SIZE=10
PIPELINE_LOG_LEVEL=INFO
```

## 📖 Usage

### Basic Usage

Process leads from a harvester output file:

```bash
python main.py harvester_output/example.json -p "AI-powered lead generation platform"
```

### Command Line Options

```bash
python main.py [OPTIONS] INPUT_FILE

Arguments:
  INPUT_FILE  Path to harvester JSON output file

Options:
  -p, --product-service TEXT   Product/service being offered [required]
  -o, --output PATH           Output file path (default: auto-generated)
  -l, --log-level TEXT        Log level [DEBUG|INFO|WARNING|ERROR]
  --log-file PATH             Log file path
  --skip-failed               Skip leads with failed extraction
  -n, --limit INTEGER         Limit number of leads to process
  --help                      Show this message and exit
```

### Examples

1. **Process with custom output file:**
   ```bash
   python main.py data.json -p "Legal tech SaaS" -o results/output.json
   ```

2. **Process only first 10 leads with debug logging:**
   ```bash
   python main.py data.json -p "Consultoria digital" -n 10 -l DEBUG
   ```

3. **Skip failed extractions:**
   ```bash
   python main.py data.json -p "Software de gestão" --skip-failed
   ```

## 🤖 Agent Pipeline

### 1. Lead Intake & Validation Agent

Validates and cleans raw lead data:
- Checks data structure integrity
- Filters failed extractions (optional)
- Cleans and normalizes text content
- Logs validation errors

### 2. Lead Analysis Agent

Performs deep analysis of lead data:
- Identifies company sector and services
- Detects recent activities and news
- Identifies potential challenges/pain points
- Calculates relevance score (0-1)
- Generates opportunity fit assessment

### 3. Persona Creation Agent (Coming Soon)

Creates detailed decision-maker personas:
- Identifies likely role/title
- Maps professional goals
- Identifies key challenges
- Determines communication preferences

### 4. Approach Strategy Agent (Coming Soon)

Develops tailored approach strategies:
- Recommends communication channels
- Defines tone and messaging style
- Identifies key value propositions
- Prepares objection handling

### 5. Message Crafting Agent (Coming Soon)

Creates personalized outreach messages:
- Generates email/LinkedIn messages
- Incorporates personalization elements
- Includes clear call-to-action
- Optimizes for engagement

## 💻 Development

### Running Tests

```bash
pytest tests/
```

### Code Style

We use Black for code formatting:

```bash
black .
```

### Adding New Agents

1. Create new agent class inheriting from `BaseAgent`
2. Implement the `process()` method
3. Define input/output data models
4. Add to pipeline in `main.py`

Example:
```python
from agents.base_agent import BaseAgent
from data_models.lead_structures import InputModel, OutputModel

class MyNewAgent(BaseAgent[InputModel, OutputModel]):
    def process(self, input_data: InputModel) -> OutputModel:
        # Your agent logic here
        pass
```

## 📚 API Reference

### Data Models

#### HarvesterOutput
```python
{
    "original_query": str,
    "collection_timestamp": datetime,
    "total_sites_targeted_for_processing": int,
    "total_sites_processed_in_extraction_phase": int,
    "sites_data": List[SiteData]
}
```

#### SiteData
```python
{
    "url": str,
    "google_search_data": GoogleSearchData,
    "extracted_text_content": str,
    "extraction_status_message": str,
    "screenshot_filepath": Optional[str]
}
```

### Output Format

The system outputs a JSON file with:
```json
{
    "processing_timestamp": "ISO 8601 timestamp",
    "original_query": "Original search query",
    "product_service_context": "Your product/service",
    "total_leads_processed": 50,
    "successful_analyses": 45,
    "results": [
        {
            "url": "https://example.com",
            "status": "analyzed",
            "sector": "Technology",
            "relevance_score": 0.85,
            "main_services": ["Service 1", "Service 2"],
            "potential_challenges": ["Challenge 1", "Challenge 2"],
            "opportunity_fit": "High potential for..."
        }
    ],
    "agent_metrics": {
        "intake_agent": {...},
        "analysis_agent": {...}
    }
}
```

## 🔮 Future Enhancements

### Google's Agent2Agent (A2A) Protocol Integration

The current implementation uses a monolithic architecture with direct function calls between agents. For future scalability and interoperability, we plan to integrate Google's [Agent2Agent (A2A) Protocol](https://github.com/google-a2a/A2A).

A2A is an open standard that enables AI agents from different frameworks to communicate effectively while maintaining their internal opacity. This would allow:

- **Distributed Architecture**: Each agent runs as an independent service
- **Language Agnostic**: Agents can be implemented in different languages
- **Scalability**: Individual agents can be scaled based on load
- **Interoperability**: Integration with third-party A2A-compliant agents

For detailed information about A2A integration, see our [A2A Integration Guide](docs/A2A_INTEGRATION_GUIDE.md).

### Other Planned Features

- CrewAI integration for enhanced agent orchestration
- Advanced NLP capabilities with LangChain
- Real-time processing with websockets
- Multi-language support
- Advanced analytics dashboard

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is proprietary software owned by Nellia. All rights reserved.

## 🆘 Support

For support, please contact:
- Email: contato@nellia.com.br
- WhatsApp: (11) 98640-9993
- Website: https://prospect.nellia.com.br

---

<div align="center">
  <p>Built with ❤️ by <a href="https://nellia.com.br">Nellia</a></p>
  <p>Transforming B2B prospecting with AI</p>
</div>
