import os
import json
import requests
import time
import re
import traceback
from typing import Optional, List, Dict # Added Dict
from pydantic import BaseModel, Field # Added Field

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
TAVILY_SEARCH_DEPTH = "advanced"
TAVILY_MAX_RESULTS_PER_QUERY = 3 # Reduced to get more focused results per query
TAVILY_TOTAL_QUERIES_PER_LEAD = 3
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000


class TavilyEnrichmentInput(BaseModel):
    company_name: str
    initial_extracted_text: str
    # product_service_offered: Optional[str] = None # Consider adding for more focused query generation
    # lead_url: Optional[str] = None # Consider adding for context

# Updated Pydantic Output Model
class TavilyEnrichmentOutput(BaseModel):
    enrichment_summary: str = "Nenhum resumo de enriquecimento gerado." # Renamed from enriched_data
    key_findings: List[str] = Field(default_factory=list)
    tavily_api_called: bool = False # Default to False
    error_message: Optional[str] = None

class TavilyEnrichmentAgent(BaseAgent[TavilyEnrichmentInput, TavilyEnrichmentOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, tavily_api_key: Optional[str] = None, **kwargs): # tavily_api_key can be optional
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
        if not self.tavily_api_key:
            self.logger.warning("Tavily API key not provided. Tavily search will be skipped.")
            # No ValueError raised here to allow agent to run without Tavily if desired,
            # it will simply return initial text with tavily_api_called=False.

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def _search_with_tavily(self, query: str, search_depth: str = TAVILY_SEARCH_DEPTH, max_results: int = TAVILY_MAX_RESULTS_PER_QUERY) -> List[dict]:
        """ Performs a search using the Tavily API. """
        if not self.tavily_api_key:
            self.logger.warning("Tavily API key not available. Skipping search.")
            return []
        try:
            self.logger.info(f"🔍 Executing Tavily search for query: '{query}'")
            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.tavily_api_key,
                    "query": query,
                    "search_depth": search_depth,
                    "include_answer": False, # Typically we want to process source content
                    "include_raw_content": False, # Get URLs and snippets first
                    "max_results": max_results,
                    # "include_domains": [], "exclude_domains": [] # Optional filters
                },
                timeout=20 # Reduced timeout slightly
            )
            response.raise_for_status()
            results = response.json().get("results", [])
            self.logger.info(f"✅ Tavily search for '{query}' returned {len(results)} results.")
            return results
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Tavily API request failed for query '{query}': {e}")
            return []
        except json.JSONDecodeError:
            self.logger.error(f"❌ Failed to decode Tavily API response for query '{query}'.")
            return []

    def process(self, input_data: TavilyEnrichmentInput) -> TavilyEnrichmentOutput:
        tavily_api_called = False
        error_message = None
        enrichment_summary = input_data.initial_extracted_text # Default to initial if no enrichment
        key_findings = []
        
        self.logger.info(f"🔍 TAVILY ENRICHMENT AGENT STARTING for company: {input_data.company_name}")
        self.logger.debug(f"📊 Input data: text_length={len(input_data.initial_extracted_text)}, Tavily API key configured: {bool(self.tavily_api_key)}")

        if not self.tavily_api_key:
            return TavilyEnrichmentOutput(
                enrichment_summary=enrichment_summary,
                key_findings=key_findings,
                tavily_api_called=False,
                error_message="Tavily API key not configured; skipping enrichment."
            )

        try:
            # Step 1: Generate search queries with LLM
            self.logger.debug("🤖 Step 1: Generating search queries with LLM...")
            # Refined prompt_template_tavily_queries
            prompt_template_tavily_queries = """
                Você é um Assistente de Pesquisa IA especializado em formular queries de busca eficazes.
                Com base no nome da empresa e no texto extraído fornecido, sua tarefa é gerar {TAVILY_TOTAL_QUERIES_PER_LEAD} consultas de pesquisa (search queries) distintas, concisas e direcionadas para a API Tavily.
                O objetivo é encontrar informações adicionais sobre a empresa, focando em:
                1.  Detalhes aprofundados sobre seus principais produtos ou serviços.
                2.  Informações de contato relevantes (e-mails de departamentos, perfis de mídia social corporativos, contatos de decisores chave, se possível).
                3.  Notícias recentes, comunicados de imprensa, ou desenvolvimentos significativos relacionados à empresa (ex: expansões, parcerias, novos lançamentos, situação financeira).

                Priorize queries que provavelmente revelarão informações B2B úteis para análise de leads.

                Nome da Empresa: "{company_name}"
                Texto Extraído Inicial (para contexto):
                \"\"\"
                {initial_extracted_text}
                \"\"\"

                Responda APENAS com um objeto JSON contendo uma lista de strings de consulta. Formato:
                {{
                    "search_queries": ["query 1", "query 2", "query 3"]
                }}
            """
            # Truncate with a buffer for the rest of the prompt
            truncated_initial_text_for_query_gen = self._truncate_text(input_data.initial_extracted_text, GEMINI_TEXT_INPUT_TRUNCATE_CHARS - 1000)
            formatted_prompt_queries = prompt_template_tavily_queries.format(
                TAVILY_TOTAL_QUERIES_PER_LEAD=TAVILY_TOTAL_QUERIES_PER_LEAD,
                company_name=input_data.company_name,
                initial_extracted_text=truncated_initial_text_for_query_gen
            )

            llm_response_queries_str = self.generate_llm_response(formatted_prompt_queries)

            search_queries = []
            if not llm_response_queries_str:
                self.logger.warning("⚠️ LLM call for Tavily queries returned no response. Using fallback query.")
                error_message = "LLM did not generate search queries."
            else:
                self.logger.debug(f"LLM returned for query generation: {llm_response_queries_str[:300]}...")
                queries_data = self.parse_llm_json_response(llm_response_queries_str, None) # Expect a dict
                if queries_data and isinstance(queries_data.get("search_queries"), list):
                    search_queries = queries_data["search_queries"]
                    self.logger.info(f"🔍 Generated {len(search_queries)} search queries: {search_queries}")
                else:
                    self.logger.warning(f"⚠️ Error decoding LLM response for search queries or not a list. Fallback. Raw: {llm_response_queries_str[:300]}")
                    error_message = "LLM did not return a valid list of search queries."

            if not search_queries: # Fallback if LLM fails or returns empty list
                search_queries = [f"latest news and key information about {input_data.company_name}"]
                self.logger.info(f"🔄 Using fallback query: {search_queries}")


            # Step 2: Perform Tavily searches
            all_tavily_results_text = ""
            if search_queries:
                tavily_api_called = True
                self.logger.info(f"🌐 Starting Tavily API calls for {len(search_queries)} queries...")
                
                for i, query in enumerate(search_queries[:TAVILY_TOTAL_QUERIES_PER_LEAD]):
                    if not query.strip(): continue
                    
                    tavily_results = self._search_with_tavily(query)
                    time.sleep(0.5) # Small delay between Tavily calls

                    if tavily_results:
                        all_tavily_results_text += f"\n\n--- Resultados da Busca para: '{query}' ---\n"
                        for result in tavily_results:
                            all_tavily_results_text += f"Fonte: {result.get('url', 'N/A')}\nTítulo: {result.get('title', 'N/A')}\nConteúdo Snippet: {result.get('content', '')}\n\n"
                    if len(all_tavily_results_text) > GEMINI_TEXT_INPUT_TRUNCATE_CHARS * 0.6: # Stop if too much text for summarizer
                        self.logger.warning(f"⚠️  Stopping Tavily search early due to accumulated text length: {len(all_tavily_results_text)} chars")
                        break
                self.logger.info(f"📊 Total Tavily results collected: {len(all_tavily_results_text)} characters.")
            
            # Step 3: Summarize and extract key findings with LLM
            if tavily_api_called and all_tavily_results_text.strip():
                self.logger.debug("🤖 Step 3: Summarizing Tavily results with LLM...")
                # Refined prompt_template_summarize
                prompt_template_summarize = """
                    Você é um Analista de Inteligência de Negócios especializado em sintetizar informações de múltiplas fontes em resumos concisos e extrair os achados mais críticos para prospecção B2B.

                    CONTEXTO:
                    Texto Extraído Original da Empresa:
                    \"\"\"
                    {initial_extracted_text}
                    \"\"\"

                    Resultados da Pesquisa Web Adicional (Tavily API):
                    \"\"\"
                    {tavily_results_text}
                    \"\"\"

                    INSTRUÇÕES:
                    Com base no "Texto Extraído Original" E nos "Resultados da Pesquisa Web Adicional", sua tarefa é:
                    1.  Gerar um `enrichment_summary`: Um resumo coeso que combine as informações mais relevantes de ambas as fontes. Deve fornecer uma visão geral atualizada da empresa, seus produtos/serviços, e quaisquer notícias ou desenvolvimentos recentes significativos. Evite redundância e foque em informações úteis para entender o lead. (Máximo 250-300 palavras)
                    2.  Identificar `key_findings`: Uma lista de 3-5 pontos chave (bullet points) extraídos de QUALQUER uma das fontes que sejam particularmente relevantes para uma possível prospecção B2B. Estes podem incluir anúncios importantes, desafios mencionados, contratações chave, lançamentos de produtos, etc.

                    FORMATO DA RESPOSTA:
                    Responda EXCLUSIVAMENTE com um objeto JSON válido, seguindo o schema abaixo. Não inclua NENHUM texto, explicação, ou markdown (como ```json) antes ou depois do objeto JSON.

                    SCHEMA JSON ESPERADO:
                    {{
                        "enrichment_summary": "string - O resumo abrangente e consolidado, conforme instrução 1.",
                        "key_findings": ["string", ...] // Lista de 3-5 achados chave (bullet points textuais). Se menos de 3 achados significativos forem encontrados, liste os que encontrar. Se nenhum, retorne uma lista vazia [].
                    }}
                """
                # Dynamic truncation based on remaining character budget for the prompt
                summarizer_prompt_overhead = 2000
                available_for_summarizer_inputs = GEMINI_TEXT_INPUT_TRUNCATE_CHARS - summarizer_prompt_overhead

                ratio_initial = len(input_data.initial_extracted_text) / (len(input_data.initial_extracted_text) + len(all_tavily_results_text) + 1e-6) # Avoid division by zero
                ratio_tavily = 1 - ratio_initial

                tr_initial_text_sum = self._truncate_text(input_data.initial_extracted_text, int(available_for_summarizer_inputs * ratio_initial))
                tr_tavily_results_sum = self._truncate_text(all_tavily_results_text, int(available_for_summarizer_inputs * ratio_tavily))

                formatted_prompt_summarize = prompt_template_summarize.format(
                    initial_extracted_text=tr_initial_text_sum,
                    tavily_results_text=tr_tavily_results_sum
                )
                
                llm_summary_response_str = self.generate_llm_response(formatted_prompt_summarize)

                if llm_summary_response_str:
                    summary_data = self.parse_llm_json_response(llm_summary_response_str, TavilyEnrichmentOutput) # Uses new model
                    if summary_data and not summary_data.error_message:
                        enrichment_summary = summary_data.enrichment_summary
                        key_findings = summary_data.key_findings
                        self.logger.info(f"✅ Summarization and key findings extraction successful. Summary length: {len(enrichment_summary)}, Findings: {len(key_findings)}")
                    else:
                        self.logger.warning(f"⚠️ LLM summarization step failed JSON parsing or Pydantic validation. Error: {summary_data.error_message if summary_data else 'No data'}. Raw: {llm_summary_response_str[:300]}")
                        # Fallback: use combined raw data and append existing error
                        enrichment_summary = input_data.initial_extracted_text + "\n\nInformações Adicionais (Tavily - Sem Sumarização LLM):\n" + all_tavily_results_text
                        current_error = summary_data.error_message if summary_data and summary_data.error_message else "LLM summarization failed to produce valid JSON."
                        error_message = f"{error_message}. {current_error}" if error_message else current_error
                else:
                    self.logger.warning("⚠️ LLM call for summarization returned no response. Appending raw Tavily data.")
                    enrichment_summary = input_data.initial_extracted_text + "\n\nInformações Adicionais (Tavily - Sem Sumarização LLM):\n" + all_tavily_results_text
                    no_summary_error = "LLM summarization failed (no response)."
                    error_message = f"{error_message}. {no_summary_error}" if error_message else no_summary_error
            
            elif tavily_api_called and not all_tavily_results_text.strip():
                 no_results_error = "Tavily API was called but returned no results for any query."
                 error_message = f"{error_message}. {no_results_error}" if error_message else no_results_error
                 self.logger.warning(f"⚠️ {no_results_error}")
            
        except Exception as e:
            self.logger.error(f"❌ An unexpected error occurred in {self.name} for {input_data.company_name}: {e}", exc_info=True)
            error_message = f"An unexpected error occurred: {str(e)}"

        return TavilyEnrichmentOutput(
            enrichment_summary=enrichment_summary, # Use the updated field name
            key_findings=key_findings,
            tavily_api_called=tavily_api_called,
            error_message=error_message.strip() if error_message else None
        )

