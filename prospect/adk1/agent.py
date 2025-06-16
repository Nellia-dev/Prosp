# adk1/agent.py

import os
import re
import time
import json
from typing import List, Dict, Any, Union

import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from tavily import TavilyClient
from google.adk.agents import Agent
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configurações Globais ---
DELAY_BETWEEN_GEMINI_CALLS_SECONDS = 5  # Atraso para respeitar limites de taxa da API Gemini
MAX_GEMINI_INPUT_CHARS = 50000          # Limite de caracteres para input no Gemini para evitar estouro de tokens
MAX_SCRAPE_RESULTS = 5                  # Número máximo de resultados de busca do Tavily a serem raspados pelas ferramentas


# --- Funções Auxiliares (Reutilizadas e Adaptadas) ---
def web_scraper(url: str) -> dict:
    """
    Raspa o conteúdo textual de uma URL fornecida.
    Esta é uma função auxiliar interna, chamada por outras ferramentas compostas.

    Args:
        url: A URL da página web a ser raspada.

    Returns:
        Um dicionário contendo:
        - "title": O título da página web.
        - "url": A URL original.
        - "content": O conteúdo textual limpo da página web.
        - "error": Uma mensagem de erro se a busca ou o parsing falhar.
    """
    try:
        # Limpa a URL de caracteres indesejados
        cleaned_url = url.strip().replace('\t', '').replace('\n', '').replace('\r', '')
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(cleaned_url, headers=headers, timeout=10)
        response.raise_for_status()  # Levanta uma exceção para códigos de status HTTP de erro

        soup = BeautifulSoup(response.text, 'html.parser')

        title = soup.title.string if soup.title else 'No Title Found'

        # Remove scripts e estilos para obter apenas o texto visível
        for script_or_style in soup(['script', 'style']):
            script_or_style.extract()

        text_content = soup.get_text(separator=' ', strip=True)

        return {
            "title": title,
            "url": url,
            "content": text_content
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"Falha ao buscar conteúdo de {url} (limpa para '{cleaned_url}'): {e}"}
    except Exception as e:
        return {"error": f"Um erro inesperado ocorreu ao raspar {url} (limpa para '{cleaned_url}'): {e}"}


def _tavily_search_internal(query: str, max_results: int = 10) -> List[Dict]: # Aumentado para 10 links
    """
    Realiza uma busca usando a API Tavily e retorna uma lista de resultados brutos.
    Requer que TAVILY_API_KEY esteja configurada nas variáveis de ambiente.
    """
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not tavily_api_key:
        raise ValueError("TAVILY_API_KEY não está configurada nas variáveis de ambiente.")

    try:
        tavily = TavilyClient(api_key=tavily_api_key)
        # depth="advanced" para resultados mais abrangentes, include_answer=False para focar nos links
        response = tavily.search(query=query, search_depth="advanced", max_results=max_results, include_answer=False, include_raw_content=False)

        results = []
        if response and response.get('results'):
            for r in response['results']:
                results.append({
                    "title": r.get('title', 'No Title Found'),
                    "url": r.get('url', ''),
                    "snippet": r.get('content', 'No snippet available.')
                })
        return results
    except Exception as e:
        raise Exception(f"Falha na busca Tavily: {e}")


def _initialize_gemini_model():
    """Função auxiliar para inicializar o modelo Gemini, configurando a chave da API."""
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY não está configurada nas variáveis de ambiente.")
    genai.configure(api_key=google_api_key)
    # Usamos gemini-1.5-flash pela velocidade e custo-benefício
    return genai.GenerativeModel("gemini-1.5-flash")


# --- COMPOSITE TOOLS (Adapted for Lead Generation) ---

