# run.py

import sys
from dotenv import load_dotenv
import os
import re
import json
from datetime import datetime
import asyncio

# Adiciona o diretório atual ao PYTHONPATH para que 'adk1' possa ser importado.
sys.path.insert(0, os.path.dirname(__file__))

# Carrega as variáveis de ambiente do arquivo .env
# Assumimos que o .env está na mesma pasta que run.py
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))


# Importa TODOS os agentes relevantes do arquivo agent.py dentro de adk1
# Renomeando para corresponder aos nomes dos agentes do seu projeto "Prospecter"
from adk1.agent import (
    root_agent,  # Este é o query_refiner_agent (refinador de query)
    lead_search_and_qualify_agent,
    structured_lead_extractor_agent,
    direct_url_lead_processor_agent
)

# Importa as classes do Google ADK para execução
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.adk.agents import Agent # Mantém essa importação para type hinting se necessário

APP_NAME = "prospecter_app" # Renomeado para o seu app
USER_ID = "prospector_user_1"
DEFAULT_SESSION_ID = "session_001"

session_service = InMemorySessionService()

async def export_leads_to_json(leads_data: list, filename: str = None):
    """Exporta a lista de leads para um arquivo JSON."""
    if not leads_data:
        print("Nenhum dado de lead para exportar.")
        return

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"leads_extracted_{timestamp}.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(leads_data, f, ensure_ascii=False, indent=4)
        print(f"\nDados de leads exportados com sucesso para '{filename}'")
    except Exception as e:
        print(f"\nErro ao exportar dados de leads para JSON: {e}")

async def call_agent_and_run(agent_to_use: Agent, query: str) -> dict:
    """
    Cria uma sessão e executa o agente especificado com a query do usuário,
    imprimindo os eventos do processo. Retorna a resposta final do agente (texto e potenciais dados JSON).
    """
    session_obj = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=DEFAULT_SESSION_ID
    )

    current_session_id = session_obj.id
    print(f"Sessão criada com ID: {current_session_id}")

    runner = Runner(
        agent=agent_to_use, # Usa o agente passado como argumento
        app_name=APP_NAME,
        session_service=session_service
    )

    print(f"\n--- Usuário para {agent_to_use.name}: {query} ---")

    user_message_content = types.Content(role='user', parts=[types.Part(text=query)])

    events = runner.run_async(
        user_id=USER_ID,
        session_id=current_session_id,
        new_message=user_message_content
    )

    final_response_text = "Nenhuma resposta final recebida."
    extracted_json_data = [] # Para coletar dados JSON de leads

    async for event in events:
        if hasattr(event, 'tool_code') and event.tool_code:
            print(f"\n--- Agente (Pensamento/Ação): Usando a ferramenta {event.tool_code.name} ---")
            print(f"--- Argumentos da ferramenta: {event.tool_code.args} ---")
        elif hasattr(event, 'tool_code_output') and event.tool_code_output:
            print(f"\n--- Agente (Saída da Ferramenta {event.tool_code_output.name}): ---")
            output = event.tool_code_output.output
            if isinstance(output, (str, dict, list)):
                # Tenta extrair JSON se a saída da ferramenta for string que parece JSON
                if isinstance(output, str):
                    try:
                        # Tenta remover markdown code block e parsear JSON
                        json_str_match = re.search(r'```json\n(.*?)```', output, re.DOTALL)
                        if json_str_match:
                            parsed_output = json.loads(json_str_match.group(1).strip())
                        else: # Tenta parsear a string diretamente
                            parsed_output = json.loads(output)

                        if isinstance(parsed_output, list) and all(isinstance(item, dict) for item in parsed_output):
                            extracted_json_data.extend(parsed_output)
                            print(f"JSON extraído da ferramenta ({len(parsed_output)} itens).")
                        elif isinstance(parsed_output, dict):
                            extracted_json_data.append(parsed_output)
                            print(f"JSON extraído da ferramenta (1 item).")
                        else:
                            print(str(output)[:500] + "...") # Não é JSON estruturado
                    except json.JSONDecodeError:
                        print(str(output)[:500] + "...") # Não é JSON válido
                else: # Se a saída já for dict ou list
                    if isinstance(output, list) and all(isinstance(item, dict) for item in output):
                        extracted_json_data.extend(output)
                        print(f"JSON extraído da ferramenta (já como list/dict) ({len(output)} itens).")
                    elif isinstance(output, dict):
                        extracted_json_data.append(output)
                        print(f"JSON extraído da ferramenta (já como dict).")
                    else:
                        print(str(output)[:500] + "...") # Outro formato de dados
            else:
                print(output)
        elif hasattr(event, 'content') and event.content and event.content.parts:
            text_content_part = next((part.text for part in event.content.parts if hasattr(part, 'text')), None)
            if text_content_part:
                final_response_text = text_content_part
                print("\n--- Agente (Resposta Final): ---")
                print(final_response_text)
                
                # Tenta extrair JSON também da resposta final do agente
                json_match = re.search(r'```json\n(.*?)```', final_response_text, re.DOTALL)
                if json_match:
                    try:
                        parsed_json = json.loads(json_match.group(1).strip())
                        if isinstance(parsed_json, list):
                            extracted_json_data.extend(parsed_json)
                        elif isinstance(parsed_json, dict):
                            extracted_json_data.append(parsed_json)
                        print(f"JSON extraído da resposta final do agente.")
                    except json.JSONDecodeError:
                        pass # Ignora se não for JSON válido no final
                break # Sai do loop após a resposta final

    return {
        "final_response": final_response_text,
        "extracted_leads": extracted_json_data
    }
        
