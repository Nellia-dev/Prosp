#!/usr/bin/env python3
"""
Enhanced Nellia Prospector - Multi-mode processing with comprehensive intelligence
Integrates features from new-cw.py and ck.py for advanced lead processing
"""

import os
import sys
import json
import time
# import asyncio # Not currently used
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import uuid # For run_id and lead_id
import requests # For MCP reporting
import traceback # For detailed error logging

from loguru import logger
from rich.console import Console
from rich.progress import Progress, TaskID
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

# Core imports
from core_logic.llm_client import LLMClientFactory, LLMClientBase
from data_models.lead_structures import (
    HarvesterOutput, 
    AnalyzedLead,
    ComprehensiveProspectPackage,
    ValidatedLead,
    SiteData,
    GoogleSearchData,
    # Import Pydantic models from lead_structures that are used by EnhancedStrategy fields
    ExternalIntelligence, ContactInformation, PainPointAnalysis, LeadQualification,
    CompetitorIntelligence, PurchaseTriggers, ValueProposition, ObjectionFramework,
    EnhancedStrategy, EnhancedPersonalizedMessage, PersonalizedMessage, InternalBriefing, CommunicationChannel,
    ToTStrategyOptionModel, EvaluatedStrategyModel, ToTActionPlanSynthesisModel,
    DetailedApproachPlanModel, ObjectionResponseModelSchema, InternalBriefingSectionSchema, DetailedPainPointSchema
)
from agents.lead_intake_agent import LeadIntakeAgent
from agents.lead_analysis_agent import LeadAnalysisAgent
from agents.enhanced_lead_processor import EnhancedLeadProcessor

# MCP Server Configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:5001")
ENABLE_MCP_REPORTING = os.getenv("ENABLE_MCP_REPORTING", "false").lower() == "true"


class ProcessingMode(Enum):
    STANDARD = "standard"
    ENHANCED = "enhanced"
    HYBRID = "hybrid"

@dataclass
class ProcessingResults:
    mode: ProcessingMode
    total_leads: int
    successful_leads: int
    failed_leads: int
    processing_time: float
    results: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

