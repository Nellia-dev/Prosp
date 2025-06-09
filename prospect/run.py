# run.py - Refactored for Programmatic Use with Event Streaming

import sys
from dotenv import load_dotenv
import os
import re
import json
from datetime import datetime
import asyncio
import time
from typing import Dict, Any, Optional, List, AsyncIterator

# Adiciona o diretório atual ao PYTHONPATH para que 'adk1' possa ser importado.
sys.path.insert(0, os.path.dirname(__file__))

# Carrega as variáveis de ambiente do arquivo .env
# Assumimos que o .env está na mesma pasta que run.py
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

# Import event models for structured event emission
from event_models import (
    PipelineStartEvent,
    PipelineEndEvent,
    AgentStartEvent,
    AgentEndEvent,
    ToolCallStartEvent,
    ToolCallOutputEvent,
    ToolCallEndEvent,
    LeadGeneratedEvent,
    StatusUpdateEvent,
    PipelineErrorEvent
)

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

# =============================================================================
# PROGRAMMATIC INTERFACE FOR MCP INTEGRATION
# =============================================================================

async def execute_agentic_pipeline(
    initial_query: str,
    business_context: Dict[str, Any],
    user_id: str,
    job_id: str,
    max_leads_to_generate: int,
    config_overrides: Dict[str, Any] = None
) -> AsyncIterator[Dict[str, Any]]:
    """
    Primary asynchronous function for programmatic invocation of the agentic pipeline.
    
    Args:
        initial_query: The user's search query or instruction
        business_context: Full business context object from the user
        user_id: ID of the user initiating the request
        job_id: The unique ID for this job.
        max_leads_to_generate: Maximum number of leads to generate (for quota management)
        config_overrides: Optional configuration overrides (e.g., max_sites_to_scrape)
    
    Yields:
        Dict[str, Any]: Structured event dictionaries for real-time updates
    """
    pipeline_start_time = time.time()
    total_leads_generated = 0
    
    try:
        # Emit pipeline start event
        yield PipelineStartEvent(
            event_type="pipeline_start",
            timestamp=datetime.now().isoformat(),
            job_id=job_id,
            user_id=user_id,
            initial_query=initial_query,
            max_leads_to_generate=max_leads_to_generate
        ).to_dict()

        # Process business context to enhance initial query
        enhanced_query = _enhance_query_with_business_context(initial_query, business_context)
        
        yield StatusUpdateEvent(
            event_type="status_update",
            timestamp=datetime.now().isoformat(),
            job_id=job_id,
            user_id=user_id,
            status_message=f"Enhanced query with business context: '{enhanced_query}'"
        ).to_dict()

        # Apply configuration overrides
        max_sites_to_scrape = config_overrides.get('max_sites_to_scrape', 3) if config_overrides else 3
        
        # Step 1: Query refinement
        yield StatusUpdateEvent(
            event_type="status_update",
            timestamp=datetime.now().isoformat(),
            job_id=job_id,
            user_id=user_id,
            status_message="Starting query refinement with root agent"
        ).to_dict()

        refined_query = None
        async for event_dict in _execute_agent_with_events(
            agent=root_agent,
            query=enhanced_query,
            job_id=job_id,
            user_id=user_id,
            business_context=business_context
        ):
            yield event_dict
            # Capture the refined query from agent end event
            if event_dict.get('event_type') == 'agent_end' and event_dict.get('success'):
                refined_query = event_dict.get('final_response', enhanced_query)

        if not refined_query:
            refined_query = enhanced_query
            
        yield StatusUpdateEvent(
            event_type="status_update",
            timestamp=datetime.now().isoformat(),
            job_id=job_id,
            user_id=user_id,
            status_message=f"Query refined to: '{refined_query}'"
        ).to_dict()

        # Step 2: Determine which agent to use based on query intent
        selected_agent = _determine_agent_by_intent(initial_query)
        
        yield StatusUpdateEvent(
            event_type="status_update",
            timestamp=datetime.now().isoformat(),
            job_id=job_id,
            user_id=user_id,
            status_message=f"Selected agent: {selected_agent.name}",
            agent_name=selected_agent.name
        ).to_dict()

        # Step 3: Execute the selected agent
        agent_query = initial_query if selected_agent == direct_url_lead_processor_agent else refined_query
        
        leads_generated_in_session = []
        async for event_dict in _execute_agent_with_events(
            agent=selected_agent,
            query=agent_query,
            job_id=job_id,
            user_id=user_id,
            business_context=business_context,
            max_leads_limit=max_leads_to_generate - total_leads_generated,
            max_sites_to_scrape=max_sites_to_scrape
        ):
            yield event_dict
            
            # Capture leads from lead_generated events
            if event_dict.get('event_type') == 'lead_generated':
                leads_generated_in_session.append(event_dict.get('lead_data'))
                total_leads_generated += 1
                
                # Stop if we've reached the limit
                if total_leads_generated >= max_leads_to_generate:
                    yield StatusUpdateEvent(
                        event_type="status_update",
                        timestamp=datetime.now().isoformat(),
                        job_id=job_id,
                        user_id=user_id,
                        status_message=f"Reached maximum leads limit: {max_leads_to_generate}"
                    ).to_dict()
                    break

        # Pipeline completion
        execution_time = time.time() - pipeline_start_time
        yield PipelineEndEvent(
            event_type="pipeline_end",
            timestamp=datetime.now().isoformat(),
            job_id=job_id,
            user_id=user_id,
            total_leads_generated=total_leads_generated,
            execution_time_seconds=execution_time,
            success=True
        ).to_dict()

    except Exception as e:
        execution_time = time.time() - pipeline_start_time
        yield PipelineErrorEvent(
            event_type="pipeline_error",
            timestamp=datetime.now().isoformat(),
            job_id=job_id,
            user_id=user_id,
            error_message=str(e),
            error_type=type(e).__name__
        ).to_dict()
        
        yield PipelineEndEvent(
            event_type="pipeline_end",
            timestamp=datetime.now().isoformat(),
            job_id=job_id,
            user_id=user_id,
            total_leads_generated=total_leads_generated,
            execution_time_seconds=execution_time,
            success=False,
            error_message=str(e)
        ).to_dict()

