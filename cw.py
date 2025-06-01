import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
import time
import requests # Para Tavily API
import traceback # Para melhor log de erros
import re
import datetime
# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configurações Globais ---
MAX_API_RETRIES = 3
API_RETRY_DELAY_SECONDS = 10 # Aumentado devido a muitas chamadas
INTER_STEP_DELAY_SECONDS = 2.5 # Delay entre sub-passos para um mesmo lead
INTER_LEAD_PROCESSING_DELAY_SECONDS = 7 # Delay entre processamento de leads diferentes
OUTPUT_FOLDER = "analysis_output_with_enrichment" # Nome da pasta de saída

# !!! ATENÇÃO: NOME DO MODELO EXIGIDO PELO USUÁRIO !!!
MODEL_NAME = "gemini-2.0-flash"

# Configurações Tavily
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TAVILY_SEARCH_DEPTH = "basic"
TAVILY_MAX_RESULTS_PER_QUERY = 2
TAVILY_TOTAL_QUERIES_PER_LEAD = 3
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 15000 # Para evitar prompts excessivamente longos

# --- Configuração do Modelo Gemini ---
model = None # Inicializa model como None
try:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not GEMINI_API_KEY:
        raise ValueError("API Key do Gemini (GEMINI_API_KEY ou GOOGLE_API_KEY) não encontrada nas variáveis de ambiente.")

    genai.configure(api_key=GEMINI_API_KEY)

    generation_config = {
        "temperature": 0.55, # Mais focado
        "top_p": 0.85,
        "top_k": 20,
    }

    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]

    print(f"--- ATENÇÃO: Tentando configurar o modelo '{MODEL_NAME}' conforme solicitado. ---")
    print("--- Se ocorrerem erros relacionados ao nome do modelo, considere usar 'gemini-1.5-flash-latest'. ---")
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        generation_config=generation_config,
        safety_settings=safety_settings
    )
    print(f"Modelo Gemini '{MODEL_NAME}' configurado com sucesso (ou a tentativa de configuração foi enviada).")

except Exception as e:
    print(f"Erro crítico ao inicializar o modelo Gemini '{MODEL_NAME}': {e}")
    print("Por favor, verifique se o nome do modelo está correto e se a API Key é válida.")
    print("Considere usar 'gemini-1.5-flash-latest' se o problema persistir com o nome do modelo atual.")
    # Não saímos, mas `model` permanecerá None, e as chamadas falharão graciosamente.

if not TAVILY_API_KEY:
    print("AVISO: TAVILY_API_KEY não encontrada. O enriquecimento de dados com Tavily será pulado.")

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# --- Funções Auxiliares ---
def truncate_text(text: str, max_chars: int = GEMINI_TEXT_INPUT_TRUNCATE_CHARS) -> str:
    """Trunca o texto para um número máximo de caracteres, se necessário."""
    return text[:max_chars] if text and len(text) > max_chars else text

# --- Funções da API Tavily ---
def search_with_tavily(query: str, search_depth: str = TAVILY_SEARCH_DEPTH, max_results: int = TAVILY_MAX_RESULTS_PER_QUERY) -> list[dict]:
    if not TAVILY_API_KEY:
        # print("  [Tavily] API Key não configurada. Pulando pesquisa.") # Logado uma vez no início
        return []
    print(f"  [Tavily] Pesquisando por: '{query}' (depth: {search_depth}, max_results: {max_results})")
    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": search_depth,
                "include_answer": False,
                "max_results": max_results
            },
            timeout=20 # Timeout para a requisição Tavily
        )
        response.raise_for_status() # Levanta um erro para status HTTP 4xx/5xx
        results = response.json().get("results", [])
        print(f"  [Tavily] Encontrados {len(results)} resultados.")
        return results
    except requests.exceptions.RequestException as e:
        print(f"  [Tavily] Erro na API Tavily: {e}")
        return []
    except Exception as e_tav:
        print(f"  [Tavily] Erro inesperado com Tavily: {e_tav}")
        return []

# --- Função Principal de Chamada à API Gemini (para texto) ---
def call_gemini_api_text_analyzer(prompt: str, agent_name: str, max_retries=MAX_API_RETRIES, delay_seconds=API_RETRY_DELAY_SECONDS) -> str:
    if not model: # Verifica se o modelo foi inicializado
        return f"Erro: Modelo Gemini '{MODEL_NAME}' não foi inicializado corretamente."

    # print(f"\n--- Agente '{agent_name}' iniciando... ---")
    # print(f"Prompt (primeiros 150 chars): {truncate_text(prompt, 150)}...")
    for attempt in range(max_retries):
        try:
            # Truncar o prompt aqui também, se necessário, antes de enviar
            # Embora seja melhor truncar os componentes do prompt antes de montá-lo.
            response = model.generate_content(truncate_text(prompt, GEMINI_TEXT_INPUT_TRUNCATE_CHARS * 2)) # Um pouco mais de margem

            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text
            elif hasattr(response, 'prompt_feedback') and response.prompt_feedback and response.prompt_feedback.block_reason:
                error_message = f"Geração bloqueada para o agente '{agent_name}'. Feedback: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}"
                print(f"Erro Gemini: {error_message}")
                if attempt < max_retries - 1:
                    print(f"Tentando novamente em {delay_seconds} segundos...")
                    time.sleep(delay_seconds)
                else:
                    return f"Erro: {error_message}"
            else:
                error_message = f"Resposta vazia ou inesperada do modelo para o agente '{agent_name}' após {attempt + 1} tentativas."
                print(f"Erro Gemini: {error_message}")
                if attempt < max_retries - 1:
                    print(f"Tentando novamente em {delay_seconds} segundos...")
                    time.sleep(delay_seconds)
                else:
                    return f"Erro: {error_message}"
        except Exception as e:
            print(f"Erro ao chamar a API Gemini para o agente '{agent_name}' (Tentativa {attempt + 1}/{max_retries}): {e}")
            if "429" in str(e) or "rate limit" in str(e).lower() or \
               "resource has been exhausted" in str(e).lower() or "503" in str(e) or \
               "model is overloaded" in str(e).lower():
                wait_time = delay_seconds * (2 ** attempt) # Exponential backoff
                print(f"Rate limit/recurso esgotado/serviço indisponível. Aguardando {wait_time} segundos antes de tentar novamente...")
                time.sleep(wait_time)
            elif attempt < max_retries - 1:
                print(f"Tentando novamente em {delay_seconds} segundos...")
                time.sleep(delay_seconds)
            else:
                return f"Erro: Falha ao chamar a API Gemini para o agente '{agent_name}' após {max_retries} tentativas: {e}"
    return f"Erro: Falha catastrófica ao obter resposta da API Gemini para o agente '{agent_name}'."


# --- Implementação dos Agentes ---

