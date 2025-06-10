# prospect/pipeline_orchestrator.py

import asyncio
import json
import os
import time
import traceback
import uuid
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

from loguru import logger

# --- Imports para o Pipeline RAG ---
# Verifica a disponibilidade das bibliotecas RAG e define uma flag.
# Isso torna o script robusto mesmo que as dependências não estejam instaladas.
try:
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer
    RAG_LIBRARIES_AVAILABLE = True
except ImportError:
    RAG_LIBRARIES_AVAILABLE = False
    # Define classes placeholder para que o type hinting não quebre
    SentenceTransformer = type('SentenceTransformer', (object,), {})
    np = type('np', (object,), {})
    faiss = type('faiss', (object,), {})

# --- Imports de Módulos do Projeto ---
# Tenta importar módulos específicos do projeto. Se falharem, o script ainda funciona,
# mas com funcionalidades limitadas.
try:
    from event_models import (LeadEnrichmentEndEvent, LeadEnrichmentStartEvent,
                              LeadGeneratedEvent, PipelineEndEvent,
                              PipelineErrorEvent, PipelineStartEvent,
                              StatusUpdateEvent)
    from agents.lead_intake_agent import LeadIntakeAgent
    from agents.lead_analysis_agent import LeadAnalysisAgent
    from agents.enhanced_lead_processor import EnhancedLeadProcessor
    from data_models.lead_structures import GoogleSearchData, SiteData
    from core_logic.llm_client import LLMClientFactory
    from adk1.agent import lead_search_and_qualify_agent as harvester_search_agent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    PROJECT_MODULES_AVAILABLE = True
except ImportError:
    PROJECT_MODULES_AVAILABLE = False
    harvester_search_agent = None  # Define para evitar NameError
    logger.warning("Módulos específicos do projeto (agents, event_models, etc.) não encontrados. Algumas funcionalidades, como a execução de streaming, serão limitadas.")


