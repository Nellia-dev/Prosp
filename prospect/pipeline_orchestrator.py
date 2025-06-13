import asyncio
import json
import os
import re
import sys
import time
import traceback
import uuid
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional
from urllib.parse import urlparse

# --- Imports para o Pipeline RAG e Harvester ---

from dotenv import load_dotenv
from loguru import logger
import os  # Ensure os is imported for environment variable manipulation

# Attempt to set a writable cache directory for Hugging Face models
# This should be done before sentence_transformers is imported or used.
# Best place is very early in the script.
# Assuming the script mcp_server.py (and thus pipeline_orchestrator.py when imported by it)
# runs from the project root '/app/'.
# If pipeline_orchestrator.py is at /app/pipeline_orchestrator.py, then its directory is /app.
# If it's at /app/prospect/pipeline_orchestrator.py, then its directory is /app/prospect.
# The traceback suggests it's /app/pipeline_orchestrator.py.
# So, os.path.dirname(file) should be /app.

# Check if __file__ is available (it might not be in interactive sessions or some environments)
if '__file__' in globals():
    app_base_dir = os.path.dirname(os.path.abspath(__file__))
else:
    # Fallback: assume current working directory or a known path if __file__ isn't reliable
    # This might need adjustment based on deployment environment
    app_base_dir = os.getcwd()
    logger.warning("Could not determine script directory using __file__. Assuming current working directory.")


# If the project root is one level up from where pipeline_orchestrator.py is (e.g. if it's in a 'prospect' subdir)
# then app_base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# Given the traceback "/app/pipeline_orchestrator.py", app_base_dir should be /app.
# Let's assume /app is the project root and is writable or a subdir like /app/.cache is.
# If mcp_server.py is at /app/mcp_server.py and imports pipeline_orchestrator.py from /app/pipeline_orchestrator.py
# then __file__ in pipeline_orchestrator.py is /app/pipeline_orchestrator.py
# os.path.dirname(__file__) is /app
# This seems correct for setting a cache within /app
# Define the target cache directory components

cache_parent_dir_name = ".cache"
cache_subdir_name = "huggingface_cache"

# Full path for the main cache directory
target_cache_dir = os.path.join(app_base_dir, cache_parent_dir_name, cache_subdir_name)  # e.g., /app/.cache/huggingface_cache

if not os.getenv("HF_HOME") and not os.getenv("TRANSFORMERS_CACHE") and not os.getenv("SENTENCE_TRANSFORMERS_HOME"):
    cache_setup_successful = False
    try:
        # Ensure the full path exists. os.makedirs creates intermediate directories.
        os.makedirs(target_cache_dir, exist_ok=True)
        logger.info(f"Attempted to ensure cache directory exists: {target_cache_dir}")

        # Check if the directory is writable by attempting to create a temporary file
        test_file_path = os.path.join(target_cache_dir, "test_writable.txt")
        with open(test_file_path, "w") as f:
            f.write("test")
        os.remove(test_file_path)
        # If we reach here, the directory is writable

        os.environ["HF_HOME"] = target_cache_dir
        os.environ["TRANSFORMERS_CACHE"] = target_cache_dir
        os.environ["SENTENCE_TRANSFORMERS_HOME"] = target_cache_dir
        logger.info(f"Successfully created and set Hugging Face cache directory to: {target_cache_dir}")
        cache_setup_successful = True

    except Exception as e:
        logger.warning(
            f"Could not create or set writable cache directory '{target_cache_dir}': {e}. "
            f"This is likely a permission issue for user '{os.getenv('USER', 'unknown')}' in '{app_base_dir}'. "
            "Model downloads might fail if default cache is not writable."
        )

    if not cache_setup_successful:
        logger.warning(
            f"Proceeding without setting custom HF_HOME. Default HuggingFace cache paths will be used, "
            "which might lead to PermissionErrors if not writable by the running user."
        )

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np  # Keep the import here for when it's available
    import google.generativeai as genai

    CORE_LIBRARIES_AVAILABLE = True
except ImportError as e:
    CORE_LIBRARIES_AVAILABLE = False
    logger.critical(f"Bibliotecas essenciais não encontradas: {e}. O pipeline não pode ser executado.")
    np = None  # Define np as None if import fails
    # For type hinting purposes when numpy might not be available,
    # we can use a forward reference string or TypeAlias if Python version supports it well.
    # For broader compatibility, a string literal is often safest for conditional imports.

# Importações de Módulos do Projeto

try:
    from event_models import (
        LeadEnrichmentEndEvent,
        LeadEnrichmentStartEvent,
        LeadGeneratedEvent,
        PipelineEndEvent,
        PipelineErrorEvent,
        PipelineStartEvent,
        StatusUpdateEvent,
    )
    from agents.lead_intake_agent import LeadIntakeAgent
    from agents.lead_analysis_agent import LeadAnalysisAgent
    from agents.enhanced_lead_processor import EnhancedLeadProcessor
    from data_models.lead_structures import GoogleSearchData, SiteData, AnalyzedLead  # Added AnalyzedLead
    from core_logic.llm_client import LLMClientFactory
    from ai_prospect_intelligence import AdvancedProspectProfiler  # Changed from prospect.ai_prospect_intelligence
    # ADK1 Imports - These are used via run_in_executor for sync blocking calls
    from adk1.agent import find_and_extract_structured_leads, search_and_qualify_leads
    # ADK1 Imports for query generation - used via runner.run_async (async)
    from adk1.agent import business_context_to_query_agent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    # Phase 2 Agent Imports
    from agents.lead_analysis_generation_agent import LeadAnalysisGenerationAgent, LeadAnalysisGenerationInput
    from agents.b2b_persona_creation_agent import B2BPersonaCreationAgent, B2BPersonaCreationInput

    PROJECT_MODULES_AVAILABLE = True
    logger.info("✅ Todos os módulos do projeto importados com sucesso, incluindo ADK1")
except ImportError as import_error:
    PROJECT_MODULES_AVAILABLE = False
    logger.error(f"❌ Módulos específicos do projeto não encontrados: {import_error}. O pipeline usará placeholders.")
    traceback.print_exc()

    # Initialize placeholders for missing functions
    def find_and_extract_structured_leads(*args, **kwargs):
        logger.error("find_and_extract_structured_leads called but not available")
        return []

    def search_and_qualify_leads(*args, **kwargs):
        logger.error("search_and_qualify_leads called but not available")
        return []

    # Placeholder for ADK runtime components if project modules fail
    class MockADKRunner:
        async def run_async(self, *args, **kwargs):
            logger.error("MockADKRunner.run_async called but ADK not available")
            class MockResponse:
                text = "Fallback query: Placeholder search"
                output_text = "Fallback query: Placeholder search" # Provide both attributes for robustness
            return MockResponse()

    class MockInMemorySessionService:
        async def create_session(self, *args, **kwargs): pass

    class MockGenAITypes:
        class Content:
            def __init__(self, *args, **kwargs): pass
        class Part:
            def __init__(self, *args, **kwargs): pass

    Runner = MockADKRunner
    InMemorySessionService = MockInMemorySessionService
    types = MockGenAITypes
    # Assume business_context_to_query_agent is also not available, fallback query generation will handle this