def agente_enriquecimento_tavily(company_name: str, texto_extraido_inicial: str) -> str:
    agent_name = "Coletor de Inteligência Adicional (Tavily)"
    if not TAVILY_API_KEY:
        return "Enriquecimento com Tavily pulado: API Key não fornecida."

    # Condição para enriquecimento (exemplo: texto curto ou com falha)
    necessita_enriquecimento = not texto_extraido_inicial or \
                               "FALHA NA EXTRAÇÃO" in texto_extraido_inicial or \
                               len(texto_extraido_inicial) < 700 # Limiar ajustável

    if not necessita_enriquecimento:
        return "Enriquecimento com Tavily não foi considerado necessário com base nos dados iniciais."

    print(f"  [{agent_name}] Dados iniciais insuficientes para '{company_name}'. Buscando com Tavily...")
    queries_tavily = [
        f"{company_name} notícias recentes",
        f"{company_name} sobre nós",
        f"principais produtos e serviços {company_name}",
        f"setor de atuação {company_name}"
    ][:TAVILY_TOTAL_QUERIES_PER_LEAD] # Limita o número de queries

    all_tavily_content_parts = []
    for q_tav in queries_tavily:
        tavily_results = search_with_tavily(q_tav)
        for res_tav in tavily_results:
            content_part = f"Fonte: {res_tav.get('url', 'N/A')}\nTítulo: {res_tav.get('title', 'N/A')}\nConteúdo: {truncate_text(res_tav.get('content', 'N/A'), 1000)}"
            all_tavily_content_parts.append(content_part)
        time.sleep(0.5) # Pequena pausa entre queries Tavily

    if not all_tavily_content_parts:
        return "Enriquecimento com Tavily tentado, mas não retornou resultados."

    texto_coletado_da_tavily = "\n\n---\n\n".join(all_tavily_content_parts)

    # Agora, usamos Gemini para resumir os dados da Tavily
    summarizer_agent_name = "Sumarizador de Inteligência de Mercado (Pós-Tavily)"
    prompt_sumarizacao_tavily = f"""
    Você é um {summarizer_agent_name}.
    As seguintes informações foram coletadas através de uma pesquisa na web (via API Tavily) sobre a empresa "{company_name}":
    --- INÍCIO DADOS TAVILY ---
    {truncate_text(texto_coletado_da_tavily, GEMINI_TEXT_INPUT_TRUNCATE_CHARS - 500)}
    --- FIM DADOS TAVILY ---

    Com base EXCLUSIVAMENTE nestas informações da Tavily, resuma os 2-3 pontos mais relevantes que complementam o nosso conhecimento sobre a empresa "{company_name}".
    Foque em:
    1. Notícias recentes ou desenvolvimentos importantes.
    2. Informações chave sobre seus produtos/serviços ou mercado.
    3. Qualquer menção a desafios ou iniciativas estratégicas.

    Se os dados da Tavily forem escassos ou irrelevantes, indique "Dados da Tavily não forneceram insights adicionais significativos."
    Formato da Saída: Um breve resumo em bullet points ou um parágrafo conciso.
    """
    return call_gemini_api_text_analyzer(prompt_sumarizacao_tavily, summarizer_agent_name)


def agente_extracao_contatos(texto_extraido_lead: str, company_name: str, produto_servico_ofertado: str) -> dict:
    agent_name = "Detetive de Contatos Digitais"
    prompt = f"""
    Você é um {agent_name}. Sua tarefa é analisar o texto fornecido, que foi extraído do site de uma empresa ({company_name}), para encontrar informações de contato.

    Texto para Análise (primeiros {GEMINI_TEXT_INPUT_TRUNCATE_CHARS} caracteres):
    ```
    {truncate_text(texto_extraido_lead)}
    ```

    Procure por:
    1. Endereços de e-mail (ex: contato@empresa.com, vendas@empresa.com). Priorize e-mails genéricos da empresa ou de departamentos relevantes para "{produto_servico_ofertado}". Evite e-mails pessoais se não parecerem ser de contato profissional. Liste no máximo 3 e-mails.
    2. Links de perfis do Instagram (URLs completas, ex: https://www.instagram.com/nomeempresa). Liste no máximo 2 perfis.

    Formato da Saída Esperada (JSON VÁLIDO E SOMENTE O JSON):
    {{
      "emails_encontrados": ["email1@example.com", "email2@example.com"],
      "instagram_perfis_encontrados": ["https://instagram.com/perfil1"],
      "sugestao_pesquisa_tavily": "Se nenhum contato direto for encontrado, ou para mais opções, pesquise na Tavily por: '[{company_name} contato]' ou '[{company_name} Instagram oficial]'."
    }}
    Se nenhum e-mail for encontrado, retorne uma lista vazia para "emails_encontrados".
    Se nenhum perfil do Instagram for encontrado, retorne uma lista vazia para "instagram_perfis_encontrados".
    A "sugestao_pesquisa_tavily" deve ser sempre incluída.
    Retorne APENAS o objeto JSON, sem nenhum texto adicional antes ou depois.
    """
    response_text = call_gemini_api_text_analyzer(prompt, agent_name)
    default_response = {
        "emails_encontrados": [],
        "instagram_perfis_encontrados": [],
        "sugestao_pesquisa_tavily": f"Pesquisar Tavily por: '{company_name} contato' ou '{company_name} Instagram oficial'."
    }
    if response_text.startswith("Erro:"):
        print(f"  [{agent_name}] Erro ao obter resposta: {response_text}")
        return default_response

    try:
        # Tentar limpar a resposta para extrair apenas o JSON
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            json_str = match.group(0)
            parsed_json = json.loads(json_str)
            # Validar estrutura básica
            if "emails_encontrados" in parsed_json and "instagram_perfis_encontrados" in parsed_json:
                return parsed_json
            else:
                print(f"  [{agent_name}] JSON retornado não tem a estrutura esperada. Resposta: {response_text}")
                return default_response
        else:
            print(f"  [{agent_name}] Não foi possível encontrar um objeto JSON na resposta. Resposta: {response_text}")
            return default_response
    except json.JSONDecodeError:
        print(f"  [{agent_name}] Falha ao decodificar JSON da resposta. Resposta: {response_text}")
        return default_response
    except Exception as e:
        print(f"  [{agent_name}] Erro inesperado ao processar resposta: {e}. Resposta: {response_text}")
        return default_response


# Funções de agentes já existentes (gerar_analise_lead, criar_persona, etc.)
# Adaptadas para usar truncate_text nos inputs maiores.