def search_and_qualify_leads(query: str, max_search_results_to_scrape: int, output_language: str = "en-US") -> List[Dict[str, Any]]:
    """
    Performs a web search for potential leads, scrapes the content, and performs an initial qualification
    using Gemini, returning the scraped content with a qualification summary.

    Args:
        query: The search query string to find leads.
        max_search_results_to_scrape: Maximum number of search results (from Tavily) to be scraped and qualified.
        output_language: The desired language for the LLM response (e.g., "en-US", "pt-BR").

    Returns:
        A list of dictionaries, each containing:
        - 'title': Page title.
        - 'url': Original URL.
        - 'snippet': Search snippet.
        - 'full_content': Scraped content.
        - 'qualification_summary': Gemini's assessment of lead relevance.
        - 'error': If any error occurred during scraping or qualification.
    """
    print(f"--- DEBUG (search_and_qualify_leads): Called with query='{query}', max_search_results_to_scrape={max_search_results_to_scrape}, output_language='{output_language}' ---")
    try:
        model = _initialize_gemini_model()
        # Use default value if not provided
        if max_search_results_to_scrape is None:
            max_search_results_to_scrape = MAX_SCRAPE_RESULTS

        print(f"--- DEBUG (search_and_qualify_leads): Calling _tavily_search_internal with query='{query}', max_results={max_search_results_to_scrape * 2} ---")
        search_results = _tavily_search_internal(query=query, max_results=max_search_results_to_scrape * 2)
        print(f"--- DEBUG (search_and_qualify_leads): _tavily_search_internal returned {len(search_results)} results ---")

        if not search_results:
            print("--- DEBUG (search_and_qualify_leads): No search results from Tavily. ---")
            return [{"error": "Não foram encontrados resultados na busca inicial com a Tavily."}]

        qualified_leads_data: list[dict[str, Any]] = []
        successfully_scraped_leads = 0
        leads_attempted_to_scrape = 0

        for result_idx, result in enumerate(search_results):
            if leads_attempted_to_scrape >= max_search_results_to_scrape:
                print(f"--- DEBUG (search_and_qualify_leads): Limite de {max_search_results_to_scrape} tentativas de raspagem atingido. Parando loop principal.")
                break
            leads_attempted_to_scrape += 1

            url_to_scrape = result.get('url')
            if url_to_scrape and url_to_scrape.startswith('http'):
                print(f"--- DEBUG (search_and_qualify_leads): [Attempt {leads_attempted_to_scrape}/{max_search_results_to_scrape}] Processing result {result_idx+1}/{len(search_results)}: {url_to_scrape} ---")

                if successfully_scraped_leads >= max_search_results_to_scrape:
                    print(f"--- DEBUG (search_and_qualify_leads): Successfully scraped {successfully_scraped_leads} leads, which meets or exceeds max_search_results_to_scrape ({max_search_results_to_scrape}). Stopping. ---")
                    break

                print(f"--- DEBUG (search_and_qualify_leads): [Attempt {leads_attempted_to_scrape}/{max_search_results_to_scrape}] Calling web_scraper for {url_to_scrape} ---")
                scraped_data = web_scraper(url=url_to_scrape)
                print(f"--- DEBUG (search_and_qualify_leads): [Attempt {leads_attempted_to_scrape}/{max_search_results_to_scrape}] web_scraper returned for {url_to_scrape} ---")

                if not scraped_data.get('error') and scraped_data.get('content'):
                    full_content = scraped_data.get('content')
                    print(f"--- DEBUG (search_and_qualify_leads): [Attempt {leads_attempted_to_scrape}/{max_search_results_to_scrape}] Successfully scraped {len(full_content)} chars from {url_to_scrape}. ---")

                    # Refined prompt_qualify
                    prompt_qualify = (
                        f"You are a business analyst specializing in lead qualification.\n"
                        f"Your task is to analyze the following web page content and determine if it represents a "
                        f"relevant B2B potential lead for the original search query: '{query}'.\n"
                        f"Key Actions:\n"
                        f"1. Identify the company/organization name, if clearly available.\n"
                        f"2. Summarize key points about the company/organization and its type of business.\n"
                        f"3. Assess its relevance as a lead for the query '{query}'.\n"
                        f"4. Be concise in your response.\n\n"
                        f"If the content is not relevant to the query or is an error/unavailable page, clearly indicate this.\n\n"
                        f"Web Page Content:\n\"\"\"\n{full_content[:MAX_GEMINI_INPUT_CHARS]}\n\"\"\"\n\n"
                        f"Important: Generate your entire response, including all textual content and string values within any JSON structure, strictly in the following language: {output_language}. Do not include any English text unless it is part of the original input data that should be preserved as is."
                    )
                    qualification_summary = "Could not qualify with Gemini. Raw content available." # Default value
                    print(f"--- DEBUG (search_and_qualify_leads): [Attempt {leads_attempted_to_scrape}/{max_search_results_to_scrape}] Calling Gemini's model.generate_content for qualification of {url_to_scrape}. ---")
                    try:
                        gemini_response = model.generate_content(prompt_qualify)
                        print(f"--- DEBUG (search_and_qualify_leads): [Attempt {leads_attempted_to_scrape}/{max_search_results_to_scrape}] Gemini's model.generate_content returned for qualification of {url_to_scrape}. ---")
                        qualification_summary = gemini_response.text
                    except Exception as gemini_err:
                        print(f"--- DEBUG (search_and_qualify_leads): [Attempt {leads_attempted_to_scrape}/{max_search_results_to_scrape}] Error qualifying with Gemini for {url_to_scrape}: {gemini_err}. ---")
                        # qualification_summary remains the default value

                    qualified_leads_data.append({
                        "title": result.get('title'),
                        "url": url_to_scrape,
                        "snippet": result.get('snippet'),
                        "full_content": full_content,
                        "qualification_summary": qualification_summary
                    })
                    successfully_scraped_leads += 1

                    if successfully_scraped_leads >= max_search_results_to_scrape:
                         print(f"--- DEBUG (search_and_qualify_leads): [Attempt {leads_attempted_to_scrape}/{max_search_results_to_scrape}] Successfully scraped leads limit ({max_search_results_to_scrape}) reached after qualifying {url_to_scrape}. ---")
                         # The main loop condition will handle breaking if this was the last attempt allowed.

                    time.sleep(DELAY_BETWEEN_GEMINI_CALLS_SECONDS)  # Pause to manage rate limits
                else:
                    print(f"--- DEBUG (search_and_qualify_leads): [Attempt {leads_attempted_to_scrape}/{max_search_results_to_scrape}] Failed to scrape '{url_to_scrape}': {scraped_data.get('error', 'Empty content/unknown error')} ---")
            else:
                print(f"--- DEBUG (search_and_qualify_leads): [Attempt {leads_attempted_to_scrape}/{max_search_results_to_scrape}] Invalid or empty URL, skipping: '{url_to_scrape}' ---")

            if successfully_scraped_leads >= max_search_results_to_scrape: # Check after processing each URL
                print(f"--- DEBUG (search_and_qualify_leads): Successfully scraped leads limit ({max_search_results_to_scrape}) reached within the outer loop for URL {url_to_scrape}. Stopping. ---")
                break

        print(f"--- DEBUG (search_and_qualify_leads): Finished. Returning {len(qualified_leads_data)} qualified leads after attempting to scrape {leads_attempted_to_scrape} search results. ---")
        return qualified_leads_data
    except ValueError as ve:
        print(f"--- DEBUG (search_and_qualify_leads): API configuration error: {ve} ---")
        return [{"error": f"API configuration error: {ve}"}]
    except Exception as e:
        print(f"--- DEBUG (search_and_qualify_leads): An unexpected error occurred in the composite tool: {e} ---")
        return [{"error": f"An unexpected error occurred in the composite tool: {e}"}]


