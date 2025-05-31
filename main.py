#!/usr/bin/env python3
"""
Nellia Prospector - Main Pipeline Orchestrator
Processes leads from harvester through the multi-agent pipeline.
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Optional
import click
from datetime import datetime
from loguru import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from data_models.lead_structures import HarvesterOutput, SiteData, FinalProspectPackage
from agents.lead_intake_agent import LeadIntakeAgent
from agents.lead_analysis_agent import LeadAnalysisAgent
from agents.persona_creation_agent import PersonaCreationAgent
from agents.approach_strategy_agent import ApproachStrategyAgent
from agents.message_crafting_agent import MessageCraftingAgent


console = Console()


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """Setup logging configuration"""
    logger.remove()  # Remove default handler
    
    # Console logging with colors
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True
    )
    
    # File logging if specified
    if log_file:
        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=log_level,
            rotation="10 MB"
        )


def load_harvester_output(file_path: str) -> HarvesterOutput:
    """Load and validate harvester output from JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate structure
        if not isinstance(data, dict) or "sites_data" not in data:
            raise ValueError("Invalid harvester output format: missing 'sites_data' key")
        
        # Parse into Pydantic model
        return HarvesterOutput.parse_obj(data)
        
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in file {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading harvester output: {e}")
        raise


def process_single_lead(
    site_data: SiteData,
    intake_agent: LeadIntakeAgent,
    analysis_agent: LeadAnalysisAgent,
    persona_agent: PersonaCreationAgent,
    strategy_agent: ApproachStrategyAgent,
    message_agent: MessageCraftingAgent,
    progress: Optional[Progress] = None,
    task_id: Optional[int] = None
) -> Optional[dict]:
    """Process a single lead through the pipeline"""
    try:
        # Step 1: Intake & Validation
        if progress and task_id is not None:
            progress.update(task_id, description=f"Validating {site_data.url}")
        
        validated_lead = intake_agent.execute(site_data)
        
        if not validated_lead.is_valid:
            logger.warning(f"Lead validation failed: {site_data.url}")
            return {
                "url": str(site_data.url),
                "status": "validation_failed",
                "errors": validated_lead.validation_errors
            }
        
        # Step 2: Lead Analysis
        if progress and task_id is not None:
            progress.update(task_id, description=f"Analyzing {site_data.url}")
        
        analyzed_lead = analysis_agent.execute(validated_lead)
        
        # Step 3: Persona Creation
        if progress and task_id is not None:
            progress.update(task_id, description=f"Creating persona for {site_data.url}")
        
        lead_with_persona = persona_agent.execute(analyzed_lead)
        
        # Step 4: Strategy Development
        if progress and task_id is not None:
            progress.update(task_id, description=f"Developing strategy for {site_data.url}")
        
        lead_with_strategy = strategy_agent.execute(lead_with_persona)
        
        # Step 5: Message Crafting
        if progress and task_id is not None:
            progress.update(task_id, description=f"Crafting message for {site_data.url}")
        
        final_prospect = message_agent.execute(lead_with_strategy)
        
        # Return complete prospect package
        return {
            "url": str(site_data.url),
            "status": "completed",
            "company_name": final_prospect.to_export_dict()["company_name"],
            "sector": analyzed_lead.analysis.company_sector,
            "relevance_score": analyzed_lead.analysis.relevance_score,
            "persona_role": lead_with_persona.persona.likely_role,
            "recommended_channel": final_prospect.personalized_message.channel.value,
            "message_preview": final_prospect.personalized_message.message_body[:100] + "...",
            "confidence_score": final_prospect.confidence_score,
            "opportunity_fit": analyzed_lead.analysis.opportunity_fit,
            "final_prospect_package": final_prospect.dict()
        }
        
    except Exception as e:
        logger.error(f"Error processing lead {site_data.url}: {e}")
        return {
            "url": str(site_data.url),
            "status": "error",
            "error": str(e)
        }


@click.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--product-service', '-p', required=True, help='Product/service being offered')
@click.option('--log-level', '-l', default='INFO', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']))
@click.option('--log-file', type=click.Path(), help='Log file path')
@click.option('--skip-failed', is_flag=True, help='Skip leads with failed extraction')
@click.option('--limit', '-n', type=int, help='Limit number of leads to process')
def main(
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
    setup_logging(log_level, log_file)
    
    console.print("[bold cyan]🚀 Nellia Prospector - Starting Pipeline[/bold cyan]")
    console.print(f"Product/Service: [green]{product_service}[/green]")
    
    # Load harvester output
    try:
        console.print(f"\n📁 Loading harvester output from: [yellow]{input_file}[/yellow]")
        harvester_data = load_harvester_output(input_file)
        total_leads = len(harvester_data.sites_data)
        console.print(f"✅ Loaded {total_leads} leads from {harvester_data.original_query}")
    except Exception as e:
        console.print(f"[red]❌ Failed to load input file: {e}[/red]")
        return 1
    
    # Apply limit if specified
    leads_to_process = harvester_data.sites_data[:limit] if limit else harvester_data.sites_data
    
    # Initialize agents
    console.print("\n🤖 Initializing agents...")
    intake_agent = LeadIntakeAgent(skip_failed_extractions=skip_failed)
    analysis_agent = LeadAnalysisAgent(product_service_context=product_service)
    persona_agent = PersonaCreationAgent()
    strategy_agent = ApproachStrategyAgent(product_service_context=product_service)
    message_agent = MessageCraftingAgent()
    
    # Process leads with progress bar
    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task(
            f"Processing {len(leads_to_process)} leads...", 
            total=len(leads_to_process)
        )
        
        for i, site_data in enumerate(leads_to_process):
            result = process_single_lead(
                site_data,
                intake_agent,
                analysis_agent,
                persona_agent,
                strategy_agent,
                message_agent,
                progress,
                task
            )
            
            if result:
                results.append(result)
            
            progress.update(task, advance=1)
    
    # Display results summary
    console.print("\n📊 [bold]Processing Summary:[/bold]")
    
    successful = [r for r in results if r.get('status') == 'completed']
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
    
    # Display top leads by relevance
    if successful:
        console.print("\n🏆 [bold]Top Leads by Relevance:[/bold]")
        top_leads = sorted(successful, key=lambda x: x.get('relevance_score', 0), reverse=True)[:5]
        
        leads_table = Table()
        leads_table.add_column("URL", style="cyan", overflow="fold")
        leads_table.add_column("Sector", style="yellow")
        leads_table.add_column("Score", style="green")
        leads_table.add_column("Channel", style="blue")
        leads_table.add_column("Confidence", style="magenta")
        
        for lead in top_leads:
            leads_table.add_row(
                lead['url'].replace('https://', '').replace('http://', '')[:40] + '...',
                lead.get('sector', 'N/A'),
                f"{lead.get('relevance_score', 0):.2f}",
                lead.get('recommended_channel', 'N/A'),
                f"{lead.get('confidence_score', 0):.2f}"
            )
        
        console.print(leads_table)
    
    # Save results
    output_file = output or f"prospector_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    output_data = {
        "processing_timestamp": datetime.now().isoformat(),
        "original_query": harvester_data.original_query,
        "product_service_context": product_service,
        "total_leads_in_file": total_leads,
        "total_leads_processed": len(results),
        "successful_analyses": len(successful),
        "validation_failures": len(failed_validation),
        "processing_errors": len(errors),
        "results": results,
        "agent_metrics": {
            "intake_agent": intake_agent.get_metrics_summary(),
            "analysis_agent": analysis_agent.get_metrics_summary(),
            "persona_agent": persona_agent.get_metrics_summary(),
            "strategy_agent": strategy_agent.get_metrics_summary(),
            "message_agent": message_agent.get_metrics_summary()
        }
    }
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        console.print(f"\n💾 Results saved to: [green]{output_file}[/green]")
    except Exception as e:
        console.print(f"[red]❌ Failed to save results: {e}[/red]")
        return 1
    
    console.print("\n✨ [bold green]Pipeline completed successfully![/bold green]")
    return 0


if __name__ == "__main__":
    sys.exit(main()) 