def gerar_analise_lead(lead_data_str: str, dados_enriquecidos: str, seu_produto_ou_servico: str) -> str:
    agent_name = "Analista de Leads Sênior"
    prompt = f"""
    Você é um {agent_name}.
    Sua tarefa é analisar profundamente os dados de um lead para identificar suas principais atividades, setor, desafios potenciais e oportunidades de negócio relevantes para um produto/serviço específico.

    Produto/Serviço a ser considerado: "{seu_produto_ou_servico}"

    Dados do Lead (extraídos do site):
    ```json
    {truncate_text(lead_data_str, 8000)}
    ```

    Dados Adicionais de Enriquecimento (se disponíveis):
    ```
    {truncate_text(dados_enriquecidos, 4000)}
    ```

    Com base em TODOS os dados fornecidos e no produto/serviço em foco, por favor, forneça:
    1. Setor de atuação da empresa.
    2. Principais serviços/produtos oferecidos pela empresa.
    3. Notícias recentes ou atividades importantes mencionadas. Se "ANÁLISE DA IMAGEM PELA IA" for mencionado nos dados do lead, resuma.
    4. Desafios ou necessidades potenciais INICIAIS.
    5. Informações sobre tamanho da empresa, cultura, valores.
    6. Diagnóstico geral e como "{seu_produto_ou_servico}" poderia se encaixar.

    Formato da Saída: Relatório detalhado. Se "FALHA NA EXTRAÇÃO..." nos dados do lead, indique e baseie-se mais nos dados de busca e enriquecimento.
    Se informação não disponível, indique "Informação não disponível".
    """
    return call_gemini_api_text_analyzer(prompt, agent_name)

def criar_persona(analise_lead: str, seu_produto_ou_servico: str, url_lead: str) -> str:
    agent_name = "Especialista em Desenvolvimento de Personas B2B"
    prompt = f"""
    Você é um {agent_name}. Crie uma persona detalhada do tomador de decisão na empresa (URL: {url_lead}), baseada na análise e no produto/serviço.

    Produto/Serviço: "{seu_produto_ou_servico}"

    Análise do Lead:
    ```
    {truncate_text(analise_lead)}
    ```
    Inclua:
    1. Nome fictício e Cargo provável.
    2. Responsabilidades e metas.
    3. Desafios e dores (conforme análise).
    4. Motivações e o que buscam.
    5. Como "{seu_produto_ou_servico}" os ajudaria.

    Formato: Perfil detalhado. Se análise insuficiente, indique especulação.
    """
    return call_gemini_api_text_analyzer(prompt, f"{agent_name} para {url_lead}")

def aprofundar_pontos_de_dor(analise_lead: str, persona: str, seu_produto_ou_servico: str, nome_empresa_lead: str) -> str:
    agent_name = "Especialista em Diagnóstico de Dores Empresariais"
    prompt = f"""
    Você é um {agent_name}. Aprofunde os pontos de dor para "{nome_empresa_lead}" (persona e produto: "{seu_produto_ou_servico}").

    Análise do Lead:
    ```
    {truncate_text(analise_lead)}
    ```
    Persona:
    ```
    {truncate_text(persona)}
    ```
    Para 3-5 dores:
    1. Descrição detalhada.
    2. Impacto negativo nos negócios.
    3. Como "{seu_produto_ou_servico}" alivia/resolve.
    4. Pergunta investigativa chave.

    Formato: Lista detalhada. Se insuficiente, use dores genéricas do setor.
    """
    return call_gemini_api_text_analyzer(prompt, f"{agent_name} para {nome_empresa_lead}")

# --- Novos Agentes Adicionais ---

def agente_qualificacao_lead(analise_lead: str, persona: str, dores_aprofundadas: str, produto_servico: str) -> str:
    agent_name = "Especialista em Qualificação de Leads"
    prompt = f"""
    Você é um {agent_name}.
    Análise do Lead:
    ```
    {truncate_text(analise_lead)}
    ```
    Persona:
    ```
    {truncate_text(persona)}
    ```
    Dores Aprofundadas:
    ```
    {truncate_text(dores_aprofundadas)}
    ```
    Produto/Serviço Oferecido: "{produto_servico}"

    Com base nestes insights, avalie o quão qualificado este lead parece ser.
    Forneça uma classificação (Ex: Alto Potencial, Potencial Médio, Baixo Potencial, Não se Encaixa Claramente)
    e uma breve justificativa (2-3 pontos principais) para sua avaliação, considerando o alinhamento dos desafios da empresa com os benefícios da solução.
    """
    return call_gemini_api_text_analyzer(prompt, agent_name)

def agente_identificacao_concorrentes(texto_extraido_lead: str, produto_servico: str, lista_seus_concorrentes_str: str = "") -> str:
    agent_name = "Analista de Inteligência Competitiva"
    prompt = f"""
    Você é um {agent_name}. Analise o seguinte texto extraído do site de uma empresa.
    Texto do Site (primeiros {GEMINI_TEXT_INPUT_TRUNCATE_CHARS} caracteres):
    ```
    {truncate_text(texto_extraido_lead)}
    ```
    Nosso Produto/Serviço: "{produto_servico}"
    Nossos Concorrentes Conhecidos (se houver): {lista_seus_concorrentes_str if lista_seus_concorrentes_str else "Nenhum listado"}

    Identifique:
    1. Quaisquer menções diretas a empresas que são concorrentes de "{produto_servico}" (incluindo os listados, se houver).
    2. Menções a tipos de soluções, ferramentas ou abordagens que a empresa do lead já possa estar utilizando para resolver os problemas que "{produto_servico}" aborda.

    Liste as menções encontradas ou indique "Nenhuma menção clara a concorrentes diretos ou soluções alternativas foi encontrada no texto fornecido."
    """
    return call_gemini_api_text_analyzer(prompt, agent_name)

def agente_gerador_perguntas_estrategicas(analise_lead: str, persona: str, dores_aprofundadas: str) -> str:
    agent_name = "Coach de Vendas Consultivas (Perguntas de Descoberta)"
    prompt = f"""
    Você é um {agent_name}.
    Análise do Lead:
    ```
    {truncate_text(analise_lead)}
    ```
    Persona:
    ```
    {truncate_text(persona)}
    ```
    Dores Aprofundadas (contém perguntas investigativas):
    ```
    {truncate_text(dores_aprofundadas)}
    ```
    Formule 2-3 perguntas estratégicas e ABERTAS adicionais para uma primeira ligação de descoberta.
    Estas perguntas devem ir ALÉM da simples confirmação de dor (já cobertas nas "Dores Aprofundadas") e buscar entender:
    - Objetivos de negócio mais amplos do lead/empresa.
    - Como eles tomam decisões sobre novas soluções.
    - O impacto e resultados que eles esperam de uma solução como a que poderia ser oferecida.
    - Seus processos atuais relacionados ao problema.
    Não repita perguntas que provavelmente já estão na seção de "Dores Aprofundadas".
    """
    return call_gemini_api_text_analyzer(prompt, agent_name)