# Nova função assíncrona para o loop principal
async def main_loop():
    print("Bem-vindo ao Prospecter: Seu Orquestrador de Geração de Leads Inteligente!")
    print("Digite sua solicitação para encontrar leads (ex: 'empresas de IA em São Paulo', 'e-mails de contato da empresa X', 'analisar este link: http://example.com/company').")
    print("Digite 'sair' para encerrar.")

    while True: # Loop para interação contínua
        user_raw_query = input("\nVocê: ").strip()
        if user_raw_query.lower() == 'sair':
            print("Encerrando a sessão.")
            break

        if not user_raw_query:
            print("Por favor, digite uma solicitação.")
            continue

        session_leads_for_export = [] # Coleta leads para a sessão atual

        try:
            print("\n*** Etapa 1: Refinando a query com o query_refiner_agent ***")
            # Primeiro, rode o agente de refinamento com a query bruta do usuário
            refiner_result = await call_agent_and_run(root_agent, user_raw_query) # root_agent é o query_refiner_agent
            refined_query = refiner_result['final_response']
            print(f"Query refinada: '{refined_query}'")

            # Analise a query original do usuário para decidir qual agente de busca usar
            # Esta lógica determina a INTENÇÃO da query original para o roteamento principal
            if re.search(r'https?://\S+', user_raw_query): # Se a query ORIGINAL contiver URLs
                print("\n*** Etapa 2: Processando links com o direct_url_lead_processor_agent ***")
                # O direct_url_lead_processor_agent precisa da query original para extrair URLs e instrução
                agent_result = await call_agent_and_run(direct_url_lead_processor_agent, user_raw_query)
                session_leads_for_export.extend(agent_result['extracted_leads'])
            elif any(keyword in user_raw_query.lower() for keyword in ["e-mails", "telefones", "contato", "estruturados", "dados da empresa", "cnpj"]):
                print("\n*** Etapa 2: Extraindo dados estruturados de leads com o structured_lead_extractor_agent ***")
                agent_result = await call_agent_and_run(structured_lead_extractor_agent, refined_query)
                session_leads_for_export.extend(agent_result['extracted_leads'])
            else: # Busca geral e qualificação
                print("\n*** Etapa 2: Realizando busca geral e qualificação de leads com o lead_search_and_qualify_agent ***")
                agent_result = await call_agent_and_run(lead_search_and_qualify_agent, refined_query)
                session_leads_for_export.extend(agent_result['extracted_leads'])

            # Oferecer exportação após cada ciclo completo de interação
            if session_leads_for_export:
                export_choice = input("Orquestrador: Deseja exportar os leads encontrados para um arquivo JSON? (s/n): ").lower()
                if export_choice == 's':
                    await export_leads_to_json(session_leads_for_export)
                session_leads_for_export = [] # Limpa após a exportação

        except Exception as e:
            print(f"\nUm erro ocorreu durante a execução do agente: {e}")
            print(f"Detalhes do erro: {e}")
            import traceback; traceback.print_exc() # Para depuração

if __name__ == "__main__":
    # Inicia o loop principal assíncrono
    asyncio.run(main_loop())
