# adk1/agent.py

import os
import re
import time
import json
from typing import List, Dict, Any, Union
from datetime import datetime

import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from tavily import TavilyClient
from google.adk.agents import Agent
from dotenv import load_dotenv

load_dotenv()

# --- Configurações Globais ---
DELAY_BETWEEN_GEMINI_CALLS_SECONDS = 5
MAX_GEMINI_INPUT_CHARS = 50000
MAX_SCRAPE_RESULTS = 5 # Ainda raspamos até 5 páginas para análise profunda
TAVILY_INITIAL_SEARCH_RESULTS = 15 # Aumentado para buscar mais resultados iniciais do Tavily

DISABLE_SSL_VERIFICATION = False # <-- Altere para False para desativar a verificação SSL em ambiente de desenvolvimento/teste

# --- Funções Auxiliares ---
def web_scraper(url: str) -> dict:
    try:
        cleaned_url = url.strip().replace('\t', '').replace('\n', '').replace('\r', '')
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(cleaned_url, headers=headers, timeout=10, verify=not DISABLE_SSL_VERIFICATION)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string if soup.title else 'No Title Found'
        for script_or_style in soup(['script', 'style']):
            script_or_style.extract()
        text_content = soup.get_text(separator=' ', strip=True)
        return {"title": title, "url": url, "content": text_content}
    except requests.exceptions.RequestException as e:
        return {"error": f"Falha ao buscar conteúdo de {url} (limpa para '{cleaned_url}'): {e}"}
    except Exception as e:
        return {"error": f"Um erro inesperado ocorreu ao raspar {url} (limpa para '{cleaned_url}'): {e}"}


def _tavily_search_internal(query: str, max_results: int = TAVILY_INITIAL_SEARCH_RESULTS) -> List[Dict]:
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not tavily_api_key:
        raise ValueError("TAVILY_API_KEY não está configurada nas variáveis de ambiente.")
    try:
        tavily = TavilyClient(api_key=tavily_api_key)
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
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY não está configurada nas variáveis de ambiente.")
    genai.configure(api_key=google_api_key)
    return genai.GenerativeModel("gemini-1.5-flash")


# --- FERRAMENTAS COMPOSITAS (Modificadas para Melhorar a Qualidade e Contexto de Negócio) ---

