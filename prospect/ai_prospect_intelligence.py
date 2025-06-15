# prospect/ai_prospect_intelligence.py

import json
import math
import os
import re
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger

# --- Imports para o Pipeline RAG ---
# Verifica a disponibilidade das bibliotecas e define uma flag.
try:
    import google.generativeai as genai
    import numpy as np
    from sentence_transformers import SentenceTransformer
    RAG_LIBRARIES_AVAILABLE = True
except ImportError as e:
    RAG_LIBRARIES_AVAILABLE = False
    logger.critical(f"Bibliotecas RAG essenciais não encontradas: {e}. Funcionalidades de IA serão desativadas.")
    # Define classes placeholder para que o type hinting não quebre durante a análise estática
    SentenceTransformer = type('SentenceTransformer', (object,), {})
    genai = type('genai', (object,), {})
    np = type('np', (object,), {})


class AdvancedProspectProfiler:
    """
    Cria um perfil de prospect avançado usando análise de sinais e um pipeline RAG
    para gerar insights preditivos baseados em um contexto de negócios.
    """
    
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AdvancedProspectProfiler, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Inicializa o profiler, carregando o modelo de embedding e o cliente LLM.
        """
        # Prevent re-initialization if already done
        if self._initialized:
            return
            
        self.embedding_model: Optional[SentenceTransformer] = None
        self.llm_client: Optional[genai.GenerativeModel] = None

        if not RAG_LIBRARIES_AVAILABLE:
            logger.warning("Bibliotecas RAG não encontradas. O AdvancedProspectProfiler não funcionará.")
            self._initialized = True
            return

        # 1. Carregar Modelo de Embedding
        try:
            logger.info("Profiler: Carregando modelo de embedding 'all-MiniLM-L6-v2'...")
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.success("Profiler: Modelo de embedding carregado com sucesso.")
        except Exception as e:
            logger.error(f"Profiler: Falha crítica ao carregar o modelo SentenceTransformer: {e}. Insights RAG estarão indisponíveis.")

        # 2. Configurar Cliente LLM (Google Gemini)
        try:
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            if not gemini_api_key:
                logger.warning("Profiler: Variável de ambiente GEMINI_API_KEY não encontrada. Insights do LLM estarão indisponíveis.")
            else:
                genai.configure(api_key=gemini_api_key)
                generation_config = {
                    "temperature": 0.4, # Um pouco mais de criatividade para os insights
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 512,
                }
                self.llm_client = genai.GenerativeModel(
                    'gemini-1.5-flash', # Updated to current available model
                    generation_config=generation_config
                )
                logger.success("Profiler: Cliente LLM Google Gemini inicializado com sucesso.")
        except Exception as e:
            logger.error(f"Profiler: Erro ao inicializar o cliente Gemini: {e}. Insights do LLM estarão indisponíveis.")
        
        self._initialized = True

    def create_advanced_prospect_profile(
        self,
        lead_data: Dict[str, Any],
        enriched_context: Dict[str, Any],
        rag_vector_store: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Cria um perfil de prospect completo, combinando análise de sinais e insights RAG.
        """
        company_name = lead_data.get('company_name', 'N/A')
        
        # Double check: Verificação da disponibilidade do contexto enriquecido
        logger.info(f"Profiler: Iniciando análise para '{company_name}'")
        logger.info(f"Profiler: Contexto enriquecido disponível: {bool(enriched_context)}")
        logger.info(f"Profiler: Vector store disponível: {bool(rag_vector_store)}")
        
        if enriched_context:
            business_desc = enriched_context.get('business_offering', {}).get('description', 'N/A')
            target_profile = enriched_context.get('prospect_targeting', {}).get('ideal_customer_profile', 'N/A')
            logger.info(f"Profiler: Usando contexto - Negócio: '{business_desc[:50]}...', Target: '{target_profile[:50]}...'")
        
        text_content = self._extract_text_from_lead(lead_data)
        intent_score = self._analyze_buying_intent(text_content)
        pain_alignment = self._analyze_pain_alignment(text_content, enriched_context)
        urgency_score = self._calculate_urgency_score(text_content)
        
        # Double check: Log dos scores calculados
        logger.info(f"Profiler: Scores para '{company_name}' - Intent: {intent_score}, Pain Alignment: {pain_alignment}, Urgency: {urgency_score}")
        
        predictive_insights = self._generate_predictive_insights(
            lead_data, enriched_context, rag_vector_store
        )

        overall_score = self._calculate_overall_prospect_score(intent_score, pain_alignment, urgency_score)
        
        # Double check: Log do resultado final
        logger.success(f"Profiler: Perfil criado para '{company_name}' - Score geral: {overall_score}, Insights: {len(predictive_insights)}")

        return {
            'prospect_score': overall_score,
            'buying_intent_score': intent_score,
            'pain_alignment_score': pain_alignment,
            'urgency_score': urgency_score,
            'predictive_insights': predictive_insights,
            'context_usage_summary': {
                'enriched_context_used': bool(enriched_context),
                'rag_vector_store_used': bool(rag_vector_store),
                'context_elements_count': len(enriched_context) if enriched_context else 0
            }
        }

    def _generate_predictive_insights(
        self,
        lead_data: Dict[str, Any],
        enriched_context: Dict[str, Any],
        rag_vector_store: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Executa o pipeline RAG completo para gerar insights preditivos e acionáveis.
        """
        company_name = lead_data.get('company_name', 'N/A')
        fallback_insights = [f"Análise padrão indica que '{company_name}' se alinha com nosso público-alvo geral."]

        # --- Validação dos Componentes RAG ---
        if not self.embedding_model:
            logger.warning(f"RAG Abortado para '{company_name}': Modelo de embedding não está carregado.")
            return fallback_insights
        if not self.llm_client:
            logger.warning(f"RAG Abortado para '{company_name}': Cliente LLM (Gemini) não está configurado.")
            return fallback_insights
        if not rag_vector_store:
            logger.warning(f"RAG Abortado para '{company_name}': Vector Store não foi fornecido.")
            return fallback_insights

        # --- Ciclo RAG ---
        try:
            # 1. Formular a Consulta (Query) a partir dos dados do lead
            lead_snippet = self._extract_text_from_lead(lead_data, max_length=1200)
            query = f"Para a empresa '{company_name}', que é descrita como '{lead_snippet}', quais são as principais dores, desafios e oportunidades de venda que nossa solução pode endereçar?"
            logger.info(f"RAG Query para '{company_name}': '{query[:100]}...'")

            # 2. Gerar Embedding da Consulta
            query_embedding = self.embedding_model.encode([query])[0].astype('float32')

            # 3. Buscar no Vector Store (FAISS)
            faiss_index = rag_vector_store.get("index")
            stored_chunks = rag_vector_store.get("chunks", [])
            retrieved_context = "Nenhum contexto específico foi recuperado."
            
            if faiss_index and stored_chunks:
                k = min(3, len(stored_chunks))
                distances, indices = faiss_index.search(np.expand_dims(query_embedding, axis=0), k)
                
                retrieved_chunks_texts = [stored_chunks[i] for i in indices[0] if i < len(stored_chunks)]
                retrieved_context = "\n\n---\n\n".join(retrieved_chunks_texts)
                logger.info(f"Profiler: {len(retrieved_chunks_texts)} chunks de contexto recuperados para '{company_name}'.")
            
            # 4. Construir o Prompt Aumentado para o LLM
            llm_prompt = self._build_rag_prompt(company_name, lead_snippet, retrieved_context)

            # 5. Chamar o LLM e processar a resposta
            logger.info(f"Profiler: Chamando a API do Gemini para gerar insights para '{company_name}'.")
            response = self.llm_client.generate_content(llm_prompt)
            
            insights = self._parse_llm_response(response.text)
            logger.success(f"Profiler: Insights gerados com sucesso para '{company_name}'.")
            return insights if insights else fallback_insights
            
        except Exception as e:
            logger.error(f"Profiler: Falha no ciclo RAG para '{company_name}': {e}")
            logger.debug(traceback.format_exc())
            return fallback_insights

    def _build_rag_prompt(self, company_name: str, lead_snippet: str, retrieved_context: str) -> str:
        """Constrói o prompt final a ser enviado para o modelo de linguagem."""
        return f"""
Você é um estrategista de vendas B2B de elite. Sua tarefa é analisar um lead e, com base no CONTEXTO ESTRATÉGICO do nosso negócio, gerar 3 insights preditivos e acionáveis.

**LEAD A SER ANALISADO:**
- **Empresa:** {company_name}
- **Descrição/Dados:** "{lead_snippet}"

**CONTEXTO ESTRATÉGICO DO NOSSO NEGÓCIO (Recuperado por IA):**
---
{retrieved_context}
---

**SUA TAREFA:**
Com base em TUDO o que foi fornecido, gere 3 insights curtos e poderosos para a equipe de vendas. Foque no "porquê" eles são um bom prospect e "como" devemos abordá-los.

Formato da resposta: Uma lista com bullets.
- **Oportunidade/Dor:** [Descreva a principal oportunidade ou dor do lead que se conecta ao nosso contexto.]
- **Ângulo de Abordagem:** [Sugira uma tática ou mensagem inicial para capturar o interesse deles.]
- **Diferencial Competitivo:** [Aponte um diferencial nosso que é particularmente relevante para este lead.]
"""

    def _parse_llm_response(self, response_text: str) -> List[str]:
        """Limpa e formata a saída do LLM para uma lista de insights."""
        lines = response_text.split('\n')
        insights = [
            line.strip().lstrip('-* ').replace('**', '') 
            for line in lines if line.strip() and len(line.strip()) > 10
        ]
        return insights

    # --- Métodos auxiliares de análise de sinais ---

    def _extract_text_from_lead(self, lead_data: Dict[str, Any], max_length: int = 2000) -> str:
        """Extrai e combina todo o texto relevante de um lead em uma única string."""
        text_parts = [
            str(lead_data.get('company_name', '')),
            str(lead_data.get('description', '')),
            str(lead_data.get('snippet', ''))
        ]
        full_text = ' '.join(filter(None, text_parts)).lower()
        return full_text[:max_length]

    def _analyze_buying_intent(self, text_content: str) -> float:
        """Estima a intenção de compra com base em palavras-chave."""
        keywords = ['hiring', 'expanding', 'funding', 'seeking', 'looking for', 'need', 'require', 'new solution']
        score = sum(1 for k in keywords if k in text_content)
        return round(min(score / 3.0, 1.0), 3) # Normalizado

    def _analyze_pain_alignment(self, text_content: str, enriched_context: Dict[str, Any]) -> float:
        """Mede o alinhamento entre as dores do lead e as soluções que oferecemos."""
        problems_we_solve = enriched_context.get('lead_qualification_criteria', {}).get('problems_we_solve', [])
        if not problems_we_solve:
            return 0.5 # Retorno neutro se não houver dores definidas
        
        # Simplifica as dores para palavras-chave
        pain_keywords = set()
        for problem in problems_we_solve:
            pain_keywords.update(re.findall(r'\b\w+\b', str(problem).lower()))
        
        if not pain_keywords:
            return 0.5

        alignment_count = sum(1 for p_kw in pain_keywords if p_kw in text_content)
        return round(min(alignment_count / len(pain_keywords), 1.0), 3)

    def _calculate_urgency_score(self, text_content: str) -> float:
        """Estima a urgência com base em palavras-chave indicativas."""
        keywords = ['urgent', 'asap', 'immediately', 'deadline', 'critical', 'priority', 'imminent']
        score = sum(1 for k in keywords if k in text_content)
        return round(min(score / 2.0, 1.0), 3) # Normalizado

    def _calculate_overall_prospect_score(self, intent: float, alignment: float, urgency: float) -> float:
        """Calcula uma pontuação geral ponderada para o prospect."""
        weights = {'intent': 0.4, 'alignment': 0.4, 'urgency': 0.2}
        score = (intent * weights['intent'] + alignment * weights['alignment'] + urgency * weights['urgency'])
        return round(score, 3)


class BuyingSignalPredictor:
    """
    Analisa texto para prever sinais de compra com base em padrões. (Complementar ao RAG)
    """
    def predict_buying_signals(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        text_content = ' '.join(str(v) for v in lead_data.values() if isinstance(v, str)).lower()
        detected_signals = []
        if 'hiring' in text_content or 'job opening' in text_content:
            detected_signals.append({'signal_type': 'Hiring/Growth', 'confidence': 0.8})
        if 'digital transformation' in text_content or 'new platform' in text_content:
            detected_signals.append({'signal_type': 'Technology Shift', 'confidence': 0.7})
        return {'detected_signals': detected_signals}


class ProspectIntentScorer:
    """
    Calcula uma pontuação de intenção de compra. (Complementar ao RAG)
    """
    def calculate_intent_score(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        text_content = ' '.join(str(v) for v in lead_data.values() if isinstance(v, str)).lower()
        score, stage = 0.0, 'awareness'
        if any(k in text_content for k in ['request a demo', 'contact sales']):
            score, stage = 0.9, 'decision'
        elif any(k in text_content for k in ['evaluating', 'considering options']):
            score, stage = 0.6, 'consideration'
        return {'intent_score': score, 'intent_stage': stage}
