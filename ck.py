import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
import time

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configurações Globais ---
MAX_API_RETRIES = 3
API_RETRY_DELAY_SECONDS = 7 # Aumentado devido a mais chamadas por lead
INTER_STEP_DELAY_SECONDS = 1.5 # Delay entre sub-passos para um mesmo lead
INTER_LEAD_PROCESSING_DELAY_SECONDS = 4 # Delay entre processamento de leads diferentes

# !!! ATENÇÃO: NOME DO MODELO EXIGIDO PELO USUÁRIO !!!
# O modelo "gemini-2.0-flash" pode não ser um nome de modelo publicamente disponível
# ou pode ser um futuro nome. Se este script falhar na inicialização do modelo
# ou nas chamadas da API, tente substituí-lo por "gemini-1.5-flash-latest".
MODEL_NAME = "gemini-2.0-flash"

# --- Configuração do Modelo Gemini ---
try:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not GEMINI_API_KEY:
        raise ValueError("API Key do Gemini (GEMINI_API_KEY ou GOOGLE_API_KEY) não encontrada nas variáveis de ambiente.")

    genai.configure(api_key=GEMINI_API_KEY)

    generation_config = {
        "temperature": 0.65, # Ligeiramente reduzido para respostas mais focadas
        "top_p": 0.9,
        "top_k": 30,
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
    exit(1)

# --- Funções "Agente" ---

def call_gemini_api(prompt: str, agent_name: str, max_retries=MAX_API_RETRIES, delay_seconds=API_RETRY_DELAY_SECONDS) -> str:
    """
    Chama a API do Gemini com o prompt fornecido e trata retries.
    """
    # print(f"\n--- Agente '{agent_name}' iniciando... ---")
    # print(f"Prompt (primeiros 150 chars): {prompt[:150]}...")
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)

            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text
            elif response.prompt_feedback:
                error_message = f"Geração bloqueada ou problema com o prompt para o agente '{agent_name}'. Feedback: {response.prompt_feedback}"
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
            if "429" in str(e) or "rate limit" in str(e).lower() or "resource has been exhausted" in str(e).lower() or "503" in str(e):
                wait_time = delay_seconds * (2 ** attempt) # Exponential backoff
                print(f"Rate limit/recurso esgotado/serviço indisponível. Aguardando {wait_time} segundos antes de tentar novamente...")
                time.sleep(wait_time)
            elif attempt < max_retries - 1:
                print(f"Tentando novamente em {delay_seconds} segundos...")
                time.sleep(delay_seconds)
            else:
                return f"Erro: Falha ao chamar a API Gemini para o agente '{agent_name}' após {max_retries} tentativas: {e}"
    return f"Erro: Falha catastrófica ao obter resposta da API Gemini para o agente '{agent_name}'."


def gerar_analise_lead(lead_data_str: str, seu_produto_ou_servico: str) -> str:
    agent_name = "Analista de Leads Sênior"
    prompt = f"""
    Você é um {agent_name}.
    Sua tarefa é analisar profundamente os dados de um lead para identificar suas principais atividades, setor, desafios potenciais e oportunidades de negócio relevantes para um produto/serviço específico.

    Produto/Serviço a ser considerado: "{seu_produto_ou_servico}"

    Dados do Lead:
    ```json
    {lead_data_str}
    ```

    Com base nos dados fornecidos e no produto/serviço em foco, por favor, forneça:
    1.  Setor de atuação da empresa (ex: Advocacia, Consultoria Jurídica, Tecnologia Jurídica).
    2.  Principais serviços/produtos oferecidos pela empresa, inferidos do texto (ex: Direito Trabalhista, Direito Civil, Consultoria em LGPD, etc.).
    3.  Notícias recentes ou atividades importantes mencionadas (eventos, prêmios, projetos de lei, publicações, etc.). Se o texto mencionar "ANÁLISE DA IMAGEM PELA IA", resuma os pontos chave dessa análise.
    4.  Desafios ou necessidades potenciais INICIAIS que a empresa possa ter, especialmente aqueles que podem ser abordados por "{seu_produto_ou_servico}".
    5.  Qualquer informação sobre o tamanho da empresa, cultura, valores ou diferenciais que possa ser inferida.
    6.  Um diagnóstico geral da empresa e seu momento atual, e como "{seu_produto_ou_servico}" poderia se encaixar superficialmente.

    Formato da Saída Esperada:
    Um relatório de análise detalhado cobrindo os 6 pontos acima. Seja conciso mas completo.
    Se o `extracted_text_content` for "FALHA NA EXTRAÇÃO...", indique isso claramente e tente basear a análise nos `google_search_data` se possível, mencionando a limitação.
    Se não houver informações suficientes para um ponto, indique "Informação não disponível" ou similar.
    """
    return call_gemini_api(prompt, agent_name)

def criar_persona(analise_lead: str, seu_produto_ou_servico: str, url_lead: str) -> str:
    agent_name = "Especialista em Desenvolvimento de Personas B2B"
    prompt = f"""
    Você é um {agent_name}.
    Sua tarefa é criar uma persona detalhada do tomador de decisão ideal dentro da empresa analisada (URL: {url_lead}), com base na análise fornecida e no produto/serviço em foco.

    Produto/Serviço a ser considerado: "{seu_produto_ou_servico}"

    Análise do Lead:
    ```
    {analise_lead}
    ```

    Com base na análise do lead e no produto/serviço, crie uma persona específica para um tomador de decisão chave.
    Inclua:
    1.  Nome fictício e Cargo provável (ex: Sócio-Diretor, Gerente Jurídico, Coordenador de TI).
    2.  Suas principais responsabilidades e metas profissionais.
    3.  Seus maiores desafios e dores no contexto profissional atual da empresa (conforme a análise).
    4.  Suas motivações e o que buscam em novas soluções/parcerias.
    5.  Como "{seu_produto_ou_servico}" poderia ajudá-los especificamente a atingir seus objetivos ou superar seus desafios.

    Formato da Saída Esperada:
    Um perfil de persona detalhado, cobrindo os 5 pontos acima.
    Se a análise do lead for insuficiente, indique que a criação da persona é especulativa ou não pode ser detalhada.
    """
    return call_gemini_api(prompt, f"{agent_name} para {url_lead}")

