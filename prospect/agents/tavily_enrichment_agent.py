import os
import json
import requests
import time
import re
import traceback
from typing import Optional, List

from pydantic import BaseModel

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
TAVILY_SEARCH_DEPTH = "advanced"  # Or "basic"
TAVILY_MAX_RESULTS_PER_QUERY = 5
TAVILY_TOTAL_QUERIES_PER_LEAD = 3
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000  # Max input tokens for Gemini Flash is 128k, roughly 512k chars. Input is 32k tokens, output 2k.


class TavilyEnrichmentInput(BaseModel):
    company_name: str
    initial_extracted_text: str


class TavilyEnrichmentOutput(BaseModel):
    enriched_data: str
    tavily_api_called: bool
    error_message: Optional[str] = None


class TavilyEnrichmentAgent(BaseAgent[TavilyEnrichmentInput, TavilyEnrichmentOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, tavily_api_key: str, **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)
        self.tavily_api_key = tavily_api_key

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def _search_with_tavily(self, query: str, search_depth: str = "advanced", max_results: int = 5) -> List[dict]:
        """
        Performs a search using the Tavily API.
        """
        try:
            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.tavily_api_key,
                    "query": query,
                    "search_depth": search_depth,
                    "include_answer": True,
                    "max_results": max_results,
                },
                timeout=100  # segundos
            )
            response.raise_for_status()  # Raise an exception for bad status codes
            return response.json().get("results", [])
        except requests.exceptions.RequestException as e:
            print(f"Tavily API request failed: {e}")
            return []
        except json.JSONDecodeError:
            print("Failed to decode Tavily API response.")
            return []

    def process(self, input_data: TavilyEnrichmentInput) -> TavilyEnrichmentOutput:
        tavily_api_called = False
        error_message = None
        enriched_data = input_data.initial_extracted_text
        
        self.logger.info(f"🔍 TAVILY ENRICHMENT STARTING for company: {input_data.company_name}")
        self.logger.info(f"📊 Input data: text_length={len(input_data.initial_extracted_text)}, api_key_available={bool(self.tavily_api_key)}")

        try:
            # First LLM call to generate search queries
            self.logger.debug("🤖 Step 1: Generating search queries with LLM")
            prompt_template_tavily_queries = """
                Com base no texto extraído e no nome da empresa, gere {TAVILY_TOTAL_QUERIES_PER_LEAD} consultas de pesquisa concisas e direcionadas para o Tavily API para encontrar informações adicionais sobre a empresa.
                Concentre-se em encontrar:
                1.  Detalhes sobre os produtos ou serviços da empresa.
                2.  Informações de contato (e-mails, perfis de mídia social).
                3.  Notícias recentes ou desenvolvimentos relacionados à empresa.
                Retorne as consultas como uma lista JSON de strings.

                Nome da Empresa: {company_name}
                Texto Extraído:
                {initial_extracted_text}

                Consultas de Pesquisa (JSON):
            """
            formatted_prompt_queries = prompt_template_tavily_queries.format(
                TAVILY_TOTAL_QUERIES_PER_LEAD=TAVILY_TOTAL_QUERIES_PER_LEAD,
                company_name=input_data.company_name,
                initial_extracted_text=self._truncate_text(input_data.initial_extracted_text, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 2) # Leave space for response
            )

            llm_response_queries = self.generate_llm_response(formatted_prompt_queries)

            if not llm_response_queries:
                self.logger.error("❌ LLM call for Tavily queries returned no response")
                return TavilyEnrichmentOutput(
                    enriched_data=enriched_data,
                    tavily_api_called=False,
                    error_message="LLM call for Tavily queries returned no response."
                )

            self.logger.debug(f"✅ LLM returned queries response, length: {len(llm_response_queries)}")
            
            try:
                # Extract JSON from the response
                match = re.search(r"```json\n(.*)\n```", llm_response_queries, re.DOTALL)
                if match:
                    json_str = match.group(1)
                    self.logger.debug("📝 Extracted queries from JSON markdown block")
                else:
                    json_str = llm_response_queries
                    self.logger.debug("📝 Using raw response as JSON")

                search_queries = json.loads(json_str)
                if not isinstance(search_queries, list) or not all(isinstance(q, str) for q in search_queries):
                    raise ValueError("LLM did not return a valid list of search strings.")
                    
                self.logger.info(f"🔍 Generated {len(search_queries)} search queries: {search_queries}")
                
            except (json.JSONDecodeError, ValueError) as e:
                self.logger.warning(f"⚠️  Error decoding LLM response for search queries: {e}")
                self.logger.debug(f"Failed response: {llm_response_queries[:500]}...")
                error_message = f"Error decoding LLM response for search queries: {e}. Response: {llm_response_queries}"
                # Fallback: use company name as a single query
                search_queries = [f"informações sobre a empresa {input_data.company_name}"]
                self.logger.info(f"🔄 Using fallback query: {search_queries}")

            all_tavily_results_text = ""
            if search_queries:
                tavily_api_called = True
                self.logger.info(f"🌐 Starting Tavily API calls for {len(search_queries)} queries")
                
                for query_count, query in enumerate(search_queries):
                    if query_count >= TAVILY_TOTAL_QUERIES_PER_LEAD:
                        self.logger.debug(f"⏭️  Stopping at query limit: {TAVILY_TOTAL_QUERIES_PER_LEAD}")
                        break
                    if not query.strip(): # Skip empty queries
                        self.logger.debug("⏭️  Skipping empty query")
                        continue
                    
                    # Add company name to query if not present
                    if input_data.company_name.lower() not in query.lower():
                        query = f"{query} ({input_data.company_name})"

                    self.logger.debug(f"🔍 Query {query_count + 1}: {query}")
                    
                    tavily_results = self._search_with_tavily(
                        query,
                        search_depth=TAVILY_SEARCH_DEPTH,
                        max_results=TAVILY_MAX_RESULTS_PER_QUERY
                    )
                    
                    self.logger.debug(f"📊 Query {query_count + 1} returned {len(tavily_results)} results")
                    time.sleep(1) # Respect API rate limits

                    if tavily_results:
                        for result in tavily_results:
                            content_length = len(result.get('content', ''))
                            all_tavily_results_text += f"Fonte: {result.get('url', 'N/A')}\nConteúdo: {result.get('content', '')}\n\n"
                            self.logger.debug(f"📄 Added result from {result.get('url', 'N/A')}: {content_length} chars")
                            
                    if len(all_tavily_results_text) > GEMINI_TEXT_INPUT_TRUNCATE_CHARS * 0.75: # Stop if too much text
                        self.logger.debug(f"⏹️  Stopping due to text length limit: {len(all_tavily_results_text)} chars")
                        break
                
                self.logger.info(f"📊 Total Tavily results collected: {len(all_tavily_results_text)} characters")
            
            if tavily_api_called and all_tavily_results_text:
                # Second LLM call to summarize and enrich
                prompt_template_summarize = """
                    Com base no texto extraído original e nos resultados da pesquisa do Tavily API, forneça um resumo abrangente e enriquecido.
                    Concentre-se em extrair e apresentar claramente:
                    1.  Uma breve visão geral da empresa.
                    2.  Principais produtos ou serviços oferecidos.
                    3.  Qualquer informação de contato encontrada (e-mails, números de telefone, perfis de mídia social).
                    4.  Pontos de interesse ou notícias recentes.
                    5.  Seja o mais informativo possível, mas evite redundâncias.

                    Texto Extraído Original:
                    {initial_extracted_text}

                    Resultados da Pesquisa Tavily:
                    {tavily_results_text}

                    Resumo Enriquecido:
                """
                truncated_initial_text = self._truncate_text(input_data.initial_extracted_text, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 3)
                truncated_tavily_results = self._truncate_text(all_tavily_results_text, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 3)

                formatted_prompt_summarize = prompt_template_summarize.format(
                    initial_extracted_text=truncated_initial_text,
                    tavily_results_text=truncated_tavily_results
                )
                
                # This LLM call is for summarization into a string, not JSON.
                enriched_summary_text = self.generate_llm_response(formatted_prompt_summarize)

                if enriched_summary_text:
                    enriched_data = enriched_summary_text
                else:
                    # Fallback if summarization fails, append Tavily results to original
                    enriched_data = input_data.initial_extracted_text + "\n\nInformações Adicionais (Tavily):\n" + all_tavily_results_text 
                    if not error_message: # Keep previous error if any
                        error_message = "LLM call for summarization returned no response. Appending raw Tavily data."
            elif tavily_api_called and not all_tavily_results_text:
                 if not error_message: # Keep previous error if any
                    error_message = "Tavily API was called but returned no results."
            
            # If no Tavily search was performed, enriched_data remains initial_extracted_text
            
        except Exception as e:
            print(f"An unexpected error occurred in TavilyEnrichmentAgent: {e}")
            traceback.print_exc()
            error_message = f"An unexpected error occurred: {str(e)}"

        return TavilyEnrichmentOutput(
            enriched_data=enriched_data,
            tavily_api_called=tavily_api_called,
            error_message=error_message
        )