def search_and_qualify_leads(query: str, max_search_results_to_scrape: int = MAX_SCRAPE_RESULTS) -> List[Dict[str, Any]]:
    """
    Realiza uma busca web por potenciais leads, raspa o conteúdo e faz uma qualificação inicial
    usando o Gemini, retornando o conteúdo raspado com um resumo de qualificação e tipo de entidade mais granular.
    Foca em identificar leads diretos vs. fontes indiretas (diretórios, artigos).

    Args:
        query: A string da query de busca para encontrar leads.
        max_search_results_to_scrape: Número máximo de resultados de busca (do Tavily) a serem raspados e qualificados.

    Returns:
        Uma lista de dicionários, cada um contendo:
        - 'title': Título da página.
        - 'url': URL original.
        - 'snippet': Trecho da busca.
        - 'full_content': Conteúdo raspado.
        - 'entity_type': Tipo de entidade (e.g., "Direct Company Lead", "Directory/List", "Informational Article", "Other").
        - 'company_name': Nome da empresa, se aplicável.
        - 'business_focus_summary': Breve descrição do foco de negócio da empresa, se for uma empresa.
        - 'match_score': Pontuação (0-100) indicando o quão bem a entidade da página se alinha com a intenção da query (se é um lead direto).
        - 'relevance_rationale': Justificativa da avaliação de relevância.
        - 'error': Se algum erro ocorreu durante a raspagem ou qualificação.
    """
    print(f"--- DEBUG (search_and_qualify_leads): Chamado com query: '{query}' e max_results_to_scrape: {max_search_results_to_scrape} ---")
    try:
        model = _initialize_gemini_model()
        # Busca mais resultados do que será raspado para ter uma margem para filtrar
        search_results = _tavily_search_internal(query=query, max_results=TAVILY_INITIAL_SEARCH_RESULTS) 

        if not search_results:
            print("--- DEBUG (search_and_qualify_leads): Nenhuns resultados da busca Tavily. ---")
            return [{"error": "Não foram encontrados resultados na busca inicial com a Tavily."}]

        qualified_leads_data = []
        count_scraped = 0

        for result in search_results:
            if count_scraped >= max_search_results_to_scrape:
                break # Limita o número de páginas raspadas

            url_to_scrape = result.get('url')
            # NOVA LÓGICA: Pular resultados de diretórios conhecidos logo no início para focar em leads diretos
            # Mantemos Econodata na lista pois pode ser uma fonte para o structured_lead_extractor_agent se ele for chamado
            # Mas para QUALIFICAÇÃO INICIAL de lead DIRETO, queremos evitar.
            # O agente lead_search_and_qualify_agent será instruído a lidar com "Directory/List"
            # mas queremos que a ferramenta tente focar em sites de empresas.
            
            # Ajuste: A filtragem mais agressiva deve ser nas INSTRUÇÕES do AGENTE, não na FERRAMENTA.
            # A ferramenta deve fornecer a categorização, e o agente decide o que exibir.
            # Por exemplo, se a query for "empresas de IA em SP", não queremos diretórios como leads diretos.
            # Mas se a query for "listas de empresas de IA em SP", queremos diretórios.
            # A responsabilidade da ferramenta é *categorizar*. A responsabilidade do agente é *filtrar/apresentar*.

            if url_to_scrape and url_to_scrape.startswith('http'):
                print(f"--- DEBUG (search_and_qualify_leads): Tentando raspar URL: '{url_to_scrape}' ---")
                scraped_data = web_scraper(url=url_to_scrape)

                if not scraped_data.get('error') and scraped_data.get('content'):
                    full_content = scraped_data.get('content')
                    
                    # PROMPT MELHORADO para qualificação mais granular e foco no contexto de negócio
                    prompt_qualify = (
                        f"Analise o seguinte conteúdo da página web: {url_to_scrape}. A query de busca original foi '{query}'. "
                        f"Sua tarefa é:\n"
                        f"1. Identificar a principal entidade da página.\n"
                        f"2. Categorizá-la de forma precisa como um de:\n"
                        f"   - 'Direct Company Lead': Se a página é o site oficial de uma empresa diretamente relevante para a query. Esta é a categoria de maior valor.\n"
                        f"   - 'Directory/List': Se a página é um diretório, uma lista de empresas, ou um agregador de dados de empresas (ex: Econodata, Telelistas).\n"
                        f"   - 'Informational Article': Se a página é um artigo de notícia, blog, conteúdo educacional ou um perfil em rede social genérica (ex: LinkedIn de funcionário, não da empresa).\n"
                        f"   - 'Other': Para qualquer outro tipo que não se encaixe e não seja um lead.\n"
                        f"3. Se for 'Direct Company Lead', extraia o nome da empresa e uma breve descrição do seu foco de negócio, incluindo mercado-alvo, proposta de valor, cliente ideal, pontos de dor que resolve, e foco da indústria. Tente extrair esses detalhes diretamente do texto.\n"
                        f"4. Atribua uma pontuação 'match_score' de 0 a 100, indicando o quão bem a *entidade principal* da página se alinha com a intenção de um 'lead direto de empresa' para a query '{query}'. Pontuações mais altas significam um match mais direto com o site de uma empresa relevante, não um diretório ou artigo.\n"
                        f"5. Forneça uma 'relevance_rationale' concisa justificando sua avaliação, a pontuação e o tipo de entidade, e se a URL é o site oficial da empresa.\n"
                        f"Responda APENAS com um objeto JSON válido no formato:\n"
                        f"{{\n"
                        f"  \"entity_type\": \"Direct Company Lead\" | \"Directory/List\" | \"Informational Article\" | \"Other\",\n"
                        f"  \"company_name\": \"Nome da Empresa\" | null,\n"
                        f"  \"business_focus_summary\": \"Breve descrição do foco de negócio da empresa, incluindo mercado-alvo e proposta de valor.\" | null,\n"
                        f"  \"match_score\": (int, 0-100),\n"
                        f"  \"relevance_rationale\": \"Justificativa da avaliação de relevância e pontuação.\"\n"
                        f"}}\n\n"
                        f"Conteúdo:\n{full_content[:MAX_GEMINI_INPUT_CHARS]}"
                    )
                    
                    qualification_output = {}
                    try:
                        gemini_response = model.generate_content(prompt_qualify)
                        json_str = gemini_response.text.strip().replace('```json\n', '').replace('\n```', '')
                        qualification_output = json.loads(json_str)
                    except json.JSONDecodeError as jde:
                        print(f"--- DEBUG (search_and_qualify_leads): Erro ao decodificar JSON de qualificação para {url_to_scrape}: {jde}. Resposta bruta: {gemini_response.text[:200]}..." )
                        qualification_output = {
                            "entity_type": "Error", "company_name": None, "business_focus_summary": None, "match_score": 0,
                            "relevance_rationale": f"Erro na qualificação JSON: {jde}. Conteúdo original: {full_content[:200]}..."
                        }
                    except Exception as gemini_err:
                        print(f"--- DEBUG (search_and_qualify_leads): Erro na chamada Gemini para qualificação {url_to_scrape}: {gemini_err}. ---")
                        qualification_output = {
                            "entity_type": "Error", "company_name": None, "business_focus_summary": None, "match_score": 0,
                            "relevance_rationale": f"Erro na chamada Gemini: {gemini_err}. Conteúdo original: {full_content[:200]}..."
                        }

                    qualified_leads_data.append({
                        "title": result.get('title'),
                        "url": url_to_scrape,
                        "snippet": result.get('snippet'),
                        "full_content": full_content,
                        **qualification_output
                    })
                    count_scraped += 1
                    time.sleep(DELAY_BETWEEN_GEMINI_CALLS_SECONDS)
                else:
                    print(f"--- DEBUG (search_and_qualify_leads): Falha ao raspar '{url_to_scrape}': {scraped_data.get('error', 'Conteúdo vazio/desconhecido')} ---")
            else:
                print(f"--- DEBUG (search_and_qualify_leads): URL inválida ou vazia, pulando: '{url_to_scrape}' ---")
            
        print(f"--- DEBUG (search_and_qualify_leads): Retornando {len(qualified_leads_data)} resultados qualificados. ---")
        return qualified_leads_data
    except ValueError as ve:
        print(f"--- DEBUG (search_and_qualify_leads): Erro de configuração da API: {ve} ---")
        return [{"error": f"Erro de configuração da API: {ve}"}]
    except Exception as e:
        print(f"--- DEBUG (search_and_qualify_leads): Um erro inesperado ocorreu na ferramenta composta: {e} ---")
        return [{"error": f"Um erro inesperado ocorreu na ferramenta composta: {e}"}]