def aprofundar_pontos_de_dor(analise_lead: str, persona: str, seu_produto_ou_servico: str, nome_empresa_lead: str) -> str:
    agent_name = "Especialista em Diagnóstico de Dores Empresariais"
    prompt = f"""
    Você é um {agent_name}.
    Com base na análise da empresa "{nome_empresa_lead}", na persona do tomador de decisão e no produto/serviço "{seu_produto_ou_servico}", sua tarefa é aprofundar os potenciais pontos de dor.

    Análise do Lead:
    ```
    {analise_lead}
    ```

    Persona do Tomador de Decisão:
    ```
    {persona}
    ```

    Produto/Serviço Foco: "{seu_produto_ou_servico}"

    Elabore sobre 3 a 5 pontos de dor específicos que a empresa "{nome_empresa_lead}" ou a persona identificada provavelmente enfrenta. Para cada ponto de dor:
    1.  Descreva o ponto de dor em detalhe.
    2.  Explique o possível impacto negativo desse problema nos negócios da empresa (ex: perda de eficiência, custos elevados, riscos legais, perda de clientes, etc.).
    3.  Sugira brevemente como "{seu_produto_ou_servico}" poderia começar a aliviar ou resolver essa dor específica.
    4.  Formule uma pergunta investigativa chave que poderia ser usada para confirmar e explorar essa dor com o lead.

    Formato da Saída Esperada:
    Uma lista detalhada dos pontos de dor, seus impactos, a conexão com o produto/serviço e uma pergunta investigativa para cada.
    Se as informações anteriores forem insuficientes, concentre-se nas dores mais genéricas do setor/tipo de empresa, adaptando-as.
    """
    return call_gemini_api(prompt, f"{agent_name} para {nome_empresa_lead}")


def desenvolver_plano_abordagem(analise_lead: str, persona: str, aprofundamento_dores: str, seu_produto_ou_servico: str, url_lead: str) -> str:
    agent_name = "Estrategista de Vendas Consultivas"
    prompt = f"""
    Você é um {agent_name}.
    Sua tarefa é desenvolver um plano de abordagem personalizado para a persona na empresa (URL: {url_lead}), focando em iniciar uma conversa sobre "{seu_produto_ou_servico}".

    Produto/Serviço: "{seu_produto_ou_servico}"

    Análise do Lead:
    ```
    {analise_lead}
    ```

    Persona do Tomador de Decisão:
    ```
    {persona}
    ```

    Aprofundamento dos Pontos de Dor:
    ```
    {aprofundamento_dores}
    ```

    Desenvolva um plano de abordagem estratégico, detalhando:
    1.  Canal de abordagem principal recomendado (ex: E-mail, LinkedIn, telefone breve) e justificativa.
    2.  Tom de voz e estilo de comunicação (ex: consultivo e empático, direto e focado em resultados).
    3.  Principais ganchos de valor de "{seu_produto_ou_servico}" a serem destacados, conectando diretamente aos pontos de dor identificados.
    4.  Lista de 2-3 objeções mais prováveis que podem surgir (ex: "já temos uma solução", "não temos orçamento agora", "muito complexo").
    5.  Estratégia inicial para despertar interesse: principais talking points e 2-3 perguntas abertas (além das investigativas de dor) para iniciar a conversa e qualificar o interesse.

    Formato da Saída Esperada:
    Um plano de abordagem claro e acionável.
    """
    return call_gemini_api(prompt, f"{agent_name} para {url_lead}")

def elaborar_respostas_objecoes(plano_abordagem: str, persona: str, seu_produto_ou_servico: str, nome_empresa_lead: str) -> str:
    agent_name = "Especialista em Contorno de Objeções B2B"
    prompt = f"""
    Você é um {agent_name}.
    Com base no plano de abordagem para a empresa "{nome_empresa_lead}", na persona e no produto/serviço "{seu_produto_ou_servico}", sua tarefa é elaborar respostas estratégicas para as objeções identificadas.

    Plano de Abordagem (contendo objeções previstas):
    ```
    {plano_abordagem}
    ```

    Persona do Tomador de Decisão:
    ```
    {persona}
    ```

    Produto/Serviço Foco: "{seu_produto_ou_servico}"

    Para cada objeção listada no plano de abordagem:
    1.  Reafirme a objeção.
    2.  Forneça um framework de resposta que seja empático, valide a preocupação (se aplicável) e reposicione o valor de "{seu_produto_ou_servico}" ou sugira um próximo passo para mitigar a objeção (ex: "Entendo sua preocupação com o orçamento. Muitos dos nossos clientes pensavam assim inicialmente, mas descobriram que [benefício de ROI/eficiência]. Poderíamos explorar rapidamente como isso se aplicaria ao seu caso específico?").
    3.  O objetivo não é vencer a discussão, mas manter a conversa aberta e direcionar para a descoberta de valor.

    Formato da Saída Esperada:
    Uma lista das objeções e suas respectivas respostas estratégicas e concisas.
    Se o plano de abordagem não listou objeções, sugira 2-3 objeções comuns para "{seu_produto_ou_servico}" e como respondê-las.
    """
    return call_gemini_api(prompt, f"{agent_name} para {nome_empresa_lead}")

def customizar_proposta_de_valor(analise_lead: str, persona: str, aprofundamento_dores: str, seu_produto_ou_servico: str, nome_empresa_lead: str) -> str:
    agent_name = "Arquiteto de Propostas de Valor Personalizadas"
    prompt = f"""
    Você é um {agent_name}.
    Sua missão é criar propostas de valor altamente personalizadas para "{nome_empresa_lead}" sobre o produto/serviço "{seu_produto_ou_servico}", com base em todas as informações coletadas.

    Análise do Lead:
    ```
    {analise_lead}
    ```

    Persona do Tomador de Decisão:
    ```
    {persona}
    ```

    Aprofundamento dos Pontos de Dor:
    ```
    {aprofundamento_dores}
    ```

    Produto/Serviço Foco: "{seu_produto_ou_servico}"

    Crie 2 a 3 propostas de valor distintas e concisas. Cada proposta deve:
    1.  Ser direcionada aos desafios e dores específicas de "{nome_empresa_lead}" e da persona, conforme identificado.
    2.  Destacar um benefício chave e quantificável (ou qualitativamente forte) de "{seu_produto_ou_servico}".
    3.  Ser formulada de maneira que ressoe diretamente com o lead (ex: "Para {nome_empresa_lead} que enfrenta [dor específica], nossa solução oferece [benefício chave], resultando em [resultado desejado]").
    4.  Ser curta o suficiente para ser usada em um e-mail inicial ou conversa.

    Formato da Saída Esperada:
    Uma lista numerada de 2-3 propostas de valor personalizadas.
    """
    return call_gemini_api(prompt, f"{agent_name} para {nome_empresa_lead}")