if __name__ == '__main__':
    # This is a placeholder for testing
    # You would need a mock LLMClient and a Tavily API Key
    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str) -> Optional[str]:
            if "consultas de pesquisa" in prompt:
                return json.dumps([
                    "latest news about Test Company Inc.",
                    "Test Company Inc. products and services",
                    "contact Test Company Inc."
                ])
            elif "Resumo Enriquecido" in prompt:
                return "This is an enriched summary about Test Company Inc. based on web search."
            return "Default mock response."

    # Replace 'YOUR_TAVILY_API_KEY' with your actual key for testing, or ensure it's in environment variables
    tavily_key = os.environ.get("TAVILY_API_KEY") 
    if not tavily_key:
        print("TAVILY_API_KEY not found in environment variables. Skipping live test.")
    else:
        print("Running a mock test for TavilyEnrichmentAgent...")
        mock_llm = MockLLMClient(api_key="mock_llm_key")
        agent = TavilyEnrichmentAgent(llm_client=mock_llm, tavily_api_key=tavily_key)
        
        test_input = TavilyEnrichmentInput(
            company_name="Test Company Inc.",
            initial_extracted_text="Test Company Inc. is a company that does testing."
        )
        
        output = agent.process(test_input)
        
        print(f"Tavily API Called: {output.tavily_api_called}")
        print(f"Enriched Data: {output.enriched_data}")
        if output.error_message:
            print(f"Error: {output.error_message}")

        print("\nTesting with a query that might return an error for Tavily queries LLM response (e.g. invalid JSON)")
        class MockLLMClientError(LLMClientBase):
            def __init__(self, api_key: str):
                super().__init__(api_key)
            def generate_text_response(self, prompt: str) -> Optional[str]:
                if "consultas de pesquisa" in prompt:
                    return "This is not a valid JSON" # Invalid response
                elif "Resumo Enriquecido" in prompt:
                     return "This is an enriched summary about Test Company Inc. based on web search."
                return "Default mock response."

        mock_llm_error = MockLLMClientError(api_key="mock_llm_key_error")
        agent_error_test = TavilyEnrichmentAgent(llm_client=mock_llm_error, tavily_api_key=tavily_key)
        output_error = agent_error_test.process(test_input)
        print(f"Tavily API Called (error test): {output_error.tavily_api_called}")
        print(f"Enriched Data (error test): {output_error.enriched_data}")
        if output_error.error_message:
            print(f"Error (error test): {output_error.error_message}")

        print("\nTesting with no Tavily results")
        # To truly test no Tavily results, you might need to mock _search_with_tavily or use a query that yields nothing
        # For now, we'll rely on the previous error message for the case where Tavily might be called but returns nothing.
        # A more direct test would involve a mock _search_with_tavily that returns [].
        # The current fallback logic will use company name if LLM fails to generate queries.
        # If that query also returns nothing, it will be caught by `tavily_api_called and not all_tavily_results_text`
        
        test_input_no_results_likely = TavilyEnrichmentInput(
            company_name="NonExistentCompanyNameXYZ123",
            initial_extracted_text="This company likely does not exist."
        )
        output_no_results = agent.process(test_input_no_results_likely) # Using the first agent with working LLM mock
        print(f"Tavily API Called (no results test): {output_no_results.tavily_api_called}")
        print(f"Enriched Data (no results test): {output_no_results.enriched_data}")
        if output_no_results.error_message:
            print(f"Error (no results test): {output_no_results.error_message}")