class PipelineOrchestrator:
    """
    Orquestra o pipeline de geração e enriquecimento de leads, incluindo a
    configuração e utilização de um pipeline RAG para inteligência avançada.
    """

    def __init__(self, business_context: Dict[str, Any], user_id: str, job_id: str):
        """
        Inicializa o orquestrador e carrega o modelo de embedding para o RAG.
        """
        self.business_context = business_context
        self.user_id = user_id
        self.job_id = job_id
        self.product_service_context = business_context.get("product_service_description", "")
        self.competitors_list = ", ".join(business_context.get("competitors", []))

        self.embedding_model: Optional[SentenceTransformer] = None
        if RAG_LIBRARIES_AVAILABLE:
            try:
                # O modelo será baixado e cacheado automaticamente na primeira execução.
                # Esta operação pode exigir acesso à internet.
                logger.info("Carregando modelo de embedding 'all-MiniLM-L6-v2'...")
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.success("Modelo de embedding SentenceTransformer carregado com sucesso.")
            except Exception as e:
                logger.error(f"Falha ao carregar o modelo SentenceTransformer: {e}. Funcionalidades RAG serão desativadas.")
        else:
            logger.warning("Bibliotecas RAG (faiss-cpu, sentence-transformers, numpy) não encontradas. Funcionalidades RAG estão desativadas.")

        self.job_vector_stores: Dict[str, Dict[str, Any]] = {}
        
        # Inicializa outros componentes do pipeline se os módulos estiverem disponíveis
        self.ai_intelligence_enabled = False
        if PROJECT_MODULES_AVAILABLE:
            try:
                from prospect.ai_prospect_intelligence import AdvancedProspectProfiler
                self.prospect_profiler = AdvancedProspectProfiler()
                self.ai_intelligence_enabled = True
                logger.info(f"[{self.job_id}] Módulo de Inteligência Artificial (AI) habilitado.")
            except ImportError:
                 logger.warning(f"[{self.job_id}] Módulo 'ai_prospect_intelligence' não encontrado. Insights avançados desativados.")

        logger.info(f"PipelineOrchestrator inicializado para o job {self.job_id}")

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 1000) -> List[str]:
        """
        Divide o texto em pedaços (chunks) de forma simples.
        Para produção, considere usar uma biblioteca mais sofisticada como a
        RecursiveCharacterTextSplitter do LangChain para respeitar a estrutura do texto.
        """
        if not text:
            return []
        # Divide o texto por parágrafos (duas quebras de linha)
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        chunks = []
        current_chunk = ""
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) + 2 > chunk_size and current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            current_chunk += ("\n\n" if current_chunk else "") + paragraph
        
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks

    async def _generate_embeddings(self, text_chunks: List[str]) -> Optional[np.ndarray]:
        """
        Gera embeddings vetoriais para os chunks de texto usando o modelo carregado.
        """
        if not self.embedding_model:
            logger.warning("Modelo de embedding não inicializado. Não é possível gerar embeddings.")
            return None

        try:
            logger.info(f"Gerando embeddings para {len(text_chunks)} chunks de texto...")
            # Para grande volume, considere usar asyncio.to_thread para não bloquear o event loop.
            embeddings_np = self.embedding_model.encode(
                text_chunks,
                show_progress_bar=False  # Altere para True para depuração visual
            )
            logger.info("Embeddings gerados com sucesso.")
            return embeddings_np.astype('float32')
        except Exception as e:
            logger.error(f"Ocorreu um erro durante a geração de embeddings: {e}")
            logger.debug(traceback.format_exc())
            return None

    async def _setup_rag_for_job(self, job_id: str, context_filepath: str) -> bool:
        """
        Configura o pipeline RAG completo para um job específico.
        1. Lê o arquivo de contexto.
        2. Divide o conteúdo em chunks.
        3. Gera os embeddings para cada chunk.
        4. Cria e popula um índice vetorial FAISS.
        """
        if not RAG_LIBRARIES_AVAILABLE:
            logger.error("Não é possível configurar o RAG, pois as bibliotecas necessárias não estão instaladas.")
            return False
            
        if self.job_vector_stores.get(job_id):
            logger.info(f"[{job_id}] O Vector Store para este job já existe. Pulando a configuração.")
            return True

        logger.info(f"[{job_id}] Configurando RAG: Lendo contexto de '{context_filepath}'")
        try:
            with open(context_filepath, "r", encoding="utf-8") as f:
                document_content = f.read()
        except FileNotFoundError:
            logger.error(f"[{job_id}] Falha na configuração do RAG: Arquivo de contexto não encontrado em '{context_filepath}'.")
            return False
        except Exception as e:
            logger.error(f"[{job_id}] Falha na configuração do RAG: Erro ao ler o arquivo de contexto: {e}")
            return False

        if not document_content.strip():
            logger.warning(f"[{job_id}] O arquivo de contexto está vazio. Nenhum dado para o RAG.")
            return False

        text_chunks = self._chunk_text(document_content)
        if not text_chunks:
            logger.warning(f"[{job_id}] Nenhum chunk de texto foi gerado a partir do conteúdo do arquivo.")
            return False
        logger.info(f"[{job_id}] Documento dividido em {len(text_chunks)} chunks.")

        chunk_embeddings_np = await self._generate_embeddings(text_chunks)
        if chunk_embeddings_np is None or chunk_embeddings_np.size == 0:
            logger.error(f"[{job_id}] Falha ao gerar embeddings. Abortando configuração do RAG.")
            return False

        embedding_dim = chunk_embeddings_np.shape[1]

        try:
            logger.info(f"[{job_id}] Inicializando índice FAISS (IndexFlatL2) com dimensão {embedding_dim}.")
            index = faiss.IndexFlatL2(embedding_dim)
            
            logger.info(f"[{job_id}] Adicionando {chunk_embeddings_np.shape[0]} embeddings ao índice FAISS.")
            index.add(chunk_embeddings_np)
            
            self.job_vector_stores[job_id] = {
                "index": index,
                "chunks": text_chunks,
                "embedding_dim": embedding_dim
            }
            logger.success(f"[{job_id}] Configuração RAG concluída. O índice FAISS está pronto para uso.")
            return True
        except Exception as e:
            logger.error(f"[{job_id}] Erro crítico durante a criação do índice FAISS: {e}", exc_info=True)
            return False

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
                "competitive_advantage": business_context.get('competitive_advantage', 'N/A')
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
        
    async def execute_streaming_pipeline(self) -> AsyncIterator[Dict[str, Any]]:
        """
        Ponto de entrada para executar o pipeline de prospecção em tempo real (exemplo).
        """
        start_time = time.time()
        if PROJECT_MODULES_AVAILABLE:
            yield PipelineStartEvent(job_id=self.job_id, user_id=self.user_id).to_dict()

        context_filename = f"./enriched_context_{self.job_id}.json"
        enriched_context = self._create_enriched_search_context(self.business_context, "real-time prospecting query")
        
        try:
            with open(context_filename, "w", encoding="utf-8") as f:
                json.dump(enriched_context, f, indent=2, ensure_ascii=False)
            await self._setup_rag_for_job(self.job_id, context_filename)
        except Exception as e:
            logger.error(f"Falha na pré-configuração do RAG para pipeline de streaming: {e}")
            if PROJECT_MODULES_AVAILABLE:
                yield PipelineErrorEvent(job_id=self.job_id, error_message=f"RAG pre-setup failed: {e}").to_dict()

        if not harvester_search_agent:
            logger.error("Agente Harvester não disponível. O pipeline de streaming não pode continuar.")
            if PROJECT_MODULES_AVAILABLE:
                yield PipelineErrorEvent(job_id=self.job_id, error_message="Harvester agent not found.").to_dict()
        else:
            # A lógica de streaming que chama o harvester iria aqui.
            logger.info("Lógica de streaming do Harvester seria executada aqui.")
            pass # Placeholder para a execução do harvester

        total_time = time.time() - start_time
        logger.info(f"Pipeline de streaming (exemplo) concluído em {total_time:.2f}s.")
        if PROJECT_MODULES_AVAILABLE:
            yield PipelineEndEvent(job_id=self.job_id, execution_time_seconds=total_time, success=True).to_dict()
