# prospect/pipeline_orchestrator.py

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
import os # Ensure os is imported for environment variable manipulation

# Attempt to set a writable cache directory for Hugging Face models
# This should be done before sentence_transformers is imported or used.
# Best place is very early in the script.

# Assuming the script mcp_server.py (and thus pipeline_orchestrator.py when imported by it)
# runs from the project root '/app/'.
# If pipeline_orchestrator.py is at /app/pipeline_orchestrator.py, then its directory is /app.
# If it's at /app/prospect/pipeline_orchestrator.py, then its directory is /app/prospect.
# The traceback suggests it's /app/pipeline_orchestrator.py.
# So, os.path.dirname(__file__) should be /app.

app_base_dir = os.path.dirname(os.path.abspath(__file__))
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
target_cache_dir = os.path.join(app_base_dir, cache_parent_dir_name, cache_subdir_name) # e.g., /app/.cache/huggingface_cache

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
        logger.warning(f"Could not create or set writable cache directory '{target_cache_dir}': {e}. This is likely a permission issue for user 'appuser' in '{app_base_dir}'. Model downloads might fail if default cache is not writable.")
    
    if not cache_setup_successful:
        logger.warning(f"Proceeding without setting custom HF_HOME. Default HuggingFace cache paths will be used, which might lead to PermissionErrors if not writable by 'appuser'.")

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np # Keep the import here for when it's available
    import google.generativeai as genai
    CORE_LIBRARIES_AVAILABLE = True
except ImportError as e:
    CORE_LIBRARIES_AVAILABLE = False
    logger.critical(f"Bibliotecas essenciais não encontradas: {e}. O pipeline não pode ser executado.")
    np = None # Define np as None if import fails
    # For type hinting purposes when numpy might not be available,
    # we can use a forward reference string or TypeAlias if Python version supports it well.
    # For broader compatibility, a string literal is often safest for conditional imports.

# Importações de Módulos do Projeto
try:
    from event_models import (LeadEnrichmentEndEvent, LeadEnrichmentStartEvent,
                              LeadGeneratedEvent, PipelineEndEvent,
                              PipelineErrorEvent, PipelineStartEvent,
                              StatusUpdateEvent)
    from agents.lead_intake_agent import LeadIntakeAgent
    from agents.lead_analysis_agent import LeadAnalysisAgent
    from agents.enhanced_lead_processor import EnhancedLeadProcessor
    from data_models.lead_structures import GoogleSearchData, SiteData, AnalyzedLead # Added AnalyzedLead
    from core_logic.llm_client import LLMClientFactory
    from ai_prospect_intelligence import AdvancedProspectProfiler # Changed from prospect.ai_prospect_intelligence
    from adk1.agent import find_and_extract_structured_leads, search_and_qualify_leads
    from agents.lead_analysis_generation_agent import LeadAnalysisGenerationAgent, LeadAnalysisGenerationInput # Phase 2
    from agents.b2b_persona_creation_agent import B2BPersonaCreationAgent, B2BPersonaCreationInput # Phase 2
    PROJECT_MODULES_AVAILABLE = True
except ImportError:
    PROJECT_MODULES_AVAILABLE = False
    logger.warning("Módulos específicos do projeto não encontrados. O pipeline usará placeholders.")