def find_and_extract_structured_leads(query: str, max_search_results_to_process: int = MAX_SCRAPE_RESULTS) -> List[Dict[str, Any]]:
    """
    Realiza uma busca profunda por leads, raspa o conteúdo e extrai informações estruturadas de leads
    usando Regex e Gemini, incluindo detalhes de negócio, com foco em qualidade.

    Args:
        query: A string da query de busca para encontrar leads.
        max_search_results_to_process: O número máximo de resultados de busca a serem raspados e analisados.

    Returns:
        Uma lista de dicionários, onde cada dicionário representa um lead estruturado.
        Retorna uma lista vazia se nenhum lead for encontrado ou se ocorrer um erro.
    """
    print(f"--- DEBUG (find_and_extract_structured_leads): Chamado com query: '{query}' e max_results: {max_search_results_to_process} ---")
    
    email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    phone_regex = r'\b(?:\+?\d{1,3}\s?)?(?:\(?\d{2}\)?\s?)?\d{4,5}[-\s]?\d{4}\b'
    website_regex = r'(?:https?:\/\/)?(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\.[a-zA-Z]{2,})(?:\/\S*)?'

    extracted_leads = []
    try:
        model = _initialize_gemini_model()
        search_results = _tavily_search_internal(query=query, max_results=TAVILY_INITIAL_SEARCH_RESULTS)

        if not search_results:
            print("--- DEBUG (find_and_extract_structured_leads): Nenhuns resultados da busca Tavily. ---")
            return [{"error": "Não foram encontrados resultados na busca inicial com a Tavily."}]

        count_processed = 0
        for result in search_results:
            if count_processed >= max_search_results_to_process:
                break
            
            url_to_scrape = result.get('url')
            # Filtro agressivo aqui também para garantir que tentamos extrair de sites de empresas, não de diretórios
            # Se o usuário pediu "e-mails de empresas X", um diretório só dará a lista, não os e-mails específicos.
            if any(domain in url_to_scrape for domain in ["econodata.com.br", "empresascnpj.com", "telelistas.net", "listasdeempresas.com.br"]):
                print(f"--- DEBUG (find_and_extract_structured_leads): Pulando URL de diretório conhecido: '{url_to_scrape}' para extração estruturada ---")
                continue

            if url_to_scrape and url_to_scrape.startswith('http'):
                print(f"--- DEBUG (find_and_extract_structured_leads): Tentando raspar URL: '{url_to_scrape}' ---")
                scraped_data = web_scraper(url=url_to_scrape)
                
                if not scraped_data.get('error') and scraped_data.get('content'):
                    full_content = scraped_data.get('content')
                    
                    emails = list(set(re.findall(email_regex, full_content)))
                    phones = list(set(re.findall(phone_regex, full_content)))
                    
                    websites_found_in_content = list(set(re.findall(website_regex, full_content)))
                    primary_website_from_search = result.get('url') 
                    
                    final_website = primary_website_from_search
                    if websites_found_in_content:
                        temp_website = max(websites_found_in_content, key=len) 
                        final_website = f"http://{temp_website}" if not temp_website.startswith('http') else temp_website


                    # PROMPT MELHORADO para extração estruturada detalhada - Garante todos os campos
                    prompt_extract = (
                        f"Extraia as seguintes informações sobre a empresa/organização deste texto. "
                        f"Responda APENAS com um objeto JSON válido. Se uma informação não for encontrada, use null ou lista vazia para listas. "
                        f"Os campos devem ser:\n"
                        f"  \"company_name\": (string) Nome completo da empresa.\n"
                        f"  \"website\": (string) URL do site principal da empresa (pode ser a URL raspada se for o site da empresa).\n"
                        f"  \"contact_emails\": (lista de strings) E-mails de contato encontrados.\n"
                        f"  \"contact_phones\": (lista de strings) Números de telefone encontrados (formato com DDD, ex: +55XXYYYYZZZZ).\n"
                        f"  \"industry\": (string) Setor da indústria da empresa (ex: 'Tecnologia', 'Saúde', 'Distribuição').\n"
                        f"  \"description\": (string) Breve resumo geral da empresa.\n"
                        f"  \"size\": (string) Tamanho da empresa (ex: '1-10 funcionários', 'PME', 'Grande Empresa', 'Não informado').\n"
                        f"  \"location\": (string) Endereço completo, ou cidade/estado de localização da empresa.\n"
                        f"  \"business_description\": (string) Detalhes sobre o que a empresa faz, seus produtos/serviços e modelo de negócio (aprofundado).\n"
                        f"  \"target_market\": (string) Quem são os clientes-alvo da empresa (ex: 'PMEs no setor de varejo', 'grandes corporações', 'consumidores finais').\n"
                        f"  \"value_proposition\": (string) O valor único que a empresa oferece aos clientes, o que a diferencia de concorrentes.\n"
                        f"  \"ideal_customer\": (string) Descrição detalhada do perfil do cliente ideal (ICP), incluindo características demográficas/firmográficas e desafios que enfrentam.\n"
                        f"  \"pain_points\": (string) Quais problemas específicos a empresa resolve para seus clientes (os 'pontos de dor').\n"
                        f"  \"industry_focus\": (string) Foco específico ou nicho dentro da indústria (ex: 'Fintech para startups', 'SaaS de CRM para PMEs').\n"
                        f"  \"source_url\": (string) A URL de onde os dados foram extraídos.\n"
                        f"  \"search_snippet\": (string) O trecho da busca original que levou a esta URL.\n"
                        f"\nConteúdo:\n{full_content[:MAX_GEMINI_INPUT_CHARS]}"
                    )
                    
                    gemini_extracted_data = {}
                    try:
                        response = model.generate_content(prompt_extract)
                        json_str = response.text.strip().replace('```json\n', '').replace('\n```', '')
                        gemini_extracted_data = json.loads(json_str)
                    except json.JSONDecodeError as jde:
                        print(f"--- DEBUG (find_and_extract_structured_leads): Erro ao decodificar JSON do Gemini para {url_to_scrape}: {jde}. Resposta bruta: {response.text[:200]}..." )
                    except Exception as gemini_err:
                        print(f"--- DEBUG (find_and_extract_structured_leads): Erro na chamada Gemini para {url_to_scrape}: {gemini_err} ---")
                    
                    # Combina resultados de Regex e Gemini
                    final_emails = list(set((gemini_extracted_data.get('contact_emails') or []) + emails))
                    final_phones = list(set((gemini_extracted_data.get('contact_phones') or []) + phones))
                    
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
                        "location": gemini_extracted_data.get('location', 'N/A'),
                        "business_description": gemini_extracted_data.get('business_description', 'N/A'),
                        "target_market": gemini_extracted_data.get('target_market', 'N/A'),
                        "value_proposition": gemini_extracted_data.get('value_proposition', 'N/A'),
                        "ideal_customer": gemini_extracted_data.get('ideal_customer', 'N/A'),
                        "pain_points": gemini_extracted_data.get('pain_points', 'N/A'),
                        "industry_focus": gemini_extracted_data.get('industry_focus', 'N/A'),
                        "source_url": url_to_scrape,
                        "search_snippet": result.get('snippet', 'N/A')
                    }
                    extracted_leads.append(lead_data)
                    count_processed += 1
                    time.sleep(DELAY_BETWEEN_GEMINI_CALLS_SECONDS)
                else:
                    print(f"--- DEBUG (find_and_extract_structured_leads): Falha ao raspar '{url_to_scrape}': {scraped_data.get('error', 'Conteúdo vazio/desconhecido')} ---")
            else:
                print(f"--- DEBUG (find_and_extract_structured_leads): URL inválida ou vazia, pulando: '{url_to_scrape}' ---")
            
        print(f"--- DEBUG (find_and_extract_structured_leads): Retornando {len(extracted_leads)} leads estruturados. ---")
        return extracted_leads

    except ValueError as ve:
        print(f"--- DEBUG (find_and_extract_structured_leads): Erro de configuração da API: {ve} ---")
        return [{"error": f"Erro de configuração da API: {ve}"}]
    except Exception as e:
        print(f"--- DEBUG (find_and_extract_structured_leads): Um erro inesperado ocorreu na ferramenta composta: {e} ---")
        return [{"error": f"Um erro inesperado ocorreu na ferramenta composta: {e}"}]