def find_and_extract_structured_leads(query: str, max_search_results_to_process: int, output_language: str = "en-US") -> List[Dict[str, Any]]:
    """
    Performs a deep search for leads, scrapes content, and extracts structured lead information
    (company name, website, emails, phones, etc.) using Regex and Gemini.

    Args:
        query: The search query string to find leads.
        max_search_results_to_process: The maximum number of search results to be scraped and analyzed.
        output_language: The desired language for the LLM response (e.g., "en-US", "pt-BR").

    Returns:
        A list of dictionaries, where each dictionary represents a structured lead.
        Returns an empty list if no leads are found or if an error occurs.
    """
    print(f"--- DEBUG (find_and_extract_structured_leads): Called with query='{query}', max_search_results_to_process={max_search_results_to_process}, output_language='{output_language}' ---")
    
    # Padrões comuns de Regex para e-mails, telefones e sites (pode ser refinado para mais variações)
    email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    # Regex para telefone (brasileiro com e sem DDI/DDD, com ou sem formatação)
    phone_regex = r'\b(?:\+?\d{1,3}\s?)?(?:\(?\d{2}\)?\s?)?\d{4,5}[-\s]?\d{4}\b'
    website_regex = r'(?:https?:\/\/)?(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\.[a-zA-Z]{2,})(?:\/\S*)?'

    extracted_leads: list[dict[str, Any]] = []
    successfully_processed_leads = 0
    leads_attempted_to_process = 0

    try:
        model = _initialize_gemini_model()
        # Use default value if not provided
        if max_search_results_to_process is None:
            max_search_results_to_process = MAX_SCRAPE_RESULTS

        print(f"--- DEBUG (find_and_extract_structured_leads): Calling _tavily_search_internal with query='{query}', max_results={max_search_results_to_process * 2} ---")
        search_results = _tavily_search_internal(query=query, max_results=max_search_results_to_process * 2)
        print(f"--- DEBUG (find_and_extract_structured_leads): _tavily_search_internal returned {len(search_results)} results ---")

        if not search_results:
            print("--- DEBUG (find_and_extract_structured_leads): No search results from Tavily. ---")
            return [{"error": "Não foram encontrados resultados na busca inicial com a Tavily."}]

        for result_idx, result in enumerate(search_results):
            if leads_attempted_to_process >= max_search_results_to_process:
                print(f"--- DEBUG (find_and_extract_structured_leads): Limite de {max_search_results_to_process} tentativas de processamento atingido. Parando loop principal.")
                break
            leads_attempted_to_process += 1
            
            url_to_scrape = result.get('url')
            if url_to_scrape and url_to_scrape.startswith('http'):
                print(f"--- DEBUG (find_and_extract_structured_leads): [Attempt {leads_attempted_to_process}/{max_search_results_to_process}] Processing result {result_idx+1}/{len(search_results)}: {url_to_scrape} ---")

                if successfully_processed_leads >= max_search_results_to_process:
                    print(f"--- DEBUG (find_and_extract_structured_leads): Successfully processed {successfully_processed_leads} leads, which meets or exceeds max_search_results_to_process ({max_search_results_to_process}). Stopping. ---")
                    break

                print(f"--- DEBUG (find_and_extract_structured_leads): [Attempt {leads_attempted_to_process}/{max_search_results_to_process}] Calling web_scraper for {url_to_scrape} ---")
                scraped_data = web_scraper(url=url_to_scrape)
                print(f"--- DEBUG (find_and_extract_structured_leads): [Attempt {leads_attempted_to_process}/{max_search_results_to_process}] web_scraper returned for {url_to_scrape} ---")
                
                if not scraped_data.get('error') and scraped_data.get('content'):
                    full_content = scraped_data.get('content')
                    print(f"--- DEBUG (find_and_extract_structured_leads): [Attempt {leads_attempted_to_process}/{max_search_results_to_process}] Successfully scraped {len(full_content)} chars from {url_to_scrape}. ---")
                    
                    # 1. Extração com Regex (passagem inicial para padrões comuns)
                    emails = list(set(re.findall(email_regex, full_content)))
                    phones = list(set(re.findall(phone_regex, full_content)))
                    
                    # Tenta obter um site mais robusto do conteúdo raspado se diferente da URL
                    websites_found_in_content = list(set(re.findall(website_regex, full_content)))
                    primary_website_from_search = result.get('url') 
                    
                    # Heurística simples: prioriza o domínio encontrado no conteúdo ou a URL da busca
                    final_website = primary_website_from_search
                    if websites_found_in_content:
                        # Pega o primeiro site que parece mais completo
                        temp_website = max(websites_found_in_content, key=len) 
                        final_website = f"http://{temp_website}" if not temp_website.startswith('http') else temp_website


                    # 2. Extração com Gemini para dados mais complexos/nuançados
                    # Refined prompt_extract
                    prompt_extract = (
                        f"You are a data extraction specialist tasked with populating a lead database.\n"
                        f"Your task is to analyze the content of a web page and extract the following information about the company/organization described in the text. "
                        f"Respond EXCLUSIVELY with a valid JSON object. Do not include any explanatory text before or after the JSON.\n"
                        f"If specific information is not found in the text, the value of the corresponding field should be `null`.\n\n"
                        f"Expected JSON Schema:\n"
                        f"- `company_name`: (string) The official name of the company/organization.\n"
                        f"- `website`: (string) The main website of the company. If multiple are mentioned, choose the most relevant or the main domain.\n"
                        f"- `contact_emails`: (list of strings) A list of contact email addresses found. If none are found, use an empty list `[]`.\n"
                        f"- `contact_phones`: (list of strings) A list of contact phone numbers found. If none are found, use an empty list `[]`.\n"
                        f"- `industry`: (string) The company's industry sector (e.g., 'Technology', 'Healthcare', 'Consulting'). If not clear, use 'Not specified'.\n"
                        f"- `description`: (string) A brief summary of the company, its products/services, or mission. Maximum of 2-3 sentences.\n"
                        f"- `size`: (string) The estimated size of the company (e.g., 'Small Business (1-50 employees)', 'Medium Business (51-200 employees)', 'Large Business (201+ employees)', 'Not specified'). Infer if possible.\n\n"
                        f"Web Page Content for Analysis:\n\"\"\"\n{full_content[:MAX_GEMINI_INPUT_CHARS]}\n\"\"\"\n\n"
                        f"Important: Generate your entire response, including all textual content and string values within any JSON structure, strictly in the following language: {output_language}. Do not include any English text unless it is part of the original input data that should be preserved as is."
                    )
                    
                    gemini_extracted_data = {}
                    print(f"--- DEBUG (find_and_extract_structured_leads): [Attempt {leads_attempted_to_process}/{max_search_results_to_process}] Calling Gemini's model.generate_content for {url_to_scrape} ---")
                    try:
                        response = model.generate_content(prompt_extract)
                        print(f"--- DEBUG (find_and_extract_structured_leads): [Attempt {leads_attempted_to_process}/{max_search_results_to_process}] Gemini's model.generate_content returned for {url_to_scrape} ---")
                        # Remove markdown code block if present
                        json_str = response.text.strip().replace('```json\n', '').replace('\n```', '')
                        gemini_extracted_data = json.loads(json_str)
                    except json.JSONDecodeError as jde:
                        print(f"--- DEBUG (find_and_extract_structured_leads): [Attempt {leads_attempted_to_process}/{max_search_results_to_process}] Error decoding JSON from Gemini for {url_to_scrape}: {jde}. Raw response: {response.text[:200]}..." )
                    except Exception as gemini_err:
                        print(f"--- DEBUG (find_and_extract_structured_leads): [Attempt {leads_attempted_to_process}/{max_search_results_to_process}] Error in Gemini call for {url_to_scrape}: {gemini_err} ---")
                    
                    # Combina resultados de Regex e Gemini, priorizando Gemini e enriquecendo
                    final_emails = list(set((gemini_extracted_data.get('contact_emails') or []) + emails))
                    final_phones = list(set((gemini_extracted_data.get('contact_phones') or []) + phones))
                    
                    # Atualiza o site se o Gemini encontrou um melhor
                    if gemini_extracted_data.get('website'):
                        final_website = gemini_extracted_data['website']

                    lead_data = {
                        "company_name": gemini_extracted_data.get('company_name', result.get('title', 'N/A')),
                        "website": final_website,
                        "contact_emails": final_emails,
                        "contact_phones": final_phones,
                        "industry": gemini_extracted_data.get('industry', 'N/A'),
                        "description": gemini_extracted_data.get('description', 'N/A'),
                        "size": gemini_extracted_data.get('size', 'N/A'),
                        "source_url": url_to_scrape,
                        "search_snippet": result.get('snippet', 'N/A')
                    }
                    extracted_leads.append(lead_data)
                    successfully_processed_leads += 1

                    if successfully_processed_leads >= max_search_results_to_process:
                        print(f"--- DEBUG (find_and_extract_structured_leads): [Attempt {leads_attempted_to_process}/{max_search_results_to_process}] Successfully processed leads limit ({max_search_results_to_process}) reached after processing a lead from {url_to_scrape}. ---")
                        # This break will exit the inner loop for results from the current URL.
                        # The outer loop condition `if successfully_processed_leads >= max_search_results_to_process:` will then break the main loop.

                    time.sleep(DELAY_BETWEEN_GEMINI_CALLS_SECONDS)  # Pause to manage rate limits
                else:
                    print(f"--- DEBUG (find_and_extract_structured_leads): [Attempt {leads_attempted_to_process}/{max_search_results_to_process}] Failed to scrape '{url_to_scrape}': {scraped_data.get('error', 'Empty content/unknown error')} ---")
            else:
                print(f"--- DEBUG (find_and_extract_structured_leads): [Attempt {leads_attempted_to_process}/{max_search_results_to_process}] Invalid or empty URL, skipping: '{url_to_scrape}' ---")
            
            if successfully_processed_leads >= max_search_results_to_process: # Check after processing each URL's results
                 print(f"--- DEBUG (find_and_extract_structured_leads): Successfully processed leads limit ({max_search_results_to_process}) reached within the outer loop for URL {url_to_scrape}. Stopping. ---")
                 break

        print(f"--- DEBUG (find_and_extract_structured_leads): Finished. Extracted {len(extracted_leads)} leads after attempting to process {leads_attempted_to_process} search results. ---")
        return extracted_leads

    except ValueError as ve:
        print(f"--- DEBUG (find_and_extract_structured_leads): API configuration error: {ve} ---")
        return [{"error": f"API configuration error: {ve}"}]
    except Exception as e:
        print(f"--- DEBUG (find_and_extract_structured_leads): An unexpected error occurred in the composite tool: {e} ---")
        return [{"error": f"An unexpected error occurred in the composite tool: {e}"}]


