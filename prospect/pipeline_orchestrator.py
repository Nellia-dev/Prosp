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

try:
    from playwright.async_api import (Error as PlaywrightError,
                                      TimeoutError as PlaywrightTimeoutError,
                                      async_playwright)
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np
    import google.generativeai as genai
    CORE_LIBRARIES_AVAILABLE = True
except ImportError as e:
    CORE_LIBRARIES_AVAILABLE = False
    logger.critical(f"Bibliotecas essenciais não encontradas: {e}. O pipeline não pode ser executado.")

# Importações de Módulos do Projeto
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
    from prospect.ai_prospect_intelligence import AdvancedProspectProfiler
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

    def __init__(self, business_context: Dict[str, Any], user_id: str, job_id: str):
        self.business_context = business_context
        self.user_id = user_id
        self.job_id = job_id
        self.product_service_context = business_context.get("product_service_description", "")
        
        if not CORE_LIBRARIES_AVAILABLE:
            raise ImportError("Dependências críticas (Playwright, Sentence-Transformers, etc.) não estão instaladas.")

        # Carregamento de modelos para RAG
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.prospect_profiler = AdvancedProspectProfiler()
        logger.info("Modelos de IA para RAG e Profiling carregados.")

        self.job_vector_stores: Dict[str, Dict[str, Any]] = {}

        # Inicialização de agentes de enriquecimento
        if PROJECT_MODULES_AVAILABLE:
            self.llm_client = LLMClientFactory.create_from_env()
            self.lead_intake_agent = LeadIntakeAgent(llm_client=self.llm_client)
            self.lead_analysis_agent = LeadAnalysisAgent(llm_client=self.llm_client, product_service_context=self.product_service_context)
            self.enhanced_lead_processor = EnhancedLeadProcessor(llm_client=self.llm_client, product_service_context=self.product_service_context)
        else: # Usa placeholders se os módulos não estiverem disponíveis
            self.lead_intake_agent = BaseAgent()
            self.lead_analysis_agent = BaseAgent()
            self.enhanced_lead_processor = BaseAgent()
            
        logger.info(f"PipelineOrchestrator inicializado para o job {self.job_id}")

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

    async def _generate_embeddings(self, text_chunks: List[str]) -> Optional[np.ndarray]:
        # ... (código do _generate_embeddings, sem alterações)
        try:
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

    # --- Lógica do Harvester Integrada ---

    async def _extract_google_result_data(self, link_locator) -> Optional[Dict]:
        # Lógica de extração de um único resultado do Google (adaptada para async)
        try:
            if not await link_locator.is_visible(timeout=500): return None
            href = await link_locator.get_attribute("href")
            if not href or not href.startswith("http"): return None
            
            h3 = link_locator.locator('h3').first
            title = await h3.inner_text(timeout=100) if await h3.count() > 0 else ""
            if not title: return None

            parent = link_locator.locator("xpath=./ancestor::div[contains(@class,'MjjYud')][1]").first
            snippet = await parent.locator("div.VwiC3b").first.inner_text(timeout=100) if await parent.count() > 0 else ""
            
            return {"url": href, "title": title, "snippet": snippet}
        except PlaywrightError:
            return None

    async def _search_google(self, query: str, max_leads: int) -> AsyncIterator[Dict]:
        # Versão async da busca no Google
        logger.info(f"Iniciando harvester no Google para a query: '{query}'")
        processed_urls = set()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            
            try:
                await page.goto("https://www.google.com/ncr", timeout=60000)
                
                # Lidar com cookies
                try:
                    await page.locator('button:has-text("Accept all")').first.click(timeout=5000)
                except PlaywrightTimeoutError:
                    logger.warning("Botão de cookie 'Accept all' não encontrado, continuando.")

                await page.locator('textarea[name="q"]').fill(query)
                await page.locator('textarea[name="q"]').press("Enter")

                for page_num in range(5): # Limite de 5 páginas de resultados
                    if len(processed_urls) >= max_leads: break
                    await page.wait_for_selector("div#search", timeout=30000)
                    
                    links = await page.locator("div.MjjYud a[href^='http']").all()
                    
                    for link_locator in links:
                        if len(processed_urls) >= max_leads: break
                        data = await self._extract_google_result_data(link_locator)
                        
                        if data and data["url"] not in processed_urls:
                            domain = urlparse(data["url"]).netloc
                            excluded = ["google.com", "youtube.com", "facebook.com", "linkedin.com", "instagram.com", "wikipedia.org"]
                            if not any(ex in domain for ex in excluded):
                                processed_urls.add(data["url"])
                                logger.info(f"Harvester encontrou um lead potencial: {data['title']}")
                                yield {
                                    "company_name": data["title"],
                                    "website": data["url"],
                                    "description": data["snippet"]
                                }

                    # Paginação
                    try:
                        next_button = page.locator('a#pnnext')
                        if await next_button.count() == 0: break
                        await next_button.click()
                    except PlaywrightError:
                        logger.warning("Não foi possível encontrar o botão 'Próxima'. Fim da busca."); break
            
            except Exception as e:
                logger.error(f"Erro crítico no harvester: {e}");
            finally:
                await browser.close()

    async def _enrich_lead(self, lead_data: Dict, lead_id: str) -> AsyncIterator[Dict]:
        # Lógica de enriquecimento de um único lead
        yield LeadEnrichmentStartEvent(job_id=self.job_id, lead_id=lead_id, company_name=lead_data.get("company_name")).to_dict()
        
        try:
            # 1. Análise inicial e RAG
            site_data = SiteData(url=lead_data["website"], extracted_text_content=lead_data["description"])
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
            
            yield LeadEnrichmentEndEvent(job_id=self.job_id, lead_id=lead_id, success=True, final_package=final_package).to_dict()

        except Exception as e:
            logger.error(f"Falha no enriquecimento para o lead {lead_id}: {e}", exc_info=True)
            yield LeadEnrichmentEndEvent(job_id=self.job_id, lead_id=lead_id, success=False, error_message=str(e)).to_dict()

    # --- Ponto de Entrada Principal ---

    async def execute_streaming_pipeline(self) -> AsyncIterator[Dict[str, Any]]:
        """
        Executa o pipeline completo: harvester -> RAG setup -> enriquecimento por lead.
        """
        start_time = time.time()
        yield PipelineStartEvent(job_id=self.job_id, user_id=self.user_id, initial_query=self.business_context.get("search_query", "N/A")).to_dict()
        
        # 1. Preparar o contexto para o RAG
        search_query = self.business_context.get("search_query", "empresas de tecnologia")
        enriched_context_dict = self._create_enriched_search_context(self.business_context, search_query)
        self.rag_context_text = json.dumps(enriched_context_dict, indent=2)

        # 2. Configurar o ambiente RAG em background
        rag_setup_task = asyncio.create_task(self._setup_rag_for_job(self.job_id, self.rag_context_text))

        # 3. Iniciar o Harvester para coletar leads
        enrichment_tasks = []
        leads_found_count = 0
        max_leads = self.business_context.get("max_leads_to_generate", 10)

        async for lead_data in self._search_google(query=search_query, max_leads=max_leads):
            leads_found_count += 1
            lead_id = str(uuid.uuid4())
            
            yield LeadGeneratedEvent(
                job_id=self.job_id,
                lead_id=lead_id,
                lead_data=lead_data,
                source_url=lead_data.get("website")
            ).to_dict()

            # Aguarda a conclusão do setup do RAG se ainda não terminou
            if not rag_setup_task.done():
                logger.info("Aguardando a finalização da configuração do RAG antes de enriquecer o primeiro lead...")
                await rag_setup_task
            
            # Inicia o enriquecimento para o lead em uma tarefa separada
            task = asyncio.create_task(self._enrich_lead_and_collect_events(lead_data, lead_id))
            enrichment_tasks.append(task)
            
        yield StatusUpdateEvent(job_id=self.job_id, status_message=f"Harvester concluído. {leads_found_count} leads encontrados. Aguardando enriquecimento...").to_dict()
        
        # Coleta os resultados das tarefas de enriquecimento
        for task_future in asyncio.as_completed(enrichment_tasks):
            events = await task_future
            for event in events:
                yield event
                
        total_time = time.time() - start_time
        yield PipelineEndEvent(job_id=self.job_id, total_leads_generated=leads_found_count, execution_time_seconds=total_time, success=True).to_dict()

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
