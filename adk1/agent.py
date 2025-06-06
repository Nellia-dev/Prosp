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


# --- FERRAMENTAS COMPOSITAS (Adaptadas para Geração de Leads) ---

def search_and_qualify_leads(query: str, max_search_results_to_scrape: int = MAX_SCRAPE_RESULTS) -> List[Dict[str, Any]]:
    """
    Realiza uma busca web por potenciais leads, raspa o conteúdo e faz uma qualificação inicial
    usando o Gemini, retornando o conteúdo raspado com um resumo de qualificação.

    Args:
        query: A string da query de busca para encontrar leads.
        max_search_results_to_scrape: Número máximo de resultados de busca (do Tavily) a serem raspados e qualificados.

    Returns:
        Uma lista de dicionários, cada um contendo:
        - 'title': Título da página.
        - 'url': URL original.
        - 'snippet': Trecho da busca.
        - 'full_content': Conteúdo raspado.
        - 'qualification_summary': Avaliação do Gemini sobre a relevância do lead.
        - 'error': Se algum erro ocorreu durante a raspagem ou qualificação.
    """
    print(f"--- DEBUG (search_and_qualify_leads): Chamado com query: '{query}' e max_results_to_scrape: {max_search_results_to_scrape} ---")
    try:
        model = _initialize_gemini_model()
        # Busca o dobro de resultados do que será raspado para ter uma margem de URLs válidas
        search_results = _tavily_search_internal(query=query, max_results=max_search_results_to_scrape * 2)

        if not search_results:
            print("--- DEBUG (search_and_qualify_leads): Nenhuns resultados da busca Tavily. ---")
            return [{"error": "Não foram encontrados resultados na busca inicial com a Tavily."}]

        qualified_leads_data = []
        count_scraped = 0

        for result in search_results:
            if count_scraped >= max_search_results_to_scrape:
                break

            url_to_scrape = result.get('url')
            if url_to_scrape and url_to_scrape.startswith('http'):
                print(f"--- DEBUG (search_and_qualify_leads): Tentando raspar URL: '{url_to_scrape}' ---")
                scraped_data = web_scraper(url=url_to_scrape)

                if not scraped_data.get('error') and scraped_data.get('content'):
                    full_content = scraped_data.get('content')
                    prompt_qualify = (
                        f"Analise o seguinte conteúdo de uma página web para determinar se ela representa um "
                        f"potencial lead para a query '{query}'. "
                        f"Resuma os pontos chave da empresa/organização e avalie rapidamente sua relevância e tipo de negócio. "
                        f"Identifique o nome da empresa, se possível. Responda de forma concisa.\n\n"
                        f"Conteúdo:\n{full_content[:MAX_GEMINI_INPUT_CHARS]}"
                    )
                    try:
                        gemini_response = model.generate_content(prompt_qualify)
                        qualification_summary = gemini_response.text
                    except Exception as gemini_err:
                        print(f"--- DEBUG (search_and_qualify_leads): Erro ao qualificar com Gemini para {url_to_scrape}: {gemini_err}. ---")
                        qualification_summary = "Não foi possível qualificar com Gemini. Conteúdo bruto disponível."

                    qualified_leads_data.append({
                        "title": result.get('title'),
                        "url": url_to_scrape,
                        "snippet": result.get('snippet'),
                        "full_content": full_content,
                        "qualification_summary": qualification_summary
                    })
                    count_scraped += 1
                    time.sleep(DELAY_BETWEEN_GEMINI_CALLS_SECONDS)  # Pausa para gerenciar limites de taxa
                else:
                    print(f"--- DEBUG (search_and_qualify_leads): Falha ao raspar '{url_to_scrape}': {scraped_data.get('error', 'Conteúdo vazio/erro desconhecido')} ---")
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
    (nome da empresa, site, e-mails, telefones, etc.) usando Regex e Gemini.

    Args:
        query: A string da query de busca para encontrar leads.
        max_search_results_to_process: O número máximo de resultados de busca a serem raspados e analisados.

    Returns:
        Uma lista de dicionários, onde cada dicionário representa um lead estruturado.
        Retorna uma lista vazia se nenhum lead for encontrado ou se ocorrer um erro.
    """
    print(f"--- DEBUG (find_and_extract_structured_leads): Chamado com query: '{query}' e max_results: {max_search_results_to_process} ---")
    
    # Padrões comuns de Regex para e-mails, telefones e sites (pode ser refinado para mais variações)
    email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    # Regex para telefone (brasileiro com e sem DDI/DDD, com ou sem formatação)
    phone_regex = r'\b(?:\+?\d{1,3}\s?)?(?:\(?\d{2}\)?\s?)?\d{4,5}[-\s]?\d{4}\b'
    website_regex = r'(?:https?:\/\/)?(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\.[a-zA-Z]{2,})(?:\/\S*)?'

    extracted_leads = []
    try:
        model = _initialize_gemini_model()
        search_results = _tavily_search_internal(query=query, max_results=max_search_results_to_process * 2) 

        if not search_results:
            print("--- DEBUG (find_and_extract_structured_leads): Nenhuns resultados da busca Tavily. ---")
            return [{"error": "Não foram encontrados resultados na busca inicial com a Tavily."}]

        count_processed = 0
        for result in search_results:
            if count_processed >= max_search_results_to_process:
                break
            
            url_to_scrape = result.get('url')
            if url_to_scrape and url_to_scrape.startswith('http'):
                print(f"--- DEBUG (find_and_extract_structured_leads): Tentando raspar URL: '{url_to_scrape}' ---")
                scraped_data = web_scraper(url=url_to_scrape)
                
                if not scraped_data.get('error') and scraped_data.get('content'):
                    full_content = scraped_data.get('content')
                    
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
                    prompt_extract = (
                        f"Extraia as seguintes informações sobre a empresa/organização deste texto. "
                        f"Responda APENAS com um objeto JSON válido. Se uma informação não for encontrada, use null. "
                        f"Campos: company_name (string), website (string, preferencialmente o principal), "
                        f"contact_emails (lista de strings), contact_phones (lista de strings), "
                        f"industry (string, ex: 'Tecnologia', 'Saúde'), description (string, breve resumo), "
                        f"size (string, ex: '1-10 funcionários', 'PME', 'Grande Empresa', 'Não informado').\n\n"
                        f"Conteúdo:\n{full_content[:MAX_GEMINI_INPUT_CHARS]}"
                    )
                    
                    gemini_extracted_data = {}
                    try:
                        response = model.generate_content(prompt_extract)
                        # Remove markdown code block if present
                        json_str = response.text.strip().replace('```json\n', '').replace('\n```', '')
                        gemini_extracted_data = json.loads(json_str)
                    except json.JSONDecodeError as jde:
                        print(f"--- DEBUG (find_and_extract_structured_leads): Erro ao decodificar JSON do Gemini para {url_to_scrape}: {jde}. Resposta bruta: {response.text[:200]}..." )
                    except Exception as gemini_err:
                        print(f"--- DEBUG (find_and_extract_structured_leads): Erro na chamada Gemini para {url_to_scrape}: {gemini_err} ---")
                    
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
                    count_processed += 1
                    time.sleep(DELAY_BETWEEN_GEMINI_CALLS_SECONDS)  # Pausa para gerenciar limites de taxa
                else:
                    print(f"--- DEBUG (find_and_extract_structured_leads): Falha ao raspar '{url_to_scrape}': {scraped_data.get('error', 'Conteúdo vazio/erro desconhecido')} ---")
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


def process_provided_urls_for_leads(urls: List[str], lead_analysis_instruction: str = "Analise este conteúdo para identificar e extrair informações de leads como nome da empresa, site, e-mails de contato e números de telefone. Apresente como um objeto JSON com os campos: company_name, website, contact_emails (lista), contact_phones (lista), industry, description, size. Se uma informação não for encontrada, use null.") -> List[Dict[str, Any]]:
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
                item_result["title"] = scraped_data.get("title", "No Title Found")

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
                time.sleep(DELAY_BETWEEN_GEMINI_CALLS_SECONDS)  # Pausa para gerenciar limites de taxa
                
        print(f"--- DEBUG (process_provided_urls_for_leads): Retornando {len(results)} resultados processados. ---")
        return results
    except ValueError as ve:
        print(f"--- DEBUG (process_provided_urls_for_leads): Erro de configuração da API: {ve} ---")
        return [{"error": f"Erro de configuração da API: {ve}"}]
    except Exception as e:
        print(f"--- DEBUG (process_provided_urls_for_leads): Um erro inesperado ocorreu na ferramenta composta: {e} ---")
        return [{"error": f"Um erro inesperado ocorreu na ferramenta composta: {e}"}]


# --- AGENTES (Adaptados para Geração de Leads) ---

# Este agente é o ponto de entrada inicial para refinar a query do usuário.
# Ele é exposto como 'root_agent' para corresponder à sua solicitação no __init__.py.
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
    tools=[] # Este agente não usa ferramentas, ele gera a query diretamente
)
# Alias para corresponder à importação desejada no __init__.py
root_agent = _query_refiner_agent_internal


lead_search_and_qualify_agent = Agent(
    name="lead_search_and_qualify_agent",
    model="gemini-1.5-flash-8b", 
    description="""Você é um agente especializado em buscar potenciais leads na web e realizar uma qualificação inicial do seu potencial, com base nos critérios fornecidos pelo usuário. Seu objetivo é identificar páginas e conteúdos que sejam relevantes para a geração de leads.""",
    instruction="""Você é responsável por encontrar e qualificar leads.
    Seu processo de trabalho é o seguinte:

    1.  **Execução da Busca e Qualificação Inicial:**
        Utilize a ferramenta `search_and_qualify_leads` com a query de busca que você recebeu (já refinada). **Para evitar exceder o limite de tokens do modelo e otimizar o tempo, você DEVE limitar o número de resultados a serem raspados e qualificados para um máximo de 3 (três) ou 4 (quatro) resultados, passando o parâmetro `max_search_results_to_scrape` com este valor.** Esta ferramenta fará a busca na internet e raspará o conteúdo das páginas relevantes, retornando o conteúdo raspado e uma `qualification_summary` (resumo de qualificação) gerado pelo Gemini.

    2.  **Análise e Agregação dos Resultados Qualificados:**
        Para cada resultado retornado pela ferramenta `search_and_qualify_leads`, analise o `qualification_summary` e o `url`.
        Filtre resultados que claramente não são relevantes ou que apresentaram erros.
        Agrupe os leads promissores, destacando o nome da empresa (se inferível do resumo ou título), a URL, e o resumo da qualificação.

    3.  **Formatação da Resposta Final:**
        Com a lista de leads qualificados, formate essas informações em uma resposta clara, amigável e legível para o usuário.
        Use bullet points ou uma lista numerada para apresentar cada lead potencial.
        Se nenhum lead relevante for encontrado, informe o usuário educadamente.

    Exemplo de resposta formatada com resultados:
    "Encontrei os seguintes potenciais leads para sua solicitação:
    - **Empresa/Título:** [Nome da Empresa ou Título da Página]
      **URL:** [URL da Página]
      **Qualificação:** [Resumo da qualificação do Gemini]
    Se precisar de mais detalhes ou da extração de dados específicos (e-mail, telefone) para esses, me diga!"

    Exemplo de resposta formatada sem resultados:
    "Desculpe, não consegui encontrar potenciais leads relevantes com os critérios fornecidos. Por favor, tente reformular sua pergunta ou forneça mais detalhes para a busca."

    Garanta que todas as etapas sejam executadas sequencialmente e que os dados sejam processados de forma precisa em cada fase.""",
    tools=[search_and_qualify_leads]
)


structured_lead_extractor_agent = Agent(
    name="structured_lead_extractor_agent",
    model="gemini-1.5-flash-8b", 
    description="""Você é um agente altamente especializado na extração de dados estruturados de leads a partir de conteúdo web. Sua função é buscar informações detalhadas como nome da empresa, site, e-mails de contato, telefones, setor e tamanho, e apresentá-las em um formato padronizado.""",
    instruction="""Você é o ponto de entrada para extrair informações de leads em um formato estruturado.
    Seu processo de trabalho é o seguinte:

    1.  **Execução da Busca e Extração Estruturada:**
        Utilize a ferramenta `find_and_extract_structured_leads` com a query de busca que você recebeu. **Para otimizar o processamento, você DEVE limitar o número de resultados a serem processados para um máximo de 3 (três) ou 4 (quatro) resultados, passando o parâmetro `max_search_results_to_process` com este valor.** Esta ferramenta fará a busca na internet, raspará o conteúdo das páginas e tentará extrair informações detalhadas de leads usando uma combinação de Regex e inteligência do Gemini. O resultado será uma lista de objetos JSON, cada um representando um lead.

    2.  **Formatação da Resposta Final:**
        Com a lista de leads estruturados retornada pela ferramenta `find_and_extract_structured_leads`:
        - Se leads forem encontrados, apresente-os claramente ao usuário. O formato ideal é uma lista de leads, onde cada lead é apresentado com seus campos (Nome da Empresa, Site, E-mails, Telefones, etc.). Você pode usar um formato textual amigável ou, se a complexidade for alta, indicar que os dados estão prontos para exportação.
        - Se a ferramenta retornar um erro ou uma lista vazia, informe o usuário educadamente sobre a falha e sugira reformular a busca ou verificar os critérios.

    Exemplo de resposta formatada com sucesso:
    "Encontrei os seguintes leads com informações estruturadas:
    - **Empresa:** [Nome da Empresa 1]
      **Site:** [Site 1]
      **E-mails:** [email1@empresa.com, email2@empresa.com]
      **Telefones:** [telefone1, telefone2]
      **Setor:** [Setor 1]
      **Descrição:** [Breve descrição 1]
      **Fonte:** [URL da fonte]
    - **Empresa:** [Nome da Empresa 2]
      ...
    Esses dados podem ser exportados para um CRM ou planilha, se desejar."

    Exemplo de resposta formatada sem sucesso:
    "Desculpe, não consegui extrair informações de leads estruturadas com base na sua solicitação. Por favor, tente refinar a query ou fornecer mais detalhes para a busca. [Mensagem de erro da ferramenta, se houver]"

    Garanta que todas as etapas sejam executadas sequencialmente e que os dados sejam processados de forma precisa em cada fase.""",
    tools=[find_and_extract_structured_leads]
)


direct_url_lead_processor_agent = Agent(
    name="direct_url_lead_processor_agent",
    model="gemini-1.5-flash-8b", 
    description="""Você é um agente especializado em processar diretamente uma lista de URLs fornecidas pelo usuário para extrair informações de leads. Para cada URL, você raspará o conteúdo e usará o Google Gemini para analisar e extrair dados de leads, gerenciando a taxa de chamadas da API.""",
    instruction="""Você é o ponto de entrada para processamento de URLs para extração de leads.
    Seu processo de trabalho é o seguinte:

    1.  **Entendimento e Extração de URLs e Instrução de Análise:**
        Ao receber a solicitação do usuário, sua primeira tarefa é identificar e extrair *todas as URLs* presentes na mensagem.
        As URLs podem ser fornecidas em uma lista, separadas por vírgulas, espaços ou em formato de texto livre.
        Você também deve identificar qual é a *instrução de análise detalhada* que o usuário deseja que o Gemini aplique a cada link para extração de leads (ex: "extraia nome da empresa, site e e-mail", "identifique o CEO e o tamanho da empresa"). Se nenhuma instrução de análise específica for dada, use a instrução padrão para extração de leads.

    2.  **Execução da Ferramenta de Processamento:**
        Utilize a ferramenta `process_provided_urls_for_leads`. Passe a lista de URLs extraídas para o parâmetro `urls` e a instrução de análise (se identificada) para o parâmetro `lead_analysis_instruction`. Esta ferramenta fará a raspagem de cada URL, chamará o Gemini para análise e extração de leads, e gerenciará os limites de taxa entre as chamadas.

    3.  **Formatação da Resposta Final:**
        Com a lista de resultados retornada pela ferramenta `process_provided_urls_for_leads`, formate as informações em uma resposta clara, amigável e legível para o usuário. Para cada URL processada, apresente o título da página (se disponível), a URL original e os dados de leads extraídos.
        Se a ferramenta retornar um erro ou se nenhum dado de lead for processado, informe o usuário educadamente.

    Exemplo de resposta formatada com resultados:
    "Analisei os seguintes links e extraí as informações de leads:
    - **Link:** [URL do Link 1]
      **Título:** [Título da Página 1]
      **Dados do Lead:** [Nome da Empresa: ABC, Site: abc.com, E-mail: contato@abc.com]
    - **Link:** [URL do Link 2]
      **Título:** [Título da Página 2]
      **Dados do Lead:** [Nome da Empresa: XYZ, Setor: Finanças]
    Se precisar de mais análises ou da exportação desses dados, por favor, me diga."

    Exemplo de resposta formatada sem resultados ou com erro:
    "Desculpe, não consegui processar os links fornecidos para extração de leads. Por favor, verifique as URLs e tente novamente, ou forneça mais detalhes sobre o que você gostaria de analisar. Se houve um erro, a chave da API Gemini pode não estar configurada corretamente ou os limites de quota foram atingidos."

    Garanta que todas as etapas sejam executadas sequencialmente e que os dados sejam processados de forma precisa em cada fase.""",
    tools=[process_provided_urls_for_leads]
)