def process_provided_urls_for_leads(urls: List[str], lead_analysis_instruction: str, output_language: str = "en-US") -> List[Dict[str, Any]]:
    """
    Scrapes content from a list of user-provided URLs and uses Google Gemini to analyze and extract
    structured lead information. Includes rate limiting.

    Args:
        urls: A list of URLs to be processed.
        lead_analysis_instruction: A prompt/instruction for Gemini to apply to each scraped text for lead extraction.
        output_language: The desired language for the LLM response (e.g., "en-US", "pt-BR").

    Returns:
        A list of dictionaries, where each dictionary contains structured lead data for a URL.
        Returns an empty list if no leads are found or if an error occurs.
    """
    print(f"--- DEBUG (process_provided_urls_for_leads): Processing {len(urls)} URLs, output_language='{output_language}'. ---")
    
    # Refined default_lead_analysis_instruction (now in English)
    default_lead_analysis_instruction = (
        "You are a data extraction specialist tasked with analyzing content from provided URLs.\n"
        "Your task is to analyze the content of a web page and extract lead information. "
        "Respond EXCLUSIVELY with a valid JSON object. Do not include any explanatory text before or after the JSON.\n"
        "If specific information is not found in the text, the value of the corresponding field should be `null`.\n\n"
        "Expected JSON Schema:\n"
        "- `company_name`: (string) The official name of the company/organization.\n"
        "- `website`: (string) The main website of the company. If multiple are mentioned, choose the most relevant or the main domain. If the analyzed URL is the site, use it.\n"
        "- `contact_emails`: (list of strings) A list of contact email addresses found. If none are found, use an empty list `[]`.\n"
        "- `contact_phones`: (list of strings) A list of contact phone numbers found. If none are found, use an empty list `[]`.\n"
        "- `industry`: (string) The company's industry sector (e.g., 'Technology', 'Healthcare', 'Consulting'). If not clear, use 'Not specified'.\n"
        "- `description`: (string) A brief summary of the company, its products/services, or mission. Maximum of 2-3 sentences.\n"
        "- `size`: (string) The estimated size of the company (e.g., 'Small Business (1-50 employees)', 'Medium Business (51-200 employees)', 'Large Business (201+ employees)', 'Not specified'). Infer if possible.\n"
    )

    current_analysis_instruction = lead_analysis_instruction if lead_analysis_instruction is not None else default_lead_analysis_instruction
    
    results = []
    try:
        model = _initialize_gemini_model()
        for i, url in enumerate(urls):
            item_result: Dict[str, Any] = {
                "url": url,
                "title": "N/A",
                "lead_data": {},
                "error": None
            }
            
            try:
                scraped_data = web_scraper(url)
                if scraped_data.get("error"):
                    item_result["error"] = f"Falha ao raspar: {scraped_data['error']}"
                    results.append(item_result)
                    continue
                
                content = scraped_data.get("content", "")
                item_result["title"] = scraped_data.get("title", "No Title Found")

                full_prompt = (
                    f"{current_analysis_instruction}\n\n"
                    f"Web Page Content for Analysis:\n\"\"\"\n{content[:MAX_GEMINI_INPUT_CHARS]}\n\"\"\"\n\n"
                    f"Important: Generate your entire response, including all textual content and string values within any JSON structure, strictly in the following language: {output_language}. Do not include any English text unless it is part of the original input data that should be preserved as is."
                )
                
                response = model.generate_content(full_prompt)
                json_str = response.text.strip().replace('```json\n', '').replace('\n```', '')
                item_result["lead_data"] = json.loads(json_str)

            except json.JSONDecodeError as jde:
                item_result["error"] = f"Error decoding JSON from Gemini analysis for {url}: {jde}. Raw response: {response.text[:200]}..."
            except Exception as e:
                item_result["error"] = f"Error processing URL {url}: {e}"
            
            results.append(item_result)
            
            if i < len(urls) - 1:
                time.sleep(DELAY_BETWEEN_GEMINI_CALLS_SECONDS)  # Pause to manage rate limits
                
        print(f"--- DEBUG (process_provided_urls_for_leads): Returning {len(results)} processed results. ---")
        return results
    except ValueError as ve:
        print(f"--- DEBUG (process_provided_urls_for_leads): API configuration error: {ve} ---")
        return [{"error": f"API configuration error: {ve}"}]
    except Exception as e:
        print(f"--- DEBUG (process_provided_urls_for_leads): An unexpected error occurred in the composite tool: {e} ---")
        return [{"error": f"An unexpected error occurred in the composite tool: {e}"}]