def _enhance_query_with_business_context(initial_query: str, business_context: Dict[str, Any]) -> str:
    """
    Enhance the initial query with relevant business context information.
    
    Args:
        initial_query: The user's original query
        business_context: Business context containing company info, industry, etc.
    
    Returns:
        Enhanced query string with business context
    """
    if not business_context:
        return initial_query
    
    # Extract relevant context fields
    industry = business_context.get('industry', '')
    company_size = business_context.get('company_size', '')
    target_market = business_context.get('target_market', '')
    location = business_context.get('location', '')
    
    # Build enhanced query
    enhanced_parts = [initial_query]
    
    if industry:
        enhanced_parts.append(f"indústria {industry}")
    if target_market:
        enhanced_parts.append(f"mercado {target_market}")
    if location:
        enhanced_parts.append(f"localização {location}")
    if company_size:
        enhanced_parts.append(f"porte {company_size}")
    
    return " ".join(enhanced_parts)

def _determine_agent_by_intent(user_query: str) -> Agent:
    """
    Determine which agent to use based on the user's query intent.
    
    Args:
        user_query: The original user query
    
    Returns:
        The appropriate agent to handle the query
    """
    # URL processing intent
    if re.search(r'https?://\S+', user_query):
        return direct_url_lead_processor_agent
    
    # Structured data extraction intent
    elif any(keyword in user_query.lower() for keyword in 
             ["e-mails", "telefones", "contato", "estruturados", "dados da empresa", "cnpj"]):
        return structured_lead_extractor_agent
    
    # General search and qualification intent (default)
    else:
        return lead_search_and_qualify_agent