def process_provided_urls_for_leads(urls: List[str], lead_analysis_instruction: str = None) -> List[Dict[str, Any]]:
    """
    Raspa o conteúdo de uma lista de URLs fornecidas pelo usuário e usa o Google Gemini para analisar e extrair
    informações estruturadas de leads. Inclui limitação de taxa.

    Args:
        urls: Uma lista de URLs a serem processadas.
        lead_analysis_instruction: Um prompt/instrução para o Gemini aplicar a cada texto raspado para extração de leads.

    Returns:
        Uma lista de dicionários, onde cada dicionário contém dados de lead estruturados para uma URL.
        Retorna uma lista vazia se nenhum lead for encontrado ou se ocorrer um erro.
    """
    print(f"--- DEBUG (process_provided_urls_for_leads): Processando {len(urls)} URLs. ---")
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
                
                # Instrução padrão para o direct_url_lead_processor_agent
                if not lead_analysis_instruction:
                    lead_analysis_instruction = (
                        f"Analise este conteúdo para identificar e extrair informações de leads como nome da empresa, "
                        f"site, e-mails de contato e números de telefone, além de uma breve descrição de negócio, "
                        f"mercado-alvo, proposta de valor, cliente ideal e pontos de dor que a empresa resolve. "
                        f"Apresente como um objeto JSON com os campos: company_name, website, contact_emails (lista), "
                        f"contact_phones (lista), industry, description, size, location, business_description, "
                        f"target_market, value_proposition, ideal_customer, pain_points, industry_focus. "
                        f"Se uma informação não for encontrada, use null ou lista vazia para listas."
                    )

                full_prompt = f"{lead_analysis_instruction}\n\nConteúdo:\n{content[:MAX_GEMINI_INPUT_CHARS]}"
                
                response = model.generate_content(full_prompt)
                json_str = response.text.strip().replace('```json\n', '').replace('\n```', '')
                item_result["lead_data"] = json.loads(json_str)

            except json.JSONDecodeError as jde:
                item_result["error"] = f"Erro ao decodificar JSON da análise Gemini para {url}: {jde}. Resposta bruta: {response.text[:200]}..."
            except Exception as e:
                item_result["error"] = f"Erro no processamento da URL {url}: {e}"
            
            results.append(item_result)
            
            if i < len(urls) - 1:
                time.sleep(DELAY_BETWEEN_GEMINI_CALLS_SECONDS)
                
        print(f"--- DEBUG (process_provided_urls_for_leads): Retornando {len(results)} resultados processados. ---")
        return results
    except ValueError as ve:
        print(f"--- DEBUG (process_provided_urls_for_leads): Erro de configuração da API: {ve} ---")
        return [{"error": f"Erro de configuração da API: {ve}"}]
    except Exception as e:
        print(f"--- DEBUG (process_provided_urls_for_leads): Um erro inesperado ocorreu na ferramenta composta: {e} ---")
        return [{"error": f"Um erro inesperado ocorreu na ferramenta composta: {e}"}]


