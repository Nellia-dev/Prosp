## Base Agent (`agents/base_agent.py`)

The `BaseAgent` class serves as the foundational abstract base class for all specialized agents within the system. It provides a common structure and shared functionalities, ensuring consistency and reducing boilerplate code across different agents.

Key Responsibilities & Functionalities:

- **Abstract Processing Method**: Defines an abstract `process(self, input_data: TInput) -> TOutput` method, which must be implemented by all inheriting concrete agent classes. This method is where the core logic of each agent resides. `TInput` and `TOutput` are generic type variables bound to Pydantic `BaseModel`, ensuring that inputs and outputs are structured and validated data models.
- **Execution Wrapper**: Provides an `execute(self, input_data: TInput) -> TOutput` method that wraps the `process` call. This wrapper handles:
  - Input and output validation (ensuring they are Pydantic models).
  - Comprehensive error logging and exception handling (including `ValidationError`).
  - Performance metrics tracking (start time, end time, processing duration, success status, error messages) through an `AgentMetrics` model.
- **LLM Client Management**: Initializes and manages an `LLMClientBase` instance (e.g., for interacting with language models like Gemini). The client can be passed during initialization or created from environment variables via `LLMClientFactory`.
- **LLM Interaction Utilities**:
  - `generate_llm_response(self, prompt: str) -> str`: A helper to generate text responses from the LLM, including error handling.
  - `parse_llm_json_response(self, response: str, expected_type: type) -> Any`: A utility to parse JSON from LLM responses, including handling common LLM quirks like markdown code blocks (e.g., ```json ... ```). It can also validate the parsed JSON against an `expected_type` (a Pydantic model).
- **Configuration**: Accepts a `config` dictionary for agent-specific settings.
- **Naming and Description**: Each agent instance has a `name` and `description` for identification and logging purposes.
- **Metrics Tracking**: Stores a list of `AgentMetrics` for each execution and provides a `get_metrics_summary()` method to retrieve aggregated performance data (total executions, success/failure counts, average processing time, total LLM tokens used) and a `reset_metrics()` method.

In essence, `BaseAgent` provides the scaffolding for creating robust, observable, and maintainable agents that can reliably process structured data and interact with LLMs.

## Initial Processing Agents

These agents are typically at the beginning of the lead processing pipeline, responsible for ingesting, validating, and performing initial analysis on raw lead data.

### 1. Lead Intake Agent (`agents/lead_intake_agent.py`)

- **Purpose**: Validates raw lead data (typically from a web scraper or data harvester), cleans it, and prepares it for further processing by other agents.
- **Input**: `SiteData` (from `data_models.lead_structures`). This model usually contains information like URL, raw extracted text content, Google search data, and an extraction status message.
- **Output**: `ValidatedLead` (from `data_models.lead_structures`). This model includes the original `SiteData`, a validation timestamp, a boolean `is_valid` flag, a list of `validation_errors`, cleaned text content, and an `extraction_successful` flag.
- **Key Responsibilities**:
  - Validating the structure and essential fields of the input `SiteData` (e.g., presence of URL).
  - Determining the success of the initial data extraction process based on `extraction_status_message` (maps to an `ExtractionStatus` enum: SUCCESS, SUCCESS_VIA_IMAGE, FAILED_TIMEOUT, etc.).
  - Optionally filtering out leads with failed extractions based on the `skip_failed_extractions` initialization parameter.
  - Cleaning the extracted text content: removing excessive whitespace, newlines, common extraction artifacts (e.g., 'TEXTO DO DOM (PARCIAL):'), and HTML entities. It also truncates very long texts.
  - Preparing the lead data into a `ValidatedLead` object, which serves as input for subsequent analysis agents.
- **Workflow**: It's one of the first agents in the pipeline, taking raw scraped data and transforming it into a more structured and reliable format.

### 2. Lead Analysis Agent (`agents/lead_analysis_agent.py`)

