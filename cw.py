import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
import time # Para adicionar um pequeno delay e evitar rate limits

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configuração do Modelo Gemini ---
try:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not GEMINI_API_KEY:
        raise ValueError("API Key do Gemini (GEMINI_API_KEY ou GOOGLE_API_KEY) não encontrada nas variáveis de ambiente.")
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Configurações de geração
    generation_config = {
        "temperature": 0.7,
        "top_p": 1, 
        "top_k": 1, 
        # "max_output_tokens": 8192, 
    }

    # Configurações de segurança
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash-latest",
        generation_config=generation_config,
        safety_settings=safety_settings
    )
    print("Modelo Gemini configurado com sucesso.")

except Exception as e:
    print(f"Erro ao inicializar o modelo Gemini: {e}")
    exit()

# --- Funções para cada etapa do processo ---

def call_gemini_api(prompt: str, max_retries=3, delay_seconds=5) -> str:
    """
    Chama a API do Gemini com o prompt fornecido e trata retries.
    """
    for attempt in range(max_retries):
        try:
            # print(f"\n--- Enviando prompt para Gemini (Tentativa {attempt + 1}) ---")
            # print(f"Prompt (primeiros 300 chars): {prompt[:300]}...")
            # print("--- Aguardando resposta... ---")
            
            response = model.generate_content(prompt)
            
            # Debug: Imprimir a resposta completa para análise
            # print(f"Resposta completa do Gemini (Tentativa {attempt + 1}): {response}")

            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                # print("--- Resposta recebida ---")
                return response.candidates[0].content.parts[0].text
            elif response.prompt_feedback:
                error_message = f"Geração bloqueada ou problema com o prompt. Feedback: {response.prompt_feedback}"
                print(f"Erro Gemini: {error_message}")
                if attempt < max_retries - 1:
                    print(f"Tentando novamente em {delay_seconds} segundos...")
                    time.sleep(delay_seconds)
                else:
                    return f"Erro: {error_message}" 
            else:
                # print("--- Resposta vazia ou inesperada ---")
                if attempt < max_retries - 1:
                    print(f"Resposta inesperada ou vazia. Tentando novamente em {delay_seconds} segundos...")
                    time.sleep(delay_seconds)
                else:
                    return "Erro: Resposta vazia ou inesperada do modelo após múltiplas tentativas."

        except Exception as e:
            print(f"Erro ao chamar a API Gemini (Tentativa {attempt + 1}): {e}")
            if "429" in str(e) or "rate limit" in str(e).lower() or "resource has been exhausted" in str(e).lower(): 
                wait_time = delay_seconds * (attempt + 2) 
                print(f"Rate limit atingido ou recurso esgotado. Aguardando {wait_time} segundos antes de tentar novamente...")
                time.sleep(wait_time)
            elif attempt < max_retries - 1:
                print(f"Tentando novamente em {delay_seconds} segundos...")
                time.sleep(delay_seconds)
            else:
                return f"Erro: Falha ao chamar a API Gemini após {max_retries} tentativas: {e}"
    return "Erro: Falha ao obter resposta da API Gemini."


def gerar_analise_lead(lead_data_str: str, seu_produto_ou_servico: str) -> str:
    prompt = f"""
    Você é um Analista de Leads Sênior.
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
    4.  Desafios ou necessidades potenciais que a empresa possa ter, especialmente aqueles que podem ser abordados por "{seu_produto_ou_servico}". Considere o tipo de empresa (escritório de advocacia, plataforma de serviços jurídicos, etc.).
    5.  Qualquer informação sobre o tamanho da empresa, cultura, valores ou diferenciais que possa ser inferida.
    6.  Um diagnóstico geral da empresa e seu momento atual, e como "{seu_produto_ou_servico}" poderia se encaixar.

    Formato da Saída Esperada:
    Um relatório de análise detalhado cobrindo os 6 pontos acima. Seja conciso mas completo.
    Se o `extracted_text_content` for "FALHA NA EXTRAÇÃO...", indique isso claramente e tente basear a análise nos `google_search_data` se possível, mencionando a limitação.
    """
    print("Gerando análise do lead...")
    return call_gemini_api(prompt)