# --- AGENTES (Adaptados para Geração de Leads) ---

_query_refiner_agent_internal = Agent(
    name="query_refiner_agent",
    model="gemini-1.5-flash-8b", 
    description="""Você é um agente especialista em refinar e otimizar consultas de pesquisa em linguagem natural para torná-las mais eficazes em motores de busca para encontrar leads. Sua saída é APENAS a query refinada.""",
    instruction="""Sua tarefa é receber uma solicitação de busca em linguagem natural do usuário sobre leads.
    Analise a intenção e os termos chave.
    Reformule essa solicitação em uma query de busca concisa, com termos específicos e palavras-chave,
    adequada para ser usada diretamente em um motor de busca como Tavily.
    SUA RESPOSTA FINAL DEVE SER APENAS A QUERY REFINADA, SEM EXPLICAÇÕES, PREFÁCIOS OU PÓS-FÁCIOS.
    Não use ferramentas. Apenas gere a query refinada.

    Exemplo:
    Usuário: "Quero encontrar empresas de software em São Paulo que trabalham com inteligência artificial."
    Sua resposta: "empresas software São Paulo inteligência artificial"

    Usuário: "Preciso de contatos de clínicas de dermatologia no Rio de Janeiro."
    Sua resposta: "clínicas dermatologia Rio de Janeiro contatos"
    """,
    tools=[]
)
root_agent = _query_refiner_agent_internal