# --- Placeholders se os módulos do projeto não estiverem disponíveis ---

if not PROJECT_MODULES_AVAILABLE:
    class BaseEvent:
        def __init__(self, **kwargs):
            self.data = kwargs
        def to_dict(self):
            return self.data

    PipelineStartEvent = (
        PipelineEndEvent
    ) = (
        LeadGeneratedEvent
    ) = (
        StatusUpdateEvent
    ) = (
        PipelineErrorEvent
    ) = (
        LeadEnrichmentStartEvent
    ) = LeadEnrichmentEndEvent = BaseEvent

    class BaseAgent:
        def __init__(self, **kwargs):
            pass
        def execute(self, data):
            return data
        async def execute_enrichment_pipeline(self, **kwargs):
            yield {"event_type": "placeholder_event"}
        async def execute_async(self, data):
             logger.warning(f"Placeholder execute_async called for {self.__class__.__name__}")
             # Return a mock object that simulates success but with placeholder data
             class MockOutput:
                 analysis_report = "Placeholder summary"
                 persona_profile = "Placeholder persona"
                 error_message = None
             return MockOutput()


    LeadIntakeAgent = LeadAnalysisAgent = EnhancedLeadProcessor = BaseAgent
    LeadAnalysisGenerationAgent = B2BPersonaCreationAgent = BaseAgent # Placeholder for Phase 2 agents


    class SiteData(dict):
        pass # Mock SiteData if needed, though inheriting dict might be enough