# --- AGENTS (Adapted for Lead Generation) ---
# Note for ADK Agents: The `output_language` parameter needs to be handled by the calling code.
# The caller (e.g., pipeline_orchestrator.py) should append the language instruction to the
# agent's base instruction when preparing the `Content` object for the `Runner`.
# Example: final_instruction = agent.instruction + "\n\n" + language_instruction_string.format(output_language=desired_lang)

# NEW AGENT: Entry point that transforms business context into a search query.
business_context_to_query_agent = Agent(
    name="business_context_to_query_agent",
    model="gemini-1.5-flash-8b",
    description="""You are a marketing and prospecting expert. Your role is to analyze a rich business context from a client and distill this information into a short, effective search query to find leads.""",
    instruction="""As a marketing and prospecting expert, your task is to analyze the provided 'business_context' JSON object.
This object contains details about a client's business, including description, target audience, industry, and location.
Based on a thorough analysis of these details, your mission is to create a SINGLE, highly optimized search query string.
This query will be used to find relevant B2B (business-to-business) leads in search engines.

Criteria for the Query:
1.  **B2B Relevance**: Focused on finding other businesses, not end consumers.
2.  **Concise and Focused**: Use essential keywords. Avoid long sentences or questions.
3.  **Practical Terms**: Think of terms that target companies would use to describe themselves or that decision-makers would use to find solutions.
4.  **Impact**: The query should be effective in identifying potential customers.

Response Format:
YOUR FINAL RESPONSE MUST BE ONLY THE GENERATED SEARCH STRING, WITHOUT ANY ADDITIONAL TEXT, GREETINGS, OR EXPLANATIONS.

Example Business Context (input you will receive):
```json
{
  "business_description": "We offer an AI-based CRM software to optimize the sales funnel for small and medium-sized teams.",
  "industry_focus": ["SaaS", "Technology", "Sales"],
  "target_market": "Small and medium-sized businesses in Brazil looking to improve customer relationship management.",
  "location": "Brazil",
  "value_proposition": "We increase sales efficiency by up to 30% with intelligent automation.",
  "pain_points_solved": ["Low lead conversion", "Difficulty in customer follow-up"]
}
```

Example of Your Response (what you should generate):
"SaaS SMB Brazil CRM sales funnel optimization"
""",
# Note: The language instruction for this agent's LLM call needs to be appended by the caller.
    tools=[]
)