# --- Placeholders se os módulos do projeto não estiverem disponíveis ---
if not PROJECT_MODULES_AVAILABLE:
    class BaseEvent:
        def __init__(self, **kwargs): self.data = kwargs
        def to_dict(self): return self.data
    PipelineStartEvent = PipelineEndEvent = LeadGeneratedEvent = StatusUpdateEvent = PipelineErrorEvent = LeadEnrichmentStartEvent = LeadEnrichmentEndEvent = BaseEvent
    class BaseAgent:
        def __init__(self, **kwargs): pass
        def execute(self, data): return data
        async def execute_enrichment_pipeline(self, **kwargs): yield {"event_type": "placeholder_event"}
    LeadIntakeAgent = LeadAnalysisAgent = EnhancedLeadProcessor = BaseAgent
    class SiteData(dict): pass


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
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.prospect_profiler = AdvancedProspectProfiler()
        logger.info("Modelos de IA para RAG e Profiling carregados.")

        self.job_vector_stores: Dict[str, Dict[str, Any]] = {}

        # Inicialização de agentes de enriquecimento
        if PROJECT_MODULES_AVAILABLE:
            logger.info("[PIPELINE_STEP] Initializing agents")
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
            if self.use_hybrid:
                logger.info("[PIPELINE_STEP] Initializing HybridPipelineOrchestrator")
                from hybrid_pipeline_orchestrator import HybridPipelineOrchestrator
                self.hybrid_orchestrator = HybridPipelineOrchestrator(
                    business_context=business_context,
                    user_id=user_id,
                    job_id=job_id
                )
                logger.info("Hybrid Pipeline Orchestrator initialized for intelligent agent selection.")
            
        else: # Usa placeholders se os módulos não estiverem disponíveis
            self.lead_intake_agent = BaseAgent(name="PlaceholderLeadIntakeAgent", description="Placeholder for LeadIntakeAgent")
            self.lead_analysis_agent = BaseAgent(name="PlaceholderLeadAnalysisAgent", description="Placeholder for LeadAnalysisAgent")
            self.enhanced_lead_processor = BaseAgent(name="PlaceholderEnhancedLeadProcessor", description="Placeholder for EnhancedLeadProcessor")
            self.lead_analysis_generation_agent = None
            self.b2b_persona_creation_agent = None
            
        logger.info(f"PipelineOrchestrator inicializado para o job {self.job_id} (Hybrid: {self.use_hybrid})")


    # --- Métodos de Configuração do RAG (do código anterior) ---
    @staticmethod
    def _chunk_text(text: str) -> List[str]:
        # ... (código do _chunk_text, sem alterações)
        if not text: return []
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        chunks, current_chunk = [], ""
        for p in paragraphs:
            if len(current_chunk) + len(p) + 2 > 1000 and current_chunk:
                chunks.append(current_chunk); current_chunk = ""
            current_chunk += ("\n\n" if current_chunk else "") + p
        if current_chunk: chunks.append(current_chunk)
        return chunks

    async def _generate_embeddings(self, text_chunks: List[str]) -> Optional['np.ndarray']: # Use string literal for type hint
        # ... (código do _generate_embeddings, sem alterações)
        try:
            if not CORE_LIBRARIES_AVAILABLE or np is None: # Guard against runtime use if not available
                logger.error("Numpy (np) is not available for embedding generation.")
                return None
            return self.embedding_model.encode(text_chunks, show_progress_bar=False).astype('float32')
        except Exception as e:
            logger.error(f"Erro na geração de embeddings: {e}"); return None

    async def _setup_rag_for_job(self, job_id: str, context_text: str) -> bool:
        # ... (código do _setup_rag_for_job, adaptado para receber texto em vez de filepath)
        if self.job_vector_stores.get(job_id): return True
        logger.info(f"[{job_id}] Configurando ambiente RAG...")
        text_chunks = self._chunk_text(context_text)
        if not text_chunks:
            logger.warning("[{job_id}] Nenhum chunk de texto para o RAG."); return False
        
        embeddings = await self._generate_embeddings(text_chunks)
        if embeddings is None:
            logger.error("[{job_id}] Falha ao gerar embeddings para o RAG."); return False
        
        try:
            index = faiss.IndexFlatL2(embeddings.shape[1])
            index.add(embeddings)
            self.job_vector_stores[job_id] = {"index": index, "chunks": text_chunks, "embedding_dim": embeddings.shape[1]}
            logger.success(f"[{job_id}] Ambiente RAG e Vector Store (FAISS) estão prontos.")
            return True
        except Exception as e:
            logger.error(f"[{job_id}] Erro na criação do índice FAISS: {e}"); return False

    # --- Lógica do Harvester Integrada com ADK1 ---

    async def _search_with_adk1_agent(self, query: str, max_leads: int) -> AsyncIterator[Dict]:
        """
        Busca leads usando o agente ADK1 mais sofisticado com Tavily API.
        Wrapper assíncrono para as ferramentas síncronas do ADK1.
        """
        logger.info(f"Iniciando harvester ADK1 para a query: '{query}'")
        
        try:
            # Executar em thread separada para não bloquear o event loop
            import concurrent.futures
            import threading
            
            def run_adk1_search():
                try:
                    # Usar find_and_extract_structured_leads para obter dados mais ricos
                    results = find_and_extract_structured_leads(query, max_leads)
                    logger.info(f"ADK1 retornou {len(results)} resultados estruturados")
                    return results
                except Exception as e:
                    logger.error(f"Erro no ADK1 find_and_extract_structured_leads: {e}")
                    # Fallback para search_and_qualify_leads
                    try:
                        results = search_and_qualify_leads(query, max_leads)
                        logger.info(f"ADK1 fallback retornou {len(results)} resultados")
                        return results
                    except Exception as e2:
                        logger.error(f"Erro no ADK1 fallback: {e2}")
                        return []
            
            # Executar em thread pool para não bloquear o event loop
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                logger.info(f"[_search_with_adk1_agent] Calling run_adk1_search with query: {query} and max_leads: {max_leads}")
                results = await loop.run_in_executor(executor, run_adk1_search)
                logger.info(f"[_search_with_adk1_agent] run_adk1_search returned {len(results)} results")
            
            # Processar e padronizar os resultados
            for result in results:
                if result.get('error'):
                    logger.warning(f"ADK1 retornou erro: {result['error']}")
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
                
                logger.info(f"ADK1 Harvester encontrou lead: {company_name}")
                yield lead_data
                
        except Exception as e:
            logger.error(f"Erro crítico no harvester ADK1: {e}")
            # Se ADK1 falhar completamente, fallback para busca básica seria implementado aqui
            # Por enquanto, retornamos sem resultados
            return

    async def _search_leads(self, query: str, max_leads: int) -> AsyncIterator[Dict]:
        """
        Método principal de busca que tenta ADK1 primeiro, com fallback se necessário.
        """
        try:
            # Tentar ADK1 primeiro
            adk1_results_count = 0
            async for lead_data in self._search_with_adk1_agent(query, max_leads):
                adk1_results_count += 1
                yield lead_data
            
            if adk1_results_count > 0:
                logger.success(f"ADK1 harvester concluído com {adk1_results_count} leads")
            else:
                logger.warning("ADK1 não retornou resultados - implementar fallback se necessário")
                
        except Exception as e:
            logger.error(f"Erro no harvester principal: {e}")

    async def _enrich_lead(self, lead_data: Dict, lead_id: str) -> AsyncIterator[Dict]:
        # Lógica de enriquecimento de um único lead
        yield LeadEnrichmentStartEvent(
            event_type="lead_enrichment_start",
            timestamp=datetime.now().isoformat(),
            job_id=self.job_id,
            user_id=self.user_id,
            lead_id=lead_id,
            company_name=lead_data.get("company_name", "N/A")
        ).to_dict()
        
        try:
            # Use hybrid orchestrator if enabled and available
            if self.use_hybrid and hasattr(self, 'hybrid_orchestrator') and PROJECT_MODULES_AVAILABLE:
                logger.info(f"[{self.job_id}-{lead_id}] Using Hybrid Pipeline Orchestrator for intelligent agent selection")
                
                # Delegate to hybrid orchestrator which handles everything
                async for event in self.hybrid_orchestrator._enrich_lead(lead_data, lead_id):
                    yield event
                return
            
            # Fallback to standard enrichment pipeline
            logger.info(f"[{self.job_id}-{lead_id}] Using standard enrichment pipeline")
            
            # 1. Análise inicial e RAG
            site_data = SiteData(
                url=lead_data.get("website", "http://example.com/unknown"),
                extracted_text_content=lead_data.get("description", ""),
                extraction_status_message="Initial data from ADK1 harvester; full extraction status TBD."
            )
            validated_lead = self.lead_intake_agent.execute(site_data)
            analyzed_lead = self.lead_analysis_agent.execute(validated_lead)

            # Ponto de integração do RAG
            rag_store = self.job_vector_stores.get(self.job_id)
            context_dict = json.loads(self.rag_context_text) if hasattr(self, "rag_context_text") else {}
            
            ai_profile = self.prospect_profiler.create_advanced_prospect_profile(
                lead_data=lead_data,
                enriched_context=context_dict,
                rag_vector_store=rag_store
            )
            analyzed_lead.ai_intelligence = ai_profile # Anexa os insights
            
            # 2. Pipeline de enriquecimento subsequente
            async for event in self.enhanced_lead_processor.execute_enrichment_pipeline(
                analyzed_lead=analyzed_lead,
                job_id=self.job_id,
                user_id=self.user_id
            ):
                event["lead_id"] = lead_id
                yield event
            
            final_package = event.get("data") if 'event' in locals() else None
            
            yield LeadEnrichmentEndEvent(
                event_type="lead_enrichment_end",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                lead_id=lead_id,
                success=True,
                final_package=final_package
            ).to_dict()

        except Exception as e:
            # Log the error safely, converting e to string explicitly for the message part
            logger.error(f"Falha no enriquecimento para o lead {lead_id}: {e}", exc_info=True)
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
        Agora integrado com persistência de contexto.
        """
        logger.info(f"[PIPELINE_START] Starting execute_streaming_pipeline for job {self.job_id}")
        start_time = time.time()

        # --- Load Search Query from Enriched Context ---
        logger.info(f"[PIPELINE_STEP] Loading search query from enriched context")
        
        # Load enriched context
        enriched_context_dict = self._load_and_parse_enriched_context(self.job_id)
        if not enriched_context_dict:
            logger.warning(f"Could not load enriched context for job {self.job_id}, using default query")
            search_query = "empresas de tecnologia B2B inovadoras" # Default query
        else:
            search_query = enriched_context_dict.get("search_query", "empresas de tecnologia B2B inovadoras")
        
        logger.info(f"[PIPELINE_STEP] Loaded search query: {search_query}")
        # --- End Search Query Loading ---
        
        max_leads = self.business_context.get("max_leads_to_generate", 10)
        logger.info(f"[PIPELINE_STEP] Max leads to generate: {max_leads}")

        logger.info(f"[PIPELINE_STEP] Yielding PipelineStartEvent")
        yield PipelineStartEvent(
            event_type="pipeline_start",
            timestamp=datetime.now().isoformat(),
            job_id=self.job_id,
            user_id=self.user_id,
            initial_query=search_query,
            max_leads_to_generate=max_leads
        ).to_dict()
        
        # 1. Executar o Harvester (que já serializa o contexto)
        # search_query and max_leads are already defined above
        
        # 2. Configurar RAG com contexto persistido
        enriched_context_dict = self._create_enriched_search_context(self.business_context, search_query)
        self.rag_context_text = json.dumps(enriched_context_dict, indent=2)
        logger.info(f"[PIPELINE_STEP] Enriched context created for job {self.job_id}: Query: '{search_query}', Context: {self.rag_context_text[:100]}...")  # Log first 100 chars for brevity
        
        # Serializar contexto para persistência
        context_filepath = self._serialize_enriched_context(enriched_context_dict, self.job_id)
        if context_filepath:
            logger.info(f"Contexto enriquecido persistido para job {self.job_id}")
            
            # Verificar se conseguimos recarregar o contexto (teste de integridade)
            logger.info("[PIPELINE_STEP] Calling _load_and_parse_enriched_context")
            loaded_context = self._load_and_parse_enriched_context(self.job_id)
            logger.info("[PIPELINE_STEP] _load_and_parse_enriched_context returned")
            if loaded_context:
                logger.success(f"Contexto carregado e validado com sucesso para job {self.job_id}")
                # Usar o contexto carregado para garantir consistência
                enriched_context_dict = loaded_context
                self.rag_context_text = json.dumps(enriched_context_dict, indent=2)
            else:
                logger.warning(f"Falha na validação do contexto persistido para job {self.job_id}, usando contexto em memória")

        # 3. Configurar o ambiente RAG em background
        rag_setup_task = asyncio.create_task(self._setup_rag_for_job(self.job_id, self.rag_context_text))

        # 4. Iniciar o Harvester para coletar leads
        enrichment_tasks = []
        leads_found_count = 0

        logger.info("[PIPELINE_STEP] Calling _search_leads")
        async for lead_data in self._search_leads(query=search_query, max_leads=max_leads):
            leads_found_count += 1
            lead_id = str(uuid.uuid4())
            
            yield LeadGeneratedEvent(
                event_type="lead_generated",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                lead_id=lead_id,
                lead_data=lead_data,
                source_url=lead_data.get("website", "N/A"),
                agent_name="ADK1HarvesterAgent" # Or a more generic harvester name
            ).to_dict()

            # Aguarda a conclusão do setup do RAG se ainda não terminou
            if not rag_setup_task.done():
                logger.info("Aguardando a finalização da configuração do RAG antes de enriquecer o primeiro lead...")
                await rag_setup_task
            
            # Inicia o enriquecimento para o lead em uma tarefa separada
            task = asyncio.create_task(self._enrich_lead_and_collect_events(lead_data, lead_id))
            enrichment_tasks.append(task)
            
        yield StatusUpdateEvent(
            event_type="status_update",
            timestamp=datetime.now().isoformat(),
            job_id=self.job_id,
            user_id=self.user_id,
            status_message=f"Harvester concluído. {leads_found_count} leads encontrados. Aguardando enriquecimento..."
        ).to_dict()
        
        # 5. Coleta os resultados das tarefas de enriquecimento
        for task_future in asyncio.as_completed(enrichment_tasks):
            events = await task_future
            for event in events:
                yield event
                
        total_time = time.time() - start_time
        yield PipelineEndEvent(
            event_type="pipeline_end",
            timestamp=datetime.now().isoformat(),
            job_id=self.job_id,
            user_id=self.user_id,
            total_leads_generated=leads_found_count,
            execution_time_seconds=total_time,
            success=True
        ).to_dict()

    async def _enrich_lead_and_collect_events(self, lead_data, lead_id):
        # Helper para coletar todos os eventos de um único enriquecimento
        events = []
        async for event in self._enrich_lead(lead_data, lead_id):
            events.append(event)
        return events
        
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
            output_dir = "harvester_output"
            os.makedirs(output_dir, exist_ok=True)

            filepath = os.path.join(output_dir, f"enriched_context_{job_id}.json")

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(enriched_context, f, indent=2, ensure_ascii=False)

            logger.success(f"Contexto enriquecido serializado com sucesso em: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Erro ao serializar contexto enriquecido para job {job_id}: {e}")
            return ""

    def _load_and_parse_enriched_context(self, job_id: str) -> Dict[str, Any]:
        """
        Carrega e converte o arquivo JSON de contexto enriquecido de volta
        para um dicionário Python.
        """
        try:
            filepath = os.path.join("harvester_output", f"enriched_context_{job_id}.json")

            if not os.path.exists(filepath):
                logger.warning(f"Arquivo de contexto não encontrado: {filepath}")
                return {}

            with open(filepath, 'r', encoding='utf-8') as f:
                enriched_context = json.load(f)

            logger.success(f"Contexto enriquecido carregado e parseado com sucesso para job {job_id}")
            return enriched_context

        except Exception as e:
            logger.error(f"Erro ao carregar contexto enriquecido para job {job_id}: {e}")
            return {}

    # def _run_harvester(self, search_query: str, max_leads: int = 10) -> AsyncIterator[Dict]:
    #     """
    #     Executa o harvester, serializa o contexto enriquecido e
    #     retorna os leads encontrados.
    #     """
    #     # 1. Criar e serializar o contexto enriquecido
    #     enriched_context = self._create_enriched_search_context(self.business_context, search_query)
    #     context_filepath = self._serialize_enriched_context(enriched_context, self.job_id)

    #     if context_filepath:
    #         logger.info(f"Contexto enriquecido persistido em: {context_filepath}")
    #     else:
    #         logger.warning("Falha na serialização do contexto, mas continuando com o harvester")

    #     # 2. Executar o harvester Google (delegação para o método existente)
    #     return self._search_leads(search_query, max_leads) # Corrected to use _search_leads

    async def generate_executive_summary(self, analyzed_lead: AnalyzedLead, external_intelligence_data: str = "") -> Optional[str]:
        """
        Generates an executive summary report for an analyzed lead. (Phase 2 Integration)
        """
        if not self.lead_analysis_generation_agent:
            logger.warning("LeadAnalysisGenerationAgent not available. Skipping executive summary.")
            return None

        logger.info(f"[{self.job_id}] Generating executive summary for: {analyzed_lead.validated_lead.site_data.url}")
        try:
            input_data = LeadAnalysisGenerationInput(
                lead_data_str=json.dumps(analyzed_lead.analysis.model_dump(), ensure_ascii=False),
                enriched_data=external_intelligence_data,
                product_service_offered=self.product_service_context
            )
            summary_output = await self.lead_analysis_generation_agent.execute_async(input_data)
            if summary_output and not summary_output.error_message:
                logger.success(f"[{self.job_id}] Executive summary generated successfully.")
                return summary_output.analysis_report
            else:
                logger.error(f"[{self.job_id}] Failed to generate executive summary: {summary_output.error_message if summary_output else 'Agent returned None'}")
                return None
        except Exception as e:
            logger.error(f"[{self.job_id}] Exception during executive summary generation: {e}")
            return None

    async def generate_narrative_persona(self, analyzed_lead: AnalyzedLead, external_intelligence_data: str = "") -> Optional[str]:
        """
        Generates a narrative B2B persona profile. (Phase 2 Integration)
        """
        if not self.b2b_persona_creation_agent:
            logger.warning("B2BPersonaCreationAgent not available. Skipping narrative persona generation.")
            return None

        logger.info(f"[{self.job_id}] Generating narrative persona for: {analyzed_lead.validated_lead.site_data.url}")
        try:
            # Construct lead_analysis string for the agent
            lead_analysis_summary = (
                f"Company: {analyzed_lead.validated_lead.site_data.url}\n"
                f"Sector: {analyzed_lead.analysis.company_sector}\n"
                f"Services: {', '.join(analyzed_lead.analysis.main_services)}\n"
                f"Challenges: {', '.join(analyzed_lead.analysis.potential_challenges)}\n"
                f"Diagnosis: {analyzed_lead.analysis.general_diagnosis}\n"
                f"Enriched Data: {external_intelligence_data[:500]}..." # Truncate for brevity
            )

            input_data = B2BPersonaCreationInput(
                lead_analysis=lead_analysis_summary,
                product_service_offered=self.product_service_context,
                lead_url=str(analyzed_lead.validated_lead.site_data.url)
            )
            persona_output = await self.b2b_persona_creation_agent.execute_async(input_data)

            if persona_output and not persona_output.error_message:
                logger.success(f"[{self.job_id}] Narrative persona generated successfully.")
                return persona_output.persona_profile
            else:
                logger.error(f"[{self.job_id}] Failed to generate narrative persona: {persona_output.error_message if persona_output else 'Agent returned None'}")
                return None
        except Exception as e:
            logger.error(f"[{self.job_id}] Exception during narrative persona generation: {e}")
            return None