def criar_persona(analise_lead: str, seu_produto_ou_servico: str, url_lead: str) -> str:
    prompt = f"""
    Você é um Especialista em Desenvolvimento de Personas B2B.
    Sua tarefa é criar uma persona detalhada do tomador de decisão ideal dentro da empresa analisada (URL: {url_lead}), com base na análise fornecida e no produto/serviço em foco.

    Produto/Serviço a ser considerado: "{seu_produto_ou_servico}"

    Análise do Lead:
    ```
    {analise_lead}
    ```

    Com base na análise do lead e no produto/serviço, crie uma persona específica para um tomador de decisão chave.
    Inclua:
    1.  Nome fictício e Cargo provável (ex: Sócio-Diretor, Gerente de Marketing Jurídico, Coordenador de TI, Advogado Responsável por Inovação, etc.).
    2.  Suas principais responsabilidades e metas profissionais.
    3.  Seus maiores desafios e dores no contexto profissional atual da empresa (conforme a análise).
    4.  Suas motivações e o que buscam em novas soluções/parcerias.
    5.  Como "{seu_produto_ou_servico}" poderia ajudá-los especificamente a atingir seus objetivos ou superar seus desafios.

    Formato da Saída Esperada:
    Um perfil de persona detalhado, cobrindo os 5 pontos acima.
    """
    print("Criando persona...")
    return call_gemini_api(prompt)

def desenvolver_plano_abordagem(analise_lead: str, persona: str, seu_produto_ou_servico: str, url_lead: str) -> str:
    prompt = f"""
    Você é um Estrategista de Vendas e Abordagem Consultiva.
    Sua tarefa é desenvolver um plano de abordagem personalizado e eficaz para a persona identificada na empresa (URL: {url_lead}), com o objetivo de iniciar uma conversa sobre um produto/serviço específico.

    Produto/Serviço a ser considerado: "{seu_produto_ou_servico}"

    Análise do Lead:
    ```
    {analise_lead}
    ```

    Persona do Tomador de Decisão:
    ```
    {persona}
    ```

    Com base na análise do lead, na persona criada e no produto/serviço, desenvolva um plano de abordagem estratégico.
    Detalhe:
    1.  Canal de abordagem principal recomendado (ex: E-mail, LinkedIn) e por quê.
    2.  Tom de voz e estilo de comunicação (ex: formal e direto, consultivo e educacional, amigável e inovador).
    3.  Principais pontos de valor de "{seu_produto_ou_servico}" a serem destacados para ESTA persona e ESTA empresa.
    4.  Possíveis objeções que podem surgir (ex: "já temos uma solução", "não temos orçamento", "não é prioridade") e como respondê-las brevemente.
    5.  O que falar e como falar para despertar interesse genuíno (principais talking points, perguntas abertas para iniciar a conversa).

    Formato da Saída Esperada:
    Um plano de abordagem claro e acionável, cobrindo os 5 pontos acima.
    """
    print("Desenvolvendo plano de abordagem...")
    return call_gemini_api(prompt)

def criar_mensagem_personalizada(analise_lead: str, persona: str, plano_abordagem: str, seu_produto_ou_servico: str, url_lead: str, nome_empresa_lead: str) -> str:
    prompt = f"""
    Você é um Redator de Copywriting B2B Sênior.
    Sua tarefa é criar uma mensagem de contato inicial (e-mail ou LinkedIn) altamente personalizada e persuasiva para a persona identificada na empresa {nome_empresa_lead} (URL: {url_lead}), com o objetivo de gerar uma resposta positiva e agendar uma conversa sobre um produto/serviço específico.

    Produto/Serviço a ser considerado: "{seu_produto_ou_servico}"

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

    Com base na análise do lead, na persona, no plano de abordagem e no produto/serviço, redija uma mensagem de contato inicial.
    Indique claramente se a mensagem é para E-mail ou LinkedIn (escolha o mais apropriado com base no plano de abordagem).
    A mensagem deve ser:
    1.  Altamente personalizada para a empresa {nome_empresa_lead} e a persona. Use o nome da empresa e insights específicos da análise.
    2.  Clara, concisa e focada nos benefícios de "{seu_produto_ou_servico}" para os desafios identificados.
    3.  Ter um call-to-action (CTA) claro para uma breve conversa (ex: "Gostaria de agendar uma conversa rápida de 15 minutos para explorar como podemos ajudar {nome_empresa_lead} a [benefício principal]?").
    4.  Demonstrar que você fez sua pesquisa sobre a empresa.
    5.  Evitar jargões excessivos e ser autêntica.
    6.  Se a análise do lead indicou "FALHA NA EXTRAÇÃO", adapte a mensagem para ser mais genérica em relação ao conteúdo do site, mas ainda personalizada com base nos dados de busca do Google, se disponíveis.

    Formato da Saída Esperada:
    A mensagem de contato inicial pronta para ser enviada, especificando o canal (E-mail ou LinkedIn).
    Inclua um Assunto (Subject) se for um e-mail.
    """
    print("Criando mensagem personalizada...")
    return call_gemini_api(prompt)