if __name__ == '__main__':
    from loguru import logger
    import sys
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"): # api_key needed for base
            super().__init__(api_key)

        def generate_text_response(self, prompt: str) -> Optional[str]:
            logger.debug(f"MockLLMClient received prompt snippet:\n{prompt[:600]}...")
            if "consultas de pesquisa" in prompt: # Query generation prompt
                return json.dumps({
                    "search_queries": [
                        "latest news about Test Company Inc.",
                        "Test Company Inc. products and services overview",
                        "key contacts or decision makers at Test Company Inc."
                    ]
                })
            elif "Resumo Enriquecido" in prompt or "SCHEMA JSON ESPERADO" in prompt: # Summarization prompt (new)
                return json.dumps({
                    "enrichment_summary": "Test Company Inc. is a notable innovator in the testing solutions sector. Recent news includes a partnership with Beta Corp and the launch of their new 'TestMax' product line. They are actively hiring for sales roles, suggesting expansion.",
                    "key_findings": [
                        "Partnership with Beta Corp.",
                        "Launch of 'TestMax' product line.",
                        "Actively hiring for sales roles (indicates expansion)."
                    ]
                })
            return json.dumps({"enrichment_summary": "Default mock summary.", "key_findings": ["Default finding."]})

    tavily_key = os.getenv("TAVILY_API_KEY_TEST") # Use a specific test key if needed, or fallback to main
    if not tavily_key:
        tavily_key = os.getenv("TAVILY_API_KEY")

    if not tavily_key:
        logger.warning("TAVILY_API_KEY not found in environment variables. Mock tests requiring actual Tavily calls will be limited.")
        # Mock _search_with_tavily to prevent actual API calls if key is missing
        def mock_search_disabled(self, query: str, search_depth: str = "advanced", max_results: int = 5) -> List[dict]:
            logger.info(f"MOCK SEARCH (DISABLED): Would search for '{query}'")
            return [{"url": f"http://mock.tavily.com/{query.replace(' ', '-')}", "content": f"Mock content for query: {query}"}]
        TavilyEnrichmentAgent._search_with_tavily_original = TavilyEnrichmentAgent._search_with_tavily
        TavilyEnrichmentAgent._search_with_tavily = mock_search_disabled
        
    logger.info("Running mock test for TavilyEnrichmentAgent...")
    mock_llm = MockLLMClient(api_key="mock_llm_key")
    agent = TavilyEnrichmentAgent(
        name="TestTavilyAgent",
        description="Test Tavily Agent",
        llm_client=mock_llm,
        tavily_api_key=tavily_key # Pass key, even if it's None (agent handles it)
    )

    test_input = TavilyEnrichmentInput(
        company_name="Test Company Inc.",
        initial_extracted_text="Test Company Inc. is a company that does testing. Their website is testcompany.com."
    )

    output = agent.process(test_input)

    logger.info(f"Tavily API Called: {output.tavily_api_called}")
    logger.info(f"Enrichment Summary: {output.enrichment_summary}")
    logger.info(f"Key Findings: {output.key_findings}")
    if output.error_message:
        logger.error(f"Error: {output.error_message}")

    assert output.tavily_api_called if tavily_key else not output.tavily_api_called # API called only if key exists
    assert "Test Company Inc." in output.enrichment_summary
    if tavily_key: # Only expect key findings if Tavily was actually called and summarization worked
        assert len(output.key_findings) > 0
        assert "TestMax" in output.key_findings[1]

    # Restore original method if mocked
    if hasattr(TavilyEnrichmentAgent, '_search_with_tavily_original'):
        TavilyEnrichmentAgent._search_with_tavily = TavilyEnrichmentAgent._search_with_tavily_original
        del TavilyEnrichmentAgent._search_with_tavily_original

    logger.info("\nMock test for TavilyEnrichmentAgent completed.")

```