def criar_mensagem_personalizada(analise_lead: str, persona: str, plano_abordagem: str, propostas_valor_customizadas: str, seu_produto_ou_servico: str, url_lead: str, nome_empresa_lead: str) -> str:
    agent_name = "Redator de Copywriting B2B Sênior (Prospecção)"
    prompt = f"""
    Você é um {agent_name}.
    Sua tarefa é criar uma mensagem de contato inicial (e-mail ou LinkedIn) altamente personalizada e persuasiva para a persona identificada na empresa {nome_empresa_lead} (URL: {url_lead}), com o objetivo de gerar uma resposta positiva e agendar uma conversa sobre "{seu_produto_ou_servico}".

    Produto/Serviço: "{seu_produto_ou_servico}"

    Análise do Lead:
    ```
    {analise_lead}
    ```

    Persona do Tomador de Decisão:
    ```
    {persona}
    ```

    Plano de Abordagem:
    ```
    {plano_abordagem}
    ```

    Propostas de Valor Customizadas para {nome_empresa_lead}:
    ```
    {propostas_valor_customizadas}
    ```

    Redija uma mensagem de contato inicial.
    Indique claramente o canal (E-mail ou LinkedIn) com base no plano de abordagem.
    A mensagem deve:
    1.  Ser altamente personalizada para {nome_empresa_lead} e a persona. Use o nome da empresa e insights específicos da análise e das propostas de valor.
    2.  Incorporar uma das propostas de valor customizadas de forma natural.
    3.  Ser clara, concisa e focada nos benefícios para os desafios identificados.
    4.  Ter um call-to-action (CTA) claro para uma breve conversa (ex: "Gostaria de agendar uma conversa rápida de 15 minutos para explorar como podemos ajudar {nome_empresa_lead} a [benefício principal da proposta de valor]?").
    5.  Demonstrar pesquisa e entendimento genuíno.
    6.  Se a análise do lead indicou "FALHA NA EXTRAÇÃO...", adapte a mensagem para ser mais cautelosa, mas ainda use o nome da empresa e as propostas de valor (que podem ser baseadas em inferências do setor).

    Formato da Saída Esperada:
    A mensagem de contato inicial pronta para ser enviada, especificando o canal (Ex: "Canal: E-mail").
    Inclua um Assunto (Subject) conciso e chamativo se for um e-mail, possivelmente mencionando o nome da empresa ou um benefício chave.
    """
    return call_gemini_api(prompt, f"{agent_name} para {nome_empresa_lead}")