lead_search_and_qualify_agent = Agent(
    name="lead_search_and_qualify_agent",
    model="gemini-1.5-flash-8b", 
    description="""Você é um agente especializado em buscar potenciais leads na web e realizar uma qualificação inicial do seu potencial, com foco em qualidade e match com o contexto de negócio. Seu objetivo é identificar páginas e conteúdos que sejam leads diretos de empresas relevantes, distinguindo-os claramente de diretórios ou artigos.""",
    instruction="""Você é responsável por encontrar e qualificar leads.
    Seu processo de trabalho é o seguinte:

    1.  **Execução da Busca e Qualificação Inicial:**
        Utilize a ferramenta `search_and_qualify_leads` com a query de busca que você recebeu (já refinada). **Para evitar exceder o limite de tokens do modelo e otimizar o tempo, você DEVE limitar o número de resultados a serem raspados e qualificados para um máximo de 3 (três) ou 4 (quatro) resultados, passando o parâmetro `max_search_results_to_scrape` com este valor.** Esta ferramenta fará a busca na internet e raspará o conteúdo das páginas relevantes, retornando uma lista de objetos JSON para cada resultado processado, contendo `entity_type`, `company_name`, `business_focus_summary`, `match_score` (0-100), `relevance_rationale`, `url` e `title`.

    2.  **Análise e Agregação dos Resultados Qualificados (Foco na Qualidade e Business Context):**
        Para cada resultado retornado pela ferramenta `search_and_qualify_leads`, analise o `entity_type`, `company_name`, `url`, `match_score`, `relevance_rationale`, `title` e `business_focus_summary`.
        
        Crie três listas separadas para organizar os resultados: `direct_leads`, `useful_sources`, e `informational_articles`.

        **Critério de Filtragem Crucial:**
        - Se `entity_type` for "Direct Company Lead" E `match_score` for **maior ou igual a 70**: Adicione à lista `direct_leads`. Estes são os leads de maior qualidade.
        - Se `entity_type` for "Directory/List": Adicione à lista `useful_sources`.
        - Se `entity_type` for "Informational Article": Adicione à lista `informational_articles`.
        - Ignore resultados com `entity_type: "Other"` ou `entity_type: "Error"` ou `match_score` abaixo de 70 que não sejam "Directory/List" ou "Informational Article".

    3.  **Formatação da Resposta Final (Clara e Segmentada, Priorizando Leads Diretos):**
        Construa a resposta final para o usuário da seguinte forma:

        "Encontrei os seguintes potenciais leads e fontes de informação para sua solicitação:

        **Leads de Empresas Diretas:**"
        - Se `direct_leads` não estiver vazia, liste cada item com:
          - **Empresa:** [company_name]
          - **URL:** [url]
          - **Foco de Negócio:** [business_focus_summary]
          - **Qualificação:** [relevance_rationale] (mencione a pontuação se apropriado, ex: "match score [match_score]/100")
        - Se `direct_leads` estiver vazia, adicione: "Nenhum lead de empresa direta de alta qualidade foi encontrado nesta busca."

        "**Fontes/Diretórios Úteis:**"
        - Se `useful_sources` não estiver vazia, liste cada item com:
          - **Nome/Título:** [title]
          - **URL:** [url]
          - **Descrição:** [relevance_rationale] (explicar por que é útil, ex: "Este é um diretório que lista empresas de...").
        - Se `useful_sources` estiver vazia, adicione: "Nenhuma fonte ou diretório útil foi encontrado nesta busca."

        "**Artigos/Informações:**"
        - Se `informational_articles` não estiver vazia, liste cada item com:
          - **Título:** [title]
          - **URL:** [url]
          - **Tópico:** [relevance_rationale] (explicar o tópico e por que foi encontrado).
        - Se `informational_articles` estiver vazia, adicione: "Nenhum artigo ou conteúdo informativo relevante foi encontrado nesta busca."

        Adicione uma linha final como "Se precisar de mais detalhes sobre os leads diretos ou da extração de dados específicos (e-mail, telefone) para esses, me diga!"

        Garanta que todas as etapas sejam executadas sequencialmente e que os dados sejam processados de forma precisa em cada fase.""",
    tools=[search_and_qualify_leads]
)


