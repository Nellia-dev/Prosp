#!/usr/bin/env python3
"""
Nellia Prospector - Main Pipeline Orchestrator (RAG Enabled)
Processes leads from harvester through the multi-agent pipeline.
"""

import json
import os
import sys
import uuid
import asyncio # ### NOVO ###
from pathlib import Path
from typing import List, Optional, Dict, Any
import click
from datetime import datetime
from loguru import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from dotenv import load_dotenv # ### NOVO ###

# Importações de modelos e agentes existentes
from data_models.lead_structures import HarvesterOutput, SiteData, FinalProspectPackage
from agents.lead_intake_agent import LeadIntakeAgent
from agents.lead_analysis_agent import LeadAnalysisAgent
from agents.persona_creation_agent import PersonaCreationAgent
from agents.approach_strategy_agent import ApproachStrategyAgent
from agents.message_crafting_agent import MessageCraftingAgent

# ### NOVAS IMPORTAÇÕES PARA O RAG ###
from prospect.pipeline_orchestrator import PipelineOrchestrator
from prospect.ai_prospect_intelligence import AdvancedProspectProfiler

console = Console()


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """Setup logging configuration"""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level=log_level,
        colorize=True
    )
    if log_file:
        logger.add(log_file, level=log_level, rotation="10 MB")