# This agent is the initial entry point for refining the user's query.
# It is exposed as 'root_agent' to match its request in __init__.py.
_query_refiner_agent_internal = Agent(
    name="query_refiner_agent",
    model="gemini-1.5-flash",
    description="""Simple keyword repeater and extractor.""",
    instruction="""You are an ultra-simplified text processing assistant.
Your sole function is to extract and repeat the key terms (keywords) from any input text.
DO NOT add any words, explanations, or formatting. Only the key terms.

If the input looks like a list of keywords, repeat them.
If the input is a sentence, extract the main nouns and technical terms.

Examples:

Input: AI consulting Brazil small companies
Output: AI consulting Brazil small companies

Input: technology software for manufacturing companies
Output: technology software manufacturing companies

Input: advanced digital marketing
Output: advanced digital marketing

Input: http://example.com
Output: http://example.com

Input: (empty)
Output: (empty)

Input: Hello, how are you?
Output: Hello

YOUR RESPONSE MUST CONTAIN ONLY THE PROCESSED TERMS.
""",
# Note: The language instruction for this agent's LLM call needs to be appended by the caller.
    tools=[]
)
# Alias to match the desired import in __init__.py
root_agent = _query_refiner_agent_internal


lead_search_and_qualify_agent = Agent(
    name="lead_search_and_qualify_agent",
    model="gemini-1.5-flash-8b",
    description="""You are an agent specialized in searching for potential leads on the web using EXACTLY the query provided by the user. You MUST NOT modify, interpret, or alter the search query in any way.""",
    instruction="""YOU ARE A LEAD SEARCH AND QUALIFICATION AGENT. YOUR FUNCTION IS EXCLUSIVELY OPERATIONAL.

CRITICAL AND MANDATORY INSTRUCTIONS:
1.  You will receive a search query from the user.
2.  Use EXACTLY this query, without any modification, interpretation, translation, or alteration.
3.  Your ONLY action is to invoke the `search_and_qualify_leads` tool.
4.  When calling `search_and_qualify_leads`, pass the EXACT query you received.
5.  Use the parameter `max_search_results_to_scrape` with the value `3` for this call. Do not use another value.
6.  After the tool is executed, return the tool's output DIRECTLY, without adding any text, comments, or formatting.
7.  The `output_language` for the tool call should be inferred from the overall request context if available, otherwise default to "en-US".
    (Caller should ideally pass `output_language` to the tool via params if the ADK framework supports it, or it's embedded in a richer user query).

EXAMPLE OF EXPECTED BEHAVIOR:
If the User Input is: "growing technology startups in Brazil"

Your Action MUST BE the tool call:
`search_and_qualify_leads(query="growing technology startups in Brazil", max_search_results_to_scrape=3, output_language="en-US")`
(Assuming "en-US" is the determined language. This part of the instruction might be hard for the LLM to act upon without explicit `output_language` in its input. The caller will need to manage this.)

REMEMBER: DO NOT alter the query. If the query is "X companies", use "X companies". Do not change to "Y agency" or anything else. Fidelity to the original query is crucial.
Your response should be only the tool call or its result.
""",
# Note: The language instruction for this agent's own LLM call (if it had one beyond tool use)
# would need to be appended by the caller. The `output_language` for the *tool* it calls
# should ideally be passed dynamically if the ADK framework allows it.
    tools=[search_and_qualify_leads]
)