# --- Script Principal ---
if __name__ == "__main__":
    meu_produto_ou_servico = input("Qual produto ou serviço você está oferecendo? (Ex: 'nossa plataforma de IA para otimização de processos jurídicos'): ")
    if not meu_produto_ou_servico:
        print("Produto/serviço não informado. Usando um placeholder genérico.")
        meu_produto_ou_servico = "nossa solução inovadora para otimização e prospecção"
    print(f"Produto/Serviço configurado: '{meu_produto_ou_servico}'")

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

    total_leads = len(leads_list_to_process)
    print(f"Total de leads a processar: {total_leads}")
    original_query_info = data_from_json_file.get("original_query", "Consulta original não especificada")
    print(f"Consulta original que gerou estes leads: {original_query_info}")

    for i, lead_info_dict in enumerate(leads_list_to_process):
        if not isinstance(lead_info_dict, dict):
            print(f"\nAVISO: Item {i+1}/{total_leads} na lista 'sites_data' não é um dicionário. Pulando. Conteúdo: {str(lead_info_dict)[:100]}...")
            all_leads_processed_data.append({
                "lead_url": f"Item inválido na posição {i}",
                "processing_status": "INVALID_LEAD_DATA_FORMAT",
                "error_message": "Item na lista 'sites_data' não é um dicionário."
            })
            continue

        current_lead_url = lead_info_dict.get('url', f'URL Desconhecida - Lead Index {i}')
        print(f"\n======================================================================")
        print(f"Processando Lead {i+1}/{total_leads}: {current_lead_url}")
        print(f"======================================================================\n")

        google_search_title = lead_info_dict.get("google_search_data", {}).get("title", "Empresa Desconhecida")
        company_name_guess = google_search_title.split(" - ")[0].split(" | ")[0].split(": ")[0].strip()
        if "http" in company_name_guess or not company_name_guess or company_name_guess == "Empresa Desconhecida":
            if current_lead_url and 'URL Desconhecida' not in current_lead_url:
                try:
                    domain_parts = current_lead_url.split('/')[2].split('.')
                    meaningful_part = domain_parts[-2] if len(domain_parts) > 1 and domain_parts[-2] not in ["com", "org", "net", "co", "adv"] else domain_parts[0]
                    company_name_guess = meaningful_part.capitalize()
                except IndexError:
                    company_name_guess = "Empresa Desconhecida"
            else:
                company_name_guess = "Empresa Desconhecida"
        
        print(f"Nome da empresa inferido: {company_name_guess}")

        lead_data_for_prompt = {
            "url": current_lead_url,
            "google_search_data": lead_info_dict.get("google_search_data", {}),
            "extracted_text_content": lead_info_dict.get("extracted_text_content", "Nenhum conteúdo extraído."),
            "extraction_status_message": lead_info_dict.get("extraction_status_message", "Status desconhecido."),
        }
        lead_data_str = json.dumps(lead_data_for_prompt, indent=2, ensure_ascii=False)

        lead_output = {
            "lead_url": current_lead_url,
            "company_name_inferred": company_name_guess,
            "produto_servico_ofertado": meu_produto_ou_servico,
            "processing_status": "PENDING",
            "analise_do_lead": "Não processado",
            "persona_desenvolvida": "Não processado",
            "aprofundamento_pontos_de_dor": "Não processado",
            "plano_de_abordagem": "Não processado",
            "elaboracao_respostas_objecoes": "Não processado",
            "propostas_de_valor_customizadas": "Não processado",
            "mensagem_personalizada_gerada": "Não processado"
        }
        
        current_step = 0
        try:
            current_step = 1
            print(f"ETAPA {current_step}: Gerando análise do lead...")
            analise = gerar_analise_lead(lead_data_str, meu_produto_ou_servico)
            lead_output["analise_do_lead"] = analise
            if analise.startswith("Erro:"): raise ValueError(f"Falha na Análise do Lead. {analise}")
            print(f"--- Análise do Lead Concluída ---")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            current_step = 2
            print(f"ETAPA {current_step}: Criando persona...")
            persona_criada = criar_persona(analise, meu_produto_ou_servico, current_lead_url)
            lead_output["persona_desenvolvida"] = persona_criada
            if persona_criada.startswith("Erro:"): raise ValueError(f"Falha na Criação da Persona. {persona_criada}")
            print(f"--- Criação da Persona Concluída ---")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            current_step = 3
            print(f"ETAPA {current_step}: Aprofundando pontos de dor...")
            dores_aprofundadas = aprofundar_pontos_de_dor(analise, persona_criada, meu_produto_ou_servico, company_name_guess)
            lead_output["aprofundamento_pontos_de_dor"] = dores_aprofundadas
            if dores_aprofundadas.startswith("Erro:"): raise ValueError(f"Falha no Aprofundamento dos Pontos de Dor. {dores_aprofundadas}")
            print(f"--- Aprofundamento dos Pontos de Dor Concluído ---")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            current_step = 4
            print(f"ETAPA {current_step}: Desenvolvendo plano de abordagem...")
            plano = desenvolver_plano_abordagem(analise, persona_criada, dores_aprofundadas, meu_produto_ou_servico, current_lead_url)
            lead_output["plano_de_abordagem"] = plano
            if plano.startswith("Erro:"): raise ValueError(f"Falha no Plano de Abordagem. {plano}")
            print(f"--- Plano de Abordagem Concluído ---")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            current_step = 5
            print(f"ETAPA {current_step}: Elaborando respostas a objeções...")
            respostas_objecoes = elaborar_respostas_objecoes(plano, persona_criada, meu_produto_ou_servico, company_name_guess)
            lead_output["elaboracao_respostas_objecoes"] = respostas_objecoes
            if respostas_objecoes.startswith("Erro:"): raise ValueError(f"Falha na Elaboração de Respostas a Objeções. {respostas_objecoes}")
            print(f"--- Elaboração de Respostas a Objeções Concluída ---")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            current_step = 6
            print(f"ETAPA {current_step}: Customizando propostas de valor...")
            propostas_valor = customizar_proposta_de_valor(analise, persona_criada, dores_aprofundadas, meu_produto_ou_servico, company_name_guess)
            lead_output["propostas_de_valor_customizadas"] = propostas_valor
            if propostas_valor.startswith("Erro:"): raise ValueError(f"Falha na Customização de Propostas de Valor. {propostas_valor}")
            print(f"--- Customização de Propostas de Valor Concluída ---")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            current_step = 7
            print(f"ETAPA {current_step}: Criando mensagem personalizada...")
            mensagem = criar_mensagem_personalizada(analise, persona_criada, plano, propostas_valor, meu_produto_ou_servico, current_lead_url, company_name_guess)
            lead_output["mensagem_personalizada_gerada"] = mensagem
            if mensagem.startswith("Erro:"): raise ValueError(f"Falha na Mensagem Personalizada. {mensagem}")
            print(f"--- Mensagem Personalizada Concluída ---")
            
            lead_output["processing_status"] = "SUCCESS"

        except ValueError as ve: # Erro específico de uma etapa que já retorna "Erro:"
            print(f"FALHA na ETAPA {current_step} para o lead {current_lead_url}: {ve}")
            lead_output["processing_status"] = f"FAILED_STEP_{current_step}"
            # Os campos já terão a mensagem de erro da respectiva função
        except Exception as e_main_loop: # Outras exceções inesperadas
            print(f"ERRO INESPERADO na ETAPA {current_step} para o lead {current_lead_url}: {e_main_loop}")
            lead_output["processing_status"] = f"UNEXPECTED_ERROR_STEP_{current_step}"
            # Garante que o campo da etapa atual registre o erro se não foi preenchido
            if current_step == 1 and lead_output["analise_do_lead"] == "Não processado": lead_output["analise_do_lead"] = f"Erro inesperado: {e_main_loop}"
            elif current_step == 2 and lead_output["persona_desenvolvida"] == "Não processado": lead_output["persona_desenvolvida"] = f"Erro inesperado: {e_main_loop}"
            # ... adicionar para outros campos se necessário ...
        
        all_leads_processed_data.append(lead_output)
        
        print(f"\n--- Processamento para o lead {current_lead_url} finalizado com status: {lead_output['processing_status']} ---")
        time.sleep(INTER_LEAD_PROCESSING_DELAY_SECONDS)

    # Salvar todos os resultados
    output_filename = f"processed_leads_output_gemini_{MODEL_NAME.replace('.', '_').replace('-', '_')}_{time.strftime('%Y%m%d_%H%M%S')}.json"
    try:
        final_output_data = {
            "processing_metadata": {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "model_used_requested": MODEL_NAME, # Registra o modelo solicitado
                "model_actually_used_comment": f"A API tentou usar '{MODEL_NAME}'. Se houver falhas, verifique a disponibilidade deste modelo.",
                "original_query": original_query_info,
                "product_service_offered": meu_produto_ou_servico,
                "total_leads_in_input_file": total_leads,
                "total_leads_processed_attempted": len(all_leads_processed_data),
                "successful_leads": sum(1 for lead in all_leads_processed_data if lead.get("processing_status") == "SUCCESS"),
                "failed_leads": sum(1 for lead in all_leads_processed_data if lead.get("processing_status", "").startswith("FAILED_STEP_") or lead.get("processing_status", "").startswith("UNEXPECTED_ERROR_STEP_") ),
                "invalid_lead_data_items": sum(1 for lead in all_leads_processed_data if lead.get("processing_status") == "INVALID_LEAD_DATA_FORMAT"),
            },
            "processed_leads_details": all_leads_processed_data
        }
        with open(output_filename, 'w', encoding='utf-8') as f_out:
            json.dump(final_output_data, f_out, indent=2, ensure_ascii=False)
        print(f"\n\nProcessamento concluído. Resultados salvos em '{output_filename}'")
    except Exception as e:
=======
import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
import time

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configurações Globais ---
MAX_API_RETRIES = 3
API_RETRY_DELAY_SECONDS = 7 # Aumentado devido a mais chamadas por lead
INTER_STEP_DELAY_SECONDS = 1.5 # Delay entre sub-passos para um mesmo lead
INTER_LEAD_PROCESSING_DELAY_SECONDS = 4 # Delay entre processamento de leads diferentes

# !!! ATENÇÃO: NOME DO MODELO EXIGIDO PELO USUÁRIO !!!
# O modelo "gemini-2.0-flash" pode não ser um nome de modelo publicamente disponível
# ou pode ser um futuro nome. Se este script falhar na inicialização do modelo
# ou nas chamadas da API, tente substituí-lo por "gemini-1.5-flash-latest".
MODEL_NAME = "gemini-2.0-flash"

# --- Configuração do Modelo Gemini ---
try:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not GEMINI_API_KEY:
        raise ValueError("API Key do Gemini (GEMINI_API_KEY ou GOOGLE_API_KEY) não encontrada nas variáveis de ambiente.")

    genai.configure(api_key=GEMINI_API_KEY)

    generation_config = {
        "temperature": 0.65, # Ligeiramente reduzido para respostas mais focadas
        "top_p": 0.9,
        "top_k": 30,
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
    exit(1)

# --- Funções "Agente" ---

def call_gemini_api(prompt: str, agent_name: str, max_retries=MAX_API_RETRIES, delay_seconds=API_RETRY_DELAY_SECONDS) -> str:
    """
    Chama a API do Gemini com o prompt fornecido e trata retries.
    """
    # print(f"\n--- Agente '{agent_name}' iniciando... ---")
    # print(f"Prompt (primeiros 150 chars): {prompt[:150]}...")
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)

            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text
            elif response.prompt_feedback:
                error_message = f"Geração bloqueada ou problema com o prompt para o agente '{agent_name}'. Feedback: {response.prompt_feedback}"
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
            if "429" in str(e) or "rate limit" in str(e).lower() or "resource has been exhausted" in str(e).lower() or "503" in str(e):
                wait_time = delay_seconds * (2 ** attempt) # Exponential backoff
                print(f"Rate limit/recurso esgotado/serviço indisponível. Aguardando {wait_time} segundos antes de tentar novamente...")
                time.sleep(wait_time)
            elif attempt < max_retries - 1:
                print(f"Tentando novamente em {delay_seconds} segundos...")
                time.sleep(delay_seconds)
            else:
                return f"Erro: Falha ao chamar a API Gemini para o agente '{agent_name}' após {max_retries} tentativas: {e}"
    return f"Erro: Falha catastrófica ao obter resposta da API Gemini para o agente '{agent_name}'."


def gerar_analise_lead(lead_data_str: str, seu_produto_ou_servico: str) -> str:
    agent_name = "Analista de Leads Sênior"
    prompt = f"""
    Você é um {agent_name}.
    Sua tarefa é analisar profundamente os dados de um lead para identificar suas principais atividades, setor, desafios potenciais e oportunidades de negócio relevantes para um produto/serviço específico.

    Produto/Serviço a ser considerado: "{seu_produto_ou_servico}"

    Dados do Lead:
    ```json
    {lead_data_str}
    ```

    Com base nos dados fornecidos e no produto/serviço em foco, por favor, forneça:
    1.  Setor de atuação da empresa (ex: Advocacia, Consultoria Jurídica, Tecnologia Jurídica).
    2.  Principais serviços/produtos oferecidos pela empresa, inferidos do texto (ex: Direito Trabalhista, Direito Civil, Consultoria em LGPD, etc.).
    3.  Notícias recentes ou atividades importantes mencionadas (eventos, prêmios, projetos de lei, publicações, etc.). Se o texto mencionar "ANÁLISE DA IMAGEM PELA IA", resuma os pontos chave dessa análise.
    4.  Desafios ou necessidades potenciais INICIAIS que a empresa possa ter, especialmente aqueles que podem ser abordados por "{seu_produto_ou_servico}".
    5.  Qualquer informação sobre o tamanho da empresa, cultura, valores ou diferenciais que possa ser inferida.
    6.  Um diagnóstico geral da empresa e seu momento atual, e como "{seu_produto_ou_servico}" poderia se encaixar superficialmente.

    Formato da Saída Esperada:
    Um relatório de análise detalhado cobrindo os 6 pontos acima. Seja conciso mas completo.
    Se o `extracted_text_content` for "FALHA NA EXTRAÇÃO...", indique isso claramente e tente basear a análise nos `google_search_data` se possível, mencionando a limitação.
    Se não houver informações suficientes para um ponto, indique "Informação não disponível" ou similar.
    """
    return call_gemini_api(prompt, agent_name)

def criar_persona(analise_lead: str, seu_produto_ou_servico: str, url_lead: str) -> str:
    agent_name = "Especialista em Desenvolvimento de Personas B2B"
    prompt = f"""
    Você é um {agent_name}.
    Sua tarefa é criar uma persona detalhada do tomador de decisão ideal dentro da empresa analisada (URL: {url_lead}), com base na análise fornecida e no produto/serviço em foco.

    Produto/Serviço a ser considerado: "{seu_produto_ou_servico}"

    Análise do Lead:
    ```
    {analise_lead}
    ```

    Com base na análise do lead e no produto/serviço, crie uma persona específica para um tomador de decisão chave.
    Inclua:
    1.  Nome fictício e Cargo provável (ex: Sócio-Diretor, Gerente Jurídico, Coordenador de TI).
    2.  Suas principais responsabilidades e metas profissionais.
    3.  Seus maiores desafios e dores no contexto profissional atual da empresa (conforme a análise).
    4.  Suas motivações e o que buscam em novas soluções/parcerias.
    5.  Como "{seu_produto_ou_servico}" poderia ajudá-los especificamente a atingir seus objetivos ou superar seus desafios.

    Formato da Saída Esperada:
    Um perfil de persona detalhado, cobrindo os 5 pontos acima.
    Se a análise do lead for insuficiente, indique que a criação da persona é especulativa ou não pode ser detalhada.
    """
    return call_gemini_api(prompt, f"{agent_name} para {url_lead}")