class EnhancedNelliaProspector:
    def __init__(
        self,
        product_service_context: str,
        competitors_list: str = "",
        processing_mode: ProcessingMode = ProcessingMode.ENHANCED,
        tavily_api_key: Optional[str] = None
    ):
        self.product_service_context = product_service_context
        self.competitors_list = competitors_list
        self.processing_mode = processing_mode
        self.console = Console()
        
        self.llm_client = LLMClientFactory.create_from_env()
        self.tavily_api_key = tavily_api_key # Store for initialization

        # MCP config for EnhancedNelliaProspector to pass to EnhancedLeadProcessor
        self.MCP_SERVER_URL = MCP_SERVER_URL
        self.ENABLE_MCP_REPORTING = ENABLE_MCP_REPORTING

        self._initialize_agents() # tavily_api_key will be taken from self.tavily_api_key
        
        self.rate_limit_delay = 1.0

    def _initialize_agents(self): # Removed tavily_api_key from params
        self.lead_intake_agent = LeadIntakeAgent(llm_client=self.llm_client)
        self.lead_analysis_agent = LeadAnalysisAgent(
            llm_client=self.llm_client,
            product_service_context=self.product_service_context
        )
        if self.processing_mode in [ProcessingMode.ENHANCED, ProcessingMode.HYBRID]:
            self.enhanced_processor = EnhancedLeadProcessor(
                llm_client=self.llm_client,
                product_service_context=self.product_service_context,
                competitors_list=self.competitors_list,
                tavily_api_key=self.tavily_api_key, # Use stored key
                mcp_server_url=self.MCP_SERVER_URL, # Pass MCP config
                enable_mcp_reporting=self.ENABLE_MCP_REPORTING # Pass MCP config
            )

    def _report_lead_start_to_mcp(self, lead_id: str, run_id: str, url: str, initial_agent: str = "LeadIntakeAgent"):
        if not self.ENABLE_MCP_REPORTING: # Use instance variable
            return
        payload = {
            "lead_id": lead_id,
            "run_id": run_id,
            "url": url,
            "status": "ACTIVE",
            "current_agent": initial_agent,
            "start_time": datetime.utcnow().isoformat(),
            "last_update_time": datetime.utcnow().isoformat()
        }
        try:
            endpoint_url = f"{self.MCP_SERVER_URL}/api/lead/start" # Use instance variable
            response = requests.post(endpoint_url, json=payload, timeout=5)
            response.raise_for_status()
            logger.info(f"Successfully reported lead start to MCP for lead_id: {lead_id} (Run ID: {run_id})")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to report lead start to MCP for lead_id: {lead_id}. Error: {e}")
        except Exception as e_un:
            logger.error(f"Unexpected error reporting lead start to MCP for lead_id: {lead_id}. Error: {e_un}")

    async def process_leads( # Made async
        self, 
        harvester_data: HarvesterOutput, 
        limit: Optional[int] = None
    ) -> ProcessingResults:
        start_time_run_processing = time.time()
        run_id = str(uuid.uuid4())

        leads_to_process = harvester_data.sites_data
        if limit:
            leads_to_process = leads_to_process[:limit]
        
        self.console.print(Panel(
            f"🚀 Enhanced Nellia Prospector (Run ID: {run_id})\n"
            f"Mode: {self.processing_mode.value.upper()}\n"
            f"Leads to process: {len(leads_to_process)}\n"
            f"MCP Reporting: {'ENABLED' if self.ENABLE_MCP_REPORTING else 'DISABLED'}\n" # Use instance variable
            f"Product/Service: {self.product_service_context[:100]}{'...' if len(self.product_service_context) > 100 else ''}",
            title="Processing Configuration",
            border_style="green"
        ))
        
        if self.processing_mode == ProcessingMode.HYBRID:
            # Assuming standard_processing can also be async if needed, or run synchronously
            standard_results_obj = await self._standard_processing(leads_to_process, run_id, is_hybrid_component=True, overall_start_time=start_time_run_processing)
            enhanced_results_obj = await self._enhanced_processing(leads_to_process, run_id, is_hybrid_component=True, overall_start_time=start_time_run_processing)

            all_results = []
            for r_std in standard_results_obj.results:
                r_std['actual_processing_mode'] = ProcessingMode.STANDARD.value
                all_results.append(r_std)
            for r_enh in enhanced_results_obj.results:
                r_enh['actual_processing_mode'] = ProcessingMode.ENHANCED.value
                all_results.append(r_enh)

            # Consolidate metrics for hybrid mode
            hybrid_metrics = {
                "standard_metrics": standard_results_obj.metrics,
                "enhanced_metrics": enhanced_results_obj.metrics,
                "total_tokens_used": standard_results_obj.metrics.get("total_tokens_used",0) + enhanced_results_obj.metrics.get("total_tokens_used",0)
            }
            return ProcessingResults(
                mode=ProcessingMode.HYBRID,
                total_leads=len(leads_to_process),
                successful_leads=standard_results_obj.successful_leads + enhanced_results_obj.successful_leads,
                failed_leads=standard_results_obj.failed_leads + enhanced_results_obj.failed_leads,
                processing_time=time.time() - start_time_run_processing, # Total time for both
                results=all_results,
                metrics=hybrid_metrics
            )
        elif self.processing_mode == ProcessingMode.ENHANCED:
            return await self._enhanced_processing(leads_to_process, run_id, overall_start_time=start_time_run_processing) # await
        else:
            return await self._standard_processing(leads_to_process, run_id, overall_start_time=start_time_run_processing) # await

    async def _standard_processing(self, leads_to_process: List[SiteData], run_id: str, is_hybrid_component: bool = False, overall_start_time: Optional[float] = None) -> ProcessingResults: # Made async
        results = []
        successful = 0
        failed = 0
        processing_start_time = time.time()
        
        with Progress(console=self.console, transient=not is_hybrid_component) as progress:
            task = progress.add_task("[blue]Standard Processing...", total=len(leads_to_process))
            for site_data in leads_to_process:
                lead_id = str(uuid.uuid4())
                self._report_lead_start_to_mcp(lead_id, run_id, str(site_data.url), "LeadIntakeAgent (Standard)")

                progress.update(task, description=f"[blue]Std Proc: {str(site_data.url)[:50]}...")
                try:
                    validated_lead = await self.lead_intake_agent.execute(site_data, lead_id=lead_id, run_id=run_id) # await and pass ids
                    if not validated_lead.is_valid:
                        failed += 1; progress.advance(task); continue
                    
                    analyzed_lead = await self.lead_analysis_agent.execute(validated_lead, lead_id=lead_id, run_id=run_id) # await and pass ids
                    if analyzed_lead.analysis.relevance_score < 0.3:
                        failed += 1; progress.advance(task); continue
                    
                    result = {
                        "lead_id": lead_id, "run_id": run_id,
                        "url": str(site_data.url),
                        "company_name": self._extract_company_name_from_analyzed(analyzed_lead),
                        "relevance_score": analyzed_lead.analysis.relevance_score,
                        "status": "standard_processed"
                    }
                    results.append(result)
                    successful += 1
                except Exception as e:
                    logger.error(f"Standard processing failed for {site_data.url} (Lead ID: {lead_id}): {e}")
                    failed += 1
                progress.advance(task)
                if not is_hybrid_component: time.sleep(self.rate_limit_delay)
        
        current_run_time = time.time() - processing_start_time
        return ProcessingResults(
            mode=ProcessingMode.STANDARD, total_leads=len(leads_to_process),
            successful_leads=successful, failed_leads=failed,
            processing_time=current_run_time, results=results,
            metrics={"avg_processing_time": current_run_time / max(1,len(leads_to_process)),
                     "success_rate": successful / max(1,len(leads_to_process)),
                     "total_tokens_used": self.llm_client.get_usage_stats()["total_tokens"]}
        )

    async def _enhanced_processing(self, leads_to_process: List[SiteData], run_id: str, is_hybrid_component: bool = False, overall_start_time: Optional[float] = None) -> ProcessingResults: # Made async
        results = []
        successful = 0
        failed = 0
        processing_start_time = time.time()
        
        with Progress(console=self.console, transient=not is_hybrid_component) as progress:
            task = progress.add_task("[green]Enhanced Processing...", total=len(leads_to_process))
            for site_data in leads_to_process:
                lead_id = str(uuid.uuid4())
                self._report_lead_start_to_mcp(lead_id, run_id, str(site_data.url), "LeadIntakeAgent (Enhanced)")

                progress.update(task, description=f"[green]Enh Proc: {str(site_data.url)[:50]}...")
                try:
                    validated_lead = await self.lead_intake_agent.execute(site_data, lead_id=lead_id, run_id=run_id) # await and pass ids
                    if not validated_lead.is_valid:
                        failed += 1; progress.advance(task); continue
                    
                    analyzed_lead = await self.lead_analysis_agent.execute(validated_lead, lead_id=lead_id, run_id=run_id) # await and pass ids
                    if analyzed_lead.analysis.relevance_score < 0.1:
                        failed += 1; progress.advance(task); continue
                    
                    comprehensive_package = await self.enhanced_processor.process(analyzed_lead, lead_id=lead_id, run_id=run_id) # await and pass ids
                    
                    result = {
                        "lead_id": lead_id, "run_id": run_id,
                        "url": str(site_data.url),
                        "company_name": comprehensive_package.processing_metadata.get("company_name", "Unknown"),
                        "overall_confidence_score": comprehensive_package.confidence_score,
                        "roi_potential_score": comprehensive_package.roi_potential_score,
                        "brazilian_market_fit": comprehensive_package.brazilian_market_fit,
                        "status": "enhanced_complete",
                        "processing_time_seconds": comprehensive_package.processing_metadata.get("total_processing_time", 0),
                    }
                    es = comprehensive_package.enhanced_strategy
                    if es:
                        if es.lead_qualification and not es.lead_qualification.error_message:
                            result["qualification_tier"] = es.lead_qualification.qualification_tier
                            result["qualification_justification"] = es.lead_qualification.justification
                        if es.pain_point_analysis and not es.pain_point_analysis.error_message:
                            result["primary_pain_category"] = es.pain_point_analysis.primary_pain_category
                            result["pain_urgency_level"] = es.pain_point_analysis.urgency_level
                            result["num_detailed_pain_points"] = len(es.pain_point_analysis.detailed_pain_points or [])
                        if es.tot_synthesized_action_plan and not es.tot_synthesized_action_plan.error_message:
                            result["recommended_strategy_name"] = es.tot_synthesized_action_plan.recommended_strategy_name
                        if es.detailed_approach_plan and not es.detailed_approach_plan.error_message:
                            result["detailed_plan_main_objective"] = es.detailed_approach_plan.main_objective
                        if es.contact_information and not es.contact_information.error_message:
                            result["contacts_emails_found"] = len(es.contact_information.emails_found or [])
                            result["contacts_instagram_found"] = len(es.contact_information.instagram_profiles or [])
                        if es.external_intelligence and not es.external_intelligence.error_message:
                            result["tavily_enriched"] = bool(es.external_intelligence.tavily_enrichment and "enrichment failed" not in es.external_intelligence.tavily_enrichment.lower())
                        if es.value_propositions:
                            result["num_value_propositions"] = len([vp for vp in es.value_propositions if not vp.error_message])
                        if es.strategic_questions: result["num_strategic_questions"] = len(es.strategic_questions)
                        if es.competitor_intelligence and not es.competitor_intelligence.error_message:
                             result["num_competitors_identified"] = len(es.competitor_intelligence.identified_competitors or [])
                        if es.purchase_triggers and not es.purchase_triggers.error_message:
                            result["num_purchase_triggers"] = len(es.purchase_triggers.identified_triggers or [])
                        if es.objection_framework and not es.objection_framework.error_message:
                            result["num_objections_prepared"] = len(es.objection_framework.anticipated_objections or [])
                    pm = comprehensive_package.enhanced_personalized_message
                    if pm and not pm.error_message and pm.primary_message:
                        result["message_channel"] = pm.primary_message.channel.value if pm.primary_message.channel else None
                    ib = comprehensive_package.internal_briefing
                    if ib and not ib.error_message:
                        result["internal_briefing_executive_summary_present"] = bool(ib.executive_summary and ib.executive_summary != "Não especificado")
                    results.append(result); successful += 1
                except Exception as e:
                    logger.error(f"Enhanced processing failed for {site_data.url} (Lead ID: {lead_id}): {e}\n{traceback.format_exc()}")
                    failed += 1
                progress.advance(task)
                if not is_hybrid_component: await asyncio.sleep(self.rate_limit_delay) # await asyncio.sleep

        current_run_time = time.time() - processing_start_time # Use processing_start_time as run_start_time is not defined here
        return ProcessingResults(
            mode=ProcessingMode.ENHANCED, total_leads=len(leads_to_process),
            successful_leads=successful, failed_leads=failed,
            processing_time=current_run_time, results=results,
            metrics={
                "avg_processing_time": current_run_time / max(1,len(leads_to_process)),
                "success_rate": successful / max(1,len(leads_to_process)),
                "total_tokens_used": self.llm_client.get_usage_stats()["total_tokens"],
                "avg_overall_confidence_score": sum(r.get("overall_confidence_score", 0) for r in results if r.get("overall_confidence_score") is not None) / max(1, successful),
                "avg_roi_potential": sum(r.get("roi_potential_score", 0) for r in results if r.get("roi_potential_score") is not None) / max(1, successful),
                "high_potential_leads": len([r for r in results if r.get("qualification_tier") == "Alto Potencial" or r.get("qualification_tier") == "High Potential"])
            }
        )
    
    def generate_report(self, results: ProcessingResults) -> None:
        self.console.rule(f"[bold cyan]Processing Report - {results.mode.value.upper()} Mode[/bold cyan]")

        summary_table = Table(title="Overall Summary")
        summary_table.add_column("Metric", style="dim cyan")
        summary_table.add_column("Value", style="bold green")
        summary_table.add_row("Total Leads Input", str(results.total_leads))
        summary_table.add_row("Successfully Processed", str(results.successful_leads))
        summary_table.add_row("Failed to Process", str(results.failed_leads))
        if results.total_leads > 0 and results.successful_leads > 0 : # Avoid division by zero if no leads processed or all failed
            summary_table.add_row("Success Rate", f"{(results.successful_leads/results.total_leads)*100:.1f}%")
        else:
            summary_table.add_row("Success Rate", "N/A (or 0.0%)")

        summary_table.add_row("Total Processing Time", f"{results.processing_time:.2f}s")
        if results.total_leads > 0 and results.processing_time > 0 :
            avg_time_per_lead = results.processing_time / results.total_leads
            summary_table.add_row("Avg Time per Lead", f"{avg_time_per_lead:.2f}s")
        else:
            summary_table.add_row("Avg Time per Lead", "N/A")

        if "total_tokens_used" in results.metrics:
            summary_table.add_row("Total LLM Tokens Used", str(results.metrics["total_tokens_used"]))
        elif "standard_metrics" in results.metrics and "enhanced_metrics" in results.metrics:
             total_tokens = results.metrics["standard_metrics"].get("total_tokens_used",0) + results.metrics["enhanced_metrics"].get("total_tokens_used",0)
             summary_table.add_row("Total LLM Tokens Used (Std + Enh)", str(total_tokens))

        self.console.print(summary_table)

        if results.mode == ProcessingMode.ENHANCED and results.results and results.successful_leads > 0:
            enhanced_metrics_table = Table(title="Enhanced Processing Aggregate Metrics")
            enhanced_metrics_table.add_column("Aggregate Metric", style="dim cyan")
            enhanced_metrics_table.add_column("Value", style="bold green")
            
            if "avg_overall_confidence_score" in results.metrics:
                enhanced_metrics_table.add_row("Avg. Overall Confidence", f"{results.metrics['avg_overall_confidence_score']:.3f}")
            if "avg_roi_potential" in results.metrics:
                enhanced_metrics_table.add_row("Avg. ROI Potential", f"{results.metrics['avg_roi_potential']:.3f}")
            if "high_potential_leads" in results.metrics:
                enhanced_metrics_table.add_row("High Potential Leads", str(results.metrics['high_potential_leads']))

            num_leads_with_contacts = sum(1 for r in results.results if r.get('contacts_emails_found', 0) > 0 or r.get('contacts_instagram_found', 0) > 0)
            if results.successful_leads > 0:
                percent_leads_with_contacts = (num_leads_with_contacts / results.successful_leads) * 100
                enhanced_metrics_table.add_row("Leads with Contacts (%)", f"{percent_leads_with_contacts:.1f}%")
            else:
                enhanced_metrics_table.add_row("Leads with Contacts (%)", "N/A")

            avg_detailed_pain_points = sum(r.get('num_detailed_pain_points', 0) for r in results.results) / max(1, results.successful_leads)
            enhanced_metrics_table.add_row("Avg. Num. Detailed Pain Points", f"{avg_detailed_pain_points:.2f}")
            
            avg_value_props = sum(r.get('num_value_propositions', 0) for r in results.results) / max(1, results.successful_leads)
            enhanced_metrics_table.add_row("Avg. Num. Value Propositions", f"{avg_value_props:.2f}")

            qualification_counts = {}
            for result_item in results.results:
                tier = result_item.get("qualification_tier", "Unknown")
                qualification_counts[tier] = qualification_counts.get(tier, 0) + 1
            for tier, count in qualification_counts.items():
                enhanced_metrics_table.add_row(f"Leads in Tier '{tier}'", str(count))
            
            self.console.print(enhanced_metrics_table)

            self.console.print("\n✨ [bold magenta]Individual Lead Summaries (First 5 Processed):[/bold magenta]")
            for i, lead_item in enumerate(results.results):
                if i >= 5 and len(results.results) > 7 :
                    self.console.print(f"... and {len(results.results) - 5} more successfully processed leads.")
                    break

                panel_content = (
                    f"[bold]URL:[/bold] {lead_item.get('url')}\n"
                    f"[bold]Lead ID (MCP):[/bold] {lead_item.get('lead_id', 'N/A')}\n"
                    f"[bold]Overall Confidence:[/bold] {lead_item.get('overall_confidence_score', 'N/A'):.3f}\n"
                    f"[bold]Qualification Tier:[/bold] {lead_item.get('qualification_tier', 'N/A')} "
                    f"([italic]Justification:[/italic] {str(lead_item.get('qualification_justification', 'N/A'))[:70]}...)\n"
                    f"[bold]Primary Pain Category:[/bold] {lead_item.get('primary_pain_category', 'N/A')} "
                    f"([italic]Urgency:[/italic] {lead_item.get('pain_urgency_level', 'N/A')}, [italic]Count:[/italic] {lead_item.get('num_detailed_pain_points', 0)})\n"
                    f"[bold]Recommended Strategy:[/bold] {lead_item.get('recommended_strategy_name', 'N/A')}\n"
                    f"  [italic]Hook:[/italic] {str(lead_item.get('recommended_strategy_hook', 'N/A'))[:70]}...\n"
                    f"[bold]Detailed Plan Objective:[/bold] {str(lead_item.get('detailed_plan_main_objective', 'N/A'))[:70]}...\n"
                    f"[bold]Message Channel:[/bold] {lead_item.get('message_channel', 'N/A')}\n"
                    f"[bold]Contacts - Emails:[/bold] {lead_item.get('contacts_emails_found', 0)} [bold]Insta:[/bold] {lead_item.get('contacts_instagram_found',0)}\n"
                    f"[bold]Tavily Enriched:[/bold] {'Yes' if lead_item.get('tavily_enriched') else 'No'}\n"
                    f"[bold]VPs:[/bold] {lead_item.get('num_value_propositions',0)} | "
                    f"[bold]Strat. Qs:[/bold] {lead_item.get('num_strategic_questions',0)} | "
                    f"[bold]Competitors:[/bold] {lead_item.get('num_competitors_identified',0)} | "
                    f"[bold]Triggers:[/bold] {lead_item.get('num_purchase_triggers',0)} | "
                    f"[bold]Objections:[/bold] {lead_item.get('num_objections_prepared',0)}"
                )
                self.console.print(Panel(panel_content, title=f"Lead: {lead_item.get('company_name', 'N/A')}", border_style="blue", expand_width=False))

        elif results.mode == ProcessingMode.HYBRID:
            self.console.print("[info]Hybrid mode executed. Summary table shows combined totals. Detailed metrics for each pipeline run were logged during processing if log level was INFO/DEBUG.[/info]")
            pass

    def save_results(self, results: ProcessingResults, output_file: str) -> None:
        output_data = {
            "processing_summary": {
                "mode": results.mode.value, "timestamp": datetime.now().isoformat(),
                "total_leads": results.total_leads, "successful_leads": results.successful_leads,
                "failed_leads": results.failed_leads, "processing_time": results.processing_time,
                "metrics": results.metrics
            },
            "configuration": {
                "product_service_context": self.product_service_context,
                "competitors_list": self.competitors_list,
                "tavily_enabled": hasattr(self, 'enhanced_processor') and bool(self.enhanced_processor.tavily_api_key if hasattr(self.enhanced_processor, 'tavily_api_key') else False)
            },
            "results": results.results
        }
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        self.console.print(f"✅ Results saved to: {output_file}")
    
    def _extract_company_name_from_analyzed(self, analyzed_lead: AnalyzedLead) -> str:
        site_data = analyzed_lead.validated_lead.site_data
        if site_data.google_search_data and site_data.google_search_data.title:
            title = site_data.google_search_data.title
            company_name = title.split(" - ")[0].split(" | ")[0].split(": ")[0]
            if len(company_name) > 5: return company_name.strip()
        url = str(site_data.url)
        domain = url.replace('https://', '').replace('http://', '').split('/')[0]
        return domain.replace('www.', '').split('.')[0].title()