structured_lead_extractor_agent = Agent(
    name="structured_lead_extractor_agent",
    model="gemini-1.5-flash-8b", 
    description="""Você é um agente altamente especializado na extração de dados estruturados de leads a partir de conteúdo web. Sua função é buscar informações detalhadas como nome da empresa, site, e-mails de contato, telefones, setor e tamanho, e apresentar em um formato padronizado, incluindo business_description, target_market, value_proposition, ideal_customer, pain_points e industry_focus.""",
    instruction="""Você é o ponto de entrada para extrair informações de leads em um formato estruturado.
    Seu processo de trabalho é o seguinte:

    1.  **Execução da Busca e Extração Estruturada:**
        Utilize a ferramenta `find_and_extract_structured_leads` com a query de busca que você recebeu. **Para otimizar o processamento, você DEVE limitar o número de resultados a serem processados para um máximo de 3 (três) ou 4 (quatro) resultados, passando o parâmetro `max_search_results_to_process` com este valor.** Esta ferramenta fará a busca na internet, raspará o conteúdo das páginas e tentará extrair informações detalhadas de leads usando uma combinação de Regex e inteligência do Gemini, retornando uma lista de objetos JSON completos.

    2.  **Formatação da Resposta Final:**
        Com a lista de leads estruturados retornada pela ferramenta `find_and_extract_structured_leads`:
        - Se leads forem encontrados, apresente-os claramente ao usuário. O formato ideal é uma lista de leads, onde cada lead é apresentado com seus campos detalhados (Nome da Empresa, Site, E-mails, Telefones, Setor, Descrição, etc., incluindo os novos campos como business_description, target_market, etc.).
        - Se a ferramenta retornar um erro ou uma lista vazia, informe o usuário educadamente sobre a falha e sugira reformular a busca ou verificar os critérios.

    Exemplo de resposta formatada com sucesso:
    "Encontrei os seguintes leads com informações estruturadas:
    - **Empresa:** [Nome da Empresa 1]
      **Site:** [Site 1]
      **E-mails:** [email1@empresa.com, email2@empresa.com]
      **Telefones:** [telefone1, telefone2]
      **Setor:** [Setor 1]
      **Localização:** [Cidade, Estado]
      **Descrição do Negócio:** [Business Description]
      **Mercado Alvo:** [Target Market]
      **Proposta de Valor:** [Value Proposition]
      **Cliente Ideal:** [Ideal Customer]
      **Pontos de Dor Resolvidos:** [Pain Points]
      **Foco da Indústria:** [Industry Focus]
      **Fonte:** [URL da fonte]
    - **Empresa:** [Nome da Empresa 2]
      ...
    Esses dados são ideais para exportação para um CRM ou planilha detalhada."

    Exemplo de resposta formatada sem sucesso:
    "Desculpe, não consegui extrair informações de leads estruturadas com base na sua solicitação. Por favor, tente refinar a query ou fornecer mais detalhes para a busca. [Mensagem de erro da ferramenta, se houver]"

    Garanta que todas as etapas sejam executadas sequencialmente e que os dados sejam processados de forma precisa em cada fase.""",
    tools=[find_and_extract_structured_leads]
)