def agente_identificacao_gatilhos_compra(lead_data_str: str, dados_enriquecidos: str, produto_servico: str) -> str:
    agent_name = "Analista de Sinais de Mercado (Gatilhos de Compra)"
    prompt = f"""
    Você é um {agent_name}. Analise os dados da empresa.
    Dados do Lead (extraídos do site e Google Search):
    ```json
    {truncate_text(lead_data_str, 8000)}
    ```
    Dados Adicionais de Enriquecimento (Tavily, se disponíveis):
    ```
    {truncate_text(dados_enriquecidos, 4000)}
    ```
    Nosso Produto/Serviço: "{produto_servico}"

    Procure por 'gatilhos de compra' ou eventos recentes (últimos 6-12 meses, se a data for inferível) como:
    - Novas contratações em posições chave (C-level, diretores de áreas relevantes para "{produto_servico}").
    - Anúncios de expansão, fusões, aquisições.
    - Lançamento de novos produtos/serviços pela empresa do lead.
    - Recebimento de investimento.
    - Participação em grandes eventos do setor (como palestrante ou expositor).
    - Menções explícitas a desafios estratégicos ou iniciativas de transformação que "{produto_servico}" pode auxiliar.

    Liste os 2-3 eventos/sinais mais relevantes encontrados e explique brevemente por que podem ser significativos para uma abordagem com "{produto_servico}".
    Se nenhum gatilho claro for encontrado, indique "Nenhum gatilho de compra óbvio identificado nos dados fornecidos."
    """
    return call_gemini_api_text_analyzer(prompt, agent_name)

# --- Agentes para Simulação ToT (Plano de Ação) ---
def agente_gerador_estrategias_abordagem_tot(sumario_lead_completo: str, produto_servico: str) -> str:
    agent_name = "Planejador Estratégico de Vendas (ToT - Geração de Opções)"
    prompt = f"""
    Você é um {agent_name}. Objetivo: gerar MÚLTIPLAS E DISTINTAS estratégias de alto nível para iniciar um contato comercial com o lead, visando apresentar "{produto_servico}".

    Sumário Consolidado do Lead:
    ```
    {truncate_text(sumario_lead_completo, GEMINI_TEXT_INPUT_TRUNCATE_CHARS - 500)}
    ```

    Gere 2 a 3 opções de estratégias de abordagem. Para cada estratégia:
    1. Nome curto e descritivo.
    2. Racional principal (1-2 frases).
    3. Canal principal sugerido.
    4. Gancho/ponto de partida principal da conversa.

    Exemplo de Formato para UMA estratégia:
    --- ESTRATÉGIA 1 ---
    Nome: [Nome da Estratégia 1]
    Racional: [Racional da Estratégia 1]
    Canal Principal: [Canal]
    Gancho Inicial: [Gancho]

    Seja criativo e considere diferentes ângulos.
    """
    return call_gemini_api_text_analyzer(prompt, agent_name)

def agente_avaliador_estrategias_tot(estrategias_propostas_texto: str, sumario_lead_completo: str) -> str:
    agent_name = "Analista Crítico de Vendas (ToT - Avaliação de Opções)"
    prompt = f"""
    Você é um {agent_name}. Avalie criticamente as estratégias de abordagem propostas.

    Sumário Consolidado do Lead:
    ```
    {truncate_text(sumario_lead_completo, 5000)}
    ```
    Estratégias de Abordagem Propostas:
    ```
    {truncate_text(estrategias_propostas_texto)}
    ```
    Para CADA estratégia:
    1. Nome da Estratégia.
    2. Prós (1-2 vantagens para este lead).
    3. Contras/Riscos (1-2 desvantagens/riscos).
    4. Probabilidade de Sucesso Estimada (Baixa, Média, Alta) e breve justificativa.

    Exemplo de Formato para UMA avaliação:
    --- AVALIAÇÃO DA ESTRATÉGIA: [Nome da Estratégia 1] ---
    Prós: ...
    Contras/Riscos: ...
    Probabilidade de Sucesso: [Alta/Média/Baixa] - Justificativa: ...
    """
    return call_gemini_api_text_analyzer(prompt, agent_name)

def agente_sintetizador_plano_acao_final_tot(avaliacao_estrategias_texto: str, estrategias_propostas_texto: str, sumario_lead_completo: str) -> str:
    agent_name = "Arquiteto de Plano de Ação de Vendas (ToT - Síntese e Decisão)"
    prompt = f"""
    Você é um {agent_name}. Desenvolva um PLANO DE AÇÃO FINAL e CONCRETO.

    Sumário Consolidado do Lead:
    ```
    {truncate_text(sumario_lead_completo, 3000)}
    ```
    Estratégias Propostas Originalmente:
    ```
    {truncate_text(estrategias_propostas_texto, 3000)}
    ```
    Avaliação Crítica das Estratégias:
    ```
    {truncate_text(avaliacao_estrategias_texto, 4000)}
    ```
    Com base em tudo isso:
    1.  **Recomendação Principal:** Qual estratégia (ou combinação) é MAIS PROMISSORA? Justifique.
    2.  **Plano de Ação Detalhado (para a estratégia recomendada):**
        a.  Canal Primário.
        b.  Mensagem Chave/Gancho Principal.
        c.  Primeiros 2-3 Passos Concretos para o vendedor.
        d.  Métrica de Sucesso para o primeiro contato.
    3.  **Plano de Contingência Breve:** Se a abordagem principal falhar.

    Formato: Relatório claro e acionável.
    """
    return call_gemini_api_text_analyzer(prompt, agent_name)


# Funções de agentes já existentes (desenvolver_plano_abordagem, etc.)
# Adaptadas para usar truncate_text e potencialmente os novos inputs.

def desenvolver_plano_abordagem_detalhado(analise_lead: str, persona: str, aprofundamento_dores: str, plano_acao_tot: str, seu_produto_ou_servico: str, url_lead: str) -> str:
    agent_name = "Estrategista de Vendas Consultivas (Detalhado)"
    prompt = f"""
    Você é um {agent_name}. Desenvolva um plano de abordagem DETALHADO para a persona na empresa (URL: {url_lead}), para "{seu_produto_ou_servico}".
    Considere o Plano de Ação ToT como guia principal.

    Plano de Ação Principal (Recomendado pelo ToT):
    ```
    {truncate_text(plano_acao_tot)}
    ```
    Análise do Lead:
    ```
    {truncate_text(analise_lead, 3000)}
    ```
    Persona:
    ```
    {truncate_text(persona, 2000)}
    ```
    Aprofundamento Dores:
    ```
    {truncate_text(aprofundamento_dores, 3000)}
    ```
    Detalhe:
    1. Canal de abordagem (confirmar ou refinar do ToT).
    2. Tom de voz e estilo de comunicação.
    3. Pontos de valor de "{seu_produto_ou_servico}" (conectados às dores e ao gancho do ToT).
    4. Lista de 2-3 objeções prováveis (além das já tratadas).
    5. Talking points e perguntas abertas para iniciar conversa (alinhados com o ToT).

    Formato: Plano de abordagem claro e acionável.
    """
    return call_gemini_api_text_analyzer(prompt, f"{agent_name} para {url_lead}")