def aprofundar_pontos_de_dor(analise_lead: str, persona: str, seu_produto_ou_servico: str, nome_empresa_lead: str) -> str:
    agent_name = "Especialista em Diagnóstico de Dores Empresariais"
    prompt = f"""
    Você é um {agent_name}.
    Com base na análise da empresa "{nome_empresa_lead}", na persona do tomador de decisão e no produto/serviço "{seu_produto_ou_servico}", sua tarefa é aprofundar os potenciais pontos de dor.

    Análise do Lead:
    ```
    {analise_lead}
    ```

    Persona do Tomador de Decisão:
    ```
    {persona}
    ```

    Produto/Serviço Foco: "{seu_produto_ou_servico}"

    Elabore sobre 3 a 5 pontos de dor específicos que a empresa "{nome_empresa_lead}" ou a persona identificada provavelmente enfrenta. Para cada ponto de dor:
    1.  Descreva o ponto de dor em detalhe.
    2.  Explique o possível impacto negativo desse problema nos negócios da empresa (ex: perda de eficiência, custos elevados, riscos legais, perda de clientes, etc.).
    3.  Sugira brevemente como "{seu_produto_ou_servico}" poderia começar a aliviar ou resolver essa dor específica.
    4.  Formule uma pergunta investigativa chave que poderia ser usada para confirmar e explorar essa dor com o lead.

    Formato da Saída Esperada:
    Uma lista detalhada dos pontos de dor, seus impactos, a conexão com o produto/serviço e uma pergunta investigativa para cada.
    Se as informações anteriores forem insuficientes, concentre-se nas dores mais genéricas do setor/tipo de empresa, adaptando-as.
    """
    return call_gemini_api(prompt, f"{agent_name} para {nome_empresa_lead}")


def desenvolver_plano_abordagem(analise_lead: str, persona: str, aprofundamento_dores: str, seu_produto_ou_servico: str, url_lead: str) -> str:
    agent_name = "Estrategista de Vendas Consultivas"
    prompt = f"""
    Você é um {agent_name}.
    Sua tarefa é desenvolver um plano de abordagem personalizado para a persona na empresa (URL: {url_lead}), focando em iniciar uma conversa sobre "{seu_produto_ou_servico}".

    Produto/Serviço: "{seu_produto_ou_servico}"

    Análise do Lead:
    ```
    {analise_lead}
    ```

    Persona do Tomador de Decisão:
    ```
    {persona}
    ```

    Aprofundamento dos Pontos de Dor:
    ```
    {aprofundamento_dores}
    ```

    Desenvolva um plano de abordagem estratégico, detalhando:
    1.  Canal de abordagem principal recomendado (ex: E-mail, LinkedIn, telefone breve) e justificativa.
    2.  Tom de voz e estilo de comunicação (ex: consultivo e empático, direto e focado em resultados).
    3.  Principais ganchos de valor de "{seu_produto_ou_servico}" a serem destacados, conectando diretamente aos pontos de dor identificados.
    4.  Lista de 2-3 objeções mais prováveis que podem surgir (ex: "já temos uma solução", "não temos orçamento agora", "muito complexo").
    5.  Estratégia inicial para despertar interesse: principais talking points e 2-3 perguntas abertas (além das investigativas de dor) para iniciar a conversa e qualificar o interesse.

    Formato da Saída Esperada:
    Um plano de abordagem claro e acionável.
    """
    return call_gemini_api(prompt, f"{agent_name} para {url_lead}")

def elaborar_respostas_objecoes(plano_abordagem: str, persona: str, seu_produto_ou_servico: str, nome_empresa_lead: str) -> str:
    agent_name = "Especialista em Contorno de Objeções B2B"
    prompt = f"""
    Você é um {agent_name}.
    Com base no plano de abordagem para a empresa "{nome_empresa_lead}", na persona e no produto/serviço "{seu_produto_ou_servico}", sua tarefa é elaborar respostas estratégicas para as objeções identificadas.

    Plano de Abordagem (contendo objeções previstas):
    ```
    {plano_abordagem}
    ```

    Persona do Tomador de Decisão:
    ```
    {persona}
    ```

    Produto/Serviço Foco: "{seu_produto_ou_servico}"

    Para cada objeção listada no plano de abordagem:
    1.  Reafirme a objeção.
    2.  Forneça um framework de resposta que seja empático, valide a preocupação (se aplicável) e reposicione o valor de "{seu_produto_ou_servico}" ou sugira um próximo passo para mitigar a objeção (ex: "Entendo sua preocupação com o orçamento. Muitos dos nossos clientes pensavam assim inicialmente, mas descobriram que [benefício de ROI/eficiência]. Poderíamos explorar rapidamente como isso se aplicaria ao seu caso específico?").
    3.  O objetivo não é vencer a discussão, mas manter a conversa aberta e direcionar para a descoberta de valor.

    Formato da Saída Esperada:
    Uma lista das objeções e suas respectivas respostas estratégicas e concisas.
    Se o plano de abordagem não listou objeções, sugira 2-3 objeções comuns para "{seu_produto_ou_servico}" e como respondê-las.
    """
    return call_gemini_api(prompt, f"{agent_name} para {nome_empresa_lead}")

def customizar_proposta_de_valor(analise_lead: str, persona: str, aprofundamento_dores: str, seu_produto_ou_servico: str, nome_empresa_lead: str) -> str:
    agent_name = "Arquiteto de Propostas de Valor Personalizadas"
    prompt = f"""
    Você é um {agent_name}.
    Sua missão é criar propostas de valor altamente personalizadas para "{nome_empresa_lead}" sobre o produto/serviço "{seu_produto_ou_servico}", com base em todas as informações coletadas.

    Análise do Lead:
    ```
    {analise_lead}
    ```

    Persona do Tomador de Decisão:
    ```
    {persona}
    ```

    Aprofundamento dos Pontos de Dor:
    ```
    {aprofundamento_dores}
    ```

    Produto/Serviço Foco: "{seu_produto_ou_servico}"

    Crie 2 a 3 propostas de valor distintas e concisas. Cada proposta deve:
    1.  Ser direcionada aos desafios e dores específicas de "{nome_empresa_lead}" e da persona, conforme identificado.
    2.  Destacar um benefício chave e quantificável (ou qualitativamente forte) de "{seu_produto_ou_servico}".
    3.  Ser formulada de maneira que ressoe diretamente com o lead (ex: "Para {nome_empresa_lead} que enfrenta [dor específica], nossa solução oferece [benefício chave], resultando em [resultado desejado]").
    4.  Ser curta o suficiente para ser usada em um e-mail inicial ou conversa.

    Formato da Saída Esperada:
    Uma lista numerada de 2-3 propostas de valor personalizadas.
    """
    return call_gemini_api(prompt, f"{agent_name} para {nome_empresa_lead}")