direct_url_lead_processor_agent = Agent(
    name="direct_url_lead_processor_agent",
    model="gemini-1.5-flash-8b", 
    description="""Você é um agente especializado em processar diretamente uma lista de URLs fornecidas pelo usuário para extrair informações de leads, incluindo detalhes de negócio. Para cada URL, você raspará o conteúdo e usará o Google Gemini para analisar e extrair dados de leads, gerenciando a taxa de chamadas da API.""",
    instruction="""Você é o ponto de entrada para processamento de URLs para extração de leads.
    Seu processo de trabalho é o seguinte:

    1.  **Entendimento e Extração de URLs e Instrução de Análise:**
        Ao receber a solicitação do usuário, sua primeira tarefa é identificar e extrair *todas as URLs* presentes na mensagem.
        As URLs podem ser fornecidas em uma lista, separadas por vírgulas, espaços ou em formato de texto livre.
        Você também deve identificar qual é a *instrução de análise detalhada* que o usuário deseja que o Gemini aplique a cada link para extração de leads. Se nenhuma instrução de análise específica for dada, use a instrução padrão detalhada para extração de leads.

    2.  **Execução da Ferramenta de Processamento:**
        Utilize a ferramenta `process_provided_urls_for_leads`. Passe a lista de URLs extraídas para o parâmetro `urls` e a instrução de análise (se identificada) para o parâmetro `lead_analysis_instruction`. Esta ferramenta fará a raspagem de cada URL, chamará o Gemini para análise e extração de leads, e gerenciará os limites de taxa entre as chamadas.

    3.  **Formatação da Resposta Final:**
        Com a lista de resultados retornada pela ferramenta `process_provided_urls_for_leads`, formate as informações em uma resposta clara, amigável e legível para o usuário. Para cada URL processada, apresente o título da página (se disponível), a URL original e os dados de leads extraídos, incluindo todos os campos detalhados.
        Se a ferramenta retornar um erro ou se nenhum dado de lead for processado, informe o usuário educadamente.

    Exemplo de resposta formatada com resultados:
    "Analisei os seguintes links e extraí as informações de leads:
    - **Link:** [URL do Link 1]
      **Título:** [Título da Página 1]
      **Dados do Lead:**
        Nome da Empresa: [Nome da Empresa]
        Site: [Site]
        E-mails: [E-mails]
        Telefones: [Telefones]
        Setor: [Setor]
        Localização: [Localização]
        Descrição do Negócio: [Business Description]
        Mercado Alvo: [Target Market]
        Proposta de Valor: [Value Proposition]
        Cliente Ideal: [Ideal Customer]
        Pontos de Dor Resolvidos: [Pain Points]
        Foco da Indústria: [Industry Focus]
    - **Link:** [URL do Link 2]
      ...
    Esses dados são ideais para exportação para um CRM ou planilha detalhada."

    Exemplo de resposta formatada sem resultados ou com erro:
    "Desculpe, não consegui processar os links fornecidos para extração de leads. Por favor, verifique as URLs e tente novamente, ou forneça mais detalhes sobre o que você gostaria de analisar. Se houve um erro, a chave da API Gemini pode não estar configurada corretamente ou os limites de quota foram atingidos."

    Garanta que todas as etapas sejam executadas sequencialmente e que os dados sejam processados de forma precisa em cada fase.""",
    tools=[process_provided_urls_for_leads]
)