def load_harvester_data(file_path: str) -> HarvesterOutput:
    try:
        with open(file_path, 'r', encoding='utf-8') as f: data = json.load(f)
        return HarvesterOutput(**data)
    except Exception as e:
        logger.error(f"Failed to load harvester data from {file_path}: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description="Enhanced Nellia Prospector - Multi-mode AI lead processing")
    parser.add_argument("harvester_file", help="Path to harvester output JSON file")
    parser.add_argument("-p", "--product", required=True, help="Product/service context for analysis")
    parser.add_argument("-m", "--mode", choices=[mode.value for mode in ProcessingMode], default=ProcessingMode.ENHANCED.value, help="Processing mode")
    parser.add_argument("-c", "--competitors", default="", help="Known competitors list")
    parser.add_argument("-n", "--limit", type=int, help="Limit number of leads to process")
    parser.add_argument("-o", "--output", help="Output file path (default: auto-generated)")
    parser.add_argument("-l", "--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO", help="Logging level")
    args = parser.parse_args()
    
    logger.remove()
    logger.add(sys.stderr, level=args.log_level.upper())

    # Required for async main
    import asyncio

    async def async_main(): # Wrap main logic in async function
        harvester_data = load_harvester_data(args.harvester_file)
        processor = EnhancedNelliaProspector(
            product_service_context=args.product, competitors_list=args.competitors,
            processing_mode=ProcessingMode(args.mode), tavily_api_key=os.getenv("TAVILY_API_KEY")
        )
        results = await processor.process_leads(harvester_data, args.limit) # await
        processor.generate_report(results)
        if args.output: output_file = args.output
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"enhanced_prospector_results_{args.mode}_{timestamp}.json"
        processor.save_results(results, output_file)
        
        if results.mode == ProcessingMode.ENHANCED and results.successful_leads > 0:
            avg_confidence = results.metrics.get("avg_overall_confidence_score", results.metrics.get("avg_confidence_score",0.0))
            avg_roi_potential = results.metrics.get("avg_roi_potential", 0.0)
            high_potential_count = results.metrics.get("high_potential_leads", 0)
            rprint(Panel(
                f"🎯 ROI OPTIMIZATION SUMMARY\n\n"
                f"Target: 527% ROI Achievement\n"
                f"High Potential Leads: {high_potential_count}/{results.successful_leads}\n"
                f"Avg Overall Confidence Score: {avg_confidence:.3f}\n"
                f"Avg ROI Potential: {avg_roi_potential:.3f}\n"
                f"Brazilian Market Optimization: ENABLED\n\n"
                f"✨ Ready for high-converting outreach!",
                title="Enhanced Processing Complete", border_style="gold1"
            ))

    try:
        asyncio.run(async_main()) # Run the async main function
    except KeyboardInterrupt: logger.info("Processing interrupted by user"); sys.exit(1)
    except Exception as e: logger.error(f"Processing failed: {e}\n{traceback.format_exc()}"); sys.exit(1)

if __name__ == "__main__":
    # main() # Original synchronous call commented out
    pass # Main execution is now handled by asyncio.run(async_main())