structured_lead_extractor_agent = Agent(
    name="structured_lead_extractor_agent",
    model="gemini-1.5-flash-8b",
    description="""You are an agent highly specialized in extracting structured lead data from web content. Your function is to find detailed information such as company name, website, contact emails, phones, industry, and size, and present it in a standardized format.""",
    instruction="""YOU ARE A STRUCTURED LEAD DATA EXTRACTOR AGENT. YOUR FUNCTION IS EXCLUSIVELY OPERATIONAL.

CRITICAL AND MANDATORY INSTRUCTIONS:
1.  You will receive a search query from the user.
2.  Your ONLY action is to invoke the `find_and_extract_structured_leads` tool.
3.  When calling `find_and_extract_structured_leads`, pass the EXACT query you received. Do not modify or interpret the query.
4.  Use the parameter `max_search_results_to_process` with the value `3`. Do not use another value.
5.  After the tool is executed, return the tool's output DIRECTLY, without adding any text, comments, or formatting.
6.  The `output_language` for the tool call should be inferred from the overall request context if available, otherwise default to "en-US".
    (Caller should ideally pass `output_language` to the tool via params if the ADK framework supports it.)

EXAMPLE OF EXPECTED BEHAVIOR:
If the User Input is: "contact details of software companies in Curitiba"

Your Action MUST BE the tool call:
`find_and_extract_structured_leads(query="contact details of software companies in Curitiba", max_search_results_to_process=3, output_language="en-US")`
(Assuming "en-US" is the determined language. Caller needs to manage this for the tool.)

Your response should be only the tool call or its result.
""",
# Note: The language instruction for this agent's own LLM call (if it had one beyond tool use)
# would need to be appended by the caller. The `output_language` for the *tool* it calls
# should ideally be passed dynamically if the ADK framework allows it.
    tools=[find_and_extract_structured_leads]
)