def elaborar_respostas_objecoes(plano_abordagem_detalhado: str, persona: str, seu_produto_ou_servico: str, nome_empresa_lead: str) -> str:
    agent_name = "Especialista em Contorno de Objeções B2B"
    prompt = f"""
    Você é um {agent_name}. Elabore respostas para objeções para "{nome_empresa_lead}" (produto: "{seu_produto_ou_servico}").

    Plano de Abordagem Detalhado (contém objeções previstas):
    ```
    {truncate_text(plano_abordagem_detalhado)}
    ```
    Persona:
    ```
    {truncate_text(persona)}
    ```
    Para cada objeção no plano (ou sugira 2-3 comuns se não houver):
    1. Reafirme a objeção.
    2. Forneça framework de resposta (empático, valide, reposicione valor, sugira próximo passo).
    Objetivo: manter conversa aberta.

    Formato: Lista de objeções e respostas.
    """
    return call_gemini_api_text_analyzer(prompt, f"{agent_name} para {nome_empresa_lead}")

def customizar_proposta_de_valor(analise_lead: str, persona: str, aprofundamento_dores: str, gatilhos_compra: str, seu_produto_ou_servico: str, nome_empresa_lead: str) -> str:
    agent_name = "Arquiteto de Propostas de Valor Personalizadas"
    prompt = f"""
    Você é um {agent_name}. Crie propostas de valor personalizadas para "{nome_empresa_lead}" (produto: "{seu_produto_ou_servico}").

    Análise Lead:
    ```
    {truncate_text(analise_lead, 3000)}
    ```
    Persona:
    ```
    {truncate_text(persona, 2000)}
    ```
    Aprofundamento Dores:
    ```
    {truncate_text(aprofundamento_dores, 3000)}
    ```
    Gatilhos de Compra/Eventos Relevantes:
    ```
    {truncate_text(gatilhos_compra, 2000)}
    ```
    Crie 2-3 propostas de valor distintas e concisas. Cada uma deve:
    1. Ser direcionada aos desafios/dores/gatilhos de "{nome_empresa_lead}" e da persona.
    2. Destacar benefício chave (quantificável ou qualitativamente forte).
    3. Ser formulada para ressoar (ex: "Para {nome_empresa_lead} que [dor/gatilho], nossa solução oferece [benefício], resultando em [resultado]").
    4. Ser curta para e-mail/conversa.

    Formato: Lista numerada.
    """
    return call_gemini_api_text_analyzer(prompt, f"{agent_name} para {nome_empresa_lead}")

def criar_mensagem_personalizada(plano_acao_final_tot: str, propostas_valor_customizadas: str, contatos_identificados: dict, seu_produto_ou_servico: str, url_lead: str, nome_empresa_lead: str, persona_nome_ficticio: str) -> str:
    agent_name = "Redator de Copywriting B2B Sênior (Prospecção)"
    # Determinar canal e contato da mensagem
    canal_sugerido = "E-mail" # Default
    destinatario_email = contatos_identificados.get("emails_encontrados", [])
    destinatario_instagram = contatos_identificados.get("instagram_perfis_encontrados", [])

    # Lógica simples para escolher o canal (pode ser melhorada com base no plano_acao_final_tot)
    if "LinkedIn" in plano_acao_final_tot: canal_sugerido = "LinkedIn"
    elif destinatario_email: canal_sugerido = "E-mail"
    elif destinatario_instagram: canal_sugerido = "Instagram DM"


    prompt = f"""
    Você é um {agent_name}. Crie uma mensagem de contato inicial para a persona (Nome Fictício: {persona_nome_ficticio if persona_nome_ficticio else 'o Tomador de Decisão'}) na empresa {nome_empresa_lead} (URL: {url_lead}), para "{seu_produto_ou_servico}".

    Plano de Ação Principal (ToT):
    ```
    {truncate_text(plano_acao_final_tot)}
    ```
    Propostas de Valor Customizadas:
    ```
    {truncate_text(propostas_valor_customizadas)}
    ```
    Contatos Disponíveis: {json.dumps(contatos_identificados)}

    Canal Preferencial (inferido do plano ou disponibilidade): {canal_sugerido}

    Redija uma mensagem para o canal indicado. A mensagem deve:
    1. Ser altamente personalizada para {nome_empresa_lead} e a persona.
    2. Incorporar uma das propostas de valor e o gancho do plano de ação.
    3. Clara, concisa, focada nos benefícios.
    4. CTA claro para uma breve conversa (ex: "Disponível para uma conversa de 15 min esta semana para explorar como podemos ajudar {nome_empresa_lead} a [benefício principal]?").
    5. Demonstrar pesquisa e entendimento.
    6. Se a análise inicial do lead (não mostrada aqui, mas inferida pelo plano) indicou "FALHA NA EXTRAÇÃO...", seja mais cauteloso.

    Formato:
    Canal: [E-mail/LinkedIn/Instagram DM]
    Assunto (se E-mail): [Assunto conciso e chamativo]
    Corpo da Mensagem:
    [Mensagem...]
    """
    return call_gemini_api_text_analyzer(prompt, f"{agent_name} para {nome_empresa_lead}")

def agente_sumarizador_briefing_interno(todos_os_dados_do_lead: dict) -> str:
    agent_name = "Assistente Executivo de Vendas (Briefing Rápido)"
    # Construir um resumo dos dados mais críticos para o prompt
    briefing_input = f"""
    Lead: {todos_os_dados_do_lead.get('company_name_inferred', 'N/A')}
    URL: {todos_os_dados_do_lead.get('lead_url', 'N/A')}
    Persona (Nome/Cargo): {truncate_text(todos_os_dados_do_lead.get('persona_desenvolvida', ''), 200)}
    Principal Dor/Oportunidade (Resumo): {truncate_text(todos_os_dados_do_lead.get('aprofundamento_pontos_de_dor', ''), 300)}
    Qualificação: {todos_os_dados_do_lead.get('qualificacao_do_lead', 'N/A')}
    Plano de Ação ToT (Resumo): {truncate_text(todos_os_dados_do_lead.get('plano_de_acao_final_tot', ''), 400)}
    Mensagem Gerada (Início): {truncate_text(todos_os_dados_do_lead.get('mensagem_personalizada_gerada', ''), 200)}
    Gatilho Principal (se houver): {truncate_text(todos_os_dados_do_lead.get('gatilhos_e_eventos_relevantes',''), 200)}
    """
    prompt = f"""
    Você é um {agent_name}. Compile um briefing ultra-conciso (máximo 5-7 bullet points principais) para o vendedor sobre o Lead, baseado nos seguintes dados consolidados.
    O objetivo é preparar o vendedor em 60 segundos.

    Dados Consolidados:
    ```
    {briefing_input}
    ```
    Destaque:
    - Empresa e Persona Chave.
    - Principal Dor/Oportunidade/Gatilho.
    - Estratégia de Abordagem Recomendada (do Plano ToT).
    - Gancho principal da mensagem de contato.
    - Uma possível objeção chave e como lidar (se inferível do plano de objeções).
    - Classificação de qualificação.
    """
    return call_gemini_api_text_analyzer(prompt, agent_name)