def load_harvester_output(file_path: str) -> HarvesterOutput:
    """Load and validate harvester output from JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return HarvesterOutput.parse_obj(data)
    except Exception as e:
        logger.error(f"Error loading harvester output: {e}")
        raise

# ### MODIFICADO ###
# A função agora recebe o profiler e o contexto para o RAG
def process_single_lead(
    site_data: SiteData,
    intake_agent: LeadIntakeAgent,
    analysis_agent: LeadAnalysisAgent,
    persona_agent: PersonaCreationAgent,
    strategy_agent: ApproachStrategyAgent,
    message_agent: MessageCraftingAgent,
    # ### NOVOS PARÂMETROS ###
    prospect_profiler: Optional[AdvancedProspectProfiler],
    enriched_context: Dict[str, Any],
    rag_vector_store: Optional[Dict[str, Any]],
    # Fim dos novos parâmetros
    progress: Optional[Progress] = None,
    task_id: Optional[int] = None
) -> Optional[dict]:
    """Process a single lead through the pipeline"""
    try:
        if progress and task_id is not None: progress.update(task_id, description=f"[yellow]Validating[/yellow] {site_data.url[:50]}...")
        validated_lead = intake_agent.execute(site_data)
        if not validated_lead.is_valid:
            return {"url": str(site_data.url), "status": "validation_failed", "errors": validated_lead.validation_errors}

        if progress and task_id is not None: progress.update(task_id, description=f"[cyan]Analyzing[/cyan] {site_data.url[:50]}...")
        analyzed_lead = analysis_agent.execute(validated_lead)

        # ### NOVO PASSO: ENRIQUECIMENTO COM AI INTELLIGENCE (RAG) ###
        ai_intelligence_data = None
        if prospect_profiler:
            if progress and task_id is not None: progress.update(task_id, description=f"[magenta]AI Profiling (RAG)[/magenta] {site_data.url[:50]}...")
            # O profiler precisa de um lead_data em formato de dicionário simples
            lead_data_for_profiler = {
                "company_name": analyzed_lead.company_profile.company_name,
                "description": analyzed_from_lead.analysis.business_summary,
                "website": str(validated_lead.url)
            }
            try:
                ai_intelligence_data = prospect_profiler.create_advanced_prospect_profile(
                    lead_data=lead_data_for_profiler,
                    enriched_context=enriched_context,
                    rag_vector_store=rag_vector_store
                )
            except Exception as e:
                 logger.error(f"AI Profiler failed for {site_data.url}: {e}")
                 ai_intelligence_data = {"error": str(e)}
        # ### FIM DO NOVO PASSO ###

        if progress and task_id is not None: progress.update(task_id, description=f"[blue]Creating Persona[/blue] {site_data.url[:50]}...")
        lead_with_persona = persona_agent.execute(analyzed_lead)
        
        if progress and task_id is not None: progress.update(task_id, description=f"[green]Developing Strategy[/green] {site_data.url[:50]}...")
        lead_with_strategy = strategy_agent.execute(lead_with_persona)

        if progress and task_id is not None: progress.update(task_id, description=f"[bold red]Crafting Message[/bold red] {site_data.url[:50]}...")
        final_prospect = message_agent.execute(lead_with_strategy)

        result_package = {
            "url": str(site_data.url),
            "status": "completed",
            "company_name": final_prospect.company_profile.company_name,
            "sector": analyzed_lead.analysis.company_sector,
            "relevance_score": analyzed_lead.analysis.relevance_score,
            "persona_role": lead_with_persona.persona.likely_role,
            "recommended_channel": final_prospect.personalized_message.channel.value,
            "message_preview": final_prospect.personalized_message.message_body[:100] + "...",
            "confidence_score": final_prospect.confidence_score,
            "opportunity_fit": analyzed_lead.analysis.opportunity_fit,
            "final_prospect_package": final_prospect.dict(),
            "ai_intelligence": ai_intelligence_data # ### NOVO ### Adiciona os dados do RAG ao resultado
        }
        return result_package
        
    except Exception as e:
        logger.error(f"Error processing lead {site_data.url}: {e}", exc_info=True)
        return {"url": str(site_data.url), "status": "error", "error": str(e)}

# ### MODIFICADO ###
# O comando agora é assíncrono para permitir a configuração do RAG
@click.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--product-service', '-p', required=True, help='Product/service being offered')
@click.option('--log-level', '-l', default='INFO', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']))
@click.option('--log-file', type=click.Path(), help='Log file path')
@click.option('--skip-failed', is_flag=True, help='Skip leads with failed extraction')
@click.option('--limit', '-n', type=int, help='Limit number of leads to process')
def main_cli(
    input_file: str,
    output: Optional[str],
    product_service: str,
    log_level: str,
    log_file: Optional[str],
    skip_failed: bool,
    limit: Optional[int]
):
    """
    Nellia Prospector - Process leads from harvester output.
    EXAMPLE:
        python main.py harvester_output/example.json -p "AI-powered lead generation"
    """
    # Envolve a execução real em uma função async
    try:
        asyncio.run(
            execute_pipeline(
                input_file, output, product_service, log_level,
                log_file, skip_failed, limit
            )
        )
    except Exception as e:
        console.print(f"[bold red]A critical error occurred: {e}[/bold red]")
        sys.exit(1)


async def execute_pipeline(
    input_file: str,
    output: Optional[str],
    product_service: str,
    log_level: str,
    log_file: Optional[str],
    skip_failed: bool,
    limit: Optional[int]
):
    """Core async pipeline execution logic"""
    setup_logging(log_level, log_file)
    load_dotenv()
    
    console.print("[bold cyan]🚀 Nellia Prospector - Starting Pipeline (RAG Enabled)[/bold cyan]")
    console.print(f"Product/Service: [green]{product_service}[/green]")
    
    try:
        console.print(f"\n📁 Loading harvester output from: [yellow]{input_file}[/yellow]")
        harvester_data = load_harvester_output(input_file)
        console.print(f"✅ Loaded {len(harvester_data.sites_data)} leads from '{harvester_data.original_query}'")
    except Exception as e:
        console.print(f"[red]❌ Failed to load input file: {e}[/red]")
        return
    
    # ### NOVO: CONFIGURAÇÃO DO RAG ###
    job_id = str(uuid.uuid4())
    
    # 1. Construir o business_context para o RAG
    business_context = {
        "business_description": f"A company that provides: {product_service}",
        "product_service_description": product_service,
        "original_query": harvester_data.original_query,
        # Você pode adicionar mais campos aqui se os tiver (ex: ideal_customer, competitors)
    }

    # 2. Instanciar o Orquestrador (usado apenas para configurar o RAG) e o Profiler
    console.print("\n[bold magenta]🛠️  Setting up RAG environment...[/bold magenta]")
    orchestrator = PipelineOrchestrator(business_context=business_context, user_id="cli_user", job_id=job_id)
    prospect_profiler = AdvancedProspectProfiler() if os.getenv("GEMINI_API_KEY") else None

    # 3. Gerar o arquivo de contexto e o vector store
    enriched_context_for_rag = orchestrator._create_enriched_search_context(business_context, harvester_data.original_query)
    context_filename = f"./enriched_context_{job_id}.md"
    
    try:
        with open(context_filename, "w", encoding="utf-8") as f:
            # Reutilizando a lógica de escrita de markdown do orquestrador
            markdown_string = f"# Enriched Search Context for Job: {job_id}\n\n"
            for key, value in enriched_context_for_rag.items():
                markdown_string += f"## {key.replace('_', ' ').title()}\n"
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        markdown_string += f"- **{sub_key.replace('_', ' ').title()}**: `{sub_value}`\n" if sub_value else f"- **{sub_key.replace('_', ' ').title()}**: N/A\n"
                else:
                    markdown_string += f"`{value}`\n" if value else "N/A\n"
                markdown_string += "\n"
            f.write(markdown_string)
        
        console.print(f"📝 Generated RAG context file: [green]{context_filename}[/green]")
        
        # Esta chamada agora é assíncrona
        rag_setup_success = await orchestrator._setup_rag_for_job(job_id, context_filename)
        if not rag_setup_success:
            console.print("[yellow]⚠️ RAG setup failed. Continuing without AI-powered insights.[/yellow]")
            rag_vector_store = None
        else:
            console.print("[bold green]✅ RAG Vector Store (FAISS) is ready.[/bold green]")
            rag_vector_store = orchestrator.job_vector_stores.get(job_id)
            
    except Exception as e:
        console.print(f"[red]❌ Error during RAG setup: {e}[/red]")
        rag_vector_store = None
    
    # ### FIM DA CONFIGURAÇÃO DO RAG ###

    leads_to_process = harvester_data.sites_data[:limit] if limit else harvester_data.sites_data
    
    console.print("\n🤖 Initializing agents...")
    intake_agent = LeadIntakeAgent(skip_failed_extractions=skip_failed)
    analysis_agent = LeadAnalysisAgent(product_service_context=product_service)
    persona_agent = PersonaCreationAgent()
    strategy_agent = ApproachStrategyAgent(product_service_context=product_service)
    message_agent = MessageCraftingAgent()
    
    results = []
    
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), BarColumn(), TaskProgressColumn(), console=console) as progress:
        task = progress.add_task(f"[bold]Processing {len(leads_to_process)} leads...[/bold]", total=len(leads_to_process))
        for site_data in leads_to_process:
            if site_data.extraction_status_message == "FAILURE" and skip_failed:
                progress.update(task, advance=1)
                continue

            result = process_single_lead(
                site_data, intake_agent, analysis_agent, persona_agent, strategy_agent, message_agent,
                prospect_profiler, enriched_context_for_rag, rag_vector_store, # Passa os objetos RAG
                progress, task
            )
            if result:
                results.append(result)
            progress.update(task, advance=1)
    
    console.print("\n📊 [bold]Processing Summary:[/bold]")
    successful = [r for r in results if r.get('status') == 'completed']
    # ... (o resto do código de exibição de resultados e salvamento permanece o mesmo) ...
    failed_validation = [r for r in results if r.get('status') == 'validation_failed']
    errors = [r for r in results if r.get('status') == 'error']
    
    summary_table = Table(title="Results")
    summary_table.add_column("Status", style="cyan")
    summary_table.add_column("Count", style="magenta")
    summary_table.add_row("✅ Successfully Completed", str(len(successful)))
    summary_table.add_row("❌ Validation Failed", str(len(failed_validation)))
    summary_table.add_row("⚠️  Processing Errors", str(len(errors)))
    summary_table.add_row("[bold]Total Processed[/bold]", f"[bold]{len(results)}[/bold]")
    
    console.print(summary_table)
    
    if successful:
        console.print("\n🏆 [bold]Top Leads by Relevance:[/bold]")
        top_leads = sorted(successful, key=lambda x: x.get('relevance_score', 0), reverse=True)[:5]
        
        leads_table = Table()
        leads_table.add_column("Company", style="cyan", overflow="fold")
        leads_table.add_column("RAG Score", style="magenta")
        leads_table.add_column("Relevance", style="green")
        leads_table.add_column("Channel", style="blue")
        
        for lead in top_leads:
            ai_score = lead.get('ai_intelligence', {}).get('prospect_score', 'N/A')
            ai_score_str = f"{ai_score:.2f}" if isinstance(ai_score, float) else "N/A"
            leads_table.add_row(
                lead['company_name'],
                ai_score_str,
                f"{lead.get('relevance_score', 0):.2f}",
                lead.get('recommended_channel', 'N/A')
            )
        
        console.print(leads_table)
    
    output_file = output or f"prospector_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    # ... (O resto do código de salvamento permanece igual) ...
    output_data = {
        "processing_timestamp": datetime.now().isoformat(),
        "original_query": harvester_data.original_query,
        "product_service_context": product_service,
        "total_leads_in_file": len(harvester_data.sites_data),
        "total_leads_processed": len(results),
        "successful_analyses": len(successful),
        "validation_failures": len(failed_validation),
        "processing_errors": len(errors),
        "results": results,
    }

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        console.print(f"\n💾 Results saved to: [green]{output_file}[/green]")
    except Exception as e:
        console.print(f"[red]❌ Failed to save results: {e}[/red]")
        return
    
    console.print("\n✨ [bold green]Pipeline completed successfully![/bold green]")


if __name__ == "__main__":
    main_cli()