async def _execute_agent_with_events(
    agent: Agent,
    query: str,
    job_id: str,
    user_id: str,
    business_context: Dict[str, Any],
    max_leads_limit: int = None,
    max_sites_to_scrape: int = None
) -> AsyncIterator[Dict[str, Any]]:
    """
    Execute an agent and yield structured events for each step.
    
    Args:
        agent: The agent to execute
        query: The query to pass to the agent
        job_id: Job identifier
        user_id: User identifier
        business_context: The user's business context for enriching leads.
        max_leads_limit: Maximum leads to generate (for quota adherence)
        max_sites_to_scrape: Maximum sites to scrape (for performance control)
    
    Yields:
        Dict[str, Any]: Structured event dictionaries
    """
    agent_start_time = time.time()
    
    try:
        # Emit agent start event
        yield AgentStartEvent(
            event_type="agent_start",
            timestamp=datetime.now().isoformat(),
            job_id=job_id,
            user_id=user_id,
            agent_name=agent.name,
            agent_description=agent.description or "No description available",
            input_query=query
        ).to_dict()

        # Modify agent tools to respect limits if applicable
        if max_sites_to_scrape and hasattr(agent, 'tools'):
            _configure_agent_tools_for_limits(agent, max_sites_to_scrape)

        # Execute agent using existing call_agent_and_run logic but with event streaming
        result = await _call_agent_and_run_with_events(
            agent, query, job_id, user_id, max_leads_limit
        )
        
        # Process extracted leads and emit lead_generated events
        for lead_data in result.get('extracted_leads', []):
            if max_leads_limit is not None and max_leads_limit <= 0:
                break

            # Structure the raw lead data into the format expected by the backend
            structured_lead = _structure_lead_data(lead_data, business_context)
            
            yield LeadGeneratedEvent(
                event_type="lead_generated",
                timestamp=datetime.now().isoformat(),
                job_id=job_id,
                user_id=user_id,
                lead_data=structured_lead,
                source_url=structured_lead.get('website', 'Unknown'),
                agent_name=agent.name
            ).to_dict()
            
            if max_leads_limit is not None:
                max_leads_limit -= 1

        # Emit agent end event
        execution_time = time.time() - agent_start_time
        yield AgentEndEvent(
            event_type="agent_end",
            timestamp=datetime.now().isoformat(),
            job_id=job_id,
            user_id=user_id,
            agent_name=agent.name,
            execution_time_seconds=execution_time,
            success=True,
            final_response=result.get('final_response')
        ).to_dict()

    except Exception as e:
        execution_time = time.time() - agent_start_time
        yield AgentEndEvent(
            event_type="agent_end",
            timestamp=datetime.now().isoformat(),
            job_id=job_id,
            user_id=user_id,
            agent_name=agent.name,
            execution_time_seconds=execution_time,
            success=False,
            error_message=str(e)
        ).to_dict()

def _configure_agent_tools_for_limits(agent: Agent, max_sites_to_scrape: int):
    """
    Configure agent tools to respect the specified limits.
    
    Args:
        agent: The agent whose tools need configuration
        max_sites_to_scrape: Maximum sites to scrape
    """
    # This is a placeholder for tool configuration logic
    # In practice, tools in adk1/agent.py already accept parameters like max_search_results_to_scrape
    # The actual implementation would need to modify the tool calls dynamically
    pass