def criar_mensagem_personalizada(analise_lead: str, persona: str, plano_abordagem: str, propostas_valor_customizadas: str, seu_produto_ou_servico: str, url_lead: str, nome_empresa_lead: str) -> str:
    agent_name = "Redator de Copywriting B2B Sênior (Prospecção)"
    prompt = f"""
    Você é um {agent_name}.
    Sua tarefa é criar uma mensagem de contato inicial (e-mail ou LinkedIn) altamente personalizada e persuasiva para a persona identificada na empresa {nome_empresa_lead} (URL: {url_lead}), com o objetivo de gerar uma resposta positiva e agendar uma conversa sobre "{seu_produto_ou_servico}".

    Produto/Serviço: "{seu_produto_ou_servico}"

    Análise do Lead:
    ```
    {analise_lead}
    ```

    Persona do Tomador de Decisão:
    ```
    {persona}
    ```

    Plano de Abordagem:
    ```
    {plano_abordagem}
    ```

    Propostas de Valor Customizadas para {nome_empresa_lead}:
    ```
    {propostas_valor_customizadas}
    ```

    Redija uma mensagem de contato inicial.
    Indique claramente o canal (E-mail ou LinkedIn) com base no plano de abordagem.
    A mensagem deve:
    1.  Ser altamente personalizada para {nome_empresa_lead} e a persona. Use o nome da empresa e insights específicos da análise e das propostas de valor.
    2.  Incorporar uma das propostas de valor customizadas de forma natural.
    3.  Ser clara, concisa e focada nos benefícios para os desafios identificados.
    4.  Ter um call-to-action (CTA) claro para uma breve conversa (ex: "Gostaria de agendar uma conversa rápida de 15 minutos para explorar como podemos ajudar {nome_empresa_lead} a [benefício principal da proposta de valor]?").
    5.  Demonstrar pesquisa e entendimento genuíno.
    6.  Se a análise do lead indicou "FALHA NA EXTRAÇÃO...", adapte a mensagem para ser mais cautelosa, mas ainda use o nome da empresa e as propostas de valor (que podem ser baseadas em inferências do setor).

    Formato da Saída Esperada:
    A mensagem de contato inicial pronta para ser enviada, especificando o canal (Ex: "Canal: E-mail").
    Inclua um Assunto (Subject) conciso e chamativo se for um e-mail, possivelmente mencionando o nome da empresa ou um benefício chave.
    """
    return call_gemini_api(prompt, f"{agent_name} para {nome_empresa_lead}")