- **Purpose**: Analyzes validated lead data to extract key business insights about the company, such as its sector, services, activities, potential challenges, and overall relevance, primarily using an LLM.
- **Input**: `ValidatedLead` (output from `LeadIntakeAgent`). It also takes `product_service_context` (a string describing the user's product/service) during initialization to tailor the analysis.
- **Output**: `AnalyzedLead` (from `data_models.lead_structures`). This model contains the original `ValidatedLead`, the `product_service_context`, and a `LeadAnalysis` object which holds the extracted insights.
- **Key Responsibilities (within `LeadAnalysis` object)**:
  - **Company Sector & Services**: Identifying the company's main industry and offerings.
  - **Recent Activities**: Extracting news, events, or projects mentioned.
  - **Potential Challenges**: Inferring potential pain points or difficulties the company might face.
  - **Company Size & Culture**: Estimating company size and gathering insights into its culture if available.
  - **Relevance Score**: Assigning a score (0 to 1) indicating the lead's relevance to the user's `product_service_context`.
  - **General Diagnosis**: Providing a summary of the company's current situation.
  - **Opportunity Fit**: Assessing how the user's `product_service_context` could help the company.
- **Workflow**: Typically follows the `LeadIntakeAgent`. If extraction was unsuccessful in the `ValidatedLead`, it generates a limited analysis (often based on Google search data if available). Otherwise, it constructs a detailed prompt for an LLM using the cleaned text and other data to generate a full analysis. It can parse JSON responses from the LLM or fall back to text parsing for the analysis content.

## Main Orchestrator Agent

### Enhanced Lead Processor (`agents/enhanced_lead_processor.py`)

- **Purpose**: Acts as a comprehensive lead intelligence and processing engine. It takes an already analyzed lead and orchestrates a series of specialized sub-agents to generate a rich, multi-faceted prospect package. This package includes deepened analysis, strategic plans, and customized communication drafts.
- **Input**: `AnalyzedLead` (output from `LeadAnalysisAgent`). It also takes `product_service_context`, `competitors_list` (string of known competitors), `tavily_api_key`, and LLM `temperature` during initialization.
- **Output**: `ComprehensiveProspectPackage` (from `data_models.lead_structures`). This is a complex data model containing the original `AnalyzedLead` along with numerous new data structures generated by the sub-agents, such as `EnhancedStrategy`, `EnhancedPersonalizedMessage`, `InternalBriefing`, confidence scores, and ROI potential.
- **Key Responsibilities & Orchestration**:
  - Initializes and manages instances of various specialized agents.
  - Sequentially calls these sub-agents, passing necessary data (often derived from the initial `AnalyzedLead` or outputs of previous sub-agents).
  - Consolidates the outputs from all sub-agents into the final `ComprehensiveProspectPackage`.
  - Calculates overall confidence and ROI potential scores based on the generated data.
- **Sub-Agents Utilized**: The `EnhancedLeadProcessor` coordinates the following agents (among others it might initialize internally for specific tasks):
  - **`TavilyEnrichmentAgent`**: Gathers external intelligence and news about the company using the Tavily web search API to enrich the lead's profile.
  - **`ContactExtractionAgent`**: Extracts contact information (emails, social media profiles) from the lead's data and suggests further search queries if needed.
  - **`PainPointDeepeningAgent`**: Further analyzes and details the lead's potential pain points, assessing their business impact and alignment with the offered product/service, and generates investigative questions.
  - **`LeadQualificationAgent`**: Qualifies the lead by assigning a tier (e.g., High, Medium, Low Potential) and provides a justification based on the analysis, persona, and pain points.
  - **`CompetitorIdentificationAgent`**: Identifies potential competitors of the lead company based on its website text and known competitor lists.
  - **`StrategicQuestionGenerationAgent`**: Generates additional strategic, open-ended questions to facilitate deeper conversations with the lead.
  - **`BuyingTriggerIdentificationAgent`**: Identifies events or signals (e.g., new hires, funding, expansion) that might indicate the lead is actively looking for solutions.
  - **`ToTStrategyGenerationAgent`**: (Tree of Thoughts - Part 1) Generates multiple distinct strategic approach options for the lead.
  - **`ToTStrategyEvaluationAgent`**: (Tree of Thoughts - Part 2) Evaluates the generated strategic options, assessing their strengths, weaknesses, and fit for the lead.
  - **`ToTActionPlanSynthesisAgent`**: (Tree of Thoughts - Part 3) Synthesizes the evaluated strategies into a single, refined action plan.
  - **`DetailedApproachPlanAgent`**: Develops a detailed, step-by-step approach plan based on the synthesized ToT action plan and other lead insights.
  - **`ObjectionHandlingAgent`**: Anticipates potential objections the lead might have and prepares response strategies and suggestions.
  - **`ValuePropositionCustomizationAgent`**: Crafts customized value propositions tailored to the lead's specific pain points, triggers, and persona.
  - **`B2BPersonalizedMessageAgent`**: Generates personalized outreach messages (e.g., email, Instagram DM) based on the developed strategy, value propositions, and contact details.
  - **`InternalBriefingSummaryAgent`**: Creates a comprehensive internal briefing document summarizing all gathered intelligence and plans for the sales team.
- **Workflow**: This agent sits centrally in the advanced lead processing pipeline, taking a broadly analyzed lead and transforming it into a highly detailed and actionable prospect package ready for sales engagement.

## Other Specialized Agents

This section covers other specialized agents that perform specific tasks within the broader lead generation and processing workflow. Some of these might be used in alternative pipelines or for more focused tasks outside the main `EnhancedLeadProcessor` orchestration, or they might represent different versions or approaches to a specific problem (e.g., persona creation).

### 1. Approach Strategy Agent (`agents/approach_strategy_agent.py`)

- **Purpose**: Develops strategic approach plans for leads that already have a persona defined. It aims to create a personalized and effective plan to engage a decision-maker, considering the Brazilian market context.
- **Input**: `LeadWithPersona` (from `data_models.lead_structures`), which contains analyzed lead data and a defined persona. It also takes `product_service_context` (string) during initialization.
- **Output**: `LeadWithStrategy` (from `data_models.lead_structures`), which includes the original `LeadWithPersona` data plus the newly created `ApproachStrategy` object.
- **Key Responsibilities (within `ApproachStrategy` object)**:
  - Defining primary and secondary communication channels (Email, LinkedIn, WhatsApp, Phone).
  - Recommending a tone of voice.
  - Listing key value propositions and talking points.
  - Preparing for potential objections with consultative responses.
  - Suggesting opening questions.
  - Stating the first interaction goal and a follow-up strategy.
- **Workflow**: This agent uses an LLM to generate the strategy. The prompt is built using lead analysis, persona details, the user's product/service context, and specific Brazilian business context (which can vary by sector like Technology, Services, Industry). It expects a JSON response from the LLM.
- **Note**: While `EnhancedLeadProcessor` has its own detailed approach planning capabilities (via `DetailedApproachPlanAgent` using ToT outputs), this agent might be used in workflows where a persona is generated first, and then a strategy is directly derived from that, perhaps for a simpler or alternative pipeline.

### 2. B2B Persona Creation Agent (`agents/b2b_persona_creation_agent.py`)

- **Purpose**: Creates a detailed B2B persona profile for a key decision-maker based on lead analysis, the product/service offered, and the lead's URL.
- **Input**: `B2BPersonaCreationInput` (Pydantic model), which includes `lead_analysis` (string), `product_service_offered` (string), and `lead_url` (string).
- **Output**: `B2BPersonaCreationOutput` (Pydantic model), containing `persona_profile` (a descriptive text string of the persona) and an optional `error_message`.
- **Key Responsibilities**: Generates a narrative persona profile using an LLM. The profile is expected to include a fictional Brazilian name, probable job title, key responsibilities, daily challenges, professional goals, motivations, how the persona seeks solutions and makes B2B purchase decisions, preferred communication style, and how the user's product/service can help. The output is a single string, not a structured JSON object from the LLM for the profile itself.
- **Note**: This agent differs from `PersonaCreationAgent` primarily in its input/output types (string-based analysis input, string profile output vs. model-based inputs/outputs) and the explicitness of `lead_url` in its input model. It might be used when a less structured persona output is sufficient or when integrating with systems expecting a text-based persona.

### 3. Message Crafting Agent (`agents/message_crafting_agent.py`)

- **Purpose**: Creates personalized outreach messages for B2B leads based on a previously defined strategy and persona.
- **Input**: `LeadWithStrategy` (from `data_models.lead_structures`), which contains the analyzed lead, persona, and a full approach strategy.
- **Output**: `FinalProspectPackage` (from `data_models.lead_structures`). This package includes the input `LeadWithStrategy`, the generated `PersonalizedMessage`, a processing timestamp, a unique lead ID, and a calculated confidence score for the package.
- **Key Responsibilities (for `PersonalizedMessage` object)**:
  - Crafting a message body tailored to the primary channel defined in the strategy.
  - Generating a subject line (if applicable, e.g., for email).
  - Defining a clear call to action.
  - Listing personalization elements used.
  - Estimating read time.
- **Workflow**: This agent constructs a detailed prompt for an LLM, incorporating company context, persona details, the specific approach strategy (channel, tone, value propositions, talking points, opening questions from the `ApproachStrategy` input), and the product/service being offered. It includes channel-specific guidance (Email, LinkedIn, WhatsApp) in its prompt to the LLM. It expects a JSON response from the LLM. It also handles fallback message creation if parsing fails.
- **Note**: While `EnhancedLeadProcessor` uses `B2BPersonalizedMessageAgent`, this `MessageCraftingAgent` seems to work with a different input structure (`LeadWithStrategy`) and might be part of an alternative or older workflow where strategy is encapsulated differently.

### 4. Persona Creation Agent (`agents/persona_creation_agent.py`)

- **Purpose**: Creates detailed decision-maker personas for analyzed B2B leads, tailored to the Brazilian market context, and outputs a structured persona model.
- **Input**: `AnalyzedLead` (from `data_models.lead_structures`), which contains comprehensive company analysis.
- **Output**: `LeadWithPersona` (from `data_models.lead_structures`), which bundles the original `AnalyzedLead` with the newly created `PersonaDetails` model.
- **Key Responsibilities (within `PersonaDetails` model)**:
  - Generating a fictional Brazilian name and likely role.
  - Detailing key responsibilities, professional goals, main challenges, and motivations.
  - Describing how the persona seeks solutions, their communication style, and decision-making process.
- **Workflow**: This agent uses an LLM to generate the persona. The prompt is built using various data points from the `AnalyzedLead` input (sector, services, challenges, size, culture, diagnosis) and general Brazilian market context considerations. It expects a JSON response from the LLM to populate the `PersonaDetails` Pydantic model.
- **Note**: This agent appears to be a core component for generating structured persona data. It contrasts with `B2BPersonaCreationAgent` which outputs a text string for the persona profile.

### 5. Lead Analysis Generation Agent (`agents/lead_analysis_generation_agent.py`)

- **Purpose**: Generates a concise textual analysis of a lead, incorporating both provided lead data (as a JSON string) and enriched information (e.g., from web searches), contextualized by the user's product/service offering.
- **Input**: `LeadAnalysisGenerationInput` (Pydantic model), which includes `lead_data_str` (JSON string of lead information), `enriched_data` (string), and `product_service_offered` (string).
- **Output**: `LeadAnalysisGenerationOutput` (Pydantic model), containing `analysis_report` (a single string with the textual analysis) and an optional `error_message`.
- **Key Responsibilities**: Uses an LLM to synthesize the input data into a readable report. The report aims to:
  - Identify the company's sector and main product/service.
  - Estimate company size and potential organizational structure.
  - Pinpoint key challenges and needs, especially those relevant to the user's product/service.
  - Briefly describe company culture and values if discernible.
  - Provide an overall diagnosis and assessment of conversion potential.
- **Workflow**: This agent seems designed to produce a human-readable summary analysis rather than a structured data model for direct machine processing in subsequent steps (unlike `LeadAnalysisAgent` which produces an `AnalyzedLead` model). It could be used for quick reviews, direct reporting, or as an input to agents that consume general text.

## Overall Agent Pipeline Flow

The agents generally form a pipeline, where the output of one agent becomes the input for the next. The most comprehensive pipeline revolves around the `EnhancedLeadProcessor` for in-depth lead development.

### Main Pipeline Example:

1.  **Raw Data (e.g., from Web Scraping/Harvester)**
    - Input: Unstructured or semi-structured company information.

2.  **`LeadIntakeAgent`**
    - Input: Raw `SiteData`.
    - Action: Validates, cleans, normalizes data.
    - Output: `ValidatedLead`.

3.  **`LeadAnalysisAgent`**
    - Input: `ValidatedLead`, `product_service_context` (user's offering).
    - Action: Performs initial LLM-based analysis of the company.
    - Output: `AnalyzedLead` (contains `LeadAnalysis` model with insights).

4.  **`EnhancedLeadProcessor`** (Orchestrator)
    - Input: `AnalyzedLead`, `product_service_context`, `competitors_list`, API keys.
    - Action: Coordinates a series of sub-agents to build a complete prospect package. The typical internal flow involves:

      - **Data Enrichment & Initial Understanding:**
        - `TavilyEnrichmentAgent`: Fetches external data.
        - `ContactExtractionAgent`: Finds contact details.
        - `PainPointDeepeningAgent`: Elaborates on potential pains.
        - `CompetitorIdentificationAgent`: Identifies lead's competitors.
        - `BuyingTriggerIdentificationAgent`: Looks for buying signals.

      - **Qualification & Strategic Foundation:**
        - `LeadQualificationAgent`: Assesses lead quality.
        - `ValuePropositionCustomizationAgent`: Creates tailored value props.
        - `StrategicQuestionGenerationAgent`: Develops insightful questions.

      - **Tree of Thoughts (ToT) for Strategy Development:**
        - `ToTStrategyGenerationAgent`: Proposes multiple approach strategies.
        - `ToTStrategyEvaluationAgent`: Evaluates these strategies.
        - `ToTActionPlanSynthesisAgent`: Synthesizes the best strategy into a coherent plan.

      - **Finalizing Engagement Assets:**
        - `DetailedApproachPlanAgent`: Creates a step-by-step engagement plan from the ToT output.
        - `ObjectionHandlingAgent`: Prepares for potential objections.
        - `B2BPersonalizedMessageAgent`: Drafts outreach messages.
        - `InternalBriefingSummaryAgent`: Compiles all information into an internal summary.

    - Output: `ComprehensiveProspectPackage` (containing all generated data and plans).

### Alternative/Modular Flows:

- Some agents like `PersonaCreationAgent` (outputting `PersonaDetails`) and `ApproachStrategyAgent` (inputting `LeadWithPersona`) can form part of a simpler, direct pipeline:
  `AnalyzedLead` -> `PersonaCreationAgent` -> `LeadWithPersona` -> `ApproachStrategyAgent` -> `LeadWithStrategy` -> `MessageCraftingAgent` -> `FinalProspectPackage`.
- Agents like `B2BPersonaCreationAgent` (outputting a string persona) or `LeadAnalysisGenerationAgent` (outputting a text report) can be used for tasks requiring less structured outputs or for specific integrations.

The system is designed to be modular, allowing for different combinations of agents depending on the desired depth of analysis and the specific workflow requirements.