async def _call_agent_and_run_with_events(
    agent_to_use: Agent, 
    query: str,
    job_id: str,
    user_id: str,
    max_leads_limit: int = None
) -> dict:
    """
    Enhanced version of call_agent_and_run that emits tool events.
    Based on the original call_agent_and_run function but with event streaming.
    """
    session_obj = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=f"{DEFAULT_SESSION_ID}_{job_id}"
    )

    current_session_id = session_obj.id

    runner = Runner(
        agent=agent_to_use,
        app_name=APP_NAME,
        session_service=session_service
    )

    user_message_content = types.Content(role='user', parts=[types.Part(text=query)])

    events = runner.run_async(
        user_id=USER_ID,
        session_id=current_session_id,
        new_message=user_message_content
    )

    final_response_text = "Nenhuma resposta final recebida."
    extracted_json_data = []
    leads_processed = 0

    async for event in events:
        if hasattr(event, 'tool_code') and event.tool_code:
            # Emit tool call start event (without yielding since this is internal)
            tool_start_time = time.time()
            
        elif hasattr(event, 'tool_code_output') and event.tool_code_output:
            output = event.tool_code_output.output
            if isinstance(output, (str, dict, list)):
                # Process tool output and extract leads
                extracted_from_tool = _extract_leads_from_output(output)
                
                # Respect lead limits
                for lead in extracted_from_tool:
                    if max_leads_limit is not None and leads_processed >= max_leads_limit:
                        break
                    extracted_json_data.append(lead)
                    leads_processed += 1
                    
        elif hasattr(event, 'content') and event.content and event.content.parts:
            text_content_part = next((part.text for part in event.content.parts if hasattr(part, 'text')), None)
            if text_content_part:
                final_response_text = text_content_part
                
                # Extract JSON from final response
                json_match = re.search(r'```json\n(.*?)```', final_response_text, re.DOTALL)
                if json_match:
                    try:
                        parsed_json = json.loads(json_match.group(1).strip())
                        if isinstance(parsed_json, list):
                            for lead in parsed_json:
                                if max_leads_limit is not None and leads_processed >= max_leads_limit:
                                    break
                                extracted_json_data.append(lead)
                                leads_processed += 1
                        elif isinstance(parsed_json, dict):
                            if max_leads_limit is None or leads_processed < max_leads_limit:
                                extracted_json_data.append(parsed_json)
                                leads_processed += 1
                    except json.JSONDecodeError:
                        pass
                break

    return {
        "final_response": final_response_text,
        "extracted_leads": extracted_json_data
    }