# --- Script Principal ---
if __name__ == "__main__":
    meu_produto_ou_servico = input("Qual produto ou serviço você está oferecendo? (Ex: 'nossa plataforma de IA para otimização de processos jurídicos', 'serviços de consultoria em transformação digital'): ")
    if not meu_produto_ou_servico:
        print("Produto/serviço não informado. Usando um placeholder genérico.")
        meu_produto_ou_servico = "nossa solução inovadora para otimização e prospecção"

    try:
        with open('leads.json', 'r', encoding='utf-8') as f:
            data_from_json_file = json.load(f) 
    except FileNotFoundError:
        print("Erro: Arquivo 'leads.json' não encontrado na raiz do projeto.")
        exit()
    except json.JSONDecodeError as e:
        print(f"Erro: Arquivo 'leads.json' não é um JSON válido. Detalhes: {e}")
        exit()

    all_leads_processed_data = []

    # Verifica se a estrutura principal é um dicionário e contém 'sites_data'
    if not isinstance(data_from_json_file, dict) or "sites_data" not in data_from_json_file:
        print(f"Erro: O conteúdo de 'leads.json' não tem a estrutura esperada (um dicionário com a chave 'sites_data').")
        print(f"Tipo encontrado: {type(data_from_json_file)}")
        if isinstance(data_from_json_file, dict):
            print(f"Chaves encontradas: {list(data_from_json_file.keys())}")
        exit()

    leads_list_to_process = data_from_json_file["sites_data"]

    if not isinstance(leads_list_to_process, list):
        print(f"Erro: O valor da chave 'sites_data' em 'leads.json' não é uma lista. Tipo encontrado: {type(leads_list_to_process)}")
        exit()
    
    print(f"Total de leads a processar: {len(leads_list_to_process)}")
    original_query_info = data_from_json_file.get("original_query", "Consulta original não especificada")
    print(f"Consulta original que gerou estes leads: {original_query_info}")


    for i, lead_info_dict in enumerate(leads_list_to_process):
        
        # Validação básica se lead_info_dict é um dicionário
        if not isinstance(lead_info_dict, dict):
            print(f"Aviso: Item {i} na lista 'sites_data' não é um dicionário. Pulando este item. Conteúdo: {str(lead_info_dict)[:100]}...")
            continue

        current_lead_url = lead_info_dict.get('url', 'URL Desconhecida')
        print(f"\n======================================================================")
        print(f"Processando Lead {i+1}/{len(leads_list_to_process)}: {current_lead_url}")
        print(f"======================================================================\n")

        # Extrai o nome da empresa do título do Google Search Data, se possível, para personalização
        google_search_title = lead_info_dict.get("google_search_data", {}).get("title", "Empresa Desconhecida")
        # Tenta limpar um pouco o título para obter um nome de empresa mais limpo
        company_name_guess = google_search_title.split(" - ")[0].split(" | ")[0].split(": ")[0]
        if "http" in company_name_guess: # Evitar usar URLs como nome
            company_name_guess = "Empresa em " + current_lead_url.split('/')[2] if current_lead_url != 'URL Desconhecida' else "Empresa Desconhecida"


        # Prepara a string de dados do lead para os prompts
        lead_data_for_prompt = {
            "url": current_lead_url,
            "google_search_data": lead_info_dict.get("google_search_data", {}),
            "extracted_text_content": lead_info_dict.get("extracted_text_content", "Nenhum conteúdo extraído."),
            "extraction_status_message": lead_info_dict.get("extraction_status_message", "Status desconhecido."),
            # "screenshot_filepath": lead_info_dict.get("screenshot_filepath", "N/A") # Removido pois não é usado no prompt
        }
        lead_data_str = json.dumps(lead_data_for_prompt, indent=2, ensure_ascii=False)
        
        # Etapa 1: Análise do Lead
        analise = gerar_analise_lead(lead_data_str, meu_produto_ou_servico)
        print("\n--- Análise do Lead Concluída ---")
        if analise.startswith("Erro:"):
            print(f"Não foi possível gerar análise para o lead: {current_lead_url}. Pulando para o próximo.")
            # Salvar o erro para este lead
            lead_output = {
                "lead_url": current_lead_url,
                "produto_servico_ofertado": meu_produto_ou_servico,
                "analise_do_lead": analise,
                "persona_desenvolvida": "Erro na etapa anterior",
                "plano_de_abordagem": "Erro na etapa anterior",
                "mensagem_personalizada_gerada": "Erro na etapa anterior"
            }
            all_leads_processed_data.append(lead_output)
            time.sleep(1) 
            continue
        time.sleep(1) 

        # Etapa 2: Criação da Persona
        persona_criada = criar_persona(analise, meu_produto_ou_servico, current_lead_url)
        print("\n--- Criação da Persona Concluída ---")
        if persona_criada.startswith("Erro:"):
            print(f"Não foi possível criar persona para o lead: {current_lead_url}. Pulando etapas restantes para este lead.")
            lead_output = {
                "lead_url": current_lead_url,
                "produto_servico_ofertado": meu_produto_ou_servico,
                "analise_do_lead": analise,
                "persona_desenvolvida": persona_criada,
                "plano_de_abordagem": "Erro na etapa anterior",
                "mensagem_personalizada_gerada": "Erro na etapa anterior"
            }
            all_leads_processed_data.append(lead_output)
            time.sleep(1)
            continue
        time.sleep(1)

        # Etapa 3: Desenvolvimento do Plano de Abordagem
        plano = desenvolver_plano_abordagem(analise, persona_criada, meu_produto_ou_servico, current_lead_url)
        print("\n--- Plano de Abordagem Concluído ---")
        if plano.startswith("Erro:"):
            print(f"Não foi possível desenvolver plano de abordagem para o lead: {current_lead_url}. Pulando etapas restantes para este lead.")
            lead_output = {
                "lead_url": current_lead_url,
                "produto_servico_ofertado": meu_produto_ou_servico,
                "analise_do_lead": analise,
                "persona_desenvolvida": persona_criada,
                "plano_de_abordagem": plano,
                "mensagem_personalizada_gerada": "Erro na etapa anterior"
            }
            all_leads_processed_data.append(lead_output)
            time.sleep(1)
            continue
        time.sleep(1)

        # Etapa 4: Criação da Mensagem Personalizada
        mensagem = criar_mensagem_personalizada(analise, persona_criada, plano, meu_produto_ou_servico, current_lead_url, company_name_guess)
        print("\n--- Mensagem Personalizada Concluída ---")
        if mensagem.startswith("Erro:"):
            print(f"Não foi possível criar mensagem personalizada para o lead: {current_lead_url}.")
            mensagem_final = "Erro ao gerar mensagem personalizada." 
        else:
            mensagem_final = mensagem
        
        lead_output = {
            "lead_url": current_lead_url,
            "company_name_inferred": company_name_guess,
            "produto_servico_ofertado": meu_produto_ou_servico,
            "analise_do_lead": analise,
            "persona_desenvolvida": persona_criada,
            "plano_de_abordagem": plano,
            "mensagem_personalizada_gerada": mensagem_final
        }
        all_leads_processed_data.append(lead_output)
        
        print(f"\n--- Processamento completo para o lead: {current_lead_url} ---")

    # Salvar todos os resultados em um novo arquivo JSON
    output_filename = "processed_leads_output_gemini_direct.json"
    try:
        # Estrutura final do JSON de saída
        final_output_data = {
            "original_query": original_query_info,
            "processing_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "product_service_offered": meu_produto_ou_servico,
            "total_leads_in_file": len(leads_list_to_process),
            "total_leads_processed_successfully_or_with_errors": len(all_leads_processed_data),
            "processed_leads_details": all_leads_processed_data
        }
        with open(output_filename, 'w', encoding='utf-8') as f_out:
            json.dump(final_output_data, f_out, indent=2, ensure_ascii=False)
        print(f"\n\nProcessamento concluído. Resultados salvos em '{output_filename}'")
    except Exception as e:
        print(f"Erro ao salvar o arquivo de saída: {e}")