# --- Script Principal ---
if __name__ == "__main__":
    start_time_script = time.time()
    meu_produto_ou_servico = input("Qual produto ou serviço você está oferecendo? (Ex: 'nossa plataforma de IA para otimização de processos jurídicos'): ")
    if not meu_produto_ou_servico:
        print("Produto/serviço não informado. Usando um placeholder genérico.")
        meu_produto_ou_servico = "nossa solução inovadora para otimização e prospecção"
    print(f"Produto/Serviço configurado: '{meu_produto_ou_servico}'")

    # Lista de concorrentes (opcional, pode ser deixada vazia)
    meus_concorrentes_str = input("Liste seus principais concorrentes, separados por vírgula (ou deixe em branco): ")


    try:
        with open('leads.json', 'r', encoding='utf-8') as f:
            data_from_json_file = json.load(f)
    except FileNotFoundError:
        print("Erro: Arquivo 'leads.json' não encontrado na raiz do projeto.")
        exit(1)
    except json.JSONDecodeError as e:
        print(f"Erro: Arquivo 'leads.json' não é um JSON válido. Detalhes: {e}")
        exit(1)

    all_leads_processed_data = []

    if not isinstance(data_from_json_file, dict) or "sites_data" not in data_from_json_file:
        print(f"Erro: O conteúdo de 'leads.json' não tem a estrutura esperada (um dicionário com a chave 'sites_data').")
        exit(1)

    leads_list_to_process = data_from_json_file["sites_data"]

    if not isinstance(leads_list_to_process, list):
        print(f"Erro: O valor da chave 'sites_data' em 'leads.json' não é uma lista.")
        exit(1)

    total_leads_input = len(leads_list_to_process)
    print(f"Total de leads a processar do arquivo 'leads.json': {total_leads_input}")
    original_query_info = data_from_json_file.get("original_query", "Consulta original não especificada no JSON")
    print(f"Consulta original (do JSON) que gerou estes leads: {original_query_info}")

    # Limitar o número de leads a processar para testes, se desejado
    # leads_list_to_process = leads_list_to_process[:1] # Processa apenas o primeiro lead

    for i, lead_info_dict_raw in enumerate(leads_list_to_process):
        lead_start_time = time.time()
        if not isinstance(lead_info_dict_raw, dict):
            print(f"\nAVISO: Item {i+1}/{total_leads_input} na lista 'sites_data' não é um dicionário. Pulando.")
            all_leads_processed_data.append({
                "lead_url": f"Item inválido na posição {i}",
                "processing_status": "INVALID_LEAD_DATA_FORMAT",
                "error_message": "Item na lista 'sites_data' não é um dicionário."
            })
            continue

        current_lead_url = lead_info_dict_raw.get('url', f'URL Desconhecida - Lead Index {i}')
        print(f"\n======================================================================")
        print(f"Processando Lead {i+1}/{total_leads_input}: {current_lead_url}")
        print(f"======================================================================\n")

        google_search_data = lead_info_dict_raw.get("google_search_data", {})
        google_search_title = google_search_data.get("title", "Empresa Desconhecida")
        company_name_guess = google_search_title.split(" - ")[0].split(" | ")[0].split(": ")[0].strip()
        if "http" in company_name_guess or not company_name_guess or company_name_guess == "Empresa Desconhecida":
            if current_lead_url and 'URL Desconhecida' not in current_lead_url:
                try:
                    domain_parts = current_lead_url.split('/')[2].split('.')
                    meaningful_part = domain_parts[-2] if len(domain_parts) > 1 and domain_parts[-2] not in ["com", "org", "net", "co", "adv", "io", "app"] else domain_parts[0]
                    company_name_guess = meaningful_part.capitalize()
                except IndexError: company_name_guess = "Empresa Desconhecida"
            else: company_name_guess = "Empresa Desconhecida"
        print(f"Nome da empresa inferido: {company_name_guess}")

        # Dados do lead como string JSON para alguns prompts
        # Inclui apenas os campos relevantes do harvester
        lead_data_from_harvester_for_prompt = {
            "url": current_lead_url,
            "google_search_data": google_search_data,
            "extracted_text_content": lead_info_dict_raw.get("extracted_text_content", "Nenhum conteúdo extraído."),
            "extraction_status_message": lead_info_dict_raw.get("extraction_status_message", "Status desconhecido."),
        }
        lead_data_str_harvester = json.dumps(lead_data_from_harvester_for_prompt, indent=2, ensure_ascii=False)

        lead_output = {
            "lead_url": current_lead_url,
            "company_name_inferred": company_name_guess,
            "produto_servico_ofertado": meu_produto_ou_servico,
            "processing_status": "PENDING",
            "dados_enriquecidos_tavily": "Não processado",
            "contatos_identificados": {"emails_encontrados": [], "instagram_perfis_encontrados": [], "sugestao_pesquisa_tavily": ""},
            "analise_do_lead": "Não processado",
            "persona_desenvolvida": "Não processado",
            "aprofundamento_pontos_de_dor": "Não processado",
            "qualificacao_do_lead": "Não processado",
            "concorrentes_ou_solucoes_mencionadas": "Não processado",
            "perguntas_estrategicas_descoberta": "Não processado",
            "gatilhos_e_eventos_relevantes": "Não processado",
            "propostas_de_valor_customizadas": "Não processado",
            "estrategias_de_abordagem_propostas_tot": "Não processado",
            "avaliacao_das_estrategias_tot": "Não processado",
            "plano_de_acao_final_tot": "Não processado",
            "plano_de_abordagem_detalhado": "Não processado",
            "elaboracao_respostas_objecoes": "Não processado",
            "mensagem_personalizada_gerada": "Não processado",
            "briefing_interno_lead": "Não processado",
        }

        current_processing_step_name = "Inicialização"
        try:
            # ETAPA 0.1: Enriquecimento com Tavily (Condicional)
            current_processing_step_name = "Enriquecimento Tavily"
            print(f"--- {current_processing_step_name} ---")
            texto_extraido_inicial = lead_info_dict_raw.get("extracted_text_content", "")
            dados_enriquecidos = agente_enriquecimento_tavily(company_name_guess, texto_extraido_inicial)
            lead_output["dados_enriquecidos_tavily"] = dados_enriquecidos
            print(f"  Resultado: {truncate_text(dados_enriquecidos, 100)}...")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            # ETAPA 0.2: Extração de Contatos
            current_processing_step_name = "Extração de Contatos"
            print(f"--- {current_processing_step_name} ---")
            contatos = agente_extracao_contatos(texto_extraido_inicial, company_name_guess, meu_produto_ou_servico)
            lead_output["contatos_identificados"] = contatos
            print(f"  Resultado: E-mails: {contatos.get('emails_encontrados')}, Instagram: {contatos.get('instagram_perfis_encontrados')}")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            # ETAPA 1: Análise do Lead
            current_processing_step_name = "Análise do Lead"
            print(f"--- {current_processing_step_name} ---")
            analise = gerar_analise_lead(lead_data_str_harvester, dados_enriquecidos, meu_produto_ou_servico)
            lead_output["analise_do_lead"] = analise
            if analise.startswith("Erro:"): raise ValueError(f"Falha na {current_processing_step_name}. {analise}")
            print(f"  Resultado (início): {truncate_text(analise, 100)}...")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            # ETAPA 2: Criação da Persona
            current_processing_step_name = "Criação da Persona"
            print(f"--- {current_processing_step_name} ---")
            persona_criada = criar_persona(analise, meu_produto_ou_servico, current_lead_url)
            lead_output["persona_desenvolvida"] = persona_criada
            if persona_criada.startswith("Erro:"): raise ValueError(f"Falha na {current_processing_step_name}. {persona_criada}")
            print(f"  Resultado (início): {truncate_text(persona_criada, 100)}...")
            # Extrair nome fictício da persona para usar na mensagem, se possível
            persona_nome_ficticio_match = re.search(r"Nome fictício:\s*([^\n]+)", persona_criada, re.IGNORECASE)
            persona_nome_ficticio = persona_nome_ficticio_match.group(1).strip() if persona_nome_ficticio_match else ""
            time.sleep(INTER_STEP_DELAY_SECONDS)

            # ETAPA 3: Aprofundamento Pontos de Dor
            current_processing_step_name = "Aprofundamento Pontos de Dor"
            print(f"--- {current_processing_step_name} ---")
            dores = aprofundar_pontos_de_dor(analise, persona_criada, meu_produto_ou_servico, company_name_guess)
            lead_output["aprofundamento_pontos_de_dor"] = dores
            if dores.startswith("Erro:"): raise ValueError(f"Falha na {current_processing_step_name}. {dores}")
            print(f"  Resultado (início): {truncate_text(dores, 100)}...")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            # ETAPA 4: Qualificação do Lead
            current_processing_step_name = "Qualificação do Lead"
            print(f"--- {current_processing_step_name} ---")
            qualificacao = agente_qualificacao_lead(analise, persona_criada, dores, meu_produto_ou_servico)
            lead_output["qualificacao_do_lead"] = qualificacao
            if qualificacao.startswith("Erro:"): raise ValueError(f"Falha na {current_processing_step_name}. {qualificacao}")
            print(f"  Resultado: {truncate_text(qualificacao, 100)}...")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            # ETAPA 5: Identificação de Concorrentes
            current_processing_step_name = "Identificação de Concorrentes"
            print(f"--- {current_processing_step_name} ---")
            concorrentes = agente_identificacao_concorrentes(texto_extraido_inicial, meu_produto_ou_servico, meus_concorrentes_str)
            lead_output["concorrentes_ou_solucoes_mencionadas"] = concorrentes
            if concorrentes.startswith("Erro:"): raise ValueError(f"Falha na {current_processing_step_name}. {concorrentes}")
            print(f"  Resultado: {truncate_text(concorrentes, 100)}...")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            # ETAPA 6: Perguntas Estratégicas de Descoberta
            current_processing_step_name = "Perguntas Estratégicas de Descoberta"
            print(f"--- {current_processing_step_name} ---")
            perg_estrategicas = agente_gerador_perguntas_estrategicas(analise, persona_criada, dores)
            lead_output["perguntas_estrategicas_descoberta"] = perg_estrategicas
            if perg_estrategicas.startswith("Erro:"): raise ValueError(f"Falha na {current_processing_step_name}. {perg_estrategicas}")
            print(f"  Resultado (início): {truncate_text(perg_estrategicas, 100)}...")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            # ETAPA 7: Identificação de Gatilhos de Compra
            current_processing_step_name = "Identificação de Gatilhos de Compra"
            print(f"--- {current_processing_step_name} ---")
            gatilhos = agente_identificacao_gatilhos_compra(lead_data_str_harvester, dados_enriquecidos, meu_produto_ou_servico)
            lead_output["gatilhos_e_eventos_relevantes"] = gatilhos
            if gatilhos.startswith("Erro:"): raise ValueError(f"Falha na {current_processing_step_name}. {gatilhos}")
            print(f"  Resultado: {truncate_text(gatilhos, 100)}...")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            # ETAPA 8: Customizar Propostas de Valor
            current_processing_step_name = "Customização Propostas de Valor"
            print(f"--- {current_processing_step_name} ---")
            propostas_valor = customizar_proposta_de_valor(analise, persona_criada, dores, gatilhos, meu_produto_ou_servico, company_name_guess)
            lead_output["propostas_de_valor_customizadas"] = propostas_valor
            if propostas_valor.startswith("Erro:"): raise ValueError(f"Falha na {current_processing_step_name}. {propostas_valor}")
            print(f"  Resultado (início): {truncate_text(propostas_valor, 100)}...")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            # Construir sumário consolidado para agentes ToT
            sumario_lead_para_tot = json.dumps({k: truncate_text(str(v), 1000) for k, v in lead_output.items() if v != "Não processado"}, ensure_ascii=False, indent=2)

            # ETAPA 9: ToT - Geração de Estratégias
            current_processing_step_name = "ToT - Geração de Estratégias"
            print(f"--- {current_processing_step_name} ---")
            estrategias_tot = agente_gerador_estrategias_abordagem_tot(sumario_lead_para_tot, meu_produto_ou_servico)
            lead_output["estrategias_de_abordagem_propostas_tot"] = estrategias_tot
            if estrategias_tot.startswith("Erro:"): raise ValueError(f"Falha na {current_processing_step_name}. {estrategias_tot}")
            print(f"  Resultado (início): {truncate_text(estrategias_tot, 100)}...")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            # ETAPA 10: ToT - Avaliação de Estratégias
            current_processing_step_name = "ToT - Avaliação de Estratégias"
            print(f"--- {current_processing_step_name} ---")
            avaliacao_estrategias_tot = agente_avaliador_estrategias_tot(estrategias_tot, sumario_lead_para_tot)
            lead_output["avaliacao_das_estrategias_tot"] = avaliacao_estrategias_tot
            if avaliacao_estrategias_tot.startswith("Erro:"): raise ValueError(f"Falha na {current_processing_step_name}. {avaliacao_estrategias_tot}")
            print(f"  Resultado (início): {truncate_text(avaliacao_estrategias_tot, 100)}...")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            # ETAPA 11: ToT - Síntese do Plano de Ação Final
            current_processing_step_name = "ToT - Síntese Plano de Ação Final"
            print(f"--- {current_processing_step_name} ---")
            plano_acao_final_tot = agente_sintetizador_plano_acao_final_tot(avaliacao_estrategias_tot, estrategias_tot, sumario_lead_para_tot)
            lead_output["plano_de_acao_final_tot"] = plano_acao_final_tot
            if plano_acao_final_tot.startswith("Erro:"): raise ValueError(f"Falha na {current_processing_step_name}. {plano_acao_final_tot}")
            print(f"  Resultado (início): {truncate_text(plano_acao_final_tot, 100)}...")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            # ETAPA 12: Plano de Abordagem Detalhado
            current_processing_step_name = "Plano de Abordagem Detalhado"
            print(f"--- {current_processing_step_name} ---")
            plano_abordagem_det = desenvolver_plano_abordagem_detalhado(analise, persona_criada, dores, plano_acao_final_tot, meu_produto_ou_servico, current_lead_url)
            lead_output["plano_de_abordagem_detalhado"] = plano_abordagem_det
            if plano_abordagem_det.startswith("Erro:"): raise ValueError(f"Falha na {current_processing_step_name}. {plano_abordagem_det}")
            print(f"  Resultado (início): {truncate_text(plano_abordagem_det, 100)}...")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            # ETAPA 13: Elaboração de Respostas a Objeções
            current_processing_step_name = "Elaboração Respostas a Objeções"
            print(f"--- {current_processing_step_name} ---")
            respostas_obj = elaborar_respostas_objecoes(plano_abordagem_det, persona_criada, meu_produto_ou_servico, company_name_guess)
            lead_output["elaboracao_respostas_objecoes"] = respostas_obj
            if respostas_obj.startswith("Erro:"): raise ValueError(f"Falha na {current_processing_step_name}. {respostas_obj}")
            print(f"  Resultado (início): {truncate_text(respostas_obj, 100)}...")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            # ETAPA 14: Criação da Mensagem Personalizada
            current_processing_step_name = "Criação Mensagem Personalizada"
            print(f"--- {current_processing_step_name} ---")
            mensagem = criar_mensagem_personalizada(plano_acao_final_tot, propostas_valor, contatos, meu_produto_ou_servico, current_lead_url, company_name_guess, persona_nome_ficticio)
            lead_output["mensagem_personalizada_gerada"] = mensagem
            if mensagem.startswith("Erro:"): raise ValueError(f"Falha na {current_processing_step_name}. {mensagem}")
            print(f"  Resultado (início): {truncate_text(mensagem, 100)}...")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            # ETAPA 15: Briefing Interno
            current_processing_step_name = "Briefing Interno"
            print(f"--- {current_processing_step_name} ---")
            briefing = agente_sumarizador_briefing_interno(lead_output) # Passa todo o lead_output
            lead_output["briefing_interno_lead"] = briefing
            if briefing.startswith("Erro:"): raise ValueError(f"Falha na {current_processing_step_name}. {briefing}")
            print(f"  Resultado (início): {truncate_text(briefing, 100)}...")

            lead_output["processing_status"] = "SUCCESS"

        except ValueError as ve:
            print(f"FALHA na ETAPA '{current_processing_step_name}' para o lead {current_lead_url}: {ve}")
            lead_output["processing_status"] = f"FAILED_STEP_{current_processing_step_name.replace(' ', '_')}"
        except Exception as e_main_loop:
            print(f"ERRO INESPERADO na ETAPA '{current_processing_step_name}' para o lead {current_lead_url}: {e_main_loop}")
            traceback.print_exc()
            lead_output["processing_status"] = f"UNEXPECTED_ERROR_STEP_{current_processing_step_name.replace(' ', '_')}"

        all_leads_processed_data.append(lead_output)
        lead_end_time = time.time()
        print(f"\n--- Processamento para o lead {current_lead_url} finalizado com status: {lead_output['processing_status']} (Tempo: {lead_end_time - lead_start_time:.2f}s) ---")
        if i < total_leads_input - 1: # Não dormir após o último lead
            time.sleep(INTER_LEAD_PROCESSING_DELAY_SECONDS)


    # Salvar todos os resultados
    timestamp_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    output_filename = f"analyzed_leads_output_{MODEL_NAME.replace('.', '_').replace('-', '_')}_{timestamp_str}.json"
    output_filepath = os.path.join(OUTPUT_FOLDER, output_filename)
    try:
        final_output_data = {
            "processing_metadata": {
                "timestamp": datetime.datetime.now().isoformat(),
                "model_used_requested": MODEL_NAME,
                "model_actually_used_comment": f"A API tentou usar '{MODEL_NAME}'. Se houver falhas, verifique a disponibilidade deste modelo. Considere 'gemini-1.5-flash-latest' como alternativa.",
                "original_query_from_json": original_query_info,
                "product_service_offered": meu_produto_ou_servico,
                "total_leads_in_input_file": total_leads_input,
                "total_leads_processed_attempted": len(all_leads_processed_data),
                "successful_leads_fully_processed": sum(1 for lead in all_leads_processed_data if lead.get("processing_status") == "SUCCESS"),
                "partially_failed_leads": sum(1 for lead in all_leads_processed_data if "FAILED_STEP_" in lead.get("processing_status", "") or "UNEXPECTED_ERROR_STEP_" in lead.get("processing_status", "")),
                "invalid_lead_data_items": sum(1 for lead in all_leads_processed_data if lead.get("processing_status") == "INVALID_LEAD_DATA_FORMAT"),
            },
            "processed_leads_details": all_leads_processed_data
        }
        with open(output_filepath, 'w', encoding='utf-8') as f_out:
            json.dump(final_output_data, f_out, indent=2, ensure_ascii=False)
        print(f"\n\nProcessamento concluído. Resultados salvos em '{output_filepath}'")
    except Exception as e:
        print(f"Erro crítico ao salvar o arquivo de saída '{output_filepath}': {e}")
        traceback.print_exc()
    finally:
        end_time_script = time.time()
        print(f"Tempo total de execução do script: {end_time_script - start_time_script:.2f} segundos.")