class PipelineOrchestrator:
    """
    Orquestra o pipeline de ponta a ponta: busca leads (harvester),
    configura o ambiente RAG e enriquece cada lead em tempo real.
    """

    def __init__(self, business_context: Dict[str, Any], user_id: str, job_id: str, use_hybrid: bool = True):
        self.business_context = business_context
        self.user_id = user_id
        self.job_id = job_id
        self.product_service_context = business_context.get("product_service_description", "")
        self.use_hybrid = use_hybrid

        if not CORE_LIBRARIES_AVAILABLE:
            raise ImportError("Dependências críticas ( Sentence-Transformers, etc.) não estão instaladas.")

        # Carregamento de modelos para RAG
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            self.prospect_profiler = AdvancedProspectProfiler()
            logger.info("Modelos de IA para RAG e Profiling carregados.")
        except Exception as e:
             logger.error(f"Falha ao carregar modelos de IA: {e}")
             # Depending on criticality, you might want to raise or set flags
             # For now, proceed with None and handle potential errors later
             self.embedding_model = None
             self.prospect_profiler = None


        self.job_vector_stores: Dict[str, Dict[str, Any]] = {}

        # Inicialização de agentes de enriquecimento
        if PROJECT_MODULES_AVAILABLE:
            logger.info("[PIPELINE_STEP] Initializing agents")
            try:
                self.llm_client = LLMClientFactory.create_from_env()
                self.lead_intake_agent = LeadIntakeAgent(
                    name="LeadIntakeAgent",
                    description="Validates and prepares lead data for processing.",
                    llm_client=self.llm_client
                )
                self.lead_analysis_agent = LeadAnalysisAgent(
                    name="LeadAnalysisAgent",
                    description="Analyzes lead data to extract insights about the company.",
                    llm_client=self.llm_client,
                    product_service_context=self.product_service_context
                )
                self.enhanced_lead_processor = EnhancedLeadProcessor(
                    name="EnhancedLeadProcessor",
                    description="Performs comprehensive lead intelligence and processing.",
                    llm_client=self.llm_client,
                    product_service_context=self.product_service_context
                )

                # Initialize Phase 2 agents for enhanced capabilities
                self.lead_analysis_generation_agent = LeadAnalysisGenerationAgent(
                    name="LeadAnalysisGenerationAgent",
                    description="Generates detailed analysis reports for leads.",
                    llm_client=self.llm_client
                )
                self.b2b_persona_creation_agent = B2BPersonaCreationAgent(
                    name="B2BPersonaCreationAgent",
                    description="Creates B2B persona profiles from lead data.",
                    llm_client=self.llm_client
                )

                # Initialize Hybrid Pipeline Orchestrator if enabled
                self.hybrid_orchestrator = None # Initialize as None
                if self.use_hybrid:
                    try:
                        logger.info("[PIPELINE_STEP] Initializing HybridPipelineOrchestrator")
                        from hybrid_pipeline_orchestrator import HybridPipelineOrchestrator
                        self.hybrid_orchestrator = HybridPipelineOrchestrator(
                            business_context=business_context,
                            user_id=user_id,
                            job_id=job_id
                        )
                        logger.info("Hybrid Pipeline Orchestrator initialized for intelligent agent selection.")
                    except ImportError as e:
                        logger.warning(f"HybridPipelineOrchestrator not found: {e}. Falling back to standard pipeline.")
                        self.use_hybrid = False # Disable hybrid if import fails
                    except Exception as e:
                         logger.error(f"Failed to initialize HybridPipelineOrchestrator: {e}")
                         self.use_hybrid = False

            except Exception as e:
                 logger.error(f"Failed to initialize one or more project agents: {e}")
                 # Revert to base agents if initialization fails even with modules present
                 PROJECT_MODULES_AVAILABLE = False
                 self.lead_intake_agent = BaseAgent(name="PlaceholderLeadIntakeAgent", description="Placeholder for LeadIntakeAgent")
                 self.lead_analysis_agent = BaseAgent(name="PlaceholderLeadAnalysisAgent", description="Placeholder for LeadAnalysisAgent")
                 self.enhanced_lead_processor = BaseAgent(name="PlaceholderEnhancedLeadProcessor", description="Placeholder for EnhancedLeadProcessor")
                 self.lead_analysis_generation_agent = BaseAgent(name="PlaceholderLeadAnalysisGenerationAgent", description="Placeholder for LeadAnalysisGenerationAgent")
                 self.b2b_persona_creation_agent = BaseAgent(name="PlaceholderB2BPersonaCreationAgent", description="Placeholder for B2BPersonaCreationAgent")
                 self.hybrid_orchestrator = None
                 self.use_hybrid = False
                 logger.warning("Using placeholder agents due to initialization failure.")


        else: # Usa placeholders se os módulos não estiverem disponíveis
            self.lead_intake_agent = BaseAgent(name="PlaceholderLeadIntakeAgent", description="Placeholder for LeadIntakeAgent")
            self.lead_analysis_agent = BaseAgent(name="PlaceholderLeadAnalysisAgent", description="Placeholder for LeadAnalysisAgent")
            self.enhanced_lead_processor = BaseAgent(name="PlaceholderEnhancedLeadProcessor", description="Placeholder for EnhancedLeadProcessor")
            self.lead_analysis_generation_agent = BaseAgent(name="PlaceholderLeadAnalysisGenerationAgent", description="Placeholder for LeadAnalysisGenerationAgent")
            self.b2b_persona_creation_agent = BaseAgent(name="PlaceholderB2BPersonaCreationAgent", description="Placeholder for B2BPersonaCreationAgent")
            self.hybrid_orchestrator = None # Ensure hybrid is None if project modules aren't available
            self.use_hybrid = False


        logger.info(f"PipelineOrchestrator inicializado para o job {self.job_id} (Hybrid: {self.use_hybrid})")


    # --- Métodos de Configuração do RAG (do código anterior) ---
    @staticmethod
    def _chunk_text(text: str) -> List[str]:
        """
        Divide um texto em chunks para processamento RAG.
        """
        if not text:
            return []
        # Basic paragraph splitting
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        chunks, current_chunk = [], ""
        # Combine small paragraphs into larger chunks
        for p in paragraphs:
            # Arbitrary chunk size limit (e.g., 1000 characters)
            if len(current_chunk) + len(p) + 2 > 1000 and current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            current_chunk += ("\n\n" if current_chunk else "") + p
        # Add the last chunk
        if current_chunk:
            chunks.append(current_chunk)
        return chunks

    async def _generate_embeddings(self, text_chunks: List[str]) -> Optional['np.ndarray']:  # Use string literal for type hint
        """
        Gera embeddings para uma lista de chunks de texto.
        """
        try:
            if not CORE_LIBRARIES_AVAILABLE or np is None or self.embedding_model is None:  # Guard against runtime use if not available
                logger.error("Numpy (np) or embedding model is not available for embedding generation.")
                return None
            # The embedding model encode method is synchronous but typically fast per chunk.
            # If it were blocking, we'd use run_in_executor here. Sentence Transformers is optimized.
            return self.embedding_model.encode(text_chunks, show_progress_bar=False).astype('float32')
        except Exception as e:
            logger.error(f"Erro na geração de embeddings: {e}")
            traceback.print_exc()
            return None

    async def _setup_rag_for_job(self, job_id: str, context_text: str) -> bool:
        """
        Configura o ambiente RAG (Vector Store) para um job específico
        usando o texto de contexto fornecido.
        """
        if self.job_vector_stores.get(job_id):
            logger.info(f"[{job_id}] Ambiente RAG já configurado.")
            return True # RAG already set up

        logger.info(f"[{job_id}] Configurando ambiente RAG...")
        text_chunks = self._chunk_text(context_text)
        if not text_chunks:
            logger.warning(f"[{job_id}] Nenhum chunk de texto para o RAG.")
            return False

        embeddings = await self._generate_embeddings(text_chunks)
        if embeddings is None:
            logger.error(f"[{job_id}] Falha ao gerar embeddings para o RAG.")
            return False

        try:
            if faiss is None: # Check if faiss was imported successfully
                 logger.error(f"[{job_id}] FAISS library not available.")
                 return False

            embedding_dim = embeddings.shape[1]
            index = faiss.IndexFlatL2(embedding_dim) # L2 distance index
            index.add(embeddings)
            self.job_vector_stores[job_id] = {"index": index, "chunks": text_chunks, "embedding_dim": embedding_dim}
            logger.success(f"[{job_id}] Ambiente RAG e Vector Store (FAISS) estão prontos.")
            return True
        except Exception as e:
            logger.error(f"[{job_id}] Erro na criação do índice FAISS: {e}")
            traceback.print_exc()
            return False

    # --- Lógica do Harvester Integrada com ADK1 ---

    async def _search_with_adk1_agent(self, query: str, max_leads: int) -> AsyncIterator[Dict]:
        """
        Busca leads usando o agente ADK1 mais sofisticado com Tavily API.
        Wrapper assíncrono para as ferramentas síncronas do ADK1.
        """
        logger.info(f"[_search_with_adk1_agent] Iniciando harvester ADK1 para a query: '{query}' com max_leads: {max_leads}")

        try:
            # Verificar se as funções ADK1 estão disponíveis (via PROJECT_MODULES_AVAILABLE check in __init__)
            if not PROJECT_MODULES_AVAILABLE:
                logger.error("[_search_with_adk1_agent] PROJECT_MODULES_AVAILABLE is False, ADK1 functions not available")
                return # Exit the generator

            # Executar em thread separada para não bloquear o event loop
            import concurrent.futures
            # No need to import threading explicitly here, ThreadPoolExecutor handles it

            def run_adk1_search():
                """Synchronous function to run in executor."""
                try:
                    # Pass the query string, not the coroutine object
                    logger.info(f"[run_adk1_search] Executando find_and_extract_structured_leads com query: '{query}', max_leads: {max_leads}")
                    # Usar find_and_extract_structured_leads para obter dados mais ricos
                    # Ensure find_and_extract_structured_leads is the actual function if PROJECT_MODULES_AVAILABLE is True
                    if 'find_and_extract_structured_leads' in globals() and not isinstance(globals()['find_and_extract_structured_leads'], type(BaseAgent)):
                         results = find_and_extract_structured_leads(query, max_leads)
                    else:
                         logger.error("[run_adk1_search] find_and_extract_structured_leads is a placeholder, cannot execute.")
                         return []

                    logger.info(f"[run_adk1_search] ADK1 find_and_extract_structured_leads retornou {len(results)} resultados estruturados")
                    return results
                except Exception as e:
                    logger.error(f"[run_adk1_search] Erro no ADK1 find_and_extract_structured_leads: {e}")
                    traceback.print_exc()
                    # Fallback para search_and_qualify_leads
                    try:
                        logger.info(f"[run_adk1_search] Tentando fallback com search_and_qualify_leads")
                        # Ensure search_and_qualify_leads is the actual function
                        if 'search_and_qualify_leads' in globals() and not isinstance(globals()['search_and_qualify_leads'], type(BaseAgent)):
                             results = search_and_qualify_leads(query, max_leads)
                        else:
                             logger.error("[run_adk1_search] search_and_qualify_leads is a placeholder, cannot execute fallback.")
                             return []

                        logger.info(f"[run_adk1_search] ADK1 fallback retornou {len(results)} resultados")
                        return results
                    except Exception as e2:
                        logger.error(f"[run_adk1_search] Erro no ADK1 fallback: {e2}")
                        traceback.print_exc()
                        return []


            # Get the current event loop
            loop = asyncio.get_event_loop()
            # Use a ThreadPoolExecutor for running blocking I/O code
            with concurrent.futures.ThreadPoolExecutor() as executor:
                logger.info(f"[_search_with_adk1_agent] Calling run_adk1_search with query: '{query}' and max_leads: {max_leads}")
                # Await the execution of the synchronous function in the thread pool
                results = await loop.run_in_executor(executor, run_adk1_search)
                logger.info(f"[_search_with_adk1_agent] run_adk1_search returned {len(results)} results")

            # Verificar se temos resultados
            if not results:
                logger.warning(f"[_search_with_adk1_agent] Nenhum resultado retornado pelo ADK1 para query: '{query}'")
                return # Exit the generator

            # Processar e padronizar os resultados
            yielded_count = 0
            for i, result in enumerate(results):
                logger.info(f"[_search_with_adk1_agent] Processando resultado {i+1}/{len(results)}: {result.get('company_name', result.get('title', 'N/A'))}")

                if result.get('error'):
                    logger.warning(f"[_search_with_adk1_agent] ADK1 retornou erro no resultado {i+1}: {result['error']}")
                    continue

                # Padronizar formato do resultado
                company_name = result.get('company_name') or result.get('title', 'N/A')
                website = result.get('website') or result.get('source_url') or result.get('url', '')
                description = (
                    result.get('description') or
                    result.get('qualification_summary') or
                    result.get('snippet') or
                    result.get('search_snippet', 'N/A')
                )

                # Basic validation for website
                if not website or not urlparse(website).scheme:
                    logger.warning(f"[_search_with_adk1_agent] Skipping result {i+1} due to missing or invalid website: {website}")
                    continue

                # Dados adicionais do ADK1 para enriquecimento
                additional_data = {
                    'industry': result.get('industry'),
                    'company_size': result.get('size'),
                    'contact_emails': result.get('contact_emails', []),
                    'contact_phones': result.get('contact_phones', []),
                    'full_content': result.get('full_content'),
                    'qualification_summary': result.get('qualification_summary')
                }

                lead_data = {
                    "company_name": company_name,
                    "website": website,
                    "description": description,
                    "adk1_enrichment": additional_data  # Dados extras do ADK1
                }

                logger.info(f"[_search_with_adk1_agent] ADK1 Harvester encontrou lead: {company_name}")
                yield lead_data
                yielded_count += 1
                if yielded_count >= max_leads:
                    logger.info(f"[_search_with_adk1_agent] Reached max_leads limit ({max_leads}). Stopping search.")
                    break # Stop iterating if max_leads is reached

            logger.info(f"[_search_with_adk1_agent] Total de leads yielded: {yielded_count}")

        except Exception as e:
            logger.error(f"[_search_with_adk1_agent] Erro crítico no harvester ADK1: {e}")
            traceback.print_exc()
            # Don't re-raise, let the generator finish naturally but report the error

    async def _search_leads(self, query: str, max_leads: int) -> AsyncIterator[Dict]:
        """
        Método principal de busca que tenta ADK1 primeiro, com fallback se necessário.
        """
        logger.info(f"[_search_leads] Iniciando busca de leads com query: '{query}', max_leads: {max_leads}")

        try:
            # Tentar ADK1 primeiro
            adk1_results_count = 0
            logger.info(f"[_search_leads] Chamando _search_with_adk1_agent")

            # Await the async generator
            async for lead_data in self._search_with_adk1_agent(query, max_leads):
                adk1_results_count += 1
                logger.info(f"[_search_leads] Yielding lead #{adk1_results_count}: {lead_data.get('company_name', 'Unknown')}")
                yield lead_data # Yield leads as they are found by the ADK1 agent

            logger.info(f"[_search_leads] _search_with_adk1_agent loop concluído. Total yields: {adk1_results_count}")

            if adk1_results_count > 0:
                logger.success(f"[_search_leads] ADK1 harvester concluído com {adk1_results_count} leads")
            else:
                logger.warning("[_search_leads] ADK1 não retornou resultados ou Project Modules não disponíveis - gerando lead de fallback para teste/garantia")

                # Fallback básico para garantir que pelo menos um lead seja gerado para teste
                # This is a safety net, yielding only one fallback lead if ADK1 yields nothing
                fallback_lead = {
                    "company_name": f"Test Company for Query: {query[:40]}...",
                    "website": "https://example.com", # Use a valid dummy URL
                    "description": f"Fallback lead generated for testing pipeline with query: {query[:100]}...",
                    "adk1_enrichment": {
                        "industry": "Technology",
                        "company_size": "Unknown",
                        "contact_emails": [],
                        "contact_phones": [],
                        "full_content": None,
                        "qualification_summary": "Fallback lead for testing pipeline"
                    }
                }
                logger.info(f"[_search_leads] Yielding fallback lead: {fallback_lead['company_name']}")
                yield fallback_lead
                # adk1_results_count remains 0 or the actual count from ADK1, this fallback doesn't change the count reported for ADK1 results

        except Exception as e:
            logger.error(f"[_search_leads] Erro no harvester principal: {e}")
            traceback.print_exc()
            # Don't re-raise, just log and let the generator finish

    async def _enrich_lead(self, lead_data: Dict, lead_id: str) -> AsyncIterator[Dict]:
        """
        Lógica de enriquecimento de um único lead, emitindo eventos de status.
        """
        company_name = lead_data.get("company_name", "N/A")
        yield LeadEnrichmentStartEvent(
            event_type="lead_enrichment_start",
            timestamp=datetime.now().isoformat(),
            job_id=self.job_id,
            user_id=self.user_id,
            lead_id=lead_id,
            company_name=company_name
        ).to_dict()
        logger.info(f"[{self.job_id}-{lead_id}] Iniciando enriquecimento para {company_name} ({lead_data.get('website', 'N/A')})")

        try:
            # Use hybrid orchestrator if enabled and available
            if self.use_hybrid and self.hybrid_orchestrator:
                logger.info(f"[{self.job_id}-{lead_id}] Using Hybrid Pipeline Orchestrator for intelligent agent selection")

                # Delegate to hybrid orchestrator which handles everything
                # The hybrid orchestrator's _enrich_lead should also be an async generator
                async for event in self.hybrid_orchestrator._enrich_lead(lead_data, lead_id):
                    yield event
                logger.info(f"[{self.job_id}-{lead_id}] Hybrid enrichment completed.")
                return # Enrichment handled by hybrid orchestrator

            # Fallback to standard enrichment pipeline
            logger.info(f"[{self.job_id}-{lead_id}] Using standard enrichment pipeline")

            # 1. Análise inicial e RAG
            site_data = SiteData(
                url=lead_data.get("website", "http://example.com/unknown"),
                extracted_text_content=lead_data.get("description", ""), # Use description from harvester as initial content
                extraction_status_message="Initial data from harvester."
            )

            if not PROJECT_MODULES_AVAILABLE:
                 logger.warning(f"[{self.job_id}-{lead_id}] Using placeholder agents for standard enrichment.")

            # These agent calls are synchronous according to their definition
            validated_lead = self.lead_intake_agent.execute(site_data)
            analyzed_lead = self.lead_analysis_agent.execute(validated_lead) # This should return an AnalyzedLead object or similar structure

            # Ponto de integração do RAG
            rag_store = self.job_vector_stores.get(self.job_id)
            context_dict = self._load_and_parse_enriched_context(self.job_id) # Load persisted context for RAG

            ai_profile = None
            if self.prospect_profiler:
                try:
                    ai_profile = self.prospect_profiler.create_advanced_prospect_profile(
                        lead_data=lead_data,
                        enriched_context=context_dict,
                        rag_vector_store=rag_store
                    )
                    logger.info(f"[{self.job_id}-{lead_id}] Advanced Prospect Profile created.")
                except Exception as e:
                    logger.error(f"[{self.job_id}-{lead_id}] Error creating AI Prospect Profile: {e}")
                    # Proceed without profile if creation fails

            # Attach AI insights if available and analyzed_lead structure supports it
            if ai_profile and hasattr(analyzed_lead, 'ai_intelligence'):
                 analyzed_lead.ai_intelligence = ai_profile
            elif ai_profile:
                 logger.warning(f"[{self.job_id}-{lead_id}] AnalyzedLead structure does not support 'ai_intelligence' attribute. AI profile not attached.")


            # 2. Pipeline de enriquecimento subsequente (Async agent)
            final_package = None
            if self.enhanced_lead_processor:
                try:
                    logger.info(f"[{self.job_id}-{lead_id}] Executing enhanced lead processor pipeline.")
                    # The enhanced_lead_processor's method is an async generator
                    async for event in self.enhanced_lead_processor.execute_enrichment_pipeline(
                        analyzed_lead=analyzed_lead,
                        job_id=self.job_id,
                        user_id=self.user_id
                    ):
                         # Ensure the event includes lead_id for tracking
                        event["lead_id"] = lead_id
                        yield event # Yield events from the enhanced processor

                    # Assuming the last event from the processor contains the final package or info
                    # This part might need adjustment based on how execute_enrichment_pipeline signals completion/result
                    # For now, let's assume the necessary data is collected within the generator
                    # or can be accessed from the modified analyzed_lead object after the loop if needed.
                    # A common pattern is for the generator to yield a final 'completion' event with the result.
                    # If not, you might need to return/yield the final data after the loop if it's not in an event.
                    # Let's check if the AnalyzedLead object was modified by the processor and extract data.
                    # Or, more reliably, look for a specific event type indicating completion.
                    # Assuming the last yielded event contains the final data in its 'data' key.
                    # This is fragile; a specific 'enrichment_completed_data' event would be better.
                    # For now, let's just use the state of analyzed_lead after processing if available.
                    if analyzed_lead and hasattr(analyzed_lead, 'analysis'): # Check if analyzed_lead is valid and has analysis data
                         final_package = analyzed_lead.analysis.model_dump() if hasattr(analyzed_lead.analysis, 'model_dump') else analyzed_lead.analysis # Handle Pydantic model or dict

                except Exception as e:
                    logger.error(f"[{self.job_id}-{lead_id}] Exception during enhanced lead processor execution: {e}")
                    traceback.print_exc()
                    # Allow the process to continue to the end event
                    final_package = None # Indicate failure to get final package

            else:
                 logger.warning(f"[{self.job_id}-{lead_id}] EnhancedLeadProcessor not available.")
                 # If enhanced processor isn't available, use the analysis from the synchronous step
                 if analyzed_lead and hasattr(analyzed_lead, 'analysis'):
                      final_package = analyzed_lead.analysis.model_dump() if hasattr(analyzed_lead.analysis, 'model_dump') else analyzed_lead.analysis

            yield LeadEnrichmentEndEvent(
                event_type="lead_enrichment_end",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                lead_id=lead_id,
                success=True if final_package else False, # Mark success if final package obtained
                final_package=final_package
            ).to_dict()
            logger.info(f"[{self.job_id}-{lead_id}] Enriquecimento finalizado.")

        except Exception as e:
            # Log the error safely, converting e to string explicitly for the message part
            logger.error(f"[{self.job_id}-{lead_id}] Falha crítica no enriquecimento para o lead: {e}", exc_info=True)
            yield LeadEnrichmentEndEvent(
                event_type="lead_enrichment_end",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                lead_id=lead_id,
                success=False,
                error_message=str(e)
            ).to_dict()

    # --- Ponto de Entrada Principal ---

    async def execute_streaming_pipeline(self) -> AsyncIterator[Dict[str, Any]]:
        """
        Executa o pipeline completo: harvester -> RAG setup -> enriquecimento por lead.
        Agora integrado com persistência de contexto e geração inteligente de query.
        """
        logger.info(f"[PIPELINE_START] Starting execute_streaming_pipeline for job {self.job_id}")
        start_time = time.time()

        # --- Generate Intelligent Search Query using RAG ---
        logger.info(f"[PIPELINE_STEP] Generating intelligent search query using RAG analysis")

        # Check if user provided additional search query in business context
        user_search_input = self.business_context.get("user_search_query", "")

        search_query = ""
        try:
            # Use AI Prospect Intelligence (via ADK1 agent) to generate optimized search query
            # AWAIT the asynchronous function call
            search_query = await self._generate_intelligent_search_query(
                business_context=self.business_context,
                user_input=user_search_input
            )
            logger.info(f"[PIPELINE_STEP] AI-generated search query: '{search_query}'")
            if not search_query.strip():
                 logger.warning("[PIPELINE_STEP] AI-generated query is empty. Falling back to basic generation.")
                 raise ValueError("AI generated empty query") # Trigger fallback

        except Exception as e:
            logger.error(f"[PIPELINE_STEP] Failed to generate AI search query: {e}. Falling back to basic generation.")
            traceback.print_exc()
            # Fallback to basic query generation
            search_query = self._generate_basic_search_query(self.business_context, user_search_input)
            logger.info(f"[PIPELINE_STEP] Using fallback search query: '{search_query}'")

        # Ensure search_query is not empty after fallback
        if not search_query.strip():
             search_query = "empresas B2B inovadoras tecnologia" # Final fallback if all else fails
             logger.warning(f"[PIPELINE_STEP] All query generation attempts failed. Using default query: '{search_query}'")


        # --- End Search Query Generation ---

        max_leads = self.business_context.get("max_leads_to_generate", 10)
        logger.info(f"[PIPELINE_STEP] Max leads to generate: {max_leads}")

        logger.info(f"[PIPELINE_STEP] Yielding PipelineStartEvent")
        yield PipelineStartEvent(
            event_type="pipeline_start",
            timestamp=datetime.now().isoformat(),
            job_id=self.job_id,
            user_id=self.user_id,
            initial_query=search_query, # Use the final generated query
            max_leads_to_generate=max_leads
        ).to_dict()

        # 1. Configurar RAG com contexto persistido
        # The context is created before the harvester starts but set up in parallel
        enriched_context_dict = self._create_enriched_search_context(self.business_context, search_query)
        # self.rag_context_text = json.dumps(enriched_context_dict, indent=2) # Store for RAG setup

        logger.info(f"[PIPELINE_STEP] Enriched context created for job {self.job_id}: Query: '{search_query}', Context: {json.dumps(enriched_context_dict, indent=2)[:100]}...")  # Log first 100 chars for brevity

        # Serializar contexto para persistência
        context_filepath = self._serialize_enriched_context(enriched_context_dict, self.job_id)
        if context_filepath:
            logger.info(f"Contexto enriquecido persistido para job {self.job_id}")

            # Verificar se conseguimos recarregar o contexto (teste de integridade)
            logger.info("[PIPELINE_STEP] Calling _load_and_parse_enriched_context for validation")
            loaded_context = self._load_and_parse_enriched_context(self.job_id)
            logger.info("[PIPELINE_STEP] _load_and_parse_enriched_context returned")
            if loaded_context:
                logger.success(f"Contexto carregado e validado com sucesso para job {self.job_id}")
                # Use the loaded context for RAG setup to ensure consistency with persisted data
                self.rag_context_text = json.dumps(loaded_context, indent=2)
            else:
                logger.warning(f"Falha na validação do contexto persistido para job {self.job_id}, using originally created context.")
                self.rag_context_text = json.dumps(enriched_context_dict, indent=2) # Use original in-memory context

        else:
            logger.warning(f"Falha na serialização do contexto para job {self.job_id}. RAG setup might use potentially non-persisted data.")
            self.rag_context_text = json.dumps(enriched_context_dict, indent=2)


        # 2. Configurar o ambiente RAG em background
        # The RAG setup needs the final self.rag_context_text
        rag_setup_task = asyncio.create_task(self._setup_rag_for_job(self.job_id, self.rag_context_text))
        logger.info(f"[PIPELINE_STEP] RAG setup task created for job {self.job_id}")


        # 3. Iniciar o Harvester para coletar leads
        enrichment_tasks = []
        leads_found_count = 0

        logger.info("[PIPELINE_STEP] Calling _search_leads")
        logger.info(f"[PIPELINE_STEP] Search parameters - query: '{search_query}', max_leads: {max_leads}")

        search_loop_entered = False
        try:
            # Await the async generator for searching leads
            async for lead_data in self._search_leads(query=search_query, max_leads=max_leads):
                if not search_loop_entered:
                    logger.info("[PIPELINE_STEP] ✅ Entered _search_leads async for loop successfully!")
                    search_loop_entered = True

                leads_found_count += 1
                lead_id = str(uuid.uuid4())

                logger.info(f"[PIPELINE_STEP] Processing lead #{leads_found_count} (Job {self.job_id}, Lead {lead_id}): {lead_data.get('company_name', 'Unknown')} - {lead_data.get('website', 'No website')}")

                yield LeadGeneratedEvent(
                    event_type="lead_generated",
                    timestamp=datetime.now().isoformat(),
                    job_id=self.job_id,
                    user_id=self.user_id,
                    lead_id=lead_id,
                    lead_data=lead_data,
                    source_url=lead_data.get("website", "N/A"),
                    agent_name="ADK1HarvesterAgent"  # Or a more generic harvester name
                ).to_dict()

                # Aguarda a conclusão do setup do RAG se ainda não terminou
                # This ensures RAG is ready before the first lead is processed, but doesn't block
                # processing subsequent leads if RAG finishes quickly.
                if not rag_setup_task.done():
                    logger.info("Aguardando a finalização da configuração do RAG antes de enriquecer o próximo lead...")
                    await rag_setup_task # Wait for RAG setup to complete

                # Inicia o enriquecimento para o lead em uma tarefa separada
                # Corrected: Pass the lead_id to the enrichment task
                task = asyncio.create_task(self._enrich_lead_and_collect_events(lead_data, lead_id))
                enrichment_tasks.append(task)

            if not search_loop_entered:
                logger.error("[PIPELINE_STEP] ❌ CRITICAL: Never entered the _search_leads async for loop! This means _search_leads yielded nothing.")
            else:
                logger.info(f"[PIPELINE_STEP] ✅ Completed _search_leads loop with {leads_found_count} leads found")

        except Exception as e:
             logger.error(f"[PIPELINE_STEP] CRITICAL ERROR during lead search: {e}")
             traceback.print_exc()
             # Continue to process any leads already yielded before the error,
             # and then report pipeline error.

        yield StatusUpdateEvent(
            event_type="status_update",
            timestamp=datetime.now().isoformat(),
            job_id=self.job_id,
            user_id=self.user_id,
            status_message=f"Harvester concluído. {leads_found_count} leads encontrados. Aguardando enriquecimento..."
        ).to_dict()

        # 4. Coleta os resultados das tarefas de enriquecimento
        # Iterate through the futures as they complete
        enrichment_success_count = 0
        enrichment_fail_count = 0
        if enrichment_tasks:
             logger.info(f"[PIPELINE_STEP] Collecting results from {len(enrichment_tasks)} enrichment tasks...")
             for task_future in asyncio.as_completed(enrichment_tasks):
                try:
                    events = await task_future
                    for event in events:
                        yield event # Yield all events from the enrichment task
                        # Track success/fail based on enrichment_end event
                        if event.get("event_type") == "lead_enrichment_end":
                            if event.get("success"):
                                enrichment_success_count += 1
                            else:
                                enrichment_fail_count += 1
                                logger.warning(f"Enrichment failed for lead {event.get('lead_id', 'N/A')}: {event.get('error_message', 'Unknown error')}")

                except Exception as e:
                    logger.error(f"[PIPELINE_STEP] Error collecting results from enrichment task: {e}")
                    traceback.print_exc()
                    # This error likely means the task crashed before yielding LeadEnrichmentEndEvent
                    enrichment_fail_count += 1 # Count as a failed enrichment

        else:
             logger.warning("[PIPELINE_STEP] No enrichment tasks were created.")


        # 5. Pipeline end
        total_time = time.time() - start_time
        pipeline_success = (leads_found_count > 0 and enrichment_fail_count == 0) # Consider pipeline successful if leads were found and enrichment didn't fail for any
        if not leads_found_count:
             logger.warning("[PIPELINE_END] Pipeline ended with 0 leads found.")
             pipeline_success = False # Cannot be successful if no leads found

        yield PipelineEndEvent(
            event_type="pipeline_end",
            timestamp=datetime.now().isoformat(),
            job_id=self.job_id,
            user_id=self.user_id,
            total_leads_generated=leads_found_count,
            total_leads_enriched=enrichment_success_count, # Report how many were successfully enriched
            total_enrichment_failures=enrichment_fail_count,
            execution_time_seconds=total_time,
            success=pipeline_success
        ).to_dict()
        logger.info(f"[PIPELINE_END] Pipeline execution finished for job {self.job_id}. Total time: {total_time:.2f}s")


    async def _enrich_lead_and_collect_events(self, lead_data, lead_id):
        """
        Helper para coletar todos os eventos de um único enriquecimento
        e retornar a lista.
        """
        events = []
        try:
            # Await the async generator and collect its yielded events
            async for event in self._enrich_lead(lead_data, lead_id):
                events.append(event)
            return events
        except Exception as e:
            logger.error(f"Critical error in _enrich_lead_and_collect_events for lead {lead_id}: {e}")
            # Add a final error event if the _enrich_lead generator itself crashes
            events.append(LeadEnrichmentEndEvent(
                event_type="lead_enrichment_end",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                lead_id=lead_id,
                success=False,
                error_message=f"Critical error during enrichment process: {str(e)}"
            ).to_dict())
            return events # Return collected events plus the error event


    def _create_enriched_search_context(self, business_context: Dict[str, Any], search_query: str) -> Dict[str, Any]:
        """
        Cria um dicionário de contexto estruturado para ser salvo e usado pelo RAG.
        """
        return {
            "search_query": search_query,
            "business_offering": {
                "description": business_context.get('business_description', 'N/A'),
                "product_service": business_context.get('product_service_description', 'N/A'),
                "value_proposition": business_context.get('value_proposition', 'N/A'),
            },
            "prospect_targeting": {
                "ideal_customer_profile": business_context.get('ideal_customer', 'N/A'),
                "industry_focus": business_context.get('industry_focus', []),
            },
            "lead_qualification_criteria": {
                "problems_we_solve": business_context.get('pain_points', []),
                "avoid_competitors": business_context.get('competitors', []),
            }
        }

    def _serialize_enriched_context(self, enriched_context: Dict[str, Any], job_id: str) -> str:
        """
        Serializa o contexto enriquecido em um arquivo JSON.
        Retorna o caminho do arquivo criado.
        """
        try:
            # Garantir que o diretório de saída existe
            # Use os.path.join for cross-platform path creation
            output_dir = os.path.join(app_base_dir, "harvester_output") # Use app_base_dir for output
            os.makedirs(output_dir, exist_ok=True)

            filepath = os.path.join(output_dir, f"enriched_context_{job_id}.json")

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(enriched_context, f, indent=2, ensure_ascii=False)

            logger.success(f"Contexto enriquecido serializado com sucesso em: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Erro ao serializar contexto enriquecido para job {job_id}: {e}")
            traceback.print_exc()
            return ""

    def _load_and_parse_enriched_context(self, job_id: str) -> Dict[str, Any]:
        """
        Carrega e converte o arquivo JSON de contexto enriquecido de volta
        para um dicionário Python.
        """
        try:
            output_dir = os.path.join(app_base_dir, "harvester_output") # Use app_base_dir for output
            filepath = os.path.join(output_dir, f"enriched_context_{job_id}.json")

            if not os.path.exists(filepath):
                logger.warning(f"Arquivo de contexto não encontrado: {filepath}")
                return {}

            with open(filepath, 'r', encoding='utf-8') as f:
                enriched_context = json.load(f)

            logger.success(f"Contexto enriquecido carregado e parseado com sucesso para job {job_id}")
            return enriched_context

        except Exception as e:
            logger.error(f"Erro ao carregar contexto enriquecido para job {job_id}: {e}")
            traceback.print_exc()
            return {}

    async def _generate_intelligent_search_query(
        self,
        business_context: Dict[str, Any],
        user_input: str = ""
    ) -> str:
        """
        Uses AI Prospect Intelligence (via ADK1 agent) to generate an optimized search query
        based on business context and optional user input.
        Corrected to properly await the ADK runner's async method.
        """
        logger.info("[QUERY_GEN] Generating intelligent search query using AI")

        # Check if ADK1 modules are available
        if not PROJECT_MODULES_AVAILABLE or 'business_context_to_query_agent' not in globals():
            logger.warning("[QUERY_GEN] ADK1 query generation agent not available. Falling back to basic generation.")
            # Raise an exception to trigger the fallback in the calling method
            raise ImportError("ADK1 query generation agent not available.")


        try:
            # The necessary ADK1 imports (Runner, InMemorySessionService, types)
            # are handled conditionally at the top of the file.
            # If PROJECT_MODULES_AVAILABLE is False, they are mocked.

            # Prepare enhanced business context for the agent
            enhanced_context = {
                "business_description": business_context.get("business_description", ""),
                "product_service_description": business_context.get("product_service_description", ""),
                "value_proposition": business_context.get("value_proposition", ""),
                "ideal_customer": business_context.get("ideal_customer", ""),
                "industry_focus": business_context.get("industry_focus", []),
                "pain_points": business_context.get("pain_points", []),
                "target_market": business_context.get("target_market", ""),
                "location": business_context.get("location", ""),
                "user_additional_query": user_input
            }

            # Convert to JSON string for the agent
            context_json = json.dumps(enhanced_context, ensure_ascii=False, indent=2)

            logger.info(f"[QUERY_GEN] Sending context to business_context_to_query_agent: {context_json[:200]}...")

            # Execute the agent to generate search query
            # Initialize in-memory session service for ADK1
            # Use the potentially mocked version if modules are not available
            temp_service = InMemorySessionService()

            # ADK sessions might need to be awaited
            await temp_service.create_session(
                app_name="query_generation",
                user_id=self.user_id,
                session_id=self.job_id
            )

            # Use the potentially mocked version if modules are not available
            runner = Runner(
                session_service=temp_service,
                agent='business_context_to_query_agent', # Agent name as defined in ADK1
                app_name="query_generation",
            )

            # Use the potentially mocked version if modules are not available
            query_content = types.Content(role="user", parts=[types.Part(text=context_json)])

            logger.info("[QUERY_GEN] Calling ADK1 runner.run_async...")
            # AWAIT the asynchronous function call from the runner
            response = await runner.run_async(
                user_id=self.user_id,
                session_id=self.job_id,
                new_message=query_content
            )
            logger.info("[QUERY_GEN] ADK1 runner.run_async completed.")


            # Assuming the response object has an 'output_text' attribute
            # or similar, based on typical ADK patterns.
            # If the agent's instruction is to return only the query,
            # this should be the direct query string.
            agent_result = None
            if hasattr(response, 'output_text') and response.output_text:
                agent_result = response.output_text
            elif hasattr(response, 'text') and response.text: # Fallback if output_text is not present or empty
                agent_result = response.text
            elif isinstance(response, str) and response.strip(): # If the response itself is the string
                 agent_result = response
            else:
                 logger.warning("[QUERY_GEN] ADK1 runner.run_async returned an unexpected empty or non-string response.")
                 # Trigger fallback by raising an error
                 raise ValueError("ADK1 agent returned empty response")


            logger.debug(f"[QUERY_GEN] Agent raw result: {agent_result}");
            print(f"[QUERY_GEN] Agent raw result type: {type(agent_result)}")  # Debugging line

            # Extract and clean the generated query
            search_query = str(agent_result).strip()

            # ADK agent might return JSON or other formats depending on its structure
            # Add logic here if the agent output needs further parsing (e.g., JSON parsing)
            # For now, assuming it returns a plain string query.

            if not search_query:
                 logger.warning("[QUERY_GEN] Extracted search query is empty after stripping.")
                 raise ValueError("Extracted search query is empty") # Trigger fallback


            logger.success(f"[QUERY_GEN] AI-generated search query: '{search_query}'")
            return search_query

        except Exception as e:
            logger.error(f"[QUERY_GEN] Failed during AI search query generation process: {e}")
            traceback.print_exc()
            # Re-raise the exception so the calling code can handle it (e.g., use fallback)
            # This also covers the ImportError from the initial check
            raise

    def _generate_basic_search_query(
        self,
        business_context: Dict[str, Any],
        user_input: str = ""
    ) -> str:
        """
        Fallback method to generate a basic search query when AI generation fails.
        """
        logger.info("[QUERY_GEN] Generating basic search query (fallback)")

        # Extract key components from business context
        industry_terms = business_context.get("industry_focus", [])
        ideal_customer = business_context.get("ideal_customer", "")
        location = business_context.get("location", "")
        pain_points = business_context.get("pain_points", [])
        product_service = business_context.get("product_service_description", "")

        # Build query components
        query_parts = []

        # Add industry terms
        if industry_terms and isinstance(industry_terms, list):
            query_parts.extend([term.strip() for term in industry_terms if term.strip()][:2])  # Take first 2, ensure clean

        # Add keywords from product/service
        if product_service:
             product_keywords = [word.strip() for word in product_service.lower().split()
                                 if len(word) > 3 and word not in ['para', 'de', 'da', 'do', 'e', 'com', 'que', 'um', 'uma']]
             query_parts.extend(product_keywords[:3])


        # Add customer profile keywords
        if ideal_customer:
            # Extract key words from ideal customer description
            customer_keywords = [word.strip() for word in ideal_customer.lower().split()
                               if len(word) > 3 and word not in ['o', 'a', 'os', 'as', 'um', 'uma', 'uns', 'umas', 'para', 'de', 'da', 'do', 'e', 'com', 'que', 'em']]
            query_parts.extend(customer_keywords[:3])  # Take first 3 relevant words

        # Add location if specified
        if location:
            location_parts = location.split(',')
            if location_parts:
                query_parts.append(location_parts[0].strip())  # Add primary location

        # Add pain point keywords
        if pain_points and isinstance(pain_points, list):
            for pain in pain_points[:1]:  # Take first pain point
                pain_keywords = [word.strip() for word in str(pain).lower().split()
                               if len(word) > 4 and word not in ['o', 'a', 'os', 'as', 'um', 'uma', 'uns', 'umas', 'para', 'de', 'da', 'do', 'e', 'com', 'que', 'em']]
                query_parts.extend(pain_keywords[:2])  # Take first 2 relevant words


        # Add user input
        if user_input.strip():
            query_parts.append(user_input.strip())

        # Combine, remove duplicates, and clean up
        search_query_list = list(dict.fromkeys([part for part in query_parts if part])) # Remove duplicates while preserving order
        search_query = " ".join(search_query_list[:10])  # Limit to 10 terms to avoid overly long queries


        # If nothing meaningful was extracted, use a default
        if not search_query.strip():
            search_query = "empresas B2B inovadoras tecnologia"
            logger.warning(f"[QUERY_GEN] Basic query generation resulted in empty string, using default: '{search_query}'")


        logger.info(f"[QUERY_GEN] Generated basic search query: '{search_query}'")
        return search_query


    async def generate_executive_summary(self, analyzed_lead: AnalyzedLead, external_intelligence_data: str = "") -> Optional[str]:
        """
        Generates an executive summary report for an analyzed lead. (Phase 2 Integration)
        """
        # Check if agent is available and not a placeholder
        if not PROJECT_MODULES_AVAILABLE or not isinstance(self.lead_analysis_generation_agent, LeadAnalysisGenerationAgent):
            logger.warning("LeadAnalysisGenerationAgent not available or is a placeholder. Skipping executive summary.")
            return None

        logger.info(f"[{self.job_id}] Generating executive summary for: {analyzed_lead.validated_lead.site_data.url}")
        try:
            # Ensure analyzed_lead.analysis is a dict or has model_dump
            analysis_data_for_agent = analyzed_lead.analysis.model_dump() if hasattr(analyzed_lead.analysis, 'model_dump') else dict(analyzed_lead.analysis)

            input_data = LeadAnalysisGenerationInput(
                lead_data_str=json.dumps(analysis_data_for_agent, ensure_ascii=False),
                enriched_data=external_intelligence_data,
                product_service_offered=self.product_service_context
            )
            # Await the asynchronous agent execution
            summary_output = await self.lead_analysis_generation_agent.execute_async(input_data)

            if summary_output and not summary_output.error_message:
                logger.success(f"[{self.job_id}] Executive summary generated successfully.")
                return summary_output.analysis_report
            else:
                error_msg = summary_output.error_message if summary_output else 'Agent returned None'
                logger.error(f"[{self.job_id}] Failed to generate executive summary: {error_msg}")
                return None
        except Exception as e:
            logger.error(f"[{self.job_id}] Exception during executive summary generation: {e}")
            traceback.print_exc()
            return None

    async def generate_narrative_persona(self, analyzed_lead: AnalyzedLead, external_intelligence_data: str = "") -> Optional[str]:
        """
        Generates a narrative B2B persona profile. (Phase 2 Integration)
        """
        # Check if agent is available and not a placeholder
        if not PROJECT_MODULES_AVAILABLE or not isinstance(self.b2b_persona_creation_agent, B2BPersonaCreationAgent):
            logger.warning("B2BPersonaCreationAgent not available or is a placeholder. Skipping narrative persona generation.")
            return None

        logger.info(f"[{self.job_id}] Generating narrative persona for: {analyzed_lead.validated_lead.site_data.url}")
        try:
            # Construct lead_analysis string for the agent
            # Ensure analyzed_lead.analysis is accessible and contains expected attributes
            analysis = analyzed_lead.analysis if hasattr(analyzed_lead, 'analysis') else {}
            validated_lead_data = analyzed_lead.validated_lead if hasattr(analyzed_lead, 'validated_lead') else None
            site_data = validated_lead_data.site_data if validated_lead_data and hasattr(validated_lead_data, 'site_data') else SiteData(url="N/A") # Use SiteData or a placeholder

            lead_analysis_summary = (
                f"Company URL: {site_data.url}\n"
                f"Company Name: {lead_data.get('company_name', 'N/A')}\n" # Use original lead_data name if available
                f"Sector: {getattr(analysis, 'company_sector', analysis.get('company_sector', 'N/A'))}\n" # Handle object or dict
                f"Services: {', '.join(getattr(analysis, 'main_services', analysis.get('main_services', ['N/A'])))}\n"
                f"Challenges: {', '.join(getattr(analysis, 'potential_challenges', analysis.get('potential_challenges', ['N/A'])))}\n"
                f"Diagnosis: {getattr(analysis, 'general_diagnosis', analysis.get('general_diagnosis', 'N/A'))}\n"
                f"Enriched Data: {external_intelligence_data[:500]}..." # Truncate for brevity
            )

            input_data = B2BPersonaCreationInput(
                lead_analysis=lead_analysis_summary,
                product_service_offered=self.product_service_context,
                lead_url=str(site_data.url) # Ensure it's a string
            )
            # Await the asynchronous agent execution
            persona_output = await self.b2b_persona_creation_agent.execute_async(input_data)

            if persona_output and not persona_output.error_message:
                logger.success(f"[{self.job_id}] Narrative persona generated successfully.")
                return persona_output.persona_profile
            else:
                error_msg = persona_output.error_message if persona_output else 'Agent returned None'
                logger.error(f"[{self.job_id}] Failed to generate narrative persona: {error_msg}")
                return None
        except Exception as e:
            logger.error(f"[{self.job_id}] Exception during narrative persona generation: {e}")
            traceback.print_exc()
            return None