# --- Script Principal ---
if __name__ == "__main__":
    meu_produto_ou_servico = input("Qual produto ou serviço você está oferecendo? (Ex: 'nossa plataforma de IA para otimização de processos jurídicos'): ")
    if not meu_produto_ou_servico:
        print("Produto/serviço não informado. Usando um placeholder genérico.")
        meu_produto_ou_servico = "nossa solução inovadora para otimização e prospecção"
    print(f"Produto/Serviço configurado: '{meu_produto_ou_servico}'")

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

    total_leads = len(leads_list_to_process)
    print(f"Total de leads a processar: {total_leads}")
    original_query_info = data_from_json_file.get("original_query", "Consulta original não especificada")
    print(f"Consulta original que gerou estes leads: {original_query_info}")

    for i, lead_info_dict in enumerate(leads_list_to_process):
        if not isinstance(lead_info_dict, dict):
            print(f"\nAVISO: Item {i+1}/{total_leads} na lista 'sites_data' não é um dicionário. Pulando. Conteúdo: {str(lead_info_dict)[:100]}...")
            all_leads_processed_data.append({
                "lead_url": f"Item inválido na posição {i}",
                "processing_status": "INVALID_LEAD_DATA_FORMAT",
                "error_message": "Item na lista 'sites_data' não é um dicionário."
            })
            continue

        current_lead_url = lead_info_dict.get('url', f'URL Desconhecida - Lead Index {i}')
        print(f"\n======================================================================")
        print(f"Processando Lead {i+1}/{total_leads}: {current_lead_url}")
        print(f"======================================================================\n")

        google_search_title = lead_info_dict.get("google_search_data", {}).get("title", "Empresa Desconhecida")
        company_name_guess = google_search_title.split(" - ")[0].split(" | ")[0].split(": ")[0].strip()
        if "http" in company_name_guess or not company_name_guess or company_name_guess == "Empresa Desconhecida":
            if current_lead_url and 'URL Desconhecida' not in current_lead_url:
                try:
                    domain_parts = current_lead_url.split('/')[2].split('.')
                    meaningful_part = domain_parts[-2] if len(domain_parts) > 1 and domain_parts[-2] not in ["com", "org", "net", "co", "adv"] else domain_parts[0]
                    company_name_guess = meaningful_part.capitalize()
                except IndexError:
                    company_name_guess = "Empresa Desconhecida"
            else:
                company_name_guess = "Empresa Desconhecida"
        
        print(f"Nome da empresa inferido: {company_name_guess}")

        lead_data_for_prompt = {
            "url": current_lead_url,
            "google_search_data": lead_info_dict.get("google_search_data", {}),
            "extracted_text_content": lead_info_dict.get("extracted_text_content", "Nenhum conteúdo extraído."),
            "extraction_status_message": lead_info_dict.get("extraction_status_message", "Status desconhecido."),
        }
        lead_data_str = json.dumps(lead_data_for_prompt, indent=2, ensure_ascii=False)

        lead_output = {
            "lead_url": current_lead_url,
            "company_name_inferred": company_name_guess,
            "produto_servico_ofertado": meu_produto_ou_servico,
            "processing_status": "PENDING",
            "analise_do_lead": "Não processado",
            "persona_desenvolvida": "Não processado",
            "aprofundamento_pontos_de_dor": "Não processado",
            "plano_de_abordagem": "Não processado",
            "elaboracao_respostas_objecoes": "Não processado",
            "propostas_de_valor_customizadas": "Não processado",
            "mensagem_personalizada_gerada": "Não processado"
        }
        
        current_step = 0
        try:
            current_step = 1
            print(f"ETAPA {current_step}: Gerando análise do lead...")
            analise = gerar_analise_lead(lead_data_str, meu_produto_ou_servico)
            lead_output["analise_do_lead"] = analise
            if analise.startswith("Erro:"): raise ValueError(f"Falha na Análise do Lead. {analise}")
            print(f"--- Análise do Lead Concluída ---")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            current_step = 2
            print(f"ETAPA {current_step}: Criando persona...")
            persona_criada = criar_persona(analise, meu_produto_ou_servico, current_lead_url)
            lead_output["persona_desenvolvida"] = persona_criada
            if persona_criada.startswith("Erro:"): raise ValueError(f"Falha na Criação da Persona. {persona_criada}")
            print(f"--- Criação da Persona Concluída ---")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            current_step = 3
            print(f"ETAPA {current_step}: Aprofundando pontos de dor...")
            dores_aprofundadas = aprofundar_pontos_de_dor(analise, persona_criada, meu_produto_ou_servico, company_name_guess)
            lead_output["aprofundamento_pontos_de_dor"] = dores_aprofundadas
            if dores_aprofundadas.startswith("Erro:"): raise ValueError(f"Falha no Aprofundamento dos Pontos de Dor. {dores_aprofundadas}")
            print(f"--- Aprofundamento dos Pontos de Dor Concluído ---")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            current_step = 4
            print(f"ETAPA {current_step}: Desenvolvendo plano de abordagem...")
            plano = desenvolver_plano_abordagem(analise, persona_criada, dores_aprofundadas, meu_produto_ou_servico, current_lead_url)
            lead_output["plano_de_abordagem"] = plano
            if plano.startswith("Erro:"): raise ValueError(f"Falha no Plano de Abordagem. {plano}")
            print(f"--- Plano de Abordagem Concluído ---")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            current_step = 5
            print(f"ETAPA {current_step}: Elaborando respostas a objeções...")
            respostas_objecoes = elaborar_respostas_objecoes(plano, persona_criada, meu_produto_ou_servico, company_name_guess)
            lead_output["elaboracao_respostas_objecoes"] = respostas_objecoes
            if respostas_objecoes.startswith("Erro:"): raise ValueError(f"Falha na Elaboração de Respostas a Objeções. {respostas_objecoes}")
            print(f"--- Elaboração de Respostas a Objeções Concluída ---")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            current_step = 6
            print(f"ETAPA {current_step}: Customizando propostas de valor...")
            propostas_valor = customizar_proposta_de_valor(analise, persona_criada, dores_aprofundadas, meu_produto_ou_servico, company_name_guess)
            lead_output["propostas_de_valor_customizadas"] = propostas_valor
            if propostas_valor.startswith("Erro:"): raise ValueError(f"Falha na Customização de Propostas de Valor. {propostas_valor}")
            print(f"--- Customização de Propostas de Valor Concluída ---")
            time.sleep(INTER_STEP_DELAY_SECONDS)

            current_step = 7
            print(f"ETAPA {current_step}: Criando mensagem personalizada...")
            mensagem = criar_mensagem_personalizada(analise, persona_criada, plano, propostas_valor, meu_produto_ou_servico, current_lead_url, company_name_guess)
            lead_output["mensagem_personalizada_gerada"] = mensagem
            if mensagem.startswith("Erro:"): raise ValueError(f"Falha na Mensagem Personalizada. {mensagem}")
            print(f"--- Mensagem Personalizada Concluída ---")
            
            lead_output["processing_status"] = "SUCCESS"

        except ValueError as ve: # Erro específico de uma etapa que já retorna "Erro:"
            print(f"FALHA na ETAPA {current_step} para o lead {current_lead_url}: {ve}")
            lead_output["processing_status"] = f"FAILED_STEP_{current_step}"
            # Os campos já terão a mensagem de erro da respectiva função
        except Exception as e_main_loop: # Outras exceções inesperadas
            print(f"ERRO INESPERADO na ETAPA {current_step} para o lead {current_lead_url}: {e_main_loop}")
            lead_output["processing_status"] = f"UNEXPECTED_ERROR_STEP_{current_step}"
            # Garante que o campo da etapa atual registre o erro se não foi preenchido
            if current_step == 1 and lead_output["analise_do_lead"] == "Não processado": lead_output["analise_do_lead"] = f"Erro inesperado: {e_main_loop}"
            elif current_step == 2 and lead_output["persona_desenvolvida"] == "Não processado": lead_output["persona_desenvolvida"] = f"Erro inesperado: {e_main_loop}"
            # ... adicionar para outros campos se necessário ...
        
        all_leads_processed_data.append(lead_output)
        
        print(f"\n--- Processamento para o lead {current_lead_url} finalizado com status: {lead_output['processing_status']} ---")
        time.sleep(INTER_LEAD_PROCESSING_DELAY_SECONDS)

    # Salvar todos os resultados
    output_filename = f"processed_leads_output_gemini_{MODEL_NAME.replace('.', '_').replace('-', '_')}_{time.strftime('%Y%m%d_%H%M%S')}.json"
    try:
        final_output_data = {
            "processing_metadata": {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "model_used_requested": MODEL_NAME, # Registra o modelo solicitado
                "model_actually_used_comment": f"A API tentou usar '{MODEL_NAME}'. Se houver falhas, verifique a disponibilidade deste modelo.",
                "original_query": original_query_info,
                "product_service_offered": meu_produto_ou_servico,
                "total_leads_in_input_file": total_leads,
                "total_leads_processed_attempted": len(all_leads_processed_data),
                "successful_leads": sum(1 for lead in all_leads_processed_data if lead.get("processing_status") == "SUCCESS"),
                "failed_leads": sum(1 for lead in all_leads_processed_data if lead.get("processing_status", "").startswith("FAILED_STEP_") or lead.get("processing_status", "").startswith("UNEXPECTED_ERROR_STEP_") ),
                "invalid_lead_data_items": sum(1 for lead in all_leads_processed_data if lead.get("processing_status") == "INVALID_LEAD_DATA_FORMAT"),
            },
            "processed_leads_details": all_leads_processed_data
        }
        with open(output_filename, 'w', encoding='utf-8') as f_out:
            json.dump(final_output_data, f_out, indent=2, ensure_ascii=False)
        print(f"\n\nProcessamento concluído. Resultados salvos em '{output_filename}'")
    except Exception as e:
        print(f"Erro crítico ao salvar o arquivo de saída '{output_filename}': {e}")