direct_url_lead_processor_agent = Agent(
    name="direct_url_lead_processor_agent",
    model="gemini-1.5-flash-8b",
    description="""You are an agent specialized in directly processing a list of URLs provided by the user to extract lead information. For each URL, you will scrape the content and use Google Gemini to analyze and extract lead data, managing API call rates.""",
    instruction="""YOU ARE A URL PROCESSOR AGENT FOR LEAD EXTRACTION. YOUR FUNCTION IS EXCLUSIVELY OPERATIONAL.

CRITICAL AND MANDATORY INSTRUCTIONS:
1.  You will receive a query from the user, which may contain one or more URLs.
2.  Your FIRST task is to identify and extract ALL valid URLs (starting with http:// or https://) from the provided query. Ignore any other text.
3.  If no valid URLs are found, you may return a message indicating this (e.g., "No valid URLs found in the query.").
4.  If valid URLs are found, your SECOND and ONLY subsequent action is to invoke the `process_provided_urls_for_leads` tool.
5.  When calling `process_provided_urls_for_leads`:
    a.  Pass the list of extracted URLs as the `urls` parameter.
    b.  Do not provide the `lead_analysis_instruction` parameter; the tool will use a suitable default instruction.
    c.  The `output_language` for the tool call should be inferred from the overall request context if available, otherwise default to "en-US".
        (Caller should ideally pass `output_language` to the tool via params if the ADK framework supports it.)
6.  After the tool is executed, return the tool's output DIRECTLY, without adding any text, comments, or formatting.

EXAMPLE OF EXPECTED BEHAVIOR:
If the User Input is: "Please analyze https://example.com/about and also www.another.org/contact"

Your Action MUST BE the tool call:
`process_provided_urls_for_leads(urls=["https://example.com/about", "https://www.another.org/contact"], output_language="en-US")`
(Assuming "en-US" is the determined language. Caller needs to manage this for the tool.)

If the User Input is: "No URL here, just text."
Your Response could be: "No valid URLs found in the query."

Your response should be only the tool call or its result, or the message about no URLs found.
""",
# Note: The language instruction for this agent's own LLM call (if it had one beyond tool use)
# would need to be appended by the caller. The `output_language` for the *tool* it calls
# should ideally be passed dynamically if the ADK framework allows it.
    tools=[process_provided_urls_for_leads]
)