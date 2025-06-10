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
# Verifica a disponibilidade das bibliotecas e define flags.
try:
    import google.generativeai as genai
    from sentence_transformers import SentenceTransformer
    import numpy as np
    RAG_LIBRARIES_AVAILABLE = True
except ImportError:
    RAG_LIBRARIES_AVAILABLE = False
    # Define classes placeholder para que o type hinting não quebre
    SentenceTransformer = type('SentenceTransformer', (object,), {})
    genai = type('genai', (object,), {})
    np = type('np', (object,), {})


class AdvancedProspectProfiler:
    """
    Cria um perfil de prospect avançado usando análise de sinais e um pipeline RAG
    para gerar insights preditivos baseados em um contexto de negócios.
    """

    def __init__(self):
        """
        Inicializa o profiler, carregando o modelo de embedding e o cliente LLM.
        """
        self.embedding_model: Optional[SentenceTransformer] = None
        self.llm_client: Optional[genai.GenerativeModel] = None

        if not RAG_LIBRARIES_AVAILABLE:
            logger.warning("Bibliotecas RAG (numpy, sentence-transformers, google-generativeai) não encontradas. Funcionalidades de profiling avançado estarão desativadas.")
            return

        # 1. Carregar Modelo de Embedding
        try:
            logger.info("Profiler: Carregando modelo de embedding 'all-MiniLM-L6-v2'...")
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.success("Profiler: Modelo de embedding carregado com sucesso.")
        except Exception as e:
            logger.error(f"Profiler: Falha ao carregar o modelo SentenceTransformer: {e}. Insights RAG desativados.")

        # 2. Configurar Cliente LLM (Google Gemini)
        try:
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            if not gemini_api_key:
                logger.warning("Profiler: Variável de ambiente GEMINI_API_KEY não encontrada. Insights do LLM desativados.")
            else:
                genai.configure(api_key=gemini_api_key)
                generation_config = {
                    "temperature": 0.3,
                    "top_p": 1,
                    "top_k": 1,
                    "max_output_tokens": 300,
                }
                self.llm_client = genai.GenerativeModel(
                    'gemini-pro',
                    generation_config=generation_config
                )
                logger.success("Profiler: Cliente LLM Google Gemini inicializado com sucesso.")
        except Exception as e:
            logger.error(f"Profiler: Erro ao inicializar o cliente Gemini: {e}. Insights do LLM desativados.")

    def create_advanced_prospect_profile(
        self,
        lead_data: Dict[str, Any],
        enriched_context: Dict[str, Any],
        rag_vector_store: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Cria um perfil de prospect completo, combinando análise de sinais e insights RAG.
        """
        text_content = self._extract_text_from_lead(lead_data)
        intent_score = self._analyze_buying_intent(text_content)
        pain_alignment = self._analyze_pain_alignment(text_content, enriched_context)
        urgency_score = self._calculate_urgency_score(text_content)
        
        predictive_insights = self._generate_predictive_insights(
            lead_data, enriched_context, rag_vector_store
        )

        return {
            'prospect_score': self._calculate_overall_prospect_score(intent_score, pain_alignment, urgency_score),
            'buying_intent_score': intent_score,
            'pain_alignment_score': pain_alignment,
            'urgency_score': urgency_score,
            'predictive_insights': predictive_insights,
        }

    def _generate_predictive_insights(
        self,
        lead_data: Dict[str, Any],
        enriched_context: Dict[str, Any],
        rag_vector_store: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Executa o pipeline RAG para gerar insights preditivos.
        """
        company_name = lead_data.get('company_name', 'N/A')
        fallback_insights = [f"Análise padrão indica que '{company_name}' pode se beneficiar de nossas soluções."]

        # Validação dos componentes RAG
        if not all([self.embedding_model, self.llm_client, rag_vector_store]):
            logger.warning(f"Componentes RAG (modelo, LLM ou vector store) indisponíveis para '{company_name}'. Retornando insights de fallback.")
            return fallback_insights

        # 1. Formular a Consulta (Query) a partir dos dados do lead
        lead_snippet = self._extract_text_from_lead(lead_data, max_length=1000)
        query = f"Para uma empresa chamada '{company_name}', descrita como '{lead_snippet}', quais são as oportunidades de venda e os desafios que nossa solução pode resolver?"

        # 2. Gerar Embedding da Consulta
        try:
            query_embedding = self.embedding_model.encode([query])[0].astype('float32')
        except Exception as e:
            logger.error(f"Profiler: Falha ao gerar embedding para a consulta do lead '{company_name}': {e}")
            return fallback_insights

        # 3. Buscar no Vector Store (FAISS)
        faiss_index = rag_vector_store.get("index")
        stored_chunks = rag_vector_store.get("chunks", [])
        retrieved_context = "Nenhum contexto específico foi recuperado."
        
        if faiss_index and stored_chunks:
            try:
                k = min(3, len(stored_chunks)) # Recupera até 3 chunks mais relevantes
                distances, indices = faiss_index.search(np.expand_dims(query_embedding, axis=0), k)
                
                # Constrói o contexto com base nos chunks recuperados
                retrieved_chunks_texts = [stored_chunks[i] for i in indices[0] if i < len(stored_chunks)]
                retrieved_context = "\n\n---\n\n".join(retrieved_chunks_texts)
                logger.info(f"Profiler: {len(retrieved_chunks_texts)} chunks de contexto recuperados para '{company_name}'.")
            except Exception as e:
                logger.error(f"Profiler: Erro na busca do FAISS para '{company_name}': {e}")
        
        # 4. Construir o Prompt para o LLM
        llm_prompt = f"""
Você é um analista de vendas B2B sênior e especialista em estratégia.
Sua tarefa é gerar 3 insights preditivos e acionáveis para a equipe de vendas sobre o lead abaixo, com base EXCLUSIVAMENTE nas informações fornecidas.

**INFORMAÇÕES DO LEAD:**
- **Nome da Empresa:** {company_name}
- **Descrição:** {lead_snippet}

**CONTEXTO ESTRATÉGICO DO NOSSO NEGÓCIO (Recuperado por IA):**
---
{retrieved_context}
---

**TAREFA:**
Com base em tudo acima, gere 3 insights preditivos. Seja direto e foque em "por que" eles podem precisar da nossa solução e "como" podemos abordá-los.

Formato da resposta (use bullets):
- Insight 1: [descreva a oportunidade ou dor]
- Insight 2: [sugira um ângulo de abordagem]
- Insight 3: [aponte um diferencial competitivo relevante]
"""

        # 5. Chamar o LLM e processar a resposta
        try:
            logger.info(f"Profiler: Chamando a API do Gemini para gerar insights para '{company_name}'.")
            response = self.llm_client.generate_content(llm_prompt)
            
            # Limpa e formata a saída do LLM
            insights = [line.strip().lstrip('- ').strip() for line in response.text.split('\n') if line.strip()]
            return insights if insights else fallback_insights
        except Exception as e:
            logger.error(f"Profiler: Erro na chamada da API do Gemini para '{company_name}': {e}")
            logger.debug(traceback.format_exc())
            return fallback_insights
    
    # Métodos de análise de sinais (não usam RAG, mas complementam o perfil)
    def _extract_text_from_lead(self, lead_data: Dict[str, Any], max_length: int = 2000) -> str:
        text_parts = [
            str(lead_data.get('company_name', '')),
            str(lead_data.get('description', '')),
            str(lead_data.get('snippet', ''))
        ]
        full_text = ' '.join(filter(None, text_parts)).lower()
        return full_text[:max_length]

    def _analyze_buying_intent(self, text_content: str) -> float:
        keywords = ['hiring', 'expanding', 'funding', 'seeking', 'looking for', 'need', 'require']
        score = sum(1 for k in keywords if k in text_content)
        return round(min(score / 3.0, 1.0), 3)

    def _analyze_pain_alignment(self, text_content: str, enriched_context: Dict[str, Any]) -> float:
        problems_we_solve = enriched_context.get('lead_qualification_criteria', {}).get('problems_we_solve', [])
        if not problems_we_solve:
            return 0.5
        
        alignment_count = sum(1 for p in problems_we_solve if str(p).lower() in text_content)
        return round(min(alignment_count / len(problems_we_solve), 1.0), 3)

    def _calculate_urgency_score(self, text_content: str) -> float:
        keywords = ['urgent', 'asap', 'immediately', 'deadline', 'critical', 'priority']
        score = sum(1 for k in keywords if k in text_content)
        return round(min(score / 2.0, 1.0), 3)

    def _calculate_overall_prospect_score(self, intent: float, alignment: float, urgency: float) -> float:
        weights = {'intent': 0.4, 'alignment': 0.4, 'urgency': 0.2}
        score = (intent * weights['intent'] + alignment * weights['alignment'] + urgency * weights['urgency'])
        return round(score, 3)


class BuyingSignalPredictor:
    """
    Analisa texto para prever sinais de compra com base em padrões de regex.
    """
    def __init__(self):
        self.signal_patterns = {
            'hiring_growth': {'patterns': [r'hiring', r'job opening', r'we are growing'], 'weight': 0.9},
            'technology_change': {'patterns': [r'upgrading systems', r'new platform', r'digital transformation'], 'weight': 0.7},
            'funding_event': {'patterns': [r'funding round', r'investment', r'series [abc]'], 'weight': 1.0},
        }

    def predict_buying_signals(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        text_content = ' '.join(str(v) for v in lead_data.values() if isinstance(v, str)).lower()
        
        detected_signals = []
        for signal, config in self.signal_patterns.items():
            if any(re.search(p, text_content) for p in config['patterns']):
                detected_signals.append({'signal_type': signal, 'confidence': config['weight']})
        
        return {'detected_signals': detected_signals}


class ProspectIntentScorer:
    """
    Calcula uma pontuação de intenção de compra com base em palavras-chave.
    """
    def __init__(self):
        self.intent_keywords = {
            'high_intent': ['looking for', 'need a solution', 'request a demo'],
            'medium_intent': ['considering', 'evaluating', 'exploring options'],
            'low_intent': ['learn more', 'what is', 'how to'],
        }

    def calculate_intent_score(self, lead_data: Dict[str, Any], enriched_context: Dict[str, Any]) -> Dict[str, Any]:
        text_content = ' '.join(str(v) for v in lead_data.values() if isinstance(v, str)).lower()
        score = 0.0
        stage = 'awareness'

        if any(k in text_content for k in self.intent_keywords['high_intent']):
            score = 0.9
            stage = 'decision'
        elif any(k in text_content for k in self.intent_keywords['medium_intent']):
            score = 0.6
            stage = 'consideration'
        elif any(k in text_content for k in self.intent_keywords['low_intent']):
            score = 0.3
            stage = 'interest'
            
        return {'intent_score': score, 'intent_stage': stage}