def _structure_lead_data(raw_lead: Dict[str, Any], business_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforms a raw lead dictionary from an agent into the structured LeadData format
    expected by the NestJS backend.
    """
    company_name = raw_lead.get('company_name') or raw_lead.get('title')
    website = raw_lead.get('url') or raw_lead.get('website')

    # A more robust way to get company name from title if not explicitly found
    if not raw_lead.get('company_name') and raw_lead.get('title'):
        # Remove common suffixes like " | Company", " - Official Site", etc.
        company_name = re.split(r'\s*[-|]\s*', raw_lead.get('title'))[0].strip()

    # Basic email extraction from notes if not present
    email = raw_lead.get('email')
    if not email:
        notes = raw_lead.get('snippet', '') + raw_lead.get('description', '')
        email_match = re.search(r'[\w\.-]+@[\w\.-]+', notes)
        if email_match:
            email = email_match.group(0)

    return {
        "company_name": company_name,
        "website": website,
        "linkedin_url": raw_lead.get('linkedin_url'),
        "status": "HARVESTED",
        "source": "AGENTIC_HARVESTER",
        "potential_score": raw_lead.get('potential_score', 0.5),
        "confidence_score": raw_lead.get('confidence_score', 0.5),
        "notes": raw_lead.get('snippet') or raw_lead.get('description'),
        "initial_prompt": business_context.get('business_description'),
        "lead_data": raw_lead, # Store original raw data for enrichment
        "contact_email": email,
    }

def _extract_leads_from_output(output) -> List[Dict[str, Any]]:
    """
    Extract lead data from tool output.
    
    Args:
        output: Tool output (string, dict, or list)
    
    Returns:
        List of lead dictionaries
    """
    extracted_leads = []
    
    if isinstance(output, str):
        try:
            # Try to remove markdown code block and parse JSON
            json_str_match = re.search(r'```json\n(.*?)```', output, re.DOTALL)
            if json_str_match:
                parsed_output = json.loads(json_str_match.group(1).strip())
            else:
                parsed_output = json.loads(output)

            if isinstance(parsed_output, list) and all(isinstance(item, dict) for item in parsed_output):
                extracted_leads.extend(parsed_output)
            elif isinstance(parsed_output, dict):
                extracted_leads.append(parsed_output)
        except json.JSONDecodeError:
            pass  # Not valid JSON
    elif isinstance(output, list) and all(isinstance(item, dict) for item in output):
        extracted_leads.extend(output)
    elif isinstance(output, dict):
        extracted_leads.append(output)
    
    return extracted_leads

# =============================================================================
# LEGACY FUNCTIONS (Preserved for backward compatibility)
# =============================================================================

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
    
    LEGACY FUNCTION - Preserved for backward compatibility
    """
    session_obj = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=DEFAULT_SESSION_ID
    )

    current_session_id = session_obj.id
    print(f"Sessão criada com ID: {current_session_id}")

    runner = Runner(
        agent=agent_to_use,
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
    extracted_json_data = []

    async for event in events:
        if hasattr(event, 'tool_code') and event.tool_code:
            print(f"\n--- Agente (Pensamento/Ação): Usando a ferramenta {event.tool_code.name} ---")
            print(f"--- Argumentos da ferramenta: {event.tool_code.args} ---")
        elif hasattr(event, 'tool_code_output') and event.tool_code_output:
            print(f"\n--- Agente (Saída da Ferramenta {event.tool_code_output.name}): ---")
            output = event.tool_code_output.output
            extracted_leads = _extract_leads_from_output(output)
            extracted_json_data.extend(extracted_leads)
            
            if extracted_leads:
                print(f"JSON extraído da ferramenta ({len(extracted_leads)} itens).")
            else:
                print(str(output)[:500] + "..." if len(str(output)) > 500 else str(output))
                
        elif hasattr(event, 'content') and event.content and event.content.parts:
            text_content_part = next((part.text for part in event.content.parts if hasattr(part, 'text')), None)
            if text_content_part:
                final_response_text = text_content_part
                print("\n--- Agente (Resposta Final): ---")
                print(final_response_text)
                
                # Try to extract JSON from final response
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
                        pass
                break

    return {
        "final_response": final_response_text,
        "extracted_leads": extracted_json_data
    }
        
async def main_loop():
    """
    Nova função assíncrona para o loop principal.
    
    LEGACY FUNCTION - Preserved for backward compatibility with interactive mode
    """
    print("Bem-vindo ao Prospecter: Seu Orquestrador de Geração de Leads Inteligente!")
    print("Digite sua solicitação para encontrar leads (ex: 'empresas de IA em São Paulo', 'e-mails de contato da empresa X', 'analisar este link: http://example.com/company').")
    print("Digite 'sair' para encerrar.")

    while True:
        user_raw_query = input("\nVocê: ").strip()
        if user_raw_query.lower() == 'sair':
            print("Encerrando a sessão.")
            break

        if not user_raw_query:
            print("Por favor, digite uma solicitação.")
            continue

        session_leads_for_export = []

        try:
            print("\n*** Etapa 1: Refinando a query com o query_refiner_agent ***")
            refiner_result = await call_agent_and_run(root_agent, user_raw_query)
            refined_query = refiner_result['final_response']
            print(f"Query refinada: '{refined_query}'")

            # Determine which agent to use based on original query intent
            if re.search(r'https?://\S+', user_raw_query):
                print("\n*** Etapa 2: Processando links com o direct_url_lead_processor_agent ***")
                agent_result = await call_agent_and_run(direct_url_lead_processor_agent, user_raw_query)
                session_leads_for_export.extend(agent_result['extracted_leads'])
            elif any(keyword in user_raw_query.lower() for keyword in ["e-mails", "telefones", "contato", "estruturados", "dados da empresa", "cnpj"]):
                print("\n*** Etapa 2: Extraindo dados estruturados de leads com o structured_lead_extractor_agent ***")
                agent_result = await call_agent_and_run(structured_lead_extractor_agent, refined_query)
                session_leads_for_export.extend(agent_result['extracted_leads'])
            else:
                print("\n*** Etapa 2: Realizando busca geral e qualificação de leads com o lead_search_and_qualify_agent ***")
                agent_result = await call_agent_and_run(lead_search_and_qualify_agent, refined_query)
                session_leads_for_export.extend(agent_result['extracted_leads'])

            if session_leads_for_export:
                export_choice = input("Orquestrador: Deseja exportar os leads encontrados para um arquivo JSON? (s/n): ").lower()
                if export_choice == 's':
                    await export_leads_to_json(session_leads_for_export)
                session_leads_for_export = []

        except Exception as e:
            print(f"\nUm erro ocorreu durante a execução do agente: {e}")
            print(f"Detalhes do erro: {e}")
            import traceback; traceback.print_exc()

if __name__ == "__main__":
    # Inicia o loop principal assíncrono
    asyncio.run(main_loop())
